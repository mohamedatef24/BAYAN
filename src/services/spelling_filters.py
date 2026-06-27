import re
import logging
from nlp.text_utils import levenshtein as _levenshtein

logger = logging.getLogger(__name__)

# ── Directional Blocks: prevent meaning-changing substitutions ──
# Used by both spelling confidence filter and grammar diff filter.
_DIRECTIONAL_BLOCKS = {
    # Demonstratives: هذه (correct feminine) → هذة (misspelling) = ALWAYS wrong
    'هذه': {'هذة'},
    'هذا': {'هذة', 'هذه'},    # masculine → don't flip to feminine forms
    # Verb/particle confusion: كان (was) ↔ كأن (as if) = ALWAYS wrong
    'كان': {'كأن'},
    'كأن': {'كان'},
    'كانت': {'كأنت'},      # H016: كانت → كأنت = ALWAYS wrong
    'كانوا': {'كأنوا'},     # also block plural form
    # Preposition confusion: different meanings, both valid
    'إلى': {'على', 'علي'},
    'على': {'إلى', 'علي'},
    'علي': {'على'},           # proper name vs preposition
    # Conjunction: لكن (correct) ↔ لاكن (misspelling of لكن, never valid)
    'لكن': {'لاكن'},          # correct → misspelling = ALWAYS wrong
    # Demonstrative: ذلك (correct) ↔ ذالك (common misspelling)
    'ذلك': {'ذالك'},          # correct → misspelling = ALWAYS wrong
    # Pronoun suffix: ه→ة corruption (G037: عمله→عملة)
    'عمله': {'عملة'},          # عمله (his work) → عملة (currency) = WRONG
    'لسانه': {'لسانة'},        # his tongue
    'بيته': {'بيتة'},          # his house
    'كتابه': {'كتابة'},        # his book → writing
}


