from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from telegram.ext import ConversationHandler

from src.models import ExtractedValue, LandCertificateExtraction, LandCertificateMultiExtraction
from src.sobo_handler import (
    SOBO_ASSET_SELECT,
    SOBO_DOC,
    SOBO_EMAIL_OPTIONS,
    SOBO_LOC,
    SOBO_MACHINERY_DOC,
    SOBO_MACHINERY_EMAIL,
    SOBO_MACHINERY_NAME,
    SOBO_CONFIRM,
    _process_sobo_extracted_file,
    build_machinery_email_content,
    build_sobo_email_content,
    build_department_email_keyboard,
    cmd_sobo,
    sobo_receive_machinery_doc,
    sobo_receive_machinery_name,
    sobo_require_email_selection,
    sobo_require_machinery_file,
    sobo_select_asset_type,
    sobo_select_email,
    SOBO_RE_SUB_TYPE,
    SOBO_DOC_MULTI,
    SOBO_DOC_MULTI_CHOICE,
    sobo_select_re_sub_type,
    _process_sobo_extracted_file_multi,
    sobo_multi_doc_choice,
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

    def test_email_content_uses_approved_template_and_escapes_values(self) -> None:
        body, body_html = build_sobo_email_content(
            {
                "source": "VCB <Gia Lai>",
                "so_thua": "72",
                "so_to": "13",
                "dia_chi": "Khu phố 2 & phường Xuân Hòa",
                "link": "https://maps.google.com/?q=1&z=2",
            }
        )

        self.assertIn("Kính gửi Anh/Chị", body)
        self.assertIn("Quyền sử dụng đất và CTXD (nếu có hoàn công trên sổ)", body)
        self.assertIn("Em gửi thông tin tài sản cần hỗ trợ tham khảo giá trị sơ bộ như sau", body_html)
        self.assertIn("Kính nhờ Anh/Chị hỗ trợ sơ bộ tài sản nêu trên", body_html)
        self.assertIn("cid:cenvalue_logo", body_html)
        self.assertIn("VCB &lt;Gia Lai&gt;", body_html)
        self.assertIn("Khu phố 2 &amp; phường Xuân Hòa", body_html)
        self.assertNotIn("VCB <Gia Lai>", body_html)

    def test_email_content_does_not_create_unsafe_location_link(self) -> None:
        _, body_html = build_sobo_email_content({"link": "javascript:alert(1)"})

        self.assertIn('href="#"', body_html)
        self.assertNotIn('href="javascript:', body_html)

    def test_machinery_email_content_only_uses_equipment_name_field(self) -> None:
        body, body_html = build_machinery_email_content({"equipment_name": "Máy cắt <CNC>"})

        self.assertIn("Máy móc thiết bị", body)
        self.assertIn("Tên thiết bị: Máy cắt <CNC>", body)
        self.assertIn("Máy cắt &lt;CNC&gt;", body_html)
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
        message = update.callback_query.edit_message_text.await_args.args[0]
        self.assertIn("không được quét hoặc phân tích", message)

    async def test_machinery_uploaded_file_is_kept_as_attachment_without_scanning(self) -> None:
        update = Mock()
        update.message.document.file_id = "file-1"
        update.message.document.file_name = "may_cat.pdf"
        update.message.photo = None
        update.message.reply_text = AsyncMock()
        telegram_file = Mock()
        telegram_file.download_to_drive = AsyncMock()
        context = Mock()
        context.user_data = {"sobo": {"asset_type": "machinery"}}
        context.bot.get_file = AsyncMock(return_value=telegram_file)

        with patch("src.sobo_handler.extract_land_certificate_with_gemini") as extract:
            state = await sobo_receive_machinery_doc(update, context)

        self.assertEqual(state, SOBO_MACHINERY_NAME)
        self.assertEqual(context.user_data["sobo"]["attachment_name"], "may_cat.pdf")
        telegram_file.download_to_drive.assert_awaited_once()
        extract.assert_not_called()

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

    async def test_machinery_email_selection_opens_send_preview_without_location_step(self) -> None:
        update = Mock()
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.data = "sobo_email_0"
        context = Mock()
        context.user_data = {
            "sobo": {
                "asset_type": "machinery",
                "equipment_name": "Máy cắt CNC",
                "attachment_name": "may_cat.pdf",
            }
        }

        state = await sobo_select_email(update, context)

        self.assertEqual(state, SOBO_CONFIRM)
        self.assertEqual(
            context.user_data["sobo"]["subject"],
            "[SƠ BỘ] - Máy móc thiết bị - Máy cắt CNC",
        )
        preview = update.callback_query.edit_message_text.await_args.args[0]
        self.assertIn("may_cat.pdf", preview)
        self.assertNotIn("Link định vị", preview)

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
        self.assertEqual(state_done, SOBO_DOC)
        self.assertEqual(context.user_data["sobo"]["suggested_email"], "Sobo.taynguyen@gmail.com")

    def test_build_email_content_multi(self) -> None:
        sobo = {
            "source": "KH Hợp Khối",
            "asset_sub_type": "multi",
            "assets_list": [
                {"so_thua": "234", "so_to": "54", "dia_chi": "Pleiku, Gia Lai"},
                {"so_thua": "235", "so_to": "54", "dia_chi": "Pleiku, Gia Lai"}
            ],
            "link": "https://maps.google.com/?q=1&z=2"
        }
        body, body_html = build_sobo_email_content(sobo)

        self.assertIn("DANH SÁCH CHI TIẾT TÀI SẢN:", body)
        self.assertIn("Tài sản 1:", body)
        self.assertIn("Số thửa đất: 234", body)
        self.assertIn("Tài sản 2:", body)
        self.assertIn("Số thửa đất: 235", body)

        self.assertIn("Thông tin chi tiết thửa đất", body_html)
        self.assertIn("Tài sản 1", body_html)
        self.assertIn("Tài sản 2", body_html)
        self.assertIn("Pleiku, Gia Lai", body_html)


if __name__ == "__main__":
    unittest.main()
