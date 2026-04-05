import subprocess, json
from pathlib import Path
from lib.log import setup_logger


logger = setup_logger()


def probe(file_path: Path):
    cmd = ['exiftool', '-j', '-n', "-@", "-"]
    try:
        result = subprocess.run(cmd, input=str(file_path), capture_output=True,
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