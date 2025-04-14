import os, sys, mutagen
sys.path.append(os.path.dirname(os.getcwd()))
from lib.common_method import check_folder_file, custom_safe_filename


while True:
    folder_path = input("请输入路径：")

    for folder in os.listdir(folder_path):
        folder_full_path = os.path.join(folder_path, folder)
        suffix, label, best_info = check_folder_file(folder_full_path, label='Amazon')
        for file in os.listdir(folder_full_path):
            if file.lower().endswith(".flac"):
                audio = mutagen.File(os.path.join(folder_full_path, file))
                date = '.'.join(audio.tags['DATE'][0][:10].split("-"))
                album = custom_safe_filename(audio.tags['ALBUM'][0].replace("THE IDOLM@STER CINDERELLA ", ""))
                break

        new_folder_name = f"[{date}][{label}][{album}][{best_info[0]}{best_info[1]}]{suffix}"
        new_folder_full_path = os.path.join(folder_path, new_folder_name)
        print(f"旧文件夹名：{folder}")
        print(f"新文件夹名：{new_folder_name}")
        os.rename(folder_full_path, new_folder_full_path)
