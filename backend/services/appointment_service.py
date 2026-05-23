"""
appointment_service.py — Business logic for the Appointment Booking module.

Provides:
  has_conflict(doctor_id, slot_date, slot_time, exclude_id)
      Check if a doctor has a conflicting confirmed appointment.

  request_appointment(patient_id, doctor_id, slot_date, slot_time, notes)
      Create a new pending appointment after validation.

  confirm_appointment(appointment_id, doctor_username)
      Confirm a pending appointment (doctor action).

  cancel_appointment(appointment_id, username, reason)
      Cancel an appointment (doctor or patient action).

  get_calendar_view(user_id, role, week_start)
      Return appointments for a 7-day window.

  get_available_slots(doctor_id, date)
      Return 30-minute slots with availability status.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta

from db import get_db

logger = logging.getLogger(__name__)

# Duration of each appointment slot in minutes
SLOT_DURATION_MIN = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return {}
    return dict(row)


def _parse_time_minutes(time_str: str) -> int:
    """Convert 'HH:MM' to total minutes since midnight."""
    parts = time_str.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def _minutes_to_time(minutes: int) -> str:
    """Convert total minutes since midnight to 'HH:MM'."""
    h = minutes // 60
    m = minutes % 60
    return f"{h:02d}:{m:02d}"


def _day_of_week(date_str: str) -> str:
    """Return abbreviated lowercase day name for a YYYY-MM-DD date string."""
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    return d.strftime("%a").lower()[:3]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def has_conflict(
    doctor_id: int,
    slot_date: str,
    slot_time: str,
    exclude_id: int | None = None,
) -> bool:
    """Check if a doctor has a conflicting confirmed appointment at the given date/time.

    Appointments occupy a 30-minute window. Two intervals overlap if:
        requested_start < existing_end AND existing_start < requested_end

    Parameters
    ----------
    doctor_id:   The doctor's user_id.
    slot_date:   Date string in YYYY-MM-DD format.
    slot_time:   Time string in HH:MM format.
    exclude_id:  Optional appointment_id to exclude (for updates).

    Returns
    -------
    bool
        True if a conflict exists, False otherwise.
    """
    requested_start = _parse_time_minutes(slot_time)
    requested_end = requested_start + SLOT_DURATION_MIN

    conn = get_db()
    try:
        query = """
            SELECT appointment_id, slot_time, duration_min
            FROM appointment
            WHERE doctor_id = ?
              AND slot_date = ?
              AND status = 'confirmed'
        """
        params: list = [doctor_id, slot_date]

        if exclude_id is not None:
            query += " AND appointment_id != ?"
            params.append(exclude_id)

        rows = conn.execute(query, params).fetchall()

        for row in rows:
            existing_start = _parse_time_minutes(row["slot_time"])
            existing_end = existing_start + (row["duration_min"] or SLOT_DURATION_MIN)
            # Overlap check
            if requested_start < existing_end and existing_start < requested_end:
                return True

        return False
    finally:
        conn.close()


def request_appointment(
    patient_id: int,
    doctor_id: int,
    slot_date: str,
    slot_time: str,
    notes: str | None = None,
) -> dict:
    """Create a new pending appointment after validation.

    Validates:
      - doctor_id exists with role='doctor'
      - slot_date is a future date (YYYY-MM-DD)
      - slot_time is within doctor's available_hours for that day of week
      - No conflict exists for the doctor at that slot

    Parameters
    ----------
    patient_id: The patient's user_id.
    doctor_id:  The doctor's user_id.
    slot_date:  Date string in YYYY-MM-DD format.
    slot_time:  Time string in HH:MM format.
    notes:      Optional notes for the appointment.

    Returns
    -------
    dict
        The created appointment record.

    Raises
    ------
    ValueError
        If any validation fails.
    """
    conn = get_db()
    try:
        # Validate doctor exists with role='doctor'
        doctor = conn.execute(
            "SELECT user_id, username, available_hours FROM user WHERE user_id = ? AND role = 'doctor'",
            (doctor_id,),
        ).fetchone()
        if doctor is None:
            raise ValueError("Invalid doctor_id or user is not a doctor.")

        # Validate slot_date is a future date
        try:
            appointment_date = datetime.strptime(slot_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            raise ValueError("slot_date must be in YYYY-MM-DD format.")

        today = date.today()
        if appointment_date < today:
            raise ValueError("slot_date must be today or a future date.")

        # Validate slot_time is within doctor's available_hours
        day_abbr = _day_of_week(slot_date)
        available_hours_raw = doctor["available_hours"]
        if available_hours_raw:
            try:
                available_hours = json.loads(available_hours_raw)
            except (json.JSONDecodeError, TypeError):
                available_hours = {}
        else:
            available_hours = {}

        if available_hours:
            day_schedule = available_hours.get(day_abbr)
            if day_schedule is None:
                raise ValueError(
                    f"Doctor is not available on {day_abbr}."
                )
            day_start = _parse_time_minutes(day_schedule["start"])
            day_end = _parse_time_minutes(day_schedule["end"])
            slot_start = _parse_time_minutes(slot_time)
            slot_end = slot_start + SLOT_DURATION_MIN

            if slot_start < day_start or slot_end > day_end:
                raise ValueError(
                    f"slot_time {slot_time} is outside doctor's available hours "
                    f"({day_schedule['start']}–{day_schedule['end']})."
                )
        else:
            # Default: allow 09:00-17:00 any day
            slot_start = _parse_time_minutes(slot_time)
            slot_end = slot_start + SLOT_DURATION_MIN
            if slot_start < 540 or slot_end > 1020:  # 09:00=540, 17:00=1020
                raise ValueError(
                    f"slot_time {slot_time} is outside default hours (09:00–17:00)."
                )

        # Check for conflicts
        if has_conflict(doctor_id, slot_date, slot_time):
            raise ValueError("Doctor has a conflicting appointment at this time.")

        # Insert appointment
        requested_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.execute(
            """
            INSERT INTO appointment
                (doctor_id, patient_id, requested_at, slot_date, slot_time,
                 duration_min, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (doctor_id, patient_id, requested_at, slot_date, slot_time,
             SLOT_DURATION_MIN, notes),
        )
        conn.commit()

        # Fetch and return the created appointment
        appointment = conn.execute(
            "SELECT * FROM appointment WHERE appointment_id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return _row_to_dict(appointment)
    finally:
        conn.close()


def confirm_appointment(appointment_id: int, doctor_username: str) -> dict:
    """Confirm a pending appointment.

    Validates:
      - Appointment exists with status='pending'
      - doctor_username matches the doctor_id on the appointment
      - No new conflicts have appeared

    Parameters
    ----------
    appointment_id:   The appointment to confirm.
    doctor_username:  Username of the doctor confirming.

    Returns
    -------
    dict
        The updated appointment record.

    Raises
    ------
    ValueError
        If validation fails.
    """
    conn = get_db()
    try:
        # Fetch appointment
        appointment = conn.execute(
            "SELECT * FROM appointment WHERE appointment_id = ?",
            (appointment_id,),
        ).fetchone()
        if appointment is None:
            raise ValueError("Appointment not found.")
        if appointment["status"] != "pending":
            raise ValueError(
                f"Appointment is not pending (current status: {appointment['status']})."
            )

        # Verify doctor_username matches the doctor_id on the appointment
        doctor = conn.execute(
            "SELECT user_id, username FROM user WHERE username = ? AND role = 'doctor'",
            (doctor_username,),
        ).fetchone()
        if doctor is None:
            raise ValueError("Doctor not found.")
        if doctor["user_id"] != appointment["doctor_id"]:
            raise ValueError("You are not the doctor assigned to this appointment.")

        # Check for new conflicts (exclude this appointment itself)
        if has_conflict(
            appointment["doctor_id"],
            appointment["slot_date"],
            appointment["slot_time"],
            exclude_id=appointment_id,
        ):
            raise ValueError("A conflicting appointment has been confirmed since this was requested.")

        # Update status to confirmed
        confirmed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            """
            UPDATE appointment
               SET status = 'confirmed', confirmed_at = ?
             WHERE appointment_id = ?
            """,
            (confirmed_at, appointment_id),
        )
        conn.commit()

        # Return updated appointment
        updated = conn.execute(
            "SELECT * FROM appointment WHERE appointment_id = ?",
            (appointment_id,),
        ).fetchone()
        return _row_to_dict(updated)
    finally:
        conn.close()


