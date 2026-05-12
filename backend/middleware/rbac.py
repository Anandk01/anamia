"""
middleware/rbac.py — Role-Based Access Control decorator.

Provides:
  require_role(*roles) : decorator factory that checks g.current_user["role"]
                         against the allowed roles list.  On failure it logs
                         the violation and returns 403.
"""

from functools import wraps

from flask import g, jsonify, request

from db import log_access_violation

# The three recognised roles (Requirement 21.1)
VALID_ROLES = {"patient", "doctor", "admin"}


def require_role(*roles):
    """Decorator factory: restrict endpoint to users whose role is in *roles*.

    Usage::

        @auth_bp.post("/some-endpoint")
        @require_auth
        @require_role("admin")
        def admin_only():
            ...

    If the authenticated user's role is not in *roles*:
      - Inserts a row into ``access_violation_log``.
      - Returns ``{"error": "Insufficient permissions"}`` with HTTP 403.
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            current_user = getattr(g, "current_user", None)
            if current_user is None:
                # require_auth was not applied — treat as unauthenticated
                return (
                    jsonify({"status": "error", "message": "Authentication required"}),
                    401,
                )

            user_role = current_user.get("role", "")

            if user_role not in roles:
                # Log the access violation
                log_access_violation(
                    username=current_user.get("username", "anonymous"),
                    endpoint=request.path,
                    role_claim=user_role,
                    ip_address=request.remote_addr,
                    action=f"Attempted {request.method} {request.path} — required role(s): {roles}",
                )
                return (
                    jsonify({"error": "Insufficient permissions"}),
                    403,
                )

            return f(*args, **kwargs)

        return decorated

    return decorator
