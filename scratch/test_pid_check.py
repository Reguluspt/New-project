from pathlib import Path
import sys
import subprocess
import os

sys.path.append(str(Path.cwd()))
from src.background_services import _is_pid_running, _read_pid, _find_running_pid_by_hint

print("Checking telegram:")
pid = _read_pid(Path("telegram.pid"))
hint = "src.telegram_server:app"
is_run = _is_pid_running(pid, hint)
discovered = _find_running_pid_by_hint(hint)
print(f"PID: {pid}, Hint: {hint}, IsRunning: {is_run}, Discovered: {discovered}")

print("\nChecking streamlit:")
pid = _read_pid(Path("streamlit.pid"))
hint = "streamlit run app.py"
is_run = _is_pid_running(pid, hint)
discovered = _find_running_pid_by_hint(hint)
print(f"PID: {pid}, Hint: {hint}, IsRunning: {is_run}, Discovered: {discovered}")

print("\nChecking mail_listener:")
pid = _read_pid(Path("data/mail_listener.pid"))
hint = "src.mail_listener"
is_run = _is_pid_running(pid, hint)
discovered = _find_running_pid_by_hint(hint)
print(f"PID: {pid}, Hint: {hint}, IsRunning: {is_run}, Discovered: {discovered}")
