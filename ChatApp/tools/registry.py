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
    name="tavily_search",
    description="Search the web for real-time information using Tavily API. Returns titles, URLs, snippets, and optionally an AI-generated answer and full page content.",
    parameters=[
        {"name": "query", "description": "Search query string"},
        {"name": "max_results", "description": "Maximum number of results (1-20, default 7)", "type": "integer", "required": False},
        {"name": "search_depth", "description": "Depth of search: 'basic', 'advanced', 'fast', or 'ultra-fast'. 'advanced' is most thorough but costs 2 API credits. 'fast' and 'ultra-fast' prioritize speed. (default 'basic')", "required": False},
        {"name": "topic", "description": "Topic: 'general', 'news', or 'finance' (default 'general')", "type": "string", "required": False},
        {"name": "days", "description": "Days back for news search (only if topic='news', default 3)", "type": "integer", "required": False},
        {"name": "time_range", "description": "Time range filter: 'day', 'week', 'month', or 'year'", "required": False},
        {"name": "start_date", "description": "Start date filter in YYYY-MM-DD format", "required": False},
        {"name": "end_date", "description": "End date filter in YYYY-MM-DD format", "required": False},
        {"name": "include_answer", "description": "Include an AI-generated answer summary of the search results", "type": "boolean", "required": False},
        {"name": "include_raw_content", "description": "Include the full cleaned content of each result page in markdown format", "type": "boolean", "required": False},
        {"name": "chunks_per_source", "description": "Number of content chunks per source when search_depth is 'advanced' (1-3, default 3)", "type": "integer", "required": False},
        {"name": "include_domains", "description": "Comma-separated list of domains to include (e.g. 'wikipedia.org,github.com')", "required": False},
        {"name": "exclude_domains", "description": "Comma-separated list of domains to exclude (e.g. 'pinterest.com,quora.com')", "required": False},
    ]
)
async def _tavily_search_tool(query: str, max_results: int = 7, search_depth: str = "basic",
                           topic: str = "general", days: int = 3, time_range: str = "",
                           start_date: str = "", end_date: str = "",
                           include_answer: bool = False, include_raw_content: bool = False,
                           chunks_per_source: int = 3,
                           include_domains: str = "", exclude_domains: str = "") -> str:
    from ChatApp.config import TAVILY_API_KEY
    if not TAVILY_API_KEY:
        return "Error: Tavily API key not configured."

    inc_domains = [d.strip() for d in include_domains.split(",") if d.strip()] if include_domains else None
    exc_domains = [d.strip() for d in exclude_domains.split(",") if d.strip()] if exclude_domains else None

    try:
        return await web_search.search_tavily(
            query=query,
            api_key=TAVILY_API_KEY,
            max_results=max_results,
            search_depth=search_depth,
            topic=topic,
            days=days,
            time_range=time_range,
            start_date=start_date,
            end_date=end_date,
            include_answer=include_answer,
            include_raw_content=include_raw_content,
            chunks_per_source=chunks_per_source,
            include_domains=inc_domains,
            exclude_domains=exc_domains,
        )
    except Exception as e:
        logger.error(f"Web search failed: {str(e)}")
        return f"Error performing web search: {str(e)}"


@llm_tool(
    name="tavily_extract",
    description="Extract and read the full content from one or more web pages using Tavily Extract. Use this to retrieve the complete text of specific URLs in markdown or plain text format. Supports extracting multiple URLs at once.",
    parameters=[
        {"name": "urls", "description": "Comma-separated list of URLs to extract content from (e.g. 'https://example.com,https://example2.com')"},
        {"name": "extract_depth", "description": "Extraction depth: 'basic' or 'advanced'. Advanced retrieves tables and embedded content but costs 2 credits per 5 URLs. (default 'basic')", "required": False},
        {"name": "format", "description": "Content format: 'markdown' or 'text' (default 'markdown')", "required": False},
        {"name": "query", "description": "Optional user intent to rerank extracted content chunks for relevance", "required": False},
        {"name": "chunks_per_source", "description": "Max content chunks per URL when query is provided (1-5, default 3)", "type": "integer", "required": False},
    ]
)
async def _tavily_extract_tool(urls: str, extract_depth: str = "basic",
                                format: str = "markdown", query: str = "",
                                chunks_per_source: int = 3) -> str:
    from ChatApp.config import TAVILY_API_KEY
    if not TAVILY_API_KEY:
        return "Error: Tavily API key not configured."
    url_list = [u.strip() for u in urls.split(",") if u.strip()]
    if not url_list:
        return "Error: No valid URLs provided."
    try:
        return await web_search.tavily_extract(
            urls=url_list,
            api_key=TAVILY_API_KEY,
            extract_depth=extract_depth,
            format=format,
            query=query,
            chunks_per_source=chunks_per_source,
        )
    except Exception as e:
        logger.error(f"Tavily Extract failed: {str(e)}")
        return f"Error performing Tavily Extract: {str(e)}"


