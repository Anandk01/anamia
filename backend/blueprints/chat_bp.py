"""
Chat Blueprint — /api/chat

Gemini-powered RAG chatbot for anemia Q&A + real-time messaging rooms.
Knowledge sourced from WHO and NHLBI fact sheets.

Routes:
    GET  /api/chat/                      → health check
    POST /api/chat/message               → process a user message with Gemini RAG
    GET  /api/chat/rooms                 → list user's chat rooms
    POST /api/chat/rooms                 → create a chat room
    GET  /api/chat/rooms/<id>/messages   → paginated message history
"""

import logging

from flask import Blueprint, g, jsonify, request

from db import get_db
from middleware.auth import require_auth
from middleware.rbac import require_role

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')


@chat_bp.get('/')
def index():
    return jsonify({"status": "ok", "blueprint": "chat", "engine": "gemini-rag"})


@chat_bp.post('/message')
@require_auth
def chat_message():
    """
    Process a user chat message using Gemini RAG.

    Request body (JSON):
        {
            "message":    str  — the user's text query (required)
            "session_id": str  — unique session identifier (required)
        }

    Response (200 OK):
        {
            "status":     "ok",
            "response":   str,
            "intent":     str,
            "session_id": str,
            "sources":    list[str]
        }
    """
    data = request.get_json(silent=True) or {}

    message = (data.get("message") or "").strip()
    session_id = (data.get("session_id") or "").strip()

    if not message:
        return jsonify({"status": "error", "message": "message must be a non-empty string"}), 400
    if not session_id:
        return jsonify({"status": "error", "message": "session_id must be a non-empty string"}), 400

    # Use Gemini RAG chatbot
    try:
        from services.gemini_chatbot_service import chat_with_gemini
        result = chat_with_gemini(message, session_id)
    except Exception as exc:
        logger.error("Gemini chatbot error: %s", exc)
        # Fallback to keyword chatbot if Gemini fails
        try:
            from services.chatbot_service import classify_and_respond, get_or_create_session
            result = classify_and_respond(message, session_id)
            session = get_or_create_session(session_id)
            session.add_exchange(message, result["response"])
            result["sources"] = []
        except Exception as fallback_exc:
            logger.error("Fallback chatbot also failed: %s", fallback_exc)
            result = {
                "response": "I'm having trouble right now. Please try again in a moment.",
                "intent": "error",
                "sources": [],
            }

    return jsonify({
        "status": "ok",
        "response": result["response"],
        "intent": result.get("intent", "general"),
        "session_id": session_id,
        "sources": result.get("sources", []),
    }), 200


# ---------------------------------------------------------------------------
# Chat Room endpoints (real-time messaging)
# ---------------------------------------------------------------------------

@chat_bp.get('/rooms')
@require_auth
def list_rooms():
    """List chat rooms for the current user."""
    username = g.current_user["username"]
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT user_id FROM user WHERE username = ?", (username,)
        ).fetchone()
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 400
        user_id = user["user_id"]

        rows = conn.execute(
            """SELECT cr.*, 
                      d.username as doctor_username,
                      p.username as patient_username
               FROM chat_room cr
               JOIN user d ON d.user_id = cr.doctor_id
               JOIN user p ON p.user_id = cr.patient_id
               WHERE cr.doctor_id = ? OR cr.patient_id = ?
               ORDER BY cr.last_message_at DESC""",
            (user_id, user_id),
        ).fetchall()
        return jsonify({"status": "ok", "rooms": [dict(r) for r in rows]}), 200
    finally:
        conn.close()


@chat_bp.post('/rooms')
@require_auth
def create_room():
    """Create a chat room between doctor and patient."""
    data = request.get_json(silent=True) or {}
    doctor_id = data.get("doctor_id")
    patient_id = data.get("patient_id")

    if not doctor_id or not patient_id:
        return jsonify({"status": "error", "message": "doctor_id and patient_id required"}), 400

    conn = get_db()
    try:
        # Check if room already exists
        existing = conn.execute(
            "SELECT * FROM chat_room WHERE doctor_id = ? AND patient_id = ?",
            (doctor_id, patient_id),
        ).fetchone()
        if existing:
            return jsonify({"status": "ok", "room": dict(existing)}), 200

        cursor = conn.execute(
            "INSERT INTO chat_room (doctor_id, patient_id) VALUES (?, ?)",
            (doctor_id, patient_id),
        )
        conn.commit()
        room = conn.execute(
            "SELECT * FROM chat_room WHERE room_id = ?", (cursor.lastrowid,)
        ).fetchone()
        return jsonify({"status": "ok", "room": dict(room)}), 201
    finally:
        conn.close()


@chat_bp.get('/rooms/<int:room_id>/messages')
@require_auth
def get_room_messages(room_id):
    """Get paginated message history for a room."""
    page = int(request.args.get("page", 1))
    per_page = 50
    offset = (page - 1) * per_page

    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT * FROM chat_message WHERE room_id = ?
               ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (room_id, per_page, offset),
        ).fetchall()
        messages = [dict(r) for r in rows]
        messages.reverse()  # Return in chronological order
        return jsonify({"status": "ok", "messages": messages, "page": page}), 200
    finally:
        conn.close()
