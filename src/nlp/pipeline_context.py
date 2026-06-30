"""
PipelineContext — Shared state for a single /api/analyze request.

INVARIANTS:
  1. original_text is IMMUTABLE after construction
  2. _offset_mappers is APPEND-ONLY — past mappers never mutated or removed
  3. map_to_original() is READ-ONLY and deterministic
  4. All coordinate transforms go through OffsetMapper public API

TERMINOLOGY:
  original_text = ORIGINAL_TEXT (user's raw input, immutable)
  current_text  = CURRENT_TEXT (pipeline working copy, mutated per stage)

# FUTURE: If pipeline grows beyond 5 stages, the linear reverse_map_offset()
# chain in map_to_original() could be replaced with a precomputed cumulative
# mapping or segment-tree composition. Not needed for 3 stages.
"""
import logging
from nlp.correction_patch import PatchSet, CorrectionPatch, PRIORITY
from nlp.stage_locker import StageLocker, PIPELINE_DEBUG

logger = logging.getLogger(__name__)


class PipelineContext:
    """
    Shared state object for a single /api/analyze request.
    Carries all pipeline state through Spelling → Grammar → Punctuation.
    Discarded after the response is sent.
    """

    def __init__(self, original_text: str):
        self.original_text: str = original_text    # IMMUTABLE — never assign again
        self.current_text: str = original_text
        self.patches: PatchSet = PatchSet()
        self._offset_mappers: list = []            # APPEND-ONLY
        self.stage_locker: StageLocker = StageLocker()

    def map_to_original(self, start: int, end: int) -> tuple:
        """
        Map CURRENT_TEXT coords → ORIGINAL_TEXT coords.

        Walks the OffsetMapper chain in REVERSE, calling
        reverse_map_offset() on each mapper.

        READ-ONLY: does not mutate any state.
        DETERMINISTIC: same inputs always produce same outputs.
        """
        curr_start, curr_end = start, end
        for mapper in reversed(self._offset_mappers):
            curr_start = mapper.reverse_map_offset(curr_start, is_end=False)
            curr_end = mapper.reverse_map_offset(curr_end, is_end=True)
        return curr_start, curr_end

    def add_patch(self, stage: str, start_current: int, end_current: int,
                  replacement: str, confidence: float = 1.0,
                  alternatives: list = None):
        """
        Create a CorrectionPatch with BOTH coordinate spaces populated.

        CURRENT coords: from the diff (for StageLocker)
        ORIGINAL coords: computed via reverse mapper chain (for API + overlap resolution)
        """
        start_orig, end_orig = self.map_to_original(start_current, end_current)
        text_len = len(self.original_text)
        start_orig = max(0, min(start_orig, text_len))
        end_orig = max(start_orig, min(end_orig, text_len))

        patch = CorrectionPatch(
            stage=stage,
            start_original=start_orig,
            end_original=end_orig,
            start_current=start_current,
            end_current=end_current,
            original=self.original_text[start_orig:end_orig],
            replacement=replacement,
            priority=PRIORITY.get(stage, 0),
            confidence=confidence,
            locked=True,
            alternatives=alternatives or [],
        )
        self.patches.add(patch)

        # Lock in CURRENT_TEXT coordinates
        self.stage_locker.lock(start_current, end_current, stage)

        if PIPELINE_DEBUG:
            logger.debug(
                f"[PipelineContext] PATCH stage={stage} "
                f"CURRENT=[{start_current}:{end_current}] "
                f"ORIGINAL=[{start_orig}:{end_orig}] "
                f"'{patch.original}' → '{replacement}'"
            )
        return patch

    def mutate_text(self, text_after: str, OffsetMapperClass):
        """
        Update CURRENT_TEXT after a stage produces a new version.

        1. Creates OffsetMapper(text_before=current_text, text_after=new)
        2. APPENDS to mapper chain (append-only invariant)
        3. Updates StageLocker via mapper.forward_map_range()
        4. Sets current_text = text_after
        """
        if text_after == self.current_text:
            return

        mapper = OffsetMapperClass(self.current_text, text_after)
        self._offset_mappers.append(mapper)  # APPEND-ONLY

        # StageLocker updates via mapper.forward_map_range() — direction is in the name
        self.stage_locker.update_via_mapper(mapper)

        if PIPELINE_DEBUG:
            logger.debug(
                f"[PipelineContext] MUTATE len={len(self.current_text)} → {len(text_after)} "
                f"mappers={len(self._offset_mappers)}"
            )
        self.current_text = text_after
