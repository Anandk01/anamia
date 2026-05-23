"""
Profile Blueprint — /api/profile

User profile management endpoints.
"""

import json

from flask import Blueprint, g, jsonify, request

from db import get_db
from middleware.auth import require_auth
from middleware.rbac import require_role
from services import profile_service

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.get("/")
@require_auth
def get_profile():
    username = g.current_user["username"]
    profile = profile_service.get_profile(username)
    if not profile:
        return jsonify({"status": "error", "message": "User not found"}), 404
    return jsonify({"status": "ok", "profile": profile}), 200


@profile_bp.get("/<username>")
@require_auth
@require_role("doctor", "admin")
def get_patient_profile(username):
    """Get a patient's profile (doctor/admin only)."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT username, email, age, sex, blood_type, known_conditions, dietary_preferences, created_at FROM user WHERE username = ?",
            (username,),
        ).fetchone()
        if not row:
            return jsonify({"status": "error", "message": "User not found"}), 404
        profile = dict(row)
        # Parse JSON fields
        for field in ['known_conditions', 'dietary_preferences']:
            if profile.get(field) and isinstance(profile[field], str):
                try:
                    profile[field] = json.loads(profile[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return jsonify({"status": "ok", "profile": profile}), 200
    finally:
        conn.close()


@profile_bp.put("/")
@require_auth
def update_profile():
    username = g.current_user["username"]
    data = request.get_json(silent=True) or {}

    # Ensure age and sex are properly handled as integers
    if 'age' in data and data['age'] is not None:
        try:
            data['age'] = int(data['age'])
        except (ValueError, TypeError):
            data['age'] = None
    if 'sex' in data and data['sex'] is not None:
        try:
            data['sex'] = int(data['sex'])
        except (ValueError, TypeError):
            data['sex'] = None

    profile = profile_service.update_health_profile(username, data)
    return jsonify({"status": "ok", "profile": profile}), 200


@profile_bp.put("/preferences")
@require_auth
def update_preferences():
    username = g.current_user["username"]
    data = request.get_json(silent=True) or {}
    profile = profile_service.update_preferences(username, data)
    return jsonify({"status": "ok", "profile": profile}), 200


@profile_bp.put("/password")
@require_auth
def change_password():
    username = g.current_user["username"]
    data = request.get_json(silent=True) or {}
    current = data.get("current_password", "")
    new = data.get("new_password", "")
    if not current or not new:
        return jsonify({"status": "error", "message": "current_password and new_password required"}), 400
    try:
        result = profile_service.change_password(username, current, new)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    return jsonify({"status": "ok", **result}), 200


@profile_bp.put("/available-hours")
@require_auth
@require_role("doctor")
def update_available_hours():
    username = g.current_user["username"]
    data = request.get_json(silent=True) or {}
    hours = data.get("hours")
    if not hours:
        return jsonify({"status": "error", "message": "hours field required"}), 400
    profile = profile_service.update_available_hours(username, hours)
    return jsonify({"status": "ok", "profile": profile}), 200


# ---------------------------------------------------------------------------
# GET /api/profile/quick-stats — quick stats for dashboard
# ---------------------------------------------------------------------------

from db import get_db

@profile_bp.get("/quick-stats")
@require_auth
def quick_stats():
    """Return quick stats for the patient dashboard."""
    username = g.current_user["username"]
    conn = get_db()
    try:
        # Total tests
        row = conn.execute("SELECT COUNT(*) as cnt FROM prediction WHERE username = ?", (username,)).fetchone()
        total_tests = row["cnt"] if row else 0

        # Last HGB
        row = conn.execute("SELECT hgb FROM prediction WHERE username = ? ORDER BY date DESC LIMIT 1", (username,)).fetchone()
        last_hgb = round(row["hgb"], 1) if row else None

        # Adherence (simple: taken / total active meds * 100)
        adherence = None

        # Next appointment
        row = conn.execute(
            "SELECT slot_date, slot_time FROM appointment WHERE patient_id = (SELECT user_id FROM user WHERE username = ?) AND status = 'confirmed' AND slot_date >= date('now') ORDER BY slot_date, slot_time LIMIT 1",
            (username,),
        ).fetchone()
        next_appointment = f"{row['slot_date']} {row['slot_time']}" if row else None

        return jsonify({
            "status": "ok",
            "total_tests": total_tests,
            "last_hgb": last_hgb,
            "adherence": adherence,
            "next_appointment": next_appointment,
        }), 200
    finally:
        conn.close()
