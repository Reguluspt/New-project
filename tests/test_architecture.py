from __future__ import annotations

import ast
import unittest
from pathlib import Path


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
