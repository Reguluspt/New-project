from __future__ import annotations

import base64
import json
import unittest
from email.message import EmailMessage
from unittest.mock import AsyncMock, Mock, patch

from src.oauth2_service import (
    OUTLOOK_GRAPH_SCOPES,
    OUTLOOK_SMTP_SCOPES,
    _access_token_claim_summary,
    _build_mime_message,
    _graph_error_detail,
    _send_outlook_smtp_sync,
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

    async def test_outlook_payload_uses_configured_sender_alias(self) -> None:
        client = Mock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.post = AsyncMock(return_value=Mock(status_code=202, headers={}))

        with (
            patch("src.oauth2_service.get_valid_access_token_async", AsyncMock(return_value="token")),
            patch("src.oauth2_service.get_outlook_sender_email", return_value="truongpnt2@outlook.com.vn"),
            patch("src.oauth2_service.is_outlook_smtp_enabled", return_value=False),
            patch("src.oauth2_service.httpx.AsyncClient", return_value=client),
        ):
            await send_email_via_oauth2(
                "outlook",
                "legacy@gmail.com",
                "to@example.com",
                "Subject",
                "<p>Body</p>",
            )

        payload = client.post.await_args.kwargs["json"]
        self.assertEqual(
            payload["message"]["from"],
            {"emailAddress": {"address": "truongpnt2@outlook.com.vn"}},
        )

    async def test_outlook_uses_smtp_oauth_when_alias_transport_is_connected(self) -> None:
        with (
            patch("src.oauth2_service.is_outlook_smtp_enabled", return_value=True),
            patch("src.oauth2_service.get_outlook_sender_email", return_value="truongpnt2@outlook.com.vn"),
            patch("src.oauth2_service.send_outlook_message_via_smtp_oauth2", AsyncMock(return_value="smtp-id")) as send,
        ):
            result = await send_email_via_oauth2(
                "outlook",
                "legacy@gmail.com",
                "to@example.com",
                "Subject",
                "<p>Body</p>",
            )

        message = send.await_args.args[0]
        self.assertEqual(result, "smtp-id")
        self.assertEqual(message["From"], "truongpnt2@outlook.com.vn")

    def test_outlook_smtp_submission_authenticates_using_alias_and_oauth_token(self) -> None:
        smtp = Mock()
        smtp.__enter__ = Mock(return_value=smtp)
        smtp.__exit__ = Mock(return_value=False)
        smtp.docmd.return_value = (235, b"accepted")
        message = EmailMessage()
        message["From"] = "truongpnt2@outlook.com.vn"
        message["To"] = "to@example.com"
        message.set_content("Body")

        with patch("src.oauth2_service.smtplib.SMTP", return_value=smtp):
            _send_outlook_smtp_sync(message, "truongpnt2@outlook.com.vn", "oauth-token")

        smtp.starttls.assert_called_once()
        self.assertEqual(smtp.docmd.call_args.args[0], "AUTH")
        self.assertIn("XOAUTH2 ", smtp.docmd.call_args.args[1])
        smtp.send_message.assert_called_once_with(
            message,
            from_addr="truongpnt2@outlook.com.vn",
            to_addrs=["to@example.com"],
        )

    def test_graph_error_detail_exposes_status_error_and_request_id(self) -> None:
        response = Mock(
            status_code=403,
            headers={"request-id": "req-123"},
            json=Mock(return_value={"error": {"code": "ErrorAccessDenied", "message": "Access is denied."}}),
            text="",
        )

        detail = _graph_error_detail(response)

        self.assertEqual(detail, "HTTP 403; ErrorAccessDenied - Access is denied.; request-id=req-123")

    def test_access_token_claim_summary_does_not_expose_identity_claims(self) -> None:
        payload = {
            "aud": "https://graph.microsoft.com",
            "scp": "Mail.Send Mail.ReadWrite",
            "tid": "tenant-id",
            "preferred_username": "person@example.com",
        }
        encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
        access_token = f"header.{encoded}.signature"

        detail = _access_token_claim_summary(access_token)

        self.assertEqual(detail, "aud=https://graph.microsoft.com; scp=Mail.Send Mail.ReadWrite; tid=tenant-id")
        self.assertNotIn("person@example.com", detail)
        self.assertNotIn(access_token, detail)

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

    def test_outlook_smtp_token_exchange_requests_smtp_scope(self) -> None:
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
            "outlook_smtp": {
                "client_id": "client",
                "client_secret": "secret",
                "tenant": "common",
            }
        }

        with (
            patch("src.oauth2_service.load_oauth_config", return_value=config),
            patch("src.oauth2_service.save_oauth_config"),
            patch("src.oauth2_service.httpx.Client", return_value=client),
        ):
            exchange_code_for_tokens("outlook_smtp", "auth-code", "https://example.test/")

        self.assertEqual(client.post.call_args.kwargs["data"]["scope"], OUTLOOK_SMTP_SCOPES)

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

    async def test_outlook_401_error_includes_safe_token_claims(self) -> None:
        payload = {
            "aud": "https://graph.microsoft.com",
            "scp": "Mail.Send",
            "tid": "tenant-id",
            "preferred_username": "person@example.com",
        }
        encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
        access_token = f"header.{encoded}.signature"
        client = Mock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        response = Mock(status_code=401, headers={"request-id": "req-401"}, text="")
        response.json.side_effect = ValueError("no json")
        client.post = AsyncMock(return_value=response)

        with (
            patch("src.oauth2_service.get_valid_access_token_async", AsyncMock(return_value=access_token)),
            patch("src.oauth2_service.httpx.AsyncClient", return_value=client),
        ):
            with self.assertRaises(RuntimeError) as raised:
                await send_email_via_oauth2(
                    "outlook",
                    "sender@example.com",
                    "to@example.com",
                    "Subject",
                    "<p>Body</p>",
                )

        message = str(raised.exception)
        self.assertIn("HTTP 401", message)
        self.assertIn("aud=https://graph.microsoft.com", message)
        self.assertIn("scp=Mail.Send", message)
        self.assertNotIn("person@example.com", message)
        self.assertNotIn(access_token, message)


if __name__ == "__main__":
    unittest.main()
