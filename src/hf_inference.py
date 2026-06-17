"""
HuggingFace Inference API client for Bayan models.

Uses huggingface_hub.InferenceClient._inner_post with RequestParameters
(v1.19.0) for internal routing inside HF Spaces.
"""

import os
import json
import logging
import time
import inspect

logger = logging.getLogger(__name__)

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")

_client = None
_RequestParameters = None


def _get_client():
    global _client
    if _client is None:
        from huggingface_hub import InferenceClient
        _client = InferenceClient(token=HF_API_TOKEN if HF_API_TOKEN else None)
    return _client


def _get_request_params_class():
    global _RequestParameters
    if _RequestParameters is None:
        from huggingface_hub.inference._common import RequestParameters
        _RequestParameters = RequestParameters
    return _RequestParameters


# Repository IDs
SUMMARIZATION_REPO = os.environ.get("SUMMARIZATION_REPO_ID", "bayan10/summarization-model")
SPELLING_REPO = os.environ.get("SPELLING_REPO_ID", "bayan10/AraSpell-Model")
PUNCTUATION_REPO = os.environ.get("PUNCTUATION_REPO_ID", "bayan10/PuncAra-v1")
AUTOCOMPLETE_REPO = os.environ.get("AUTOCOMPLETE_REPO_ID", "bayan10/AutoComplete")


def _call_model(repo_id, payload, task=None):
    """
    Call HF model using _inner_post with RequestParameters.
    """
    client = _get_client()
    RP = _get_request_params_class()

    if "options" not in payload:
        payload["options"] = {"wait_for_model": True}

    data_bytes = json.dumps(payload).encode("utf-8")
    logger.info("Calling HF model: %s (task=%s)", repo_id, task)

    # Construct RequestParameters - try with fields we know
    try:
        # Inspect what fields RequestParameters accepts
        sig = inspect.signature(RP)
        params = sig.parameters
        logger.info("RequestParameters fields: %s", list(params.keys()))

        # Build kwargs based on what's available
        rp_kwargs = {}
        if "model" in params:
            rp_kwargs["model"] = repo_id
        if "task" in params and task:
            rp_kwargs["task"] = task
        if "data" in params:
            rp_kwargs["data"] = data_bytes
        if "json" in params:
            rp_kwargs["json"] = payload

        rp = RP(**rp_kwargs)
        response = client._inner_post(rp)

    except Exception as e:
        logger.warning("RequestParameters construction failed: %s", e)
        # Last resort: try creating with just positional arg
        rp = RP(data_bytes)
        response = client._inner_post(rp)

    # Parse response
    if isinstance(response, bytes):
        result = json.loads(response.decode("utf-8"))
    elif isinstance(response, str):
        result = json.loads(response)
    else:
        result = response

    logger.info("HF result for %s: type=%s preview=%s",
                repo_id, type(result).__name__, str(result)[:200])
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
        if "error" in result:
            raise RuntimeError("HF API error: " + str(result["error"]))
        return (result.get("summary_text")
                or result.get("generated_text")
                or result.get("translation_text")
                or fallback)
    return str(result) if result else fallback


# ============================================================
# Model wrappers
# ============================================================

def hf_summarize(text, max_length=128, min_length=30):
    result = _call_model(SUMMARIZATION_REPO, {
        "inputs": text,
        "parameters": {"max_length": max_length, "min_length": min_length},
    }, task="summarization")
    return _extract_text(result, text[:100])


def hf_correct_spelling(text):
    result = _call_model(SPELLING_REPO, {"inputs": text})
    return _extract_text(result, text)


def hf_add_punctuation(text):
    result = _call_model(PUNCTUATION_REPO, {"inputs": text})
    return _extract_text(result, text)


def hf_autocomplete(text, n=5):
    result = _call_model(AUTOCOMPLETE_REPO, {
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
        return _get_client() is not None
    except Exception:
        return False


def debug_test_all_models():
    """Test all HF models with full diagnostics."""
    results = {}
    test_text = "هذا نص تجريبي للاختبار"
    long_text = (test_text + " ") * 5

    try:
        import huggingface_hub
        RP = _get_request_params_class()
        rp_sig = str(inspect.signature(RP))
        rp_fields = list(inspect.signature(RP).parameters.keys())
        results["_info"] = {
            "hf_hub_version": huggingface_hub.__version__,
            "RequestParameters_signature": rp_sig[:300],
            "RequestParameters_fields": rp_fields,
        }
    except Exception as e:
        results["_info"] = {"error": repr(e)[:300]}

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
