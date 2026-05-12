"""
SHAP-based Feature Importance for Anemia Prediction Explainability.

This module generates human-readable explanations for each prediction by
computing SHAP values using ``shap.TreeExplainer`` on the Random Forest
classifier.  For each prediction it returns the top-3 features ranked by
absolute SHAP value, together with a directional label derived from
population reference ranges.

Directional labels per feature
-------------------------------
  HGB  : Low < 12, Normal 12–17, High > 17
  MCV  : Low < 80, Normal 80–100, High > 100
  MCH  : Low < 27, Normal 27–33, High > 33
  MCHC : Low < 32, Normal 32–36, High > 36
  RDW  : Normal < 14.5, Elevated ≥ 14.5
  RBC  : Low < 4.0, Normal 4.0–5.5, High > 5.5
  TLC  : Low < 4.0, Normal 4.0–11.0, High > 11.0
  PLT  : Low < 150, Normal 150–400, High > 400

Fallback behaviour
------------------
If ``shap`` is not installed or raises a runtime error, the module falls
back to ``sklearn.inspection.permutation_importance`` computed on a small
synthetic dataset.  In the fallback path ``shap_value`` is set to ``0.0``
for all returned entries.

Feature order expected by the model
------------------------------------
  ["RBC", "MCV", "MCH", "MCHC", "RDW", "TLC", "PLT", "HGB"]
"""

import logging
import numpy as np
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature metadata
# ---------------------------------------------------------------------------

#: Canonical feature order that the RF model was trained on.
FEATURE_ORDER: List[str] = ["RBC", "MCV", "MCH", "MCHC", "RDW", "TLC", "PLT", "HGB"]

#: Population reference ranges used to assign directional labels.
#: Each entry is a tuple of (low_threshold, high_threshold, labels_dict).
#: ``None`` for a threshold means "no bound in that direction".
#:
#: labels_dict keys: "low", "normal", "high" (or "elevated" for RDW).
_REFERENCE_RANGES: Dict[str, Dict[str, Any]] = {
    "HGB": {
        "low_threshold": 12.0,
        "high_threshold": 17.0,
        "labels": {"low": "Low", "normal": "Normal", "high": "High"},
    },
    "MCV": {
        "low_threshold": 80.0,
        "high_threshold": 100.0,
        "labels": {"low": "Low", "normal": "Normal", "high": "High"},
    },
    "MCH": {
        "low_threshold": 27.0,
        "high_threshold": 33.0,
        "labels": {"low": "Low", "normal": "Normal", "high": "High"},
    },
    "MCHC": {
        "low_threshold": 32.0,
        "high_threshold": 36.0,
        "labels": {"low": "Low", "normal": "Normal", "high": "High"},
    },
    "RDW": {
        # RDW only has a single upper threshold; below is Normal, at/above is Elevated.
        "low_threshold": None,
        "high_threshold": 14.5,
        "labels": {"low": None, "normal": "Normal", "high": "Elevated"},
    },
    "RBC": {
        "low_threshold": 4.0,
        "high_threshold": 5.5,
        "labels": {"low": "Low", "normal": "Normal", "high": "High"},
    },
    "TLC": {
        "low_threshold": 4.0,
        "high_threshold": 11.0,
        "labels": {"low": "Low", "normal": "Normal", "high": "High"},
    },
    "PLT": {
        "low_threshold": 150.0,
        "high_threshold": 400.0,
        "labels": {"low": "Low", "normal": "Normal", "high": "High"},
    },
}


def _get_direction(feature: str, value: float) -> str:
    """
    Map a raw CBC feature value to a directional label using population
    reference ranges.

    Parameters
    ----------
    feature : str
        Feature name (must be one of the keys in ``_REFERENCE_RANGES``).
    value : float
        Raw (unscaled) measurement value.

    Returns
    -------
    str
        One of "Low", "Normal", "High", "Elevated", or "Unknown" if the
        feature is not in the reference table.
    """
    ref = _REFERENCE_RANGES.get(feature)
    if ref is None:
        logger.warning("No reference range defined for feature '%s'", feature)
        return "Unknown"

    low_thresh = ref["low_threshold"]
    high_thresh = ref["high_threshold"]
    labels = ref["labels"]

    # RDW-style: only an upper threshold (no "low" category)
    if low_thresh is None:
        if value >= high_thresh:
            return labels["high"]  # "Elevated"
        return labels["normal"]    # "Normal"

    # Standard three-way classification
    if value < low_thresh:
        return labels["low"]
    if value > high_thresh:
        return labels["high"]
    return labels["normal"]


