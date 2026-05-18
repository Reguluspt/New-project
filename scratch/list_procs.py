import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

cmd = ["powershell", "-NoProfile", "-Command", 
       "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | Select-Object ProcessId, ParentProcessId, CommandLine | Format-List"]
try:
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    print(res.stdout)
except Exception as e:
    print("Error:", e)
