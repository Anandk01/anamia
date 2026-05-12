"""
test_reports_properties.py — Property-based tests for the reports API.

Property 12: GET /api/reports never returns other users' records for patient/doctor.
Property 18: Pagination union equals total N with no duplicates.

**Validates: Requirements 6.1, 6.2**
"""

import json
import os
import sys
from datetime import datetime
from unittest.mock import patch

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

# Ensure backend/ is importable
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_username_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"),
    min_size=3,
    max_size=15,
).filter(lambda s: s[0].isalpha())

_password_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="!@#"),
    min_size=8,
    max_size=20,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_auth_module():
    import importlib
    return importlib.import_module("blueprints.auth_bp")


def _register_and_login(client, username, email, password, role="patient"):
    """Register + verify OTP + login. Returns JWT token or None on failure."""
    auth_module = _get_auth_module()
    captured = {}

    real_gen = auth_module._generate_otp

    def fake_gen():
        otp = real_gen()
        captured["otp"] = otp
        return otp

    with patch.object(auth_module, "_generate_otp", side_effect=fake_gen), \
         patch.object(auth_module, "_send_email", return_value=None):
        reg_resp = client.post("/auth/register", json={
            "username": username, "email": email, "password": password
        })

    if reg_resp.status_code != 200:
        return None

    otp = captured.get("otp")
    if not otp:
        return None

    with patch.object(auth_module, "_send_email", return_value=None):
        verify_resp = client.post("/auth/verify-register-otp", json={
            "email": email, "otp": otp
        })

    if verify_resp.status_code != 200:
        return None

    # If role != patient, update in DB directly
    if role != "patient":
        import db as db_module
        import sqlite3
        conn = sqlite3.connect(db_module.DB_PATH)
        conn.execute("UPDATE user SET role = ? WHERE username = ?", (role, username))
        conn.commit()
        conn.close()

    login_resp = client.post("/auth/login", json={
        "username": username, "password": password
    })

    if login_resp.status_code != 200:
        return None

    return login_resp.get_json().get("token")


def _insert_prediction(db_conn, username, hgb=12.0, severity="None"):
    """Insert a fake prediction record for a user."""
    db_conn.execute(
        """
        INSERT INTO prediction
          (username, rbc, mcv, mch, mchc, rdw, tlc, plt, hgb,
           anemia_detected, severity_level, anemia_type, confidence,
           explanation, diet_recs, health_tips, risk_category, date)
        VALUES (?, 4.5, 85.0, 28.0, 33.0, 13.5, 7.0, 250.0, ?,
                0, ?, 'None', 0.9, '[]', '[]', '[]', 'N/A', ?)
        """,
        (username, hgb, severity, datetime.utcnow().isoformat(sep=" ")),
    )
    db_conn.commit()


# ---------------------------------------------------------------------------
# Property 12 — GET /api/reports never returns other users' records
# **Validates: Requirements 6.1**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    username_a=_username_strategy,
    username_b=_username_strategy,
    password=_password_strategy,
)
def test_property_12_reports_never_returns_other_users_records(
    app, client, db_conn, username_a, username_b, password
):
    """
    Property 12: For any two distinct users A and B, when user A calls
    GET /api/reports, the response MUST NOT contain any records belonging
    to user B.

    **Validates: Requirements 6.1**
    """
    # Ensure usernames are distinct
    if username_a == username_b:
        return

    email_a = f"{username_a.lower()}@prop12a.example.com"
    email_b = f"{username_b.lower()}@prop12b.example.com"

    # Skip if either user already exists
    for uname, email in [(username_a, email_a), (username_b, email_b)]:
        row = db_conn.execute(
            "SELECT user_id FROM user WHERE username = ? OR email = ?",
            (uname, email),
        ).fetchone()
        if row is not None:
            return

    # Register both users
    token_a = _register_and_login(client, username_a, email_a, password)
    token_b = _register_and_login(client, username_b, email_b, password)

    if not token_a or not token_b:
        return

    # Insert 2 predictions for user B
    _insert_prediction(db_conn, username_b, hgb=11.0, severity="Mild")
    _insert_prediction(db_conn, username_b, hgb=10.0, severity="Moderate")

    # User A fetches their own reports
    resp = client.get(
        "/api/reports",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.get_json()}"

    data = resp.get_json()
    records = data.get("records", [])

    # None of the returned records should belong to user B
    for rec in records:
        assert rec["username"] != username_b, (
            f"User A's report list contains a record belonging to user B "
            f"(username={username_b!r}, record={rec})"
        )


# ---------------------------------------------------------------------------
# Property 18 — Pagination union = total N, no duplicates
# **Validates: Requirements 6.2**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    username=_username_strategy,
    password=_password_strategy,
    num_records=st.integers(min_value=1, max_value=25),
)
def test_property_18_pagination_union_equals_total_no_duplicates(
    app, client, db_conn, username, password, num_records
):
    """
    Property 18: The union of all paginated pages MUST equal the total
    record count N, and MUST contain no duplicate prediction_ids.

    **Validates: Requirements 6.2**
    """
    email = f"{username.lower()}@prop18.example.com"

    # Skip if user already exists
    row = db_conn.execute(
        "SELECT user_id FROM user WHERE username = ? OR email = ?",
        (username, email),
    ).fetchone()
    if row is not None:
        return

    token = _register_and_login(client, username, email, password)
    if not token:
        return

    # Insert num_records predictions for this user
    for i in range(num_records):
        _insert_prediction(db_conn, username, hgb=12.0 - i * 0.1)

    headers = {"Authorization": f"Bearer {token}"}

    # Fetch first page to get total and pages
    resp1 = client.get("/api/reports?page=1", headers=headers)
    assert resp1.status_code == 200, f"Page 1 failed: {resp1.get_json()}"

    data1 = resp1.get_json()
    total = data1["total"]
    total_pages = data1["pages"]

    assert total >= num_records, (
        f"Expected at least {num_records} records, got {total}"
    )

    # Collect all prediction_ids across all pages
    all_ids = []
    for page in range(1, total_pages + 1):
        resp = client.get(f"/api/reports?page={page}", headers=headers)
        assert resp.status_code == 200, f"Page {page} failed: {resp.get_json()}"
        records = resp.get_json().get("records", [])
        for rec in records:
            all_ids.append(rec["prediction_id"])

    # Union count must equal total
    assert len(all_ids) == total, (
        f"Union of pages has {len(all_ids)} records but total={total}"
    )

    # No duplicates
    assert len(all_ids) == len(set(all_ids)), (
        f"Duplicate prediction_ids found across pages: "
        f"{[x for x in all_ids if all_ids.count(x) > 1]}"
    )
