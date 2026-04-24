from ChatApp.providers.llm_provider import LLMProvider
from typing import Dict, Any
import httpx
import json
class DeepSeekProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.base_url = base_url

    def get_api_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def build_payload(self, model, messages, tools=None, stream=True, thinking=True, **kwargs):
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if thinking:
            payload["extra_body"] = {"thinking": {"type": "enabled"}}
        return payload

    async def parse_stream(self, response: httpx.Response):
        tool_calls_map: Dict[int, Dict[str, Any]] = {}  # key: index
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:].strip()
            if data_str == "[DONE]":
                # 流结束，发出完整工具调用
                if tool_calls_map:
                    complete_tool_calls = [
                        tool_calls_map[i] for i in sorted(tool_calls_map.keys())
                    ]
                    yield {"type": "tool_calls_complete", "data": complete_tool_calls}
                yield {"type": "done"}
                break

            try:
                data = json.loads(data_str)
                delta = data["choices"][0].get("delta", {})
                # finish_reason = data["choices"][0].get("finish_reason")

                # 处理内容与推理
                if delta.get("content"):
                    yield {"type": "content", "data": delta["content"]}
                if delta.get("reasoning_content"):
                    yield {"type": "reasoning", "data": delta["reasoning_content"]}

                # 处理工具调用增量
                if delta.get("tool_calls"):
                    for tc_delta in delta["tool_calls"]:
                        idx = tc_delta["index"]
                        if idx not in tool_calls_map:
                            tool_calls_map[idx] = {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            }
                        cur = tool_calls_map[idx]
                        if "id" in tc_delta:
                            cur["id"] = tc_delta["id"]
                        if tc_delta.get("function"):
                            if "name" in tc_delta["function"]:
                                cur["function"]["name"] += tc_delta["function"]["name"]
                            if "arguments" in tc_delta["function"]:
                                cur["function"]["arguments"] += tc_delta["function"]["arguments"]
                    # 发出增量事件（可选，用于前端实时展示）
                    yield {"type": "tool_calls_delta", "data": delta["tool_calls"]}

            except json.JSONDecodeError:
                continue

    def convert_messages_to_provider_format(self, messages):
        # DeepSeek 直接支持我们的内部格式，无需转换
        return messages