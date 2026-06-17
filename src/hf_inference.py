"""
HuggingFace Inference API client for Bayan models.

Uses huggingface_hub.InferenceClient which routes through HF's internal
network when running inside HF Spaces (bypasses external DNS).

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

logger = logging.getLogger(__name__)

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")

# Lazy-initialized client
_client = None


def _get_client():
    """Get or create the InferenceClient singleton."""
    global _client
    if _client is None:
        from huggingface_hub import InferenceClient
        _client = InferenceClient(token=HF_API_TOKEN if HF_API_TOKEN else None)
        logger.info("InferenceClient initialized (token=%s)", "set" if HF_API_TOKEN else "not set")
    return _client


# ============================================================
# Repository IDs
# ============================================================

SUMMARIZATION_REPO = os.environ.get("SUMMARIZATION_REPO_ID", "bayan10/summarization-model")
SPELLING_REPO = os.environ.get("SPELLING_REPO_ID", "bayan10/AraSpell-Model")
PUNCTUATION_REPO = os.environ.get("PUNCTUATION_REPO_ID", "bayan10/PuncAra-v1")
AUTOCOMPLETE_REPO = os.environ.get("AUTOCOMPLETE_REPO_ID", "bayan10/AutoComplete")


# ============================================================
# Model-specific wrappers using InferenceClient typed methods
# ============================================================

def hf_summarize(text, max_length=128, min_length=30):
    """Summarize Arabic text via HF Inference API."""
    client = _get_client()
    logger.info("Calling summarization: %s", SUMMARIZATION_REPO)

    result = client.summarization(text, model=SUMMARIZATION_REPO)

    logger.info("Summarization result: %s — %s", type(result).__name__, str(result)[:150])

    # SummarizationOutput has .summary_text
    if hasattr(result, "summary_text"):
        return result.summary_text
    if isinstance(result, dict):
        return result.get("summary_text", result.get("generated_text", str(result)))
    return str(result)


def hf_correct_spelling(text):
    """Correct spelling in Arabic text via HF Inference API."""
    client = _get_client()
    logger.info("Calling spelling: %s", SPELLING_REPO)

    # Try text2text_generation first (for seq2seq models), fall back to text_generation
    try:
        result = client.text2text_generation(text, model=SPELLING_REPO)
        logger.info("Spelling result (t2t): %s — %s", type(result).__name__, str(result)[:150])
        if hasattr(result, "generated_text"):
            return result.generated_text
        if isinstance(result, str):
            return result if result.strip() else text
        if isinstance(result, dict):
            return result.get("generated_text", text)
        return text
    except Exception as e1:
        logger.warning("text2text_generation failed for spelling: %s", repr(e1)[:200])
        try:
            result = client.text_generation(text, model=SPELLING_REPO, max_new_tokens=len(text) + 50)
            logger.info("Spelling result (tg): %s — %s", type(result).__name__, str(result)[:150])
            if isinstance(result, str):
                return result if result.strip() else text
            return text
        except Exception as e2:
            logger.error("text_generation also failed for spelling: %s", repr(e2)[:200])
            raise


def hf_add_punctuation(text):
    """Add punctuation to Arabic text via HF Inference API."""
    client = _get_client()
    logger.info("Calling punctuation: %s", PUNCTUATION_REPO)

    try:
        result = client.text2text_generation(text, model=PUNCTUATION_REPO)
        logger.info("Punctuation result (t2t): %s — %s", type(result).__name__, str(result)[:150])
        if hasattr(result, "generated_text"):
            return result.generated_text
        if isinstance(result, str):
            return result if result.strip() else text
        if isinstance(result, dict):
            return result.get("generated_text", text)
        return text
    except Exception as e1:
        logger.warning("text2text_generation failed for punctuation: %s", repr(e1)[:200])
        try:
            result = client.text_generation(text, model=PUNCTUATION_REPO, max_new_tokens=len(text) + 50)
            logger.info("Punctuation result (tg): %s — %s", type(result).__name__, str(result)[:150])
            if isinstance(result, str):
                return result if result.strip() else text
            return text
        except Exception as e2:
            logger.error("text_generation also failed for punctuation: %s", repr(e2)[:200])
            raise


def hf_autocomplete(text, n=5):
    """Get autocomplete suggestions for Arabic text via HF Inference API."""
    client = _get_client()
    logger.info("Calling autocomplete: %s", AUTOCOMPLETE_REPO)

    result = client.text_generation(text, model=AUTOCOMPLETE_REPO, max_new_tokens=20)

    logger.info("Autocomplete result: %s — %s", type(result).__name__, str(result)[:150])

    if isinstance(result, str):
        completion = result[len(text):].strip() if result.startswith(text) else result
        return [completion] if completion else [text]

    return [text]


def check_hf_api_available():
    """Quick check if HF Inference API is reachable."""
    try:
        client = _get_client()
        return client is not None
    except Exception:
        return False


def debug_test_all_models():
    """
    Test all HF models and return results dict.
    Also includes diagnostic info about InferenceClient internals.
    """
    results = {}
    test_text = "هذا نص تجريبي للاختبار"
    long_text = (test_text + " ") * 5

    # Diagnostic info
    try:
        client = _get_client()
        diag = {
            "client_type": type(client).__name__,
            "api_url": getattr(client, "api_url", "N/A"),
            "base_url": getattr(client, "base_url", "N/A"),
            "model": getattr(client, "model", "N/A"),
        }
        # Check available methods
        diag["has_post"] = hasattr(client, "post")
        diag["has_text2text"] = hasattr(client, "text2text_generation")
        diag["has_summarization"] = hasattr(client, "summarization")
        diag["has_text_generation"] = hasattr(client, "text_generation")
    except Exception as e:
        diag = {"error": repr(e)[:200]}

    results["_diagnostics"] = diag

    # Test env vars
    results["_env"] = {
        "HF_INFERENCE_ENDPOINT": os.environ.get("HF_INFERENCE_ENDPOINT", "NOT SET"),
        "HF_API_URL": os.environ.get("HF_API_URL", "NOT SET"),
        "SPACE_ID": os.environ.get("SPACE_ID", "NOT SET"),
    }

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
