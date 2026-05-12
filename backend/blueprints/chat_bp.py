"""
Chat Blueprint — /api/chat

Gemini-powered RAG chatbot for anemia Q&A.
Knowledge sourced from WHO and NHLBI fact sheets.

Routes:
    GET  /api/chat/           → health check
    POST /api/chat/message    → process a user message with Gemini RAG
"""

import logging

from flask import Blueprint, jsonify, request

from middleware.auth import require_auth

logger = logging.getLogger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')


@chat_bp.get('/')
def index():
    return jsonify({"status": "ok", "blueprint": "chat", "engine": "gemini-rag"})


@chat_bp.post('/message')
@require_auth
def chat_message():
    """
    Process a user chat message using Gemini RAG.

    Request body (JSON):
        {
            "message":    str  — the user's text query (required)
            "session_id": str  — unique session identifier (required)
        }

    Response (200 OK):
        {
            "status":     "ok",
            "response":   str,
            "intent":     str,
            "session_id": str,
            "sources":    list[str]
        }
    """
    data = request.get_json(silent=True) or {}

    message = (data.get("message") or "").strip()
    session_id = (data.get("session_id") or "").strip()

    if not message:
        return jsonify({"status": "error", "message": "message must be a non-empty string"}), 400
    if not session_id:
        return jsonify({"status": "error", "message": "session_id must be a non-empty string"}), 400

    # Use Gemini RAG chatbot
    try:
        from services.gemini_chatbot_service import chat_with_gemini
        result = chat_with_gemini(message, session_id)
    except Exception as exc:
        logger.error("Gemini chatbot error: %s", exc)
        # Fallback to keyword chatbot if Gemini fails
        try:
            from services.chatbot_service import classify_and_respond, get_or_create_session
            result = classify_and_respond(message, session_id)
            session = get_or_create_session(session_id)
            session.add_exchange(message, result["response"])
            result["sources"] = []
        except Exception as fallback_exc:
            logger.error("Fallback chatbot also failed: %s", fallback_exc)
            result = {
                "response": "I'm having trouble right now. Please try again in a moment.",
                "intent": "error",
                "sources": [],
            }

    return jsonify({
        "status": "ok",
        "response": result["response"],
        "intent": result.get("intent", "general"),
        "session_id": session_id,
        "sources": result.get("sources", []),
    }), 200
