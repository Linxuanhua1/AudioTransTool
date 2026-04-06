import mutagen
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable
# APEV2
from mutagen.monkeysaudio import MonkeysAudio
from mutagen.tak import TAK
from mutagen.wavpack import WavPack
# ID3
from mutagen.trueaudio import TrueAudio
from mutagen.aiff import AIFF
from mutagen.dsf import DSF
from mutagen.wave import WAVE
from mutagen.mp3 import MP3
# M4A
from mutagen.aac import AAC
# Vorbis
from mutagen.ogg import OggFileType
from mutagen.flac import FLAC, Picture

from mutagen.mp4 import MP4Cover, MP4Tags, MP4FreeForm
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
    ID3,
)


from meta_map import (
    ID3_TO_STANDARD, ID3_NOT_SUPPORTED,
    MP4_TO_STANDARD, APEV2_TO_STANDARD, ImageTag, ImageType,
    STANDARD_TO_MP4, MP4_TUPLE_REVERSE,
    STANDARD_TO_ID3, ID3_TUPLE_REVERSE,
    STANDARD_TO_APEV2,
)
from lib.log import setup_logger

logger = setup_logger(__name__)


InternalTags = dict[str, set]

# ID3 帧名 -> mutagen 帧类，用于 to_id3 写入
_ID3_FRAME_CLASSES: dict[str, type] = {
    'TALB': TALB, 'TBPM': TBPM, 'TCOM': TCOM, 'TCON': TCON, 'TCOP': TCOP,
    'TCMP': TCMP, 'TDEN': TDEN, 'TDES': TDES, 'TKWD': TKWD,
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

# MP4 bool 字段集合
_MP4_BOOL_FIELDS = {'cpil', 'pgap', 'hdvd', 'pcst', 'shwm'}

# MP4 int 字段集合（值要存成 int list）
_MP4_INT_FIELDS = {
    'tmpo', 'rtng', 'plID', 'atID', 'cnID', 'cmID', 'sfID',
    'geID', 'stik', 'tves', 'tvsn', 'akID',
}


class MetaHandler(ABC):
    def __init__(self, file_p: Path):
        self.file_p = file_p
        self.audio = mutagen.File(file_p)
        self._internal: InternalTags | None = None

    @property
    def internal(self) -> InternalTags:
        if self._internal is None:
            self._internal = self._to_internal()
        return self._internal

    @abstractmethod
    def _to_internal(self) -> InternalTags:
        pass

    def to_vorbis(self, output_path: Path) -> None:
        """
        将 internal 写入 output_path 指向的 Vorbis/FLAC 文件。
        Vorbis Comment 的字段名即标准 key（大写），直接写入即可。
        PIC 单独用各自格式的图片接口写入。
        """
        audio = mutagen.File(output_path)
        if audio is None:
            raise ValueError(f"无法打开文件: {output_path}")

        # 清空现有 tag
        audio.clear()
        if hasattr(audio, 'clear_pictures'):
            audio.clear_pictures()  # FLAC

        for std_key, values in self.internal.items():
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
                        # OggVorbis：将 Picture 编码为 base64 存入 METADATA_BLOCK_PICTURE
                        import base64
                        audio["METADATA_BLOCK_PICTURE"] = [
                            base64.b64encode(pic.write()).decode("ascii")
                        ]
                continue

            str_values = [v for v in values if isinstance(v, str)]
            if not str_values:
                continue
            # Vorbis Comment 字段名规范为大写，但读取时不区分大小写；写入时统一大写
            audio[std_key.upper()] = str_values

        audio.save(output_path)

    def to_mp4(self, output_path: Path) -> None:
        """
        将 internal 写入 output_path 指向的 MP4/M4A 文件。
        """
        audio = mutagen.File(output_path)
        if audio is None:
            raise ValueError(f"无法打开文件: {output_path}")

        if audio.tags is None:
            audio.add_tags()
        tags: MP4Tags = audio.tags

        # 先清空
        tags.clear()

        # tuple 字段需要聚合后一起写，用临时 dict 收集
        # key: mp4_field_name -> [val0, val1]
        tuple_buf: dict[str, list] = {}

        for std_key, values in self.internal.items():
            # --- 封面图 ---
            if std_key == "PIC":
                covers = []
                for img in values:
                    if not isinstance(img, ImageTag):
                        continue
                    fmt = MP4Cover.FORMAT_JPEG if (img.mime or "").endswith("jpeg") or (img.mime or "").endswith("jpg") else MP4Cover.FORMAT_PNG
                    covers.append(MP4Cover(img.data, imageformat=fmt))
                if covers:
                    tags["covr"] = covers
                continue

            # --- tuple 字段：TRACKNUMBER/TOTALTRACKS/DISCNUMBER/TOTALDISCS ---
            if std_key in MP4_TUPLE_REVERSE:
                mp4_key, idx = MP4_TUPLE_REVERSE[std_key]
                buf = tuple_buf.setdefault(mp4_key, [0, 0])
                val = next(iter(values), "0")
                try:
                    buf[idx] = int(val)
                except (ValueError, TypeError):
                    pass
                continue

            # --- freeform 字段（----:com.apple.iTunes:XXX）---
            mp4_key = STANDARD_TO_MP4.get(std_key)
            if mp4_key is None:
                # 没有映射的字段写成 freeform
                freeform_key = f"----:com.apple.iTunes:{std_key}"
                tags[freeform_key] = [
                    MP4FreeForm(v.encode("utf-8") if isinstance(v, str) else v)
                    for v in values
                ]
                continue

            # --- bool 字段 ---
            if mp4_key in _MP4_BOOL_FIELDS:
                val = next(iter(values), "0")
                try:
                    tags[mp4_key] = bool(int(val))
                except (ValueError, TypeError):
                    tags[mp4_key] = False
                continue

            # --- int 字段 ---
            if mp4_key in _MP4_INT_FIELDS:
                int_vals = []
                for v in values:
                    try:
                        int_vals.append(int(v))
                    except (ValueError, TypeError):
                        pass
                if int_vals:
                    tags[mp4_key] = int_vals
                continue

            # --- 普通字符串字段 ---
            str_vals = [v for v in values if isinstance(v, str)]
            if str_vals:
                tags[mp4_key] = str_vals

        # 写回 tuple 字段
        for mp4_key, (num, total) in tuple_buf.items():
            tags[mp4_key] = [(num, total)]

        audio.save(output_path)

    def to_id3(self, output_path: Path) -> None:
        """
        将 internal 写入 output_path 指向的 ID3 文件（MP3 等）。
        """
        try:
            id3 = ID3(output_path)
        except mutagen.id3.ID3NoHeaderError:
            id3 = ID3()

        id3.clear()

        # tuple 字段聚合缓冲：id3_frame_name -> [val, total]
        tuple_buf: dict[str, list] = {}

        for std_key, values in self.internal.items():
            # --- 封面图 ---
            if std_key == "PIC":
                for img in values:
                    if not isinstance(img, ImageTag):
                        continue
                    pic_type = img.type.value if isinstance(img.type, ImageType) else (img.type or 0)
                    id3.add(APIC(
                        encoding=3,       # UTF-8
                        mime=img.mime or "image/jpeg",
                        type=pic_type,
                        desc=img.desc or "",
                        data=img.data,
                    ))
                continue

            # --- COMMENT ---
            if std_key.startswith("COMMENT"):
                desc = std_key[8:] if std_key.startswith("COMMENT:") else ""
                id3.add(COMM(encoding=3, lang="eng", desc=desc, text=list(values)))
                continue

            # --- LYRICS (USLT 无时间轴版本) ---
            if std_key == "LYRICS":
                for lyric in values:
                    id3.add(SYLT(encoding=3, lang="eng", desc="", text=lyric))
                continue

            # --- PODCAST (PCST，bool 帧) ---
            if std_key == "PODCAST":
                val = next(iter(values), "0")
                try:
                    id3.add(PCST(encoding=3, value=int(val)))
                except (ValueError, TypeError):
                    id3.add(PCST(encoding=3, value=0))
                continue

            # --- MUSICBRAINZ_TRACKID -> UFID ---
            if std_key == "MUSICBRAINZ_TRACKID":
                for v in values:
                    id3.add(UFID(owner="http://musicbrainz.org", data=v.encode("utf-8")))
                continue

            # --- URL 字段（WXXX for unknown, 或标准 Wxx） ---
            if std_key.startswith("WXXX"):
                desc = std_key[4:] if len(std_key) > 4 else ""
                for v in values:
                    id3.add(WXXX(encoding=3, desc=desc, url=v))
                continue

            if std_key == "URL":
                for v in values:
                    id3.add(WXXX(encoding=3, desc="", url=v))
                continue

            # --- TXXX：TXXX 自定义文本帧（映射里没有的 key） ---
            # 先查标准映射
            id3_key = STANDARD_TO_ID3.get(std_key)

            if id3_key is None:
                # MusicBrainz 自定义字段：MUSICBRAINZ_XXXX -> TXXX:MusicBrainz Xxxx
                if std_key.startswith("MUSICBRAINZ_"):
                    parts = std_key[len("MUSICBRAINZ_"):].replace("_", " ").title()
                    desc = f"MusicBrainz {parts}"
                elif std_key == "ACOUSTID_ID":
                    desc = "Acoustid Id"
                else:
                    desc = std_key
                id3.add(TXXX(encoding=3, desc=desc, text=list(values)))
                continue

            # --- tuple 字段：TRACKNUMBER/TOTALTRACKS/DISCNUMBER/TOTALDISCS ---
            if std_key in ID3_TUPLE_REVERSE:
                # ID3_TUPLE_REVERSE 的 value 是 ('disk', idx)，但对 ID3 我们用帧名
                # TRCK = TRACKNUMBER/TOTALTRACKS，TPOS = DISCNUMBER/TOTALDISCS
                frame_name = "TRCK" if std_key in ("TRACKNUMBER", "TOTALTRACKS") else "TPOS"
                idx = 0 if std_key in ("TRACKNUMBER", "DISCNUMBER") else 1
                buf = tuple_buf.setdefault(frame_name, ["", ""])
                val = next(iter(values), "")
                buf[idx] = str(val)
                continue

            # --- URL 帧（标准 Wxx） ---
            frame_cls = _ID3_FRAME_CLASSES.get(id3_key)
            if frame_cls is not None and issubclass(frame_cls, UrlFrame):
                for v in values:
                    id3.add(frame_cls(url=v))
                continue

            # --- 普通 TextFrame ---
            if frame_cls is not None:
                id3.add(frame_cls(encoding=3, text=list(values)))
                continue

            logger.warning("standard key %s (id3: %s) 没有对应的帧类，跳过", std_key, id3_key)

        # 写回 tuple 帧
        for frame_name, (num, total) in tuple_buf.items():
            frame_cls = TRCK if frame_name == "TRCK" else TPOS
            text = f"{num}/{total}" if total else num
            id3.add(frame_cls(encoding=3, text=[text]))

        id3.save(output_path)

    def to_apev2(self, output_path: Path) -> None:
        """
        将 internal 写入 output_path 指向的 APEv2 文件（APE/WavPack 等）。
        APEv2 只有文本值和二进制封面两种类型。
        """
        audio = mutagen.File(output_path)
        if audio is None:
            raise ValueError(f"无法打开文件: {output_path}")

        if audio.tags is None:
            audio.add_tags()

        # 清空现有 tag
        audio.tags.clear()

        # APEV2_TO_STANDARD 反查：ImageType -> APEv2 封面字段名
        _image_type_to_ape: dict[ImageType, str] = {
            v: k for k, v in APEV2_TO_STANDARD.items()
            if isinstance(v, ImageType)
        }

        for std_key, values in self.internal.items():
            # --- 封面图 ---
            if std_key == "PIC":
                for img in values:
                    if not isinstance(img, ImageTag):
                        continue
                    img_type = img.type if isinstance(img.type, ImageType) else ImageType.Front
                    ape_field = _image_type_to_ape.get(img_type, "Cover Art (Front)")
                    # APEv2 封面格式：<文件名>\x00<二进制数据>
                    suffix = (img.mime or "image/jpeg").split("/")[-1]
                    filename = f"cover.{suffix}".encode("utf-8")
                    audio.tags[ape_field] = filename + b"\x00" + img.data
                continue

            # 查映射（反查 APEV2_TO_STANDARD）
            ape_key = STANDARD_TO_APEV2.get(std_key, std_key)

            str_vals = [v for v in values if isinstance(v, str)]
            if not str_vals:
                continue

            # APEv2 多值用 \x00 分隔
            audio.tags[ape_key] = "\x00".join(str_vals)

        audio.save(output_path)

    @staticmethod
    def _merge(target: InternalTags, source: InternalTags) -> None:
        for key, values in source.items():
            target.setdefault(key, set()).update(values)

    @staticmethod
    def from_file(file_p: Path) -> "MetaHandler":
        audio = mutagen.File(file_p)
        if audio is None:
            raise ValueError(f"无法读取文件: {file_p}")

        TYPE_MAP = {
            MP3: ID3Handler,
            TrueAudio: ID3Handler,
            WAVE: ID3Handler,
            AIFF: ID3Handler,
            DSF: ID3Handler,
            FLAC: VorbisHandler,
            OggFileType: VorbisHandler,
            AAC: MP4Handler,
            MonkeysAudio: APEv2Handler,
            WavPack: APEv2Handler,
            TAK: APEv2Handler,
        }

        handler_cls = TYPE_MAP.get(type(audio))
        if handler_cls is None:
            raise ValueError(f"不支持的文件类型: {type(audio).__name__}")

        return handler_cls(file_p)


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


class APEv2Handler(MetaHandler):
    def to_apev2(self, output_path: Path) -> None:
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


if __name__ == "__main__":
    test_audio = Path(r"C:\Users\Linxuanhua\Desktop\AudioTransTool\test\test_metadata\16bit44.1khz.ape")
    meta_handler = MetaHandler.from_file(test_audio)
    meta_handler.to_vorbis(Path(r'C:\Users\Linxuanhua\Desktop\AudioTransTool\test\test_metadata\test.flac'))