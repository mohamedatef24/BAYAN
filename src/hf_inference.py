"""
HuggingFace Inference API client for Bayan models.

IMPORTANT: HF Spaces free tier has NO outbound DNS resolution.
Neither urllib, requests, httpx, nor InferenceClient can reach
external APIs from inside the container.

This module provides graceful fallbacks:
- Summarization: uses local model (loaded in model_loader.py / app.py)
- Spelling/Punctuation/Grammar/Autocomplete: return input unchanged (graceful degradation)
  These features require either a paid HF Space tier or local model files.
"""

import os
import logging
import time

logger = logging.getLogger(__name__)

HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")

# Repository IDs (kept for reference)
SUMMARIZATION_REPO = os.environ.get("SUMMARIZATION_REPO_ID", "bayan10/summarization-model")
SPELLING_REPO = os.environ.get("SPELLING_REPO_ID", "bayan10/AraSpell-Model")
PUNCTUATION_REPO = os.environ.get("PUNCTUATION_REPO_ID", "bayan10/PuncAra-v1")
AUTOCOMPLETE_REPO = os.environ.get("AUTOCOMPLETE_REPO_ID", "bayan10/AutoComplete")


def hf_summarize(text, max_length=128, min_length=30):
    """
    Summarize Arabic text.
    NOTE: In HF API mode, this should NOT be called — the local
    summarization model is used instead (see app.py load_models).
    This is a fallback that returns the first few sentences.
    """
    logger.warning("hf_summarize called but no external API available. Using extractive fallback.")
    # Simple extractive fallback: first N words
    words = text.split()
    target = max(10, max_length // 4)
    return " ".join(words[:target]).strip()


def hf_correct_spelling(text):
    """
    Correct spelling — graceful degradation (returns input unchanged).
    Spelling correction requires local model files or a paid tier with network access.
    """
    logger.info("Spelling correction unavailable (no network). Returning original text.")
    return text


def hf_add_punctuation(text):
    """
    Add punctuation — graceful degradation (returns input unchanged).
    Punctuation requires local model files or a paid tier with network access.
    """
    logger.info("Punctuation unavailable (no network). Returning original text.")
    return text


def hf_autocomplete(text, n=5):
    """
    Autocomplete — graceful degradation (returns empty list).
    Autocomplete requires local model files or a paid tier with network access.
    """
    logger.info("Autocomplete unavailable (no network). Returning empty.")
    return []


def check_hf_api_available():
    """HF Inference API is NOT available on free tier (no outbound DNS)."""
    return False


def debug_test_all_models():
    """Return status of all models."""
    return {
        "_info": {
            "note": "HF Spaces free tier has NO outbound DNS. External API calls are impossible.",
            "recommendation": "Use local model loading for summarization. Other models require local files or paid tier.",
        },
        "summarization": {
            "status": "fallback",
            "note": "Using local model via model_loader.py (loaded from HF Hub at build time)",
        },
        "spelling": {
            "status": "unavailable",
            "note": "Returns input unchanged. Requires local model files.",
        },
        "punctuation": {
            "status": "unavailable",
            "note": "Returns input unchanged. Requires local model files.",
        },
        "autocomplete": {
            "status": "unavailable",
            "note": "Returns empty. Requires local model files.",
        },
    }
