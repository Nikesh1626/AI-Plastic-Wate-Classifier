import os
import sys
import json
import random
import time
from collections import deque

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

FALLBACK_HOME_INSIGHTS = {
    "tip": "Carry a reusable bottle for one day each week to cut single-use plastic waste.",
    "fact": "A clean, sorted plastic item is far more likely to be recycled than a contaminated one.",
}

FALLBACK_HOME_INSIGHT_OPTIONS = [
    {
        "tip": "Keep one reusable bag near your door so you never need a plastic carry bag.",
        "fact": "Most recycling lines slow down when mixed waste appears, reducing total recovery rates.",
    },
    {
        "tip": "Rinse and dry food containers before disposal to improve recycling quality.",
        "fact": "Contaminated plastic can cause otherwise recyclable batches to be rejected.",
    },
    {
        "tip": "Choose refill packs for daily essentials to reduce rigid plastic packaging waste.",
        "fact": "Source-separated plastic is significantly easier to sort and process at recycling facilities.",
    },
]

FALLBACK_RECYCLING_INSTRUCTIONS = {
    "PET": [
        "Rinse bottle and cap with water to remove residue.",
        "Crush lightly and keep in dry plastic recycling stream.",
        "Give to kabadiwala or municipal dry-waste collection point.",
    ],
    "HDPE": [
        "Wash the container and remove product residue.",
        "Dry it fully before adding to plastic bin.",
        "Submit through local MRF, recycler, or kabadi pickup.",
    ],
    "LDPE": [
        "Keep wrappers and bags clean and dry.",
        "Collect separately from rigid plastics.",
        "Drop at stores or centres that accept plastic film.",
    ],
    "PP": [
        "Rinse food boxes or cups thoroughly.",
        "Allow moisture to dry before sorting.",
        "Send through dry-waste channel or kabadi network.",
    ],
    "PS": [
        "Do not mix food-soiled thermocol with dry recyclables.",
        "Keep clean pieces separate in a bag.",
        "Use specialised recycler or municipal drop-off if available.",
    ],
    "PVC": [
        "Do not burn or heat this plastic.",
        "Store separately from common household plastic waste.",
        "Hand over only to authorised collection facilities.",
    ],
    "OTHER": [
        "Keep item in dry waste and avoid contamination.",
        "Separate from easier-to-recycle PET/HDPE items.",
        "Check local ward guidance for final disposal route.",
    ],
}

FALLBACK_DESI_REUSE_IDEAS = {
    "PET": [
        "Use cleaned bottle for storing dal or rice in kitchen shelves.",
        "Make a small watering bottle for balcony tulsi or money plant.",
        "Convert into a funnel for transferring oil or grains.",
    ],
    "HDPE": [
        "Reuse sturdy container for washing powder refill at home.",
        "Store pooja flowers before composting.",
        "Use as utility box for screws, plugs, and small tools.",
    ],
    "LDPE": [
        "Reuse clean carry bag as small dustbin liner.",
        "Keep as shoe-cover bag while travelling in monsoon.",
        "Use to wrap wet umbrellas before entering office/home.",
    ],
    "PP": [
        "Reuse dabbas for keeping masalas or snack portions.",
        "Store sewing or rangoli items in labelled boxes.",
        "Use as fridge organizer for cut vegetables.",
    ],
    "PS": [
        "Reuse clean thermocol pieces as packaging cushion.",
        "Use for school craft base projects.",
        "Break and keep for protecting fragile decor storage.",
    ],
    "PVC": [
        "Reuse pipe pieces for balcony plant support.",
        "Use short sections as cable organizers in study table.",
        "Create utility hooks for broom or mop storage.",
    ],
    "OTHER": [
        "Repurpose sturdy containers for non-food storage only.",
        "Use for organizing charging cables and adapters.",
        "Convert into holder for cleaning brushes in wash area.",
    ],
}

HOME_INSIGHT_TOPICS = [
    "kitchen waste sorting",
    "plastic bottle handling",
    "shopping habits",
    "school and office plastics",
    "street litter prevention",
    "plastic film and wraps",
    "recycling contamination",
    "reuse before recycle",
    "household segregation",
    "community collection habits",
]

HOME_INSIGHT_STYLES = [
    "practical and direct",
    "friendly and concise",
    "action-oriented",
    "myth-busting",
    "data-backed and simple",
]

_RECENT_HOME_INSIGHTS = deque(maxlen=10)


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


def _build_light_model_candidates(preferred_model: str):
    # Lightweight models keep cost low for short home-page content.
    defaults = [
        "gemini-flash-lite-latest",
        "gemini-2.0-flash-lite",
        "gemini-flash-latest",
    ]
    models = []
    for model_name in [preferred_model] + defaults:
        cleaned = (model_name or "").strip()
        if cleaned and cleaned not in models:
            models.append(cleaned)
    return models


