import re
import time
import difflib
import logging
import traceback
from nlp.text_utils import get_word_positions, OffsetMapper, get_word_diffs, levenshtein as _levenshtein
from nlp.punctuation.punctuation_rules import validate_punctuation_diff
from services.spelling_filters import (
    _is_small_spelling_change,
    _is_spelling_only_change,
    _is_orthographic_variant,
    _DIRECTIONAL_BLOCKS,
)

logger = logging.getLogger(__name__)


def _get_spelling_alternatives(original_word, best_correction, spell_checker, max_alts=3):
    """Generate alternative spelling suggestions for a word."""
    alts = []
    seen = {best_correction, original_word}

    # 1. Try edit distance 1 candidates from the spell checker's vocabulary
    try:
        clean_w = re.sub(r'[^\w]', '', original_word)
        edit_cands = spell_checker.edit_corrector.known(spell_checker.edit_corrector.edits1(clean_w))
        if edit_cands:
            ranked = sorted(list(edit_cands), key=lambda x: spell_checker.vocab_manager.get_frequency_rank(x))
            for c in ranked:
                if c not in seen and len(alts) < max_alts - 1:
                    alts.append(c)
                    seen.add(c)
    except Exception:
        pass

    # 2. Always include 'keep as-is' as the last alternative
    # Return: [best_correction, alt1, alt2, ..., original_word(keep)]
    result = [best_correction] + alts + [original_word]
    return result[:max_alts + 1]  # cap at max_alts + keep-as-is


