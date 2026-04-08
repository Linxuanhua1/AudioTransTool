# 支持质量探测的音频格式和排序格式
ALLOWED_READ_AUDIO_FORMAT = [
    ".dsf", ".wv", ".wav", ".alfc", ".aif", ".aiff",
    ".flac", ".m4a", ".mp3", ".ogg", ".wma"
]

_AUDIO_FORMAT_ORDER = {ext: i for i, ext in enumerate(ALLOWED_READ_AUDIO_FORMAT)}

# 支持的图片格式（用于 booklet 检测）
_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".webp", ".jxl"}

_DSD_RATE_MAP = {
    "2.8224":  "DSD64",
    "5.6448":  "DSD128",
    "11.2896": "DSD256",
    "22.5792": "DSD512",
    "45.1584": "DSD1024",
}

_COMMENT_SOURCE_MAP = {
    "jasrac /": "MORA",
    "ototoy":   "OTOTOY",
    "bandcamp": "Bandcamp",
}