def _is_small_spelling_change(orig_word, corr_word, vocab_manager=None):
    """
    Heuristic: only accept small spelling edits and ignore
    aggressive changes (to avoid over-editing).

    CRITICAL: If both words are in-vocabulary (both are valid Arabic words),
    only accept known orthographic fixes (ه→ة, hamza whitelist).
    This prevents the model from corrupting correct words (e.g. وكان→وكأن).

    Returns:
        float: 0.0 = reject, 0.5 = dampened confidence (rare word risk),
               0.9 = normal confidence. Phase 2 (BUG-034/035/036/037/E8).
    """
    if not orig_word or not corr_word:
        return 0.0
    if orig_word == corr_word:
        return 0.0

    # ── FIX-39: Edit distance hallucination guard (from legacy AraSpell OutputValidator) ──
    # Block corrections where the edit distance is too high relative to word length.
    # This catches model hallucinations like والممرضات→والرضا, شجعتهم→يجعلهم, طبخ→طبي.
    _ed_dist = _levenshtein(orig_word, corr_word)
    _max_len = max(len(orig_word), len(corr_word))
    if _max_len >= 3 and _ed_dist > max(2, _max_len * 0.4):
        logger.info(
            f"[SPELLING] Blocked hallucination: '{orig_word}'→'{corr_word}' "
            f"(edit_dist={_ed_dist}, max_allowed={max(2, int(_max_len * 0.4))})"
        )
        return 0.0

    # ── FIX-42a: Length ratio guard ──
    # Block corrections that shrink the word significantly (>30% shorter).
    # Catches: والممرضات(9)→والرضا(6), للطالبه(7)→للطالب(6), شجعتهم(6)→يجعلهم(6)
    # These often indicate the model hallucinated a different word.
    _orig_len = len(orig_word)
    _corr_len = len(corr_word)
    if _orig_len >= 5 and _corr_len < _orig_len * 0.7:
        logger.info(
            f"[SPELLING] Blocked length shrink: '{orig_word}'→'{corr_word}' "
            f"(len {_orig_len}→{_corr_len}, ratio={_corr_len/_orig_len:.2f})"
        )
        return 0.0

    # ── FIX-42b: First-letter change guard ──
    # Block corrections that change the first character (after stripping common prefixes).
    # Catches: افهمه→تفهمة (أ→ت), واحتاج→وتحتاج (ا→ت).
    # The first root letter almost never changes in a typo — it's a hallucination.
    if _orig_len >= 3 and _corr_len >= 3:
        # Strip common prefixes (ال, و, ف, ب, ل, ك) to compare root starts
        _PREFIXES = ('وال', 'فال', 'بال', 'كال', 'لل', 'ال', 'و', 'ف', 'ب', 'ل', 'ك')
        _o_root = orig_word
        _c_root = corr_word
        for _pfx in _PREFIXES:
            if _o_root.startswith(_pfx) and len(_o_root) > len(_pfx) + 1:
                _o_root = _o_root[len(_pfx):]
                break
        for _pfx in _PREFIXES:
            if _c_root.startswith(_pfx) and len(_c_root) > len(_pfx) + 1:
                _c_root = _c_root[len(_pfx):]
                break
        # If roots start with different letters AND this isn't an orthographic pair
        # AND roots have same length (true consonant swap, not a character addition)
        # Exception: الولاد→الأولاد has roots ولاد(4)→أولاد(5) — different length = allow
        _HAMZA_CHARS = set('أإآاء')
        _STOP_WORDS = {"التي", "الذي", "الذين", "هذا", "هذه", "هؤلاء", "تلك", "ذلك"}
        if (_o_root and _c_root and _o_root[0] != _c_root[0]
                and len(_o_root) == len(_c_root)  # same-length roots only
                and not (_o_root[0] in _HAMZA_CHARS and _c_root[0] in _HAMZA_CHARS)
                and corr_word not in _STOP_WORDS):
            logger.info(
                f"[SPELLING] Blocked first-letter change: '{orig_word}'→'{corr_word}' "
                f"(root '{_o_root[0]}'→'{_c_root[0]}')"
            )
            return 0.0

    # ── GUARD 1: Numeral protection (Phase 1, BUG-011/012/E1) ──
    # Reject corrections that remove/change/introduce digits.
    # Numeral hallucination is a complete-replacement failure mode.
    _DIGITS = set('0123456789٠١٢٣٤٥٦٧٨٩')
    if any(c in _DIGITS for c in orig_word):
        return 0.0  # Never "correct" text containing numerals
    if any(c in _DIGITS for c in corr_word):
        return 0.0  # Never introduce digits that weren't in original

    # ── GUARD 2: Directional confusable-word rules (Phase 1, BUG-004/005/E4) ──
    # For known function words, only allow corrections TOWARD the valid form.
    # This prevents meaning-changing substitutions that pass orthographic checks.
    #
    # ── B5 KNOWN LIMITATION (BUG-025/026): Shadda Duplication ──
    # AraSpell duplicates shadda-bearing words in ISOLATION: إنّ→إن إن, أنّ→أن أن.
    # In sentence context (e.g., "إنّ العلم نور"), the model handles shadda correctly.
    # This is an isolation-only AraSpell quirk — no pipeline filter needed.
    # _DIRECTIONAL_BLOCKS is defined at module level (line ~100)
    if corr_word in _DIRECTIONAL_BLOCKS.get(orig_word, set()):
        return 0.0

    # Check with common prefixes stripped (و+كان→و+كأن etc.)
    _CLITIC_PREFIXES = ('و', 'ف', 'ب', 'ل', 'ك')
    for _pfx in _CLITIC_PREFIXES:
        if (orig_word.startswith(_pfx) and corr_word.startswith(_pfx)
                and len(orig_word) > len(_pfx) + 1):
            _orig_stem = orig_word[len(_pfx):]
            _corr_stem = corr_word[len(_pfx):]
            if _corr_stem in _DIRECTIONAL_BLOCKS.get(_orig_stem, set()):
                return 0.0

    # ── FIX-30: Prefix-stripping protection ──
    # Block corrections that strip a clitic prefix from a valid compound:
    #   وبالمستشفيات → والمستشفيات  (stripped ب from وب prefix chain)
    #   فبالتالي → وبالتالي         (swapped ف→و)
    # These destroy the meaning of the prefix (بال = by the, و = and, ف = so/then)
    _COMPOUND_PREFIXES = ['وبال', 'فبال', 'وال', 'فال', 'بال', 'كال', 'ول', 'فل',
                          'وب', 'فب', 'وك', 'فك']
    for _cpfx in _COMPOUND_PREFIXES:
        if orig_word.startswith(_cpfx) and len(orig_word) > len(_cpfx) + 2:
            if not corr_word.startswith(_cpfx):
                # Original has compound prefix but correction doesn't — check if
                # the stem is the same (meaning only the prefix was stripped)
                _stem = orig_word[len(_cpfx):]
                for _alt_pfx in _COMPOUND_PREFIXES + list(_CLITIC_PREFIXES) + ['ال', '']:
                    if corr_word.startswith(_alt_pfx):
                        _corr_stem2 = corr_word[len(_alt_pfx):]
                        if _stem == _corr_stem2 or _levenshtein(_stem, _corr_stem2) <= 1:
                            return 0.0
            break  # Only check the longest matching prefix

    # Ignore tokens that contain non-letters (numbers / punctuation)
    # Arabic letters range plus basic Latin letters.
    if re.search(r'[^ء-يآأإىa-zA-Z]', orig_word):
        return 0.0
    if re.search(r'[^ء-يآأإىa-zA-Z]', corr_word):
        return 0.0

    # Fix S2: Reject corrections that drop feminine marker (ه/ة)
    # e.g. بارده→بارد, منخفظه→منخفض — these are WORSE than no correction
    feminine_endings = ('ه', 'ة')
    if orig_word.endswith(feminine_endings) and not corr_word.endswith(feminine_endings):
        # Only reject if the correction is just the word minus the ending
        if corr_word == orig_word[:-1] or len(corr_word) < len(orig_word):
            return 0.0

    # ── FIX-41: Block corrections that ADD trailing ا/ي to IV words ──
    # Model sometimes adds accusative markers: واجب→واجبا, معطف→معطفا.
    # If the original word is IV and the correction just appends a letter, reject.
    if vocab_manager and len(corr_word) == len(orig_word) + 1 and corr_word.startswith(orig_word):
        _appended_char = corr_word[-1]
        if _appended_char in ('ا', 'ي', 'و') and vocab_manager.is_iv(orig_word):
            logger.info(
                f"[SPELLING] Blocked trailing '{_appended_char}' addition: "
                f"'{orig_word}'→'{corr_word}' (original is IV)"
            )
            return 0.0

    # CRITICAL: If both words are valid Arabic words, only accept known fixes.
    # This prevents the spelling model from changing one correct word to another
    # (e.g. وكان→وكأن, which changes "and was" to "as if" — a meaning change).
    if vocab_manager:
        orig_iv = vocab_manager.is_iv(orig_word)
        corr_iv = vocab_manager.is_iv(corr_word)
        if orig_iv and corr_iv:
             # Both are valid words — only accept known orthographic fixes:
            # 1. ه→ة at word end (feminine marker fix)
            #    B3 (BUG-014/015): EXCEPT when ه is a pronoun suffix (preceded by ت).
            #    Pattern: verb+ته = "verb + him/it", NOT ta marbuta.
            #    E.g., فتأملته (fataamaltahu) → فتأملتة is WRONG.
            if (orig_word.endswith('ه') and corr_word.endswith('ة')
                    and orig_word[:-1] == corr_word[:-1]):
                # FIX-38: Expanded pronoun suffix guard.
                # ه at end can be: (a) ta marbuta (should be ة) OR (b) pronoun "him/it".
                # The old guard only blocked ته. But كله (كل+ه), احبه (احب+ه),
                # عنده (عند+ه) are ALL pronoun suffixes — the ه is NOT ta marbuta.
                # Strategy (from legacy AraSpell WordAligner): if the STEM (word without ه)
                # is itself IV, then ه is likely a pronoun suffix → block the change.
                # If the stem is NOT IV, ه is likely a misspelled ة → allow.
                #
                # FIX-50: Whitelist bypass — known feminine nouns always allowed.
                # BERT vocab includes subword fragments (الحكوم, المدرس) as IV,
                # causing false pronoun detection. These known words bypass the guard.
                _KNOWN_FEMININE = {
                    'الحكومه', 'المدرسه', 'الشركه', 'الجامعه', 'المدينه',
                    'القصه', 'المكتبه', 'الطائره', 'الوزاره', 'المديره',
                    'المعلمه', 'الطالبه', 'القريه', 'الحديقه', 'المحكمه',
                    'المنطقه', 'الدوله', 'السياره', 'الغرفه', 'المحطه',
                    'الوظيفه', 'العائله', 'الحياه', 'الصلاه',
                    'حكومه', 'مدرسه', 'شركه', 'جامعه', 'مدينه',
                    'قصه', 'مكتبه', 'طائره', 'وزاره', 'مديره',
                    'معلمه', 'طالبه', 'قريه', 'حديقه', 'محكمه',
                    'منطقه', 'دوله', 'سياره', 'غرفه', 'محطه',
                    'وظيفه', 'عائله', 'حياه', 'صلاه',
                }
                if orig_word in _KNOWN_FEMININE:
                    return 0.9
                stem = orig_word[:-1]
                if len(stem) >= 2 and vocab_manager.is_iv(stem):
                    logger.info(
                        f"[SPELLING] Blocked ه→ة (pronoun suffix): "
                        f"'{orig_word}'→'{corr_word}' (stem '{stem}' is IV → ه is pronoun)"
                    )
                    return 0.0
                return 0.9
            # 2. ة→ه at word end (less common but valid)
            if (orig_word.endswith('ة') and corr_word.endswith('ه')
                    and orig_word[:-1] == corr_word[:-1]):
                return 0.9
            # 3. Word is in the hamza whitelist (known common errors)
            #    CRITICAL (Phase 5 fix, BUG-016/027): only accept if the correction
            #    MATCHES the whitelist target — not any arbitrary correction.
            #    FIX-02: This check now ALWAYS accepts whitelist matches, bypassing IV-IV guard.
            from nlp.spelling.araspell_rules import AraSpellPostProcessor
            if orig_word in AraSpellPostProcessor.HAMZA_WHITELIST:
                expected = AraSpellPostProcessor.HAMZA_WHITELIST[orig_word]
                if corr_word == expected:
                    return 0.9
                else:
                    logger.info(
                        f"[SPELLING] Whitelist mismatch: '{orig_word}'→'{corr_word}' "
                        f"(expected '{expected}') — rejected"
                    )
                    return 0.0
            # 4. Check prefixed hamza (و+whitelist word, etc.)
            for prefix in AraSpellPostProcessor.HAMZA_PREFIXES:
                if orig_word.startswith(prefix) and len(orig_word) > len(prefix) + 1:
                    remainder = orig_word[len(prefix):]
                    if remainder in AraSpellPostProcessor.HAMZA_WHITELIST:
                        expected = prefix + AraSpellPostProcessor.HAMZA_WHITELIST[remainder]
                        if corr_word == expected:
                            return 0.9
                        else:
                            logger.info(
                                f"[SPELLING] Prefixed whitelist mismatch: '{orig_word}'→'{corr_word}' "
                                f"(expected '{expected}') — rejected"
                            )
                            return 0.0
            # 5. FIX-02: Alif maqsura fix (ي↔ى at end) — both IV but correction is valid
            if (orig_word.endswith('ي') and corr_word.endswith('ى')
                    and orig_word[:-1] == corr_word[:-1]):
                return 0.85
            if (orig_word.endswith('ى') and corr_word.endswith('ي')
                    and orig_word[:-1] == corr_word[:-1]):
                return 0.85
            # ── Phase 12 (A7): Vocab-aware IV-IV override ──
            # Allow keyboard-adjacent single edits when correction is significantly
            # more common. Prevents blocking genuine typos where both happen to be IV.
            if len(orig_word) == len(corr_word):
                from nlp.spelling.araspell_rules import RulesBasedCorrector
                edit_dist = _levenshtein(orig_word, corr_word)
                if edit_dist == 1:
                    orig_rank = vocab_manager.get_frequency_rank(orig_word)
                    corr_rank = vocab_manager.get_frequency_rank(corr_word)
                    if corr_rank < orig_rank and corr_rank < 5000:
                        # Check keyboard proximity for extra safety
                        for a, b in zip(orig_word, corr_word):
                            if a != b:
                                if RulesBasedCorrector.is_keyboard_neighbor(a, b):
                                    logger.info(
                                        f"[SPELLING] Vocab-override (IV-IV): "
                                        f"'{orig_word}'(rank={orig_rank})→"
                                        f"'{corr_word}'(rank={corr_rank}) "
                                        f"keyboard-adjacent '{a}'→'{b}'"
                                    )
                                    return 0.5
                                break
            # 6. FIX-49: Trailing و removal (المصنعو→المصنع)
            # Common model artifact — original has trailing و that should be removed
            if (orig_word.endswith('و') and corr_word == orig_word[:-1]
                    and len(corr_word) >= 3):
                return 0.8
            # 7. FIX-49b: Trailing و→وا (حضرو→حضروا)
            # Missing alif after waw al-jama'a
            if (orig_word.endswith('و') and corr_word == orig_word + 'ا'
                    and len(orig_word) >= 3):
                return 0.8
            # Both are valid words and change is NOT a known fix — REJECT
            # This prevents وكان→وكأن, etc.
            return 0.0

    dist = _levenshtein(orig_word, corr_word)
    max_len = max(len(orig_word), len(corr_word))

    # Tighter filter for OOV words: reject edits that change word roots
    # Allow max 2 edits at max 50% of word length
    if dist > 2 or (dist / max_len) > 0.5:
        return 0.0

    # CRITICAL: Only allow ORTHOGRAPHIC fixes (ه↔ة, ا↔أ↔إ↔آ, ي↔ى).
    # Any other letter change means the word's ROOT is different
    # (e.g. عضلية→عملية ض→م = completely different word!)
    ORTHO_PAIRS = {
        ('ه', 'ة'), ('ة', 'ه'),
        ('ا', 'أ'), ('أ', 'ا'), ('ا', 'إ'), ('إ', 'ا'), ('ا', 'آ'), ('آ', 'ا'),
        ('ي', 'ى'), ('ى', 'ي'),
        ('ؤ', 'و'), ('و', 'ؤ'),  # hamza on waw
        ('ئ', 'ي'), ('ي', 'ئ'),  # hamza on ya
        ('ء', 'أ'), ('أ', 'ء'),  # standalone hamza ↔ hamza on alef
        ('ء', 'ؤ'), ('ؤ', 'ء'),  # standalone hamza ↔ hamza on waw
        ('ء', 'ئ'), ('ئ', 'ء'),  # standalone hamza ↔ hamza on ya
    }
    # ── Phase 12 (A2): Phonetically confusable pairs ──
    # Arabic letters commonly confused due to similar pronunciation.
    # From AraSpell.py ContextualCorrector.CONFUSION_PAIRS.
    PHONETIC_PAIRS = {
        ('ض', 'ظ'), ('ظ', 'ض'),  # emphatic d/z
        ('ذ', 'ز'), ('ز', 'ذ'),  # z variants
        ('ص', 'س'), ('س', 'ص'),  # s variants
        ('ط', 'ت'), ('ت', 'ط'),  # t variants
        ('ق', 'ك'), ('ك', 'ق'),  # k/q variants
        ('د', 'ض'), ('ض', 'د'),  # d/emphatic-d
        ('غ', 'ق'), ('ق', 'غ'),  # gh/q
    }

    from nlp.spelling.araspell_rules import RulesBasedCorrector

    # ── Phase 13: Adjacent character transposition detection ──
    # Transpositions (e.g., العصوبات→الصعوبات) have Levenshtein=2 but are a
    # single adjacent swap. Detect and accept when OOV→IV.
    if len(orig_word) == len(corr_word) and dist == 2:
        _transposition_found = False
        for _ti in range(len(orig_word) - 1):
            if (orig_word[_ti] == corr_word[_ti + 1] and
                orig_word[_ti + 1] == corr_word[_ti] and
                orig_word[:_ti] == corr_word[:_ti] and
                orig_word[_ti + 2:] == corr_word[_ti + 2:]):
                _transposition_found = True
                break
        if _transposition_found:
            if vocab_manager:
                _orig_oov = not vocab_manager.is_iv(orig_word)
                _corr_iv = vocab_manager.is_iv(corr_word)
                if _orig_oov and _corr_iv:
                    logger.info(
                        f"[SPELLING] Transposition accepted (OOV→IV): "
                        f"'{orig_word}'→'{corr_word}'"
                    )
                    return 0.6  # Dampened confidence for transpositions
                elif _orig_oov and not _corr_iv:
                    # Both OOV — still accept transposition with lower confidence
                    logger.info(
                        f"[SPELLING] Transposition accepted (OOV→OOV): "
                        f"'{orig_word}'→'{corr_word}' (low confidence)"
                    )
                    return 0.5
            else:
                return 0.6  # No vocab manager — accept with dampened confidence

    # ── Phase 13: Single character insertion detection ──
    # When the original has one extra character (user typed an extra letter),
    # e.g., الكتتاب→الكتاب (extra ت). Levenshtein=1, lengths differ by 1.
    if len(orig_word) == len(corr_word) + 1 and dist == 1:
        # Find where the extra character is in orig_word
        _insertion_valid = False
        for _di in range(len(orig_word)):
            # Try removing character at position _di from orig_word
            _candidate = orig_word[:_di] + orig_word[_di + 1:]
            if _candidate == corr_word:
                _insertion_valid = True
                break
        if _insertion_valid:
            if vocab_manager:
                _orig_oov = not vocab_manager.is_iv(orig_word)
                _corr_iv = vocab_manager.is_iv(corr_word)
                if _orig_oov and _corr_iv:
                    # FIX-35: Don't strip verb conjugation suffixes.
                    # Only block ن (feminine plural: ذهبن→ذهب) and
                    # ت (feminine past: كتبت→كتب) — these are the
                    # suffixes grammar commonly adds that spelling
                    # would try to strip. Other endings (ة,ا,ي,و,ه)
                    # are more likely genuine typos than grammar fixes.
                    _CONJUGATION_SUFFIXES = {'ن', 'ت'}
                    _removed_char = None
                    for _di2 in range(len(orig_word)):
                        if orig_word[:_di2] + orig_word[_di2 + 1:] == corr_word:
                            _removed_char = orig_word[_di2]
                            _removed_pos = _di2
                            break
                    if (_removed_char in _CONJUGATION_SUFFIXES
                            and _removed_pos == len(orig_word) - 1
                            and len(corr_word) >= 3):
                        logger.info(
                            f"[SPELLING] Rejected suffix strip: "
                            f"'{orig_word}'→'{corr_word}' "
                            f"(removing suffix '{_removed_char}' likely strips conjugation)"
                        )
                        return 0.0
                    logger.info(
                        f"[SPELLING] Insertion fix accepted (OOV→IV): "
                        f"'{orig_word}'→'{corr_word}' (extra char removed)"
                    )
                    return 0.7
            else:
                return 0.6

    # ── Phase 13: Single character deletion detection ──
    # When the original is missing one character (user missed a key),
    # e.g., الكتب→الكتاب (missing ا). Levenshtein=1, lengths differ by 1.
    if len(corr_word) == len(orig_word) + 1 and dist == 1:
        # Find where the missing character should be in corr_word
        _deletion_valid = False
        for _di in range(len(corr_word)):
            # Try removing character at position _di from corr_word
            _candidate = corr_word[:_di] + corr_word[_di + 1:]
            if _candidate == orig_word:
                _deletion_valid = True
                break
        if _deletion_valid:
            if vocab_manager:
                _orig_oov = not vocab_manager.is_iv(orig_word)
                _corr_iv = vocab_manager.is_iv(corr_word)
                if _orig_oov and _corr_iv:
                    logger.info(
                        f"[SPELLING] Deletion fix accepted (OOV→IV): "
                        f"'{orig_word}'→'{corr_word}' (missing char added)"
                    )
                    return 0.7
            else:
                return 0.6

    # Check every character pair — reject if ANY non-orthographic change
    if len(orig_word) != len(corr_word):
        # Length change = structural change, not just orthographic
        # Exception: if diff is just adding/removing ا at start (hamza)
        if abs(len(orig_word) - len(corr_word)) > 1:
            return 0.0

    # ── FIX: Block Grammar Changes masked as Spelling Typos (Dual → Plural) ──
    if orig_word.endswith('ان') and corr_word.endswith('ات') and orig_word[:-2] == corr_word[:-2]:
        logger.info(
            f"[SPELLING] Blocked grammatical change (Dual→Plural): "
            f"'{orig_word}'→'{corr_word}'"
        )
        return 0.0

    # ── Phase 12 (A1): Keyboard-neighbor and phonetic acceptance ──
    # Check each differing character: ortho → full accept, keyboard/phonetic → dampened
    _has_keyboard_or_phonetic = False
    for a, b in zip(orig_word, corr_word):
        if a != b:
            if (a, b) in ORTHO_PAIRS:
                continue  # Orthographic — fully accepted
            elif RulesBasedCorrector.is_keyboard_neighbor(a, b) or (a, b) in PHONETIC_PAIRS:
                _has_keyboard_or_phonetic = True  # Mark for dampened confidence
            else:
                return 0.0  # Not ortho, not keyboard, not phonetic → reject
    # If we reached here, all diffs are ortho or keyboard/phonetic
    if _has_keyboard_or_phonetic:
        logger.info(
            f"[SPELLING] Keyboard/phonetic typo accepted: "
            f"'{orig_word}'→'{corr_word}' (dampened to 0.6)"
        )
        return 0.6  # Dampened confidence for keyboard/phonetic typos

    # ── B3 (BUG-014/015): Pronoun suffix guard (OOV path) ──
    # Same guard as IV-IV path: block ه→ة when preceded by ت
    if (orig_word.endswith('ه') and corr_word.endswith('ة')
            and len(orig_word) >= 3 and orig_word[-2] == 'ت'
            and orig_word[:-1] == corr_word[:-1]):
        logger.info(
            f"[SPELLING] Blocked ه→ة at pronoun suffix (OOV path): "
            f"'{orig_word}'→'{corr_word}'"
        )
        return 0.0

    # ── Phase 2 (BUG-034/035/036/037/E8): Confidence dampening ──
    # If the original word might be a valid rare word (OOV in model but
    # potentially real Arabic), dampen confidence so users can reject easily.
    if vocab_manager:
        orig_iv = vocab_manager.is_iv(orig_word)
        corr_iv = vocab_manager.is_iv(corr_word)

        # Phase 2.2: Use frequency rank if available.
        # If the original word is a known word (even rare), require a
        # meaningfully higher confidence bar before replacing it.
        orig_rank = vocab_manager.get_frequency_rank(orig_word)  # 999999 if unknown
        corr_rank = vocab_manager.get_frequency_rank(corr_word)  # 999999 if unknown
        if orig_iv and corr_iv and orig_rank < 999999:
            # Original is a known ranked word — correction should be more common
            # If correction is rarer or similarly ranked, dampen confidence
            if corr_rank >= orig_rank:
                logger.info(
                    f"[SPELLING] Dampened (freq): '{orig_word}'(rank={orig_rank})"
                    f"→'{corr_word}'(rank={corr_rank}) — corr not more common"
                )
                return 0.5

        if not orig_iv and corr_iv:
            # OOV→IV: original might be a rare word being "corrected" to common
            # Dampen confidence to 0.5 (lower than normal 0.9)
            logger.info(
                f"[SPELLING] Dampened confidence: '{orig_word}'→'{corr_word}' "
                f"(OOV→IV, possible rare word)"
            )
            return 0.5

    # ── B2 (BUG-006/009/010/013): Hamza-removal dampening ──
    # Hamza changes (أ→ا, إ→ا, ء→ا, etc.) between same-length words are
    # ambiguous — could be a valid fix OR a corruption. Always dampen these
    # to 0.5 regardless of vocab_manager status. This prevents BUG-009
    # (قرأ→قرا) and BUG-013 (خطأ→خطا) from leaking at full confidence.
    _HAMZA_CHARS = set('أإآؤئء')
    if len(orig_word) == len(corr_word):
        has_hamza_diff = False
        for a, b in zip(orig_word, corr_word):
            if a != b:
                if a in _HAMZA_CHARS or b in _HAMZA_CHARS:
                    has_hamza_diff = True
                else:
                    has_hamza_diff = False
                    break  # Non-hamza difference, don't apply this guard
        if has_hamza_diff:
            logger.info(
                f"[SPELLING] Dampened (hamza-only): '{orig_word}'→'{corr_word}'"
            )
            return 0.5

    return 0.9


