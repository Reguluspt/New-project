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
    CertificateExtraction,
    READY_FOR_WEB_STATUS,
    EmailMatchExtraction,
    MailListenerSettings,
    _contract_id_for_update,
    build_professional_forward_message,
    build_reply_message,
    extract_certificate_number_locally,
    ensure_processed_email_table,
    _extract_imap_ids,
    load_mail_listener_settings,
    mark_email_processed,
    match_record,
    parse_incoming_email,
    process_incoming_email,
    was_email_processed,
    update_matched_record,
)
from src.database_manager import (
    PROJECT_ROOT,
    SENT_TO_PROFESSIONAL_STATUS,
    create_outbound_tracking_record,
    ensure_mail_workflow_schema,
    find_record_by_thread_reference,
    find_recent_record_by_subject,
    update_certificate_forwarded,
    update_certificate_received,
)
from src.mail_service import GmailSmtpSettings


def _html_part(message: EmailMessage) -> str:
    part = next(part for part in message.walk() if part.get_content_type() == "text/html")
    return part.get_payload(decode=True).decode("utf-8")


def _raw_email() -> bytes:
    message = EmailMessage()
    message["From"] = "Son <son@example.com>"
    message["Reply-To"] = "reply@example.com"
    message["Subject"] = "Xin so hop dong"
    message["Message-ID"] = "<msg-1@example.com>"
    message.set_content("Khach hang Nguyen Van A, tai san tai xa Hoa An.")
    return message.as_bytes()


def _raw_admin_reply() -> bytes:
    message = EmailMessage()
    message["From"] = "Admin <admin@example.com>"
    message["Reply-To"] = "admin@example.com"
    message["To"] = "Sender <sender@gmail.com>"
    message["Cc"] = "manager@example.com"
    message["Subject"] = "Re: [XIN SỐ] - VCB Gia Lai - Thửa đất số Lô 25B2"
    message["Message-ID"] = "<reply-1@example.com>"
    message["In-Reply-To"] = "<outbound-1@example.com>"
    message["References"] = "<outbound-1@example.com>"
    message["Thread-Topic"] = "[XIN SỐ] - VCB Gia Lai"
    message["Thread-Index"] = "AdzExampleThreadIndex"
    message.set_content("Số chứng thư: CT-2026-0007\nGhi chú Hành chính: ưu tiên xử lý trong ngày.")
    message.add_attachment(
        b"certificate attachment",
        maintype="application",
        subtype="pdf",
        filename="chung-thu.pdf",
    )
    return message.as_bytes()


