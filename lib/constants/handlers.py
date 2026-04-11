from lib.audio.audio_handler import (
    WavHandler, M4aHandler, ApeHandler, TakHandler, TtaHandler,
    FlacHandler, WavepackHandler, DSDHandler, AiffHandler
)
from lib.image.image_handler import (
    JpgHandler, PngHandler, BmpHandler, TiffHandler, WebpHandler
)


# ============================================================================
# 音频处理器映射
# ============================================================================

AUDIO_HANDLERS = {
    '.wav': WavHandler,
    '.m4a': M4aHandler,
    '.ape': ApeHandler,
    '.tak': TakHandler,
    '.tta': TtaHandler,
    '.flac': FlacHandler,
    ".wv": WavepackHandler,
    ".dsf": DSDHandler,
    ".dff": DSDHandler,
    ".aiff": AiffHandler,
    ".aif": AiffHandler,
    ".aifc": AiffHandler,
}


# ============================================================================
# 图片处理器映射
# ============================================================================

IMAGE_HANDLERS = {
    '.jpeg': JpgHandler,
    '.jpg': JpgHandler,
    '.png': PngHandler,
    '.bmp': BmpHandler,
    '.tif': TiffHandler,
    '.tiff': TiffHandler,
    '.webp': WebpHandler
}
