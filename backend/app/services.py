"""Gemini-backed helper services: text translation and image→query vision."""
import os, base64, binascii
import google.generativeai as genai

_LANG_NAME = {"en": "English", "de": "German", "zh": "Traditional Chinese"}

# Tiny in-memory cache so re-rendering the same chat doesn't re-hit Gemini.
_translation_cache: dict[tuple[str, str], str] = {}


def translate(text: str, target_lang: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    key = (text, target_lang)
    if key in _translation_cache:
        return _translation_cache[key]
    target_name = _LANG_NAME.get(target_lang, target_lang)
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = (
        f"Translate the following marketplace/negotiation message into {target_name}. "
        f"Return only the translation, no quotes, no explanation.\n\n{text}"
    )
    result = model.generate_content(prompt).text.strip()
    _translation_cache[key] = result
    return result


def identify_product(image_base64: str) -> str:
    """Identify the product in a photo and return a concise search query."""
    raw = image_base64.strip()
    if raw.startswith("data:"):
        # strip a data URL prefix like "data:image/jpeg;base64,"
        raw = raw.split(",", 1)[-1]
    try:
        image_bytes = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValueError("Invalid base64 image data") from e

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = (
        "Identify the second-hand product in this photo. Respond with a short search "
        "query of brand + model only (e.g. 'iPhone 14 128GB' or 'Sony A7 III'). "
        "No extra words."
    )
    result = model.generate_content(
        [prompt, {"mime_type": "image/jpeg", "data": image_bytes}]
    )
    return result.text.strip()
