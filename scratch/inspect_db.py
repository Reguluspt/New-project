import sqlite3
from pathlib import Path

def inspect_targeted():
    output_lines = []
    
    cases_db = "c:/Users/Truon/Documents/New project/data/cases.db"
    records_db = "c:/Users/Truon/Documents/New project/data/telegram_records.db"
    
    # Check cases.db
    if Path(cases_db).exists():
        output_lines.append(f"\n======================================")
        output_lines.append(f"INSPECTING: {cases_db}")
        conn = sqlite3.connect(cases_db)
        conn.row_factory = sqlite3.Row
        
        # Query cases table for IDs 1231, 1232
        row_1231 = conn.execute("SELECT * FROM cases WHERE id = 1231").fetchone()
        row_1232 = conn.execute("SELECT * FROM cases WHERE id = 1232").fetchone()
        
        if row_1231:
            output_lines.append("Found Case 1231:")
            output_lines.append(f"  {dict(row_1231)}")
        else:
            output_lines.append("Case 1231 not found.")
            
        if row_1232:
            output_lines.append("Found Case 1232:")
            output_lines.append(f"  {dict(row_1232)}")
        else:
            output_lines.append("Case 1232 not found.")
            
        # Let's also see if there's any case with telegram_record_id = '813' or '845'
        rows_by_tg = conn.execute("SELECT * FROM cases WHERE telegram_record_id IN ('813', '845', 813, 845)").fetchall()
        if rows_by_tg:
            output_lines.append(f"Found {len(rows_by_tg)} cases matching Telegram record IDs '813' or '845':")
            for r in rows_by_tg:
                output_lines.append(f"  {dict(r)}")
        else:
            output_lines.append("No cases found matching Telegram record IDs 813 or 845 in cases table.")
            
        conn.close()
        
    # Check telegram_records.db
    if Path(records_db).exists():
        output_lines.append(f"\n======================================")
        output_lines.append(f"INSPECTING: {records_db}")
        conn = sqlite3.connect(records_db)
        conn.row_factory = sqlite3.Row
        
        # Query records table for IDs 813, 845
        row_813 = conn.execute("SELECT * FROM records WHERE id = 813").fetchone()
        row_845 = conn.execute("SELECT * FROM records WHERE id = 845").fetchone()
        
        if row_813:
            output_lines.append("Found Telegram Record 813:")
            output_lines.append(f"  {dict(row_813)}")
        else:
            output_lines.append("Telegram Record 813 not found.")
            
        if row_845:
            output_lines.append("Found Telegram Record 845:")
            output_lines.append(f"  {dict(row_845)}")
        else:
            output_lines.append("Telegram Record 845 not found.")
            
        # Let's query recent 10 records to see what the IDs are
        recent_records = conn.execute("SELECT * FROM records ORDER BY id DESC LIMIT 10").fetchall()
        output_lines.append("Recent 10 Telegram records:")
        for r in recent_records:
            output_lines.append(f"  ID: {r['id']} | Customer: {r['customer_info']} | Created At: {r['created_at']}")
            
        conn.close()
        
    Path("scratch/output.txt").write_text("\n".join(output_lines), encoding="utf-8")
    print("Done! Output written to scratch/output.txt")

if __name__ == '__main__':
    inspect_targeted()
