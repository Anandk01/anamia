"""
Appointments Blueprint — /api/appointments

Handles appointment booking, confirmation, cancellation, and calendar views.

Routes:
    POST /api/appointments/request                    → patient requests an appointment
    GET  /api/appointments/calendar                   → calendar view (patient + doctor)
    GET  /api/appointments/<id>                       → get single appointment
    PUT  /api/appointments/<id>/confirm               → doctor confirms appointment
    PUT  /api/appointments/<id>/cancel                → patient or doctor cancels
    PUT  /api/appointments/<id>/complete              → doctor marks as completed
    GET  /api/appointments/available-slots            → patient views available slots
"""

from datetime import date, datetime, timedelta

from flask import Blueprint, g, jsonify, request

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
@require_role("patient")
def request_appointment():
    """Create a new pending appointment.

    Request JSON:
        {
            "doctor_id":  int  — the doctor's user_id,
            "slot_date":  str  — date in YYYY-MM-DD format,
            "slot_time":  str  — time in HH:MM format,
            "notes":      str  — optional notes
        }

    Response JSON (201):
        {"status": "ok", "appointment": {...}}

    Response JSON (400):
        {"status": "error", "message": "..."}
    """
    data = request.get_json(silent=True) or {}

    doctor_id = data.get("doctor_id")
    slot_date = data.get("slot_date")
    slot_time = data.get("slot_time")
    notes = data.get("notes")

    if not doctor_id or not slot_date or not slot_time:
        return jsonify({"status": "error", "message": "doctor_id, slot_date, and slot_time are required"}), 400

    username = g.current_user["username"]
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
    """Confirm a pending appointment.

    Response JSON (200):
        {"status": "ok", "appointment": {...}}

    Response JSON (400):
        {"status": "error", "message": "..."}
    """
    username = g.current_user["username"]

    try:
        appointment = appointment_service.confirm_appointment(appointment_id, username)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    return jsonify({"status": "ok", "appointment": appointment}), 200


# ---------------------------------------------------------------------------
# PUT /api/appointments/<id>/cancel — patient or doctor cancels
# ---------------------------------------------------------------------------

@appointments_bp.put("/<int:appointment_id>/cancel")
@require_auth
@require_role("patient", "doctor")
def cancel_appointment(appointment_id: int):
    """Cancel an appointment.

    Request JSON (optional):
        {"reason": str}

    Response JSON (200):
        {"status": "ok", "appointment": {...}}

    Response JSON (400):
        {"status": "error", "message": "..."}
    """
    data = request.get_json(silent=True) or {}
    reason = data.get("reason")
    username = g.current_user["username"]

    try:
        appointment = appointment_service.cancel_appointment(appointment_id, username, reason)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    return jsonify({"status": "ok", "appointment": appointment}), 200


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
@require_role("patient")
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
