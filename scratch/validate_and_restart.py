import sys
import py_compile
import subprocess
from pathlib import Path

def main():
    project_root = Path.cwd()
    src_dir = project_root / "src"
    
    print("Validating syntax...")
    files_to_check = list(src_dir.glob("*.py")) + [project_root / "main.py"]
    
    all_ok = True
    for f in files_to_check:
        try:
            py_compile.compile(str(f), doraise=True)
        except py_compile.PyCompileError as e:
            print(f"Syntax error in {f.name}: {e}")
            all_ok = False
    
    if not all_ok:
        print("Validation failed. Aborting restart.")
        sys.exit(1)
        
    print("Syntax OK. Proceeding to aggressive restart...")
    
    python_exe = str(project_root / ".venv" / "Scripts" / "python.exe")
    restart_script = str(project_root / "scratch" / "aggressive_restart.py")
    
    subprocess.run([python_exe, restart_script], check=True)
    print("Validation and restart complete.")

if __name__ == "__main__":
    main()
