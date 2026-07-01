# ContextualCorrector — MLM-based contextual validation for spelling corrections
# Adapted from legacy AraSpell ContextualCorrector.
#
# Purpose: After the spelling model produces corrections, this module validates
# each OOV word by masking it and asking BERT what word should go there.
# If BERT's top prediction is very different from the correction, the
# original word is kept (the model hallucinated).
#
# Usage in pipeline: Called AFTER spelling correction, BEFORE grammar.
# Only processes OOV words (never touches IV words).

import logging
import torch
import threading
from collections import OrderedDict
from typing import List, Tuple, Optional, Dict

logger = logging.getLogger(__name__)

# Singleton instance
_instance = None
_loading = False
_lock = threading.RLock()


class ContextualCorrector:
    """MLM-based contextual validation for spelling corrections.
    
    Uses BERT's masked language model to validate spelling corrections.
    For each OOV word in the corrected text:
    1. Masks the word and asks BERT for predictions
    2. If BERT strongly disagrees with the correction, reverts to original
    3. Never touches IV words (they're already correct)
    """

    def __init__(self, model_name: str = 'aubmindlab/bert-base-arabertv02'):
        """Initialize with BERT MLM model."""
        from transformers import AutoTokenizer, AutoModelForMaskedLM

        logger.info(f"[MLM] Loading contextual corrector: {model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForMaskedLM.from_pretrained(model_name)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = self.model.to(self.device)
        self.model.eval()

        # Simple cache for scores
        self._cache: OrderedDict[str, float] = OrderedDict()
        self._cache_max = 5000

        # Vocab for candidate filtering
        self.vocab = self.tokenizer.get_vocab()
        
        logger.info(f"[MLM] Contextual corrector loaded on {self.device}")

    def score_word_in_context(self, text: str, position: int, word: str) -> float:
        """Score how well a word fits in context using BERT MLM.
        
        Args:
            text: Full sentence
            position: Word index (0-based) in the sentence
            word: The word to score
            
        Returns:
            Probability score (0.0 to 1.0) — higher = better fit
        """
        cache_key = f"{hash(text)}|{position}|{word}"
        if cache_key in self._cache:
            self._cache.move_to_end(cache_key)
            return self._cache[cache_key]

        words = text.split()
        if position >= len(words):
            return 0.0

        # Create masked text
        masked_words = words.copy()
        masked_words[position] = self.tokenizer.mask_token
        masked_text = ' '.join(masked_words)

        try:
            inputs = self.tokenizer(
                masked_text, return_tensors='pt',
                padding=True, truncation=True, max_length=128
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                outputs = self.model(**inputs)

            # Find [MASK] token position
            mask_idx = (inputs['input_ids'] == self.tokenizer.mask_token_id).nonzero(as_tuple=True)[1]
            if len(mask_idx) == 0:
                return 0.0

            # Get probability for the target word
            logits = outputs.logits[0, mask_idx[0], :]
            probs = torch.softmax(logits, dim=0)

            word_tokens = self.tokenizer.encode(word, add_special_tokens=False)
            if not word_tokens:
                return 0.0

            # Use first subword token probability only. For multi-subword
            # words, the single [MASK] distribution only predicts the first
            # subword — multiplying unrelated token probs is nonsensical.
            score = probs[word_tokens[0]].item()

        except Exception as e:
            logger.warning(f"[MLM] Score error for '{word}': {e}")
            score = 0.0

        # Cache management
        if len(self._cache) >= self._cache_max:
            for _ in range(self._cache_max // 5):
                self._cache.popitem(last=False)
        self._cache[cache_key] = score

        return score

    def validate_corrections(
        self,
        original_text: str,
        corrected_text: str,
        vocab_manager=None,
        confidence_threshold: float = 0.001,
        min_pred_score: float = 0.12,
        similarity_threshold: float = 0.90,
    ) -> str:
        """Validate spelling corrections using MLM context.
        
        For each word that changed between original and corrected:
        - If the correction is OOV: revert (model hallucinated)
        - If the correction scores very low in context AND the original
          scores much better: revert
        - If BERT has a better suggestion that's similar to original: use it
        
        Args:
            original_text: Text before spelling correction
            corrected_text: Text after spelling correction
            vocab_manager: VocabManager for IV/OOV checks
            confidence_threshold: Min BERT score to keep a word without checking
            min_pred_score: Min BERT score for a replacement candidate
            similarity_threshold: Min similarity (Levenshtein) for replacements
            
        Returns:
            Validated text with hallucinations reverted
        """
        orig_words = original_text.split()
        corr_words = corrected_text.split()
        
        # Only process when word counts match (1:1 mapping)
        if len(orig_words) != len(corr_words):
            return corrected_text

        result_words = corr_words.copy()
        changes_made = 0

        for i, (orig_w, corr_w) in enumerate(zip(orig_words, corr_words)):
            # Skip unchanged words
            if orig_w == corr_w:
                continue

            # Never touch IV words in correction
            if vocab_manager and vocab_manager.is_iv(corr_w):
                continue

            # Score the correction in context
            corr_score = self.score_word_in_context(corrected_text, i, corr_w)

            # If correction has decent BERT confidence, keep it
            if corr_score > confidence_threshold:
                continue

            # Score the original word in its own context (not contaminated by other corrections)
            orig_score = self.score_word_in_context(original_text, i, orig_w)

            # If original scores better, revert
            if orig_score > corr_score * 10 and orig_score > 0.01:
                logger.info(
                    f"[MLM] Reverting hallucination: '{corr_w}'→'{orig_w}' "
                    f"(corr_score={corr_score:.4f}, orig_score={orig_score:.4f})"
                )
                result_words[i] = orig_w
                changes_made += 1
                continue

            # Try BERT's own top predictions as alternatives
            predictions = self._predict_top_k(corrected_text, i, top_k=5)
            
            for pred_word, pred_score in predictions:
                if pred_word == corr_w or pred_word == orig_w:
                    continue

                # Must be IV
                if vocab_manager and not vocab_manager.is_iv(pred_word):
                    continue

                # Must be similar to the original (not a random word)
                similarity = self._similarity(orig_w, pred_word)
                if similarity < similarity_threshold:
                    continue

                # Must have strong BERT confidence
                if pred_score < min_pred_score:
                    continue

                # Must be a big improvement
                if pred_score > corr_score * 50 and pred_score > 0.2:
                    logger.info(
                        f"[MLM] Replacing with BERT prediction: '{corr_w}'→'{pred_word}' "
                        f"(pred_score={pred_score:.4f}, corr_score={corr_score:.4f})"
                    )
                    result_words[i] = pred_word
                    changes_made += 1
                    break

        if changes_made:
            logger.info(f"[MLM] Contextual validation: {changes_made} corrections adjusted")

        return ' '.join(result_words)

    def _predict_top_k(self, text: str, position: int, top_k: int = 5) -> List[Tuple[str, float]]:
        """Predict top-k words for a masked position."""
        words = text.split()
        if position >= len(words):
            return []

        masked_words = words.copy()
        masked_words[position] = self.tokenizer.mask_token
        masked_text = ' '.join(masked_words)

        try:
            inputs = self.tokenizer(
                masked_text, return_tensors='pt',
                padding=True, truncation=True, max_length=128
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model(**inputs)

            mask_idx = (inputs['input_ids'] == self.tokenizer.mask_token_id).nonzero(as_tuple=True)[1]
            if len(mask_idx) == 0:
                return []

            logits = outputs.logits[0, mask_idx[0], :]
            probs = torch.softmax(logits, dim=0)
            top_k_weights, top_k_indices = torch.topk(probs, top_k, sorted=True)

            results = []
            for j in range(top_k):
                token_id = top_k_indices[j].item()
                score = top_k_weights[j].item()
                token = self.tokenizer.decode([token_id]).strip()
                # Skip subword tokens and special tokens
                if not token.startswith("##") and token not in self.tokenizer.all_special_tokens:
                    results.append((token, score))

            return results

        except Exception as e:
            logger.warning(f"[MLM] Prediction error: {e}")
            return []

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Calculate normalized Levenshtein similarity between two strings."""
        if not a or not b:
            return 0.0
        max_len = max(len(a), len(b))
        m, n = len(a), len(b)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[0]
            dp[0] = i
            for j in range(1, n + 1):
                temp = dp[j]
                if a[i-1] == b[j-1]:
                    dp[j] = prev
                else:
                    dp[j] = 1 + min(prev, dp[j], dp[j-1])
                prev = temp
        dist = dp[n]
        return 1.0 - (dist / max_len)


def get_contextual_corrector() -> Optional[ContextualCorrector]:
    """Get or create the singleton ContextualCorrector instance.

    Returns None if loading fails (graceful degradation).
    """
    global _instance, _loading

    if _instance is not None:
        return _instance

    with _lock:
        if _instance is not None:
            return _instance

        if _loading:
            return None  # Prevent recursive loading

        _loading = True
        try:
            _instance = ContextualCorrector()
            return _instance
        except Exception as e:
            logger.warning(f"[MLM] Failed to load contextual corrector: {e}")
            return None
        finally:
            _loading = False


def is_loaded() -> bool:
    """Check if the contextual corrector is loaded."""
    return _instance is not None
