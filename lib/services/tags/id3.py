import mutagen, logging
from pathlib import Path
from typing import Callable
from mutagen.id3 import (
    TextFrame, UrlFrame, NumericPartTextFrame, PairedTextFrame, TPOS, TRCK,
    USLT, PCST, APIC, COMM, TXXX, WXXX, UFID, ID3)

from . import InternalImageTag, ImageType
from lib.services.constants import ID3_TO_STANDARD, ID3_NOT_SUPPORTED, STANDARD_TO_ID3, ID3_TUPLE_REVERSE, ID3_FRAME_CLASSES
from .base import MetaReader, MetaWriter, InternalTags


logger = logging.getLogger(__name__)


class ID3Writer(MetaWriter):
    def __init__(self, output_path: Path):
        self.output_path = output_path
        audio = mutagen.File(output_path)
        if audio is None:
            raise ValueError(f"无法打开文件: {output_path}")
        if audio.tags is None:
            audio.add_tags()
        self.audio = audio
        self.tags: ID3 = audio.tags
        self.tags.clear()
        self.tuple_buf: dict[str, list] = {}

    def write(self, internal: InternalTags) -> None:
        for std_key, values in internal.items():
            if std_key == "PIC":
                self._write_pic(values)
            elif std_key.startswith("COMMENT"):
                self._write_comment(std_key, values)
            elif std_key == "LYRICS":
                self._write_lyrics(values)
            elif std_key == "PODCAST":
                self._write_podcast(values)
            elif std_key == "MUSICBRAINZ_TRACKID":
                self._write_musicbrainz_trackid(values)
            elif std_key.startswith("WXXX"):
                self._write_wxxx(std_key, values)
            elif std_key == "URL":
                for v in values:
                    self.tags.add(WXXX(encoding=3, desc="", url=v))
            elif std_key in ID3_TUPLE_REVERSE:
                self._write_tuple_frame(std_key, values)
            else:
                id3_key = STANDARD_TO_ID3.get(std_key)
                if id3_key is not None:
                    self._write_standard_frame(id3_key, values)
                else:
                    self._write_txxx(std_key, values)

        self._flush_tuple_frames()
        self.tags.save(self.output_path)

    def _write_pic(self, values: set) -> None:
        for img in values:
            if not isinstance(img, InternalImageTag):
                continue
            pic_type = img.type.value if isinstance(img.type, ImageType) else (img.type or 0)
            self.tags.add(APIC(
                encoding=3, mime=img.mime or "image/jpeg",
                type=pic_type, desc=img.desc or "", data=img.data,
            ))

    def _write_comment(self, std_key: str, values: set) -> None:
        desc = std_key[8:] if std_key.startswith("COMMENT:") else ""
        self.tags.add(COMM(encoding=3, lang="eng", desc=desc, text=list(values)))

    def _write_lyrics(self, values: set) -> None:
        for lyric in values:
            self.tags.add(USLT(encoding=3, lang="eng", desc="", text=lyric))

    def _write_podcast(self, values: set) -> None:
        val = next(iter(values), "0")
        try:
            self.tags.add(PCST(encoding=3, value=int(val)))
        except (ValueError, TypeError):
            self.tags.add(PCST(encoding=3, value=0))

    def _write_musicbrainz_trackid(self, values: set) -> None:
        for v in values:
            self.tags.add(UFID(owner="http://musicbrainz.org", data=v.encode("utf-8")))

    def _write_wxxx(self, std_key: str, values: set) -> None:
        desc = std_key[4:] if len(std_key) > 4 else ""
        for v in values:
            self.tags.add(WXXX(encoding=3, desc=desc, url=v))

    def _write_txxx(self, std_key: str, values: set) -> None:
        if std_key.startswith("MUSICBRAINZ_"):
            parts = std_key[len("MUSICBRAINZ_"):].replace("_", " ").title()
            desc = f"MusicBrainz {parts}"
        elif std_key == "ACOUSTID_ID":
            desc = "Acoustid Id"
        else:
            desc = std_key
        self.tags.add(TXXX(encoding=3, desc=desc, text=list(values)))

    def _write_tuple_frame(self, std_key: str, values: set) -> None:
        frame_name = "TRCK" if std_key in ("TRACKNUMBER", "TOTALTRACKS") else "TPOS"
        idx = 0 if std_key in ("TRACKNUMBER", "DISCNUMBER") else 1
        buf = self.tuple_buf.setdefault(frame_name, ["", ""])
        buf[idx] = str(next(iter(values), ""))

    def _write_standard_frame(self, id3_key: str, values: set) -> None:
        frame_cls = ID3_FRAME_CLASSES.get(id3_key)
        if frame_cls is None:
            logger.warning(f"id3 key {id3_key}没有对应的帧类，跳过")
            return
        if issubclass(frame_cls, UrlFrame):
            for v in values:
                self.tags.add(frame_cls(url=v))
        else:
            self.tags.add(frame_cls(encoding=3, text=list(values)))

    def _flush_tuple_frames(self) -> None:
        for frame_name, (num, total) in self.tuple_buf.items():
            frame_cls = TRCK if frame_name == "TRCK" else TPOS
            text = f"{num}/{total}" if total else num
            self.tags.add(frame_cls(encoding=3, text=[text]))


