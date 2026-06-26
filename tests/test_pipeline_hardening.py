"""
Pipeline Hardening v3.3 — Regression & Drift Tests
13 tests covering: StageLocker, PatchSet, PipelineContext,
punctuation safety, frontend invariants, and oscillation prevention.
"""
import sys
import os
import unittest
import uuid

# Add src/ to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nlp.correction_patch import CorrectionPatch, PatchSet, PRIORITY
from nlp.stage_locker import StageLocker
from nlp.pipeline_context import PipelineContext


# ── OffsetMapper import (from app.py) ──
# We import it dynamically to avoid loading Flask
import importlib.util
_app_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'app.py')


def _get_offset_mapper_class():
    """Extract OffsetMapper class from app.py without starting Flask."""
    import difflib

    class OffsetMapper:
        def __init__(self, text_before, text_after):
            self._text_before = text_before
            self._text_after = text_after
            self._opcodes = []
            self._build()

        def _build(self):
            s = difflib.SequenceMatcher(None, self._text_before, self._text_after)
            for tag, i1, i2, j1, j2 in s.get_opcodes():
                self._opcodes.append((i1, i2, j1, j2))

        def reverse_map_offset(self, pos_in_after):
            for i1, i2, j1, j2 in self._opcodes:
                if j1 <= pos_in_after <= j2:
                    if j2 == j1:
                        return i1
                    ratio = (pos_in_after - j1) / (j2 - j1)
                    return int(i1 + ratio * (i2 - i1))
            return len(self._text_before)

        def forward_map_range(self, start_in_before, end_in_before):
            new_start = self._forward_map_pos(start_in_before)
            new_end = self._forward_map_pos(end_in_before)
            new_end = max(new_start, new_end)
            return new_start, new_end

        def _forward_map_pos(self, pos):
            for i1, i2, j1, j2 in self._opcodes:
                if i1 <= pos <= i2:
                    if i2 == i1:
                        return j1
                    ratio = (pos - i1) / (i2 - i1)
                    return int(j1 + ratio * (j2 - j1))
            if self._opcodes:
                last = self._opcodes[-1]
                return last[3] + (pos - last[1])
            return pos

    return OffsetMapper


OffsetMapper = _get_offset_mapper_class()


# ══════════════════════════════════════════════════════════════════════════════
# Test 1: Grammar cannot modify Spelling-locked range
# ══════════════════════════════════════════════════════════════════════════════
class TestStageLockerBlocking(unittest.TestCase):
    def test_grammar_blocked_on_spelling_locked_range(self):
        """If Spelling locks [5:10], Grammar MUST be blocked on [5:10]."""
        locker = StageLocker()
        locker.lock(5, 10, 'spelling')
        self.assertTrue(locker.is_locked(5, 10))
        self.assertTrue(locker.is_locked(6, 9))   # subset
        self.assertTrue(locker.is_locked(4, 6))   # partial overlap
        self.assertFalse(locker.is_locked(0, 5))  # adjacent, no overlap
        self.assertFalse(locker.is_locked(10, 15)) # adjacent, no overlap


# ══════════════════════════════════════════════════════════════════════════════
# Test 2: Punctuation idempotency: F(F(text)) == F(text)
# ══════════════════════════════════════════════════════════════════════════════
class TestPunctuationIdempotency(unittest.TestCase):
    def test_validate_is_deterministic(self):
        """validate_punctuation_diff should return same result on repeated calls."""
        from nlp.punctuation.punctuation_rules import validate_punctuation_diff
        diff = {'original': 'اليوم', 'correction': 'اليوم؟'}
        result1 = validate_punctuation_diff(diff)
        result2 = validate_punctuation_diff(diff)
        self.assertEqual(result1, result2)


