# SandBox

Docker 容器管理服务，运行在 **port 8020**，由 `run.py` 通过 multiprocessing 启动。

## 目录结构

```
SandBox/
├── main.py               # FastAPI 应用 + lifespan（定时清理、关闭清理）
├── config.py             # 容器限制配置（超时、内存、CPU、网络隔离）
├── container_manager.py  # Docker SDK 封装（创建/执行/上传/下载/清理）
└── utils.py              # tar 打包/解包工具（文件传输用）
```

## 核心架构

### 容器生命周期

```
ChatApp 请求
  ├─> POST /containers/run              # 创建新容器，返回 container_id
  ├─> POST /containers/{id}/exec        # 执行 shell 命令
  ├─> POST /containers/{id}/exec_python # 执行 Python 代码
  ├─> POST /containers/{id}/upload      # tar 上传文件到 /workspace
  ├─> GET  /containers/{id}/download    # 从 /workspace 下载文件（tar）
  ├─> GET  /containers/{id}/files       # 列出 /workspace 文件（含图片尺寸）
  ├─> GET  /containers/{id}/status      # 容器状态查询
  └─> POST /containers/{id}/stop        # 停止并删除容器

自动清理:
  ├─> AsyncIOScheduler 每 30s 运行 cleanup_idle_containers()
  ├─> 空闲超时 1 小时 → 自动停止
  └─> 容器数超过 MAX_CONTAINERS(10) → 优先清理最少使用的
```

### 容器配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `IDLE_TIMEOUT` | 3600s | 空闲容器清理超时 |
| `MAX_CONTAINERS` | 10 | 最大并发容器数 |
| `DEFAULT_IMAGE` | `python:3.12-slim` | 基础镜像（ChatApp 实际使用 `python3.12-workspace`） |
| `DEFAULT_MEM_LIMIT` | 512m | 内存限制 |
| `DEFAULT_CPU_QUOTA` | 50000 | CPU 配额（0.5 核） |
| `DEFAULT_NETWORK_DISABLED` | true | 容器网络隔离（安全） |

### 文件传输机制

所有文件通过 **tar 流** 传输，避免在宿主机上创建临时文件：
- **上传**: 前端传来的文件 → 内存 tar 打包 → `put_archive()` 写入容器
- **下载**: 容器内文件 → `get_archive()` 读取 tar → 返回原始流

### 依赖

```
SandBox
  ├─> docker.from_env()   # 需要挂载 /var/run/docker.sock
  └─> APScheduler          # 定时清理任务
```

### 被调用方式

仅由 **ChatApp** 通过 HTTP 内部调用（`SANDBOX_SERVICE_URL`，默认 `http://127.0.0.1:8020`），不对外暴露。
