from __future__ import annotations

import unittest
from email.message import EmailMessage
from email.policy import SMTP
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, patch

import aiosqlite

from src.mail_listener import (
    AUTO_REPLY_CC,
    READY_FOR_WEB_STATUS,
    EmailMatchExtraction,
    MailListenerSettings,
    _contract_id_for_update,
    build_reply_message,
    ensure_processed_email_table,
    _extract_imap_ids,
    mark_email_processed,
    match_record,
    parse_incoming_email,
    process_incoming_email,
    was_email_processed,
    update_matched_record,
)
from src.mail_service import GmailSmtpSettings


def _raw_email() -> bytes:
    message = EmailMessage()
    message["From"] = "Son <son@example.com>"
    message["Reply-To"] = "reply@example.com"
    message["Subject"] = "Xin so hop dong"
    message["Message-ID"] = "<msg-1@example.com>"
    message.set_content("Khach hang Nguyen Van A, tai san tai xa Hoa An.")
    return message.as_bytes()


class MailListenerTests(unittest.IsolatedAsyncioTestCase):
    def test_parse_incoming_email_reads_headers_and_text(self) -> None:
        incoming = parse_incoming_email(_raw_email(), uid="11")

        self.assertEqual(incoming.uid, "11")
        self.assertEqual(incoming.from_email, "son@example.com")
        self.assertEqual(incoming.reply_to, "reply@example.com")
        self.assertIn("Nguyen Van A", incoming.text)

    def test_parse_incoming_email_decodes_folded_subject_for_reply(self) -> None:
        message = EmailMessage(policy=SMTP)
        message["From"] = "Son <son@example.com>"
        message["Subject"] = "[XIN SỐ] - VCB Gia Lai - Thửa đất số Lô 25B2, tờ bản đồ số QH, tại địa chỉ Khu quy hoạch đô thị Diên Phú, thành phố Pleiku, tỉnh Gia Lai."
        message["Message-ID"] = "<msg-folded@example.com>"
        message.set_content("Khach hang Nguyen Van A.")

        incoming = parse_incoming_email(message.as_bytes(), uid="12")
        reply = build_reply_message(
            incoming=incoming,
            record={
                "contract_number": "010/2026/N04-1026/DN",
                "asset_type": "BĐS đặc thù khác",
                "asset_description": "Thửa đất số 90,92",
                "customer_info": "Ngân hàng A",
                "valuation_fee_number": "27500000",
            },
            smtp_settings=GmailSmtpSettings(
                host="smtp.gmail.com",
                port=587,
                username="sender@gmail.com",
                password="app-password",
                mail_from="Sender <sender@gmail.com>",
                mail_to="",
                mail_cc=[],
            ),
            cc_list=[AUTO_REPLY_CC],
        )

        self.assertNotIn("\n", incoming.subject)
        self.assertNotIn("\r", incoming.subject)
        self.assertTrue(str(reply["Subject"]).startswith("Re: [XIN SỐ]"))

    def test_extract_imap_ids_ignores_status_words(self) -> None:
        ids = _extract_imap_ids([b"5 6 13 SEARCH completed (Success)"])

        self.assertEqual(ids, ["5", "6", "13"])

    def test_contract_id_for_update_ignores_plain_numbers(self) -> None:
        self.assertEqual(_contract_id_for_update("5"), "")
        self.assertEqual(_contract_id_for_update("010/2026/N04-1051/DN"), "010/2026/N04-1051/DN")
        self.assertEqual(_contract_id_for_update("N04.1027"), "N04.1027")

    def test_match_record_uses_customer_or_asset_address_confidence(self) -> None:
        match = match_record(
            [
                {
                    "id": "1",
                    "customer_info": "Nguyen Van A",
                    "asset_description": "Thua dat tai xa Hoa An",
                    "contract_number": "",
                }
            ],
            EmailMatchExtraction(
                customer_name="Nguyen Van A",
                asset_address="xa Hoa An",
                confidence=0.95,
            ),
        )

        self.assertIsNotNone(match)
        self.assertGreater(match.score, 0.8)
        self.assertEqual(match.record["id"], "1")

    def test_build_reply_message_adds_thread_headers_and_host_cc(self) -> None:
        incoming = parse_incoming_email(_raw_email(), uid="11")
        smtp_settings = GmailSmtpSettings(
            host="smtp.gmail.com",
            port=587,
            username="sender@gmail.com",
            password="app-password",
            mail_from="Sender <sender@gmail.com>",
            mail_to="",
            mail_cc=[],
        )
        message = build_reply_message(
            incoming=incoming,
            record={
                "contract_number": "010/2026/N04-1026/DN",
                "asset_type": "BĐS đặc thù khác",
                "asset_description": "Thửa đất số 90,92",
                "customer_info": "Ngân hàng A",
                "valuation_fee_number": "27500000",
            },
            smtp_settings=smtp_settings,
            cc_list=[AUTO_REPLY_CC],
        )

        self.assertEqual(message["To"], "reply@example.com")
        self.assertIn(AUTO_REPLY_CC, message["Cc"])
        self.assertEqual(message["In-Reply-To"], "<msg-1@example.com>")
        html = message.get_payload()[1].get_payload(decode=True).decode("utf-8")
        self.assertIn("Gửi Sơn,", html)
        self.assertIn("27.500.000", html)

    async def test_update_matched_record_sets_contract_and_ready_status(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contract_number TEXT,
                        status TEXT
                    )
                    """
                )
                await db.execute("INSERT INTO records (contract_number, status) VALUES ('', 'PENDING')")
                await db.commit()

            await update_matched_record(db_path, 1, "010/2026/N04-1026/DN")

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("SELECT contract_number, status FROM records WHERE id = 1")
                row = await cursor.fetchone()

        self.assertEqual(row, ("010/2026/N04-1026/DN", READY_FOR_WEB_STATUS))

    async def test_process_incoming_email_replies_updates_and_notifies(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contract_number TEXT,
                        customer_info TEXT,
                        chu_so_huu TEXT,
                        asset_description TEXT,
                        dia_chi TEXT,
                        asset_type TEXT,
                        valuation_fee_number TEXT,
                        status TEXT
                    )
                    """
                )
                await db.execute(
                    """
                    INSERT INTO records (
                        contract_number, customer_info, chu_so_huu, asset_description,
                        dia_chi, asset_type, valuation_fee_number, status
                    )
                    VALUES ('', 'Nguyen Van A', 'Nguyen Van A', 'Thua dat tai xa Hoa An',
                            'xa Hoa An', 'BĐS đặc thù khác', '2200000', 'PENDING')
                    """
                )
                await db.commit()
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
                auto_reply_cc=[AUTO_REPLY_CC],
            )

            with (
                patch(
                    "src.mail_listener.analyze_email_with_gemini",
                    return_value=EmailMatchExtraction(
                        contract_id="010/2026/N04-1026/DN",
                        customer_name="Nguyen Van A",
                        asset_address="xa Hoa An",
                        confidence=0.95,
                    ),
                ),
                patch(
                    "src.mail_listener.load_gmail_smtp_settings",
                    return_value=GmailSmtpSettings(
                        host="smtp.gmail.com",
                        port=587,
                        username="sender@gmail.com",
                        password="app-password",
                        mail_from="Sender <sender@gmail.com>",
                        mail_to="",
                        mail_cc=[],
                    ),
                ),
                patch("src.mail_listener.send_thread_reply", AsyncMock()) as reply_mock,
                patch("src.mail_listener.notify_telegram", AsyncMock()) as notify_mock,
                patch("src.mail_listener.append_listener_log") as log_mock,
            ):
                match = await process_incoming_email(_raw_email(), uid="11", settings=settings)

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("SELECT contract_number, status FROM records WHERE id = 1")
                row = await cursor.fetchone()

        self.assertIsNotNone(match)
        reply_mock.assert_awaited_once()
        notify_mock.assert_awaited_once()
        logged_events = [call.args[0] for call in log_mock.call_args_list]
        self.assertIn("matched", logged_events)
        self.assertIn("replied", logged_events)
        self.assertEqual(row, ("010/2026/N04-1026/DN", READY_FOR_WEB_STATUS))

    async def test_process_incoming_email_logs_skipped_low_score(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contract_number TEXT,
                        customer_info TEXT,
                        chu_so_huu TEXT,
                        asset_description TEXT,
                        dia_chi TEXT,
                        status TEXT
                    )
                    """
                )
                await db.execute(
                    "INSERT INTO records (contract_number, customer_info, chu_so_huu, asset_description, dia_chi, status) VALUES ('', 'Other', 'Other', 'Other', 'Other', 'PENDING')"
                )
                await db.commit()
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
                auto_reply_cc=[AUTO_REPLY_CC],
            )

            with (
                patch(
                    "src.mail_listener.analyze_email_with_gemini",
                    return_value=EmailMatchExtraction(
                        customer_name="No Match",
                        asset_address="No Match",
                        confidence=0.95,
                    ),
                ),
                patch("src.mail_listener.append_listener_log") as log_mock,
            ):
                match = await process_incoming_email(_raw_email(), uid="11", settings=settings)

        self.assertIsNotNone(match)
        self.assertLessEqual(match.score, 0.8)
        log_mock.assert_called_once()
        self.assertEqual(log_mock.call_args.args[0], "skipped")

    async def test_processed_email_history_prevents_duplicate_processing(self) -> None:
        incoming = parse_incoming_email(_raw_email(), uid="11")
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await ensure_processed_email_table(db_path)

            before = await was_email_processed(db_path, incoming, mailbox="INBOX")
            await mark_email_processed(
                db_path,
                incoming,
                mailbox="INBOX",
                result="replied",
                record_id="7",
                score=0.97,
            )
            after = await was_email_processed(db_path, incoming, mailbox="INBOX")

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute(
                    "SELECT message_id, result, record_id, score FROM processed_emails"
                )
                row = await cursor.fetchone()

        self.assertFalse(before)
        self.assertTrue(after)
        self.assertEqual(row, ("<msg-1@example.com>", "replied", "7", 0.97))


if __name__ == "__main__":
    unittest.main()
