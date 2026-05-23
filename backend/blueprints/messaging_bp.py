"""
Messaging Blueprint — /api/messages

Doctor-to-doctor messaging endpoints.

Routes:
    GET  /api/messages/doctors                      → list all doctors (for search)
    GET  /api/messages/rooms                        → doctor's room list (doctor-to-doctor)
    GET  /api/messages/room/<other_doctor_username> → get/create room between two doctors
    POST /api/messages/send                         → send a message
    GET  /api/messages/unread-count                 → count unread messages
    POST /api/messages/mark-read                    → mark messages as read
"""

from flask import Blueprint, g, jsonify, request

from db import get_db
from middleware.auth import require_auth
from middleware.rbac import require_role
from utils import notify_user

messaging_bp = Blueprint("messaging", __name__, url_prefix="/api/messages")


def _get_user_id(username: str) -> int | None:
    conn = get_db()
    try:
        row = conn.execute("SELECT user_id FROM user WHERE username = ?", (username,)).fetchone()
        return row["user_id"] if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /api/messages/doctors — list all active doctors for search
# ---------------------------------------------------------------------------

@messaging_bp.get("/doctors")
@require_auth
@require_role("doctor")
def list_doctors():
    """Return all active doctors except the current user (for search/start conversation)."""
    username = g.current_user["username"]

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT username, specialization FROM user WHERE role = 'doctor' AND status = 'active' AND username != ?",
            (username,),
        ).fetchall()
        doctors = [{"username": r["username"], "specialization": r["specialization"] or "General"} for r in rows]
        return jsonify({"status": "ok", "doctors": doctors}), 200
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /api/messages/rooms — doctor-to-doctor room list
# ---------------------------------------------------------------------------

@messaging_bp.get("/rooms")
@require_auth
@require_role("doctor")
def list_rooms():
    """Return all chat rooms where current doctor is either party (doctor-to-doctor)."""
    username = g.current_user["username"]
    user_id = _get_user_id(username)

    conn = get_db()
    try:
        rooms = conn.execute(
            """SELECT cr.room_id, cr.doctor_id, cr.patient_id, cr.last_message_at
               FROM chat_room cr
               WHERE cr.doctor_id = ? OR cr.patient_id = ?
               ORDER BY cr.last_message_at DESC""",
            (user_id, user_id),
        ).fetchall()

        result = []
        for room in rooms:
            room_dict = dict(room)
            # Determine the other doctor's user_id
            other_id = room_dict["patient_id"] if room_dict["doctor_id"] == user_id else room_dict["doctor_id"]
            # Get other doctor's username
            other_row = conn.execute("SELECT username, specialization FROM user WHERE user_id = ?", (other_id,)).fetchone()
            if not other_row:
                continue

            # Get last message
            last_msg = conn.execute(
                "SELECT content, message_type, created_at FROM chat_message WHERE room_id = ? ORDER BY created_at DESC LIMIT 1",
                (room_dict["room_id"],),
            ).fetchone()
            # Get unread count
            unread = conn.execute(
                "SELECT COUNT(*) as cnt FROM chat_message WHERE room_id = ? AND sender_username != ? AND read_at IS NULL",
                (room_dict["room_id"], username),
            ).fetchone()

            result.append({
                "room_id": room_dict["room_id"],
                "other_doctor_username": other_row["username"],
                "specialization": other_row["specialization"] or "General",
                "last_message": last_msg["content"] if last_msg else None,
                "last_message_type": last_msg["message_type"] if last_msg else None,
                "last_message_at": last_msg["created_at"] if last_msg else room_dict["last_message_at"],
                "unread_count": unread["cnt"] if unread else 0,
            })

        return jsonify({"status": "ok", "rooms": result}), 200
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /api/messages/room/<other_doctor_username> — get/create room between two doctors
# ---------------------------------------------------------------------------

