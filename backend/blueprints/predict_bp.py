"""
Prediction Blueprint — /api

Routes:
    POST /api/predict   → full prediction pipeline (auth: patient, doctor)
"""

import json
import logging
from datetime import datetime

from flask import Blueprint, g, jsonify, request

from db import get_db
from middleware.auth import require_auth
from middleware.rbac import require_role
from schemas.cbc_schema import validate_cbc
from services.prediction_service import get_prediction_service

logger = logging.getLogger(__name__)

predict_bp = Blueprint("predict", __name__, url_prefix="/api")

# ---------------------------------------------------------------------------
# Optional service imports (tasks 6 and 7 — use try/except fallback)
# ---------------------------------------------------------------------------
try:
    from services.recommendation_service import (  # noqa: PLC0415
        get_diet_recommendations,
        get_health_tips,
    )
    _HAS_RECOMMENDATIONS = True
except ImportError:
    _HAS_RECOMMENDATIONS = False

try:
    from services.alert_service import check_and_alert  # noqa: PLC0415
    _HAS_ALERTS = True
except ImportError:
    _HAS_ALERTS = False


# ---------------------------------------------------------------------------
# POST /api/predict
# ---------------------------------------------------------------------------

@predict_bp.post("/predict")
@require_auth
@require_role("patient", "doctor", "admin")
def predict():
    """
    Run the full anemia prediction pipeline on submitted CBC values.

    Request body (JSON):
        {
            "rbc": float, "mcv": float, "mch": float, "mchc": float,
            "rdw": float, "tlc": float, "plt": float, "hgb": float
        }

    Returns:
        200: {"status": "ok", "prediction": {...full result...}}
        400: {"status": "error", "message": "..."}
        500: {"status": "error", "message": "..."}
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"status": "error", "message": "Request body must be JSON"}), 400

    # --- Validate CBC schema ---
    cbc_dict, errors = validate_cbc(data)
    if errors:
        return jsonify({"status": "error", "message": "; ".join(errors)}), 400

    # --- Run prediction pipeline ---
    try:
        svc = get_prediction_service()
        result = svc.predict(cbc_dict)
    except Exception as exc:
        logger.exception("Prediction pipeline failed")
        return jsonify({"status": "error", "message": f"Prediction failed: {exc}"}), 500

    current_user = g.current_user
    username = current_user["username"]
    role = current_user.get("role", "patient")

    # --- Fetch user profile for recommendations ---
    vegan_diet = False
    age = None
    sex = None
    try:
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT vegan_diet, age, sex FROM user WHERE username = ?",
                (username,),
            ).fetchone()
            if row:
                vegan_diet = bool(row["vegan_diet"])
                age = row["age"]
                sex = row["sex"]
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Could not fetch user profile for %s: %s", username, exc)

    # --- Recommendations (task 6 — fallback to empty lists) ---
    diet_recs = []
    health_tips = []
    if _HAS_RECOMMENDATIONS:
        try:
            diet_recs = get_diet_recommendations(
                result["anemia_type"], vegan=vegan_diet
            )
            health_tips = get_health_tips(
                result["severity_level"],
                result["anemia_type"],
                age=age,
                sex=sex,
            )
        except Exception as exc:
            logger.warning("Recommendation service failed: %s", exc)

    result["diet_recs"] = diet_recs
    result["health_tips"] = health_tips

    # --- Alert service (task 7 — fallback silently) ---
    if _HAS_ALERTS:
        try:
            # Determine recipient email
            if role == "doctor":
                recipient_email = current_user.get("email", "")
            else:
                # For patients, use configured alert email from app config
                from flask import current_app  # noqa: PLC0415
                recipient_email = current_app.config.get("EMAIL_ADDRESS", "")

            if recipient_email:
                check_and_alert(result, username, recipient_email)
        except Exception as exc:
            logger.warning("Alert service failed: %s", exc)

    # --- Persist to DB ---
    prediction_id = None
    target_patient = data.get("username", username) if role == "doctor" else username
    try:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        try:
            cursor = conn.execute(
                """
                INSERT INTO prediction (
                    username, rbc, mcv, mch, mchc, rdw, tlc, plt, hgb,
                    anemia_detected, severity_level, anemia_type, confidence,
                    explanation, diet_recs, health_tips, risk_category, date,
                    doctor_username
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    target_patient,
                    cbc_dict["rbc"],
                    cbc_dict["mcv"],
                    cbc_dict["mch"],
                    cbc_dict["mchc"],
                    cbc_dict["rdw"],
                    cbc_dict["tlc"],
                    cbc_dict["plt"],
                    cbc_dict["hgb"],
                    result["anemia_detected"],
                    result["severity_level"],
                    result["anemia_type"],
                    result["anemia_confidence"],
                    json.dumps(result["explanation"]),
                    json.dumps(diet_recs),
                    json.dumps(health_tips),
                    "N/A",
                    now,
                    username if role == "doctor" else None,
                ),
            )
            conn.commit()
            prediction_id = cursor.lastrowid
        finally:
            conn.close()
    except Exception as exc:
        logger.exception("Failed to persist prediction to DB")
        return jsonify({"status": "error", "message": f"DB persistence failed: {exc}"}), 500

    # --- Notify patient of new report (Spec 04) ---
    try:
        from utils import notify_user  # noqa: PLC0415
        if role == "doctor" and target_patient != username:
            notify_user(target_patient, 'new_report', {
                'prediction_id': prediction_id,
                'doctor_username': username,
                'risk_category': result.get('risk_category', 'N/A'),
                'severity': result['severity_level'],
                'anemia_type': result['anemia_type'],
                'hgb': float(cbc_dict['hgb']),
                'date': datetime.utcnow().isoformat()
            })
    except Exception as exc:
        logger.warning("Failed to notify patient: %s", exc)

    # --- Auto-create alerts based on HGB (Spec 04) ---
    try:
        hgb_val = float(cbc_dict['hgb'])
        if hgb_val < 10.0:
            from utils import notify_user as _nu, notify_admin as _na  # noqa: PLC0415
            severity_alert = 'critical' if hgb_val < 8.0 else 'warning'
            alert_msg = f"{'Critical' if hgb_val < 8.0 else 'Low'} HGB detected: {hgb_val} g/dL for patient {target_patient}."
            conn = get_db()
            try:
                conn.execute(
                    """INSERT INTO alert_log (prediction_id, recipient_email, recipient_username, patient_username, hgb_value, severity_level, sent_at, delivery_status)
                       VALUES (?, '', ?, ?, ?, ?, datetime('now'), 'auto')""",
                    (prediction_id, username, target_patient, hgb_val, severity_alert),
                )
                conn.commit()
            finally:
                conn.close()
            payload = {'patient_username': target_patient, 'message': alert_msg, 'severity': severity_alert, 'hgb': hgb_val}
            _na('critical_alert', payload)
            _nu(username, 'patient_alert', payload)
            if target_patient != username:
                _nu(target_patient, 'my_alert', payload)
    except Exception as exc:
        logger.warning("Auto-alert creation failed: %s", exc)

    # --- AI Report Generation (Gemini) ---
    ai_report = None
    ai_sources = []
    try:
        from services.gemini_report_service import generate_ai_report
        ai_result = generate_ai_report({**result, "cbc": cbc_dict}, username)
        ai_report = ai_result.get("ai_report")
        ai_sources = ai_result.get("sources", [])
    except Exception as exc:
        logger.warning("AI report generation failed: %s", exc)

    return jsonify({
        "status": "ok",
        "prediction_id": prediction_id,
        "anemia_detected": result["anemia_detected"],
        "severity_level": result["severity_level"],
        "anemia_type": result["anemia_type"],
        "confidence": result["anemia_confidence"],
        "explanation": result["explanation"],
        "diet_recs": diet_recs,
        "health_tips": health_tips,
        "cbc": cbc_dict,
        "anemia_confidence": result["anemia_confidence"],
        "severity_confidence": result["severity_confidence"],
        "type_confidence": result["type_confidence"],
        "hgb": result["hgb"],
        "ai_report": ai_report,
        "ai_sources": ai_sources,
    }), 200
