import httpx
import base64
import json
import logging
import ChatApp.config as config
from ChatApp.providers.model_manager import get_image_model_info, get_audio_model_info

logger = logging.getLogger(__name__)

AUDIO_MIME_MAP = {
    "wav": "audio/wav", "mp3": "audio/mp3", "mpeg": "audio/mpeg",
    "mp4": "audio/mp4", "m4a": "audio/mp4", "ogg": "audio/ogg",
    "flac": "audio/flac", "aac": "audio/aac", "aiff": "audio/aiff",
    "webm": "audio/webm",
}


async def inquire_image(question: str, image: bytes, image_format: str) -> str:
    info = await get_image_model_info()
    return await _transcribe(info, question, image=image, image_format=image_format)


async def inquire_audio(question: str, audio: bytes, audio_format: str) -> str:
    info = await get_audio_model_info()
    return await _transcribe(info, question, audio=audio, audio_format=audio_format)


async def _transcribe(info: dict, question: str, *, image=None, image_format=None, audio=None, audio_format=None) -> str:
    provider = info.get("provider", "openrouter")
    model = info["model"]

    if provider == "gemini":
        return await _call_gemini(model, question, image=image, image_format=image_format, audio=audio, audio_format=audio_format)
    else:
        return await _call_openai_compat(model, question, image=image, image_format=image_format, audio=audio, audio_format=audio_format)


# ── Gemini provider ─────────────────────────────────────

def _build_gemini_payload(model: str, question: str, *, image=None, image_format=None, audio=None, audio_format=None) -> dict:
    parts: list = [{"text": question}]

    if image is not None:
        image_b64 = base64.b64encode(image).decode()
        mime = f"image/{image_format}"
        parts.append({"inlineData": {"mimeType": mime, "data": image_b64}})

    if audio is not None:
        audio_b64 = base64.b64encode(audio).decode()
        mime = AUDIO_MIME_MAP.get(audio_format, f"audio/{audio_format}")
        parts.append({"inlineData": {"mimeType": mime, "data": audio_b64}})

    return {
        "contents": [{"parts": parts}]
    }


def _extract_gemini_text(response: httpx.Response) -> str:
    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return f"Error: {response.text}"


async def _call_gemini(model: str, question: str, **kwargs) -> str:
    payload = _build_gemini_payload(model, question, **kwargs)
    headers = {
        "x-goog-api-key": config.GEMINI_API_KEY,
        "Content-Type": "application/json",
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
    return _extract_gemini_text(response)


# ── OpenAI-compatible provider (OpenRouter, DeepSeek) ────

def _build_openai_payload(model: str, question: str, *, image=None, image_format=None, audio=None, audio_format=None) -> dict:
    content: list = [{"type": "text", "text": question}]

    if image is not None:
        image_b64 = base64.b64encode(image).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/{image_format};base64,{image_b64}"}
        })

    if audio is not None:
        audio_b64 = base64.b64encode(audio).decode()
        content.append({
            "type": "input_audio",
            "input_audio": {"data": audio_b64, "format": audio_format}
        })

    return {
        "model": model,
        "messages": [{"role": "user", "content": content}]
    }


def _extract_openai_text(response: httpx.Response) -> str:
    try:
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return f"Error: {response.text}"


async def _call_openai_compat(model: str, question: str, **kwargs) -> str:
    payload = _build_openai_payload(model, question, **kwargs)
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    url = "https://openrouter.ai/api/v1/chat/completions"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
    return _extract_openai_text(response)
