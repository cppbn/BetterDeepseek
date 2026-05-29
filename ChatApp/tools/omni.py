import httpx
import base64
import logging
import ChatApp.config as config
from ChatApp.providers.model_manager import get_image_model, get_audio_model

logger = logging.getLogger(__name__)

AUDIO_MIME_MAP = {
    "wav": "audio/wav", "mp3": "audio/mp3", "mpeg": "audio/mpeg",
    "mp4": "audio/mp4", "m4a": "audio/mp4", "ogg": "audio/ogg",
    "flac": "audio/flac", "aac": "audio/aac", "aiff": "audio/aiff",
    "webm": "audio/webm",
}


async def inquire_image(question: str, image: bytes, image_format: str) -> str:
    model = await get_image_model()
    return await _transcribe(model, question, image=image, image_format=image_format)


async def inquire_audio(question: str, audio: bytes, audio_format: str) -> str:
    model = await get_audio_model()
    return await _transcribe(model, question, audio=audio, audio_format=audio_format)


def _build_payload(model: str, question: str, *, image=None, image_format=None, audio=None, audio_format=None) -> dict:
    content: list = [{"type": "text", "text": question}]

    if image is not None:
        image_b64 = base64.b64encode(image).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/{image_format};base64,{image_b64}"}
        })

    if audio is not None:
        audio_b64 = base64.b64encode(audio).decode()
        mime = AUDIO_MIME_MAP.get(audio_format, f"audio/{audio_format}")
        fmt = mime.split("/")[-1]
        fmt_map = {"mpeg": "mp3", "mp4": "m4a"}
        fmt = fmt_map.get(fmt, fmt)
        content.append({
            "type": "input_audio",
            "input_audio": {"data": audio_b64, "format": fmt}
        })

    return {
        "model": model,
        "messages": [{"role": "user", "content": content}]
    }


def _extract_text(response: httpx.Response) -> str:
    try:
        return response.json()["choices"][0]["message"]["content"]
    except Exception:
        return f"Error: {response.text}"


async def _transcribe(model: str, question: str, **kwargs) -> str:
    payload = _build_payload(model, question, **kwargs)
    headers = {
        "Authorization": f"Bearer {config.NEWAPI_API_KEY}",
        "Content-Type": "application/json",
    }
    url = f"{config.NEWAPI_BASE_URL}/chat/completions"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
    return _extract_text(response)
