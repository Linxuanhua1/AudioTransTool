from lib.audio_handler import AudioHandler, HANDLERS, Splitter
import os
import tomllib

with open("config.toml", 'rb') as f:
    config = tomllib.load(f)

aud_hdl = AudioHandler()

folder_path = input('请输入要转码的路径：')

for root, dirs, files in os.walk(folder_path):
    for file in files:
        audio_file_path = os.path.join(root, file)
        # 获取文件扩展名并调用对应的处理函数
        _, ext = os.path.splitext(audio_file_path)
        handler = HANDLERS.get(ext)  # 获取对应的处理函数

        if handler:
            if aud_hdl.is_audio_allowed_to_convert(audio_file_path):
                handler(audio_file_path)  # 调用处理函数

if config['activate_cue_splitting']:
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.flac'):
                file_path = os.path.join(root, file)
                Splitter.split_flac_with_cue(file_path)