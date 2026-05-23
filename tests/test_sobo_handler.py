from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from telegram.ext import ConversationHandler

from src.models import ExtractedValue, LandCertificateExtraction
from src.sobo_handler import (
    SOBO_DOC,
    SOBO_EMAIL_OPTIONS,
    SOBO_LOC,
    _process_sobo_extracted_file,
    build_sobo_email_content,
    build_department_email_keyboard,
    sobo_require_email_selection,
    sobo_select_email,
)


def _value(value: str) -> ExtractedValue:
    return ExtractedValue(value=value, confidence=0.95, evidence=value)


class SoboHandlerTests(unittest.IsolatedAsyncioTestCase):
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


if __name__ == "__main__":
    unittest.main()
