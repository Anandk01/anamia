"""
gemini_report_service.py — AI-powered clinical report generation using Groq.

Generates a personalised clinical narrative for each prediction result,
grounded in WHO and NHLBI knowledge sources.
"""

import logging
import os

from services.rag_knowledge import get_relevant_chunks, format_context

logger = logging.getLogger(__name__)

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


REPORT_PROMPT = """You are a clinical AI assistant generating a personalised anemia report.
Use ONLY the provided WHO and NHLBI knowledge to write evidence-based recommendations.

PATIENT DATA:
- HGB (Haemoglobin): {hgb} g/dL
- Anemia Detected: {anemia_detected}
- Severity: {severity_level}
- Anemia Type: {anemia_type}
- Confidence: {confidence}%
- CBC Values: RBC={rbc}, MCV={mcv}, MCH={mch}, MCHC={mchc}, RDW={rdw}, TLC={tlc}, PLT={plt}
- Top Features (SHAP): {explanation}

KNOWLEDGE BASE (WHO & NHLBI):
{knowledge}

Generate a structured clinical report with these sections:
1. **Clinical Summary** (2-3 sentences explaining the result in plain language)
2. **What This Means** (explain the severity and what it implies for the patient)
3. **Recommended Diet** (specific foods from the WHO/NHLBI sources)
4. **Lifestyle Recommendations** (3-4 actionable tips)
5. **When to See a Doctor** (based on severity)
6. **Important Disclaimer** (one sentence)

Keep the tone supportive, clear, and non-alarming. Do not prescribe medications."""


def generate_ai_report(prediction_result: dict, username: str) -> dict:
    """Generate an AI-powered clinical narrative for a prediction result."""
    try:
        client = _get_client()
    except RuntimeError as e:
        logger.error("AI not configured: %s", e)
        return {"ai_report": None, "sources": [], "error": str(e)}

    # Build query for RAG retrieval
    anemia_type = prediction_result.get("anemia_type", "Other")
    severity = prediction_result.get("severity_level", "None")
    query = f"{anemia_type} anemia {severity} diet treatment symptoms"

    relevant_chunks = get_relevant_chunks(query, max_chunks=6)
    knowledge = format_context(relevant_chunks)

    # Format explanation
    explanation = prediction_result.get("explanation", [])
    explanation_str = "; ".join(
        f"{e.get('feature', '')} ({e.get('direction', '')})"
        for e in explanation[:3]
    ) if explanation else "Not available"

    confidence = prediction_result.get("anemia_confidence", 0)
    confidence_pct = round(confidence * 100, 1)
    cbc = prediction_result.get("cbc", {})

    prompt = REPORT_PROMPT.replace("{hgb}", str(prediction_result.get("hgb", "N/A")))
    prompt = prompt.replace("{anemia_detected}", "Yes" if prediction_result.get("anemia_detected") == 1 else "No")
    prompt = prompt.replace("{severity_level}", str(severity))
    prompt = prompt.replace("{anemia_type}", str(anemia_type))
    prompt = prompt.replace("{confidence}", str(confidence_pct))
    prompt = prompt.replace("{rbc}", str(cbc.get("rbc", "N/A")))
    prompt = prompt.replace("{mcv}", str(cbc.get("mcv", "N/A")))
    prompt = prompt.replace("{mch}", str(cbc.get("mch", "N/A")))
    prompt = prompt.replace("{mchc}", str(cbc.get("mchc", "N/A")))
    prompt = prompt.replace("{rdw}", str(cbc.get("rdw", "N/A")))
    prompt = prompt.replace("{tlc}", str(cbc.get("tlc", "N/A")))
    prompt = prompt.replace("{plt}", str(cbc.get("plt", "N/A")))
    prompt = prompt.replace("{explanation}", str(explanation_str))
    prompt = prompt.replace("{knowledge}", str(knowledge))

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a clinical AI assistant specializing in anemia."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.3,
        )
        ai_report = response.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("AI report generation failed: %s", exc)
        return {"ai_report": None, "sources": [], "error": str(exc)}

    sources = list({chunk["url"] for chunk in relevant_chunks})

    return {
        "ai_report": ai_report,
        "sources": sources,
        "error": None,
    }
