"""
chatbot_service.py -- Keyword-based intent classifier and response engine for
the anemia chatbot.

Public API
----------
classify_and_respond(message: str, session_id: str) -> dict
    Returns {"response": str, "intent": str}

get_or_create_session(session_id: str) -> ChatSession
    Returns (or creates) the ChatSession for the given session_id.

ChatSession
    Stores the last 5 (user_message, bot_response) pairs in a deque.
"""

import random
from collections import deque

# ---------------------------------------------------------------------------
# Intent keyword map
# ---------------------------------------------------------------------------

# Each entry: (intent_name, [keywords_lowercase])
# Order matters: more specific intents are checked first.
_INTENT_KEYWORDS: list = [
    (
        "diagnosis_prescription",
        [
            "diagnose", "prescribe", "prescription", "medication", "medicine",
            "drug", "treatment", "cure", "dose", "dosage", "tablet", "capsule",
            "injection", "therapy",
        ],
    ),
    (
        "anemia_definition",
        [
            "what is anemia", "define anemia", "anemia meaning",
            "what does anemia mean", "what is anaemia", "define anaemia",
        ],
    ),
    (
        "cbc_interpretation",
        [
            "cbc", "blood test", "hgb", "haemoglobin", "hemoglobin",
            "rbc", "mcv", "mch", "mchc", "rdw", "tlc", "plt", "platelet",
            "interpret", "result", "blood count", "complete blood",
        ],
    ),
    (
        "types",
        [
            "type", "kind", "iron deficiency", "b12", "folate", "vitamin",
            "macrocytic", "microcytic", "normocytic", "iron-deficiency",
            "vitamin b12", "folate deficiency",
        ],
    ),
    (
        "dietary_advice",
        [
            "diet", "food", "eat", "nutrition", "meal", "vegetarian", "vegan",
            "iron rich", "iron-rich", "what to eat", "foods for", "nutrients",
            "supplement", "spinach", "lentil",
        ],
    ),
    (
        "when_to_see_doctor",
        [
            "doctor", "hospital", "emergency", "urgent", "severe",
            "when should", "see a doctor", "visit", "clinic", "consult",
            "medical help", "seek help",
        ],
    ),
    (
        "symptoms",
        [
            "symptom", "sign", "feel", "tired", "fatigue", "dizzy",
            "pale", "breathless", "weakness", "weak", "exhausted",
            "shortness of breath", "headache", "cold hands", "cold feet",
            "irregular heartbeat", "chest pain",
        ],
    ),
]

# ---------------------------------------------------------------------------
# Response templates (>=2 variants per intent)
# ---------------------------------------------------------------------------

