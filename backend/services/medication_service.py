"""
medication_service.py — Business logic for the Medication Tracker module.

Provides:
  prescribe_medication(doctor_username, patient_username, name, dose_mg, frequency, start_date, end_date)
      Create a new medication entry prescribed by a doctor.

  get_todays_schedule(username)
      Return medications due today with taken status.

  log_medication(med_id, username, skipped, notes)
      Log a medication dose with duplicate prevention.

  calculate_adherence(username, days)
      Calculate adherence percentage and streak.

  deactivate_medication(med_id, doctor_username)
      Deactivate a medication.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from db import get_db

logger = logging.getLogger(__name__)

VALID_FREQUENCIES = ("daily", "twice", "thrice", "weekly")

# Mapping from frequency to expected doses per day
DOSES_PER_DAY = {
    "daily": 1,
    "twice": 2,
    "thrice": 3,
    "weekly": 1,  # only on the matching day of week
}

# Dose window durations in hours for duplicate prevention
DOSE_WINDOW_HOURS = {
    "daily": 24,
    "twice": 12,
    "thrice": 8,
    "weekly": 24,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row) -> dict:
    """Convert a sqlite3.Row to a plain dict."""
    if row is None:
        return {}
    return dict(row)


def _today_str() -> str:
    """Return today's date as YYYY-MM-DD string."""
    return date.today().strftime("%Y-%m-%d")


def _is_weekly_due(start_date_str: str, check_date: date) -> bool:
    """Check if a weekly medication is due on check_date.

    Weekly medications are due on the same day of the week as their start_date.
    """
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False
    return start_date.weekday() == check_date.weekday()


