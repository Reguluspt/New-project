from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from src.mail_service import _remove_phone_numbers, load_gmail_smtp_settings, render_mail_html, send_appraisal_email


class MailServiceTests(unittest.IsolatedAsyncioTestCase):
    def test_render_mail_html_uses_professional_template(self) -> None:
        html = render_mail_html(
            {
                "contract_number": "010/2026/N04-1051/DN",
                "asset_type": "BĐS đặc thù khác",
                "customer_info": "Ông Phan Đình Phúc",
                "valuation_fee_number": "2.200.000 Đã bao gồm VAT",
            }
        )

        self.assertIn("THÔNG TIN HỒ SƠ", html)
        self.assertIn("N04-1051", html)
        self.assertNotIn("010/2026/N04-1051/DN", html)
        self.assertIn("background-color:#ffc000", html)
        self.assertIn("Truongpnt", html)
        self.assertIn("Gửi Phương,", html)
        self.assertNotIn("Gửi Ông Phan", html)

    async def test_send_appraisal_email_uses_gmail_smtp_settings(self) -> None:
        env = {
            "SMTP_USERNAME": "sender@gmail.com",
            "SMTP_PASSWORD": "app-password",
            "MAIL_FROM": "Sender Name",
            "ADMIN_EMAIL": "admin@example.com",
            "MANAGEMENT_CC": "",
            "CONTROL_BOARD_CC": "",
        }
        with (
            patch.dict("os.environ", env, clear=True),
            patch("src.mail_service.aiosmtplib.send", AsyncMock()) as smtp_send,
        ):
            result = await send_appraisal_email(
                {
                    "contract_number": "HD-001",
                    "customer_info": "Khách A",
                    "source": "MB AMC ARR - Mr. Long - 0905226968",
                    "asset_description": "Thửa đất số 78d, tờ bản đồ số 13, địa chỉ Xã Hòa An, huyện Krông Păc, tỉnh Đak Lak.",
                }
            )

        self.assertEqual(result.to_email, "admin@example.com")
        self.assertEqual(
            result.subject,
            "[XIN SỐ] - MB AMC ARR - Mr. Long - Thửa đất số 78d, tờ bản đồ số 13, địa chỉ Xã Hòa An, huyện Krông Păc, tỉnh Đak Lak.",
        )
        smtp_send.assert_awaited_once()
        kwargs = smtp_send.await_args.kwargs
        self.assertEqual(kwargs["hostname"], "smtp.gmail.com")
        self.assertEqual(kwargs["port"], 587)
        self.assertEqual(kwargs["username"], "sender@gmail.com")
        self.assertEqual(kwargs["password"], "app-password")
        self.assertTrue(kwargs["start_tls"])
        self.assertEqual(kwargs["recipients"], ["admin@example.com"])
        self.assertEqual(result.cc_emails, [])
        message = smtp_send.await_args.args[0]
        self.assertTrue(message["Message-ID"])
        self.assertIn("@gmail.com>", message["Message-ID"])

    async def test_send_appraisal_email_includes_monitor_cc_header_and_recipients(self) -> None:
        env = {
            "SMTP_USERNAME": "sender@gmail.com",
            "SMTP_PASSWORD": "app-password",
            "MAIL_FROM": "Sender Name",
            "ADMIN_EMAIL": "admin@example.com",
            "MANAGEMENT_CC": "manager@example.com",
            "CONTROL_BOARD_CC": "control@example.com, manager@example.com",
        }
        with (
            patch.dict("os.environ", env, clear=True),
            patch("src.mail_service.aiosmtplib.send", AsyncMock()) as smtp_send,
        ):
            result = await send_appraisal_email(
                {
                    "contract_number": "HD-001",
                    "customer_info": "Khách A",
                    "source": "VP Bank",
                    "asset_description": "Thửa đất số 1",
                }
        )

        self.assertEqual(result.to_email, "admin@example.com")
        self.assertEqual(result.cc_emails, ["manager@example.com", "control@example.com"])
        smtp_send.assert_awaited_once()
        message = smtp_send.await_args.args[0]
        self.assertEqual(message["Cc"], "manager@example.com, control@example.com")
        self.assertEqual(
            smtp_send.await_args.kwargs["recipients"],
            ["admin@example.com", "manager@example.com", "control@example.com"],
        )

    def test_load_settings_builds_monitor_cc_from_management_and_control(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "MAIL_USERNAME": "sender@gmail.com",
                "MAIL_PASSWORD": "app-password",
                "ADMIN_EMAIL": "admin@example.com",
                "PROFESSIONAL_DEPT_EMAIL": "pro@example.com",
                "MANAGEMENT_CC": "manager@example.com",
                "CONTROL_BOARD_CC": "control@example.com, manager@example.com",
            },
            clear=True,
        ):
            settings = load_gmail_smtp_settings()

        self.assertEqual(settings.admin_email, "admin@example.com")
        self.assertEqual(settings.professional_dept_email, "pro@example.com")
        self.assertEqual(settings.monitor_cc_list, ["manager@example.com", "control@example.com"])

    def test_remove_phone_numbers_from_subject_source(self) -> None:
        self.assertEqual(_remove_phone_numbers("MB AMC ARR - Mr. Long - 0905226968"), "MB AMC ARR - Mr. Long")
        self.assertEqual(_remove_phone_numbers("VP Bank - Gia Lai - Chị Ngọc - 0972638579"), "VP Bank - Gia Lai - Chị Ngọc")


if __name__ == "__main__":
    unittest.main()
