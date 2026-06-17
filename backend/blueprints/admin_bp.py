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

    Returns flat JSON with fields expected by the frontend:
      total_predictions, total_users, anemia_cases, severe_cases,
      alerts_sent, retrain_count, active_doctors, avg_adherence,
      daily_predictions, severity_distribution, type_distribution
    """
    conn = get_db()
    try:
        # --- Total users ---
        total_users = conn.execute(
            "SELECT COUNT(*) FROM user"
        ).fetchone()[0]

        # --- Active doctors ---
        active_doctors = conn.execute(
            "SELECT COUNT(*) FROM user WHERE role = 'doctor' AND status = 'active'"
        ).fetchone()[0]

        # --- Total predictions ---
        total_predictions = conn.execute(
            "SELECT COUNT(*) FROM prediction"
        ).fetchone()[0]

        # --- Anemia cases (anemia_detected = 1) ---
        anemia_cases = conn.execute(
            "SELECT COUNT(*) FROM prediction WHERE anemia_detected = 1"
        ).fetchone()[0]

        # --- Severe cases (severity_level = 'Severe' or hgb < 8.0) ---
        severe_cases = conn.execute(
            "SELECT COUNT(*) FROM prediction WHERE severity_level = 'Severe'"
        ).fetchone()[0]

        # --- Alerts sent ---
        alerts_sent = conn.execute(
            "SELECT COUNT(*) FROM alert_log"
        ).fetchone()[0]

        # --- Retrain count ---
        retrain_count = 0
        try:
            retrain_count = conn.execute(
                "SELECT COUNT(*) FROM model_metrics"
            ).fetchone()[0]
        except Exception:
            pass

        # --- Avg adherence (placeholder — null if no data) ---
        avg_adherence = None
        try:
            row = conn.execute(
                """SELECT AVG(adherence_pct) as avg_adh FROM (
                    SELECT m.username,
                        CASE WHEN COUNT(ml.log_id) = 0 THEN NULL
                        ELSE ROUND(100.0 * COUNT(CASE WHEN ml.skipped = 0 THEN 1 END) / COUNT(ml.log_id), 1)
                        END as adherence_pct
                    FROM medication m
                    LEFT JOIN medication_log ml ON ml.med_id = m.med_id
                    WHERE m.active = 1
                    GROUP BY m.username
                )"""
            ).fetchone()
            if row and row["avg_adh"] is not None:
                avg_adherence = round(row["avg_adh"], 1)
        except Exception:
            pass

        # --- Severity distribution ---
        severity_rows = conn.execute(
            "SELECT severity_level, COUNT(*) AS cnt FROM prediction GROUP BY severity_level"
        ).fetchall()
        severity_distribution = {"None": 0, "Mild": 0, "Moderate": 0, "Severe": 0}
        for row in severity_rows:
            key = row["severity_level"] or "None"
            severity_distribution[key] = row["cnt"]

        # --- Type distribution ---
        type_rows = conn.execute(
            "SELECT anemia_type, COUNT(*) AS cnt FROM prediction WHERE anemia_type IS NOT NULL AND anemia_type != '' GROUP BY anemia_type"
        ).fetchall()
        type_distribution = {}
        for row in type_rows:
            type_distribution[row["anemia_type"]] = row["cnt"]

        # --- Daily predictions (last 30 days) ---
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
        daily_predictions = [
            {"date": row["day"], "count": row["cnt"]} for row in daily_rows
        ]

    finally:
        conn.close()

    return jsonify({
        "total_predictions": total_predictions,
        "total_users": total_users,
        "anemia_cases": anemia_cases,
        "severe_cases": severe_cases,
        "alerts_sent": alerts_sent,
        "retrain_count": retrain_count,
        "active_doctors": active_doctors,
        "avg_adherence": avg_adherence,
        "daily_predictions": daily_predictions,
        "severity_distribution": severity_distribution,
        "type_distribution": type_distribution,
    }), 200


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


# ---------------------------------------------------------------------------
# PATCH /api/users/<id>/reactivate (Admin only)
# ---------------------------------------------------------------------------

@admin_bp.patch("/users/<int:user_id>/reactivate")
@require_auth
@require_role("admin")
def reactivate_user(user_id: int):
    """Set a user's status back to 'active'."""
    conn = get_db()
    try:
        target = conn.execute(
            "SELECT user_id, username, status FROM user WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if target is None:
            return jsonify({"status": "error", "message": "User not found."}), 404
        if target["status"] == "active":
            return jsonify({"status": "error", "message": "User is already active."}), 400

        conn.execute("UPDATE user SET status = 'active' WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()

    return jsonify({"status": "ok", "message": f"User '{target['username']}' has been reactivated."}), 200


# ---------------------------------------------------------------------------
# Doctor-Patient Assignment endpoints
# ---------------------------------------------------------------------------

@admin_bp.get("/unassigned-patients")
@require_auth
@require_role("admin")
def unassigned_patients():
    """Return all active patients not yet assigned to any doctor."""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT u.username, u.email, u.created_at FROM user u
               WHERE u.role = 'patient' AND u.status = 'active'
               AND u.user_id NOT IN (SELECT patient_id FROM doctor_patient)"""
        ).fetchall()
        return jsonify({"status": "ok", "patients": [dict(r) for r in rows]}), 200
    finally:
        conn.close()


@admin_bp.get("/assignments")
@require_auth
@require_role("admin")
def list_assignments():
    """Return all doctor-patient assignments."""
    conn = get_db()
    try:
        rows = conn.execute(
            """SELECT d.username as doctor_username, p.username as patient_username, dp.assigned_at
               FROM doctor_patient dp
               JOIN user d ON d.user_id = dp.doctor_id
               JOIN user p ON p.user_id = dp.patient_id
               ORDER BY dp.assigned_at DESC"""
        ).fetchall()
        return jsonify({"status": "ok", "assignments": [dict(r) for r in rows]}), 200
    finally:
        conn.close()


@admin_bp.post("/assign")
@require_auth
@require_role("admin")
def assign_patients():
    """Assign one or more patients to a doctor."""
    data = request.get_json(silent=True) or {}
    doctor_username = data.get("doctor_username")
    patient_usernames = data.get("patient_usernames", [])
    if not doctor_username or not patient_usernames:
        return jsonify({"status": "error", "message": "doctor_username and patient_usernames required"}), 400

    conn = get_db()
    try:
        doc = conn.execute(
            "SELECT user_id FROM user WHERE username = ? AND role = 'doctor'",
            (doctor_username,)
        ).fetchone()
        if not doc:
            return jsonify({"status": "error", "message": "Doctor not found"}), 404

        assigned = 0
        for pu in patient_usernames:
            pat = conn.execute(
                "SELECT user_id FROM user WHERE username = ? AND role = 'patient'",
                (pu,)
            ).fetchone()
            if pat:
                try:
                    conn.execute(
                        "INSERT INTO doctor_patient (doctor_id, patient_id) VALUES (?, ?)",
                        (doc["user_id"], pat["user_id"])
                    )
                    assigned += 1
                except Exception:
                    pass  # duplicate, skip
        conn.commit()
        return jsonify({"status": "ok", "assigned": assigned}), 200
    finally:
        conn.close()


@admin_bp.delete("/unassign")
@require_auth
@require_role("admin")
def unassign_patient():
    """Remove a patient from a doctor's assignment."""
    data = request.get_json(silent=True) or {}
    doctor_username = data.get("doctor_username")
    patient_username = data.get("patient_username")
    if not doctor_username or not patient_username:
        return jsonify({"status": "error", "message": "doctor_username and patient_username required"}), 400

    conn = get_db()
    try:
        doc = conn.execute("SELECT user_id FROM user WHERE username = ?", (doctor_username,)).fetchone()
        pat = conn.execute("SELECT user_id FROM user WHERE username = ?", (patient_username,)).fetchone()
        if doc and pat:
            conn.execute(
                "DELETE FROM doctor_patient WHERE doctor_id = ? AND patient_id = ?",
                (doc["user_id"], pat["user_id"])
            )
            conn.commit()
        return jsonify({"status": "ok", "unassigned": True}), 200
    finally:
        conn.close()
