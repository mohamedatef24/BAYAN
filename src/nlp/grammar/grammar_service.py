"""
Grammar Service — Lazy-loaded Arabic grammar correction.

Uses:
  1. Gradio Client → mohammedahmedezz2004/bayan_arabic_grammarly_correction (seq2seq model)
  2. ArabicGrammarGuard (camel-tools rule-based post-processing)

Model + rules loaded on first request and kept in memory.
"""

import logging
import time

logger = logging.getLogger(__name__)

# ── Lazy-loaded singletons ──
_grammar_checker = None
_load_error = None

GRADIO_SPACE = "mohammedahmedezz2004/bayan_arabic_grammarly_correction"


class GrammarChecker:
    """
    Grammar correction pipeline:
      1. Gradio model inference (seq2seq grammar correction)
      2. Rule-based post-processing (camel-tools ArabicGrammarGuard)
    """

    def __init__(self, client, rules):
        self.client = client
        self.rules = rules

    def correct(self, text: str) -> str:
        """
        Run grammar correction on text.
        Returns corrected text, or original text if correction fails.
        """
        if not text or not text.strip():
            return text

        try:
            # 1. Model inference via Gradio
            model_output = self.client.predict(
                text=text,
                api_name="/correct_grammar"
            )
            logger.info(f"Grammar model output: '{model_output[:80]}...' (input: '{text[:80]}...')")

            if not model_output or not model_output.strip():
                logger.warning("Grammar model returned empty output, returning original")
                return text

            # 2. Rule-based post-processing
            corrected = self.rules.process(text, model_output)
            logger.info(f"Grammar rules output: '{corrected[:80]}...'")

            return corrected

        except Exception as e:
            logger.error(f"Grammar correction failed: {e}")
            # Graceful degradation: return original text
            return text


def get_grammar_model():
    """
    Lazy-load the grammar model on first call.
    Returns the GrammarChecker instance, or raises RuntimeError if loading fails.
    """
    global _grammar_checker, _load_error

    if _grammar_checker is not None:
        return _grammar_checker

    if _load_error is not None:
        raise RuntimeError(f"Grammar model previously failed to load: {_load_error}")

    try:
        t0 = time.time()
        logger.info("Loading Grammar model (lazy init)...")

        # 1. Initialize Gradio Client
        logger.info(f"Connecting to Gradio Space: {GRADIO_SPACE}")
        from gradio_client import Client
        client = Client(GRADIO_SPACE)
        logger.info("Gradio Client connected")

        # 2. Initialize rule-based post-processor (camel-tools)
        logger.info("Loading ArabicGrammarGuard (camel-tools MLE disambiguator)...")
        from nlp.grammar.grammar_rules import ArabicGrammarGuard
        rules = ArabicGrammarGuard()
        logger.info("ArabicGrammarGuard loaded")

        # 3. Create GrammarChecker instance
        _grammar_checker = GrammarChecker(client, rules)

        elapsed = time.time() - t0
        logger.info(f"Grammar model ready in {elapsed:.1f}s")
        return _grammar_checker

    except Exception as e:
        import traceback
        _load_error = str(e)
        logger.error(f"Failed to load grammar model: {e}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Grammar model load failed: {e}")


def is_loaded() -> bool:
    """Check if the grammar model is loaded."""
    return _grammar_checker is not None


def get_load_error() -> str:
    """Return the last load error, or empty string."""
    return _load_error or ""
