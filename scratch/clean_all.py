import subprocess
import os

print("--- EXTREME PURE-PYTHON PROCESS CLEANUP ---")

# Let's use PowerShell via clean list command (no cmd.exe parsing) to find and kill processes
# We'll kill all processes with command line containing src.telegram_server, src.mail_listener, or streamlit
targets = ["src.telegram_server", "src.mail_listener", "streamlit"]

# Find all python processes running these
cmd = ["powershell", "-NoProfile", "-Command", 
       "Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | Select-Object ProcessId, CommandLine | ConvertTo-Json"]

res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
if res.returncode == 0 and res.stdout.strip():
    try:
        procs = json = None
        import json
        procs = json.loads(res.stdout.strip())
        # Convert single dict to list if only one process returned
        if isinstance(procs, dict):
            procs = [procs]
            
        for proc in procs:
            pid = proc.get("ProcessId")
            cmdline = proc.get("CommandLine") or ""
            if not pid:
                continue
            
            # Avoid killing our current script process
            if str(pid) == str(os.getpid()):
                continue
                
            for target in targets:
                if target in cmdline:
                    print(f"Force killing PID {pid}: {cmdline}")
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                    break
    except Exception as e:
        print("Error parsing json:", e)
else:
    print("No python processes retrieved or powerShell failed:", res.stderr)

print("Cleanup completed.")
