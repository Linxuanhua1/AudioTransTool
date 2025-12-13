import os, concurrent.futures
from tqdm import tqdm
from typing import Callable
from dataclasses import dataclass
from enum import Enum
from lib.audio_handler import  AudioHandler, AudioProbe, Splitter, setup_audio_module_logger
from lib.image_handler import ImageHandler, ImageProbe, setup_image_module_logger
from lib.utils import get_root_dir_and_name
from lib.log import LoggerManager


AUDIO_HANDLERS = {
    '.wav': AudioHandler.wav2flac,
    '.m4a': AudioHandler.m4a2flac,
    '.ape': AudioHandler.ape2flac,
    '.tak': AudioHandler.tak2flac,
    '.tta': AudioHandler.tta2flac,
    '.flac': AudioHandler.flac2flac
}

IMAGE_HANDLER = {
    '.jpeg': ImageHandler.jpg2jxl,
    '.jpg': ImageHandler.jpg2jxl,
    '.png': ImageHandler.png2jxl,
    '.bmp': ImageHandler.bmp2jxl,
    '.tif': ImageHandler.tif2jxl,
    '.tiff': ImageHandler.tif2jxl,
    '.webp': ImageHandler.webp2jxl
}


class TaskType(Enum):
    """任务类型枚举"""
    AUDIO_CONVERT = "audio_convert"
    AUDIO_SPLIT = "audio_split"
    IMAGE_CONVERT = "image_convert"


@dataclass
class TaskConfig:
    """任务配置"""
    task_type: TaskType
    name: str
    description: str
    append_handler: Callable
    worker_handler: Callable
    enabled_key: str | None = None  # config中的启用键名


