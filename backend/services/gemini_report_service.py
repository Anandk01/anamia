"""
gemini_report_service.py — AI-powered clinical report generation using Gemini.

Generates a personalised clinical narrative for each prediction result,
grounded in WHO and NHLBI knowledge sources.
"""

import logging
import os

from google import genai

from services.rag_knowledge import get_all_diet_knowledge, get_relevant_chunks, format_context

logger = logging.getLogger(__name__)

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


REPORT_PROMPT = """You are a clinical AI assistant generating a personalised anemia report.
Use ONLY the provided WHO and NHLBI knowledge to write evidence-based recommendations.

PATIENT DATA:
- Username: {username}
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
3. **Recommended Diet** (specific foods from the WHO/NHLBI sources, cite them)
4. **Lifestyle Recommendations** (3-4 actionable tips based on the knowledge base)
5. **When to See a Doctor** (based on severity — be specific)
6. **Important Disclaimer** (one sentence)

Keep the tone supportive, clear, and non-alarming. Do not prescribe medications.
Base ALL recommendations on the WHO and NHLBI sources provided."""


def generate_ai_report(prediction_result: dict, username: str) -> dict:
    """
    Generate an AI-powered clinical narrative for a prediction result.

    Parameters
    ----------
    prediction_result : dict
        Full prediction result from PredictionService.predict()
    username : str
        Patient/doctor username

    Returns
    -------
    dict
        {"ai_report": str, "sources": list, "error": None or str}
    """
    try:
        client = _get_client()
    except RuntimeError as e:
        logger.error("Gemini not configured: %s", e)
        return {"ai_report": None, "sources": [], "error": str(e)}

    # Build query for RAG retrieval
    anemia_type = prediction_result.get("anemia_type", "Other")
    severity = prediction_result.get("severity_level", "None")
    query = f"{anemia_type} anemia {severity} diet treatment symptoms"

    relevant_chunks = get_relevant_chunks(query, max_chunks=6)
    # Always include diet knowledge
    diet_chunks = [c for c in relevant_chunks if "diet" in c.get("topic", "")]
    if not diet_chunks:
        from services.rag_knowledge import KNOWLEDGE_BASE
        diet_chunks = [c for c in KNOWLEDGE_BASE if "diet" in c["topic"]]
        relevant_chunks = relevant_chunks + diet_chunks

    knowledge = format_context(relevant_chunks)

    # Format explanation
    explanation = prediction_result.get("explanation", [])
    explanation_str = "; ".join(
        f"{e.get('feature', '')} ({e.get('direction', '')})"
        for e in explanation[:3]
    ) if explanation else "Not available"

    # Format confidence
    confidence = prediction_result.get("anemia_confidence", 0)
    confidence_pct = round(confidence * 100, 1)

    cbc = prediction_result.get("cbc", {})

    prompt = REPORT_PROMPT.replace("{username}", str(username))
    prompt = prompt.replace("{hgb}", str(prediction_result.get("hgb", "N/A")))
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
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt,
        )
        ai_report = response.text.strip()
    except Exception as exc:
        logger.error("Gemini report generation failed: %s", exc)
        return {"ai_report": None, "sources": [], "error": str(exc)}

    sources = list({chunk["url"] for chunk in relevant_chunks})

    return {
        "ai_report": ai_report,
        "sources": sources,
        "error": None,
    }
