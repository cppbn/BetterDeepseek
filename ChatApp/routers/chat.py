from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, Response
import aiosqlite
import httpx
import json
import logging
import aiofiles
from typing import Dict, Any, Optional

from ChatApp.pydantic_models import ChatRequest, MessageResponse
from ChatApp.database import (
    get_db, session_belongs_to_user, get_messages_db, save_message_db,
    get_message_attachments_db, save_file, update_session_title_db,
    get_session_title_db, save_token_usage_db, build_llm_messages
)
from ChatApp.dependencies import get_current_user
import ChatApp.config as config
from ChatApp.tools.registry import global_tools_registry, global_tools_for_llm, get_tool_definition
from ChatApp.tools.sandbox import check_availability, run_sandbox, is_running, download_file_with_meta, upload_file_to_sandbox
from ChatApp.routers.sessions import running_sandboxes, aiolock

from ChatApp.providers.models import supported_models

from ChatApp.providers.deepseek import DeepSeekProvider
from ChatApp.providers.openrouter import OpenRouterProvider
from ChatApp.providers.model_manager import get_title_model

PROVIDER_MAP = {
    "deepseek": lambda: DeepSeekProvider(api_key=config.DEEPSEEK_API_KEY),
    "openrouter": lambda: OpenRouterProvider(api_key=config.OPENROUTER_API_KEY)
}

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions/{session_id}/chat", tags=["chat"])


TITLE_MAX_LENGTH = 40

async def generate_session_title(session_id: str, user_msg: str, assistant_reply: str) -> str | None:
    """生成会话标题并保存到数据库，返回标题文本或 None"""
    try:
        provider = DeepSeekProvider(api_key=config.DEEPSEEK_API_KEY)
        title_model = await get_title_model()
        prompt = (
            f"Generate a concise title (6 words or fewer) for this conversation. "
            f"Reply with only the title, no quotes, no punctuation.\n\n"
            f"User: {user_msg[:500]}\nAssistant: {assistant_reply[:500]}"
        )
        payload = provider.build_payload(
            model=title_model,
            messages=provider.convert_messages_to_provider_format([
                {"role": "user", "content": prompt}
            ]),
            stream=False,
            thinking=False,
        )
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(provider.get_api_url(), headers=provider.get_headers(), json=payload)
            if resp.status_code == 200:
                data = resp.json()
                title = data["choices"][0]["message"]["content"].strip()[:TITLE_MAX_LENGTH]
                title = title.strip('"\'').strip()
                if title:
                    async with aiosqlite.connect(config.DATABASE_URL) as db:
                        await update_session_title_db(db, session_id, title)
                    logger.info(f"Session {session_id} auto-titled: {title}")
                    return title
            else:
                logger.warning(f"Title generation failed: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Title generation error for session {session_id}: {e}")
    return None


