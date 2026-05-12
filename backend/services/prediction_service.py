"""
services/prediction_service.py — Supervised ML prediction pipeline.

Provides:
  PredictionService  : singleton class that loads the three trained models
                       and exposes a ``predict(cbc_dict)`` method that runs
                       the full anemia detection + severity + type +
                       explainability pipeline.

Singleton access
----------------
Use ``get_prediction_service()`` to obtain the shared instance.  The first
call loads the models from ``backend/models/``; subsequent calls return the
cached instance.

Prediction pipeline
-------------------
  1. Scale input using rf_scaler (StandardScaler).
  2. RF binary classifier → anemia_detected (0/1) + anemia_confidence.
  3. If anemia_detected == 1:
       GB multi-class classifier → severity_level + severity_confidence.
     Else:
       severity_level = "None", severity_confidence = 1.0.
  4. Clinical rule engine (type_classifier) → anemia_type + type_confidence.
     (If anemia_detected == 0: anemia_type = "N/A", type_confidence = 1.0.)
  5. SHAP explainability → explanation (list of 3 dicts).

Severity mapping
----------------
  0 → "None"
  1 → "Mild"
  2 → "Moderate"
  3 → "Severe"
"""

import logging
import os
from typing import Any, Dict, Optional

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODELS_DIR = os.path.join(_BASE_DIR, "models")

RF_CLASSIFIER_PATH = os.path.join(_MODELS_DIR, "rf_anemia_classifier.pkl")
RF_SCALER_PATH = os.path.join(_MODELS_DIR, "rf_scaler.pkl")
GB_SEVERITY_PATH = os.path.join(_MODELS_DIR, "gb_severity_classifier.pkl")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEVERITY_MAP: Dict[int, str] = {
    0: "None",
    1: "Mild",
    2: "Moderate",
    3: "Severe",
}

# Feature order expected by the models (must match training order)
FEATURE_ORDER = ["RBC", "MCV", "MCH", "MCHC", "RDW", "TLC", "PLT", "HGB"]

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------
_instance: Optional["PredictionService"] = None


def get_prediction_service() -> "PredictionService":
    """Return the shared PredictionService singleton, creating it if needed."""
    global _instance
    if _instance is None:
        _instance = PredictionService()
    return _instance


# ---------------------------------------------------------------------------
# PredictionService
# ---------------------------------------------------------------------------

class PredictionService:
    """
    Loads the three trained ML models and runs the full prediction pipeline.

    Attributes
    ----------
    rf_model   : sklearn RandomForestClassifier (binary anemia detection)
    scaler     : sklearn StandardScaler (fitted on training data)
    gb_model   : sklearn GradientBoostingClassifier (severity multi-class)
    """

    def __init__(self) -> None:
        self.rf_model = self._load_model(RF_CLASSIFIER_PATH, "rf_anemia_classifier")
        self.scaler = self._load_model(RF_SCALER_PATH, "rf_scaler")
        self.gb_model = self._load_model(GB_SEVERITY_PATH, "gb_severity_classifier")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_model(path: str, name: str) -> Any:
        """Load a joblib model; raise RuntimeError if unavailable."""
        if not os.path.exists(path):
            raise RuntimeError(
                f"Model file not found: {path}. "
                f"Run the training script to generate '{name}.pkl'."
            )
        try:
            model = joblib.load(path)
            logger.info("Loaded model '%s' from %s", name, path)
            return model
        except Exception as exc:
            raise RuntimeError(f"Failed to load model '{name}': {exc}") from exc

    def _cbc_to_array(self, cbc_dict: Dict[str, float]) -> np.ndarray:
        """
        Convert a normalised CBC dict (lowercase keys) to a (1, 8) numpy array
        in the canonical FEATURE_ORDER.
        """
        upper = {k.upper(): v for k, v in cbc_dict.items()}
        row = [float(upper[feat]) for feat in FEATURE_ORDER]
        return np.array(row, dtype=np.float64).reshape(1, -1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, cbc_dict: Dict[str, float]) -> Dict[str, Any]:
        """
        Run the full prediction pipeline on a validated CBC input.

        Parameters
        ----------
        cbc_dict : dict
            Normalised CBC values with lowercase keys (output of validate_cbc).
            Must contain all 8 fields: rbc, mcv, mch, mchc, rdw, tlc, plt, hgb.

        Returns
        -------
        dict with keys:
          anemia_detected    : int   (0 or 1)
          anemia_confidence  : float (0.0–1.0)
          severity_level     : str   ("None" / "Mild" / "Moderate" / "Severe")
          severity_confidence: float (0.0–1.0)
          anemia_type        : str
          type_confidence    : float (0.0–1.0)
          explanation        : list of 3 dicts (feature, direction, shap_value)
          hgb                : float
        """
        # --- Step 1: Build input array and scale ---
        raw_array = self._cbc_to_array(cbc_dict)
        scaled_array = self.scaler.transform(raw_array)

        # --- Step 2: RF binary prediction ---
        rf_pred = int(self.rf_model.predict(scaled_array)[0])
        rf_proba = self.rf_model.predict_proba(scaled_array)[0]
        # Confidence = probability of the predicted class
        anemia_confidence = float(rf_proba[rf_pred])

        # --- Step 3: GB severity (only if anemia detected) ---
        if rf_pred == 1:
            gb_pred = int(self.gb_model.predict(scaled_array)[0])
            gb_proba = self.gb_model.predict_proba(scaled_array)[0]
            severity_level = SEVERITY_MAP.get(gb_pred, "Unknown")
            severity_confidence = float(gb_proba[gb_pred])
        else:
            severity_level = "None"
            severity_confidence = 1.0

        # --- Step 4: Anemia type classification ---
        if rf_pred == 1:
            try:
                from services.type_classifier import classify_anemia_type  # noqa: PLC0415
                type_result = classify_anemia_type(
                    mcv=cbc_dict["mcv"],
                    mch=cbc_dict["mch"],
                    mchc=cbc_dict["mchc"],
                    rdw=cbc_dict["rdw"],
                )
                anemia_type = type_result["anemia_type"]
                type_confidence = float(type_result["confidence"])
            except Exception as exc:
                logger.warning("Type classification failed: %s", exc)
                anemia_type = "Unknown"
                type_confidence = 0.0
        else:
            anemia_type = "N/A"
            type_confidence = 1.0

        # --- Step 5: SHAP explainability ---
        try:
            from services.explainability import explain_prediction  # noqa: PLC0415
            explanation = explain_prediction(self.rf_model, self.scaler, cbc_dict)
        except Exception as exc:
            logger.warning("Explainability failed: %s", exc)
            explanation = []

        return {
            "anemia_detected": rf_pred,
            "anemia_confidence": round(anemia_confidence, 6),
            "severity_level": severity_level,
            "severity_confidence": round(severity_confidence, 6),
            "anemia_type": anemia_type,
            "type_confidence": round(type_confidence, 6),
            "explanation": explanation,
            "hgb": float(cbc_dict["hgb"]),
        }

    def reload(self) -> None:
        """Reload all models from disk (used after retraining/rollback)."""
        self.rf_model = self._load_model(RF_CLASSIFIER_PATH, "rf_anemia_classifier")
        self.scaler = self._load_model(RF_SCALER_PATH, "rf_scaler")
        self.gb_model = self._load_model(GB_SEVERITY_PATH, "gb_severity_classifier")
        logger.info("PredictionService models reloaded.")
