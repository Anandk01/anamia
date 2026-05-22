"""
Reports Blueprint — /api

Routes:
    GET /api/reports              → paginated prediction history (role-filtered)
    GET /api/reports/<id>         → single prediction record detail
    GET /api/trend/<username>     → HGB time-series for trend chart
"""

import json
import logging
import math

from flask import Blueprint, g, jsonify, request

from db import get_db
from middleware.auth import require_auth

logger = logging.getLogger(__name__)

reports_bp = Blueprint("reports", __name__, url_prefix="/api")

PAGE_SIZE = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_json_field(value):
    """Safely parse a JSON TEXT field from the DB; return [] on failure."""
    if value is None:
        return []
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def _row_to_dict(row) -> dict:
    """Convert a sqlite3.Row prediction record to a serialisable dict."""
    d = dict(row)
    d["explanation"] = _parse_json_field(d.get("explanation"))
    d["diet_recs"] = _parse_json_field(d.get("diet_recs"))
    d["health_tips"] = _parse_json_field(d.get("health_tips"))
    return d


# ---------------------------------------------------------------------------
# GET /api/reports
# ---------------------------------------------------------------------------

@reports_bp.get("/reports")
@require_auth
def get_reports():
    """
    Return paginated prediction history, role-filtered.

    Query params:
        page (int, default 1) — 1-based page number

    Role behaviour:
        patient / doctor : only their own records (WHERE username = current_user)
        admin            : all records

    Returns:
        200: {"status": "ok", "records": [...], "total": N, "page": P, "pages": total_pages}
        400: {"status": "error", "message": "..."}
    """
    current_user = g.current_user
    username = current_user["username"]
    role = current_user.get("role", "patient")

    # Parse page param
    try:
        page = int(request.args.get("page", 1))
        if page < 1:
            page = 1
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid 'page' parameter"}), 400

    offset = (page - 1) * PAGE_SIZE

    conn = get_db()
    try:
        if role == "admin":
            total_row = conn.execute(
                "SELECT COUNT(*) FROM prediction"
            ).fetchone()
            total = total_row[0]

            rows = conn.execute(
                "SELECT * FROM prediction ORDER BY date DESC LIMIT ? OFFSET ?",
                (PAGE_SIZE, offset),
            ).fetchall()
        else:
            total_row = conn.execute(
                "SELECT COUNT(*) FROM prediction WHERE username = ?",
                (username,),
            ).fetchone()
            total = total_row[0]

            rows = conn.execute(
                "SELECT * FROM prediction WHERE username = ? ORDER BY date DESC LIMIT ? OFFSET ?",
                (username, PAGE_SIZE, offset),
            ).fetchall()
    finally:
        conn.close()

    records = [_row_to_dict(row) for row in rows]
    total_pages = max(1, math.ceil(total / PAGE_SIZE))

    return jsonify({
        "status": "ok",
        "records": records,
        "total": total,
        "page": page,
        "pages": total_pages,
    }), 200


# ---------------------------------------------------------------------------
# GET /api/reports/<id>
# ---------------------------------------------------------------------------

@reports_bp.get("/reports/<int:report_id>")
@require_auth
def get_report(report_id: int):
    """
    Return a single prediction record by ID with ownership check.

    Role behaviour:
        patient / doctor : can only access their own records
        admin            : can access any record

    Returns:
        200: {"status": "ok", "record": {...}}
        403: {"status": "error", "message": "Access denied"}
        404: {"status": "error", "message": "Record not found"}
    """
    current_user = g.current_user
    username = current_user["username"]
    role = current_user.get("role", "patient")

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM prediction WHERE prediction_id = ?",
            (report_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return jsonify({"status": "error", "message": "Record not found"}), 404

    # Ownership check
    if role != "admin" and row["username"] != username:
        return jsonify({"status": "error", "message": "Access denied"}), 403

    return jsonify({"status": "ok", "record": _row_to_dict(row)}), 200


# ---------------------------------------------------------------------------
# GET /api/trend/<username>
# ---------------------------------------------------------------------------

@reports_bp.get("/trend/<string:target_username>")
@require_auth
def get_trend(target_username: str):
    """
    Return the last 12+ HGB values with dates and severity_level for a user.

    Ownership enforcement:
        patient / doctor : can only view their own trend data
        admin            : can view any user's trend data

    Returns:
        200: {"status": "ok", "username": str, "trend": [{"date": str, "hgb": float, "severity_level": str}, ...]}
        403: {"status": "error", "message": "Access denied"}
        404: {"status": "error", "message": "No trend data found"}
    """
    current_user = g.current_user
    username = current_user["username"]
    role = current_user.get("role", "patient")

    # Ownership check — doctors can view any patient's trend
    if role not in ("admin", "doctor") and target_username != username:
        return jsonify({"status": "error", "message": "Access denied"}), 403

    conn = get_db()
    try:
        # Support ?source=doctor filter to only show doctor-submitted predictions
        source = request.args.get("source")
        if source == "doctor":
            rows = conn.execute(
                """
                SELECT p.date, p.hgb, p.severity_level
                FROM prediction p
                JOIN user u ON p.username = u.username
                WHERE p.username = ? AND u.role = 'doctor'
                UNION
                SELECT p.date, p.hgb, p.severity_level
                FROM prediction p
                WHERE p.username = ?
                  AND EXISTS (SELECT 1 FROM user u2 WHERE u2.username = p.username AND u2.role != 'patient')
                ORDER BY date ASC
                LIMIT 50
                """,
                (target_username, target_username),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT date, hgb, severity_level
                FROM prediction
                WHERE username = ?
                ORDER BY date ASC
                LIMIT 50
                """,
                (target_username,),
            ).fetchall()
    finally:
        conn.close()

    if not rows:
        return jsonify({"status": "error", "message": "No trend data found"}), 404

    trend = [
        {
            "date": row["date"],
            "hgb": float(row["hgb"]),
            "severity_level": row["severity_level"],
        }
        for row in rows
    ]

    return jsonify({
        "status": "ok",
        "username": target_username,
        "trend": trend,
    }), 200