_RESPONSES: dict = {
    "anemia_definition": [
        (
            "Anemia is a condition where your blood doesn't have enough healthy red blood cells "
            "or haemoglobin to carry adequate oxygen to your body's tissues. This can leave you "
            "feeling tired and weak. It's one of the most common blood disorders worldwide."
        ),
        (
            "Anemia occurs when the level of haemoglobin (HGB) in your blood falls below normal "
            "thresholds -- typically below 12 g/dL for women and 13 g/dL for men. Red blood cells "
            "carry oxygen, so a shortage can affect energy levels and organ function."
        ),
        (
            "Simply put, anemia means your blood has a reduced capacity to carry oxygen. This "
            "happens when you have too few red blood cells, or when those cells don't contain "
            "enough haemoglobin. Common causes include iron deficiency, vitamin B12 deficiency, "
            "and chronic disease."
        ),
    ],
    "symptoms": [
        (
            "Common symptoms of anemia include: persistent fatigue and weakness, pale or yellowish "
            "skin, dizziness or lightheadedness, shortness of breath during normal activities, "
            "cold hands and feet, headaches, and an irregular or fast heartbeat. Symptoms vary "
            "depending on the severity and underlying cause."
        ),
        (
            "Anemia can cause a range of symptoms: you might feel unusually tired, look pale, "
            "feel dizzy when standing up, or get breathless easily. Some people also experience "
            "chest pain, headaches, or difficulty concentrating. Mild anemia may have no noticeable "
            "symptoms at all."
        ),
        (
            "The most telling signs of anemia are fatigue, weakness, and pallor (pale skin or "
            "pale inner eyelids). You may also notice dizziness, shortness of breath, or a rapid "
            "heartbeat. If you're experiencing several of these symptoms, a CBC blood test can "
            "help confirm whether anemia is the cause."
        ),
    ],
    "types": [
        (
            "There are several types of anemia, each with a different cause:\n"
            "- Iron-Deficiency Anemia: the most common type; caused by insufficient iron, "
            "leading to small, pale red blood cells (microcytic).\n"
            "- Vitamin B12 Deficiency Anemia: causes large red blood cells (macrocytic); "
            "common in vegans and older adults.\n"
            "- Folate Deficiency Anemia: also macrocytic; often linked to poor diet or "
            "malabsorption.\n"
            "- Other/Normocytic Anemia: normal-sized red blood cells but reduced count; "
            "can be caused by chronic disease, kidney problems, or bone marrow issues."
        ),
        (
            "Anemia is classified mainly by the size of red blood cells:\n"
            "- Microcytic (small cells): usually Iron-Deficiency Anemia -- low MCV and MCH.\n"
            "- Macrocytic (large cells): usually B12 or Folate Deficiency -- high MCV.\n"
            "- Normocytic (normal-sized cells): often linked to chronic illness or acute blood loss.\n"
            "Each type requires a different treatment approach, which is why accurate diagnosis "
            "through CBC and additional tests is important."
        ),
    ],
    "dietary_advice": [
        (
            "Diet plays a key role in managing anemia. For iron-deficiency anemia, focus on:\n"
            "- Red meat, poultry, and fish (haem iron -- highly absorbable)\n"
            "- Spinach, lentils, tofu, and pumpkin seeds (non-haem iron)\n"
            "- Pair iron-rich foods with vitamin C (citrus, bell peppers) to boost absorption\n"
            "- Avoid tea/coffee with meals as they inhibit iron absorption\n\n"
            "For B12 deficiency: eggs, dairy, salmon, and fortified cereals.\n"
            "For folate deficiency: broccoli, asparagus, avocado, chickpeas, and oranges."
        ),
        (
            "Good nutrition is essential for treating and preventing anemia:\n"
            "- Iron-rich foods: lean red meat, liver, beans, lentils, dark leafy greens, "
            "fortified cereals\n"
            "- Vitamin B12 sources: eggs, milk, cheese, fish, meat (vegans should consider "
            "B12-fortified foods or supplements)\n"
            "- Folate sources: leafy greens, legumes, avocado, citrus fruits\n"
            "- Vitamin C helps your body absorb non-haem iron -- try a glass of orange juice "
            "with your iron-rich meal.\n\n"
            "Always consult a doctor before starting supplements."
        ),
    ],
    "when_to_see_doctor": [
        (
            "You should see a doctor if you experience:\n"
            "- Severe fatigue that interferes with daily life\n"
            "- Chest pain, rapid heartbeat, or shortness of breath at rest\n"
            "- Fainting or near-fainting episodes\n"
            "- Symptoms that don't improve with dietary changes\n"
            "- A haemoglobin level below 8 g/dL (Moderate-Severe anemia)\n\n"
            "Seek emergency care immediately if you have chest pain, difficulty breathing, "
            "or signs of severe blood loss."
        ),
        (
            "It's important to consult a doctor when:\n"
            "- Your symptoms are worsening or not improving\n"
            "- You have a known chronic condition (kidney disease, cancer, autoimmune disorder)\n"
            "- You are pregnant -- anemia during pregnancy needs prompt management\n"
            "- Your CBC results show HGB below 7 g/dL (Severe anemia)\n"
            "- You experience unexplained weight loss alongside anemia symptoms\n\n"
            "Don't delay -- early treatment prevents complications."
        ),
    ],
    "cbc_interpretation": [
        (
            "A Complete Blood Count (CBC) measures several key values:\n"
            "- HGB (Haemoglobin): main indicator -- normal is ~12-17 g/dL; below 12 suggests anemia\n"
            "- RBC (Red Blood Cell count): normal ~4.0-5.5 million/uL\n"
            "- MCV (Mean Corpuscular Volume): size of red cells -- low (<80 fL) = microcytic, "
            "high (>100 fL) = macrocytic\n"
            "- MCH/MCHC: haemoglobin content per cell -- low values suggest iron deficiency\n"
            "- RDW (Red Cell Distribution Width): variation in cell size -- elevated (>14.5%) "
            "suggests mixed deficiency\n"
            "- TLC (Total Leucocyte Count): white blood cells -- normal 4-11 thousand/uL\n"
            "- PLT (Platelets): normal 150-400 thousand/uL\n\n"
            "This system analyses all 8 CBC values together to predict anemia presence, "
            "severity, and likely type."
        ),
        (
            "Here's a quick guide to reading your CBC results:\n"
            "- HGB below 12 g/dL (women) or 13 g/dL (men) -> anemia likely\n"
            "- Low MCV + Low MCH -> Iron-Deficiency Anemia (microcytic)\n"
            "- High MCV -> B12 or Folate Deficiency (macrocytic)\n"
            "- Normal MCV with low HGB -> Normocytic anemia (chronic disease, etc.)\n"
            "- High RDW -> mixed deficiency or early iron/B12 deficiency\n\n"
            "Remember, CBC values should always be interpreted alongside your symptoms and "
            "medical history by a qualified doctor."
        ),
    ],
    "diagnosis_prescription": [
        (
            "I'm not able to provide medical diagnoses or prescribe medications -- that's "
            "something only a qualified doctor can do safely. Please consult your doctor or "
            "a haematologist who can review your full medical history and test results to "
            "recommend the right treatment for you."
        ),
        (
            "For specific diagnoses and medication recommendations, please speak with a "
            "licensed healthcare professional. Self-medicating for anemia (especially with "
            "iron supplements) can sometimes be harmful without knowing the exact cause. "
            "Your doctor can order the right tests and prescribe the appropriate treatment."
        ),
        (
            "I understand you're looking for treatment guidance, but I'm designed to provide "
            "general information only -- not medical advice. Please visit a doctor or clinic "
            "for a proper diagnosis and personalised prescription. They can run the necessary "
            "tests and create a safe treatment plan for you."
        ),
    ],
    "out_of_scope": [
        (
            "I'm sorry, I'm not sure I can help with that. I'm specialised in answering "
            "questions about anemia -- its definition, symptoms, types, dietary advice, CBC "
            "interpretation, and when to seek medical help. For other health concerns, please "
            "consult a qualified doctor."
        ),
        (
            "That question is outside my area of expertise. I'm here to help with anemia-related "
            "topics such as symptoms, types, diet, and CBC results. For anything beyond that, "
            "I'd recommend speaking with a healthcare professional."
        ),
        (
            "I'm not able to answer that question, but I'm happy to help with anything related "
            "to anemia -- like what it is, its symptoms, types, dietary recommendations, or how "
            "to read your CBC results. Is there something along those lines I can help you with?"
        ),
    ],
}

