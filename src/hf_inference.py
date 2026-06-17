"""
HuggingFace Inference API client for Bayan models.

Uses huggingface_hub.InferenceClient which routes through HF's internal
network when running inside HF Spaces.
"""

import os
import json
import logging
import time

logger = logging.getLogger(__name__)

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")

_client = None


def _get_client():
    global _client
    if _client is None:
        from huggingface_hub import InferenceClient
        _client = InferenceClient(token=HF_API_TOKEN if HF_API_TOKEN else None)
        logger.info("InferenceClient initialized")
    return _client


# Repository IDs
SUMMARIZATION_REPO = os.environ.get("SUMMARIZATION_REPO_ID", "bayan10/summarization-model")
SPELLING_REPO = os.environ.get("SPELLING_REPO_ID", "bayan10/AraSpell-Model")
PUNCTUATION_REPO = os.environ.get("PUNCTUATION_REPO_ID", "bayan10/PuncAra-v1")
AUTOCOMPLETE_REPO = os.environ.get("AUTOCOMPLETE_REPO_ID", "bayan10/AutoComplete")


def _raw_inference(repo_id, payload):
    """
    Make a raw inference call using whatever transport InferenceClient uses.
    Tries multiple approaches to find one that works.
    """
    client = _get_client()

    # Approach 1: Try the internal _post method
    if hasattr(client, '_post'):
        logger.info("Using client._post for %s", repo_id)
        response = client._post(json=payload, model=repo_id)
        return json.loads(response) if isinstance(response, (bytes, str)) else response

    # Approach 2: Get the session from the client and use it directly
    session = None
    for attr in ['_session', 'session', '_client', 'client', '_http_client']:
        if hasattr(client, attr):
            session = getattr(client, attr)
            break

    if session and hasattr(session, 'post'):
        # Find the base API URL
        api_url = None
        for attr in ['api_url', 'base_url', '_api_url', 'inference_url', '_base_url']:
            val = getattr(client, attr, None)
            if val and isinstance(val, str):
                api_url = val
                break

        if not api_url:
            api_url = "https://api-inference.huggingface.co/models"

        url = api_url.rstrip('/') + '/' + repo_id if '/models' in api_url else api_url + '/models/' + repo_id
        logger.info("Using session.post to %s", url)

        headers = {"Content-Type": "application/json"}
        if HF_API_TOKEN:
            headers["Authorization"] = "Bearer " + HF_API_TOKEN

        resp = session.post(url, json=payload, headers=headers, timeout=120)
        return resp.json()

    raise RuntimeError("No usable transport found on InferenceClient")


# ============================================================
# Model wrappers
# ============================================================

def _extract_text(result, fallback=""):
    """Extract text from various HF response formats."""
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
    """Summarize Arabic text."""
    result = _raw_inference(SUMMARIZATION_REPO, {
        "inputs": text,
        "parameters": {"max_length": max_length, "min_length": min_length},
        "options": {"wait_for_model": True},
    })
    return _extract_text(result, text[:100])


def hf_correct_spelling(text):
    """Correct spelling in Arabic text."""
    result = _raw_inference(SPELLING_REPO, {
        "inputs": text,
        "options": {"wait_for_model": True},
    })
    return _extract_text(result, text)


def hf_add_punctuation(text):
    """Add punctuation to Arabic text."""
    result = _raw_inference(PUNCTUATION_REPO, {
        "inputs": text,
        "options": {"wait_for_model": True},
    })
    return _extract_text(result, text)


def hf_autocomplete(text, n=5):
    """Get autocomplete suggestions."""
    result = _raw_inference(AUTOCOMPLETE_REPO, {
        "inputs": text,
        "parameters": {"max_new_tokens": 20},
        "options": {"wait_for_model": True},
    })

    if isinstance(result, str):
        c = result[len(text):].strip() if result.startswith(text) else result
        return [c] if c else [text]
    if isinstance(result, list):
        out = []
        for item in result:
            g = item.get("generated_text", "") if isinstance(item, dict) else str(item)
            if g.startswith(text):
                g = g[len(text):].strip()
            if g:
                out.append(g)
        return out if out else [text]
    return [text]


def check_hf_api_available():
    try:
        return _get_client() is not None
    except Exception:
        return False


def debug_test_all_models():
    """Full diagnostic debug."""
    results = {}
    test_text = "هذا نص تجريبي للاختبار"
    long_text = (test_text + " ") * 5

    # Deep diagnostics
    try:
        client = _get_client()
        import huggingface_hub
        all_attrs = [a for a in dir(client) if not a.startswith('__')]
        private_attrs = {a: str(type(getattr(client, a, None)).__name__)
                        for a in all_attrs if a.startswith('_') and not a.startswith('__')}
        public_methods = [a for a in all_attrs if not a.startswith('_')
                         and callable(getattr(client, a, None))]

        diag = {
            "hf_hub_version": getattr(huggingface_hub, '__version__', 'unknown'),
            "has__post": hasattr(client, '_post'),
            "has_session": hasattr(client, '_session') or hasattr(client, 'session'),
            "private_attrs": private_attrs,
            "public_methods": public_methods[:30],
        }

        # Try to find internal session/transport
        for attr in ['_session', 'session', '_client', 'client', '_http_client',
                     '_api_url', 'api_url', 'base_url', '_base_url', 'inference_url',
                     'headers', '_headers']:
            val = getattr(client, attr, 'NOT_FOUND')
            if val != 'NOT_FOUND':
                diag['found_' + attr] = str(val)[:200] if not callable(val) else 'callable'
    except Exception as e:
        diag = {"error": repr(e)[:300]}

    results["_diagnostics"] = diag
    results["_env"] = {
        "HF_INFERENCE_ENDPOINT": os.environ.get("HF_INFERENCE_ENDPOINT", "NOT SET"),
        "SPACE_ID": os.environ.get("SPACE_ID", "NOT SET"),
    }

    # Test each model
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
