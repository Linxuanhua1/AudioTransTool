import io, mutagen, hashlib
from pathlib import Path
from collections import defaultdict
from PIL import Image

from lib.organizer.consts import ALLOWED_READ_AUDIO_FORMAT
from lib.tags.registery_consts import TYPE_TO_READER
from lib.tags.image import ImageTag
from lib.common.path_manager import PathManager


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
        unique_images: dict[str, ImageTag] = {}

        for f in files:
            src_audio = mutagen.File(str(f))
            reader_cls = TYPE_TO_READER.get(type(src_audio))
            internal= reader_cls(f).internal

            pics = internal.get("PIC", set())
            for pic in pics:
                if isinstance(pic, ImageTag) and pic.data:
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
        for f in files:
            if self._remove_embedded_pics(f):
                removed += 1
        print(f"  已从 {removed} 个音频文件中移除内嵌图片")

    # ------------------------------------------------------------------ #
    # 保存图片为 PNG
    # ------------------------------------------------------------------ #

    @staticmethod
    def _save_images(album_dir: Path, images: list[ImageTag]) -> int:
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
    def _remove_embedded_pics(file_p: Path) -> bool:
        """删除单个音频文件的所有内嵌图片，返回是否有修改。"""
        try:
            audio = mutagen.File(file_p)
            if audio is None:
                return False

            from mutagen.flac import FLAC
            from mutagen.oggvorbis import OggVorbis
            from mutagen.mp4 import MP4Tags
            from mutagen.id3 import ID3
            from mutagen.apev2 import APEv2

            modified = False

            # FLAC / OGG
            if isinstance(audio, (FLAC, OggVorbis)):
                if audio.pictures:
                    audio.clear_pictures()
                    modified = True

            elif hasattr(audio, "tags") and isinstance(audio.tags, type(None)) is False:
                # MP4
                if isinstance(audio.tags, MP4Tags) and "covr" in audio.tags:
                    del audio.tags["covr"]
                    modified = True
                # ID3
                elif hasattr(audio.tags, "getall"):
                    apics = audio.tags.getall("APIC")
                    if apics:
                        audio.tags.delall("APIC")
                        modified = True
                # APEv2
                elif hasattr(audio.tags, "keys"):
                    cover_keys = [k for k in audio.tags.keys() if k.startswith("Cover Art")]
                    for k in cover_keys:
                        del audio.tags[k]
                        modified = True

            if modified:
                audio.save()
            return modified

        except Exception as e:
            print(f"  删除内嵌图片失败 {file_p.name}：{e}")
            return False
