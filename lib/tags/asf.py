from pathlib import Path
import struct
import mutagen
from mutagen.asf import ASFByteArrayAttribute, ASFTags

from lib.tags.tag_mappings import (
    ASF_TO_STANDARD, ASF_SKIP_TO_MAP, STANDARD_TO_ASF, ASF_TUPLE_REVERSE,
)
from . import InternalImageTag, ImageType, MetaWriter, MetaReader, InternalTags


class AsfWriter(MetaWriter):
    def __init__(self, output_path: Path):
        self.output_path = output_path
        audio = mutagen.File(output_path)
        if audio is None:
            raise ValueError(f"无法打开文件: {output_path}")
        if audio.tags is None:
            audio.add_tags()
        self.audio = audio
        self.tags = audio.tags  # ASFTags（list 子类，(key, ASFBaseAttribute) 的集合）
        self.tags.clear()
        self.tuple_buf: dict[str, list] = {}

    def write(self, internal: InternalTags) -> None:
        for std_key, values in internal.items():
            # 与 AsfReader 读取侧对称：编码器/SDK 自动生成的技术字段直接跳过
            if std_key in ASF_SKIP_TO_MAP:
                continue
            if std_key == "PIC":
                self._write_pic(values)
            elif std_key in ASF_TUPLE_REVERSE:
                self._write_tuple(std_key, values)
            else:
                self._write_text(std_key, values)

        self._flush_tuples()
        self.audio.save(self.output_path)

    def _write_pic(self, values: set) -> None:
        """
        反向构造 WM/Picture 二进制块，与 AsfReader._handle_asf_image 对称：
        - 1 byte: picture type
        - 4 bytes: image data size (little-endian)
        - UTF-16-LE null-terminated MIME
        - UTF-16-LE null-terminated description
        - raw image data
        """
        attrs = []
        for img in values:
            if not isinstance(img, InternalImageTag):
                continue
            pic_type = img.type.value if isinstance(img.type, ImageType) else (img.type or 0)
            header = struct.pack("<bi", pic_type, len(img.data))
            mime = (img.mime or "").encode("utf-16-le") + b"\x00\x00"
            desc = (img.desc or "").encode("utf-16-le") + b"\x00\x00"
            block = header + mime + desc + img.data
            attrs.append(ASFByteArrayAttribute(block))
        if attrs:
            self.tags["WM/Picture"] = attrs

    def _write_tuple(self, std_key: str, values: set) -> None:
        asf_key, idx = ASF_TUPLE_REVERSE[std_key]
        buf = self.tuple_buf.setdefault(asf_key, ["", ""])
        buf[idx] = str(next(iter(values), ""))

    def _flush_tuples(self) -> None:
        # AsfReader 读取 WM/PartOfSet 时按 "a/b" 严格拆成两段，
        # 所以这里始终写成 "num/total"（缺失的一段补 0），保证能被自身读回。
        for asf_key, (num, total) in self.tuple_buf.items():
            self.tags[asf_key] = [f"{num or '0'}/{total or '0'}"]

    def _write_text(self, std_key: str, values: set) -> None:
        asf_key = STANDARD_TO_ASF.get(std_key)
        if asf_key is None:
            raise ValueError(f"未知的标准字段，缺少 ASF 映射: {std_key!r}")
        str_vals = [str(v) for v in values]
        if str_vals:
            self.tags[asf_key] = str_vals

class AsfReader(MetaReader):
    def copy_to(self, output_path: Path) -> None:
        # 同格式（WMA -> WMA）直通：原样复制全部 ASF 属性，
        # 不经过标准化中间层，因此跳过字段、未映射字段、WM/Picture 都会被完整保留。
        dst = mutagen.File(output_path)
        if dst.tags is None:
            dst.tags = ASFTags()
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
            if field in ASF_SKIP_TO_MAP:
                continue

            if field == "WM/Picture":
                std_value = self._handle_asf_image(tag)
            else:
                std_value = self._handle_text(field, tag)
            self._merge(std_tags, std_value)

        return std_tags

    def _handle_asf_image(self, tag) -> InternalTags:
        """
        解析 ASF / WM/Picture 二进制数据，返回 ImageTag。
        数据结构：
        - 1 byte: picture type
        - 4 bytes: image data size (little-endian)
        - UTF-16-LE null-terminated MIME
        - UTF-16-LE null-terminated description
        - raw image data
        """
        result: InternalTags = {}
        for data in tag:
            data = data.value
            pic_type_raw, size = struct.unpack_from("<bi", data)
            pos = 5

            mime, pos = self._read_utf16le_cstring(data, pos)
            desc, pos = self._read_utf16le_cstring(data, pos)

            image_data = data[pos:pos + size]
            if len(image_data) != size:
                raise ValueError("Invalid ASF picture block: image data truncated")

            try:
                pic_type = ImageType(pic_type_raw)
            except ValueError:
                pic_type = None

            pic = InternalImageTag(data=image_data, type=pic_type, desc=desc or None, mime=mime or None)
            result.setdefault("PIC", set()).add(pic)
        return result

    # 读取 UTF-16-LE 的 null 结尾字符串
    @staticmethod
    def _read_utf16le_cstring(buf: bytes, start: int) -> tuple[str, int]:
        chunks = bytearray()
        pos = start

        while pos + 1 < len(buf):
            if buf[pos:pos + 2] == b"\x00\x00":
                pos += 2
                return chunks.decode("utf-16-le"), pos
            chunks.extend(buf[pos:pos + 2])
            pos += 2

        raise ValueError("Invalid ASF picture block: unterminated UTF-16 string")

    @staticmethod
    def _handle_text(field: str, tag) -> InternalTags:
        if field not in ASF_TO_STANDARD:
            raise ValueError(f"未知的 ASF 字段，缺少映射: {field!r}")
        map_field = ASF_TO_STANDARD[field]
        # 处理WM/PartOfSet
        if isinstance(map_field, tuple):
            result = {}
            map_field1, map_field2 = map_field
            for val in tag:
                val1, val2 = val.value.split('/')
                result.setdefault(map_field1, set()).add(str(val1))
                result.setdefault(map_field2, set()).add(str(val2))
            return result
        else:
            values = set(i.value for i in tag)
            return {map_field: values}

