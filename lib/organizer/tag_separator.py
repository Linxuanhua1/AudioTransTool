from pathlib import Path

from lib.common.path_manager import PathManager
from lib.organizer.audio_tag_reader import AudioTagReader, TagBundle
from lib.organizer.catno_helper import CatNoHelper


class TagSeparator:
    """
    标签分割操作类。

    用法
    ----
    separator = TagSeparator()
    separator.separate_tag()   # 交互式循环
    """

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
        modified: list[TagBundle] = []

        for p in folder_p.rglob("*"):
            if p.suffix.lower() not in AudioTagReader.supported_extensions():
                continue
            original = self._update_file(p)
            if original:
                modified.append(original)

        if modified and input("是否撤回修改？(y/n): ").strip().lower() == "y":
            self._rollback(modified)

    # ------------------------------------------------------------------ #
    # 单文件处理
    # ------------------------------------------------------------------ #

    def _update_file(self, file_p: Path) -> TagBundle | None:
        """
        读取标签 → 分割 → 写回。
        若无需修改返回 None；若修改成功返回保存了原始值的 TagBundle（用于撤回）。
        """
        try:
            bundle = AudioTagReader.read(file_p)
            if bundle is None:
                return None

            new_artist      = CatNoHelper.separate_text(bundle.artist)
            new_albumartist = CatNoHelper.separate_text(bundle.albumartist)
            new_composer    = CatNoHelper.separate_text(bundle.composer)

            if (new_artist == bundle.artist
                    and new_albumartist == bundle.albumartist
                    and new_composer == bundle.composer):
                print(f"{file_p} 无需修改")
                return None

            print(
                f"修改前 [{file_p}]:\n"
                f"  Artist:       {bundle.artist}\n"
                f"  Album Artist: {bundle.albumartist}\n"
                f"  Composer:     {bundle.composer}"
            )

            # 保留原始快照用于撤回
            original = TagBundle(
                file_path=file_p,
                artist=bundle.artist,
                albumartist=bundle.albumartist,
                composer=bundle.composer,
            )

            AudioTagReader.write_people_tags(file_p, new_artist, new_albumartist, new_composer)

            # 读回确认
            updated = AudioTagReader.read(file_p)
            if updated:
                print(
                    f"修改后 [{file_p}]:\n"
                    f"  Artist:       {updated.artist}\n"
                    f"  Album Artist: {updated.albumartist}\n"
                    f"  Composer:     {updated.composer}"
                )
            print("-" * 50)
            return original

        except Exception as e:
            print(f"[错误] 处理文件 {file_p} 时出错：{e}")
            return None

    # ------------------------------------------------------------------ #
    # 撤回
    # ------------------------------------------------------------------ #

    @staticmethod
    def _rollback(modified: list[TagBundle]) -> None:
        for bundle in modified:
            if AudioTagReader.restore(bundle):
                print(f"已撤回 {bundle.file_path} 的修改")
