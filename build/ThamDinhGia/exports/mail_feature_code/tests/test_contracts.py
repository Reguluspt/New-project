from __future__ import annotations

import unittest

from src.contracts import short_contract_number


class ContractNumberTests(unittest.TestCase):
    def test_short_contract_number_extracts_code_from_full_contract(self) -> None:
        self.assertEqual(short_contract_number("010/2026/N04-1051/DN"), "N04-1051")

    def test_short_contract_number_normalizes_dot_separator(self) -> None:
        self.assertEqual(short_contract_number("010/2026/N04.1027/DN"), "N04.1027")

    def test_short_contract_number_keeps_unknown_format(self) -> None:
        self.assertEqual(short_contract_number("HD-001"), "HD-001")

    def test_short_contract_number_uses_fallback_for_empty_value(self) -> None:
        self.assertEqual(short_contract_number("", fallback="Chưa có số HĐ"), "Chưa có số HĐ")


if __name__ == "__main__":
    unittest.main()
