from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from src.email_reply_service import DEFAULT_PHATHANH_RECIPIENT, format_phathanh_recipient_html
from views.case_documents import (
    _case_with_organization_contact_address,
    _manual_delivery_contact_error,
    _mark_phathanh_case_completed,
)


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

    def test_successful_phathanh_marks_case_completed(self) -> None:
        with patch("views.case_documents.update_case") as update_case:
            updated = _mark_phathanh_case_completed(Path("cases.db"), 17)

        self.assertTrue(updated)
        update_case.assert_called_once_with(
            Path("cases.db"),
            17,
            {"case_status": "Hoàn thành", "cancel_reason": ""},
        )

    def test_phathanh_without_cases_database_skips_completion_update(self) -> None:
        with patch("views.case_documents.update_case") as update_case:
            updated = _mark_phathanh_case_completed(None, 17)

        self.assertFalse(updated)
        update_case.assert_not_called()

    def test_organization_phathanh_uses_organization_address_from_contacts(self) -> None:
        export_case = {
            "customer_type": "organization",
            "customer_info": "CONG TY ABC",
            "customer_address": "Dia chi chu tai san",
        }

        with patch(
            "views.case_documents.find_organization_by_query",
            return_value=[{"address": "Dia chi cong ty"}],
        ) as find_org:
            enriched_case = _case_with_organization_contact_address(export_case, Path("cases.db"))

        find_org.assert_called_once_with(Path("cases.db"), "CONG TY ABC")
        self.assertEqual(enriched_case["customer_address"], "Dia chi cong ty")
        self.assertEqual(export_case["customer_address"], "Dia chi chu tai san")


if __name__ == "__main__":
    unittest.main()
