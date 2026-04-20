import subprocess


cmd = r'python -m nuitka --follow-imports --standalone --include-package=chardet .\musicbox.py'

result = subprocess.run(cmd, check=True, text=True, encoding='utf-8')

subprocess.run(r"robocopy .\bin .\musicbox.dist\bin /E")