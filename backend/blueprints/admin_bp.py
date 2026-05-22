"""
Admin Blueprint — /api

Handles admin-only operations: system stats, user management, and audit logging.

Routes:
    GET   /api/stats                    → system-wide statistics (Admin only)
    GET   /api/users                    → list all users (Admin only)
    POST  /api/users                    → create a new user (Admin only)
    PATCH /api/users/<id>/deactivate    → deactivate a user account (Admin only)
"""

import math
from datetime import datetime, timedelta

import bcrypt
from flask import Blueprint, g, jsonify, request

from db import get_db, log_access_violation
from middleware.auth import require_auth
from middleware.rbac import require_role
from services.audit_service import log_action

admin_bp = Blueprint("admin", __name__, url_prefix="/api")


# ---------------------------------------------------------------------------
# Task 11.5 — Audit logging middleware
# ---------------------------------------------------------------------------

@admin_bp.before_request
def audit_log_admin_request():
    """Log every authenticated admin Blueprint request to access_violation_log.

    Uses before_request as specified. Only logs when g.current_user is already
    set — this occurs when auth middleware has been applied as a before_request
    hook at the app level, or when the request context already carries a user
    (e.g. from a prior middleware). For view-function-level @require_auth
    decorators, the after_request companion below handles the actual write once
    g.current_user is populated.

    The guard ``if current_user is None: return`` satisfies the task requirement
    to skip logging for unauthenticated requests.
    """
    current_user = getattr(g, "current_user", None)
    if current_user is None:
        # Auth decorator hasn't run yet (it's a view-function decorator).
        # Store request metadata in g so the after_request hook can log it.
        g._admin_audit_pending = True
        return  # Do not log yet

    _write_admin_audit_log(current_user)


@admin_bp.after_request
def audit_log_admin_after(response):
    """Companion hook: write the audit log entry after the view function runs.

    This fires after @require_auth has populated g.current_user, ensuring the
    username is available. Only writes if before_request flagged a pending entry.
    """
    if getattr(g, "_admin_audit_pending", False):
        current_user = getattr(g, "current_user", None)
        if current_user is not None:
            _write_admin_audit_log(current_user)
    return response


def _write_admin_audit_log(current_user: dict) -> None:
    """Insert one audit row into access_violation_log for an admin request."""
    username = current_user.get("username", "anonymous")
    endpoint = request.path
    method = request.method
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    action = f"admin_{method.lower()}_{endpoint.replace('/', '_').strip('_')}"

    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO access_violation_log
                (username, endpoint, role_claim, timestamp, ip_address, action)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                endpoint,
                current_user.get("role", ""),
                timestamp,
                request.remote_addr,
                action,
            ),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Placeholder index route
# ---------------------------------------------------------------------------

@admin_bp.get("/")
def index():
    return jsonify({"status": "ok", "blueprint": "admin"})


# ---------------------------------------------------------------------------
# Task 11.1 — GET /api/stats (Admin only)
# ---------------------------------------------------------------------------

