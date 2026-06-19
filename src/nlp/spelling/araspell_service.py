"""
AraSpell Service — Lazy-loaded Arabic spelling correction.

Model is loaded on first request and kept in memory.
Pre-downloaded during Docker build; loaded from HF cache at runtime (no network needed).
"""

import os
import logging
import time
import torch

import threading

logger = logging.getLogger(__name__)

# ── Lazy-loaded singletons ──
_spell_checker = None
_load_error = None
_load_lock = threading.Lock()

# Model identifiers
MODEL_REPO = 'bayan10/AraSpell-Model'
MODEL_FILENAME = 'last_model.pt'
TOKENIZER_NAME = 'aubmindlab/bert-base-arabertv02'


def get_spelling_model():
    """
    Lazy-load the spelling model on first call.
    Returns the ArabicSpellChecker instance, or raises RuntimeError if loading fails.
    """
    global _spell_checker, _load_error, _load_lock

    if _spell_checker is not None:
        return _spell_checker

    with _load_lock:
        if _spell_checker is not None:
            return _spell_checker

        if _load_error is not None:
            raise RuntimeError(f"Spelling model previously failed to load: {_load_error}")

        try:
            t0 = time.time()
        logger.info("Loading AraSpell spelling model (lazy init)...")

        from huggingface_hub import hf_hub_download
        from transformers import AutoTokenizer, EncoderDecoderModel

        # 1. Download checkpoint (from HF cache — pre-downloaded in Docker build)
        logger.info(f"Resolving checkpoint: {MODEL_REPO}/{MODEL_FILENAME}")
        model_path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILENAME)
        logger.info(f"Checkpoint path: {model_path}")

        # 2. Load tokenizer
        logger.info(f"Loading tokenizer: {TOKENIZER_NAME}")
        tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_NAME)

        # 3. Build encoder-decoder model from AraBERT
        logger.info("Building EncoderDecoderModel from AraBERT...")
        model = EncoderDecoderModel.from_encoder_decoder_pretrained(
            TOKENIZER_NAME, TOKENIZER_NAME
        )

        # 4. Configure generation
        model.config.decoder_start_token_id = tokenizer.cls_token_id
        model.config.pad_token_id = tokenizer.pad_token_id
        model.config.eos_token_id = tokenizer.sep_token_id
        model.generation_config.max_length = 128
        model.generation_config.decoder_start_token_id = tokenizer.cls_token_id
        model.generation_config.pad_token_id = tokenizer.pad_token_id
        model.generation_config.eos_token_id = tokenizer.sep_token_id

        # 5. Load trained weights
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Loading checkpoint weights on {device}...")
        checkpoint = torch.load(model_path, map_location=device, weights_only=False)
        model.load_state_dict(checkpoint['model_state_dict'], strict=False)
        model = model.to(device)
        model.eval()

        epoch = checkpoint.get('epoch', 'N/A')
        logger.info(f"Spelling model loaded on {device}, epoch: {epoch}")

        # 6. Initialize the spell checker pipeline (contextual=True for MLM-based refinement)
        from nlp.spelling.araspell_rules import ArabicSpellChecker
        _spell_checker = ArabicSpellChecker(
            model, tokenizer, device, use_contextual=True
        )

        elapsed = time.time() - t0
        logger.info(f"AraSpell ready in {elapsed:.1f}s")
        return _spell_checker

        except Exception as e:
        import traceback
        _load_error = str(e)
        logger.error(f"Failed to load spelling model: {e}")
        logger.error(traceback.format_exc())
        raise RuntimeError(f"Spelling model load failed: {e}")


def is_loaded() -> bool:
    """Check if the spelling model is loaded."""
        return _spell_checker is not None


def get_load_error() -> str:
    """Return the last load error, or empty string."""
    return _load_error or ""
