import io
import os
import tarfile
from typing import BinaryIO


def tar_pack(file_content: bytes, arcname: str) -> bytes:
    """将文件内容打包成 tar 流"""
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        info = tarfile.TarInfo(name=arcname)
        info.size = len(file_content)
        tar.addfile(info, io.BytesIO(file_content))
    return tar_stream.getvalue()


def tar_unpack(tar_data: bytes, target_path: str) -> bytes:
    """从 tar 流中提取指定路径的文件内容（支持绝对/相对路径，自动匹配 basename 作为后备）"""
    # 规范化目标路径：移除前导斜杠，转为相对路径
    normalized_target = target_path.lstrip('/')
    with tarfile.open(fileobj=io.BytesIO(tar_data), mode="r") as tar:
        # 先尝试精确匹配
        for member in tar.getmembers():
            if member.name == normalized_target:
                f = tar.extractfile(member)
                if f:
                    return f.read()
        # 若失败，尝试仅匹配文件名（向后兼容）
        basename = os.path.basename(normalized_target)
        for member in tar.getmembers():
            if os.path.basename(member.name) == basename:
                f = tar.extractfile(member)
                if f:
                    return f.read()
    raise FileNotFoundError(f"File {target_path} not found in tar archive")