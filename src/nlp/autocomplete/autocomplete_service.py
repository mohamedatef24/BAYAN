"""
AutoComplete Service — Hybrid bigram + GPT-2 Arabic autocomplete.

COMPLETELY INDEPENDENT from the correction pipeline.
This module has ZERO interaction with:
- /api/analyze
- StageLockManager / OffsetMapper / ClaimedRanges
- OverlapResolver / PatchSet / CorrectionPatch
- Highlight rendering

Architecture:
    User types → debounce → POST /api/autocomplete
    → HybridAutoComplete.predict(context)
    → Bigram lookup + GPT-2 scoring
    → Ranked suggestions returned to frontend
"""

import os
import time
import pickle
import logging
import threading
from functools import lru_cache

import torch
from huggingface_hub import hf_hub_download

logger = logging.getLogger(__name__)

# ─── Singleton ────────────────────────────────────────────────────────────────
_instance = None
_lock = threading.Lock()


def get_autocomplete_model():
    """Lazy-loaded singleton — returns the cached HybridAutoComplete instance."""
    global _instance
    if _instance is not None:
        return _instance

    with _lock:
        if _instance is not None:
            return _instance
        _instance = HybridAutoComplete()
    return _instance


# ─── Cache key helper ─────────────────────────────────────────────────────────
def _context_key(context: str) -> str:
    """Use last 5 words for cache key — preserves enough context for GPT-2 awareness."""
    words = context.strip().split()
    return " ".join(words[-5:]) if words else ""


