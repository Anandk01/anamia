"""
middleware/auth.py — JWT authentication decorator.

Provides:
  require_auth  : decorator that validates the Bearer JWT, checks the
                  jwt_blacklist table, and attaches g.current_user to the
                  Flask request context.
"""

import os
from functools import wraps

import jwt
from flask import g, jsonify, request

from db import get_db

# JWT secret — read from environment; fall back to dev default.
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"


def require_auth(f):
    """Decorator: validate JWT and populate g.current_user.

    Reads the ``Authorization: Bearer <token>`` header, decodes the JWT,
    verifies it has not expired, checks it has not been blacklisted, and
    stores the decoded payload as ``g.current_user``.

    Returns 401 JSON on any failure.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return (
                jsonify({"status": "error", "message": "Missing or invalid Authorization header"}),
                401,
            )

        token = auth_header[len("Bearer "):]

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            return jsonify({"status": "error", "message": "Token has expired"}), 401
        except jwt.InvalidTokenError as exc:
            return jsonify({"status": "error", "message": f"Invalid token: {exc}"}), 401

        # Check jwt_blacklist
        jti = payload.get("jti")
        if jti:
            conn = get_db()
            try:
                row = conn.execute(
                    "SELECT jti FROM jwt_blacklist WHERE jti = ?", (jti,)
                ).fetchone()
            finally:
                conn.close()

            if row:
                return jsonify({"status": "error", "message": "Token has been revoked"}), 401

        # Attach user info to Flask's request context
        g.current_user = {
            "username": payload.get("username"),
            "role": payload.get("role"),
            "email": payload.get("email"),
            "jti": jti,
            "exp": payload.get("exp"),
        }

        return f(*args, **kwargs)

    return decorated
