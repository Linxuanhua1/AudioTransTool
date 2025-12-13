import os

path1 = r'D:\Coding Programme\amazon-music\downloads\converted\3\[2025.04.23][Amazon][Our Chant][24bit96kHz][flac]'
path2 = r'D:\Coding Programme\amazon-music\downloads\converted\3\Our Chant'

pcmdata1 = b''
pcmdata2 = b''
flag = True
for file in os.listdir(path1):
    with open(os.path.join(path1, file), 'rb') as f:
        tmp = f.read()
        # if flag:
        #     flag = False
        #     pcmdata1 += tmp[88:]
        # else:
        pcmdata1 += tmp[44:]

for file in os.listdir(path2):
    with open(os.path.join(path2, file), 'rb') as f:
        tmp = f.read()
        pcmdata2 += tmp[44:]

print(len(pcmdata1), len(pcmdata2))

def print_diff_bytes(data1, data2):
    length = min(len(data1), len(data2))
    diff_count = 0
    for i in range(length):
        if data1[i] != data2[i]:
            print(f"Byte {i}: data1=0x{data1[i]:02x}, data2=0x{data2[i]:02x}")
            diff_count += 1
            if diff_count >= 20:  # 限制打印数量防止太多
                print("...还有更多不同字节，停止打印")
                break
    if diff_count == 0 and len(data1) == len(data2):
        print("两个数据完全相同")
    elif diff_count == 0:
        print(f"前{length}字节相同，但长度不同，data1长度={len(data1)}, data2长度={len(data2)}")

print_diff_bytes(pcmdata1, pcmdata2)