# ─── Main Service ─────────────────────────────────────────────────────────────
class HybridAutoComplete:
    """
    Hybrid Arabic autocomplete:
    1. Statistical (bigram) — fast, always available
    2. Neural (GPT-2) — contextual, optional (may OOM on free tier)
    3. Hybrid scoring: alpha * stat + (1-alpha) * neural
    """

    BIGRAM_REPO = "bayan10/AutoComplete"
    BIGRAM_FILE = "bigram_model_v4.pkl"
    GPT2_MODEL = "aubmindlab/aragpt2-base"

    def __init__(self):
        t0 = time.time()
        logger.info("Loading AutoComplete model (lazy init)...")

        self.unigrams = None
        self.bigrams = None
        self.gpt2_tokenizer = None
        self.gpt2_model = None
        self.device = "cpu"
        self.alpha = 0.6  # Weight: 60% bigram, 40% GPT-2
        self._cache = {}
        self._cache_max = 256

        # 1. Load bigram (required — small file)
        self._load_bigram()

        # 2. Load GPT-2 (optional — large model, may OOM)
        self._load_gpt2()

        elapsed = time.time() - t0
        mode = "hybrid" if self.gpt2_model else "bigram-only"
        logger.info(f"AutoComplete ready in {elapsed:.1f}s (mode: {mode})")

    def _load_bigram(self):
        """Load bigram model from HuggingFace Hub."""
        try:
            path = hf_hub_download(
                repo_id=self.BIGRAM_REPO,
                filename=self.BIGRAM_FILE,
            )
            with open(path, "rb") as f:
                data = pickle.load(f)
            self.unigrams = data["unigrams"]
            self.bigrams = data["bigrams"]
            logger.info(
                f"Bigram model loaded: {len(self.unigrams)} unigrams, "
                f"{len(self.bigrams)} bigram contexts"
            )
        except Exception as e:
            logger.error(f"Failed to load bigram model: {e}")
            self.unigrams = {}
            self.bigrams = {}

    def _load_gpt2(self):
        """Load GPT-2 model with OOM fallback."""
        try:
            from transformers import GPT2LMHeadModel, GPT2Tokenizer

            logger.info(f"Loading GPT-2 tokenizer: {self.GPT2_MODEL}")
            self.gpt2_tokenizer = GPT2Tokenizer.from_pretrained(self.GPT2_MODEL)
            self.gpt2_tokenizer.pad_token = self.gpt2_tokenizer.eos_token

            logger.info(f"Loading GPT-2 model: {self.GPT2_MODEL}")
            self.gpt2_model = GPT2LMHeadModel.from_pretrained(self.GPT2_MODEL)
            self.gpt2_model.config.pad_token_id = self.gpt2_tokenizer.eos_token_id
            self.gpt2_model.eval()

            logger.info("GPT-2 loaded successfully (hybrid mode enabled)")

        except (torch.cuda.OutOfMemoryError, MemoryError, RuntimeError) as e:
            logger.warning(f"GPT-2 OOM — falling back to bigram-only mode: {e}")
            self.gpt2_tokenizer = None
            self.gpt2_model = None
        except Exception as e:
            logger.warning(f"GPT-2 load failed — bigram-only mode: {e}")
            self.gpt2_tokenizer = None
            self.gpt2_model = None

    # ─── Prediction ───────────────────────────────────────────────────────

    def predict(self, context: str, n: int = 5) -> list:
        """
        Get top-N autocomplete suggestions for the given context.

        Args:
            context: Text before the cursor (last ~200 chars)
            n: Number of suggestions to return

        Returns:
            List of suggestion strings (ranked by score)
        """
        if not context or not context.strip():
            return []

        context = context.strip()

        # Check cache
        cache_key = _context_key(context)
        if cache_key in self._cache:
            return self._cache[cache_key][:n]

        try:
            if self.gpt2_model is not None:
                results = self._hybrid_predict(context, n)
            else:
                results = self._bigram_predict(context, n)

            # Cache the result
            if len(self._cache) >= self._cache_max:
                # Evict oldest entries (simple FIFO)
                keys = list(self._cache.keys())
                for k in keys[:len(keys) // 2]:
                    del self._cache[k]
            self._cache[cache_key] = results

            return results[:n]

        except Exception as e:
            logger.error(f"AutoComplete prediction error: {e}")
            return []

    def _bigram_predict(self, context: str, n: int = 5) -> list:
        """Statistical-only prediction using bigram model."""
        from .autocomplete_rules import merge_similar_predictions, filter_suggestions

        tokens = context.strip().split()
        if not tokens:
            return []

        last_word = tokens[-1]
        candidates = []

        # Try bigram lookup
        if last_word in self.bigrams:
            for w, c in self.bigrams[last_word].items():
                if len(w) < 2 or w == last_word:
                    continue
                candidates.append((w, c))

        # Fallback to unigram if no bigram matches
        if not candidates:
            for w, c in self.unigrams.items():
                if len(w) < 2:
                    continue
                candidates.append((w, c))

        if not candidates:
            return []

        total = sum(c for _, c in candidates)
        if total == 0:
            return []

        preds = [(w, c / total) for w, c in candidates]
        preds.sort(key=lambda x: x[1], reverse=True)
        preds = merge_similar_predictions(preds, top_k=n * 3)
        preds = filter_suggestions(preds)

        return [w for w, _ in preds[:n]]

    def _hybrid_predict(self, context: str, n: int = 5) -> list:
        """Hybrid prediction: bigram + GPT-2 scoring.
        
        GPT-2 receives the FULL sentence as context for true context awareness.
        Bigram provides frequency-based candidates from the last word.
        GPT-2's own top predictions are ADDED as candidates so contextually
        appropriate words that bigram doesn't know about can still appear.
        """
        from .autocomplete_rules import merge_similar_predictions, filter_suggestions

        tokens = context.strip().split()
        if not tokens:
            return []

        last_word = tokens[-1]

        # 1. Get bigram candidates (frequency-based, last word only)
        stat_candidates = []
        if last_word in self.bigrams:
            for w, c in self.bigrams[last_word].items():
                if len(w) < 2 or w == last_word:
                    continue
                stat_candidates.append((w, c))

        # 2. Get GPT-2 next-token probabilities using FULL context
        #    GPT-2 sees the entire sentence, not just the last word
        gpt2_probs = self._gpt2_next_token_probs(context, top_k=50)

        # 3. If no bigram candidates, use GPT-2 predictions directly
        if not stat_candidates:
            if gpt2_probs:
                # Use GPT-2's own contextual predictions
                gpt2_preds = sorted(gpt2_probs.items(), key=lambda x: x[1], reverse=True)
                gpt2_preds = filter_suggestions(gpt2_preds)
                return [w for w, _ in gpt2_preds[:n]]
            return self._bigram_predict(context, n)

        total = sum(c for _, c in stat_candidates)
        if total == 0:
            if gpt2_probs:
                gpt2_preds = sorted(gpt2_probs.items(), key=lambda x: x[1], reverse=True)
                gpt2_preds = filter_suggestions(gpt2_preds)
                return [w for w, _ in gpt2_preds[:n]]
            return self._bigram_predict(context, n)

        stat_preds = [(w, c / total) for w, c in stat_candidates]
        stat_preds.sort(key=lambda x: x[1], reverse=True)
        stat_preds = merge_similar_predictions(stat_preds, top_k=20)

        # 4. Hybrid scoring: combine bigram frequency with GPT-2 context score
        results = []
        seen_words = set()
        for w, stat_p in stat_preds:
            neural_p = gpt2_probs.get(w, 1e-8)
            score = self.alpha * stat_p + (1 - self.alpha) * neural_p
            results.append((w, score))
            seen_words.add(w)

        # 5. ADD GPT-2's own top contextual predictions as bonus candidates
        #    These are words GPT-2 thinks fit the context but bigram doesn't know
        for w, neural_p in sorted(gpt2_probs.items(), key=lambda x: x[1], reverse=True)[:10]:
            if w not in seen_words and len(w) >= 2:
                # Give these a lower alpha since they have no bigram backing
                score = 0.3 * neural_p  # Lower weight, but still contextual
                results.append((w, score))
                seen_words.add(w)

        results.sort(key=lambda x: x[1], reverse=True)
        results = filter_suggestions(results)

        return [w for w, _ in results[:n]]

    def _gpt2_next_token_probs(self, prefix: str, top_k: int = 50) -> dict:
        """Get GPT-2 next-token probability distribution."""
        if self.gpt2_model is None or self.gpt2_tokenizer is None:
            return {}

        try:
            inputs = self.gpt2_tokenizer(
                prefix,
                return_tensors="pt",
                truncation=True,
                max_length=512,  # Shorter than 1024 for speed
            )

            with torch.no_grad():
                outputs = self.gpt2_model(**inputs)
                logits = outputs.logits[0, -1]

            probs = torch.softmax(logits, dim=-1)
            top_probs, top_ids = torch.topk(probs, top_k)

            prob_dict = {}
            for idx, prob in zip(top_ids, top_probs):
                word = self.gpt2_tokenizer.decode([idx]).strip()
                if word and len(word) >= 2:
                    prob_dict[word] = prob.item()

            return prob_dict

        except Exception as e:
            logger.warning(f"GPT-2 scoring failed: {e}")
            return {}

    # ─── Health ───────────────────────────────────────────────────────────

    def is_ready(self) -> bool:
        """Returns True if at least the bigram model is loaded."""
        return bool(self.unigrams)

    def get_mode(self) -> str:
        """Returns 'hybrid', 'bigram-only', or 'unavailable'."""
        if self.gpt2_model and self.unigrams:
            return "hybrid"
        elif self.unigrams:
            return "bigram-only"
        return "unavailable"
