"""
Retrain Blueprint — /api/retrain

Handles ML model retraining workflow: dataset upload, training trigger,
admin approval, rollback, and status polling.

Routes:
    POST /api/retrain/upload    → upload new training dataset
    POST /api/retrain/start     → trigger retraining job (background thread)
    POST /api/retrain/approve   → admin approves new model
    POST /api/retrain/rollback  → roll back to previous model
    GET  /api/retrain/status    → poll retraining job status
"""

import io
import logging
import os
import shutil
import threading
from datetime import datetime

import joblib
import pandas as pd
from flask import Blueprint, g, jsonify, request
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from db import get_db
from middleware.auth import require_auth
from middleware.rbac import require_role
from services.audit_service import log_action

logger = logging.getLogger(__name__)

retrain_bp = Blueprint("retrain", __name__, url_prefix="/api/retrain")

# ---------------------------------------------------------------------------
# Directory constants
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.path.join(_BASE_DIR, "retrain_uploads")
MODELS_DIR = os.path.join(_BASE_DIR, "models")
MODELS_NEW_DIR = os.path.join(MODELS_DIR, "new")
MODELS_BACKUP_DIR = os.path.join(MODELS_DIR, "backup")
TRAIN_CSV_PATH = os.path.join(_BASE_DIR, "data", "train.csv")

# Required columns (case-insensitive)
REQUIRED_COLUMNS = {"rbc", "mcv", "mch", "mchc", "rdw", "tlc", "plt", "hgb", "label"}
FEATURE_COLUMNS = ["rbc", "mcv", "mch", "mchc", "rdw", "tlc", "plt", "hgb"]

# Model filenames
RF_MODEL_FILE = "rf_anemia_classifier.pkl"
RF_SCALER_FILE = "rf_scaler.pkl"
GB_MODEL_FILE = "gb_severity_classifier.pkl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_dirs():
    """Create required directories if they don't exist."""
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(MODELS_NEW_DIR, exist_ok=True)
    os.makedirs(MODELS_BACKUP_DIR, exist_ok=True)


def _assign_severity_label(hgb_series: pd.Series) -> pd.Series:
    """
    Map HGB values to WHO severity labels:
      0 = None     (HGB >= 12.0)
      1 = Mild     (10.0 <= HGB < 12.0)
      2 = Moderate (8.0  <= HGB < 10.0)
      3 = Severe   (HGB  < 8.0)
    """
    import numpy as np
    conditions = [
        hgb_series >= 12.0,
        (hgb_series >= 10.0) & (hgb_series < 12.0),
        (hgb_series >= 8.0) & (hgb_series < 10.0),
        hgb_series < 8.0,
    ]
    choices = [0, 1, 2, 3]
    result = pd.Series(index=hgb_series.index, dtype=int)
    for cond, choice in zip(conditions, choices):
        result[cond] = choice
    return result


def _get_latest_upload() -> str | None:
    """Return the path to the most recently uploaded CSV, or None."""
    _ensure_dirs()
    files = [
        f for f in os.listdir(UPLOADS_DIR)
        if f.endswith(".csv")
    ]
    if not files:
        return None
    files.sort(reverse=True)  # timestamp-based names sort correctly
    return os.path.join(UPLOADS_DIR, files[0])


