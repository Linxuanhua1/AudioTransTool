import os, threading
from pathlib import Path
from lib.common.log import setup_logger


logger = setup_logger()


class PathManager:
    _SAFE_FILENAME_TRANS = str.maketrans('/?:\\*"<>|', '／？：＼＊＂＜＞｜')

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reserved = set()

    @classmethod
    def safe_filename(cls, name: str) -> str:
        return name.translate(cls._SAFE_FILENAME_TRANS).strip()

    @staticmethod
    def check_input_folder_path(is_double_check: bool = False) -> Path | str:
        while True:
            folder_p = input("请输入文件夹：").strip()
            if folder_p in ("#", "$"):
                return str(folder_p)

            path = Path(folder_p)

            if not path.exists():
                logger.info("文件夹路径不存在，请重新输入文件夹", extra={"plain": True})
                continue

            if not path.is_dir():
                logger.info("请输入文件夹，而不是文件", extra={"plain": True})
                continue

            if is_double_check:
                is_start = input("请输入Y/N来确认是否是该文件夹：").strip().lower()
                if is_start == "y":
                    logger.info(f"文件夹为：{folder_p}", extra={"plain": True})
                    return PathManager.to_unc_path(folder_p)
            else:
                return PathManager.to_unc_path(folder_p)

    def get_output_path(self, desired_path: str | Path) -> Path:
        desired_path = Path(desired_path)

        suffix = desired_path.suffix
        stem = desired_path.stem
        parent = desired_path.parent

        with self._lock:
            candidate = desired_path
            index = 1

            while self._is_taken(candidate):
                candidate = parent / f"{stem} ({index}){suffix}"
                index += 1

            self._reserved.add(self._path_key(candidate))

        return candidate

    def _is_taken(self, path: Path) -> bool:
        return path.exists() or self._path_key(path) in self._reserved

    @staticmethod
    def _path_key(path: Path) -> str:
        return os.path.normcase(os.path.normpath(str(path)))

    @staticmethod
    def to_unc_path(path: str | Path) -> Path:
        path = Path(path).resolve(strict=False)
        path_str = str(path)

        # 已经是扩展长路径，直接返回
        if path_str.startswith("\\\\?\\"):
            return path

        # 普通 UNC 共享路径
        if path_str.startswith("\\\\"):
            return Path("\\\\?\\UNC\\" + path_str.lstrip("\\"))

        # 本地绝对路径
        return Path("\\\\?\\" + path_str)

    @staticmethod
    def to_norm_path(path: str | Path) -> Path:
        path = Path(path).resolve(strict=False)
        path_str = str(path)

        # 已经是扩展长路径，直接返回
        if path_str.startswith("\\\\?\\"):
            return Path(path_str[4:])
        elif path_str.startswith("\\\\?\\UNC\\"):
            return Path(path_str[8:])
        else:
            return Path(path_str)