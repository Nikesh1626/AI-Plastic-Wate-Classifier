import os
import sys
import importlib
from pathlib import Path

try:
    OpenAI = importlib.import_module("openai").OpenAI
    _OPENAI_AVAILABLE = True
except Exception:
    OpenAI = None
    _OPENAI_AVAILABLE = False

try:
    from dotenv import load_dotenv, dotenv_values
except ImportError:
    load_dotenv = None
    dotenv_values = None

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

if load_dotenv is not None:
    load_dotenv(dotenv_path=ENV_PATH, override=True)


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


def _get_openai_key() -> str:
    # Primary source: process environment (supports deployment env vars).
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key

    # Fallback: read directly from local .env if env var was not populated.
    if dotenv_values is not None:
        values = dotenv_values(ENV_PATH)
        file_key = str(values.get("OPENAI_API_KEY", "") or "").strip()
        if file_key:
            os.environ["OPENAI_API_KEY"] = file_key
            return file_key

    return ""


def get_recycling_advice(plastic_type: str, confidence: float = None) -> str:
    """
    Calls the OpenAI ChatGPT API to generate practical reuse and recycling
    advice for the given plastic type.

    Requires OPENAI_API_KEY in the environment.
    Optional: OPENAI_MODEL (defaults to gpt-4o-mini)
    """
    if not _OPENAI_AVAILABLE:
        return _fallback_recycling_advice(
            plastic_type,
            "OpenAI SDK is not installed. Run: pip install openai",
        )

    api_key = _get_openai_key()
    if not api_key:
        return _fallback_recycling_advice(
            plastic_type,
            "OPENAI_API_KEY is missing.",
        )

    model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    conf_text = f"{confidence:.1f}%" if confidence is not None else "unknown confidence"

    system_prompt = (
        "You are a sustainability assistant. Keep responses practical, concise, "
        "safe, and actionable for household users. Use short bullet points."
    )

    user_prompt = (
        f"The plastic type detected is {plastic_type} (detection confidence: {conf_text}).\n"
        "Suggest practical reuse ideas and safe recycling methods for everyday household users.\n"
        "If home recycling is possible, briefly explain the steps.\n"
        "Otherwise, recommend responsible disposal options.\n"
        "Also include one short environmental tip.\n"
        "Keep the total answer under 150 words."
    )

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=220,
        )

        text = ""
        if response.choices and response.choices[0].message:
            text = (response.choices[0].message.content or "").strip()

        if text:
            return text
        return _fallback_recycling_advice(plastic_type, "AI returned an empty response.")

    except Exception as exc:
        err = str(exc)
        lower_err = err.lower()
        print(f"[ChatGPT Error] {type(exc).__name__}: {err[:220]}", file=sys.stderr)

        if "401" in err or "invalid api key" in lower_err or "incorrect api key" in lower_err:
            return _fallback_recycling_advice(plastic_type, "OpenAI API key is invalid.")

        if "429" in err or "rate limit" in lower_err or "quota" in lower_err:
            return _fallback_recycling_advice(
                plastic_type,
                "OpenAI rate limit or quota is reached for this API key.",
            )

        if "model" in lower_err and ("not found" in lower_err or "does not exist" in lower_err):
            return _fallback_recycling_advice(
                plastic_type,
                f"OPENAI_MODEL '{model_name}' is unavailable for this key.",
            )

        return _fallback_recycling_advice(
            plastic_type,
            "ChatGPT request failed. Please try again shortly.",
        )