@router.post("/stream")
async def chat_stream(
    session_id: str,
    request: ChatRequest,
    fastapi_request: Request, 
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    """流式聊天端点"""
    if not await session_belongs_to_user(db, session_id, current_user["id"]):
        raise HTTPException(status_code=404, detail="Session not exists or Unauthenticated")

    model_info = supported_models.get(request.model or "default") or supported_models["default"]
    llm_provider = PROVIDER_MAP[model_info["provider"]]()

    # 获取历史消息，重建完整多轮上下文（含 reasoning、tool_calls、tool_result）
    history = await get_messages_db(db, session_id, current_user["id"])
    messages_for_llm: list[dict[str, Any]] = build_llm_messages(history)
    
    # 配置 LLM
    enable_search = request.enable_search
    enable_code_exec = request.enable_code_exec

    logger.info(f"Chat stream started for session {session_id}, model={model_info["model"]}, enable_search={enable_search}, enable_code_exec={enable_code_exec}")

    if not await check_availability():
        logger.warning("Sandbox Unavailable")
        enable_code_exec = False

    # 准备工具
    tools_registry: Dict[str, Any] = {}
    tools_for_llm = []
    sandbox_id: Optional[str] = None

    if enable_code_exec:
        sandbox_id = running_sandboxes.get(session_id)
        if not sandbox_id or not await is_running(sandbox_id):
            try:
                sandbox_id = await run_sandbox(image="python3.12-workspace" ,mem_limit="640m")
                logger.info(f"Started new sandbox {sandbox_id} for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to start sandbox: {e}")
                enable_code_exec = False
                sandbox_id = None
            else:
                async with aiolock:
                    running_sandboxes[session_id] = sandbox_id

    if enable_code_exec and sandbox_id:
        tools_registry["exec_shell"] = global_tools_registry["exec_shell"]
        tools_for_llm.append(global_tools_for_llm["exec_shell"])
        tools_registry["exec_python"] = global_tools_registry["exec_python"]
        tools_for_llm.append(global_tools_for_llm["exec_python"])
        tools_registry["describe_image"] = global_tools_registry["describe_image"]
        tools_for_llm.append(global_tools_for_llm["describe_image"])
        tools_registry["describe_audio"] = global_tools_registry["describe_audio"]
        tools_for_llm.append(global_tools_for_llm["describe_audio"])
        tools_for_llm.append(
            get_tool_definition(
                name="export_file",
                description="export file from sandbox and display it to user",
                parameters=[{"name": "path", "description": "the file path"}]
            )
        )
    if enable_search:
        tools_registry["web_search"] = global_tools_registry["web_search"]
        tools_for_llm.append(global_tools_for_llm["web_search"])
        tools_registry["fetch_url"] = global_tools_registry["fetch_url"]
        tools_for_llm.append(global_tools_for_llm["fetch_url"])

    # 系统提示词
    if enable_code_exec:
        llm_system_message = config.SYSTEM_PROMPT_WITH_CODE_EXEC
    else:
        llm_system_message = config.SYSTEM_PROMPT_DEFAULT
    messages_for_llm.insert(0, {"role": "system", "content": llm_system_message})

    last_msg_idx = history[-1].idx if history else -1
    next_seq = history[-1].seq + 1 if history else 0

    # 处理附件
    uploaded_attachments = await get_message_attachments_db(db, session_id, None)
    final_message = request.message
    valid_attachments = []
    if request.attachments_file_id and uploaded_attachments:
        # 分能不能使用sandbox处理。不能则将文本附加到用户消息；能则将文件名附加到用户消息，文件上传到sandbox
        for att in uploaded_attachments:
            if att["id"] in request.attachments_file_id:
                if enable_code_exec and sandbox_id:
                    async with aiofiles.open(att["file_path"], mode='rb') as f:
                        if await upload_file_to_sandbox(sandbox_id, f"/workspace/{att["original_filename"]}", await f.read()):
                            final_message += f"\n[{att['original_filename']}]"
                        else:
                            logger.warning(f"Failed to upload to sandbox: {att["file_path"]}")
                else:
                    if att["mime_type"].startswith("text"):
                        async with aiofiles.open(att["file_path"], encoding="utf-8") as f:
                            text_content = await f.read(100000)
                            final_message += f"\n[{att['original_filename']}]\n{text_content}"
                            if len(text_content) >= 100000:
                                final_message += "\n[file truncated at 100KB]"
                valid_attachments.append(att)

    message_id = await save_message_db(db, session_id, next_seq, last_msg_idx + 1, "user", "message", final_message)
    next_seq += 1
    last_msg_idx += 1

    for att in valid_attachments:
        await db.execute("UPDATE files SET message_id = ? WHERE id = ?", (message_id, att["id"]))
    await db.commit()

    messages_for_llm.append({"role": "user", "content": final_message})

    async def event_generator():
        nonlocal next_seq
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0}
        while True:
            if await fastapi_request.is_disconnected():
                logger.info(f"Client disconnected for session {session_id}")
                return

            reasoning_content = ""
            content = ""

            headers = llm_provider.get_headers()

            payload = llm_provider.build_payload(
                model=model_info["model"],
                messages=llm_provider.convert_messages_to_provider_format(messages_for_llm),
                tools=tools_for_llm,
                thinking=model_info["thinking"],
            )

            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=180.0)) as client:
                async with client.stream("POST", llm_provider.get_api_url(), headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"LLM API error {response.status_code}: {error_text}")
                        yield "data: " + json.dumps({"error": f"LLM error {response.status_code}: {error_text}"}) + "\n\n"
                        return
                    current_tool_calls = []
                    async for event in llm_provider.parse_stream(response):
                        if await fastapi_request.is_disconnected():
                            logger.info(f"Client disconnected for session {session_id}")
                            return
                        if event["type"] == "done":
                            break
                        elif event["type"] == "content":
                            content += event["data"]
                            yield f"data: {json.dumps({'type': 'content', 'content': event['data']})}\n\n"
                        elif event["type"] == "reasoning":
                            reasoning_content += event["data"]
                            yield f"data: {json.dumps({'type': 'reasoning_content', 'content': event['data']})}\n\n"
                        elif event["type"] == "tool_calls_complete":
                            current_tool_calls: list = event["data"]
                        elif event["type"] == "usage":
                            usage_data = event["data"]
                            total_usage["prompt_tokens"] += usage_data.get("prompt_tokens", 0)
                            total_usage["completion_tokens"] += usage_data.get("completion_tokens", 0)

            # 处理工具调用
            if current_tool_calls:
                
                assistant_msg = {
                    "role": "assistant",
                    "reasoning_content": reasoning_content if reasoning_content else None,
                    "content": content if content else None,
                    "tool_calls": current_tool_calls,
                }
                messages_for_llm.append(assistant_msg)
                if reasoning_content:
                    await save_message_db(db, session_id, next_seq, last_msg_idx + 1, "assistant", "reasoning", reasoning_content)
                    next_seq += 1
                if content:
                    await save_message_db(db, session_id, next_seq, last_msg_idx + 1, "assistant", "message", content)
                    next_seq += 1

                for tc in current_tool_calls:
                    func_name = tc["function"]["name"]
                    func_args_str = tc["function"]["arguments"]
                    tool_call_id = tc["id"]

                    try:
                        func_args = json.loads(func_args_str)
                        yield f"data: {json.dumps({'type': 'tool_call', 'content': {'name': func_name, 'args': func_args}})}\n\n"
                        tc_msg_id = await save_message_db(db, session_id, next_seq, last_msg_idx + 1, "assistant", "tool_call", json.dumps({'name': func_name, 'args': func_args, 'id': tool_call_id}))
                        next_seq += 1
                        logger.info(f"Tool call: {func_name} with args {func_args}")

                        # 注入 sandbox 参数
                        if func_name in ["exec_shell", "exec_python", "describe_image", "describe_audio"]:
                            func_args["container_id"] = sandbox_id

                        # 特殊工具 export_file
                        if func_name == "export_file":
                            if sandbox_id:
                                file_bytes, filename, mime_type = await download_file_with_meta(sandbox_id, func_args["path"])
                                saved_file_info = await save_file(session_id, tc_msg_id, file_bytes, filename, mime_type, db)
                                yield f"data: {json.dumps({'type': 'file', 'content': {'file_id': saved_file_info['file_id']}})}\n\n"
                                result = f"{filename} exported"
                                logger.info(f"File exported: {filename}")
                            else:
                                result = "Error: sandbox not available for export_file"
                        elif func_name in tools_registry:
                            result = await tools_registry[func_name](**func_args)
                        else:
                            result = f"Error: Unknown tool {func_name}"

                    except json.JSONDecodeError:
                        result = f"Error: Invalid arguments JSON: {func_args_str}"
                    except Exception as e:
                        logger.error(f"Tool execution failed: {func_name}, error: {str(e)}")
                        result = f"Error: Tool execution failed - {str(e)}"

                    yield f"data: {json.dumps({'type': 'tool_result', 'content': str(result)})}\n\n"
                    await save_message_db(db, session_id, next_seq, last_msg_idx + 1, "tool", "tool_result", json.dumps({'tool_call_id': tool_call_id, 'content': str(result)}))
                    next_seq += 1

                    messages_for_llm.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": func_name,
                        "content": str(result)
                    })

                continue  # 继续下一轮 LLM 调用

            else:
                # 无工具调用，结束
                if reasoning_content:
                    await save_message_db(db, session_id, next_seq, last_msg_idx + 1, "assistant", "reasoning", reasoning_content)
                    next_seq += 1
                if content:
                    await save_message_db(db, session_id, next_seq, last_msg_idx + 1, "assistant", "message", content)
                    next_seq += 1
                logger.info(f"Chat stream finished for session {session_id}")

                if total_usage.get("prompt_tokens") or total_usage.get("completion_tokens"):
                    try:
                        await save_token_usage_db(
                            db, session_id, current_user["id"], model_info["model"],
                            total_usage["prompt_tokens"], total_usage["completion_tokens"]
                        )
                    except Exception:
                        pass

                # 标题自动生成（仅首次对话且无标题时）
                if not await get_session_title_db(db, session_id):
                    first_user_msg = next((m["content"] for m in messages_for_llm if m["role"] == "user"), None)
                    if first_user_msg and content:
                        try:
                            title = await generate_session_title(session_id, first_user_msg, content)
                            if title:
                                yield f"data: {json.dumps({'type': 'title', 'content': title})}\n\n"
                        except Exception:
                            pass
                return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("")
async def chat(
    session_id: str,
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db)
):
    # TODO 普通聊天端点
    return Response("Endpoint not open", 404)