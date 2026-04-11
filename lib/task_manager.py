import concurrent.futures, pyvips, logging
from pathlib import Path
from operator import methodcaller
from typing import Any, Callable
from tqdm import tqdm
from dataclasses import dataclass
from enum import Enum, auto

from lib.audio.audio_handler import AudioEncodeFormat
from lib.constants import AUDIO_HANDLERS, IMAGE_HANDLERS
from lib.audio.audio_splitter import Splitter
from lib.common import PathManager, MediaProbe, AudioFormatChecker, ImageFormatChecker


logger = logging.getLogger(__name__)


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
                call_func=methodcaller("compress_audio"),
                enabled_key = "act_audio_trans"
            ),
            TaskType.AUDIO_SPLIT: TaskConfig(
                task_type=TaskType.AUDIO_SPLIT,
                name="音频分轨",
                description="音频分轨中",
                call_func=methodcaller("split_flac_with_cue"),
                enabled_key="act_cue_splitting"
            ),

            TaskType.IMAGE_CONVERT: TaskConfig(
                task_type=TaskType.IMAGE_CONVERT,
                name="图片转码",
                description="图片转码中",
                call_func=methodcaller("compress_img"),
                enabled_key="act_img_transc"
            )
        }

    def process_f(self, folder_p: Path, task_types: list[TaskType]) -> None:
        for task_type in task_types:
            task_en_key = self.task_configs[task_type].enabled_key
            is_task_enabled = self.config['transcode'].get(task_en_key, False)
            if is_task_enabled:
                self._process_single_task_type(folder_p, task_type)
            else:
                logger.info(f"{self.task_configs[task_type].name} 已禁用，跳过")

    def _process_single_task_type(self, folder_p: Path, task_type: TaskType) -> None:
        """处理单一类型的任务"""
        task_config = self.task_configs[task_type]
        logger.info(f'{task_config.name}任务开始')

        tasks = self._collect_tasks(folder_p, task_type)
        if tasks:
            logger.info(f'找到 {len(tasks)} 个{task_config.name}任务')
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.config['transcode']['max_threads']) as executor:
                list(tqdm(
                    executor.map(task_config.call_func, tasks),
                    total=len(tasks),
                    desc=task_config.description
                ))
        else:
            logger.info(f"没有符合条件的{task_config.name}任务")
        logger.info(f'{task_config.name}任务结束')

    def _collect_tasks(self, folder_p: Path, task_type: TaskType) -> list:
        """收集指定类型的任务，使用批量 probe + format checker 过滤"""
        if task_type == TaskType.AUDIO_CONVERT:
            return self._collect_audio_tasks(folder_p)
        elif task_type == TaskType.AUDIO_SPLIT:
            return self._collect_split_tasks(folder_p)
        elif task_type == TaskType.IMAGE_CONVERT:
            return self._collect_image_tasks(folder_p)
        return []

    def _collect_audio_tasks(self, folder_p: Path) -> list:
        # 1. 收集所有匹配扩展名的文件
        candidates: list[Path] = []
        for p in folder_p.rglob("*"):
            ext = p.suffix.lower()
            if ext in AUDIO_HANDLERS:
                candidates.append(p)

        if not candidates:
            return []

        # 2. 批量 probe
        metadata_map = self._batch_probe(candidates)

        # 3. 用 FormatChecker 过滤并创建 handler
        tasks = []
        for file_p in candidates:
            ext = file_p.suffix.lower()
            metadata = metadata_map.get(file_p)
            encode_format = AudioFormatChecker.check(ext, metadata, file_p, self.config)

            if encode_format is AudioEncodeFormat.UNSUPPORTED:
                continue

            handler_cls = AUDIO_HANDLERS[ext]
            handler = handler_cls(file_p, self.path_manager, self.config,
                                  metadata=metadata, encode_format=encode_format)
            logger.debug(f'添加{file_p}到音频转码队列中')
            tasks.append(handler)

        return tasks

    def _collect_image_tasks(self, folder_p: Path) -> list:
        # 1. 收集所有匹配扩展名的文件（排除 cover 文件）
        candidates: list[Path] = []
        for p in folder_p.rglob("*"):
            ext = p.suffix.lower()
            stem = p.stem

            if ext not in IMAGE_HANDLERS:
                continue

            # 跳过 cover 文件（保持原有逻辑）
            if stem + ext == 'Cover.png':
                continue
            elif stem + ext == "cover.png":
                base_dir = p.parent
                save_p = base_dir / "Cover.png"
                p.rename(save_p)
                continue
            elif stem.lower() == "cover":
                base_dir = p.parent
                save_p = base_dir / "Cover.png"
                img = pyvips.Image.new_from_file(str(p), access="sequential")
                img.write_to_file(save_p)
                p.unlink()
                continue

            candidates.append(p)

        if not candidates:
            return []

        # 2. 批量 probe
        metadata_map = self._batch_probe(candidates)

        # 3. 用 FormatChecker 过滤并创建 handler
        tasks = []
        for file_p in candidates:
            ext = file_p.suffix.lower()
            metadata = metadata_map.get(file_p)

            if not ImageFormatChecker.check(ext, metadata, file_p):
                continue

            handler_cls = IMAGE_HANDLERS[ext]
            handler = handler_cls(file_p, self.config)
            logger.debug(f'添加{file_p}到图片转码队列中')
            tasks.append(handler)

        return tasks

    def _collect_split_tasks(self, folder_p: Path) -> list:
        tasks = []
        for p in folder_p.rglob("*"):
            ext = p.suffix.lower()
            if ext == '.flac':
                cue_path = p.with_suffix('.cue')
                if cue_path.exists():
                    tasks.append(Splitter(p, self.path_manager, self.config))
        return tasks

    @staticmethod
    def _batch_probe(paths: list[Path]) -> dict[Path, dict]:
        """批量 probe 文件，返回 {路径: 元数据} 映射"""
        results = MediaProbe.probe(paths)
        if not results:
            return {}

        metadata_map: dict[Path, dict] = {}
        for item in results:
            source = Path(item['SourceFile'])
            metadata_map[source] = item

        return metadata_map