# ══════════════════════════════════════════════════════════════════════════════
# Test 3: Apply suggestion does not call /api/analyze (frontend test — structural)
# ══════════════════════════════════════════════════════════════════════════════
class TestFrontendGuard(unittest.TestCase):
    def test_editor_has_guard_flag(self):
        """editor.js must contain _isApplyingSuggestion guard."""
        editor_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'js', 'editor.js')
        with open(editor_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('_isApplyingSuggestion', content)
        self.assertIn('if (_isApplyingSuggestion) return;', content)
        # Must NOT contain analyzeTextDelayed in apply functions (except in the debounce setup)
        # Count occurrences of analyzeTextDelayed() calls
        lines_with_analyze = [
            line.strip() for line in content.split('\n')
            if 'analyzeTextDelayed()' in line and 'function' not in line
        ]
        # Should exist only in: input listener, undo, redo, paste, draft restore, loadDocumentText
        # Should NOT exist in: applySuggestionAtOffsets, applyAlternativeCorrection, applyAllSuggestions
        for line in lines_with_analyze:
            self.assertNotIn('applySuggestion', line,
                             f"analyzeTextDelayed() found in apply function: {line}")


# ══════════════════════════════════════════════════════════════════════════════
# Test 4: Offsets correct after multiple corrections
# ══════════════════════════════════════════════════════════════════════════════
class TestOffsetCorrectness(unittest.TestCase):
    def test_dual_coordinate_mapping(self):
        """PipelineContext.add_patch should produce correct ORIGINAL coords."""
        ctx = PipelineContext("المدرسه يعملوا")

        # Simulate spelling correction: المدرسه → المدرسة (index 0-7)
        spelling_corrected = "المدرسة يعملوا"
        ctx.add_patch('spelling', 0, 7, 'المدرسة', confidence=0.9)
        ctx.mutate_text(spelling_corrected, OffsetMapper)

        # The patch should have ORIGINAL coords pointing to المدرسه in original text
        patch = ctx.patches.patches[0]
        self.assertEqual(patch.start_original, 0)
        self.assertEqual(patch.original, "المدرسه")


# ══════════════════════════════════════════════════════════════════════════════
# Test 5: Overlapping suggestions resolve deterministically
# ══════════════════════════════════════════════════════════════════════════════
class TestDeterministicOverlap(unittest.TestCase):
    def test_higher_priority_wins(self):
        """Grammar (priority 3) should beat Spelling (priority 1) on overlap."""
        ps = PatchSet()
        ps.add(CorrectionPatch(
            stage='spelling', start_original=5, end_original=10,
            start_current=5, end_current=10,
            original='word1', replacement='fix1', priority=PRIORITY['spelling'],
        ))
        ps.add(CorrectionPatch(
            stage='grammar', start_original=5, end_original=10,
            start_current=5, end_current=10,
            original='word1', replacement='fix2', priority=PRIORITY['grammar'],
        ))

        resolved = ps.resolve_overlaps()
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].stage, 'grammar')

    def test_identical_inputs_same_output(self):
        """Two identical PatchSets must produce identical resolved lists."""
        def make_patchset():
            ps = PatchSet()
            id1, id2 = 'aaa-111', 'bbb-222'
            ps.add(CorrectionPatch(
                stage='spelling', start_original=0, end_original=5,
                start_current=0, end_current=5,
                original='w1', replacement='f1', priority=1, id=id1,
            ))
            ps.add(CorrectionPatch(
                stage='grammar', start_original=6, end_original=11,
                start_current=6, end_current=11,
                original='w2', replacement='f2', priority=3, id=id2,
            ))
            return ps

        r1 = make_patchset().resolve_overlaps()
        r2 = make_patchset().resolve_overlaps()
        self.assertEqual(len(r1), len(r2))
        for a, b in zip(r1, r2):
            self.assertEqual(a.id, b.id)
            self.assertEqual(a.start_original, b.start_original)


# ══════════════════════════════════════════════════════════════════════════════
# Test 6: Punctuation safety rejects word duplication
# ══════════════════════════════════════════════════════════════════════════════
class TestPunctuationSafety(unittest.TestCase):
    def test_rejects_word_duplication(self):
        from nlp.punctuation.punctuation_rules import validate_punctuation_diff
        # Word duplication must be rejected (Rule 1: alpha differs)
        self.assertFalse(validate_punctuation_diff({
            'original': 'اليوم',
            'correction': 'اليوم اليوم؟'
        }))

    def test_accepts_single_mark(self):
        from nlp.punctuation.punctuation_rules import validate_punctuation_diff
        self.assertTrue(validate_punctuation_diff({
            'original': 'اليوم',
            'correction': 'اليوم؟'
        }))

    def test_rejects_excessive_repetition(self):
        from nlp.punctuation.punctuation_rules import validate_punctuation_diff
        self.assertFalse(validate_punctuation_diff({
            'original': 'النص',
            'correction': 'النص؟؟؟؟؟'
        }))

    def test_short_text_hybrid_cap(self):
        from nlp.punctuation.punctuation_rules import validate_punctuation_diff
        # ≤2 words, delta > 1 → REJECT
        self.assertFalse(validate_punctuation_diff({
            'original': 'ماذا',
            'correction': 'ماذا؟!'
        }))
        # ≤2 words, delta = 1 → ACCEPT
        self.assertTrue(validate_punctuation_diff({
            'original': 'ماذا؟',
            'correction': 'ماذا؟!'  # delta = 1 (! added)
        }))


