"""
HuggingFace Inference API client for Bayan models.

Instead of loading 500MB+ models into RAM locally, this module calls
HuggingFace's free Inference API to run predictions remotely.

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
import urllib.request
import urllib.error
import ssl

logger = logging.getLogger(__name__)

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")
HF_API_BASE = "https://api-inference.huggingface.co/models/"

# Timeout for inference calls (seconds)
HF_TIMEOUT = 120  # 2 min — accounts for cold starts


def _build_headers():
    """Build request headers with auth token."""
    headers = {"Content-Type": "application/json"}
    if HF_API_TOKEN:
        headers["Authorization"] = "Bearer " + HF_API_TOKEN
    return headers


def _call_hf_api(repo_id, payload, timeout=HF_TIMEOUT):
    """
    Call HuggingFace Inference API.

    Sends wait_for_model=true to handle cold starts automatically
    (HF will wait up to ~2min for the model to load instead of 503).
    Returns parsed JSON response or raises Exception.
    """
    url = HF_API_BASE + repo_id
    headers = _build_headers()

    # Tell HF to wait for the model to load instead of returning 503
    if "options" not in payload:
        payload["options"] = {"wait_for_model": True}
    else:
        payload["options"]["wait_for_model"] = True

    data = json.dumps(payload).encode("utf-8")
    ctx = ssl.create_default_context()

    logger.info("Calling HF API: %s (payload keys: %s)", repo_id, list(payload.keys()))

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        body = resp.read().decode("utf-8")
        result = json.loads(body)
        logger.info("HF API success for %s: response type=%s", repo_id, type(result).__name__)
        return result

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logger.error("HF API error for %s: HTTP %d — %s", repo_id, e.code, body[:500])
        raise RuntimeError(
            "HF API error for {} (HTTP {}): {}".format(repo_id, e.code, body[:300])
        )

    except Exception as e:
        logger.error("HF API exception for %s: %s", repo_id, str(e))
        raise


# ============================================================
# Model-specific wrappers
# ============================================================

SUMMARIZATION_REPO = os.environ.get("SUMMARIZATION_REPO_ID", "bayan10/summarization-model")
SPELLING_REPO = os.environ.get("SPELLING_REPO_ID", "bayan10/AraSpell-Model")
PUNCTUATION_REPO = os.environ.get("PUNCTUATION_REPO_ID", "bayan10/PuncAra-v1")
AUTOCOMPLETE_REPO = os.environ.get("AUTOCOMPLETE_REPO_ID", "bayan10/AutoComplete")


def hf_summarize(text, max_length=128, min_length=30):
    """Summarize Arabic text via HF Inference API."""
    payload = {
        "inputs": text,
        "parameters": {
            "max_length": max_length,
            "min_length": min_length,
        }
    }

    result = _call_hf_api(SUMMARIZATION_REPO, payload)

    # HF summarization returns: [{"summary_text": "..."}]
    if isinstance(result, list) and len(result) > 0:
        return result[0].get("summary_text", result[0].get("generated_text", ""))

    if isinstance(result, dict):
        return result.get("summary_text", result.get("generated_text", str(result)))

    return str(result)


def hf_correct_spelling(text):
    """Correct spelling in Arabic text via HF Inference API."""
    payload = {"inputs": text}

    result = _call_hf_api(SPELLING_REPO, payload)

    # Text2text / seq2seq models return: [{"generated_text": "..."}]
    if isinstance(result, list) and len(result) > 0:
        item = result[0]
        if isinstance(item, dict):
            return item.get("generated_text", item.get("translation_text", text))
        return str(item)

    if isinstance(result, dict):
        return result.get("generated_text", result.get("translation_text", text))

    return text


def hf_add_punctuation(text):
    """Add punctuation to Arabic text via HF Inference API."""
    payload = {"inputs": text}

    result = _call_hf_api(PUNCTUATION_REPO, payload)

    if isinstance(result, list) and len(result) > 0:
        item = result[0]
        if isinstance(item, dict):
            return item.get("generated_text", item.get("translation_text", text))
        return str(item)

    if isinstance(result, dict):
        return result.get("generated_text", result.get("translation_text", text))

    return text


def hf_autocomplete(text, n=5):
    """Get autocomplete suggestions for Arabic text via HF Inference API."""
    payload = {
        "inputs": text,
        "parameters": {
            "max_new_tokens": 20,
        }
    }

    result = _call_hf_api(AUTOCOMPLETE_REPO, payload)

    # Text generation returns: [{"generated_text": "..."}]
    if isinstance(result, list):
        suggestions = []
        for item in result:
            if isinstance(item, dict):
                gen = item.get("generated_text", "")
                # Remove the input prefix to get just the completion
                if gen.startswith(text):
                    gen = gen[len(text):].strip()
                if gen:
                    suggestions.append(gen)
        return suggestions if suggestions else [text]

    return [text]


def check_hf_api_available():
    """Quick check if HF Inference API is reachable."""
    try:
        url = HF_API_BASE + SUMMARIZATION_REPO
        headers = _build_headers()
        req = urllib.request.Request(url, headers=headers, method="GET")
        ctx = ssl.create_default_context()
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        return resp.status == 200
    except Exception:
        return False


def debug_test_all_models():
    """
    Test all HF models and return results dict.
    Used by /api/debug-models endpoint for troubleshooting.
    """
    results = {}
    test_text = "هذا نص تجريبي للاختبار"

    for name, fn, args in [
        ("summarization", hf_summarize, (test_text + " " + test_text * 3, 30, 10)),
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
                "error": str(e)[:500],
            }

    return results