def _retrain_in_background(admin_username: str, retrain_id: int, upload_path: str):
    """
    Background thread: load data, retrain RF + GB, store metrics in retrain_log.
    New models are saved to backend/models/new/.
    """
    try:
        # --- Load uploaded CSV ---
        upload_df = pd.read_csv(upload_path)
        upload_df.columns = [c.strip().lower() for c in upload_df.columns]

        # Auto-label if label values are not in {0,1,2,3}
        valid_labels = {0, 1, 2, 3}
        label_vals = set(upload_df["label"].dropna().unique())
        if not label_vals.issubset(valid_labels):
            # Re-derive from HGB using severity thresholds
            upload_df["label"] = _assign_severity_label(upload_df["hgb"])

        # --- Load existing training data ---
        existing_df = pd.read_csv(TRAIN_CSV_PATH)
        existing_df.columns = [c.strip().lower() for c in existing_df.columns]

        # Map existing severity_label column to "label" if needed
        if "label" not in existing_df.columns:
            if "severity_label" in existing_df.columns:
                existing_df["label"] = existing_df["severity_label"]
            elif "hgb" in existing_df.columns:
                existing_df["label"] = _assign_severity_label(existing_df["hgb"])

        # Keep only needed columns
        needed = FEATURE_COLUMNS + ["label"]
        upload_sub = upload_df[[c for c in needed if c in upload_df.columns]].copy()
        existing_sub = existing_df[[c for c in needed if c in existing_df.columns]].copy()

        combined = pd.concat([existing_sub, upload_sub], ignore_index=True)
        combined = combined.dropna(subset=FEATURE_COLUMNS + ["label"])
        combined["label"] = combined["label"].astype(int)

        dataset_size = len(combined)

        # --- 80/20 split ---
        X = combined[FEATURE_COLUMNS].values
        y = combined["label"].values

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # --- Scale ---
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        # --- Train RF (binary: anemia detected = label > 0) ---
        y_train_binary = (y_train > 0).astype(int)
        y_test_binary = (y_test > 0).astype(int)

        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X_train_scaled, y_train_binary)
        rf_pred = rf.predict(X_test_scaled)

        rf_acc = float(accuracy_score(y_test_binary, rf_pred))
        rf_prec = float(precision_score(y_test_binary, rf_pred, average="weighted", zero_division=0))
        rf_rec = float(recall_score(y_test_binary, rf_pred, average="weighted", zero_division=0))
        rf_f1 = float(f1_score(y_test_binary, rf_pred, average="weighted", zero_division=0))

        # --- Train GB (multi-class severity) ---
        gb = GradientBoostingClassifier(n_estimators=100, random_state=42)
        gb.fit(X_train_scaled, y_train)
        gb_pred = gb.predict(X_test_scaled)

        gb_acc = float(accuracy_score(y_test, gb_pred))
        gb_prec = float(precision_score(y_test, gb_pred, average="weighted", zero_division=0))
        gb_rec = float(recall_score(y_test, gb_pred, average="weighted", zero_division=0))
        gb_f1 = float(f1_score(y_test, gb_pred, average="weighted", zero_division=0))

        # Use RF metrics as primary (anemia detection is the primary task)
        accuracy = rf_acc
        prec_score = rf_prec
        recall = rf_rec
        f1 = rf_f1

        # --- Save new models to models/new/ ---
        _ensure_dirs()
        joblib.dump(rf, os.path.join(MODELS_NEW_DIR, RF_MODEL_FILE))
        joblib.dump(scaler, os.path.join(MODELS_NEW_DIR, RF_SCALER_FILE))
        joblib.dump(gb, os.path.join(MODELS_NEW_DIR, GB_MODEL_FILE))

        completed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # --- Update retrain_log ---
        conn = get_db()
        try:
            conn.execute(
                """
                UPDATE retrain_log
                SET status = 'completed',
                    dataset_size = ?,
                    accuracy = ?,
                    precision_score = ?,
                    recall = ?,
                    f1_score = ?,
                    completed_at = ?
                WHERE retrain_id = ?
                """,
                (dataset_size, accuracy, prec_score, recall, f1, completed_at, retrain_id),
            )
            conn.commit()
        finally:
            conn.close()

        logger.info(
            "Retraining completed: retrain_id=%d, accuracy=%.4f", retrain_id, accuracy
        )

    except Exception as exc:
        logger.exception("Retraining failed for retrain_id=%d: %s", retrain_id, exc)
        completed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        try:
            conn.execute(
                """
                UPDATE retrain_log
                SET status = 'failed', completed_at = ?
                WHERE retrain_id = ?
                """,
                (completed_at, retrain_id),
            )
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@retrain_bp.get("/")
def index():
    return jsonify({"status": "ok", "blueprint": "retrain"})


# ---------------------------------------------------------------------------
# Task 10.1 — POST /api/retrain/upload
# ---------------------------------------------------------------------------

@retrain_bp.post("/upload")
@require_auth
@require_role("admin")
def upload_csv():
    """
    Accept a multipart CSV upload, validate columns and numeric values,
    store to backend/retrain_uploads/ with a timestamp-based filename.

    Returns:
        200: {"status": "ok", "message": "CSV uploaded", "filename": str, "rows": int}
        400: {"status": "error", "errors": [...]}
    """
    _ensure_dirs()

    if "file" not in request.files:
        return jsonify({"status": "error", "errors": ["No file field named 'file' in request"]}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"status": "error", "errors": ["No file selected"]}), 400

    # Read CSV
    try:
        content = file.read()
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        return jsonify({"status": "error", "errors": [f"Failed to parse CSV: {exc}"]}), 400

    # Normalise column names to lowercase
    df.columns = [c.strip().lower() for c in df.columns]

    # Check required columns (case-insensitive)
    present_cols = set(df.columns)
    missing_cols = REQUIRED_COLUMNS - present_cols
    errors = []

    if missing_cols:
        for col in sorted(missing_cols):
            errors.append(f"missing required column: '{col}'")
        return jsonify({"status": "error", "errors": errors}), 400

    # Check all feature columns are numeric (no NaN, no non-numeric values)
    for col in FEATURE_COLUMNS:
        col_series = df[col]
        # Check for NaN
        if col_series.isna().any():
            errors.append(f"column '{col}' has non-numeric values")
            continue
        # Check numeric dtype
        if not pd.api.types.is_numeric_dtype(col_series):
            # Try coercing
            coerced = pd.to_numeric(col_series, errors="coerce")
            if coerced.isna().any():
                errors.append(f"column '{col}' has non-numeric values")

    if errors:
        return jsonify({"status": "error", "errors": errors}), 400

    # Store with timestamp-based filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"retrain_{timestamp}.csv"
    save_path = os.path.join(UPLOADS_DIR, filename)

    df.to_csv(save_path, index=False)

    return jsonify({
        "status": "ok",
        "message": "CSV uploaded",
        "filename": filename,
        "rows": len(df),
    }), 200


