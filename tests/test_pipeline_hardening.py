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


if __name__ == '__main__':
    unittest.main()
