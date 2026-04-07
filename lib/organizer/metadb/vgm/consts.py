import tomllib, re
from typing import Any


with open("config.toml", "rb") as _f:
    _cfg = tomllib.load(_f)

_vgm_cfg: dict[str, Any] = _cfg.get("vgm", {})

FRANCHISE_MODE: str     = _vgm_cfg.get("franchise_mode", "grouped")
FETCH_THREADS: int      = _vgm_cfg.get("fetch_threads", 4)
VGM_COOKIE: str         = _vgm_cfg.get("cookie", "")
PRODUCT_FOLDER_TPL: str = _vgm_cfg.get("product_folder_template", "[{date}] {product_name}")
ALBUM_FOLDER_TPL: str   = _vgm_cfg.get("album_folder_template",
                                        "[{date}][{catno}][{album}][{media_format}]")

if VGM_COOKIE == "":
    raise Exception("cookie不能为空")

HEADERS: dict[str, str] = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'zh-CN,zh;q=0.9',
    'cache-control': 'max-age=0',
    'dnt': '1',
    'priority': 'u=0, i',
    'referer': 'https://vgmdb.net/product/1094',
    'sec-ch-ua': '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
    'sec-ch-ua-arch': '"x86"',
    'sec-ch-ua-bitness': '"64"',
    'sec-ch-ua-full-version': '"146.0.7680.178"',
    'sec-ch-ua-full-version-list': '"Chromium";v="146.0.7680.178", "Not-A.Brand";v="24.0.0.0", "Google Chrome";v="146.0.7680.178"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-model': '""',
    'sec-ch-ua-platform': '"Windows"',
    'sec-ch-ua-platform-version': '"10.0.0"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'sec-gpc': '1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
    'cookie': VGM_COOKIE,
}

PRODUCT_CATEGORIES = [
    "Game", "Animation", "Publication", "Radio/Audio Drama",
    "Live Action", "Tokusatsu/Puppetry", "Multimedia Franchise",
    "Game-adjacent", "Event", "Artist Works",
]

BASE_URL = "https://vgmdb.net"

URL_RE = re.compile(r"^https?://vgmdb\.net/product/\d+$")

VGM_FIELD_MAP = {
    "Catalog Number": "catno",
    "Release Date":   "date",
    "Publish Format":  "publish_format",
    "Media Format":   "media_format",
    "Classification": "classification",
    "Published by":   "publisher",
    "Composed by":    "composer",
    "Arranged by":    "arranger",
    "Performed by":   "performer",
    "Release Price":  "price",
}

MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}