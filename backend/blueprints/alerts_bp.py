"""
Alerts Blueprint — /api/alerts

Handles alert log retrieval and test alert dispatch.

Routes:
    GET  /api/alerts/        → list all alert_log rows ordered by sent_at DESC (Admin only)
    POST /api/alerts/test    → send a test alert email (Admin only)
"""

from flask import Blueprint, jsonify, request

from db import get_db
from middleware.auth import require_auth
from middleware.rbac import require_role

alerts_bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")


# ---------------------------------------------------------------------------
# GET /api/alerts/ — list all alert log entries (Admin only)
# ---------------------------------------------------------------------------

@alerts_bp.get("")
@require_auth
@require_role("admin")
def list_alerts():
    """Return all alert_log rows ordered by sent_at DESC.

    **Validates: Requirements 6.4, 6.5, 15.6, 20.6, 21.5**

    Response JSON:
        {
            "status": "ok",
            "alerts": [
                {
                    "alert_id": int,
                    "prediction_id": int,
                    "recipient_email": str,
                    "recipient_username": str,
                    "patient_username": str,
                    "hgb_value": float,
                    "severity_level": str,
                    "sent_at": str,
                    "delivery_status": str,
                    "retry_count": int
                },
                ...
            ],
            "total": int
        }
    """
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT alert_id, prediction_id, recipient_email, recipient_username,
                   patient_username, hgb_value, severity_level, sent_at,
                   delivery_status, retry_count
              FROM alert_log
             ORDER BY sent_at DESC
            """
        ).fetchall()
    finally:
        conn.close()

    alerts = [dict(row) for row in rows]
    return jsonify({"status": "ok", "alerts": alerts, "total": len(alerts)}), 200


# ---------------------------------------------------------------------------
# POST /api/alerts/test — send a test alert (Admin only)
# ---------------------------------------------------------------------------

@alerts_bp.post("/test")
@require_auth
@require_role("admin")
def test_alert():
    """Trigger a test alert email using a mock prediction result.

    **Validates: Requirements 6.1, 6.2**

    Request JSON:
        {
            "email":    str   — recipient email address,
            "username": str   — patient username to include in the alert,
            "hgb":      float — HGB value (should be < 7.0 to trigger),
            "severity": str   — severity level string (e.g. "Severe")
        }

    Response JSON (200):
        {"status": "ok", "message": "Test alert triggered", "triggered": bool}

    Response JSON (400):
        {"status": "error", "message": "..."}
    """
    data = request.get_json(silent=True) or {}

    # Validate required fields
    errors = []
    if not data.get("email"):
        errors.append("'email' is required")
    if not data.get("username"):
        errors.append("'username' is required")
    if data.get("hgb") is None:
        errors.append("'hgb' is required")
    else:
        try:
            float(data["hgb"])
        except (TypeError, ValueError):
            errors.append("'hgb' must be a numeric value")
    if not data.get("severity"):
        errors.append("'severity' is required")

    if errors:
        return jsonify({"status": "error", "message": "; ".join(errors)}), 400

    # Build a mock prediction_result dict
    mock_prediction = {
        "hgb": float(data["hgb"]),
        "severity_level": str(data["severity"]),
        "prediction_id": 0,  # test alert — no real prediction row
    }

    from services.alert_service import check_and_alert  # noqa: PLC0415

    triggered = check_and_alert(
        prediction_result=mock_prediction,
        username=str(data["username"]),
        recipient_email=str(data["email"]),
    )

    return jsonify(
        {
            "status": "ok",
            "message": "Test alert triggered" if triggered else "Threshold not met — no alert sent",
            "triggered": triggered,
        }
    ), 200


# ---------------------------------------------------------------------------
# GET /api/alerts/mine — list alerts for the current doctor
# ---------------------------------------------------------------------------

@alerts_bp.get("/mine")
@require_auth
@require_role("doctor")
def my_alerts():
    """Return alert_log rows where recipient_username matches the current doctor."""
    from flask import g
    username = g.current_user["username"]
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT alert_id, prediction_id, recipient_email, recipient_username,
                   patient_username, hgb_value, severity_level, sent_at,
                   delivery_status, retry_count, COALESCE(read, 0) as read
              FROM alert_log
             WHERE recipient_username = ?
             ORDER BY sent_at DESC
            """,
            (username,),
        ).fetchall()
    finally:
        conn.close()

    alerts = [dict(row) for row in rows]
    return jsonify({"status": "ok", "alerts": alerts, "total": len(alerts)}), 200


@alerts_bp.patch("/<int:alert_id>/read")
@require_auth
@require_role("doctor")
def mark_alert_read(alert_id):
    """Mark an alert as read."""
    from flask import g
    username = g.current_user["username"]
    conn = get_db()
    try:
        conn.execute(
            "UPDATE alert_log SET read = 1 WHERE alert_id = ? AND recipient_username = ?",
            (alert_id, username),
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"status": "ok"}), 200