@messaging_bp.get("/room/<other_doctor_username>")
@require_auth
@require_role("doctor")
def get_room(other_doctor_username: str):
    """Get or create a chat room between two doctors and return last 50 messages."""
    username = g.current_user["username"]

    if username == other_doctor_username:
        return jsonify({"status": "error", "message": "Cannot message yourself"}), 400

    my_id = _get_user_id(username)
    other_id = _get_user_id(other_doctor_username)

    if not my_id or not other_id:
        return jsonify({"status": "error", "message": "User not found"}), 404

    conn = get_db()
    try:
        # Check if room exists (either direction)
        room = conn.execute(
            "SELECT * FROM chat_room WHERE (doctor_id = ? AND patient_id = ?) OR (doctor_id = ? AND patient_id = ?)",
            (my_id, other_id, other_id, my_id),
        ).fetchone()

        if not room:
            cursor = conn.execute(
                "INSERT INTO chat_room (doctor_id, patient_id) VALUES (?, ?)",
                (my_id, other_id),
            )
            conn.commit()
            room_id = cursor.lastrowid
        else:
            room_id = room["room_id"]

        # Mark messages from other doctor as read
        conn.execute(
            "UPDATE chat_message SET read_at = datetime('now') WHERE room_id = ? AND sender_username = ? AND read_at IS NULL",
            (room_id, other_doctor_username),
        )
        conn.commit()

        # Get last 50 messages
        messages = conn.execute(
            """SELECT message_id, room_id, sender_username, content, message_type, file_url, read_at, created_at
               FROM chat_message WHERE room_id = ? ORDER BY created_at ASC LIMIT 50""",
            (room_id,),
        ).fetchall()

        return jsonify({
            "status": "ok",
            "room_id": room_id,
            "other_doctor_username": other_doctor_username,
            "messages": [dict(m) for m in messages],
        }), 200
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# POST /api/messages/send
# ---------------------------------------------------------------------------

@messaging_bp.post("/send")
@require_auth
def send_message():
    """Send a message in a chat room.

    Request JSON:
        {"room_id": int, "content": str}
    """
    data = request.get_json(silent=True) or {}
    room_id = data.get("room_id")
    content = data.get("content", "").strip()

    if not room_id or not content:
        return jsonify({"status": "error", "message": "room_id and content are required"}), 400

    username = g.current_user["username"]

    conn = get_db()
    try:
        # Verify user belongs to this room
        room = conn.execute("SELECT * FROM chat_room WHERE room_id = ?", (room_id,)).fetchone()
        if not room:
            return jsonify({"status": "error", "message": "Room not found"}), 404

        # Get usernames for both parties in this room
        party1_row = conn.execute("SELECT username FROM user WHERE user_id = ?", (room["doctor_id"],)).fetchone()
        party2_row = conn.execute("SELECT username FROM user WHERE user_id = ?", (room["patient_id"],)).fetchone()

        if not party1_row or not party2_row:
            return jsonify({"status": "error", "message": "Room users not found"}), 404

        party1_username = party1_row["username"]
        party2_username = party2_row["username"]

        if username not in (party1_username, party2_username):
            return jsonify({"status": "error", "message": "Not authorized"}), 403

        # Insert message
        cursor = conn.execute(
            "INSERT INTO chat_message (room_id, sender_username, content) VALUES (?, ?, ?)",
            (room_id, username, content),
        )
        conn.execute(
            "UPDATE chat_room SET last_message_at = datetime('now') WHERE room_id = ?",
            (room_id,),
        )
        conn.commit()

        message_id = cursor.lastrowid
        msg_row = conn.execute("SELECT * FROM chat_message WHERE message_id = ?", (message_id,)).fetchone()

        # Notify recipient
        recipient = party2_username if username == party1_username else party1_username
        try:
            notify_user(recipient, 'new_message', {
                'room_id': room_id,
                'message_id': message_id,
                'sender_username': username,
                'content': content,
                'created_at': msg_row["created_at"] if msg_row else None,
            })
        except Exception:
            pass

        return jsonify({"status": "ok", "message": dict(msg_row) if msg_row else {"message_id": message_id}}), 201
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /api/messages/unread-count
# ---------------------------------------------------------------------------

@messaging_bp.get("/unread-count")
@require_auth
def unread_count():
    """Return count of unread messages for current user."""
    username = g.current_user["username"]
    user_id = _get_user_id(username)

    conn = get_db()
    try:
        # Count unread messages in rooms where user is either party
        count = conn.execute(
            """SELECT COUNT(*) as cnt FROM chat_message cm
               JOIN chat_room cr ON cr.room_id = cm.room_id
               WHERE (cr.doctor_id = ? OR cr.patient_id = ?) AND cm.sender_username != ? AND cm.read_at IS NULL""",
            (user_id, user_id, username),
        ).fetchone()

        return jsonify({"status": "ok", "count": count["cnt"] if count else 0}), 200
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# POST /api/messages/mark-read
# ---------------------------------------------------------------------------

@messaging_bp.post("/mark-read")
@require_auth
def mark_read():
    """Mark all messages in a room from other party as read.

    Request JSON: {"room_id": int}
    """
    data = request.get_json(silent=True) or {}
    room_id = data.get("room_id")
    if not room_id:
        return jsonify({"status": "error", "message": "room_id is required"}), 400

    username = g.current_user["username"]

    conn = get_db()
    try:
        conn.execute(
            "UPDATE chat_message SET read_at = datetime('now') WHERE room_id = ? AND sender_username != ? AND read_at IS NULL",
            (room_id, username),
        )
        conn.commit()
        return jsonify({"status": "ok"}), 200
    finally:
        conn.close()
