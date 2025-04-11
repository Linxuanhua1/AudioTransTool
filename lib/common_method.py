import os


def check_input_folder_path(is_double_check=True):
    while True:
        folder_path = input('请输入文件夹：')
        if not os.path.isdir(folder_path):
            print('请输入文件夹，而不是文件')
            continue
        if not os.path.exists(folder_path):
            print('文件夹路径不存在，请重新输入文件夹')
            continue

        if is_double_check:
            is_start = input("请输入Y/N来确认是否是该文件夹：")
            if is_start.lower() == 'y':
                print(f'文件夹为：{folder_path}')
                break
        else:
            break
    return folder_path


def get_file_name_and_root(file_path):
    root, file = os.path.split(file_path)
    name, _ = os.path.splitext(file)
    return root, name