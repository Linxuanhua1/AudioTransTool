"""
CatNoHelper
===========
与光盘编号、日期格式化和标签文本分割相关的纯函数工具集。
原 utils.py 中的函数和 folder.py 中的 _normalize_date 统一收归于此。
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import List


# --------------------------------------------------------------------------- #
# 配置加载
# --------------------------------------------------------------------------- #

with open("config.toml", "rb") as _f:
    _config = tomllib.load(_f)

SEPARATORS: list[str] = _config["separators"]


# --------------------------------------------------------------------------- #
# CatNoHelper
# --------------------------------------------------------------------------- #

class CatNoHelper:
    """
    无状态工具类，所有方法为静态方法。

    光盘编号格式示例
    ---------------
    折叠形式：ABCD-15599~01   （表示 ABCD-15599 到 ABCD-15601）
    展开列表：["ABCD-15599", "ABCD-15600", "ABCD-15601"]
    """

    # ------------------------------------------------------------------ #
    # 光盘编号展开 / 折叠
    # ------------------------------------------------------------------ #

    @staticmethod
    def unfold(catno: str) -> list[str]:
        """
        将折叠的编号范围展开为列表。
        例：ABCD-15599~01 → ["ABCD-15599", "ABCD-15600", "ABCD-15601"]
        """
        match = re.match(r"([A-Z]+-\d+)[~～](\d+)", catno)
        if not match:
            return [catno]

        prefix_full = match.group(1)           # "ABCD-15599"
        prefix      = prefix_full.split("-")[0] # "ABCD"
        start_str   = prefix_full.split("-")[1] # "15599"
        end_suffix  = match.group(2)            # "01"

        digit_len = len(start_str)
        start_num = int(start_str)

        # 补全结束编号
        end_full = int(start_str[: digit_len - len(end_suffix)] + end_suffix)
        if end_full < start_num:
            end_full += 10 ** len(end_suffix)

        return [
            f"{prefix}-{str(i).zfill(digit_len)}"
            for i in range(start_num, end_full + 1)
        ]

    @staticmethod
    def fold(nums: list[str]) -> str:
        """
        将连续编号列表折叠回紧凑字符串。
        例：["ABCD-15599", "ABCD-15600", "ABCD-15601"] → "ABCD-15599~01"
        """
        prefix_match = re.match(r"([A-Z]+)-(\d+)", nums[0])
        prefix    = prefix_match.group(1)
        start_str = prefix_match.group(2)
        digit_len = len(start_str)

        end_str = re.match(r"[A-Z]+-(\d+)", nums[-1]).group(1)

        # 找最后不同的部分作为后缀
        suffix = "0"
        for i in range(digit_len):
            if start_str[i] != end_str[i]:
                suffix = end_str[i:]
                break

        return f"{prefix}-{start_str}~{suffix}"

    # ------------------------------------------------------------------ #
    # 日期格式化
    # ------------------------------------------------------------------ #

    @staticmethod
    def normalize_date(orig_date: str) -> str:
        """
        将 6 位、8 位或已含点的日期统一为 YYYY.MM.DD 格式。

        例：
            "230415"  → "2023.04.15"
            "20230415"→ "2023.04.15"
            "2023.04.15" → "2023.04.15"（原样返回）
        """
        if "." in orig_date:
            return orig_date
        if len(orig_date) == 6:
            prefix = "19" if int(orig_date[:2]) > 50 else "20"
            return f"{prefix}{orig_date[:2]}.{orig_date[2:4]}.{orig_date[4:]}"
        # 8 位
        return f"{orig_date[:4]}.{orig_date[4:6]}.{orig_date[6:]}"

    # ------------------------------------------------------------------ #
    # 文本分割
    # ------------------------------------------------------------------ #

    @staticmethod
    def separate_text(values: List[str]) -> List[str]:
        """
        当列表仅有单个值时，尝试按配置的分隔符拆分为多个值。
        多值列表直接原样返回。
        """
        if len(values) != 1:
            return values
        pattern = "|".join(re.escape(sep) for sep in SEPARATORS)
        return [v.strip() for v in re.split(pattern, values[0]) if v.strip()]

    # ------------------------------------------------------------------ #
    # 正则选择器（CLI 辅助）
    # ------------------------------------------------------------------ #

    @staticmethod
    def choose_pattern(prompt_lines: List[str], patterns: dict) -> str:
        """
        交互式正则表达式选择器。
        patterns 格式：{'1': r'...', '2': r'...'}，末尾自动追加"自定义"选项。
        """
        while True:
            choice = input("\n".join(prompt_lines) + "\n请输入数字：")
            if choice in patterns:
                return patterns[choice]
            if choice == str(len(patterns) + 1):
                return input("请输入正则表达式：")
            print("输入不正确，请重新输入")
