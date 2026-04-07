import mutagen
from pathlib import Path
from typing import Callable

from mutagen.mp4 import MP4Cover, MP4Tags, MP4FreeForm

from lib.meta.image import ImageTag, ImageType
from lib.meta.consts import MP4_TO_STANDARD, STANDARD_TO_MP4, MP4_TUPLE_REVERSE, MP4_INT_FIELDS, MP4_BOOL_FIELDS
from lib.meta.base import MetaHandler, InternalTags, logger


def _write_mp4_pic(tags: MP4Tags, values: set) -> None:
    covers = []
    for img in values:
        if not isinstance(img, ImageTag):
            continue
        mime = img.mime or ""
        fmt = MP4Cover.FORMAT_JPEG if mime.endswith(("jpeg", "jpg")) else MP4Cover.FORMAT_PNG
        covers.append(MP4Cover(img.data, imageformat=fmt))
    if covers:
        tags["covr"] = covers


def _write_mp4_tuple(tuple_buf: dict, std_key: str, values: set) -> None:
    mp4_key, idx = MP4_TUPLE_REVERSE[std_key]
    buf = tuple_buf.setdefault(mp4_key, [0, 0])
    try:
        buf[idx] = int(next(iter(values), "0"))
    except (ValueError, TypeError):
        pass


def _write_mp4_bool(tags: MP4Tags, mp4_key: str, values: set) -> None:
    try:
        tags[mp4_key] = bool(int(next(iter(values), "0")))
    except (ValueError, TypeError):
        tags[mp4_key] = False


def _write_mp4_int(tags: MP4Tags, mp4_key: str, values: set) -> None:
    int_vals = []
    for v in values:
        try:
            int_vals.append(int(v))
        except (ValueError, TypeError):
            pass
    if int_vals:
        tags[mp4_key] = int_vals


def _write_mp4_freeform(tags: MP4Tags, std_key: str, values: set) -> None:
    freeform_key = f"----:com.apple.iTunes:{std_key}"
    tags[freeform_key] = [
        MP4FreeForm(v.encode("utf-8") if isinstance(v, str) else v)
        for v in values
    ]


def _write_mp4_str(tags: MP4Tags, mp4_key: str, values: set) -> None:
    str_vals = [v for v in values if isinstance(v, str)]
    if str_vals:
        tags[mp4_key] = str_vals


def _flush_mp4_tuples(tags: MP4Tags, tuple_buf: dict) -> None:
    for mp4_key, (num, total) in tuple_buf.items():
        tags[mp4_key] = [(num, total)]


def write_mp4(internal: InternalTags, output_path: Path) -> None:
    audio = mutagen.File(output_path)
    if audio is None:
        raise ValueError(f"无法打开文件: {output_path}")

    if audio.tags is None:
        audio.add_tags()
    tags: MP4Tags = audio.tags
    tags.clear()

    tuple_buf: dict[str, list] = {}

    for std_key, values in internal.items():
        if std_key == "PIC":
            _write_mp4_pic(tags, values)
        elif std_key in MP4_TUPLE_REVERSE:
            _write_mp4_tuple(tuple_buf, std_key, values)
        else:
            mp4_key = STANDARD_TO_MP4.get(std_key)
            if mp4_key is None:
                _write_mp4_freeform(tags, std_key, values)
            elif mp4_key in MP4_BOOL_FIELDS:
                _write_mp4_bool(tags, mp4_key, values)
            elif mp4_key in MP4_INT_FIELDS:
                _write_mp4_int(tags, mp4_key, values)
            else:
                _write_mp4_str(tags, mp4_key, values)

    _flush_mp4_tuples(tags, tuple_buf)
    audio.save(output_path)


# ------------------------------------------------------------------ #
#  MP4Handler                                                          #
# ------------------------------------------------------------------ #

class MP4Handler(MetaHandler):
    def to_mp4(self, output_path: Path) -> None:
        dst = mutagen.File(output_path)
        dst.tags.clear()
        dst.tags.update(self.audio.tags)
        dst.save(output_path)

    def _to_internal(self) -> InternalTags:
        tags = self.audio.tags
        if tags is None:
            return {}

        std_tags: InternalTags = {}
        for field, tag in tags.items():
            if field == "©too":
                continue

            handler = self._FIELD_HANDLERS.get(field)

            if handler is None:
                first = tag[0] if isinstance(tag, list) and tag else tag
                for val_type, type_handler in self._TYPE_HANDLERS:
                    if isinstance(first, val_type):
                        handler = type_handler
                        break

            if handler is None:
                logger.error(f"{self.file_p}有不支持的MP4 tag，字段名为{field}，内容为{tag}")
                continue

            self._merge(std_tags, handler(self, tag, field))

        return std_tags

    def _handle_xid(self, tag, field) -> InternalTags:
        result = {}
        for item in tag:
            tmp_s = item.split(":")
            result.setdefault("CONTENTPROVIDER", set()).add(tmp_s[0])
            result.setdefault(tmp_s[1].upper(), set()).add(tmp_s[2])
        return result

    def _handle_bool(self, tag, field) -> InternalTags:
        map_field = MP4_TO_STANDARD[field]
        return {map_field: {str(int(tag))}}

    def _handle_tuple_list(self, tag, field) -> InternalTags:
        result = {}
        map_field1, map_field2 = MP4_TO_STANDARD[field]
        for val in tag:
            result.setdefault(map_field1, set()).add(str(val[0]))
            result.setdefault(map_field2, set()).add(str(val[1]))
        return result

    def _handle_str_list(self, tag, field) -> InternalTags:
        map_field = MP4_TO_STANDARD[field]
        return {map_field: set(tag)}

    def _handle_int_list(self, tag, field) -> InternalTags:
        map_field = MP4_TO_STANDARD[field]
        return {map_field: {str(i) for i in tag}}

    def _handle_freeform(self, tag, field) -> InternalTags:
        map_field = field.replace("----:com.apple.iTunes:", "")
        return {map_field: {bytes(i).decode("utf-8") for i in tag}}

    def _handle_cover(self, tag, field) -> InternalTags:
        FORMAT_MAP = {13: "image/jpeg", 14: "image/png"}
        result: InternalTags = {}
        for p in tag:
            img_format = FORMAT_MAP.get(p.imageformat)
            if img_format is None:
                logger.warning(f"{self.file_p}有不支持的图片格式: {p.imageformat}")
                continue
            pic = ImageTag(data=bytes(p), type=ImageType.Front, desc=None, mime=img_format)
            result.setdefault("PIC", set()).add(pic)
        return result

    _FIELD_HANDLERS: dict[str, Callable] = {
        "xid ": _handle_xid,
    }

    _TYPE_HANDLERS: list[tuple[type, Callable]] = [
        (bool,        _handle_bool),
        (tuple,       _handle_tuple_list),
        (str,         _handle_str_list),
        (int,         _handle_int_list),
        (MP4FreeForm, _handle_freeform),
        (MP4Cover,    _handle_cover),
    ]