# ---------------------------------------------------------------------------
# Task 10.2 — POST /api/retrain/start
# ---------------------------------------------------------------------------

@retrain_bp.post("/start")
@require_auth
@require_role("admin")
def start_retrain():
    """
    Trigger retraining in a background thread.
    Returns 202 immediately with the retrain_id.
    """
    admin_username = g.current_user["username"]

    upload_path = _get_latest_upload()
    if upload_path is None:
        return jsonify({
            "status": "error",
            "message": "No uploaded CSV found. Please upload a CSV first via POST /api/retrain/upload.",
        }), 400

    triggered_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Insert a "running" row into retrain_log
    conn = get_db()
    try:
        cursor = conn.execute(
            """
            INSERT INTO retrain_log
                (admin_username, dataset_size, status, triggered_at)
            VALUES (?, 0, 'running', ?)
            """,
            (admin_username, triggered_at),
        )
        conn.commit()
        retrain_id = cursor.lastrowid
    finally:
        conn.close()

    # Launch background thread
    thread = threading.Thread(
        target=_retrain_in_background,
        args=(admin_username, retrain_id, upload_path),
        daemon=True,
    )
    thread.start()

    # --- Audit service log: retrain start ---
    log_action(
        actor=admin_username,
        action="retrain_start",
        details={"retrain_id": retrain_id},
        ip=request.remote_addr,
    )

    return jsonify({
        "status": "ok",
        "message": "Retraining started",
        "retrain_id": retrain_id,
    }), 202


# ---------------------------------------------------------------------------
# Task 10.3 — GET /api/retrain/status
# ---------------------------------------------------------------------------

@retrain_bp.get("/status")
@require_auth
@require_role("admin")
def retrain_status():
    """
    Return the latest retrain_log row with status and metrics.
    """
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT retrain_id, admin_username, dataset_size, accuracy,
                   precision_score, recall, f1_score, status,
                   triggered_at, completed_at
            FROM retrain_log
            ORDER BY retrain_id DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return jsonify({"status": "ok", "retrain": None}), 200

    retrain_data = {
        "retrain_id": row["retrain_id"],
        "admin_username": row["admin_username"],
        "dataset_size": row["dataset_size"],
        "accuracy": row["accuracy"],
        "precision_score": row["precision_score"],
        "recall": row["recall"],
        "f1_score": row["f1_score"],
        "status": row["status"],
        "triggered_at": row["triggered_at"],
        "completed_at": row["completed_at"],
    }

    return jsonify({"status": "ok", "retrain": retrain_data}), 200


# ---------------------------------------------------------------------------
# Task 10.4 — POST /api/retrain/approve
# ---------------------------------------------------------------------------

