import subprocess, json, logging
from pathlib import Path


logger = logging.getLogger(__name__)


def probe(file_path: Path):
    cmd = ['exiftool', '-j', '-n', "-@", "-"]
    try:
        result = subprocess.run(cmd, input=str(file_path), capture_output=True,
                                text=True, check=True, encoding='utf-8')
        return json.loads(result.stdout)[0]
    except subprocess.CalledProcessError as e:
        logger.error(e.stderr)
        return None