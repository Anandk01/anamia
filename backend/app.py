"""
Anemia Detection and Management System — Flask Application Factory

Entry point for the ADMS backend. Provides a `create_app()` factory function
that wires together all Blueprints, loads ML models, initialises the database,
and configures CORS and environment variables.
"""

import os
import logging

import joblib
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

# Load environment variables from .env file as early as possible
load_dotenv()

logger = logging.getLogger(__name__)


# ─── ML Model Paths ───────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_MODELS_DIR = os.path.join(_BASE_DIR, "models")

RF_CLASSIFIER_PATH = os.path.join(_MODELS_DIR, "rf_anemia_classifier.pkl")
RF_SCALER_PATH = os.path.join(_MODELS_DIR, "rf_scaler.pkl")
GB_SEVERITY_PATH = os.path.join(_MODELS_DIR, "gb_severity_classifier.pkl")


def _load_model(path: str, config_key: str, app: Flask) -> None:
    """
    Attempt to load a joblib model from *path* and store it in app.config
    under *config_key*. If the file does not exist or fails to load, the
    config value is set to None and a warning is logged.
    """
    if not os.path.exists(path):
        logger.warning(
            "Model file not found: %s — app.config['%s'] set to None", path, config_key
        )
        app.config[config_key] = None
        return

    try:
        app.config[config_key] = joblib.load(path)
        logger.info("Loaded model '%s' from %s", config_key, path)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to load model '%s' from %s: %s — set to None",
            config_key,
            path,
            exc,
        )
        app.config[config_key] = None


def create_app() -> Flask:
    """
    Application factory.

    Creates and configures the Flask application:
      1. Loads environment variables (already done at module level via load_dotenv)
      2. Configures SMTP / email settings from .env
      3. Loads ML models into app.config
      4. Initialises the database (via db.py — imported with try/except because
         db.py may not exist yet during early development)
      5. Registers all 8 Blueprints
      6. Enables CORS

    Returns the configured Flask app instance.
    """
    app = Flask(__name__)

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    # ── Email / SMTP configuration ────────────────────────────────────────────
    app.config["EMAIL_ADDRESS"] = os.getenv("EMAIL_ADDRESS", "")
    app.config["EMAIL_PASSWORD"] = os.getenv("EMAIL_PASSWORD", "")
    app.config["SMTP_SERVER"] = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    app.config["SMTP_PORT"] = int(os.getenv("SMTP_PORT", "587"))

    # ── ML Models ─────────────────────────────────────────────────────────────
    _load_model(RF_CLASSIFIER_PATH, "RF_CLASSIFIER", app)
    _load_model(RF_SCALER_PATH, "RF_SCALER", app)
    _load_model(GB_SEVERITY_PATH, "GB_SEVERITY", app)

    # ── Database initialisation ───────────────────────────────────────────────
    # db.py is implemented in task 1.3; guard with try/except so the app can
    # start even before that file exists.
    try:
        from db import init_db  # noqa: PLC0415
        with app.app_context():
            init_db()
    except ImportError:
        logger.warning(
            "backend/db.py not found — skipping database initialisation. "
            "Implement db.py (task 1.3) to enable DB setup."
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database initialisation failed: %s", exc)

    # ── Blueprint registration ─────────────────────────────────────────────────
    # All blueprints are imported from the blueprints package.
    from blueprints import (  # noqa: PLC0415
        admin_bp,
        alerts_bp,
        analytics_bp,
        appointments_bp,
        assignment_bp,
        auth_bp,
        chat_bp,
        education_bp,
        forum_bp,
        medication_bp,
        notifications_bp,
        ocr_bp,
        predict_bp,
        prescriptions_bp,
        profile_bp,
        reports_bp,
        retrain_bp,
    )

    app.register_blueprint(auth_bp)
    app.register_blueprint(predict_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(retrain_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(medication_bp)
    app.register_blueprint(forum_bp)
    app.register_blueprint(education_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(prescriptions_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(assignment_bp)

    # ── Flask-SocketIO (optional) ─────────────────────────────────────────────
    try:
        from flask_socketio import SocketIO
        socketio = SocketIO(app, cors_allowed_origins="*")
        from services.websocket_service import init_socketio
        init_socketio(socketio)
        app.config['SOCKETIO'] = socketio
        logger.info("Flask-SocketIO initialized successfully.")
    except ImportError:
        logger.warning("flask-socketio not installed — WebSocket features disabled.")
    except Exception as exc:
        logger.warning("SocketIO initialization failed: %s", exc)

    # ── Health endpoint ───────────────────────────────────────────────────────
    @app.route("/health", methods=["GET"])
    def health():
        """Return service health: model availability and DB connectivity."""
        from flask import jsonify  # noqa: PLC0415

        # Model checks
        rf_ok = app.config.get("RF_CLASSIFIER") is not None
        gb_ok = app.config.get("GB_SEVERITY") is not None

        # DB check — attempt a trivial query
        db_ok = False
        try:
            from db import get_db  # noqa: PLC0415
            conn = get_db()
            conn.execute("SELECT 1")
            conn.close()
            db_ok = True
        except Exception:  # noqa: BLE001
            db_ok = False

        return jsonify(
            {
                "status": "ok",
                "models": {
                    "rf_classifier": rf_ok,
                    "gb_severity": gb_ok,
                },
                "db": db_ok,
            }
        )

    logger.info("ADMS Flask application created successfully.")
    return app


# ─── Development entry point ──────────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    socketio = app.config.get('SOCKETIO')
    if socketio:
        socketio.run(app, debug=True)
    else:
        app.run(debug=True)
