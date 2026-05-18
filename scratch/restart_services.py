from dotenv import load_dotenv
from pathlib import Path
import os
import sys

# Add src to path
sys.path.append(str(Path.cwd()))

def main():
    load_dotenv(Path('API.env'))
    load_dotenv(Path('.env'))
    from src.background_services import ensure_background_services
    results = ensure_background_services()
    print(f"Restarted services: {results}")

if __name__ == "__main__":
    main()
