from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, Mock
from unittest.mock import patch

from src.mail_renderer import (
    MailData,
    html_preview_file,
    image_preview_file,
    mail_data_from_record,
    format_fee_for_mail,
    render_appraisal_email,
    send_appraisal_email_preview,
)


class MailRendererTests(unittest.IsolatedAsyncioTestCase):
    def test_render_appraisal_email_uses_jinja_template(self) -> None:
        data = MailData(
            recipient_name="Phuong",
            contract_id="010/2026/N04-1045/DN",
            asset_type="BDS dac thu khac",
            asset_description="Gia tri quyen su dung dat tai thua dat so 51",
            preliminary_status="Chua so bo",
            purpose="Lam co so tham khao de the chap vay von",
            source="NHCS Chu Pah",
            customer_info="Ong Quan Van Dung",
            fee_valuation="2.200.000 Da bao gom VAT",
            deposit="0",
            sales_staff="Truongpnt",
            pro_staff="Thampt2",
            notes="Lien he khach hang lay phap ly",
        )

        html = render_appraisal_email(data)

        self.assertIn("THÔNG TIN HỒ SƠ", html)
        self.assertIn("background-color:#ffc000", html)
        self.assertIn("background-color:#ffff00", html)
        self.assertIn("color:#ff0000", html)
        self.assertIn("010/2026/N04-1045/DN", html)
        self.assertIn("BDS dac thu khac", html)
        self.assertIn("2.200.000 Da bao gom VAT", html)

    def test_render_appraisal_email_can_use_custom_template_dir(self) -> None:
        with TemporaryDirectory() as tmpdir:
            template_dir = Path(tmpdir)
            (template_dir / "mail_template.html").write_text("Xin chao {{ recipient_name }}", encoding="utf-8")

            html = render_appraisal_email(MailData(recipient_name="Anh A"), template_dir=template_dir)

        self.assertEqual(html, "Xin chao Anh A")

    def test_html_preview_file_returns_named_input_file(self) -> None:
        preview = html_preview_file("<html></html>", filename="preview.html")

        self.assertEqual(preview.filename, "preview.html")

    def test_image_preview_file_returns_named_input_file(self) -> None:
        preview = image_preview_file(b"png", filename="preview.png")

        self.assertEqual(preview.filename, "preview.png")

    async def test_send_preview_uses_telegram_photo_when_png_render_succeeds(self) -> None:
        context = Mock()
        context.bot.send_photo = AsyncMock()
        context.bot.send_document = AsyncMock()

        with patch("src.mail_renderer.render_html_preview_png", AsyncMock(return_value=b"png")):
            await send_appraisal_email_preview(chat_id=123, html="<html></html>", context=context)

        context.bot.send_photo.assert_awaited_once()
        context.bot.send_document.assert_not_awaited()
        kwargs = context.bot.send_photo.await_args.kwargs
        self.assertEqual(kwargs["chat_id"], 123)
        self.assertEqual(kwargs["caption"], "Bản xem trước email thẩm định")

    async def test_send_preview_falls_back_to_html_document_when_png_render_fails(self) -> None:
        context = Mock()
        context.bot.send_photo = AsyncMock()
        context.bot.send_document = AsyncMock()

        with patch("src.mail_renderer.render_html_preview_png", AsyncMock(side_effect=RuntimeError("no browser"))):
            await send_appraisal_email_preview(chat_id=123, html="<html></html>", context=context)

        context.bot.send_photo.assert_not_awaited()
        context.bot.send_document.assert_awaited_once()
        kwargs = context.bot.send_document.await_args.kwargs
        self.assertEqual(kwargs["chat_id"], 123)
        self.assertIn("chưa tạo được ảnh preview", kwargs["caption"])

    def test_mail_data_from_record_maps_available_fields(self) -> None:
        data = mail_data_from_record(
            {
                "id": "7",
                "contract_number": "010/2026/N04-1051/DN",
                "chu_so_huu": "Nguyen Van A",
                "dia_chi": "Thua dat tai Dak Lak",
                "valuation_fee_number": "2200000",
                "business_staff": "",
            }
        )

        self.assertEqual(data.contract_id, "N04-1051")
        self.assertEqual(data.recipient_name, "Nguyen Van A")
        self.assertEqual(data.asset_description, "Thua dat tai Dak Lak")
        self.assertEqual(data.fee_valuation, "2.200.000")
        self.assertEqual(data.sales_staff, "Truongpnt")

    def test_format_fee_for_mail_adds_thousand_separators_and_preserves_suffix(self) -> None:
        self.assertEqual(format_fee_for_mail("2200000"), "2.200.000")
        self.assertEqual(format_fee_for_mail("2200000 Đã bao gồm VAT"), "2.200.000 Đã bao gồm VAT")
        self.assertEqual(format_fee_for_mail("2.200.000 Đã bao gồm VAT"), "2.200.000 Đã bao gồm VAT")


if __name__ == "__main__":
    unittest.main()
