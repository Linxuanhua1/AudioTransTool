"""标签 Reader/Writer 注册表。

按 mutagen 文件类型映射到对应的标准化 Reader/Writer。位于 tags 层顶端，
直接 eager 构建（不再延迟加载）。
"""
from lib.tags.tag_mappings import ID3_TYPES, VORBIS_TYPES, MP4_TYPES, APEV2_TYPES, ASF_TYPES
from lib.tags.id3 import ID3Reader, ID3Writer
from lib.tags.mp4 import MP4Reader, MP4Writer
from lib.tags.apev2 import APEv2Reader, APEv2Writer
from lib.tags.vorbis import VorbisReader, VorbisWriter
from lib.tags.asf import AsfReader, AsfWriter

TYPE_TO_READER = {
    **{t: ID3Reader for t in ID3_TYPES},
    **{t: VorbisReader for t in VORBIS_TYPES},
    **{t: MP4Reader for t in MP4_TYPES},
    **{t: APEv2Reader for t in APEV2_TYPES},
    ASF_TYPES: AsfReader,
}

TYPE_TO_WRITER = {
    **{t: ID3Writer for t in ID3_TYPES},
    **{t: VorbisWriter for t in VORBIS_TYPES},
    **{t: MP4Writer for t in MP4_TYPES},
    **{t: APEv2Writer for t in APEV2_TYPES},
    ASF_TYPES: AsfWriter,
}

TAG_GROUPS = [
    (ID3Reader, ID3Writer),
    (VorbisReader, VorbisWriter),
    (MP4Reader, MP4Writer),
    (APEv2Reader, APEv2Writer),
    (AsfReader, AsfWriter),
]
