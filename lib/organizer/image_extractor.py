import io, mutagen, hashlib
from pathlib import Path
from collections import defaultdict
from PIL import Image
from typing import Any

from lib.constants import ALLOWED_READ_AUDIO_FORMAT, TYPE_TO_READER, TYPE_TO_WRITER
from lib.tags import InternalImageTag
from lib.common import PathManager


# --------------------------------------------------------------------------- #
# ImageExtractor
# --------------------------------------------------------------------------- #

class ImageExtractor:
    """
    提取音频内嵌图片并删除内嵌图片。

    用法
    ----
    extractor = ImageExtractor()
    extractor.extract_and_remove()
    """

    def extract_and_remove(self) -> None:
        """交互式入口。"""
        print("询问输入文件夹的时候，输入 # 返回主菜单")
        while True:
            folder_path = PathManager.check_input_folder_path()
            if folder_path == "#":
                print("返回主菜单")
                return
            self._process_root(Path(folder_path))

    # ------------------------------------------------------------------ #
    # 处理根目录
    # ------------------------------------------------------------------ #

    def _process_root(self, root: Path) -> None:
        # 按专辑目录分组音频文件
        groups: dict[Path, list[Path]] = defaultdict(list)

        for f in root.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in ALLOWED_READ_AUDIO_FORMAT:
                continue
            groups[f.parent].append(f)

        if not groups:
            print("未找到音频文件")
            return

        for album_dir, files in sorted(groups.items()):
            self._process_album(album_dir, files)

    # ------------------------------------------------------------------ #
    # 处理单个专辑目录
    # ------------------------------------------------------------------ #

    def _process_album(self, album_dir: Path, files: list[Path]) -> None:
        print(f"\n处理专辑目录：{album_dir}")

        # 收集所有去重后的图片（以 bytes 为 key 去重）
        unique_images: dict[str, InternalImageTag] = {}
        pending_del_pic: list[tuple[Path, Any, dict]] = []

        for f in files:
            src_audio = mutagen.File(str(f))
            audio_type = type(src_audio)
            reader_cls = TYPE_TO_READER.get(audio_type)
            internal= reader_cls(f).internal

            pics = internal.get("PIC", set())
            if not pics:
                continue

            internal["PIC"] = set()
            pending_del_pic.append((f, audio_type, internal))
            for pic in pics:
                if isinstance(pic, InternalImageTag) and pic.data:
                    digest = hashlib.sha256(pic.data).hexdigest()
                    unique_images.setdefault(digest, pic)

        if not unique_images:
            print("  没有内嵌图片，跳过")
            return

        # 保存图片
        images_list = list(unique_images.values())
        saved = self._save_images(album_dir, images_list)
        print(f"  已保存 {saved} 张图片")

        # 删除内嵌图片
        removed = 0
        if self._remove_embedded_pics(pending_del_pic):
            removed += 1
        print(f"  已从 {removed} 个音频文件中移除内嵌图片")

    # ------------------------------------------------------------------ #
    # 保存图片为 PNG
    # ------------------------------------------------------------------ #

    @staticmethod
    def _save_images(album_dir: Path, images: list[InternalImageTag]) -> int:
        count = 0
        for i, img in enumerate(images):
            if i == 0:
                name = "Cover.png"
            else:
                name = f"Cover({i + 1}).png"

            out_path = album_dir / name
            try:
                pil_img = Image.open(io.BytesIO(img.data))
                pil_img.save(out_path, format="PNG")
                count += 1
                print(f"  保存：{name}")
            except Exception as e:
                print(f"  保存图片失败：{e}")
        return count

    # ------------------------------------------------------------------ #
    # 删除内嵌图片
    # ------------------------------------------------------------------ #

    @staticmethod
    def _remove_embedded_pics(audio_tags: list[tuple[Path, Any, dict]]) -> int:
        deleted = 0
        for f, audio_type, internal in audio_tags:
            writer_cls = TYPE_TO_WRITER.get(audio_type)
            writer_cls(f).write(internal)
            deleted += 1
        return deleted