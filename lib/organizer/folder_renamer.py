"""
FolderRenamer
=============
文件夹重命名操作类。

重命名逻辑基于 config.toml [rename] 中的配置：
  - extract_pattern / extract_groups: 从文件夹名提取字段的正则和变量映射
  - output_template: 输出命名模板，使用 {变量名} 引用字段

支持的变量：
  date, album, catalognumber, artist, audio_source,
  BitDepth, SampleRate, folder_content
"""

import re
import tomllib
from pathlib import Path

from lib.common.path_manager import PathManager
from lib.organizer.folder_scanner import FolderScanner
from lib.organizer.audio_tag_reader import AudioTagReader
from lib.organizer.catno_helper import CatNoHelper


# --------------------------------------------------------------------------- #
# 配置加载
# --------------------------------------------------------------------------- #

with open("config.toml", "rb") as _f:
    _cfg = tomllib.load(_f)

_rename_cfg = _cfg.get("rename", {})

# 从文件夹名提取信息的正则和变量映射
EXTRACT_PATTERN: str       = _rename_cfg.get("extract_pattern", r"(.*) \[.*?\] (.*)")
EXTRACT_GROUPS: list[str]  = _rename_cfg.get("extract_groups", ["date", "album"])

# 输出命名模板
OUTPUT_TEMPLATE: str       = _rename_cfg.get("output_template",
    "[{date}][{audio_source}][{album}][{BitDepth}{SampleRate}]{folder_content}")

# 所有支持的字段名（用于提示和校验）
ALL_FIELDS = [
    "BitDepth", "SampleRate", "folder_content", "catalognumber",
    "date", "audio_source", "album", "artist",
]

# 匹配 D1, D2, Disc1, Disc 1, disc02 等碟片子目录名
_DISC_DIR_RE = re.compile(r"^(?:D|Disc|disc|DISC)\s*\d+$", re.IGNORECASE)

# 是否已确认过 pattern（运行期间只提示一次）
_pattern_confirmed = False


# --------------------------------------------------------------------------- #
# FolderRenamer
# --------------------------------------------------------------------------- #

