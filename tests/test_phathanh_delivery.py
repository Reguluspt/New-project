from __future__ import annotations

import unittest

from src.email_reply_service import DEFAULT_PHATHANH_RECIPIENT, format_phathanh_recipient_html
from views.case_documents import _manual_delivery_contact_error


class PhathanhDeliveryTests(unittest.TestCase):
    def test_default_delivery_recipient_is_rendered_when_no_selection_is_supplied(self) -> None:
        recipient_html = format_phathanh_recipient_html(None)

        self.assertIn("VP TẠI GIA LAI", recipient_html)
        self.assertIn("<strong>Địa chỉ:</strong>", recipient_html)
        self.assertIn("<strong>Điện thoại</strong>", recipient_html)
        self.assertIn("90/60/3 Trường Chinh", DEFAULT_PHATHANH_RECIPIENT)

    def test_manual_recipient_content_is_escaped_before_embedding_in_mail(self) -> None:
        recipient_html = format_phathanh_recipient_html(
            'Công ty <script>alert("x")</script>\nĐịa chỉ: 12 Test\nĐiện thoại: 0123'
        )

        self.assertNotIn("<script>", recipient_html)
        self.assertIn("&lt;script&gt;", recipient_html)
        self.assertIn("<strong>Địa chỉ:</strong>", recipient_html)
        self.assertIn("<strong>Điện thoại:</strong>", recipient_html)

    def test_manual_recipient_may_be_used_without_saving_to_contacts(self) -> None:
        error = _manual_delivery_contact_error(
            short_name="",
            details="Người nhận phát sinh\nĐịa chỉ: 1 Test",
            save_to_contacts=False,
            contacts=[],
        )

        self.assertIsNone(error)

    def test_saving_manual_recipient_requires_unique_short_name(self) -> None:
        contacts = [{"short_name": "Khach A", "full_details": "Dia chi"}]

        missing_name_error = _manual_delivery_contact_error(
            short_name="",
            details="Người nhận",
            save_to_contacts=True,
            contacts=contacts,
        )
        duplicate_error = _manual_delivery_contact_error(
            short_name=" khach a ",
            details="Người nhận",
            save_to_contacts=True,
            contacts=contacts,
        )

        self.assertIn("tên gợi nhớ", missing_name_error.lower())
        self.assertIn("đã có trong danh bạ", duplicate_error.lower())


if __name__ == "__main__":
    unittest.main()