class TaskManager:
    """统一任务管理器"""
    def __init__(self, config: dict[str, any], logger_mgr: LoggerManager, lock=None):
        self.main_logger = logger_mgr.setup_worker_logger(logger_mgr.queue, 'Task Manager')
        self.queue = logger_mgr.queue
        self.setup_worker_logger = logger_mgr.setup_worker_logger

        self.config = config
        self.lock = lock
        self.worker_count = 1

        # 注册所有任务类型
        self.task_configs = {
            TaskType.AUDIO_CONVERT: TaskConfig(
                task_type=TaskType.AUDIO_CONVERT,
                name="音频转码",
                description="音频转码中",
                append_handler=self._append_audio_task,
                worker_handler=self._audio_worker_wrapper
            ),
            TaskType.AUDIO_SPLIT: TaskConfig(
                task_type=TaskType.AUDIO_SPLIT,
                name="音频分轨",
                description="音频分轨中",
                append_handler=self._append_split_task,
                worker_handler=self._split_worker_wrapper,
                enabled_key="activate_cue_splitting"
            ),
            TaskType.IMAGE_CONVERT: TaskConfig(
                task_type=TaskType.IMAGE_CONVERT,
                name="图片转码",
                description="图片转码中",
                append_handler=self._append_image_task,
                worker_handler=self._image_worker_wrapper,
                enabled_key="activate_image_transc"
            )
        }

    def process_folder(self, folder_path: str, task_types: list[TaskType]) -> None:
        """处理文件夹中的所有指定类型任务"""
        for task_type in task_types:
            if self._is_task_enabled(task_type):
                self._process_single_task_type(folder_path, task_type)
            else:
                self.main_logger.info(f"{self.task_configs[task_type].name} 已禁用，跳过")

    def _is_task_enabled(self, task_type: TaskType) -> bool:
        """检查任务是否启用"""
        config = self.task_configs[task_type]
        if config.enabled_key is None:
            return True  # 没有启用键则默认启用
        return self.config.get(config.enabled_key, False)

    def _process_single_task_type(self, folder_path: str, task_type: TaskType) -> None:
        """处理单一类型的任务"""
        task_config = self.task_configs[task_type]
        self.main_logger.info(f'开始{task_config.name}')

        # 收集任务
        tasks = self._collect_tasks(folder_path, task_config)

        if tasks:
            self.main_logger.info(f'找到 {len(tasks)} 个{task_config.name}任务')

            # 执行任务
            with concurrent.futures.ProcessPoolExecutor(
                    max_workers=self.config['max_workers']
            ) as executor:
                list(tqdm(
                    executor.map(task_config.worker_handler, tasks),
                    total=len(tasks),
                    desc=task_config.description
                ))
        else:
            self.main_logger.info(f"没有符合条件的{task_config.name}任务")
        self.main_logger.info(f'{task_config.name}结束')
        self.main_logger.info('-' * 100)

    def _collect_tasks(self, folder_path: str, task_config: TaskConfig) -> list[tuple]:
        """收集指定类型的任务"""
        tasks = []

        for root, dirs, files in os.walk(folder_path):
            # 音频转码需要跳过特定目录
            if task_config.task_type == TaskType.AUDIO_CONVERT:
                if self.config['is_skip_compressed_audio']:
                    dirs[:] = [d for d in dirs if all(tag not in d for tag in self.config['AUDIO_TRACS_EXCLUDED_TAGS'])]

            for file in files:
                file_path = os.path.join(root, file)
                task_data = task_config.append_handler(file_path)

                if task_data:
                    self.main_logger.info(f'添加{file_path}到{task_config.name}队列中')
                    tasks.append(task_data)

        return tasks

    # ===== 任务收集方法 =====
    def _append_audio_task(self, file_path: str) -> tuple | None:
        """收集音频转码任务"""
        _, ext = os.path.splitext(file_path)
        handler = AUDIO_HANDLERS.get(ext)

        if handler and AudioProbe.is_allowed_to_convert(file_path):
            return self.queue, file_path, handler, self.config
        return None

    def _append_split_task(self, file_path: str) -> tuple | None:
        """收集音频分轨任务"""
        if file_path.lower().endswith('.flac'):
            root, file = os.path.split(file_path)
            name, _ = os.path.splitext(file)
            cue_path = os.path.join(root, f'{name}.cue')
            if os.path.exists(cue_path):
                return self.queue, file_path, self.config, self.lock
        return None

    def _append_image_task(self, file_path: str) -> tuple | None:
        """收集图片转码任务"""
        _, ext = os.path.splitext(file_path)
        _, name = get_root_dir_and_name(file_path)
        handler = IMAGE_HANDLER.get(ext.lower())

        # 跳过已经是目标格式的封面
        if name + ext == 'Cover.png':
            return None

        if handler and ImageProbe.is_allowed_to_convert(file_path):
            return self.queue, file_path, handler, name, self.config
        return None

    # ===== 工作线程包装方法 =====
    def _audio_worker_wrapper(self, task: tuple) -> None:

        """音频转码工作线程包装器"""
        try:
            queue, audio_path, handler, config = task
            work_logger = self.setup_worker_logger(self.queue, "Audio Worker")
            setup_audio_module_logger(work_logger)
            work_logger.info(f'即将处理音频{audio_path}')
            handler(audio_path, config['is_del_source_audio'])
            work_logger.info(f"{audio_path} 转码成功")

        except Exception as e:
            work_logger.error(f"{task[1]} 转码失败: {e}")

    def _split_worker_wrapper(self, task: tuple) -> None:
        """音频分轨工作线程包装器"""
        try:
            queue, file_path, config, lock = task
            work_logger = self.setup_worker_logger(self.queue, "Split Worker")
            setup_audio_module_logger(work_logger)
            Splitter.split_flac_with_cue(file_path, config['is_delete_single_track'], lock)

        except Exception as e:
            work_logger.error(f"{task[1]} 分轨失败: {e}")

    def _image_worker_wrapper(self, task: tuple) -> None:
        """图片转码工作线程包装器"""
        try:
            queue, img_path, handler, name, config = task
            work_logger = self.setup_worker_logger(self.queue, "Image Worker")
            setup_image_module_logger(work_logger)
            self._process_single_image(img_path, handler, name, config, work_logger)

        except Exception as e:
            work_logger.error(f"{task[1]} 图片转码失败: {e}")

    @staticmethod
    def _process_single_image(img_path: str, handler: Callable,
                              name: str, config: dict[str, any], work_logger) -> None:
        """处理单个图片"""
        work_logger.info('即将处理图片')

        if name.lower() == 'cover':
            ImageHandler.cover2png(img_path)
        else:
            handler(img_path, config['is_del_source_img'])

        work_logger.info(f'转换完成')
        work_logger.info('-' * 100)

