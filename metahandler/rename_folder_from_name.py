import os, re, sys
sys.path.append(os.path.dirname(os.getcwd()))
from lib.common_method import check_folder_file


def map_pattern():
    while True:
        pattern = input('选择匹配的正则表达式：\n'
                        '1、(.*) \\[.*?\\] (.*)\n'
                        '2、\\[(.*?)\\] (.*?) \\[.*?\\].*\n'
                        '3、\\[(.*?)\\]\\[.*?\\]\\[(.*?)\\].*\n'
                        '4、自定义\n'
                        '请输入数字：')
        if pattern == '1':
            pattern = r'(.*) \[.*?\] (.*)'
            return pattern
        elif pattern == '2':
            pattern = r'\[(.*?)\] (.*?) \[.*?\].*'
            return pattern
        elif pattern == '3':
            pattern = r'\[(.*?)\]\[.*?\]\[(.*?)\].*'
            return pattern
        elif pattern == '4':
            pattern = input("请输入正则表达式：")
            return pattern
        else:
            print('输入匹配模式不正确请重新输入')

print('提示输入路径的时候输入#可以更改正则表达式')
pattern = map_pattern()

while True:
    folder_path = input("请输入路径：")
    if folder_path == '#':
        pattern = map_pattern()
        continue
    for folder in os.listdir(folder_path):
        match = re.match(pattern, folder)
        if match:
            folder_full_path = os.path.join(folder_path, folder)
            suffix, label, best_info = check_folder_file(folder_full_path)
            orig_date = match.group(1)
            if '.'in orig_date:
                date = orig_date
            elif len(orig_date) == 6:
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