"""
gemini_chatbot_service.py — Gemini-powered RAG chatbot for anemia Q&A.

Uses Google Gemini (gemini-3-flash-preview) with a static RAG knowledge base
sourced from WHO and NHLBI anemia fact sheets.

Knowledge sources:
  - WHO Anaemia Fact Sheet: https://www.who.int/news-room/fact-sheets/detail/anaemia
  - NHLBI Iron-Deficiency Anemia: https://www.nhlbi.nih.gov/health/anemia/iron-deficiency-anemia
  - NHLBI Anemia Treatment: https://www.nhlbi.nih.gov/health/anemia/treatment
"""

import logging
import os
from collections import deque
from typing import Dict

from google import genai

from services.rag_knowledge import format_context, get_relevant_chunks

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client (reads GEMINI_API_KEY from environment automatically)
# ---------------------------------------------------------------------------

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are AnemiaBot, an AI health assistant specialising in anaemia (anemia).
You answer questions based ONLY on the provided medical knowledge from WHO and NHLBI sources.

STRICT RULES:
1. Only answer questions about anaemia, its symptoms, causes, types, diet, treatment, and CBC values.
2. Always cite your source (WHO or NHLBI) when giving information.
3. NEVER provide a specific medical diagnosis for the user.
4. NEVER prescribe specific medications or dosages.
5. For any question about personal diagnosis or prescription, say: "Please consult a qualified doctor for personalised medical advice."
6. If a question is outside your knowledge domain, say: "I can only answer questions about anaemia. Please consult a doctor for other health concerns."
7. Keep responses concise, clear, and helpful — 2–4 sentences for simple questions, up to 6 for complex ones.
8. Use plain language, not medical jargon.
9. When recommending diet, only recommend foods mentioned in the WHO/NHLBI sources.

KNOWLEDGE BASE:
{context}

CONVERSATION HISTORY:
{history}

USER QUESTION: {question}

Respond as AnemiaBot:"""

# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

_sessions: Dict[str, deque] = {}


class ChatSession:
    """Stores the last 5 (user, bot) message pairs for context."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history: deque = deque(maxlen=5)

    def add(self, user_msg: str, bot_msg: str):
        self.history.append({"user": user_msg, "bot": bot_msg})

    def format_history(self) -> str:
        if not self.history:
            return "No previous messages."
        lines = []
        for turn in self.history:
            lines.append(f"User: {turn['user']}")
            lines.append(f"AnemiaBot: {turn['bot']}")
        return "\n".join(lines)


def _get_or_create_session(session_id: str) -> ChatSession:
    if session_id not in _sessions:
        _sessions[session_id] = ChatSession(session_id)
    return _sessions[session_id]


# ---------------------------------------------------------------------------
# Main chat function
# ---------------------------------------------------------------------------

def chat_with_gemini(message: str, session_id: str) -> dict:
    """
    Process a user message using Gemini RAG and return a response.
    """
    try:
        client = _get_client()
    except RuntimeError as e:
        logger.error("Gemini not configured: %s", e)
        return {
            "response": "AI chatbot is not configured. Please contact the administrator.",
            "intent": "error",
            "sources": [],
        }

    # --- Retrieve relevant knowledge chunks ---
    relevant_chunks = get_relevant_chunks(message, max_chunks=4)
    context = format_context(relevant_chunks)

    if not context:
        from services.rag_knowledge import KNOWLEDGE_BASE
        context = format_context(KNOWLEDGE_BASE[:3])

    # --- Get session history ---
    session = _get_or_create_session(session_id)
    history_text = session.format_history()

    # --- Build prompt ---
    # Using .replace instead of .format to avoid issues with curly braces in context/history
    prompt = SYSTEM_PROMPT.replace("{context}", context)
    prompt = prompt.replace("{history}", history_text)
    prompt = prompt.replace("{question}", message)

    # --- Call Gemini using new SDK ---
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        bot_response = response.text.strip()
    except Exception as exc:
        # Retry with fallback model
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=prompt,
            )
            bot_response = response.text.strip()
        except Exception as exc2:
            logger.error("Gemini API call failed: %s / %s", exc, exc2)
            return {
                "response": "I'm having trouble connecting to the AI service. Please try again in a moment.",
                "intent": "error",
            "sources": [],
        }

    intent = _detect_intent(message)
    session.add(message, bot_response)
    sources = list({chunk["url"] for chunk in relevant_chunks})

    return {
        "response": bot_response,
        "intent": intent,
        "sources": sources,
    }


def _detect_intent(message: str) -> str:
    """Simple keyword-based intent detection for logging."""
    msg = message.lower()
    if any(w in msg for w in ["what is", "define", "meaning", "anaemia", "anemia"]):
        return "anemia_definition"
    if any(w in msg for w in ["symptom", "sign", "feel", "tired", "fatigue", "dizzy"]):
        return "symptoms"
    if any(w in msg for w in ["cause", "why", "reason", "how do i get"]):
        return "causes"
    if any(w in msg for w in ["diet", "food", "eat", "nutrition", "iron-rich", "vitamin"]):
        return "dietary_advice"
    if any(w in msg for w in ["treat", "cure", "medicine", "supplement", "pill"]):
        return "treatment"
    if any(w in msg for w in ["doctor", "hospital", "when should", "see a"]):
        return "when_to_see_doctor"
    if any(w in msg for w in ["cbc", "hgb", "haemoglobin", "hemoglobin", "rbc", "mcv"]):
        return "cbc_interpretation"
    if any(w in msg for w in ["iron deficiency", "b12", "folate", "type"]):
        return "types"
    return "general"
