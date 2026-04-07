import mutagen
from pathlib import Path
from mutagen.flac import FLAC, Picture

from lib.meta.meta_map import ImageTag, ImageType
from lib.meta.base import MetaHandler, InternalTags


def write_vorbis(internal: InternalTags, output_path: Path) -> None:
    audio = mutagen.File(output_path)
    if audio is None:
        raise ValueError(f"无法打开文件: {output_path}")

    audio.clear()
    if hasattr(audio, 'clear_pictures'):
        audio.clear_pictures()

    for std_key, values in internal.items():
        if std_key == "PIC":
            for img in values:
                if not isinstance(img, ImageTag):
                    continue
                pic = Picture()
                pic.data = img.data
                pic.mime = img.mime or "image/jpeg"
                pic.desc = img.desc or ""
                pic.type = img.type.value if isinstance(img.type, ImageType) else (img.type or 0)
                if isinstance(audio, FLAC):
                    audio.add_picture(pic)
                else:
                    import base64
                    audio["METADATA_BLOCK_PICTURE"] = [
                        base64.b64encode(pic.write()).decode("ascii")
                    ]
            continue

        str_values = [v for v in values if isinstance(v, str)]
        if not str_values:
            continue
        audio[std_key.upper()] = str_values

    audio.save(output_path)


# ------------------------------------------------------------------ #
#  Reader: Vorbis/FLAC -> internal                                     #
# ------------------------------------------------------------------ #

class VorbisHandler(MetaHandler):
    def to_vorbis(self, output_path: Path) -> None:
        dst = mutagen.File(output_path)
        dst.clear()
        if hasattr(dst, 'clear_pictures'):
            dst.clear_pictures()
        dst.tags.update(self.audio.tags)
        if hasattr(self.audio, 'pictures'):
            for pic in self.audio.pictures:
                dst.add_picture(pic)
        dst.save(output_path)

    def _to_internal(self) -> InternalTags:
        tags = self.audio.tags
        std_tags: InternalTags = {}

        for field, tag in tags.items():
            std_tags.setdefault(field, set()).update(tag)

        if self.audio.pictures is not None:
            std_tags.setdefault("PIC", set()).update(self.audio.pictures)
        return std_tags