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
from mutagen.asf import ASF

from .id3 import ID3Reader, ID3Writer
from .mp4 import MP4Reader, MP4Writer
from .apev2 import APEv2Reader, APEv2Writer
from .vorbis import VorbisReader, VorbisWriter
from .asf import AsfReader
from .base import MetaReader, MetaWriter


ID3_TYPES = (MP3, TrueAudio, WAVE, AIFF, DSF)
VORBIS_TYPES = (FLAC, OggFileType, OggVorbis)
MP4_TYPES = (AAC, MP4)
APEV2_TYPES = (MonkeysAudio, WavPack, TAK)
ASF_TYPES = ASF


TYPE_TO_READER: dict[type, type[MetaReader]] = {
    **{t: ID3Reader for t in ID3_TYPES},
    **{t: VorbisReader for t in VORBIS_TYPES},
    **{t: MP4Reader for t in MP4_TYPES},
    **{t: APEv2Reader for t in APEV2_TYPES},
    ASF: AsfReader
}
TYPE_TO_WRITER: dict[type, type[MetaWriter]] = {
    **{t: ID3Writer for t in ID3_TYPES},
    **{t: VorbisWriter for t in VORBIS_TYPES},
    **{t: MP4Writer for t in MP4_TYPES},
    **{t: APEv2Writer for t in APEV2_TYPES},
}

# 同 tag 格式分组，用于直通判断
TAG_GROUPS: list[tuple[type[MetaReader], type[MetaWriter]]] = [
    (ID3Reader, ID3Writer),
    (VorbisReader, VorbisWriter),
    (MP4Reader, MP4Writer),
    (APEv2Reader, APEv2Writer),
]