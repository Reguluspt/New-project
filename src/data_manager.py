import os
import shutil
import zipfile
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Constants for Paths
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
DATA_DIR = PROJECT_ROOT / "data"
BACKUP_DIR = DATA_DIR / "backups"
EXPORTS_DIR = PROJECT_ROOT / "exports"
LOGS_DIR = PROJECT_ROOT / "logs"

# Files to include in full backup
DATABASE_FILES = [
    PROJECT_ROOT / "cases.db",  # Legacy/Root db if exists
    DATA_DIR / "cases.db",
    DATA_DIR / "telegram_records.db",
]

CONFIG_FILES = [
    PROJECT_ROOT / "API.env",
    PROJECT_ROOT / ".env",
    DATA_DIR / "ai_config.json",
    DATA_DIR / "case_output_config.json",
    DATA_DIR / "case_table_config.json",
    DATA_DIR / "template_config.json",
    DATA_DIR / "mail_listener_state.json",
]

DATA_FOLDERS = [
    DATA_DIR / "case_files",
    DATA_DIR / "uploads",
]

def ensure_backup_dir():
    """Ensure the backup directory exists."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def get_existing_db_files():
    """Returns a list of database files that actually exist on disk."""
    return [f for f in DATABASE_FILES if f.exists()]

def get_existing_config_files():
    """Returns a list of config files that actually exist on disk."""
    return [f for f in CONFIG_FILES if f.exists()]

def create_backup(include_folders: bool = False) -> str:
    """
    Creates a zip backup of databases, configs, and optionally data folders.
    Returns the path to the created zip file.
    """
    ensure_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"backup_{timestamp}.zip"
    zip_path = BACKUP_DIR / zip_name

    files_to_back_up = get_existing_db_files() + get_existing_config_files()
    
    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add files
            for file_path in files_to_back_up:
                # Store relative to PROJECT_ROOT to maintain structure or just flat
                # Let's keep a simple structure: db/ for databases, config/ for env/json
                arcname = file_path.relative_to(PROJECT_ROOT)
                zipf.write(file_path, arcname=arcname)
            
            # Add folders if requested
            if include_folders:
                for folder in DATA_FOLDERS:
                    if folder.exists():
                        for root, _, files in os.walk(folder):
                            for file in files:
                                file_full_path = Path(root) / file
                                arcname = file_full_path.relative_to(PROJECT_ROOT)
                                zipf.write(file_full_path, arcname=arcname)
        
        logger.info(f"Backup created successfully: {zip_path}")
        return str(zip_path)
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        if zip_path.exists():
            zip_path.unlink()
        raise

def get_backup_bytes(zip_path: str) -> bytes:
    """Read a backup file and return its content as bytes."""
    with open(zip_path, "rb") as f:
        return f.read()

def list_backups():
    """List all available backups in the backup directory, sorted by date."""
    if not BACKUP_DIR.exists():
        return []
    backups = list(BACKUP_DIR.glob("backup_*.zip"))
    backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return backups

def restore_backup(zip_stream) -> bool:
    """
    Restores data from an uploaded zip file stream.
    Safely backs up current data before overwriting.
    """
    import tempfile
    
    temp_extract_dir = Path(tempfile.mkdtemp())
    temp_pre_restore_dir = Path(tempfile.mkdtemp())
    
    success = False
    try:
        # 1. Create a "pre-restore" backup of current critical files just in case
        critical_files = get_existing_db_files() + get_existing_config_files()
        for f in critical_files:
            rel_path = f.relative_to(PROJECT_ROOT)
            backup_target = temp_pre_restore_dir / rel_path
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, backup_target)
            
        # 2. Extract uploaded zip to temp dir
        with zipfile.ZipFile(zip_stream, 'r') as zipf:
            zipf.extractall(temp_extract_dir)
            
        # 3. Validate - basic check for critical db files
        # We expect at least data/cases.db or cases.db to exist in the zip
        extracted_files = list(temp_extract_dir.rglob("*.db"))
        if not extracted_files:
            raise ValueError("No database files found in the backup zip.")
            
        # 4. Overwrite existing files from extracted content
        # We iterate over everything extracted and move it to PROJECT_ROOT
        for root, _, files in os.walk(temp_extract_dir):
            for file in files:
                source_path = Path(root) / file
                rel_path = source_path.relative_to(temp_extract_dir)
                target_path = PROJECT_ROOT / rel_path
                
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy and overwrite
                shutil.copy2(source_path, target_path)
        
        logger.info("Restore completed successfully.")
        success = True
        return True

    except Exception as e:
        logger.error(f"Restore failed: {e}")
        # Rollback: Copy back from pre-restore backup
        try:
            logger.info("Attempting rollback...")
            for root, _, files in os.walk(temp_pre_restore_dir):
                for file in files:
                    source_path = Path(root) / file
                    rel_path = source_path.relative_to(temp_pre_restore_dir)
                    target_path = PROJECT_ROOT / rel_path
                    shutil.copy2(source_path, target_path)
            logger.info("Rollback successful.")
        except Exception as rb_e:
            logger.critical(f"Rollback FAILED: {rb_e}")
            
        raise e
    finally:
        # Clean up temp dirs
        shutil.rmtree(temp_extract_dir, ignore_errors=True)
        shutil.rmtree(temp_pre_restore_dir, ignore_errors=True)

def wipe_all_data(include_logs: bool = False) -> bool:
    """
    Wipes all data from databases and optionally clears exports and logs.
    Keeps the database schema (tables) intact.
    """
    import sqlite3
    
    db_files = get_existing_db_files()
    
    try:
        for db_path in db_files:
            logger.info(f"Wiping database: {db_path}")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                logger.info(f"Deleting all rows from table: {table}")
                cursor.execute(f"DELETE FROM {table};")
                # Reset autoincrement
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}';")
            
            conn.commit()
            conn.close()
            
        # Clear exports folder
        if EXPORTS_DIR.exists():
            logger.info(f"Purging exports directory: {EXPORTS_DIR}")
            for item in EXPORTS_DIR.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
                    
        # Clear logs if requested
        if include_logs and LOGS_DIR.exists():
            logger.info(f"Purging logs directory: {LOGS_DIR}")
            for item in LOGS_DIR.iterdir():
                if item.is_file() and item.suffix == '.log':
                    item.unlink()
                    
        logger.info("Wipe data completed successfully.")
        return True
        
    except Exception as e:
        logger.error(f"Wipe data failed: {e}")
        raise e
