import subprocess, json
from pprint import pprint


log_p = r"C:\Users\Linxuanhua\Desktop\KICA-900.log"

cmd = ['cambia', '-p', log_p]
result = subprocess.run(cmd, capture_output=True, check=True, text=True, encoding="utf-8")

info = json.loads(result.stdout)

if info is None:
    print("Unknown")

ripper = info['parsed']['parsed_logs'][0]['ripper']
score = info['evaluation_combined'][0]['evaluations'][0]['score']
print(ripper, score)