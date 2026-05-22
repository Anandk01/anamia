"""
Analytics Blueprint — /api/analytics

Dashboard analytics and system metrics.
"""

from flask import Blueprint, g, jsonify, request

from db import get_db
from middleware.auth import require_auth
from middleware.rbac import require_role
from services import analytics_service

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@analytics_bp.get("/overview")
@require_auth
@require_role("doctor", "admin")
def overview():
    doctor_username = None
    if g.current_user["role"] == "doctor":
        doctor_username = g.current_user["username"]
    metrics = analytics_service.get_overview_metrics(doctor_username=doctor_username)
    return jsonify({"status": "ok", "metrics": metrics}), 200


@analytics_bp.get("/trends")
@require_auth
@require_role("doctor", "admin")
def trends():
    metric = request.args.get("metric", "predictions")
    period = int(request.args.get("period_days", 30))
    data = analytics_service.get_trend_data(metric, period)
    return jsonify({"status": "ok", "trends": data}), 200


@analytics_bp.get("/adherence-summary")
@require_auth
@require_role("doctor", "admin")
def adherence_summary():
    doctor_username = None
    if g.current_user["role"] == "doctor":
        doctor_username = g.current_user["username"]
    data = analytics_service.get_adherence_summary(doctor_username)
    return jsonify({"status": "ok", "summary": data}), 200


@analytics_bp.get("/appointments-summary")
@require_auth
@require_role("doctor", "admin")
def appointments_summary():
    period = int(request.args.get("period_days", 30))
    data = analytics_service.get_appointments_summary(period)
    return jsonify({"status": "ok", "summary": data}), 200


@analytics_bp.get("/model-performance")
@require_auth
@require_role("admin")
def model_performance():
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT * FROM model_metrics ORDER BY trained_at DESC LIMIT 20"""
        ).fetchall()
        return jsonify({"status": "ok", "metrics": [dict(r) for r in rows]}), 200
    finally:
        conn.close()


@analytics_bp.get("/system-health")
@require_auth
@require_role("admin")
def system_health():
    data = analytics_service.get_system_health()
    return jsonify({"status": "ok", "health": data}), 200
