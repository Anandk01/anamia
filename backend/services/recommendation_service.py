"""
recommendation_service.py — Diet recommendations and personalised health tips.

Provides:
  get_diet_recommendations(anemia_type, vegan=False)
      Returns a list of food item dicts for the given anemia type.
      Each item: {"name": str, "rationale": str, "is_vegan": bool}
      When vegan=True, non-vegan items are filtered out.

  get_health_tips(severity_level, anemia_type, age=None, sex=None)
      Returns a list of personalised health tip strings based on severity,
      anemia type, and optional demographic attributes.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Diet recommendation lookup table
# ---------------------------------------------------------------------------
# Each entry: {"name": str, "rationale": str, "is_vegan": bool}

_DIET_TABLE: dict[str, list[dict]] = {
    "Iron-Deficiency": [
        {
            "name": "Spinach",
            "rationale": "Rich in non-haem iron; pair with vitamin C to boost absorption.",
            "is_vegan": True,
        },
        {
            "name": "Lentils",
            "rationale": "Excellent plant-based iron source; also provides folate and protein.",
            "is_vegan": True,
        },
        {
            "name": "Red Meat (lean beef/lamb)",
            "rationale": "Highest bioavailable haem iron; directly absorbed without conversion.",
            "is_vegan": False,
        },
        {
            "name": "Tofu (firm)",
            "rationale": "Good non-haem iron source for plant-based diets; versatile in cooking.",
            "is_vegan": True,
        },
        {
            "name": "Pumpkin Seeds",
            "rationale": "Concentrated iron and zinc; easy to add to meals or snacks.",
            "is_vegan": True,
        },
        {
            "name": "Fortified Breakfast Cereals",
            "rationale": "Many cereals provide 100% daily iron per serving; check the label.",
            "is_vegan": True,
        },
    ],
    "Vitamin B12 Deficiency": [
        {
            "name": "Eggs",
            "rationale": "Good source of B12, especially in the yolk; easy to prepare daily.",
            "is_vegan": False,
        },
        {
            "name": "Dairy (milk / yogurt)",
            "rationale": "Readily absorbed B12; yogurt also supports gut health.",
            "is_vegan": False,
        },
        {
            "name": "Salmon",
            "rationale": "Exceptionally high in B12 and omega-3 fatty acids.",
            "is_vegan": False,
        },
        {
            "name": "Fortified Cereals",
            "rationale": "Reliable B12 source for vegetarians; check label for cyanocobalamin.",
            "is_vegan": True,
        },
        {
            "name": "Beef (lean cuts)",
            "rationale": "One of the richest natural B12 sources; also provides haem iron.",
            "is_vegan": False,
        },
        {
            "name": "Nutritional Yeast",
            "rationale": "Fortified nutritional yeast is the primary vegan B12 source.",
            "is_vegan": True,
        },
    ],
    "Folate Deficiency": [
        {
            "name": "Broccoli",
            "rationale": "High in folate and vitamin C; lightly steam to preserve nutrients.",
            "is_vegan": True,
        },
        {
            "name": "Asparagus",
            "rationale": "One of the best vegetable sources of folate per serving.",
            "is_vegan": True,
        },
        {
            "name": "Avocado",
            "rationale": "Rich in folate and healthy monounsaturated fats.",
            "is_vegan": True,
        },
        {
            "name": "Chickpeas",
            "rationale": "Excellent folate and protein source; great in salads and curries.",
            "is_vegan": True,
        },
        {
            "name": "Oranges",
            "rationale": "Good folate content plus vitamin C, which aids iron absorption.",
            "is_vegan": True,
        },
        {
            "name": "Spinach",
            "rationale": "High in folate; also provides iron and other micronutrients.",
            "is_vegan": True,
        },
        {
            "name": "Lentils",
            "rationale": "Among the highest folate content of any food; also rich in iron.",
            "is_vegan": True,
        },
    ],
    "Other": [
        {
            "name": "Lean Chicken",
            "rationale": "Provides haem iron and high-quality protein for general maintenance.",
            "is_vegan": False,
        },
        {
            "name": "Kidney Beans",
            "rationale": "Good plant-based iron and folate; supports overall blood health.",
            "is_vegan": True,
        },
        {
            "name": "Quinoa",
            "rationale": "Complete protein with moderate iron; gluten-free whole grain.",
            "is_vegan": True,
        },
        {
            "name": "Dark Chocolate (≥70% cocoa)",
            "rationale": "Surprisingly good iron source; enjoy in moderation.",
            "is_vegan": True,
        },
        {
            "name": "Sardines",
            "rationale": "Rich in haem iron, B12, and omega-3; convenient canned option.",
            "is_vegan": False,
        },
        {
            "name": "Sunflower Seeds",
            "rationale": "Good non-haem iron and vitamin E; easy to add to salads.",
            "is_vegan": True,
        },
    ],
    "N/A": [
        {
            "name": "Lean Chicken",
            "rationale": "Provides haem iron and high-quality protein for general maintenance.",
            "is_vegan": False,
        },
        {
            "name": "Kidney Beans",
            "rationale": "Good plant-based iron and folate; supports overall blood health.",
            "is_vegan": True,
        },
        {
            "name": "Quinoa",
            "rationale": "Complete protein with moderate iron; gluten-free whole grain.",
            "is_vegan": True,
        },
        {
            "name": "Dark Chocolate (≥70% cocoa)",
            "rationale": "Surprisingly good iron source; enjoy in moderation.",
            "is_vegan": True,
        },
        {
            "name": "Sardines",
            "rationale": "Rich in haem iron, B12, and omega-3; convenient canned option.",
            "is_vegan": False,
        },
        {
            "name": "Sunflower Seeds",
            "rationale": "Good non-haem iron and vitamin E; easy to add to salads.",
            "is_vegan": True,
        },
    ],
}

# Fallback for unknown types — use the "Other" list
_FALLBACK_TYPE = "Other"


def get_diet_recommendations(anemia_type: str, vegan: bool = False) -> list[dict]:
    """Return diet recommendations for the given anemia type.

    Parameters
    ----------
    anemia_type:
        One of "Iron-Deficiency", "Vitamin B12 Deficiency", "Folate Deficiency",
        "Other", or "N/A".  Unknown values fall back to the "Other" list.
    vegan:
        When True, only items where ``is_vegan=True`` are returned.

    Returns
    -------
    list[dict]
        Each dict has keys: ``name`` (str), ``rationale`` (str), ``is_vegan`` (bool).
        At least 5 items are returned for non-vegan requests; vegan requests may
        return fewer items if the type has limited vegan options.
    """
    items = _DIET_TABLE.get(anemia_type, _DIET_TABLE[_FALLBACK_TYPE])

    if vegan:
        items = [item for item in items if item["is_vegan"]]

    return list(items)


# ---------------------------------------------------------------------------
# Health tips lookup table
# ---------------------------------------------------------------------------
# Keyed by (severity_level, anemia_type) → list of tip strings.
# "default" key used as fallback for unknown combinations.

_HEALTH_TIPS: dict[tuple[str, str], list[str]] = {
    # ── None severity ────────────────────────────────────────────────────────
    ("None", "N/A"): [
        "Maintain a balanced diet rich in iron, B12, and folate to keep your blood counts healthy.",
        "Stay well-hydrated and exercise regularly to support optimal circulation.",
        "Schedule annual blood tests to monitor your CBC values over time.",
        "Limit tea and coffee with meals as tannins can inhibit iron absorption.",
    ],
    ("None", "Iron-Deficiency"): [
        "Your iron levels appear adequate — continue eating iron-rich foods to maintain them.",
        "Pair iron-rich foods with vitamin C sources (citrus, bell peppers) to maximise absorption.",
        "Avoid consuming calcium-rich foods at the same time as iron-rich meals.",
        "Regular light exercise supports healthy red blood cell production.",
    ],
    ("None", "Vitamin B12 Deficiency"): [
        "Your B12 levels appear adequate — continue consuming B12-rich foods regularly.",
        "If you follow a plant-based diet, consider a B12 supplement to prevent future deficiency.",
        "Avoid excessive alcohol, which can impair B12 absorption.",
        "Get your B12 levels checked annually, especially if you are over 50.",
    ],
    ("None", "Folate Deficiency"): [
        "Your folate levels appear adequate — maintain a diet rich in leafy greens and legumes.",
        "Avoid overcooking vegetables, as heat destroys folate.",
        "If planning a pregnancy, ensure adequate folate intake to prevent neural tube defects.",
        "Limit alcohol consumption, which depletes folate stores.",
    ],
    ("None", "Other"): [
        "Your blood counts appear normal — maintain a varied, nutrient-rich diet.",
        "Stay active and get regular check-ups to monitor your overall health.",
        "Ensure adequate hydration to support blood volume and circulation.",
        "Manage stress levels, as chronic stress can affect nutrient absorption.",
    ],
    # ── Mild severity ────────────────────────────────────────────────────────
    ("Mild", "Iron-Deficiency"): [
        "Increase your intake of haem iron (red meat, poultry, fish) or non-haem iron (legumes, spinach).",
        "Take iron supplements only if recommended by your doctor — self-supplementing can cause toxicity.",
        "Avoid drinking tea or coffee within one hour of iron-rich meals.",
        "Cook in cast-iron cookware to add small amounts of dietary iron to food.",
        "Eat vitamin C-rich foods alongside iron sources to enhance absorption.",
    ],
    ("Mild", "Vitamin B12 Deficiency"): [
        "Increase consumption of B12-rich foods: eggs, dairy, fish, and fortified cereals.",
        "If you are vegetarian or vegan, a B12 supplement is strongly recommended.",
        "Discuss B12 injections with your doctor if oral supplementation is insufficient.",
        "Avoid excessive alcohol, which interferes with B12 absorption.",
        "Have your B12 levels re-tested in 3 months to monitor improvement.",
    ],
    ("Mild", "Folate Deficiency"): [
        "Eat more folate-rich foods: leafy greens, legumes, citrus fruits, and fortified grains.",
        "Consider a folic acid supplement (400–800 mcg/day) after consulting your doctor.",
        "Avoid overcooking vegetables — steam or eat raw where possible.",
        "Limit alcohol intake, as it significantly reduces folate absorption.",
        "If pregnant or planning pregnancy, folate supplementation is critical.",
    ],
    ("Mild", "Other"): [
        "Consult your doctor to identify the underlying cause of mild anemia.",
        "Eat a varied diet covering all major nutrient groups to support blood health.",
        "Ensure adequate protein intake to support haemoglobin synthesis.",
        "Avoid strenuous exercise until your haemoglobin levels improve.",
        "Monitor for symptoms such as fatigue, pallor, or shortness of breath.",
    ],
    # ── Moderate severity ────────────────────────────────────────────────────
    ("Moderate", "Iron-Deficiency"): [
        "Seek medical evaluation promptly — moderate iron-deficiency anemia requires treatment.",
        "Your doctor may prescribe oral iron supplements (ferrous sulfate or ferrous gluconate).",
        "Take iron supplements on an empty stomach for better absorption, unless they cause nausea.",
        "Avoid antacids, calcium supplements, and dairy within 2 hours of iron supplementation.",
        "Report any worsening symptoms (severe fatigue, chest pain, dizziness) to your doctor immediately.",
        "Follow up with a blood test in 4–6 weeks to assess treatment response.",
    ],
    ("Moderate", "Vitamin B12 Deficiency"): [
        "Moderate B12 deficiency requires prompt medical attention — see your doctor soon.",
        "B12 injections (hydroxocobalamin or cyanocobalamin) may be prescribed for faster correction.",
        "Neurological symptoms (tingling, numbness) can occur — report these to your doctor.",
        "Avoid alcohol completely until B12 levels normalise.",
        "Eat B12-rich foods daily in addition to any prescribed supplementation.",
        "Re-test B12 levels after 8 weeks of treatment.",
    ],
    ("Moderate", "Folate Deficiency"): [
        "Moderate folate deficiency requires medical evaluation and likely supplementation.",
        "Your doctor may prescribe folic acid 5 mg/day for several months.",
        "Ensure adequate B12 levels before starting high-dose folate — masking B12 deficiency is dangerous.",
        "Eat folate-rich foods daily: dark leafy greens, lentils, chickpeas, and fortified cereals.",
        "Avoid alcohol entirely during treatment.",
        "Re-test folate levels after 4 weeks of supplementation.",
    ],
    ("Moderate", "Other"): [
        "Moderate anemia of unclear type requires thorough medical investigation.",
        "Your doctor may order additional tests (ferritin, B12, folate, reticulocyte count).",
        "Avoid self-medicating — incorrect supplementation can worsen some types of anemia.",
        "Rest adequately and avoid strenuous physical activity until levels improve.",
        "Ensure your diet covers all key nutrients: iron, B12, folate, and protein.",
        "Follow up with your doctor within 2 weeks.",
    ],
    # ── Severe severity ──────────────────────────────────────────────────────
    ("Severe", "Iron-Deficiency"): [
        "URGENT: Severe iron-deficiency anemia requires immediate medical attention.",
        "Intravenous iron infusion or blood transfusion may be necessary — do not delay.",
        "Identify and treat the underlying cause of blood loss (e.g., GI bleeding, heavy menstruation).",
        "Do not attempt to self-treat with over-the-counter supplements at this severity.",
        "Restrict physical activity until haemoglobin levels are stabilised by your medical team.",
        "Follow all medical instructions strictly and attend all follow-up appointments.",
    ],
    ("Severe", "Vitamin B12 Deficiency"): [
        "URGENT: Severe B12 deficiency can cause irreversible neurological damage — seek care immediately.",
        "Intramuscular B12 injections are typically required at this severity.",
        "Report any neurological symptoms (confusion, memory loss, balance problems) immediately.",
        "Avoid alcohol completely.",
        "Dietary changes alone are insufficient at this severity — medical treatment is essential.",
        "Attend all follow-up appointments and re-test levels as directed by your doctor.",
    ],
    ("Severe", "Folate Deficiency"): [
        "URGENT: Severe folate deficiency requires immediate medical treatment.",
        "High-dose folic acid supplementation under medical supervision is necessary.",
        "Ensure B12 deficiency is ruled out before starting high-dose folate therapy.",
        "Avoid alcohol completely.",
        "Dietary changes alone are insufficient — follow your doctor's treatment plan.",
        "Monitor for signs of megaloblastic anemia: extreme fatigue, pallor, and shortness of breath.",
    ],
    ("Severe", "Other"): [
        "URGENT: Severe anemia requires immediate medical evaluation and treatment.",
        "Blood transfusion may be required — go to an emergency department if you feel faint or have chest pain.",
        "Do not attempt to self-treat at this severity level.",
        "Restrict all physical activity until cleared by your medical team.",
        "Identify and treat the underlying cause with your doctor's guidance.",
        "Attend all follow-up appointments without delay.",
    ],
}

# Paediatric tip (added when age < 18)
_PAEDIATRIC_TIP = (
    "Children and adolescents have higher iron requirements due to rapid growth — "
    "ensure age-appropriate dietary intake and consult a paediatrician for guidance."
)

# Menstrual iron-loss tip (added when sex == 1, i.e. female)
_MENSTRUAL_TIP = (
    "Menstrual blood loss increases iron requirements — consider tracking your cycle "
    "and discussing iron supplementation with your doctor if periods are heavy."
)

# Default fallback tips for unknown (severity, type) combinations
_DEFAULT_TIPS = [
    "Maintain a balanced diet rich in iron, B12, folate, and protein.",
    "Stay hydrated and exercise moderately to support healthy blood production.",
    "Consult your doctor for personalised advice based on your full blood panel.",
]


def get_health_tips(
    severity_level: str,
    anemia_type: str,
    age: int | None = None,
    sex: int | None = None,
) -> list[str]:
    """Return personalised health tips for the given severity and anemia type.

    Parameters
    ----------
    severity_level:
        One of "None", "Mild", "Moderate", "Severe".
    anemia_type:
        One of "Iron-Deficiency", "Vitamin B12 Deficiency", "Folate Deficiency",
        "Other", or "N/A".
    age:
        Patient age in years.  If provided and < 18, a paediatric tip is appended.
    sex:
        Patient sex encoded as an integer.  1 = female.  If provided and == 1,
        a menstrual iron-loss tip is appended.

    Returns
    -------
    list[str]
        At least 3 tip strings.  Additional demographic tips may be appended.
    """
    key = (severity_level, anemia_type)
    tips = list(_HEALTH_TIPS.get(key, _DEFAULT_TIPS))

    # Demographic additions
    if age is not None and age < 18:
        tips.append(_PAEDIATRIC_TIP)

    if sex is not None and sex == 1:
        tips.append(_MENSTRUAL_TIP)

    return tips
