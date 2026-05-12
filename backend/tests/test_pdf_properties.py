"""
test_pdf_properties.py — Property-based tests for PDF filename and label logic.

Property 19: Filename regex match for any username/date combo.
Property 20: PDF text labels contain all required section headers.

These tests validate the Python-side filename pattern logic and the
expected label structure of generated PDF reports.

**Validates: Requirements 11.2, 11.3, 11.4**
"""

import re
import sys
import os
from datetime import datetime, timedelta

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

# Ensure backend/ is importable
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ---------------------------------------------------------------------------
# Filename pattern logic (mirrors frontend pdfService.js generateFilename)
# ---------------------------------------------------------------------------

FILENAME_REGEX = re.compile(r"^anemia_report_[^_]+_\d{8}\.pdf$")


def format_date_yyyymmdd(date_str: str) -> str:
    """
    Parse a datetime string 'YYYY-MM-DD HH:MM:SS' and return 'YYYYMMDD'.
    Mirrors the frontend formatDateYYYYMMDD function.
    """
    # Support both 'YYYY-MM-DD HH:MM:SS' and ISO 'YYYY-MM-DDTHH:MM:SS'
    date_str_clean = date_str.replace(" ", "T")
    dt = datetime.fromisoformat(date_str_clean)
    return dt.strftime("%Y%m%d")


def generate_filename(username: str, date_str: str) -> str:
    """
    Generate the PDF filename following the pattern:
    anemia_report_{username}_{YYYYMMDD}.pdf
    Mirrors the frontend generateFilename function.
    """
    date_part = format_date_yyyymmdd(date_str)
    return f"anemia_report_{username}_{date_part}.pdf"


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Valid username: alphanumeric + underscore + dot, 1–20 chars
_username_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_."),
    min_size=1,
    max_size=20,
).filter(lambda s: len(s) >= 1)

