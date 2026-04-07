import mutagen
from abc import ABC, abstractmethod
from pathlib import Path

from lib.log import setup_logger

logger = setup_logger(__name__)

InternalTags = dict[str, set]


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
        from lib.meta.vorbis import write_vorbis
        write_vorbis(self.internal, output_path)

    def to_mp4(self, output_path: Path) -> None:
        from lib.meta.mp4 import write_mp4
        write_mp4(self.internal, output_path)

    def to_id3(self, output_path: Path) -> None:
        from lib.meta.id3 import write_id3
        write_id3(self.internal, output_path)

    def to_apev2(self, output_path: Path) -> None:
        from lib.meta.apev2 import write_apev2
        write_apev2(self.internal, output_path)

    def write_to(self, output_path: Path) -> None:
        """根据目标文件类型自动选择写入方法。"""
        from mutagen.mp3 import MP3
        from mutagen.trueaudio import TrueAudio
        from mutagen.wave import WAVE
        from mutagen.aiff import AIFF
        from mutagen.dsf import DSF
        from mutagen.flac import FLAC
        from mutagen.ogg import OggFileType
        from mutagen.aac import AAC
        from mutagen.monkeysaudio import MonkeysAudio
        from mutagen.wavpack import WavPack
        from mutagen.tak import TAK

        audio = mutagen.File(output_path)
        if audio is None:
            raise ValueError(f"无法读取目标文件: {output_path}")

        TYPE_TO_WRITER = {
            MP3:           self.to_id3,
            TrueAudio:     self.to_id3,
            WAVE:          self.to_id3,
            AIFF:          self.to_id3,
            DSF:           self.to_id3,
            FLAC:          self.to_vorbis,
            OggFileType:   self.to_vorbis,
            AAC:           self.to_mp4,
            MonkeysAudio:  self.to_apev2,
            WavPack:       self.to_apev2,
            TAK:           self.to_apev2,
        }

        writer = TYPE_TO_WRITER.get(type(audio))
        if writer is None:
            raise ValueError(f"不支持的目标文件类型: {type(audio).__name__}")

        writer(output_path)

    @staticmethod
    def _merge(target: InternalTags, source: InternalTags) -> None:
        for key, values in source.items():
            target.setdefault(key, set()).update(values)

    @staticmethod
    def from_file(file_p: Path) -> MetaHandler:
        from mutagen.mp3 import MP3
        from mutagen.trueaudio import TrueAudio
        from mutagen.wave import WAVE
        from mutagen.aiff import AIFF
        from mutagen.dsf import DSF
        from mutagen.flac import FLAC
        from mutagen.ogg import OggFileType
        from mutagen.aac import AAC
        from mutagen.monkeysaudio import MonkeysAudio
        from mutagen.wavpack import WavPack
        from mutagen.tak import TAK

        from lib.meta.id3 import ID3Handler
        from lib.meta.mp4 import MP4Handler
        from lib.meta.apev2 import APEv2Handler
        from lib.meta.vorbis import VorbisHandler

        audio = mutagen.File(file_p)
        if audio is None:
            raise ValueError(f"无法读取文件: {file_p}")

        TYPE_MAP = {
            MP3:           ID3Handler,
            TrueAudio:     ID3Handler,
            WAVE:          ID3Handler,
            AIFF:          ID3Handler,
            DSF:           ID3Handler,
            FLAC:          VorbisHandler,
            OggFileType:   VorbisHandler,
            AAC:           MP4Handler,
            MonkeysAudio:  APEv2Handler,
            WavPack:       APEv2Handler,
            TAK:           APEv2Handler,
        }

        handler_cls = TYPE_MAP.get(type(audio))
        if handler_cls is None:
            raise ValueError(f"不支持的文件类型: {type(audio).__name__}")

        return handler_cls(file_p)
