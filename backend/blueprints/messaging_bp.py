"""
Messaging Blueprint — /api/messages

Real-time doctor-patient messaging endpoints.

Routes:
    GET  /api/messages/room/<patient_username>  → get/create room, return messages
    POST /api/messages/send                     → send a message
    GET  /api/messages/unread-count             → count unread messages
    GET  /api/messages/rooms                    → doctor's room list
    POST /api/messages/mark-read               → mark messages as read
"""

from flask import Blueprint, g, jsonify, request

from db import get_db, get_doctor_for_patient, get_patients_for_doctor
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
# GET /api/messages/room/<patient_username>
# ---------------------------------------------------------------------------

@messaging_bp.get("/room/<patient_username>")
@require_auth
def get_room(patient_username: str):
    """Get or create a chat room and return last 50 messages.

    For doctor: validates patient is assigned.
    For patient: patient_username must be self, room is with assigned doctor.
    """
    username = g.current_user["username"]
    role = g.current_user["role"]

    if role == "doctor":
        doctor_username = username
        # Validate patient is assigned
        assigned = get_patients_for_doctor(doctor_username)
        if patient_username not in assigned:
            return jsonify({"status": "error", "message": "Patient not assigned to you"}), 403
    elif role == "patient":
        # Patient can only access their own room
        if patient_username != username:
            return jsonify({"status": "error", "message": "Not authorized"}), 403
        doctor_username = get_doctor_for_patient(username)
        if not doctor_username:
            return jsonify({"status": "error", "message": "No doctor assigned"}), 404
    else:
        return jsonify({"status": "error", "message": "Not authorized"}), 403

    doctor_id = _get_user_id(doctor_username)
    patient_id = _get_user_id(patient_username)
    if not doctor_id or not patient_id:
        return jsonify({"status": "error", "message": "User not found"}), 404

    conn = get_db()
    try:
        # Get or create room
        room = conn.execute(
            "SELECT * FROM chat_room WHERE doctor_id = ? AND patient_id = ?",
            (doctor_id, patient_id),
        ).fetchone()

        if not room:
            cursor = conn.execute(
                "INSERT INTO chat_room (doctor_id, patient_id) VALUES (?, ?)",
                (doctor_id, patient_id),
            )
            conn.commit()
            room_id = cursor.lastrowid
        else:
            room_id = room["room_id"]

        # Mark messages from other party as read
        other_username = patient_username if role == "doctor" else doctor_username
        conn.execute(
            "UPDATE chat_message SET read_at = datetime('now') WHERE room_id = ? AND sender_username = ? AND read_at IS NULL",
            (room_id, other_username),
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
            "doctor_username": doctor_username,
            "patient_username": patient_username,
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

        # Get usernames for doctor and patient in this room
        doctor_row = conn.execute("SELECT username FROM user WHERE user_id = ?", (room["doctor_id"],)).fetchone()
        patient_row = conn.execute("SELECT username FROM user WHERE user_id = ?", (room["patient_id"],)).fetchone()

        if not doctor_row or not patient_row:
            return jsonify({"status": "error", "message": "Room users not found"}), 404

        doctor_username = doctor_row["username"]
        patient_username = patient_row["username"]

        if username not in (doctor_username, patient_username):
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
        recipient = patient_username if username == doctor_username else doctor_username
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
    role = g.current_user["role"]

    conn = get_db()
    try:
        if role == "doctor":
            # Count unread messages in rooms where user is doctor, sent by patients
            count = conn.execute(
                """SELECT COUNT(*) as cnt FROM chat_message cm
                   JOIN chat_room cr ON cr.room_id = cm.room_id
                   WHERE cr.doctor_id = ? AND cm.sender_username != ? AND cm.read_at IS NULL""",
                (user_id, username),
            ).fetchone()
        else:
            # Count unread messages in rooms where user is patient, sent by doctors
            count = conn.execute(
                """SELECT COUNT(*) as cnt FROM chat_message cm
                   JOIN chat_room cr ON cr.room_id = cm.room_id
                   WHERE cr.patient_id = ? AND cm.sender_username != ? AND cm.read_at IS NULL""",
                (user_id, username),
            ).fetchone()

        return jsonify({"status": "ok", "count": count["cnt"] if count else 0}), 200
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /api/messages/rooms — doctor's room list
# ---------------------------------------------------------------------------

@messaging_bp.get("/rooms")
@require_auth
@require_role("doctor")
def list_rooms():
    """Return all chat rooms for this doctor with last message and unread count."""
    username = g.current_user["username"]
    user_id = _get_user_id(username)

    conn = get_db()
    try:
        rooms = conn.execute(
            """SELECT cr.room_id, cr.last_message_at, u.username as patient_username
               FROM chat_room cr
               JOIN user u ON u.user_id = cr.patient_id
               WHERE cr.doctor_id = ?
               ORDER BY cr.last_message_at DESC""",
            (user_id,),
        ).fetchall()

        result = []
        for room in rooms:
            room_dict = dict(room)
            # Get last message
            last_msg = conn.execute(
                "SELECT content, created_at FROM chat_message WHERE room_id = ? ORDER BY created_at DESC LIMIT 1",
                (room_dict["room_id"],),
            ).fetchone()
            # Get unread count
            unread = conn.execute(
                "SELECT COUNT(*) as cnt FROM chat_message WHERE room_id = ? AND sender_username != ? AND read_at IS NULL",
                (room_dict["room_id"], username),
            ).fetchone()

            room_dict["last_message"] = last_msg["content"] if last_msg else None
            room_dict["last_message_at"] = last_msg["created_at"] if last_msg else room_dict["last_message_at"]
            room_dict["unread_count"] = unread["cnt"] if unread else 0
            result.append(room_dict)

        return jsonify({"status": "ok", "rooms": result}), 200
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
