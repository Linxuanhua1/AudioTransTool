from lib.audio_handler import AudioHandler, HANDLERS, Splitter, EXCLUDED_DIRS
import os
import tomllib
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)


with open("config.toml", 'rb') as f:
    config = tomllib.load(f)

aud_hdl = AudioHandler()

is_path = False

while not is_path:
    logger.info('请输出要转码的文件夹：')
    folder_path = input()
    if not os.path.isdir(folder_path):
        logger.info('请输入文件夹，而不是文件')
        continue
    if not os.path.exists(folder_path):
        logger.info('文件夹路径不存在，请重新输入文件夹')
        continue
    logger.info("请输入Y/N来确认是否是该文件夹：")
    is_start = input()
    if is_start.lower() == 'y':
        logger.info(f'转码文件夹为：{folder_path}')
        is_path = True

logger.info('开始转码')
for root, dirs, files in os.walk(folder_path):
    [dirs.remove(d) for d in list(dirs) if d.lower() in EXCLUDED_DIRS]
    for file in files:
        audio_file_path = os.path.join(root, file)
        # 获取文件扩展名并调用对应的处理函数
        _, ext = os.path.splitext(audio_file_path)
        handler = HANDLERS.get(ext)  # 获取对应的处理函数

        if handler:
            if aud_hdl.is_audio_allowed_to_convert(audio_file_path):
                logger.info(f'即将处理音频{audio_file_path}')
                handler(audio_file_path, config['is_delete_origin_audio'])  # 调用处理函数

if config['activate_cue_splitting']:
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.flac'):
                file_path = os.path.join(root, file)
                Splitter.split_flac_with_cue(file_path, config['is_delete_single_track'])