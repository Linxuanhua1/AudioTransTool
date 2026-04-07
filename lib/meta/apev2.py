import mutagen
from mutagen.apev2 import APEv2
from pathlib import Path

from lib.meta.image import ImageTag, ImageType
from lib.meta.consts import APEV2_TO_STANDARD, STANDARD_TO_APEV2, IMAGE_TYPE_TO_APE
from lib.meta.base import MetaReader, MetaWriter, InternalTags


class APEv2Writer(MetaWriter):
    def __init__(self, output_path: Path):
        self.output_path = output_path
        audio = mutagen.File(output_path)
        if audio is None:
            raise ValueError(f"无法打开文件: {output_path}")
        if audio.tags is None:
            audio.add_tags()
        self.audio = audio
        self.audio.tags.clear()

    def write(self, internal: InternalTags) -> None:
        for std_key, values in internal.items():
            if std_key == "PIC":
                self._write_pic(values)
            else:
                self._write_text(std_key, values)
        self.audio.save(self.output_path)

    def _write_pic(self, values: set) -> None:
        for img in values:
            if not isinstance(img, ImageTag):
                continue
            img_type = img.type if isinstance(img.type, ImageType) else ImageType.Front
            ape_field = IMAGE_TYPE_TO_APE.get(img_type, "Cover Art (Front)")
            suffix = (img.mime or "image/jpeg").split("/")[-1]
            filename = f"cover.{suffix}".encode("utf-8")
            self.audio.tags[ape_field] = filename + b"\x00" + img.data

    def _write_text(self, std_key: str, values: set) -> None:
        str_vals = [v for v in values if isinstance(v, str)]
        if not str_vals:
            return
        ape_key = STANDARD_TO_APEV2.get(std_key, std_key)
        self.audio.tags[ape_key] = "\x00".join(str_vals)


class APEv2Reader(MetaReader):
    def copy_to(self, output_path: Path) -> None:
        dst = mutagen.File(output_path)
        if dst.tags is None:
            dst.tags = APEv2()
        else:
            dst.tags.clear()
        dst.tags.update(self.audio.tags)
        dst.save(output_path)

    def read(self) -> InternalTags:
        tags = self.audio.tags
        if tags is None:
            return {}

        std_tags: InternalTags = {}
        for field, tag in tags.items():
            if field.startswith("Cover Art"):
                std_value = self._handle_cover(field, tag)
            else:
                std_value = self._handle_text(field, tag)
            self._merge(std_tags, std_value)

        return std_tags

    def _handle_cover(self, field, tag) -> InternalTags:
        img_type = APEV2_TO_STANDARD[field]
        delimiter = tag.value.find(b"\x00")
        comment = tag.value[:delimiter].decode("utf-8", "replace")
        suffix = Path(comment).suffix.lower().lstrip(".")
        pic = ImageTag(
            data=tag.value[delimiter + 1:],
            type=img_type,
            desc=None,
            mime=f"image/{suffix}",
        )
        return {"PIC": {pic}}

    def _handle_text(self, field, tag) -> InternalTags:
        map_field = APEV2_TO_STANDARD.get(field, field)
        values = set(tag.value.split(b"\x00")) if b"\x00" in tag else set(tag)
        return {map_field: values}
