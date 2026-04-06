from lib.organizer.tag import separate_tag
from lib.organizer.folder import rename_folder_from_name, rename_folder_from_tag, write_catno_from_folder_name
from lib.organizer.remote import get_meta_from_musicbrainz, fetch_vgm_and_create_folder

ACTIONS = [
    ("分割音频的艺术家、专辑艺术家和编曲家",                   separate_tag),
    ("根据光盘编号从musicbrainz拉取数据",                    get_meta_from_musicbrainz),
    ("根据歌曲标签重命名文件夹",                               rename_folder_from_tag),
    ("提取文件夹名中的光盘编号写入音频标签",                  write_catno_from_folder_name),
    ("提取文件夹名重命名文件夹",                            rename_folder_from_name),
    ("从vgm拉取系列数据并创建对应文件夹",                    fetch_vgm_and_create_folder),
]


def run():
    while True:
        print("\n请选择操作：")
        for i, (name, _) in enumerate(ACTIONS, 1):
            print(f"  {i}. {name}")
        print("  #. 退出")

        choice = input("请输入数字：").strip()
        if choice == '#':
            print("退出")
            return
        if choice.isdigit() and 1 <= int(choice) <= len(ACTIONS):
            ACTIONS[int(choice) - 1][1]()
        else:
            print("输入不正确，请重新输入")
