import os, re, sys
sys.path.append(os.path.dirname(os.getcwd()))
from lib.common_method import check_folder_file


while True:
    folder_path = input("请输入路径：")

    # pattern = r'(.*) \[.*?\] (.*)'
    pattern = r'\[(.*?)\] (.*) \['

    for folder in os.listdir(folder_path):
        match = re.match(pattern, folder)
        if match:
            folder_full_path = os.path.join(folder_path, folder)
            suffix, label, best_info = check_folder_file(folder_full_path)
            orig_date = match.group(1)
            if len(orig_date) == 6:
                prefix = "19" if int(orig_date[:2]) > 50 else "20"
                date = f'{prefix}{orig_date[:2]}.{orig_date[2:4]}.{orig_date[4:]}'
            else:
                date = f'{orig_date[:4]}.{orig_date[4:6]}.{orig_date[6:]}'
            if best_info[0] == 'N/A':
                new_folder_name = f"[{date}][{label}][{match.group(2)}][{best_info[1]}]{suffix}"
            else:
                new_folder_name = f"[{date}][{label}][{match.group(2)}][{best_info[0]}{best_info[1]}]{suffix}"
            new_folder_full_path = os.path.join(folder_path, new_folder_name)
            print(f"旧文件夹名：{folder}")
            print(f"新文件夹名：{new_folder_name}")
            os.rename(folder_full_path, new_folder_full_path)
        else:
            # print(f"no match for {folder}")
            pass