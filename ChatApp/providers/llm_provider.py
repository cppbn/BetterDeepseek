from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Any, Optional
import httpx

class LLMProvider(ABC):
    """LLM 服务商抽象接口"""

    @staticmethod
    def build_image_content(mime_type: str, base64_data: str) -> dict[str, Any]:
        """构建 provider-agnostic 内部 image 内容格式。"""
        return {"type": "image", "mime_type": mime_type, "data": base64_data}

    @staticmethod
    def build_audio_content(mime_type: str, base64_data: str) -> dict[str, Any]:
        """构建 provider-agnostic 内部 audio 内容格式。"""
        return {"type": "audio", "mime_type": mime_type, "data": base64_data}

    @staticmethod
    def _convert_content_to_openai(content):
        """将 provider-agnostic 内容转换为 OpenAI 格式。

        供 DeepSeek / OpenRouter 等 OpenAI 兼容 provider 调用。
        """
        if not isinstance(content, list):
            return content
        result = []
        for item in content:
            if not isinstance(item, dict):
                result.append(item)
                continue
            t = item.get("type")
            if t == "text":
                result.append(item)
            elif t == "image":
                mime = item.get("mime_type", "image/png")
                data = item.get("data", "")
                result.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}})
            elif t == "audio":
                mime = item.get("mime_type", "audio/wav")
                data = item.get("data", "")
                fmt = mime.split("/")[-1]
                fmt_map = {"mpeg": "mp3", "mp4": "m4a"}
                fmt = fmt_map.get(fmt, fmt)
                result.append({"type": "input_audio", "input_audio": {"data": data, "format": fmt}})
            else:
                result.append(item)
        return result

    @abstractmethod
    def get_api_url(self) -> str:
        """返回 API 端点 URL"""
        pass

    @abstractmethod
    def get_headers(self) -> Dict[str, str]:
        """返回请求头（含认证）"""
        pass

    @abstractmethod
    def build_payload(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        stream: bool = True,
        thinking: Optional[bool] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """构造请求体"""
        pass

    @abstractmethod
    async def parse_stream(
        self,
        response: httpx.Response,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        解析流式响应，yield 统一格式的事件。
        注意：这是一个异步生成器方法，调用时需使用 `async for`。
        """
        yield {}# 抽象生成器至少需要一个 yield 占位（或使用 `pass` 配合 `@abstractmethod`）
        # 实际实现时应根据具体平台处理

    @abstractmethod
    def convert_messages_to_provider_format(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """将内部统一消息格式转换为该平台要求的格式"""
        pass