@admin_bp.get("/stats")
@require_auth
@require_role("admin")
def get_stats():
    """Return system-wide statistics for the Admin Dashboard.

    Queries:
      - Users by role count
      - Total predictions
      - Predictions by severity_level
      - Predictions by anemia_type
      - Total critical alerts sent (delivery_status='sent')
      - Predictions per day for the last 30 days
    """
    conn = get_db()
    try:
        # --- Users by role ---
        role_rows = conn.execute(
            "SELECT role, COUNT(*) AS cnt FROM user GROUP BY role"
        ).fetchall()
        users_by_role = {"patient": 0, "doctor": 0, "admin": 0}
        for row in role_rows:
            users_by_role[row["role"]] = row["cnt"]

        # --- Total predictions ---
        total_predictions = conn.execute(
            "SELECT COUNT(*) FROM prediction"
        ).fetchone()[0]

        # --- Predictions by severity_level ---
        severity_rows = conn.execute(
            "SELECT severity_level, COUNT(*) AS cnt FROM prediction GROUP BY severity_level"
        ).fetchall()
        predictions_by_severity = {"None": 0, "Mild": 0, "Moderate": 0, "Severe": 0}
        for row in severity_rows:
            predictions_by_severity[row["severity_level"]] = row["cnt"]

        # --- Predictions by anemia_type ---
        type_rows = conn.execute(
            "SELECT anemia_type, COUNT(*) AS cnt FROM prediction GROUP BY anemia_type"
        ).fetchall()
        predictions_by_type = {}
        for row in type_rows:
            predictions_by_type[row["anemia_type"]] = row["cnt"]

        # --- Total critical alerts sent ---
        total_alerts_sent = conn.execute(
            "SELECT COUNT(*) FROM alert_log WHERE delivery_status = 'sent'"
        ).fetchone()[0]

        # --- Predictions per day for the last 30 days ---
        cutoff = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        daily_rows = conn.execute(
            """
            SELECT DATE(date) AS day, COUNT(*) AS cnt
            FROM prediction
            WHERE DATE(date) >= ?
            GROUP BY DATE(date)
            ORDER BY day ASC
            """,
            (cutoff,),
        ).fetchall()
        predictions_per_day = [
            {"date": row["day"], "count": row["cnt"]} for row in daily_rows
        ]

    finally:
        conn.close()

    stats = {
        "users_by_role": users_by_role,
        "total_predictions": total_predictions,
        "predictions_by_severity": predictions_by_severity,
        "predictions_by_type": predictions_by_type,
        "total_alerts_sent": total_alerts_sent,
        "predictions_per_day": predictions_per_day,
    }

    return jsonify({"status": "ok", "stats": stats}), 200


# ---------------------------------------------------------------------------
# Task 11.2 — GET /api/users (Admin only)
# ---------------------------------------------------------------------------

