"""Tests for cases CRUD API endpoints."""


def test_list_cases(auth_client):
    resp = auth_client.get("/api/cases")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert isinstance(data["items"], list)


def test_list_cases_pagination(auth_client):
    resp = auth_client.get("/api/cases?page=1&size=5")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["items"]) <= 5


def test_list_cases_unauthenticated(client):
    resp = client.get("/api/cases")
    assert resp.status_code == 401


def test_create_and_get_case(auth_client):
    """Create a case, verify retrieval, update, and delete it."""
    payload = {
        "contract_number": "TEST-PYTEST-001",
        "customer_info": "Khách Hàng Test",
        "phone": "0900000000",
        "status": "Đang xử lý",
        "branch": "Hà Nội",
        "valuation_fee": 500000,
        "total_fee": 500000,
        "payment_status": "Chưa thanh toán",
    }
    create_resp = auth_client.post("/api/cases", json=payload)
    assert create_resp.status_code in (200, 201)
    created = create_resp.get_json()
    case_id = created.get("id")
    assert case_id is not None

    # Get the case
    get_resp = auth_client.get(f"/api/cases/{case_id}")
    assert get_resp.status_code == 200
    data = get_resp.get_json()
    assert data.get("contract_number") == "TEST-PYTEST-001"

    # Update the case
    update_resp = auth_client.put(f"/api/cases/{case_id}", json={"notes": "Updated by pytest"})
    assert update_resp.status_code == 200

    # Delete the case (cleanup)
    delete_resp = auth_client.delete(f"/api/cases/{case_id}")
    assert delete_resp.status_code == 200


def test_get_nonexistent_case(auth_client):
    resp = auth_client.get("/api/cases/999999999")
    assert resp.status_code == 404


def test_filter_cases_by_status(auth_client):
    resp = auth_client.get("/api/cases?status=%C4%90ang+x%E1%BB%AD+l%C3%BD")
    assert resp.status_code == 200


def test_sort_cases(auth_client):
    resp = auth_client.get("/api/cases?sort=received_date&order=desc")
    assert resp.status_code == 200


def test_cases_filter_options(auth_client):
    resp = auth_client.get("/api/cases/filters")
    assert resp.status_code == 200
