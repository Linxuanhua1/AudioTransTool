import subprocess, os, mutagen
from collections import defaultdict

os.environ['PATH'] = os.environ['PATH'] + os.pathsep + os.path.dirname(os.getcwd()) + '/bin/'

#  fuck flac，我说怎么多了44个字节，原来是在这里猫着呢
def detect_multiple_wav_headers(audio_file, end_point=100):
    # 解码flac，得到wav数据
    if audio_file.endswith('.flac'):
        proc = subprocess.Popen(['flac', '-d', '--stdout', audio_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        wav_data, _ = proc.communicate()
        wav_data = wav_data[:end_point]
    elif audio_file.endswith('.wav'):
        with open(audio_file, 'rb') as f:
            wav_data = f.read(end_point)
    # 搜索所有 RIFF 头位置
    positions = []
    start = 0
    while True:
        pos = wav_data.find(b'RIFF', start)
        if pos == -1:
            break
        positions.append(pos)
        start = pos + 4
    print('-'*50)
    print(audio_file)
    # print(wav_data)
    # print(audio_file)
    if len(positions) > 1:
        print(f"检测到 {len(positions)} 个 WAV 头，可能有多余头文件")
        print("头文件位置：", positions)
        return True
    else:
        print("只检测到一个 WAV 头，正常")
        return False

def group_need_repair(flac_group_by_album_and_disc):
    need_repair_group = defaultdict(list)
    for group, tracks in flac_group_by_album_and_disc.items():
        if detect_multiple_wav_headers(tracks[0][1]):
            need_repair_group[group] = tracks
        # for track in tracks:
        #     if detect_multiple_wav_headers(track[1]):
        #         need_repair_group[group]= tracks
    return need_repair_group

def group_flac_by_folder(root_dir):
    flac_group_by_folder = defaultdict(list)  # key: 文件夹路径, value: flac文件列表
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith('.flac'):
                flac_group_by_folder[dirpath].append(os.path.join(dirpath, filename))
    return flac_group_by_folder

def second_group_flac_by_album_disc(flac_group_by_folder):  # 二次分类，把专辑名字和碟号相同的归为一类
    flac_group_by_album_and_disc = defaultdict(list)  # 假设一个文件夹下有很多个整轨拆分出来的或者专辑名不一样的，应该要单独处理
    for dirpath, file_paths in flac_group_by_folder.items():
        for file_path in file_paths:
            audio = mutagen.File(file_path)
            disc_num = audio.tags.get('DISCNUMBER')[0] if audio.tags.get('DISCNUMBER') else '1'
            album = audio.tags.get('ALBUM')[0]
            track_num = int(audio.tags.get('TRACKNUMBER')[0])
            flac_group_by_album_and_disc[f'{album}-disc{disc_num}'].append((track_num, file_path))

    # 对每个值排序，按照曲目号排序
    for key in flac_group_by_album_and_disc:
        flac_group_by_album_and_disc[key] = sorted(flac_group_by_album_and_disc[key], key=lambda x: x[0])

    return flac_group_by_album_and_disc

def repair_audio(need_repair_group):
    for group, tracks in need_repair_group.items():
        whole_track_origin = b''
        len_list = []
        for track in tracks:
            proc_decode = subprocess.Popen(['flac', '-d', '--stdout', track[1]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            wav_data, _ = proc_decode.communicate()
            pcm_data = wav_data[44:]
            len_list.append(len(pcm_data))
            whole_track_origin += pcm_data
        root, _ = os.path.split(tracks[0][1])
        whole_track_correct = whole_track_origin[44:]  # 去掉重复头

        for i in range(len(len_list)):
            track_path = tracks[i][1]
            _, file_name = os.path.split(track_path)
            name, ext = os.path.splitext(file_name)

            output_path = os.path.join(root, f'{name}-correct{ext}')

            print(output_path)
            cmd = [
                'flac', '--force-raw-format', '--sign=signed', '--endian=little',
                '--channels=2', '--sample-rate=44100', '--bps=16', '-',
                '--best', '--threads=16', '-o', output_path
            ]

            start = sum(len_list[:i])
            end = sum(len_list[:i + 1]) if i < len(len_list) - 1 else None
            data = whole_track_correct[start:end]

            proc_encode = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc_encode.communicate(input=data)
            source_audio = mutagen.File(track_path)
            target_audio = mutagen.File(output_path)

            for key, value in source_audio.tags.items():
                target_audio.tags[key] = value

            target_audio.save()

            os.remove(track_path)
            os.rename(output_path, track_path)

            if proc_encode.returncode != 0:
                print(f"Track {i} 编码失败：", err.decode(errors="ignore"))


def main():
    repair_path = input('请输入路径：')
    flac_group_by_folder = group_flac_by_folder(repair_path)
    flac_group_by_album_and_disc = second_group_flac_by_album_disc(flac_group_by_folder)
    need_repair_group = group_need_repair(flac_group_by_album_and_disc)
    if need_repair_group:
        is_repair = True if input("请输入Y/N，来选择是否要修复：").lower() == 'y' else False
        if is_repair:
            repair_audio(need_repair_group)
    #  第一步先判断整个文件夹下边的文件是否需要修复
    #  第二步记录一下需要修复的专辑文件夹，让用户确定
    #  第三步先读取音频的元数据，然后对音频先分组，一个碟号的放在一起
    #  重新读取解码音频到内存，然后输出设置是纯pcm流，记录除最后一个音轨的长度，按照

if __name__ == '__main__':
    while True:
        main()
    # file_path = r"C:\Users\Linxuanhua\Desktop\1\01. Last regrets (Girls in Tears mix).wav"
    # detect_multiple_wav_headers(file_path)