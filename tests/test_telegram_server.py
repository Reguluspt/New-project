from __future__ import annotations

import unittest
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, Mock, patch

import aiosqlite
from fastapi import FastAPI
from telegram.ext import ConversationHandler

from src.models import ExtractedValue, LandCertificateExtraction
from src.telegram_server import (
    ASK_MISSING_FIELD,
    CONFIRM_CALLBACK,
    CONFIRMED_STATUS,
    CONFIRMING,
    EDIT_CALLBACK,
    EDIT_FIELD_SELECT,
    EmailDraft,
    PENDING_STATUS,
    PROJECT_ROOT,
    SEND_MAIL_CALLBACK_PREFIX,
    TELEGRAM_WEBHOOK_PATH,
    TelegramSettings,
    WEB_AUTOMATION_CALLBACK_PREFIX,
    automation_keyboard,
    build_form_field_queue,
    build_telegram_application,
    chat_id_command,
    draft_email,
    editable_record_fields,
    format_editable_field_list,
    format_extraction_response,
    get_record,
    get_case_by_contract_number,
    get_record_by_contract_number,
    handle_confirmation_callback,
    handle_edit_field_selection,
    handle_missing_field_reply,
    handle_post_confirm_action,
    init_records_db,
    load_telegram_settings,
    listener_off_command,
    listener_log_command,
    listener_on_command,
    listener_status_command,
    missing_required_fields,
    process_land_certificate_file,
    register_bot_commands,
    save_record,
    send_email,
    search_dropdown_options,
    send_mail_by_contract_command,
    start_manual_entry,
    sync_hidden_gcn_fields_from_form,
    telegram_webhook,
    update_record_fields,
    update_record_status,
)


def _value(value: str) -> ExtractedValue:
    return ExtractedValue(value=value, confidence=0.95, evidence=f"evidence {value}")


def _sample_extraction() -> LandCertificateExtraction:
    return LandCertificateExtraction(
        so_thua_dat=_value("123"),
        so_to_ban_do=_value("45"),
        dia_chi_thua_dat=_value("Phuong Tan Loi"),
        ten_chu_so_huu_cuoi_cung=_value("Nguyen Van A"),
        dia_chi_chu_so_huu_cuoi_cung=_value("12 Le Loi"),
        so_cccd_chu_so_huu_cuoi_cung=_value("012345678901"),
        notes=[],
        page_metadata=[],
    )


