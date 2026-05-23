"""
Appointments Blueprint — /api/appointments

Handles appointment booking, confirmation, cancellation, and calendar views.

Routes:
    POST /api/appointments/request                    → patient/admin requests an appointment
    GET  /api/appointments/calendar                   → calendar view (patient + doctor)
    GET  /api/appointments/<id>                       → get single appointment
    PUT  /api/appointments/<id>/confirm               → doctor confirms appointment
    PUT  /api/appointments/<id>/cancel                → patient or doctor cancels
    PUT  /api/appointments/<id>/complete              → doctor marks as completed
    PUT  /api/appointments/<id>/reschedule            → doctor reschedules appointment
    GET  /api/appointments/available-slots            → patient views available slots
"""

import smtplib
from datetime import date, datetime, timedelta
from email.mime.text import MIMEText

from flask import Blueprint, current_app, g, jsonify, request

from db import get_db
from middleware.auth import require_auth
from middleware.rbac import require_role
from services import appointment_service

appointments_bp = Blueprint("appointments", __name__, url_prefix="/api/appointments")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_id(username: str) -> int | None:
    """Look up user_id from username."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT user_id FROM user WHERE username = ?", (username,)
        ).fetchone()
        return row["user_id"] if row else None
    finally:
        conn.close()


def _get_username_by_id(user_id: int) -> str | None:
    """Look up username from user_id."""
    conn = get_db()
    try:
        row = conn.execute("SELECT username FROM user WHERE user_id = ?", (user_id,)).fetchone()
        return row["username"] if row else None
    finally:
        conn.close()


def _get_email_by_id(user_id: int) -> str | None:
    """Look up email from user_id."""
    conn = get_db()
    try:
        row = conn.execute("SELECT email FROM user WHERE user_id = ?", (user_id,)).fetchone()
        return row["email"] if row else None
    finally:
        conn.close()


def _notify_user(username: str, ntype: str, title: str, message: str):
    """Insert a notification for a user."""
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO notification (username, type, title, message) VALUES (?, ?, ?, ?)",
            (username, ntype, title, message),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def _send_email_notification(to_email: str, subject: str, body: str):
    """Send email notification using app SMTP config. Fails silently."""
    try:
        smtp_server = current_app.config.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = current_app.config.get("SMTP_PORT", 587)
        email_addr = current_app.config.get("EMAIL_ADDRESS", "")
        email_pass = current_app.config.get("EMAIL_PASSWORD", "")
        if not email_addr or not email_pass or not to_email:
            return
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = email_addr
        msg["To"] = to_email
        with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(email_addr, email_pass)
            server.sendmail(email_addr, [to_email], msg.as_string())
    except Exception:
        pass


def _get_current_monday() -> str:
    """Return the current week's Monday as YYYY-MM-DD."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# POST /api/appointments/request — patient requests an appointment
# ---------------------------------------------------------------------------

@appointments_bp.post("/request")
@require_auth
@require_role("patient", "admin")
def request_appointment():
    """Create a new pending appointment (or confirmed if admin-scheduled).

    Request JSON:
        {
            "doctor_id":  int  — the doctor's user_id,
            "patient_id": int  — (admin only) the patient's user_id,
            "slot_date":  str  — date in YYYY-MM-DD format,
            "slot_time":  str  — time in HH:MM format,
            "notes":      str  — optional notes
        }
    """
    data = request.get_json(silent=True) or {}

    doctor_id = data.get("doctor_id")
    slot_date = data.get("slot_date")
    slot_time = data.get("slot_time")
    notes = data.get("notes")

    if not doctor_id or not slot_date or not slot_time:
        return jsonify({"status": "error", "message": "doctor_id, slot_date, and slot_time are required"}), 400

    username = g.current_user["username"]
    role = g.current_user["role"]

    # Admin can schedule for any patient
    if role == "admin":
        patient_id = data.get("patient_id")
        if not patient_id:
            return jsonify({"status": "error", "message": "patient_id is required for admin scheduling"}), 400
        patient_id = int(patient_id)
    else:
        patient_id = _get_user_id(username)
        if patient_id is None:
            return jsonify({"status": "error", "message": "Patient user not found"}), 400

    try:
        appointment = appointment_service.request_appointment(
            patient_id=patient_id,
            doctor_id=int(doctor_id),
            slot_date=slot_date,
            slot_time=slot_time,
            notes=notes,
        )
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    # If admin scheduled, auto-confirm
    if role == "admin":
        conn = get_db()
        try:
            conn.execute(
                "UPDATE appointment SET status = 'confirmed', confirmed_at = datetime('now') WHERE appointment_id = ?",
                (appointment["appointment_id"],),
            )
            conn.commit()
            appointment["status"] = "confirmed"
        finally:
            conn.close()

    # Notify doctor about new appointment request
    doctor_username = _get_username_by_id(int(doctor_id))
    patient_username = _get_username_by_id(patient_id)
    if doctor_username:
        _notify_user(doctor_username, "appointment",
                     "New Appointment Request",
                     f"Patient {patient_username or 'unknown'} has requested an appointment on {slot_date} at {slot_time}")

    return jsonify({"status": "ok", "appointment": appointment}), 201