class MailListenerTests(unittest.IsolatedAsyncioTestCase):
    def test_extract_certificate_number_locally_reads_labeled_value(self) -> None:
        extraction = extract_certificate_number_locally(
            "Em gửi anh số chứng thư: 010/2026/N05-0879/DN."
        )

        self.assertEqual(extraction.certificate_number, "010/2026/N05-0879/DN")
        self.assertEqual(extraction.confidence, 1.0)

    def test_load_mail_listener_settings_uses_shared_records_db_env(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "IMAP_USERNAME": "imap@example.com",
                "IMAP_PASSWORD": "secret",
                "GEMINI_API_KEY": "gemini",
                "TELEGRAM_BOT_TOKEN": "token",
                "TELEGRAM_CHAT_ID": "123",
                "RECORDS_DB_PATH": "shared/records.db",
                "TELEGRAM_RECORDS_DB": "legacy/records.db",
            },
            clear=True,
        ):
            settings = load_mail_listener_settings()

        self.assertEqual(settings.records_db_path, str((PROJECT_ROOT / "shared" / "records.db").resolve()))

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
        html = _html_part(message)
        self.assertIn("Gửi Sơn,", html)
        self.assertIn("27.500.000", html)
        self.assertIn("cid:logo_cenvalue", html)
        self.assertIn("Content-ID: <logo_cenvalue>", message.as_string())

    def test_build_professional_forward_message_sets_thread_headers(self) -> None:
        incoming = parse_incoming_email(_raw_admin_reply(), uid="21")
        settings = MailListenerSettings(
            imap_host="imap.gmail.com",
            imap_port=993,
            imap_username="sender@gmail.com",
            imap_password="app-password",
            mailbox="INBOX",
            records_db_path="tmp/records.db",
            gemini_api_key="gemini",
            gemini_model="gemini-test",
            telegram_bot_token="token",
            telegram_chat_id="123",
            auto_reply_cc=[],
            admin_email="admin@example.com",
            professional_dept_email="pro@example.com",
            monitor_cc_list=["manager@example.com", "control@example.com"],
        )
        message = build_professional_forward_message(
            incoming=incoming,
            record={
                "id": "5",
                "customer_info": "Nguyễn Thị Loan",
                "asset_description": "Thửa đất số Lô 25B2",
                "valuation_fee_number": "3000000",
                "professional_recipient_email": "anhvtn6@cenvalue.vn",
            },
            certificate_number="CT-2026-0007",
            smtp_settings=GmailSmtpSettings(
                host="smtp.gmail.com",
                port=587,
                username="sender@gmail.com",
                password="app-password",
                mail_from="Sender <sender@gmail.com>",
                mail_to="",
                mail_cc=[],
            ),
            settings=settings,
        )

        self.assertEqual(message["To"], "anhvtn6@cenvalue.vn")
        self.assertEqual(message["Cc"], "admin@example.com, manager@example.com, control@example.com")
        self.assertEqual(message["In-Reply-To"], "<reply-1@example.com>")
        self.assertIn("<reply-1@example.com>", message["References"])
        self.assertEqual(message["Thread-Topic"], "[XIN SỐ] - VCB Gia Lai")
        self.assertEqual(message["Thread-Index"], "AdzExampleThreadIndex")
        html = _html_part(message)
        self.assertIn("CT-2026-0007", html)
        self.assertNotIn("N04-0007", html)
        self.assertIn("Chị Ánh", html)
        self.assertIn("Em phân chuyên viên định giá tài sản", html)
        self.assertIn("ưu tiên xử lý trong ngày", html)
        self.assertIn("THÔNG TIN HỒ SƠ", html)
        attachments = list(message.iter_attachments())
        self.assertEqual(attachments[0].get_filename(), "chung-thu.pdf")
        self.assertEqual(attachments[0].get_payload(decode=True), b"certificate attachment")
        self.assertIn("Số chứng thư", html)
        self.assertIn("cid:logo_cenvalue", html)
        self.assertIn("Content-ID: <logo_cenvalue>", message.as_string())

    def test_build_professional_forward_message_preserves_full_certificate_number(self) -> None:
        incoming = parse_incoming_email(_raw_admin_reply(), uid="22")
        settings = MailListenerSettings(
            imap_host="imap.gmail.com",
            imap_port=993,
            imap_username="sender@gmail.com",
            imap_password="app-password",
            mailbox="INBOX",
            records_db_path="tmp/records.db",
            gemini_api_key="gemini",
            gemini_model="gemini-test",
            telegram_bot_token="token",
            telegram_chat_id="123",
            auto_reply_cc=[],
            admin_email="admin@example.com",
            professional_dept_email="pro@example.com",
            monitor_cc_list=[],
        )
        message = build_professional_forward_message(
            incoming=incoming,
            record={"id": "5", "contract_number": "010/2026/N06-0106/DN"},
            certificate_number="010/2024/D10-0105",
            smtp_settings=GmailSmtpSettings(
                host="smtp.gmail.com",
                port=587,
                username="sender@gmail.com",
                password="app-password",
                mail_from="Sender <sender@gmail.com>",
                mail_to="",
                mail_cc=[],
            ),
            settings=settings,
        )

        html = _html_part(message)
        self.assertIn("010/2024/D10-0105", html)
        self.assertNotIn("010/2026/N06-010/2024/D10-0105/DN", html)
        self.assertIn("THÔNG TIN HỒ SƠ", html)

    async def test_certificate_updates_preserve_contract_number(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contract_number TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'PENDING'
                    )
                    """
                )
                await db.commit()
            await ensure_mail_workflow_schema(db_path)
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    "INSERT INTO records (contract_number) VALUES (?)",
                    ("010/2026/N06-0106/DN",),
                )
                await db.commit()

            await update_certificate_forwarded(
                db_path,
                1,
                certificate_number="010/2024/D10-0105",
            )
            await update_certificate_received(
                db_path,
                1,
                certificate_number="010/2024/D10-0105",
            )

            async with aiosqlite.connect(db_path) as db:
                row = await (await db.execute(
                    "SELECT certificate_number, contract_number FROM records WHERE id = 1"
                )).fetchone()

        self.assertEqual(row, ("010/2024/D10-0105", "010/2026/N06-0106/DN"))

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
                await db.commit()
            await ensure_mail_workflow_schema(db_path)
            async with aiosqlite.connect(db_path) as db:
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

    async def test_process_admin_certificate_reply_forwards_updates_and_notifies(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL DEFAULT '',
                        customer_info TEXT NOT NULL DEFAULT '',
                        chu_so_huu TEXT NOT NULL DEFAULT '',
                        asset_description TEXT NOT NULL DEFAULT '',
                        valuation_fee_number TEXT NOT NULL DEFAULT '',
                        contract_number TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'PENDING'
                    )
                    """
                )
                await db.commit()
            await ensure_mail_workflow_schema(db_path)
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    INSERT INTO records (
                        customer_info, chu_so_huu, asset_description, valuation_fee_number,
                        outbound_message_id, outbound_subject
                    )
                    VALUES ('Nguyễn Thị Loan', 'Nguyễn Thị Loan', 'Thửa đất số Lô 25B2',
                            '3000000', '<outbound-1@example.com>', '[XIN SỐ] - VCB Gia Lai')
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
                auto_reply_cc=[],
                admin_email="admin@example.com",
                professional_dept_email="pro@example.com",
                monitor_cc_list=["manager@example.com"],
            )

            with (
                patch(
                    "src.mail_listener.analyze_certificate_with_gemini",
                    return_value=CertificateExtraction(certificate_number="CT-2026-0007", confidence=0.96),
                ),
                patch("src.mail_listener.send_professional_forward", AsyncMock()) as forward_mock,
                patch("src.record_case_sync.sync_record_to_case", AsyncMock()),
                patch("src.mail_listener.notify_telegram", AsyncMock()) as notify_mock,
                patch("src.mail_listener.append_listener_log"),
            ):
                match = await process_incoming_email(_raw_admin_reply(), uid="21", settings=settings)

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute(
                    "SELECT certificate_number, status FROM records WHERE id = 1"
                )
                row = await cursor.fetchone()

        self.assertIsNotNone(match)
        forward_mock.assert_awaited_once()
        notify_mock.assert_awaited_once()
        self.assertEqual(row, ("CT-2026-0007", SENT_TO_PROFESSIONAL_STATUS))
        self.assertIn("Nguyễn Thị Loan", notify_mock.await_args.args[1])

    async def test_process_admin_certificate_reply_falls_back_to_subject_match(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL DEFAULT '',
                        customer_info TEXT NOT NULL DEFAULT '',
                        chu_so_huu TEXT NOT NULL DEFAULT '',
                        source TEXT NOT NULL DEFAULT '',
                        dia_chi TEXT NOT NULL DEFAULT '',
                        asset_description TEXT NOT NULL DEFAULT '',
                        valuation_fee_number TEXT NOT NULL DEFAULT '',
                        contract_number TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'PENDING'
                    )
                    """
                )
                await db.commit()
            await ensure_mail_workflow_schema(db_path)
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    INSERT INTO records (
                        customer_info, chu_so_huu, source, dia_chi,
                        asset_description, valuation_fee_number, outbound_subject
                    )
                    VALUES ('Nguyễn Thị Loan', 'Nguyễn Thị Loan', 'VCB Gia Lai - Mr Bảo',
                            'Khu quy hoạch đô thị Diên Phú',
                            'Thửa đất số Lô 25B2, tờ bản đồ số QH; tại địa chỉ Khu quy hoạch đô thị Diên Phú',
                            '3000000', '[XIN SỐ] - VCB Gia Lai - Thửa đất số Lô 25B2')
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
                auto_reply_cc=[],
                admin_email="admin@example.com",
                professional_dept_email="pro@example.com",
                monitor_cc_list=["manager@example.com"],
            )

            with (
                patch(
                    "src.mail_listener.analyze_certificate_with_gemini",
                    return_value=CertificateExtraction(certificate_number="CT-2026-0008", confidence=0.96),
                ),
                patch("src.mail_listener.send_professional_forward", AsyncMock()),
                patch("src.record_case_sync.sync_record_to_case", AsyncMock()),
                patch("src.mail_listener.notify_telegram", AsyncMock()),
                patch("src.mail_listener.append_listener_log"),
            ):
                match = await process_incoming_email(_raw_admin_reply(), uid="22", settings=settings)

        self.assertIsNotNone(match)
        self.assertEqual(match.record["id"], "1")

    async def test_process_admin_certificate_reply_does_not_match_untracked_record_fields(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL DEFAULT '',
                        customer_info TEXT NOT NULL DEFAULT '',
                        chu_so_huu TEXT NOT NULL DEFAULT '',
                        source TEXT NOT NULL DEFAULT '',
                        dia_chi TEXT NOT NULL DEFAULT '',
                        asset_description TEXT NOT NULL DEFAULT '',
                        valuation_fee_number TEXT NOT NULL DEFAULT '',
                        contract_number TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'PENDING'
                    )
                    """
                )
                await db.commit()
            await ensure_mail_workflow_schema(db_path)
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    INSERT INTO records (
                        customer_info, chu_so_huu, source, dia_chi,
                        asset_description, valuation_fee_number
                    )
                    VALUES ('Nguyễn Thị Loan', 'Nguyễn Thị Loan', 'VCB Gia Lai - Mr Bảo',
                            'Khu quy hoạch đô thị Diên Phú',
                            'Thửa đất số Lô 25B2, tờ bản đồ số QH; tại địa chỉ Khu quy hoạch đô thị Diên Phú',
                            '3000000')
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
                auto_reply_cc=[],
                admin_email="admin@example.com",
                professional_dept_email="pro@example.com",
                monitor_cc_list=["manager@example.com"],
            )

            with (
                patch(
                    "src.mail_listener.analyze_certificate_with_gemini",
                    return_value=CertificateExtraction(certificate_number="CT-2026-0008", confidence=0.96),
                ),
                patch("src.mail_listener.send_professional_forward", AsyncMock()) as forward_mock,
                patch("src.record_case_sync.sync_record_to_case", AsyncMock()),
                patch("src.mail_listener.notify_telegram", AsyncMock()) as notify_mock,
                patch("src.mail_listener.append_listener_log"),
            ):
                match = await process_incoming_email(_raw_admin_reply(), uid="23", settings=settings)

        self.assertIsNone(match)
        forward_mock.assert_not_awaited()
        notify_mock.assert_awaited_once()

    async def test_create_outbound_tracking_record_maps_desktop_case_fields(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            record_id = await create_outbound_tracking_record(
                db_path,
                {
                    "contract_number": "N04-1047",
                    "asset_description": "Thửa đất số 78d",
                    "source": "MB AMC ARR - Mr. Long",
                    "customer_info": "Công ty ABC",
                    "so_thua_dat": "78d",
                    "so_to_ban_do": "13",
                    "dia_chi_thua_dat": "Xã Hòa An",
                    "owner_name": "Công ty ABC",
                },
            )

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute(
                    "SELECT contract_number, so_thua, so_to, dia_chi, chu_so_huu, asset_description FROM records WHERE id = ?",
                    (record_id,),
                )
                row = await cursor.fetchone()

        self.assertEqual(row, ("N04-1047", "78d", "13", "Xã Hòa An", "Công ty ABC", "Thửa đất số 78d"))

    async def test_thread_matching_strips_reply_prefixes_and_uses_like_subject(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL DEFAULT '',
                        customer_info TEXT NOT NULL DEFAULT '',
                        chu_so_huu TEXT NOT NULL DEFAULT '',
                        source TEXT NOT NULL DEFAULT '',
                        dia_chi TEXT NOT NULL DEFAULT '',
                        asset_description TEXT NOT NULL DEFAULT '',
                        valuation_fee_number TEXT NOT NULL DEFAULT '',
                        contract_number TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'PENDING'
                    )
                    """
                )
                await db.commit()
            await ensure_mail_workflow_schema(db_path)
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    INSERT INTO records (
                        customer_info, chu_so_huu, source, dia_chi,
                        asset_description, outbound_message_id, outbound_subject
                    )
                    VALUES (
                        'Khách A', 'Khách A', 'VCB Gia Lai', 'Xã Hòa An',
                        'Thửa đất số 78d, tờ bản đồ số 13',
                        '<outbound-2@gmail.com>',
                        '[XIN SỐ] - VCB Gia Lai - Thửa đất số 78d, tờ bản đồ số 13'
                    )
                    """
                )
                await db.commit()

            by_thread = await find_record_by_thread_reference(
                db_path,
                in_reply_to="",
                references="",
                subject="  FWD: RE: [XIN SỐ] - VCB Gia Lai - Thửa đất số 78d, tờ bản đồ số 13 - đã cấp số",
            )
            by_recent = await find_recent_record_by_subject(
                db_path,
                subject="Re: đã cấp số chứng thư cho VCB Gia Lai thửa đất 78d",
            )

        self.assertIsNotNone(by_thread)
        self.assertEqual(by_thread["id"], "1")
        self.assertIsNotNone(by_recent)
        self.assertEqual(by_recent["id"], "1")

    async def test_admin_certificate_reply_logs_and_notifies_when_no_record_match(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE records (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL DEFAULT '',
                        customer_info TEXT NOT NULL DEFAULT '',
                        chu_so_huu TEXT NOT NULL DEFAULT '',
                        source TEXT NOT NULL DEFAULT '',
                        dia_chi TEXT NOT NULL DEFAULT '',
                        asset_description TEXT NOT NULL DEFAULT '',
                        valuation_fee_number TEXT NOT NULL DEFAULT '',
                        contract_number TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'PENDING'
                    )
                    """
                )
                await db.commit()
            await ensure_mail_workflow_schema(db_path)
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
                admin_email="admin@example.com",
                professional_dept_email="pro@example.com",
                monitor_cc_list=[],
            )

            with (
                patch(
                    "src.mail_listener.analyze_certificate_with_gemini",
                    return_value=CertificateExtraction(certificate_number="010/2026/N04-9999/DN", confidence=0.95),
                ),
                patch("src.mail_listener.notify_telegram", AsyncMock()) as notify_mock,
                patch("src.mail_listener.append_listener_log"),
            ):
                match = await process_incoming_email(_raw_admin_reply(), uid="99", settings=settings)

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("SELECT event, reason, raw_email_text FROM listener_logs")
                row = await cursor.fetchone()

        self.assertIsNone(match)
        notify_mock.assert_awaited_once()
        self.assertIn("không đối soát được hồ sơ", notify_mock.await_args.args[1])
        self.assertEqual(row[0], "record_match_failed")
        self.assertEqual(row[1], "no_thread_record")
        self.assertIn("CT-2026-0007", row[2])

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
