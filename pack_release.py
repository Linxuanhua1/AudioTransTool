import subprocess, chardet
from pathlib import Path

bin_path = str(Path(chardet.__file__).parent / "models" / "*.bin")
cmd = (f'python -m nuitka --follow-imports --standalone --include-package=chardet --include-package-data=chardet'
       f' --include-data-files="{bin_path}"=chardet/models/ ./musicbox.py')

result = subprocess.run(cmd, check=True, text=True, encoding='utf-8')

subprocess.run(r"robocopy .\bin .\musicbox.dist\bin /E")