from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.auth import _create_auth_token, _validate_auth_token, authenticate


class AuthTests(unittest.TestCase):
    def test_authenticate_uses_configured_credentials(self) -> None:
        with patch.dict(
            os.environ,
            {"APP_LOGIN_USERNAME": "staff", "APP_LOGIN_PASSWORD": "secret"},
            clear=False,
        ):
            self.assertTrue(authenticate("staff", "secret"))
            self.assertFalse(authenticate("staff", "wrong"))
            self.assertFalse(authenticate("other", "secret"))

    def test_authenticate_rejects_missing_configuration(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(authenticate("staff", "secret"))

    def test_signed_auth_token_restores_configured_user(self) -> None:
        with patch.dict(
            os.environ,
            {"APP_LOGIN_USERNAME": "staff", "APP_LOGIN_PASSWORD": "secret"},
            clear=False,
        ):
            token = _create_auth_token("staff", now=100)
            self.assertEqual(_validate_auth_token(token, now=101), "staff")
            self.assertIsNone(_validate_auth_token(token, now=100 + 31 * 24 * 60 * 60))

    def test_signed_auth_token_is_invalid_after_password_change(self) -> None:
        with patch.dict(
            os.environ,
            {"APP_LOGIN_USERNAME": "staff", "APP_LOGIN_PASSWORD": "secret"},
            clear=False,
        ):
            token = _create_auth_token("staff", now=100)
        with patch.dict(
            os.environ,
            {"APP_LOGIN_USERNAME": "staff", "APP_LOGIN_PASSWORD": "new-secret"},
            clear=False,
        ):
            self.assertIsNone(_validate_auth_token(token, now=101))


if __name__ == "__main__":
    unittest.main()