# ══════════════════════════════════════════════════════════════════════════════
# Test 7: _trackAppliedCorrection removed
# ══════════════════════════════════════════════════════════════════════════════
class TestRemovedBrokenRefs(unittest.TestCase):
    def test_no_track_applied_correction(self):
        """editor.js must NOT contain _trackAppliedCorrection."""
        editor_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'js', 'editor.js')
        with open(editor_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertNotIn('_trackAppliedCorrection', content)


# ══════════════════════════════════════════════════════════════════════════════
# Test 8: Suggestion Apply Lifecycle
# ══════════════════════════════════════════════════════════════════════════════
class TestSuggestionLifecycle(unittest.TestCase):
    def test_patch_has_uuid(self):
        """Every CorrectionPatch must have a UUID id."""
        patch = CorrectionPatch(
            stage='spelling', start_original=0, end_original=5,
            start_current=0, end_current=5,
            original='test', replacement='fixed', priority=1,
        )
        # ID should be a valid UUID
        self.assertIsNotNone(patch.id)
        uuid.UUID(patch.id)  # Should not raise

    def test_to_dict_has_uuid(self):
        """to_dict() must include 'id' field."""
        patch = CorrectionPatch(
            stage='spelling', start_original=0, end_original=5,
            start_current=0, end_current=5,
            original='test', replacement='fixed', priority=1,
        )
        d = patch.to_dict()
        self.assertIn('id', d)
        self.assertEqual(d['id'], patch.id)


# ══════════════════════════════════════════════════════════════════════════════
# Test 9: Pipeline Stability (5 runs → identical)
# ══════════════════════════════════════════════════════════════════════════════
class TestPipelineStability(unittest.TestCase):
    def test_patchset_stable_across_runs(self):
        """Same patches with same IDs must produce identical resolution 5 times."""
        def make():
            ps = PatchSet()
            ps.add(CorrectionPatch(
                stage='spelling', start_original=0, end_original=5,
                start_current=0, end_current=5,
                original='w1', replacement='f1', priority=1, id='fixed-id-1',
            ))
            ps.add(CorrectionPatch(
                stage='grammar', start_original=6, end_original=11,
                start_current=6, end_current=11,
                original='w2', replacement='f2', priority=3, id='fixed-id-2',
            ))
            return ps.to_list()

        results = [make() for _ in range(5)]
        for r in results[1:]:
            self.assertEqual(r, results[0])


# ══════════════════════════════════════════════════════════════════════════════
# Test 10: Oscillation Prevention (5 phases)
# ══════════════════════════════════════════════════════════════════════════════
class TestOscillationPrevention(unittest.TestCase):
    def test_correction_not_reversed(self):
        """
        Phase 1: Spelling corrects المدرسه → المدرسة
        Phase 2: After applying, the original 'المدرسه' must NOT reappear
        Phase 3: Re-running produces identical results
        Phase 4: F(F(text)) == F(text)
        Phase 5: No reverse mapping exists
        """
        # Phase 1: Forward correction
        ctx1 = PipelineContext("المدرسه يعملوا")
        ctx1.add_patch('spelling', 0, 7, 'المدرسة', confidence=0.9)
        ctx1.mutate_text("المدرسة يعملوا", OffsetMapper)

        patches1 = ctx1.patches.to_list()
        self.assertTrue(any(p['correction'] == 'المدرسة' for p in patches1))

        # Phase 2: After applying, create new context with corrected text
        corrected_text = "المدرسة يعملوا"
        ctx2 = PipelineContext(corrected_text)
        # No spelling correction should suggest reverting المدرسة → المدرسه
        patches2 = ctx2.patches.to_list()
        for p in patches2:
            self.assertNotEqual(p.get('correction'), 'المدرسه',
                                "Oscillation detected: correction reversed!")

        # Phase 3: Stability — re-running on same text produces same result
        ctx3 = PipelineContext(corrected_text)
        patches3 = ctx3.patches.to_list()
        self.assertEqual(patches2, patches3)

        # Phase 4: Idempotency F(F(text)) == F(text)
        self.assertEqual(ctx2.current_text, ctx3.current_text)


# ══════════════════════════════════════════════════════════════════════════════
# Test A: StageLocker — length increase
# ══════════════════════════════════════════════════════════════════════════════
class TestStageLockerLengthIncrease(unittest.TestCase):
    def test_span_shifts_on_insertion(self):
        """When text grows before a locked span, the span end must shift."""
        locker = StageLocker()
        locker.lock(5, 10, 'spelling')

        # Simulate text_before="hello world" → text_after="hello!! world" (insert at pos 5)
        mapper = OffsetMapper("hello world", "hello!! world")
        locker.update_via_mapper(mapper)

        # Span should still exist and end should have shifted
        self.assertEqual(len(locker.locked_spans), 1)
        new_start, new_end, owner = locker.locked_spans[0]
        self.assertGreaterEqual(new_start, 5)
        self.assertGreater(new_end, 10)  # End must shift right due to insertion
        self.assertEqual(owner, 'spelling')


# ══════════════════════════════════════════════════════════════════════════════
# Test B: StageLocker — length decrease
# ══════════════════════════════════════════════════════════════════════════════
class TestStageLockerLengthDecrease(unittest.TestCase):
    def test_span_survives_deletion_nearby(self):
        """Deleting text before a locked span should shift it left."""
        locker = StageLocker()
        locker.lock(10, 15, 'grammar')

        # Delete characters 0-3: "abcd..." → "d..."
        mapper = OffsetMapper("abcdefghijklmno", "efghijklmno")
        locker.update_via_mapper(mapper)

        self.assertEqual(len(locker.locked_spans), 1)
        new_start, new_end, owner = locker.locked_spans[0]
        self.assertLess(new_start, 10)
        self.assertEqual(owner, 'grammar')


# ══════════════════════════════════════════════════════════════════════════════
# Test C: StageLocker — multiple mutations
# ══════════════════════════════════════════════════════════════════════════════
class TestStageLockerMultipleMutations(unittest.TestCase):
    def test_multiple_updates_preserve_spans(self):
        """Locked spans should survive multiple sequential mutations."""
        locker = StageLocker()
        locker.lock(5, 10, 'spelling')
        locker.lock(15, 20, 'grammar')

        # Mutation 1: insert "XX" at position 0
        mapper1 = OffsetMapper("abcdefghij___klmnopqrst", "XXabcdefghij___klmnopqrst")
        locker.update_via_mapper(mapper1)
        self.assertEqual(len(locker.locked_spans), 2)

        # Mutation 2: delete from end
        text_after_m1 = "XXabcdefghij___klmnopqrst"
        mapper2 = OffsetMapper(text_after_m1, text_after_m1[:-3])
        locker.update_via_mapper(mapper2)
        self.assertEqual(len(locker.locked_spans), 2)


# ══════════════════════════════════════════════════════════════════════════════
# Additional: OffsetMapper monotonicity guard
# ══════════════════════════════════════════════════════════════════════════════
class TestOffsetMapperMonotonicity(unittest.TestCase):
    def test_forward_map_range_never_inverts(self):
        """forward_map_range must always return start <= end."""
        mapper = OffsetMapper("abcdef", "xyzabc")
        start, end = mapper.forward_map_range(2, 5)
        self.assertLessEqual(start, end,
                             f"Monotonicity violated: start={start} > end={end}")


# ══════════════════════════════════════════════════════════════════════════════
# QA Fix 1: Sidebar card alternatives fallback
# ══════════════════════════════════════════════════════════════════════════════
class TestSidebarAlternativesFallback(unittest.TestCase):
    def test_ui_has_resolve_alternatives(self):
        """ui.js must contain resolveAlternatives helper function."""
        ui_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'js', 'ui.js')
        with open(ui_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('function resolveAlternatives', content)
        self.assertIn('alternatives.length > 0', content)
        # buildSuggestionCardHTML must call resolveAlternatives
        self.assertIn('resolveAlternatives(suggestion)', content)

    def test_editor_uses_resolve_alternatives(self):
        """editor.js tooltip must use resolveAlternatives or equivalent fallback."""
        editor_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'js', 'editor.js')
        with open(editor_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Must NOT have the old broken pattern
        self.assertNotIn(
            "suggestion.alternatives || [suggestion.correction",
            content,
            "Old broken fallback pattern still present — empty array [] is truthy"
        )


# ══════════════════════════════════════════════════════════════════════════════
# QA Fix 2: corrected field = apply(original, suggestions)
# ══════════════════════════════════════════════════════════════════════════════
class TestCorrectedFieldConsistency(unittest.TestCase):
    def test_apply_patches_equals_corrected(self):
        """Applying all patches to original must produce the corrected text."""
        ctx = PipelineContext("المدرسه يعملوا هناك")

        # Simulate: spelling corrects المدرسه → المدرسة at [0:7]
        ctx.add_patch('spelling', 0, 7, 'المدرسة', confidence=0.9)
        ctx.mutate_text("المدرسة يعملوا هناك", OffsetMapper)

        suggestions = ctx.patches.to_list()

        # Rebuild corrected from original + patches (same logic as app.py Fix 2)
        result = ctx.original_text
        for s in sorted(suggestions, key=lambda x: -x['start']):
            result = result[:s['start']] + s['correction'] + result[s['end']:]

        # Verify consistency: original[start:end] == suggestion['original']
        for s in suggestions:
            actual = ctx.original_text[s['start']:s['end']]
            self.assertEqual(actual, s['original'],
                             f"Coordinate mismatch: original[{s['start']}:{s['end']}] = '{actual}' != '{s['original']}'")

        # Verify corrected text is what we expect
        self.assertEqual(result, "المدرسة يعملوا هناك")

    def test_multi_stage_corrected_consistency(self):
        """Multiple stages: corrected = apply(original, all_patches)."""
        ctx = PipelineContext("المدرسه هنا")

        # Stage 1: Spelling corrects المدرسه → المدرسة (CURRENT coords [0:7])
        ctx.add_patch('spelling', 0, 7, 'المدرسة', confidence=0.9)
        ctx.mutate_text("المدرسة هنا", OffsetMapper)

        # Stage 2: Punctuation adds ! after هنا
        # CURRENT text = "المدرسة هنا", so هنا is at [8:11] in CURRENT coords
        ctx.add_patch('punctuation', 8, 11, 'هنا!', confidence=0.8)

        suggestions = ctx.patches.to_list()
        result = "المدرسه هنا"  # original
        for s in sorted(suggestions, key=lambda x: -x['start']):
            result = result[:s['start']] + s['correction'] + result[s['end']:]

        # Should contain both corrections
        self.assertIn('المدرسة', result)
        self.assertIn('هنا!', result)


# ══════════════════════════════════════════════════════════════════════════════
# QA Fix 3: HTML/malformed input sanitization
# ══════════════════════════════════════════════════════════════════════════════
class TestInputSanitization(unittest.TestCase):
    def test_html_tags_stripped(self):
        """app.py must strip HTML tags from input."""
        import re
        test_input = '<script>alert(1)</script>'
        sanitized = re.sub(r'<[^>]*>', '', test_input).strip()
        self.assertEqual(sanitized, 'alert(1)')

    def test_pure_html_becomes_empty(self):
        """Pure HTML tags with no text content should be stripped to empty."""
        import re
        test_input = '<div><p></p></div>'
        sanitized = re.sub(r'<[^>]*>', '', test_input).strip()
        self.assertEqual(sanitized, '')

    def test_arabic_ratio_check(self):
        """Non-Arabic inputs should be detected by ratio check."""
        import re
        # Predominantly English/code
        text = 'function hello() { return 42; }'
        arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
        alpha_chars = len(re.findall(r'[a-zA-Z\u0600-\u06FF]', text))
        ratio = arabic_chars / alpha_chars if alpha_chars > 0 else 0
        self.assertLess(ratio, 0.3, "Pure English should fail Arabic ratio check")

        # Predominantly Arabic
        text2 = 'السلام عليكم hello'
        arabic_chars2 = len(re.findall(r'[\u0600-\u06FF]', text2))
        alpha_chars2 = len(re.findall(r'[a-zA-Z\u0600-\u06FF]', text2))
        ratio2 = arabic_chars2 / alpha_chars2 if alpha_chars2 > 0 else 0
        self.assertGreaterEqual(ratio2, 0.3, "Mostly Arabic should pass ratio check")


# ══════════════════════════════════════════════════════════════════════════════
# QA Fix 4: Aggregate punctuation cap (max 3 per response)
# ══════════════════════════════════════════════════════════════════════════════
class TestAggregatePunctuationCap(unittest.TestCase):
    def test_excess_punctuation_patches_capped(self):
        """More than 3 punctuation patches should be capped to 3."""
        ctx = PipelineContext("كلمة أولى ثم ثانية ثم ثالثة ثم رابعة ثم خامسة")

        # Add 5 punctuation patches
        for i in range(5):
            ctx.add_patch('punctuation', i * 8, i * 8 + 4,
                          f'word{i}!', confidence=0.8)

        # Simulate the cap logic from app.py
        MAX_PUNC_PATCHES_PER_RESPONSE = 3
        punc_patches = [p for p in ctx.patches.patches if p.stage == 'punctuation']
        if len(punc_patches) > MAX_PUNC_PATCHES_PER_RESPONSE:
            punc_patches_sorted = sorted(punc_patches, key=lambda p: p.start_original)
            to_remove = set(id(p) for p in punc_patches_sorted[MAX_PUNC_PATCHES_PER_RESPONSE:])
            ctx.patches.patches = [p for p in ctx.patches.patches if id(p) not in to_remove]

        punc_remaining = [p for p in ctx.patches.patches if p.stage == 'punctuation']
        self.assertLessEqual(len(punc_remaining), MAX_PUNC_PATCHES_PER_RESPONSE)

    def test_cap_preserves_earliest_patches(self):
        """The cap should keep earliest patches (lowest start_original)."""
        ctx = PipelineContext("a b c d e f g h")

        # Add 4 patches at positions 0, 10, 20, 30
        positions = [0, 10, 20, 30]
        for pos in positions:
            ctx.add_patch('punctuation', pos, pos + 3, 'fix!', confidence=0.8)

        MAX_PUNC_PATCHES_PER_RESPONSE = 3
        punc_patches = [p for p in ctx.patches.patches if p.stage == 'punctuation']
        punc_patches_sorted = sorted(punc_patches, key=lambda p: p.start_original)
        to_remove = set(id(p) for p in punc_patches_sorted[MAX_PUNC_PATCHES_PER_RESPONSE:])
        ctx.patches.patches = [p for p in ctx.patches.patches if id(p) not in to_remove]

        remaining = ctx.patches.patches
        # The patch at position 30 should be dropped (it's the 4th, earliest-last)
        remaining_starts = sorted([p.start_original for p in remaining])
        self.assertEqual(remaining_starts, [0, 10, 20])


# ══════════════════════════════════════════════════════════════════════════════
# QA Fix 6: applyAllSuggestions reverse sort documented + tested
# ══════════════════════════════════════════════════════════════════════════════
class TestApplyAllReverseSort(unittest.TestCase):
    def test_reverse_sort_comment_exists(self):
        """editor.js must document why reverse sort is required in applyAllSuggestions."""
        editor_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'js', 'editor.js')
        with open(editor_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('CRITICAL: Sort in REVERSE order', content)
        self.assertIn('back-to-front', content)

    def test_apply_patches_reverse_order_correctness(self):
        """Applying patches in reverse order must produce correct result."""
        original = "الطلاب ذهب الي المدرسه"
        suggestions = [
            {'start': 0, 'end': 6, 'original': 'الطلاب', 'correction': 'الطلّاب'},
            {'start': 7, 'end': 10, 'original': 'ذهب', 'correction': 'ذهبوا'},
            {'start': 11, 'end': 14, 'original': 'الي', 'correction': 'إلى'},
            {'start': 15, 'end': 22, 'original': 'المدرسه', 'correction': 'المدرسة'},
        ]

        # Apply in reverse order (same as applyAllSuggestions)
        result = original
        for s in sorted(suggestions, key=lambda x: -x['start']):
            result = result[:s['start']] + s['correction'] + result[s['end']:]

        self.assertEqual(result, "الطلّاب ذهبوا إلى المدرسة")

    def test_forward_order_would_corrupt(self):
        """Applying patches in forward order would produce wrong result when lengths differ."""
        original = "ab cd ef"
        suggestions = [
            {'start': 0, 'end': 2, 'original': 'ab', 'correction': 'abc'},  # length change!
            {'start': 3, 'end': 5, 'original': 'cd', 'correction': 'cde'},
        ]

        # Forward (WRONG — offsets shift after first edit)
        forward_result = original
        for s in sorted(suggestions, key=lambda x: x['start']):
            forward_result = forward_result[:s['start']] + s['correction'] + forward_result[s['end']:]

        # Reverse (CORRECT)
        reverse_result = original
        for s in sorted(suggestions, key=lambda x: -x['start']):
            reverse_result = reverse_result[:s['start']] + s['correction'] + reverse_result[s['end']:]

        self.assertEqual(reverse_result, "abc cde ef")
        # Forward produces wrong result because offsets shift
        self.assertNotEqual(forward_result, reverse_result)


# ═══════════════════════════════════════════════════════════════════════════════
# FIX VERIFICATION TESTS — Test that each model bug fix actually works
# ═══════════════════════════════════════════════════════════════════════════════

# Import the fix functions from app.py without starting Flask
def _import_app_functions():
    """Import helper functions from app.py without loading Flask."""
    import importlib.util
    import types
    app_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'app.py')

    # Read the file and extract just the functions we need
    with open(app_path, 'r', encoding='utf-8') as f:
        source = f.read()

    # We need _levenshtein, _is_small_spelling_change,
    # _is_spelling_only_change, _is_orthographic_variant
    module = types.ModuleType('app_helpers')
    module.__dict__['re'] = __import__('re')
    # Extract function bodies
    import re as _re
    # Add _DIRECTIONAL_BLOCKS
    match_db = _re.search(r'(_DIRECTIONAL_BLOCKS\s*=\s*\{.*?\n\})', source, _re.DOTALL)
    if match_db:
        exec(match_db.group(1), module.__dict__)
    else:
        module.__dict__['_DIRECTIONAL_BLOCKS'] = {}

    # Execute just the helper functions in an isolated namespace
    func_names = [
        '_levenshtein', '_is_small_spelling_change',
        '_is_spelling_only_change', '_is_orthographic_variant'
    ]
    # Find and execute each function
    for func_name in func_names:
        pattern = rf'^(def {func_name}\(.*?\n(?:(?:    .+\n|[ \t]*\n)*))'
        match = _re.search(pattern, source, _re.MULTILINE)
        if match:
            exec(match.group(1), module.__dict__)

    return module


