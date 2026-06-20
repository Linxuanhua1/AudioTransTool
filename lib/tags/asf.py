from pathlib import Path
import struct

from lib.tags.tag_mappings import ASF_TO_STANDARD, ASF_SKIP_TO_MAP
from . import InternalImageTag, ImageType, MetaWriter, MetaReader, InternalTags


# TODO: AsfWriter
class AsfWriter(MetaWriter):
    def __init__(self, output_p: Path):
        pass

    def write(self, input_root: Path) -> None:
        pass

class AsfReader(MetaReader):
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

