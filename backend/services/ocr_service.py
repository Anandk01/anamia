"""
services/ocr_service.py — OCR-based CBC field extraction.

Provides:
  extract_cbc_from_file(filepath, mime_type)
    Accepts a file path and MIME type, runs Tesseract OCR on the image/PDF,
    and returns extracted CBC values with per-field confidence indicators.

Return format:
  {
    "values":     {"hgb": float, "rbc": float, ...},
    "confidence": {"hgb": "High"|"Medium"|"Low", ...},
    "warnings":   [str, ...]
  }
"""

from __future__ import annotations

import os
import base64
import logging
from typing import Any

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini Client Helper
# ---------------------------------------------------------------------------

_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment")
        _client = genai.Client(api_key=api_key)
    return _client

# ---------------------------------------------------------------------------
# Typical reference ranges used for "Medium" confidence detection
# (value outside range → unusual → Medium confidence)
# ---------------------------------------------------------------------------
_TYPICAL_RANGES: dict[str, tuple[float, float]] = {
    "hgb":  (7.0,  20.0),
    "rbc":  (2.0,   8.0),
    "mcv":  (50.0, 130.0),
    "mch":  (15.0,  45.0),
    "mchc": (25.0,  40.0),
    "rdw":  (10.0,  25.0),
    "tlc":  (1.0,   30.0),
    "plt":  (20.0, 800.0),
}

# ---------------------------------------------------------------------------
# Regex patterns for each CBC field
# ---------------------------------------------------------------------------
_PATTERNS: dict[str, str] = {
    "hgb":  r"(?:HGB|Hgb|Hemoglobin|Haemoglobin)\s*[:\-]?\s*(\d+\.?\d*)",
    "rbc":  r"(?:RBC|Red Blood Cell)\s*[:\-]?\s*(\d+\.?\d*)",
    "mcv":  r"(?:MCV)\s*[:\-]?\s*(\d+\.?\d*)",
    "mch":  r"(?:MCH)\s*[:\-]?\s*(\d+\.?\d*)",
    "mchc": r"(?:MCHC)\s*[:\-]?\s*(\d+\.?\d*)",
    "rdw":  r"(?:RDW)\s*[:\-]?\s*(\d+\.?\d*)",
    "tlc":  r"(?:TLC|WBC|White Blood Cell)\s*[:\-]?\s*(\d+\.?\d*)",
    "plt":  r"(?:PLT|Platelet)\s*[:\-]?\s*(\d+\.?\d*)",
}

# Human-readable field names for warning messages
_FIELD_LABELS: dict[str, str] = {
    "hgb":  "HGB (Haemoglobin)",
    "rbc":  "RBC (Red Blood Cell)",
    "mcv":  "MCV",
    "mch":  "MCH",
    "mchc": "MCHC",
    "rdw":  "RDW",
    "tlc":  "TLC/WBC (White Blood Cell)",
    "plt":  "PLT (Platelet)",
}


def _get_image_from_file(filepath: str, mime_type: str):
    """
    Load the first page of a PDF or an image file as a PIL Image.

    Raises ImportError if required libraries are not installed.
    Raises RuntimeError on conversion failure.
    """
    if mime_type == "application/pdf":
        try:
            from pdf2image import convert_from_path  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "pdf2image is required for PDF processing. "
                "Install it with: pip install pdf2image"
            ) from exc

        pages = convert_from_path(filepath, first_page=1, last_page=1)
        if not pages:
            raise RuntimeError("pdf2image returned no pages for the given PDF.")
        return pages[0]

    else:
        # JPEG or PNG — open directly with PIL
        try:
            from PIL import Image  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "Pillow is required for image processing. "
                "Install it with: pip install Pillow"
            ) from exc

        return Image.open(filepath)


