import io
from PIL import Image
import logging
logger = logging.getLogger(__name__)
# 配置压缩阈值（字节数）
IMAGE_SIZE_THRESHOLD = 2 * 1024 * 1024  # 2MB
MAX_IMAGE_DIMENSION = 720  # 最大边长（像素）
JPEG_QUALITY = 75  # JPEG 压缩质量 (1-100)

async def _compress_image_if_needed(image_bytes: bytes, original_format: str) -> tuple[bytes, str]:
    """
    如果图片字节数超过阈值，则进行压缩。
    返回 (compressed_bytes, new_format)
    """
    if len(image_bytes) <= IMAGE_SIZE_THRESHOLD:
        return image_bytes, original_format

    try:
        img = Image.open(io.BytesIO(image_bytes))
        # 转换为 RGB 模式（JPEG 不支持透明通道）
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # 调整尺寸（保持宽高比）
        width, height = img.size
        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            ratio = min(MAX_IMAGE_DIMENSION / width, MAX_IMAGE_DIMENSION / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # 编码为 JPEG（统一格式以获得更好的压缩率）
        output_buffer = io.BytesIO()
        img.save(output_buffer, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        compressed_bytes = output_buffer.getvalue()

        logger.info(f"Image compressed: {len(image_bytes)} -> {len(compressed_bytes)} bytes")
        return compressed_bytes, "jpeg"
    except Exception as e:
        logger.warning(f"Image compression failed, using original: {e}")
        return image_bytes, original_format