import os
import sys
from pathlib import Path
import shutil

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.data_manager import create_backup, get_backup_bytes, restore_backup, wipe_all_data, list_backups
from src.sqlite_store import init_db, add_organization

def test_data_manager_workflow():
    print("--- Testing Data Manager Workflow ---")
    
    # 1. Setup dummy data
    db_path = Path("data/cases.db")
    init_db(db_path)
    org_id = add_organization(db_path, {"name": "Test Org", "tax_code": "123456"})
    print(f"Added test organization ID: {org_id}")
    
    # 2. Test Backup
    print("\nTesting Backup...")
    backup_path = create_backup(include_folders=False)
    print(f"Backup created at: {backup_path}")
    assert Path(backup_path).exists()
    
    # 3. Test Wipe
    print("\nTesting Wipe...")
    try:
        wipe_all_data(include_logs=True)
    except Exception as e:
        print(f"Wipe logs warning (ignoring): {e}")
        wipe_all_data(include_logs=False)
    import sqlite3
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM organizations").fetchone()[0]
    conn.close()
    print(f"Organization count after wipe: {count}")
    assert count == 0
    
    # 4. Test Restore
    print("\nTesting Restore...")
    with open(backup_path, "rb") as f:
        success = restore_backup(f)
    print(f"Restore success: {success}")
    
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM organizations").fetchone()[0]
    conn.close()
    print(f"Organization count after restore: {count}")
    assert count > 0
    
    print("\n--- All Data Manager Tests Passed! ---")

if __name__ == "__main__":
    try:
        test_data_manager_workflow()
    except Exception as e:
        print(f"Test FAILED: {e}")
        import traceback
        traceback.print_exc()
