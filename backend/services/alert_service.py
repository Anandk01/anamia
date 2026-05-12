"""
alert_service.py — Automated doctor alert service for critical anemia cases.

Provides:
  check_and_alert(prediction_result, username, recipient_email)
      Checks whether the prediction meets the Critical_Threshold
      (HGB < 7.0 g/dL or severity_level == "Severe").
      If triggered:
        1. Inserts a row into alert_log with delivery_status="pending".
        2. Spawns a background thread that attempts to send the HTML email
           up to 3 times at 30-second intervals.
        3. Returns immediately (non-blocking) after the DB insert.

  compose_alert_email(username, hgb, severity, timestamp)
      Returns the HTML email body string.  Exposed for testing.
"""

from __future__ import annotations

import logging
import os
import smtplib
import threading
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Critical threshold constants
# ---------------------------------------------------------------------------

CRITICAL_HGB_THRESHOLD = 7.0
CRITICAL_SEVERITY = "Severe"

# Retry configuration
MAX_RETRIES = 3
RETRY_INTERVAL_SECONDS = 30


# ---------------------------------------------------------------------------
# Email composition
# ---------------------------------------------------------------------------

def compose_alert_email(
    username: str,
    hgb: float,
    severity: str,
    timestamp: str,
) -> str:
    """Compose and return the HTML body for a critical-alert email.

    Parameters
    ----------
    username:  Patient username.
    hgb:       HGB value in g/dL.
    severity:  Severity level string (e.g. "Severe").
    timestamp: UTC timestamp string when the alert was triggered.

    Returns
    -------
    str
        HTML email body containing all four required fields.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <style>
    body {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 30px auto; background: #fff;
                  border-radius: 8px; overflow: hidden;
                  box-shadow: 0 2px 8px rgba(0,0,0,0.12); }}
    .header {{ background: #ef4444; color: #fff; padding: 24px 32px; }}
    .header h1 {{ margin: 0; font-size: 22px; }}
    .body {{ padding: 24px 32px; color: #333; }}
    .field {{ margin-bottom: 12px; }}
    .label {{ font-weight: bold; color: #555; }}
    .value {{ color: #111; }}
    .alert-box {{ background: #fef2f2; border-left: 4px solid #ef4444;
                  padding: 12px 16px; border-radius: 4px; margin: 20px 0; }}
    .footer {{ background: #f9fafb; padding: 16px 32px; font-size: 12px;
               color: #888; border-top: 1px solid #e5e7eb; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>&#9888; Critical Anemia Alert</h1>
    </div>
    <div class="body">
      <p>A patient result has met the <strong>Critical Threshold</strong> and requires
         your immediate attention.</p>

      <div class="field">
        <span class="label">Patient Username:</span>
        <span class="value">{username}</span>
      </div>
      <div class="field">
        <span class="label">HGB Value:</span>
        <span class="value">{hgb:.2f} g/dL</span>
      </div>
      <div class="field">
        <span class="label">Severity Level:</span>
        <span class="value">{severity}</span>
      </div>
      <div class="field">
        <span class="label">Alert Timestamp (UTC):</span>
        <span class="value">{timestamp}</span>
      </div>

      <div class="alert-box">
        <strong>Recommendation:</strong> Please act immediately. Review the patient's
        full CBC results and initiate appropriate clinical intervention without delay.
        Consider urgent referral or blood transfusion if clinically indicated.
      </div>
    </div>
    <div class="footer">
      This is an automated alert from the Anemia Detection and Management System.
      Do not reply to this email.
    </div>
  </div>
</body>
</html>"""


# ---------------------------------------------------------------------------
# SMTP helpers
# ---------------------------------------------------------------------------

