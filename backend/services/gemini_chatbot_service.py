"""
gemini_chatbot_service.py — AI-powered RAG chatbot for anemia Q&A.

Uses Groq API (OpenAI-compatible) with a static RAG knowledge base
sourced from WHO and NHLBI anemia fact sheets.
"""

import logging
import os
from collections import deque
from typing import Dict

from services.rag_knowledge import format_context, get_relevant_chunks

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Groq client via OpenAI SDK
# ---------------------------------------------------------------------------

_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in environment")
        _client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
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
{history}"""

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


def _detect_intent(message: str) -> str:
    """Simple keyword-based intent detection."""
    msg = message.lower()
    if any(w in msg for w in ['symptom', 'sign', 'feel']):
        return 'symptoms'
    if any(w in msg for w in ['diet', 'food', 'eat', 'nutrition']):
        return 'dietary_advice'
    if any(w in msg for w in ['type', 'iron', 'b12', 'folate']):
        return 'types'
    if any(w in msg for w in ['treat', 'cure', 'medicine']):
        return 'treatment'
    if any(w in msg for w in ['cbc', 'blood test', 'hemoglobin', 'hgb']):
        return 'cbc_interpretation'
    if any(w in msg for w in ['what is', 'define', 'meaning']):
        return 'anemia_definition'
    return 'general'


# ---------------------------------------------------------------------------
# Main chat function
# ---------------------------------------------------------------------------

def chat_with_gemini(message: str, session_id: str) -> dict:
    """
    Process a user message using Groq AI and return a response.
    """
    try:
        client = _get_client()
    except RuntimeError as e:
        logger.error("AI not configured: %s", e)
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

    # --- Build system prompt ---
    system_prompt = SYSTEM_PROMPT.replace("{context}", context)
    system_prompt = system_prompt.replace("{history}", history_text)

    # --- Call Groq via OpenAI SDK ---
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        bot_response = response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("Groq API call failed: %s", exc)
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
