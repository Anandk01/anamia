"""
websocket_service.py — SocketIO event handlers for real-time messaging.

Provides WebSocket events for:
  - connect/disconnect with JWT auth
  - join_personal_room (global room per user)
  - join_room / send_message / message_read
  - typing_start / typing_stop
"""

import logging
import jwt
import os

from flask import request
from db import get_db

logger = logging.getLogger(__name__)

# Will be initialized by app.py
socketio = None

JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key")


def init_socketio(sio):
    """Register event handlers on the SocketIO instance."""
    global socketio
    socketio = sio

    @sio.on('connect')
    def handle_connect(auth=None):
        """Authenticate user via JWT token passed in query params."""
        token = request.args.get('token')
        if not token:
            logger.warning("WebSocket connection rejected: no token")
            return False
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            # Store user info in flask_socketio session (not request.environ)
            from flask import session
            session['ws_user'] = data.get('username') or data.get('sub')
            session['ws_role'] = data.get('role')
            logger.info("Client connected: %s", session.get('ws_user'))
        except Exception as exc:
            logger.warning("WebSocket connection rejected: %s", exc)
            return False

    @sio.on('join_personal_room')
    def handle_join_personal_room(data):
        """Join user's personal room and optionally admin_room."""
        from flask_socketio import join_room
        username = data.get('username')
        role = data.get('role')
        if username:
            join_room(f"user_{username}")
            logger.info("User %s joined personal room", username)
        if role == 'admin':
            join_room('admin_room')
            logger.info("Admin %s joined admin_room", username)

    @sio.on('disconnect')
    def handle_disconnect():
        logger.info("Client disconnected")

    @sio.on('join_room')
    def handle_join_room(data):
        """Join a chat room. data = {"room_id": int}"""
        from flask_socketio import join_room
        room_id = data.get('room_id')
        if room_id:
            join_room(f"room_{room_id}")

    @sio.on('send_message')
    def handle_send_message(data):
        """Send message to room. data = {"room_id": int, "content": str, "sender": str}"""
        from flask_socketio import emit
        room_id = data.get('room_id')
        content = data.get('content', '')
        sender = data.get('sender', '')

        if not room_id or not content:
            return

        # Store in DB
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO chat_message (room_id, sender_username, content) VALUES (?, ?, ?)",
                (room_id, sender, content),
            )
            conn.execute(
                "UPDATE chat_room SET last_message_at = datetime('now') WHERE room_id = ?",
                (room_id,),
            )
            conn.commit()
        finally:
            conn.close()

        emit('new_message', {
            'room_id': room_id,
            'sender': sender,
            'content': content,
        }, room=f"room_{room_id}")

    @sio.on('message_read')
    def handle_message_read(data):
        """Mark messages as read. data = {"room_id": int, "username": str}"""
        from flask_socketio import emit
        room_id = data.get('room_id')
        username = data.get('username')

        if not room_id or not username:
            return

        conn = get_db()
        try:
            conn.execute(
                """UPDATE chat_message SET read_at = datetime('now')
                   WHERE room_id = ? AND sender_username != ? AND read_at IS NULL""",
                (room_id, username),
            )
            conn.commit()
        finally:
            conn.close()

        emit('messages_read', {'room_id': room_id, 'reader': username}, room=f"room_{room_id}")

    @sio.on('typing_start')
    def handle_typing_start(data):
        """Broadcast typing indicator. data = {"room_id": int, "username": str}"""
        from flask_socketio import emit
        room_id = data.get('room_id')
        username = data.get('username')
        if room_id:
            emit('user_typing', {'username': username}, room=f"room_{room_id}", include_self=False)

    @sio.on('typing_stop')
    def handle_typing_stop(data):
        """Stop typing indicator. data = {"room_id": int, "username": str}"""
        from flask_socketio import emit
        room_id = data.get('room_id')
        username = data.get('username')
        if room_id:
            emit('user_stopped_typing', {'username': username}, room=f"room_{room_id}", include_self=False)
