import json

import pytest

from src.form_options_store import (
    add_custom_form_option,
    load_custom_form_options,
    merge_custom_form_options,
)


def test_add_custom_form_option_persists_trimmed_unique_values(tmp_path):
    path = tmp_path / "custom_form_options.json"

    values = add_custom_form_option("source", "  Ngân hàng A  ", path)
    values = add_custom_form_option("source", "Ngân hàng A", path)

    assert values == ["Ngân hàng A"]
    assert json.loads(path.read_text(encoding="utf-8")) == {"source": ["Ngân hàng A"]}
    assert load_custom_form_options(path) == {"source": ["Ngân hàng A"]}


def test_add_custom_form_option_rejects_invalid_field(tmp_path):
    with pytest.raises(ValueError):
        add_custom_form_option("unknown", "Giá trị", tmp_path / "options.json")


def test_merge_custom_form_options_preserves_existing_order(tmp_path):
    path = tmp_path / "custom_form_options.json"
    add_custom_form_option("valuation_purpose", "Mục đích mới", path)

    merged = merge_custom_form_options(
        {"valuation_purpose": ["Mục đích cũ", "Mục đích mới"]},
        path,
    )

    assert merged["valuation_purpose"] == ["Mục đích cũ", "Mục đích mới"]