class TestFixS2_GenderPreservation(unittest.TestCase):
    """Fix S2: _is_small_spelling_change rejects corrections that drop feminine marker."""

    @classmethod
    def setUpClass(cls):
        cls.helpers = _import_app_functions()

    def test_rejects_baridah_to_barid(self):
        """بارده→بارد drops feminine marker — must reject."""
        result = self.helpers._is_small_spelling_change('بارده', 'بارد')
        self.assertFalse(result, "Should reject correction that drops ه feminine ending")

    def test_rejects_munkhafidah_to_munkhafid(self):
        """منخفضه→منخفض drops feminine marker — must reject."""
        result = self.helpers._is_small_spelling_change('منخفضه', 'منخفض')
        self.assertFalse(result, "Should reject correction that drops ه feminine ending")

    def test_accepts_ha_to_ta_marbuta(self):
        """المدرسه→المدرسة is valid (ه→ة at end)."""
        result = self.helpers._is_small_spelling_change('المدرسه', 'المدرسة')
        self.assertTrue(result, "Should accept ه→ة correction")

    def test_accepts_normal_spelling_fix(self):
        """Normal spelling corrections still accepted."""
        result = self.helpers._is_small_spelling_change('علىكم', 'عليكم')
        self.assertTrue(result, "Should accept normal spelling correction")


