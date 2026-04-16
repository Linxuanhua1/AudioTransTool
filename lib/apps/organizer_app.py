import logging
from lib.services.media_ops import FolderRenamer, TagSeparator, RemoteFetcher, ImageExtractor


logger = logging.getLogger("musicbox.organizer")


class OrganizerApp:
    def __init__(self, config) -> None:
        self.config = config
        self._renamer: FolderRenamer | None = None
        self._separator: TagSeparator | None = None
        self._fetcher: RemoteFetcher | None = None
        self._extractor: ImageExtractor | None = None

    @property
    def renamer(self) -> FolderRenamer:
        if self._renamer is None:
            self._renamer = FolderRenamer(self.config)
        return self._renamer

    @property
    def separator(self) -> TagSeparator:
        if self._separator is None:
            self._separator = TagSeparator(self.config)
        return self._separator

    @property
    def fetcher(self) -> RemoteFetcher:
        if self._fetcher is None:
            self._fetcher = RemoteFetcher(self.config)
        return self._fetcher

    @property
    def extractor(self) -> ImageExtractor:
        if self._extractor is None:
            self._extractor = ImageExtractor()
        return self._extractor

    @property
    def actions(self):
        return [
            ("根据音频标签重命名文件夹", self.renamer.rename_from_tag),
            ("提取文件夹名重命名文件夹（未压力测试）", self.renamer.rename_from_name),
            ("将音频标签的图片提取到同目录，同时删除音频标签的图片", self.extractor.extract_and_remove),
            ("分割音频的自定义字段（未压力测试）", self.separator.separate_tag),
            ("从 VGMdb 拉取数据并创建对应文件夹", self.fetcher.fetch_vgm_and_create_folder),
            # ("根据光盘编号从 MusicBrainz 拉取数据", self.fetcher.fetch_from_musicbrainz),
        ]

    def run(self) -> None:
        while True:
            logger.info("\n请选择操作：", extra={"plain": True, "plain_to_file": True})
            for i, (name, _) in enumerate(self.actions, 1):
                logger.info(f"  {i}. {name}", extra={"plain": True, "plain_to_file": True})
            logger.info("  #. 返回上一级", extra={"plain": True, "plain_to_file": True})

            choice = input("请输入数字：").strip()
            if choice == "#":
                logger.info("返回主菜单", extra={"plain": True, "plain_to_file": True})
                return

            if choice.isdigit() and 1 <= int(choice) <= len(self.actions):
                _, handler = self.actions[int(choice) - 1]
                handler()
            else:
                logger.info("输入不正确，请重新输入", extra={"plain": True, "plain_to_file": True})