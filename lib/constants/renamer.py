"""
重命名器相关常量
包含支持的字段、提取字段等重命名功能使用的常量
"""

# ============================================================================
# 重命名器支持的字段
# ============================================================================

# 重命名器支持从文件夹名提取的字段集合
RENAMER_SUPPORTED_EXTRACT_FIELD: set = {
    "DATE", "ALBUM", "CATALOGNUMBER", "ALBUMARTIST", "SOURCE", "QUALITY", "FOLDER_CONTENT", "SCORE"
}

# 需要从tag中提取的字段列表
FIELD_EXTRACT_FROM_TAGS: list = [
    "DATE", "ALBUM", "CATALOGNUMBER", "ALBUMARTIST"
]
