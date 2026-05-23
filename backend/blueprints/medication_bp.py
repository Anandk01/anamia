"""
Medication Blueprint — /api/medications

Handles medication prescriptions, scheduling, logging, adherence tracking,
and history.

Routes:
    POST /api/medications/                        → doctor prescribes medication
    GET  /api/medications/                        → list medications
    GET  /api/medications/schedule                → patient's today schedule
    POST /api/medications/<med_id>/log            → patient logs a dose
    GET  /api/medications/adherence               → adherence stats
    PUT  /api/medications/<med_id>/deactivate     → doctor deactivates medication
    GET  /api/medications/history                 → patient's medication log history
"""

from flask import Blueprint, g, jsonify, request

from db import get_db, get_doctor_for_patient
from middleware.auth import require_auth
from middleware.rbac import require_role
from services import medication_service
from utils import notify_user

medication_bp = Blueprint("medications", __name__, url_prefix="/api/medications")

PAGE_SIZE = 20


# ---------------------------------------------------------------------------
# POST /api/medications/ — doctor prescribes medication
# ---------------------------------------------------------------------------

@medication_bp.post("/")
@require_auth
@require_role("doctor")
def prescribe_medication():
    """Create a new medication prescription.

    Request JSON:
        {
            "patient_username": str,
            "name": str,
            "dose_mg": float,
            "frequency": str,
            "start_date": str,
            "end_date": str (optional)
        }

    Response JSON (201):
        {"status": "ok", "medication": {...}}

    Response JSON (400):
        {"status": "error", "message": "..."}
    """
    data = request.get_json(silent=True) or {}

    patient_username = data.get("patient_username")
    name = data.get("name")
    dose_mg = data.get("dose_mg")
    frequency = data.get("frequency")
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not patient_username or not name or dose_mg is None or not frequency or not start_date:
        return jsonify({
            "status": "error",
            "message": "patient_username, name, dose_mg, frequency, and start_date are required"
        }), 400

    doctor_username = g.current_user["username"]

    try:
        medication = medication_service.prescribe_medication(
            doctor_username=doctor_username,
            patient_username=patient_username,
            name=name,
            dose_mg=float(dose_mg),
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    return jsonify({"status": "ok", "medication": medication}), 201


# ---------------------------------------------------------------------------
# POST /api/medications/prescribe — doctor prescribes with full details
# ---------------------------------------------------------------------------

@medication_bp.post("/prescribe")
@require_auth
@require_role("doctor")
def prescribe_medication_full():
    """Doctor prescribes medication linked to a patient with extended fields.

    Request JSON:
        {
            "patient_username": str,
            "name": str,
            "dose_mg": float,
            "dose_unit": str (optional, default 'mg'),
            "frequency": str,
            "reminder_times": list (optional, e.g. ["08:00", "20:00"]),
            "start_date": str,
            "end_date": str (optional),
            "notes": str (optional),
            "prediction_id": int (optional)
        }
    """
    import json as _json

    data = request.get_json(silent=True) or {}
    doctor_username = g.current_user["username"]
    patient_username = data.get("patient_username")
    name = data.get("name")
    dose_mg = data.get("dose_mg")
    dose_unit = data.get("dose_unit", "mg")
    frequency = data.get("frequency")
    reminder_times = data.get("reminder_times")
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    notes = data.get("notes")
    prediction_id = data.get("prediction_id")

    if not patient_username or not name or dose_mg is None or not frequency or not start_date:
        return jsonify({"status": "error", "message": "patient_username, name, dose_mg, frequency, and start_date are required"}), 400

    reminder_times_json = _json.dumps(reminder_times) if reminder_times else None

    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO medication (username, name, dose_mg, frequency, start_date, end_date,
                prescribed_by, active, created_at, doctor_username, prediction_id, dose_unit, reminder_times, added_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), ?, ?, ?, ?, 'doctor')""",
            (patient_username, name, float(dose_mg), frequency, start_date, end_date,
             doctor_username, doctor_username, prediction_id, dose_unit, reminder_times_json),
        )
        conn.commit()
        med_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM medication WHERE med_id = ?", (med_id,)).fetchone()
    finally:
        conn.close()

    # Notify patient
    try:
        notify_user(patient_username, 'new_prescription', {
            'med_id': med_id,
            'doctor_username': doctor_username,
            'name': name,
            'dose_mg': float(dose_mg),
            'dose_unit': dose_unit,
            'frequency': frequency,
            'start_date': start_date,
        })
    except Exception:
        pass

    return jsonify({"status": "ok", "medication": dict(row)}), 201


# ---------------------------------------------------------------------------
# GET /api/medications/ — list medications
# ---------------------------------------------------------------------------

@medication_bp.get("/")
@require_auth
@require_role("patient", "doctor")
def list_medications():
    """List medications for the current user.

    Query params:
        active (str): "1" for active only (default), "0" for all.
        patient_username (str): For doctors, filter by patient username.

    Response JSON (200):
        {"status": "ok", "medications": [...]}
    """
    active_param = request.args.get("active", "1")
    active_only = active_param == "1"

    username = g.current_user["username"]
    role = g.current_user["role"]

    conn = get_db()
    try:
        if role == "patient":
            # Patients see their own medications
            if active_only:
                rows = conn.execute(
                    "SELECT * FROM medication WHERE username = ? AND active = 1 ORDER BY created_at DESC",
                    (username,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM medication WHERE username = ? ORDER BY created_at DESC",
                    (username,),
                ).fetchall()
        else:
            # Doctors see medications they prescribed
            patient_username = request.args.get("patient_username")
            if patient_username:
                # Filter by specific patient
                if active_only:
                    rows = conn.execute(
                        "SELECT * FROM medication WHERE prescribed_by = ? AND username = ? AND active = 1 ORDER BY created_at DESC",
                        (username, patient_username),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM medication WHERE prescribed_by = ? AND username = ? ORDER BY created_at DESC",
                        (username, patient_username),
                    ).fetchall()
            else:
                # All medications prescribed by this doctor
                if active_only:
                    rows = conn.execute(
                        "SELECT * FROM medication WHERE prescribed_by = ? AND active = 1 ORDER BY created_at DESC",
                        (username,),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT * FROM medication WHERE prescribed_by = ? ORDER BY created_at DESC",
                        (username,),
                    ).fetchall()

        medications = [dict(row) for row in rows]
    finally:
        conn.close()

    return jsonify({"status": "ok", "medications": medications}), 200


# ---------------------------------------------------------------------------
# GET /api/medications/schedule — patient's today schedule
# ---------------------------------------------------------------------------

@medication_bp.get("/schedule")
@require_auth
@require_role("patient")
def get_schedule():
    """Get the patient's medication schedule for a given date.

    Query params:
        date (str): Date in YYYY-MM-DD format. Defaults to today.

    Response JSON (200):
        {"status": "ok", "schedule": [...]}
    """
    username = g.current_user["username"]

    try:
        schedule = medication_service.get_todays_schedule(username)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    return jsonify({"status": "ok", "schedule": schedule}), 200


# ---------------------------------------------------------------------------
# POST /api/medications/<med_id>/log — patient logs a dose
# ---------------------------------------------------------------------------

@medication_bp.post("/<int:med_id>/log")
@require_auth
@require_role("patient")
def log_dose(med_id: int):
    """Log a medication dose.

    Request JSON:
        {
            "skipped": bool (optional, default false),
            "notes": str (optional)
        }

    Response JSON (201):
        {"status": "ok", "log_entry": {...}}

    Response JSON (400):
        {"status": "error", "message": "..."}
    """
    data = request.get_json(silent=True) or {}

    skipped = data.get("skipped", False)
    notes = data.get("notes")
    username = g.current_user["username"]

    try:
        log_entry = medication_service.log_medication(
            med_id=med_id,
            username=username,
            skipped=bool(skipped),
            notes=notes,
        )
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    return jsonify({"status": "ok", "log_entry": log_entry}), 201


# ---------------------------------------------------------------------------
# GET /api/medications/adherence — adherence stats
# ---------------------------------------------------------------------------

@medication_bp.get("/adherence")
@require_auth
@require_role("patient", "doctor")
def get_adherence():
    """Get medication adherence statistics.

    Query params:
        days (int): Number of days to look back (default 7).
        patient_username (str): For doctors, specify the patient.

    Response JSON (200):
        {"status": "ok", "adherence": {...}}

    Response JSON (400):
        {"status": "error", "message": "..."}
    """
    days_param = request.args.get("days", "7")
    try:
        days = int(days_param)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "days must be an integer"}), 400

    username = g.current_user["username"]
    role = g.current_user["role"]

    if role == "doctor":
        # Doctors can check a specific patient's adherence
        patient_username = request.args.get("patient_username")
        if patient_username:
            username = patient_username

    try:
        adherence = medication_service.calculate_adherence(username, days)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    return jsonify({"status": "ok", "adherence": adherence}), 200


# ---------------------------------------------------------------------------
# PUT /api/medications/<med_id>/deactivate — doctor deactivates medication
# ---------------------------------------------------------------------------

@medication_bp.put("/<int:med_id>/deactivate")
@require_auth
@require_role("doctor")
def deactivate_medication(med_id: int):
    """Deactivate a medication.

    Response JSON (200):
        {"status": "ok", "medication": {...}}

    Response JSON (400):
        {"status": "error", "message": "..."}
    """
    doctor_username = g.current_user["username"]

    try:
        medication = medication_service.deactivate_medication(med_id, doctor_username)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

    return jsonify({"status": "ok", "medication": medication}), 200


# ---------------------------------------------------------------------------
# GET /api/medications/history — patient's medication log history
# ---------------------------------------------------------------------------

@medication_bp.get("/history")
@require_auth
@require_role("patient")
def get_history():
    """Get paginated medication log history for a specific medication.

    Query params:
        med_id (int): Required. The medication ID.
        page (int): Page number (default 1).

    Response JSON (200):
        {"status": "ok", "logs": [...], "page": int, "total_pages": int, "total": int}

    Response JSON (400):
        {"status": "error", "message": "..."}

    Response JSON (403):
        {"status": "error", "message": "..."}
    """
    med_id_param = request.args.get("med_id")
    page_param = request.args.get("page", "1")

    if not med_id_param:
        return jsonify({"status": "error", "message": "med_id query parameter is required"}), 400

    try:
        med_id = int(med_id_param)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "med_id must be an integer"}), 400

    try:
        page = int(page_param)
        if page < 1:
            page = 1
    except (TypeError, ValueError):
        page = 1

    username = g.current_user["username"]

    conn = get_db()
    try:
        # Verify the medication belongs to the current user
        medication = conn.execute(
            "SELECT * FROM medication WHERE med_id = ? AND username = ?",
            (med_id, username),
        ).fetchone()

        if medication is None:
            return jsonify({
                "status": "error",
                "message": "Medication not found or does not belong to this user"
            }), 403

        # Count total logs for pagination
        count_row = conn.execute(
            "SELECT COUNT(*) as total FROM medication_log WHERE med_id = ?",
            (med_id,),
        ).fetchone()
        total = count_row["total"] if count_row else 0

        total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

        # Fetch paginated logs
        offset = (page - 1) * PAGE_SIZE
        rows = conn.execute(
            "SELECT * FROM medication_log WHERE med_id = ? ORDER BY taken_at DESC LIMIT ? OFFSET ?",
            (med_id, PAGE_SIZE, offset),
        ).fetchall()

        logs = [dict(row) for row in rows]
    finally:
        conn.close()

    return jsonify({
        "status": "ok",
        "logs": logs,
        "page": page,
        "total_pages": total_pages,
        "total": total,
    }), 200