def _cbc_dict_to_array(cbc_dict: Dict[str, float]) -> np.ndarray:
    """
    Convert a CBC dictionary to a 1-D numpy array in ``FEATURE_ORDER``.

    Parameters
    ----------
    cbc_dict : dict
        Raw (unscaled) CBC values keyed by feature name (case-insensitive).

    Returns
    -------
    np.ndarray
        Shape ``(1, 8)`` array ready for scaler/model input.

    Raises
    ------
    KeyError
        If any feature in ``FEATURE_ORDER`` is missing from ``cbc_dict``.
    """
    # Normalise keys to uppercase for lookup
    normalised = {k.upper(): v for k, v in cbc_dict.items()}
    row = [float(normalised[feat]) for feat in FEATURE_ORDER]
    return np.array(row, dtype=np.float64).reshape(1, -1)


def _build_synthetic_dataset(
    cbc_array: np.ndarray,
    n_samples: int = 200,
    noise_scale: float = 0.15,
) -> np.ndarray:
    """
    Build a small synthetic dataset around the given input for use with
    permutation importance.

    The dataset is constructed by adding Gaussian noise (scaled by the
    absolute value of each feature) to the input vector, ensuring all
    generated values are non-negative.

    Parameters
    ----------
    cbc_array : np.ndarray
        Shape ``(1, 8)`` input vector (already scaled).
    n_samples : int
        Number of synthetic samples to generate.
    noise_scale : float
        Relative noise magnitude (fraction of each feature's absolute value).

    Returns
    -------
    np.ndarray
        Shape ``(n_samples, 8)`` synthetic dataset.
    """
    rng = np.random.default_rng(seed=42)
    base = np.tile(cbc_array, (n_samples, 1))
    # Scale noise by the magnitude of each feature to keep proportions sensible
    scale = np.abs(cbc_array) * noise_scale + 1e-6
    noise = rng.normal(loc=0.0, scale=scale, size=base.shape)
    synthetic = base + noise
    return np.clip(synthetic, a_min=0.0, a_max=None)


def _explain_with_permutation_importance(
    rf_model: Any,
    scaled_input: np.ndarray,
    cbc_dict: Dict[str, float],
) -> List[Dict[str, Any]]:
    """
    Fallback explainability using sklearn permutation importance.

    Computes permutation importance on a small synthetic dataset centred
    around the input.  Returns top-3 features with ``shap_value=0.0``.

    Parameters
    ----------
    rf_model : sklearn RandomForestClassifier
        Trained RF model.
    scaled_input : np.ndarray
        Shape ``(1, 8)`` scaled input vector.
    cbc_dict : dict
        Raw (unscaled) CBC values for directional label computation.

    Returns
    -------
    list of dict
        Top-3 feature dicts: ``{"feature": str, "direction": str, "shap_value": float}``.
    """
    from sklearn.inspection import permutation_importance

    logger.info("Using permutation importance fallback for explainability")

    X_synthetic = _build_synthetic_dataset(scaled_input, n_samples=200)
    y_synthetic = rf_model.predict(X_synthetic)

    result = permutation_importance(
        rf_model,
        X_synthetic,
        y_synthetic,
        n_repeats=5,
        random_state=42,
        scoring="accuracy",
    )

    importances = result.importances_mean  # shape (8,)
    top3_indices = np.argsort(np.abs(importances))[::-1][:3]

    normalised_cbc = {k.upper(): v for k, v in cbc_dict.items()}

    return [
        {
            "feature": FEATURE_ORDER[idx],
            "direction": _get_direction(
                FEATURE_ORDER[idx], normalised_cbc.get(FEATURE_ORDER[idx], 0.0)
            ),
            "shap_value": 0.0,
        }
        for idx in top3_indices
    ]


