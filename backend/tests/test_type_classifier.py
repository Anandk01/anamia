"""
Unit tests for backend/services/type_classifier.py

Covers:
  - All four classification branches (Iron-Deficiency, Folate, B12, Other)
  - Boundary / edge cases (MCV exactly at 80 and 100)
  - Confidence range invariant (always in [0.0, 1.0])
  - Partial microcytic criteria (MCV < 80 but MCH ≥ 27 → Other)
"""

import pytest
from services.type_classifier import classify_anemia_type


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _result(mcv, mch=28.0, mchc=33.0, rdw=13.0):
    """Convenience wrapper with sensible defaults."""
    return classify_anemia_type(mcv=mcv, mch=mch, mchc=mchc, rdw=rdw)


# ---------------------------------------------------------------------------
# Iron-Deficiency (MCV < 80 AND MCH < 27)
# ---------------------------------------------------------------------------

class TestIronDeficiency:
    def test_classic_iron_deficiency(self):
        result = classify_anemia_type(mcv=65.0, mch=20.0, mchc=30.0, rdw=16.0)
        assert result["anemia_type"] == "Iron-Deficiency"

    def test_confidence_in_range(self):
        result = classify_anemia_type(mcv=65.0, mch=20.0, mchc=30.0, rdw=16.0)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_high_confidence_far_from_boundary(self):
        # Very low MCV and MCH → high confidence
        result = classify_anemia_type(mcv=55.0, mch=15.0, mchc=28.0, rdw=18.0)
        assert result["anemia_type"] == "Iron-Deficiency"
        assert result["confidence"] > 0.7

    def test_low_confidence_near_boundary(self):
        # Just below both thresholds → lower confidence than far case
        result_near = classify_anemia_type(mcv=79.0, mch=26.5, mchc=31.0, rdw=14.0)
        result_far = classify_anemia_type(mcv=60.0, mch=18.0, mchc=28.0, rdw=18.0)
        assert result_near["anemia_type"] == "Iron-Deficiency"
        assert result_near["confidence"] < result_far["confidence"]

    def test_partial_criteria_mcv_low_mch_normal(self):
        # MCV < 80 but MCH ≥ 27 → should NOT be Iron-Deficiency
        result = classify_anemia_type(mcv=75.0, mch=28.0, mchc=33.0, rdw=13.0)
        assert result["anemia_type"] != "Iron-Deficiency"

    def test_partial_criteria_mch_low_mcv_normal(self):
        # MCH < 27 but MCV ≥ 80 → should NOT be Iron-Deficiency
        result = classify_anemia_type(mcv=85.0, mch=24.0, mchc=31.0, rdw=13.0)
        assert result["anemia_type"] != "Iron-Deficiency"


# ---------------------------------------------------------------------------
# Macrocytic — Folate Deficiency (MCV > 100 AND RDW > 14.5)
# ---------------------------------------------------------------------------

class TestFolateDeficiency:
    def test_classic_folate(self):
        result = classify_anemia_type(mcv=110.0, mch=35.0, mchc=34.0, rdw=16.0)
        assert result["anemia_type"] == "Folate Deficiency"

    def test_confidence_in_range(self):
        result = classify_anemia_type(mcv=110.0, mch=35.0, mchc=34.0, rdw=16.0)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_high_confidence_far_from_boundaries(self):
        result = classify_anemia_type(mcv=120.0, mch=38.0, mchc=35.0, rdw=19.0)
        assert result["anemia_type"] == "Folate Deficiency"
        assert result["confidence"] > 0.7

    def test_rdw_just_above_threshold(self):
        result = classify_anemia_type(mcv=105.0, mch=34.0, mchc=33.0, rdw=14.6)
        assert result["anemia_type"] == "Folate Deficiency"


# ---------------------------------------------------------------------------
# Macrocytic — Vitamin B12 Deficiency (MCV > 100 AND RDW ≤ 14.5)
# ---------------------------------------------------------------------------

class TestB12Deficiency:
    def test_classic_b12(self):
        result = classify_anemia_type(mcv=108.0, mch=36.0, mchc=34.0, rdw=13.0)
        assert result["anemia_type"] == "Vitamin B12 Deficiency"

    def test_confidence_in_range(self):
        result = classify_anemia_type(mcv=108.0, mch=36.0, mchc=34.0, rdw=13.0)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_rdw_exactly_at_threshold(self):
        # RDW == 14.5 → ≤ threshold → B12
        result = classify_anemia_type(mcv=105.0, mch=34.0, mchc=33.0, rdw=14.5)
        assert result["anemia_type"] == "Vitamin B12 Deficiency"

    def test_rdw_just_below_threshold(self):
        result = classify_anemia_type(mcv=105.0, mch=34.0, mchc=33.0, rdw=14.4)
        assert result["anemia_type"] == "Vitamin B12 Deficiency"


