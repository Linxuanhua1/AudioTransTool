import os, sys, mutagen
sys.path.append(os.path.dirname(os.getcwd()))
from lib.common_method import check_input_folder_path

while True:
    folder_path = check_input_folder_path(is_double_check=False)
    for folder in os.listdir(folder_path):
        base_folder = os.path.join(folder_path, folder)
        if os.path.isdir(base_folder):
            for file in os.listdir(base_folder):
                if file.endswith(('.txt', '.log')):
                    name, ext = os.path.splitext(file)
                    catno = name