# ---------------------------------------------------------------------------
# GET /api/appointments/calendar — calendar view for patient or doctor
# ---------------------------------------------------------------------------

@appointments_bp.get("/calendar")
@require_auth
@require_role("patient", "doctor")
def get_calendar():
    """Return appointments for a 7-day window.

    Query params:
        week_start (str): Start date in YYYY-MM-DD format. Defaults to current Monday.

    Response JSON (200):
        {"status": "ok", "appointments": [...]}

    Response JSON (400):
        {"status": "error", "message": "..."}
    """
    week_start = request.args.get("week_start", _get_current_monday())

    username = g.current_user["username"]
    role = g.current_user["role"]
    user_id = _get_user_id(username)
    if user_id is None:
        return jsonify({"status": "error", "message": "User not found"}), 400

    try:
        appointments = appointment_service.get_calendar_view(user_id, role, week_start)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    return jsonify({"status": "ok", "appointments": appointments}), 200


# ---------------------------------------------------------------------------
# GET /api/appointments/<id> — get single appointment
# ---------------------------------------------------------------------------

@appointments_bp.get("/<int:appointment_id>")
@require_auth
@require_role("patient", "doctor")
def get_appointment(appointment_id: int):
    """Fetch a single appointment by ID.

    Verifies the current user is either the doctor or patient on the appointment.

    Response JSON (200):
        {"status": "ok", "appointment": {...}}

    Response JSON (403):
        {"status": "error", "message": "Not authorized..."}

    Response JSON (404):
        {"status": "error", "message": "Appointment not found"}
    """
    username = g.current_user["username"]
    user_id = _get_user_id(username)
    if user_id is None:
        return jsonify({"status": "error", "message": "User not found"}), 400

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM appointment WHERE appointment_id = ?",
            (appointment_id,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return jsonify({"status": "error", "message": "Appointment not found"}), 404

    appointment = dict(row)

    # Verify user is either the doctor or patient on this appointment
    if user_id != appointment["doctor_id"] and user_id != appointment["patient_id"]:
        return jsonify({"status": "error", "message": "Not authorized to view this appointment"}), 403

    return jsonify({"status": "ok", "appointment": appointment}), 200


# ---------------------------------------------------------------------------
# PUT /api/appointments/<id>/confirm — doctor confirms appointment
# ---------------------------------------------------------------------------

@appointments_bp.put("/<int:appointment_id>/confirm")
@require_auth
@require_role("doctor")
def confirm_appointment(appointment_id: int):
    """Confirm a pending appointment and notify patient."""
    username = g.current_user["username"]

    try:
        appointment = appointment_service.confirm_appointment(appointment_id, username)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    # Notify patient
    patient_username = _get_username_by_id(appointment.get("patient_id"))
    if patient_username:
        _notify_user(patient_username, "appointment", "Appointment Confirmed",
                     f"Dr. {username} has confirmed your appointment on {appointment.get('slot_date')} at {appointment.get('slot_time')}")
        patient_email = _get_email_by_id(appointment.get("patient_id"))
        if patient_email:
            _send_email_notification(patient_email, "Appointment Confirmed",
                                     f"Your appointment with Dr. {username} on {appointment.get('slot_date')} at {appointment.get('slot_time')} has been confirmed.")

    return jsonify({"status": "ok", "appointment": appointment}), 200


# ---------------------------------------------------------------------------
# PUT /api/appointments/<id>/cancel — patient or doctor cancels
# ---------------------------------------------------------------------------

@appointments_bp.put("/<int:appointment_id>/cancel")
@require_auth
@require_role("patient", "doctor")
def cancel_appointment(appointment_id: int):
    """Cancel an appointment and notify the other party."""
    data = request.get_json(silent=True) or {}
    reason = data.get("reason")
    username = g.current_user["username"]
    role = g.current_user["role"]

    # Get appointment info before cancelling
    conn = get_db()
    try:
        row = conn.execute("SELECT patient_id, doctor_id, slot_date, slot_time FROM appointment WHERE appointment_id = ?", (appointment_id,)).fetchone()
    finally:
        conn.close()

    try:
        appointment = appointment_service.cancel_appointment(appointment_id, username, reason)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    # Notify the other party
    if row:
        if role == "doctor":
            patient_username = _get_username_by_id(row["patient_id"])
            if patient_username:
                msg = f"Dr. {username} has cancelled your appointment on {row['slot_date']} at {row['slot_time']}."
                if reason:
                    msg += f" Reason: {reason}"
                _notify_user(patient_username, "appointment", "Appointment Cancelled", msg)
                patient_email = _get_email_by_id(row["patient_id"])
                if patient_email:
                    _send_email_notification(patient_email, "Appointment Cancelled", msg)
        else:
            doctor_username = _get_username_by_id(row["doctor_id"])
            if doctor_username:
                _notify_user(doctor_username, "appointment", "Appointment Cancelled",
                             f"Patient {username} has cancelled the appointment on {row['slot_date']} at {row['slot_time']}.")

    return jsonify({"status": "ok", "appointment": appointment}), 200


# ---------------------------------------------------------------------------
# PUT /api/appointments/<id>/reschedule — doctor reschedules appointment
# ---------------------------------------------------------------------------

@appointments_bp.put("/<int:appointment_id>/reschedule")
@require_auth
@require_role("doctor")
def reschedule_appointment(appointment_id: int):
    """Reschedule: cancel old appointment, create new one with new date/time.

    Request JSON:
        {"new_date": "YYYY-MM-DD", "new_time": "HH:MM", "reason": "optional"}
    """
    data = request.get_json(silent=True) or {}
    new_date = data.get("new_date")
    new_time = data.get("new_time")
    reason = data.get("reason", "Rescheduled by doctor")

    if not new_date or not new_time:
        return jsonify({"status": "error", "message": "new_date and new_time are required"}), 400

    username = g.current_user["username"]
    doctor_id = _get_user_id(username)

    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM appointment WHERE appointment_id = ?", (appointment_id,)).fetchone()
        if not row:
            return jsonify({"status": "error", "message": "Appointment not found"}), 404
        appt = dict(row)
        if appt["doctor_id"] != doctor_id:
            return jsonify({"status": "error", "message": "Not authorized"}), 403
        if appt["status"] in ("cancelled", "completed"):
            return jsonify({"status": "error", "message": "Cannot reschedule a cancelled/completed appointment"}), 400

        # Cancel old
        conn.execute(
            "UPDATE appointment SET status = 'cancelled', cancellation_reason = ? WHERE appointment_id = ?",
            (reason, appointment_id),
        )
        # Create new
        cursor = conn.execute(
            """INSERT INTO appointment (doctor_id, patient_id, slot_date, slot_time, status, notes)
               VALUES (?, ?, ?, ?, 'pending', ?)""",
            (doctor_id, appt["patient_id"], new_date, new_time, f"Rescheduled from {appt['slot_date']} {appt['slot_time']}"),
        )
        conn.commit()
        new_id = cursor.lastrowid
        new_row = conn.execute("SELECT * FROM appointment WHERE appointment_id = ?", (new_id,)).fetchone()
    finally:
        conn.close()

    # Notify patient
    patient_username = _get_username_by_id(appt["patient_id"])
    if patient_username:
        msg = f"Dr. {username} has rescheduled your appointment to {new_date} at {new_time}."
        if reason:
            msg += f" Reason: {reason}"
        _notify_user(patient_username, "appointment", "Appointment Rescheduled", msg)
        patient_email = _get_email_by_id(appt["patient_id"])
        if patient_email:
            _send_email_notification(patient_email, "Appointment Rescheduled", msg)

    return jsonify({"status": "ok", "appointment": dict(new_row)}), 200


# ---------------------------------------------------------------------------
# PUT /api/appointments/<id>/complete — doctor marks as completed
# ---------------------------------------------------------------------------

@appointments_bp.put("/<int:appointment_id>/complete")
@require_auth
@require_role("doctor")
def complete_appointment(appointment_id: int):
    """Mark a confirmed appointment as completed.

    Verifies:
      - Appointment exists with status='confirmed'
      - Current user is the doctor on the appointment

    Response JSON (200):
        {"status": "ok", "appointment": {...}}

    Response JSON (400/403/404):
        {"status": "error", "message": "..."}
    """
    username = g.current_user["username"]
    user_id = _get_user_id(username)
    if user_id is None:
        return jsonify({"status": "error", "message": "User not found"}), 400

    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM appointment WHERE appointment_id = ?",
            (appointment_id,),
        ).fetchone()

        if row is None:
            return jsonify({"status": "error", "message": "Appointment not found"}), 404

        appointment = dict(row)

        if appointment["status"] != "confirmed":
            return jsonify({
                "status": "error",
                "message": f"Appointment is not confirmed (current status: {appointment['status']})"
            }), 400

        if appointment["doctor_id"] != user_id:
            return jsonify({"status": "error", "message": "Not authorized to complete this appointment"}), 403

        # Update status to completed
        conn.execute(
            "UPDATE appointment SET status = 'completed' WHERE appointment_id = ?",
            (appointment_id,),
        )
        conn.commit()

        # Fetch updated appointment
        updated_row = conn.execute(
            "SELECT * FROM appointment WHERE appointment_id = ?",
            (appointment_id,),
        ).fetchone()
        updated = dict(updated_row)
    finally:
        conn.close()

    return jsonify({"status": "ok", "appointment": updated}), 200


