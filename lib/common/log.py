import sys
import logging
import logging.handlers
import datetime
from pathlib import Path


class PlainAwareFormatter(logging.Formatter):
    def format(self, record):
        if getattr(record, "plain", False):
            return record.getMessage()
        return super().format(record)


class ExcludePlainFilter(logging.Filter):
    def filter(self, record):
        return not getattr(record, "plain", False)


def setup_logger() -> logging.Logger:
    logger = logging.getLogger()
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
    file_handler.addFilter(ExcludePlainFilter())
    logger.addHandler(file_handler)

    return logger