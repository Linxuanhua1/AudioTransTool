"""
常量模块统一导出
所有常量集中管理，方便统一导入

使用延迟导入机制避免循环依赖：
- AUDIO_HANDLERS, IMAGE_HANDLERS（handlers → audio_handler → transfer → constants）
- TYPE_TO_READER, TYPE_TO_WRITER, TAG_GROUPS（tags → constants）
均通过 __getattr__ 机制延迟加载
"""

# 格式相关
from .formats import (
    ALLOWED_READ_AUDIO_FORMAT,
    AUDIO_FORMAT_ORDER,
    DIRECT_SPLIT_FORMATS,
    IMAGE_FORMATS,
)

# 指令相关
from .cli_cmd import (
    CMD_WAVBYTES2FLAC,
    CMD_PCMBYTES2FLAC,
    CMD_BYTES2WV,
    CMD_APE2WAVBYTES,
    CMD_TAK2WAVBYTES,
    CMD_TTA2WAVBYTES,
    CMD_M4A2WAVBYTES,
    CMD_WAVPACK2WAVBYTES,
    AUDIO_EXT2CLI_CMD
)

# 扫描器相关
from .scanner import (
    DSD_RATE_MAP,
    COMMENT_SOURCE_MAP,
)

# 重命名器相关
from .renamer import (
    RENAMER_SUPPORTED_EXTRACT_FIELD,
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

# ============================================================================
# 延迟导入的常量（通过 __getattr__ 机制）
# 以下常量存在循环依赖，必须延迟加载：
#   - AUDIO_HANDLERS, IMAGE_HANDLERS (handlers → audio_handler → transfer → constants)
#   - TYPE_TO_READER, TYPE_TO_WRITER, TAG_GROUPS (tags → constants)
# ============================================================================

def __getattr__(name):
    """
    模块级延迟导入接口
    支持：TYPE_TO_READER, TYPE_TO_WRITER, TAG_GROUPS, AUDIO_HANDLERS, IMAGE_HANDLERS
    """
    if name in ('TYPE_TO_READER', 'TYPE_TO_WRITER', 'TAG_GROUPS'):
        from . import tag_mappings
        return getattr(tag_mappings, name)
    if name in ('AUDIO_HANDLERS', 'IMAGE_HANDLERS'):
        from .handlers import AUDIO_HANDLERS, IMAGE_HANDLERS
        # 写入模块属性，后续访问不再触发 __getattr__
        globals()['AUDIO_HANDLERS'] = AUDIO_HANDLERS
        globals()['IMAGE_HANDLERS'] = IMAGE_HANDLERS
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # 格式
    'ALLOWED_READ_AUDIO_FORMAT',
    'AUDIO_FORMAT_ORDER',
    "DIRECT_SPLIT_FORMATS",
    'IMAGE_FORMATS',
    # 指令相关
    "CMD_M4A2WAVBYTES",
    "CMD_TTA2WAVBYTES",
    "CMD_BYTES2WV",
    "CMD_PCMBYTES2FLAC",
    "CMD_TAK2WAVBYTES",
    "CMD_APE2WAVBYTES",
    "CMD_WAVPACK2WAVBYTES",
    "CMD_WAVBYTES2FLAC",
    "AUDIO_EXT2CLI_CMD",
    # 扫描器
    'DSD_RATE_MAP',
    'COMMENT_SOURCE_MAP',
    # 重命名器
    'RENAMER_SUPPORTED_EXTRACT_FIELD',
    # VGM
    'VGM_HEADERS',
    'VGM_BASE_URL',
    'VGM_URL_RE',
    'VGM_PRODUCT_CATEGORIES',
    'VGM_FIELD_MAP',
    'VGM_MONTH_MAP',
    # Tag 映射（纯数据）
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