@retrain_bp.post("/approve")
@require_auth
@require_role("admin")
def approve_retrain():
    """
    Compare new model accuracy vs current model accuracy.
    If accuracy drop > 5pp: return warning requiring {"confirm": true}.
    On approval: backup current .pkl files, copy new models, reload PredictionService.
    """
    _ensure_dirs()

    # Get the latest completed retrain_log row (new model metrics)
    conn = get_db()
    try:
        latest_row = conn.execute(
            """
            SELECT retrain_id, accuracy
            FROM retrain_log
            WHERE status = 'completed'
            ORDER BY retrain_id DESC
            LIMIT 1
            """
        ).fetchone()

        # Get the second-most-recent completed row (previous model accuracy)
        prior_row = conn.execute(
            """
            SELECT accuracy
            FROM retrain_log
            WHERE status = 'completed'
            ORDER BY retrain_id DESC
            LIMIT 1 OFFSET 1
            """
        ).fetchone()
    finally:
        conn.close()

    if latest_row is None:
        return jsonify({
            "status": "error",
            "message": "No completed retraining found. Run POST /api/retrain/start first.",
        }), 400

    new_accuracy = latest_row["accuracy"] or 0.0
    current_accuracy = prior_row["accuracy"] if prior_row and prior_row["accuracy"] is not None else 0.0

    # Check for accuracy drop > 5 percentage points
    accuracy_drop = current_accuracy - new_accuracy
    if accuracy_drop > 0.05 and current_accuracy > 0.0:
        body = request.get_json(silent=True) or {}
        if not body.get("confirm"):
            return jsonify({
                "status": "warning",
                "message": (
                    f"New model accuracy ({new_accuracy:.4f}) is more than 5 percentage points "
                    f"lower than current accuracy ({current_accuracy:.4f}). "
                    "Send {\"confirm\": true} to proceed anyway."
                ),
                "new_accuracy": new_accuracy,
                "current_accuracy": current_accuracy,
                "accuracy_drop": round(accuracy_drop, 4),
            }), 200

    # Check that new model files exist
    new_rf_path = os.path.join(MODELS_NEW_DIR, RF_MODEL_FILE)
    new_scaler_path = os.path.join(MODELS_NEW_DIR, RF_SCALER_FILE)
    new_gb_path = os.path.join(MODELS_NEW_DIR, GB_MODEL_FILE)

    missing = [p for p in [new_rf_path, new_scaler_path, new_gb_path] if not os.path.exists(p)]
    if missing:
        return jsonify({
            "status": "error",
            "message": f"New model files not found: {missing}. Run POST /api/retrain/start first.",
        }), 400

    # Backup current models
    for fname in [RF_MODEL_FILE, RF_SCALER_FILE, GB_MODEL_FILE]:
        src = os.path.join(MODELS_DIR, fname)
        dst = os.path.join(MODELS_BACKUP_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            logger.info("Backed up %s → %s", src, dst)

    # Copy new models to models/
    for fname in [RF_MODEL_FILE, RF_SCALER_FILE, GB_MODEL_FILE]:
        src = os.path.join(MODELS_NEW_DIR, fname)
        dst = os.path.join(MODELS_DIR, fname)
        shutil.copy2(src, dst)
        logger.info("Deployed new model %s → %s", src, dst)

    # Reload PredictionService singleton
    try:
        from services.prediction_service import get_prediction_service  # noqa: PLC0415
        get_prediction_service().reload()
        logger.info("PredictionService reloaded after model approval.")
    except Exception as exc:
        logger.warning("Failed to reload PredictionService: %s", exc)

    # --- Audit service log: retrain approve ---
    log_action(
        actor=g.current_user["username"],
        action="retrain_approve",
        ip=request.remote_addr,
    )

    return jsonify({
        "status": "ok",
        "message": "New models approved and deployed. PredictionService reloaded.",
        "new_accuracy": new_accuracy,
    }), 200


# ---------------------------------------------------------------------------
# Task 10.5 — POST /api/retrain/rollback
# ---------------------------------------------------------------------------

@retrain_bp.post("/rollback")
@require_auth
@require_role("admin")
def rollback_retrain():
    """
    Restore .pkl files from backend/models/backup/ to backend/models/,
    then reload PredictionService singleton.
    """
    _ensure_dirs()

    # Check backup files exist
    backup_files = [RF_MODEL_FILE, RF_SCALER_FILE, GB_MODEL_FILE]
    missing = [
        f for f in backup_files
        if not os.path.exists(os.path.join(MODELS_BACKUP_DIR, f))
    ]
    if missing:
        return jsonify({
            "status": "error",
            "message": f"Backup model files not found: {missing}. Cannot rollback.",
        }), 400

    # Restore backup models to models/
    for fname in backup_files:
        src = os.path.join(MODELS_BACKUP_DIR, fname)
        dst = os.path.join(MODELS_DIR, fname)
        shutil.copy2(src, dst)
        logger.info("Restored backup %s → %s", src, dst)

    # Reload PredictionService singleton
    try:
        from services.prediction_service import get_prediction_service  # noqa: PLC0415
        get_prediction_service().reload()
        logger.info("PredictionService reloaded after rollback.")
    except Exception as exc:
        logger.warning("Failed to reload PredictionService after rollback: %s", exc)

    # --- Audit service log: retrain rollback ---
    log_action(
        actor=g.current_user["username"],
        action="retrain_rollback",
        ip=request.remote_addr,
    )

    return jsonify({
        "status": "ok",
        "message": "Models rolled back to previous version. PredictionService reloaded.",
    }), 200
