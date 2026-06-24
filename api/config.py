from pathlib import Path

# Re-use paths from src/app_config.py
try:
    from src.app_config import DATA_DIR, OUTPUT_DIR, ROOT
except ImportError:
    ROOT = Path(__file__).resolve().parent.parent
    DATA_DIR = ROOT / "data"
    OUTPUT_DIR = ROOT / "outputs"

class Config:
    SQLITE_DATABASE = DATA_DIR / "cases.db"
    RECORDS_DB = DATA_DIR / "telegram_records.db"
    CORS_ORIGINS = ["http://localhost:5173"]
