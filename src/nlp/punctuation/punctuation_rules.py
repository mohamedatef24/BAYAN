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


def validate_punctuation_diff(diff: dict, full_text: str = '') -> bool:
    """
    Return True ONLY if the diff is a safe punctuation-only change.

    ALLOWED:
        - Inserting 1 punctuation mark (short text) or 1–3 (long text)
        - Replacing one punctuation mark with another
        - Adding terminal punctuation to sentences (3+ words) that lack it

    REJECTED:
        - Adding/deleting/duplicating Arabic words
        - Rewriting phrases
        - Excessive punctuation repetition (3+ consecutive identical)
        - Punctuation spam: delta/word_count > 0.5 (multi-word diffs)
        - Short text (≤2 words): delta > 1
        - Any diff: delta > MAX_PUNCT_DELTA
        - Adding terminal punctuation to short fragments (≤2 words) (FIX-01)
        - Adding terminal punctuation when text already ends with punct
    """
    original = diff.get('original', '')
    correction = diff.get('correction', '')

    # ── Rule 0 (FIX-01): Reject terminal punctuation injection ──
    # PuncAra-v1 unconditionally adds . or ؟ to every sentence.
    # This rule catches the pattern: "word" → "word." / "word؟" / "word،"
    # where the ONLY change is appending 1-2 terminal punctuation marks.
    #
    # Phase 13: Allow terminal punct for multi-word sentences (3+ words)
    # that don't already end with punctuation. Only block for:
    #   - Short fragments (≤2 words in full text)
    #   - Text that already has terminal punctuation
    TERMINAL_PUNCT = set('.,،؛؟!:;?!')
    orig_stripped = original.rstrip()
    corr_stripped = correction.rstrip()
    if orig_stripped and corr_stripped:
        # Check if correction is just original + terminal punct
        orig_alpha_r0 = re.sub(r'[.,،؛؟!:;?\s]', '', original)
        corr_alpha_r0 = re.sub(r'[.,،؛؟!:;?\s]', '', correction)
        if (_normalize_for_comparison(orig_alpha_r0) ==
                _normalize_for_comparison(corr_alpha_r0)):
            # Same word content — check if only terminal punct was added
            orig_punct_end = sum(1 for c in original if c in TERMINAL_PUNCT)
            corr_punct_end = sum(1 for c in correction if c in TERMINAL_PUNCT)
            if corr_punct_end > orig_punct_end:
                # Only adding punctuation — check if it's at the END (terminal)
                orig_no_punct = re.sub(r'[.,،؛؟!:;?!]+$', '', original)
                corr_no_punct = re.sub(r'[.,،؛؟!:;?!]+$', '', correction)
                if _normalize_for_comparison(orig_no_punct.replace(' ', '')) == \
                   _normalize_for_comparison(corr_no_punct.replace(' ', '')):
                    # This is a pure terminal-punctuation addition.
                    # Decide whether to allow based on full text context.
                    _full_word_count = len(re.findall(
                        r'[\u0600-\u06FFa-zA-Z]+', full_text
                    )) if full_text else 0
                    _full_already_has_terminal = bool(
                        re.search(r'[.،؛؟!?!][\s]*$', full_text)
                    ) if full_text else False
                    # Also check for ellipsis (... at end)
                    _full_has_ellipsis = full_text.rstrip().endswith('...') if full_text else False

                    if _full_word_count >= 3 and not _full_already_has_terminal and not _full_has_ellipsis:
                        # Multi-word sentence without terminal punct → ALLOW
                        logger.info(
                            f"[PUNC-SAFETY] Allowed terminal punct for sentence "
                            f"({_full_word_count} words): "
                            f"'{original}' → '{correction}'"
                        )
                        # Fall through to remaining rules (don't return yet)
                    else:
                        # Short fragment OR already has terminal punct → REJECT
                        logger.info(
                            f"[PUNC-SAFETY] Rejected terminal punct injection: "
                            f"'{original}' → '{correction}'"
                        )
                        return False

    # ── Rule 0b (Batch 4): Reject punct insertion when original has no punctuation ──
    # If the original text has zero Arabic punctuation and the correction
    # only adds commas/semicolons (not at the very end), it's overcorrection.
    # This catches "already correct" texts that PuncAra sprinkles with commas.
    orig_punct_count_r0b = sum(1 for c in original if c in ARABIC_PUNCT_CHARS)
    if orig_punct_count_r0b == 0:
        corr_punct_count_r0b = sum(1 for c in correction if c in ARABIC_PUNCT_CHARS)
        if corr_punct_count_r0b > 0:
            # Only allow if adding a single period/question at the very end
            stripped_corr = correction.rstrip()
            if stripped_corr and stripped_corr[-1] in '.؟?!':
                # This is terminal punct (already handled by Rule 0)
                pass
            else:
                # Mid-sentence punct insertion on a clean sentence → reject
                logger.info(
                    f"[PUNC-SAFETY] Rejected mid-sentence punct insertion on clean text: "
                    f"'{original}' → '{correction}'"
                )
                return False

    # ── Rule 0c (Batch 4 + FIX-26): Reject punctuation rearrangement/substitution ──
    # When original already has punctuation and the correction merely MOVES
    # or SUBSTITUTES marks (e.g., ، → : or ، → ؛), reject.
    # The PuncAra model should NOT replace existing punctuation.
    orig_punct_count_r0c = sum(1 for c in original if c in ARABIC_PUNCT_CHARS)
    corr_punct_count_r0c = sum(1 for c in correction if c in ARABIC_PUNCT_CHARS)
    if orig_punct_count_r0c > 0 and corr_punct_count_r0c > 0:
        # Both have punctuation — check if alpha content is the same
        orig_alpha_r0c = re.sub(r'[.,،؛؟!:;?\s]', '', original)
        corr_alpha_r0c = re.sub(r'[.,،؛؟!:;?\s]', '', correction)
        if _normalize_for_comparison(orig_alpha_r0c) == _normalize_for_comparison(corr_alpha_r0c):
            # Same word content, but punct changed — reject any punct modification
            logger.info(
                f"[PUNC-SAFETY] Rejected punct substitution: "
                f"'{original}' → '{correction}'"
            )
            return False

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

    return True

