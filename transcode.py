import os, tomllib, multiprocessing, time
from lib.task_manager import TaskManager, TaskType
from lib.utils import check_input_folder_path
from lib.log import LoggerManager


def main():
    with multiprocessing.Manager() as manager:  # 没什么别的作用，仅用于生成多进程队列
        with LoggerManager() as logger_mgr:
            os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.getcwd() + '/bin/'
            logger_mgr.setup(manager)
            with open("lib/config.toml", 'rb') as f:
                config = tomllib.load(f)

            while True:
                time.sleep(1)
                print('输入#号退出程序')
                folder_path = check_input_folder_path(is_double_check=True)
                if folder_path == "#":
                    break

                # 创建任务管理器
                lock = manager.Lock()
                task_manager = TaskManager(config, logger_mgr, lock)

                # 定义任务执行顺序
                task_sequence = [
                    TaskType.AUDIO_CONVERT,
                    TaskType.AUDIO_SPLIT,
                    TaskType.IMAGE_CONVERT
                ]

                # 批量处理所有任务类型
                task_manager.process_folder(folder_path, task_sequence)



if __name__ == '__main__':
    main()