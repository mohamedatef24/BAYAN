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
NUM_BEAMS = 2  # Lower beams = less hallucination on CPU


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


def _word_set(text: str) -> set:
    """Extract set of Arabic words from text."""
    return set(re.findall(r'[\u0600-\u06FF]+', text))


def _is_hallucinated(original: str, corrected: str) -> bool:
    """
    Check if the grammar output is hallucinated / garbled.
    Returns True if output should be discarded.
    """
    # 1. Output too long (grammar should NOT add lots of text)
    if len(corrected) > len(original) * 1.5:
        logger.warning(f"Grammar hallucination: output too long ({len(corrected)} vs {len(original)})")
        return True

    # 2. Output too short
    if len(corrected) < len(original) * 0.5:
        logger.warning(f"Grammar hallucination: output too short ({len(corrected)} vs {len(original)})")
        return True

    # 3. Check word order preservation — grammar should NOT rearrange sentences
    orig_words = re.findall(r'[\u0600-\u06FF]+', original)
    corr_words = re.findall(r'[\u0600-\u06FF]+', corrected)

    if len(corr_words) > len(orig_words) * 1.5:
        logger.warning(f"Grammar hallucination: too many words ({len(corr_words)} vs {len(orig_words)})")
        return True

    # 4. Check for duplicated segments (repeated phrases)
    if len(corr_words) > 3:
        # Check if any 3-word sequence appears more than once
        trigrams = [' '.join(corr_words[i:i+3]) for i in range(len(corr_words)-2)]
        if len(trigrams) != len(set(trigrams)):
            logger.warning("Grammar hallucination: repeated phrases detected")
            return True

    # 5. First word of output should be close to first word of input
    #    (grammar shouldn't rearrange sentence start)
    if orig_words and corr_words:
        if orig_words[0] != corr_words[0]:
            # Check if the first few words are completely rearranged
            orig_start = set(orig_words[:3])
            corr_start = set(corr_words[:3])
            if not orig_start.intersection(corr_start):
                logger.warning("Grammar hallucination: sentence completely rearranged")
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

        # Calculate dynamic max_length: slightly more than input to allow small expansions
        input_len = inputs['input_ids'].shape[1]
        dynamic_max_len = min(int(input_len * 1.3) + 10, MAX_INPUT_LENGTH)

        # Generate correction with conservative params to avoid hallucination
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=dynamic_max_len,
                num_beams=NUM_BEAMS,
                early_stopping=True,
                no_repeat_ngram_size=3,
                length_penalty=1.0,
                repetition_penalty=1.5,
            )

        # Decode output
        corrected = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Safety: if model returns empty, keep original
        if not corrected or not corrected.strip():
            return text

        corrected = corrected.strip()

        # Check for hallucination
        if _is_hallucinated(text, corrected):
            return text

        return corrected

    except Exception as e:
        logger.error(f"Grammar correction failed: {e}")
        return text