# ---------------------------------------------------------------------------
# Normocytic — Other (MCV 80–100)
# ---------------------------------------------------------------------------

class TestNormocytic:
    def test_classic_normocytic(self):
        result = classify_anemia_type(mcv=90.0, mch=30.0, mchc=33.0, rdw=13.0)
        assert result["anemia_type"] == "Other"

    def test_confidence_in_range(self):
        result = classify_anemia_type(mcv=90.0, mch=30.0, mchc=33.0, rdw=13.0)
        assert 0.0 <= result["confidence"] <= 1.0

    def test_mcv_exactly_80_is_normocytic(self):
        # MCV == 80 does NOT satisfy MCV < 80, so → Other
        result = classify_anemia_type(mcv=80.0, mch=26.0, mchc=31.0, rdw=13.0)
        assert result["anemia_type"] == "Other"

    def test_mcv_exactly_100_is_normocytic(self):
        # MCV == 100 does NOT satisfy MCV > 100, so → Other
        result = classify_anemia_type(mcv=100.0, mch=33.0, mchc=34.0, rdw=16.0)
        assert result["anemia_type"] == "Other"

    def test_mcv_just_above_80_is_normocytic(self):
        result = classify_anemia_type(mcv=80.1, mch=28.0, mchc=33.0, rdw=13.0)
        assert result["anemia_type"] == "Other"

    def test_mcv_just_below_100_is_normocytic(self):
        result = classify_anemia_type(mcv=99.9, mch=32.0, mchc=34.0, rdw=13.0)
        assert result["anemia_type"] == "Other"

    def test_centred_mcv_higher_confidence_than_boundary(self):
        # MCV at midpoint (90) should have higher confidence than near boundary (81)
        result_centre = classify_anemia_type(mcv=90.0, mch=30.0, mchc=33.0, rdw=13.0)
        result_edge = classify_anemia_type(mcv=81.0, mch=28.0, mchc=33.0, rdw=13.0)
        assert result_centre["confidence"] > result_edge["confidence"]


# ---------------------------------------------------------------------------
# Return structure invariants
# ---------------------------------------------------------------------------

class TestReturnStructure:
    @pytest.mark.parametrize("mcv,mch,mchc,rdw", [
        (65.0, 20.0, 30.0, 16.0),   # Iron-Deficiency
        (110.0, 35.0, 34.0, 16.0),  # Folate
        (108.0, 36.0, 34.0, 13.0),  # B12
        (90.0, 30.0, 33.0, 13.0),   # Other
        (80.0, 26.0, 31.0, 13.0),   # Boundary MCV=80
        (100.0, 33.0, 34.0, 16.0),  # Boundary MCV=100
    ])
    def test_always_returns_required_keys(self, mcv, mch, mchc, rdw):
        result = classify_anemia_type(mcv=mcv, mch=mch, mchc=mchc, rdw=rdw)
        assert "anemia_type" in result
        assert "confidence" in result

    @pytest.mark.parametrize("mcv,mch,mchc,rdw", [
        (65.0, 20.0, 30.0, 16.0),
        (110.0, 35.0, 34.0, 16.0),
        (108.0, 36.0, 34.0, 13.0),
        (90.0, 30.0, 33.0, 13.0),
    ])
    def test_confidence_always_between_0_and_1(self, mcv, mch, mchc, rdw):
        result = classify_anemia_type(mcv=mcv, mch=mch, mchc=mchc, rdw=rdw)
        assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.parametrize("mcv,mch,mchc,rdw", [
        (65.0, 20.0, 30.0, 16.0),
        (110.0, 35.0, 34.0, 16.0),
        (108.0, 36.0, 34.0, 13.0),
        (90.0, 30.0, 33.0, 13.0),
    ])
    def test_anemia_type_is_valid_string(self, mcv, mch, mchc, rdw):
        valid_types = {
            "Iron-Deficiency",
            "Folate Deficiency",
            "Vitamin B12 Deficiency",
            "Other",
        }
        result = classify_anemia_type(mcv=mcv, mch=mch, mchc=mchc, rdw=rdw)
        assert result["anemia_type"] in valid_types
