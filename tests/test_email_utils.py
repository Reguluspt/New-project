from __future__ import annotations

import smtplib
import unittest
from unittest.mock import AsyncMock, Mock, patch

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

    async def test_html_email_embeds_cenvalue_logo_image(self) -> None:
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
            result = await send_sobo_email_with_result(
                "to@example.com",
                "Subject",
                "Body",
                html_body='<img src="cid:cenvalue_logo" alt="CENVALUE">',
            )

        message = smtp.send_message.call_args.args[0]
        mime_source = message.as_string()
        self.assertTrue(result.success)
        self.assertIn("cid:cenvalue_logo", mime_source)
        self.assertIn("Content-ID: <cenvalue_logo>", mime_source)
        self.assertIn('filename="logo.jpg"', mime_source)

    async def test_outlook_html_email_embeds_inline_cenvalue_logo_image(self) -> None:
        client = Mock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.post = AsyncMock(return_value=Mock(status_code=202))

        with (
            patch.dict("os.environ", {"MAIL_USERNAME": "sender@example.com"}, clear=True),
            patch("src.email_utils.load_dotenv"),
            patch("src.oauth2_service.is_oauth_enabled", side_effect=lambda provider: provider == "outlook"),
            patch("src.oauth2_service.get_valid_access_token_async", AsyncMock(return_value="token")),
            patch("httpx.AsyncClient", return_value=client),
        ):
            result = await send_sobo_email_with_result(
                "to@example.com",
                "Subject",
                "Body",
                html_body='<img src="cid:cenvalue_logo" alt="CENVALUE">',
            )

        payload = client.post.await_args.kwargs["json"]
        logo = payload["message"]["attachments"][0]
        self.assertTrue(result.success)
        self.assertEqual(logo["contentId"], "cenvalue_logo")
        self.assertTrue(logo["isInline"])
        self.assertEqual(logo["name"], "logo.jpg")


if __name__ == "__main__":
    unittest.main()
