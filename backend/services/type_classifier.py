"""
Clinical Rule Engine for Anemia Type Classification.

This module classifies anemia into one of four types based on CBC indices
(MCV, MCH, MCHC, RDW) using clinically validated morphological rules:

  1. Iron-Deficiency Anemia (microcytic hypochromic):
       MCV < 80 fL  AND  MCH < 27 pg
       Red cells are small (low MCV) and pale (low MCH), characteristic of
       iron-deficient erythropoiesis.

  2. Macrocytic Anemias — differentiated by RDW:
       MCV > 100 fL
         RDW > 14.5 %  →  Folate Deficiency
           (high RDW reflects anisocytosis from megaloblastic marrow)
         RDW ≤ 14.5 %  →  Vitamin B12 Deficiency
           (uniform macrocytes, lower RDW)

  3. Other / Normocytic:
       MCV 80–100 fL  (does not meet microcytic or macrocytic criteria)
       Covers normocytic anemias (chronic disease, haemolysis, aplastic, etc.)

Confidence scoring (0.0–1.0):
  Confidence reflects how far the key CBC values are from the decision
  boundaries.  A sigmoid function maps the normalised distance to [0, 1]:

      confidence = 1 / (1 + exp(-k * distance))

  where `distance` is the absolute deviation from the threshold divided by
  a clinically meaningful scale factor, and `k` controls the steepness.
  Values exactly on a boundary yield confidence ≈ 0.5; values far from the
  boundary approach 1.0.

Reference ranges used for scale factors:
  MCV  : physiological range ~60–120 fL  → scale = 20 fL
  MCH  : physiological range ~20–35 pg   → scale = 7 pg
  RDW  : physiological range ~11–20 %    → scale = 4.5 %
"""

import math
from typing import Dict


# ---------------------------------------------------------------------------
# Threshold constants (clinically validated)
# ---------------------------------------------------------------------------
MCV_MICRO_THRESHOLD = 80.0    # fL — below this: microcytic
MCV_MACRO_THRESHOLD = 100.0   # fL — above this: macrocytic
MCH_LOW_THRESHOLD = 27.0      # pg — below this: hypochromic
RDW_FOLATE_THRESHOLD = 14.5   # % — above this: folate deficiency pattern

# Scale factors for sigmoid normalisation (clinically meaningful spread)
MCV_SCALE = 20.0   # fL
MCH_SCALE = 7.0    # pg
RDW_SCALE = 4.5    # %

# Sigmoid steepness — k=3 gives a smooth but decisive curve
SIGMOID_K = 3.0


