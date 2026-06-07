"""
Source 匹配规则解析 API。

把原先写死在 ``AudioSource.detect_source`` 里的来源判定逻辑，改为由
``config.toml`` 的 ``[rename.match_rules]`` 驱动。规则是一个有序列表，
逐条匹配，命中即返回；全部未命中时返回 ``source_fallback``。

config.toml 中的写法（数组表，顺序即优先级）::

    [rename]
    source_fallback = "WEB"          # 所有规则都未命中时的兜底来源

    [[rename.match_rules]]
    field  = "QBZ_TID"               # 要检测的标准标签字段；特殊值 "EXT" 表示音频扩展名
    match  = "exists"                # exists / contains / equals / regex
    source = "Qobuz"                 # 命中后返回的来源；省略则透传字段原值

    [[rename.match_rules]]
    field  = "URL"
    match  = "contains"
    map    = { tidal = "Tidal", amazon = "Amazon" }   # 「子串 -> 来源」映射

字段说明：
    field          要检测的标准标签字段名（如 QBZ_TID / URL / COMMENT / SOURCE）；
                   特殊值 "EXT" 表示文件夹内音频文件的扩展名集合（如 .dsf）。
    match          匹配方式：
                       exists   - 字段有值即命中
                       contains - 字段值包含某子串
                       equals   - 字段值等于某值
                       regex    - 字段值匹配正则
    value          contains/equals/regex 的匹配目标，可为字符串或字符串列表。
    map            value 的替代写法，{ 目标 = 来源 } 的内联表，按顺序匹配，
                   命中哪个目标就返回对应来源（等价于多条不同 source 的规则）。
    source         命中后返回的来源标签。省略时透传字段原值（用于 SOURCE 透传）。
    case_sensitive 是否区分大小写，默认 false。
"""

import re
import logging
from typing import Optional


logger = logging.getLogger("musicbox.services.media_ops.folder_renamer.match_rules")


# 扩展名伪字段：匹配文件夹内音频文件的扩展名集合
EXT_FIELD = "EXT"

VALID_MATCH = ("exists", "contains", "equals", "regex")


