import os

# 空闲超时（秒）
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT", 300))
# 最大容器数
MAX_CONTAINERS = int(os.getenv("MAX_CONTAINERS", 10))
# 清理扫描间隔（秒）
CLEANUP_INTERVAL = int(os.getenv("CLEANUP_INTERVAL", 30))
# 默认镜像
DEFAULT_IMAGE = os.getenv("DEFAULT_IMAGE", "python:3.12-slim")
# 默认内存限制
DEFAULT_MEM_LIMIT = os.getenv("DEFAULT_MEM_LIMIT", "512m")
# 默认 CPU 限额（微秒），50000 对应 0.5 核
DEFAULT_CPU_QUOTA = int(os.getenv("DEFAULT_CPU_QUOTA", 50000))
# 默认禁用网络
DEFAULT_NETWORK_DISABLED = os.getenv("DEFAULT_NETWORK_DISABLED", "true").lower() == "true"