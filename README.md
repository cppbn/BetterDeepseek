
# BetterDeepseek

BetterDeepseek 是一个增强版的 Deepseek 对话服务，支持联网搜索、Agent 沙盒等功能。

## 前置要求

- Python 3.10+
- Docker 20.10+
- 有效的 API Keys：
  - [Deepseek API Key](https://platform.deepseek.com/)
  - [Tavily API Key](https://tavily.com/)
  - [OpenRouter API Key](https://openrouter.ai/)

## 前端部署

前端为静态文件，直接通过 Nginx 提供服务。

### 获取构建产物

前往 [Releases](https://github.com/cppbn/BetterDeepseek/releases) 页面，下载最新版本的 `dist.zip` 。

```bash
# 下载示例（请替换为最新版本）
wget https://github.com/cppbn/BetterDeepseek/releases/download/v1.0.0/dist.zip
```

### 部署到 Nginx

1. 解压到网站目录（例如 `/var/www/betterdeepseek`）：

```bash
unzip dist.zip -d /var/www/betterdeepseek
```

2. 创建 Nginx 配置文件 `/etc/nginx/sites-available/betterdeepseek`（或 `conf.d/betterdeepseek.conf`）：

```nginx
server {
    listen 80;
    server_name your-domain.com;   # 替换为你的域名或 IP

    root /var/www/betterdeepseek;
    index index.html;

    location /api {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

3. 启用站点并重载 Nginx：

```bash
# 创建软链接（仅 Debian/Ubuntu）
ln -s /etc/nginx/sites-available/betterdeepseek /etc/nginx/sites-enabled/

# 测试配置并重载
nginx -t && systemctl reload nginx
```

## 后端部署
LLM 通过 Docker 创建容器来执行代码，因此先制作 python3.12-workspace 镜像。

```dockerfile
FROM python:3.12-slim

WORKDIR /workspace

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libtiff6 \
    libopenjp2-7 \
    tk8.6-dev \
    tcl8.6-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    numpy \
    pandas \
    scipy \
    sympy \
    openpyxl \
    python-docx \
    PyPDF2 \
    lxml \
    beautifulsoup4 \
    matplotlib \
    seaborn \
    pylint \
    && echo "Custom environment with specified libraries installed."
```

创建目录 python3.12-workspace，创建 dockerfile，写入以上内容。
包含的包可以自行修改，修改后建议同时修改系统提示词。

```bash
# 构建镜像（在 python3.12-workspace 下执行）
docker build -t python3.12-workspace .
```

开始部署

```bash
git clone https://github.com/cppbn/BetterDeepseek.git
cd BetterDeepseek

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cat > .env << EOF
DEEPSEEK_API_KEY="your-deepseek-key"
OPENROUTER_API_KEY="your-openrouter-key"
TAVILY_API_KEY="your-tavily-key"
JWT_SECRET_KEY="$(openssl rand -hex 32)"
ADMIN_API_KEY="$(openssl rand -hex 16)"
EOF

# 启动服务
python run.py
```

## Docker 部署

```bash
git clone https://github.com/cppbn/BetterDeepseek.git
cd BetterDeepseek

# 构建镜像
docker build -t better-deepseek .

# 创建 .env 文件（同上，也可运行时通过 -e 传入）
docker run -d \
    --name better-ds \
    -p 8010:8010 \
    --env-file .env \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -e RUN_IN_DOCKER="true" \
    better-deepseek
```

> 挂载 `/var/run/docker.sock` 是必要的，否则 LLM 无法使用 Docker 容器来执行代码

## 演示网站

[BetterDeepseek 演示站](https://chat.mytckrlh.top) – 由作者提供，仅用于功能展示，请勿压测或上传敏感信息。建议**自行部署**使用。