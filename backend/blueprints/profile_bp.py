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


@profile_bp.get("")
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
    """Get a patient's profile (doctor/admin only).
    Returns basic user info even if profile fields are empty."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT username, email, age, sex, blood_type, known_conditions, dietary_preferences, created_at, role FROM user WHERE username = ?",
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


@profile_bp.put("")
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
    schedule = data.get("schedule") or data.get("hours")

    if not schedule:
        return jsonify({"status": "error", "message": "schedule required"}), 400

    # Convert array format to dict format for slot generation
    day_map = {
        "Monday": "mon", "Tuesday": "tue", "Wednesday": "wed",
        "Thursday": "thu", "Friday": "fri", "Saturday": "sat", "Sunday": "sun"
    }
    hours_dict = {}
    max_patients = data.get("max_patients_per_day", 10)

    if isinstance(schedule, list):
        for item in schedule:
            if item.get("available"):
                key = day_map.get(item["day"], item["day"][:3].lower())
                hours_dict[key] = {"start": item["start"], "end": item["end"]}
    elif isinstance(schedule, dict):
        hours_dict = schedule

    hours_dict["_max_patients_per_day"] = max_patients

    conn = get_db()
    try:
        conn.execute(
            "UPDATE user SET available_hours = ? WHERE username = ?",
            (json.dumps(hours_dict), username),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify({"status": "ok", "saved": True}), 200


@profile_bp.get("/available-hours")
@require_auth
def get_available_hours():
    """Return the current user's available hours schedule in array format."""
    username = g.current_user["username"]
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT available_hours FROM user WHERE username = ?", (username,)
        ).fetchone()
        if not row or not row["available_hours"]:
            return jsonify({"status": "ok", "schedule": [], "max_patients_per_day": 10}), 200

        hours = json.loads(row["available_hours"])
        max_patients = hours.get("_max_patients_per_day", 10)

        # Convert dict format back to array format for the frontend
        day_map_reverse = {
            "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday",
            "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday"
        }
        days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        schedule = []
        for day in days_order:
            key = day[:3].lower()
            if key in hours and isinstance(hours[key], dict):
                schedule.append({
                    "day": day,
                    "available": True,
                    "start": hours[key].get("start", "09:00"),
                    "end": hours[key].get("end", "17:00"),
                })
            else:
                schedule.append({
                    "day": day,
                    "available": False,
                    "start": "09:00",
                    "end": "17:00",
                })

        return jsonify({"status": "ok", "schedule": schedule, "max_patients_per_day": max_patients}), 200
    finally:
        conn.close()


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
