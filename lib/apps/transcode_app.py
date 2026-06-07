import logging

from lib.services.transcode import TranscodeTask, AudioTranscode, AudioSplit, ImageTranscode
from lib.utils import PathManager, clear_screen

logger = logging.getLogger("musicbox.transcode")


class TranscodeApp:
    def __init__(self, config) -> None:
        self.config = config

    @property
    def sub_actions(self) -> list[tuple[str, type[TranscodeTask]]]:
        return [
            ("audio transcode", AudioTranscode),
            ("split cue", AudioSplit),
            ("image transcode", ImageTranscode),
        ]

    def run(self) -> None:
        while True:
            logger.info("\n请选择转码功能：", extra={"plain": True})
            for i, (name, _) in enumerate(self.sub_actions, 1):
                logger.info(f"  {i}. {name}", extra={"plain": True})
            logger.info("  #. 返回上一级", extra={"plain": True})

            choice = input("请输入数字：").strip()
            if choice == "#":
                logger.info("返回主菜单", extra={"plain": True})
                clear_screen()
                return

            clear_screen()

            if choice.isdigit() and 1 <= int(choice) <= len(self.sub_actions):
                _, task_cls = self.sub_actions[int(choice) - 1]
                self._run_single(task_cls)
            else:
                logger.info("输入不正确，请重新输入", extra={"plain": True})

    def _run_single(self, task_cls: type[TranscodeTask]) -> None:
        path_manager = PathManager()
        task = task_cls(self.config, path_manager)

        logger.info("输入#号返回上一级", extra={"plain": True})
        folder_p = path_manager.check_input_folder_path(is_double_check=True)
        if folder_p == "#":
            logger.info("返回上一级", extra={"plain": True})
            clear_screen()
            return
        clear_screen()

        task.process(folder_p)
