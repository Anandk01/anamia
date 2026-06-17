"""
gemini_report_service.py — AI report generation using google-genai with gemini-3.5-flash.
"""

import logging
import os

from google import genai

from services.rag_knowledge import get_relevant_chunks, format_context

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


REPORT_PROMPT = """Generate a personalised anemia report based on:
- HGB: {hgb} g/dL
- Anemia: {anemia_detected}
- Severity: {severity_level}
- Type: {anemia_type}
- CBC: RBC={rbc}, MCV={mcv}, MCH={mch}, MCHC={mchc}, RDW={rdw}, TLC={tlc}, PLT={plt}

Knowledge: {knowledge}

Write sections: Clinical Summary, What This Means, Recommended Diet, Lifestyle Tips, When to See Doctor.
Keep it supportive and clear. Do not prescribe medications."""


def generate_ai_report(prediction_result: dict, username: str) -> dict:
    try:
        client = _get_client()
    except RuntimeError as e:
        return {"ai_report": None, "sources": [], "error": str(e)}

    anemia_type = prediction_result.get("anemia_type", "Other")
    severity = prediction_result.get("severity_level", "None")
    query = f"{anemia_type} anemia {severity} diet treatment"

    relevant_chunks = get_relevant_chunks(query, max_chunks=6)
    knowledge = format_context(relevant_chunks)
    cbc = prediction_result.get("cbc", {})

    prompt = REPORT_PROMPT.replace("{hgb}", str(prediction_result.get("hgb", "N/A")))
    prompt = prompt.replace("{anemia_detected}", "Yes" if prediction_result.get("anemia_detected") == 1 else "No")
    prompt = prompt.replace("{severity_level}", str(severity))
    prompt = prompt.replace("{anemia_type}", str(anemia_type))
    prompt = prompt.replace("{rbc}", str(cbc.get("rbc", "N/A")))
    prompt = prompt.replace("{mcv}", str(cbc.get("mcv", "N/A")))
    prompt = prompt.replace("{mch}", str(cbc.get("mch", "N/A")))
    prompt = prompt.replace("{mchc}", str(cbc.get("mchc", "N/A")))
    prompt = prompt.replace("{rdw}", str(cbc.get("rdw", "N/A")))
    prompt = prompt.replace("{tlc}", str(cbc.get("tlc", "N/A")))
    prompt = prompt.replace("{plt}", str(cbc.get("plt", "N/A")))
    prompt = prompt.replace("{knowledge}", str(knowledge))

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )
        ai_report = response.text.strip()
    except Exception as exc:
        logger.error("Gemini report failed: %s", exc)
        return {"ai_report": None, "sources": [], "error": str(exc)}

    sources = list({c["url"] for c in relevant_chunks})
    return {"ai_report": ai_report, "sources": sources, "error": None}
