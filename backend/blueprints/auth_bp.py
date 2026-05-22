"""
Auth Blueprint — /auth

Handles user registration (OTP flow), login (JWT issuance),
logout (token blacklist), and password reset.

Routes:
    POST /auth/register              → validate input, send OTP
    POST /auth/verify-register-otp   → verify OTP, create account, return JWT
    POST /auth/login                 → validate credentials, return JWT
    POST /auth/logout                → blacklist JWT jti
    POST /auth/forgot-password       → send password-reset OTP
    POST /auth/verify-reset-otp      → verify OTP, update password hash
"""

import hashlib
import os
import secrets
import smtplib
import uuid
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import bcrypt
import jwt
from flask import Blueprint, current_app, g, jsonify, request

from db import get_db
from middleware.auth import JWT_ALGORITHM, JWT_SECRET, require_auth
from services.audit_service import log_action

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# ---------------------------------------------------------------------------
# Module-level in-memory stores
# ---------------------------------------------------------------------------

# { email: {"otp_hash": str, "expires_at": datetime} }
_otp_store: dict = {}

# { email: {"username": str, "password": str} }
_pending_registrations: dict = {}

# { email: {"otp_hash": str, "expires_at": datetime} }
_reset_otp_store: dict = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _generate_otp() -> str:
    """Return a zero-padded 6-digit OTP string."""
    return str(secrets.randbelow(1_000_000)).zfill(6)


