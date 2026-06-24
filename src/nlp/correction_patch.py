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

PRIORITY = {'autocomplete': 0, 'spelling': 1, 'punctuation': 2, 'grammar': 3}


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

    def add(self, patch: CorrectionPatch):
        self.patches.append(patch)

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
                    # ── Phase 14: Cross-stage compatibility ──
                    # Spelling + Punctuation are COMPATIBLE stages:
                    # spelling fixes the word, punctuation adds marks.
                    # They should never conflict.
                    _compatible_pair = {
                        frozenset({'spelling', 'punctuation'}),
                    }
                    if frozenset({patch.stage, claimed_stage}) in _compatible_pair:
                        continue  # Compatible stages — allow coexistence

                    # ── FIX-36: Grammar + Punctuation merge ──
                    # When punctuation adds a trailing character to a grammar
                    # correction at the same span, merge instead of dropping.
                    if (patch.stage == 'punctuation' and claimed_stage == 'grammar'
                            and patch.start_original == cs and patch.end_original == ce):
                        # Check if punctuation correction = grammar correction + punct char
                        grammar_patch = resolved[res_idx]
                        punc_correction = patch.replacement
                        gram_correction = grammar_patch.replacement
                        if (len(punc_correction) == len(gram_correction) + 1
                                and punc_correction.startswith(gram_correction)
                                and punc_correction[-1] in _PUNCT_CHARS):
                            # Merge: append the trailing punct to grammar correction
                            grammar_patch.replacement = punc_correction
                            logger.info(
                                f"[OVERLAP] Merged punctuation into grammar "
                                f"[{cs}:{ce}]: '{grammar_patch.original}' → "
                                f"'{grammar_patch.replacement}'"
                            )
                            has_substantial_overlap = True  # Don't add separately
                            break

                    # Calculate overlap amount
                    overlap_start = max(patch.start_original, cs)
                    overlap_end = min(patch.end_original, ce)
                    overlap_width = overlap_end - overlap_start
                    # Compare to the smaller patch's width
                    patch_width = max(1, patch.end_original - patch.start_original)
                    claimed_width = max(1, ce - cs)
                    smaller_width = min(patch_width, claimed_width)
                    overlap_ratio = overlap_width / smaller_width
                    if overlap_ratio > 0.5:
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
        return [p.to_dict() for p in self.resolve_overlaps()]
