from typing import Dict, List, Any, Callable
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# 全局注册表
global_tools_registry: Dict[str, Callable] = {}
global_tools_for_llm: Dict[str, Dict[str, Any]] = {}


def get_tool_definition(name: str, description: str, parameters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """生成符合 OpenAI function calling 格式的工具定义"""
    properties = {}
    required = []
    for param in parameters:
        prop = {
            "type": param.get("type", "string"),
            "description": param["description"]
        }
        properties[param["name"]] = prop
        if param.get("required", True):
            required.append(param["name"])
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }


def llm_tool(name: str, description: str, parameters: List[Dict[str, Any]]) -> Callable:
    """装饰器：将函数注册为 LLM 可调用的工具"""
    def decorator(func: Callable) -> Callable:
        global_tools_registry[name] = func
        tool_def = get_tool_definition(name, description, parameters)
        global_tools_for_llm[name] = tool_def

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper
    return decorator


# 导入并注册内置工具
from ChatApp.tools import sandbox, web_search, omni

@llm_tool(
    name="exec_python",
    description="execute python code in sandbox",
    parameters=[
        {"name": "code", "description": "code to execute"},
        {"name": "timeout", "type": "integer", "description": "maximum execution time in seconds;30 by default", "required": False}
    ]
)
async def _exec_python_tool(container_id: str, code: str, timeout: int = 30) -> str:
    logger.info(f"Executing Python code in sandbox {container_id}, timeout={timeout}")
    return await sandbox.exec_python(container_id, code, timeout)


@llm_tool(
    name="exec_shell",
    description="execute shell command in sandbox",
    parameters=[
        {"name": "cmd", "description": "command to execute"},
        {"name": "timeout", "type": "integer", "description": "maximum execution time in seconds;30 by default", "required": False}
    ]
)
async def _exec_shell_tool(container_id: str, cmd: str, timeout: int = 30) -> str:
    logger.info(f"Executing shell command in sandbox {container_id}: {cmd}, timeout={timeout}")
    return await sandbox.exec_shell(container_id, cmd, timeout)


@llm_tool(
    name="web_search",
    description="Search the web for real-time information using Tavily API.",
    parameters=[
        {"name": "query", "description": "Search query string"},
        {"name": "max_results", "description": "Maximum number of results (1-20, default 7)", "type": "integer", "required": False},
        {"name": "search_depth", "description": "Depth of search: 'basic' or 'advanced' (default 'basic')", "required": False},
        {"name": "topic", "description": "Topic: 'general' or 'news' (default 'general')", "type": "string", "required": False},
        {"name": "days", "description": "Days back for news search (only if topic='news', default 3)", "type": "integer", "required": False},
    ]
)
async def _web_search_tool(query: str, max_results: int = 7, search_depth: str = "basic",
                           topic: str = "general", days: int = 3) -> str:
    from ChatApp.config import TAVILY_API_KEY
    if not TAVILY_API_KEY:
        return "Error: Tavily API key not configured."
    try:
        return await web_search.search_tavily(
            query=query,
            api_key=TAVILY_API_KEY,
            max_results=max_results,
            search_depth=search_depth,
            topic=topic,
            days=days
        )
    except Exception as e:
        logger.error(f"Web search failed: {str(e)}")
        return f"Error performing web search: {str(e)}"


@llm_tool(
    name="fetch_url",
    description="Fetch and extract main text content from a given URL.",
    parameters=[
        {"name": "url", "description": "The URL to fetch", "type": "string"},
        {"name": "max_length", "description": "Maximum characters to return (default 2000)", "type": "integer", "required": False}
    ]
)
async def _fetch_url_tool(url: str, max_length: int = 2000) -> str:
    try:
        return await web_search.fetch_url(url, max_length)
    except Exception as e:
        logger.error(f"URL fetch failed: {str(e)}")
        return f"Error fetching URL: {str(e)}"

from ChatApp.tools.utils import _compress_image_if_needed

@llm_tool(
    name="describe_image",
    description="Describe the content of an image file located inside the sandbox. Provide a question about the image (e.g., 'What is in this image?').",
    parameters=[
        {"name": "file_path", "description": "Absolute path to the image file inside the sandbox container."},
        {"name": "question", "description": "The question to ask about the image (e.g., 'What is depicted in this image?').", "required": False},
    ]
)
async def _describe_image_tool(container_id: str, file_path: str, question: str = "Describe this image in detail.") -> str:
    """
    从沙箱下载图片文件，必要时压缩，调用多模态模型进行描述。
    """
    try:
        from ChatApp.tools.sandbox import download_file_from_sandbox
        import mimetypes

        image_bytes = await download_file_from_sandbox(container_id, file_path)

        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and mime_type.startswith("image/"):
            original_format = mime_type.split('/')[-1]
        else:
            # 简单检测常见头部
            if image_bytes.startswith(b'\x89PNG'):
                original_format = "png"
            elif image_bytes.startswith(b'\xff\xd8\xff'):
                original_format = "jpeg"
            elif image_bytes.startswith(b'GIF'):
                original_format = "gif"
            elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[8:12]:
                original_format = "webp"
            else:
                return "Error: Could not determine image format."

        # 自动压缩大图片
        compressed_bytes, final_format = await _compress_image_if_needed(image_bytes, original_format)

        description = await omni.inquire_image(question, compressed_bytes, final_format)
        return description
    except Exception as e:
        logger.error(f"Image description failed: {str(e)}")
        return f"Error describing image: {str(e)}"


@llm_tool(
    name="describe_audio",
    description="Transcribe or describe the content of an audio file located inside the sandbox. Provide a question about the audio (e.g., 'What is being said in this recording?').",
    parameters=[
        {"name": "file_path", "description": "Absolute path to the audio file inside the sandbox container."},
        {"name": "question", "description": "The question to ask about the audio (e.g., 'Transcribe the speech in this audio.').", "required": False},
    ]
)
async def _describe_audio_tool(container_id: str, file_path: str, question: str = "Transcribe this audio and describe any notable sounds.") -> str:
    """
    从沙箱下载音频文件，调用多模态模型进行转录或描述。
    该工具会在运行时由 chat.py 注入 container_id。
    """
    try:
        from ChatApp.tools.sandbox import download_file_from_sandbox
        import mimetypes

        audio_bytes = await download_file_from_sandbox(container_id, file_path)

        # 推断音频格式
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type or not mime_type.startswith("audio/"):
            # 简单后缀映射
            ext = file_path.split('.')[-1].lower()
            format_map = {
                "wav": "wav",
                "mp3": "mp3",
                "m4a": "m4a",
                "flac": "flac",
                "ogg": "ogg",
            }
            audio_format = format_map.get(ext, "wav")  # 默认 wav
        else:
            audio_format = mime_type.split('/')[-1]

        description = await omni.inquire_audio(question, audio_bytes, audio_format)
        return description
    except Exception as e:
        logger.error(f"Audio description failed: {str(e)}")
        return f"Error describing audio: {str(e)}"