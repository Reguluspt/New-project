"""Tests for organizations and delivery endpoints.

Actual routes:
  GET    /api/organizations
  POST   /api/organizations
  PUT    /api/organizations/<id>
  DELETE /api/organizations/<id>

  GET    /api/delivery/contacts
  POST   /api/delivery/contacts
  PUT    /api/delivery/contacts/<id>
  DELETE /api/delivery/contacts/<id>
"""


def test_list_organizations(auth_client):
    resp = auth_client.get("/api/organizations")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_create_and_delete_organization(auth_client):
    payload = {
        "tax_code": "TESTPYTEST99",
        "name": "Tổ Chức Test Pytest",
        "abbreviation": "TEST-ORG",
        "representative": "Nguyễn Test",
    }
    create_resp = auth_client.post("/api/organizations", json=payload)
    assert create_resp.status_code in (200, 201)
    created = create_resp.get_json()
    org_id = created.get("id")
    assert org_id is not None

    # Update — PUT requires required fields, not just partial patch
    update_resp = auth_client.put(f"/api/organizations/{org_id}", json={
        "tax_code": "TESTPYTEST99",
        "name": "Tổ Chức Test Pytest - Updated",
        "abbreviation": "TEST-ORG-2",
        "representative": "Nguyễn Test",
    })
    assert update_resp.status_code == 200

    # Delete
    delete_resp = auth_client.delete(f"/api/organizations/{org_id}")
    assert delete_resp.status_code == 200


def test_search_organizations(auth_client):
    resp = auth_client.get("/api/organizations?search=ng%C3%A2n+h%C3%A0ng")
    assert resp.status_code == 200


def test_organizations_unauthenticated(client):
    resp = client.get("/api/organizations")
    assert resp.status_code == 401


def test_list_delivery_contacts(auth_client):
    # Delivery route is /api/delivery/contacts, not /api/delivery
    resp = auth_client.get("/api/delivery/contacts")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_create_and_delete_delivery(auth_client):
    payload = {
        "short_name": "PYTEST-DLV",
        "full_details": "Địa chỉ test pytest - 123 Đường Test, Hà Nội",
    }
    create_resp = auth_client.post("/api/delivery/contacts", json=payload)
    assert create_resp.status_code in (200, 201)
    created = create_resp.get_json()
    item_id = created.get("id")
    assert item_id is not None

    # Update — PUT requires all required fields
    update_resp = auth_client.put(f"/api/delivery/contacts/{item_id}", json={
        "short_name": "PYTEST-DLV-2",
        "full_details": "Địa chỉ test pytest - 123 Đường Test, Hà Nội - Updated",
    })
    assert update_resp.status_code == 200

    # Delete
    delete_resp = auth_client.delete(f"/api/delivery/contacts/{item_id}")
    assert delete_resp.status_code == 200