# ---------------------------------------------------------------------------
# Session management (Task 9.2)
# ---------------------------------------------------------------------------


class ChatSession:
    """Stores the last 5 (user_message, bot_response) exchange pairs."""

    def __init__(self):
        self._history = deque(maxlen=5)
        self.last_intent = None

    def add_exchange(self, user_msg, bot_response):
        """Append a (user_message, bot_response) pair to the history."""
        self._history.append((user_msg, bot_response))

    @property
    def history(self):
        """Return history as a list (oldest first)."""
        return list(self._history)

    def recent_messages(self, n=2):
        """Return the n most recent (user, bot) pairs."""
        h = list(self._history)
        return h[-n:] if len(h) >= n else h


# Module-level session store keyed by session_id
_sessions: dict = {}


def get_or_create_session(session_id: str) -> ChatSession:
    """Return the existing ChatSession for session_id, or create a new one."""
    if session_id not in _sessions:
        _sessions[session_id] = ChatSession()
    return _sessions[session_id]


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

# Intents that benefit from context boosting when they appear in recent history
_CONTEXT_BOOSTABLE = {
    "symptoms", "types", "dietary_advice", "cbc_interpretation",
    "anemia_definition", "when_to_see_doctor",
}

# Follow-up phrases that signal "tell me more about the previous topic"
_FOLLOW_UP_PHRASES = [
    "tell me more", "more about", "elaborate", "explain more", "go on",
    "continue", "what else", "anything else", "more details", "more info",
    "more information", "expand on", "can you explain",
]


