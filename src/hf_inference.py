"""
HuggingFace Inference API client for Bayan models.

Dynamically discovers a reachable HF API endpoint from inside HF Spaces,
since api-inference.huggingface.co is not DNS-resolvable from free-tier containers.
"""

import os
import json
import logging
import time
import socket

logger = logging.getLogger(__name__)

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")

_client = None
_working_url = None


def _get_client():
    global _client
    if _client is None:
        from huggingface_hub import InferenceClient
        _client = InferenceClient(token=HF_API_TOKEN if HF_API_TOKEN else None)
    return _client


# Repository IDs
SUMMARIZATION_REPO = os.environ.get("SUMMARIZATION_REPO_ID", "bayan10/summarization-model")
SPELLING_REPO = os.environ.get("SPELLING_REPO_ID", "bayan10/AraSpell-Model")
PUNCTUATION_REPO = os.environ.get("PUNCTUATION_REPO_ID", "bayan10/PuncAra-v1")
AUTOCOMPLETE_REPO = os.environ.get("AUTOCOMPLETE_REPO_ID", "bayan10/AutoComplete")


def _find_working_endpoint():
    """Try multiple HF API endpoints to find one that resolves."""
    global _working_url

    if _working_url:
        return _working_url

    # Candidate API endpoints
    candidates = [
        "https://router.huggingface.co/hf-inference/models/",
        "https://api-inference.huggingface.co/models/",
        "https://api.huggingface.co/models/",
        "https://huggingface.co/api/models/",
    ]

    for url in candidates:
        # Extract hostname from URL
        hostname = url.split("//")[1].split("/")[0]
        try:
            socket.getaddrinfo(hostname, 443)
            logger.info("DNS resolved for: %s", hostname)
            _working_url = url
            return url
        except socket.gaierror:
            logger.warning("DNS failed for: %s", hostname)
            continue

    logger.error("No HF API endpoint is reachable!")
    return None


def _call_model_httpx(repo_id, payload, task=""):
    """Call HF model using httpx (same transport as InferenceClient)."""
    import httpx

    base_url = _find_working_endpoint()
    if not base_url:
        raise RuntimeError("No reachable HF API endpoint found")

    url = base_url + repo_id

    if "options" not in payload:
        payload["options"] = {"wait_for_model": True}

    headers = {"Content-Type": "application/json"}
    if HF_API_TOKEN:
        headers["Authorization"] = "Bearer " + HF_API_TOKEN

    logger.info("Calling HF model: %s at %s", repo_id, url)

    with httpx.Client(timeout=120) as client:
        resp = client.post(url, json=payload, headers=headers)

    if resp.status_code != 200:
        raise RuntimeError(f"HF API error (HTTP {resp.status_code}): {resp.text[:300]}")

    result = resp.json()
    logger.info("HF result for %s: type=%s preview=%s",
                repo_id, type(result).__name__, str(result)[:200])

    if isinstance(result, dict) and "error" in result:
        raise RuntimeError("HF API error: " + str(result["error"]))

    return result


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


# ============================================================
# Model wrappers
# ============================================================

def hf_summarize(text, max_length=128, min_length=30):
    result = _call_model_httpx(SUMMARIZATION_REPO, {
        "inputs": text,
        "parameters": {"max_length": max_length, "min_length": min_length},
    }, task="summarization")
    return _extract_text(result, text[:100])


def hf_correct_spelling(text):
    result = _call_model_httpx(SPELLING_REPO, {"inputs": text})
    return _extract_text(result, text)


def hf_add_punctuation(text):
    result = _call_model_httpx(PUNCTUATION_REPO, {"inputs": text})
    return _extract_text(result, text)


def hf_autocomplete(text, n=5):
    result = _call_model_httpx(AUTOCOMPLETE_REPO, {
        "inputs": text,
        "parameters": {"max_new_tokens": 20},
    }, task="text-generation")

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
        return _find_working_endpoint() is not None
    except Exception:
        return False


def debug_test_all_models():
    """Test DNS resolution + all HF models."""
    results = {}
    test_text = "هذا نص تجريبي للاختبار"
    long_text = (test_text + " ") * 5

    # DNS diagnostics
    dns_results = {}
    hostnames = [
        "router.huggingface.co",
        "api-inference.huggingface.co",
        "api.huggingface.co",
        "huggingface.co",
        "hf.co",
        "google.com",
        "pypi.org",
    ]
    for hostname in hostnames:
        try:
            addrs = socket.getaddrinfo(hostname, 443)
            dns_results[hostname] = "OK (" + addrs[0][4][0] + ")"
        except socket.gaierror as e:
            dns_results[hostname] = "FAIL: " + str(e)

    results["_dns"] = dns_results
    results["_working_endpoint"] = _find_working_endpoint() or "NONE"

    try:
        import huggingface_hub
        results["_info"] = {"hf_hub_version": huggingface_hub.__version__}
    except Exception as e:
        results["_info"] = {"error": repr(e)[:200]}

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
                "result": str(result)[:300],
                "time_seconds": round(elapsed, 2),
            }
        except Exception as e:
            results[name] = {
                "status": "error",
                "error_type": type(e).__name__,
                "error": str(e)[:500] if str(e) else repr(e)[:500],
            }

    return results
