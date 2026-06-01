from __future__ import annotations

import asyncio
import unittest
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

import aiosqlite

from src.database_manager import (
    create_sobo_record,
    get_all_sobo_records,
    find_sobo_record_by_thread,
    update_sobo_record_status,
    update_sobo_record_note,
)
from src.mail_listener import (
    MailListenerSettings,
    process_incoming_email,
)

def _raw_sobo_reply(in_reply_to: str, subject: str) -> bytes:
    message = EmailMessage()
    message["From"] = "Nghiep Vu <nghiepvu@example.com>"
    message["Reply-To"] = "nghiepvu@example.com"
    message["To"] = "Bot <bot@cenvalue.vn>"
    message["Subject"] = f"Re: {subject}"
    message["Message-ID"] = "<sobo-reply-1@example.com>"
    message["In-Reply-To"] = in_reply_to
    message["References"] = in_reply_to
    message.set_content("Kết quả định giá sơ bộ tài sản: khoảng 5 tỷ đồng.")
    return message.as_bytes()


class SoboIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_and_get_sobo_record(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            
            # 1. Create a record
            record_payload = {
                "asset_type": "real_estate",
                "asset_sub_type": "single",
                "source": "VCB Gia Lai",
                "so_thua": "123",
                "so_to": "45",
                "dia_chi": "Pleiku, Gia Lai",
                "link": "https://maps.google.com/123",
                "email_recipient": "sobo.taynguyen@gmail.com",
                "outbound_subject": "[SƠ BỘ] - VCB Gia Lai - Thửa 123",
                "outbound_message_id": "<outbound-sobo-1@example.com>",
                "status": "PENDING",
                "note": "Cần gấp trong chiều",
                "equipment_name": "",
            }
            
            record_id = await create_sobo_record(db_path, record_payload)
            self.assertEqual(record_id, 1)
            
            # 2. Retrieve all records
            records = await get_all_sobo_records(db_path)
            self.assertEqual(len(records), 1)
            
            rec = records[0]
            self.assertEqual(rec["id"], 1)
            self.assertEqual(rec["asset_type"], "real_estate")
            self.assertEqual(rec["source"], "VCB Gia Lai")
            self.assertEqual(rec["so_thua"], "123")
            self.assertEqual(rec["status"], "PENDING")
            self.assertEqual(rec["note"], "Cần gấp trong chiều")
            
            # 3. Update status
            await update_sobo_record_status(db_path, 1, "RESPONDED")
            records = await get_all_sobo_records(db_path)
            self.assertEqual(records[0]["status"], "RESPONDED")
            self.assertIsNotNone(records[0]["responded_at"])
            
            # 4. Update note
            await update_sobo_record_note(db_path, 1, "Đã giục nghiệp vụ")
            records = await get_all_sobo_records(db_path)
            self.assertEqual(records[0]["note"], "Đã giục nghiệp vụ")

    async def test_find_sobo_record_by_thread_and_subject(self) -> None:
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
            
            # Test match by message_id
            match = await find_sobo_record_by_thread(
                db_path,
                ref_blob="<outbound-sobo-2@example.com>",
                subject="Re: [SƠ BỘ] - Máy móc thiết bị - Cẩu trục tháp"
            )
            self.assertIsNotNone(match)
            self.assertEqual(match["id"], 1)
            self.assertEqual(match["equipment_name"], "Cẩu trục tháp")
            
            # Test match by subject fallback
            match_sub = await find_sobo_record_by_thread(
                db_path,
                ref_blob="",
                subject="Re: [SƠ BỘ] - Máy móc thiết bị - Cẩu trục tháp"
            )
            self.assertIsNotNone(match_sub)
            self.assertEqual(match_sub["id"], 1)

    async def test_mail_listener_handles_sobo_reply_correctly(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            
            # Insert preliminary pending case
            record_payload = {
                "asset_type": "real_estate",
                "asset_sub_type": "single",
                "source": "KH Doanh nghiệp",
                "so_thua": "789",
                "so_to": "12",
                "dia_chi": "Đà Nẵng",
                "link": "https://maps.google.com/789",
                "email_recipient": "sobo.danang@gmail.com",
                "outbound_subject": "[SƠ BỘ] - KH Doanh nghiệp - Thửa 789",
                "outbound_message_id": "<outbound-sobo-3@example.com>",
                "status": "PENDING",
                "note": "",
                "equipment_name": "",
            }
            await create_sobo_record(db_path, record_payload)
            
            settings = MailListenerSettings(
                imap_host="imap.gmail.com",
                imap_port=993,
                imap_username="sender@gmail.com",
                imap_password="app-password",
                mailbox="INBOX",
                records_db_path=db_path,
                gemini_api_key="gemini",
                gemini_model="gemini-test",
                telegram_bot_token="token",
                telegram_chat_id="123",
                auto_reply_cc=[],
            )
            
            raw_email_bytes = _raw_sobo_reply("<outbound-sobo-3@example.com>", "[SƠ BỘ] - KH Doanh nghiệp - Thửa 789")
            
            with (
                patch("src.mail_listener.notify_telegram", AsyncMock()) as notify_mock,
                patch("src.mail_listener.append_listener_log") as log_mock,
            ):
                match = await process_incoming_email(
                    raw_email_bytes,
                    uid="101",
                    settings=settings
                )
                
            # Verify record updated
            records = await get_all_sobo_records(db_path)
            self.assertEqual(records[0]["status"], "RESPONDED")
            self.assertIsNotNone(records[0]["responded_at"])
            
            # Verify notification and logger
            notify_mock.assert_awaited_once()
            notify_content = notify_mock.await_args.args[1]
            self.assertIn("Thông báo phản hồi Sơ bộ", notify_content)
            self.assertIn("Thửa đất: 789", notify_content)
            self.assertIn("khoảng 5 tỷ đồng", notify_content)
            
            logged_events = [call.args[0] for call in log_mock.call_args_list]
            self.assertIn("sobo_responded", logged_events)
            self.assertIsNone(match) # process_incoming_email returns None on preliminary match


if __name__ == "__main__":
    unittest.main()
