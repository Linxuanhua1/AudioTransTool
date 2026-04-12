from pathlib import Path
from typing import Callable
from jinja2 import Template

from lib.common import PathManager
from .. import FolderScanner, FolderUtils
from . import FieldExtractor, PatternValidator


class FolderRenamer:
    def __init__(self, config: dict):
        self.config: dict = config['rename']
        self.extractor = FieldExtractor()
        self.folder_utils = FolderUtils()
        self.extract_pattern: str = self.config['extract_pattern']
        self.extract_groups: str = self.config['extract_groups']
        self.output_template: Template = Template(self.config['output_template'])
        self.booklet_threshold: int = self.config['booklet_threshold']
        self.folder_content_template: Template = Template(self.config['folder_content_template'])
        self.disc_f_pattern: str = self.config['disc_f_pattern']

    # ------------------------------------------------------------------ #
    # 公开入口
    # ------------------------------------------------------------------ #

    def _run_batch_rename(self, rename_func: Callable[[Path], None]) -> None:
        if not PatternValidator.confirm_pattern(self.config):
            return

        print("\n提示输入路径的时候输入 # 返回主菜单")

        while True:
            folder_p = PathManager.check_input_folder_path()
            if folder_p == "#":
                print("返回主菜单")
                return

            rename_func(folder_p)

    def rename_from_name(self) -> None:
        self._run_batch_rename(self._batch_rename_from_name)

    def rename_from_tag(self) -> None:
        self._run_batch_rename(self._batch_rename_from_tag)

    # ------------------------------------------------------------------ #
    # 批量处理逻辑
    # ------------------------------------------------------------------ #

    def _batch_rename_from_name(self, input_root: Path) -> None:
        album_dirs = FolderUtils.collect_album_dirs(input_root, self.disc_f_pattern)

        pending: list[tuple[Path, Path]] = []
        for folder_p in album_dirs:
            # 1. 从文件夹名提取字段
            name_fields = FieldExtractor.extract_from_folder_name(folder_p.name, self.extract_pattern, self.extract_groups)
            # 如果正则没有匹配到，跳过
            if not any(name_fields.values()):
                continue

            # 2. 生成新名称
            new_name = FieldExtractor.format_fields_to_name(name_fields, self.output_template)
            if not new_name:
                continue
            # 3. 添加到重命名操作列表
            new_path = folder_p.parent / PathManager.safe_filename(new_name)
            pending.append((folder_p, new_path))
        self._execute(pending)

    def _batch_rename_from_tag(self, input_root: Path) -> None:
        album_dirs = FolderUtils.collect_album_dirs(input_root, self.disc_f_pattern)
        pending: list[tuple[Path, Path]] = []
        for folder_p in album_dirs:
            # 1. 从音频标签提取字段
            standard_tag: dict[str, set] = FieldExtractor.extract_from_audio_tags(folder_p)
            # 如果没有读取到有效的 date 和 album，跳过
            if not (standard_tag.get("DATE") and standard_tag.get("ALBUM")):
                print(f"跳过（未找到有效标签）: {folder_p.name}")
                continue
            # 2. 扫描文件夹获取音频信息
            scan_fields: dict[str, str] = FolderScanner.analyze(folder_p, self.booklet_threshold,
                                                                self.folder_content_template, standard_tag).to_dict()
            all_fields = standard_tag | scan_fields
            # 3. 生成新名称
            new_name = FieldExtractor.format_fields_to_name(all_fields, self.output_template)
            if not new_name:
                continue
            # 4. 添加到重命名操作列表
            new_path = folder_p.parent / PathManager.safe_filename(new_name)
            pending.append((folder_p, new_path))
        self._execute(pending)

    # ------------------------------------------------------------------ #
    # 验证和执行
    # ------------------------------------------------------------------ #

    @staticmethod
    def _execute(pending: list[tuple[Path, Path]]):
        renamed: list[tuple[Path, Path]] = []
        for old_p, new_p in pending:
            if new_p.exists():
                print(f"目标路径{new_p}已存在，跳过重命名{old_p}")
                continue
            old_p.rename(new_p)
            print(f"{old_p}重命名为{new_p}")
            renamed.append((old_p, new_p))

        is_ack = input('是否确认重命名？(y/n)：（回车为n）').strip().lower()
        if is_ack != "y":
            for old_p, new_p in renamed:
                new_p.rename(old_p)
            print("已撤回重命名")
        else:
            print("完成重命名")