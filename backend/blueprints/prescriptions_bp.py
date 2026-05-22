"""
Prescriptions Blueprint — /api/prescriptions

Prescription management endpoints.
"""

from flask import Blueprint, g, jsonify, request

from db import get_db
from middleware.auth import require_auth
from middleware.rbac import require_role

prescriptions_bp = Blueprint("prescriptions", __name__, url_prefix="/api/prescriptions")


@prescriptions_bp.post("/")
@require_auth
@require_role("doctor")
def create_prescription():
    import json as _json
    data = request.get_json(silent=True) or {}
    doctor_id = g.current_user["username"]
    # Accept both patient_id and patient_username
    patient_id = data.get("patient_id") or data.get("patient_username")
    if not patient_id:
        return jsonify({"status": "error", "message": "patient_username is required"}), 400

    # Serialize medications to JSON string if it's a list
    medications = data.get("medications", "")
    if isinstance(medications, (list, dict)):
        medications = _json.dumps(medications)

    # Accept both instructions and dosage_instructions
    dosage_instructions = data.get("dosage_instructions") or data.get("instructions") or ""
    diet_plan = data.get("diet_plan") or ""

    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO prescription
               (doctor_id, patient_id, prediction_id, medications,
                dosage_instructions, duration_days, follow_up_date, notes, diet_plan)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (doctor_id, patient_id, data.get("prediction_id"),
             medications, dosage_instructions,
             data.get("duration_days"), data.get("follow_up_date"),
             data.get("notes"), diet_plan),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM prescription WHERE prescription_id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        # Notify patient about new prescription
        try:
            conn.execute(
                "INSERT INTO notification (username, type, title, message) VALUES (?, 'system', 'New Prescription', ?)",
                (patient_id, f"Dr. {doctor_id} has prescribed medications for you"),
            )
            conn.commit()
        except Exception:
            pass

        # If follow_up_date is set, create notification and auto-confirmed appointment
        follow_up_date = data.get("follow_up_date")
        if follow_up_date:
            try:
                conn.execute(
                    "INSERT INTO notification (username, type, title, message, scheduled_at) VALUES (?, 'appointment', 'Follow-up Appointment', ?, ?)",
                    (patient_id, f"Follow-up appointment with Dr. {doctor_id}", follow_up_date),
                )
                # Get user IDs for appointment
                doc_row = conn.execute("SELECT user_id FROM user WHERE username = ?", (doctor_id,)).fetchone()
                pat_row = conn.execute("SELECT user_id FROM user WHERE username = ?", (patient_id,)).fetchone()
                if doc_row and pat_row:
                    conn.execute(
                        """INSERT INTO appointment (doctor_id, patient_id, slot_date, slot_time, status, confirmed_at, notes)
                           VALUES (?, ?, ?, '10:00', 'confirmed', datetime('now'), 'Follow-up from prescription')""",
                        (doc_row["user_id"], pat_row["user_id"], follow_up_date),
                    )
                conn.commit()
            except Exception:
                pass

        return jsonify({"status": "ok", "prescription": dict(row)}), 201
    finally:
        conn.close()


@prescriptions_bp.get("/")
@require_auth
@require_role("doctor")
def list_prescriptions():
    """List prescriptions created by this doctor."""
    doctor_id = g.current_user["username"]
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM prescription WHERE doctor_id = ? ORDER BY created_at DESC",
            (doctor_id,),
        ).fetchall()
        return jsonify({"status": "ok", "prescriptions": [dict(r) for r in rows]}), 200
    finally:
        conn.close()


@prescriptions_bp.get("/mine")
@require_auth
@require_role("patient")
def my_prescriptions():
    """List prescriptions for the current patient."""
    import json as _json
    patient_id = g.current_user["username"]
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM prescription WHERE patient_id = ? ORDER BY created_at DESC",
            (patient_id,),
        ).fetchall()
        results = []
        for r in rows:
            rx = dict(r)
            # Parse medications JSON string back to list
            if isinstance(rx.get("medications"), str):
                try:
                    rx["medications"] = _json.loads(rx["medications"])
                except (ValueError, TypeError):
                    rx["medications"] = []
            rx["id"] = rx.get("prescription_id")
            rx["doctor_username"] = rx.get("doctor_id")
            results.append(rx)
        return jsonify({"status": "ok", "prescriptions": results}), 200
    finally:
        conn.close()


@prescriptions_bp.get("/<int:prescription_id>")
@require_auth
def get_prescription(prescription_id):
    username = g.current_user["username"]
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM prescription WHERE prescription_id = ?",
            (prescription_id,),
        ).fetchone()
        if not row:
            return jsonify({"status": "error", "message": "Not found"}), 404
        rx = dict(row)
        if rx["doctor_id"] != username and rx["patient_id"] != username:
            return jsonify({"status": "error", "message": "Not authorized"}), 403
        return jsonify({"status": "ok", "prescription": rx}), 200
    finally:
        conn.close()


@prescriptions_bp.get("/<int:prescription_id>/pdf")
@require_auth
def get_prescription_pdf(prescription_id):
    """Return prescription as simple text (PDF generation placeholder)."""
    username = g.current_user["username"]
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM prescription WHERE prescription_id = ?",
            (prescription_id,),
        ).fetchone()
        if not row:
            return jsonify({"status": "error", "message": "Not found"}), 404
        rx = dict(row)
        if rx["doctor_id"] != username and rx["patient_id"] != username:
            return jsonify({"status": "error", "message": "Not authorized"}), 403

        text = (
            f"PRESCRIPTION #{rx['prescription_id']}\n"
            f"Doctor: {rx['doctor_id']}\n"
            f"Patient: {rx['patient_id']}\n"
            f"Medications: {rx['medications']}\n"
            f"Dosage: {rx.get('dosage_instructions', 'N/A')}\n"
            f"Duration: {rx.get('duration_days', 'N/A')} days\n"
            f"Notes: {rx.get('notes', 'N/A')}\n"
            f"Date: {rx['created_at']}\n"
        )
        return text, 200, {'Content-Type': 'text/plain'}
    finally:
        conn.close()
