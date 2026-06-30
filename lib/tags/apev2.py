import mutagen
from mutagen.apev2 import APEv2
from pathlib import Path

from . import InternalImageTag, ImageType, MetaReader, MetaWriter, InternalTags
from lib.tags.tag_mappings import APEV2_TO_STANDARD, STANDARD_TO_APEV2, IMAGE_TYPE_TO_APE, APEV2_TUPLE_REVERSE


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
        self.tuple_buf: dict[str, list] = {}

    def write(self, internal: InternalTags) -> None:
        for std_key, values in internal.items():
            if std_key == "PIC":
                self._write_pic(values)
            elif std_key in APEV2_TUPLE_REVERSE:
                self._write_tuple(std_key, values)
            else:
                self._write_text(std_key, values)
        self._flush_tuples()  # 新增
        self.audio.save(self.output_path)

    def _write_pic(self, values: set) -> None:
        for img in values:
            if not isinstance(img, InternalImageTag):
                continue
            img_type = img.type if isinstance(img.type, ImageType) else ImageType.Front
            ape_key = IMAGE_TYPE_TO_APE.get(img_type, "Cover Art (Front)")
            suffix = (img.mime or "image/jpeg").split("/")[-1]
            filename = f"cover.{suffix}".encode("utf-8")
            self.audio.tags[ape_key] = filename + b"\x00" + img.data

    def _write_tuple(self, std_key: str, values: set) -> None:  # 新增
        ape_key, idx = APEV2_TUPLE_REVERSE[std_key]
        buf = self.tuple_buf.setdefault(ape_key, [0, 0])
        try:
            buf[idx] = int(next(iter(values), "0"))
        except (ValueError, TypeError):
            pass

    def _flush_tuples(self) -> None:  # 新增
        for ape_key, (num, total) in self.tuple_buf.items():
            if total:
                self.audio.tags[ape_key] = f"{num}/{total}"
            else:
                self.audio.tags[ape_key] = str(num)

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

    @staticmethod
    def _handle_cover(field: str, tag) -> InternalTags:
        img_type = APEV2_TO_STANDARD[field.upper()]
        delimiter = tag.value.find(b"\x00")
        comment = tag.value[:delimiter].decode("utf-8", "replace")
        suffix = Path(comment).suffix.lower().lstrip(".")
        pic = InternalImageTag(
            data=tag.value[delimiter + 1:],
            type=img_type,
            desc=None,
            mime=f"image/{suffix}",
        )
        return {"PIC": {pic}}

    @staticmethod
    def _handle_text(field:str , tag) -> InternalTags:
        map_field = APEV2_TO_STANDARD.get(field.upper(), field.upper())
        if isinstance(map_field, tuple):
            result = {}
            map_field1, map_field2 = map_field
            for val in tag:
                # discnumber和track字段可能不带/
                if "/" in val:
                    val1, val2 = val.split('/')
                    result.setdefault(map_field1, set()).add(str(val1))
                    result.setdefault(map_field2, set()).add(str(val2))
                else:
                    result.setdefault(map_field1, set()).add(str(val))
            return result
        else:
            values = set(tag.value.split(b"\x00")) if b"\x00" in tag else set(tag)
            return {map_field: values}
