"""
HuggingFace Inference API client for Bayan models.

Uses the `requests` library (via huggingface_hub's internal session)
to call the HF Inference API from within HF Spaces.

Models:
  - bayan10/summarization-model  (MBart, summarization pipeline)
  - bayan10/AraSpell-Model       (spelling correction)
  - bayan10/PuncAra-v1           (punctuation, encoder-decoder)
  - bayan10/AutoComplete         (text generation / fill-mask)
"""

import os
import json
import logging
import time
import requests

logger = logging.getLogger(__name__)

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")
HF_API_BASE = "https://api-inference.huggingface.co/models/"
HF_TIMEOUT = 120  # seconds — accounts for cold starts


def _headers():
    """Build request headers with auth token."""
    h = {"Content-Type": "application/json"}
    if HF_API_TOKEN:
        h["Authorization"] = "Bearer " + HF_API_TOKEN
    return h


def _call_model(repo_id, payload):
    """
    Call any HF model via the Inference API.
    Uses requests library + wait_for_model option.
    Returns parsed JSON response.
    """
    url = HF_API_BASE + repo_id

    # Tell HF to wait for the model to load instead of returning 503
    if "options" not in payload:
        payload["options"] = {"wait_for_model": True}

    logger.info("HF API call: %s", repo_id)
    resp = requests.post(url, headers=_headers(), json=payload, timeout=HF_TIMEOUT)

    logger.info("HF API response for %s: HTTP %d, size=%d bytes",
                repo_id, resp.status_code, len(resp.content))

    if resp.status_code != 200:
        logger.error("HF API error for %s: HTTP %d — %s",
                     repo_id, resp.status_code, resp.text[:500])
        raise RuntimeError("HF API error for {} (HTTP {}): {}".format(
            repo_id, resp.status_code, resp.text[:300]))

    result = resp.json()
    logger.info("HF API result for %s: type=%s, preview=%s",
                repo_id, type(result).__name__, str(result)[:150])
    return result


# ============================================================
# Repository IDs
# ============================================================

SUMMARIZATION_REPO = os.environ.get("SUMMARIZATION_REPO_ID", "bayan10/summarization-model")
SPELLING_REPO = os.environ.get("SPELLING_REPO_ID", "bayan10/AraSpell-Model")
PUNCTUATION_REPO = os.environ.get("PUNCTUATION_REPO_ID", "bayan10/PuncAra-v1")
AUTOCOMPLETE_REPO = os.environ.get("AUTOCOMPLETE_REPO_ID", "bayan10/AutoComplete")


# ============================================================
# Model-specific wrappers
# ============================================================

def _extract_text(result, fallback=""):
    """Extract generated text from various HF response formats."""
    if isinstance(result, list) and len(result) > 0:
        item = result[0]
        if isinstance(item, dict):
            return (item.get("summary_text")
                    or item.get("generated_text")
                    or item.get("translation_text")
                    or fallback)
        return str(item) if str(item).strip() else fallback

    if isinstance(result, dict):
        return (result.get("summary_text")
                or result.get("generated_text")
                or result.get("translation_text")
                or fallback)

    return str(result) if result else fallback


def hf_summarize(text, max_length=128, min_length=30):
    """Summarize Arabic text via HF Inference API."""
    result = _call_model(SUMMARIZATION_REPO, {
        "inputs": text,
        "parameters": {
            "max_length": max_length,
            "min_length": min_length,
        }
    })
    return _extract_text(result, text[:100])


def hf_correct_spelling(text):
    """Correct spelling in Arabic text via HF Inference API."""
    result = _call_model(SPELLING_REPO, {"inputs": text})
    return _extract_text(result, text)


def hf_add_punctuation(text):
    """Add punctuation to Arabic text via HF Inference API."""
    result = _call_model(PUNCTUATION_REPO, {"inputs": text})
    return _extract_text(result, text)


def hf_autocomplete(text, n=5):
    """Get autocomplete suggestions for Arabic text via HF Inference API."""
    result = _call_model(AUTOCOMPLETE_REPO, {
        "inputs": text,
        "parameters": {"max_new_tokens": 20}
    })

    if isinstance(result, str):
        completion = result[len(text):].strip() if result.startswith(text) else result
        return [completion] if completion else [text]

    if isinstance(result, list):
        suggestions = []
        for item in result:
            gen = item.get("generated_text", "") if isinstance(item, dict) else str(item)
            if gen.startswith(text):
                gen = gen[len(text):].strip()
            if gen:
                suggestions.append(gen)
        return suggestions if suggestions else [text]

    return [text]


def check_hf_api_available():
    """Quick check if HF Inference API is reachable."""
    try:
        resp = requests.get(HF_API_BASE + SUMMARIZATION_REPO,
                           headers=_headers(), timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


def debug_test_all_models():
    """
    Test all HF models and return results dict.
    Used by /api/debug-models endpoint for troubleshooting.
    """
    results = {}
    test_text = "هذا نص تجريبي للاختبار"
    long_text = (test_text + " ") * 5

    for name, fn, args in [
        ("summarization", hf_summarize, (long_text, 30, 10)),
        ("spelling", hf_correct_spelling, (test_text,)),
        ("punctuation", hf_add_punctuation, (test_text,)),
        ("autocomplete", hf_autocomplete, (test_text, 3)),
    ]:
        try:
            t0 = time.time()
            result = fn(*args)
            elapsed = time.time() - t0
            results[name] = {
                "status": "ok",
                "result": str(result)[:200],
                "time_seconds": round(elapsed, 2),
            }
        except Exception as e:
            results[name] = {
                "status": "error",
                "error_type": type(e).__name__,
                "error": str(e)[:500] if str(e) else repr(e)[:500],
            }

    return results
