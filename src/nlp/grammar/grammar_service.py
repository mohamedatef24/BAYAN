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
    
    Transient errors (rate limiting, network timeouts) are NOT cached —
    the next request will retry loading. Only permanent failures are cached.
    
    The Gradio Client connection retries up to 3 times with exponential backoff
    to handle sleeping Spaces and rate-limit responses.
    """
    global _grammar_checker, _load_error

    if _grammar_checker is not None:
        return _grammar_checker

    if _load_error is not None:
        raise RuntimeError(f"Grammar model previously failed to load: {_load_error}")

    try:
        t0 = time.time()
        logger.info("Loading Grammar model (lazy init)...")

        # 1. Initialize Gradio Client — with retry for rate limiting / sleeping Spaces
        from gradio_client import Client
        client = None
        max_retries = 3
        last_err = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Connecting to Gradio Space: {GRADIO_SPACE} (attempt {attempt}/{max_retries})")
                client = Client(GRADIO_SPACE)
                logger.info("Gradio Client connected")
                break
            except Exception as conn_err:
                last_err = conn_err
                err_msg = str(conn_err).lower()
                is_retryable = any(kw in err_msg for kw in [
                    'too many requests', 'rate limit', '429',
                    'timeout', 'connection', 'sleeping'
                ])
                if is_retryable and attempt < max_retries:
                    wait = 2 ** attempt  # 2s, 4s, 8s
                    logger.warning(
                        f"Gradio connection attempt {attempt} failed ({conn_err}). "
                        f"Retrying in {wait}s..."
                    )
                    time.sleep(wait)
                else:
                    raise  # Not retryable or last attempt — bubble up

        if client is None:
            raise RuntimeError(f"Gradio connection failed after {max_retries} attempts: {last_err}")

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
        error_msg = str(e)
        logger.error(f"Failed to load grammar model: {e}")
        logger.error(traceback.format_exc())

        # Transient errors (rate limiting, network) should NOT be cached —
        # allow retry on next request
        transient_keywords = ['Too many requests', 'rate limit', 'timeout',
                              'ConnectionError', 'ConnectTimeout', 'ReadTimeout',
                              '429', 'sleeping']
        is_transient = any(kw.lower() in error_msg.lower() for kw in transient_keywords)

        if is_transient:
            logger.warning(f"Grammar load error is TRANSIENT — will retry on next request: {error_msg}")
            # Do NOT set _load_error — next call will retry
        else:
            _load_error = error_msg  # Cache permanent failures only

        raise RuntimeError(f"Grammar model load failed: {e}")


def is_loaded() -> bool:
    """Check if the grammar model is loaded."""
    return _grammar_checker is not None


def get_load_error() -> str:
    """Return the last load error, or empty string."""
    return _load_error or ""
