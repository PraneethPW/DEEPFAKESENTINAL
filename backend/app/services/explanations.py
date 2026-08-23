import json
import logging

import httpx
from pydantic import ValidationError

from app.config import settings
from app.models import Analysis
from app.schemas import ExplanationOut


logger = logging.getLogger(__name__)
SYSTEM_PROMPT = """You are explaining an existing machine-generated media screening result.
Do not alter the detector classification. Do not invent visual evidence or metadata.
Do not claim legal or forensic certainty. Do not state that a highlighted region is definitely forged.
Explain only the structured analysis supplied to you. Return JSON with keys: summary,
evidence_interpretation, quality_context, recommended_review, limitations."""


def structured_context(analysis: Analysis) -> dict:
    return {
        "analysis_id": analysis.id,
        "analysis_type": analysis.media_type,
        "classification": analysis.classification,
        "fake_probability": analysis.fake_probability,
        "real_probability": analysis.real_probability,
        "quality_status": analysis.quality_status,
        "face_detected": analysis.quality.face_detected if analysis.quality else None,
        "attention_available": any(item.available for item in analysis.evidence),
        "warnings": analysis.quality.warnings if analysis.quality else [],
        "analysed_frames": analysis.analysed_frames,
        "aggregate": analysis.aggregate_metadata,
        "human_review": analysis.reviews[-1].decision if analysis.reviews else None,
        "review_notes": [note.note for note in analysis.notes[-5:]],
    }


def deterministic_fallback(analysis: Analysis) -> ExplanationOut:
    label = (analysis.classification or "INCONCLUSIVE").replace("_", " ").title()
    warnings = "; ".join(analysis.quality.warnings or []) if analysis.quality else "No quality data is available."
    return ExplanationOut(
        summary=f"The configured detector returned {label}. This is a screening signal for human review, not a definitive authenticity finding.",
        evidence_interpretation=(
            "Highlighted regions contributed more strongly to the model output; they are not a pixel-level forgery mask."
            if any(item.available for item in analysis.evidence)
            else "No usable attention evidence map was produced for this analysis."
        ),
        quality_context=warnings or f"Input quality was rated {analysis.quality_status}.",
        recommended_review="Inspect the original source, provenance, temporal consistency, and highlighted regions before recording a human decision.",
        limitations="AI explanation is currently unavailable. Detector output can be affected by compression, quality, and unseen generation methods.",
    )


def explain(analysis: Analysis, question: str | None = None) -> tuple[ExplanationOut, str]:
    if not settings.openrouter_api_key:
        return deterministic_fallback(analysis), "deterministic"
    context = structured_context(analysis)
    prompt = f"Structured detector evidence:\n{json.dumps(context)}"
    if question:
        prompt += f"\nUser question: {question}"
    payload = {
        "model": settings.openrouter_model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }
    try:
        response = httpx.post(
            f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        for attempt in range(2):
            try:
                return ExplanationOut.model_validate_json(content), "openrouter"
            except ValidationError:
                if attempt == 0:
                    payload["messages"].append({"role": "assistant", "content": content})
                    payload["messages"].append({"role": "user", "content": "Return only valid JSON matching the requested keys."})
                    retry = httpx.post(
                        f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                        json=payload,
                        timeout=45,
                    )
                    retry.raise_for_status()
                    content = retry.json()["choices"][0]["message"]["content"]
        raise ValueError("invalid structured explanation")
    except Exception:
        logger.exception("OpenRouter explanation unavailable")
        return deterministic_fallback(analysis), "deterministic"