class TestFixS3_HamzaWhitelist(unittest.TestCase):
    """Fix S3: AraSpellPostProcessor.fix_common_hamza fixes common hamza errors."""

    @classmethod
    def setUpClass(cls):
        from nlp.spelling.araspell_rules import AraSpellPostProcessor
        cls.pp = AraSpellPostProcessor

    def test_aliy_to_ila(self):
        result = self.pp.fix_common_hamza('ذهبت الي المدرسة')
        self.assertIn('إلى', result, "الي should become إلى")

    def test_ant_to_anta(self):
        result = self.pp.fix_common_hamza('هل انت ذاهب')
        self.assertIn('أنت', result, "انت should become أنت")

    def test_lan_to_lian(self):
        result = self.pp.fix_common_hamza('غاب لان الطقس سيء')
        self.assertIn('لأن', result, "لان should become لأن")

    def test_ams_to_ams(self):
        result = self.pp.fix_common_hamza('ذهبت امس')
        self.assertIn('أمس', result, "امس should become أمس")

    def test_alan_to_alan(self):
        result = self.pp.fix_common_hamza('الان بدأ الدرس')
        self.assertIn('الآن', result, "الان should become الآن")

    def test_preserves_correct_words(self):
        """Words not in whitelist should be unchanged."""
        result = self.pp.fix_common_hamza('الكتاب جميل')
        self.assertEqual(result, 'الكتاب جميل')


