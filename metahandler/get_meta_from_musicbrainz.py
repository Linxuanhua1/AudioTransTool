import musicbrainzngs, os, mutagen

os.environ['path'] = os.environ['PATH'] + os.pathsep + os.path.dirname(os.getcwd())

from lib.common_method import get_file_name_and_root, check_multi_result, check_input_folder_path


musicbrainzngs.set_useragent(
    "MyMusicApp",
    "1.0",
    "your@email.com"
)

folder_path = check_input_folder_path(is_double_check=False)

for dir in os.listdir(folder_path):
    base_dir = os.path.join(folder_path, dir)
    if os.path.isdir(base_dir):
        catno = None
        for file in os.listdir(base_dir):
            if file.endswith(".flac"):
                audio = mutagen.File(os.path.join(dir, file))
                catno = audio.tags.get('CATALOGNUMBER')
                break
        if catno:
            # 假设我们搜索 catalog number 为 "TOCP-53510"
            result = musicbrainzngs.search_releases(catno=catno, limit=5)

            release = check_multi_result(result)

            if release:
                print(release)
            else:
                print('没有结果')
        else:
            print('该文件夹下没有的音频没有搜索需要的元数据，请标上后再试')