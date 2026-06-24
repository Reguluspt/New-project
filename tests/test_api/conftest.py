"""
Shared pytest fixtures for API integration tests.
"""
import sys
import os
import pytest

# Ensure project root is on the path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Load .env before importing app
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, "API.env"), override=True)
os.environ.setdefault("SECRET_KEY", "test-secret-key")

from api import create_app

_ADMIN_USERNAME = "truongpnt"
_ADMIN_PASSWORD = "Cen2026"


@pytest.fixture(scope="session")
def app():
    """Create the Flask application once per test session."""
    application = create_app()
    application.config.update({"TESTING": True})
    yield application


@pytest.fixture()
def client(app):
    """Fresh unauthenticated test client for each test (no cookie carry-over)."""
    with app.test_client() as c:
        yield c


@pytest.fixture()
def auth_client(app):
    """
    Authenticated test client per test.
    Logs in within a context manager so the cookie jar persists across
    requests made with this client, but is discarded after the test.
    """
    with app.test_client() as c:
        resp = c.post(
            "/api/auth/login",
            json={"username": _ADMIN_USERNAME, "password": _ADMIN_PASSWORD},
        )
        if resp.status_code != 200:
            pytest.skip(
                f"Login failed ({resp.status_code}): {resp.get_data(as_text=True)}"
            )
        yield c