def _parse_home_insights(raw_text: str):
    text = (raw_text or "").strip()
    if not text:
        return None

    # First try strict JSON.
    try:
        payload = json.loads(text)
        tip = str(payload.get("tip", "")).strip()
        fact = str(payload.get("fact", "")).strip()
        if tip and fact:
            return {"tip": tip, "fact": fact}
    except Exception:
        pass

    # Fallback parser if model returns prefixed lines.
    tip = ""
    fact = ""
    for line in text.splitlines():
        clean = line.strip().lstrip("-*")
        lower = clean.lower()
        if lower.startswith("tip:"):
            tip = clean.split(":", 1)[1].strip()
        elif lower.startswith("fact:"):
            fact = clean.split(":", 1)[1].strip()

    if tip and fact:
        return {"tip": tip, "fact": fact}
    return None


def _normalize_insight(text: str) -> str:
    return " ".join((text or "").lower().replace("\n", " ").split())


def _insight_signature(payload: dict) -> str:
    return _normalize_insight(f"{payload.get('tip', '')} | {payload.get('fact', '')}")


def _token_overlap_ratio(a: str, b: str) -> float:
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0.0
    overlap = len(set_a & set_b)
    return overlap / max(len(set_a), len(set_b))


def _is_too_similar_to_recent(payload: dict) -> bool:
    candidate = _insight_signature(payload)
    for recent in _RECENT_HOME_INSIGHTS:
        if candidate == recent:
            return True
        if _token_overlap_ratio(candidate, recent) >= 0.72:
            return True
    return False


def _remember_home_insight(payload: dict):
    _RECENT_HOME_INSIGHTS.append(_insight_signature(payload))


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


def _fallback_classification_guidance(plastic_type: str, reason: str = "") -> dict:
    recycling = FALLBACK_RECYCLING_INSTRUCTIONS.get(
        plastic_type,
        [
            "Rinse the item and keep it in dry waste.",
            "Separate from wet or food-contaminated waste.",
            "Use local authorised recycler or kabadi collection.",
        ],
    )
    reuse = FALLBACK_DESI_REUSE_IDEAS.get(
        plastic_type,
        [
            "Reuse as a small organizer for household utility items.",
            "Use as non-food storage in cleaning area.",
            "Repurpose in home craft before final disposal.",
        ],
    )
    reuse_quoted = []
    for item in reuse[:3]:
        clean = str(item).strip().strip('"')
        reuse_quoted.append(f'"{clean}"')
    advice = (
        "Keep plastics clean and dry, segregate by type, and prioritise safe disposal through your local kabadi or municipal dry-waste channel."
    )
    if reason:
        advice = f"{advice} ({reason})"
    return {
        "recycling_instructions": recycling[:3],
        "reuse_ideas": reuse_quoted,
        "ai_advice": advice,
    }


def _parse_classification_guidance(raw_text: str):
    text = (raw_text or "").strip()
    if not text:
        return None

    try:
        payload = json.loads(text)
    except Exception:
        return None

    recycling = payload.get("recycling_instructions") or payload.get("recyclingInstructions")
    reuse = payload.get("reuse_ideas") or payload.get("reuseIdeas")
    advice = payload.get("ai_advice") or payload.get("aiAdvice")

    if not isinstance(recycling, list) or not isinstance(reuse, list) or not isinstance(advice, str):
        return None

    recycling_clean = [str(item).strip() for item in recycling if str(item).strip()][:3]
    reuse_clean = [str(item).strip().strip('"') for item in reuse if str(item).strip()][:3]
    advice_clean = advice.strip()

    if len(recycling_clean) < 2 or len(reuse_clean) < 2 or not advice_clean:
        return None

    reuse_quoted = [f'"{item}"' for item in reuse_clean]
    return {
        "recycling_instructions": recycling_clean,
        "reuse_ideas": reuse_quoted,
        "ai_advice": advice_clean,
    }


def _is_advice_redundant(ai_advice: str, recycling: list, reuse: list) -> bool:
    ai_norm = _normalize_insight(ai_advice)
    for item in recycling + reuse:
        if _token_overlap_ratio(ai_norm, _normalize_insight(item)) >= 0.72:
            return True
    return False