def _get_smtp_config() -> dict:
    """Return SMTP configuration from Flask app context or environment variables."""
    try:
        from flask import current_app  # noqa: PLC0415
        return {
            "email_address": current_app.config.get("EMAIL_ADDRESS", ""),
            "email_password": current_app.config.get("EMAIL_PASSWORD", ""),
            "smtp_server": current_app.config.get("SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port": int(current_app.config.get("SMTP_PORT", 587)),
        }
    except RuntimeError:
        # No Flask app context — fall back to environment variables
        return {
            "email_address": os.getenv("EMAIL_ADDRESS", ""),
            "email_password": os.getenv("EMAIL_PASSWORD", ""),
            "smtp_server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            "smtp_port": int(os.getenv("SMTP_PORT", "587")),
        }


def _send_email(
    recipient_email: str,
    subject: str,
    html_body: str,
    smtp_config: dict,
) -> None:
    """Send an HTML email via SMTP with STARTTLS.

    Raises smtplib.SMTPException (or subclass) on failure.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_config["email_address"]
    msg["To"] = recipient_email
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_config["smtp_server"], smtp_config["smtp_port"]) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_config["email_address"], smtp_config["email_password"])
        server.sendmail(smtp_config["email_address"], recipient_email, msg.as_string())


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _insert_alert_log(
    prediction_id: int,
    recipient_email: str,
    recipient_username: str,
    patient_username: str,
    hgb_value: float,
    severity_level: str,
    sent_at: str,
) -> int:
    """Insert a pending alert_log row and return the new alert_id."""
    from db import get_db  # noqa: PLC0415

    conn = get_db()
    try:
        cursor = conn.execute(
            """
            INSERT INTO alert_log
                (prediction_id, recipient_email, recipient_username, patient_username,
                 hgb_value, severity_level, sent_at, delivery_status, retry_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0)
            """,
            (
                prediction_id,
                recipient_email,
                recipient_username,
                patient_username,
                hgb_value,
                severity_level,
                sent_at,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _update_alert_log(alert_id: int, delivery_status: str, retry_count: int) -> None:
    """Update delivery_status and retry_count for an existing alert_log row."""
    from db import get_db  # noqa: PLC0415

    conn = get_db()
    try:
        conn.execute(
            """
            UPDATE alert_log
               SET delivery_status = ?, retry_count = ?
             WHERE alert_id = ?
            """,
            (delivery_status, retry_count, alert_id),
        )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Retry loop (runs in background thread)
# ---------------------------------------------------------------------------

def _retry_send(
    alert_id: int,
    recipient_email: str,
    subject: str,
    html_body: str,
    smtp_config: dict,
) -> None:
    """Attempt to send the alert email up to MAX_RETRIES times.

    Runs in a background thread.  Updates alert_log after each attempt.
    Sleeps RETRY_INTERVAL_SECONDS between attempts.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _send_email(recipient_email, subject, html_body, smtp_config)
            _update_alert_log(alert_id, "sent", attempt)
            logger.info(
                "Alert %d sent successfully on attempt %d to %s",
                alert_id,
                attempt,
                recipient_email,
            )
            return  # Success — stop retrying
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Alert %d send attempt %d/%d failed: %s",
                alert_id,
                attempt,
                MAX_RETRIES,
                exc,
            )
            _update_alert_log(alert_id, "failed", attempt)

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_INTERVAL_SECONDS)

    logger.error(
        "Alert %d failed after %d attempts — giving up.", alert_id, MAX_RETRIES
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_and_alert(
    prediction_result: dict,
    username: str,
    recipient_email: str,
) -> bool:
    """Check whether the prediction meets the Critical_Threshold and, if so, alert.

    The function returns immediately after inserting the alert_log row.
    Email delivery is handled asynchronously in a background thread.

    Parameters
    ----------
    prediction_result:
        Dict containing at least:
          - "hgb"            : float — HGB value in g/dL
          - "severity_level" : str   — e.g. "Severe", "Moderate", etc.
          - "prediction_id"  : int   — (optional) DB prediction row ID
    username:
        Patient username (used in the email body and alert_log).
    recipient_email:
        Email address of the doctor/recipient to notify.

    Returns
    -------
    bool
        True if an alert was triggered, False otherwise.
    """
    hgb = float(prediction_result.get("hgb", 0.0))
    severity = prediction_result.get("severity_level", "")
    prediction_id = int(prediction_result.get("prediction_id", 0))

    # Check Critical_Threshold
    if hgb >= CRITICAL_HGB_THRESHOLD and severity != CRITICAL_SEVERITY:
        return False

    # UTC timestamp for the alert
    sent_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Compose email
    html_body = compose_alert_email(username, hgb, severity, sent_at)
    subject = f"[CRITICAL ALERT] Anemia Patient: {username} — HGB {hgb:.2f} g/dL ({severity})"

    # Insert pending row into alert_log (synchronous — before returning)
    alert_id = _insert_alert_log(
        prediction_id=prediction_id,
        recipient_email=recipient_email,
        recipient_username=recipient_email,  # use email as username when not provided
        patient_username=username,
        hgb_value=hgb,
        severity_level=severity,
        sent_at=sent_at,
    )

    # Capture SMTP config in the current context (may be Flask app context)
    smtp_config = _get_smtp_config()

    # Launch background thread for email delivery with retry
    thread = threading.Thread(
        target=_retry_send,
        args=(alert_id, recipient_email, subject, html_body, smtp_config),
        daemon=True,
        name=f"alert-{alert_id}",
    )
    thread.start()

    logger.info(
        "Alert triggered for patient '%s' (HGB=%.2f, severity=%s). "
        "alert_id=%d, recipient=%s",
        username,
        hgb,
        severity,
        alert_id,
        recipient_email,
    )
    return True
