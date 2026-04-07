"""
ImageExtractor
==============
遍历目录下的音频文件，提取内嵌图片保存为 PNG 到同目录，
然后删除音频中的内嵌图片。

同一专辑目录下相同的图片数据只保存一次。
"""
import io, re, mutagen
from pathlib import Path
from collections import defaultdict
from PIL import Image

from lib.tags.base import MetaReader
from lib.tags.image import ImageTag
from lib.common.path_manager import PathManager


# --------------------------------------------------------------------------- #
# Reader 分发
# --------------------------------------------------------------------------- #

def _get_reader_cls(file_p: Path) -> type[MetaReader] | None:
    from lib.tags.id3 import ID3Reader
    from lib.tags.mp4 import MP4Reader
    from lib.tags.apev2 import APEv2Reader
    from lib.tags.vorbis import VorbisReader

    from mutagen.mp3 import MP3
    from mutagen.trueaudio import TrueAudio
    from mutagen.wave import WAVE
    from mutagen.aiff import AIFF
    from mutagen.dsf import DSF
    from mutagen.flac import FLAC
    from mutagen.ogg import OggFileType
    from mutagen.oggvorbis import OggVorbis
    from mutagen.aac import AAC
    from mutagen.monkeysaudio import MonkeysAudio
    from mutagen.wavpack import WavPack
    from mutagen.tak import TAK
    from mutagen.mp4 import MP4

    audio = mutagen.File(file_p)
    if audio is None:
        return None

    TYPE_MAP: dict[type, type[MetaReader]] = {
        **{t: ID3Reader for t in (MP3, TrueAudio, WAVE, AIFF, DSF)},
        **{t: VorbisReader for t in (FLAC, OggFileType, OggVorbis)},
        **{t: MP4Reader for t in (AAC, MP4)},
        **{t: APEv2Reader for t in (MonkeysAudio, WavPack, TAK)},
    }
    return TYPE_MAP.get(type(audio))


_DISC_DIR_RE = re.compile(r"^(?:D|Disc|disc|DISC)\s*\d+$", re.IGNORECASE)

_AUDIO_EXTS = {
    ".flac", ".ogg", ".mp3", ".wav", ".dsf", ".m4a", ".wma",
    ".aiff", ".aif", ".tta", ".ape", ".wv", ".tak", ".aac",
}


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
            if not f.is_file() or f.suffix.lower() not in _AUDIO_EXTS:
                continue
            album_dir = self._resolve_album_dir(f, root)
            groups[album_dir].append(f)

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
        unique_images: dict[bytes, ImageTag] = {}

        for f in files:
            reader_cls = _get_reader_cls(f)
            if reader_cls is None:
                continue
            try:
                reader = reader_cls(f)
                internal = reader.internal
            except Exception as e:
                print(f"  读取失败 {f.name}：{e}")
                continue

            pics = internal.get("PIC", set())
            for pic in pics:
                if isinstance(pic, ImageTag) and pic.data:
                    unique_images.setdefault(pic.data, pic)

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
                name = f"Cover ({i + 1}).png"

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
            from mutagen.ogg import OggFileType
            from mutagen.mp4 import MP4
            from mutagen.id3 import ID3
            from mutagen.apev2 import APEv2

            modified = False

            # FLAC / OGG
            if isinstance(audio, FLAC):
                if audio.pictures:
                    audio.clear_pictures()
                    modified = True
                if "METADATA_BLOCK_PICTURE" in (audio.tags or {}):
                    del audio.tags["METADATA_BLOCK_PICTURE"]
                    modified = True
            elif isinstance(audio, OggFileType):
                if audio.tags and "METADATA_BLOCK_PICTURE" in audio.tags:
                    del audio.tags["METADATA_BLOCK_PICTURE"]
                    modified = True
            # MP4
            elif hasattr(audio, "tags") and isinstance(audio.tags, type(None)) is False:
                from mutagen.mp4 import MP4Tags
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

    # ------------------------------------------------------------------ #
    # 解析专辑目录
    # ------------------------------------------------------------------ #

    @staticmethod
    def _resolve_album_dir(audio_file: Path, root: Path) -> Path:
        parent = audio_file.parent
        if parent == root:
            return parent
        if _DISC_DIR_RE.match(parent.name.strip()) and parent.parent != root:
            return parent.parent
        return parent
