import os
import subprocess
import time
from pathlib import Path

def main():
    print("Aggressively cleaning up old bot processes using taskkill...")
    
    # 1. Try to kill by PID files first
    pid_files = ["telegram.pid", "data/mail_listener.pid"]
    for pf in pid_files:
        path = Path(pf)
        if path.exists():
            try:
                pid = path.read_text().strip()
                print(f"Killing PID {pid} from {pf}")
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                path.unlink()
            except Exception as e:
                print(f"Could not kill PID from {pf}: {e}")

    # 2. Kill all python processes that might be running our server
    # We look for processes running uvicorn src.telegram_server:app, src.mail_listener, or streamlit
    import json
    targets = ["src.telegram_server", "src.mail_listener", "streamlit"]
    cmd = ["powershell", "-NoProfile", "-Command", 
           "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | Select-Object ProcessId, CommandLine | ConvertTo-Json"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if res.returncode == 0 and res.stdout.strip():
        try:
            procs = json.loads(res.stdout.strip())
            if isinstance(procs, dict):
                procs = [procs]
            for proc in procs:
                pid = proc.get("ProcessId")
                cmdline = proc.get("CommandLine") or ""
                if not pid or str(pid) == str(os.getpid()):
                    continue
                for target in targets:
                    if target in cmdline:
                        print(f"Force killing PID {pid}: {cmdline}")
                        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                        break
        except Exception as e:
            print("Error cleaning up processes:", e)
    
    # Wait for ports to clear
    time.sleep(2)
    
    # 3. Restart using the project's background_services logic
    print("Starting services...")
    project_root = Path.cwd()
    os.environ["PYTHONIOENCODING"] = "utf-8"
    python_exe = str(project_root / ".venv" / "Scripts" / "python.exe")
    
    try:
        subprocess.run([python_exe, "-c", """
from dotenv import load_dotenv
from pathlib import Path
import sys
import os
sys.path.append(str(Path.cwd()))
load_dotenv(Path('API.env'))
load_dotenv(Path('.env'))
from src.background_services import ensure_background_services
print(ensure_background_services())
        """], check=True)
        print("Services started successfully.")
    except Exception as e:
        print(f"Failed to start services: {e}")
    
    print("Cleanup and restart complete.")

if __name__ == "__main__":
    main()