def _run_gemini_ocr(image_path: str, mime_type: str) -> dict:
    """
    Use Google Gemini to extract CBC values from the report file.
    Returns a dict with 'values', 'confidence', and 'warnings'.
    """
    client = _get_client()
    
    # Read file data
    with open(image_path, "rb") as f:
        file_data = f.read()

    prompt = """
    You are a medical OCR assistant. Extract Complete Blood Count (CBC) values from this lab report.
    Return ONLY a JSON object with the following keys:
    - "rbc": Red Blood Cell count
    - "mcv": Mean Corpuscular Volume
    - "mch": Mean Corpuscular Hemoglobin
    - "mchc": Mean Corpuscular Hemoglobin Concentration
    - "rdw": Red Cell Distribution Width
    - "tlc": Total Leucocyte Count (or WBC)
    - "plt": Platelet count
    - "hgb": Hemoglobin (Haemoglobin)

    Rules:
    1. Only include numeric values.
    2. If a value is not found, omit the key or set it to null.
    3. Use the most clear and unambiguous value if multiple are present.
    """

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=file_data, mime_type=mime_type)
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        import json
        extracted_data = json.loads(response.text)
        
        # Filter and clean values
        values = {}
        confidence = {}
        warnings = []
        
        for field in ["rbc", "mcv", "mch", "mchc", "rdw", "tlc", "plt", "hgb"]:
            val = extracted_data.get(field)
            if val is not None:
                try:
                    num_val = float(val)
                    values[field] = num_val
                    
                    # Basic range-based confidence (similar to old logic)
                    lo, hi = _TYPICAL_RANGES[field]
                    if lo <= num_val <= hi:
                        confidence[field] = "High"
                    else:
                        confidence[field] = "Medium"
                        warnings.append(f"{_FIELD_LABELS[field]} value {num_val} is outside typical range.")
                except (ValueError, TypeError):
                    warnings.append(f"Non-numeric value extracted for {field}: {val}")
            else:
                warnings.append(f"Could not find {_FIELD_LABELS[field]} in the report.")
                
        return {
            "values": values,
            "confidence": confidence,
            "warnings": warnings
        }
        
    except Exception as e:
        logger.error("Gemini OCR failed: %s", e)
        return {
            "values": {},
            "confidence": {},
            "warnings": [f"AI OCR failed: {str(e)}"]
        }


def _extract_fields(text: str) -> tuple[dict[str, float], dict[str, str], list[str]]:
    """
    Apply regex patterns to OCR text and extract CBC field values.

    Returns:
        values     — dict of field_name → float
        confidence — dict of field_name → "High" | "Medium" | "Low"
        warnings   — list of warning strings for unextracted fields
    """
    values: dict[str, float] = {}
    confidence: dict[str, str] = {}
    warnings: list[str] = []

    for field, pattern in _PATTERNS.items():
        matches = re.findall(pattern, text, re.IGNORECASE)

        if not matches:
            # No match found — field not included, add warning
            warnings.append(
                f"Could not extract {_FIELD_LABELS[field]} from the report."
            )
            continue

        if len(matches) == 1:
            # Single unambiguous match
            try:
                value = float(matches[0])
            except ValueError:
                warnings.append(
                    f"Extracted value for {_FIELD_LABELS[field]} is not numeric: "
                    f"{matches[0]!r}."
                )
                continue

            # Check if value is within typical range
            lo, hi = _TYPICAL_RANGES[field]
            if lo <= value <= hi:
                conf = "High"
            else:
                conf = "Medium"
                warnings.append(
                    f"{_FIELD_LABELS[field]} value {value} is outside the typical "
                    f"range [{lo}, {hi}] — please verify."
                )

            values[field] = value
            confidence[field] = conf

        else:
            # Multiple matches — ambiguous; take the first, mark as Medium
            try:
                value = float(matches[0])
            except ValueError:
                warnings.append(
                    f"Extracted value for {_FIELD_LABELS[field]} is not numeric: "
                    f"{matches[0]!r}."
                )
                continue

            lo, hi = _TYPICAL_RANGES[field]
            if lo <= value <= hi:
                conf = "Medium"
            else:
                conf = "Medium"

            values[field] = value
            confidence[field] = conf
            warnings.append(
                f"Multiple matches found for {_FIELD_LABELS[field]}; "
                f"using first value {value}. Please verify."
            )

    return values, confidence, warnings


def extract_cbc_from_file(
    filepath: str,
    mime_type: str,
) -> dict[str, Any]:
    """
    Extract CBC field values from an uploaded blood-report file.

    Parameters
    ----------
    filepath  : str
        Absolute or relative path to the temporary file on disk.
    mime_type : str
        MIME type of the file: "image/jpeg", "image/png", or "application/pdf".

    Returns
    -------
    dict with keys:
        "values"     : dict[str, float]  — extracted CBC fields
        "confidence" : dict[str, str]    — "High" | "Medium" | "Low" per field
        "warnings"   : list[str]         — messages for missing/unusual fields
    """
    empty_result: dict[str, Any] = {
        "values": {},
        "confidence": {},
        "warnings": [],
    }

    # ── Step 1-3: Process with Gemini ─────────────────────────────────────────
    return _run_gemini_ocr(filepath, mime_type)