def _sigmoid(x: float) -> float:
    """Standard sigmoid function, clamped to avoid overflow."""
    try:
        return 1.0 / (1.0 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def _distance_confidence(value: float, threshold: float, scale: float) -> float:
    """
    Compute a confidence score in [0, 1] based on how far `value` is from
    `threshold`, normalised by `scale`.

    Returns ~0.5 when value == threshold (boundary case), approaching 1.0
    as the absolute distance grows.
    """
    normalised_distance = abs(value - threshold) / scale
    return _sigmoid(SIGMOID_K * normalised_distance)


def _iron_deficiency_confidence(mcv: float, mch: float) -> float:
    """
    Confidence for Iron-Deficiency: combine MCV distance from 80 and
    MCH distance from 27 using the geometric mean so both criteria
    contribute equally.
    """
    conf_mcv = _distance_confidence(mcv, MCV_MICRO_THRESHOLD, MCV_SCALE)
    conf_mch = _distance_confidence(mch, MCH_LOW_THRESHOLD, MCH_SCALE)
    return math.sqrt(conf_mcv * conf_mch)


def _macrocytic_confidence(mcv: float) -> float:
    """Confidence for macrocytic classification based on MCV distance from 100."""
    return _distance_confidence(mcv, MCV_MACRO_THRESHOLD, MCV_SCALE)


def _rdw_differentiation_confidence(rdw: float) -> float:
    """Confidence for Folate vs B12 differentiation based on RDW distance from 14.5."""
    return _distance_confidence(rdw, RDW_FOLATE_THRESHOLD, RDW_SCALE)


def _normocytic_confidence(mcv: float) -> float:
    """
    Confidence for normocytic classification: highest when MCV is centred
    in the 80–100 range (midpoint = 90), decreasing toward the boundaries.
    """
    midpoint = (MCV_MICRO_THRESHOLD + MCV_MACRO_THRESHOLD) / 2.0  # 90.0
    half_range = (MCV_MACRO_THRESHOLD - MCV_MICRO_THRESHOLD) / 2.0  # 10.0
    # Distance from midpoint, normalised by half-range
    normalised_distance = abs(mcv - midpoint) / half_range
    # Invert: centred → high confidence, near boundary → low confidence
    # Use 1 - sigmoid(k * normalised_distance) so centre → ~0.88, boundary → ~0.5
    return 1.0 - _sigmoid(SIGMOID_K * normalised_distance) + 0.5
    # Clamp to [0, 1]


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def classify_anemia_type(
    mcv: float,
    mch: float,
    mchc: float,
    rdw: float,
) -> Dict[str, object]:
    """
    Classify anemia type from CBC morphological indices.

    Parameters
    ----------
    mcv : float
        Mean Corpuscular Volume in femtolitres (fL).
    mch : float
        Mean Corpuscular Haemoglobin in picograms (pg).
    mchc : float
        Mean Corpuscular Haemoglobin Concentration in g/dL.
        (Accepted for completeness; not used in primary rules but available
        for future refinement.)
    rdw : float
        Red Cell Distribution Width as a percentage (%).

    Returns
    -------
    dict
        {
            "anemia_type": str,   # one of the four type strings below
            "confidence": float   # 0.0–1.0
        }

    Anemia types returned
    ---------------------
    - "Iron-Deficiency"         MCV < 80 AND MCH < 27
    - "Folate Deficiency"       MCV > 100 AND RDW > 14.5
    - "Vitamin B12 Deficiency"  MCV > 100 AND RDW ≤ 14.5
    - "Other"                   MCV 80–100 (normocytic)

    Edge cases
    ----------
    - MCV exactly at 80 or 100: treated as normocytic ("Other") because the
      strict inequalities (< 80, > 100) are not satisfied.
    - MCV < 80 but MCH ≥ 27: does not meet full Iron-Deficiency criteria;
      classified as "Other" with low confidence.
    """
    # --- Rule 1: Microcytic hypochromic → Iron-Deficiency ---
    if mcv < MCV_MICRO_THRESHOLD and mch < MCH_LOW_THRESHOLD:
        confidence = _iron_deficiency_confidence(mcv, mch)
        return {
            "anemia_type": "Iron-Deficiency",
            "confidence": round(_clamp(confidence), 4),
        }

    # --- Rule 2: Macrocytic → differentiate by RDW ---
    if mcv > MCV_MACRO_THRESHOLD:
        macro_conf = _macrocytic_confidence(mcv)
        rdw_conf = _rdw_differentiation_confidence(rdw)
        # Combined confidence: macrocytic certainty × RDW differentiation certainty
        combined = math.sqrt(macro_conf * rdw_conf)

        if rdw > RDW_FOLATE_THRESHOLD:
            return {
                "anemia_type": "Folate Deficiency",
                "confidence": round(_clamp(combined), 4),
            }
        else:
            return {
                "anemia_type": "Vitamin B12 Deficiency",
                "confidence": round(_clamp(combined), 4),
            }

    # --- Rule 3: Normocytic → Other ---
    confidence = _normocytic_confidence(mcv)
    return {
        "anemia_type": "Other",
        "confidence": round(_clamp(confidence), 4),
    }