def explain_prediction(
    rf_model: Any,
    scaler: Any,
    cbc_dict: Dict[str, float],
) -> List[Dict[str, Any]]:
    """
    Generate a SHAP-based explanation for a single CBC prediction.

    Uses ``shap.TreeExplainer`` on the Random Forest classifier to compute
    SHAP values for the given input.  Returns the top-3 features ranked by
    absolute SHAP value, each annotated with a directional label derived
    from population reference ranges.

    If SHAP is unavailable or raises a runtime error, falls back to
    permutation importance (``shap_value`` will be ``0.0`` in that case).

    Parameters
    ----------
    rf_model : sklearn RandomForestClassifier
        Trained RF binary classifier (anemia detection).
    scaler : sklearn StandardScaler
        Fitted scaler used during training; applied internally to the raw
        CBC values before computing SHAP values.
    cbc_dict : dict
        Raw (unscaled) CBC values keyed by feature name (case-insensitive).
        Must contain all 8 features: RBC, MCV, MCH, MCHC, RDW, TLC, PLT, HGB.

    Returns
    -------
    list of dict
        Exactly 3 dicts, each with keys:
          - ``"feature"``   (str)   : CBC feature name, e.g. ``"HGB"``
          - ``"direction"`` (str)   : directional label, e.g. ``"Low"``
          - ``"shap_value"``(float) : SHAP value (0.0 in fallback mode)

    Notes
    -----
    - The function handles scaling internally; pass raw (unscaled) values.
    - SHAP values are taken from the positive class (anemia=1) output.
    - If fewer than 3 features are available (should not happen with 8
      features), the list is padded to length 3 using remaining features.
    """
    # --- Step 1: Build scaled input array ---
    try:
        raw_array = _cbc_dict_to_array(cbc_dict)
    except (KeyError, ValueError) as exc:
        logger.error("Failed to build input array from cbc_dict: %s", exc)
        raise ValueError(f"Invalid cbc_dict: {exc}") from exc

    try:
        scaled_array = scaler.transform(raw_array)
    except Exception as exc:
        logger.error("Scaler transform failed: %s", exc)
        raise RuntimeError(f"Scaler transform failed: {exc}") from exc

    normalised_cbc = {k.upper(): v for k, v in cbc_dict.items()}

    # --- Step 2: Attempt SHAP explanation ---
    try:
        import shap  # noqa: PLC0415 — intentional lazy import for fallback

        explainer = shap.TreeExplainer(rf_model)
        shap_values = explainer.shap_values(scaled_array)

        # shap_values may be:
        #   - ndarray of shape (1, 8) for single-output models
        #   - list of two arrays [(1,8), (1,8)] for binary classifiers
        #     where index 0 = class 0 (no anemia), index 1 = class 1 (anemia)
        if isinstance(shap_values, list):
            # Use class-1 (anemia) SHAP values
            values_for_class1 = np.array(shap_values[1]).flatten()
        else:
            # Single output — use as-is
            values_for_class1 = np.array(shap_values).flatten()

        if len(values_for_class1) != len(FEATURE_ORDER):
            raise RuntimeError(
                f"SHAP returned {len(values_for_class1)} values, "
                f"expected {len(FEATURE_ORDER)}"
            )

        # Top-3 by absolute SHAP value
        top3_indices = np.argsort(np.abs(values_for_class1))[::-1][:3]

        explanation = [
            {
                "feature": FEATURE_ORDER[idx],
                "direction": _get_direction(
                    FEATURE_ORDER[idx],
                    normalised_cbc.get(FEATURE_ORDER[idx], 0.0),
                ),
                "shap_value": float(round(values_for_class1[idx], 6)),
            }
            for idx in top3_indices
        ]

        logger.debug(
            "SHAP explanation computed successfully: %s",
            [(e["feature"], e["shap_value"]) for e in explanation],
        )
        return explanation

    except ImportError:
        logger.warning(
            "shap package not installed; falling back to permutation importance"
        )
    except Exception as exc:  # noqa: BLE001 — broad catch for SHAP runtime errors
        logger.warning(
            "SHAP explanation failed (%s: %s); falling back to permutation importance",
            type(exc).__name__,
            exc,
        )

    # --- Step 3: Fallback — permutation importance ---
    try:
        return _explain_with_permutation_importance(rf_model, scaled_array, cbc_dict)
    except Exception as exc:
        logger.error(
            "Permutation importance fallback also failed: %s", exc, exc_info=True
        )
        # Last-resort: return top-3 features with zero SHAP values and Unknown direction
        return [
            {"feature": feat, "direction": "Unknown", "shap_value": 0.0}
            for feat in FEATURE_ORDER[:3]
        ]