def cancel_appointment(
    appointment_id: int,
    username: str,
    reason: str | None = None,
) -> dict:
    """Cancel an appointment.

    Validates:
      - Appointment exists and is not already cancelled/completed
      - username is either the doctor or patient on the appointment

    Parameters
    ----------
    appointment_id: The appointment to cancel.
    username:       Username of the person cancelling.
    reason:         Optional cancellation reason.

    Returns
    -------
    dict
        The updated appointment record.

    Raises
    ------
    ValueError
        If validation fails.
    """
    conn = get_db()
    try:
        # Fetch appointment
        appointment = conn.execute(
            "SELECT * FROM appointment WHERE appointment_id = ?",
            (appointment_id,),
        ).fetchone()
        if appointment is None:
            raise ValueError("Appointment not found.")
        if appointment["status"] in ("cancelled", "completed"):
            raise ValueError(
                f"Appointment is already {appointment['status']}."
            )

        # Verify username is either the doctor or patient
        user = conn.execute(
            "SELECT user_id, username FROM user WHERE username = ?",
            (username,),
        ).fetchone()
        if user is None:
            raise ValueError("User not found.")

        is_doctor = user["user_id"] == appointment["doctor_id"]
        is_patient = user["user_id"] == appointment["patient_id"]
        if not is_doctor and not is_patient:
            raise ValueError("You are not authorized to cancel this appointment.")

        # Update status to cancelled
        conn.execute(
            """
            UPDATE appointment
               SET status = 'cancelled', cancellation_reason = ?
             WHERE appointment_id = ?
            """,
            (reason, appointment_id),
        )
        conn.commit()

        # Return updated appointment
        updated = conn.execute(
            "SELECT * FROM appointment WHERE appointment_id = ?",
            (appointment_id,),
        ).fetchone()
        return _row_to_dict(updated)
    finally:
        conn.close()


