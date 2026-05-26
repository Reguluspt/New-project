from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, Mock, patch

from src.oauth2_service import _build_mime_message, get_enabled_oauth_provider, send_email_via_oauth2


class OAuth2EmailLogoTests(unittest.IsolatedAsyncioTestCase):
    def test_enabled_provider_prefers_outlook_when_google_is_also_configured(self) -> None:
        with patch("src.oauth2_service.is_oauth_enabled", return_value=True):
            provider = get_enabled_oauth_provider()

        self.assertEqual(provider, "outlook")

    def test_google_mime_message_embeds_logo_for_shared_template_cid(self) -> None:
        message = _build_mime_message(
            "sender@example.com",
            "to@example.com",
            "Subject",
            '<img src="cid:logo_cenvalue" alt="CENVALUE">',
        )

        source = message.as_string()
        self.assertIn("cid:logo_cenvalue", source)
        self.assertIn("Content-ID: <logo_cenvalue>", source)
        self.assertIn('filename="logo.jpg"', source)

    async def test_outlook_payload_embeds_inline_logo_for_shared_template_cid(self) -> None:
        client = Mock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.post = AsyncMock(return_value=Mock(status_code=202, headers={}))

        with (
            patch("src.oauth2_service.get_valid_access_token_async", AsyncMock(return_value="token")),
            patch("src.oauth2_service.httpx.AsyncClient", return_value=client),
        ):
            await send_email_via_oauth2(
                "outlook",
                "sender@example.com",
                "to@example.com",
                "Subject",
                '<img src="cid:logo_cenvalue" alt="CENVALUE">',
            )

        payload = client.post.await_args.kwargs["json"]
        logo = payload["message"]["attachments"][0]
        self.assertEqual(logo["contentId"], "logo_cenvalue")
        self.assertTrue(logo["isInline"])
        self.assertEqual(logo["contentType"], "image/jpeg")


if __name__ == "__main__":
    unittest.main()
