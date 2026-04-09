import tomllib
from typing import Callable

from lib.organizer.folder_renamer.folder_renamer import FolderRenamer
from lib.organizer.catno_writer import CatNoWriter
from lib.organizer.tag_separator import TagSeparator
from lib.organizer.remote_fetcher import RemoteFetcher
from lib.organizer.image_extractor import ImageExtractor
from lib.common.log import setup_logger


logger = setup_logger(__name__)


class Organizer:
    def __init__(self) -> None:
        with open("config.toml", 'rb') as f:
            self.config = tomllib.load(f)
        self._renamer:   FolderRenamer   | None = None
        self._writer:    CatNoWriter     | None = None
        self._separator: TagSeparator    | None = None
        self._fetcher:   RemoteFetcher   | None = None
        self._extractor: ImageExtractor  | None = None

    @property
    def renamer(self) -> FolderRenamer:
        if self._renamer is None:
            self._renamer = FolderRenamer(self.config)
        return self._renamer

    @property
    def writer(self) -> CatNoWriter:
        if self._writer is None:
            self._writer = CatNoWriter()
        return self._writer

    @property
    def separator(self) -> TagSeparator:
        if self._separator is None:
            self._separator = TagSeparator()
        return self._separator

    @property
    def fetcher(self) -> RemoteFetcher:
        if self._fetcher is None:
            self._fetcher = RemoteFetcher()
        return self._fetcher

    @property
    def extractor(self) -> ImageExtractor:
        if self._extractor is None:
            self._extractor = ImageExtractor()
        return self._extractor

    @property
    def _actions(self) -> list[tuple[str, Callable]]:
        return [
            ("根据音频标签重命名文件夹",                          self.renamer.rename_from_tag),
            ("提取文件夹名重命名文件夹",                          self.renamer.rename_from_name),
            ("将音频标签的图片提取到同目录，同时删除音频标签的图片",   self.extractor.extract_and_remove),
            ("分割音频的艺术家、专辑艺术家和编曲家",                self.separator.separate_tag),
            ("提取文件夹名中的光盘编号写入音频标签",                self.writer.write_from_folder_name),
            ("从 VGMdb 拉取数据并创建对应文件夹",                  self.fetcher.fetch_vgm_and_create_folder),
            ("根据光盘编号从 MusicBrainz 拉取数据",               self.fetcher.fetch_from_musicbrainz),
        ]

    def run(self) -> None:
        while True:
            actions = self._actions
            logger.info("\n请选择操作：", extra={"plain": True})
            for i, (name, _) in enumerate(actions, 1):
                logger.info(f"  {i}. {name}", extra={"plain": True})
            logger.info("  #. 退出", extra={"plain": True})

            choice = input("请输入数字：").strip()
            if choice == "#":
                logger.info("退出", extra={"plain": True})
                return

            if choice.isdigit() and 1 <= int(choice) <= len(actions):
                _, handler = actions[int(choice) - 1]
                handler()
            else:
                logger.info("输入不正确，请重新输入", extra={"plain": True})


if __name__ == "__main__":
    Organizer().run()
