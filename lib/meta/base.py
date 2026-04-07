import mutagen
from abc import ABC, abstractmethod
from pathlib import Path

from lib.log import setup_logger

logger = setup_logger(__name__)

InternalTags = dict[str, set]


class MetaReader(ABC):
    def __init__(self, file_p: Path):
        self.file_p = file_p
        self.audio = mutagen.File(file_p)
        self._internal: InternalTags | None = None

    @property
    def internal(self) -> InternalTags:
        if self._internal is None:
            self._internal = self.read()
        return self._internal

    @abstractmethod
    def read(self) -> InternalTags:
        pass

    @staticmethod
    def copy_to(out_p: Path) -> None:
        pass

    @staticmethod
    def _merge(target: InternalTags, source: InternalTags) -> None:
        for key, values in source.items():
            target.setdefault(key, set()).update(values)


class MetaWriter(ABC):
    @abstractmethod
    def __init__(self, file_p: Path):
        pass

    @abstractmethod
    def write(self, internal: InternalTags) -> None:
        pass


class MetaTransfer:
    # tag 格式分组，同组内直通
    @staticmethod
    def transfer_meta(input_p: Path, output_p: Path) -> None:
        from lib.meta.id3 import ID3Reader, ID3Writer
        from lib.meta.mp4 import MP4Reader, MP4Writer
        from lib.meta.apev2 import APEv2Reader, APEv2Writer
        from lib.meta.vorbis import VorbisReader, VorbisWriter

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
            MetaTransfer._copy_tags(reader_cls(input_p), output_p)
            return

        internal = MetaTransfer._read_from_file(input_p, reader_cls)
        MetaTransfer._write_to_file(output_p, writer_cls, internal)

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
