# PuncAra — Arabic Punctuation Restoration Rules
# Extracted from PuncAra.py — preprocessing + postprocessing + chunking logic.
# All classes are imported by punctuation_service.py.
#
# MERGED: Best of V1 + V2
# - V2: Threshold >= 1 (not 5) — allows terminal punct on any real text
# - V2: Fallback to `original` word count when `full_text` is empty
# - V1: Softened exclamation guard — blocks ؟/! on SHORT texts (< 3 words)
#        without cue words, but allows on longer sentences

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

    # 5.5 Syntactic context fixes for model hallucinations
    # Remove colons/semicolons before relative pronouns
    text = re.sub(r'[؛:]\s*(التي|الذي|الذين|اللتان|اللذان|اللاتي|اللواتي)', r' \1', text)
    
    # Fix misplaced colons for saying verbs (e.g. قال: المعلم -> قال المعلم:)
    text = re.sub(r'\b(قال|يقول|قالت|تقول|أجاب|أجابت|سأل|سألت|أخبر|أخبرت|صرح|صرحت|أضاف|أضافت|أردف|أردفت):?\s+(ال[أ-ي]+|أحمد|محمد|محمود|علي|عمر|خالد|فاطمة|مريم|عائشة|خديجة)\b:?', r'\1 \2:', text)

    # NEW: Strict Colon Guard
    _ALLOWED_COLON_CUES = r'(قال|يقول|قالت|تقول|أجاب|أجابت|سأل|سألت|أخبر|أخبرت|صرح|صرحت|أضاف|أضافت|أردف|أردفت|وضح|وضحت|أوضح|أوضحت|رد|ردت|التالي|الآتي|مثال|ملاحظة|تنبيه|تحذير|قائلا|قائلة|اسم|العمر|تاريخ|رقم|عاجل|الآتية|التالية)'
    
    def _colon_guard(match):
        prev_word = match.group(1)
        if re.fullmatch(_ALLOWED_COLON_CUES, prev_word):
            return match.group(0)
        # Strip colons from definite nouns (ال-prefix) and preposition+definite combos
        # (لل, بال, فال, وال, كال). These are never valid colon targets.
        if prev_word.startswith(('ال', 'لل', 'بال', 'فال', 'وال', 'كال')):
            return f'{prev_word}'
        return match.group(0)
        
    text = re.sub(r'([\u0600-\u06FF]+)(\s*:)', _colon_guard, text)
    
    # Remove colons after specific non-speech verbs (fallback for verbs without ال)
    text = re.sub(r'\b(يقدر|يستطيع|يمكن|يجب|ينبغي|يعتبر|يعد|يرى|يعتقد)\s*:', r'\1 ', text)
    # Replace semicolon with comma if followed by "و" (and) or similar conjunctions, as semicolon is for separate clauses
    text = re.sub(r'؛\s*(و|ف|ثم|أو|أم|بل)\b', r'، \1', text)

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
# PUNCTUATION SAFETY LAYER — Pipeline Hardening v3.4 (Merged V1+V2)
# ══════════════════════════════════════════════════════════════════════════════

ARABIC_PUNCT_CHARS = set('.,،؛؟!:;?!')
MAX_PUNCT_DELTA = 3
MAX_PUNCT_DELTA_SHORT = 1   # Stricter cap for short texts (≤2 words)
MAX_PUNCT_RATIO = 0.5       # max punctuation delta per word (multi-word diffs)

