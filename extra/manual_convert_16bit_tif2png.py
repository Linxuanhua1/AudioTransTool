import os
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed


def convert_tif_to_png(file_path):
    """单个文件转换函数"""
    root, file = os.path.split(file_path)
    name, _ = os.path.splitext(file)
    output_path = os.path.join(root, f"{name}.png")
    try:
        subprocess.run(['magick', file_path, output_path], check=True)
        return f"手动转换 {file_path} 成功"
    except subprocess.CalledProcessError as e:
        return f"转换 {file_path} 失败: {e}"

if __name__ == "__main__":
    folder = input("请输入路径：")

    # 收集所有.tif文件路径
    tif_files = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(".tif"):  # 小写更保险
                tif_files.append(os.path.join(root, file))

    # 使用进程池并行处理
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(convert_tif_to_png, f) for f in tif_files]

        for future in as_completed(futures):
            print(future.result())
