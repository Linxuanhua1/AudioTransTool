import re, os, sys
sys.path.append(os.path.dirname(os.getcwd()))
from lib.common_method import check_input_folder_path, unfold_catno, fold_catno
import mutagen


print('提示输入路径的时候输入#可以更改正则表达式')
pattern = input('请输入匹配的正则表达式：')

while True:
    folder_path = check_input_folder_path(is_double_check=False)
    if folder_path == '#':
        pattern = input('请输入匹配的正则表达式：')
        continue
    # 可选模板
    # \[.*?\] .*? \[(.*?)\]
    # .*\[(.*?)\].*
    print('-' * 50)
    for folder in os.listdir(folder_path):
        base_folder = os.path.join(folder_path, folder)
        if os.path.isdir(base_folder):
            result = re.match(pattern, folder)
            if result:
                log_count = 0
                catno = result.group(1)
                if "~" in catno:
                    catno = unfold_catno(catno)
                print(f'为{base_folder}下的音频写入光盘编号')
                for file in os.listdir(base_folder):
                    if file.endswith(('.flac', '.dsf', '.wav')):
                        audio = mutagen.File(os.path.join(base_folder, file))
                        audio['CATALOGNUMBER'] = catno
                        audio.save()
                    elif file.endswith('.log'):
                        log_count += 1
                        tmp_log_path = os.path.join(base_folder, file)
                if log_count == 1:
                    _, file = os.path.split(tmp_log_path)
                    if file != f'{catno}.log':
                        os.rename(tmp_log_path, os.path.join(base_folder, f'{catno}.log'))
                        print(f'将{file}改名为{catno}.log')
                    else:
                        print(f'{file}无需改名')
                elif log_count > 1:
                    print(f'文件夹下有多个log文件不进行重命名，请手动复核')
                else:
                    catno = fold_catno(catno) if isinstance(catno, list) else catno
                    txt_path = os.path.join(base_folder, f'{catno}.txt')
                    if not os.path.exists(txt_path):
                        with open(os.path.join(base_folder, f'{catno}.txt'), 'w') as f:
                            f.write("")
                        print(f'因文件夹下没有log文件在文件夹下创建了{catno}.txt')
                    else:
                        print(f'当前路径下已有{catno}.txt')
                print(f'完成写入')
                print('-' * 50)
            else:
                pass
