"""
Grammar correction service using Bayan_Arabic_Grammar (T5).
Lazy-loads the model on first request, keeps it resident in memory.
"""
import logging
import re
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logger = logging.getLogger(__name__)

_grammar_model = None
_grammar_tokenizer = None
_device = None

MODEL_ID = "bayan10/Bayan_Arabic_Grammar"

# Generation parameters
MAX_INPUT_LENGTH = 512


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


def _is_hallucinated(original: str, corrected: str) -> bool:
    """
    Check if the grammar output is hallucinated / garbled.
    Returns True if output should be discarded.
    """
    orig_words = re.findall(r'[\u0600-\u06FF]+', original)
    corr_words = re.findall(r'[\u0600-\u06FF]+', corrected)

    # 1. Output too long (grammar corrections are minor edits)
    if len(corrected) > len(original) * 1.5:
        logger.warning(f"Hallucination: output too long ({len(corrected)} vs {len(original)} chars)")
        return True

    # 2. Output too short
    if len(corrected) < len(original) * 0.5:
        logger.warning(f"Hallucination: output too short ({len(corrected)} vs {len(original)} chars)")
        return True

    # 3. Too many words added
    if len(corr_words) > len(orig_words) * 1.4:
        logger.warning(f"Hallucination: too many words ({len(corr_words)} vs {len(orig_words)})")
        return True

    # 4. Check for duplicated 2-word phrases (bigrams)
    if len(corr_words) > 4:
        bigrams = [f"{corr_words[i]} {corr_words[i+1]}" for i in range(len(corr_words)-1)]
        if len(bigrams) != len(set(bigrams)):
            logger.warning("Hallucination: repeated bigrams detected")
            return True

    # 5. Sentence start rearranged (grammar shouldn't move first word to end)
    if orig_words and corr_words:
        # Check if first 2 original words appear in first 4 corrected words
        orig_head = set(orig_words[:2])
        corr_head = set(corr_words[:4])
        if len(orig_head) > 0 and not orig_head.intersection(corr_head):
            logger.warning("Hallucination: sentence start completely rearranged")
            return True

    return False


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

        # Dynamic max_length: close to input to prevent hallucination
        input_len = inputs['input_ids'].shape[1]
        dynamic_max_len = min(int(input_len * 1.3) + 5, MAX_INPUT_LENGTH)

        # Strategy: greedy decoding (most stable for grammar correction)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=dynamic_max_len,
                num_beams=1,          # Greedy decoding — most stable
                do_sample=False,
                repetition_penalty=2.0,  # Strong penalty against repeating
            )

        # Decode output
        raw_output = tokenizer.decode(outputs[0], skip_special_tokens=True)
        logger.info(f"[GRAMMAR-RAW] input({len(text)}): '{text}'")
        logger.info(f"[GRAMMAR-RAW] output({len(raw_output)}): '{raw_output}'")

        # Safety: if model returns empty, keep original
        if not raw_output or not raw_output.strip():
            logger.warning("Grammar returned empty output")
            return text

        corrected = raw_output.strip()

        # Check for hallucination
        if _is_hallucinated(text, corrected):
            return text

        return corrected

    except Exception as e:
        logger.error(f"Grammar correction failed: {e}")
        return text
