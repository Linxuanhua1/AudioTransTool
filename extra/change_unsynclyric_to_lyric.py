import mutagen, os

folder_path = input("请输入路径：")

for root, dirs, files in os.walk(folder_path):
    for file in files:
        if file.lower().endswith(".flac"):
            audio_path = os.path.join(root, file)
            print(f"正在处理文件{audio_path}")
            audio = mutagen.File(audio_path)
            if audio.tags:
                lyric = audio.get("UNSYNCEDLYRICS", None)
                if lyric:
                    audio["LYRICS"] = lyric
                    audio.pop('UNSYNCEDLYRICS')
                    print("成功将歌词从UNSYNCEDLYRICS改到LYRICS，并且删除UNSYNCEDLYRICS")
                else:
                    print('该音频文件没有歌词')
                audio.save()

print('完成更改')