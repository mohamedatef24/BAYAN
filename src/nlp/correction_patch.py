"""
CorrectionPatch — Immutable correction with dual coordinate spaces.
PatchSet — Deterministic container with greedy overlap resolution.

TERMINOLOGY:
  ORIGINAL_TEXT = user's raw input (immutable)
  CURRENT_TEXT  = pipeline's working copy (mutated by each stage)

COORDINATE OWNERSHIP:
  start_original / end_original → PatchSet overlap resolution + API response
  start_current / end_current   → StageLocker + pipeline internals
"""
import uuid
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

PRIORITY = {'autocomplete': 0, 'punctuation': 1, 'spelling': 2, 'grammar': 3}


@dataclass
class CorrectionPatch:
    """
    Immutable correction suggestion with dual coordinate spaces.

    ORIGINAL coords (start_original, end_original):
      → Used by PatchSet.resolve_overlaps() for conflict resolution
      → Exported to frontend via to_dict() as 'start'/'end'
      → NEVER used for StageLocker or pipeline mutation

    CURRENT coords (start_current, end_current):
      → Used by StageLocker.lock() / is_locked()
      → Pipeline-internal range checking
      → NEVER sent to frontend
    """
    stage: str
    start_original: int
    end_original: int
    start_current: int
    end_current: int
    original: str
    replacement: str
    priority: int
    confidence: float = 1.0
    locked: bool = True
    alternatives: list = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        """
        Serialize for API response.
        Exports ORIGINAL_TEXT coordinates ONLY as 'start' and 'end'.
        CURRENT_TEXT coordinates are pipeline-internal and never exposed.
        """
        return {
            'id': self.id,
            'start': self.start_original,
            'end': self.end_original,
            'original': self.original,
            'correction': self.replacement,
            'type': self.stage,
            'priority': self.priority,
            'confidence': self.confidence,
            'locked': self.locked,
            'alternatives': self.alternatives,
        }


