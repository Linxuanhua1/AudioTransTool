import sys, logging, logging.handlers, multiprocessing, datetime, queue
from pathlib import Path
from concurrent_log_handler import ConcurrentRotatingFileHandler
from dataclasses import dataclass
from enum import Enum


class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


@dataclass
class LoggerConfig:
    """日志配置"""
    log_dir: str = "logs"
    max_file_size: int = 1024 * 500  # 500KB
    backup_count: int = 5
    console_level: LogLevel = LogLevel.INFO
    file_level: LogLevel = LogLevel.DEBUG
    error_level: LogLevel = LogLevel.ERROR
    date_format: str = "%Y-%m-%d_%H_%M_%S"
    log_format: str = "%(asctime)s | %(processName)s | %(levelname)s | %(message)s"
    enable_console: bool = True
    enable_file: bool = True
    enable_error_file: bool = True


class LoggerManager:
    """多进程日志管理器"""

    def __init__(self, config: LoggerConfig | None = None):
        self.config = config or LoggerConfig()
        self.queue: multiprocessing.Queue | None = None
        self.listener_process: multiprocessing.Process | None = None
        self.manager: multiprocessing.Manager | None = None
        self._is_setup = False

    def setup(self, manager: multiprocessing.Manager) -> logging.Logger:
        """
        设置日志系统

        Args:
            manager: 多进程管理器

        Returns:
            配置好的主进程logger
        """
        if self._is_setup:
            raise RuntimeError("Logger already setup")

        self.manager = manager
        self.queue = manager.Queue(-1)

        # 启动监听进程
        self.listener_process = multiprocessing.Process(
            target=self._listener_process,
            args=(self.queue, self.config)
        )
        self.listener_process.start()

        # 配置主进程logger
        main_logger = self._setup_main_logger()
        self._is_setup = True

        return main_logger

    @staticmethod
    def setup_worker_logger(log_queue: multiprocessing.Queue,
                            logger_name: str | None = None, level: int = logging.INFO) -> logging.Logger:
        """
        静态方法：为工作进程设置logger（用于多进程环境）
        Args:
            log_queue: 日志队列
            logger_name: logger名称
            level: 日志级别
        Returns:
            配置好的工作进程logger
        """
        logger = logging.getLogger(logger_name)

        # 避免重复添加handler
        if not logger.handlers:
            handler = logging.handlers.QueueHandler(log_queue)
            logger.addHandler(handler)
            logger.setLevel(level)

        return logger

    def shutdown(self):
        """关闭日志系统"""
        if self.queue is not None:
            # 发送退出信号
            self.queue.put_nowait(None)

        if self.listener_process is not None and self.listener_process.is_alive():
            # 等待监听进程结束
            self.listener_process.join(timeout=5)
            if self.listener_process.is_alive():
                self.listener_process.terminate()
                self.listener_process.join()

        self._is_setup = False

    def _setup_main_logger(self) -> logging.Logger:
        """设置主进程logger"""
        logger = logging.getLogger(__name__)

        # 清除现有handlers
        logger.handlers.clear()

        if self.queue is not None:
            handler = logging.handlers.QueueHandler(self.queue)
            logger.addHandler(handler)
            logger.setLevel(self.config.console_level.value)

        return logger

    @staticmethod
    def _listener_process(log_queue: multiprocessing.Queue, config: LoggerConfig):
        """监听进程函数"""
        try:
            # 创建根logger
            root_logger = logging.getLogger()
            root_logger.handlers.clear()  # 清除现有handlers

            formatter = logging.Formatter(config.log_format)

            # 设置控制台处理器
            if config.enable_console:
                console_handler = LoggerManager._create_console_handler(formatter)
                root_logger.addHandler(console_handler)

            # 确保日志目录存在
            log_dir = Path(config.log_dir)
            log_dir.mkdir(exist_ok=True)

            # 生成时间戳
            now_str = datetime.datetime.now().strftime(config.date_format)

            # 设置文件处理器
            if config.enable_file:
                file_handler = LoggerManager._create_file_handler(
                    log_dir / f"main_{now_str}.log",
                    config.max_file_size,
                    config.backup_count,
                    formatter,
                    config.file_level.value
                )
                root_logger.addHandler(file_handler)

            # 设置错误日志处理器
            if config.enable_error_file:
                error_handler = LoggerManager._create_file_handler(
                    log_dir / f"error_{now_str}.log",
                    config.max_file_size,
                    config.backup_count,
                    formatter,
                    config.error_level.value
                )
                root_logger.addHandler(error_handler)

            root_logger.setLevel(logging.DEBUG)

            # 监听日志记录
            while True:
                try:
                    record = log_queue.get(timeout=1)
                    if record is None:  # 退出信号
                        break
                    root_logger.handle(record)
                except queue.Empty:
                    continue  # 队列为空，继续等待
                except Exception as e:
                    # 避免日志系统本身的错误影响程序运行
                    print(f"Logger error: {e}", file=sys.stderr)

        except Exception as e:
            print(f"Fatal logger error: {e}", file=sys.stderr)
        finally:
            # 清理资源
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)

    @staticmethod
    def _create_console_handler(formatter: logging.Formatter) -> logging.StreamHandler:
        """创建控制台处理器"""
        console_handler = logging.StreamHandler(sys.stdout)

        # Windows平台编码处理
        if sys.platform.startswith('win'):
            try:
                import io
                if hasattr(sys.stdout, 'buffer'):
                    sys.stdout = io.TextIOWrapper(
                        sys.stdout.buffer,
                        encoding='utf-8',
                        errors='replace'
                    )
            except Exception:
                pass  # 编码设置失败时继续使用默认设置

        console_handler.setFormatter(formatter)
        return console_handler

    @staticmethod
    def _create_file_handler(
            filename: Path,
            max_bytes: int,
            backup_count: int,
            formatter: logging.Formatter,
            level: int
    ) -> ConcurrentRotatingFileHandler:
        """创建文件处理器"""
        handler = ConcurrentRotatingFileHandler(
            str(filename),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        handler.setFormatter(formatter)
        handler.setLevel(level)
        return handler

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.shutdown()


