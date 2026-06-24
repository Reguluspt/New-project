"""Tests for sobo (preliminary valuation) endpoints.

Actual routes:
  GET  /api/sobo                            → paginated list
  GET  /api/sobo/<id>                       → single record
  PUT  /api/sobo/<id>                       → update record
  GET  /api/sobo/stats                      → stats
  POST /api/sobo/check-mail                 → check email
  POST /api/sobo/from-case/<case_id>        → create sobo from case
"""


def test_list_sobo(auth_client):
    resp = auth_client.get("/api/sobo")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


def test_sobo_pagination(auth_client):
    resp = auth_client.get("/api/sobo?page=1&size=5")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["items"]) <= 5


def test_sobo_stats(auth_client):
    resp = auth_client.get("/api/sobo/stats")
    assert resp.status_code == 200


def test_sobo_search(auth_client):
    resp = auth_client.get("/api/sobo?search=%C4%91%E1%BA%A5t")
    assert resp.status_code == 200


def test_sobo_get_nonexistent(auth_client):
    resp = auth_client.get("/api/sobo/999999999")
    assert resp.status_code == 404


def test_sobo_update_nonexistent(auth_client):
    """Updating a non-existent sobo record — the API returns 200 (upsert) or 404 depending on implementation."""
    resp = auth_client.put("/api/sobo/999999999", json={"status": "Đã xử lý"})
    assert resp.status_code in (200, 404)


def test_unauthenticated(client):
    resp = client.get("/api/sobo")
    assert resp.status_code == 401