def _hash_otp(otp: str) -> str:
    """Return the SHA-256 hex digest of *otp*."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _send_email(to_address: str, subject: str, body_html: str) -> None:
    """Send an HTML email via SMTP (STARTTLS).

    Raises smtplib.SMTPException (or subclass) on failure.
    """
    from_address = current_app.config["EMAIL_ADDRESS"]
    password = current_app.config["EMAIL_PASSWORD"]
    smtp_server = current_app.config["SMTP_SERVER"]
    smtp_port = current_app.config["SMTP_PORT"]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address
    msg.attach(MIMEText(body_html, "html"))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(from_address, password)
        server.sendmail(from_address, to_address, msg.as_string())


def _issue_jwt(user_row) -> str:
    """Issue a 24-hour JWT for *user_row* (sqlite3.Row or dict-like)."""
    now = datetime.utcnow()
    payload = {
        "sub": user_row["username"],
        "username": user_row["username"],
        "role": user_row["role"],
        "email": user_row["email"],
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(hours=24),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _bcrypt_hash(password: str) -> str:
    """Return a bcrypt hash (cost=12) of *password* as a UTF-8 string."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def _bcrypt_check(password: str, hashed: str) -> bool:
    """Return True if *password* matches *hashed*."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@auth_bp.get("/")
def index():
    return jsonify({"status": "ok", "blueprint": "auth"})


# ---------------------------------------------------------------------------
# Task 2.1 — POST /auth/register
# ---------------------------------------------------------------------------

@auth_bp.post("/register")
def register():
    """Validate input, generate OTP, send via email, store pending registration."""
    data = request.get_json(silent=True) or {}

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    # --- Validation ---
    errors = []
    if not username:
        errors.append("username is required")
    if not email:
        errors.append("email is required")
    if not password:
        errors.append("password is required")
    elif len(password) < 8:
        errors.append("password must be at least 8 characters")

    if errors:
        return jsonify({"status": "error", "message": "; ".join(errors)}), 400

    # --- Uniqueness check ---
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT username, email FROM user WHERE username = ? OR email = ?",
            (username, email),
        ).fetchone()
    finally:
        conn.close()

    if existing:
        if existing["username"] == username:
            return jsonify({"status": "error", "message": "Username already taken"}), 409
        return jsonify({"status": "error", "message": "Email already registered"}), 409

    # --- Generate and store OTP ---
    otp = _generate_otp()
    otp_hash = _hash_otp(otp)
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    _otp_store[email] = {"otp_hash": otp_hash, "expires_at": expires_at}
    _pending_registrations[email] = {"username": username, "password": password}

    # --- Send OTP email ---
    subject = "Your Anemia Detection System — Registration OTP"
    body = f"""
    <html><body>
    <p>Hello <strong>{username}</strong>,</p>
    <p>Your one-time password (OTP) for registration is:</p>
    <h2 style="letter-spacing:4px;">{otp}</h2>
    <p>This OTP is valid for <strong>10 minutes</strong>.</p>
    <p>If you did not request this, please ignore this email.</p>
    </body></html>
    """

    try:
        _send_email(email, subject, body)
    except Exception as exc:  # noqa: BLE001
        # Clean up stored state on SMTP failure
        _otp_store.pop(email, None)
        _pending_registrations.pop(email, None)
        return (
            jsonify({"status": "error", "message": f"Failed to send OTP email: {exc}"}),
            500,
        )

    return jsonify({"status": "ok", "message": "OTP sent to your email address"}), 200


# ---------------------------------------------------------------------------
# Task 2.2 — POST /auth/verify-register-otp
# ---------------------------------------------------------------------------

@auth_bp.post("/verify-register-otp")
def verify_register_otp():
    """Verify OTP, create user account, issue JWT."""
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()

    if not email or not otp:
        return jsonify({"status": "error", "message": "email and otp are required"}), 400

    stored = _otp_store.get(email)
    if not stored:
        return jsonify({"status": "error", "message": "No pending OTP for this email"}), 400

    # Check expiry
    if datetime.utcnow() > stored["expires_at"]:
        _otp_store.pop(email, None)
        _pending_registrations.pop(email, None)
        return jsonify({"status": "error", "message": "OTP has expired. Please register again"}), 400

    # Check hash
    if _hash_otp(otp) != stored["otp_hash"]:
        return jsonify({"status": "error", "message": "Invalid OTP"}), 400

    # Retrieve pending registration data
    pending = _pending_registrations.get(email)
    if not pending:
        return jsonify({"status": "error", "message": "No pending registration for this email"}), 400

    username = pending["username"]
    password = pending["password"]

    # Create user
    password_hash = _bcrypt_hash(password)
    conn = get_db()
    try:
        # Double-check uniqueness (race condition guard)
        existing = conn.execute(
            "SELECT user_id FROM user WHERE username = ? OR email = ?",
            (username, email),
        ).fetchone()
        if existing:
            return jsonify({"status": "error", "message": "Account already exists"}), 409

        conn.execute(
            """
            INSERT INTO user (username, email, password_hash, role, status)
            VALUES (?, ?, ?, 'patient', 'active')
            """,
            (username, email, password_hash),
        )
        conn.commit()

        user_row = conn.execute(
            "SELECT username, email, role FROM user WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()

    # Clean up OTP state
    _otp_store.pop(email, None)
    _pending_registrations.pop(email, None)

    token = _issue_jwt(user_row)

    return jsonify({
        "status": "ok",
        "token": token,
        "user": {
            "username": user_row["username"],
            "role": user_row["role"],
            "email": user_row["email"],
        },
    }), 200


# ---------------------------------------------------------------------------
# Task 2.3 + 2.4 — POST /auth/login (with account lockout)
# ---------------------------------------------------------------------------

@auth_bp.post("/login")
def login():
    """Authenticate user by username or email, issue JWT."""
    data = request.get_json(silent=True) or {}

    identifier = (data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"status": "error", "message": "username/email and password are required"}), 400

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT * FROM user WHERE username = ? OR email = ?",
            (identifier, identifier.lower()),
        ).fetchone()

        if not user:
            return jsonify({"status": "error", "message": "Invalid credentials"}), 401

        # Check account status
        if user["status"] != "active":
            return (
                jsonify({"status": "error", "message": "Account is inactive. Contact support."}),
                401,
            )

        # Check lockout
        if user["locked_until"]:
            locked_until_dt = datetime.strptime(user["locked_until"], "%Y-%m-%d %H:%M:%S")
            if datetime.utcnow() < locked_until_dt:
                return (
                    jsonify({
                        "status": "error",
                        "message": "Account is temporarily locked",
                        "locked_until": user["locked_until"],
                    }),
                    401,
                )
            else:
                # Lock has expired — clear it
                conn.execute(
                    "UPDATE user SET locked_until = NULL, failed_attempts = 0 WHERE user_id = ?",
                    (user["user_id"],),
                )
                conn.commit()

        # Verify password
        if not _bcrypt_check(password, user["password_hash"]):
            # --- Audit service log: login failure ---
            log_action(
                actor=identifier,
                action="login_failure",
                details={"reason": "invalid_credentials"},
                ip=request.remote_addr,
            )

            # Increment failed_attempts (Task 2.4)
            new_attempts = (user["failed_attempts"] or 0) + 1
            if new_attempts >= 5:
                locked_until = datetime.utcnow() + timedelta(minutes=15)
                locked_until_str = locked_until.strftime("%Y-%m-%d %H:%M:%S")
                conn.execute(
                    "UPDATE user SET failed_attempts = ?, locked_until = ? WHERE user_id = ?",
                    (new_attempts, locked_until_str, user["user_id"]),
                )
                conn.commit()
                # Send lockout notification email (best-effort)
                _send_lockout_email(user["email"], user["username"], locked_until_str)
                return (
                    jsonify({
                        "status": "error",
                        "message": "Too many failed attempts. Account locked for 15 minutes.",
                        "locked_until": locked_until_str,
                    }),
                    401,
                )
            else:
                conn.execute(
                    "UPDATE user SET failed_attempts = ? WHERE user_id = ?",
                    (new_attempts, user["user_id"]),
                )
                conn.commit()
                return jsonify({"status": "error", "message": "Invalid credentials"}), 401

        # Successful login — reset failed_attempts
        conn.execute(
            "UPDATE user SET failed_attempts = 0, locked_until = NULL WHERE user_id = ?",
            (user["user_id"],),
        )
        conn.commit()

        token = _issue_jwt(user)

        # --- Audit service log: login success ---
        log_action(
            actor=user["username"],
            action="login_success",
            ip=request.remote_addr,
        )

        return jsonify({
            "status": "ok",
            "token": token,
            "user": {
                "username": user["username"],
                "role": user["role"],
                "email": user["email"],
            },
        }), 200

    finally:
        conn.close()


def _send_lockout_email(email: str, username: str, locked_until: str) -> None:
    """Send account lockout notification email (best-effort, swallows errors)."""
    subject = "Anemia Detection System — Account Locked"
    body = f"""
    <html><body>
    <p>Hello <strong>{username}</strong>,</p>
    <p>Your account has been temporarily locked due to 5 consecutive failed login attempts.</p>
    <p>Your account will be unlocked at: <strong>{locked_until} UTC</strong></p>
    <p>If this was not you, please contact support immediately.</p>
    </body></html>
    """
    try:
        _send_email(email, subject, body)
    except Exception:  # noqa: BLE001
        pass  # Lockout email is best-effort


# ---------------------------------------------------------------------------
# Task 2.5 — POST /auth/logout
# ---------------------------------------------------------------------------

@auth_bp.post("/logout")
@require_auth
def logout():
    """Blacklist the current JWT's jti."""
    jti = g.current_user.get("jti")
    exp = g.current_user.get("exp")

    if not jti:
        return jsonify({"status": "error", "message": "Token has no jti claim"}), 400

    # Convert exp (Unix timestamp) to ISO string for storage
    if exp:
        exp_str = datetime.utcfromtimestamp(exp).strftime("%Y-%m-%d %H:%M:%S")
    else:
        exp_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO jwt_blacklist (jti, exp) VALUES (?, ?)",
            (jti, exp_str),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify({"status": "ok", "message": "Logged out successfully"}), 200


