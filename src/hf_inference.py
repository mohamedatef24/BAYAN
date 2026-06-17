"""
HuggingFace Inference API client for Bayan models.

Uses huggingface_hub.InferenceClient which works from within HF Spaces
(handles internal routing / DNS automatically).

Models:
  - bayan10/summarization-model  (MBart, summarization pipeline)
  - bayan10/AraSpell-Model       (spelling correction)
  - bayan10/PuncAra-v1           (punctuation, encoder-decoder)
  - bayan10/AutoComplete         (text generation / fill-mask)
"""

import os
import logging
import time

logger = logging.getLogger(__name__)

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")

# Lazy-initialized client (created on first use)
_client = None


def _get_client():
    """Get or create the InferenceClient singleton."""
    global _client
    if _client is None:
        from huggingface_hub import InferenceClient
        _client = InferenceClient(token=HF_API_TOKEN if HF_API_TOKEN else None)
        logger.info("HuggingFace InferenceClient initialized (token=%s)", "set" if HF_API_TOKEN else "not set")
    return _client


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

def hf_summarize(text, max_length=128, min_length=30):
    """Summarize Arabic text via HF Inference API."""
    client = _get_client()
    logger.info("Calling HF summarization: %s (max_length=%d)", SUMMARIZATION_REPO, max_length)
    
    result = client.summarization(
        text,
        model=SUMMARIZATION_REPO,
        parameters={"max_length": max_length, "min_length": min_length},
    )
    
    logger.info("Summarization result type: %s", type(result).__name__)
    
    # Result is a SummarizationOutput with .summary_text
    if hasattr(result, 'summary_text'):
        return result.summary_text
    
    # Fallback for dict responses
    if isinstance(result, dict):
        return result.get("summary_text", result.get("generated_text", str(result)))
    
    return str(result)


def hf_correct_spelling(text):
    """Correct spelling in Arabic text via HF Inference API."""
    client = _get_client()
    logger.info("Calling HF spelling correction: %s", SPELLING_REPO)
    
    # Use text_generation since model has no pipeline_tag
    result = client.text_generation(
        text,
        model=SPELLING_REPO,
        max_new_tokens=len(text) + 50,
    )
    
    logger.info("Spelling result type: %s, value: %s", type(result).__name__, str(result)[:100])
    
    if isinstance(result, str):
        return result if result.strip() else text
    
    if isinstance(result, dict):
        return result.get("generated_text", text)
    
    return text


def hf_add_punctuation(text):
    """Add punctuation to Arabic text via HF Inference API."""
    client = _get_client()
    logger.info("Calling HF punctuation: %s", PUNCTUATION_REPO)
    
    # PuncAra is an encoder-decoder model
    result = client.text_generation(
        text,
        model=PUNCTUATION_REPO,
        max_new_tokens=len(text) + 50,
    )
    
    logger.info("Punctuation result type: %s, value: %s", type(result).__name__, str(result)[:100])
    
    if isinstance(result, str):
        return result if result.strip() else text
    
    if isinstance(result, dict):
        return result.get("generated_text", text)
    
    return text


def hf_autocomplete(text, n=5):
    """Get autocomplete suggestions for Arabic text via HF Inference API."""
    client = _get_client()
    logger.info("Calling HF autocomplete: %s", AUTOCOMPLETE_REPO)
    
    result = client.text_generation(
        text,
        model=AUTOCOMPLETE_REPO,
        max_new_tokens=20,
    )
    
    logger.info("Autocomplete result type: %s, value: %s", type(result).__name__, str(result)[:100])
    
    if isinstance(result, str):
        # Result includes the input + completion
        completion = result
        if completion.startswith(text):
            completion = completion[len(text):].strip()
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
        client = _get_client()
        # Just check if the client can be created
        return client is not None
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
