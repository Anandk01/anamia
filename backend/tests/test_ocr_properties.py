"""
test_ocr_properties.py — Property-based tests for the OCR upload endpoint.

**Validates: Requirements 12.1, 12.5**

Properties tested:
  Property 21 — Oversized file (> 10 MB) or wrong MIME type → 400 BEFORE
                ocr_service.extract_cbc_from_file is called (verified with mock).

Test cases:
  - File with wrong MIME type (text/plain, application/json) → 400
  - File exceeding 10 MB → 400
  - Valid MIME but empty file → should proceed to OCR (not 400)
"""

from __future__ import annotations

import importlib
import io
import os
import sys
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

# Ensure backend/ is importable when pytest is run from the workspace root.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# Force the actual module (not the Blueprint object) into sys.modules so that
# patch("blueprints.ocr_bp.extract_cbc_from_file") resolves correctly.
_ocr_bp_module = importlib.import_module("blueprints.ocr_bp")

# ---------------------------------------------------------------------------
# Constants (must match ocr_bp.py)
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_auth_token(app) -> str:
    """Insert a test user and return a valid JWT."""
    import bcrypt
    import jwt as pyjwt
    import db as db_module
    from middleware.auth import JWT_SECRET, JWT_ALGORITHM

    username = f"ocruser_{uuid.uuid4().hex[:8]}"
    email = f"{username}@example.com"
    pw_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt(rounds=4)).decode()

    with app.app_context():
        conn = db_module.get_db()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO user "
                "(username, email, password_hash, role, status) "
                "VALUES (?, ?, ?, 'patient', 'active')",
                (username, email, pw_hash),
            )
            conn.commit()
        finally:
            conn.close()

    now = datetime.utcnow()
    payload = {
        "sub": username,
        "username": username,
        "role": "patient",
        "email": email,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(hours=24),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _upload(client, data: bytes, mime_type: str, token: str):
    """POST /api/ocr/upload with the given bytes and MIME type."""
    return client.post(
        "/api/ocr/upload",
        data={"file": (io.BytesIO(data), "report.bin", mime_type)},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )


# ---------------------------------------------------------------------------
# Property 21 — Wrong MIME type → 400, extract_cbc_from_file NOT called
# **Validates: Requirements 12.5**
# ---------------------------------------------------------------------------

INVALID_MIME_TYPES = ["text/plain", "application/json"]


@pytest.mark.parametrize("bad_mime", INVALID_MIME_TYPES)
def test_property_21_wrong_mime_type_returns_400_no_ocr(app, client, bad_mime):
    """
    Property 21 (wrong MIME): Uploading a file with an unsupported MIME type
    MUST return 400 and MUST NOT call extract_cbc_from_file.

    **Validates: Requirements 12.5**
    """
    token = _get_auth_token(app)
    small_data = b"some content"

    with patch.object(
        _ocr_bp_module, "extract_cbc_from_file"
    ) as mock_extract:
        resp = _upload(client, small_data, bad_mime, token)

    assert resp.status_code == 400, (
        f"Expected 400 for MIME type {bad_mime!r}, got {resp.status_code}"
    )
    mock_extract.assert_not_called()


# ---------------------------------------------------------------------------
# Property 21 — Oversized file → 400, extract_cbc_from_file NOT called
# **Validates: Requirements 12.5**
# ---------------------------------------------------------------------------

@settings(max_examples=5, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    extra_bytes=st.integers(min_value=1, max_value=1024 * 1024),  # 1 B – 1 MB over limit
    mime_type=st.sampled_from(sorted(ALLOWED_MIME_TYPES)),
)
def test_property_21_oversized_file_returns_400_no_ocr(
    app, client, extra_bytes: int, mime_type: str
):
    """
    Property 21 (oversized): Uploading a file whose size exceeds 10 MB MUST
    return 400 and MUST NOT call extract_cbc_from_file.

    **Validates: Requirements 12.5**
    """
    token = _get_auth_token(app)
    oversized_data = b"x" * (MAX_FILE_SIZE_BYTES + extra_bytes)

    with patch.object(
        _ocr_bp_module, "extract_cbc_from_file"
    ) as mock_extract:
        resp = _upload(client, oversized_data, mime_type, token)

    assert resp.status_code == 400, (
        f"Expected 400 for oversized file ({len(oversized_data)} bytes), "
        f"got {resp.status_code}"
    )
    mock_extract.assert_not_called()


# ---------------------------------------------------------------------------
# Property 21 — Valid MIME + empty file → proceeds to OCR (not 400)
# **Validates: Requirements 12.1**
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("valid_mime", sorted(ALLOWED_MIME_TYPES))
def test_property_21_valid_mime_empty_file_proceeds_to_ocr(app, client, valid_mime):
    """
    Property 21 (valid MIME, empty file): An empty file with a valid MIME type
    MUST NOT be rejected with 400 due to MIME/size validation — it should
    proceed to the OCR step (extract_cbc_from_file IS called).

    The OCR step itself may return empty values, but the validation gate
    must not block it.

    **Validates: Requirements 12.1**
    """
    token = _get_auth_token(app)
    empty_data = b""

    mock_ocr_result = {
        "values": {},
        "confidence": {},
        "warnings": ["No CBC fields could be extracted from the empty file."],
    }

    with patch.object(
        _ocr_bp_module,
        "extract_cbc_from_file",
        return_value=mock_ocr_result,
    ) as mock_extract:
        resp = _upload(client, empty_data, valid_mime, token)

    # Must not be a 400 from validation
    assert resp.status_code != 400, (
        f"Empty file with valid MIME {valid_mime!r} should not be rejected "
        f"by validation (got 400)"
    )

    # extract_cbc_from_file must have been called
    mock_extract.assert_called_once()


# ---------------------------------------------------------------------------
# Unit tests — endpoint requires authentication
# ---------------------------------------------------------------------------

def test_ocr_upload_requires_auth(client):
    """POST /api/ocr/upload without a token must return 401."""
    resp = client.post(
        "/api/ocr/upload",
        data={"file": (io.BytesIO(b"data"), "report.jpg", "image/jpeg")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 401


def test_ocr_upload_no_file_field_returns_400(app, client):
    """POST /api/ocr/upload with no file field must return 400."""
    token = _get_auth_token(app)
    resp = client.post(
        "/api/ocr/upload",
        data={},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_ocr_upload_returns_ok_structure_on_success(app, client):
    """
    POST /api/ocr/upload with a valid JPEG and mocked OCR must return 200
    with the expected JSON structure.
    """
    token = _get_auth_token(app)
    small_jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100  # minimal JPEG-like bytes

    mock_ocr_result = {
        "values": {"hgb": 12.5, "rbc": 4.5},
        "confidence": {"hgb": "High", "rbc": "High"},
        "warnings": [],
    }

    with patch.object(
        _ocr_bp_module,
        "extract_cbc_from_file",
        return_value=mock_ocr_result,
    ):
        resp = _upload(client, small_jpeg, "image/jpeg", token)

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert "values" in body
    assert "confidence" in body
    assert "warnings" in body
    assert body["values"]["hgb"] == pytest.approx(12.5)
