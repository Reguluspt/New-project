from __future__ import annotations

import ast
import os
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent


class ArchitectureTests(unittest.TestCase):
    def test_app_no_longer_imports_access_control(self) -> None:
        source_paths = [ROOT / "app.py", *ROOT.joinpath("src").rglob("*.py"), *ROOT.joinpath("views").rglob("*.py")]
        offenders: list[str] = []
        for path in source_paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "src.access_control":
                            offenders.append(f"{path}:{node.lineno}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module == "src.access_control":
                        offenders.append(f"{path}:{node.lineno}")

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()


class BackgroundServiceTests(unittest.TestCase):
    def test_ngrok_args_uses_webhook_host_as_static_url(self) -> None:
        from src.background_services import ngrok_args

        env = {
            "WEBHOOK_URL": "https://example.ngrok-free.dev/webhook/telegram",
            "NGROK_FORWARD_PORT": "8000",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(
                ngrok_args(),
                ["ngrok", "http", "8000", "--url", "https://example.ngrok-free.dev"],
            )
