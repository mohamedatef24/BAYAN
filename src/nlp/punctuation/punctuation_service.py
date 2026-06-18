"""
Punctuation Service — Lazy-loaded Arabic punctuation restoration.

Uses:
  1. bayan10/PuncAra-v1 (EncoderDecoderModel — local, seq2seq)
  2. Rule-based pre/post-processing from punctuation_rules.py

Model loaded on first request and kept in memory.
"""

import logging
import time
import torch
import re

logger = logging.getLogger(__name__)

# ── Lazy-loaded singletons ──
_punctuation_checker = None
_load_error = None

HF_REPO_ID = "bayan10/PuncAra-v1"


class PunctuationChecker:
    """
    Arabic punctuation restoration pipeline:
      1. Preprocessing (remove diacritics)
      2. Model inference (chunked, windowed — 50 words/chunk)
      3. Postprocessing (typographic cleanup)
    """

    def __init__(self, model, tokenizer, device):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device

    def _predict_chunk(self, text_chunk: str) -> str:
        """Run model inference on a single chunk (max 128 tokens)."""
        from nlp.punctuation.punctuation_rules import arabic_preprocessing

        text_chunk = arabic_preprocessing(text_chunk)

        inputs = self.tokenizer(
            text_chunk, return_tensors="pt",
            padding=True, truncation=True, max_length=128
        ).to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                inputs.input_ids,
                attention_mask=inputs.attention_mask,
                decoder_start_token_id=self.tokenizer.cls_token_id,
                bos_token_id=self.tokenizer.cls_token_id,
                eos_token_id=self.tokenizer.sep_token_id,
                pad_token_id=self.tokenizer.pad_token_id,
                max_length=128,
                num_beams=3,
                repetition_penalty=1.2,
                length_penalty=1.0,
                early_stopping=True,
                do_sample=False
            )

        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def _fix_punctuation(self, text: str) -> str:
        """Process a paragraph using non-overlapping window chunking."""
        words = text.split()
        total_words = len(words)
        window_size = 50
        stride = 50

        if total_words <= window_size:
            return self._predict_chunk(text)

        segments_output = []
        for i in range(0, total_words, stride):
            chunk_words = words[i: i + window_size]
            chunk_text = " ".join(chunk_words)
            if not chunk_text.strip():
                continue

            processed_segment = self._predict_chunk(chunk_text).strip()

            # Remove trailing punctuation from non-last segments (context continues)
            is_last_segment = (i + window_size) >= total_words
            if not is_last_segment:
                punctuation_marks = ".?!،؛:؟!"
                if processed_segment and processed_segment[-1] in punctuation_marks:
                    processed_segment = processed_segment[:-1]

            segments_output.append(processed_segment)

        result = " ".join(segments_output)
        result = re.sub(r'\s+', ' ', result).strip()
        return result

    def correct(self, text: str) -> str:
        """
        Run full punctuation restoration on text.
        Handles multi-paragraph documents.
        Returns punctuated text, or original text on failure.
        """
        if not text or not text.strip():
            return text

        try:
            from nlp.punctuation.punctuation_rules import arabic_postprocessing

            # Split into paragraphs
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
            processed_paragraphs = []

            for paragraph in paragraphs:
                punctuated = self._fix_punctuation(paragraph)
                cleaned = arabic_postprocessing(punctuated)
                processed_paragraphs.append(cleaned)

            result = "\n\n".join(processed_paragraphs)
            logger.info(f"Punctuation output: '{result[:80]}...' (input: '{text[:80]}...')")
            return result

        except Exception as e:
            logger.error(f"Punctuation correction failed: {e}")
            return text


def get_punctuation_model():
    """
    Lazy-load the punctuation model on first call.
    Returns the PunctuationChecker instance, or raises RuntimeError if loading fails.
    """
    global _punctuation_checker, _load_error

    if _punctuation_checker is not None:
        return _punctuation_checker

    if _load_error is not None:
        raise RuntimeError(f"Punctuation model previously failed to load: {_load_error}")

    try:
        t0 = time.time()
        logger.info("Loading PuncAra-v1 punctuation model (lazy init)...")

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Punctuation model device: {device}")

        from transformers import EncoderDecoderModel, AutoTokenizer

        logger.info(f"Loading model from HF Hub: {HF_REPO_ID}")
        model = EncoderDecoderModel.from_pretrained(HF_REPO_ID)
        tokenizer = AutoTokenizer.from_pretrained(HF_REPO_ID)

        # Configure special tokens
        model.config.decoder_start_token_id = tokenizer.cls_token_id
        model.config.bos_token_id = tokenizer.cls_token_id
        model.config.eos_token_id = tokenizer.sep_token_id
        model.config.pad_token_id = tokenizer.pad_token_id

        model = model.to(device)
        model.eval()

        _punctuation_checker = PunctuationChecker(model, tokenizer, device)

        elapsed = time.time() - t0
        logger.info(f"PuncAra-v1 ready in {elapsed:.1f}s")
        return _punctuation_checker

    except Exception as e:
        import traceback
        _load_error = str(e)
        logger.error(f"Failed to load punctuation model: {e}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Punctuation model load failed: {e}")


def is_loaded() -> bool:
    """Check if the punctuation model is loaded."""
    return _punctuation_checker is not None


def get_load_error() -> str:
    """Return the last load error, or empty string."""
    return _load_error or ""
