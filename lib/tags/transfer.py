from pathlib import Path
import mutagen, logging

from . import MetaReader, MetaWriter, InternalTags
from lib.constants import TYPE_TO_READER, TYPE_TO_WRITER, TAG_GROUPS

logger = logging.getLogger(__name__)

class TagsTransfer:
    # tag 格式分组，同组内直通
    @staticmethod
    def transfer_meta(input_p: Path, output_p: Path) -> None:
        src_audio = mutagen.File(input_p)
        dst_audio = mutagen.File(output_p)
        if src_audio is None:
            raise ValueError(f"无法读取源文件: {input_p}")
        if dst_audio is None:
            raise ValueError(f"无法读取目标文件: {output_p}")
        if type(src_audio) == "DSDIFF":
            logger.info(f"{input_p}是dff文件，没有元数据信息，跳过转移元数据")
            return
        reader_cls = TYPE_TO_READER.get(type(src_audio))
        writer_cls = TYPE_TO_WRITER.get(type(dst_audio))
        if reader_cls is None:
            raise ValueError(f"不支持的源文件类型: {type(src_audio).__name__}")
        if writer_cls is None:
            raise ValueError(f"不支持的目标文件类型: {type(dst_audio).__name__}")

        # 同 tag 格式直通
        same_format = any(
            reader_cls is r and writer_cls is w
            for r, w in TAG_GROUPS
        )
        if same_format:
            TagsTransfer._copy_tags(reader_cls(input_p), output_p)
            return

        internal = TagsTransfer._read_from_file(input_p, reader_cls)
        TagsTransfer._write_to_file(output_p, writer_cls, internal)

    @staticmethod
    def _read_from_file(input_p: Path, reader_cls: type[MetaReader]) -> InternalTags:
        return reader_cls(input_p).internal

    @staticmethod
    def _write_to_file(output_p: Path, writer_cls: type[MetaWriter], internal: InternalTags) -> None:
        writer_cls(output_p).write(internal)

    @staticmethod
    def _copy_tags(reader: MetaReader, output_p: Path) -> None:
        """同 tag 格式直通复制，不经过 internal 转换。"""
        reader.copy_to(output_p)