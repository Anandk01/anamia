"""
analytics_service.py — Dashboard analytics and metrics.

Provides:
  get_overview_metrics, get_trend_data, get_adherence_summary,
  get_appointments_summary, get_system_health
"""

from datetime import date, timedelta

from db import get_db


def get_overview_metrics(doctor_username=None, date_range=None):
    """Get high-level dashboard metrics."""
    conn = get_db()
    try:
        metrics = {}
        metrics['total_patients'] = conn.execute(
            "SELECT COUNT(*) FROM user WHERE role = 'patient'"
        ).fetchone()[0]
        metrics['total_doctors'] = conn.execute(
            "SELECT COUNT(*) FROM user WHERE role = 'doctor'"
        ).fetchone()[0]
        metrics['total_predictions'] = conn.execute(
            "SELECT COUNT(*) FROM prediction"
        ).fetchone()[0]
        metrics['total_appointments'] = conn.execute(
            "SELECT COUNT(*) FROM appointment"
        ).fetchone()[0]
        metrics['anemia_detected_count'] = conn.execute(
            "SELECT COUNT(*) FROM prediction WHERE anemia_detected = 1"
        ).fetchone()[0]

        if doctor_username:
            metrics['my_patients'] = conn.execute(
                """SELECT COUNT(*) FROM doctor_patient dp
                   JOIN user u ON u.user_id = dp.doctor_id
                   WHERE u.username = ?""",
                (doctor_username,),
            ).fetchone()[0]

        return metrics
    finally:
        conn.close()


def get_trend_data(metric, period_days=30):
    """Get daily trend data for a given metric over period_days."""
    conn = get_db()
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)
        start_str = start_date.strftime("%Y-%m-%d")

        if metric == 'predictions':
            rows = conn.execute(
                """SELECT date(date) as day, COUNT(*) as count
                   FROM prediction WHERE date >= ?
                   GROUP BY date(date) ORDER BY day""",
                (start_str,),
            ).fetchall()
        elif metric == 'appointments':
            rows = conn.execute(
                """SELECT slot_date as day, COUNT(*) as count
                   FROM appointment WHERE slot_date >= ?
                   GROUP BY slot_date ORDER BY day""",
                (start_str,),
            ).fetchall()
        elif metric == 'registrations':
            rows = conn.execute(
                """SELECT date(created_at) as day, COUNT(*) as count
                   FROM user WHERE created_at >= ?
                   GROUP BY date(created_at) ORDER BY day""",
                (start_str,),
            ).fetchall()
        else:
            return []

        return [{"date": r["day"], "count": r["count"]} for r in rows]
    finally:
        conn.close()


def get_adherence_summary(doctor_username=None):
    """Get medication adherence summary across patients."""
    conn = get_db()
    try:
        if doctor_username:
            rows = conn.execute(
                """SELECT m.username, COUNT(ml.log_id) as taken,
                   COUNT(CASE WHEN ml.skipped = 1 THEN 1 END) as skipped
                   FROM medication m
                   LEFT JOIN medication_log ml ON ml.med_id = m.med_id
                   WHERE m.prescribed_by = ? AND m.active = 1
                   GROUP BY m.username""",
                (doctor_username,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT m.username, COUNT(ml.log_id) as taken,
                   COUNT(CASE WHEN ml.skipped = 1 THEN 1 END) as skipped
                   FROM medication m
                   LEFT JOIN medication_log ml ON ml.med_id = m.med_id
                   WHERE m.active = 1
                   GROUP BY m.username"""
            ).fetchall()

        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_appointments_summary(period_days=30):
    """Get appointment statistics for the given period."""
    conn = get_db()
    try:
        start = (date.today() - timedelta(days=period_days)).strftime("%Y-%m-%d")
        row = conn.execute(
            """SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN status='confirmed' THEN 1 END) as confirmed,
                COUNT(CASE WHEN status='cancelled' THEN 1 END) as cancelled,
                COUNT(CASE WHEN status='completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status='pending' THEN 1 END) as pending
               FROM appointment WHERE slot_date >= ?""",
            (start,),
        ).fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def get_system_health():
    """Get basic system health metrics."""
    conn = get_db()
    try:
        db_ok = True
        conn.execute("SELECT 1")
    except Exception:
        db_ok = False
    finally:
        conn.close()

    return {
        "database": "healthy" if db_ok else "unhealthy",
        "status": "operational",
    }