def _run_spelling_stage(ctx, original_text, timing_ms, tel_events, run_spelling, is_religious):
    """Execute spelling correction and OOV cleanup."""
    current_text = ctx.current_text
    # 1. Spelling (with conservative post-filtering to avoid over-editing)
    if run_spelling:
        try:
            t0 = time.time()
            logger.info(f"[ANALYZE] Step 1: Spelling correction starting...")
            from nlp.spelling.araspell_service import get_spelling_model
            spell_checker = get_spelling_model()
            raw_corrected = spell_checker.correct(current_text)
            timing_ms['spelling_ms'] = int((time.time() - t0) * 1000)
            logger.info(f"[ANALYZE] Step 1: Spelling done in {timing_ms['spelling_ms']}ms")

            # ── Phase 14 (FIX-31): Strip hallucinated trailing punctuation ──
            # The AraSpell model sometimes hallucinates trailing '...' or '.'
            # that weren't in the input. Strip them to prevent dot accumulation.
            # NOTE: Must .rstrip() first — model may add trailing whitespace
            # after dots, breaking the $ anchor.
            _rc_stripped = raw_corrected.rstrip()
            _ct_stripped = current_text.rstrip()
            _input_trailing = re.search(r'[\.،؛؟!]+$', _ct_stripped)
            _output_trailing = re.search(r'[\.،؛؟!]+$', _rc_stripped)
            if _output_trailing and not _input_trailing:
                raw_corrected = _rc_stripped[:_output_trailing.start()]
                logger.info(
                    f"[SPELLING] Stripped hallucinated trailing punct: "
                    f"'{_output_trailing.group()}'"
                )
            elif _output_trailing and _input_trailing:
                # If input had some trailing punct, preserve only what was there
                if len(_output_trailing.group()) > len(_input_trailing.group()):
                    raw_corrected = _rc_stripped[:_output_trailing.start()] + _input_trailing.group()
                    logger.info(
                        f"[SPELLING] Trimmed extra trailing punct: "
                        f"'{_output_trailing.group()}' → '{_input_trailing.group()}'"
                    )

            # ── Phase 12 (A4): Output Stability Test ──
            # If re-preprocessing the correction changes it significantly,
            # the correction is unstable → fall back to re-preprocessed version.
            if raw_corrected != current_text:
                try:
                    re_preprocessed = spell_checker.preprocess(raw_corrected)
                    _stab_dist = _levenshtein(
                        raw_corrected.replace(' ', ''),
                        re_preprocessed.replace(' ', '')
                    )
                    if _stab_dist > 0:
                        _stab_ratio = _stab_dist / max(len(raw_corrected), 1)
                        if _stab_ratio > 0.15:
                            logger.info(
                                f"[SPELLING] Unstable correction "
                                f"(ratio={_stab_ratio:.2f}), using preprocessed"
                            )
                            raw_corrected = re_preprocessed
                except Exception:
                    pass  # Stability check is optional

            if raw_corrected != ctx.current_text:
                orig_word_positions = get_word_positions(ctx.current_text)
                corr_word_positions = get_word_positions(raw_corrected)

                orig_word_strings = [w[0] for w in orig_word_positions]
                corr_word_strings = [w[0] for w in corr_word_positions]

                s = difflib.SequenceMatcher(None, orig_word_strings, corr_word_strings)
                new_words = []

                for tag, i1, i2, j1, j2 in s.get_opcodes():
                    if tag == 'equal':
                        start_idx = orig_word_positions[i1][1]
                        end_idx = orig_word_positions[i2-1][2]
                        new_words.append(current_text[start_idx:end_idx])
                    elif tag == 'replace':
                        o_segment = orig_word_strings[i1:i2]
                        c_segment = corr_word_strings[j1:j2]

                        start_idx = orig_word_positions[i1][1]
                        end_idx = orig_word_positions[i2-1][2]

                        if len(o_segment) == 1 and len(c_segment) == 1:
                            # 1-word → 1-word: accept only small edits (typos)
                            o_word = o_segment[0]
                            c_word = c_segment[0]
                            _spell_conf = _is_small_spelling_change(o_word, c_word, spell_checker.vocab_manager)
                            if _spell_conf:
                                # ── Phase 12 (A3): Keyboard proximity bonus ──
                                # Boost confidence for keyboard-adjacent typo fixes
                                if len(o_word) == len(c_word):
                                    from nlp.spelling.araspell_rules import RulesBasedCorrector
                                    for _oc, _cc in zip(o_word, c_word):
                                        if _oc != _cc and RulesBasedCorrector.is_keyboard_neighbor(_oc, _cc):
                                            _spell_conf = min(_spell_conf * 1.05, 0.95)
                                logger.info(f"[SPELLING] Accepted: '{o_word}'→'{c_word}' (conf={_spell_conf})")
                                new_words.append(c_word)
                                ctx.add_patch(
                                    'spelling', start_idx, end_idx,
                                    c_word, confidence=_spell_conf,
                                    alternatives=_get_spelling_alternatives(o_word, c_word, spell_checker),
                                )
                            else:
                                logger.info(f"[SPELLING] Rejected: '{o_word}'→'{c_word}' (filter blocked)")
                                new_words.append(current_text[start_idx:end_idx])
                        elif len(o_segment) == 1 and len(c_segment) > 1:
                            o_word = o_segment[0]

                            # FIX-021: AraSpell seq2seq sometimes detaches prefixes (e.g. بالشاروع -> ب الشارع)
                            # Re-attach known prefixes before processing the split
                            if len(c_segment) == 2 and c_segment[0] in {'ب', 'ف', 'ك', 'ل'}:
                                rejoined_word = "".join(c_segment)
                                _spell_conf = _is_small_spelling_change(o_word, rejoined_word, spell_checker.vocab_manager)
                                if _spell_conf:
                                    logger.info(f"[SPELLING] Re-attached prefix: '{o_word}'→'{rejoined_word}'")
                                    new_words.append(rejoined_word)
                                    ctx.add_patch(
                                        'spelling', start_idx, end_idx,
                                        rejoined_word, confidence=_spell_conf,
                                        alternatives=[rejoined_word, o_word],
                                    )
                                    continue

                            # 1-word → N words: accept word splits (e.g. فيالمدرسة → في المدرسة)
                            if len(o_word) >= 5 and ' ' not in o_word:
                                corr_str = " ".join(c_segment)
                                # ── Phase 3 (BUG-021/028/029): validate split parts ──
                                # Reject splits where any part is a dangling fragment
                                _VALID_SINGLE_CHAR = {'و', 'ب', 'ل', 'ك', 'ف', 'أ'}
                                _parts_ok = all(
                                    len(p) >= 2 or p in _VALID_SINGLE_CHAR
                                    for p in c_segment
                                )
                                # Phase 3.2: Reject splits that detach known pronoun suffixes
                                # from nouns (e.g. مستشفياتهم → مستشفيات هم is WRONG)
                                _ATTACHED_PRONOUNS = {
                                    'هم', 'هن', 'ها', 'هما', 'كم', 'كن', 'نا',
                                    'ه', 'ك',  # single-char pronouns
                                }
                                if _parts_ok and len(c_segment) >= 2:
                                    last_part = c_segment[-1]
                                    if last_part in _ATTACHED_PRONOUNS:
                                        # Check if joined form ≈ original (pronoun was attached)
                                        joined_no_space = ''.join(c_segment)
                                        if _levenshtein(o_word, joined_no_space) <= 2:
                                            _parts_ok = False
                                            logger.info(
                                                f"[SPELLING] Rejected split: '{o_word}'→'{corr_str}' "
                                                f"(detached pronoun suffix '{last_part}')"
                                            )
                                    elif len(c_segment) >= 2:
                                        for idx, p in enumerate(c_segment):
                                            if p in {'و', 'ف', 'ب', 'ل', 'ك'} and idx > 0:
                                                _parts_ok = False
                                                logger.info(
                                                    f"[SPELLING] Rejected split: '{o_word}'→'{corr_str}' "
                                                    f"(invalid standalone conjunction '{p}' inside split)"
                                                )
                                                break
                                if _parts_ok:
                                    new_words.append(corr_str)
                                    ctx.add_patch(
                                        'spelling', start_idx, end_idx,
                                        corr_str, confidence=0.85,
                                        alternatives=[corr_str, o_word],
                                    )
                                else:
                                    logger.info(
                                        f"[SPELLING] Rejected split: '{o_word}'→'{corr_str}' "
                                        f"(dangling fragment in parts: {c_segment})"
                                    )
                                    new_words.append(current_text[start_idx:end_idx])
                            else:
                                new_words.append(current_text[start_idx:end_idx])
                        else:
                            # N→M replacement: process each original word individually
                            # Build a mapping by trying to match original words to corrected words
                            corr_joined = " ".join(c_segment)
                            ci = 0  # cursor into c_segment
                            for oi in range(i1, i2):
                                o_word = orig_word_strings[oi]
                                o_start = orig_word_positions[oi][1]
                                o_end = orig_word_positions[oi][2]

                                if ci < len(c_segment):
                                    c_word = c_segment[ci]
                                    # Check if this is a 1→1 small edit
                                    _spell_conf2 = _is_small_spelling_change(o_word, c_word, spell_checker.vocab_manager)
                                    if _spell_conf2:
                                        new_words.append(c_word)
                                        ctx.add_patch(
                                            'spelling', o_start, o_end,
                                            c_word, confidence=_spell_conf2,
                                            alternatives=_get_spelling_alternatives(o_word, c_word, spell_checker),
                                        )
                                        ci += 1
                                    # Check if this is a 1→N word split
                                    elif len(o_word) >= 5 and ci + 1 < len(c_segment):
                                        # Try to consume multiple corrected words for this one original word
                                        split_parts = [c_segment[ci]]
                                        temp_ci = ci + 1
                                        joined = c_segment[ci]
                                        while temp_ci < len(c_segment) and len(joined) < len(o_word) + 2:
                                            joined += c_segment[temp_ci]
                                            split_parts.append(c_segment[temp_ci])
                                            temp_ci += 1
                                        # Check if the joined parts roughly match the original
                                        corr_str = " ".join(split_parts)
                                        joined_no_space = "".join(split_parts)
                                        dist = _levenshtein(o_word, joined_no_space)
                                        # ── Phase 3 (BUG-021/028/029): validate split parts ──
                                        _VALID_SC = {'و', 'ب', 'ل', 'ك', 'ف', 'أ'}
                                        _parts_ok = all(
                                            len(p) >= 2 or p in _VALID_SC
                                            for p in split_parts
                                        )
                                        # Phase 3.2: Reject splits detaching pronoun suffixes
                                        _ATTACHED_PRON = {
                                            'هم', 'هن', 'ها', 'هما', 'كم', 'كن', 'نا',
                                            'ه', 'ك',
                                        }
                                        if _parts_ok and len(split_parts) >= 2:
                                            for idx, p in enumerate(split_parts):
                                                if p in {'و', 'ف', 'ب', 'ل', 'ك'} and idx > 0:
                                                    _parts_ok = False
                                                    logger.info(
                                                        f"[SPELLING] Rejected N→M split: '{o_word}'→'{corr_str}' "
                                                        f"(invalid standalone conjunction '{p}' inside split)"
                                                    )
                                                    break

                                        if _parts_ok and len(split_parts) == 2:
                                            if split_parts[-1] in _ATTACHED_PRON:
                                                if _levenshtein(o_word, joined_no_space) <= 2:
                                                    _parts_ok = False
                                                    logger.info(
                                                        f"[SPELLING] Rejected N→M split: '{o_word}'→'{corr_str}' "
                                                        f"(detached pronoun suffix '{split_parts[-1]}')"
                                                    )
                                        if dist <= 3 and len(split_parts) > 1 and _parts_ok:
                                            new_words.append(corr_str)
                                            ctx.add_patch(
                                                'spelling', o_start, o_end,
                                                corr_str, confidence=0.85,
                                                alternatives=[corr_str, o_word],
                                            )
                                            ci = temp_ci
                                        else:
                                            if not _parts_ok:
                                                logger.info(
                                                    f"[SPELLING] Rejected N→M split: '{o_word}'→'{corr_str}' "
                                                    f"(dangling fragment)"
                                                )
                                            new_words.append(current_text[o_start:o_end])
                                            ci += 1
                                    else:
                                        new_words.append(current_text[o_start:o_end])
                                        ci += 1
                                else:
                                    new_words.append(current_text[o_start:o_end])
                    elif tag == 'delete':
                        for idx in range(i1, i2):
                            new_words.append(current_text[orig_word_positions[idx][1]:orig_word_positions[idx][2]])
                    elif tag == 'insert':
                        continue

                safe_text = " ".join(new_words)

                # ── Phase 12 (A5): Bidirectional Word Validation ──
                # Compare assembled result with raw model output word-by-word.
                # If our pipeline corrupted a word the model got right, revert it.
                try:
                    _safe_words = safe_text.split()
                    _raw_words = raw_corrected.split()
                    if len(_safe_words) == len(_raw_words):
                        _bidi_changed = False
                        for _bi in range(len(_safe_words)):
                            if _safe_words[_bi] != _raw_words[_bi]:
                                _sw_iv = spell_checker.vocab_manager.is_iv(_safe_words[_bi])
                                _rw_iv = spell_checker.vocab_manager.is_iv(_raw_words[_bi])
                                # Our word is OOV but model's word is IV → take model's
                                if not _sw_iv and _rw_iv:
                                    # ── FIX-28a: Digit guard for bidirectional path ──
                                    # Numbers (2020, 150, etc.) are OOV but must NOT be
                                    # replaced with Arabic words (يناير, خمسين).
                                    _BIDI_DIGITS = set('0123456789٠١٢٣٤٥٦٧٨٩')
                                    if any(c in _BIDI_DIGITS for c in _safe_words[_bi]):
                                        logger.info(
                                            f"[SPELLING] Bidirectional blocked (digit): "
                                            f"'{_safe_words[_bi]}'→'{_raw_words[_bi]}'"
                                        )
                                        continue
                                    # ── FIX-28b: Prefix-change guard ──
                                    # Prevent changing leading clitics: فبالتالي→وبالتالي
                                    # If the words share the same stem but differ only in
                                    # the leading prefix (و↔ف↔ب↔ل↔ك), reject.
                                    _CLITIC_PFX = ('و', 'ف', 'ب', 'ل', 'ك')
                                    _sw = _safe_words[_bi]
                                    _rw = _raw_words[_bi]
                                    if (len(_sw) > 3 and len(_rw) > 3
                                            and _sw[0] in _CLITIC_PFX and _rw[0] in _CLITIC_PFX
                                            and _sw[0] != _rw[0] and _sw[1:] == _rw[1:]):
                                        logger.info(
                                            f"[SPELLING] Bidirectional blocked (prefix swap): "
                                            f"'{_sw}'→'{_rw}'"
                                        )
                                        continue
                                    # ── FIX-43: Validate bidirectional fix through spelling guard ──
                                    # The bidirectional path bypassed ALL spelling guards (FIX-42b first-letter,
                                    # FIX-42a length ratio, FIX-39 edit distance). Now we validate the
                                    # OOV→IV replacement through _is_small_spelling_change to catch corruptions
                                    # like واحتاج→وتحتاج, افهمه→تفهمة, والممرضات→والرضا.
                                    _bidi_spell_conf = _is_small_spelling_change(
                                        _safe_words[_bi], _raw_words[_bi],
                                        spell_checker.vocab_manager
                                    )
                                    if not _bidi_spell_conf:
                                        logger.info(
                                            f"[SPELLING] Bidirectional blocked (spelling guard): "
                                            f"'{_safe_words[_bi]}'→'{_raw_words[_bi]}'"
                                        )
                                        continue
                                    logger.info(
                                        f"[SPELLING] Bidirectional fix: "
                                        f"'{_safe_words[_bi]}'(OOV)→'{_raw_words[_bi]}'(IV)"
                                    )
                                    # ── Phase 13: Create patch for bidirectional fix ──
                                    # Find this word's position in the ORIGINAL text so the
                                    # user sees the correction as a suggestion in the UI.
                                    try:
                                        _orig_words_list = original_text.split()
                                        if _bi < len(_orig_words_list):
                                            _bidi_orig_word = _orig_words_list[_bi]
                                            # Only create patch if the original word matches
                                            # (bidirectional fix is correcting a filter-rejected word)
                                            if _bidi_orig_word == _safe_words[_bi]:
                                                _bidi_pos = 0
                                                for _bw_idx in range(_bi):
                                                    _next_pos = original_text.find(_orig_words_list[_bw_idx], _bidi_pos)
                                                    if _next_pos >= 0:
                                                        _bidi_pos = _next_pos + len(_orig_words_list[_bw_idx])
                                                _bidi_start = original_text.find(_bidi_orig_word, max(0, _bidi_pos))
                                                if _bidi_start >= 0:
                                                    _bidi_end = _bidi_start + len(_bidi_orig_word)
                                                    ctx.add_patch(
                                                        'spelling', _bidi_start, _bidi_end,
                                                        _raw_words[_bi], confidence=0.6,
                                                        alternatives=[_raw_words[_bi], _bidi_orig_word],
                                                    )
                                    except Exception:
                                        pass  # Patch creation is best-effort
                                    _safe_words[_bi] = _raw_words[_bi]
                                    _bidi_changed = True
                        if _bidi_changed:
                            _new_safe = ' '.join(_safe_words)
                            _new_oov = spell_checker.vocab_manager.count_oov_words(_new_safe)
                            _old_oov = spell_checker.vocab_manager.count_oov_words(safe_text)
                            if _new_oov <= _old_oov:
                                safe_text = _new_safe
                except Exception:
                    pass  # Bidirectional check is optional

                ctx.mutate_text(safe_text, OffsetMapper)
                current_text = ctx.current_text
        except Exception as e:
            logger.error(f"[ANALYZE] Spelling failed: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            timing_ms['spelling_error'] = f"{type(e).__name__}: {str(e)[:200]}"

    # ── FIX-44: OOV Cleanup Pass (between spelling and grammar) ──
    # After spelling corrections, some OOV words remain because:
    # 1. The model didn't correct them (missed)
    # 2. Our guards blocked a bad correction (but word is still OOV)
    # 3. Trailing و artifacts from model output
    #
    # For each remaining OOV word, try to find the closest IV word
    # using edit-distance-1 candidates from BERT vocabulary.
    if not is_religious:
      try:
        from nlp.spelling.araspell_service import get_spelling_model
        _oov_checker = get_spelling_model()
        _oov_text = ctx.current_text
        _oov_words = _oov_text.split()
        _oov_changed = False
        _oov_result = []

        for _ow_idx, _ow in enumerate(_oov_words):
            # Skip short words (prepositions etc.)
            if len(_ow) <= 2:
                _oov_result.append(_ow)
                continue

            # Strip trailing punctuation for IV check
            _ow_clean = _ow.rstrip('.،؛؟!?!')

            # Skip if already IV
            if _oov_checker.vocab_manager.is_iv(_ow_clean):
                _oov_result.append(_ow)
                continue

            _punct_suffix = _ow[len(_ow_clean):]  # preserve punctuation

            # ── FIX-46a: ه→ة fix (vocab-validated) ──
            # الحكومه→الحكومة, الشركه→الشركة, المدرسه→المدرسة
            if len(_ow_clean) >= 4 and _ow_clean.endswith('ه'):
                _ta_cand = _ow_clean[:-1] + 'ة'
                if _oov_checker.vocab_manager.is_iv(_ta_cand):
                    logger.info(
                        f"[OOV-CLEANUP] ه→ة fix: '{_ow}'→'{_ta_cand}{_punct_suffix}'"
                    )
                    _oov_result.append(_ta_cand + _punct_suffix)
                    _oov_changed = True
                    _ow_pos = sum(len(w) + 1 for w in _oov_words[:_ow_idx])
                    if _ow_pos + len(_ow) <= len(_oov_text):
                        ctx.add_patch(
                            'spelling', _ow_pos, _ow_pos + len(_ow),
                            _ta_cand + _punct_suffix, confidence=0.8,
                        )
                    continue

            # ── FIX-46b: Trailing و removal (expanded) ──
            # المصنعو→المصنع, الماضيةو→الماضية
            # Expanded char set: ANY Arabic letter before و (if result is IV)
            if len(_ow_clean) > 4 and _ow_clean.endswith('و'):
                _wo_cand = _ow_clean[:-1]
                if _oov_checker.vocab_manager.is_iv(_wo_cand):
                    logger.info(
                        f"[OOV-CLEANUP] Trailing و fix: '{_ow}'→'{_wo_cand}{_punct_suffix}'"
                    )
                    _oov_result.append(_wo_cand + _punct_suffix)
                    _oov_changed = True
                    _ow_pos = sum(len(w) + 1 for w in _oov_words[:_ow_idx])
                    if _ow_pos + len(_ow) <= len(_oov_text):
                        ctx.add_patch(
                            'spelling', _ow_pos, _ow_pos + len(_ow),
                            _wo_cand + _punct_suffix, confidence=0.75,
                        )
                    continue

                # ── FIX-46c: Trailing و→وا for verbs ──
                # حضرو→حضروا, صممو→صمموا (missing alif)
                _woa_cand = _ow_clean + 'ا'
                if _oov_checker.vocab_manager.is_iv(_woa_cand):
                    logger.info(
                        f"[OOV-CLEANUP] و→وا fix: '{_ow}'→'{_woa_cand}{_punct_suffix}'"
                    )
                    _oov_result.append(_woa_cand + _punct_suffix)
                    _oov_changed = True
                    _ow_pos = sum(len(w) + 1 for w in _oov_words[:_ow_idx])
                    if _ow_pos + len(_ow) <= len(_oov_text):
                        ctx.add_patch(
                            'spelling', _ow_pos, _ow_pos + len(_ow),
                            _woa_cand + _punct_suffix, confidence=0.7,
                        )
                    continue

            # ── FIX-46d: Handle .و pattern ──
            # الدروس.و→الدروس (period + و artifact)
            if _ow.endswith('.و') or _ow.endswith('،و'):
                _dotwo_cand = _ow[:-2]  # remove both . and و
                _dotwo_clean = _dotwo_cand.rstrip('.،؛؟!?!')
                if len(_dotwo_clean) >= 3 and _oov_checker.vocab_manager.is_iv(_dotwo_clean):
                    logger.info(
                        f"[OOV-CLEANUP] .و artifact fix: '{_ow}'→'{_dotwo_clean}.'"
                    )
                    _oov_result.append(_dotwo_clean + '.')
                    _oov_changed = True
                    _ow_pos = sum(len(w) + 1 for w in _oov_words[:_ow_idx])
                    if _ow_pos + len(_ow) <= len(_oov_text):
                        ctx.add_patch(
                            'spelling', _ow_pos, _ow_pos + len(_ow),
                            _dotwo_clean + '.', confidence=0.75,
                        )
                    continue

            _oov_result.append(_ow)

        if _oov_changed:
            _oov_new_text = ' '.join(_oov_result)
            logger.info(f"[OOV-CLEANUP] Applied OOV fixes: '{_oov_text[:80]}' → '{_oov_new_text[:80]}'")
            ctx.mutate_text(_oov_new_text, OffsetMapper)
            current_text = ctx.current_text

      except Exception as e:
        logger.warning(f"[OOV-CLEANUP] Failed: {type(e).__name__}: {e}")




def _run_grammar_stage(ctx, timing_ms, tel_events, is_religious):
    """Execute grammar correction with structured content protection."""
    if is_religious:
        return
    current_text = ctx.current_text
    # ── FIX-03: Structured content protection ──
    # Protect URLs, emails, dates, code etc. from grammar model destruction
    _PROTECTED_PATTERNS = [
        r'https?://\S+',           # URLs
        r'\S+@\S+\.\S+',           # Emails
        r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}',  # Dates
        r'\d{1,2}:\d{2}',          # Times
        r'#[؀-ۿ\w]+',     # Hashtags
        r'@[\w]+',                 # Mentions
        r'\+?\d{10,13}',           # Phone numbers
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}',  # IP addresses
        r'v\d+\.\d+\.\d+',         # Version numbers
    ]
    _structured_placeholders = []  # (start, end, original_text, label)
    _grammar_input_text = ctx.current_text
    if not is_religious:
        for _pat in _PROTECTED_PATTERNS:
            for _m in re.finditer(_pat, _grammar_input_text):
                _structured_placeholders.append((_m.start(), _m.end(), _m.group()))
        # Replace structured content with Arabic placeholder tokens
        if _structured_placeholders:
            _structured_placeholders.sort(key=lambda x: x[0], reverse=True)
            for _sp_start, _sp_end, _sp_text in _structured_placeholders:
                _grammar_input_text = _grammar_input_text[:_sp_start] + 'بيان' + _grammar_input_text[_sp_end:]
            logger.info(f"[ANALYZE] Protected {len(_structured_placeholders)} structured elements")

    # 2. Grammar (runs on spelling-corrected text — word-level dependency)
    if not is_religious:
      try:
        t0 = time.time()
        logger.info(f"[ANALYZE] Step 2: Grammar correction starting...")
        from nlp.grammar.grammar_service import get_grammar_model
        grammar_checker = get_grammar_model()
        corrected_grammar = grammar_checker.correct(_grammar_input_text)
        timing_ms['grammar_ms'] = int((time.time() - t0) * 1000)
        logger.info(f"[ANALYZE] Step 2: Grammar done in {timing_ms['grammar_ms']}ms")

        # ── Phase 11: Telemetry — raw grammar output ──
        import json as _tel_json
        logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"grammar_raw_output","input":_grammar_input_text[:200],"output":corrected_grammar[:200]})}')
        tel_events.append({"event":"grammar_raw_output","input":_grammar_input_text[:200],"output":corrected_grammar[:200]})

        # FIX-03: Restore structured content in grammar output
        if _structured_placeholders:
            # Restore in forward order
            for _sp_start, _sp_end, _sp_text in reversed(_structured_placeholders):
                corrected_grammar = corrected_grammar.replace('بيان', _sp_text, 1)

        if corrected_grammar != ctx.current_text:
            diffs = get_word_diffs(ctx.current_text, corrected_grammar)
            _grammar_accepted_diffs = []  # FIX-04: track accepted diffs
            _grammar_total_diffs = len(diffs)
            logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"grammar_diffs_extracted","count":_grammar_total_diffs})}')
            tel_events.append({"event":"grammar_diffs_extracted","count":_grammar_total_diffs})
            for d in diffs:
                orig_text = d.get('original', '')
                corr_text = d.get('correction', '')
                logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"grammar_diff","original":orig_text[:80],"correction":corr_text[:80],"start":d["start"],"end":d["end"]})}')
                tel_events.append({"event":"grammar_diff","original":orig_text[:80],"correction":corr_text[:80],"start":d["start"],"end":d["end"]})

                # Evaluate grammar patterns early to bypass heuristic blocks.
                _is_grammar_pattern = False
                if orig_text and corr_text:
                    _o_cl = orig_text.rstrip('.,،؛;:!؟?()[]{}«»"\'…')
                    _c_cl = corr_text.rstrip('.,،؛;:!؟?()[]{}«»"\'…')

                    # Priority 4: Diacritic-Normalized Grammar Validation
                    _o_cl = re.sub(r'[ً-ٰٟ]', '', _o_cl)
                    _c_cl = re.sub(r'[ً-ٰٟ]', '', _c_cl)

                    # Case: ون/ان → ين (sound masculine plural / dual case change)
                    if (_o_cl.endswith('ون') and _c_cl.endswith('ين') and _o_cl[:-2] == _c_cl[:-2]):
                        _is_grammar_pattern = True
                    elif (_o_cl.endswith('ان') and _c_cl.endswith('ين') and _o_cl[:-2] == _c_cl[:-2] and len(_o_cl) >= 4):
                        _is_grammar_pattern = True
                    # Nasb/Jazm: ون → وا (verb mood)
                    elif (_o_cl.endswith('ون') and _c_cl.endswith('وا') and len(_o_cl) >= 3):
                        _o_stem = _o_cl[:-2]
                        _c_stem = _c_cl[:-2]
                        if _o_stem == _c_stem or (len(_o_stem) > 1 and _o_stem[1:] == _c_stem[1:] and _o_stem[0] in 'يت' and _c_stem[0] in 'يت'):
                            _is_grammar_pattern = True
                    # Five nouns: وك → اك/يك
                    elif (len(_o_cl) >= 3 and len(_c_cl) >= 3 and _o_cl[-2:] in ('وك', 'وه', 'يك', 'يه') and _c_cl[-2:] in ('اك', 'اه', 'وك', 'وه', 'يك', 'يه')):
                        if _o_cl[:-2] == _c_cl[:-2]:
                            _is_grammar_pattern = True
                    # Demonstrative: هذان→هاتان, هاتان→هذان
                    elif ({_o_cl, _c_cl} <= {'هذان', 'هاتان'}):
                        _is_grammar_pattern = True
                    # Past tense masc plural: verb→verb+وا
                    elif (_c_cl.endswith('وا') and _c_cl[:-2] == _o_cl and len(_o_cl) >= 3):
                        _is_grammar_pattern = True
                    # Past tense masc plural replacement (Collision Fixes): ت/ن/ى/ة → وا
                    elif (_c_cl.endswith('وا') and _o_cl[-1:] in ('ت', 'ن', 'ى', 'ة', 'و') and _c_cl[:-2] == _o_cl[:-1] and len(_o_cl) >= 3):
                        _is_grammar_pattern = True
                    # Past tense masc plural replacement: ون/ين/ان → وا
                    elif (_c_cl.endswith('وا') and _o_cl[-2:] in ('ون', 'ين', 'ان') and _c_cl[:-2] == _o_cl[:-2] and len(_o_cl) >= 4):
                        _is_grammar_pattern = True
                    # Past tense fem plural: verb→verb+ن
                    elif (_c_cl.endswith('ن') and _c_cl[:-1] == _o_cl and len(_o_cl) >= 3):
                        _is_grammar_pattern = True
                    # Past tense fem plural replacement (Collision Fixes): ت/ى/ة/و → ن
                    elif (_c_cl.endswith('ن') and _o_cl[-1:] in ('ت', 'ى', 'ة', 'و') and _c_cl[:-1] == _o_cl[:-1] and len(_o_cl) >= 3):
                        _is_grammar_pattern = True
                    # Past tense fem plural replacement: وا/ون/ين/ان → ن
                    elif (_c_cl.endswith('ن') and _o_cl[-2:] in ('وا', 'ون', 'ين', 'ان') and _c_cl[:-1] == _o_cl[:-2] and len(_o_cl) >= 4):
                        _is_grammar_pattern = True
                    # Present tense fem plural: ون → ن
                    elif (_o_cl.endswith('ون') and _c_cl.endswith('ن') and len(_o_cl) >= 3):
                        _o_stem = _o_cl[:-2]
                        _c_stem = _c_cl[:-1]
                        if _o_stem == _c_stem or (len(_o_stem) > 1 and _o_stem[1:] == _c_stem[1:] and _o_stem[0] in 'يت' and _c_stem[0] in 'يت'):
                            _is_grammar_pattern = True
                    # Masc Plural Addition: +ون
                    elif (_c_cl.endswith('ون') and _c_cl[:-2] == _o_cl and len(_o_cl) >= 3):
                        _is_grammar_pattern = True
                    # Dual Addition: +ان or +ين
                    elif ((_c_cl.endswith('ان') or _c_cl.endswith('ين')) and _c_cl[:-2] == _o_cl and len(_o_cl) >= 3):
                        _is_grammar_pattern = True
                    # Feminine Dual Addition: +تان / +تين
                    elif (_c_cl.endswith('تان') or _c_cl.endswith('تين')):
                        if _o_cl.endswith('ة') and _c_cl[:-3] == _o_cl[:-1] and len(_o_cl) >= 3:
                            _is_grammar_pattern = True
                        elif _c_cl[:-3] == _o_cl and len(_o_cl) >= 3:
                            _is_grammar_pattern = True
                    # Feminine Plural Addition: +ات
                    elif (_c_cl.endswith('ات') and len(_c_cl) >= 4):
                        if _o_cl.endswith('ة') and _c_cl[:-2] == _o_cl[:-1]:
                            _is_grammar_pattern = True
                        elif _c_cl[:-2] == _o_cl:
                            _is_grammar_pattern = True
                    # Gender: +ة (جميل→جميلة)
                    elif (_c_cl.endswith('ة') and _c_cl[:-1] == _o_cl and len(_o_cl) >= 3):
                        _is_grammar_pattern = True
                    # Gender with ي: ذكي→ذكية
                    elif (_c_cl.endswith('ية') and _c_cl[:-1] == _o_cl[:-1] + 'ي' and _o_cl.endswith('ي') and len(_o_cl) >= 3):
                        _is_grammar_pattern = True
                    # Pronoun gender agreement: ه/ة → ها
                    elif (_c_cl.endswith('ها') and _o_cl[-1:] in ('ه', 'ة') and _c_cl[:-2] == _o_cl[:-1] and len(_o_cl) >= 3):
                        _is_grammar_pattern = True
                    # Pronoun gender agreement: ها → ه
                    elif (_c_cl.endswith('ه') and _o_cl.endswith('ها') and _c_cl[:-1] == _o_cl[:-2] and len(_o_cl) >= 4):
                        _is_grammar_pattern = True

                # StageLocker: skip diffs that overlap with locked ranges
                # Phase 11: Hierarchy-aware — grammar (3) overrides spelling (2)
                # Phase 15: Bypass StageLocker entirely for valid Grammar S-V patches to fix collisions
                if not _is_grammar_pattern and ctx.stage_locker.is_locked_for(d['start'], d['end'], 'grammar'):
                    logger.info(
                        f"[LOCK] Grammar blocked on [{d['start']}:{d['end']}] "
                        f"'{d.get('original','')}' — locked by equal/higher priority stage"
                    )
                    logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"filter_reject","filter":"StageLocker","original":orig_text[:80],"correction":corr_text[:80]})}')
                    tel_events.append({"event":"filter_reject","filter":"StageLocker","original":orig_text[:80],"correction":corr_text[:80]})
                    continue

                # Reject grammar hallucinations (e.g. جالس→جاكسون)
                if orig_text and corr_text:
                    orig_chars = set(orig_text.replace(' ', ''))
                    corr_chars = set(corr_text.replace(' ', ''))
                    if orig_chars and corr_chars:
                        jaccard = len(orig_chars & corr_chars) / len(orig_chars | corr_chars)
                        if jaccard < 0.3:
                            logger.info(
                                f"[GRAMMAR] Rejected hallucination: '{orig_text}'→'{corr_text}' "
                                f"(jaccard={jaccard:.2f})"
                            )
                            logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"filter_reject","filter":"Jaccard_03","original":orig_text[:80],"correction":corr_text[:80],"jaccard":round(jaccard,3)})}')
                            tel_events.append({"event":"filter_reject","filter":"Jaccard_03","original":orig_text[:80],"correction":corr_text[:80],"jaccard":round(jaccard,3)})
                            continue

                # Reject dialect/hallucination verb suffixes like "تون"
                if orig_text and corr_text:
                    _c_clean = corr_text.rstrip('.,،؛;:!؟?()[]{}«»"\'…')
                    _o_clean = orig_text.rstrip('.,،؛;:!؟?()[]{}«»"\'…')
                    if _c_clean.endswith('تون') and not _o_clean.endswith('تون'):
                        logger.info(f"[GRAMMAR] Rejected hallucination: '{orig_text}'→'{corr_text}' (invalid suffix 'تون')")
                        continue

                # ── FIX-13: Named entity protection ──
                # Reject grammar changes to words that look like proper nouns:
                # - Title case Latin words (proper nouns in mixed text)
                # - Single words where the grammar just adds/removes spaces
                if orig_text and corr_text:
                    # If original has no spaces but correction does (grammar split a name)
                    _has_latin = any('A' <= c <= 'Z' or 'a' <= c <= 'z' for c in orig_text)
                    if _has_latin and orig_text != corr_text:
                        logger.info(
                            f"[GRAMMAR] Skipping entity (contains Latin): "
                            f"'{orig_text}'→'{corr_text}'"
                        )
                        logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"filter_reject","filter":"LatinGuard","original":orig_text[:80],"correction":corr_text[:80]})}')
                        tel_events.append({"event":"filter_reject","filter":"LatinGuard","original":orig_text[:80],"correction":corr_text[:80]})
                        continue

                # ── FIX-22: Emoji protection ──
                # Don't let grammar split/modify emoji sequences
                if orig_text and re.search(r'[\U0001F300-\U0001F9FF]', orig_text):
                    logger.info(
                        f"[GRAMMAR] Skipping emoji content: '{orig_text}'"
                    )
                    continue

                # ── FIX-23: Tanween removal blocker ──
                # The grammar model often strips tanween (ً/ٌ/ٍ) from correct text.
                # Block diffs where the only change is tanween removal.
                if orig_text and corr_text:
                    _TANWEEN = 'ًٌٍ'  # ً ٌ ٍ
                    _orig_no_tnwn = re.sub(f'[{_TANWEEN}]', '', orig_text)
                    _corr_no_tnwn = re.sub(f'[{_TANWEEN}]', '', corr_text)
                    if _orig_no_tnwn == _corr_no_tnwn and orig_text != corr_text:
                        logger.info(
                            f"[GRAMMAR] Blocked tanween removal: "
                            f"'{orig_text}'→'{corr_text}'"
                        )
                        logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"filter_reject","filter":"TanweenGuard","original":orig_text[:80],"correction":corr_text[:80]})}')
                        tel_events.append({"event":"filter_reject","filter":"TanweenGuard","original":orig_text[:80],"correction":corr_text[:80]})
                        continue

                # ── FIX-24: Grammar punctuation stripping blocker ──
                # The grammar model removes periods/punctuation from end of text.
                # e.g., 'البلاد.' → 'البلاد' — this is WRONG, the period is correct.
                # Block diffs where the only change is punctuation removal/addition.
                if orig_text and corr_text:
                    _PUNCT_CHARS = '.,،؛;:!؟?()[]{}«»"\'…'
                    _orig_stripped = orig_text.strip(_PUNCT_CHARS)
                    _corr_stripped = corr_text.strip(_PUNCT_CHARS)
                    if _orig_stripped == _corr_stripped and orig_text != corr_text:
                        logger.info(
                            f"[GRAMMAR] Blocked punct stripping: "
                            f"'{orig_text}'→'{corr_text}'"
                        )
                        logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"filter_reject","filter":"PunctuationGuard","original":orig_text[:80],"correction":corr_text[:80]})}')
                        tel_events.append({"event":"filter_reject","filter":"PunctuationGuard","original":orig_text[:80],"correction":corr_text[:80]})
                        continue
                    # Also block combined tanween + punct stripping
                    _TANWEEN2 = 'ًٌٍ'
                    _orig_clean = re.sub(f'[{_TANWEEN2}]', '', _orig_stripped)
                    _corr_clean = re.sub(f'[{_TANWEEN2}]', '', _corr_stripped)
                    if _orig_clean == _corr_clean and orig_text != corr_text:
                        logger.info(
                            f"[GRAMMAR] Blocked tanween+punct strip: "
                            f"'{orig_text}'→'{corr_text}'"
                        )
                        logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"filter_reject","filter":"PunctuationGuard","original":orig_text[:80],"correction":corr_text[:80]})}')
                        tel_events.append({"event":"filter_reject","filter":"PunctuationGuard","original":orig_text[:80],"correction":corr_text[:80]})
                        continue

                # ── FIX-25: Grammar punctuation spacing blocker ──
                # The grammar model inserts spaces around punctuation:
                # e.g., 'حالك؟' → 'حالك ؟', 'المكتبة،' → 'المكتبة ،'
                # Block diffs where the only change is spacing around punct.
                if orig_text and corr_text:
                    # Normalize: collapse spaces around common punct marks
                    def _norm_punct_spacing(t):
                        # Remove spaces before/after common punct
                        t = re.sub(r'\s+([.,:;!?،؛؟!%$)}\]>])', r'\1', t)
                        t = re.sub(r'([({\[<])\s+', r'\1', t)
                        return t
                    _orig_normed = _norm_punct_spacing(orig_text)
                    _corr_normed = _norm_punct_spacing(corr_text)
                    if _orig_normed == _corr_normed and orig_text != corr_text:
                        logger.info(
                            f"[GRAMMAR] Blocked punct spacing: "
                            f"'{orig_text}'→'{corr_text}'"
                        )
                        continue


                # ── FIX-42d: Grammar trailing letter addition guard ──
                # Block grammar changes that add ا/ي to end of IV words.
                # Catches: واجب→واجبا, معطف→معطفا
                # Must come AFTER _is_grammar_pattern so we don't block valid grammar.
                if not _is_grammar_pattern and orig_text and corr_text:
                    _o_g2 = orig_text.rstrip('.،؛؟!?!')
                    _c_g2 = corr_text.rstrip('.،؛؟!?!')
                    if (len(_c_g2) == len(_o_g2) + 1 and _c_g2.startswith(_o_g2)
                            and _c_g2[-1] in ('ا', 'ي')):
                        logger.info(
                            f"[GRAMMAR] Blocked trailing letter addition: "
                            f"'{orig_text}'→'{corr_text}'"
                        )
                        continue

                # ── FIX-27a: Grammar structured data protection ──
                # Block grammar diffs where the original contains digits.
                # The grammar model corrupts dates/numbers/times/percentages.
                # e.g., '2026-06-22' → 'عشرين 26-06-22ا'
                if orig_text and any(c.isdigit() for c in orig_text):
                    logger.info(
                        f"[GRAMMAR] Blocked digit-containing diff: "
                        f"'{orig_text}'→'{corr_text}'"
                    )
                    logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"filter_reject","filter":"DigitGuard","original":orig_text[:80],"correction":corr_text[:80]})}')
                    tel_events.append({"event":"filter_reject","filter":"DigitGuard","original":orig_text[:80],"correction":corr_text[:80]})
                    continue

                # ── FIX-27b: Grammar hallucination guard (Jaccard) ──
                # Block grammar diffs where the correction is too different
                # from the original (character-level Jaccard < 0.5).
                # Catches: القانون→القانين, يعزف→يعزفون, للإنسان→للإنسين
                if not _is_grammar_pattern and orig_text and corr_text and len(orig_text) > 2:
                    # Strip punctuation/spaces and normalize Alif/Hamza for comparison
                    _o_norm = re.sub(r'[\s.,،؛؟!:;?]', '', orig_text)
                    _c_norm = re.sub(r'[\s.,،؛؟!:;?]', '', corr_text)
                    _o_norm = re.sub(r'[أإآ]', 'ا', _o_norm)
                    _c_norm = re.sub(r'[أإآ]', 'ا', _c_norm)
                    _o_chars = set(_o_norm)
                    _c_chars = set(_c_norm)
                    if _o_chars and _c_chars:
                        _jac = len(_o_chars & _c_chars) / len(_o_chars | _c_chars)
                        if _jac < 0.5:
                            logger.info(
                                f"[GRAMMAR] Blocked low-Jaccard diff (j={_jac:.2f}): "
                                f"'{orig_text}'→'{corr_text}'"
                            )
                            logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"filter_reject","filter":"Jaccard_05","original":orig_text[:80],"correction":corr_text[:80],"jaccard":round(_jac,3)})}')
                            tel_events.append({"event":"filter_reject","filter":"Jaccard_05","original":orig_text[:80],"correction":corr_text[:80],"jaccard":round(_jac,3)})
                            continue

                # ── FIX-06: Directional block protection for grammar ──
                # Prevents meaning-changing substitutions (كان→كأن etc.)
                # especially critical when spelling is skipped (>1000 chars).
                if not _is_grammar_pattern and corr_text in _DIRECTIONAL_BLOCKS.get(orig_text, set()):
                    logger.info(
                        f"[GRAMMAR] Directional block: '{orig_text}'→'{corr_text}'"
                    )
                    logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"filter_reject","filter":"DirectionalBlock","original":orig_text[:80],"correction":corr_text[:80]})}')
                    tel_events.append({"event":"filter_reject","filter":"DirectionalBlock","original":orig_text[:80],"correction":corr_text[:80]})
                    continue
                # Also check with clitic prefixes
                _gram_dir_blocked = False
                for _gpfx in ('و', 'ف', 'ب', 'ل', 'ك'):
                    if (orig_text.startswith(_gpfx) and corr_text.startswith(_gpfx)
                            and len(orig_text) > len(_gpfx) + 1):
                        _g_orig_stem = orig_text[len(_gpfx):]
                        _g_corr_stem = corr_text[len(_gpfx):]
                        if _g_corr_stem in _DIRECTIONAL_BLOCKS.get(_g_orig_stem, set()):
                            logger.info(
                                f"[GRAMMAR] Directional block (prefixed): "
                                f"'{orig_text}'→'{corr_text}'"
                            )
                            _gram_dir_blocked = True
                            break
                if _gram_dir_blocked:
                      logger.error(traceback.format_exc())
                      continue
                # DEBUG_TRACE
                if _is_grammar_pattern:
                    logger.debug(f"[DEBUG_TRACE] Pattern match found for: '{orig_text}'→'{corr_text}'")

                # FIX-22: Protect tanween (preserve ً ٌ ٍ from original)
                _TANWEEN_CHARS = set('ًٌٍ')
                if any(c in _TANWEEN_CHARS for c in orig_text) and not any(c in _TANWEEN_CHARS for c in corr_text):
                    # Grammar stripped tanween — reattach it
                    for _tc in _TANWEEN_CHARS:
                        if _tc in orig_text and _tc not in corr_text:
                            corr_text = corr_text + _tc
                            break

                # Re-label: if grammar's change is purely orthographic
                # (hamza, ه→ة, etc.), tag it as 'spelling' for correct UI icon
                stage_label = 'grammar'
                if _is_spelling_only_change(orig_text, corr_text):
                    stage_label = 'spelling'
                _grammar_accepted_diffs.append(d)  # FIX-04: track accepted
                logger.info(f'[FILTER-TEL] {_tel_json.dumps({"event":"patch_accepted","stage":stage_label,"original":orig_text[:80],"correction":corr_text[:80],"start":d["start"],"end":d["end"]})}')
                tel_events.append({"event":"patch_accepted","stage":stage_label,"original":orig_text[:80],"correction":corr_text[:80],"start":d["start"],"end":d["end"]})
                ctx.add_patch(
                    stage_label, d['start'], d['end'],
                    corr_text, confidence=1.0
                )

            # ── B7 (E6): Bracket-balance guard ──
            # If grammar's output lost brackets, reject the grammar correction.
            _OPEN_BRACKETS = set('([{')
            _CLOSE_BRACKETS = set(')]}')
            orig_opens = sum(1 for c in ctx.current_text if c in _OPEN_BRACKETS)
            orig_closes = sum(1 for c in ctx.current_text if c in _CLOSE_BRACKETS)
            corr_opens = sum(1 for c in corrected_grammar if c in _OPEN_BRACKETS)
            corr_closes = sum(1 for c in corrected_grammar if c in _CLOSE_BRACKETS)
            orig_balanced = (orig_opens == orig_closes)
            corr_balanced = (corr_opens == corr_closes)
            if orig_balanced and not corr_balanced:
                logger.info(
                    f"[GRAMMAR] Rejected bracket-unbalanced output: "
                    f"orig=({orig_opens},{orig_closes}), corr=({corr_opens},{corr_closes})"
                )
                # Don't mutate text — keep pre-grammar text
            elif _grammar_accepted_diffs:
                # FIX-04: Rebuild grammar text from ACCEPTED diffs only,
                # not the full model output. Prevents phantom corrections.
                _safe_grammar = ctx.current_text
                # Apply accepted diffs in reverse order to build safe text
                for _ad in sorted(_grammar_accepted_diffs, key=lambda x: x['start'], reverse=True):
                    _safe_grammar = (_safe_grammar[:_ad['start']] +
                                    _ad['correction'] +
                                    _safe_grammar[_ad['end']:])
                ctx.mutate_text(_safe_grammar, OffsetMapper)
            current_text = ctx.current_text
      except Exception as e:
        logger.error(f"[ANALYZE] Grammar failed: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())
        timing_ms['grammar_error'] = f"{type(e).__name__}: {str(e)[:200]}"
        try:
            from nlp.grammar.grammar_rules import ArabicGrammarGuard
            _fallback_rules = ArabicGrammarGuard()
            _fallback_out = _fallback_rules.process(_grammar_input_text, _grammar_input_text)
            if _fallback_out != _grammar_input_text:
                logger.info("[ANALYZE] Grammar rule-only fallback produced corrections")
                corrected_grammar = _fallback_out
                diffs = get_word_diffs(ctx.current_text, corrected_grammar)
                for d in diffs:
                    ctx.patches.add(d['start'], d['end'], d['original'], d['correction'], 'grammar', 0.6)
                ctx.mutate_text(corrected_grammar, OffsetMapper)
        except Exception as fe:
            logger.error(f"[ANALYZE] Grammar rule-only fallback also failed: {fe}")




def _run_punctuation_stage(ctx, timing_ms, tel_events, is_religious):
    """Execute punctuation correction with safety guards."""
    current_text = ctx.current_text
    # 3. Punctuation (runs on grammar-corrected text — PuncAra-v1 local model)
    # FIX-07: Skip punctuation for religious text
    # FIX-51: Skip punctuation when spelling+grammar found no errors (clean text)
    _has_real_corrections = any(p.stage in ('spelling', 'grammar') for p in ctx.patches.patches)
    if not is_religious and _has_real_corrections:
      try:
        t0 = time.time()
        logger.info(f"[ANALYZE] Step 3: Punctuation starting...")
        from nlp.punctuation.punctuation_service import get_punctuation_model
        punc_checker = get_punctuation_model()
        corrected_punc = punc_checker.correct(ctx.current_text)
        timing_ms['punctuation_ms'] = int((time.time() - t0) * 1000)
        logger.info(f"[ANALYZE] Step 3: Punctuation done in {timing_ms['punctuation_ms']}ms")
        if corrected_punc != ctx.current_text:
            diffs = get_word_diffs(ctx.current_text, corrected_punc)
            for d in diffs:
                # StageLocker: skip diffs that overlap with locked ranges
                # BUT allow pure punctuation insertions near locked words
                # Phase 11: Hierarchy-aware — punctuation (1) blocked by spelling (2) and grammar (3)
                lock_info = ctx.stage_locker.is_locked_by_for(d['start'], d['end'], 'punctuation')
                if lock_info:
                    orig_alpha = re.sub(r'[^؀-ۿa-zA-Z]', '', d.get('original', ''))
                    corr_alpha = re.sub(r'[^؀-ۿa-zA-Z]', '', d.get('correction', ''))
                    ls, le, owner = lock_info
                    if orig_alpha != corr_alpha:
                        # Diff changes actual words — block it
                        logger.info(
                            f"[LOCK] Punctuation blocked on [{d['start']}:{d['end']}] "
                            f"'{d.get('original','')}' — locked by {owner}[{ls}:{le}]"
                        )
                        continue
                    # Arabic text unchanged — only punctuation added/moved. Allow through.
                    logger.info(
                        f"[LOCK] Punctuation ALLOWED through lock [{d['start']}:{d['end']}] "
                        f"'{d.get('original','')}' → '{d.get('correction','')}' "
                        f"(locked by {owner}[{ls}:{le}])"
                    )
                # Punctuation safety layer: reject non-punctuation changes
                # FIX-52: Block punctuation diffs on digit-containing text
                if d.get('original', '') and any(c.isdigit() for c in d.get('original', '')):
                    logger.info(
                        f"[PUNC-SAFETY] Blocked digit-containing punct diff: "
                        f"'{d.get('original','')}' → '{d.get('correction','')}'"
                    )
                    continue
                if not validate_punctuation_diff(d, full_text=ctx.current_text):
                    logger.info(
                        f"[PUNC-SAFETY] Rejected diff [{d['start']}:{d['end']}] "
                        f"'{d.get('original','')}' → '{d.get('correction','')}' — not a safe punctuation change"
                    )
                    continue
                ctx.add_patch(
                    'punctuation', d['start'], d['end'],
                    d['correction'], confidence=0.8
                )

            # ── Aggregate punctuation cap (Fix 4): max 3 punctuation patches per response ──
            MAX_PUNC_PATCHES_PER_RESPONSE = 3
            punc_patches = [p for p in ctx.patches.patches if p.stage == 'punctuation']
            if len(punc_patches) > MAX_PUNC_PATCHES_PER_RESPONSE:
                # Keep earliest patches (by start_original) — consistent with PatchSet sort
                punc_patches_sorted = sorted(punc_patches, key=lambda p: p.start_original)
                to_remove = set(id(p) for p in punc_patches_sorted[MAX_PUNC_PATCHES_PER_RESPONSE:])
                # FIX-18: Also remove StageLocker locks for capped patches
                for _capped_p in punc_patches_sorted[MAX_PUNC_PATCHES_PER_RESPONSE:]:
                    ctx.stage_locker.unlock(_capped_p.start_original, _capped_p.end_original)
                ctx.patches.patches = [p for p in ctx.patches.patches if id(p) not in to_remove]
                logger.info(
                    f"[PUNC-CAP] Capped punctuation patches: "
                    f"{len(punc_patches)} → {MAX_PUNC_PATCHES_PER_RESPONSE}"
                )

            # FIX-05: Rebuild punctuation text from accepted diffs only (respecting locks and caps)
            _safe_punc = ctx.current_text
            _final_punc_patches = [p for p in ctx.patches.patches if p.stage == 'punctuation']
            for _p in sorted(_final_punc_patches, key=lambda x: x.start_current, reverse=True):
                _safe_punc = (_safe_punc[:_p.start_current] +
                             _p.replacement +
                             _safe_punc[_p.end_current:])
            ctx.mutate_text(_safe_punc, OffsetMapper)
            current_text = ctx.current_text

        # ── FIX-37: Rule-based terminal period fallback ──
        # The punctuation model often fails to add a period at the end
        # of longer sentences. If no terminal punctuation exists after
        # model processing, inject a period suggestion for the last word.
        # Threshold=4 words to avoid noisy suggestions while user is
        # still typing short phrases.
        _TERMINAL_PUNCT = set('.،؛؟!?!')
        _current_stripped = ctx.current_text.rstrip()
        _has_terminal = _current_stripped and _current_stripped[-1] in _TERMINAL_PUNCT
        _word_count_fb = len(re.findall(r'[؀-ۿa-zA-Z]+', ctx.current_text))
        if not _has_terminal and _word_count_fb >= 4:
            # Find the last word's position in current_text
            _last_word_match = re.search(r'([؀-ۿ]+)\s*$', _current_stripped)
            if _last_word_match:
                _lw_start = _last_word_match.start(1)
                _lw_end = _last_word_match.end(1)
                _lw_text = _last_word_match.group(1)
                # Check this range isn't already a patch
                _already_patched = any(
                    p.stage == 'punctuation'
                    and p.start_current == _lw_start
                    for p in ctx.patches.patches
                )
                if not _already_patched:
                    ctx.add_patch(
                        'punctuation', _lw_start, _lw_end,
                        _lw_text + '.', confidence=0.7
                    )
                    logger.info(
                        f"[PUNC-FALLBACK] Injected terminal period: "
                        f"'{_lw_text}' → '{_lw_text}.' at [{_lw_start}:{_lw_end}]"
                    )
      except Exception as e:
        logger.error(f"[ANALYZE] Punctuation failed: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())
        timing_ms['punctuation_error'] = f"{type(e).__name__}: {str(e)[:200]}"