class ID3Reader(MetaReader):
    def copy_to(self, output_path: Path) -> None:
        try:
            dst = ID3(output_path)
        except mutagen.id3.ID3NoHeaderError:
            dst = ID3()
        dst.clear()
        dst.update(self.audio.tags)
        dst.save(output_path)

    def read(self) -> InternalTags:
        tags = self.audio.tags
        if tags is None:
            return {}

        std_tags: InternalTags = {}
        for field, tag in tags.items():
            frame_name = type(tag).__name__
            if frame_name in ID3_NOT_SUPPORTED:
                continue
            if frame_name in ("TENC", "TSSE"):
                continue

            lookup_key = field if field.startswith("UFID") else frame_name
            handler = self._FRAME_HANDLERS.get(lookup_key)

            if handler is None:
                for base_type, type_handler in self._TYPE_HANDLERS:
                    if isinstance(tag, base_type):
                        handler = type_handler
                        break

            if handler is None:
                logger.error(f"{self.file_p}有不支持读取的帧，帧名为{frame_name}，内容为{tag.value}")
                continue

            self._merge(std_tags, handler(self, tag, field))

        return std_tags

    def _handle_paired_text(self, tag, field) -> InternalTags:
        result = {}
        for role, name in tag.people:
            result.setdefault(role.upper(), set()).add(name)
        return result

    def _handle_numeric_part(self, tag, field) -> InternalTags:
        result = {}
        map_field1, map_field2 = ID3_TO_STANDARD[type(tag).__name__]
        for item in tag.text:
            part1, sep, part2 = item.partition("/")
            result.setdefault(map_field1, set()).add(part1)
            if sep and part2:
                result.setdefault(map_field2, set()).add(part2)
        return result

    def _handle_text_frame(self, tag, field) -> InternalTags:
        map_field = ID3_TO_STANDARD[type(tag).__name__]
        return {map_field: set(tag.text)}

    def _handle_comm(self, tag, field) -> InternalTags:
        desc_key = f"COMMENT:{tag.desc}" if tag.desc else "COMMENT"
        return {desc_key: set(tag.text)}

    def _handle_txxx(self, tag, field) -> InternalTags:
        desc_lower = tag.desc.lower()
        if desc_lower.startswith("musicbrainz"):
            parts = tag.desc.upper().split(" ")
            map_field = parts[0] + "_" + "".join(parts[1:])
        elif desc_lower == "acoustid id":
            map_field = "ACOUSTID_ID"
        else:
            map_field = tag.desc.upper()
        return {map_field: set(tag.text)}

    def _handle_url_frame(self, tag, field) -> InternalTags:
        map_field = ID3_TO_STANDARD[type(tag).__name__]
        return {map_field: {tag.url}}

    def _handle_wxxx(self, tag, field) -> InternalTags:
        map_field = "WXXX" + tag.desc.upper() if tag.desc else "URL"
        return {map_field: {tag.url}}

    def _handle_apic(self, tag, field) -> InternalTags:
        pic = InternalImageTag(data=tag.data, type=tag.type, desc=tag.desc, mime=tag.mime)
        return {"PIC": {pic}}

    def _handle_ufid(self, tag, field) -> InternalTags:
        return {"MUSICBRAINZ_TRACKID": {tag.data.decode("utf-8")}}

    def _handle_lyrics(self, tag, field) -> InternalTags:
        map_field = ID3_TO_STANDARD[type(tag).__name__]
        return {map_field: {tag.text}}

    def _handle_podcast(self, tag, field) -> InternalTags:
        map_field = ID3_TO_STANDARD[type(tag).__name__]
        return {map_field: {str(tag.value)}}

    _FRAME_HANDLERS: dict[str, Callable] = {
        "COMM": _handle_comm,
        "TXXX": _handle_txxx,
        "WXXX": _handle_wxxx,
        "APIC": _handle_apic,
        "SYLT": _handle_lyrics,
        "USLT": _handle_lyrics,
        "PCST": _handle_podcast,
        "UFID:http://musicbrainz.org": _handle_ufid,
    }

    _TYPE_HANDLERS: list[tuple[type, Callable]] = [
        (PairedTextFrame,      _handle_paired_text),
        (NumericPartTextFrame, _handle_numeric_part),
        (TextFrame,            _handle_text_frame),
        (UrlFrame,             _handle_url_frame),
    ]
