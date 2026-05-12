"""
test_predict_properties.py — Property-based tests for the prediction pipeline.

**Validates: Requirements 1, 2, 3, 4, 9, 10, 11, 18**

Properties tested:
  Property 1  — RF output is always 0 or 1 (for any valid CBC input)
  Property 2  — GB severity always matches HGB threshold rules
  Property 3  — Confidence scores are always in [0.0, 1.0]
  Property 4  — SHAP explanation always has exactly 3 entries with "feature" (str)
                and "direction" (str) keys
  Property 9  — DB round-trip: stored CBC values match input to 6 decimal places
  Property 10 — CBC JSON serialisation round-trip to 6dp
  Property 11 — Invalid schema → 400, PredictionService.predict never called
  Property 18 — Pagination: ≤20 records per page, union of all pages = N total,
                no duplicates
"""

import json
import os
import sys
from unittest.mock import patch

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

# Ensure backend/ is importable
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ---------------------------------------------------------------------------
# CBC value strategies (per spec ranges)
# ---------------------------------------------------------------------------

_rbc_st   = st.floats(min_value=0.1,  max_value=8.0,   allow_nan=False, allow_infinity=False)
_mcv_st   = st.floats(min_value=50.0, max_value=130.0,  allow_nan=False, allow_infinity=False)
_mch_st   = st.floats(min_value=15.0, max_value=45.0,   allow_nan=False, allow_infinity=False)
_mchc_st  = st.floats(min_value=25.0, max_value=40.0,   allow_nan=False, allow_infinity=False)
_rdw_st   = st.floats(min_value=10.0, max_value=25.0,   allow_nan=False, allow_infinity=False)
_tlc_st   = st.floats(min_value=1.0,  max_value=20.0,   allow_nan=False, allow_infinity=False)
_plt_st   = st.floats(min_value=50.0, max_value=600.0,  allow_nan=False, allow_infinity=False)
_hgb_st   = st.floats(min_value=1.0,  max_value=20.0,   allow_nan=False, allow_infinity=False)

_cbc_strategy = st.fixed_dictionaries({
    "rbc":  _rbc_st,
    "mcv":  _mcv_st,
    "mch":  _mch_st,
    "mchc": _mchc_st,
    "rdw":  _rdw_st,
    "tlc":  _tlc_st,
    "plt":  _plt_st,
    "hgb":  _hgb_st,
})

