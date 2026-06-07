"""常量模块统一导出（纯字面数据，无任何上层依赖）。

只包含与具体业务无关的常量数据，可被任意层安全导入，不存在循环依赖。
标签映射数据见 lib.tags.tag_mappings；Reader/Writer 注册表见 lib.tags.registry；
音频/图片处理器注册表见 lib.services.transcode.registry。
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
    AUDIO_EXT2CLI_CMD,
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


__all__ = [
    # 格式
    "ALLOWED_READ_AUDIO_FORMAT",
    "AUDIO_FORMAT_ORDER",
    "DIRECT_SPLIT_FORMATS",
    "IMAGE_FORMATS",
    # 指令
    "CMD_WAVBYTES2FLAC",
    "CMD_PCMBYTES2FLAC",
    "CMD_BYTES2WV",
    "CMD_APE2WAVBYTES",
    "CMD_TAK2WAVBYTES",
    "CMD_TTA2WAVBYTES",
    "CMD_M4A2WAVBYTES",
    "CMD_WAVPACK2WAVBYTES",
    "AUDIO_EXT2CLI_CMD",
    # 扫描器
    "DSD_RATE_MAP",
    "COMMENT_SOURCE_MAP",
    # 重命名器
    "RENAMER_SUPPORTED_EXTRACT_FIELD",
    # VGM
    "VGM_HEADERS",
    "VGM_BASE_URL",
    "VGM_URL_RE",
    "VGM_PRODUCT_CATEGORIES",
    "VGM_FIELD_MAP",
    "VGM_MONTH_MAP",
]
