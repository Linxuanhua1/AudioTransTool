import re, mutagen
from pathlib import Path
from typing import Optional
from jinja2 import Template

from .consts import _RENAMER_SUPPORTED_EXTRACT_FIELD, _FIELD_EXTRACT_FROM_TAGS
from lib.organizer.consts import ALLOWED_READ_AUDIO_FORMAT
from lib.tags.registery_consts import TYPE_TO_READER


class FieldExtractor:
    """字段提取器，从多种来源提取重命名字段。"""

    @staticmethod
    def extract_from_folder_name(folder_name: str, extract_pattern: str, extract_groups) -> dict[str, str]:
        fields: dict[str, str] = {k: "" for k in _RENAMER_SUPPORTED_EXTRACT_FIELD}

        match = re.match(extract_pattern, folder_name)
        if not match:
            return fields

        # 按 EXTRACT_GROUPS 将捕获组映射为字段
        for i, group_name in enumerate(extract_groups):
            if i + 1 <= len(match.groups()):
                val = match.group(i + 1).strip()
                fields[group_name] = val

        return fields

    @staticmethod
    def extract_from_audio_tags(folder_path: Path) -> dict[str, str]:
        """
        从音频文件标签中提取 date 和 album 字段。

        Args:
            folder_path: 文件夹路径

        Returns:
            包含 date 和 album 的字段字典
        """
        fields: dict[str, str] = {k: "" for k in _FIELD_EXTRACT_FROM_TAGS}

        # 遍历文件夹中的音频文件，读取第一个有效的标签
        for p in folder_path.rglob("*"):
            if not p.is_file() or p.suffix not in ALLOWED_READ_AUDIO_FORMAT:
                continue

            src_audio = mutagen.File(str(p))
            reader_cls = TYPE_TO_READER.get(type(src_audio))
            standard_tag = reader_cls(p).internal
            if standard_tag:
                date_values: set[str] | None= standard_tag.get("DATE", set())
                year_values: set[str] | None= standard_tag.get("YEAR", set())
                catno_values: set[str] | None= standard_tag.get("CATNO", set())

                if date_values:
                    fields["DATE"] = sorted(date_values, key=len, reverse=True)[0].replace('-', '.')
                else:
                    fields["DATE"] = sorted(year_values, key=len, reverse=True)[0].replace('-', '.')
                fields["ALBUM"] = next(iter(standard_tag['ALBUM']))

                fields["CATALOGNUMBER"] = catno_values if catno_values else "N/A"

                # 如果标签中还有 artist 信息，也提取
                if standard_tag.get("ARTIST", None):
                    fields["ALBUMARTIST"] = '-'.join(standard_tag.get("ARTIST"))
                
                # 找到第一个有效标签就返回
                break

        return fields

    @staticmethod
    def format_fields_to_name(fields: dict[str, str], output_template: Template) -> Optional[str]:
        try:
            # 使用 format 方法填充模板
            return output_template.render(**fields)
        except KeyError as e:
            missing_var = str(e).strip("'")
            print(f"  模板中引用了未知变量 '{missing_var}'，跳过")
            print(f"  提示：请检查 config.toml 中的 output_template")
            print(f"  当前字段值: {', '.join(k for k, v in fields.items() if v)}")
            return None
