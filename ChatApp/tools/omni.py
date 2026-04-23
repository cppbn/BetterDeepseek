import httpx
import base64
import ChatApp.config as config

async def inquire_image(question: str, image: bytes, image_format: str):
    image_b64 = base64.b64encode(image).decode('utf-8')
    image_data_url = f"data:image/{image_format};base64,{image_b64}"
    messages = [{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": question,
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image_data_url
                }
            }
        ]
    }]
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen/qwen3.5-flash-02-23",
        "messages": messages
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
    try:
        result = response.json()["choices"][0]["message"]["content"]
    except:
        result = f"Error: {response.text}"
    return result

async def inquire_audio(question: str, audio: bytes, audio_format: str):
    audio_b64 = base64.b64encode(audio).decode("utf-8")
    messages = [{
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": question,
            },
            {
                "type": "input_audio",
                "input_audio": {
                    "data": audio_b64,
                    "format": audio_format
                }
            }
        ]
    }]
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "xiaomi/mimo-v2.5",
        "messages": messages
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
    try:
        result = response.json()["choices"][0]["message"]["content"]
    except:
        result = f"Error: {response.text}"
    return result
