import os, subprocess

folder = input("请输入路径")

for root, dirs, files in os.walk(folder):
    for file in files:
        if file.endswith(".tif"):
            file_path = os.path.join(root, file)
            name, _ = os.path.splitext(file)
            subprocess.run(['D:\Tools\ImageMagick-7.1.2-Q16-HDRI\magick.exe', file_path, os.path.join(root, f'{name}.png')])
            print(f'手动转换{file_path}成功')