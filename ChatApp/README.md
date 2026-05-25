# ChatApp

Chat API 服务，运行在 **port 8010**，由 `run.py` 通过 multiprocessing 启动。

## 目录结构

```
ChatApp/
├── main.py              # FastAPI 应用入口 + lifespan（初始化 DB、加载模型配置）
├── config.py            # 环境变量读取（JWT_SECRET_KEY, ADMIN_API_KEY 等）
├── auth.py              # JWT 签发/验证、密码哈希
├── database.py          # SQLite schema（6 张表）+ 全部 CRUD 函数
├── dependencies.py      # FastAPI 依赖注入（get_current_user）
├── pydantic_models.py   # 请求/响应 Pydantic schema
├── routers/             # API 路由层
│   ├── auth.py          # /api/register, /api/login, /api/me
│   ├── sessions.py      # /api/sessions CRUD + 消息历史
│   ├── chat.py          # /api/sessions/{id}/chat/stream (SSE 流式对话核心)
│   ├── files.py         # /api/sessions/{id}/files 上传/下载
│   ├── admin.py         # /api/admin/* 管理面板 API
│   └── models.py        # /api/models 公开模型列表
├── providers/           # LLM 提供商适配层
│   ├── llm_provider.py  # 抽象基类（统一接口）
│   ├── deepseek.py      # DeepSeek API（流式 SSE 解析、工具调用）
│   ├── openrouter.py    # OpenRouter API（含 reasoning 支持）
│   ├── gemini.py        # Google Gemini（多模态、thought signature）
│   ├── opencode_go.py   # OpenCode Go API
│   ├── bigmodel.py      # 智谱 BigModel（未接入 PROVIDER_MAP）
│   ├── models.py        # supported_models 字典 + init_models()
│   └── model_manager.py # 从 DB 加载/刷新模型配置、取标题/图片/音频模型
└── tools/               # LLM 工具层
    ├── registry.py      # @llm_tool 装饰器 + 全局工具注册表
    ├── sandbox.py       # HTTP 客户端调用 SandBox 服务
    ├── web_search.py    # Tavily 搜索/提取/爬取 API
    ├── omni.py          # 图片/音频转录（调用 Gemini/OpenRouter 多模态）
    └── utils.py         # 图片压缩工具
```

## 核心架构

### 启动流程

```
run.py
  └─> main.py lifespan
        ├─> init_db()          # 建表 + 种子数据
        └─> init_models()      # 从 model_configs 表加载到内存
```

### 对话流程

```
POST /api/sessions/{id}/chat/stream (SSE)
  ├─> 验证 session 归属
  ├─> 从 supported_models 查模型配置
  ├─> 通过 PROVIDER_MAP 选择 Provider
  ├─> 检查/启动 SandBox 容器
  ├─> 注册工具（代码执行 / 搜索）
  ├─> 构建 LLM 消息历史（含多轮工具调用）
  ├─> 调用 Provider 流式 API
  ├─> 处理工具调用 → 调用 SandBox / Tavily
  ├─> 流式返回 SSE 事件：content, reasoning, tool_call, tool_result, file, error, done
  └─> 首次对话自动生成标题
```

### Provider 架构

```
LLMProvider (抽象基类)
  ├── DeepSeekProvider    # api.deepseek.com
  ├── OpenRouterProvider  # openrouter.ai
  ├── GeminiProvider      # generativelanguage.googleapis.com
  └── OpenCodeGoProvider  # opencode.ai/zen/go/v1

PROVIDER_MAP = {
    "deepseek": ...,
    "openrouter": ...,
    "gemini": ...,
    "opencode_go": ...,
}
```

所有 Provider 输出统一的事件流：`content | reasoning | tool_calls_delta | tool_calls_complete | usage | done`

### 数据库表

| 表名 | 用途 |
|------|------|
| `users` | 用户账号 |
| `sessions` | 对话会话 |
| `messages` | 消息记录（含 tool_call / tool_result） |
| `files` | 上传文件元数据 |
| `model_configs` | 模型配置（provider, model, thinking 等） |
| `token_usage` | Token 用量统计 |

### 依赖关系

```
ChatApp
  ├─> SandBox (HTTP)    → 代码执行、文件操作
  ├─> DeepSeek (HTTPS)  → LLM 对话
  ├─> OpenRouter (HTTPS)→ LLM 对话
  ├─> Gemini (HTTPS)    → LLM 对话 + 多模态
  ├─> OpenCode Go (HTTPS)→ LLM 对话
  └─> Tavily (HTTPS)    → 网页搜索
```