def _medication_active_on_date(med: dict, check_date: date) -> bool:
    """Check if a medication is active on the given date.

    Active means: active=1, start_date <= check_date, and
    (end_date is None or end_date >= check_date).
    """
    if not med.get("active", 1):
        return False

    try:
        start = datetime.strptime(med["start_date"], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False

    if check_date < start:
        return False

    end_date_str = med.get("end_date")
    if end_date_str:
        try:
            end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if check_date > end:
                return False
        except (ValueError, TypeError):
            pass  # Treat invalid end_date as no end date

    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def prescribe_medication(
    doctor_username: str,
    patient_username: str,
    name: str,
    dose_mg: float,
    frequency: str,
    start_date: str,
    end_date: str | None = None,
) -> dict:
    """Create a new medication entry prescribed by a doctor.

    Validates:
      - doctor_username exists with role='doctor'
      - patient_username exists with role='patient'
      - frequency is one of: daily, twice, thrice, weekly

    Parameters
    ----------
    doctor_username:  Username of the prescribing doctor.
    patient_username: Username of the patient.
    name:             Medication name.
    dose_mg:          Dose in milligrams.
    frequency:        One of 'daily', 'twice', 'thrice', 'weekly'.
    start_date:       Start date in YYYY-MM-DD format.
    end_date:         Optional end date in YYYY-MM-DD format.

    Returns
    -------
    dict
        The created medication record.

    Raises
    ------
    ValueError
        If any validation fails.
    """
    # Validate frequency
    if frequency not in VALID_FREQUENCIES:
        raise ValueError(
            f"Invalid frequency '{frequency}'. Must be one of: {', '.join(VALID_FREQUENCIES)}"
        )

    conn = get_db()
    try:
        # Validate doctor exists with role='doctor'
        doctor = conn.execute(
            "SELECT username FROM user WHERE username = ? AND role = 'doctor'",
            (doctor_username,),
        ).fetchone()
        if doctor is None:
            raise ValueError("Doctor not found or user is not a doctor.")

        # Validate patient exists with role='patient'
        patient = conn.execute(
            "SELECT username FROM user WHERE username = ? AND role = 'patient'",
            (patient_username,),
        ).fetchone()
        if patient is None:
            raise ValueError("Patient not found or user is not a patient.")

        # Insert medication
        created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.execute(
            """
            INSERT INTO medication
                (username, name, dose_mg, frequency, start_date, end_date,
                 prescribed_by, active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (patient_username, name, dose_mg, frequency, start_date, end_date,
             doctor_username, created_at),
        )
        conn.commit()

        # Fetch and return the created medication
        medication = conn.execute(
            "SELECT * FROM medication WHERE med_id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return _row_to_dict(medication)
    finally:
        conn.close()


def get_todays_schedule(username: str) -> list[dict]:
    """Get all active medications due today with taken status.

    For each medication, determines how many doses are due today based on
    frequency:
      - daily = 1 dose
      - twice = 2 doses
      - thrice = 3 doses
      - weekly = 1 dose (only on the same day of week as start_date)

    Checks medication_log for today to see which doses are already taken.

    Parameters
    ----------
    username: The patient's username.

    Returns
    -------
    list[dict]
        List of {med_id, name, dose_mg, frequency, doses_due, doses_taken,
                 taken: bool, taken_at: str|None}.
    """
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")

    conn = get_db()
    try:
        # Get all active medications for the user
        medications = conn.execute(
            """
            SELECT * FROM medication
            WHERE username = ? AND active = 1
            """,
            (username,),
        ).fetchall()

        schedule = []
        for med in medications:
            med_dict = _row_to_dict(med)

            # Check if medication is active on today's date
            if not _medication_active_on_date(med_dict, today):
                continue

            # For weekly medications, only due on the start_date's day of week
            if med_dict["frequency"] == "weekly":
                if not _is_weekly_due(med_dict["start_date"], today):
                    continue

            # Count doses taken today
            logs_today = conn.execute(
                """
                SELECT log_id, taken_at, skipped FROM medication_log
                WHERE med_id = ?
                  AND date(taken_at) = ?
                  AND skipped = 0
                """,
                (med_dict["med_id"], today_str),
            ).fetchall()

            doses_due = DOSES_PER_DAY.get(med_dict["frequency"], 1)
            doses_taken = len(logs_today)

            # Get the most recent taken_at for display
            last_taken_at = None
            if logs_today:
                last_taken_at = logs_today[-1]["taken_at"]

            taken = doses_taken >= doses_due

            schedule.append({
                "med_id": med_dict["med_id"],
                "name": med_dict["name"],
                "dose_mg": med_dict["dose_mg"],
                "dose_unit": med_dict.get("dose_unit", "mg"),
                "frequency": med_dict["frequency"],
                "reminder_times": med_dict.get("reminder_times"),
                "doses_due": doses_due,
                "doses_taken": doses_taken,
                "taken": taken,
                "taken_at": last_taken_at,
            })

        return schedule
    finally:
        conn.close()


def log_medication(
    med_id: int,
    username: str,
    skipped: bool = False,
    notes: str | None = None,
) -> dict:
    """Log a medication dose with duplicate prevention.

    Validates:
      - med_id exists and belongs to username
      - Medication is active
      - No duplicate log within the current dose window

    Dose windows:
      - daily: same day (24h window)
      - twice: same 12h window
      - thrice: same 8h window
      - weekly: same day (24h window)

    Parameters
    ----------
    med_id:   The medication ID.
    username: The patient's username.
    skipped:  Whether the dose was skipped.
    notes:    Optional notes.

    Returns
    -------
    dict
        The created log entry.

    Raises
    ------
    ValueError
        If validation fails or duplicate detected.
    """
    conn = get_db()
    try:
        # Verify med_id exists and belongs to username
        medication = conn.execute(
            "SELECT * FROM medication WHERE med_id = ? AND username = ?",
            (med_id, username),
        ).fetchone()
        if medication is None:
            raise ValueError("Medication not found or does not belong to this user.")

        med_dict = _row_to_dict(medication)

        # Verify medication is active
        if not med_dict.get("active", 0):
            raise ValueError("Medication is not active.")

        # Duplicate prevention: check within the dose window
        now = datetime.utcnow()
        frequency = med_dict["frequency"]
        window_hours = DOSE_WINDOW_HOURS.get(frequency, 24)

        window_start = now - timedelta(hours=window_hours)
        window_start_str = window_start.strftime("%Y-%m-%d %H:%M:%S")

        # Count logs in the current window
        existing_logs = conn.execute(
            """
            SELECT COUNT(*) as cnt FROM medication_log
            WHERE med_id = ?
              AND taken_at >= ?
            """,
            (med_id, window_start_str),
        ).fetchone()

        max_doses_in_window = 1  # Each window allows exactly 1 dose
        if existing_logs and existing_logs["cnt"] >= max_doses_in_window:
            raise ValueError(
                f"Dose already logged within the current {window_hours}h window. "
                "Please wait before logging another dose."
            )

        # Insert log entry
        taken_at = now.strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.execute(
            """
            INSERT INTO medication_log (med_id, taken_at, skipped, notes)
            VALUES (?, ?, ?, ?)
            """,
            (med_id, taken_at, 1 if skipped else 0, notes),
        )
        conn.commit()

        # Fetch and return the created log
        log_entry = conn.execute(
            "SELECT * FROM medication_log WHERE log_id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return _row_to_dict(log_entry)
    finally:
        conn.close()


def calculate_adherence(username: str, days: int = 7) -> dict:
    """Calculate medication adherence over a given period.

    For each active medication, calculates expected doses over the period
    based on frequency and active date range. Counts actual taken logs
    (skipped=0) in the period.

    Parameters
    ----------
    username: The patient's username.
    days:     Number of days to look back (default 7).

    Returns
    -------
    dict
        {adherence_percent: float, total_doses: int, taken_doses: int, streak: int}
    """
    today = date.today()
    period_start = today - timedelta(days=days - 1)

    conn = get_db()
    try:
        # Get all active medications for the user
        medications = conn.execute(
            """
            SELECT * FROM medication
            WHERE username = ? AND active = 1
            """,
            (username,),
        ).fetchall()

        total_expected = 0
        total_taken = 0

        for med in medications:
            med_dict = _row_to_dict(med)
            frequency = med_dict["frequency"]

            # Calculate expected doses for each day in the period
            for day_offset in range(days):
                check_date = period_start + timedelta(days=day_offset)

                if not _medication_active_on_date(med_dict, check_date):
                    continue

                if frequency == "weekly":
                    if _is_weekly_due(med_dict["start_date"], check_date):
                        total_expected += 1
                else:
                    total_expected += DOSES_PER_DAY[frequency]

            # Count actual taken logs in the period
            period_start_str = period_start.strftime("%Y-%m-%d")
            today_str = today.strftime("%Y-%m-%d")
            taken_count = conn.execute(
                """
                SELECT COUNT(*) as cnt FROM medication_log
                WHERE med_id = ?
                  AND date(taken_at) >= ?
                  AND date(taken_at) <= ?
                  AND skipped = 0
                """,
                (med_dict["med_id"], period_start_str, today_str),
            ).fetchone()

            if taken_count:
                total_taken += taken_count["cnt"]

        # Calculate adherence percentage, clamped to [0, 100]
        if total_expected > 0:
            adherence_percent = (total_taken / total_expected) * 100
            adherence_percent = max(0.0, min(100.0, adherence_percent))
        else:
            adherence_percent = 100.0  # No medications expected = perfect adherence

        # Calculate streak: consecutive days from today backwards where all
        # doses were taken
        streak = _calculate_streak(conn, username, medications, today)

        return {
            "adherence_percent": round(adherence_percent, 1),
            "total_doses": total_expected,
            "taken_doses": total_taken,
            "streak": streak,
        }
    finally:
        conn.close()


def _calculate_streak(conn, username: str, medications, today: date) -> int:
    """Calculate consecutive days from today backwards where all doses were taken.

    A day counts toward the streak if every expected dose for that day has a
    corresponding non-skipped log entry.
    """
    streak = 0

    for day_offset in range(365):  # Look back up to a year
        check_date = today - timedelta(days=day_offset)
        check_date_str = check_date.strftime("%Y-%m-%d")

        day_expected = 0
        day_taken = 0

        for med in medications:
            med_dict = _row_to_dict(med)
            frequency = med_dict["frequency"]

            if not _medication_active_on_date(med_dict, check_date):
                continue

            if frequency == "weekly":
                if _is_weekly_due(med_dict["start_date"], check_date):
                    day_expected += 1
                else:
                    continue
            else:
                day_expected += DOSES_PER_DAY[frequency]

            # Count taken logs for this med on this day
            taken = conn.execute(
                """
                SELECT COUNT(*) as cnt FROM medication_log
                WHERE med_id = ?
                  AND date(taken_at) = ?
                  AND skipped = 0
                """,
                (med_dict["med_id"], check_date_str),
            ).fetchone()

            if taken:
                day_taken += taken["cnt"]

        # If no medications were expected this day, skip it (don't break streak)
        if day_expected == 0:
            continue

        # Check if all expected doses were taken
        if day_taken >= day_expected:
            streak += 1
        else:
            break

    return streak


def deactivate_medication(med_id: int, doctor_username: str) -> dict:
    """Deactivate a medication.

    Validates:
      - med_id exists
      - doctor_username matches prescribed_by or is any doctor

    Parameters
    ----------
    med_id:           The medication ID to deactivate.
    doctor_username:  Username of the doctor performing the action.

    Returns
    -------
    dict
        The updated medication record.

    Raises
    ------
    ValueError
        If validation fails.
    """
    conn = get_db()
    try:
        # Verify med_id exists
        medication = conn.execute(
            "SELECT * FROM medication WHERE med_id = ?",
            (med_id,),
        ).fetchone()
        if medication is None:
            raise ValueError("Medication not found.")

        # Verify doctor_username is a valid doctor
        doctor = conn.execute(
            "SELECT username FROM user WHERE username = ? AND role = 'doctor'",
            (doctor_username,),
        ).fetchone()
        if doctor is None:
            raise ValueError("Doctor not found or user is not a doctor.")

        # Set active=0
        conn.execute(
            "UPDATE medication SET active = 0 WHERE med_id = ?",
            (med_id,),
        )
        conn.commit()

        # Return updated medication
        updated = conn.execute(
            "SELECT * FROM medication WHERE med_id = ?",
            (med_id,),
        ).fetchone()
        return _row_to_dict(updated)
    finally:
        conn.close()