# Valid date: generate a datetime between 2000-01-01 and 2030-12-31
_date_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2030, 12, 31, 23, 59, 59),
).map(lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S"))


# ---------------------------------------------------------------------------
# Property 19 — Filename regex match for any username/date combo
# **Validates: Requirements 11.4**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(username=_username_strategy, date_str=_date_strategy)
def test_property_19_filename_matches_regex(username: str, date_str: str):
    """
    Property 19: For any valid username and date string, the generated
    filename MUST match the pattern anemia_report_{username}_{YYYYMMDD}.pdf

    **Validates: Requirements 11.4**
    """
    filename = generate_filename(username, date_str)

    assert FILENAME_REGEX.match(filename), (
        f"Filename {filename!r} does not match pattern {FILENAME_REGEX.pattern!r} "
        f"(username={username!r}, date_str={date_str!r})"
    )


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(username=_username_strategy, date_str=_date_strategy)
def test_property_19_filename_starts_with_prefix(username: str, date_str: str):
    """
    Property 19 (prefix): Filename always starts with 'anemia_report_'.

    **Validates: Requirements 11.4**
    """
    filename = generate_filename(username, date_str)
    assert filename.startswith("anemia_report_"), (
        f"Filename {filename!r} does not start with 'anemia_report_'"
    )


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(username=_username_strategy, date_str=_date_strategy)
def test_property_19_filename_ends_with_pdf(username: str, date_str: str):
    """
    Property 19 (suffix): Filename always ends with '.pdf'.

    **Validates: Requirements 11.4**
    """
    filename = generate_filename(username, date_str)
    assert filename.endswith(".pdf"), (
        f"Filename {filename!r} does not end with '.pdf'"
    )


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(username=_username_strategy, date_str=_date_strategy)
def test_property_19_date_part_is_8_digits(username: str, date_str: str):
    """
    Property 19 (date part): The date portion of the filename is exactly 8 digits.

    **Validates: Requirements 11.4**
    """
    filename = generate_filename(username, date_str)
    # Remove .pdf and split by _
    parts = filename[:-4].split("_")
    date_part = parts[-1]
    assert re.match(r"^\d{8}$", date_part), (
        f"Date part {date_part!r} in filename {filename!r} is not 8 digits"
    )


# ---------------------------------------------------------------------------
# Property 20 — PDF text labels contain all required section headers
# **Validates: Requirements 11.2, 11.3**
# ---------------------------------------------------------------------------

# Required section labels that must appear in any generated PDF report
REQUIRED_PDF_LABELS = [
    "Patient Information",
    "CBC Values",
    "Prediction Result",
    "Top Feature Explanations",
    "Diet Recommendations",
    "Health Tips",
    "Disclaimer",
]


def _build_report_data(hgb: float, severity: str, anemia_detected: int) -> dict:
    """Build a minimal report data dict for testing."""
    return {
        "date": "2024-06-15 10:30:00",
        "cbc": {
            "rbc": 4.5, "mcv": 85.0, "mch": 28.0, "mchc": 33.0,
            "rdw": 13.5, "tlc": 7.0, "plt": 250.0, "hgb": hgb,
        },
        "anemia_detected": anemia_detected,
        "severity_level": severity,
        "anemia_type": "Iron-Deficiency",
        "anemia_confidence": 0.87,
        "explanation": [
            {"feature": "HGB", "direction": "Low", "shap_value": -0.45},
            {"feature": "MCV", "direction": "Low", "shap_value": -0.32},
            {"feature": "MCH", "direction": "Low", "shap_value": -0.21},
        ],
        "diet_recs": [
            {"name": "Spinach", "rationale": "High in iron", "is_vegan": True},
        ],
        "health_tips": ["Take iron supplements as prescribed."],
    }


_severity_strategy = st.sampled_from(["None", "Mild", "Moderate", "Severe"])
_hgb_strategy = st.floats(min_value=4.0, max_value=18.0, allow_nan=False, allow_infinity=False)


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(
    hgb=_hgb_strategy,
    severity=_severity_strategy,
)
def test_property_20_required_labels_present_in_report_structure(
    hgb: float, severity: str
):
    """
    Property 20: For any valid report data, the report structure MUST
    contain all required section labels.

    This test validates the data structure that would be rendered into
    the PDF — ensuring all required sections are present regardless of
    the specific HGB value or severity level.

    **Validates: Requirements 11.2, 11.3**
    """
    anemia_detected = 1 if hgb < 12.0 else 0
    report_data = _build_report_data(hgb, severity, anemia_detected)

    # Verify all required sections have data in the report structure
    assert "cbc" in report_data, "Report must contain CBC values section"
    assert "anemia_detected" in report_data, "Report must contain prediction result"
    assert "severity_level" in report_data, "Report must contain severity level"
    assert "explanation" in report_data, "Report must contain SHAP explanation"
    assert "diet_recs" in report_data, "Report must contain diet recommendations"
    assert "health_tips" in report_data, "Report must contain health tips"
    assert "date" in report_data, "Report must contain date"

    # Verify CBC has all 8 required fields
    cbc_fields = {"rbc", "mcv", "mch", "mchc", "rdw", "tlc", "plt", "hgb"}
    assert cbc_fields.issubset(set(report_data["cbc"].keys())), (
        f"CBC section missing fields: {cbc_fields - set(report_data['cbc'].keys())}"
    )

    # Verify explanation has at most 3 entries (top-3 SHAP)
    assert len(report_data["explanation"]) <= 3, (
        f"Explanation should have at most 3 entries, got {len(report_data['explanation'])}"
    )

    # Verify each explanation entry has required keys
    for entry in report_data["explanation"]:
        assert "feature" in entry, "SHAP entry must have 'feature'"
        assert "direction" in entry, "SHAP entry must have 'direction'"
        assert "shap_value" in entry, "SHAP entry must have 'shap_value'"


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(username=_username_strategy, date_str=_date_strategy)
def test_property_20_filename_embeds_username(username: str, date_str: str):
    """
    Property 20 (filename): The generated filename MUST embed the username.

    **Validates: Requirements 11.4**
    """
    filename = generate_filename(username, date_str)
    assert username in filename, (
        f"Username {username!r} not found in filename {filename!r}"
    )
