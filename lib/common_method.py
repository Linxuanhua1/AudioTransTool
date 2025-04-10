import os


def get_file_name_and_root(file_path):
    root, file = os.path.split(file_path)
    name, _ = os.path.splitext(file)
    return root, name