class FolderRenamer:
    """
    文件夹重命名操作类。

    用法
    ----
    renamer = FolderRenamer()
    renamer.rename_from_name()   # 基于文件夹名正则提取 → 重命名
    renamer.rename_from_tag()    # 基于音频标签 → 重命名
    """

    def __init__(self) -> None:
        self._scanner = FolderScanner()

    # ------------------------------------------------------------------ #
    # 工具方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_disc_dir(name: str) -> bool:
        return bool(_DISC_DIR_RE.match(name.strip()))

    @staticmethod
    def _find_album_dir(audio_file: Path, input_root: Path) -> Path | None:
        parent = audio_file.parent
        if parent == input_root:
            return None
        if FolderRenamer._is_disc_dir(parent.name) and parent.parent != input_root:
            return parent.parent
        return parent

    @staticmethod
    def _collect_album_dirs(input_root: Path) -> list[Path]:
        seen: set[Path] = set()
        result: list[Path] = []
        exts = AudioTagReader.supported_extensions()
        for f in input_root.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in exts:
                continue
            album_dir = FolderRenamer._find_album_dir(f, input_root)
            if album_dir and album_dir not in seen:
                seen.add(album_dir)
                result.append(album_dir)
        return sorted(result)

    # ------------------------------------------------------------------ #
    # Pattern 确认（首次运行时提示一次）
    # ------------------------------------------------------------------ #

    @staticmethod
    def _confirm_pattern() -> None:
        """首次运行时显示当前 pattern 让用户确认，后续不再提示。"""
        global _pattern_confirmed
        if _pattern_confirmed:
            return

        print("\n当前重命名配置（来自 config.toml [rename]）：")
        print(f"  提取正则:   {EXTRACT_PATTERN}")
        print(f"  提取变量:   {EXTRACT_GROUPS}")
        print(f"  输出模板:   {OUTPUT_TEMPLATE}")
        choice = input("是否使用此配置？(y/n，直接回车=y): ").strip().lower()
        if choice and choice != "y":
            print("请修改 config.toml [rename] 后重新运行")
            return
        _pattern_confirmed = True

    # ------------------------------------------------------------------ #
    # 构建字段字典（从文件夹扫描结果填充 audio_source / BitDepth 等）
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_fields_from_scan(result) -> dict[str, str]:
        """从 FolderScanner.ScanResult 构建通用字段字典。"""
        depth, rate = result.best_info
        return {
            "audio_source": result.label,
            "BitDepth": depth if depth != "N/A" else "",
            "SampleRate": rate if rate != "N/A" else "",
            "folder_content": result.suffix,
        }

    @staticmethod
    def _format_name(fields: dict[str, str]) -> str:
        """用 OUTPUT_TEMPLATE 和字段字典生成新名称。"""
        try:
            return OUTPUT_TEMPLATE.format(**fields)
        except KeyError as e:
            print(f"  ⚠ 模板中引用了未知变量 {e}，跳过")
            return ""

    # ------------------------------------------------------------------ #
    # 公开入口
    # ------------------------------------------------------------------ #

    def rename_from_name(self) -> None:
        """根据文件夹名正则匹配结果重命名。输入 # 返回。"""
        self._confirm_pattern()
        if not _pattern_confirmed:
            return

        print("提示输入路径的时候输入 # 返回主菜单")
        while True:
            folder_path = PathManager.check_input_folder_path()
            if folder_path == "#":
                print("返回主菜单")
                return
            self._batch_rename_from_name(Path(folder_path))

    def rename_from_tag(self) -> None:
        """从音频标签读取日期和专辑名后重命名。输入 # 返回。"""
        self._confirm_pattern()
        if not _pattern_confirmed:
            return

        print("提示输入路径的时候输入 # 返回主菜单")
        while True:
            folder_path = PathManager.check_input_folder_path()
            if folder_path == "#":
                print("返回主菜单")
                return
            self._batch_rename_from_tag(Path(folder_path))

    # ------------------------------------------------------------------ #
    # 批量处理
    # ------------------------------------------------------------------ #

    def _batch_rename_from_name(self, input_root: Path) -> None:
        """
        从文件夹名中按 EXTRACT_PATTERN 提取字段，
        再结合 FolderScanner 扫描结果，用 OUTPUT_TEMPLATE 生成新名称。
        """
        album_dirs = self._collect_album_dirs(input_root)
        pending: list[tuple[Path, Path]] = []

        for p in album_dirs:
            match = re.match(EXTRACT_PATTERN, p.name)
            if not match:
                continue

            # 按 EXTRACT_GROUPS 将捕获组映射为字段
            fields: dict[str, str] = {k: "" for k in ALL_FIELDS}
            for i, group_name in enumerate(EXTRACT_GROUPS):
                if i + 1 <= len(match.groups()):
                    val = match.group(i + 1).strip()
                    # 日期字段自动标准化
                    if group_name == "date":
                        val = CatNoHelper.normalize_date(val)
                    fields[group_name] = val

            # 用 FolderScanner 补充 audio_source / BitDepth / SampleRate / folder_content
            result = FolderScanner.analyze(p)
            scan_fields = self._build_fields_from_scan(result)
            for k, v in scan_fields.items():
                if not fields.get(k):
                    fields[k] = v

            new_name = self._format_name(fields)
            if not new_name:
                continue
            new_p = p.parent / new_name
            if new_p != p:
                pending.append((p, new_p))

        self._confirm_and_rename(pending)

    def _batch_rename_from_tag(self, input_root: Path) -> None:
        """从音频标签读取 date / album，结合扫描结果重命名。"""
        album_dirs = self._collect_album_dirs(input_root)
        pending: list[tuple[Path, Path]] = []

        for p in album_dirs:
            result = FolderScanner.analyze(p)
            date, album = self._read_date_and_album(p)

            if not (date and album):
                continue

            fields: dict[str, str] = {k: "" for k in ALL_FIELDS}
            fields["date"] = date
            fields["album"] = album

            scan_fields = self._build_fields_from_scan(result)
            for k, v in scan_fields.items():
                if not fields.get(k):
                    fields[k] = v

            new_name = self._format_name(fields)
            if not new_name:
                continue
            new_p = p.parent / new_name
            if new_p != p:
                pending.append((p, new_p))

        self._confirm_and_rename(pending)

    # ------------------------------------------------------------------ #
    # 确认并执行
    # ------------------------------------------------------------------ #

    @staticmethod
    def _confirm_and_rename(pending: list[tuple[Path, Path]]) -> None:
        if not pending:
            print("没有需要重命名的文件夹")
            return

        print(f"\n即将重命名 {len(pending)} 个文件夹：")
        print("-" * 60)
        for old_p, new_p in pending:
            print(f"  {old_p.name}")
            print(f"  → {new_p.name}")
            print()

        choice = input("是否执行重命名？(y/n): ").strip().lower()
        if choice != "y":
            print("已取消")
            return

        for old_p, new_p in pending:
            old_p.rename(new_p)
            print(f"已重命名：{old_p.name} → {new_p.name}")
        print("全部完成")

    # ------------------------------------------------------------------ #
    # 从音频读取日期和专辑名
    # ------------------------------------------------------------------ #

    @staticmethod
    def _read_date_and_album(folder_p: Path) -> tuple[str, str]:
        for p in folder_p.rglob("*"):
            if not p.is_file():
                continue
            bundle = AudioTagReader.read(p)
            if bundle and bundle.date and bundle.album:
                return bundle.date, PathManager.safe_filename(bundle.album)
        return "", ""
