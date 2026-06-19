"""
Grammar Service — Lazy-loaded Arabic grammar correction.

Pipeline:
  1. Gradio Client → mohammedahmedezz2004/bayan_arabic_grammarly_correction (seq2seq model)
  2. ArabicGrammarGuard (camel-tools rule-based post-processing)

Fallback (when Gradio space unavailable / network error):
  - Rules-only mode: applies ArabicGrammarGuard rules directly to input text
  - This ensures grammar still works on HF Spaces free tier (no outbound DNS)

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
      1. Gradio model inference (seq2seq grammar correction) — optional
      2. Rule-based post-processing (camel-tools ArabicGrammarGuard) — always runs

    If Gradio client is None (unavailable), runs rules-only mode.
    """

    def __init__(self, client, rules):
        self.client = client      # may be None in rules-only mode
        self.rules = rules

    def correct(self, text: str) -> str:
        """
        Run grammar correction on text.
        Returns corrected text, or original text if correction fails.
        """
        if not text or not text.strip():
            return text

        model_output = text  # default: pass-through if no model

        # 1. Model inference via Gradio (if client available)
        if self.client is not None:
            try:
                result = self.client.predict(
                    text=text,
                    api_name="/correct_grammar"
                )
                if result and result.strip():
                    model_output = result
                    logger.info(
                        f"Grammar model output: '{model_output[:80]}' "
                        f"(input: '{text[:80]}')"
                    )
                else:
                    logger.warning("Grammar model returned empty output, using rules-only")
            except Exception as e:
                logger.warning(f"Grammar Gradio call failed ({e}), falling back to rules-only")
                model_output = text  # rules will still run on original

        # 2. Rule-based post-processing (always runs)
        try:
            corrected = self.rules.process(text, model_output)
            logger.info(f"Grammar rules output: '{corrected[:80]}'")
            return corrected
        except Exception as e:
            logger.error(f"Grammar rules failed: {e}")
            return model_output  # return model output or original


def get_grammar_model():
    """
    Lazy-load the grammar model on first call.
    Returns a GrammarChecker (always succeeds — falls back to rules-only).
    """
    global _grammar_checker, _load_error

    if _grammar_checker is not None:
        return _grammar_checker

    try:
        t0 = time.time()
        logger.info("Loading Grammar model (lazy init)...")

        # 1. Load rule-based post-processor (camel-tools) — required
        logger.info("Loading ArabicGrammarGuard (camel-tools MLE disambiguator)...")
        from nlp.grammar.grammar_rules import ArabicGrammarGuard
        rules = ArabicGrammarGuard()
        logger.info("ArabicGrammarGuard loaded")

        # 2. Try connecting to Gradio Space — optional, graceful failure
        client = None
        try:
            logger.info(f"Connecting to Gradio Space: {GRADIO_SPACE}")
            from gradio_client import Client
            # Short timeout so we don't block startup
            client = Client(GRADIO_SPACE, verbose=False)
            logger.info("Gradio Client connected successfully")
        except Exception as e:
            logger.warning(
                f"Gradio client unavailable ({e}). "
                f"Grammar will use rules-only mode (no seq2seq model)."
            )
            client = None  # rules-only fallback

        # 3. Create GrammarChecker instance
        _grammar_checker = GrammarChecker(client, rules)

        elapsed = time.time() - t0
        mode = "Gradio + rules" if client else "rules-only"
        logger.info(f"Grammar service ready in {elapsed:.1f}s (mode: {mode})")
        return _grammar_checker

    except Exception as e:
        import traceback
        _load_error = str(e)
        logger.error(f"Failed to load grammar service: {e}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Grammar service load failed: {e}")


def reset_load_error() -> None:
    """Reset load error to allow retry on next call."""
    global _grammar_checker, _load_error
    _grammar_checker = None
    _load_error = None


def is_loaded() -> bool:
    """Check if the grammar model is loaded."""
    return _grammar_checker is not None


def get_load_error() -> str:
    """Return the last load error, or empty string."""
    return _load_error or ""
