from __future__ import annotations

import smtplib
import unittest
from unittest.mock import Mock, patch

from src.email_utils import send_sobo_email, send_sobo_email_with_result


class SoboEmailUtilsTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_sobo_email_returns_missing_config_message(self) -> None:
        with patch.dict("os.environ", {}, clear=True), patch("src.email_utils.load_dotenv"):
            result = await send_sobo_email_with_result("to@example.com", "Subject", "Body")

        self.assertFalse(result.success)
        self.assertIn("MAIL_USERNAME", result.user_message)

    async def test_send_sobo_email_reports_smtp_authentication_error(self) -> None:
        smtp = Mock()
        smtp.__enter__ = Mock(return_value=smtp)
        smtp.__exit__ = Mock(return_value=False)
        smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"BadCredentials")

        env = {
            "MAIL_SERVER": "smtp.gmail.com",
            "MAIL_PORT": "587",
            "MAIL_USERNAME": "sender@gmail.com",
            "MAIL_PASSWORD": "app password",
            "MAIL_FROM": "Sender Name",
        }
        with (
            patch.dict("os.environ", env, clear=True),
            patch("src.email_utils.load_dotenv"),
            patch("src.email_utils.smtplib.SMTP", return_value=smtp),
        ):
            result = await send_sobo_email_with_result("to@example.com", "Subject", "Body")

        self.assertFalse(result.success)
        self.assertIn("Gmail tu choi dang nhap SMTP", result.user_message)
        smtp.login.assert_called_once_with("sender@gmail.com", "apppassword")

    async def test_send_sobo_email_legacy_wrapper_returns_bool(self) -> None:
        smtp = Mock()
        smtp.__enter__ = Mock(return_value=smtp)
        smtp.__exit__ = Mock(return_value=False)

        env = {
            "MAIL_SERVER": "smtp.gmail.com",
            "MAIL_PORT": "587",
            "MAIL_USERNAME": "sender@gmail.com",
            "MAIL_PASSWORD": "app password",
        }
        with (
            patch.dict("os.environ", env, clear=True),
            patch("src.email_utils.load_dotenv"),
            patch("src.email_utils.smtplib.SMTP", return_value=smtp),
        ):
            result = await send_sobo_email("to@example.com", "Subject", "Body")

        self.assertTrue(result)
        smtp.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