class SourceMatcher:
    """解析并执行 [rename.match_rules] 规则，从标签 / 扩展名推断 source。"""

    def __init__(self, rules: list[dict], fallback: str):
        self.fallback = fallback
        self.rules = [self._compile(rule, i) for i, rule in enumerate(rules)]

    # ------------------------------------------------------------------ #
    # 构造
    # ------------------------------------------------------------------ #

    @classmethod
    def from_config(cls, rename_config: dict) -> "SourceMatcher":
        """从 config.toml 的 [rename] 配置段构造匹配器（match_rules / source_fallback 必须已配置）。"""
        rules = rename_config["match_rules"]
        fallback = rename_config["source_fallback"]
        return cls(rules, fallback)

    # ------------------------------------------------------------------ #
    # 规则编译 / 校验
    # ------------------------------------------------------------------ #

    def _compile(self, rule: dict, idx: int) -> dict:
        """校验单条规则并预处理（小写化 / 预编译正则）。"""
        where = f"[rename.match_rules] 第 {idx + 1} 条规则"

        if not isinstance(rule, dict):
            raise ValueError(f"{where} 必须是表(table)，实际为 {type(rule).__name__}")

        field = rule.get("field")
        if not isinstance(field, str) or not field:
            raise ValueError(f"{where} 缺少有效的 field")

        match = rule.get("match")
        if match not in VALID_MATCH:
            raise ValueError(f"{where} 的 match={match!r} 无效，可选: {list(VALID_MATCH)}")

        case_sensitive = bool(rule.get("case_sensitive", False))
        compiled = {"field": field, "match": match, "case_sensitive": case_sensitive}

        # exists：不需要 value/map，source 可省略（省略=透传字段值）
        if match == "exists":
            if "value" in rule or "map" in rule:
                raise ValueError(f"{where} 的 match='exists' 不应再提供 value 或 map")
            compiled["pairs"] = [(None, rule.get("source"))]
            return compiled

        # contains/equals/regex：value 与 map 二选一
        has_value, has_map = "value" in rule, "map" in rule
        if has_value == has_map:
            raise ValueError(f"{where} 的 match='{match}' 需要且只能提供 value 或 map 其一")

        raw_pairs: list[tuple[str, Optional[str]]] = []
        if has_map:
            mapping = rule["map"]
            if not isinstance(mapping, dict) or not mapping:
                raise ValueError(f"{where} 的 map 必须是非空内联表")
            raw_pairs = list(mapping.items())
        else:
            value = rule["value"]
            values = value if isinstance(value, list) else [value]
            source = rule.get("source")           # 省略=透传字段值
            raw_pairs = [(v, source) for v in values]

        # 预处理 needle
        compiled["pairs"] = [
            self._prepare_needle(needle, label, match, case_sensitive, where)
            for needle, label in raw_pairs
        ]
        return compiled

    @staticmethod
    def _prepare_needle(needle, label, match: str, case_sensitive: bool, where: str):
        if not isinstance(needle, str):
            raise ValueError(f"{where} 的匹配目标必须是字符串，实际为 {type(needle).__name__}")
        if match == "regex":
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                return re.compile(needle, flags), label
            except re.error as e:
                raise ValueError(f"{where} 的正则 {needle!r} 编译失败: {e}")
        # contains / equals：不区分大小写时预先小写化 needle
        return (needle if case_sensitive else needle.lower()), label

    # ------------------------------------------------------------------ #
    # 执行
    # ------------------------------------------------------------------ #

    def match(self, tags: Optional[dict], exts: Optional[set]) -> str:
        """按顺序应用规则，返回命中的 source；都未命中返回 fallback。

        Args:
            tags: 标准化后的标签字典（字段名 -> 字符串值）。
            exts: 文件夹内音频文件的扩展名集合（用于 field='EXT' 的规则）。
        """
        tags = tags or {}
        exts = {e.lower() for e in (exts or set()) if e}
        for rule in self.rules:
            result = self._apply(rule, tags, exts)
            if result is not None:
                return result
        return self.fallback

    def _apply(self, rule: dict, tags: dict, exts: set) -> Optional[str]:
        # 取出待匹配的主体（subject）列表
        if rule["field"] == EXT_FIELD:
            subjects = list(exts)
        else:
            value = tags.get(rule["field"])
            subjects = [value] if value else []     # 与原逻辑一致：仅在字段有值时参与匹配
        if not subjects:
            return None

        match, case_sensitive = rule["match"], rule["case_sensitive"]

        if match == "exists":
            label = rule["pairs"][0][1]
            return label if label is not None else subjects[0]

        for needle, label in rule["pairs"]:
            for subject in subjects:
                if self._hit(match, needle, subject, case_sensitive):
                    return label if label is not None else subject
        return None

    @staticmethod
    def _hit(match: str, needle, subject: str, case_sensitive: bool) -> bool:
        if match == "regex":
            return needle.search(subject) is not None
        cmp = subject if case_sensitive else subject.lower()
        if match == "contains":
            return needle in cmp
        return needle == cmp        # equals

    # ------------------------------------------------------------------ #
    # 展示（供配置确认时打印）
    # ------------------------------------------------------------------ #

    def describe(self) -> list[str]:
        """生成人类可读的规则描述，用于配置确认环节打印。"""
        lines: list[str] = []
        for i, rule in enumerate(self.rules, 1):
            field, match = rule["field"], rule["match"]
            if match == "exists":
                label = rule["pairs"][0][1]
                target = f"-> {label}" if label is not None else "-> (透传字段值)"
                lines.append(f"  {i}. {field} 存在即命中 {target}")
            else:
                targets = ", ".join(
                    f"{getattr(n, 'pattern', n)}=>{lbl if lbl is not None else '(透传)'}"
                    for n, lbl in rule["pairs"]
                )
                lines.append(f"  {i}. {field} {match}: {targets}")
        lines.append(f"  *. 兜底: -> {self.fallback}")
        return lines
