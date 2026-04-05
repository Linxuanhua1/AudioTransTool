import concurrent.futures, logging, pyvips
from pathlib import Path
from operator import methodcaller
from typing import Any, Callable
from tqdm import tqdm
from dataclasses import dataclass
from enum import Enum, auto
from lib.audio.audio_handler import FlacHandler, M4aHandler, DSDHandler, WavHandler, WavepackHandler, TakHandler
from lib.audio.audio_handler import TtaHandler, ApeHandler, AiffHandler, AudioHandler
from lib.audio.audio_splitter import Splitter
from lib.path_manager import PathManager
from lib.img.image_handler import WebpHandler, JpgHandler, BmpHandler, TiffHandler, PngHandler


logger = logging.getLogger(__name__)


AUDIO_HANDLERS = {
    '.wav': WavHandler,
    '.m4a': M4aHandler,
    '.ape': ApeHandler,
    '.tak': TakHandler,
    '.tta': TtaHandler,
    '.flac': FlacHandler,
    ".wv": WavepackHandler,
    ".dsf": DSDHandler,
    ".dff": DSDHandler,
    ".aiff": AiffHandler,
    ".aif": AiffHandler,
    ".aifc": AiffHandler,
}

IMAGE_HANDLER = {
    '.jpeg': JpgHandler,
    '.jpg': JpgHandler,
    '.png': PngHandler,
    '.bmp': BmpHandler,
    '.tif': TiffHandler,
    '.tiff': TiffHandler,
    '.webp': WebpHandler
}


class TaskType(Enum):
    """任务类型枚举"""
    AUDIO_CONVERT = auto()
    AUDIO_SPLIT = auto()
    IMAGE_CONVERT = auto()


@dataclass
class TaskConfig:
    """任务配置"""
    task_type: TaskType
    name: str
    description: str
    get_handler_cls: Callable
    call_func: Callable
    enabled_key: str | None = None  # config中的启用键名


class TaskManager:
    """统一任务管理器"""
    def __init__(self, config: dict[str, Any], path_manager: PathManager):
        self.config = config
        self.worker_count = 1
        self.path_manager = path_manager

        # 注册所有任务类型
        self.task_configs = {
            TaskType.AUDIO_CONVERT: TaskConfig(
                task_type=TaskType.AUDIO_CONVERT,
                name="音频转码",
                description="音频转码中",
                get_handler_cls=self._get_audio_handler,
                call_func=methodcaller("compress_audio"),
                enabled_key = "act_audio_trans"
            ),
            TaskType.AUDIO_SPLIT: TaskConfig(
                task_type=TaskType.AUDIO_SPLIT,
                name="音频分轨",
                description="音频分轨中",
                get_handler_cls=self._get_split_handler,
                call_func=methodcaller("split_flac_with_cue"),
                enabled_key="act_cue_splitting"
            ),

            TaskType.IMAGE_CONVERT: TaskConfig(
                task_type=TaskType.IMAGE_CONVERT,
                name="图片转码",
                description="图片转码中",
                get_handler_cls=self._get_image_handler,
                call_func=methodcaller("compress_img"),
                enabled_key="act_img_transc"
            )
        }

    def process_f(self, folder_p: Path, task_types: list[TaskType]) -> None:
        for task_type in task_types:
            task_en_key = self.task_configs[task_type].enabled_key
            is_task_enabled = self.config.get(task_en_key, False)
            if is_task_enabled:
                self._process_single_task_type(folder_p, task_type)
            else:
                logger.info(f"{self.task_configs[task_type].name} 已禁用，跳过")

    def _process_single_task_type(self, folder_p: Path, task_type: TaskType) -> None:
        """处理单一类型的任务"""
        task_config = self.task_configs[task_type]
        logger.info(f'{task_config.name}任务开始')

        tasks = self._collect_tasks(folder_p, task_config)
        if tasks:
            logger.info(f'找到 {len(tasks)} 个{task_config.name}任务')
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.config['max_threads']) as executor:
                list(tqdm(
                    executor.map(task_config.call_func, tasks),
                    total=len(tasks),
                    desc=task_config.description
                ))
        else:
            logger.info(f"没有符合条件的{task_config.name}任务")
        logger.info(f'{task_config.name}任务结束')

    @staticmethod
    def _collect_tasks(folder_p: Path, task_config: TaskConfig) -> list[tuple]:
        """收集指定类型的任务"""
        tasks = []
        for p in folder_p.rglob("*"):
            task_data = task_config.get_handler_cls(p)
            if task_data:
                logger.debug(f'添加{p}到{task_config.name}队列中')
                tasks.append(task_data)
        return tasks

    def _get_audio_handler(self, file_p: Path) -> object | None:
        ext = file_p.suffix.lower()
        handler_cls: type[AudioHandler] = AUDIO_HANDLERS.get(ext)
        if handler_cls is not None:
            return handler_cls(file_p, self.config)
        return None

    def _get_split_handler(self, file_p: Path) -> object | None:
        ext = file_p.suffix.lower()
        if ext.endswith('.flac'):
            cue_path = file_p.with_suffix('.cue')
            if cue_path.exists():
                return Splitter(file_p, self.path_manager, self.config)
        return None

    def _get_image_handler(self, file_p: Path) -> tuple | None:
        ext = file_p.suffix.lower()
        stem = file_p.stem
        handler = IMAGE_HANDLER.get(ext.lower())

        # 跳过已经是目标格式的封面
        if stem + ext == 'Cover.png':
            return None
        elif stem + ext == "cover.png":
            base_dir = file_p.parent
            save_p = base_dir / "Cover.png"
            file_p.rename(save_p)
            return None
        elif stem.lower() == "cover":
            base_dir = file_p.parent
            save_p = base_dir / "Cover.png"
            img = pyvips.Image.new_from_file(str(file_p), access="sequential")
            img.write_to_file(save_p)
            file_p.unlink()
            return None

        if handler:
            return file_p, handler, self.config
        return None

