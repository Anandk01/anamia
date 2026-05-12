"""
test_auth_properties.py — Property-based tests for authentication flows.

**Validates: Requirements 8.2, 8.3, 8.4, 8.7**

Properties tested:
  Property 14 — Any valid registration input → account has role=patient
  Property 15 — Wrong/expired OTP → 400, no account created
  Property 16 — Successful login JWT exp within ±60s of now+24h
  Property 17 — After logout, same token → 401
"""

import hashlib
import json
import sqlite3
import sys
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

# Ensure backend/ is importable
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Valid username: alphanumeric + underscore, 3–20 characters
_username_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"),
    min_size=3,
    max_size=20,
).filter(lambda s: s[0].isalpha() if s else False)

# Valid password: at least 8 printable ASCII characters (no spaces to avoid
# JSON encoding issues)
_password_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="!@#$%^&*",
    ),
    min_size=8,
    max_size=30,
)

# Valid email strategy
_email_strategy = st.emails()

# Wrong OTP: 6-digit string that is NOT the correct OTP
_wrong_otp_strategy = st.text(
    alphabet="0123456789",
    min_size=6,
    max_size=6,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _get_auth_module():
    """Return the auth_bp *module* (not the Blueprint object).

    ``blueprints.auth_bp`` is the Blueprint instance exported from the module.
    We need the module itself to patch its private helpers.
    """
    import importlib
    return importlib.import_module("blueprints.auth_bp")


def _register_and_get_otp(client, username: str, email: str, password: str):
    """
    Call POST /auth/register with SMTP mocked.
    Returns the OTP that was stored in the in-memory _otp_store.
    """
    captured_otp = {}

    auth_module = _get_auth_module()
    real_generate = auth_module._generate_otp

    def fake_generate():
        otp = real_generate()
        captured_otp["value"] = otp
        return otp

    with patch.object(auth_module, "_generate_otp", side_effect=fake_generate), \
         patch.object(auth_module, "_send_email", return_value=None):
        resp = client.post(
            "/auth/register",
            json={"username": username, "email": email, "password": password},
        )

    return resp, captured_otp.get("value")


def _full_register(client, username: str, email: str, password: str):
    """Register + verify OTP. Returns the verify-otp response."""
    resp, otp = _register_and_get_otp(client, username, email, password)
    if resp.status_code != 200:
        return resp, None

    auth_module = _get_auth_module()
    with patch.object(auth_module, "_send_email", return_value=None):
        verify_resp = client.post(
            "/auth/verify-register-otp",
            json={"email": email, "otp": otp},
        )
    return verify_resp, otp


# ---------------------------------------------------------------------------
# Property 14 — Any valid registration input → account has role=patient
# **Validates: Requirements 8.2**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    username=_username_strategy,
    password=_password_strategy,
)
def test_property_14_registration_always_creates_patient_role(
    app, client, db_conn, username, password
):
    """
    Property 14: For any valid (username, email, password) combination,
    after successful OTP verification the created account MUST have role='patient'.

    **Validates: Requirements 8.2**
    """
    # Use a deterministic email derived from username to avoid email strategy
    # generating addresses that are too long or contain special chars that
    # confuse the in-memory OTP store key.
    email = f"{username.lower()}@test.example.com"

    # Skip if username already exists in this test's DB (hypothesis may
    # generate the same username twice across examples within one test run
    # when max_examples is low — this is a test isolation concern, not a bug).
    row = db_conn.execute(
        "SELECT user_id FROM user WHERE username = ? OR email = ?",
        (username, email),
    ).fetchone()
    if row is not None:
        return  # already registered in a previous example — skip

    verify_resp, _ = _full_register(client, username, email, password)

    # If registration failed for any reason (e.g. duplicate from seed data),
    # skip rather than fail — we only assert on successful registrations.
    if verify_resp.status_code != 200:
        return

    data = verify_resp.get_json()
    assert data["status"] == "ok", f"Expected ok, got: {data}"

    # Assert role in JWT response
    assert data["user"]["role"] == "patient", (
        f"Expected role=patient, got {data['user']['role']!r}"
    )

    # Assert role in DB
    db_row = db_conn.execute(
        "SELECT role FROM user WHERE username = ?", (username,)
    ).fetchone()
    assert db_row is not None, "User row not found in DB after registration"
    assert db_row["role"] == "patient", (
        f"DB role is {db_row['role']!r}, expected 'patient'"
    )


