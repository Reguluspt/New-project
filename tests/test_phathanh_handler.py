import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.ext import ConversationHandler

from src.phathanh_handler import finalize_phathanh


class PhathanhHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_finalize_uses_shared_mail_flow_and_marks_case_completed(self) -> None:
        status_message = SimpleNamespace(edit_text=AsyncMock())
        update = SimpleNamespace(
            callback_query=None,
            message=SimpleNamespace(reply_text=AsyncMock(return_value=status_message)),
        )
        context = SimpleNamespace(
            user_data={
                "phathanh_record": {
                    "id": "42",
                    "contract_number": "010/2026/N05-0881/DN",
                    "certificate_number": "CT-2026-001",
                },
                "phathanh_recipient": "Recipient details",
                "phathanh_record_source": "cases",
                "phathanh_cases_db": "data/cases.db",
            }
        )

        with (
            patch(
                "src.email_reply_service.send_phathanh_email_for_case",
                new=AsyncMock(return_value="sender@example.test"),
            ) as send_mail,
            patch("src.sqlite_store.update_case") as update_case,
        ):
            result = await finalize_phathanh(update, context)

        self.assertEqual(result, ConversationHandler.END)
        send_mail.assert_awaited_once_with(context.user_data["phathanh_record"], recipient="Recipient details")
        update_case.assert_called_once_with(
            "data/cases.db",
            42,
            {
                "case_status": "Hoàn thành",
                "cancel_reason": "",
                "certificate_number": "CT-2026-001",
            },
        )
        status_message.edit_text.assert_awaited()

    async def test_finalize_does_not_update_cases_db_for_records_source(self) -> None:
        status_message = SimpleNamespace(edit_text=AsyncMock())
        update = SimpleNamespace(
            callback_query=None,
            message=SimpleNamespace(reply_text=AsyncMock(return_value=status_message)),
        )
        context = SimpleNamespace(
            user_data={
                "phathanh_record": {"id": "7", "contract_number": "010/2026/N05-0881/DN"},
                "phathanh_recipient": "Recipient details",
                "phathanh_record_source": "records",
                "phathanh_cases_db": "data/cases.db",
            }
        )

        with (
            patch(
                "src.email_reply_service.send_phathanh_email_for_case",
                new=AsyncMock(return_value="sender@example.test"),
            ) as send_mail,
            patch("src.sqlite_store.update_case") as update_case,
        ):
            result = await finalize_phathanh(update, context)

        self.assertEqual(result, ConversationHandler.END)
        send_mail.assert_awaited_once_with(context.user_data["phathanh_record"], recipient="Recipient details")
        update_case.assert_not_called()


if __name__ == "__main__":
    unittest.main()
