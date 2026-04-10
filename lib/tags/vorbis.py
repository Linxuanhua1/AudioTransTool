import mutagen
from pathlib import Path
from mutagen.flac import FLAC, Picture

from . import InternalImageTag, ImageType, MetaReader, MetaWriter, InternalTags


class VorbisWriter(MetaWriter):
    def __init__(self, output_path: Path):
        self.output_path = output_path
        audio = mutagen.File(output_path)
        if audio is None:
            raise ValueError(f"无法打开文件: {output_path}")
        audio.clear()
        if hasattr(audio, 'clear_pictures'):
            audio.clear_pictures()
        self.audio = audio

    def write(self, internal: InternalTags) -> None:
        for std_key, values in internal.items():
            if std_key == "PIC":
                self._write_pic(values)
            else:
                str_values = [v for v in values if isinstance(v, str)]
                if str_values:
                    self.audio[std_key.upper()] = str_values
        self.audio.save(self.output_path)

    def _write_pic(self, values: set) -> None:
        import base64
        for img in values:
            if not isinstance(img, InternalImageTag):
                continue
            pic = Picture()
            pic.data = img.data
            pic.mime = img.mime or "image/jpeg"
            pic.desc = img.desc or ""
            pic.type = img.type.value if isinstance(img.type, ImageType) else (img.type or 0)
            if isinstance(self.audio, FLAC):
                self.audio.add_picture(pic)
            else:
                self.audio["METADATA_BLOCK_PICTURE"] = [
                    base64.b64encode(pic.write()).decode("ascii")
                ]


class VorbisReader(MetaReader):
    def copy_to(self, output_path: Path) -> None:
        dst = mutagen.File(output_path)
        dst.clear()
        if hasattr(dst, 'clear_pictures'):
            dst.clear_pictures()
        dst.tags.update(self.audio.tags)
        if hasattr(self.audio, 'pictures'):
            for pic in self.audio.pictures:
                dst.add_picture(pic)
        dst.save(output_path)

    def read(self) -> InternalTags:
        tags = self.audio.tags
        std_tags: InternalTags = {}

        for field, tag in tags.items():
            std_tags.setdefault(field.upper(), set()).update(tag)

        if self.audio.pictures is not None:
            std_tags.setdefault("PIC", set()).update(self.audio.pictures)
        return std_tags
