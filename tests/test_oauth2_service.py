from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, Mock, patch

from src.oauth2_service import (
    OUTLOOK_GRAPH_SCOPES,
    _build_mime_message,
    _graph_error_detail,
    exchange_code_for_tokens,
    get_enabled_oauth_provider,
    send_email_via_oauth2,
)


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

    def test_graph_error_detail_exposes_status_error_and_request_id(self) -> None:
        response = Mock(
            status_code=403,
            headers={"request-id": "req-123"},
            json=Mock(return_value={"error": {"code": "ErrorAccessDenied", "message": "Access is denied."}}),
            text="",
        )

        detail = _graph_error_detail(response)

        self.assertEqual(detail, "HTTP 403; ErrorAccessDenied - Access is denied.; request-id=req-123")

    def test_outlook_token_exchange_requests_graph_scopes(self) -> None:
        response = Mock(status_code=200)
        response.json.return_value = {
            "access_token": "access",
            "refresh_token": "refresh",
            "expires_in": 3600,
        }
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock(return_value=False)
        client.post.return_value = response
        config = {
            "outlook": {
                "client_id": "client",
                "client_secret": "secret",
                "tenant": "tenant-id",
            }
        }

        with (
            patch("src.oauth2_service.load_oauth_config", return_value=config),
            patch("src.oauth2_service.save_oauth_config") as save_config,
            patch("src.oauth2_service.httpx.Client", return_value=client),
        ):
            exchange_code_for_tokens("outlook", "auth-code", "https://example.test/")

        token_payload = client.post.call_args.kwargs["data"]
        self.assertEqual(token_payload["scope"], OUTLOOK_GRAPH_SCOPES)
        save_config.assert_called_once()

    async def test_outlook_send_error_includes_http_status_when_body_is_blank(self) -> None:
        client = Mock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        response = Mock(status_code=403, headers={}, text="")
        response.json.side_effect = ValueError("no json")
        client.post = AsyncMock(return_value=response)

        with (
            patch("src.oauth2_service.get_valid_access_token_async", AsyncMock(return_value="token")),
            patch("src.oauth2_service.httpx.AsyncClient", return_value=client),
        ):
            with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
                await send_email_via_oauth2(
                    "outlook",
                    "sender@example.com",
                    "to@example.com",
                    "Subject",
                    "<p>Body</p>",
                )


if __name__ == "__main__":
    unittest.main()