def get_classification_guidance(plastic_type: str, confidence: float = None) -> dict:
    """Returns structured recycling instructions, desi reuse ideas, and distinct AI advice."""
    if not _GENAI_AVAILABLE:
        return _fallback_classification_guidance(
            plastic_type,
            "Gemini SDK is not installed on this environment.",
        )

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _fallback_classification_guidance(
            plastic_type,
            "GEMINI_API_KEY is missing.",
        )

    model_name = os.environ.get("GEMINI_MODEL", "gemini-flash-latest").strip() or "gemini-flash-latest"
    conf_text = f"{confidence:.1f}%" if confidence is not None else "unknown confidence"

    prompt = (
        f"Plastic type detected: {plastic_type} (confidence: {conf_text}). "
        "Return valid JSON only with keys: recycling_instructions, reuse_ideas, ai_advice. "
        "recycling_instructions: array of 2-3 short actionable points for this exact plastic type. "
        "reuse_ideas: array of 2-3 desi Indian practical reuse ideas; each idea should be plain text (no markdown). "
        "ai_advice: one compact paragraph with additional guidance that DOES NOT repeat or paraphrase any point from recycling_instructions or reuse_ideas. "
        "No markdown, no numbering, no extra keys, no preface."
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
                parsed = _parse_classification_guidance(response.text or "")
                if not parsed:
                    continue
                if _is_advice_redundant(
                    parsed["ai_advice"],
                    parsed["recycling_instructions"],
                    parsed["reuse_ideas"],
                ):
                    parsed["ai_advice"] = (
                        "For best outcomes, keep this plastic in a dry segregated stream and hand it only to reliable local collection channels; avoid mixing with wet waste."
                    )
                return parsed
            except Exception as model_exc:
                exc_str = str(model_exc)
                exc_type = type(model_exc).__name__
                print(
                    f"[Gemini Structured Guidance Error] model={candidate_model} {exc_type}: {exc_str[:200]}",
                    file=sys.stderr,
                )
                if _is_quota_error(model_exc):
                    continue
                break
        return _fallback_classification_guidance(
            plastic_type,
            f"Gemini unavailable for models: {', '.join(attempted_models)}",
        )
    except Exception as exc:
        print(f"[Gemini Structured Guidance Error] {type(exc).__name__}: {str(exc)[:200]}", file=sys.stderr)
        return _fallback_classification_guidance(
            plastic_type,
            "Gemini service failed unexpectedly.",
        )


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


def get_home_insights() -> dict:
    """
    Generates a short smart eco tip and a fun fact for the homepage.
    Uses a low-cost Gemini model suitable for lightweight copy updates.
    """
    if not _GENAI_AVAILABLE:
        return dict(FALLBACK_HOME_INSIGHTS)

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return dict(FALLBACK_HOME_INSIGHTS)

    model_name = (
        os.environ.get("GEMINI_LIGHT_MODEL", "gemini-flash-lite-latest").strip()
        or "gemini-flash-lite-latest"
    )

    try:
        client = genai.Client(api_key=api_key)
        for _ in range(4):
            topic = random.choice(HOME_INSIGHT_TOPICS)
            style = random.choice(HOME_INSIGHT_STYLES)
            nonce = f"{time.time_ns()}-{random.randint(1000, 9999)}"
            avoid = "; ".join(list(_RECENT_HOME_INSIGHTS)[-4:]) or "none"
            prompt = (
                "Generate homepage content for a plastic recycling app. "
                "Return valid JSON only with keys tip and fact. "
                "tip: one practical eco action, max 20 words. "
                "fact: one accurate recycling-related fact, max 22 words. "
                f"Topic focus: {topic}. Writing style: {style}. "
                f"Avoid repeating these recent ideas: {avoid}. "
                f"Uniqueness token: {nonce}. "
                "No markdown, no extra keys, no explanation."
            )

            for candidate_model in _build_light_model_candidates(model_name):
                try:
                    response = client.models.generate_content(
                        model=candidate_model,
                        contents=prompt,
                    )
                    parsed = _parse_home_insights(response.text or "")
                    if parsed and not _is_too_similar_to_recent(parsed):
                        _remember_home_insight(parsed)
                        return parsed
                except Exception as model_exc:
                    exc_str = str(model_exc)
                    exc_type = type(model_exc).__name__
                    print(
                        f"[Gemini Home Insights Error] model={candidate_model} {exc_type}: {exc_str[:200]}",
                        file=sys.stderr,
                    )
                    if _is_quota_error(model_exc):
                        continue
                    break
    except Exception as exc:
        print(f"[Gemini Home Insights Error] {type(exc).__name__}: {str(exc)[:200]}", file=sys.stderr)

    chosen = random.choice(FALLBACK_HOME_INSIGHT_OPTIONS + [FALLBACK_HOME_INSIGHTS])
    _remember_home_insight(chosen)
    return dict(chosen)
