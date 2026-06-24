from __future__ import annotations

import os
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, Mock, patch

from telegram.ext import ConversationHandler

from src.models import ExtractedValue, LandCertificateExtraction, LandCertificateMultiExtraction
from src.sobo_handler import (
    SOBO_ASSET_SELECT,
    SOBO_DOC,
    SOBO_EMAIL_OPTIONS,
    SOBO_LOC,
    SOBO_MACHINERY_DOC,
    SOBO_MACHINERY_DOC_CHOICE,
    SOBO_MACHINERY_EMAIL,
    SOBO_MACHINERY_NAME,
    SOBO_CONFIRM,
    SOBO_NOTE,
    _process_sobo_extracted_file,
    build_machinery_email_content,
    build_sobo_email_content,
    build_department_email_keyboard,
    cmd_sobo,
    sobo_receive_machinery_doc,
    sobo_receive_machinery_name,
    sobo_machinery_doc_choice,
    sobo_receive_note,
    sobo_receive_source,
    sobo_handle_confirm,
    sobo_require_email_selection,
    sobo_require_machinery_file,
    sobo_select_asset_type,
    sobo_select_email,
    get_sobo_conversation_handler,
    SOBO_RE_SUB_TYPE,
    SOBO_DOC_MULTI,
    SOBO_DOC_MULTI_CHOICE,
    sobo_select_re_sub_type,
    _process_sobo_extracted_file_multi,
    sobo_multi_doc_choice,
    _handle_machinery_media_group_photos,
    cleanup_old_sobo_uploads,
    sobo_receive_doc,
)


def _value(value: str) -> ExtractedValue:
    return ExtractedValue(value=value, confidence=0.95, evidence=value)


class SoboHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_command_starts_with_two_asset_type_choices(self) -> None:
        update = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        context.user_data = {}

        state = await cmd_sobo(update, context)

        self.assertEqual(state, SOBO_ASSET_SELECT)
        keyboard = update.message.reply_text.await_args.kwargs["reply_markup"]
        labels = [row[0].text for row in keyboard.inline_keyboard]
        self.assertIn("🏠 Bất động sản", labels)
        self.assertIn("⚙️ Máy móc thiết bị", labels)

    def test_cleanup_old_sobo_uploads_only_removes_stale_sobo_files(self) -> None:
        with TemporaryDirectory() as tmpdir:
            old_sobo = Path(tmpdir) / "sobo_old.pdf"
            old_other = Path(tmpdir) / "other_old.pdf"
            new_sobo = Path(tmpdir) / "sobo_new.pdf"
            for path in (old_sobo, old_other, new_sobo):
                path.write_text("x", encoding="utf-8")

            now = 1_000_000.0
            old_mtime = now - (91 * 24 * 60 * 60)
            new_mtime = now - (10 * 24 * 60 * 60)
            os.utime(old_sobo, (old_mtime, old_mtime))
            os.utime(old_other, (old_mtime, old_mtime))
            os.utime(new_sobo, (new_mtime, new_mtime))

            removed = cleanup_old_sobo_uploads(tmpdir, now=now)

            self.assertEqual(removed, 1)
            self.assertFalse(old_sobo.exists())
            self.assertTrue(old_other.exists())
            self.assertTrue(new_sobo.exists())

    async def test_real_estate_doc_upload_is_rejected_while_ocr_is_running(self) -> None:
        update = Mock()
        update.message.document = Mock(file_id="file-1")
        update.message.photo = None
        update.message.reply_text = AsyncMock()
        context = Mock()
        context.user_data = {"sobo": {"ocr_processing": True}}

        with patch("asyncio.create_task") as create_task:
            state = await sobo_receive_doc(update, context)

        self.assertEqual(state, SOBO_DOC)
        create_task.assert_not_called()
        self.assertIn("đang quét", update.message.reply_text.await_args.args[0].lower())

    def test_email_content_uses_approved_template_and_escapes_values(self) -> None:
        body, body_html = build_sobo_email_content(
            {
                "source": "VCB <Gia Lai>",
                "so_thua": "72",
                "so_to": "13",
                "dia_chi": "Khu phố 2 & phường Xuân Hòa",
                "link": "https://maps.google.com/?q=1&z=2",
                "note": "Hồ sơ cần phản hồi <gấp>",
            }
        )

        self.assertIn("Kính gửi Anh/Chị", body)
        self.assertIn("Quyền sử dụng đất và CTXD (nếu có hoàn công trên sổ)", body)
        self.assertIn("Em gửi thông tin tài sản cần hỗ trợ tham khảo giá trị sơ bộ như sau", body_html)
        self.assertIn("Kính nhờ Anh/Chị hỗ trợ sơ bộ tài sản nêu trên", body_html)
        self.assertIn("cid:cenvalue_logo", body_html)
        self.assertIn("VCB &lt;Gia Lai&gt;", body_html)
        self.assertIn("Khu phố 2 &amp; phường Xuân Hòa", body_html)
        self.assertIn("Ghi chú: Hồ sơ cần phản hồi <gấp>", body)
        self.assertIn("Hồ sơ cần phản hồi &lt;gấp&gt;", body_html)
        self.assertNotIn("VCB <Gia Lai>", body_html)

    def test_email_content_does_not_create_unsafe_location_link(self) -> None:
        _, body_html = build_sobo_email_content({"link": "javascript:alert(1)"})

        self.assertIn('href="#"', body_html)
        self.assertNotIn('href="javascript:', body_html)

    def test_machinery_email_content_only_uses_equipment_name_field(self) -> None:
        body, body_html = build_machinery_email_content(
            {"equipment_name": "Máy cắt <CNC>", "note": "Kiểm tra serial & công suất"}
        )

        self.assertIn("Máy móc thiết bị", body)
        self.assertIn("Tên thiết bị: Máy cắt <CNC>", body)
        self.assertIn("Máy cắt &lt;CNC&gt;", body_html)
        self.assertIn("Ghi chú: Kiểm tra serial & công suất", body)
        self.assertIn("Kiểm tra serial &amp; công suất", body_html)
        self.assertNotIn("Số thửa đất", body_html)
        self.assertNotIn("Định vị tài sản", body_html)

    def test_email_keyboard_marks_suggested_destination(self) -> None:
        suggested = SOBO_EMAIL_OPTIONS[0]
        keyboard = build_department_email_keyboard(suggested)

        self.assertIn("(gợi ý)", keyboard.inline_keyboard[0][0].text)
        self.assertEqual(keyboard.inline_keyboard[0][0].callback_data, "sobo_email_0")
        self.assertEqual(keyboard.inline_keyboard[-1][0].callback_data, "sobo_cancel")

    async def test_extraction_prompts_for_manual_email_selection(self) -> None:
        extraction = LandCertificateExtraction(
            so_thua_dat=_value("72"),
            so_to_ban_do=_value("13"),
            dia_chi_thua_dat=_value("Khu phố 2, phường Xuân Hoà, Gia Lai"),
            ten_chu_so_huu_cuoi_cung=_value("Nguyen Van A"),
            dia_chi_chu_so_huu_cuoi_cung=_value("Gia Lai"),
            so_cccd_chu_so_huu_cuoi_cung=_value("012345678901"),
            notes=[],
        )
        update = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        context.user_data = {"sobo": {}}

        with patch("asyncio.to_thread", AsyncMock(return_value=extraction)):
            state = await _process_sobo_extracted_file(update, context, str(Path("gcn.pdf")))

        self.assertEqual(state, SOBO_DOC)
        self.assertNotIn("email", context.user_data["sobo"])
        args, kwargs = update.message.reply_text.await_args
        self.assertIn("chọn", args[0].lower())
        self.assertIsNotNone(kwargs["reply_markup"])

    async def test_extraction_merges_multiple_assets_for_hop_khoi(self) -> None:
        extraction = LandCertificateMultiExtraction(
            assets=[
                LandCertificateExtraction(
                    so_thua_dat=_value("234"),
                    so_to_ban_do=_value("54"),
                    dia_chi_thua_dat=_value("Phường Pleiku, Gia Lai"),
                    ten_chu_so_huu_cuoi_cung=_value("Nguyen Van A"),
                    dia_chi_chu_so_huu_cuoi_cung=_value("Gia Lai"),
                    so_cccd_chu_so_huu_cuoi_cung=_value("012345678901"),
                    notes=[],
                ),
                LandCertificateExtraction(
                    so_thua_dat=_value("235"),
                    so_to_ban_do=_value("54"),
                    dia_chi_thua_dat=_value("Phường Pleiku, Gia Lai"),
                    ten_chu_so_huu_cuoi_cung=_value("Nguyen Van A"),
                    dia_chi_chu_so_huu_cuoi_cung=_value("Gia Lai"),
                    so_cccd_chu_so_huu_cuoi_cung=_value("012345678901"),
                    notes=[],
                )
            ]
        )
        update = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        context.user_data = {"sobo": {}}

        with patch("asyncio.to_thread", AsyncMock(return_value=extraction)):
            state = await _process_sobo_extracted_file(update, context, str(Path("gcn.pdf")))

        self.assertEqual(state, SOBO_DOC)
        self.assertEqual(context.user_data["sobo"]["so_thua"], "234 + 235")
        self.assertEqual(context.user_data["sobo"]["so_to"], "54")
        self.assertEqual(context.user_data["sobo"]["dia_chi"], "Phường Pleiku, Gia Lai")
        self.assertEqual(context.user_data["sobo"]["suggested_email"], "Sobo.taynguyen@gmail.com")

    async def test_selected_email_is_saved_before_requesting_location(self) -> None:
        update = Mock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = "sobo_email_2"
        context = Mock()
        context.user_data = {"sobo": {}}

        state = await sobo_select_email(update, context)

        self.assertEqual(state, SOBO_LOC)
        self.assertEqual(context.user_data["sobo"]["email"], SOBO_EMAIL_OPTIONS[2])
        update.callback_query.edit_message_text.assert_awaited_once()

    async def test_machinery_asset_branch_requests_file_attachment(self) -> None:
        update = Mock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = "sobo_asset_machinery"
        context = Mock()
        context.user_data = {"sobo": {}}

        state = await sobo_select_asset_type(update, context)

        self.assertEqual(state, SOBO_MACHINERY_DOC)
        self.assertEqual(context.user_data["sobo"]["asset_type"], "machinery")
        self.assertEqual(context.user_data["sobo"]["file_paths"], [])
        self.assertEqual(context.user_data["sobo"]["attachment_names"], [])
        message = update.callback_query.edit_message_text.await_args.args[0]
        self.assertIn("không được quét hoặc phân tích", message)

    async def test_machinery_uploaded_file_opens_add_more_or_finish_choice_without_scanning(self) -> None:
        update = Mock()
        update.message.document.file_id = "file-1"
        update.message.document.file_name = "may_<cat>.pdf"
        update.message.photo = None
        update.message.reply_text = AsyncMock()
        telegram_file = Mock()
        telegram_file.download_to_drive = AsyncMock()
        context = Mock()
        context.user_data = {"sobo": {"asset_type": "machinery"}}
        context.bot.get_file = AsyncMock(return_value=telegram_file)

        with patch("src.sobo_handler.extract_land_certificate_with_gemini") as extract:
            state = await sobo_receive_machinery_doc(update, context)

        self.assertEqual(state, SOBO_MACHINERY_DOC_CHOICE)
        self.assertEqual(context.user_data["sobo"]["attachment_names"], ["may_<cat>.pdf"])
        self.assertEqual(len(context.user_data["sobo"]["file_paths"]), 1)
        telegram_file.download_to_drive.assert_awaited_once()
        extract.assert_not_called()
        keyboard = update.message.reply_text.await_args.kwargs["reply_markup"]
        labels = [row[0].text for row in keyboard.inline_keyboard]
        self.assertIn("➕ Tải thêm tài liệu", labels)
        self.assertIn("✅ Kết thúc", labels)
        self.assertIn("may_&lt;cat&gt;.pdf", update.message.reply_text.await_args.args[0])

    async def test_machinery_finish_after_documents_prompts_for_equipment_name(self) -> None:
        update = Mock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = "sobo_machinery_done"
        context = Mock()
        context.user_data = {"sobo": {"attachment_names": ["ho_so.pdf"], "file_paths": ["ho_so.pdf"]}}

        state = await sobo_machinery_doc_choice(update, context)

        self.assertEqual(state, SOBO_MACHINERY_NAME)
        self.assertIn("Tên thiết bị", update.callback_query.edit_message_text.await_args.args[0])

    async def test_machinery_additional_document_returns_to_upload_step(self) -> None:
        update = Mock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = "sobo_machinery_more"
        context = Mock()
        context.user_data = {"sobo": {"attachment_names": ["ho_so.pdf"], "file_paths": ["ho_so.pdf"]}}

        state = await sobo_machinery_doc_choice(update, context)

        self.assertEqual(state, SOBO_MACHINERY_DOC)
        self.assertIn("tiếp theo", update.callback_query.edit_message_text.await_args.args[0])

    async def test_machinery_photo_album_is_merged_into_one_pdf_attachment(self) -> None:
        update1 = Mock()
        update1.message.message_id = 1
        update1.message.photo = [Mock(file_id="photo-1", file_unique_id="unique-1")]
        update1.message.reply_text = AsyncMock()
        update2 = Mock()
        update2.message.message_id = 2
        update2.message.photo = [Mock(file_id="photo-2", file_unique_id="unique-2")]
        context = Mock()
        context.user_data = {"sobo": {"asset_type": "machinery", "file_paths": [], "attachment_names": []}}
        logo_path = Path("src/templates/logo.jpg")
        file1 = Mock()
        file1.download_to_drive = AsyncMock(side_effect=lambda path: shutil.copyfile(logo_path, path))
        file2 = Mock()
        file2.download_to_drive = AsyncMock(side_effect=lambda path: shutil.copyfile(logo_path, path))
        context.bot.get_file = AsyncMock(side_effect=[file1, file2])

        state = await _handle_machinery_media_group_photos([update1, update2], context)
        merged_path = Path(context.user_data["sobo"]["file_paths"][0])
        try:
            import fitz

            with fitz.open(merged_path) as document:
                self.assertEqual(document.page_count, 2)
            self.assertEqual(state, SOBO_MACHINERY_DOC_CHOICE)
            self.assertEqual(len(context.user_data["sobo"]["attachment_names"]), 1)
        finally:
            merged_path.unlink(missing_ok=True)

    def test_machinery_upload_state_accepts_background_album_choice_callbacks(self) -> None:
        conversation = get_sobo_conversation_handler()
        callbacks = [
            handler.callback
            for handler in conversation.states[SOBO_MACHINERY_DOC]
            if hasattr(handler, "callback")
        ]

        self.assertIn(sobo_machinery_doc_choice, callbacks)

    async def test_machinery_name_prompts_for_email_selection(self) -> None:
        update = Mock()
        update.message.text = "Máy cắt CNC"
        update.message.reply_text = AsyncMock()
        context = Mock()
        context.user_data = {"sobo": {"asset_type": "machinery"}}

        state = await sobo_receive_machinery_name(update, context)

        self.assertEqual(state, SOBO_MACHINERY_EMAIL)
        self.assertEqual(context.user_data["sobo"]["equipment_name"], "Máy cắt CNC")
        self.assertIsNotNone(update.message.reply_text.await_args.kwargs["reply_markup"])

    async def test_machinery_branch_rejects_name_before_file_upload(self) -> None:
        update = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()

        state = await sobo_require_machinery_file(update, context)

        self.assertEqual(state, SOBO_MACHINERY_DOC)
        prompt = update.message.reply_text.await_args.args[0]
        self.assertIn("tải lên file", prompt)

    async def test_machinery_email_selection_prompts_for_note_without_location_step(self) -> None:
        update = Mock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = "sobo_email_0"
        context = Mock()
        context.user_data = {
            "sobo": {
                "asset_type": "machinery",
                "equipment_name": "Máy cắt CNC",
                "attachment_names": ["may_cat.pdf", "anh_thiet_bi.pdf"],
            }
        }

        state = await sobo_select_email(update, context)

        self.assertEqual(state, SOBO_NOTE)
        prompt = update.callback_query.edit_message_text.await_args.args[0]
        self.assertIn("ghi chú", prompt.lower())
        self.assertNotIn("Link định vị", prompt)

    async def test_machinery_note_opens_send_preview_with_note(self) -> None:
        update = Mock()
        update.message.text = "Ưu tiên phản hồi trong ngày"
        update.message.reply_text = AsyncMock()
        context = Mock()
        context.user_data = {
            "sobo": {
                "asset_type": "machinery",
                "equipment_name": "Máy cắt CNC",
                "attachment_names": ["may_cat.pdf", "anh_thiet_bi.pdf"],
                "email": SOBO_EMAIL_OPTIONS[0],
            }
        }

        state = await sobo_receive_note(update, context)

        self.assertEqual(state, SOBO_CONFIRM)
        self.assertEqual(
            context.user_data["sobo"]["subject"],
            "[SƠ BỘ] - Máy móc thiết bị - Máy cắt CNC",
        )
        preview = update.message.reply_text.await_args.args[0]
        self.assertIn("may_cat.pdf", preview)
        self.assertIn("anh_thiet_bi.pdf", preview)
        self.assertIn("Ghi chú: Ưu tiên phản hồi trong ngày", preview)

    async def test_machinery_send_includes_all_collected_attachments(self) -> None:
        update = Mock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = "sobo_send"
        context = Mock()
        context.user_data = {
            "sobo": {
                "asset_type": "machinery",
                "email": SOBO_EMAIL_OPTIONS[0],
                "subject": "Subject",
                "body": "Body",
                "body_html": "<p>Body</p>",
                "file_paths": ["may_cat.pdf", "anh_thiet_bi.pdf"],
            }
        }

        with patch(
            "src.sobo_handler.send_sobo_email_with_result",
            AsyncMock(return_value=Mock(success=True)),
        ) as send:
            state = await sobo_handle_confirm(update, context)

        self.assertEqual(state, ConversationHandler.END)
        self.assertEqual(send.await_args.kwargs["attachment_path"], ["may_cat.pdf", "anh_thiet_bi.pdf"])

    async def test_real_estate_source_prompts_for_note_before_preview(self) -> None:
        update = Mock()
        update.message.text = "VCB Gia Lai"
        update.message.reply_text = AsyncMock()
        context = Mock()
        context.user_data = {"sobo": {"email": SOBO_EMAIL_OPTIONS[0]}}

        state = await sobo_receive_source(update, context)

        self.assertEqual(state, SOBO_NOTE)
        self.assertEqual(context.user_data["sobo"]["source"], "VCB Gia Lai")
        prompt = update.message.reply_text.await_args.args[0]
        self.assertIn("ghi chú", prompt.lower())

    async def test_real_estate_note_opens_send_preview_with_note(self) -> None:
        update = Mock()
        update.message.text = "Tài sản có lối đi chung"
        update.message.reply_text = AsyncMock()
        context = Mock()
        context.user_data = {
            "sobo": {
                "asset_sub_type": "single",
                "source": "VCB Gia Lai",
                "so_thua": "72",
                "so_to": "13",
                "dia_chi": "Pleiku, Gia Lai",
                "email": SOBO_EMAIL_OPTIONS[0],
            }
        }

        state = await sobo_receive_note(update, context)

        self.assertEqual(state, SOBO_CONFIRM)
        self.assertEqual(context.user_data["sobo"]["note"], "Tài sản có lối đi chung")
        preview = update.message.reply_text.await_args.args[0]
        self.assertIn("Ghi chú: Tài sản có lối đi chung", preview)

    async def test_location_text_before_email_selection_is_rejected(self) -> None:
        update = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()

        state = await sobo_require_email_selection(update, context)

        self.assertEqual(state, SOBO_DOC)
        update.message.reply_text.assert_awaited_once()

    async def test_invalid_email_callback_ends_conversation(self) -> None:
        update = Mock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = "sobo_email_999"
        context = Mock()
        context.user_data = {"sobo": {}}

        state = await sobo_select_email(update, context)

        self.assertEqual(state, ConversationHandler.END)
        self.assertNotIn("sobo", context.user_data)

    async def test_real_estate_asset_select_sub_types(self) -> None:
        update = Mock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = "sobo_asset_real_estate"
        context = Mock()
        context.user_data = {"sobo": {}}

        state = await sobo_select_asset_type(update, context)

        self.assertEqual(state, SOBO_RE_SUB_TYPE)
        self.assertEqual(context.user_data["sobo"]["asset_type"], "real_estate")
        update.callback_query.edit_message_text.assert_awaited_once()
        keyboard = update.callback_query.edit_message_text.await_args.kwargs["reply_markup"]
        labels = [row[0].text for row in keyboard.inline_keyboard]
        self.assertIn("📄 Hồ sơ 1 tài sản", labels)
        self.assertIn("📚 Hồ sơ nhiều tài sản", labels)

    async def test_re_sub_type_select_single(self) -> None:
        update = Mock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = "sobo_re_single"
        context = Mock()
        context.user_data = {"sobo": {}}

        state = await sobo_select_re_sub_type(update, context)

        self.assertEqual(state, SOBO_DOC)
        self.assertEqual(context.user_data["sobo"]["asset_sub_type"], "single")
        update.callback_query.edit_message_text.assert_awaited_once()

    async def test_re_sub_type_select_multi(self) -> None:
        update = Mock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = "sobo_re_multi"
        context = Mock()
        context.user_data = {"sobo": {}}

        state = await sobo_select_re_sub_type(update, context)

        self.assertEqual(state, SOBO_DOC_MULTI)
        self.assertEqual(context.user_data["sobo"]["asset_sub_type"], "multi")
        self.assertEqual(context.user_data["sobo"]["assets_list"], [])
        self.assertEqual(context.user_data["sobo"]["file_paths"], [])
        update.callback_query.edit_message_text.assert_awaited_once()

    def test_multi_document_state_accepts_post_scan_choice_callbacks(self) -> None:
        conversation = get_sobo_conversation_handler()
        callbacks = [
            handler.callback
            for handler in conversation.states[SOBO_DOC_MULTI]
            if hasattr(handler, "callback")
        ]

        self.assertIn(sobo_multi_doc_choice, callbacks)

    async def test_multi_asset_scanning_loop(self) -> None:
        # Asset 1
        extraction1 = LandCertificateExtraction(
            so_thua_dat=_value("234"),
            so_to_ban_do=_value("54"),
            dia_chi_thua_dat=_value("Phường Pleiku, Gia Lai"),
            ten_chu_so_huu_cuoi_cung=_value("Nguyen Van A"),
            dia_chi_chu_so_huu_cuoi_cung=_value("Gia Lai"),
            so_cccd_chu_so_huu_cuoi_cung=_value("012345678901"),
            notes=[],
        )
        update1 = Mock()
        update1.message.reply_text = AsyncMock()
        context = Mock()
        context.user_data = {"sobo": {"asset_type": "real_estate", "asset_sub_type": "multi", "assets_list": [], "file_paths": [], "attachment_names": []}}

        with patch("asyncio.to_thread", AsyncMock(return_value=extraction1)):
            state = await _process_sobo_extracted_file_multi(update1, context, str(Path("gcn1.pdf")))

        self.assertEqual(state, SOBO_DOC_MULTI_CHOICE)
        self.assertEqual(len(context.user_data["sobo"]["assets_list"]), 1)
        self.assertEqual(context.user_data["sobo"]["assets_list"][0]["so_thua"], "234")
        self.assertEqual(context.user_data["sobo"]["assets_list"][0]["so_to"], "54")
        self.assertEqual(context.user_data["sobo"]["assets_list"][0]["dia_chi"], "Phường Pleiku, Gia Lai")

        # Select next
        update_query_next = Mock()
        update_query_next.callback_query.answer = AsyncMock()
        update_query_next.callback_query.edit_message_text = AsyncMock()
        update_query_next.callback_query.data = "sobo_multi_next"

        state_next = await sobo_multi_doc_choice(update_query_next, context)
        self.assertEqual(state_next, SOBO_DOC_MULTI)

        # Asset 2
        extraction2 = LandCertificateExtraction(
            so_thua_dat=_value("235"),
            so_to_ban_do=_value("54"),
            dia_chi_thua_dat=_value("Phường Pleiku, Gia Lai"),
            ten_chu_so_huu_cuoi_cung=_value("Nguyen Van A"),
            dia_chi_chu_so_huu_cuoi_cung=_value("Gia Lai"),
            so_cccd_chu_so_huu_cuoi_cung=_value("012345678901"),
            notes=[],
        )
        update2 = Mock()
        update2.message.reply_text = AsyncMock()

        with patch("asyncio.to_thread", AsyncMock(return_value=extraction2)):
            state = await _process_sobo_extracted_file_multi(update2, context, str(Path("gcn2.pdf")))
        self.assertEqual(state, SOBO_DOC_MULTI_CHOICE)
        self.assertEqual(len(context.user_data["sobo"]["assets_list"]), 2)
        self.assertEqual(context.user_data["sobo"]["assets_list"][1]["so_thua"], "235")

        # Select done
        update_query_done = Mock()
        update_query_done.callback_query.answer = AsyncMock()
        update_query_done.callback_query.edit_message_text = AsyncMock()
        update_query_done.callback_query.data = "sobo_multi_done"
    
        state_done = await sobo_multi_doc_choice(update_query_done, context)
        self.assertEqual(state_done, SOBO_DOC_MULTI_CHOICE)

        # Confirm selection
        update_query_confirm = Mock()
        update_query_confirm.callback_query.answer = AsyncMock()
        update_query_confirm.callback_query.edit_message_text = AsyncMock()
        update_query_confirm.callback_query.data = "sobo_multi_confirm"

        state_confirm = await sobo_multi_doc_choice(update_query_confirm, context)
        self.assertEqual(state_confirm, SOBO_DOC)
        self.assertEqual(context.user_data["sobo"]["suggested_email"], "Sobo.taynguyen@gmail.com")

    async def test_multi_asset_pdf_keeps_every_extracted_asset(self) -> None:
        extraction = LandCertificateMultiExtraction(
            assets=[
                LandCertificateExtraction(
                    so_thua_dat=_value("264"),
                    so_to_ban_do=_value("68"),
                    dia_chi_thua_dat=_value("Plei Dur, Gia Lai"),
                    ten_chu_so_huu_cuoi_cung=_value("Dang Thi Kieu Mi"),
                    dia_chi_chu_so_huu_cuoi_cung=_value("Gia Lai"),
                    so_cccd_chu_so_huu_cuoi_cung=_value(""),
                    notes=[],
                ),
                LandCertificateExtraction(
                    so_thua_dat=_value("38"),
                    so_to_ban_do=_value("74"),
                    dia_chi_thua_dat=_value("Plei Wet, Gia Lai"),
                    ten_chu_so_huu_cuoi_cung=_value("Dang Thi Kieu Mi"),
                    dia_chi_chu_so_huu_cuoi_cung=_value("Gia Lai"),
                    so_cccd_chu_so_huu_cuoi_cung=_value(""),
                    notes=[],
                ),
            ]
        )
        update = Mock()
        update.message.reply_text = AsyncMock()
        context = Mock()
        context.user_data = {
            "sobo": {
                "asset_type": "real_estate",
                "asset_sub_type": "multi",
                "assets_list": [],
                "file_paths": [],
                "attachment_names": [],
            }
        }

        with patch("asyncio.to_thread", AsyncMock(return_value=extraction)):
            state = await _process_sobo_extracted_file_multi(update, context, str(Path("two_assets.pdf")))

        self.assertEqual(state, SOBO_DOC_MULTI_CHOICE)
        self.assertEqual(
            context.user_data["sobo"]["assets_list"],
            [
                {"so_thua": "264", "so_to": "68", "dia_chi": "Plei Dur, Gia Lai"},
                {"so_thua": "38", "so_to": "74", "dia_chi": "Plei Wet, Gia Lai"},
            ],
        )
        self.assertEqual(context.user_data["sobo"]["file_paths"], ["two_assets.pdf"])
        message = update.message.reply_text.await_args.args[0]
        self.assertIn("2 tài sản", message)
        self.assertIn("Thửa: 264", message)
        self.assertIn("Thửa: 38", message)

    def test_build_email_content_multi(self) -> None:
        sobo = {
            "source": "KH Hợp Khối",
            "asset_sub_type": "multi",
            "assets_list": [
                {"so_thua": "234", "so_to": "54", "dia_chi": "Pleiku, Gia Lai"},
                {"so_thua": "235", "so_to": "54", "dia_chi": "Pleiku, Gia Lai"}
            ],
            "link": "https://maps.google.com/?q=1&z=2",
            "note": "Định giá gấp trong ngày"
        }
        body, body_html = build_sobo_email_content(sobo)

        self.assertIn("DANH SÁCH CHI TIẾT TÀI SẢN:", body)
        self.assertIn("Tài sản 1:", body)
        self.assertIn("Số thửa đất: 234", body)
        self.assertIn("Tài sản 2:", body)
        self.assertIn("Số thửa đất: 235", body)
        self.assertIn("Ghi chú: Định giá gấp trong ngày", body)

        self.assertIn("THÔNG TIN TÀI SẢN THẨM ĐỊNH", body_html)
        self.assertIn("Tài sản 1", body_html)
        self.assertIn("Tài sản 2", body_html)
        self.assertIn("Pleiku, Gia Lai", body_html)
        self.assertIn("Định giá gấp trong ngày", body_html)


if __name__ == "__main__":
    unittest.main()
