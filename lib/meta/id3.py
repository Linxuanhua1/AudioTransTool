import mutagen
from pathlib import Path
from typing import Callable

from mutagen.id3 import (
    TextFrame, UrlFrame, NumericPartTextFrame, PairedTextFrame,
    TALB, TBPM, TCOM, TCON, TCOP, TCMP, TDEN, TDES, TKWD, TCAT,
    MVNM, MVIN, GRP1, TDOR, TDLY, TDRC, TDRL, TDTG, TENC, TEXT, TFLT,
    TGID, TIT1, TIT2, TIT3, TKEY, TLAN, TLEN, TMED, TMOO, TOAL, TOFN,
    TOLY, TOPE, TOWN, TPE1, TPE2, TPE3, TPE4, TPOS, TPRO, TPUB, TRCK,
    TRSN, TRSO, TSO2, TSOA, TSOC, TSOP, TSOT, TSRC, TSSE, TSST,
    WCOM, WCOP, WFED, WOAF, WOAR, WOAS, WORS, WPAY, WPUB,
    TIPL, TMCL, IPLS,
    SYLT, PCST, APIC,
    COMM, TXXX, WXXX,
    UFID,
    ID3, TORY,
)

from lib.meta.meta_map import (
    ID3_TO_STANDARD, ID3_NOT_SUPPORTED, ImageTag, ImageType,
    STANDARD_TO_ID3, ID3_TUPLE_REVERSE,
)
from lib.meta.base import MetaHandler, InternalTags, logger


_ID3_FRAME_CLASSES: dict[str, type] = {
    'TALB': TALB, 'TBPM': TBPM, 'TCOM': TCOM, 'TCON': TCON, 'TCOP': TCOP,
    'TCMP': TCMP, 'TDEN': TDEN, 'TDES': TDES, 'TKWD': TKWD, "TORY": TORY,
    'TCAT': TCAT, 'MVNM': MVNM, 'MVIN': MVIN, 'GRP1': GRP1, 'TDOR': TDOR,
    'TDLY': TDLY, 'TDRC': TDRC, 'TDRL': TDRL, 'TDTG': TDTG, 'TENC': TENC,
    'TEXT': TEXT, 'TFLT': TFLT, 'TGID': TGID, 'TIT1': TIT1, 'TIT2': TIT2,
    'TIT3': TIT3, 'TKEY': TKEY, 'TLAN': TLAN, 'TLEN': TLEN, 'TMED': TMED,
    'TMOO': TMOO, 'TOAL': TOAL, 'TOFN': TOFN, 'TOLY': TOLY, 'TOPE': TOPE,
    'TOWN': TOWN, 'TPE1': TPE1, 'TPE2': TPE2, 'TPE3': TPE3, 'TPE4': TPE4,
    'TPRO': TPRO, 'TPUB': TPUB, 'TRSN': TRSN, 'TRSO': TRSO, 'TSO2': TSO2,
    'TSOA': TSOA, 'TSOC': TSOC, 'TSOP': TSOP, 'TSOT': TSOT, 'TSRC': TSRC,
    'TSSE': TSSE, 'TSST': TSST,
    'WCOM': WCOM, 'WCOP': WCOP, 'WFED': WFED, 'WOAF': WOAF, 'WOAR': WOAR,
    'WOAS': WOAS, 'WORS': WORS, 'WPAY': WPAY, 'WPUB': WPUB,
    'TIPL': TIPL, 'TMCL': TMCL, 'IPLS': IPLS,
}


def write_id3(internal: InternalTags, output_path: Path) -> None:
    try:
        id3 = ID3(output_path)
    except mutagen.id3.ID3NoHeaderError:
        id3 = ID3()

    id3.clear()
    tuple_buf: dict[str, list] = {}

    for std_key, values in internal.items():
        if std_key == "PIC":
            for img in values:
                if not isinstance(img, ImageTag):
                    continue
                pic_type = img.type.value if isinstance(img.type, ImageType) else (img.type or 0)
                id3.add(APIC(
                    encoding=3, mime=img.mime or "image/jpeg",
                    type=pic_type, desc=img.desc or "", data=img.data,
                ))
            continue

        if std_key.startswith("COMMENT"):
            desc = std_key[8:] if std_key.startswith("COMMENT:") else ""
            id3.add(COMM(encoding=3, lang="eng", desc=desc, text=list(values)))
            continue

        if std_key == "LYRICS":
            for lyric in values:
                id3.add(SYLT(encoding=3, lang="eng", desc="", text=lyric))
            continue

        if std_key == "PODCAST":
            val = next(iter(values), "0")
            try:
                id3.add(PCST(encoding=3, value=int(val)))
            except (ValueError, TypeError):
                id3.add(PCST(encoding=3, value=0))
            continue

        if std_key == "MUSICBRAINZ_TRACKID":
            for v in values:
                id3.add(UFID(owner="http://musicbrainz.org", data=v.encode("utf-8")))
            continue

        if std_key.startswith("WXXX"):
            desc = std_key[4:] if len(std_key) > 4 else ""
            for v in values:
                id3.add(WXXX(encoding=3, desc=desc, url=v))
            continue

        if std_key == "URL":
            for v in values:
                id3.add(WXXX(encoding=3, desc="", url=v))
            continue

        id3_key = STANDARD_TO_ID3.get(std_key)
        if id3_key is None:
            if std_key.startswith("MUSICBRAINZ_"):
                parts = std_key[len("MUSICBRAINZ_"):].replace("_", " ").title()
                desc = f"MusicBrainz {parts}"
            elif std_key == "ACOUSTID_ID":
                desc = "Acoustid Id"
            else:
                desc = std_key
            id3.add(TXXX(encoding=3, desc=desc, text=list(values)))
            continue

        if std_key in ID3_TUPLE_REVERSE:
            frame_name = "TRCK" if std_key in ("TRACKNUMBER", "TOTALTRACKS") else "TPOS"
            idx = 0 if std_key in ("TRACKNUMBER", "DISCNUMBER") else 1
            buf = tuple_buf.setdefault(frame_name, ["", ""])
            val = next(iter(values), "")
            buf[idx] = str(val)
            continue

        frame_cls = _ID3_FRAME_CLASSES.get(id3_key)
        if frame_cls is not None and issubclass(frame_cls, UrlFrame):
            for v in values:
                id3.add(frame_cls(url=v))
            continue

        if frame_cls is not None:
            id3.add(frame_cls(encoding=3, text=list(values)))
            continue

        logger.warning("standard key %s (id3: %s) 没有对应的帧类，跳过", std_key, id3_key)

    for frame_name, (num, total) in tuple_buf.items():
        frame_cls = TRCK if frame_name == "TRCK" else TPOS
        text = f"{num}/{total}" if total else num
        id3.add(frame_cls(encoding=3, text=[text]))

    id3.save(output_path)


class ID3Handler(MetaHandler):
    def to_id3(self, output_path: Path) -> None:
        try:
            dst = ID3(output_path)
        except mutagen.id3.ID3NoHeaderError:
            dst = ID3()
        dst.clear()
        dst.update(self.audio.tags)
        dst.save(output_path)

    def _to_internal(self) -> InternalTags:
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
        pic = ImageTag(data=tag.data, type=tag.type, desc=tag.desc, mime=tag.mime)
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