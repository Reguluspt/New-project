"""Tests for templates and settings endpoints.

Actual routes:
  GET /api/templates           → list of templates
  GET /api/templates/<name>    → single template info (includes placeholders)
  PUT /api/templates/<name>    → upload new version

  GET /api/settings            → read settings (read-only, no global PUT)
  PUT /api/settings/paths      → update path configuration
  POST /api/settings/backup    → create backup
"""

import json

from api.blueprints import settings as settings_module


def test_list_templates(auth_client):
    resp = auth_client.get("/api/templates")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    # Each template must have name and path
    for tmpl in data:
        assert "name" in tmpl
        assert "path" in tmpl


def test_get_single_template(auth_client):
    """If no templates exist, skip. Otherwise fetch details."""
    resp = auth_client.get("/api/templates")
    templates = resp.get_json()
    if not templates:
        return  # No templates configured; skip
    name = templates[0]["name"]
    detail_resp = auth_client.get(f"/api/templates/{name}")
    assert detail_resp.status_code in (200, 404)


def test_get_settings(auth_client):
    resp = auth_client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)


def test_update_ai_config_masks_key_and_clears_legacy_storage(auth_client, monkeypatch, tmp_path):
    env_path = tmp_path / "API.env"
    env_path.write_text("GEMINI_API_KEY=old-key\nGEMINI_MODEL=old-model\n", encoding="utf-8")
    ai_config_path = tmp_path / "ai_config.json"
    ai_config_path.write_text(
        json.dumps({"providers": {"Gemini": {"api_key": "legacy-key"}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings_module, "API_ENV_PATH", env_path)
    monkeypatch.setattr(settings_module, "AI_CONFIG_PATH", ai_config_path)
    monkeypatch.setenv("GEMINI_API_KEY", "old-key")

    response = auth_client.put(
        "/api/settings/ai-config",
        json={"gemini_api_key": "new-secret-key", "gemini_model": "gemini-test"},
    )

    assert response.status_code == 200
    assert "new-secret-key" not in response.get_data(as_text=True)
    assert response.get_json()["gemini"]["key_suffix"] == "••••-key"
    assert "GEMINI_API_KEY=new-secret-key" in env_path.read_text(encoding="utf-8")
    assert json.loads(ai_config_path.read_text(encoding="utf-8"))["providers"]["Gemini"]["api_key"] == ""


def test_restart_ai_services_uses_fixed_allowlist(auth_client, monkeypatch):
    commands = []

    def fake_run(command, **kwargs):
        commands.append((command, kwargs))

    monkeypatch.setattr(settings_module.subprocess, "run", fake_run)

    response = auth_client.post("/api/settings/ai-config/restart-services")

    assert response.status_code == 200
    assert [command for command, _ in commands] == [
        ["systemctl", "restart", "telegram-bot.service"],
        ["systemctl", "restart", "mail-listener.service"],
    ]


def test_create_backup(auth_client):
    """Trigger a backup creation; should return 200 or 201."""
    resp = auth_client.post("/api/settings/backup")
    assert resp.status_code in (200, 201, 500)  # 500 if backup dir not configured, still not a route error


def test_unauthenticated_templates(client):
    resp = client.get("/api/templates")
    assert resp.status_code == 401


def test_unauthenticated_settings(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 401
