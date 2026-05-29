import httpx
import json
import logging
from typing import Dict, Any, AsyncGenerator

logger = logging.getLogger(__name__)


class NewApiProvider:
    def __init__(self, api_key: str, base_url: str = "http://localhost:3050/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def get_api_url(self) -> str:
        return f"{self.base_url}/chat/completions"

    @property
    def models_url(self) -> str:
        return f"{self.base_url}/models"

    def get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def build_payload(
        self,
        model: str,
        messages: list,
        tools: list | None = None,
        stream: bool = True,
        thinking: bool = True,
        **kwargs,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if thinking:
            payload["reasoning"] = {"enabled": True}
        return payload

    def build_image_content(self, mime_type: str, base64_data: str) -> dict:
        return {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}}

    def build_audio_content(self, mime_type: str, base64_data: str) -> dict:
        fmt = mime_type.split("/")[-1]
        fmt_map = {"mpeg": "mp3", "mp4": "m4a"}
        fmt = fmt_map.get(fmt, fmt)
        return {"type": "input_audio", "input_audio": {"data": base64_data, "format": fmt}}

    def convert_messages_to_provider_format(self, messages: list) -> list:
        return messages

    async def parse_stream(self, response: httpx.Response) -> AsyncGenerator[Dict[str, Any], None]:
        tool_calls_map: Dict[int, Dict[str, Any]] = {}
        usage = None
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:].strip()
            if data_str == "[DONE]":
                if usage:
                    yield {"type": "usage", "data": usage}
                if tool_calls_map:
                    complete_tool_calls = [
                        tool_calls_map[i] for i in sorted(tool_calls_map.keys())
                    ]
                    yield {"type": "tool_calls_complete", "data": complete_tool_calls}
                yield {"type": "done"}
                break

            try:
                data = json.loads(data_str)

                if "usage" in data and data["usage"]:
                    usage = data["usage"]

                choices = data.get("choices")
                if not choices:
                    continue
                delta = choices[0].get("delta", {})

                if delta.get("content"):
                    yield {"type": "content", "data": delta["content"]}
                if delta.get("reasoning_content"):
                    yield {"type": "reasoning", "data": delta["reasoning_content"]}

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
                        if "id" in tc_delta and tc_delta["id"]:
                            cur["id"] = tc_delta["id"]
                        if tc_delta.get("function"):
                            if "name" in tc_delta["function"] and tc_delta["function"]["name"]:
                                cur["function"]["name"] += tc_delta["function"]["name"]
                            if "arguments" in tc_delta["function"] and tc_delta["function"]["arguments"]:
                                cur["function"]["arguments"] += tc_delta["function"]["arguments"]

            except (json.JSONDecodeError, KeyError, IndexError):
                continue
