import copy
import logging
import tomlkit
import tomllib
from pathlib import Path


logger = logging.getLogger("musicbox.config")

CONFIG_PATH = Path("config.toml")

content = """[transcode]
# =========================================================================== #
# 转码 配置
# =========================================================================== #
is_del_single_trk = false                # 分轨时是否删除原来的整轨和cue，默认为false
is_del_cue = false                       # 是否删除cue文件，默认为false
is_del_src_audio = false                 # 是否删除转码前的音频，默认为false
is_en_flac0_compress = false             # 是否要压缩无压缩的flac（比如mora的音频），默认为false
is_en_flt_compress = false               # 是否开启浮点音频压缩（常见于一些asmr和e-onkyo音频），默认为false
is_en_dsd_compress = false               # 是否开启dsd压缩，默认为false
is_del_src_img = false                   # 是否删除转码前的图片，默认为false
is_hdd = true                            # 存储介质是否为hdd，若为hdd多线程的线程数将设置为1，若为ssd则多线程数量为cpu核心数
                                         # （仅在音频处理的时候，因为音频处理的速度瓶颈在硬盘，图片压缩的速度瓶颈在cpu）

# --------------------------------------------------------------------------- #
# 图片转 png 规则
# --------------------------------------------------------------------------- #
# 下列文件名（不区分大小写匹配）的图片会被转换为 png，输出文件名采用此处书写的大小写
# （如 "Cover" -> Cover.png）；留空 [] 则不做此转换
img_to_png_names = ["Cover"]


# =========================================================================== #
# 自定义任务流 配置（Custom Task Process，主菜单 3）
# =========================================================================== #
[custom_task]
# 按此顺序在同一文件夹上依次执行任务，可混合两类任务（列入即执行）：
#   transcode 任务：audio_transcode、split_cue、image_transcode
#   organizer 任务：rename_from_tag、rename_from_name、extract_and_remove、separate_tag
task_pipeline = ["audio_transcode", "split_cue", "image_transcode"]


# =========================================================================== #
# VGMdb 配置
# =========================================================================== #
[vgm]
# Franchise 模式：
#   "flat"    = 直接获取页面所有专辑，在系列文件夹下创建专辑文件夹
#   "grouped" = 先获取所有作品再按分类归组，重复专辑放 Compilation 文件夹
franchise_mode = "grouped"

# 线程数量
fetch_threads = 4

# VGMdb 登录态 cookie（从浏览器复制整段 Cookie 字符串）
cookie = ""

# 作品文件夹命名模板（grouped 模式下使用）
# 可用变量：{date} {product_name}
product_fld_tpl = "[{date}] {product_name}"

# 专辑文件夹命名模板
# 可用变量：
#   {date}          - 发行日期 (Release Date)
#   {catno}         - 目录编号 (Catalog Number)
#   {album}         - 专辑名
#   {media_format}  - 媒体类型 (CD / Digital / Vinyl 等)
#   {publish_format}- 出版类型 (Commercial / Doujin 等)
#   {classification}- 分类 (Soundtrack / Arrange 等，多个用+连接)
#   {publisher}     - 发行商
#   {composer}      - 作曲家
#   {arranger}      - 编曲家
#   {performer}     - 表演者
#   {price}         - 价格
album_fld_tpl = "[{date}][{catno}][{album}][{media_format}]"

# =========================================================================== #
# 重命名 配置
# =========================================================================== #
[rename]
seps = ["/", "&", ", ", "; ", " _ ", " / ", "、", " feat. "]  # 元数据切分分割符

# 支持切分的字段如下：
# ALBUM, ALBUMARTIST, ALBUMARTISTSORT, ALBUMSORT, APPLESTOREACCOUNTTYPE, ARTIST,
# ARTISTSORT, AUDIODELAY, BPM, COMMENT, COMPOSER, COMPOSERSORT, CONDUCTOR, CONTENTGROUP,
# COPYRIGHT, DATE, DESCRIPTION, DIRECTOR, ENCODEDBY, ENCODERSETTINGS, ENCODINGTIME,
# FILEOWNER, FILETYPE, GENRE, GROUPING, INITIALKEY, INVOLVEDPEOPLE, ISRC, ITUNESACCOUNT,
# ITUNESADVISORY, ITUNESALBUMID, ITUNESARTISTID, ITUNESCATALOGID, ITUNESCOMPOSERID,
# ITUNESCOUNTRYID, ITUNESGENREID, ITUNESMEDIATYPE, ITUNESMOVEMENTNAME, ITUNESMOVEMENTNUMBER,
# ITUNESOWNER, ITUNESPURCHASEDATE, LANGUAGE, LENGTH, LYRICIST, LYRICS, MEDIATYPE, MIXARTIST,
# MOOD, MOVEMENT, MOVEMENTNAME, MOVEMENTTOTAL, MUSICBRAINZ_TRACKID, MUSICIANCREDITS, NARRATOR,
# NETRADIOOWNER, NETRADIOSTATION, ORIGARTIST, ORIGINALALBUM, ORIGINALDATE, ORIGINALFILENAME,
# ORIGLYRICIST, PODCASTCATEGORY, PODCASTDESC, PODCASTID, PODCASTKEYWORDS, PODCASTURL, PRODUCEDNOTICE,
# PUBLISHER, RATE, RATING, RECORDINGTIME, RELEASETIME, SETSUBTITLE, STOREDESCRIPTION, SUBTITLE,
# TAGGINGTIME, TITLE, TITLESORT, TVEPISODE, TVEPISODEID, TVNETWORK, TVSEASON, TVSHOW, TVSHOWSORT,
# WORK, WWWARTIST, WWWAUDIOFILE, WWWAUDIOSOURCE, WWWCOMMERCIALINFO, WWWCOPYRIGHT, WWWPAYMENT,
# WWWPUBLISHER, WWWRADIOPAGE

sep_fields = ["ARTIST", "ALBUMARTIST", "COMPOSER"]    # 切分的字段

disc_f_pattern = "^(?:D|Disc|disc|DISC)\\\\s*\\\\d+$"   # 查询目录时候检测音频的父目录是不是碟片文件夹
booklet_threshold = 2                               # 图片数量阈值：当某种格式图片 >= 此值时认为是 booklet

# --- 从文件夹名提取信息的正则 (rename_from_name 使用) ---
# pattern: 正则表达式，每个捕获组对应 groups 中的一个变量名
# groups:  按顺序指定每个捕获组代表的字段
extract_pattern = '(.*) \\[.*?\\] (.*)'
# 可选字段用 {% if var %}...{% endif %} 包裹，有值时渲染，无值时跳过
# 可用字段: DATE, ALBUM, CATALOGNUMBER, ALBUMARTIST, SOURCE, QUALITY, FOLDER_CONTENT, SCORE
extract_groups = ["DATE", "ALBUM"]

# --- 输出命名模板 (rename_from_name / rename_from_tag 共用) ---
# 文件夹内容有四个部分组成，audio_parts、video_parts、iso_parts、booklet_parts
folder_content_template = \"\"\"\\
{% if audio_parts %}{{audio_parts}}{% endif %}\\
{% if video_parts %}+{{video_parts}}{% endif %}\\
{% if iso_parts %}+{{iso_parts}}{% endif %}\\
{% if booklet_parts %}+{{booklet_parts}}{% endif %}\\
\"\"\"
# 可选字段用 {% if var %}...{% endif %} 包裹，有值时渲染，无值时跳过
# 可用字段: DATE, ALBUM, CATALOGNUMBER, ALBUMARTIST, SOURCE, QUALITY, FOLDER_CONTENT, SCORE (可选，仅日志抓取时有值)
output_template = "[{{DATE}}][{{SOURCE}}][{{ALBUM}}][{{QUALITY}}][{{FOLDER_CONTENT}}]{% if CATALOGNUMBER %}[{{CATALOGNUMBER}}]{% endif %}{% if SCORE %}[log{{SCORE}}%]{% endif %}"

# --- Source 来源匹配 ---
# source 检测规则已抽到文件末尾的 [[rename.match_rules]] 数组表（按顺序匹配，命中即用）。
# source_fallback 为所有规则都未命中时的兜底来源。
source_fallback = "WEB"

# --- 从文件夹名提取编号的正则 (write_from_folder_name 使用) ---
catno_extract_pattern = '\\[.*?\\] .*? \\[(.*?)\\]'
catno_extract_group = "catalognumber"

# =========================================================================== #
# Source 来源匹配规则（rename_from_tag 使用）
# =========================================================================== #
# 规则为有序数组，逐条匹配，命中即返回；全部未命中时用上面的 source_fallback。
# 字段：
#   field          要检测的标准标签字段名（QBZ_TID / URL / COMMENT / SOURCE ...）；
#                  特殊值 "EXT" 表示文件夹内音频扩展名集合（如 .dsf）。
#   match          匹配方式：
#                    exists   - 字段有值即命中
#                    contains - 字段值包含某子串
#                    equals   - 字段值等于某值
#                    regex    - 字段值匹配正则
#   value          contains/equals/regex 的匹配目标，可为字符串或字符串列表。
#   map            value 的替代写法，{ 目标 = 来源 } 内联表，按顺序匹配，命中即返回对应来源。
#   source         命中后返回的来源；省略则透传字段原值（用于 SOURCE 透传）。
#   case_sensitive 是否区分大小写，默认 false。

[[rename.match_rules]]
field = "QBZ_TID"
match = "exists"
source = "Qobuz"

[[rename.match_rules]]
field = "URL"
match = "contains"
map = { tidal = "Tidal", amazon = "Amazon" }

[[rename.match_rules]]
field = "COMMENT"
match = "contains"
map = { "jasrac /" = "MORA", ototoy = "OTOTOY", bandcamp = "Bandcamp" }

[[rename.match_rules]]
field = "SOURCE"
match = "exists"            # source 省略 -> 透传 SOURCE 字段值

[[rename.match_rules]]
field = "EXT"
match = "equals"
value = ".dsf"
source = "ISO转DSF"

"""



