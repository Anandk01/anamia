"""
conftest.py — Shared pytest fixtures for the ADMS backend test suite.

Provides:
  - app        : Flask test application configured with an in-memory SQLite DB
  - client     : Flask test client bound to the test app
  - db_conn    : raw sqlite3 connection to the in-memory DB (for assertions)
"""

import os
import sqlite3
import sys
import tempfile

import pytest

# Ensure the backend directory is on sys.path so imports work when pytest is
# invoked from the workspace root or from backend/.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


@pytest.fixture(scope="function")
def app(tmp_path):
    """Create a Flask test application backed by a temporary SQLite file.

    A fresh database file is created for every test function so tests are
    fully isolated from each other and from the production ``anemia.db``.
    """
    db_file = tmp_path / "test_anemia.db"
    db_path = str(db_file)

    # Patch DB_PATH in db module before importing the app factory so that
    # every call to get_db() inside the app uses the test database.
    import db as db_module
    original_db_path = db_module.DB_PATH
    db_module.DB_PATH = db_path

    # Also patch sqlite3.connect calls that go through db.get_db
    # (get_db reads DB_PATH at call time, so patching the module attribute
    # is sufficient — no need to monkeypatch sqlite3 itself).

    from app import create_app

    flask_app = create_app()
    flask_app.config.update(
        {
            "TESTING": True,
            # Disable SMTP — tests must mock _send_email themselves
            "EMAIL_ADDRESS": "test@example.com",
            "EMAIL_PASSWORD": "test-password",
            "SMTP_SERVER": "localhost",
            "SMTP_PORT": 1025,
        }
    )

    # Initialise the test database schema
    with flask_app.app_context():
        db_module.init_db()

    yield flask_app

    # Restore original DB_PATH after the test
    db_module.DB_PATH = original_db_path


@pytest.fixture(scope="function")
def client(app):
    """Return a Flask test client for the test application."""
    return app.test_client()


@pytest.fixture(scope="function")
def db_conn(app):
    """Return a raw sqlite3 connection to the test database.

    Useful for asserting DB state directly without going through the API.
    The connection is closed automatically after the test.
    """
    import db as db_module

    conn = sqlite3.connect(db_module.DB_PATH)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()
