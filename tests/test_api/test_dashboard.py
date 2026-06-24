"""Tests for dashboard API endpoints.

Actual routes:
  GET /api/dashboard/stats         → { year_projected, year_paid, year_unpaid, month_projected, ... }
  GET /api/dashboard/recent-cases  → { cases: [...] }
  GET /api/dashboard/filters       → { years, branches, staff_names, statuses }
"""


def test_stats_structure(auth_client):
    resp = auth_client.get("/api/dashboard/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    for key in ("year_projected", "year_paid", "year_unpaid", "month_projected"):
        assert key in data, f"Missing key: {key}"
    for key in ("year_projected", "year_paid", "year_unpaid", "month_projected"):
        assert isinstance(data[key], (int, float))
        assert data[key] >= 0


def test_stats_with_filters(auth_client):
    resp = auth_client.get("/api/dashboard/stats?year=2024")
    assert resp.status_code == 200


def test_recent_cases(auth_client):
    resp = auth_client.get("/api/dashboard/recent-cases")
    assert resp.status_code == 200
    data = resp.get_json()
    # Response is a plain list of recent case objects
    assert isinstance(data, list)


def test_filter_options(auth_client):
    resp = auth_client.get("/api/dashboard/filters")
    assert resp.status_code == 200
    data = resp.get_json()
    for key in ("years", "branches", "staff_names", "statuses"):
        assert key in data


def test_unauthenticated_denied(client):
    resp = client.get("/api/dashboard/stats")
    assert resp.status_code == 401