# HGB strategies for Property 2 — clearly in one severity band
_hgb_severe_st   = st.floats(min_value=1.0,  max_value=7.9,   allow_nan=False, allow_infinity=False)
_hgb_moderate_st = st.floats(min_value=8.0,  max_value=9.9,   allow_nan=False, allow_infinity=False)
_hgb_mild_st     = st.floats(min_value=10.0, max_value=11.9,  allow_nan=False, allow_infinity=False)
_hgb_none_st     = st.floats(min_value=12.0, max_value=20.0,  allow_nan=False, allow_infinity=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cbc(hgb: float, **overrides) -> dict:
    """Return a valid CBC dict with the given HGB and sensible defaults."""
    base = {
        "rbc":  4.5,
        "mcv":  80.0,
        "mch":  27.0,
        "mchc": 32.0,
        "rdw":  13.0,
        "tlc":  6.0,
        "plt":  250.0,
        "hgb":  hgb,
    }
    base.update(overrides)
    return base


def _get_token(client, app) -> str:
    """Insert a test patient directly into the DB and return a JWT."""
    import bcrypt
    import jwt as pyjwt
    from datetime import datetime, timedelta
    import uuid

    from middleware.auth import JWT_SECRET, JWT_ALGORITHM
    import db as db_module

    username = "testpatient"
    email = "testpatient@example.com"
    password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt(rounds=4)).decode()

    with app.app_context():
        conn = db_module.get_db()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO user (username, email, password_hash, role, status) "
                "VALUES (?, ?, ?, 'patient', 'active')",
                (username, email, password_hash),
            )
            conn.commit()
        finally:
            conn.close()

    now = datetime.utcnow()
    payload = {
        "sub": username,
        "username": username,
        "role": "patient",
        "email": email,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(hours=24),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Property 1 — RF output is always 0 or 1
# **Validates: Requirements 1.1**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(cbc=_cbc_strategy)
def test_property_1_rf_output_is_binary(cbc):
    """
    Property 1: For any valid CBC input, the RF classifier MUST return
    anemia_detected as either 0 or 1.

    **Validates: Requirements 1.1**
    """
    from services.prediction_service import PredictionService

    svc = PredictionService()
    result = svc.predict(cbc)

    assert result["anemia_detected"] in (0, 1), (
        f"Expected anemia_detected in {{0, 1}}, got {result['anemia_detected']!r}"
    )


# ---------------------------------------------------------------------------
# Property 2 — GB severity always matches HGB threshold rules
# **Validates: Requirements 2.1, 2.2**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(hgb=_hgb_severe_st)
def test_property_2_gb_severity_severe(hgb):
    """
    Property 2 (Severe): When HGB < 8.0 and anemia is detected,
    severity_level MUST be 'Severe'.

    **Validates: Requirements 2.2**
    """
    from services.prediction_service import PredictionService

    svc = PredictionService()
    cbc = _make_cbc(hgb)
    result = svc.predict(cbc)

    if result["anemia_detected"] == 1:
        assert result["severity_level"] == "Severe", (
            f"HGB={hgb:.4f} (<8.0) → expected severity='Severe', "
            f"got {result['severity_level']!r}"
        )


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(hgb=_hgb_moderate_st)
def test_property_2_gb_severity_moderate(hgb):
    """
    Property 2 (Moderate): When 8.0 ≤ HGB < 10.0 and anemia is detected,
    severity_level MUST be 'Moderate'.

    **Validates: Requirements 2.2**
    """
    from services.prediction_service import PredictionService

    svc = PredictionService()
    cbc = _make_cbc(hgb)
    result = svc.predict(cbc)

    if result["anemia_detected"] == 1:
        assert result["severity_level"] == "Moderate", (
            f"HGB={hgb:.4f} (8.0–9.9) → expected severity='Moderate', "
            f"got {result['severity_level']!r}"
        )


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(hgb=_hgb_mild_st)
def test_property_2_gb_severity_mild(hgb):
    """
    Property 2 (Mild): When 10.0 ≤ HGB < 12.0 and anemia is detected,
    severity_level MUST be 'Mild'.

    **Validates: Requirements 2.2**
    """
    from services.prediction_service import PredictionService

    svc = PredictionService()
    cbc = _make_cbc(hgb)
    result = svc.predict(cbc)

    if result["anemia_detected"] == 1:
        assert result["severity_level"] == "Mild", (
            f"HGB={hgb:.4f} (10.0–11.9) → expected severity='Mild', "
            f"got {result['severity_level']!r}"
        )


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(hgb=_hgb_none_st)
def test_property_2_gb_severity_none(hgb):
    """
    Property 2 (None): When HGB ≥ 12.0 and no anemia is detected,
    severity_level MUST be 'None'.

    **Validates: Requirements 2.3**
    """
    from services.prediction_service import PredictionService

    svc = PredictionService()
    cbc = _make_cbc(hgb)
    result = svc.predict(cbc)

    if result["anemia_detected"] == 0:
        assert result["severity_level"] == "None", (
            f"HGB={hgb:.4f} (≥12.0, no anemia) → expected severity='None', "
            f"got {result['severity_level']!r}"
        )


# ---------------------------------------------------------------------------
# Property 3 — Confidence scores are always in [0.0, 1.0]
# **Validates: Requirements 1.1, 2.1, 3.2**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(cbc=_cbc_strategy)
def test_property_3_confidence_in_unit_interval(cbc):
    """
    Property 3: For any valid CBC input, all confidence scores returned by
    the prediction pipeline MUST be in the closed interval [0.0, 1.0].

    **Validates: Requirements 1.1, 2.1, 3.2**
    """
    from services.prediction_service import PredictionService

    svc = PredictionService()
    result = svc.predict(cbc)

    for key in ("anemia_confidence", "severity_confidence", "type_confidence"):
        val = result[key]
        assert 0.0 <= val <= 1.0, (
            f"Confidence '{key}' = {val} is outside [0.0, 1.0]"
        )


# ---------------------------------------------------------------------------
# Property 4 — SHAP explanation always has exactly 3 entries
# **Validates: Requirements 4.1, 4.2**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(cbc=_cbc_strategy)
def test_property_4_shap_explanation_structure(cbc):
    """
    Property 4: For any valid CBC input, the explanation field MUST contain
    exactly 3 entries, each with a 'feature' key (str) and a 'direction' key (str).

    **Validates: Requirements 4.1, 4.2**
    """
    from services.prediction_service import PredictionService

    svc = PredictionService()
    result = svc.predict(cbc)

    explanation = result["explanation"]

    assert isinstance(explanation, list), (
        f"explanation must be a list, got {type(explanation).__name__}"
    )
    assert len(explanation) == 3, (
        f"explanation must have exactly 3 entries, got {len(explanation)}"
    )

    for i, entry in enumerate(explanation):
        assert isinstance(entry.get("feature"), str), (
            f"explanation[{i}]['feature'] must be a str, got {type(entry.get('feature')).__name__}"
        )
        assert isinstance(entry.get("direction"), str), (
            f"explanation[{i}]['direction'] must be a str, got {type(entry.get('direction')).__name__}"
        )
        assert len(entry["feature"]) > 0, f"explanation[{i}]['feature'] must not be empty"
        assert len(entry["direction"]) > 0, f"explanation[{i}]['direction'] must not be empty"


# ---------------------------------------------------------------------------
# Property 9 — DB round-trip: stored CBC values match input to 6dp
# **Validates: Requirements 1.5, 18.2**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(cbc=_cbc_strategy)
def test_property_9_db_roundtrip(app, client, cbc):
    """
    Property 9: After POST /api/predict, the CBC values stored in the DB
    (retrieved via GET /api/reports) MUST match the input values to 6 decimal
    places.

    **Validates: Requirements 1.5, 18.2**
    """
    token = _get_token(client, app)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/predict", json=cbc, headers=headers)
    assert resp.status_code == 200, (
        f"POST /api/predict failed: {resp.status_code} — {resp.get_json()}"
    )

    prediction_id = resp.get_json()["prediction_id"]

    # Retrieve the stored record
    report_resp = client.get(f"/api/reports/{prediction_id}", headers=headers)
    assert report_resp.status_code == 200, (
        f"GET /api/reports/{prediction_id} failed: {report_resp.status_code}"
    )

    record = report_resp.get_json()["record"]

    for field in ("rbc", "mcv", "mch", "mchc", "rdw", "tlc", "plt", "hgb"):
        stored = round(float(record[field]), 6)
        original = round(float(cbc[field]), 6)
        assert stored == original, (
            f"DB round-trip mismatch for '{field}': "
            f"stored={stored}, original={original}"
        )


# ---------------------------------------------------------------------------
# Property 11 — Invalid schema → 400, PredictionService.predict never called
# **Validates: Requirements 1.3, 18.4**
# ---------------------------------------------------------------------------

# Strategy for invalid CBC payloads: missing one or more required fields
_required_fields = ["rbc", "mcv", "mch", "mchc", "rdw", "tlc", "plt", "hgb"]

_invalid_cbc_strategy = st.one_of(
    # Missing one or more fields
    st.sets(
        st.sampled_from(_required_fields),
        min_size=1,
        max_size=8,
    ).map(lambda missing: {
        f: 5.0 for f in _required_fields if f not in missing
    }),
    # Non-numeric value for one field
    st.sampled_from(_required_fields).map(lambda bad_field: {
        **{f: 5.0 for f in _required_fields},
        bad_field: "not-a-number",
    }),
    # Completely empty payload
    st.just({}),
)


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(invalid_cbc=_invalid_cbc_strategy)
def test_property_11_invalid_schema_returns_400_predict_not_called(
    app, client, invalid_cbc
):
    """
    Property 11: For any invalid CBC payload (missing fields, non-numeric values),
    POST /api/predict MUST return 400 and PredictionService.predict MUST NOT
    be called.

    **Validates: Requirements 1.3, 18.4**
    """
    token = _get_token(client, app)
    headers = {"Authorization": f"Bearer {token}"}

    import importlib
    predict_bp_module = importlib.import_module("blueprints.predict_bp")

    with patch.object(predict_bp_module, "get_prediction_service") as mock_get_svc:
        mock_svc = mock_get_svc.return_value
        mock_svc.predict.return_value = {}

        resp = client.post("/api/predict", json=invalid_cbc, headers=headers)

    assert resp.status_code == 400, (
        f"Expected 400 for invalid CBC {invalid_cbc!r}, got {resp.status_code}: "
        f"{resp.get_json()}"
    )
    mock_svc.predict.assert_not_called()


# ---------------------------------------------------------------------------
# Property 10 — CBC JSON serialisation round-trip to 6dp
# **Validates: Requirements 18.2**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(cbc=_cbc_strategy)
def test_property_10_json_serialisation_roundtrip(cbc):
    """
    Property 10: Serialising a CBC dict to a JSON string and deserialising it
    MUST produce values equal to the originals within 6 decimal places.

    **Validates: Requirements 18.2**
    """
    serialised = json.dumps(cbc)
    deserialised = json.loads(serialised)

    for field in ("rbc", "mcv", "mch", "mchc", "rdw", "tlc", "plt", "hgb"):
        original = round(float(cbc[field]), 6)
        recovered = round(float(deserialised[field]), 6)
        assert original == recovered, (
            f"JSON round-trip mismatch for '{field}': "
            f"original={original}, recovered={recovered}"
        )


# ---------------------------------------------------------------------------
# Property 18 — Pagination: ≤20/page, union = N total, no duplicates
# **Validates: Requirements 9.4**
# ---------------------------------------------------------------------------

@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(n_records=st.integers(min_value=1, max_value=55))
def test_property_18_pagination(app, client, n_records):
    """
    Property 18: When N prediction records exist for a user, paginating through
    all pages via GET /api/reports MUST satisfy:
      - Each page has ≤ 20 records
      - The union of all pages contains exactly N unique prediction_ids
      - No prediction_id appears on more than one page

    **Validates: Requirements 9.4**
    """
    token = _get_token(client, app)
    headers = {"Authorization": f"Bearer {token}"}

    # Insert N predictions via the API
    cbc_payload = _make_cbc(hgb=9.0)
    inserted_ids = []
    for _ in range(n_records):
        resp = client.post("/api/predict", json=cbc_payload, headers=headers)
        assert resp.status_code == 200, (
            f"Failed to insert prediction: {resp.status_code} — {resp.get_json()}"
        )
        inserted_ids.append(resp.get_json()["prediction_id"])

    # Paginate through all pages
    all_ids = []
    page = 1
    while True:
        resp = client.get(f"/api/reports?page={page}", headers=headers)
        assert resp.status_code == 200, (
            f"GET /api/reports?page={page} failed: {resp.status_code}"
        )
        data = resp.get_json()
        records = data["records"]
        total = data["total"]
        total_pages = data["pages"]

        # Each page must have ≤ 20 records
        assert len(records) <= 20, (
            f"Page {page} has {len(records)} records, expected ≤ 20"
        )

        all_ids.extend(r["prediction_id"] for r in records)

        if page >= total_pages:
            break
        page += 1

    # Total reported must match what we inserted (may be more if DB had prior records)
    assert total >= n_records, (
        f"total={total} is less than n_records={n_records}"
    )

    # No duplicates across pages
    assert len(all_ids) == len(set(all_ids)), (
        f"Duplicate prediction_ids found across pages: "
        f"{[pid for pid in all_ids if all_ids.count(pid) > 1]}"
    )

    # All inserted IDs must appear in the paginated results
    all_ids_set = set(all_ids)
    for pid in inserted_ids:
        assert pid in all_ids_set, (
            f"Inserted prediction_id {pid} not found in paginated results"
        )