# ---------------------------------------------------------------------------
# GET /api/appointments/available-slots — patient views available slots
# ---------------------------------------------------------------------------

@appointments_bp.get("/available-slots")
@require_auth
@require_role("patient")
def get_available_slots():
    """Return available 30-minute slots for a doctor on a given date.

    Query params:
        doctor_id (int): The doctor's user_id.
        date (str):      Date in YYYY-MM-DD format.

    Response JSON (200):
        {"status": "ok", "slots": [{"time": "HH:MM", "available": bool}, ...]}

    Response JSON (400):
        {"status": "error", "message": "..."}
    """
    doctor_id = request.args.get("doctor_id")
    date_str = request.args.get("date")

    if not doctor_id or not date_str:
        return jsonify({"status": "error", "message": "doctor_id and date are required"}), 400

    try:
        doctor_id_int = int(doctor_id)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "doctor_id must be an integer"}), 400

    try:
        slots = appointment_service.get_available_slots(doctor_id_int, date_str)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    return jsonify({"status": "ok", "slots": slots}), 200


# ---------------------------------------------------------------------------
# GET /api/appointments/doctors — list available doctors for booking
# ---------------------------------------------------------------------------

@appointments_bp.get("/doctors")
@require_auth
@require_role("patient", "admin")
def list_doctors():
    """Return list of doctors available for appointment booking.

    Returns all active users with role='doctor'.

    Response JSON (200):
        {"status": "ok", "doctors": [{"id": int, "name": str, "specialization": str}, ...]}
    """
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT user_id, username, specialization FROM user WHERE role = 'doctor' AND status = 'active'"
        ).fetchall()
        doctors = [
            {"id": r["user_id"], "name": r["username"], "specialization": r["specialization"] or "General"}
            for r in rows
        ]
        return jsonify({"status": "ok", "doctors": doctors}), 200
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /api/appointments/pending-count — count pending appointments for user
# ---------------------------------------------------------------------------

