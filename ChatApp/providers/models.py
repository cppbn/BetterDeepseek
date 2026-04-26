from ChatApp.providers.model_manager import get_models

supported_models = {
    "default": {"provider": "deepseek", "model": "deepseek-reasoner", "thinking": True, "accept_image": False, "accept_audio": False}
}


async def init_models():
    data = await get_models()
    supported_models.clear()
    supported_models.update(data)
