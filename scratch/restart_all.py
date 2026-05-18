import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add current directory (root) to path
sys.path.append(str(Path.cwd()))

from src.background_services import ensure_background_services

if __name__ == "__main__":
    load_dotenv("API.env")
    res = ensure_background_services()
    print(f"Background services: {res}")
    
    # Start Streamlit if not running
    streamlit_port = os.getenv("STREAMLIT_PORT", "8501")
    streamlit_addr = os.getenv("STREAMLIT_ADDRESS", "0.0.0.0")
    python_exe = sys.executable
    
    # Simple check if already running (approximate)
    import subprocess
    try:
        # Check for streamlit process with app.py
        check_cmd = f"Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -like '*-m streamlit run app.py*' }} | Select-Object -ExpandProperty ProcessId"
        output = subprocess.check_output(["powershell", "-NoProfile", "-Command", check_cmd], text=True).strip()
        if output:
            print(f"Streamlit already running with PID: {output}")
        else:
            print("Starting Streamlit...")
            args = [python_exe, "-m", "streamlit", "run", "app.py", "--server.port", streamlit_port, "--server.address", streamlit_addr]
            # Use CREATE_NO_WINDOW (0x08000000)
            subprocess.Popen(args, creationflags=0x08000000, stdout=open("streamlit_stdout.log", "a"), stderr=open("streamlit_stderr.log", "a"))
            print("Streamlit started in background.")
    except Exception as e:
        print(f"Error starting streamlit: {e}")
