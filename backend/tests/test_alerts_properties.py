"""
test_alerts_properties.py — Property-based tests for the Alert Service.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

Properties tested:
  Property 7 — For any critical input (hgb < 7.0 or severity="Severe"), the alert
               email body contains the patient username, HGB value, severity level,
               and a timestamp.
  Property 8 — retry_count in alert_log never exceeds 3 after the retry loop
               completes (regardless of how many failures occur).
"""

from __future__ import annotations

import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

# Ensure backend/ is importable when pytest is run from the workspace root.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from services.alert_service import (
    MAX_RETRIES,
    compose_alert_email,
    _retry_send,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# HGB values that are strictly below the critical threshold (< 7.0)
_hgb_critical_low_st = st.floats(
    min_value=0.1,
    max_value=6.99,
    allow_nan=False,
    allow_infinity=False,
)

# HGB values at or above the threshold (≥ 7.0) — used with severity="Severe"
_hgb_any_st = st.floats(
    min_value=0.1,
    max_value=20.0,
    allow_nan=False,
    allow_infinity=False,
)

# Usernames: printable ASCII, non-empty, reasonable length
_username_st = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-."),
    min_size=1,
    max_size=50,
)

# ---------------------------------------------------------------------------
# Property 7 — Email body contains username, HGB, severity, timestamp
# **Validates: Requirements 6.2**
# ---------------------------------------------------------------------------


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(hgb=_hgb_critical_low_st, username=_username_st)
def test_property_7_email_body_contains_required_fields_low_hgb(
    hgb: float, username: str
) -> None:
    """
    Property 7a: For any HGB < 7.0, compose_alert_email() MUST produce an HTML
    body that contains the patient username, the HGB value, the severity level,
    and a timestamp string.

    **Validates: Requirements 6.2**
    """
    severity = "Severe"
    timestamp = "2024-01-15 10:30:00"

    body = compose_alert_email(username, hgb, severity, timestamp)

    assert username in body, (
        f"Email body does not contain username={username!r}"
    )
    # HGB value should appear as a formatted float (e.g. "6.50")
    assert f"{hgb:.2f}" in body, (
        f"Email body does not contain HGB value {hgb:.2f}"
    )
    assert severity in body, (
        f"Email body does not contain severity={severity!r}"
    )
    assert timestamp in body, (
        f"Email body does not contain timestamp={timestamp!r}"
    )


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(hgb=_hgb_any_st, username=_username_st)
def test_property_7_email_body_contains_required_fields_severe(
    hgb: float, username: str
) -> None:
    """
    Property 7b: For any HGB value when severity="Severe", compose_alert_email()
    MUST produce an HTML body that contains the patient username, the HGB value,
    the severity level, and a timestamp string.

    **Validates: Requirements 6.2**
    """
    severity = "Severe"
    timestamp = "2024-06-20 08:15:45"

    body = compose_alert_email(username, hgb, severity, timestamp)

    assert username in body, (
        f"Email body does not contain username={username!r}"
    )
    assert f"{hgb:.2f}" in body, (
        f"Email body does not contain HGB value {hgb:.2f}"
    )
    assert severity in body, (
        f"Email body does not contain severity={severity!r}"
    )
    assert timestamp in body, (
        f"Email body does not contain timestamp={timestamp!r}"
    )


# ---------------------------------------------------------------------------
# Property 8 — retry_count in alert_log never exceeds 3
# **Validates: Requirements 6.3**
# ---------------------------------------------------------------------------


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    hgb=_hgb_critical_low_st,
    username=_username_st,
)
def test_property_8_retry_count_never_exceeds_3(
    hgb: float,
    username: str,
) -> None:
    """
    Property 8: After the retry loop completes (all attempts exhausted),
    the retry_count recorded in alert_log MUST NOT exceed MAX_RETRIES (3).

    We mock:
      - _send_email to always raise (simulating persistent failure)
      - _update_alert_log to capture the retry_count values written
      - time.sleep to avoid real delays

    **Validates: Requirements 6.3**
    """
    recorded_retry_counts: list[int] = []

    def fake_update(alert_id: int, delivery_status: str, retry_count: int) -> None:
        recorded_retry_counts.append(retry_count)

    with (
        patch("services.alert_service._send_email", side_effect=Exception("SMTP failure")),
        patch("services.alert_service._update_alert_log", side_effect=fake_update),
        patch("services.alert_service.time.sleep", return_value=None),
    ):
        _retry_send(
            alert_id=1,
            recipient_email="doctor@example.com",
            subject="Test Alert",
            html_body=compose_alert_email(username, hgb, "Severe", "2024-01-01 00:00:00"),
            smtp_config={
                "email_address": "test@example.com",
                "email_password": "password",
                "smtp_server": "localhost",
                "smtp_port": 1025,
            },
        )

    # Must have recorded exactly MAX_RETRIES update calls
    assert len(recorded_retry_counts) == MAX_RETRIES, (
        f"Expected {MAX_RETRIES} update calls, got {len(recorded_retry_counts)}"
    )

    # No recorded retry_count may exceed MAX_RETRIES
    for count in recorded_retry_counts:
        assert count <= MAX_RETRIES, (
            f"retry_count={count} exceeds MAX_RETRIES={MAX_RETRIES}"
        )


# ---------------------------------------------------------------------------
# Unit tests — check_and_alert integration
# ---------------------------------------------------------------------------


