import datetime
import logging
import logging.handlers
import sys
from pathlib import Path


class PlainAwareFormatter(logging.Formatter):
    def format(self, record):
        if getattr(record, "plain", False):
            return record.getMessage()
        return super().format(record)


class FilePlainFilter(logging.Filter):
    def filter(self, record):
        # 非 plain 日志，正常写入文件
        if not getattr(record, "plain", False):
            return True

        # plain 日志，是否写入文件由 plain_to_file 控制，默认 False
        return getattr(record, "plain_to_file", False)


def setup_logger(name) -> logging.Logger:
    logger = logging.getLogger(name=name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    log_path = Path("logs")
    log_path.mkdir(parents=True, exist_ok=True)

    now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    log_format = "%(asctime)s | %(threadName)s | %(levelname)s | %(message)s"
    formatter = PlainAwareFormatter(log_format)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / f"main_{now_str}.log",
        maxBytes=1024 * 500,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(FilePlainFilter())
    logger.addHandler(file_handler)

    return logger