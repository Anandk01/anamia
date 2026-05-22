"""
notification_service.py — Notification management service.

Provides:
  create_notification, schedule_medication_reminders,
  schedule_appointment_reminder, send_notification, get_unread_count
"""

from datetime import datetime, timedelta, timezone

from db import get_db


def create_notification(username, type, title, message, delivery_method='push', scheduled_at=None):
    """Create a notification for a user."""
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO notification (username, type, title, message, delivery_method, scheduled_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, type, title, message, delivery_method, scheduled_at),
        )
        conn.commit()
        return {"notification_id": cursor.lastrowid}
    finally:
        conn.close()


def schedule_medication_reminders(username):
    """Create medication reminder notifications for today's schedule."""
    conn = get_db()
    try:
        meds = conn.execute(
            "SELECT * FROM medication WHERE username = ? AND active = 1",
            (username,),
        ).fetchall()

        created = 0
        for med in meds:
            create_notification(
                username=username,
                type='medication',
                title=f"Time to take {med['name']}",
                message=f"Take {med['dose_mg']}mg of {med['name']}",
                delivery_method='push',
            )
            created += 1

        return {"reminders_created": created}
    finally:
        conn.close()


def schedule_appointment_reminder(appointment_id):
    """Create a reminder notification for an upcoming appointment."""
    conn = get_db()
    try:
        appt = conn.execute(
            """SELECT a.*, u.username as patient_username
               FROM appointment a
               JOIN user u ON u.user_id = a.patient_id
               WHERE a.appointment_id = ?""",
            (appointment_id,),
        ).fetchone()

        if not appt:
            return {"error": "Appointment not found"}

        create_notification(
            username=appt['patient_username'],
            type='appointment',
            title='Upcoming Appointment',
            message=f"You have an appointment on {appt['slot_date']} at {appt['slot_time']}",
            delivery_method='push',
            scheduled_at=appt['slot_date'],
        )
        return {"scheduled": True}
    finally:
        conn.close()


def send_notification(notification_id):
    """Mark a notification as sent (placeholder — no actual push for now)."""
    conn = get_db()
    try:
        sent_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE notification SET sent_at = ? WHERE notification_id = ?",
            (sent_at, notification_id),
        )
        conn.commit()
        return {"sent": True}
    finally:
        conn.close()


def get_unread_count(username):
    """Get count of unread notifications for a user."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as count FROM notification WHERE username = ? AND read = 0",
            (username,),
        ).fetchone()
        return row["count"] if row else 0
    finally:
        conn.close()
