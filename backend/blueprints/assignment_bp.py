"""
Assignment Blueprint — /api/assignment

Provides endpoints for doctors and patients to query their assignments.

Routes:
    GET /api/assignment/my-patients  → doctor's assigned patients
    GET /api/assignment/my-doctor    → patient's assigned doctor
"""

from flask import Blueprint, g, jsonify
from db import get_db, get_patients_for_doctor, get_doctor_for_patient
from middleware.auth import require_auth
from middleware.rbac import require_role

assignment_bp = Blueprint("assignment", __name__, url_prefix="/api/assignment")


@assignment_bp.get("/my-patients")
@require_auth
@require_role("doctor")
def my_patients():
    """Return list of patients assigned to the current doctor."""
    username = g.current_user["username"]
    patients = get_patients_for_doctor(username)
    conn = get_db()
    try:
        result = []
        for p in patients:
            row = conn.execute(
                "SELECT username, email FROM user WHERE username = ?", (p,)
            ).fetchone()
            if row:
                result.append({"username": row["username"], "email": row["email"]})
        return jsonify({"status": "ok", "patients": result}), 200
    finally:
        conn.close()


@assignment_bp.get("/my-doctor")
@require_auth
@require_role("patient")
def my_doctor():
    """Return the doctor assigned to the current patient."""
    username = g.current_user["username"]
    doctor = get_doctor_for_patient(username)
    if not doctor:
        return jsonify({"status": "ok", "doctor": None, "message": "No doctor assigned yet"}), 200
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT username, email, specialization FROM user WHERE username = ?",
            (doctor,)
        ).fetchone()
        if row:
            return jsonify({"status": "ok", "doctor": {
                "username": row["username"],
                "email": row["email"],
                "specialization": row["specialization"],
            }}), 200
        return jsonify({"status": "ok", "doctor": None}), 200
    finally:
        conn.close()
