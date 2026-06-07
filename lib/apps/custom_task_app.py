import logging
from pathlib import Path

from lib.services.transcode import AudioTranscode, TASK_NAME_TO_CLASS
from lib.services.media_ops import FolderRenamer, ImageExtractor, TagSeparator
from lib.utils import PathManager, clear_screen

logger = logging.getLogger("musicbox.custom_task")


class CustomTaskApp:
    """自定义任务流：按 config.toml 中 [custom_task].task_pipeline 定义的顺序，
    在用户给定的同一个文件夹上依次执行任务。任务流可混合两类任务：

      - transcode 任务（audio_transcode / split_cue / image_transcode）。
      - organizer 任务（rename_from_tag / rename_from_name / extract_and_remove /
        separate_tag）。

    列入任务流即执行；未知的任务名会被记录并跳过。
    """
    def __init__(self, config) -> None:
        self.config = config
        self._renamer: FolderRenamer | None = None
        self._extractor: ImageExtractor | None = None
        self._separator: TagSeparator | None = None

    # ------------------------------------------------------------------ #
    # organizer 服务（按需创建）
    # ------------------------------------------------------------------ #

    @property
    def renamer(self) -> FolderRenamer:
        if self._renamer is None:
            self._renamer = FolderRenamer(self.config)
        return self._renamer

    @property
    def extractor(self) -> ImageExtractor:
        if self._extractor is None:
            self._extractor = ImageExtractor()
        return self._extractor

    @property
    def separator(self) -> TagSeparator:
        if self._separator is None:
            self._separator = TagSeparator(self.config)
        return self._separator

    # ------------------------------------------------------------------ #
    # 任务注册表 / 任务流解析
    # ------------------------------------------------------------------ #

    def _build_registry(self, path_manager: PathManager) -> dict:
        """任务名 -> (显示名, runner(folder_p))。"""
        registry: dict = {}
        # transcode 任务：列入任务流即执行
        pipeline_names = {str(n).strip().lower() for n in self.config["custom_task"]["task_pipeline"]}
        split_in_pipeline = "split_cue" in pipeline_names
        for name, task_cls in TASK_NAME_TO_CLASS.items():
            task = task_cls(self.config, path_manager)
            # 同一任务流中若也包含 split_cue，音频转码跳过「可直接分轨且带 cue」的整轨文件，交给 split_cue
            if isinstance(task, AudioTranscode):
                task.skip_cue_direct_split = split_in_pipeline
            registry[name] = (task.NAME, lambda fp, t=task: t.process(fp))
        # organizer 任务：直接在该文件夹上执行
        registry["rename_from_tag"] = ("根据音频标签重命名文件夹", lambda fp: self.renamer.run_rename_from_tag(fp))
        registry["rename_from_name"] = ("提取文件夹名重命名文件夹", lambda fp: self.renamer.run_rename_from_name(fp))
        registry["extract_and_remove"] = ("提取并移除内嵌图片", lambda fp: self.extractor.run_extract_and_remove(fp))
        registry["separate_tag"] = ("分割音频自定义字段", lambda fp: self.separator.run_separate_tag(fp))
        return registry

    def _resolve_pipeline(self, registry: dict) -> list:
        """解析 config 中的 task_pipeline，返回 [(name, display, runner), ...]（顺序即执行顺序）。"""
        names = self.config["custom_task"]["task_pipeline"]
        steps: list = []
        for name in names:
            key = str(name).strip().lower()
            entry = registry.get(key)
            if entry is None:
                logger.error(f"未知的任务名 '{name}'，已跳过。可用任务：{', '.join(registry)}")
                continue
            display, runner = entry
            steps.append((key, display, runner))
        return steps

    # ------------------------------------------------------------------ #
    # 入口
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        while True:
            path_manager = PathManager()
            logger.info("输入#号返回主菜单", extra={"plain": True})
            folder_p = path_manager.check_input_folder_path(is_double_check=True)
            if folder_p == "#":
                logger.info("返回主菜单", extra={"plain": True})
                clear_screen()
                return
            clear_screen()

            registry = self._build_registry(path_manager)
            steps = self._resolve_pipeline(registry)
            if not steps:
                logger.info(
                    "未配置有效的任务流，请检查 config.toml 中 [custom_task].task_pipeline",
                    extra={"plain": True},
                )
                continue

            flow = " -> ".join(display for _, display, _ in steps)
            logger.info(f"自定义任务流：{flow}", extra={"plain": True})

            for _, _, runner in steps:
                runner(Path(folder_p))

            logger.info("\n任务流全部执行完毕", extra={"plain": True})
