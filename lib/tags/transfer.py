from pathlib import Path
import mutagen
from lib.tags.base import MetaReader, MetaWriter, InternalTags


class TagsTransfer:
    # tag 格式分组，同组内直通
    @staticmethod
    def transfer_meta(input_p: Path, output_p: Path) -> None:
        from lib.tags.id3 import ID3Reader, ID3Writer
        from lib.tags.mp4 import MP4Reader, MP4Writer
        from lib.tags.apev2 import APEv2Reader, APEv2Writer
        from lib.tags.vorbis import VorbisReader, VorbisWriter

        from mutagen.mp3 import MP3
        from mutagen.trueaudio import TrueAudio
        from mutagen.wave import WAVE
        from mutagen.aiff import AIFF
        from mutagen.dsf import DSF
        from mutagen.flac import FLAC
        from mutagen.ogg import OggFileType
        from mutagen.oggvorbis import OggVorbis
        from mutagen.aac import AAC
        from mutagen.monkeysaudio import MonkeysAudio
        from mutagen.wavpack import WavPack
        from mutagen.tak import TAK
        from mutagen.mp4 import MP4

        ID3_TYPES    = (MP3, TrueAudio, WAVE, AIFF, DSF)
        VORBIS_TYPES = (FLAC, OggFileType, OggVorbis)
        MP4_TYPES    = (AAC, MP4)
        APEV2_TYPES  = (MonkeysAudio, WavPack, TAK)

        TYPE_TO_READER: dict[type, type[MetaReader]] = {
            **{t: ID3Reader    for t in ID3_TYPES},
            **{t: VorbisReader for t in VORBIS_TYPES},
            **{t: MP4Reader    for t in MP4_TYPES},
            **{t: APEv2Reader  for t in APEV2_TYPES},
        }
        TYPE_TO_WRITER: dict[type, type[MetaWriter]] = {
            **{t: ID3Writer    for t in ID3_TYPES},
            **{t: VorbisWriter for t in VORBIS_TYPES},
            **{t: MP4Writer    for t in MP4_TYPES},
            **{t: APEv2Writer  for t in APEV2_TYPES},
        }

        # 同 tag 格式分组，用于直通判断
        TAG_GROUPS: list[tuple[type[MetaReader], type[MetaWriter]]] = [
            (ID3Reader,    ID3Writer),
            (VorbisReader, VorbisWriter),
            (MP4Reader,    MP4Writer),
            (APEv2Reader,  APEv2Writer),
        ]

        src_audio = mutagen.File(input_p)
        dst_audio = mutagen.File(output_p)
        if src_audio is None:
            raise ValueError(f"无法读取源文件: {input_p}")
        if dst_audio is None:
            raise ValueError(f"无法读取目标文件: {output_p}")

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