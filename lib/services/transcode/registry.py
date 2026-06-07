"""音频/图片处理器注册表：扩展名 -> Handler 类。

原 constants/handlers.py 上移至 transcode 层（处理器属于本层），直接 eager 构建。
"""
from .audio import (WavHandler, M4aHandler, ApeHandler, TakHandler, TtaHandler,
                    FlacHandler, WavepackHandler, DSDHandler, AiffHandler)
from .image.image_handler import (JpgHandler, PngHandler, BmpHandler, TiffHandler, WebpHandler)


AUDIO_HANDLERS = {
    ".wav": WavHandler,
    ".m4a": M4aHandler,
    ".ape": ApeHandler,
    ".tak": TakHandler,
    ".tta": TtaHandler,
    ".flac": FlacHandler,
    ".wv": WavepackHandler,
    ".dsf": DSDHandler,
    ".dff": DSDHandler,
    ".aiff": AiffHandler,
    ".aif": AiffHandler,
    ".aifc": AiffHandler,
}

IMAGE_HANDLERS = {
    ".jpeg": JpgHandler,
    ".jpg": JpgHandler,
    ".png": PngHandler,
    ".bmp": BmpHandler,
    ".tif": TiffHandler,
    ".tiff": TiffHandler,
    ".webp": WebpHandler,
}
