# PuncAra — Arabic Punctuation Restoration Rules
# Extracted from PuncAra.py — preprocessing + postprocessing + chunking logic.
# All classes are imported by punctuation_service.py.

import re
import logging

logger = logging.getLogger(__name__)


def arabic_preprocessing(text: str) -> str:
    """Remove Arabic diacritics to normalize input for the model."""
    arabic_diacritics = re.compile(r'[\u064B-\u0652]')
    return re.sub(arabic_diacritics, '', text).strip()


def arabic_postprocessing(text: str) -> str:
    """
    Typographic cleanup and punctuation normalization after model inference.
    Handles: bracket spacing, duplicate marks, chunk-join artifacts, etc.
    """
    if not text:
        return text

    # 1. Protect numbers/fractions/time from incorrect conversion
    text = re.sub(r'(?<=\d),(?=\d)', '٪TEMP_COMMA٪', text)
    text = re.sub(r'(?<=\d):(?=\d)', '٪TEMP_COLON٪', text)

    # 2. Arabize typographic marks
    text = text.replace(',', '،').replace(';', '؛').replace('?', '؟')

    # 3. Fix internal spacing for brackets and Arabic quotes
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    text = re.sub(r'\[\s+', '[', text)
    text = re.sub(r'\s+\]', ']', text)
    text = re.sub(r'«\s+', '«', text)
    text = re.sub(r'\s+»', '»', text)

    # 4. Remove repeated emotional marks (except ellipsis)
    text = re.sub(r'([،؛:!؟])\1+', r'\1', text)
    text = re.sub(r'\.{4,}', '...', text)

    # 5. Fix chunk-join contradictions
    text = re.sub(r'[،؛:]+([.!؟])', r'\1', text)
    text = re.sub(r'،؛|؛،', '؛', text)
    text = re.sub(r'([!؟])\.', r'\1', text)

    # 6. Remove stray leading punctuation
    text = re.sub(r'^[،؛:!؟. \t]+', '', text)

    # 7. Ensure single space after punctuation before text
    text = re.sub(r'([،؛:!؟.])(?=\S)', r'\1 ', text)

    # 8. Restore protected numbers
    text = text.replace('٪TEMP_COMMA٪', ',').replace('٪TEMP_COLON٪', ':')

    # 9. Attach punctuation to preceding word
    text = re.sub(r'\s+([،؛:!؟.])', r'\1', text)

    # 10. Collapse horizontal spaces only
    text = re.sub(r'[ \t]+', ' ', text).strip()
    return text


# ══════════════════════════════════════════════════════════════════════════════
# PUNCTUATION SAFETY LAYER — Pipeline Hardening v3.3
# ══════════════════════════════════════════════════════════════════════════════

ARABIC_PUNCT_CHARS = set('.,،؛؟!:;?!')
MAX_PUNCT_DELTA = 3
MAX_PUNCT_DELTA_SHORT = 1   # Stricter cap for short texts (≤2 words)
MAX_PUNCT_RATIO = 0.5       # max punctuation delta per word (multi-word diffs)


def _normalize_for_comparison(text: str) -> str:
    """
    Normalize Arabic for safe comparison.
    Prevents false rejection from hamza/alef/ya variants.
    """
    # Remove diacritics
    text = re.sub(r'[\u064B-\u0652]', '', text)
    # Fold hamza/alef variants: أ إ آ → ا
    text = re.sub(r'[أإآ]', 'ا', text)
    # Fold ya: ى → ي
    text = text.replace('ى', 'ي')
    # Fold ta marbuta: ة → ه (comparison only)
    text = text.replace('ة', 'ه')
    return text


def validate_punctuation_diff(diff: dict) -> bool:
    """
    Return True ONLY if the diff is a safe punctuation-only change.

    ALLOWED:
        - Inserting 1 punctuation mark (short text) or 1–3 (long text)
        - Replacing one punctuation mark with another

    REJECTED:
        - Adding/deleting/duplicating Arabic words
        - Rewriting phrases
        - Excessive punctuation repetition (3+ consecutive identical)
        - Punctuation spam: delta/word_count > 0.5 (multi-word diffs)
        - Short text (≤2 words): delta > 1
        - Any diff: delta > MAX_PUNCT_DELTA
    """
    original = diff.get('original', '')
    correction = diff.get('correction', '')

    # ── Rule 1: Alphabetic content must be identical after normalization ──
    orig_alpha = re.sub(r'[.,،؛؟!:;?\s]', '', original)
    corr_alpha = re.sub(r'[.,،؛؟!:;?\s]', '', correction)

    if _normalize_for_comparison(orig_alpha) != _normalize_for_comparison(corr_alpha):
        return False

    # ── Rule 2: Reject excessive repetition (3+ consecutive identical) ──
    if re.search(r'([.,،؛؟!:;?])\1{2,}', correction):
        return False

    # ── Shared computation for Rules 3–5 ──
    orig_punct_count = sum(1 for c in original if c in ARABIC_PUNCT_CHARS)
    corr_punct_count = sum(1 for c in correction if c in ARABIC_PUNCT_CHARS)
    punct_delta = max(0, corr_punct_count - orig_punct_count)
    word_count = len(re.findall(r'[\u0600-\u06FFa-zA-Z]+', correction)) or 1

    # ── Rule 3: Short-text hybrid cap (≤2 words → max 1 mark added) ──
    if word_count <= 2 and punct_delta > MAX_PUNCT_DELTA_SHORT:
        return False

    # ── Rule 4: Ratio-based spam protection (multi-word diffs) ──
    if word_count > 2 and punct_delta / word_count > MAX_PUNCT_RATIO:
        return False

    # ── Rule 5: Absolute delta cap ──
    if punct_delta > MAX_PUNCT_DELTA:
        return False

    # ── Rule 6: Reject mid-word punctuation insertion ──
    # If the correction ends with a punctuation mark followed by nothing,
    # but the original word is a PREFIX of a longer word in context,
    # this indicates mid-word split (e.g. الدفت→الدفت. when word was الدفتر).
    # Detect by checking if correction has punctuation NOT at word boundary.
    for pc in ARABIC_PUNCT_CHARS:
        if pc in correction:
            # Check if punctuation is followed by an Arabic letter (mid-word)
            idx = correction.find(pc)
            if idx >= 0 and idx < len(correction) - 1:
                next_char = correction[idx + 1]
                if '\u0600' <= next_char <= '\u06FF':
                    return False

    return True