@appointments_bp.get("/pending-count")
@require_auth
def pending_count():
    """Return count of pending appointments for the current user."""
    username = g.current_user["username"]
    user_id = _get_user_id(username)
    role = g.current_user["role"]

    conn = get_db()
    try:
        if role == "doctor":
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM appointment WHERE doctor_id = ? AND status = 'pending'",
                (user_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM appointment WHERE patient_id = ? AND status IN ('pending', 'confirmed')",
                (user_id,),
            ).fetchone()
        return jsonify({"status": "ok", "count": row["cnt"] if row else 0}), 200
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# POST /api/appointments/availability — doctor sets weekly schedule
# ---------------------------------------------------------------------------

@appointments_bp.post("/availability")
@require_auth
@require_role("doctor")
def set_availability():
    """Set or update doctor's weekly availability.

    Request JSON:
        {
            "day_of_week": int (0=Monday, 6=Sunday),
            "start_time": str (HH:MM),
            "end_time": str (HH:MM),
            "slot_duration_minutes": int (default 30)
        }
    """
    data = request.get_json(silent=True) or {}
    doctor_username = g.current_user["username"]
    day_of_week = data.get("day_of_week")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    slot_duration = data.get("slot_duration_minutes", 30)

    if day_of_week is None or not start_time or not end_time:
        return jsonify({"status": "error", "message": "day_of_week, start_time, and end_time are required"}), 400

    conn = get_db()
    try:
        # Delete existing entry for this day, then insert new one
        conn.execute(
            "DELETE FROM doctor_availability WHERE doctor_username = ? AND day_of_week = ?",
            (doctor_username, int(day_of_week)),
        )
        conn.execute(
            """INSERT INTO doctor_availability (doctor_username, day_of_week, start_time, end_time, slot_duration_minutes)
               VALUES (?, ?, ?, ?, ?)""",
            (doctor_username, int(day_of_week), start_time, end_time, int(slot_duration)),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify({"status": "ok", "saved": True}), 200


# ---------------------------------------------------------------------------
# GET /api/appointments/availability/<doctor_username> — get doctor's schedule
# ---------------------------------------------------------------------------

@appointments_bp.get("/availability/<doctor_username>")
@require_auth
def get_availability(doctor_username: str):
    """Return doctor's weekly availability schedule."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM doctor_availability WHERE doctor_username = ? ORDER BY day_of_week",
            (doctor_username,),
        ).fetchall()
        schedule = [dict(r) for r in rows]
        return jsonify({"status": "ok", "availability": schedule}), 200
    finally:
        conn.close()
