import os
import shutil
import zipfile
import time
from pathlib import Path

def build_installer():
    # Paths
    PROJECT_ROOT = Path(__file__).parent.parent.absolute()
    BUILD_ROOT = PROJECT_ROOT / "build"
    APP_NAME = "ThamDinhGia"
    BUILD_DIR = BUILD_ROOT / APP_NAME
    ZIP_NAME = f"{APP_NAME}_v1.0_setup.zip"
    
    print(f"--- Starting build process ---")
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Build Directory: {BUILD_DIR}")
    
    # 1. Clean build directory if exists
    if BUILD_DIR.exists():
        print(f"Cleaning existing build directory...")
        for _ in range(3): # Try up to 3 times
            try:
                shutil.rmtree(BUILD_DIR)
                break
            except Exception as e:
                print(f"Warning: Could not clean build dir ({e}). Retrying in 1s...")
                time.sleep(1)
        else:
            print("Error: Failed to clean build directory. Please ensure no files are open.")
            # Move on anyway, we'll try to overwrite
    
    if not BUILD_DIR.exists():
        BUILD_DIR.mkdir(parents=True)
    
    # 2. Define exclusion rules
    EXCLUDE_DIRS = {
        '.git', '.venv', '__pycache__', '.pytest_cache', 
        'build', 'samples', 'design_stitch', 'docs', 'tests'
    }
    
    EXCLUDE_FILES = {
        'cases.db', 'telegram.pid', 'streamlit.pid', 
        'streamlit_stdout.log', 'streamlit_stderr.log',
        'telegram_stdout.log', 'telegram_stderr.log',
        'API.env', '.env', 'temp.txt', 'ngrok.exe'
    }
    
    EXCLUDE_PATTERNS = ['test_', 'scratch_', '.pyc', '.pid', '.log']

    def is_excluded(path: Path):
        # Check explicit exclusions
        if path.name in EXCLUDE_DIRS or path.name in EXCLUDE_FILES:
            return True
        # Check patterns
        for pattern in EXCLUDE_PATTERNS:
            if pattern in path.name:
                return True
        return False

    # 3. Copy files
    print(f"Copying files...")
    for item in PROJECT_ROOT.iterdir():
        if item.name == "build": # Skip build dir itself
            continue
            
        if is_excluded(item):
            continue
            
        target = BUILD_DIR / item.name
        
        try:
            if item.is_dir():
                # Special handling for data folder to keep structure but empty data
                if item.name == "data":
                    if not target.exists(): target.mkdir()
                    # Copy JSON configs only
                    for subitem in item.iterdir():
                        if subitem.suffix == ".json" and not is_excluded(subitem):
                            shutil.copy2(subitem, target / subitem.name)
                    # Ensure subdirs exist but empty
                    (target / "uploads").mkdir(exist_ok=True)
                    (target / "case_files").mkdir(exist_ok=True)
                    (target / "backups").mkdir(exist_ok=True)
                else:
                    if target.exists(): shutil.rmtree(target)
                    shutil.copytree(item, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.log', '*.pid'))
            else:
                shutil.copy2(item, target)
        except Exception as e:
            print(f"Warning: Skipped {item.name} due to error: {e}")

    # 4. Create necessary empty folders
    print(f"Ensuring empty directories...")
    (BUILD_DIR / "exports").mkdir(exist_ok=True)
    (BUILD_DIR / "logs").mkdir(exist_ok=True)
    (BUILD_DIR / "outputs").mkdir(exist_ok=True)
    
    # 5. Handle API.env.example if it exists
    env_example = PROJECT_ROOT / "API.env.example"
    if env_example.exists():
        shutil.copy2(env_example, BUILD_DIR / "API.env.example")

    # 6. Create ZIP archive
    print(f"Creating ZIP archive: {ZIP_NAME}...")
    zip_path = BUILD_ROOT / ZIP_NAME
    
    # Check if zip exists and is accessible
    if zip_path.exists():
        try:
            zip_path.unlink()
        except:
            print("Warning: Could not delete existing zip. Creating a new timestamped one.")
            ZIP_NAME = f"{APP_NAME}_v1.0_{int(time.time())}_setup.zip"
            zip_path = BUILD_ROOT / ZIP_NAME

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(BUILD_DIR):
            for file in files:
                file_path = Path(root) / file
                arcname = Path(APP_NAME) / file_path.relative_to(BUILD_DIR)
                zipf.write(file_path, arcname=arcname)
    
    print(f"\n--- Build complete! ---")
    print(f"Distribution ZIP created at: {zip_path}")
    print(f"Size: {zip_path.stat().st_size / (1024*1024):.2f} MB")
    print(f"\nINSTRUCTIONS FOR RECIPIENT:")
    print(f"1. Extract the ZIP file.")
    print(f"2. Run 'CaiDat.bat' first.")
    print(f"3. Run 'CauHinhBanDau.bat' to setup API keys.")
    print(f"4. Run 'KhoiDongHeThong.bat' to start the app.")

if __name__ == "__main__":
    build_installer()