def get_calendar_view(user_id: int, role: str, week_start: str) -> list[dict]:
    """Return all appointments for a 7-day window starting from week_start.

    Filters by role:
      - doctors see appointments where doctor_id matches
      - patients see appointments where patient_id matches

    Each result includes the other party's username.

    Parameters
    ----------
    user_id:    The user's user_id.
    role:       'doctor' or 'patient'.
    week_start: Start date in YYYY-MM-DD format.

    Returns
    -------
    list[dict]
        List of appointment dicts with patient/doctor username included.
    """
    try:
        start_date = datetime.strptime(week_start, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError("week_start must be in YYYY-MM-DD format.")

    end_date = start_date + timedelta(days=6)
    end_date_str = end_date.strftime("%Y-%m-%d")

    conn = get_db()
    try:
        if role == "doctor":
            rows = conn.execute(
                """
                SELECT a.*, u.username AS patient_username
                FROM appointment a
                JOIN user u ON u.user_id = a.patient_id
                WHERE a.doctor_id = ?
                  AND a.slot_date >= ?
                  AND a.slot_date <= ?
                ORDER BY a.slot_date, a.slot_time
                """,
                (user_id, week_start, end_date_str),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT a.*, u.username AS doctor_username
                FROM appointment a
                JOIN user u ON u.user_id = a.doctor_id
                WHERE a.patient_id = ?
                  AND a.slot_date >= ?
                  AND a.slot_date <= ?
                ORDER BY a.slot_date, a.slot_time
                """,
                (user_id, week_start, end_date_str),
            ).fetchall()

        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def get_available_slots(doctor_id: int, date_str: str) -> list[dict]:
    """Return 30-minute slots within doctor's available_hours for the given date.

    Each slot is marked as available=True/False based on existing confirmed
    appointments. For today's date, past slots are marked as unavailable.

    Parameters
    ----------
    doctor_id: The doctor's user_id.
    date_str:  Date string in YYYY-MM-DD format.

    Returns
    -------
    list[dict]
        List of {"time": "HH:MM", "available": bool}.

    Raises
    ------
    ValueError
        If doctor not found or date is invalid.
    """
    conn = get_db()
    try:
        # Fetch doctor's available_hours
        doctor = conn.execute(
            "SELECT user_id, available_hours FROM user WHERE user_id = ? AND role = 'doctor'",
            (doctor_id,),
        ).fetchone()
        if doctor is None:
            raise ValueError("Doctor not found.")

        available_hours_raw = doctor["available_hours"]
        if available_hours_raw:
            try:
                available_hours = json.loads(available_hours_raw)
            except (json.JSONDecodeError, TypeError):
                available_hours = {}
        else:
            available_hours = {}

        # Determine day of week
        day_abbr = _day_of_week(date_str)
        day_schedule = available_hours.get(day_abbr)

        # Default to 09:00-17:00 if no schedule configured
        if not day_schedule:
            day_schedule = {"start": "09:00", "end": "17:00"}

        day_start = _parse_time_minutes(day_schedule["start"])
        day_end = _parse_time_minutes(day_schedule["end"])

        # Generate all 30-minute slots
        slots: list[dict] = []
        current = day_start
        while current + SLOT_DURATION_MIN <= day_end:
            slots.append({"time": _minutes_to_time(current), "available": True})
            current += SLOT_DURATION_MIN

        # Fetch confirmed appointments for this doctor on this date
        confirmed = conn.execute(
            """
            SELECT slot_time, duration_min
            FROM appointment
            WHERE doctor_id = ?
              AND slot_date = ?
              AND status = 'confirmed'
            """,
            (doctor_id, date_str),
        ).fetchall()

        # Mark conflicting slots as unavailable
        for slot in slots:
            slot_start = _parse_time_minutes(slot["time"])
            slot_end = slot_start + SLOT_DURATION_MIN
            for appt in confirmed:
                appt_start = _parse_time_minutes(appt["slot_time"])
                appt_end = appt_start + (appt["duration_min"] or SLOT_DURATION_MIN)
                if slot_start < appt_end and appt_start < slot_end:
                    slot["available"] = False
                    break

        # For today's date, mark past slots as unavailable
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            raise ValueError("date must be in YYYY-MM-DD format.")

        if target_date == date.today():
            now_minutes = datetime.now().hour * 60 + datetime.now().minute
            for slot in slots:
                slot_start = _parse_time_minutes(slot["time"])
                if slot_start <= now_minutes:
                    slot["available"] = False

        # Check max patients per day — if booked count >= max, mark all as unavailable
        max_patients = available_hours.get("_max_patients_per_day", 10)
        booked_count = conn.execute(
            "SELECT COUNT(*) FROM appointment WHERE doctor_id = ? AND slot_date = ? AND status IN ('confirmed', 'pending')",
            (doctor_id, date_str),
        ).fetchone()[0]

        if booked_count >= max_patients:
            for slot in slots:
                slot["available"] = False

        return slots
    finally:
        conn.close()
