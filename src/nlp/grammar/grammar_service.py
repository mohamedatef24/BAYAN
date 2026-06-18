"""
Grammar correction service using Bayan_Arabic_Grammar (T5).
Lazy-loads the model on first request, keeps it resident in memory.
"""
import logging
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logger = logging.getLogger(__name__)

_grammar_model = None
_grammar_tokenizer = None
_device = None

MODEL_ID = "bayan10/Bayan_Arabic_Grammar"

# Generation parameters — ORIGINAL WORKING VALUES
MAX_INPUT_LENGTH = 512
MAX_OUTPUT_LENGTH = 512
NUM_BEAMS = 4


def get_grammar_model():
    """
    Lazy-load the grammar model. Returns (model, tokenizer, device).
    Loads once, stays in memory forever.
    """
    global _grammar_model, _grammar_tokenizer, _device

    if _grammar_model is not None:
        return _grammar_model, _grammar_tokenizer, _device

    logger.info("Loading Grammar model (lazy init)...")

    _device = "cpu"

    try:
        logger.info(f"Loading tokenizer: {MODEL_ID}")
        _grammar_tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID, local_files_only=True
        )

        logger.info(f"Loading T5 model: {MODEL_ID}")
        _grammar_model = AutoModelForSeq2SeqLM.from_pretrained(
            MODEL_ID, local_files_only=True
        )
        _grammar_model.to(_device)
        _grammar_model.eval()

        logger.info(f"Grammar model loaded on {_device}")

    except Exception as e:
        logger.error(f"Failed to load grammar model: {e}")
        # Try without local_files_only as fallback
        try:
            logger.info("Retrying without local_files_only...")
            _grammar_tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
            _grammar_model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID)
            _grammar_model.to(_device)
            _grammar_model.eval()
            logger.info(f"Grammar model loaded on {_device} (fallback)")
        except Exception as e2:
            logger.error(f"Grammar model load failed completely: {e2}")
            _grammar_model = None
            _grammar_tokenizer = None
            raise

    return _grammar_model, _grammar_tokenizer, _device


def correct_grammar(text: str) -> str:
    """
    Run grammar correction on input text using T5.
    Returns the corrected text.
    """
    if not text or not text.strip():
        return text

    model, tokenizer, device = get_grammar_model()

    try:
        # Tokenize input
        inputs = tokenizer(
            text,
            return_tensors="pt",
            max_length=MAX_INPUT_LENGTH,
            truncation=True,
            padding=True
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Generate correction — ORIGINAL WORKING PARAMS
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=MAX_OUTPUT_LENGTH,
                num_beams=NUM_BEAMS,
                early_stopping=True,
                no_repeat_ngram_size=3,
            )

        # Decode output
        corrected = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Log for debugging
        logger.info(f"[GRAMMAR-RAW] input({len(text)}): '{text}'")
        logger.info(f"[GRAMMAR-RAW] output({len(corrected)}): '{corrected}'")

        # Safety: if model returns empty, keep original
        if not corrected or not corrected.strip():
            return text

        return corrected.strip()

    except Exception as e:
        logger.error(f"Grammar correction failed: {e}")
        return text
