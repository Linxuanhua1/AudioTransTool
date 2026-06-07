"""音频目标编码格式枚举（叶子模块，无重依赖）。

单独成文件：format_checker 等只需依赖该枚举，无需导入承载 mutagen/tags 依赖的 audio_handler。
"""
from enum import Enum, auto


class AudioEncodeFormat(Enum):
    FLAC = auto()
    WAVEPACK = auto()
    UNSUPPORTED = auto()
