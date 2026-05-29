import logging
from ChatApp.providers.model_manager import get_models

logger = logging.getLogger(__name__)

supported_models: dict = {}


async def init_models():
    data = await get_models()
    if not data:
        import aiosqlite
        from ChatApp.config import DATABASE_URL
        from ChatApp.providers.model_manager import sync_models_from_newapi
        try:
            async with aiosqlite.connect(DATABASE_URL) as db:
                await sync_models_from_newapi(db)
            logger.info("Auto-synced models from new-api on startup")
        except Exception as e:
            logger.warning(f"Auto-sync failed: {e}")
        data = await get_models()
    supported_models.clear()
    supported_models.update(data)
