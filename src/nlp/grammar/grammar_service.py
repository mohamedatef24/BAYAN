"""
Grammar Service — Lazy-loaded Arabic grammar correction.

Uses:
  1. Gradio Client → mohammedahmedezz2004/bayan_arabic_grammarly_correction (seq2seq model)
  2. ArabicGrammarGuard (camel-tools rule-based post-processing)

Model + rules loaded on first request and kept in memory.
"""

import logging
import time
import threading

logger = logging.getLogger(__name__)

# ── Lazy-loaded singletons ──
_grammar_checker = None
_load_error = None
_lock = threading.Lock()

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

    @staticmethod
    def _preserve_punctuation(original: str, corrected: str) -> str:
        """
        Preserve punctuation from the original text if the grammar model removed it.
        """
        PUNCT_CHARS = set('.,;:!?،؛؟!.:«»"\'()-–—…')
        orig_words = original.split()
        corr_words = corrected.split()
        
        if not orig_words or not corr_words:
            return corrected

        # If word count matches exactly, we can restore punctuation word-by-word
        if len(orig_words) == len(corr_words):
            result = []
            for o_w, c_w in zip(orig_words, corr_words):
                c_has_punct = any(ch in PUNCT_CHARS for ch in c_w)
                o_has_punct = any(ch in PUNCT_CHARS for ch in o_w)
                if o_has_punct and not c_has_punct:
                    prefix = ""
                    for ch in o_w:
                        if ch in PUNCT_CHARS: prefix += ch
                        else: break
                    suffix = ""
                    for ch in reversed(o_w):
                        if ch in PUNCT_CHARS: suffix = ch + suffix
                        else: break
                    result.append(prefix + c_w + suffix)
                else:
                    result.append(c_w)
            return " ".join(result)
            
        # Global prefix/suffix if lengths differ
        prefix = ""
        for ch in original:
            if ch in PUNCT_CHARS: prefix += ch
            elif not ch.isspace(): break
            
        suffix = ""
        for ch in reversed(original):
            if ch in PUNCT_CHARS: suffix = ch + suffix
            elif not ch.isspace(): break
            
        c_stripped = corrected.strip('.,;:!?،؛؟!.:«»"\'()-–—… \t\n')
        
        # Only add prefix/suffix if the corrected text doesn't already have them
        if prefix and c_stripped.startswith(prefix):
            prefix = ""
        if suffix and c_stripped.endswith(suffix):
            suffix = ""
            
        return prefix + c_stripped + suffix


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
            _mo_display = model_output[:80] + ('...' if len(model_output) > 80 else '')
            _ti_display = text[:80] + ('...' if len(text) > 80 else '')
            logger.info(f"Grammar model output: '{_mo_display}' (input: '{_ti_display}')")

            if not model_output or not model_output.strip():
                logger.warning("Grammar model returned empty output, returning original")
                return text

            # 2. Rule-based post-processing
            corrected = self.rules.process(text, model_output)
            
            # 3. Preserve original punctuation if the model stripped it
            corrected = self._preserve_punctuation(text, corrected)
            
            _cr_display = corrected[:80] + ('...' if len(corrected) > 80 else '')
            logger.info(f"Grammar rules output: '{_cr_display}'")

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

    with _lock:
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