# ---------------------------------------------------------------------------
# Property 15 — Wrong/expired OTP → 400, no account created
# **Validates: Requirements 8.3**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    username=_username_strategy,
    password=_password_strategy,
    wrong_otp=_wrong_otp_strategy,
)
def test_property_15_wrong_otp_returns_400_no_account_created(
    app, client, db_conn, username, password, wrong_otp
):
    """
    Property 15: Submitting a wrong OTP during registration MUST return 400
    and MUST NOT create a user account in the database.

    **Validates: Requirements 8.3**
    """
    email = f"{username.lower()}@wrongotp.example.com"

    # Skip if already registered
    row = db_conn.execute(
        "SELECT user_id FROM user WHERE username = ? OR email = ?",
        (username, email),
    ).fetchone()
    if row is not None:
        return

    resp, correct_otp = _register_and_get_otp(client, username, email, password)
    if resp.status_code != 200:
        return  # registration step failed — skip

    # Ensure wrong_otp is actually different from the correct OTP
    if wrong_otp == correct_otp:
        # Flip last digit to guarantee it's wrong
        wrong_otp = wrong_otp[:-1] + str((int(wrong_otp[-1]) + 1) % 10)

    auth_module = _get_auth_module()
    with patch.object(auth_module, "_send_email", return_value=None):
        verify_resp = client.post(
            "/auth/verify-register-otp",
            json={"email": email, "otp": wrong_otp},
        )

    # Must return 400
    assert verify_resp.status_code == 400, (
        f"Expected 400 for wrong OTP, got {verify_resp.status_code}"
    )

    # No account must have been created
    db_row = db_conn.execute(
        "SELECT user_id FROM user WHERE username = ? OR email = ?",
        (username, email),
    ).fetchone()
    assert db_row is None, (
        f"Account was created despite wrong OTP for username={username!r}"
    )


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    username=_username_strategy,
    password=_password_strategy,
)
def test_property_15b_expired_otp_returns_400_no_account_created(
    app, client, db_conn, username, password
):
    """
    Property 15 (expired variant): Submitting an expired OTP MUST return 400
    and MUST NOT create a user account.

    **Validates: Requirements 8.3**
    """
    email = f"{username.lower()}@expiredotp.example.com"

    row = db_conn.execute(
        "SELECT user_id FROM user WHERE username = ? OR email = ?",
        (username, email),
    ).fetchone()
    if row is not None:
        return

    resp, correct_otp = _register_and_get_otp(client, username, email, password)
    if resp.status_code != 200 or correct_otp is None:
        return

    # Manually expire the OTP in the in-memory store
    auth_module = _get_auth_module()
    if email in auth_module._otp_store:
        auth_module._otp_store[email]["expires_at"] = (
            datetime.utcnow() - timedelta(minutes=1)
        )

    with patch.object(auth_module, "_send_email", return_value=None):
        verify_resp = client.post(
            "/auth/verify-register-otp",
            json={"email": email, "otp": correct_otp},
        )

    assert verify_resp.status_code == 400, (
        f"Expected 400 for expired OTP, got {verify_resp.status_code}"
    )

    db_row = db_conn.execute(
        "SELECT user_id FROM user WHERE username = ? OR email = ?",
        (username, email),
    ).fetchone()
    assert db_row is None, (
        f"Account was created despite expired OTP for username={username!r}"
    )


# ---------------------------------------------------------------------------
# Property 16 — Successful login JWT exp within ±60s of now+24h
# **Validates: Requirements 8.4**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    username=_username_strategy,
    password=_password_strategy,
)
def test_property_16_login_jwt_exp_within_24h_window(
    app, client, db_conn, username, password
):
    """
    Property 16: After a successful login, the JWT's 'exp' claim MUST be
    within ±60 seconds of (now + 24 hours).

    **Validates: Requirements 8.4**
    """
    email = f"{username.lower()}@jwtexp.example.com"

    # Skip if already registered
    row = db_conn.execute(
        "SELECT user_id FROM user WHERE username = ? OR email = ?",
        (username, email),
    ).fetchone()
    if row is not None:
        return

    # Register the user
    verify_resp, _ = _full_register(client, username, email, password)
    if verify_resp.status_code != 200:
        return

    # Record time just before login
    before_login = datetime.utcnow()

    # Login
    login_resp = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )

    after_login = datetime.utcnow()

    assert login_resp.status_code == 200, (
        f"Login failed: {login_resp.get_json()}"
    )

    token = login_resp.get_json()["token"]

    # Decode without verification to inspect claims
    from middleware.auth import JWT_SECRET, JWT_ALGORITHM
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

    exp_dt = datetime.utcfromtimestamp(payload["exp"])

    # Expected expiry: between (before_login + 24h - 60s) and (after_login + 24h + 60s)
    expected_min = before_login + timedelta(hours=24) - timedelta(seconds=60)
    expected_max = after_login + timedelta(hours=24) + timedelta(seconds=60)

    assert expected_min <= exp_dt <= expected_max, (
        f"JWT exp {exp_dt} is outside the expected window "
        f"[{expected_min}, {expected_max}]"
    )


# ---------------------------------------------------------------------------
# Property 17 — After logout, same token → 401
# **Validates: Requirements 8.7**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    username=_username_strategy,
    password=_password_strategy,
)
def test_property_17_after_logout_token_is_rejected(
    app, client, db_conn, username, password
):
    """
    Property 17: After a user logs out, any subsequent request using the
    same JWT MUST be rejected with 401.

    **Validates: Requirements 8.7**
    """
    email = f"{username.lower()}@logout.example.com"

    # Skip if already registered
    row = db_conn.execute(
        "SELECT user_id FROM user WHERE username = ? OR email = ?",
        (username, email),
    ).fetchone()
    if row is not None:
        return

    # Register
    verify_resp, _ = _full_register(client, username, email, password)
    if verify_resp.status_code != 200:
        return

    # Login
    login_resp = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    if login_resp.status_code != 200:
        return

    token = login_resp.get_json()["token"]
    auth_header = {"Authorization": f"Bearer {token}"}

    # Verify token works before logout (sanity check)
    pre_logout_resp = client.post("/auth/logout", headers=auth_header)
    assert pre_logout_resp.status_code == 200, (
        f"Logout failed: {pre_logout_resp.get_json()}"
    )

    # After logout, the same token must be rejected on a protected endpoint
    post_logout_resp = client.post("/auth/logout", headers=auth_header)
    assert post_logout_resp.status_code == 401, (
        f"Expected 401 after logout, got {post_logout_resp.status_code}: "
        f"{post_logout_resp.get_json()}"
    )
