import os
import sys

try:
    from google import genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


FALLBACK_ADVICE = {
    "PET": [
        "Rinse and dry bottles before recycling.",
        "Reuse as non-food storage containers.",
        "Avoid storing hot liquids in reused PET bottles.",
    ],
    "HDPE": [
        "Clean containers and keep caps attached if local rules allow.",
        "Reuse for garden tools or storage bins.",
        "HDPE is widely accepted in most recycling programs.",
    ],
    "LDPE": [
        "Reuse as liners or protective wraps.",
        "Keep separate from wet waste.",
        "Use dedicated plastic drop-off points where available.",
    ],
    "PP": [
        "Rinse food residue thoroughly before recycling.",
        "Reuse as dry-item storage for home organization.",
        "Check local acceptance rules for rigid PP containers.",
    ],
    "PS": [
        "Avoid hot food reuse due to leaching risks.",
        "Reuse carefully for packing material if clean.",
        "Prefer dedicated drop-off facilities for PS waste.",
    ],
    "PVC": [
        "Do not burn PVC; it can release harmful fumes.",
        "Reuse only for non-food applications.",
        "Use authorized collection centers for safe disposal.",
    ],
    "OTHER": [
        "Reuse options are limited; prioritize reduction.",
        "Avoid using for food or hot liquids.",
        "Consult specialized local recyclers or municipal support.",
    ],
}


def _is_quota_error(exc: Exception) -> bool:
    error_text = str(exc).upper()
    return "429" in error_text or "RESOURCE_EXHAUSTED" in error_text


def _build_model_candidates(preferred_model: str):
    # Try the preferred model first, then known stable fallbacks.
    defaults = [
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
    ]
    models = []
    for model_name in [preferred_model] + defaults:
        cleaned = (model_name or "").strip()
        if cleaned and cleaned not in models:
            models.append(cleaned)
    return models


def _fallback_recycling_advice(plastic_type: str, reason: str = "") -> str:
    tips = FALLBACK_ADVICE.get(
        plastic_type,
        [
            "Rinse and dry the item before disposal.",
            "Prefer authorized collection centers for mixed plastics.",
            "Reduce single-use plastic where possible.",
        ],
    )
    bullet_text = "\n".join([f"- {tip}" for tip in tips])
    if reason:
        return (
            "AI Sustainability Assistant is temporarily unavailable. "
            f"{reason}\n\n"
            "Practical guidance for now:\n"
            f"{bullet_text}"
        )
    return "Practical guidance:\n" + bullet_text


def get_recycling_advice(plastic_type: str, confidence: float = None) -> str:
    """
    Calls the Gemini API to generate practical reuse and recycling advice
    for the given plastic type.

    Requires the GEMINI_API_KEY environment variable to be set.
    Install dependency: pip install google-genai
    """
    if not _GENAI_AVAILABLE:
        return _fallback_recycling_advice(
            plastic_type,
            "Gemini SDK is not installed on this environment.",
        )

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _fallback_recycling_advice(
            plastic_type,
            "GEMINI_API_KEY is missing.",
        )

    model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-latest").strip() or "gemini-flash-latest"
    conf_text = f"{confidence:.1f}%" if confidence is not None else "unknown confidence"

    prompt = (
        f"The plastic type detected is {plastic_type} (detection confidence: {conf_text}).\n"
        "Suggest practical reuse ideas and safe recycling methods for everyday household users.\n"
        "If home recycling is possible, briefly explain the steps.\n"
        "Otherwise, recommend responsible disposal options.\n"
        "Also include one short environmental tip.\n"
        "Keep the total answer under 150 words. Use simple language and bullet points."
    )

    try:
        client = genai.Client(api_key=api_key)
        attempted_models = []
        for candidate_model in _build_model_candidates(model_name):
            attempted_models.append(candidate_model)
            try:
                response = client.models.generate_content(
                    model=candidate_model,
                    contents=prompt,
                )
                text = (response.text or "").strip()
                if text:
                    return text
            except Exception as model_exc:
                exc_str = str(model_exc)
                exc_type = type(model_exc).__name__
                print(
                    f"[Gemini Error] model={candidate_model} {exc_type}: {exc_str[:200]}",
                    file=sys.stderr,
                )
                if _is_quota_error(model_exc):
                    continue
                return _fallback_recycling_advice(
                    plastic_type,
                    f"Gemini failed on model {candidate_model}.",
                )

        attempted = ", ".join(attempted_models)
        return _fallback_recycling_advice(
            plastic_type,
            "Gemini quota/rate limit reached for available models. "
            f"Tried: {attempted}.",
        )
    except Exception as exc:
        exc_str = str(exc)
        exc_type = type(exc).__name__

        # Log the actual error for debugging
        print(f"[Gemini Error] {exc_type}: {exc_str[:200]}", file=sys.stderr)

        if _is_quota_error(exc):
            return _fallback_recycling_advice(
                plastic_type,
                "Gemini quota is exceeded for the current API key.",
            )

        return _fallback_recycling_advice(
            plastic_type,
            "Gemini service failed unexpectedly.",
        )
