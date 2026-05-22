"""
Profile Blueprint — /api/profile

User profile management endpoints.
"""

from flask import Blueprint, g, jsonify, request

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


@profile_bp.put("/")
@require_auth
def update_profile():
    username = g.current_user["username"]
    data = request.get_json(silent=True) or {}
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
