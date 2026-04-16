import os, tomllib
from pathlib import Path

os.environ["PATH"] = os.environ["PATH"] + os.pathsep + os.getcwd() + "/bin/"

from lib.services.utils import setup_logger, generate_config
from lib.apps import OrganizerApp, TranscodeApp

logger = setup_logger("musicbox")



class MusicBoxApp:
    def __init__(self, config) -> None:
        self.config = config
        self.organizer = OrganizerApp(config)
        self.transcode = TranscodeApp(config)

    def run(self) -> None:
        while True:
            logger.info("\n请选择主功能：", extra={"plain": True})
            logger.info("  1. transcode", extra={"plain": True})
            logger.info("  2. media_ops", extra={"plain": True})
            logger.info("  #. 退出程序", extra={"plain": True})

            choice = input("请输入数字：").strip()

            if choice == "#":
                logger.info("退出程序", extra={"plain": True})
                return
            elif choice == "1":
                self.transcode.run()
            elif choice == "2":
                self.organizer.run()
            else:
                logger.info("输入不正确，请重新输入", extra={"plain": True})


def load_config() -> dict:
    config_path = Path("config.toml")
    if not config_path.exists():
        generate_config()

    with open(config_path, "rb") as f:
        return tomllib.load(f)


def main() -> None:
    config = load_config()
    app = MusicBoxApp(config)
    app.run()


if __name__ == "__main__":
    main()