from pathlib import Path
from typing import Any
import mutagen, re

from lib.constants import ALLOWED_READ_AUDIO_FORMAT, TYPE_TO_READER, TYPE_TO_WRITER
from lib.common import PathManager


class TagSeparator:
    def __init__(self, config):
        self.seps = config['rename']['seps']
        self.sep_fields = config['rename']['sep_fields']

    # ------------------------------------------------------------------ #
    # 公开入口
    # ------------------------------------------------------------------ #

    def separate_tag(self) -> None:
        """交互式循环：选择文件夹后对其下所有音频做标签分割。"""
        print("询问输入文件夹的时候，输入 # 返回主菜单")
        while True:
            folder_p = PathManager.check_input_folder_path()
            if folder_p == "#":
                print("返回主菜单")
                return
            self._process_directory(Path(folder_p))

    # ------------------------------------------------------------------ #
    # 目录处理
    # ------------------------------------------------------------------ #

    def _process_directory(self, folder_p: Path) -> None:
        """递归处理目录，处理完后询问是否撤回。"""
        pending_seps: list[tuple] = []

        for p in folder_p.rglob("*"):
            if p.suffix.lower() not in ALLOWED_READ_AUDIO_FORMAT:
                continue
            pending_sep = self._collect_sep_audio_tags(p)
            if pending_sep:
                pending_seps.append(pending_sep)

        if pending_seps:
            self._execuate(pending_seps)

    # ------------------------------------------------------------------ #
    # 单文件处理
    # ------------------------------------------------------------------ #

    def _collect_sep_audio_tags(self, file_p: Path) -> tuple[Path, Any, dict[str, set], dict[str, set]]:
        audio = mutagen.File(str(file_p))
        if audio.tags is None:
            return None
        audio_type = type(audio)
        reader_cls = TYPE_TO_READER.get(audio_type)
        internal = reader_cls(file_p).internal

        pending_sep_tags: dict[str, set] = {field: internal.get(field, set()) for field in self.sep_fields}

        sep_tags: dict[str, set] = {field: self.separate_text(values) for field, values in pending_sep_tags.items()}

        if pending_sep_tags == sep_tags:
            print(f"{file_p} 无需修改")
            return None

        pending_sep = (file_p, audio_type, pending_sep_tags, sep_tags)

        return pending_sep

    # ------------------------------------------------------------------ #
    # 撤回
    # ------------------------------------------------------------------ #

    @staticmethod
    def _execuate(pending_seps) -> None:
        for file_p, audio_type, pending_sep_tags, sep_tags in pending_seps:

            print(
                f"修改前 [{file_p}]:\n"
                + "\n".join(f"  {key}: {value}" for key, value in pending_sep_tags.items())
            )

            writer_cls = TYPE_TO_WRITER.get(audio_type)
            writer_cls(file_p).write(sep_tags)
            print(
                f"修改后 [{file_p}]:\n"
                + "\n".join(f"  {key}: {value}" for key, value in sep_tags.items())
            )

        if input("是否撤回修改？(y/n):（回车为n） ").strip().lower() == "y":
            for file_p, audio_type, pending_sep_tags, sep_tags in pending_seps:
                writer_cls = TYPE_TO_WRITER.get(audio_type)
                writer_cls(file_p).write(pending_sep_tags)
                print(f"已撤回 {file_p} 的修改")


    def separate_text(self, values: set[str]) -> set[str]:
        """
        当列表仅有单个值时，尝试按配置的分隔符拆分为多个值。
        多值列表直接原样返回。
        """
        if len(values) != 1:
            return values
        pattern = "|".join(re.escape(sep) for sep in self.seps)

        return {v.strip() for v in re.split(pattern, next(iter(values))) if v.strip()}