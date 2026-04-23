import threading
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json
import docker
from docker.errors import DockerException, NotFound, APIError

import SandBox.config as config

from SandBox.utils import tar_pack, tar_unpack

logger = logging.getLogger(__name__)


class ContainerManager:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.containers: Dict[str, dict] = {}  # container_id -> {last_activity, created_at}
        self.lock = threading.Lock()

    def cleanup_idle_containers(self):
        """
        手动触发空闲容器清理。
        销毁所有超过 IDLE_TIMEOUT 未活动的容器。
        """
        now = time.time()
        with self.lock:
            idle_candidates = [
                cid for cid, info in self.containers.items()
                if now - info["last_activity"] > config.IDLE_TIMEOUT
            ]
        for cid in idle_candidates:
            self._destroy_container(cid, reason="idle timeout")

    def _destroy_container(self, container_id: str, reason: str = "manual") -> bool:
        """
        销毁容器，返回是否成功。
        """
        with self.lock:
            if container_id not in self.containers:
                return False

        try:
            container = self.docker_client.containers.get(container_id)
        except NotFound:
            # 容器已不存在，仅清理跟踪记录
            with self.lock:
                self.containers.pop(container_id, None)
            logger.info(f"Container {container_id} already removed, cleaned tracking")
            return True
        except DockerException as e:
            logger.error(f"Cannot get container {container_id}: {e}")
            # 无法确认状态，但仍移除跟踪记录（避免泄漏）
            with self.lock:
                self.containers.pop(container_id, None)
            return False

        try:
            container.reload()
            if container.status == 'running':
                container.stop(timeout=5)
                logger.debug(f"Container {container_id} stopped")
            container.remove(force=True)
            logger.info(f"Container {container_id} destroyed: {reason}")
            return True
        except NotFound:
            # 操作过程中容器已消失，直接忽略
            logger.info(f"Container {container_id} vanished during destroy")
            return True
        except (APIError, DockerException) as e:
            logger.error(f"Failed to destroy container {container_id}: {e}")
            return False

    def _prune_idle_for_capacity(self) -> bool:
        """
        在达到上限时，按最后活动时间升序销毁空闲容器，直到有空位。
        返回 True 表示现在可以创建新容器，False 表示资源仍然不足。
        """
        with self.lock:
            current_count = len(self.containers)
            if current_count < config.MAX_CONTAINERS:
                return True
            # 需要释放的容器数量（至少释放一个）
            need_free = current_count - config.MAX_CONTAINERS + 1
            # 按最后活动时间升序排序，取最久未活动的 need_free 个
            sorted_containers = sorted(self.containers.items(), key=lambda x: x[1]["last_activity"])
            to_remove = [cid for cid, _ in sorted_containers[:need_free]]
        # 释放锁后逐个销毁，避免死锁
        for cid in to_remove:
            self._destroy_container(cid, reason="resource shortage")
        # 再次检查是否还有空位
        with self.lock:
            return len(self.containers) < config.MAX_CONTAINERS

    def create_container(
        self,
        image: str = config.DEFAULT_IMAGE,
        mem_limit: str = config.DEFAULT_MEM_LIMIT,
        cpu_quota: int = config.DEFAULT_CPU_QUOTA,
        network_disabled: bool = config.DEFAULT_NETWORK_DISABLED,
    ) -> Optional[str]:
        """创建并启动一个新容器，返回容器ID，若资源不足返回None"""
        # 资源不足时尝试清理空闲容器
        if not self._prune_idle_for_capacity():
            logger.warning("No idle containers to prune, cannot create new container")
            return None

        try:
            # 使用 tail -f /dev/null 保持容器运行
            container = self.docker_client.containers.create(
                image=image,
                command=["tail", "-f", "/dev/null"],
                mem_limit=mem_limit,
                cpu_quota=cpu_quota,
                network_disabled=network_disabled,
                detach=True,
            )
            container.start()
            cid = container.id
            now = time.time()
            with self.lock:
                self.containers[cid] = {
                    "last_activity": now,
                    "created_at": now,
                }
            logger.info(f"Created container {cid}")
            return cid
        except DockerException as e:
            logger.error(f"Failed to create container: {e}")
            return None

    def stop_container(self, container_id: str) -> bool:
        """停止并删除容器"""
        return self._destroy_container(container_id, reason="user request")

    def update_activity(self, container_id: str):
        """更新容器的最后活动时间"""
        with self.lock:
            if container_id in self.containers:
                self.containers[container_id]["last_activity"] = time.time()

    def container_exists(self, container_id: str) -> bool:
        """检查容器是否被跟踪且实际存在"""
        with self.lock:
            if container_id not in self.containers:
                return False
        try:
            self.docker_client.containers.get(container_id)
            return True
        except NotFound:
            with self.lock:
                self.containers.pop(container_id, None)
            return False

    def container_status(self, container_id: str) -> dict:
        """返回容器状态信息"""
        with self.lock:
            tracked = container_id in self.containers
            last_activity = self.containers.get(container_id, {}).get("last_activity")

        if not tracked:
            return {"exists": False, "running": False, "tracked": False}

        try:
            container = self.docker_client.containers.get(container_id)
            status = container.status  # "running", "exited", etc.
            return {
                "exists": True,
                "running": status == "running",
                "tracked": True,
                "last_activity": last_activity,
            }
        except NotFound:
            with self.lock:
                self.containers.pop(container_id, None)
            return {"exists": False, "running": False, "tracked": False}

    def get_container(self, container_id: str):
        """获取 Docker 容器对象"""
        try:
            return self.docker_client.containers.get(container_id)
        except NotFound:
            return None

    def exec_command(self, container_id: str, cmd: List[str], timeout: int = 30):
        """
        在容器中执行命令，返回 (exit_code, stdout, stderr)
        使用 timeout 命令包装原始命令，确保执行时长受控
        """
        if not self.container_exists(container_id):
            raise ValueError(f"Container {container_id} not found")
        self.update_activity(container_id)
        container = self.get_container(container_id)
        if not container:
            raise ValueError(f"Container {container_id} not running")

        # 使用 timeout 命令包装（要求容器内存在 timeout 命令，python:3.x-slim 默认包含）
        wrapped_cmd = ["timeout", str(timeout)] + cmd
        try:
            exec_result = container.exec_run(wrapped_cmd, stdout=True, stderr=True, demux=True)
            exit_code = exec_result.exit_code
            stdout = exec_result.output[0].decode("utf-8", errors="replace") if exec_result.output[0] else ""
            stderr = exec_result.output[1].decode("utf-8", errors="replace") if exec_result.output[1] else ""

            log_cmd = " ".join(cmd)
            timestamp = datetime.now().isoformat()
            stdout_preview = stdout[:200] + "..." if len(stdout) > 200 else stdout
            stderr_preview = stderr[:100] + "..." if len(stderr) > 100 else stderr

            log_entry = {
                "timestamp": timestamp,
                "command": log_cmd,
                "exit_code": exit_code,
                "stdout_preview": stdout_preview,
                "stderr_preview": stderr_preview,
            }
            log_json = json.dumps(log_entry, ensure_ascii=False)
            write_cmd = [
                "python", "-c",
                f"import os\nos.makedirs('/workspace', exist_ok=True)\nwith open('/workspace/exec_log.txt', 'a', encoding='utf-8') as f: f.write({repr(log_json)} + '\\n')"
            ]
            container.exec_run(write_cmd)

            return exit_code, stdout, stderr
        except APIError as e:
            raise RuntimeError(f"Exec failed: {e}")

    def upload_file(self, container_id: str, dest_path: str, file_content: bytes):
        """上传文件到容器"""
        if not self.container_exists(container_id):
            raise ValueError(f"Container {container_id} not found")
        self.update_activity(container_id)
        container = self.get_container(container_id)
        if not container:
            raise ValueError(f"Container {container_id} not running")
        # 将文件打包成tar流
        tar_data = tar_pack(file_content, dest_path)
        success = container.put_archive("/", tar_data)  # 相对根目录解压
        if not success:
            raise RuntimeError("Upload failed")

    def download_file(self, container_id: str, file_path: str) -> bytes:
        if not self.container_exists(container_id):
            raise ValueError(f"Container {container_id} not found")
        self.update_activity(container_id)
        container = self.get_container(container_id)
        if not container:
            raise ValueError(f"Container {container_id} not running")
        try:
            bits, stat = container.get_archive(file_path)
            tar_data = b"".join(bits)
            file_content = tar_unpack(tar_data, file_path)
            return file_content
        except APIError as e:
            raise RuntimeError(f"Download failed: {e}")

    def shutdown(self):
        """停止所有容器并关闭 Docker 客户端"""
        with self.lock:
            cids = list(self.containers.keys())
        for cid in cids:
            self._destroy_container(cid, reason="shutdown")
        self.docker_client.close()