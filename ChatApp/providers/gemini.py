from ChatApp.providers.llm_provider import LLMProvider
from typing import AsyncGenerator, Dict, List, Any, Optional
import httpx
import json
import logging

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self._model = ""
        self._thought_signature: Optional[str] = None

    def get_api_url(self) -> str:
        return f"{self.base_url}/models/{self._model}:streamGenerateContent?alt=sse"

    def get_headers(self) -> Dict[str, str]:
        return {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

    def build_payload(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        stream: bool = True,
        thinking: Optional[bool] = None,
        **kwargs
    ) -> Dict[str, Any]:
        self._model = model

        original_messages = kwargs.get("original_messages", [])
        payload: Dict[str, Any] = {"contents": messages}

        system_parts: List[Dict[str, str]] = []
        for msg in original_messages:
            if msg.get("role") == "system":
                text = msg.get("content", "")
                if isinstance(text, str) and text.strip():
                    system_parts.append({"text": text})
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}

        generation_config: Dict[str, Any] = {}

        if thinking:
            if "2.5" in model:
                generation_config["thinkingConfig"] = {"thinkingBudget": -1}
            else:
                generation_config["thinkingConfig"] = {
                    "thinkingLevel": "high",
                    "includeThoughts": True,
                }

        if tools:
            function_declarations: List[Dict[str, Any]] = []
            for tool in tools:
                func = tool.get("function", {})
                if func:
                    declaration = {
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                    }
                    params = func.get("parameters")
                    if params:
                        declaration["parameters"] = _to_gemini_schema(params)
                    function_declarations.append(declaration)
            if function_declarations:
                payload["tools"] = [{"functionDeclarations": function_declarations}]

        if generation_config:
            payload["generationConfig"] = generation_config

        return payload

    async def parse_stream(
        self,
        response: httpx.Response,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        tool_calls_buffer: list = []
        usage = None
        self._thought_signature = None
        end_reason = None

        try:
            async for raw_line in response.aiter_lines():
                if not raw_line.startswith("data: "):
                    continue
                data_str = raw_line[6:].strip()
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if "error" in data:
                    err = data["error"]
                    logger.error(f"Gemini SSE error: {err}")
                    yield {"type": "done"}
                    return

                if "promptFeedback" in data:
                    fb = data["promptFeedback"]
                    if fb.get("blockReason"):
                        logger.warning(f"Gemini prompt blocked: {fb['blockReason']}")
                        yield {"type": "done"}
                        return

                candidates = data.get("candidates", [])
                if not candidates:
                    if "usageMetadata" in data:
                        um = data["usageMetadata"]
                        yield {"type": "usage", "data": {
                            "prompt_tokens": um.get("promptTokenCount", 0),
                            "completion_tokens": um.get("candidatesTokenCount", 0),
                            "total_tokens": um.get("totalTokenCount", 0),
                        }}
                    continue

                candidate = candidates[0]
                finish_reason = candidate.get("finishReason")

                if finish_reason in ("SAFETY", "RECITATION", "BLOCKLIST"):
                    for sr in candidate.get("safetyRatings", []):
                        if sr.get("blocked"):
                            logger.warning(f"Gemini blocked category={sr.get('category')}: {sr}")
                    if finish_reason not in ("STOP", "MAX_TOKENS"):
                        end_reason = finish_reason
                        continue

                content = candidate.get("content") or {}
                parts = content.get("parts", [])

                for part in parts:
                    if not isinstance(part, dict):
                        continue

                    if "thoughtSignature" in part:
                        self._thought_signature = part["thoughtSignature"]

                    is_thought = part.get("thought")
                    if is_thought:
                        if "text" in part and part["text"]:
                            yield {"type": "reasoning", "data": part["text"]}
                    elif "text" in part and part["text"]:
                        yield {"type": "content", "data": part["text"]}

                    if "functionCall" in part:
                        fc = part["functionCall"]
                        args = fc.get("args", {})
                        if not isinstance(args, dict):
                            args = {}
                        tool_calls_buffer.append({
                            "id": f"call_{len(tool_calls_buffer)}_{fc.get('name', '')}",
                            "type": "function",
                            "function": {
                                "name": fc.get("name", ""),
                                "arguments": json.dumps(args, ensure_ascii=False),
                            }
                        })

                if finish_reason and finish_reason not in ("STOP",):
                    logger.debug(f"Gemini finish reason: {finish_reason}")
                    if finish_reason == "MAX_TOKENS":
                        end_reason = finish_reason

                if "usageMetadata" in data:
                    um = data["usageMetadata"]
                    yield {"type": "usage", "data": {
                        "prompt_tokens": um.get("promptTokenCount", 0),
                        "completion_tokens": um.get("candidatesTokenCount", 0),
                        "total_tokens": um.get("totalTokenCount", 0),
                    }}

        except Exception as e:
            logger.error(f"Gemini parse_stream exception: {e}", exc_info=True)

        if self._thought_signature:
            yield {"type": "thought_signature", "data": self._thought_signature}

        if tool_calls_buffer:
            yield {"type": "tool_calls_complete", "data": tool_calls_buffer}

        if end_reason and end_reason != "MAX_TOKENS":
            logger.warning(f"Gemini stream ended with: {end_reason}")

        yield {"type": "done"}

    def convert_messages_to_provider_format(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        contents: List[Dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "")
            if role == "system":
                continue

            gemini_role = _to_gemini_role(role)
            parts = _build_parts(msg, role)

            if parts:
                contents.append({"role": gemini_role, "parts": parts})

        return contents


def _to_gemini_role(openai_role: str) -> str:
    if openai_role == "assistant":
        return "model"
    if openai_role == "tool":
        return "function"
    return "user"


def _build_parts(msg: Dict[str, Any], role: str) -> List[Dict[str, Any]]:
    content = msg.get("content", "")
    parts: List[Dict[str, Any]] = []

    if role == "tool":
        response_name = msg.get("name", "")
        response_content = msg.get("content", "")

        if isinstance(response_content, list):
            text_parts = [
                item["text"] for item in response_content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            response_obj = {"result": " ".join(text_parts) if text_parts else "done"}
        elif isinstance(response_content, str):
            try:
                response_obj = json.loads(response_content)
            except (json.JSONDecodeError, TypeError):
                response_obj = {"result": response_content}
        elif response_content is None:
            response_obj = {"result": "done"}
        else:
            response_obj = response_content

        parts.append({
            "functionResponse": {
                "name": response_name,
                "response": response_obj,
            }
        })
        return parts

    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append({"text": item["text"]})
                elif item.get("type") == "image_url":
                    url = item.get("image_url", {}).get("url", "")
                    mime_type, data = _parse_data_url(url)
                    if mime_type and data:
                        parts.append({
                            "inlineData": {"mimeType": mime_type, "data": data}
                        })
                elif item.get("type") == "input_audio":
                    aud = item.get("input_audio", {})
                    data = aud.get("data", "")
                    mime_type = aud.get("format", "audio/wav")
                    if data:
                        parts.append({
                            "inlineData": {"mimeType": mime_type, "data": data}
                        })
    else:
        if isinstance(content, str) and content.strip():
            parts.append({"text": content})
        elif not isinstance(content, str) and content is not None:
            parts.append({"text": str(content)})

    if role == "assistant":
        tool_calls = msg.get("tool_calls", [])
        for tc in tool_calls:
            func = tc.get("function", {})
            try:
                args = json.loads(func.get("arguments", "{}"))
            except (json.JSONDecodeError, TypeError):
                args = {}
            parts.append({
                "functionCall": {
                    "name": func.get("name", ""),
                    "args": args,
                }
            })

        thought_sig = msg.get("thought_signature")
        if thought_sig:
            parts.append({"thoughtSignature": thought_sig})

    return parts


def _parse_data_url(url: str) -> tuple:
    if not url.startswith("data:"):
        return "", ""
    try:
        header, b64 = url.split(",", 1)
        mime_type = header.split(":")[1].split(";")[0]
        return mime_type, b64
    except (IndexError, ValueError):
        return "", ""


_TYPE_MAP = {
    "object": "OBJECT",
    "string": "STRING",
    "number": "NUMBER",
    "integer": "INTEGER",
    "boolean": "BOOLEAN",
    "array": "ARRAY",
    "null": "NULL",
}


def _to_gemini_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Convert JSON Schema types to Gemini uppercase types."""
    result: Dict[str, Any] = {}
    for key, value in schema.items():
        if key == "type" and isinstance(value, str):
            result[key] = _TYPE_MAP.get(value, value.upper())
        elif key == "properties" and isinstance(value, dict):
            result[key] = {k: _to_gemini_schema(v) for k, v in value.items()}
        elif key == "items" and isinstance(value, dict):
            result[key] = _to_gemini_schema(value)
        elif key == "enum" and isinstance(value, list):
            result[key] = value
        elif isinstance(value, dict):
            result[key] = _to_gemini_schema(value)
        else:
            result[key] = value
    return result
