from src.form_options_store import add_custom_form_option
from api.blueprints import entry as entry_module


def test_add_entry_form_option_endpoint_persists_value(auth_client, monkeypatch, tmp_path):
    options_path = tmp_path / "custom_form_options.json"

    def add_for_test(field, value):
        return add_custom_form_option(field, value, options_path)

    monkeypatch.setattr(entry_module, "add_custom_form_option", add_for_test)

    response = auth_client.post(
        "/api/entry/form-options/custom",
        json={"field": "source", "value": "  Ngân hàng Test  "},
    )

    assert response.status_code == 200
    assert response.get_json() == {"field": "source", "values": ["Ngân hàng Test"]}


def test_add_entry_form_option_endpoint_rejects_unknown_field(auth_client):
    response = auth_client.post(
        "/api/entry/form-options/custom",
        json={"field": "unknown", "value": "Test"},
    )

    assert response.status_code == 400
    assert "error" in response.get_json()
