import re
from pathlib import Path
from lib.constants import ALLOWED_READ_AUDIO_FORMAT


class FolderUtils:
    """文件夹工具类。"""
    @staticmethod
    def find_album_dir(audio_file: Path, input_root: Path, disc_f_pattern: str) -> Path | None:
        """
        根据音频文件路径查找其所属的专辑目录。
        逻辑：
        - 如果音频文件直接在 input_root 下，返回输入目录
        - 如果音频文件在碟片目录（如 D1）下，则返回碟片目录的父目录
        - 否则返回音频文件的父目录
        """
        parent = audio_file.parent

        if parent == input_root:
            return parent

        is_disc_dir = re.match(disc_f_pattern, parent.name, flags=re.IGNORECASE)

        # 如果在碟片目录下，返回碟片目录的父目录
        if is_disc_dir and parent.parent != input_root:
            return parent.parent
        
        return parent

    @staticmethod
    def collect_album_dirs(input_root: Path, disc_f_pattern: str) -> list[Path]:
        """
        收集输入根目录下所有包含音频文件的专辑目录。
        Args:
            input_root: 输入根目录
            disc_f_pattern: 碟片文件夹模板
        Returns:
            专辑目录列表（已去重并排序）
        """
        seen: set[Path] = set()
        result: list[Path] = []
        
        # 遍历所有音频文件
        for f in input_root.rglob("*"):
            if not f.is_file() or f.suffix not in ALLOWED_READ_AUDIO_FORMAT:
                continue

            # 找到专辑目录
            album_dir = FolderUtils.find_album_dir(f, input_root, disc_f_pattern)
            if album_dir and album_dir not in seen:
                seen.add(album_dir)
                result.append(album_dir)
        
        return sorted(result)

