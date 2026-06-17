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
# First call may be slow (cold start = model loading on HF servers)
HF_TIMEOUT_FIRST = 120   # 2 min for cold start
HF_TIMEOUT_NORMAL = 60   # 1 min for warm model


def _build_headers():
    """Build request headers with auth token."""
    headers = {"Content-Type": "application/json"}
    if HF_API_TOKEN:
        headers["Authorization"] = "Bearer " + HF_API_TOKEN
    return headers


def _call_hf_api(repo_id, payload, timeout=HF_TIMEOUT_NORMAL, retries=2):
    """
    Call HuggingFace Inference API.
    
    Handles cold starts by retrying when model is loading.
    Returns parsed JSON response or raises Exception.
    """
    url = HF_API_BASE + repo_id
    headers = _build_headers()
    data = json.dumps(payload).encode("utf-8")
    
    ctx = ssl.create_default_context()
    
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            result = json.loads(resp.read().decode("utf-8"))
            return result
            
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            
            # Model is loading (cold start) — wait and retry
            if e.code == 503 and "loading" in body.lower():
                try:
                    wait_data = json.loads(body)
                    wait_time = wait_data.get("estimated_time", 30)
                except (json.JSONDecodeError, KeyError):
                    wait_time = 30
                    
                logger.info(
                    "Model %s is loading (attempt %d/%d), waiting %.0fs...",
                    repo_id, attempt + 1, retries + 1, wait_time
                )
                time.sleep(min(wait_time, 60))
                continue
            
            # Other HTTP error
            logger.error("HF API error for %s: HTTP %d — %s", repo_id, e.code, body[:200])
            raise RuntimeError(
                "HF Inference API error (HTTP {}): {}".format(e.code, body[:200])
            )
            
        except Exception as e:
            if attempt < retries:
                logger.warning("HF API call failed (attempt %d): %s", attempt + 1, str(e))
                time.sleep(5)
                continue
            raise
    
    raise RuntimeError("HF Inference API: max retries exceeded for " + repo_id)


# ============================================================
# Model-specific wrappers
# ============================================================

# --- Repository IDs ---
SUMMARIZATION_REPO = os.environ.get("SUMMARIZATION_REPO_ID", "bayan10/summarization-model")
SPELLING_REPO = os.environ.get("SPELLING_REPO_ID", "bayan10/AraSpell-Model")
PUNCTUATION_REPO = os.environ.get("PUNCTUATION_REPO_ID", "bayan10/PuncAra-v1")
AUTOCOMPLETE_REPO = os.environ.get("AUTOCOMPLETE_REPO_ID", "bayan10/AutoComplete")


def hf_summarize(text, max_length=128, min_length=30):
    """
    Summarize Arabic text via HF Inference API.
    Returns the summary string.
    """
    payload = {
        "inputs": text,
        "parameters": {
            "max_length": max_length,
            "min_length": min_length,
        }
    }
    
    result = _call_hf_api(SUMMARIZATION_REPO, payload, timeout=HF_TIMEOUT_FIRST)
    
    # HF summarization returns: [{"summary_text": "..."}]
    if isinstance(result, list) and len(result) > 0:
        return result[0].get("summary_text", "")
    
    # Fallback: might return {"generated_text": "..."}
    if isinstance(result, dict):
        return result.get("summary_text", result.get("generated_text", str(result)))
    
    return str(result)


def hf_correct_spelling(text):
    """
    Correct spelling in Arabic text via HF Inference API.
    Returns the corrected string.
    """
    payload = {"inputs": text}
    
    result = _call_hf_api(SPELLING_REPO, payload, timeout=HF_TIMEOUT_FIRST)
    
    # Text2text models return: [{"generated_text": "..."}]
    if isinstance(result, list) and len(result) > 0:
        return result[0].get("generated_text", text)
    
    if isinstance(result, dict):
        return result.get("generated_text", text)
    
    return text


def hf_add_punctuation(text):
    """
    Add punctuation to Arabic text via HF Inference API.
    Returns the punctuated string.
    """
    payload = {"inputs": text}
    
    result = _call_hf_api(PUNCTUATION_REPO, payload, timeout=HF_TIMEOUT_FIRST)
    
    # Encoder-decoder models return: [{"generated_text": "..."}]
    if isinstance(result, list) and len(result) > 0:
        return result[0].get("generated_text", text)
    
    if isinstance(result, dict):
        return result.get("generated_text", text)
    
    return text


def hf_autocomplete(text, n=5):
    """
    Get autocomplete suggestions for Arabic text via HF Inference API.
    Returns a list of suggestion strings.
    """
    payload = {
        "inputs": text,
        "parameters": {
            "num_return_sequences": min(n, 5),
            "max_new_tokens": 20,
        }
    }
    
    result = _call_hf_api(AUTOCOMPLETE_REPO, payload, timeout=HF_TIMEOUT_FIRST)
    
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
    """
    Quick check if HF Inference API is reachable.
    Returns True if API responds, False otherwise.
    """
    try:
        url = HF_API_BASE + SUMMARIZATION_REPO
        headers = _build_headers()
        # Use GET to just check if model exists (won't trigger inference)
        req = urllib.request.Request(url, headers=headers, method="GET")
        ctx = ssl.create_default_context()
        resp = urllib.request.urlopen(req, timeout=10, context=ctx)
        return resp.status == 200
    except Exception:
        return False