def test_check_and_alert_triggers_for_low_hgb(app) -> None:
    """check_and_alert returns True and inserts alert_log row when HGB < 7.0."""
    import db as db_module

    prediction = {"hgb": 5.5, "severity_level": "Severe", "prediction_id": 0}

    with app.app_context():
        with (
            patch("services.alert_service._send_email", return_value=None),
            patch("services.alert_service.time.sleep", return_value=None),
        ):
            from services.alert_service import check_and_alert
            triggered = check_and_alert(prediction, "testpatient", "doctor@example.com")

        # Give the background thread a moment to write the DB row
        time.sleep(0.2)

        assert triggered is True

        conn = db_module.get_db()
        try:
            row = conn.execute(
                "SELECT * FROM alert_log WHERE patient_username = 'testpatient'"
            ).fetchone()
        finally:
            conn.close()

        assert row is not None, "Expected an alert_log row to be inserted"
        assert row["hgb_value"] == pytest.approx(5.5)
        assert row["severity_level"] == "Severe"


def test_check_and_alert_triggers_for_severe_severity(app) -> None:
    """check_and_alert returns True when severity_level == 'Severe' even if HGB >= 7.0."""
    import db as db_module

    prediction = {"hgb": 8.5, "severity_level": "Severe", "prediction_id": 0}

    with app.app_context():
        with (
            patch("services.alert_service._send_email", return_value=None),
            patch("services.alert_service.time.sleep", return_value=None),
        ):
            from services.alert_service import check_and_alert
            triggered = check_and_alert(prediction, "severepatient", "doctor@example.com")

        time.sleep(0.2)

        assert triggered is True

        conn = db_module.get_db()
        try:
            row = conn.execute(
                "SELECT * FROM alert_log WHERE patient_username = 'severepatient'"
            ).fetchone()
        finally:
            conn.close()

        assert row is not None


def test_check_and_alert_does_not_trigger_for_non_critical(app) -> None:
    """check_and_alert returns False when HGB >= 7.0 and severity != 'Severe'."""
    prediction = {"hgb": 9.0, "severity_level": "Moderate", "prediction_id": 0}

    with app.app_context():
        from services.alert_service import check_and_alert
        triggered = check_and_alert(prediction, "normalpatient", "doctor@example.com")

    assert triggered is False


def test_retry_loop_stops_on_success() -> None:
    """_retry_send stops after the first successful send and records 'sent'."""
    recorded: list[tuple] = []

    def fake_update(alert_id: int, delivery_status: str, retry_count: int) -> None:
        recorded.append((delivery_status, retry_count))

    with (
        patch("services.alert_service._send_email", return_value=None),  # always succeeds
        patch("services.alert_service._update_alert_log", side_effect=fake_update),
        patch("services.alert_service.time.sleep", return_value=None),
    ):
        _retry_send(
            alert_id=99,
            recipient_email="doc@example.com",
            subject="Test",
            html_body="<p>test</p>",
            smtp_config={
                "email_address": "a@b.com",
                "email_password": "pw",
                "smtp_server": "localhost",
                "smtp_port": 1025,
            },
        )

    # Only one update call — on the first successful attempt
    assert len(recorded) == 1, f"Expected 1 update call, got {len(recorded)}: {recorded}"
    assert recorded[0][0] == "sent"
    assert recorded[0][1] == 1


def test_email_body_contains_act_immediately() -> None:
    """The email body must contain a recommendation to act immediately."""
    body = compose_alert_email("patient1", 5.0, "Severe", "2024-01-01 00:00:00")
    assert "immediately" in body.lower(), "Email body should recommend acting immediately"


def test_get_alerts_endpoint_requires_admin(app, client) -> None:
    """GET /api/alerts/ must return 403 for non-admin users."""
    import bcrypt
    import jwt as pyjwt
    from datetime import datetime, timedelta
    import uuid
    from middleware.auth import JWT_SECRET, JWT_ALGORITHM
    import db as db_module

    with app.app_context():
        conn = db_module.get_db()
        try:
            pw = bcrypt.hashpw(b"pass1234", bcrypt.gensalt(rounds=4)).decode()
            conn.execute(
                "INSERT OR IGNORE INTO user (username, email, password_hash, role, status) "
                "VALUES ('docuser', 'doc@x.com', ?, 'doctor', 'active')",
                (pw,),
            )
            conn.commit()
        finally:
            conn.close()

    now = datetime.utcnow()
    token = pyjwt.encode(
        {
            "sub": "docuser",
            "username": "docuser",
            "role": "doctor",
            "email": "doc@x.com",
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(hours=24),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    resp = client.get("/api/alerts/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_get_alerts_endpoint_returns_list_for_admin(app, client) -> None:
    """GET /api/alerts/ returns 200 with an alerts list for admin users."""
    import bcrypt
    import jwt as pyjwt
    from datetime import datetime, timedelta
    import uuid
    from middleware.auth import JWT_SECRET, JWT_ALGORITHM
    import db as db_module

    with app.app_context():
        conn = db_module.get_db()
        try:
            pw = bcrypt.hashpw(b"pass1234", bcrypt.gensalt(rounds=4)).decode()
            conn.execute(
                "INSERT OR IGNORE INTO user (username, email, password_hash, role, status) "
                "VALUES ('adminuser2', 'admin2@x.com', ?, 'admin', 'active')",
                (pw,),
            )
            conn.commit()
        finally:
            conn.close()

    now = datetime.utcnow()
    token = pyjwt.encode(
        {
            "sub": "adminuser2",
            "username": "adminuser2",
            "role": "admin",
            "email": "admin2@x.com",
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(hours=24),
        },
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    resp = client.get("/api/alerts/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "alerts" in data
    assert isinstance(data["alerts"], list)
