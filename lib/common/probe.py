import subprocess, json
from pathlib import Path
from lib.common.log import setup_logger


logger = setup_logger()


def probe(file_p: Path) -> dict:
    try:
        if file_p.suffix == '.wv':
            cmd = ['wvunpack', '-s', file_p]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8')
            output = parse_wvunpack_output(result.stdout)
            return output
        else:
            cmd = ['exiftool', '-j', '-n', "-@", "-"]
            result = subprocess.run(cmd, input=str(file_p), capture_output=True,
                                    text=True, check=True, encoding='utf-8')
            return json.loads(result.stdout)[0]
    except subprocess.CalledProcessError as e:
        output = f"{e.stdout}\n{e.stderr}"
        if "Unknown file type" in output:
            return None
        else:
            logger.error(e.stderr)
            logger.error(e.stdout)
            return None

def parse_wvunpack_output(text: str) -> dict:
    result = {}

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # 跳过标题行
        if line.startswith("WVUNPACK"):
            continue
        if line.startswith("Copyright"):
            continue

        # 只处理 k:v 形式
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()

    return result