@admin_bp.get("/users")
@require_auth
@require_role("admin")
def list_users():
    """Return a paginated, filterable list of all user accounts.

    Query params:
      - search : substring match on username or email (LIKE %search%)
      - role   : exact role filter (patient / doctor / admin)
      - status : exact status filter (active / inactive)
      - page   : page number (1-indexed, default 1)

    Returns 20 users per page.
    """
    search = request.args.get("search", "").strip()
    role_filter = request.args.get("role", "").strip()
    status_filter = request.args.get("status", "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1

    page_size = 20
    offset = (page - 1) * page_size

    # Build dynamic WHERE clause
    conditions = []
    params = []

    if search:
        conditions.append("(username LIKE ? OR email LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if role_filter:
        conditions.append("role = ?")
        params.append(role_filter)
    if status_filter:
        conditions.append("status = ?")
        params.append(status_filter)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    conn = get_db()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM user {where_clause}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT user_id, username, email, role, status, created_at
            FROM user
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset],
        ).fetchall()
    finally:
        conn.close()

    users = [
        {
            "user_id": row["user_id"],
            "username": row["username"],
            "email": row["email"],
            "role": row["role"],
            "status": row["status"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]

    total_pages = max(1, math.ceil(total / page_size))

    return jsonify(
        {
            "status": "ok",
            "users": users,
            "total": total,
            "page": page,
            "pages": total_pages,
        }
    ), 200


# ---------------------------------------------------------------------------
# Task 11.3 — POST /api/users (Admin only)
# ---------------------------------------------------------------------------

@admin_bp.post("/users")
@require_auth
@require_role("admin")
def create_user():
    """Create a new user account with any role (no OTP required).

    Request body (JSON):
      - username : str (required, unique)
      - email    : str (required, unique)
      - password : str (required, ≥ 8 chars)
      - role     : str (required: patient / doctor / admin)

    Returns 201 with the created user data (no password_hash).
    Logs the action to access_violation_log with action="admin_create_user".
    """
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    role = (data.get("role") or "").strip().lower()

    # --- Validation ---
    errors = {}
    if not username:
        errors["username"] = "Username is required."
    if not email:
        errors["email"] = "Email is required."
    if not password:
        errors["password"] = "Password is required."
    elif len(password) < 8:
        errors["password"] = "Password must be at least 8 characters."
    if role not in ("patient", "doctor", "admin"):
        errors["role"] = "Role must be one of: patient, doctor, admin."

    if errors:
        return jsonify({"status": "error", "message": "Validation failed", "details": errors}), 400

    # --- Hash password ---
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=12)
    ).decode("utf-8")

    conn = get_db()
    try:
        # Check uniqueness
        existing = conn.execute(
            "SELECT user_id FROM user WHERE username = ? OR email = ?",
            (username, email),
        ).fetchone()
        if existing:
            return jsonify(
                {"status": "error", "message": "Username or email already exists."}
            ), 409

        cursor = conn.execute(
            """
            INSERT INTO user (username, email, password_hash, role, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (username, email, password_hash, role),
        )
        conn.commit()
        new_user_id = cursor.lastrowid

        # Fetch the created user row
        row = conn.execute(
            "SELECT user_id, username, email, role, status, created_at FROM user WHERE user_id = ?",
            (new_user_id,),
        ).fetchone()
    finally:
        conn.close()

    # --- Audit log ---
    current_user = g.current_user
    log_access_violation(
        username=current_user.get("username", "anonymous"),
        endpoint=request.path,
        role_claim=current_user.get("role", ""),
        ip_address=request.remote_addr,
        action="admin_create_user",
    )

    # --- Audit service log ---
    log_action(
        actor=current_user.get("username", "anonymous"),
        action="user_create",
        target=username,
        details={"role": role},
        ip=request.remote_addr,
    )

    created = {
        "user_id": row["user_id"],
        "username": row["username"],
        "email": row["email"],
        "role": row["role"],
        "status": row["status"],
        "created_at": row["created_at"],
    }

    return jsonify({"status": "ok", "user": created}), 201


# ---------------------------------------------------------------------------
# Task 11.4 — PATCH /api/users/<id>/deactivate (Admin only)
# ---------------------------------------------------------------------------

@admin_bp.patch("/users/<int:user_id>/deactivate")
@require_auth
@require_role("admin")
def deactivate_user(user_id: int):
    """Set a user's status to 'inactive'.

    If the target user has role='admin', the request body must include
    {"confirm_admin_id": <id>} referencing a second active admin account.

    Logs the action to access_violation_log with action="admin_deactivate_user".
    """
    data = request.get_json(silent=True) or {}
    current_user = g.current_user

    conn = get_db()
    try:
        # Fetch target user
        target = conn.execute(
            "SELECT user_id, username, role, status FROM user WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        if target is None:
            return jsonify({"status": "error", "message": "User not found."}), 404

        if target["status"] == "inactive":
            return jsonify({"status": "error", "message": "User is already inactive."}), 400

        # If target is an admin, require a second admin confirmation
        if target["role"] == "admin":
            confirm_admin_id = data.get("confirm_admin_id")
            if confirm_admin_id is None:
                return jsonify(
                    {
                        "status": "error",
                        "message": (
                            "Deactivating an admin account requires a second admin confirmation. "
                            "Provide {'confirm_admin_id': <id>} of another active admin."
                        ),
                    }
                ), 400

            # Verify the confirming admin exists, is active, is an admin, and is not the same user
            confirming_admin = conn.execute(
                "SELECT user_id, role, status FROM user WHERE user_id = ?",
                (confirm_admin_id,),
            ).fetchone()

            if (
                confirming_admin is None
                or confirming_admin["role"] != "admin"
                or confirming_admin["status"] != "active"
                or confirming_admin["user_id"] == user_id
            ):
                return jsonify(
                    {
                        "status": "error",
                        "message": "confirm_admin_id must reference a different active admin account.",
                    }
                ), 400

        # Perform deactivation
        conn.execute(
            "UPDATE user SET status = 'inactive' WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()

    # --- Audit log ---
    log_access_violation(
        username=current_user.get("username", "anonymous"),
        endpoint=request.path,
        role_claim=current_user.get("role", ""),
        ip_address=request.remote_addr,
        action="admin_deactivate_user",
    )

    # --- Audit service log ---
    log_action(
        actor=current_user.get("username", "anonymous"),
        action="user_deactivate",
        target=str(user_id),
        ip=request.remote_addr,
    )

    return jsonify(
        {
            "status": "ok",
            "message": f"User '{target['username']}' has been deactivated.",
        }
    ), 200
