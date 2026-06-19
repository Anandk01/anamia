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
import re
import base64
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Typical reference ranges
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
    """Use Gemini 3.5 Flash to extract CBC values from the report file."""
    import json as _json

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {"values": {}, "confidence": {}, "warnings": ["GEMINI_API_KEY not configured"]}

    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)



    # Read file
    with open(image_path, "rb") as f:
        file_data = f.read()

    if len(file_data) > 10 * 1024 * 1024:
        return {"values": {}, "confidence": {}, "warnings": ["File too large (>10MB)"]}

    # Detect mime from bytes if needed
    if mime_type not in ("image/jpeg", "image/png", "image/webp", "application/pdf"):
        if file_data[:3] == b'\xff\xd8\xff':
            mime_type = "image/jpeg"
        elif file_data[:8] == b'\x89PNG\r\n\x1a\n':
            mime_type = "image/png"
        elif file_data[:4] == b'%PDF':
            mime_type = "application/pdf"
        else:
            mime_type = "image/jpeg"

    prompt = """Extract CBC values from this lab report. Return ONLY JSON:
{"rbc": number, "mcv": number, "mch": number, "mchc": number, "rdw": number, "tlc": number, "plt": number, "hgb": number}
Omit keys if not found."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=file_data, mime_type=mime_type),
            ],
        )
        raw_text = response.text.strip()

        # Parse JSON
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        extracted_data = _json.loads(raw_text)

        values = {}
        confidence = {}
        warnings = []

        for field in ["rbc", "mcv", "mch", "mchc", "rdw", "tlc", "plt", "hgb"]:
            val = extracted_data.get(field)
            if val is not None:
                try:
                    num_val = float(val)
                    values[field] = num_val
                    lo, hi = _TYPICAL_RANGES[field]
                    confidence[field] = "High" if lo <= num_val <= hi else "Medium"
                except (ValueError, TypeError):
                    warnings.append(f"Non-numeric {field}: {val}")
            else:
                warnings.append(f"Could not find {_FIELD_LABELS[field]}")

        return {"values": values, "confidence": confidence, "warnings": warnings}

    except Exception as e:
        logger.error("Gemini OCR failed: %s", e)
        return {"values": {}, "confidence": {}, "warnings": [f"AI OCR failed: {str(e)}"]}


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


def _run_tesseract_ocr(filepath: str, mime_type: str) -> dict:
    """
    Use Tesseract OCR to extract CBC values from the report file.
    Falls back to regex extraction from OCR text.
    """
    import pytesseract
    from PIL import Image

    # Set Tesseract path
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

    try:
        # For PDFs, convert first page to image
        if mime_type == "application/pdf":
            try:
                import fitz
                doc = fitz.open(filepath)
                if doc.page_count == 0:
                    return {"values": {}, "confidence": {}, "warnings": ["PDF has no pages"]}
                page = doc[0]
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                doc.close()
                # Load from bytes
                import io
                image = Image.open(io.BytesIO(img_bytes))
            except Exception as e:
                return {"values": {}, "confidence": {}, "warnings": [f"PDF processing failed: {str(e)}"]}
        else:
            # Direct image
            image = Image.open(filepath)

        # Run Tesseract OCR
        text = pytesseract.image_to_string(image)
        logger.info("Tesseract OCR extracted %d characters", len(text))

        if not text.strip():
            return {"values": {}, "confidence": {}, "warnings": ["Could not extract any text from the image"]}

        # Use regex-based extraction
        values, confidence, warnings = _extract_fields(text)

        if not values:
            warnings.append("Could not identify CBC values in the extracted text.")

        return {"values": values, "confidence": confidence, "warnings": warnings}

    except Exception as e:
        logger.error("Tesseract OCR failed: %s", e)
        return {"values": {}, "confidence": {}, "warnings": [f"OCR failed: {str(e)}"]}


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

    # ── Use Gemini OCR ────────────────────────────────────────────────────────
    return _run_gemini_ocr(filepath, mime_type)
