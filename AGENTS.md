# AGENTS.md

## Project overview

Two FastAPI services started by `python run.py` via multiprocessing:
- **ChatApp** (port 8010) — chat API, auth, sessions, streaming SSE, admin
- **SandBox** (port 8020) — Docker container management for code execution

ChatApp calls SandBox internally over HTTP (`SANDBOX_SERVICE_URL`, default `http://127.0.0.1:8020`). Both must be running for code-execution tools to work.

Frontend is a Vue 3 + TypeScript + Vite project in `Frontend/` (separate subdirectory).

## Commands

```bash
# Backend (from repo root)
python run.py                          # starts both ChatApp:8010 + SandBox:8020

# Frontend (workdir: Frontend/)
npm run dev                            # Vite dev server
npm run build                          # production build (runs type-check + vite build)
npm run type-check                     # vue-tsc --build (TypeScript only)
npm run lint                           # oxlint + eslint (sequential)
npm run format                         # prettier
```

There is no test runner in this repo.

## Architecture gotchas

### Model configs live in the database, not code
`ChatApp/providers/models.py` has a fallback `supported_models` dict, but `init_models()` in the ChatApp lifespan overwrites it from the `model_configs` SQLite table. Editing the Python file alone won't change available models — use the admin API (`PUT /api/admin/models/{key}`) or modify the DB directly.

### Default sandbox image is custom
Chat endpoint hardcodes `image="python3.12-workspace"` (a custom image from the README), NOT the SandBox default `python:3.12-slim`. Build this image before using code execution:
```bash
docker build -t python3.12-workspace .
```

### Docker socket required
SandBox uses `docker.from_env()`. In production Docker deployments, mount `/var/run/docker.sock`. The `killpython.sh` script cleans up orphaned containers.

### Streaming-only chat
Only `POST /api/sessions/{id}/chat/stream` (SSE) is implemented. The non-stream `POST /api/sessions/{id}/chat` returns 404 "Endpoint not open".

### Required env vars (crash on missing)
`JWT_SECRET_KEY` and `ADMIN_API_KEY` raise `RuntimeError` on startup if not set. Others (`DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, `TAVILY_API_KEY`) default to `""`.

### BigModel provider is unused
`ChatApp/providers/bigmodel.py` implements `LLMProvider` but is not in the `PROVIDER_MAP` in `ChatApp/routers/chat.py`. Only `deepseek` and `openrouter` are wired.

### Database
SQLite at `chat.db` via `aiosqlite`. No migration framework — schema is idempotent `CREATE TABLE IF NOT EXISTS`. `chat.db` is gitignored.

### Playwright
Global browser instance managed in `ChatApp/tools/web_search.py` (lazy-loaded, cleaned up on shutdown). Base Docker image already includes Playwright + Chromium.

## Key files

| File | Purpose |
|------|---------|
| `run.py` | Entrypoint — launches both services |
| `ChatApp/main.py` | ChatApp FastAPI app + lifespan |
| `ChatApp/routers/chat.py` | Core streaming chat logic + tool orchestration |
| `ChatApp/routers/admin.py` | Admin API (model configs, users, token usage) |
| `ChatApp/providers/model_manager.py` | DB-backed model config cache |
| `ChatApp/providers/deepseek.py` | DeepSeek API provider |
| `ChatApp/providers/openrouter.py` | OpenRouter API provider |
| `ChatApp/tools/registry.py` | Tool registration via `@llm_tool` decorator |
| `ChatApp/tools/sandbox.py` | HTTP client to SandBox service |
| `SandBox/main.py` | SandBox FastAPI app |
| `SandBox/container_manager.py` | Docker container lifecycle + cleanup |
| `Frontend/` | Vue 3 frontend (separate npm project) |
