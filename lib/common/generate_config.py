content = """[transcode]
# =========================================================================== #
# 转码 配置
# =========================================================================== #
act_audio_trans = false                  # 是否开启音频转码，默认为false
act_cue_splitting = false                # 是否开启分轨功能，默认为false
act_img_transc = false                   # 是否开启照片转码，默认为false，转换所有支持格式到jxl
is_del_single_trk = false                # 分轨时是否删除原来的整轨和cue，默认为false
is_del_cue = false                       # 是否删除cue文件，默认为false
is_del_src_audio = false                 # 是否删除转码前的音频，默认为false
is_en_flac0_compress = false             # 是否要压缩无压缩的flac（比如mora的音频），默认为false
is_en_flt_compress = false               # 是否开启浮点音频压缩（常见于一些asmr和e-onkyo音频），默认为false
is_en_dsd_compress = false               # 是否开启dsd压缩，默认为false
is_del_src_img = false                   # 是否删除转码前的图片，默认为false
is_hdd = true                            # 存储介质是否为hdd，若为hdd多线程的线程数将设置为1，若为ssd则多线程数量为cpu核心数
                                          （仅在音频处理的时候，因为音频处理的速度瓶颈在硬盘，图片压缩的速度瓶颈在cpu）


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

# 支持的字段如下：
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
output_template = "[{{DATE}}][{{SOURCE}}][{{ALBUM}}][{{QUALITY}}][{{FOLDER_CONTENT}}]{% if SCORE %}[log{{SCORE}}%]{% endif %}"

# --- 从文件夹名提取编号的正则 (write_from_folder_name 使用) ---
catno_extract_pattern = '\\[.*?\\] .*? \\[(.*?)\\]'
catno_extract_group = "catalognumber"

"""



def generate_config():
    with open("config.toml", "w", encoding="utf-8") as f:
        f.write(content)