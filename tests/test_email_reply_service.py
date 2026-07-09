from __future__ import annotations

import asyncio
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

from src.email_reply_service import (
    gemini_keys_with_backups,
    send_phathanh_email_for_case,
    send_phathanh_email_via_browser_use,
    send_phathanh_email_via_playwright_raw,
)


class EmailReplyServiceTests(unittest.TestCase):
    def test_browser_use_gemini_keys_include_unique_backup_keys(self) -> None:
        keys = gemini_keys_with_backups(
            primary_key="primary-key",
            backup_keys="backup-one, primary-key, backup-two",
        )

        self.assertEqual(keys, ["primary-key", "backup-one", "backup-two"])

    def test_browser_use_agent_receives_backup_key_as_fallback_llm(self) -> None:
        captured = {}

        class FakeChatGoogle:
            def __init__(self, *, model, api_key):
                self.model = model
                self.api_key = api_key

        class FakeBrowser:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            async def stop(self):
                captured["browser_stopped"] = True

        class FakeAgent:
            def __init__(self, **kwargs):
                captured["agent_kwargs"] = kwargs

            async def run(self):
                captured["agent_ran"] = True
                return types.SimpleNamespace(is_successful=lambda: True)

        class FakeTools:
            def action(self, _description):
                def decorator(func):
                    return func

                return decorator

        class FakeActionResult:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        fake_browser_use = types.SimpleNamespace(
            Agent=FakeAgent,
            Browser=FakeBrowser,
            ChatGoogle=FakeChatGoogle,
            Tools=FakeTools,
        )
        fake_browser_use_views = types.SimpleNamespace(ActionResult=FakeActionResult)

        env = {
            "GEMINI_API_KEY": "primary-key",
            "GEMINI_BACKUP_KEYS": "backup-key",
            "GEMINI_MODEL": "gemini-test",
            "MAIL_USERNAME": "webmail-user",
            "MAIL_PASSWORD": "webmail-password",
            "WEBMAIL_URL": "https://owa.example.test/",
            "PLAYWRIGHT_HEADLESS": "true",
        }
        with (
            patch.dict(
                sys.modules,
                {"browser_use": fake_browser_use, "browser_use.agent.views": fake_browser_use_views},
            ),
            patch.dict("os.environ", env, clear=False),
        ):
            result = asyncio.run(
                send_phathanh_email_via_browser_use(
                    {"contract_number": "010/2026/N06-0946/DN", "from": "sender@example.test"},
                    "<p>body</p>",
                )
            )

        agent_kwargs = captured["agent_kwargs"]
        self.assertEqual(agent_kwargs["llm"].api_key, "primary-key")
        self.assertEqual(agent_kwargs["llm"].model, "gemini-test")
        self.assertEqual(agent_kwargs["fallback_llm"].api_key, "backup-key")
        self.assertEqual(agent_kwargs["fallback_llm"].model, "gemini-test")
        self.assertTrue(captured["agent_ran"])
        self.assertTrue(captured["browser_stopped"])
        self.assertEqual(result, "sender@example.test")

    def test_phathanh_playwright_mode_uses_raw_playwright_without_oauth_lookup(self) -> None:
        case = {
            "contract_number": "010/2026/N06-0946/DN",
            "customer_info": "Test Customer",
            "customer_address": "Test Address",
        }

        with (
            patch.dict("os.environ", {"PHATHANH_SEND_MODE": "playwright"}, clear=False),
            patch(
                "src.email_reply_service.send_phathanh_email_via_playwright_raw",
                new=AsyncMock(return_value="playwright-recipient"),
            ) as send_raw,
            patch("src.oauth2_service.get_enabled_oauth_provider") as get_provider,
        ):
            result = asyncio.run(send_phathanh_email_for_case(case, recipient="Recipient"))

        self.assertEqual(result, "playwright-recipient")
        send_raw.assert_awaited_once()
        self.assertIn("010/2026/N06-0946/DN", send_raw.await_args.args[0]["contract_number"])
        self.assertIn("Test Customer", send_raw.await_args.args[1])
        get_provider.assert_not_called()

    def test_raw_playwright_does_not_send_when_html_insert_fails(self) -> None:
        captured = {"send_clicked": False}

        class FakeElement:
            def __init__(self, name: str):
                self.name = name

            async def click(self):
                if self.name == "send":
                    captured["send_clicked"] = True

            async def press(self, _key):
                return None

            async def fill(self, _value):
                return None

        class FakePage:
            async def goto(self, *_args, **_kwargs):
                return None

            async def wait_for_load_state(self, *_args, **_kwargs):
                return None

            async def wait_for_timeout(self, *_args, **_kwargs):
                return None

            async def wait_for_selector(self, selector, *_args, **_kwargs):
                if "input#username" in selector:
                    raise RuntimeError("already logged in")
                if "button:has-text('Send')" in selector:
                    return FakeElement("send")
                return FakeElement("other")

            async def click(self, *_args, **_kwargs):
                return None

            async def evaluate(self, *_args, **_kwargs):
                return {"ok": False, "reason": "reply editor not found"}

        class FakeContext:
            def __init__(self):
                self.pages = [FakePage()]

            async def new_page(self):
                return FakePage()

            async def close(self):
                captured["context_closed"] = True

        class FakeChromium:
            async def launch_persistent_context(self, *_args, **_kwargs):
                return FakeContext()

        class FakePlaywright:
            def __init__(self):
                self.chromium = FakeChromium()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

        fake_playwright_module = types.SimpleNamespace(async_playwright=lambda: FakePlaywright())

        with (
            patch.dict(sys.modules, {"playwright.async_api": fake_playwright_module}),
            patch.dict(
                "os.environ",
                {
                    "CHROME_USER_DATA_DIR": ".",
                    "WEBMAIL_URL": "https://owa.example.test/",
                    "PLAYWRIGHT_HEADLESS": "true",
                },
                clear=False,
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "Không thể chèn nội dung phát hành"):
                asyncio.run(
                    send_phathanh_email_via_playwright_raw(
                        {"contract_number": "010/2026/N06-0946/DN"},
                        "<p>body</p>",
                    )
                )

        self.assertFalse(captured["send_clicked"])
        self.assertTrue(captured["context_closed"])


if __name__ == "__main__":
    unittest.main()
