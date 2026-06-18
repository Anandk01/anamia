"""
gemini_chatbot_service.py — Gemini-powered RAG chatbot for anemia Q&A.
Uses google-genai SDK with gemini-2.5-flash model.
"""

import logging
import os
from collections import deque
from typing import Dict

from google import genai

from services.rag_knowledge import format_context, get_relevant_chunks

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=api_key)
    return _client


SYSTEM_PROMPT = """You are AnemiaBot, an AI health assistant specialising in anaemia.
Answer based ONLY on the provided knowledge from WHO and NHLBI sources.
RULES:
1. Only answer about anaemia, symptoms, causes, types, diet, treatment, CBC values.
2. NEVER diagnose or prescribe medications.
3. Keep responses concise (2-4 sentences).
4. If outside domain, say: "I can only answer questions about anaemia."

KNOWLEDGE:
{context}

HISTORY:
{history}"""

_sessions: Dict[str, deque] = {}


class ChatSession:
    def __init__(self, sid):
        self.history = deque(maxlen=5)

    def add(self, user_msg, bot_msg):
        self.history.append({"user": user_msg, "bot": bot_msg})

    def format_history(self):
        if not self.history:
            return "None"
        return "\n".join(f"User: {t['user']}\nBot: {t['bot']}" for t in self.history)


def _get_or_create_session(sid):
    if sid not in _sessions:
        _sessions[sid] = ChatSession(sid)
    return _sessions[sid]


def _detect_intent(msg):
    m = msg.lower()
    if any(w in m for w in ['symptom', 'sign']): return 'symptoms'
    if any(w in m for w in ['diet', 'food', 'eat']): return 'dietary_advice'
    if any(w in m for w in ['type', 'iron', 'b12']): return 'types'
    if any(w in m for w in ['cbc', 'hemoglobin', 'hgb']): return 'cbc_interpretation'
    return 'general'


def chat_with_gemini(message: str, session_id: str) -> dict:
    try:
        client = _get_client()
    except RuntimeError as e:
        return {"response": "AI chatbot not configured.", "intent": "error", "sources": []}

    relevant_chunks = get_relevant_chunks(message, max_chunks=4)
    context = format_context(relevant_chunks)
    if not context:
        from services.rag_knowledge import KNOWLEDGE_BASE
        context = format_context(KNOWLEDGE_BASE[:3])

    session = _get_or_create_session(session_id)
    prompt = SYSTEM_PROMPT.replace("{context}", context).replace("{history}", session.format_history())
    full_prompt = prompt + f"\n\nUser: {message}\nAnemiaBot:"

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
        )
        bot_response = response.text.strip()
    except Exception as exc:
        logger.error("Gemini failed: %s", exc)
        return {"response": "AI service temporarily unavailable. Please try again.", "intent": "error", "sources": []}

    session.add(message, bot_response)
    sources = list({c["url"] for c in relevant_chunks})
    return {"response": bot_response, "intent": _detect_intent(message), "sources": sources}