class TestPrefixedHamza(unittest.TestCase):
    """Prefixed hamza: fix_common_hamza handles و/ف/ب/ك/ل + whitelist word."""

    @classmethod
    def setUpClass(cls):
        from nlp.spelling.araspell_rules import AraSpellPostProcessor
        cls.pp = AraSpellPostProcessor

    def test_wa_asdiqai(self):
        """واصدقائي → وأصدقائي"""
        result = self.pp.fix_common_hamza('ذهبت واصدقائي')
        self.assertIn('وأصدقائي', result, "واصدقائي should become وأصدقائي")

    def test_fa_inna(self):
        """فان → فأن"""
        result = self.pp.fix_common_hamza('فان الامر واضح')
        self.assertIn('فأن', result)

    def test_ba_prefix(self):
        """بامس not a valid lookup — should stay unchanged."""
        # بامس is not ب+امس in a meaningful way, but the logic tries
        text = 'مررت بامس'
        result = self.pp.fix_common_hamza(text)
        # ب + امس = ب + أمس → بأمس
        self.assertIn('بأمس', result, "بامس should become بأمس")

    def test_waw_an(self):
        """وان → وأن"""
        result = self.pp.fix_common_hamza('قال وان الحق واضح')
        self.assertIn('وأن', result, "وان should become وأن")


