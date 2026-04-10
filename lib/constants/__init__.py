"""
常量模块统一导出
所有常量集中管理，方便统一导入
"""

# 格式相关
from .formats import (
    ALLOWED_READ_AUDIO_FORMAT,
    AUDIO_FORMAT_ORDER,
    IMAGE_FORMATS,
)

# 扫描器相关
from .scanner import (
    DSD_RATE_MAP,
    COMMENT_SOURCE_MAP,
)

# 重命名器相关
from .renamer import (
    RENAMER_SUPPORTED_EXTRACT_FIELD,
    FIELD_EXTRACT_FROM_TAGS,
)

# VGM 相关
from .vgm import (
    VGM_HEADERS,
    VGM_BASE_URL,
    VGM_URL_RE,
    VGM_PRODUCT_CATEGORIES,
    VGM_FIELD_MAP,
    VGM_MONTH_MAP,
)

# Tag 映射相关
from .tag_mappings import (
    # Mutagen 类型
    ID3_TYPES,
    VORBIS_TYPES,
    MP4_TYPES,
    APEV2_TYPES,
    ASF_TYPES,
    # Reader/Writer 映射
    TYPE_TO_READER,
    TYPE_TO_WRITER,
    TAG_GROUPS,
    # ID3 映射
    ID3_NOT_SUPPORTED,
    ID3_TO_STANDARD,
    STANDARD_TO_ID3,
    ID3_TUPLE_REVERSE,
    ID3_FRAME_CLASSES,
    # APEv2 映射
    APEV2_TO_STANDARD,
    STANDARD_TO_APEV2,
    IMAGE_TYPE_TO_APE,
    # MP4 映射
    MP4_TO_STANDARD,
    STANDARD_TO_MP4,
    MP4_TUPLE_REVERSE,
    MP4_BOOL_FIELDS,
    MP4_INT_FIELDS,
    # ASF 映射
    ASF_TO_STANDARD,
)

# 处理器映射相关
from .handlers import (
    AUDIO_HANDLERS,
    IMAGE_HANDLERS,
)


__all__ = [
    # 格式
    'ALLOWED_READ_AUDIO_FORMAT',
    'AUDIO_FORMAT_ORDER',
    'IMAGE_FORMATS',
    # 扫描器
    'DSD_RATE_MAP',
    'COMMENT_SOURCE_MAP',
    # 重命名器
    'RENAMER_SUPPORTED_EXTRACT_FIELD',
    'FIELD_EXTRACT_FROM_TAGS',
    # VGM
    'VGM_HEADERS',
    'VGM_BASE_URL',
    'VGM_URL_RE',
    'VGM_PRODUCT_CATEGORIES',
    'VGM_FIELD_MAP',
    'VGM_MONTH_MAP',
    # Tag 映射
    'ID3_TYPES',
    'VORBIS_TYPES',
    'MP4_TYPES',
    'APEV2_TYPES',
    'ASF_TYPES',
    'TYPE_TO_READER',
    'TYPE_TO_WRITER',
    'TAG_GROUPS',
    'ID3_NOT_SUPPORTED',
    'ID3_TO_STANDARD',
    'STANDARD_TO_ID3',
    'ID3_TUPLE_REVERSE',
    'ID3_FRAME_CLASSES',
    'APEV2_TO_STANDARD',
    'STANDARD_TO_APEV2',
    'IMAGE_TYPE_TO_APE',
    'MP4_TO_STANDARD',
    'STANDARD_TO_MP4',
    'MP4_TUPLE_REVERSE',
    'MP4_BOOL_FIELDS',
    'MP4_INT_FIELDS',
    'ASF_TO_STANDARD',
    # 处理器
    'AUDIO_HANDLERS',
    'IMAGE_HANDLERS',
]
