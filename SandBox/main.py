from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel
import mimetypes
import os
from urllib.parse import quote
from typing import List
import logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import json

from SandBox.container_manager import ContainerManager
import SandBox.config as config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

def cleanup_job():
    manager.cleanup_idle_containers()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    logger.info("Application starting up")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        cleanup_job,
        trigger=IntervalTrigger(seconds=config.CLEANUP_INTERVAL),
        id="cleanup_job",
        replace_existing=True
    )
    scheduler.start()
    yield
    # 关闭时
    logger.info("Application shutting down")
    scheduler.shutdown()
    manager.shutdown()

app = FastAPI(title="Docker Python Sandbox", lifespan=lifespan)
manager = ContainerManager()

class RunRequest(BaseModel):
    image: str = config.DEFAULT_IMAGE
    mem_limit: str = config.DEFAULT_MEM_LIMIT
    cpu_quota: int = config.DEFAULT_CPU_QUOTA
    network_disabled: bool = config.DEFAULT_NETWORK_DISABLED

class ExecRequest(BaseModel):
    cmd: List[str]
    timeout: int = 30

class ExecPythonRequest(BaseModel):
    code: str
    timeout: int = 30

@app.post("/containers/run")
async def run_container(req: RunRequest = RunRequest()):
    cid = manager.create_container(
        image=req.image,
        mem_limit=req.mem_limit,
        cpu_quota=req.cpu_quota,
        network_disabled=req.network_disabled,
    )
    if cid is None:
        raise HTTPException(status_code=429, detail="Resource exhausted: no idle container to prune")
    manager.exec_command(cid, ["mkdir", "-p", "/workspace"])
    return {"success": True, "data": {"container_id": cid}}

@app.post("/containers/{container_id}/stop")
async def stop_container(container_id: str):
    if not manager.container_exists(container_id):
        raise HTTPException(status_code=404, detail="Container not found")
    manager.stop_container(container_id)
    return {"success": True, "message": "Container stopped"}

@app.post("/containers/{container_id}/exec")
async def exec_command(container_id: str, req: ExecRequest):
    try:
        exit_code, stdout, stderr = manager.exec_command(container_id, req.cmd, req.timeout)
        return {"success": True, "data": {"exit_code": exit_code, "stdout": stdout, "stderr": stderr}}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/containers/{container_id}/exec_python")
async def exec_python(container_id: str, req: ExecPythonRequest):
    cmd = ["python", "-c", req.code]
    try:
        exit_code, stdout, stderr = manager.exec_command(container_id, cmd, req.timeout)
        return {"success": True, "data": {"exit_code": exit_code, "stdout": stdout, "stderr": stderr}}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/containers/{container_id}/upload")
async def upload_file(container_id: str, path: str = Form(...), file: UploadFile = File(...)):
    try:
        content = await file.read()
        manager.upload_file(container_id, path, content)
        return {"success": True, "message": "File uploaded"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/containers/{container_id}/download")
async def download_file(container_id: str, path: str):
    try:
        content = manager.download_file(container_id, path)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    mime_type, _ = mimetypes.guess_type(path)
    if mime_type is None:
        mime_type = "application/octet-stream"

    filename = path.split('/')[-1]
    encoded_filename = quote(filename, safe='')

    # 生成一个 ASCII 回退名（如 "file.txt"）
    base, ext = os.path.splitext(filename)
    fallback_name = f"file{ext}" if ext else "file"

    # 构造 Content-Disposition（符合 RFC 6266 + RFC 5987）
    content_disposition = (
        f'attachment; filename="{fallback_name}"; '
        f"filename*=UTF-8''{encoded_filename}"
    )

    # 自定义头 X-Filename 也进行编码（确保仅含 ASCII）
    safe_filename = quote(filename, safe='')

    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": content_disposition,
            "X-Filename": safe_filename,
            "X-Mime-Type": mime_type,
            "X-File-Size": str(len(content))
        }
    )

@app.get("/containers/{container_id}/status")
async def container_status(container_id: str):
    """获取容器的存在性、运行状态及最后活动时间"""
    status = manager.container_status(container_id)
    return {"success": True, "data": status}

_LIST_FILES_SCRIPT = '''import os, json, stat, time
ws = "/workspace"
results = []
img_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff", ".tif"}

def is_text(fp):
    try:
        with open(fp, "rb") as f:
            return b"\\x00" not in f.read(4096)
    except:
        return False

def img_size(fp):
    try:
        from PIL import Image
        with Image.open(fp) as img:
            return img.size
    except:
        return None

for root, dirs, files in os.walk(ws):
    dirs[:] = [d for d in dirs if not d.startswith(".")]
    for name in sorted(files):
        if name.startswith("."):
            continue
        path = os.path.join(root, name)
        try:
            st = os.stat(path)
        except:
            continue
        rel = os.path.relpath(path, ws)
        info = {"name": rel, "size": st.st_size,
                "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(st.st_mtime))}
        lo = name.lower()
        ext = os.path.splitext(name)[1].lower()
        if ext in img_exts:
            info["type"] = "image"
            wh = img_size(path)
            if wh:
                info["width"], info["height"] = wh
        elif is_text(path):
            info["type"] = "text"
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = 0
                    chars = 0
                    for line in f:
                        lines += 1
                        chars += len(line)
                info["lines"] = lines
                info["chars"] = chars
            except:
                pass
        else:
            info["type"] = "binary"
        results.append(info)

print(json.dumps(results, ensure_ascii=False))
'''

@app.get("/containers/{container_id}/files")
async def list_files(container_id: str):
    try:
        exit_code, stdout, stderr = manager.exec_command(
            container_id, ["python", "-c", _LIST_FILES_SCRIPT], timeout=30
        )
        if exit_code != 0:
            raise HTTPException(status_code=500, detail=f"Failed to list files: {stderr}")
        files = json.loads(stdout) if stdout.strip() else []
        return {"success": True, "data": files}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}