def generate_config() -> None:
    """写出带完整注释的默认 config.toml（文件不存在时使用）。"""
    CONFIG_PATH.write_text(content, encoding="utf-8")


def _is_table(obj) -> bool:
    """是否为可递归补子键的「表」；数组表 / 数组 / 标量返回 False。"""
    return hasattr(obj, "keys") and not isinstance(obj, (list, tuple, str, bytes))


def _fill_missing(default_tbl, user_tbl) -> int:
    """把 default_tbl 中存在、user_tbl 中缺失的键递归补进 user_tbl，返回补全数量。

    用户已有的键一律保留原值（不覆盖）；仅对「表」递归补子键，
    数组(含数组表)/标量按整键缺失才补。
    """
    added = 0
    for key, default_val in default_tbl.items():
        if key not in user_tbl:
            user_tbl[key] = copy.deepcopy(default_val)
            added += 1
        elif _is_table(default_val) and _is_table(user_tbl[key]):
            added += _fill_missing(default_val, user_tbl[key])
    return added


def ensure_config() -> dict:
    """确保 config.toml 完整：缺文件则生成；缺键则用默认值补全并写回（保留注释）。返回完整配置。"""
    if not CONFIG_PATH.exists():
        generate_config()
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)

    default_doc = tomlkit.parse(content)
    user_doc = tomlkit.parse(CONFIG_PATH.read_text(encoding="utf-8"))

    added = _fill_missing(default_doc, user_doc)
    if added:
        CONFIG_PATH.write_text(tomlkit.dumps(user_doc), encoding="utf-8")
        logger.info(f"config.toml 缺少 {added} 个参数，已自动补全默认值")

    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)