from lib.audio_handler import AudioHandler, HANDLERS, Splitter, EXCLUDED_DIRS
from lib.common_method import check_input_folder_path
import os
import tomllib
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

with open("lib/config.toml", 'rb') as f:
    config = tomllib.load(f)

aud_hdl = AudioHandler()

folder_path = check_input_folder_path()

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