@llm_tool(
    name="tavily_crawl",
    description="Crawl a website starting from a base URL, following links to explore and extract content from multiple pages. Returns the full content of each crawled page. Useful for comprehensive research across a site.",
    parameters=[
        {"name": "url", "description": "The root URL to begin crawling"},
        {"name": "instructions", "description": "Natural language instructions for the crawler (e.g. 'Find all pages about pricing'). Costs 2 credits per 10 pages when specified.", "required": False},
        {"name": "max_depth", "description": "Max depth of crawl from the base URL (1-5, default 1)", "type": "integer", "required": False},
        {"name": "max_breadth", "description": "Max links to follow per page (1-500, default 20)", "type": "integer", "required": False},
        {"name": "limit", "description": "Total number of links to process before stopping (default 50)", "type": "integer", "required": False},
        {"name": "extract_depth", "description": "Extraction depth: 'basic' or 'advanced' (default 'basic')", "required": False},
        {"name": "format", "description": "Content format: 'markdown' or 'text' (default 'markdown')", "required": False},
    ]
)
async def _tavily_crawl_tool(url: str, instructions: str = "", max_depth: int = 1,
                              max_breadth: int = 20, limit: int = 50,
                              extract_depth: str = "basic", format: str = "markdown") -> str:
    from ChatApp.config import TAVILY_API_KEY
    if not TAVILY_API_KEY:
        return "Error: Tavily API key not configured."
    try:
        return await web_search.tavily_crawl(
            url=url,
            api_key=TAVILY_API_KEY,
            instructions=instructions,
            max_depth=max_depth,
            max_breadth=max_breadth,
            limit=limit,
            extract_depth=extract_depth,
            format=format,
        )
    except Exception as e:
        logger.error(f"Tavily Crawl failed: {str(e)}")
        return f"Error performing Tavily Crawl: {str(e)}"


