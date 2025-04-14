import musicbrainzngs, os, mutagen, sys

sys.path.append(os.path.dirname(os.getcwd()))

from lib.common_method import check_multi_result, check_input_folder_path


musicbrainzngs.set_useragent(
    "MyMusicApp",
    "1.0",
    "your@email.com"
)

folder_path = check_input_folder_path(is_double_check=False)

for dir in os.listdir(folder_path):
    base_path = os.path.join(folder_path, dir)
    if os.path.isdir(base_path):
        catno = None
        for file in os.listdir(base_path):
            if file.endswith(".flac"):
                audio = mutagen.File(os.path.join(base_path, file))
                catno = audio.tags.get('CATALOGNUMBER')
                break
        if catno:
            result = musicbrainzngs.search_releases(catno=catno[0] if isinstance(catno, list) else catno, limit=5)
            album_id = check_multi_result(result)
            if album_id:
                for file in os.listdir(base_path):
                    if file.endswith(".flac"):
                        audio = mutagen.File(os.path.join(base_path, file))
                        audio["MUSICBRAINZ_ALBUMID"] = album_id
                        audio.save()
                print(f"成功将albumid写入{base_path}下的音频")
            else:
                print('没有查询到结果')
        else:
            print('该文件夹下没有的音频没有搜索需要的元数据，请标上后再试')