import mutagen, base64, pyvips
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
        for img in values:
            pic = process_picture(img)
            if isinstance(self.audio, FLAC):
                self.audio.add_picture(pic)
            else:
                encoded_picture = base64.b64encode(pic.write()).decode("ascii")
                self.audio.setdefault("metadata_block_picture", []).append(encoded_picture)

class VorbisReader(MetaReader):
    def copy_to(self, output_path: Path) -> None:
        src = self.internal
        dst = mutagen.File(output_path)
        dst.clear()
        if hasattr(dst, 'clear_pictures'):
            dst.clear_pictures()
        if src.get("PIC"):
            for img in src['PIC']:
                pic = process_picture(img)
                if isinstance(self.audio, FLAC):
                    self.audio.add_picture(pic)
                else:
                    encoded_picture = base64.b64encode(pic.write()).decode("ascii")
                    self.audio.setdefault("metadata_block_picture", []).append(encoded_picture)

    def read(self) -> InternalTags:
        tags = self.audio.tags
        std_tags: InternalTags = {}

        for field, tag in tags.items():
            if field.lower() == "metadata_block_picture":
                for p in tag:
                    data = base64.b64decode(p)
                    pic = Picture(data)
                    internal_image = InternalImageTag(pic.data, ImageType(pic.type), pic.desc, pic.mime)
                    std_tags.setdefault("PIC", set()).add(internal_image)
            else:
                std_tags.setdefault(field.upper(), set()).update(tag)

        if hasattr(self.audio, "pictures"):
            std_tags.setdefault("PIC", set()).update(self.audio.pictures)
        return std_tags


def process_picture(img: InternalImageTag) -> Picture:
    """处理图片逻辑：包括格式推断、MIME 类型设置等"""
    pic = Picture()
    pic.data = img.data
    # 设置 MIME 类型
    if img.mime:
        pic.mime = img.mime
    else:
        image = pyvips.Image.new_from_buffer(img.data, "")
        fmt = image.format
        if fmt == "jpeg":
            pic.mime = "image/jpeg"
        elif fmt == "png":
            pic.mime = "image/png"
        else:
            raise ValueError(f"Vorbis Comment不支持的图片格式{fmt}")
    pic.desc = img.desc or ""
    pic.type = img.type.value if isinstance(img.type, ImageType) else (img.type or 0)
    return pic