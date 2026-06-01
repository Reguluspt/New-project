import asyncio
import aiosqlite
from pathlib import Path
from tempfile import TemporaryDirectory
from src.database_manager import create_sobo_record, find_sobo_record_by_thread, _normalize_subject, _like_pattern

async def main():
    with TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "records.db")
        
        record_payload = {
            "asset_type": "machinery",
            "asset_sub_type": "",
            "source": "KH Cá nhân",
            "so_thua": "",
            "so_to": "",
            "dia_chi": "",
            "link": "",
            "email_recipient": "sobo.danang@gmail.com",
            "outbound_subject": "[SƠ BỘ] - Máy móc thiết bị - Cẩu trục tháp",
            "outbound_message_id": "<outbound-sobo-2@example.com>",
            "status": "PENDING",
            "note": "",
            "equipment_name": "Cẩu trục tháp",
        }
        await create_sobo_record(db_path, record_payload)
        
        subject = "Re: [SƠ BỘ] - Máy móc thiết bị - Cẩu trục tháp"
        norm = _normalize_subject(subject)
        like_pat = _like_pattern(norm)
        
        print("Normalized subject:", repr(norm))
        print("Like pattern:", repr(like_pat))
        
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM sobo_records")
            row = await cursor.fetchone()
            print("DB outbound_subject:", repr(row["outbound_subject"]))
            print("DB outbound_message_id:", repr(row["outbound_message_id"]))
            
            # Try matching step-by-step
            cursor = await db.execute(
                "SELECT * FROM sobo_records WHERE outbound_subject IS NOT NULL"
            )
            rows = await cursor.fetchall()
            print("Total rows:", len(rows))
            
            # Test LIKE
            cursor = await db.execute(
                "SELECT * FROM sobo_records WHERE LOWER(outbound_subject) LIKE ?", (like_pat,)
            )
            print("LIKE without ESCAPE:", await cursor.fetchone() is not None)
            
            # Test LIKE with ESCAPE
            cursor = await db.execute(
                "SELECT * FROM sobo_records WHERE LOWER(outbound_subject) LIKE ? ESCAPE '\\'", (like_pat,)
            )
            print("LIKE with ESCAPE '\\':", await cursor.fetchone() is not None)
            
        match = await find_sobo_record_by_thread(db_path, ref_blob="", subject=subject)
        print("Match result:", match)

if __name__ == "__main__":
    asyncio.run(main())
