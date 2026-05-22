"""
Notifications Blueprint — /api/notifications

Notification management endpoints.
"""

from flask import Blueprint, g, jsonify, request

from db import get_db
from middleware.auth import require_auth
from services import notification_service

notifications_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@notifications_bp.get("/")
@require_auth
def list_notifications():
    username = g.current_user["username"]
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page

    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT * FROM notification WHERE username = ?
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (username, per_page, offset),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM notification WHERE username = ?",
            (username,),
        ).fetchone()[0]
        return jsonify({
            "status": "ok",
            "notifications": [dict(r) for r in rows],
            "total": total,
            "page": page,
        }), 200
    finally:
        conn.close()


@notifications_bp.get("/unread-count")
@require_auth
def unread_count():
    username = g.current_user["username"]
    count = notification_service.get_unread_count(username)
    return jsonify({"status": "ok", "count": count}), 200


@notifications_bp.put("/<int:notification_id>/read")
@require_auth
def mark_read(notification_id):
    username = g.current_user["username"]
    conn = get_db()
    try:
        conn.execute(
            "UPDATE notification SET read = 1 WHERE notification_id = ? AND username = ?",
            (notification_id, username),
        )
        conn.commit()
        return jsonify({"status": "ok"}), 200
    finally:
        conn.close()


@notifications_bp.put("/read-all")
@require_auth
def mark_all_read():
    username = g.current_user["username"]
    conn = get_db()
    try:
        conn.execute(
            "UPDATE notification SET read = 1 WHERE username = ? AND read = 0",
            (username,),
        )
        conn.commit()
        return jsonify({"status": "ok"}), 200
    finally:
        conn.close()


@notifications_bp.delete("/<int:notification_id>")
@require_auth
def delete_notification(notification_id):
    username = g.current_user["username"]
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM notification WHERE notification_id = ? AND username = ?",
            (notification_id, username),
        )
        conn.commit()
        return jsonify({"status": "ok"}), 200
    finally:
        conn.close()
