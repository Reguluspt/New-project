from __future__ import annotations

import unittest
import base64
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx

from src import oauth2_service


class GmailRateLimitTests(unittest.IsolatedAsyncioTestCase):
    def test_retry_after_body_sets_cooldown(self) -> None:
        response = httpx.Response(
            429,
            text="User-rate limit exceeded. Retry after 2099-01-01T09:42:39.731Z",
            request=httpx.Request("GET", "https://gmail.googleapis.com/gmail/v1/users/me/messages"),
        )

        with patch.object(oauth2_service, "GMAIL_COOLDOWN_PATH", Path(self._testMethodName)):
            try:
                with self.assertRaises(oauth2_service.GmailRateLimitError) as caught:
                    oauth2_service.handle_gmail_rate_limit_response(response)
                self.assertEqual(caught.exception.retry_after, "2099-01-01T09:42:39.731000Z")
                self.assertEqual(oauth2_service.get_gmail_cooldown_until(), "2099-01-01T09:42:39.731000Z")
            finally:
                Path(self._testMethodName).unlink(missing_ok=True)

    async def test_fetch_gmail_skips_http_calls_during_cooldown(self) -> None:
        cooldown_path = Path(f"{self._testMethodName}.json")
        retry_after = datetime(2099, 1, 1, tzinfo=timezone.utc)

        with (
            patch.object(oauth2_service, "GMAIL_COOLDOWN_PATH", cooldown_path),
            patch("src.oauth2_service.get_valid_access_token_async", AsyncMock(return_value="token")),
            patch("src.oauth2_service.httpx.AsyncClient") as async_client,
        ):
            try:
                oauth2_service.set_gmail_cooldown_until(retry_after)
                with self.assertRaises(oauth2_service.GmailRateLimitError):
                    await oauth2_service.fetch_emails_via_oauth2("google", query_contract="SƠ BỘ")
                async_client.assert_not_called()
            finally:
                cooldown_path.unlink(missing_ok=True)

    async def test_fetch_gmail_gets_only_unprocessed_message_ids(self) -> None:
        client = Mock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        raw_email = base64.urlsafe_b64encode(
            b"Subject: Re: [SO BO #1]\r\nFrom: a@example.com\r\n\r\nBody"
        ).decode("ascii")
        client.get = AsyncMock(
            side_effect=[
                httpx.Response(
                    200,
                    json={"messages": [{"id": "old-id"}, {"id": "new-id", "threadId": "thread-1"}]},
                    request=httpx.Request("GET", "https://gmail.googleapis.com/gmail/v1/users/me/messages"),
                ),
                httpx.Response(
                    200,
                    json={"raw": raw_email},
                    request=httpx.Request("GET", "https://gmail.googleapis.com/gmail/v1/users/me/messages/new-id"),
                ),
            ]
        )

        with (
            patch("src.oauth2_service.get_valid_access_token_async", AsyncMock(return_value="token")),
            patch("src.oauth2_service.raise_if_gmail_cooling_down"),
            patch("src.oauth2_service.httpx.AsyncClient", return_value=client),
        ):
            emails = await oauth2_service.fetch_emails_via_oauth2(
                "google",
                query_contract="SƠ BỘ",
                limit=10,
                unread_only=False,
                skip_uids={"old-id"},
            )

        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]["uid"], "new-id")
        self.assertEqual(client.get.await_count, 2)
        detail_url = client.get.await_args_list[1].args[0]
        self.assertTrue(detail_url.endswith("/new-id"))
