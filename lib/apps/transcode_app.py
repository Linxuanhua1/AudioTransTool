import logging

from lib.services.task_manager import TaskManager, TaskType
from lib.services.utils import PathManager, clear_screen

logger = logging.getLogger("musicbox.transcode")


class TranscodeApp:
    def __init__(self, config) -> None:
        self.config = config

    def run(self) -> None:
        while True:
            path_manager = PathManager()
            logger.info("输入#号返回主菜单", extra={"plain": True})
            folder_p = path_manager.check_input_folder_path(is_double_check=True)
            if folder_p == "#":
                logger.info("返回主菜单", extra={"plain": True})
                return
            clear_screen()

            task_manager = TaskManager(self.config, path_manager)

            task_sequence = [
                TaskType.AUDIO_CONVERT,
                TaskType.AUDIO_SPLIT,
                TaskType.IMAGE_CONVERT,
            ]

            task_manager.process_f(folder_p, task_sequence)