# ---------------------------------------------------------------------------
# Task 2.6 — POST /auth/forgot-password
# ---------------------------------------------------------------------------

@auth_bp.post("/forgot-password")
def forgot_password():
    """Send a password-reset OTP to the registered email."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"status": "error", "message": "email is required"}), 400

    conn = get_db()
    try:
        user = conn.execute(
            "SELECT username, email FROM user WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()

    # Always return 200 to avoid email enumeration
    if not user:
        return jsonify({"status": "ok", "message": "If that email is registered, an OTP has been sent"}), 200

    otp = _generate_otp()
    otp_hash = _hash_otp(otp)
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    _reset_otp_store[email] = {"otp_hash": otp_hash, "expires_at": expires_at}

    subject = "Anemia Detection System — Password Reset OTP"
    body = f"""
    <html><body>
    <p>Hello <strong>{user['username']}</strong>,</p>
    <p>Your one-time password (OTP) for password reset is:</p>
    <h2 style="letter-spacing:4px;">{otp}</h2>
    <p>This OTP is valid for <strong>10 minutes</strong>.</p>
    <p>If you did not request a password reset, please ignore this email.</p>
    </body></html>
    """

    try:
        _send_email(email, subject, body)
    except Exception as exc:  # noqa: BLE001
        _reset_otp_store.pop(email, None)
        return (
            jsonify({"status": "error", "message": f"Failed to send OTP email: {exc}"}),
            500,
        )

    return jsonify({"status": "ok", "message": "If that email is registered, an OTP has been sent"}), 200


# ---------------------------------------------------------------------------
# Task 2.6 — POST /auth/verify-reset-otp
# ---------------------------------------------------------------------------

@auth_bp.post("/verify-reset-otp")
def verify_reset_otp():
    """Verify password-reset OTP and update the user's password hash."""
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    otp = (data.get("otp") or "").strip()
    new_password = data.get("new_password") or ""

    errors = []
    if not email:
        errors.append("email is required")
    if not otp:
        errors.append("otp is required")
    if not new_password:
        errors.append("new_password is required")
    elif len(new_password) < 8:
        errors.append("new_password must be at least 8 characters")

    if errors:
        return jsonify({"status": "error", "message": "; ".join(errors)}), 400

    stored = _reset_otp_store.get(email)
    if not stored:
        return jsonify({"status": "error", "message": "No pending password reset for this email"}), 400

    # Check expiry
    if datetime.utcnow() > stored["expires_at"]:
        _reset_otp_store.pop(email, None)
        return jsonify({"status": "error", "message": "OTP has expired. Please request a new one"}), 400

    # Check hash
    if _hash_otp(otp) != stored["otp_hash"]:
        return jsonify({"status": "error", "message": "Invalid OTP"}), 400

    # Update password
    new_hash = _bcrypt_hash(new_password)
    conn = get_db()
    try:
        result = conn.execute(
            "UPDATE user SET password_hash = ?, failed_attempts = 0, locked_until = NULL WHERE email = ?",
            (new_hash, email),
        )
        conn.commit()
        if result.rowcount == 0:
            return jsonify({"status": "error", "message": "User not found"}), 404
    finally:
        conn.close()

    _reset_otp_store.pop(email, None)

    return jsonify({"status": "ok", "message": "Password updated successfully"}), 200
