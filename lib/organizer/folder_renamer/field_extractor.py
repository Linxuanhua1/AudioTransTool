import re, mutagen
from datetime import datetime
from pathlib import Path
from typing import Optional
from jinja2 import Template

from lib.constants import (
    RENAMER_SUPPORTED_EXTRACT_FIELD,
    ALLOWED_READ_AUDIO_FORMAT,
    TYPE_TO_READER,
)


class FieldExtractor:
    """字段提取器，从多种来源提取重命名字段。"""

    @staticmethod
    def extract_from_folder_name(folder_name: str, extract_pattern: str, extract_groups) -> dict[str, str]:
        fields: dict[str, str] = {k: "" for k in RENAMER_SUPPORTED_EXTRACT_FIELD}

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
    def extract_from_audio_tags(folder_path: Path) -> dict[str, set]:
        """
        从音频文件标签中提取 date 和 album 字段。

        Args:
            folder_path: 文件夹路径

        Returns:
            包含 date 和 album 的字段字典
        """
        for p in folder_path.rglob("*"):
            if not p.is_file() or p.suffix not in ALLOWED_READ_AUDIO_FORMAT:
                continue

            src_audio = mutagen.File(str(p))
            reader_cls = TYPE_TO_READER.get(type(src_audio))
            standard_tag = reader_cls(p).internal
            date_values: set[str] | None = standard_tag.get("DATE", set())
            year_values: set[str] | None = standard_tag.get("YEAR", set())
            time_values = [str(i) for i in (date_values | year_values)]
            standard_tag = {k: next(iter(v)) for k, v in standard_tag.items() if v}
            if time_values:
                tmp_v = FieldExtractor.normalize_date(sorted(time_values, key=len, reverse=True)[0])
                standard_tag["DATE"] = tmp_v
                standard_tag.pop("YEAR", None)

            return standard_tag

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

    def normalize_date(text: str) -> str | None:
        s = text.strip()

        # 去掉末尾括号内容，支持中英文括号
        s = re.sub(r"\s*[（(].*?[）)]\s*$", "", s)

        # 去掉末尾活动标记，例如 C70 / Comic
        s = re.sub(r"\s+[A-Za-z]+\d*$", "", s)

        # 1) 年份 yyyy
        m = re.fullmatch(r"(\d{4})", s)
        if m:
            return m.group(1)

        # 2) 年月 yyyy.mm / yyyy-mm / yyyy/mm
        m = re.fullmatch(r"(\d{4})[./-](\d{1,2})", s)
        if m:
            year, month = map(int, m.groups())
            if 1 <= month <= 12:
                return f"{year:04d}.{month:02d}"
            return None

        # 3) 年月日 yyyy/m/d 或 yyyy-m-d
        m = re.fullmatch(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", s)
        if m:
            year, month, day = map(int, m.groups())
            try:
                return datetime(year, month, day).strftime("%Y.%m.%d")
            except ValueError:
                return None

        # 4) 年月日 yyyymmdd
        m = re.fullmatch(r"(\d{4})(\d{2})(\d{2})", s)
        if m:
            year, month, day = map(int, m.groups())
            try:
                return datetime(year, month, day).strftime("%Y.%m.%d")
            except ValueError:
                return None

        # 5) 年月日 yymmdd
        m = re.fullmatch(r"(\d{2})(\d{2})(\d{2})", s)
        if m:
            yy, month, day = map(int, m.groups())
            year = 2000 + yy if yy <= 69 else 1900 + yy
            try:
                return datetime(year, month, day).strftime("%Y.%m.%d")
            except ValueError:
                return None

        return None