class PatchSet:
    """
    Deterministic overlap resolution using greedy first-fit strategy.

    Resolution order: priority DESC → confidence DESC → start ASC → id ASC
    The id tiebreaker guarantees identical ordering for identical inputs.

    Strategy: Greedy — first non-overlapping patch wins its range.
    One range = one owner. No stacking.
    This is deterministic and sufficient for ≤3 pipeline stages.

    # FUTURE: If pipeline grows beyond 5 stages or requires minimal-loss
    # coverage optimization, consider weighted interval scheduling:
    #   - Model as weighted job scheduling problem
    #   - Use dynamic programming on sorted intervals
    #   - Maximize sum(priority * confidence) of selected non-overlapping patches
    # Not needed now — greedy is correct for the current architecture.
    """

    def __init__(self):
        self.patches: list = []
        self._resolved_cache = None

    def add(self, patch: CorrectionPatch):
        self.patches.append(patch)
        self._resolved_cache = None

    def resolve_overlaps(self) -> list:
        """
        Single owner per range. Deterministic resolution.
        Uses ORIGINAL coordinates for overlap detection.

        Phase 14: Relaxed overlap rules:
        1. Patches with < 50% overlap of the smaller patch coexist freely
        2. Spelling + Punctuation patches from different stages always coexist
           (they're compatible: one fixes the word, the other adds punct)
        3. Same-stage overlaps are always resolved (higher confidence wins)
        4. FIX-36: Grammar + Punctuation — merge trailing punct into grammar
        """
        sorted_patches = sorted(
            self.patches,
            key=lambda p: (-p.priority, -p.confidence, p.start_original, p.id)
        )

        claimed_ranges = []  # list of (start, end, stage, patch_index)
        resolved = []

        # FIX-36: Punctuation chars that can be merged into grammar corrections
        _PUNCT_CHARS = set('.,،؛;:!؟?')

        for patch in sorted_patches:
            has_substantial_overlap = False
            overlapping_resolved_idx = None
            for ci, (cs, ce, claimed_stage, res_idx) in enumerate(claimed_ranges):
                # Check if there's any overlap at all
                if patch.start_original < ce and patch.end_original > cs:
                    # ── FIX-36 & Phase 14: Generalized Punctuation Merge ──
                    # If punctuation adds characters to a grammar or spelling correction,
                    # merge them instead of coexisting. Coexisting overlapping patches
                    # break _apply_patches_to_original.
                    if patch.stage == 'punctuation' and claimed_stage in ('grammar', 'spelling'):
                        claimed_patch = resolved[res_idx]
                        punc_correction = patch.replacement
                        prev_correction = claimed_patch.replacement
                        
                        # Check if punctuation is just appending trailing punctuation
                        # Scenario A: Exact match merge (prev_correction is prefix)
                        if (len(punc_correction) > len(prev_correction)
                                and punc_correction.startswith(prev_correction)
                                and all(c in _PUNCT_CHARS for c in punc_correction[len(prev_correction):])):
                            claimed_patch.replacement = punc_correction
                            logger.info(
                                f"[OVERLAP] Merged trailing punctuation into {claimed_stage} "
                                f"[{cs}:{ce}]: '{claimed_patch.original}' → "
                                f"'{claimed_patch.replacement}'"
                            )
                            has_substantial_overlap = True
                            break
                            
                        # Scenario B: Punctuation just adds punct to its own original text
                        # (e.g. original='المدرسة', replacement='المدرسة.', but prev_correction is a split like 'في المدرسة')
                        if (len(punc_correction) > len(patch.original)
                                and punc_correction.startswith(patch.original)
                                and all(c in _PUNCT_CHARS for c in punc_correction[len(patch.original):])):
                            added_punct = punc_correction[len(patch.original):]
                            # Only append if it doesn't already end with that punct
                            if not claimed_patch.replacement.endswith(added_punct):
                                claimed_patch.replacement += added_punct
                                logger.info(
                                    f"[OVERLAP] Appended trailing punctuation into {claimed_stage} "
                                    f"[{cs}:{ce}]: '{claimed_patch.original}' → "
                                    f"'{claimed_patch.replacement}'"
                                )
                            has_substantial_overlap = True
                            break
                            
                        # Check if punctuation is just prepending leading punctuation
                        if (len(punc_correction) > len(prev_correction)
                                and punc_correction.endswith(prev_correction)
                                and all(c in _PUNCT_CHARS for c in punc_correction[:-len(prev_correction)])):
                            claimed_patch.replacement = punc_correction
                            logger.info(
                                f"[OVERLAP] Merged leading punctuation into {claimed_stage} "
                                f"[{cs}:{ce}]: '{claimed_patch.original}' → "
                                f"'{claimed_patch.replacement}'"
                            )
                            has_substantial_overlap = True
                            break

                    # Calculate overlap amount
                    overlap_start = max(patch.start_original, cs)
                    overlap_end = min(patch.end_original, ce)
                    overlap_width = overlap_end - overlap_start
                    
                    if overlap_width > 0:
                        # STRICT NON-OVERLAP RULE: ANY overlap causes the lower priority patch to be dropped.
                        # Overlapping patches cannot be safely applied sequentially by standard frontend/benchmark clients.
                        has_substantial_overlap = True
                        overlapping_resolved_idx = res_idx
                        break

            if not has_substantial_overlap:
                res_idx = len(resolved)
                resolved.append(patch)
                claimed_ranges.append((patch.start_original, patch.end_original, patch.stage, res_idx))
            else:
                # Only log "Dropped" if we didn't merge
                if overlapping_resolved_idx is not None or patch.stage != 'punctuation':
                    logger.info(
                        f"[OVERLAP] Dropped {patch.stage} [{patch.start_original}:{patch.end_original}] "
                        f"'{patch.original}' — conflicts with higher-priority span"
                    )

        dropped = len(self.patches) - len(resolved)
        if dropped > 0:
            logger.info(f"[OVERLAP] Resolved {dropped} overlapping suggestions")

        return resolved

    def to_list(self) -> list:
        """Serialize resolved patches for API response."""
        if self._resolved_cache is None:
            self._resolved_cache = self.resolve_overlaps()
        return [p.to_dict() for p in self._resolved_cache]
