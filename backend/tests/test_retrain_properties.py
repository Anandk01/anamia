"""
test_retrain_properties.py — Property-based tests for the retraining pipeline.

**Validates: Requirements 16.1, 16.2**

Properties tested:
  Property 22 — Any CSV missing required columns → 400 listing each missing
                column, no retrain_log row created.
"""

import io
import os
import sys
from unittest.mock import patch

import pandas as pd
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

# Ensure backend/ is importable
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = ["rbc", "mcv", "mch", "mchc", "rdw", "tlc", "plt", "hgb", "label"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_admin_token(app) -> str:
    """Create a JWT for the seeded admin account."""
    import jwt as pyjwt
    from datetime import datetime, timedelta
    import uuid

    secret = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
    payload = {
        "username": "admin",
        "role": "admin",
        "email": "admin@anemia.local",
        "jti": str(uuid.uuid4()),
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


def _build_csv_bytes(columns: list[str], n_rows: int = 5) -> bytes:
    """Build a minimal valid CSV with the given columns and numeric data."""
    data = {col: [1.0] * n_rows for col in columns}
    df = pd.DataFrame(data)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Property 22 — Missing required columns → 400, no retrain_log row created
# **Validates: Requirements 16.1, 16.2**
# ---------------------------------------------------------------------------


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
)
@given(
    present_cols=st.sets(
        st.sampled_from(REQUIRED_COLUMNS),
        min_size=1,                           # at least 1 col so CSV is parseable
        max_size=len(REQUIRED_COLUMNS) - 1,  # always at least one missing
    )
)
def test_property_22_missing_columns_returns_400_no_retrain_log(
    app, client, db_conn, present_cols
):
    """
    Property 22: Any CSV upload that is missing at least one required column
    MUST return HTTP 400 with a list of missing columns, and MUST NOT create
    any row in the retrain_log table.

    **Validates: Requirements 16.1, 16.2**
    """
    # Ensure at least one column is missing
    missing_cols = set(REQUIRED_COLUMNS) - present_cols
    assert len(missing_cols) >= 1, "Test invariant: at least one column must be missing"

    token = _make_admin_token(app)
    headers = {"Authorization": f"Bearer {token}"}

    # Count retrain_log rows before the request
    before_count = db_conn.execute(
        "SELECT COUNT(*) FROM retrain_log"
    ).fetchone()[0]

    # Build CSV with only the present columns
    csv_bytes = _build_csv_bytes(list(present_cols), n_rows=3)

    resp = client.post(
        "/api/retrain/upload",
        data={"file": (io.BytesIO(csv_bytes), "test_upload.csv")},
        content_type="multipart/form-data",
        headers=headers,
    )

    # Must return 400
    assert resp.status_code == 400, (
        f"Expected 400 for CSV missing columns {missing_cols}, "
        f"got {resp.status_code}: {resp.get_json()}"
    )

    data = resp.get_json()
    assert data is not None, "Response body must be JSON"
    assert data.get("status") == "error", (
        f"Expected status='error', got {data.get('status')!r}"
    )

    # The errors list must mention each missing column
    errors = data.get("errors", [])
    assert isinstance(errors, list), f"'errors' must be a list, got {type(errors)}"
    assert len(errors) >= 1, "At least one error must be reported"

    errors_text = " ".join(errors).lower()
    for col in missing_cols:
        assert col in errors_text, (
            f"Missing column '{col}' not mentioned in errors: {errors}"
        )

    # No new retrain_log row must have been created
    after_count = db_conn.execute(
        "SELECT COUNT(*) FROM retrain_log"
    ).fetchone()[0]
    assert after_count == before_count, (
        f"retrain_log row was created despite invalid CSV upload "
        f"(before={before_count}, after={after_count})"
    )
