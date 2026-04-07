"""
CatNoWriter
===========
从文件夹名提取光盘编号，写入文件夹下所有音频文件的标签，
并按规则处理 log / txt 文件。

提取正则和变量映射来自 config.toml [rename] 中的：
  catno_extract_pattern — 正则表达式（第一个捕获组为编号）
  catno_extract_group   — 捕获组对应的字段名（应为 catalognumber）
"""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path

from lib.common.path_manager import PathManager
from lib.organizer.audio_tag_reader import AudioTagReader
from lib.organizer.catno_helper import CatNoHelper


# --------------------------------------------------------------------------- #
# 配置加载
# --------------------------------------------------------------------------- #

with open("config.toml", "rb") as _f:
    _cfg = tomllib.load(_f)

_rename_cfg = _cfg.get("rename", {})

CATNO_PATTERN: str = _rename_cfg.get("catno_extract_pattern", r"\[.*?\] .*? \[(.*?)\]")
CATNO_GROUP: str   = _rename_cfg.get("catno_extract_group", "catalognumber")

# 是否已确认过 pattern
_pattern_confirmed = False


# --------------------------------------------------------------------------- #
# CatNoWriter
# --------------------------------------------------------------------------- #

class CatNoWriter:
    """
    光盘编号写入操作类。

    用法
    ----
    writer = CatNoWriter()
    writer.write_from_folder_name()   # 交互式循环
    """

    # ------------------------------------------------------------------ #
    # Pattern 确认
    # ------------------------------------------------------------------ #

    @staticmethod
    def _confirm_pattern() -> None:
        """首次运行时显示当前 pattern 让用户确认。"""
        global _pattern_confirmed
        if _pattern_confirmed:
            return

        print("\n当前编号提取配置（来自 config.toml [rename]）：")
        print(f"  提取正则:   {CATNO_PATTERN}")
        print(f"  提取变量:   {CATNO_GROUP}")
        choice = input("是否使用此配置？(y/n，直接回车=y): ").strip().lower()
        if choice and choice != "y":
            print("请修改 config.toml [rename] 后重新运行")
            return
        _pattern_confirmed = True

    # ------------------------------------------------------------------ #
    # 公开入口
    # ------------------------------------------------------------------ #

    def write_from_folder_name(self) -> None:
        """交互式循环：提取文件夹名中的光盘编号并写入音频标签。"""
        self._confirm_pattern()
        if not _pattern_confirmed:
            return

        print("提示输入路径的时候输入 # 返回主菜单")
        while True:
            folder_path = PathManager.check_input_folder_path()
            if folder_path == "#":
                print("返回主菜单")
                return

            print("-" * 50)
            self._process_parent_folder(folder_path, CATNO_PATTERN)

    # ------------------------------------------------------------------ #
    # 批量处理父文件夹
    # ------------------------------------------------------------------ #

    def _process_parent_folder(self, parent: str, pattern: str) -> None:
        for folder in os.listdir(parent):
            base_path = os.path.join(parent, folder)
            if not os.path.isdir(base_path):
                continue

            match = re.match(pattern, folder)
            if not match:
                continue

            raw_catno = match.group(1)
            catno = CatNoHelper.unfold(raw_catno) if ("~" in raw_catno or "～" in raw_catno) else raw_catno

            print(f"为 {base_path} 下的音频写入光盘编号")
            self._process_album_folder(base_path, catno)
            print("完成写入")
            print("-" * 50)

    # ------------------------------------------------------------------ #
    # 处理单个专辑文件夹
    # ------------------------------------------------------------------ #

    def _process_album_folder(self, base_path: str, catno: str | list[str]) -> None:
        log_files: list[str] = []

        for file in os.listdir(base_path):
            file_path = Path(os.path.join(base_path, file))
            ext = file.lower()

            if ext.endswith((".flac", ".ogg", ".mp3", ".m4a", ".wav", ".dsf")):
                self._write_audio(file_path, catno)
            elif ext.endswith(".log"):
                log_files.append(str(file_path))

        display_catno = CatNoHelper.fold(catno) if isinstance(catno, list) else catno
        self._handle_log_or_txt(base_path, log_files, display_catno)

    # ------------------------------------------------------------------ #
    # 写入单个音频文件
    # ------------------------------------------------------------------ #

    @staticmethod
    def _write_audio(file_path: Path, catno: str | list[str]) -> None:
        AudioTagReader.write_catno(file_path, catno)

    # ------------------------------------------------------------------ #
    # Log / Txt 处理
    # ------------------------------------------------------------------ #

    @staticmethod
    def _handle_log_or_txt(base_path: str, log_files: list[str], display_catno: str) -> None:
        if len(log_files) == 1:
            CatNoWriter._rename_single_log(base_path, log_files[0], display_catno)
        elif len(log_files) > 1:
            print("文件夹下有多个 log 文件，不进行重命名，请手动复核")
        else:
            CatNoWriter._ensure_txt(base_path, display_catno)

    @staticmethod
    def _rename_single_log(base_path: str, log_path: str, display_catno: str) -> None:
        log_file = os.path.basename(log_path)
        expected = f"{display_catno}.log"
        if log_file != expected:
            os.rename(log_path, os.path.join(base_path, expected))
            print(f"将 {log_file} 改名为 {expected}")
        else:
            print(f"{log_file} 无需改名")

    @staticmethod
    def _ensure_txt(base_path: str, display_catno: str) -> None:
        txt_path = os.path.join(base_path, f"{display_catno}.txt")
        if not os.path.exists(txt_path):
            Path(txt_path).write_text("")
            print(f"因文件夹下没有 log 文件，已创建 {display_catno}.txt")
        else:
            print(f"当前路径下已有 {display_catno}.txt")
