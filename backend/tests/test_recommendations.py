"""
test_recommendations.py — Property-based and unit tests for the Recommendation Engine.

**Validates: Requirements 5, 7**

Properties tested:
  Property 5 — For any anemia_type input, get_diet_recommendations() returns ≥5 food items
               (non-vegan call).
  Property 6 — vegan=True result is a strict subset of vegan=False result; no non-vegan
               items appear in the vegan result.
"""

import os
import sys

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

# Ensure backend/ is importable when pytest is run from the workspace root.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from services.recommendation_service import get_diet_recommendations, get_health_tips

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_ANEMIA_TYPES = [
    "Iron-Deficiency",
    "Vitamin B12 Deficiency",
    "Folate Deficiency",
    "Other",
    "N/A",
]

_anemia_type_st = st.sampled_from(_ANEMIA_TYPES)

_SEVERITY_LEVELS = ["None", "Mild", "Moderate", "Severe"]

# ---------------------------------------------------------------------------
# Property 5 — ≥5 food items for any anemia_type (non-vegan call)
# **Validates: Requirements 5.2**
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("anemia_type", _ANEMIA_TYPES)
def test_property_5_at_least_5_items_parametrize(anemia_type: str) -> None:
    """
    Property 5 (parametrize): get_diet_recommendations(anemia_type) MUST return
    at least 5 food items for every supported anemia type.

    **Validates: Requirements 5.2**
    """
    items = get_diet_recommendations(anemia_type)
    assert len(items) >= 5, (
        f"Expected ≥5 items for anemia_type={anemia_type!r}, got {len(items)}"
    )


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(anemia_type=_anemia_type_st)
def test_property_5_at_least_5_items_hypothesis(anemia_type: str) -> None:
    """
    Property 5 (hypothesis): For any anemia_type drawn from the supported set,
    get_diet_recommendations() MUST return at least 5 food items.

    **Validates: Requirements 5.2**
    """
    items = get_diet_recommendations(anemia_type)
    assert len(items) >= 5, (
        f"Expected ≥5 items for anemia_type={anemia_type!r}, got {len(items)}"
    )


# ---------------------------------------------------------------------------
# Property 6 — vegan=True result is strict subset of vegan=False result;
#              no non-vegan items in vegan result
# **Validates: Requirements 5.5**
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("anemia_type", _ANEMIA_TYPES)
def test_property_6_vegan_subset_parametrize(anemia_type: str) -> None:
    """
    Property 6 (parametrize): The vegan=True result MUST be a subset of the
    vegan=False result, and MUST NOT contain any item where is_vegan=False.

    **Validates: Requirements 5.5**
    """
    all_items = get_diet_recommendations(anemia_type, vegan=False)
    vegan_items = get_diet_recommendations(anemia_type, vegan=True)

    # Build sets of item names for subset check
    all_names = {item["name"] for item in all_items}
    vegan_names = {item["name"] for item in vegan_items}

    # vegan result must be a subset of the full result
    assert vegan_names <= all_names, (
        f"vegan=True names {vegan_names - all_names!r} not found in vegan=False result "
        f"for anemia_type={anemia_type!r}"
    )

    # No non-vegan items in the vegan result
    non_vegan_in_vegan = [item for item in vegan_items if not item["is_vegan"]]
    assert non_vegan_in_vegan == [], (
        f"Non-vegan items found in vegan=True result for anemia_type={anemia_type!r}: "
        f"{[i['name'] for i in non_vegan_in_vegan]}"
    )


@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(anemia_type=_anemia_type_st)
def test_property_6_vegan_subset_hypothesis(anemia_type: str) -> None:
    """
    Property 6 (hypothesis): For any anemia_type, the vegan=True result MUST be
    a subset of the vegan=False result, and MUST NOT contain any non-vegan item.

    **Validates: Requirements 5.5**
    """
    all_items = get_diet_recommendations(anemia_type, vegan=False)
    vegan_items = get_diet_recommendations(anemia_type, vegan=True)

    all_names = {item["name"] for item in all_items}
    vegan_names = {item["name"] for item in vegan_items}

    # Subset check
    assert vegan_names <= all_names, (
        f"vegan=True names {vegan_names - all_names!r} not in vegan=False result "
        f"for anemia_type={anemia_type!r}"
    )

    # No non-vegan items in vegan result
    non_vegan_in_vegan = [item for item in vegan_items if not item["is_vegan"]]
    assert non_vegan_in_vegan == [], (
        f"Non-vegan items in vegan=True result for anemia_type={anemia_type!r}: "
        f"{[i['name'] for i in non_vegan_in_vegan]}"
    )


