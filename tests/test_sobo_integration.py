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
    delete_sobo_record,
    get_all_sobo_records,
    find_sobo_record_by_thread,
    update_sobo_record_status,
    update_sobo_record_note,
    sync_telegram_records_to_sobo,
)
from src.mail_listener import (
    MailListenerSettings,
    process_incoming_email,
    parse_sobo_subject,
    clean_sobo_reply_subject,
    extract_maps_link,
    sync_sobo_emails_from_mailbox,
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

            # 5. Delete record
            await delete_sobo_record(db_path, 1)
            records = await get_all_sobo_records(db_path)
            self.assertEqual(records, [])

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

    async def test_create_sobo_record_preserves_historical_timestamps(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await create_sobo_record(
                db_path,
                {
                    "created_at": "2026-06-01 10:00:00",
                    "asset_type": "real_estate",
                    "outbound_sent_at": "2026-06-01 10:00:00",
                    "responded_at": "2026-06-01 11:30:00",
                    "status": "RESPONDED",
                },
            )

            records = await get_all_sobo_records(db_path)

            self.assertEqual(records[0]["created_at"], "2026-06-01 10:00:00")
            self.assertEqual(records[0]["outbound_sent_at"], "2026-06-01 10:00:00")
            self.assertEqual(records[0]["responded_at"], "2026-06-01 11:30:00")

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

    async def test_sync_telegram_records_to_sobo(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            
            # Initialize both tables by connecting/calling helper
            await ensure_tracking_schema(db_path)
            
            async with aiosqlite.connect(db_path) as db:
                # Create records table manually or let database_manager do it.
                # Since records schema is created dynamically, we can just insert a sample row
                await db.execute(
                    "CREATE TABLE IF NOT EXISTS records ("
                    "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                    "  asset_type TEXT,"
                    "  so_thua TEXT,"
                    "  so_to TEXT,"
                    "  dia_chi TEXT,"
                    "  source TEXT,"
                    "  preliminary_status TEXT,"
                    "  outbound_message_id TEXT,"
                    "  outbound_subject TEXT,"
                    "  outbound_sent_at TEXT,"
                    "  status TEXT,"
                    "  personal_note TEXT,"
                    "  created_at TEXT"
                    ")"
                )
                await db.execute(
                    "INSERT INTO records ("
                    "  asset_type, so_thua, so_to, dia_chi, source, preliminary_status,"
                    "  outbound_message_id, outbound_subject, status, personal_note, created_at"
                    ") VALUES ("
                    "  'real_estate', '101', '50', 'Hanoi', 'BIDV', 'Sơ bộ',"
                    "  '<msg-sync-1@example.com>', '[SƠ BỘ] - BIDV - Thửa 101', 'PENDING', 'Gấp lắm', '2026-06-01 10:00:00'"
                    ")"
                )
                await db.commit()
            
            # 1. First sync should sync 1 record
            synced = await sync_telegram_records_to_sobo(db_path)
            self.assertEqual(synced, 1)
            
            # 2. Second sync should sync 0 (already exists)
            synced_again = await sync_telegram_records_to_sobo(db_path)
            self.assertEqual(synced_again, 0)
            
            # 3. Verify values inside sobo_records
            sobo_recs = await get_all_sobo_records(db_path)
            self.assertEqual(len(sobo_recs), 1)
            rec = sobo_recs[0]
            self.assertEqual(rec["outbound_message_id"], "<msg-sync-1@example.com>")
            self.assertEqual(rec["so_thua"], "101")
            self.assertEqual(rec["dia_chi"], "Hanoi")
            self.assertEqual(rec["status"], "PENDING")
            self.assertEqual(rec["note"], "Gấp lắm")

    def test_parse_sobo_subject(self) -> None:
        # Test real estate single
        res1 = parse_sobo_subject("[SƠ BỘ] - VCB Gia Lai - Thửa đất số 72, tờ bản đồ số 13; tại địa chỉ Pleiku")
        self.assertIsNotNone(res1)
        self.assertEqual(res1["source"], "VCB Gia Lai")
        self.assertEqual(res1["so_thua"], "72")
        self.assertEqual(res1["so_to"], "13")
        self.assertEqual(res1["dia_chi"], "Pleiku")
        self.assertEqual(res1["asset_sub_type"], "single")

        # Test real estate multi
        res2 = parse_sobo_subject("[SƠ BỘ] - BIDV - Thửa đất số 101 + 102, tờ bản đồ số 5; tại địa chỉ Hanoi")
        self.assertIsNotNone(res2)
        self.assertEqual(res2["source"], "BIDV")
        self.assertEqual(res2["so_thua"], "101 + 102")
        self.assertEqual(res2["so_to"], "5")
        self.assertEqual(res2["dia_chi"], "Hanoi")
        self.assertEqual(res2["asset_sub_type"], "multi")

        # Test machinery
        res3 = parse_sobo_subject("[SƠ BỘ] - Máy móc thiết bị - Máy cắt CNC")
        self.assertIsNotNone(res3)
        self.assertEqual(res3["source"], "Máy móc thiết bị")
        self.assertEqual(res3["asset_type"], "machinery")
        self.assertEqual(res3["equipment_name"], "Máy cắt CNC")

    def test_clean_sobo_reply_subject(self) -> None:
        self.assertEqual(clean_sobo_reply_subject("Re: [SƠ BỘ] - Thửa 1"), "[SƠ BỘ] - Thửa 1")
        self.assertEqual(clean_sobo_reply_subject("RE: re: [SƠ BỘ] - Thửa 2"), "[SƠ BỘ] - Thửa 2")

    def test_extract_maps_link(self) -> None:
        text = "Hello, here is link: https://maps.app.goo.gl/XYZ123 for you."
        self.assertEqual(extract_maps_link(text), "https://maps.app.goo.gl/XYZ123")

    async def test_sync_sobo_emails_from_mailbox(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await ensure_tracking_schema(db_path)
            
            # Construct a raw mock email bytes
            # Request email
            msg1 = EmailMessage()
            msg1["From"] = "bot@cenvalue.vn"
            msg1["To"] = "sobo.danang@gmail.com"
            msg1["Subject"] = "[SƠ BỘ] - BIDV - Thửa đất số 77, tờ bản đồ số 88; tại địa chỉ Danang"
            msg1["Message-ID"] = "<msg-request-999@example.com>"
            msg1["Date"] = "Mon, 1 Jun 2026 10:00:00 +0700"
            msg1.set_content("Định vị: https://maps.google.com/77")
            
            # Response email
            msg2 = EmailMessage()
            msg2["From"] = "sobo.danang@gmail.com"
            msg2["To"] = "bot@cenvalue.vn"
            msg2["Subject"] = "Re: [SƠ BỘ] - BIDV - Thửa đất số 77, tờ bản đồ số 88; tại địa chỉ Danang"
            msg2["Message-ID"] = "<msg-reply-999@example.com>"
            msg2["In-Reply-To"] = "<msg-request-999@example.com>"
            msg2["References"] = "<msg-request-999@example.com>"
            msg2["Date"] = "Mon, 1 Jun 2026 11:30:00 +0700"
            msg2.set_content("Kết quả sơ bộ: 10 tỷ.")
            
            mock_emails = [
                {"raw_bytes": msg1.as_bytes(), "uid": "1", "thread_id": "1"},
                {"raw_bytes": msg2.as_bytes(), "uid": "2", "thread_id": "1"},
            ]
            
            with (
                patch("src.oauth2_service.get_enabled_oauth_provider", return_value="google"),
                patch("src.oauth2_service.fetch_emails_via_oauth2", AsyncMock(return_value=mock_emails)),
            ):
                synced = await sync_sobo_emails_from_mailbox(db_path)
                self.assertEqual(synced, 2)
                
            sobo_recs = await get_all_sobo_records(db_path)
            self.assertEqual(len(sobo_recs), 1)
            rec = sobo_recs[0]
            self.assertEqual(rec["outbound_message_id"], "<msg-request-999@example.com>")
            self.assertEqual(rec["so_thua"], "77")
            self.assertEqual(rec["so_to"], "88")
            self.assertEqual(rec["dia_chi"], "Danang")
            self.assertEqual(rec["link"], "https://maps.google.com/77")
            self.assertEqual(rec["status"], "RESPONDED")


# Helper helper mock to ensure tracking schema runs correctly
async def ensure_tracking_schema(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS sobo_records ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,"
            "  asset_type TEXT NOT NULL,"
            "  asset_sub_type TEXT,"
            "  source TEXT,"
            "  so_thua TEXT,"
            "  so_to TEXT,"
            "  dia_chi TEXT,"
            "  link TEXT,"
            "  email_recipient TEXT,"
            "  outbound_subject TEXT,"
            "  outbound_message_id TEXT,"
            "  outbound_sent_at TEXT,"
            "  responded_at TEXT,"
            "  status TEXT NOT NULL DEFAULT 'PENDING',"
            "  note TEXT,"
            "  equipment_name TEXT"
            ")"
        )
        await db.commit()


if __name__ == "__main__":
    unittest.main()
