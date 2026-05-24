from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.mail_service import _remove_phone_numbers, _subject_asset_text, load_gmail_smtp_settings, render_mail_html, send_appraisal_email


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
        self.assertIn("010/2026/N04-1051/DN", html)
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
            patch("src.mail_service._send_sync") as send_sync_mock,
        ):
            result = await send_appraisal_email(
                {
                    "contract_number": "N05-0854",
                    "customer_info": "Khách A",
                    "source": "MB AMC ARR - Mr. Long - 0905226968",
                    "asset_description": "Thửa đất số 78d, tờ bản đồ số 13, địa chỉ Xã Hòa An, huyện Krông Păc, tỉnh Đak Lak.",
                }
            )

        self.assertEqual(result.to_email, "admin@example.com")
        self.assertTrue(result.subject.startswith("[010/2026/N05-0854/DN] - MB AMC ARR - Mr. Long - "))
        send_sync_mock.assert_called_once()
        args, _ = send_sync_mock.call_args
        message, recipients, settings = args
        
        self.assertEqual(settings.host, "smtp.gmail.com")
        self.assertEqual(settings.port, 587)
        self.assertEqual(settings.username, "sender@gmail.com")
        self.assertEqual(settings.password, "app-password")
        self.assertEqual(recipients, ["admin@example.com"])
        self.assertEqual(result.cc_emails, [])
        self.assertTrue(message["Message-ID"])
        self.assertIn("@gmail.com>", message["Message-ID"])
        mime_source = message.as_string()
        self.assertIn("cid:logo_cenvalue", mime_source)
        self.assertIn("Content-ID: <logo_cenvalue>", mime_source)
        self.assertIn('filename="logo.jpg"', mime_source)

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
            patch("src.mail_service._send_sync") as send_sync_mock,
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
        send_sync_mock.assert_called_once()
        message, recipients, _ = send_sync_mock.call_args.args
        self.assertEqual(message["Cc"], "manager@example.com, control@example.com")
        self.assertEqual(
            recipients,
            ["admin@example.com", "manager@example.com", "control@example.com"],
        )

    async def test_send_appraisal_email_removes_linebreaks_from_headers(self) -> None:
        env = {
            "SMTP_USERNAME": "sender@gmail.com",
            "SMTP_PASSWORD": "app-password",
            "MAIL_FROM": "Sender Name",
            "ADMIN_EMAIL": "admin@example.com",
            "MANAGEMENT_CC": "manager@example.com\n",
            "CONTROL_BOARD_CC": "",
        }
        with (
            patch.dict("os.environ", env, clear=True),
            patch("src.mail_service._send_sync") as send_sync_mock,
        ):
            result = await send_appraisal_email(
                {
                    "contract_number": "HD-002",
                    "customer_info": "Khach A",
                    "source": "VP Bank\nGia Lai",
                    "asset_description": "Thua dat so 1",
                }
            )

        message, recipients, _ = send_sync_mock.call_args.args
        self.assertNotIn("\n", result.subject)
        self.assertEqual(message["Subject"], result.subject)
        self.assertEqual(message["Cc"], "manager@example.com")
        self.assertEqual(recipients, ["admin@example.com", "manager@example.com"])

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


    def test_subject_asset_text_uses_first_asset_address_only(self) -> None:
        self.assertEqual(
            _subject_asset_text(
                "Thửa đất số 1, tờ bản đồ số 2; tại địa chỉ Phường Hội Phú, tỉnh Gia Lai.\n"
                "Thửa đất số 3, tờ bản đồ số 4; tại địa chỉ Phường Thắng Lợi."
            ),
            "Phường Hội Phú, tỉnh Gia Lai",
        )


if __name__ == "__main__":
    unittest.main()