# ---------------------------------------------------------------------------
# Unit tests — item structure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("anemia_type", _ANEMIA_TYPES)
def test_diet_items_have_required_keys(anemia_type: str) -> None:
    """Each food item dict must have 'name', 'rationale', and 'is_vegan' keys."""
    items = get_diet_recommendations(anemia_type)
    for item in items:
        assert "name" in item, f"Missing 'name' key in item: {item}"
        assert "rationale" in item, f"Missing 'rationale' key in item: {item}"
        assert "is_vegan" in item, f"Missing 'is_vegan' key in item: {item}"
        assert isinstance(item["name"], str) and item["name"], "name must be a non-empty str"
        assert isinstance(item["rationale"], str) and item["rationale"], "rationale must be a non-empty str"
        assert isinstance(item["is_vegan"], bool), "is_vegan must be a bool"


# ---------------------------------------------------------------------------
# Unit tests — health tips
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("severity", _SEVERITY_LEVELS)
@pytest.mark.parametrize("anemia_type", _ANEMIA_TYPES)
def test_health_tips_at_least_3(severity: str, anemia_type: str) -> None:
    """get_health_tips() MUST return at least 3 tips for every (severity, type) combo."""
    tips = get_health_tips(severity, anemia_type)
    assert len(tips) >= 3, (
        f"Expected ≥3 tips for ({severity!r}, {anemia_type!r}), got {len(tips)}"
    )
    for tip in tips:
        assert isinstance(tip, str) and tip, "Each tip must be a non-empty string"


def test_health_tips_paediatric_tip_added_for_child() -> None:
    """When age < 18, a paediatric tip must be appended."""
    tips_adult = get_health_tips("Mild", "Iron-Deficiency", age=30)
    tips_child = get_health_tips("Mild", "Iron-Deficiency", age=10)
    assert len(tips_child) == len(tips_adult) + 1, (
        "Expected one extra tip for paediatric patient"
    )
    assert any("paediatric" in t.lower() or "children" in t.lower() or "adolescent" in t.lower()
               for t in tips_child), "Paediatric tip not found"


def test_health_tips_menstrual_tip_added_for_female() -> None:
    """When sex == 1 (female), a menstrual iron-loss tip must be appended."""
    tips_male = get_health_tips("Mild", "Iron-Deficiency", sex=0)
    tips_female = get_health_tips("Mild", "Iron-Deficiency", sex=1)
    assert len(tips_female) == len(tips_male) + 1, (
        "Expected one extra tip for female patient"
    )
    assert any("menstrual" in t.lower() or "period" in t.lower() or "cycle" in t.lower()
               for t in tips_female), "Menstrual tip not found"


def test_health_tips_both_demographic_tips() -> None:
    """When age < 18 AND sex == 1, both demographic tips must be appended."""
    base_tips = get_health_tips("Mild", "Iron-Deficiency")
    demo_tips = get_health_tips("Mild", "Iron-Deficiency", age=15, sex=1)
    assert len(demo_tips) == len(base_tips) + 2, (
        "Expected two extra tips for young female patient"
    )


def test_health_tips_no_extra_for_adult_male() -> None:
    """When age >= 18 and sex != 1, no demographic tips are added."""
    base_tips = get_health_tips("Mild", "Iron-Deficiency")
    adult_male_tips = get_health_tips("Mild", "Iron-Deficiency", age=35, sex=0)
    assert len(adult_male_tips) == len(base_tips), (
        "No extra tips expected for adult male"
    )


def test_unknown_anemia_type_falls_back_gracefully() -> None:
    """Unknown anemia_type should fall back to the 'Other' list without raising."""
    items = get_diet_recommendations("Unknown Type")
    assert len(items) >= 5, "Fallback should still return ≥5 items"


def test_unknown_severity_type_combo_returns_default_tips() -> None:
    """Unknown (severity, type) combo should return the default fallback tips."""
    tips = get_health_tips("Unknown", "Unknown")
    assert len(tips) >= 3, "Default fallback should return ≥3 tips"