@llm_tool(
    name="tavily_map",
    description="Map a website's structure starting from a base URL. Discovers and lists all URLs across the site without extracting full page content. Use this to understand a site's structure before deciding which pages to extract or crawl.",
    parameters=[
        {"name": "url", "description": "The root URL to begin mapping"},
        {"name": "instructions", "description": "Natural language instructions to filter which pages to discover (e.g. 'Find all documentation pages'). Costs 2 credits per 10 pages when specified.", "required": False},
        {"name": "max_depth", "description": "Max depth of mapping from the base URL (1-5, default 1)", "type": "integer", "required": False},
        {"name": "max_breadth", "description": "Max links to follow per page (1-500, default 20)", "type": "integer", "required": False},
        {"name": "limit", "description": "Total number of links to process before stopping (default 50)", "type": "integer", "required": False},
    ]
)
async def _tavily_map_tool(url: str, instructions: str = "", max_depth: int = 1,
                            max_breadth: int = 20, limit: int = 50) -> str:
    from ChatApp.config import TAVILY_API_KEY
    if not TAVILY_API_KEY:
        return "Error: Tavily API key not configured."
    try:
        return await web_search.tavily_map(
            url=url,
            api_key=TAVILY_API_KEY,
            instructions=instructions,
            max_depth=max_depth,
            max_breadth=max_breadth,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Tavily Map failed: {str(e)}")
        return f"Error performing Tavily Map: {str(e)}"

import base64
import mimetypes
from ChatApp.tools.utils import _compress_image_if_needed

@llm_tool(
    name="read_image",
    description="Read and view an image file from the sandbox. Use this to visually inspect images, charts, plots, screenshots, and photos.",
    parameters=[
        {"name": "file_path", "description": "Path to the image file in the sandbox, e.g. /workspace/plot.png"}
    ]
)
async def _read_image_tool(file_path: str, container_id: str):
    file_path = sandbox.normalize_path(file_path)
    image_bytes = await sandbox.download_file_from_sandbox(container_id, file_path)

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type.startswith("image/"):
        original_format = mime_type.split("/")[-1]
    else:
        if image_bytes.startswith(b'\x89PNG'):
            original_format = "png"
        elif image_bytes.startswith(b'\xff\xd8\xff'):
            original_format = "jpeg"
        elif image_bytes.startswith(b'GIF'):
            original_format = "gif"
        elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[8:12]:
            original_format = "webp"
        else:
            return {"type": "error", "content": f"Could not determine image format for {file_path}"}
        mime_type = f"image/{original_format}"

    compressed_bytes, final_format = await _compress_image_if_needed(image_bytes, original_format)
    b64 = base64.b64encode(compressed_bytes).decode("utf-8")
    final_mime = f"image/{final_format}"

    logger.info(f"read_image: {file_path} ({len(image_bytes)} bytes -> {len(compressed_bytes)} bytes)")
    return {
        "type": "image",
        "data": b64,
        "mime_type": final_mime,
        "file_path": file_path
    }


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

        file_path = sandbox.normalize_path(file_path)
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
    name="get_time",
    description="Get the current date and time. Use this when you need to answer questions about what date or time it is now.",
    parameters=[
        {"name": "timezone", "description": "IANA timezone name (e.g. 'Asia/Shanghai', 'America/New_York', 'UTC'). Default: 'Asia/Shanghai'.", "required": False}
    ]
)
async def _get_time_tool(timezone: str = "Asia/Shanghai") -> str:
    import datetime
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        from backports import zoneinfo as ZoneInfo
    try:
        tz = ZoneInfo(timezone)
        now = datetime.datetime.now(tz)
    except Exception:
        now = datetime.datetime.now(datetime.timezone.utc)
        tz_name = "UTC"
    else:
        tz_name = timezone
    return now.strftime(f"%Y-%m-%d %H:%M:%S %Z ({tz_name})  %A, week %W")

@llm_tool(
    name="read_txt",
    description="Read a text file from the sandbox. Use this to view the contents of .txt, .md, .py, .json, .csv, .log, .yaml, .cfg, .env and other text-based files.",
    parameters=[
        {"name": "file_path", "description": "Path to the text file in the sandbox, e.g. /workspace/output.txt"},
        {"name": "max_chars", "description": "Maximum characters to return (default 5000)", "type": "integer", "required": False}
    ]
)
async def _read_txt_tool(file_path: str, container_id: str, max_chars: int = 5000) -> str:
    file_path = sandbox.normalize_path(file_path)
    content_bytes = await sandbox.download_file_from_sandbox(container_id, file_path)
    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = content_bytes.decode("latin-1")
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[... truncated, {len(text) - max_chars} more characters]"
    return text

@llm_tool(
    name="read_audio",
    description="Read and listen to an audio file from the sandbox. Use this to hear audio recordings, speech, music, or sound effects.",
    parameters=[
        {"name": "file_path", "description": "Path to the audio file in the sandbox, e.g. /workspace/recording.wav"}
    ]
)
async def _read_audio_tool(file_path: str, container_id: str):
    file_path = sandbox.normalize_path(file_path)
    audio_bytes = await sandbox.download_file_from_sandbox(container_id, file_path)

    af_mime, _ = mimetypes.guess_type(file_path)
    if not af_mime or not af_mime.startswith("audio/"):
        ext = file_path.split(".")[-1].lower()
        format_map = {"wav": "wav", "mp3": "mpeg", "m4a": "mp4", "flac": "flac", "ogg": "ogg"}
        audio_format = format_map.get(ext, "wav")
    else:
        audio_format = af_mime.split("/")[-1]

    b64 = base64.b64encode(audio_bytes).decode("utf-8")

    logger.info(f"read_audio: {file_path} ({len(audio_bytes)} bytes)")
    return {
        "type": "audio",
        "data": b64,
        "mime_type": f"audio/{audio_format}",
        "file_path": file_path
    }


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

        file_path = sandbox.normalize_path(file_path)
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