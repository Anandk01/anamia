"""
model_evaluation_service.py — ML model evaluation and drift detection.

Provides:
  evaluate_model, detect_drift, train_all_models
"""

import json
import logging
from datetime import datetime, timezone

from db import get_db

logger = logging.getLogger(__name__)


def evaluate_model(model, X_test, y_test, model_name):
    """Compute metrics for a model and store in model_metrics table."""
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

    try:
        from sklearn.metrics import roc_auc_score
    except ImportError:
        roc_auc_score = None

    y_pred = model.predict(X_test)

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
    rec = recall_score(y_test, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)

    auc = None
    if roc_auc_score and hasattr(model, 'predict_proba'):
        try:
            y_proba = model.predict_proba(X_test)
            if y_proba.shape[1] == 2:
                auc = roc_auc_score(y_test, y_proba[:, 1])
            else:
                auc = roc_auc_score(y_test, y_proba, multi_class='ovr', average='weighted')
        except Exception:
            auc = None

    cm = confusion_matrix(y_test, y_pred).tolist()

    # Store in DB
    conn = get_db()
    try:
        conn.execute(
            """INSERT INTO model_metrics
               (model_name, accuracy, precision_score, recall, f1_score, auc_roc,
                confusion_matrix, dataset_name, dataset_size)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (model_name, acc, prec, rec, f1, auc,
             json.dumps(cm), "evaluation", len(y_test)),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "model_name": model_name,
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "auc_roc": round(auc, 4) if auc else None,
        "confusion_matrix": cm,
    }


def detect_drift(model_name, new_metrics):
    """Compare new metrics with latest stored metrics. Flag if >5% drop."""
    conn = get_db()
    try:
        row = conn.execute(
            """SELECT accuracy, precision_score, recall, f1_score
               FROM model_metrics WHERE model_name = ?
               ORDER BY trained_at DESC LIMIT 1""",
            (model_name,),
        ).fetchone()

        if not row:
            return {"drift_detected": False, "message": "No baseline metrics found."}

        baseline = dict(row)
        drift_flags = []
        threshold = 0.05

        for metric_key in ['accuracy', 'f1_score']:
            old_val = baseline.get(metric_key, 0)
            new_val = new_metrics.get(metric_key, 0)
            if old_val > 0 and (old_val - new_val) / old_val > threshold:
                drift_flags.append(f"{metric_key}: {old_val:.4f} -> {new_val:.4f}")

        return {
            "drift_detected": len(drift_flags) > 0,
            "flags": drift_flags,
            "baseline": baseline,
            "new_metrics": new_metrics,
        }
    finally:
        conn.close()


def train_all_models(dataset_path):
    """Train RF, GB, XGBoost, LightGBM on the given dataset. Returns metrics dict."""
    import pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier

    df = pd.read_csv(dataset_path)
    # Assume last column is target
    X = df.iloc[:, :-1]
    y = df.iloc[:, -1]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    results = {}

    # Random Forest
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    results['random_forest'] = evaluate_model(rf, X_test, y_test, 'random_forest')

    # Gradient Boosting
    gb = GradientBoostingClassifier(n_estimators=100, random_state=42)
    gb.fit(X_train, y_train)
    results['gradient_boosting'] = evaluate_model(gb, X_test, y_test, 'gradient_boosting')

    # XGBoost (conditional)
    try:
        from xgboost import XGBClassifier
        xgb = XGBClassifier(n_estimators=100, random_state=42, use_label_encoder=False, eval_metric='mlogloss')
        xgb.fit(X_train, y_train)
        results['xgboost'] = evaluate_model(xgb, X_test, y_test, 'xgboost')
    except ImportError:
        logger.warning("xgboost not installed, skipping")

    # LightGBM (conditional)
    try:
        from lightgbm import LGBMClassifier
        lgbm = LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)
        lgbm.fit(X_train, y_train)
        results['lightgbm'] = evaluate_model(lgbm, X_test, y_test, 'lightgbm')
    except ImportError:
        logger.warning("lightgbm not installed, skipping")

    return results