class TelegramServerTests(unittest.IsolatedAsyncioTestCase):
    def test_load_settings_from_environment(self) -> None:
        with (
            patch("src.telegram_server.load_dotenv"),
            patch.dict(
                "os.environ",
                {
                    "TELEGRAM_BOT_TOKEN": "token",
                    "WEBHOOK_URL": "https://example.com/base/",
                    "GEMINI_API_KEY": "gemini-secret",
                    "GEMINI_MODEL": "gemini-test",
                    "TELEGRAM_UPLOAD_DIR": "tmp/uploads",
                    "TELEGRAM_RECORDS_DB": "tmp/records.db",
                },
                clear=True,
            ),
        ):
            settings = load_telegram_settings()

        self.assertEqual(settings.bot_token, "token")
        self.assertEqual(settings.webhook_endpoint, f"https://example.com/base{TELEGRAM_WEBHOOK_PATH}")
        self.assertEqual(settings.gemini_api_key, "gemini-secret")
        self.assertEqual(settings.gemini_model, "gemini-test")
        self.assertEqual(settings.upload_dir, "tmp/uploads")
        self.assertEqual(settings.records_db_path, os.path.abspath(os.path.join(PROJECT_ROOT, "tmp/records.db")))

    def test_records_db_path_environment_takes_precedence_and_is_absolute(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "TELEGRAM_BOT_TOKEN": "token",
                "WEBHOOK_URL": "https://example.com/base/",
                "GEMINI_API_KEY": "gemini-secret",
                "RECORDS_DB_PATH": "shared/records.db",
                "TELEGRAM_RECORDS_DB": "legacy/records.db",
            },
            clear=True,
        ):
            settings = load_telegram_settings()

        self.assertEqual(settings.records_db_path, os.path.abspath(os.path.join(PROJECT_ROOT, "shared/records.db")))

    def test_webhook_url_can_be_full_endpoint(self) -> None:
        settings = TelegramSettings(
            bot_token="token",
            webhook_url=f"https://example.com{TELEGRAM_WEBHOOK_PATH}",
            gemini_api_key="gemini-secret",
            gemini_model="gemini-test",
            upload_dir="tmp/uploads",
            records_db_path="tmp/records.db",
        )

        self.assertEqual(settings.webhook_endpoint, f"https://example.com{TELEGRAM_WEBHOOK_PATH}")

    def test_load_settings_accepts_mail_style_gmail_variables(self) -> None:
        with (
            patch("src.telegram_server.load_dotenv"),
            patch.dict(
                "os.environ",
                {
                    "TELEGRAM_BOT_TOKEN": "token",
                    "WEBHOOK_URL": "https://example.com/webhook/telegram",
                    "GEMINI_API_KEY": "gemini-secret",
                    "MAIL_USERNAME": "sender@gmail.com",
                    "MAIL_PASSWORD": "app-password",
                    "MAIL_FROM": "Appraiser Name",
                    "MAIL_SERVER": "smtp.gmail.com",
                    "MAIL_PORT": "587",
                },
                clear=True,
            ),
        ):
            settings = load_telegram_settings()

        self.assertEqual(settings.smtp_host, "smtp.gmail.com")
        self.assertEqual(settings.smtp_port, 587)
        self.assertEqual(settings.smtp_username, "sender@gmail.com")
        self.assertEqual(settings.smtp_password, "app-password")
        self.assertEqual(settings.mail_from, "Appraiser Name <sender@gmail.com>")

    def test_build_telegram_application_registers_handlers(self) -> None:
        telegram_app = build_telegram_application("123456:ABCDEF")

        handlers = telegram_app.handlers[0]
        self.assertGreaterEqual(len(handlers), 4)
        self.assertTrue(any(isinstance(handler, ConversationHandler) for handler in handlers))

    async def test_register_bot_commands_enables_command_menu(self) -> None:
        telegram_app = Mock()
        telegram_app.bot = Mock()
        telegram_app.bot.set_my_commands = AsyncMock()
        telegram_app.bot.set_chat_menu_button = AsyncMock()

        await register_bot_commands(telegram_app)

        commands = telegram_app.bot.set_my_commands.await_args.args[0]
        self.assertEqual([command.command for command in commands], ["sobo", "phathanh", "nhap", "tra_cuu", "gui_mail", "cancel", "start"])
        telegram_app.bot.set_chat_menu_button.assert_awaited_once()

    async def test_webhook_processes_update_payload(self) -> None:
        app = FastAPI()
        telegram_app = Mock()
        telegram_app.bot = Mock()
        telegram_app.process_update = AsyncMock()
        app.state.telegram_app = telegram_app

        request = Mock()
        request.app = app
        request.json = AsyncMock(return_value={"update_id": 123456})

        result = await telegram_webhook(request)

        self.assertEqual(result, {"ok": True})
        telegram_app.process_update.assert_awaited_once()

    async def test_init_db_and_save_record(self) -> None:
        extraction = _sample_extraction()
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await init_records_db(db_path)
            record_id = await save_record(db_path, "data/uploads/gcn.pdf", extraction)

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute(
                    "SELECT so_thua, so_to, dia_chi, chu_so_huu, status FROM records WHERE id = ?",
                    (record_id,),
                )
                row = await cursor.fetchone()

        self.assertEqual(row, ("123", "45", "Phuong Tan Loi", "Nguyen Van A", PENDING_STATUS))

    async def test_update_record_fields_and_status(self) -> None:
        extraction = _sample_extraction()
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await init_records_db(db_path)
            record_id = await save_record(db_path, "data/uploads/gcn.pdf", extraction)
            await update_record_fields(db_path, record_id, {"so_to": "99", "ignored": "no"})
            await update_record_status(db_path, record_id, CONFIRMED_STATUS)

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("SELECT so_to, status FROM records WHERE id = ?", (record_id,))
                row = await cursor.fetchone()

        self.assertEqual(row, ("99", CONFIRMED_STATUS))

    async def test_save_record_reuses_previous_defaults_for_skipped_fields(self) -> None:
        extraction = _sample_extraction()
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await init_records_db(db_path)
            first_id = await save_record(db_path, "data/uploads/first.pdf", extraction)
            await update_record_fields(
                db_path,
                first_id,
                {
                    "preliminary_status": "Đã sơ bộ",
                    "expected_finish_date": "03 ngày",
                    "survey_cost": "500.000",
                },
            )
            second_id = await save_record(db_path, "data/uploads/second.pdf", extraction)

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute(
                    "SELECT preliminary_status, expected_finish_date, survey_cost FROM records WHERE id = ?",
                    (second_id,),
                )
                row = await cursor.fetchone()

        self.assertEqual(row, ("Đã sơ bộ", "03 ngày", "500.000"))

    async def test_get_record_and_draft_email_from_template(self) -> None:
        extraction = _sample_extraction()
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_path = str(root / "records.db")
            template_path = root / "mail.txt"
            template_path.write_text("Ho so {id}: {so_thua}/{so_to} - {chu_so_huu}", encoding="utf-8")
            await init_records_db(db_path)
            record_id = await save_record(db_path, "data/uploads/gcn.pdf", extraction)
            record = await get_record(db_path, record_id)
            draft = await draft_email(
                record_id,
                db_path,
                template_path=str(template_path),
                to_email="ops@example.com",
            )

        self.assertEqual(record["so_thua"], "123")
        self.assertEqual(draft.to_email, "ops@example.com")
        self.assertIn("Ho so", draft.body)
        self.assertIn("123/45", draft.body)
        self.assertIn("Nguyen Van A", draft.subject)

    async def test_get_record_by_contract_number_matches_short_contract(self) -> None:
        extraction = _sample_extraction()
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await init_records_db(db_path)
            record_id = await save_record(db_path, "data/uploads/gcn.pdf", extraction)
            await update_record_fields(db_path, record_id, {"contract_number": "010/2026/N04.1027/DN"})

            record = await get_record_by_contract_number(db_path, "N04.1027")

        self.assertIsNotNone(record)
        self.assertEqual(record["id"], str(record_id))
        self.assertEqual(record["contract_number"], "010/2026/N04.1027/DN")

    async def test_get_case_by_contract_number_matches_main_cases_database(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "cases.db")
            async with aiosqlite.connect(db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE cases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contract_number TEXT,
                        customer_info TEXT,
                        valuation_fee_number INTEGER
                    )
                    """
                )
                await db.execute(
                    "INSERT INTO cases (contract_number, customer_info, valuation_fee_number) VALUES (?, ?, ?)",
                    ("010/2026/N04-1051/DN", "Khách A", 2200000),
                )
                await db.commit()

            record = await get_case_by_contract_number(db_path, "N04-1051")

        self.assertIsNotNone(record)
        self.assertEqual(record["contract_number"], "010/2026/N04-1051/DN")
        self.assertEqual(record["customer_info"], "Khách A")

    async def test_send_email_uses_smtp(self) -> None:
        settings = TelegramSettings(
            bot_token="token",
            webhook_url="https://example.com",
            gemini_api_key="gemini-secret",
            gemini_model="gemini-test",
            upload_dir="tmp/uploads",
            records_db_path="tmp/records.db",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="sender@example.com",
            smtp_password="secret",
            mail_from="sender@example.com",
            mail_to="ops@example.com",
        )
        draft = EmailDraft(subject="Subject", body="Body", to_email="ops@example.com")
        smtp = Mock()
        smtp.__enter__ = Mock(return_value=smtp)
        smtp.__exit__ = Mock(return_value=False)
        with patch("src.telegram_server.smtplib.SMTP", return_value=smtp):
            await send_email(settings, draft)

        smtp.starttls.assert_called_once()
        smtp.login.assert_called_once_with("sender@example.com", "secret")
        smtp.send_message.assert_called_once()

    def test_missing_required_fields_checks_so_to_so_thua_owner(self) -> None:
        missing = missing_required_fields(
            {
                "so_to": "",
                "so_thua": "123",
                "chu_so_huu": "  ",
                "dia_chi": "",
            }
        )

        self.assertEqual([field for field, _label in missing], ["so_to", "chu_so_huu"])

    def test_build_form_field_queue_adds_organization_fields_when_needed(self) -> None:
        individual_fields = [field for field, _label in build_form_field_queue({"customer_type": "individual"})]
        organization_fields = [field for field, _label in build_form_field_queue({"customer_type": "organization"})]

        self.assertIn("contract_number", individual_fields)
        self.assertNotIn("preliminary_status", individual_fields)
        self.assertNotIn("expected_finish_date", individual_fields)
        self.assertNotIn("survey_cost", individual_fields)
        self.assertIn("valuation_staff", individual_fields)
        self.assertNotIn("tax_code", individual_fields)
        self.assertIn("tax_code", organization_fields)
        self.assertIn("authorization_note", organization_fields)

    def test_search_dropdown_options_matches_keywords_without_case_or_accents(self) -> None:
        matches = search_dropdown_options(
            "vp gia lai",
            [
                "BIDV Gia Lai - Mr Cuong",
                "VP Bank - Gia Lai - Chi Ngoc",
                "Sacombank Kon Tum",
            ],
        )

        self.assertEqual(matches[0], "VP Bank - Gia Lai - Chi Ngoc")

    def test_manual_entry_syncs_hidden_gcn_fields_from_form_values(self) -> None:
        values = sync_hidden_gcn_fields_from_form(
            {
                "customer_info": "Nguyễn Văn A",
                "customer_address": "Xã A",
                "asset_description": "Thửa đất số 3, tờ bản đồ số 22; tại địa chỉ Xã Đak Đoa, tỉnh Gia Lai.",
                "so_thua": "",
                "so_to": "",
                "dia_chi": "",
                "chu_so_huu": "",
            }
        )

        self.assertEqual(values["chu_so_huu"], "Nguyễn Văn A")
        self.assertEqual(values["so_thua"], "3")
        self.assertEqual(values["so_to"], "22")
        self.assertEqual(values["dia_chi"], "Xã Đak Đoa, tỉnh Gia Lai")

    def test_editable_field_list_is_numbered(self) -> None:
        values = {
            "so_thua": "123",
            "so_to": "45",
            "dia_chi": "Dak Lak",
            "chu_so_huu": "Nguyen Van A",
            "customer_type": "individual",
            "contract_number": "010/2026/N04-1051/DN",
        }

        fields = editable_record_fields(values)
        text = format_editable_field_list(values)

        self.assertEqual(fields[0], ("customer_type", "Loại khách hàng"))
        self.assertNotIn("Số thửa", text)
        self.assertIn("1. Loại khách hàng: Cá nhân", text)
        self.assertIn("4. Số hợp đồng: N04-1051", text)

    async def test_missing_field_reply_updates_record_and_shows_confirmation(self) -> None:
        extraction = _sample_extraction().model_copy(update={"so_to_ban_do": _value("")})
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await init_records_db(db_path)
            record_id = await save_record(db_path, "data/uploads/gcn.pdf", extraction)
            context = Mock()
            context.user_data = {
                "pending_record": {
                    "record_id": record_id,
                    "db_path": db_path,
                    "values": {
                        "so_thua": "123",
                        "so_to": "",
                        "dia_chi": "Phuong Tan Loi",
                        "chu_so_huu": "Nguyen Van A",
                    },
                    "missing_fields": [("so_to", "So to ban do")],
                }
            }
            message = Mock()
            message.text = "45"
            message.reply_text = AsyncMock()
            update = Mock()
            update.effective_message = message

            state = await handle_missing_field_reply(update, context)

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("SELECT so_to FROM records WHERE id = ?", (record_id,))
                row = await cursor.fetchone()

        self.assertEqual(state, CONFIRMING)
        self.assertEqual(row, ("45",))
        self.assertEqual(context.user_data["pending_record"]["values"]["so_to"], "45")
        self.assertEqual(context.user_data["pending_record"]["missing_fields"], [])
        message.reply_text.assert_awaited()

    async def test_form_field_reply_updates_excel_supplemental_field(self) -> None:
        extraction = _sample_extraction()
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await init_records_db(db_path)
            record_id = await save_record(db_path, "data/uploads/gcn.pdf", extraction)
            context = Mock()
            context.user_data = {
                "pending_record": {
                    "record_id": record_id,
                    "db_path": db_path,
                    "values": {
                        "customer_type": "individual",
                        "contract_number": "",
                        "so_thua": "123",
                        "so_to": "45",
                        "chu_so_huu": "Nguyen Van A",
                    },
                    "form_fields": [("contract_number", "Số hợp đồng")],
                    "missing_fields": [],
                }
            }
            message = Mock()
            message.text = "010/2026/N04-1045/DN"
            message.reply_text = AsyncMock()
            update = Mock()
            update.effective_message = message

            state = await handle_missing_field_reply(update, context)

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("SELECT contract_number FROM records WHERE id = ?", (record_id,))
                row = await cursor.fetchone()

        self.assertEqual(state, CONFIRMING)
        self.assertEqual(row, ("010/2026/N04-1045/DN",))
        self.assertEqual(context.user_data["pending_record"]["values"]["contract_number"], "010/2026/N04-1045/DN")

    async def test_manual_entry_command_creates_blank_record_and_asks_first_field(self) -> None:
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await init_records_db(db_path)
            context = Mock()
            context.application.bot_data = {
                "settings": TelegramSettings(
                    bot_token="token",
                    webhook_url="https://example.com",
                    gemini_api_key="gemini-secret",
                    gemini_model="gemini-test",
                    upload_dir=str(Path(tmpdir) / "uploads"),
                    records_db_path=db_path,
                )
            }
            context.user_data = {}
            message = Mock()
            message.reply_text = AsyncMock()
            update = Mock()
            update.effective_message = message

            state = await start_manual_entry(update, context)

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("SELECT file_path, status FROM records")
                row = await cursor.fetchone()

        pending_record = context.user_data["pending_record"]
        self.assertEqual(state, ASK_MISSING_FIELD)
        self.assertEqual(row, ("manual_entry", PENDING_STATUS))
        self.assertEqual(pending_record["form_fields"][0][0], "customer_type")
        self.assertEqual(pending_record["missing_fields"], [])
        self.assertEqual(message.reply_text.await_count, 2)
        self.assertIn("Da tao ho so nhap thu cong", message.reply_text.await_args_list[0].args[0])
        self.assertIn("Nhập", message.reply_text.await_args_list[1].args[0])

    async def test_dropdown_field_keyword_search_asks_user_to_pick_match(self) -> None:
        extraction = _sample_extraction()
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await init_records_db(db_path)
            record_id = await save_record(db_path, "data/uploads/gcn.pdf", extraction)
            context = Mock()
            context.application.bot_data = {
                "excel_dropdown_options": {
                    "source": [
                        "VP Bank - Gia Lai - Chi Ngoc",
                        "VP Bank Kon Tum - Mr Luan",
                        "BIDV Gia Lai - Mr Cuong",
                    ]
                }
            }
            context.user_data = {
                "pending_record": {
                    "record_id": record_id,
                    "db_path": db_path,
                    "values": {"source": "", "so_thua": "123", "so_to": "45", "chu_so_huu": "Nguyen Van A"},
                    "form_fields": [("source", "Nguồn/đối tác")],
                    "missing_fields": [],
                }
            }
            message = Mock()
            message.text = "vp"
            message.reply_text = AsyncMock()
            update = Mock()
            update.effective_message = message

            state = await handle_missing_field_reply(update, context)

        self.assertEqual(state, CONFIRMING - 1)
        self.assertEqual(context.user_data["pending_record"]["pending_dropdown"]["field"], "source")
        self.assertEqual(len(context.user_data["pending_record"]["pending_dropdown"]["matches"]), 2)
        message.reply_text.assert_awaited()

    async def test_dropdown_field_numeric_choice_saves_matched_option(self) -> None:
        extraction = _sample_extraction()
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await init_records_db(db_path)
            record_id = await save_record(db_path, "data/uploads/gcn.pdf", extraction)
            context = Mock()
            context.application.bot_data = {"excel_dropdown_options": {}}
            context.user_data = {
                "pending_record": {
                    "record_id": record_id,
                    "db_path": db_path,
                    "values": {"source": "", "so_thua": "123", "so_to": "45", "chu_so_huu": "Nguyen Van A"},
                    "form_fields": [("source", "Nguồn/đối tác")],
                    "missing_fields": [],
                    "pending_dropdown": {
                        "field": "source",
                        "matches": ["VP Bank - Gia Lai - Chi Ngoc", "VP Bank Kon Tum - Mr Luan"],
                    },
                }
            }
            message = Mock()
            message.text = "1"
            message.reply_text = AsyncMock()
            update = Mock()
            update.effective_message = message

            state = await handle_missing_field_reply(update, context)

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("SELECT source FROM records WHERE id = ?", (record_id,))
                row = await cursor.fetchone()

        self.assertEqual(state, CONFIRMING)
        self.assertEqual(row, ("VP Bank - Gia Lai - Chi Ngoc",))
        self.assertNotIn("pending_dropdown", context.user_data["pending_record"])

    async def test_customer_type_organization_adds_organization_questions(self) -> None:
        extraction = _sample_extraction()
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await init_records_db(db_path)
            record_id = await save_record(db_path, "data/uploads/gcn.pdf", extraction)
            context = Mock()
            context.user_data = {
                "pending_record": {
                    "record_id": record_id,
                    "db_path": db_path,
                    "values": {
                        "customer_type": "individual",
                        "so_thua": "123",
                        "so_to": "45",
                        "chu_so_huu": "Nguyen Van A",
                    },
                    "form_fields": [("customer_type", "Loại khách hàng")],
                    "missing_fields": [],
                }
            }
            message = Mock()
            message.text = "tổ chức"
            message.reply_text = AsyncMock()
            update = Mock()
            update.effective_message = message

            await handle_missing_field_reply(update, context)

        remaining = [field for field, _label in context.user_data["pending_record"]["form_fields"]]
        self.assertEqual(context.user_data["pending_record"]["values"]["customer_type"], "organization")
        self.assertIn("tax_code", remaining)

    async def test_confirmation_callback_updates_status_to_confirmed(self) -> None:
        extraction = _sample_extraction()
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await init_records_db(db_path)
            record_id = await save_record(db_path, "data/uploads/gcn.pdf", extraction)
            context = Mock()
            context.application.bot_data = {
                "settings": TelegramSettings(
                    bot_token="token",
                    webhook_url="https://example.com",
                    gemini_api_key="gemini-secret",
                    gemini_model="gemini-test",
                    upload_dir="tmp/uploads",
                    records_db_path=db_path,
                    mail_to="ops@example.com",
                )
            }
            context.user_data = {
                "pending_record": {
                    "record_id": record_id,
                    "db_path": db_path,
                    "values": {},
                    "missing_fields": [],
                }
            }
            query = Mock()
            query.data = CONFIRM_CALLBACK
            query.answer = AsyncMock()
            query.edit_message_text = AsyncMock()
            query.message = Mock()
            query.message.chat_id = 123
            query.message.reply_text = AsyncMock()
            update = Mock()
            update.callback_query = query

            with patch("src.telegram_server.send_appraisal_email_preview", AsyncMock()) as preview_mock:
                await handle_confirmation_callback(update, context)

            async with aiosqlite.connect(db_path) as db:
                cursor = await db.execute("SELECT status FROM records WHERE id = ?", (record_id,))
                row = await cursor.fetchone()

        self.assertEqual(row, (CONFIRMED_STATUS,))
        self.assertNotIn("pending_record", context.user_data)
        query.answer.assert_awaited_once()
        query.edit_message_text.assert_awaited_once()
        query.message.reply_text.assert_awaited_once()
        preview_mock.assert_awaited_once()

    async def test_edit_callback_prompts_numbered_field_list(self) -> None:
        context = Mock()
        context.user_data = {
            "pending_record": {
                "record_id": 5,
                "db_path": "tmp/records.db",
                "values": {
                    "so_thua": "123",
                    "so_to": "45",
                    "dia_chi": "Dak Lak",
                    "chu_so_huu": "Nguyen Van A",
                    "customer_type": "individual",
                },
                "missing_fields": [],
            }
        }
        query = Mock()
        query.data = EDIT_CALLBACK
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        update = Mock()
        update.callback_query = query

        state = await handle_confirmation_callback(update, context)

        self.assertEqual(state, EDIT_FIELD_SELECT)
        query.edit_message_text.assert_awaited_once()
        self.assertIn("1. Loại khách hàng: Cá nhân", query.edit_message_text.await_args.args[0])

    async def test_edit_field_selection_sets_single_field_to_edit(self) -> None:
        context = Mock()
        context.user_data = {
            "pending_record": {
                "record_id": 5,
                "db_path": "tmp/records.db",
                "values": {
                    "so_thua": "123",
                    "so_to": "45",
                    "dia_chi": "Dak Lak",
                    "chu_so_huu": "Nguyen Van A",
                    "customer_type": "individual",
                },
                "missing_fields": [],
            }
        }
        message = Mock()
        message.text = "4"
        message.reply_text = AsyncMock()
        update = Mock()
        update.effective_message = message

        state = await handle_edit_field_selection(update, context)

        self.assertEqual(state, 0)
        self.assertEqual(context.user_data["pending_record"]["form_fields"], [("contract_number", "Số hợp đồng")])
        message.reply_text.assert_awaited_once()

    async def test_post_confirm_send_mail_callback_sends_email(self) -> None:
        context = Mock()
        context.user_data = {}
        context.application.bot_data = {
            "settings": TelegramSettings(
                bot_token="token",
                webhook_url="https://example.com",
                gemini_api_key="gemini-secret",
                gemini_model="gemini-test",
                upload_dir="tmp/uploads",
                records_db_path="tmp/records.db",
                mail_to="ops@example.com",
            )
        }
        query = Mock()
        query.data = f"{SEND_MAIL_CALLBACK_PREFIX}:9"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        update = Mock()
        update.callback_query = query

        with (
            patch("src.telegram_server.get_record", AsyncMock(return_value={"id": "9", "contract_number": "HD-009"})) as get_record_mock,
            patch("src.telegram_server.send_appraisal_email_service", AsyncMock()) as send_mail_mock,
        ):
            await handle_post_confirm_action(update, context)

        get_record_mock.assert_awaited_once_with("tmp/records.db", 9)
        send_mail_mock.assert_awaited_once()
        self.assertEqual(send_mail_mock.await_args.args[0]["to_email"], "ops@example.com")
        self.assertIn("Đã gửi mail thành công", query.edit_message_text.await_args.args[0])

    async def test_send_mail_by_contract_command_sends_matching_record(self) -> None:
        extraction = _sample_extraction()
        with TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "records.db")
            await init_records_db(db_path)
            record_id = await save_record(db_path, "data/uploads/gcn.pdf", extraction)
            await update_record_fields(db_path, record_id, {"contract_number": "010/2026/N04-1051/DN"})
            context = Mock()
            context.args = ["N04-1051"]
            context.application.bot_data = {
                "settings": TelegramSettings(
                    bot_token="token",
                    webhook_url="https://example.com",
                    gemini_api_key="gemini-secret",
                    gemini_model="gemini-test",
                    upload_dir=str(Path(tmpdir) / "uploads"),
                    records_db_path=db_path,
                    cases_db_path=str(Path(tmpdir) / "cases.db"),
                    mail_to="ops@example.com",
                )
            }
            message = Mock()
            message.reply_text = AsyncMock()
            update = Mock()
            update.effective_message = message

            with patch("src.telegram_server.send_appraisal_email_service", AsyncMock()) as send_mail_mock:
                await send_mail_by_contract_command(update, context)

        send_mail_mock.assert_awaited_once()
        self.assertEqual(send_mail_mock.await_args.args[0]["contract_number"], "010/2026/N04-1051/DN")
        self.assertEqual(send_mail_mock.await_args.args[0]["to_email"], "ops@example.com")
        self.assertIn("Đã gửi mail thành công cho hồ sơ N04-1051 từ Telegram", message.reply_text.await_args_list[-1].args[0])

    async def test_send_mail_by_contract_command_falls_back_to_main_cases_database(self) -> None:
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            records_db = str(root / "records.db")
            cases_db = str(root / "cases.db")
            await init_records_db(records_db)
            async with aiosqlite.connect(cases_db) as db:
                await db.execute(
                    """
                    CREATE TABLE cases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contract_number TEXT,
                        customer_info TEXT,
                        valuation_fee_number INTEGER,
                        source TEXT
                    )
                    """
                )
                await db.execute(
                    "INSERT INTO cases (contract_number, customer_info, valuation_fee_number, source) VALUES (?, ?, ?, ?)",
                    ("010/2026/N04-1051/DN", "Khách A", 2200000, "VP Bank"),
                )
                await db.commit()
            context = Mock()
            context.args = ["N04-1051"]
            context.application.bot_data = {
                "settings": TelegramSettings(
                    bot_token="token",
                    webhook_url="https://example.com",
                    gemini_api_key="gemini-secret",
                    gemini_model="gemini-test",
                    upload_dir=str(root / "uploads"),
                    records_db_path=records_db,
                    cases_db_path=cases_db,
                    mail_to="ops@example.com",
                )
            }
            message = Mock()
            message.reply_text = AsyncMock()
            update = Mock()
            update.effective_message = message

            with patch("src.telegram_server.send_appraisal_email_service", AsyncMock()) as send_mail_mock:
                await send_mail_by_contract_command(update, context)

        send_mail_mock.assert_awaited_once()
        self.assertEqual(send_mail_mock.await_args.args[0]["contract_number"], "010/2026/N04-1051/DN")
        self.assertEqual(send_mail_mock.await_args.args[0]["customer_info"], "Khách A")
        self.assertIn("từ quản lý hồ sơ", message.reply_text.await_args_list[-1].args[0])

    async def test_send_mail_by_contract_command_requires_contract_argument(self) -> None:
        context = Mock()
        context.args = []
        message = Mock()
        message.reply_text = AsyncMock()
        update = Mock()
        update.effective_message = message

        await send_mail_by_contract_command(update, context)

        message.reply_text.assert_awaited_once()
        self.assertIn("/gui_mail N04-1051", message.reply_text.await_args.args[0])

    async def test_chat_id_command_saves_chat_id_to_api_env(self) -> None:
        with TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / "API.env"
            env_path.write_text("MAIL_TO=ops@example.com\n", encoding="utf-8")
            message = Mock()
            message.reply_text = AsyncMock()
            update = Mock()
            update.effective_message = message
            update.effective_chat.id = 123456
            context = Mock()

            with patch("src.telegram_server.PROJECT_ROOT", str(Path(tmpdir))):
                await chat_id_command(update, context)

            text = env_path.read_text(encoding="utf-8")

        self.assertIn("TELEGRAM_CHAT_ID=123456", text)
        message.reply_text.assert_awaited_once()

    async def test_listener_on_command_enables_and_starts_background_process(self) -> None:
        message = Mock()
        message.reply_text = AsyncMock()
        update = Mock()
        update.effective_message = message
        update.effective_user.username = "tester"
        context = Mock()

        with (
            patch("src.telegram_server.set_listener_enabled") as enabled_mock,
            patch("src.telegram_server._start_mail_listener_background", return_value=456) as start_mock,
            patch("src.telegram_server._format_listener_status", return_value="status text"),
        ):
            await listener_on_command(update, context)

        enabled_mock.assert_called_once_with(True, updated_by="telegram:tester")
        start_mock.assert_called_once()
        self.assertIn("PID: 456", message.reply_text.await_args.args[0])

    async def test_listener_off_command_disables_without_killing_process(self) -> None:
        message = Mock()
        message.reply_text = AsyncMock()
        update = Mock()
        update.effective_message = message
        update.effective_user = None
        context = Mock()

        with (
            patch("src.telegram_server.set_listener_enabled") as enabled_mock,
            patch("src.telegram_server._format_listener_status", return_value="status text"),
        ):
            await listener_off_command(update, context)

        enabled_mock.assert_called_once_with(False, updated_by="telegram")
        self.assertIn("Đã tắt theo dõi Gmail", message.reply_text.await_args.args[0])

    async def test_listener_status_command_reports_current_status(self) -> None:
        message = Mock()
        message.reply_text = AsyncMock()
        update = Mock()
        update.effective_message = message
        context = Mock()

        with patch("src.telegram_server._format_listener_status", return_value="listener status"):
            await listener_status_command(update, context)

        message.reply_text.assert_awaited_once_with("listener status")

    async def test_listener_log_command_sends_recent_log_lines(self) -> None:
        message = Mock()
        message.reply_text = AsyncMock()
        update = Mock()
        update.effective_message = message
        context = Mock()

        with patch("src.telegram_server.read_recent_listener_logs", return_value=[
            {
                "time": "2026-05-02T10:00:00+07:00",
                "event": "matched",
                "record_id": "2",
                "score": 1.0,
                "subject": "Xin so hop dong N04-1070",
            }
        ]):
            await listener_log_command(update, context)

        text = message.reply_text.await_args.args[0]
        self.assertIn("10 dòng log", text)
        self.assertIn("[matched]", text)
        self.assertIn("HS #2", text)

    async def test_post_confirm_web_callback_starts_background_task(self) -> None:
        context = Mock()
        context.user_data = {}
        context.application.bot_data = {
            "settings": TelegramSettings(
                bot_token="token",
                webhook_url="https://example.com",
                gemini_api_key="gemini-secret",
                gemini_model="gemini-test",
                upload_dir="tmp/uploads",
                records_db_path="tmp/records.db",
            )
        }
        query = Mock()
        query.data = f"{WEB_AUTOMATION_CALLBACK_PREFIX}:9"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.message.chat_id = 123
        update = Mock()
        update.callback_query = query

        created_tasks = []

        def fake_create_task(coro):
            created_tasks.append(coro)
            coro.close()
            return Mock()

        with patch("src.telegram_server.create_task", side_effect=fake_create_task):
            await handle_post_confirm_action(update, context)

        self.assertEqual(len(created_tasks), 1)
        query.edit_message_text.assert_awaited_once()

    def test_automation_keyboard_contains_record_actions(self) -> None:
        keyboard = automation_keyboard(11)
        # keyboard.inline_keyboard is [[btn1], [btn2], [btn3]]
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, f"{SEND_MAIL_CALLBACK_PREFIX}:11")
        self.assertEqual(keyboard.inline_keyboard[1][0].callback_data, f"{WEB_AUTOMATION_CALLBACK_PREFIX}:11")

    async def test_process_file_downloads_extracts_and_saves_record(self) -> None:
        extraction = _sample_extraction()
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            settings = TelegramSettings(
                bot_token="token",
                webhook_url="https://example.com",
                gemini_api_key="gemini-secret",
                gemini_model="gemini-test",
                upload_dir=str(root / "uploads"),
                records_db_path=str(root / "records.db"),
            )
            await init_records_db(settings.records_db_path)

            downloaded_file = Mock()
            downloaded_file.download_to_drive = AsyncMock(
                side_effect=lambda custom_path: Path(custom_path).write_bytes(b"%PDF-1.4\nsample")
            )
            file_ref = Mock()
            file_ref.get_file = AsyncMock(return_value=downloaded_file)

            with patch("src.telegram_server.extract_land_certificate_with_gemini", return_value=extraction) as gemini:
                record_id, upload_path, result = await process_land_certificate_file(
                    file_ref=file_ref,
                    file_name="GCN mau.pdf",
                    settings=settings,
                )

            async with aiosqlite.connect(settings.records_db_path) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM records WHERE id = ?", (record_id,))
                count_row = await cursor.fetchone()

            self.assertIs(result, extraction)
            self.assertTrue(Path(upload_path).exists())
            self.assertEqual(Path(upload_path).parent.name, "uploads")
            self.assertEqual(count_row[0], 1)
            gemini.assert_called_once_with(upload_path, api_key="gemini-secret", model="gemini-test")

    def test_format_extraction_response(self) -> None:
        response = format_extraction_response(7, _sample_extraction())

        self.assertIn("ban ghi #7", response)
        self.assertIn("So thua: 123", response)
        self.assertIn("So to ban do: 45", response)
        self.assertIn("Chu so huu: Nguyen Van A", response)
        self.assertIn(f"Trang thai: {PENDING_STATUS}", response)


if __name__ == "__main__":
    unittest.main()
