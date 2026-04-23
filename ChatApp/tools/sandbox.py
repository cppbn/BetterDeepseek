import httpx
import logging
import shlex
from typing import Tuple, Optional
from urllib.parse import unquote

from ChatApp.config import SANDBOX_SERVICE_URL

logger = logging.getLogger(__name__)

async def _sandbox_request(
    method: str,
    endpoint: str,
    json: Optional[dict] = None,
    files: Optional[dict] = None,
    data: Optional[dict] = None,
    timeout: float = 30.0
) -> httpx.Response:
    """向沙箱服务发送请求的基础函数"""
    url = f"{SANDBOX_SERVICE_URL.rstrip('/')}{endpoint}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        if method.upper() == "GET":
            resp = await client.get(url, params=data)
        elif method.upper() == "POST":
            if files:
                resp = await client.post(url, files=files, data=data)
            else:
                resp = await client.post(url, json=json, data=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
        resp.raise_for_status()
        return resp


async def check_availability() -> bool:
    """检查沙箱服务是否可用"""
    try:
        resp = await _sandbox_request("GET", "/health", timeout=5.0)
        return resp.status_code == 200 and resp.json().get("status") == "ok"
    except Exception as e:
        logger.warning(f"Sandbox service unavailable: {e}")
        return False


async def is_running(container_id: str) -> bool:
    """检查指定容器是否正在运行"""
    try:
        resp = await _sandbox_request("GET", f"/containers/{container_id}/status")
        data = resp.json()
        return data.get("data", {}).get("running", False)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return False
        raise
    except Exception:
        return False


async def run_sandbox(
    image: str = "python:3.12-slim",
    mem_limit: str = "256m",
    cpu_quota: int = 50000,
    network_disabled: bool = True
) -> str:
    """创建并运行一个新的沙箱容器，返回容器 ID"""
    payload = {
        "image": image,
        "mem_limit": mem_limit,
        "cpu_quota": cpu_quota,
        "network_disabled": network_disabled
    }
    resp = await _sandbox_request("POST", "/containers/run", json=payload)
    data = resp.json()
    container_id = data.get("data", {}).get("container_id")
    if not container_id:
        raise RuntimeError("Failed to create container: no container_id returned")
    logger.info(f"Created sandbox container: {container_id}")
    return container_id


async def stop_sandbox(container_id: str) -> bool:
    """停止并移除容器"""
    try:
        resp = await _sandbox_request("POST", f"/containers/{container_id}/stop")
        return resp.json().get("success", False)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return False
        raise


async def exec_shell(
    container_id: str,
    cmd: str,
    timeout: int = 30
) -> str:
    """在容器中执行 shell 命令，返回合并后的输出字符串（含 stderr）"""
    payload = {"cmd": shlex.split(cmd), "timeout": timeout}
    resp = await _sandbox_request("POST", f"/containers/{container_id}/exec", json=payload)
    data = resp.json()
    exec_data = data.get("data", {})
    exit_code = exec_data.get("exit_code", -1)
    stdout = exec_data.get("stdout", "")
    stderr = exec_data.get("stderr", "")
    
    if exit_code != 0:
        return f"[Command failed with exit code {exit_code}]\nSTDERR:\n{stderr}\nSTDOUT:\n{stdout}"
    return stdout if stdout else "(no output)"


async def exec_python(
    container_id: str,
    code: str,
    timeout: int = 30
) -> str:
    """在容器中执行 Python 代码，返回合并后的输出字符串（含错误）"""
    payload = {"code": code, "timeout": timeout}
    resp = await _sandbox_request("POST", f"/containers/{container_id}/exec_python", json=payload)
    data = resp.json()
    exec_data = data.get("data", {})
    exit_code = exec_data.get("exit_code", -1)
    stdout = exec_data.get("stdout", "")
    stderr = exec_data.get("stderr", "")
    
    if exit_code != 0:
        return f"[Python execution failed with exit code {exit_code}]\nSTDERR:\n{stderr}\nSTDOUT:\n{stdout}"
    return stdout if stdout else "(no output)"


async def upload_file_to_sandbox(
    container_id: str,
    path: str,
    content: bytes
) -> bool:
    """上传文件到容器内的指定路径"""
    files = {"file": (path.split("/")[-1], content)}
    data = {"path": path}
    resp = await _sandbox_request(
        "POST",
        f"/containers/{container_id}/upload",
        files=files,
        data=data
    )
    return resp.json().get("success", False)


async def download_file_from_sandbox(
    container_id: str,
    path: str
) -> bytes:
    """从容器下载文件内容"""
    resp = await _sandbox_request("GET", f"/containers/{container_id}/download", data={"path": path})
    return resp.content

async def download_file_with_meta(
    container_id: str,
    path: str,
    timeout: float = 30.0
) -> Tuple[bytes, str, str]:
    url = f"{SANDBOX_SERVICE_URL.rstrip('/')}/containers/{container_id}/download"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, params={"path": path})
        resp.raise_for_status()

        content = resp.content
        headers = resp.headers

        filename_encoded = headers.get("X-Filename")
        if filename_encoded:
            filename = unquote(filename_encoded)
        else:
            filename = path.split('/')[-1]

        mime_type = headers.get("X-Mime-Type", "application/octet-stream")
        return content, filename, mime_type