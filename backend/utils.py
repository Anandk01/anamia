"""
utils.py — Real-time notification helpers.

Provides notify_user() and notify_admin() for emitting SocketIO events
from any blueprint without circular imports.
"""


def notify_user(username: str, event: str, data: dict):
    """Send a real-time event to a specific user's room."""
    try:
        from flask import current_app
        socketio = current_app.config.get('SOCKETIO')
        if socketio:
            socketio.emit(event, data, to=f"user_{username}")
    except Exception:
        pass


def notify_admin(event: str, data: dict):
    """Send a real-time event to all admins."""
    try:
        from flask import current_app
        socketio = current_app.config.get('SOCKETIO')
        if socketio:
            socketio.emit(event, data, to='admin_room')
    except Exception:
        pass