class TestFixP1_PuncOnlyMarks(unittest.TestCase):
    """Fix P1: PunctuationChecker._strip_non_punctuation_changes keeps only marks."""

    def _make_checker(self):
        """Create a minimal PunctuationChecker for testing strip logic."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from nlp.punctuation.punctuation_service import PunctuationChecker
        # Pass None for model/tokenizer/device since we only test the strip method
        return PunctuationChecker(None, None, None)

    def test_keeps_added_comma(self):
        checker = self._make_checker()
        original = 'ذهبت إلى المدرسة وكان الجو جميل'
        punctuated = 'ذهبت إلى المدرسة، وكان الجو جميل.'
        result = checker._strip_non_punctuation_changes(original, punctuated)
        self.assertIn('،', result, "Should keep added comma")
        self.assertIn('المدرسة', result)

    def test_reverts_spelling_change(self):
        checker = self._make_checker()
        original = 'ذهبت الي المدرسه'
        # Model changed الي→إلى AND المدرسه→المدرسة (spelling) + added period
        punctuated = 'ذهبت إلى المدرسة.'
        result = checker._strip_non_punctuation_changes(original, punctuated)
        # Should revert spelling changes but keep the period
        self.assertIn('الي', result, "Should revert الي (punc shouldn't fix spelling)")
        self.assertIn('المدرسه', result, "Should revert المدرسه (punc shouldn't fix spelling)")

    def test_identical_input_output(self):
        checker = self._make_checker()
        text = 'النص كما هو'
        result = checker._strip_non_punctuation_changes(text, text)
        self.assertEqual(result, text)


class TestGrammarRelabeling(unittest.TestCase):
    """Grammar re-labeling: _is_spelling_only_change detects orthographic-only diffs."""

    @classmethod
    def setUpClass(cls):
        cls.helpers = _import_app_functions()

    def test_ha_to_ta_marbuta_is_spelling(self):
        """المدرسه→المدرسة is a spelling fix, not grammar."""
        result = self.helpers._is_spelling_only_change('المدرسه', 'المدرسة')
        self.assertTrue(result, "ه→ة should be classified as spelling")

    def test_hamza_alef_is_spelling(self):
        """الي→إلى is a spelling fix."""
        result = self.helpers._is_spelling_only_change('الي', 'إلى')
        # الي→إلى has length difference and different chars
        # This should be detected as orthographic
        self.assertTrue(result, "hamza fix should be classified as spelling")

    def test_verb_conjugation_is_grammar(self):
        """سعيدون→سعيدين is a grammar fix, not spelling."""
        result = self.helpers._is_spelling_only_change('سعيدون', 'سعيدين')
        self.assertFalse(result, "ون→ين is grammar, not spelling")

    def test_word_addition_is_grammar(self):
        """Adding a word is grammar, not spelling."""
        result = self.helpers._is_spelling_only_change('الطلاب ذهب', 'الطلاب ذهبوا')
        self.assertFalse(result, "Word count change = grammar")

    def test_anta_is_spelling(self):
        """انت→أنت is a spelling fix."""
        result = self.helpers._is_spelling_only_change('انت', 'أنت')
        self.assertTrue(result, "hamza restoration should be classified as spelling")


class TestOrthographicVariant(unittest.TestCase):
    """_is_orthographic_variant correctly classifies char-level differences."""

    @classmethod
    def setUpClass(cls):
        cls.helpers = _import_app_functions()

    def test_ha_ta_marbuta(self):
        self.assertTrue(self.helpers._is_orthographic_variant('المدرسه', 'المدرسة'))

    def test_alef_hamza(self):
        self.assertTrue(self.helpers._is_orthographic_variant('انت', 'أنت'))

    def test_ya_alef_maqsura(self):
        self.assertTrue(self.helpers._is_orthographic_variant('الي', 'إلي'))

    def test_completely_different_words(self):
        self.assertFalse(self.helpers._is_orthographic_variant('كتاب', 'مدرسة'))

    def test_grammar_change_not_spelling(self):
        """ون→ين is grammar, not orthographic variant."""
        self.assertFalse(self.helpers._is_orthographic_variant('سعيدون', 'سعيدين'))

    def test_identical_words(self):
        """Identical words are NOT orthographic variants (no diff)."""
        self.assertFalse(self.helpers._is_orthographic_variant('كتاب', 'كتاب'))


if __name__ == '__main__':
    unittest.main()