def _is_spelling_only_change(original: str, correction: str) -> bool:
    """
    Detect if a grammar model's correction is actually a spelling/orthographic fix
    (hamza, ه→ة, ا→أ, etc.) rather than a true grammar change.

    Used to re-label grammar patches as 'spelling' for correct UI icons.
    """
    if not original or not correction:
        return False

    # Normalize: strip diacritics for comparison
    strip_diacritics = lambda t: re.sub(r'[ً-ٰٟ]', '', t)
    o = strip_diacritics(original)
    c = strip_diacritics(correction)

    if o == c:
        return True  # Only diacritical difference

    # Check word-by-word for single-word changes
    o_words = o.split()
    c_words = c.split()

    if len(o_words) != len(c_words):
        return False  # Word count changed = grammar (word split/merge)

    all_spelling = True
    for ow, cw in zip(o_words, c_words):
        if ow == cw:
            continue
        if _is_orthographic_variant(ow, cw):
            continue
        all_spelling = False
        break

    return all_spelling


def _is_orthographic_variant(word1: str, word2: str) -> bool:
    """
    Check if two words differ only by common Arabic orthographic variations:
    - Hamza placement: ا↔أ↔إ↔آ, ى↔ي, ه↔ة
    - These are spelling differences, not grammar.
    """
    if len(word1) != len(word2):
        # Allow ه→ة at end (same length since both are 1 char)
        # But also allow small length diffs for hamza additions
        if abs(len(word1) - len(word2)) > 1:
            return False
        # Check if only difference is a trailing ة↔ه
        if (word1[:-1] == word2[:-1] and
                {word1[-1], word2[-1]} <= {'ه', 'ة'}):
            return True
        return False

    # Same length: check char-by-char
    SPELLING_EQUIVALENCES = {
        frozenset({'ا', 'أ'}), frozenset({'ا', 'إ'}), frozenset({'ا', 'آ'}),
        frozenset({'أ', 'إ'}), frozenset({'أ', 'آ'}), frozenset({'إ', 'آ'}),
        frozenset({'ى', 'ي'}), frozenset({'ه', 'ة'}),
        frozenset({'ؤ', 'و'}), frozenset({'ئ', 'ي'}), frozenset({'ئ', 'ء'}),
    }
    diff_count = 0
    for c1, c2 in zip(word1, word2):
        if c1 == c2:
            continue
        if frozenset({c1, c2}) in SPELLING_EQUIVALENCES:
            diff_count += 1
        else:
            return False  # Non-orthographic difference = grammar
    return diff_count > 0  # At least one orthographic difference