# Exclamation/question cue words (from V1 FIX-29, used in softened guard)
_EXCL_CUES = {'يا', 'ما', 'كم', 'لا', 'هل', 'أين', 'متى',
              'كيف', 'لماذا', 'ماذا', 'أي', 'لعل', 'ليت'}


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
        - Adding terminal punctuation to any text (1+ words) that lacks it
        - Adding ؟/! to short texts (< 3 words) ONLY with cue words

    REJECTED:
        - Adding/deleting/duplicating Arabic words
        - Rewriting phrases
        - Excessive punctuation repetition (3+ consecutive identical)
        - Punctuation spam: delta/word_count > 0.5 (multi-word diffs)
        - Short text (≤2 words): delta > 1
        - Any diff: delta > MAX_PUNCT_DELTA
        - Adding terminal punctuation when text already ends with punct
        - Adding ؟/! to short texts without interrogative/exclamatory cues
    """
    original = diff.get('original', '')
    correction = diff.get('correction', '')

    # ── Rule 0 (FIX-01 + FIX-30 + Merged Guard): Terminal punctuation ──
    # PuncAra-v1 unconditionally adds . or ؟ to every sentence.
    # This rule catches the pattern: "word" → "word." / "word؟" / "word،"
    # where the ONLY change is appending 1-2 terminal punctuation marks.
    #
    # From V2 (FIX-30): Threshold lowered from 5 → 1. Even single-word
    # fragments deserve terminal punctuation (e.g. "اليوم" → "اليوم.").
    #
    # From V2 (FIX-30): When full_text isn't provided, fall back to
    # counting words in `original` instead of returning 0.
    #
    # From V1 (FIX-29, softened): For SHORT texts (< 3 words), block ؟/!
    # unless text contains interrogative/exclamatory cue words. For longer
    # texts (3+ words), allow any terminal punct freely. This prevents
    # "محمد" → "محمد؟" while still allowing "اليوم" → "اليوم.".
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
                    
                    is_at_end = False
                    if full_text and 'end' in diff:
                        is_at_end = diff['end'] >= len(full_text) - 2
                    elif not full_text:
                        is_at_end = True  # If no context, assume it's a standalone fragment
                    
                    if not is_at_end:
                        # Mid-sentence punctuation addition. This is safe to fall through to other rules.
                        pass
                    else:
                        # This is a pure terminal-punctuation addition.
                        # V2 FIX-30: Fall back to original when full_text is empty
                        _word_count_source = full_text if full_text else original
                        _full_word_count = len(re.findall(
                            r'[\u0600-\u06FFa-zA-Z]+', _word_count_source
                        ))
                        _full_already_has_terminal = bool(
                            re.search(r'[.،؛؟!?!][\s]*$', full_text)
                        ) if full_text else False
                        _full_has_ellipsis = full_text.rstrip().endswith('...') if full_text else False
    
                        # V2 FIX-30: Allow for 1+ words (not 5)
                        if _full_word_count >= 1 and not _full_already_has_terminal and not _full_has_ellipsis:
                            # ── Softened FIX-29 (Merged): Short-text ؟/! guard ──
                            # For short texts (< 3 words), block ؟ and ! unless
                            # cue words are present. Prevents "محمد" → "محمد؟"
                            # but allows "اليوم" → "اليوم." (period is safe).
                            # For 3+ words, allow freely (V2 behavior).
                            _added_punct = correction[len(orig_stripped):]
                            if _full_word_count < 3 and ('!' in _added_punct or '؟' in _added_punct):
                                _text_to_scan = full_text if full_text else original
                                _has_cue = any(w in _EXCL_CUES for w in _text_to_scan.split())
                                if not _has_cue:
                                    logger.info(
                                        f"[PUNC-SAFETY] Blocked !/؟ on short text without cue: "
                                        f"'{original}' → '{correction}'"
                                    )
                                    return False
    
                            logger.info(
                                f"[PUNC-SAFETY] Allowed terminal punct for sentence "
                                f"({_full_word_count} words): "
                                f"'{original}' → '{correction}'"
                            )
                            # Fall through to remaining rules (don't return yet)
                        else:
                            # Already has terminal punct or ends in ellipsis → REJECT
                            logger.info(
                                f"[PUNC-SAFETY] TerminalPunctuationGuard triggered: removing trailing punctuation "
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
