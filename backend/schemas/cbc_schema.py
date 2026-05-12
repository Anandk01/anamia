"""
schemas/cbc_schema.py — Input validation for CBC (Complete Blood Count) data.

Provides:
  validate_cbc(data) : normalise field names, check presence and type of all
                       8 required CBC fields, check values are non-negative.

The 8 required fields (case-insensitive):
  rbc, mcv, mch, mchc, rdw, tlc, plt, hgb
"""

from typing import Any, Dict, List, Tuple

# Canonical lowercase field names required for prediction
REQUIRED_FIELDS: List[str] = ["rbc", "mcv", "mch", "mchc", "rdw", "tlc", "plt", "hgb"]


def validate_cbc(data: Dict[str, Any]) -> Tuple[Dict[str, float], List[str]]:
    """
    Validate and normalise a CBC input dictionary.

    Steps:
      1. Normalise all keys to lowercase.
      2. Check that all 8 required fields are present.
      3. Check that each field value is numeric (int or float, not bool).
      4. Check that each numeric value is ≥ 0.

    Parameters
    ----------
    data : dict
        Raw CBC input, keys may be any case (e.g. "HGB", "Hgb", "hgb").

    Returns
    -------
    (normalised_dict, errors_list)
        normalised_dict : dict with lowercase keys and float values.
                          Empty dict if there are errors.
        errors_list     : list of human-readable error strings.
                          Empty list on success.
    """
    if not isinstance(data, dict):
        return {}, ["Input must be a JSON object"]

    # Step 1: normalise keys to lowercase
    normalised: Dict[str, Any] = {k.lower(): v for k, v in data.items()}

    errors: List[str] = []

    # Step 2: check all required fields are present
    missing = [field for field in REQUIRED_FIELDS if field not in normalised]
    if missing:
        errors.append(f"Missing required fields: {', '.join(missing)}")

    # Step 3 & 4: validate each present required field
    result: Dict[str, float] = {}
    for field in REQUIRED_FIELDS:
        if field not in normalised:
            # Already reported as missing above
            continue

        value = normalised[field]

        # bool is a subclass of int in Python — reject it explicitly
        if isinstance(value, bool):
            errors.append(f"Field '{field}' must be numeric (got boolean)")
            continue

        if not isinstance(value, (int, float)):
            errors.append(f"Field '{field}' must be numeric (got {type(value).__name__})")
            continue

        float_value = float(value)

        if float_value < 0:
            errors.append(f"Field '{field}' must be ≥ 0 (got {float_value})")
            continue

        result[field] = float_value

    if errors:
        return {}, errors

    return result, []
