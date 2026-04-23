from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Any, Optional
import httpx

class LLMProvider(ABC):
    """LLM 服务商抽象接口"""

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