"""
OCR Blueprint — /api/ocr

Handles CBC report image/PDF upload and Tesseract-based field extraction.

Routes:
    GET  /api/ocr/          → health check
    POST /api/ocr/upload    → upload file, extract CBC fields via OCR
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
import logging

from flask import Blueprint, jsonify, request

from middleware.auth import require_auth
from services.ocr_service import extract_cbc_from_file

logger = logging.getLogger(__name__)

ocr_bp = Blueprint("ocr", __name__, url_prefix="/api/ocr")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Suffix map for tempfile creation
_MIME_TO_SUFFIX: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/pdf": ".pdf",
}

# Delay before the temporary file is deleted (seconds)
_TEMP_FILE_DELETE_DELAY = 60


# ---------------------------------------------------------------------------
# Helper: schedule file deletion
# ---------------------------------------------------------------------------

def _schedule_delete(filepath: str, delay: int = _TEMP_FILE_DELETE_DELAY) -> None:
    """Delete *filepath* after *delay* seconds in a background thread."""

    def _delete() -> None:
        time.sleep(delay)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.debug("Deleted temporary OCR file: %s", filepath)
        except OSError as exc:
            logger.warning("Failed to delete temporary OCR file %s: %s", filepath, exc)

    t = threading.Thread(target=_delete, daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@ocr_bp.get("/")
def index():
    """Health check for the OCR blueprint."""
    return jsonify({"status": "ok", "blueprint": "ocr"})


@ocr_bp.post("/upload")
@require_auth
def upload():
    """
    POST /api/ocr/upload

    Accept a multipart/form-data upload with a single field named "file".
    Validate MIME type and file size, run OCR, and return extracted CBC values.

    Request
    -------
    Content-Type: multipart/form-data
    Body field:   file  (JPEG, PNG, or PDF; max 10 MB)

    Response 200
    ------------
    {
        "status":     "ok",
        "values":     { "hgb": float, ... },
        "confidence": { "hgb": "High"|"Medium"|"Low", ... },
        "warnings":   [ str, ... ]
    }

    Response 400
    ------------
    { "status": "error", "message": str }
    """
    # ── 1. Check file field is present ────────────────────────────────────────
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file field in request."}), 400

    uploaded_file = request.files["file"]

    if uploaded_file.filename == "":
        return jsonify({"status": "error", "message": "No file selected."}), 400

    # ── 2. Validate MIME type ─────────────────────────────────────────────────
    mime_type: str = uploaded_file.content_type or ""

    # Normalise: strip parameters (e.g. "image/jpeg; charset=utf-8" → "image/jpeg")
    mime_type = mime_type.split(";")[0].strip().lower()

    if mime_type not in ALLOWED_MIME_TYPES:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": (
                        f"Unsupported file type: {mime_type!r}. "
                        "Allowed types: image/jpeg, image/png, application/pdf."
                    ),
                }
            ),
            400,
        )

    # ── 3. Validate file size (read into memory once) ─────────────────────────
    data: bytes = uploaded_file.read()

    if len(data) > MAX_FILE_SIZE_BYTES:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": (
                        f"File size {len(data)} bytes exceeds the 10 MB limit. "
                        "Please upload a smaller file."
                    ),
                }
            ),
            400,
        )

    # ── 4. Save to a named temporary file ─────────────────────────────────────
    suffix = _MIME_TO_SUFFIX.get(mime_type, "")

    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix, delete=False
        ) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
    except OSError as exc:
        logger.error("Failed to write temporary file: %s", exc)
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Server error: could not save uploaded file.",
                }
            ),
            500,
        )

    # ── 5. Run OCR ────────────────────────────────────────────────────────────
    try:
        result = extract_cbc_from_file(tmp_path, mime_type)
    except Exception as exc:  # noqa: BLE001
        logger.error("OCR extraction failed: %s", exc)
        # Schedule cleanup even on failure
        _schedule_delete(tmp_path)
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"OCR processing failed: {exc}",
                }
            ),
            500,
        )

    # ── 6. Schedule file deletion within 60 s ─────────────────────────────────
    _schedule_delete(tmp_path)

    # ── 7. Return result ──────────────────────────────────────────────────────
    return jsonify(
        {
            "status": "ok",
            "values": result.get("values", {}),
            "confidence": result.get("confidence", {}),
            "warnings": result.get("warnings", []),
        }
    )
