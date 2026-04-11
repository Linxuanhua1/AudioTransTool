import tomllib, os
os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.getcwd() + '/bin/'
from pathlib import Path
from lib.common.generate_config import generate_config
from lib.task_manager import TaskManager, TaskType
from lib.common.path_manager import PathManager
from lib.common.log import setup_logger

def main():
    if not Path("config.toml").exists():
        generate_config()

    with open("config.toml", 'rb') as f:
        config = tomllib.load(f)

    logger = setup_logger()

    while True:
        path_manager = PathManager()
        logger.info('输入#号退出程序', extra={"plain": True})
        folder_p = path_manager.check_input_folder_path(is_double_check=True)
        if folder_p == "#":
            break

        task_manager = TaskManager(config, path_manager)

        # 定义任务执行顺序
        task_sequence = [
            TaskType.AUDIO_CONVERT,
            TaskType.AUDIO_SPLIT,
            TaskType.IMAGE_CONVERT
        ]

        # 批量处理所有任务类型
        task_manager.process_f(folder_p, task_sequence)



if __name__ == '__main__':
    main()