import re as _re


def _kw_match(keyword: str, text: str) -> bool:
    """Return True if keyword appears in text without being a substring of an
    unrelated word.

    Strategy:
    - Multi-word keywords: simple substring match (already specific enough).
    - Single-word keywords: require a word boundary at the START of the keyword
      so that e.g. "eat" does not match "weather", but "type" still matches
      "types", "symptom" matches "symptoms", etc.
    """
    if " " in keyword:
        return keyword in text
    # Require word boundary before the keyword; allow trailing word chars
    # so stems like "type" match "types", "symptom" matches "symptoms", etc.
    return bool(_re.search(r"\b" + _re.escape(keyword), text))


def _score_intent(message_lower: str) -> dict:
    """Return a score dict mapping intent name to match count."""
    scores = {intent: 0 for intent, _ in _INTENT_KEYWORDS}
    scores["out_of_scope"] = 0

    for intent, keywords in _INTENT_KEYWORDS:
        for kw in keywords:
            if _kw_match(kw, message_lower):
                scores[intent] += 1

    return scores


def _classify_intent(message: str, session: ChatSession) -> str:
    """Classify the intent of message, using session context for follow-ups."""
    message_lower = message.lower().strip()

    # Score all intents
    scores = _score_intent(message_lower)

    # Context injection: if the message looks like a follow-up and the last
    # intent is boostable, boost that intent's score.
    is_follow_up = any(phrase in message_lower for phrase in _FOLLOW_UP_PHRASES)
    if is_follow_up and session.last_intent in _CONTEXT_BOOSTABLE:
        scores[session.last_intent] = scores.get(session.last_intent, 0) + 3

    # Also check the last 2 messages in history for context clues.
    # For short follow-up messages (<=6 words), give a small boost to the
    # last known intent.
    word_count = len(message_lower.split())
    if word_count <= 6 and session.last_intent in _CONTEXT_BOOSTABLE:
        scores[session.last_intent] = scores.get(session.last_intent, 0) + 1

    # diagnosis_prescription always wins if it has any score (safety guardrail)
    if scores.get("diagnosis_prescription", 0) > 0:
        return "diagnosis_prescription"

    # Pick the highest-scoring intent
    best_intent = max(scores, key=lambda k: scores[k])
    if scores[best_intent] == 0:
        return "out_of_scope"

    return best_intent


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------


def classify_and_respond(message: str, session_id: str) -> dict:
    """Classify message intent and return a response.

    Parameters
    ----------
    message:    The user's chat message.
    session_id: Unique identifier for the chat session.

    Returns
    -------
    dict with keys:
        "response" (str) -- the bot's reply
        "intent"   (str) -- the classified intent name
    """
    session = get_or_create_session(session_id)

    intent = _classify_intent(message, session)

    # Pick a random response variant for variety
    response_variants = _RESPONSES.get(intent, _RESPONSES["out_of_scope"])
    response = random.choice(response_variants)

    # Update session's last intent
    session.last_intent = intent

    return {"response": response, "intent": intent}
