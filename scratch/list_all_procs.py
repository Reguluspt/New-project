import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Search for any process containing "telegram_server" or "app.py" or "mail_listener"
cmd = ["powershell", "-NoProfile", "-Command", 
       "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*telegram_server*' -or $_.CommandLine -like '*mail_listener*' -or $_.CommandLine -like '*streamlit*' } | Select-Object ProcessId, ParentProcessId, Name, CommandLine | Format-List"]
try:
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    print(res.stdout)
except Exception as e:
    print("Error:", e)
