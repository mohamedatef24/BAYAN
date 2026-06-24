"""
StageLocker — Protects corrected ranges in CURRENT_TEXT from later stages.

STRICT RULES:
  ✅ Operates ONLY in CURRENT_TEXT coordinates
  ✅ Updates spans ONLY via mapper.forward_map_range() (direction is in the name)
  ❌ MUST NOT access any mapper internals (._opcodes, etc.)
  ❌ MUST NOT reason about mapping direction — the method name handles it
  ❌ MUST NOT implement any coordinate mapping logic

TERMINOLOGY:
  lock():               registers a range in CURRENT_TEXT as owned
  is_locked():          checks if a range in CURRENT_TEXT overlaps any owned range (ABSOLUTE)
  is_locked_for():      checks if a range is locked FOR A SPECIFIC STAGE (HIERARCHICAL)
  update_via_mapper():  shifts all spans forward when CURRENT_TEXT mutates

HIERARCHY (Phase 11):
  protection (99) ─── Absolute, overrides everything
  grammar    (3)  ─── May override spelling
  spelling   (2)  ─── Blocks punctuation, blocked by grammar
  punctuation(1)  ─── Blocked by spelling and grammar
"""
import logging

logger = logging.getLogger(__name__)

# Set to True for structured debug logging across all pipeline components
PIPELINE_DEBUG = False

# ═══════════════════════════════════════════════════════════════
# Phase 11: Hierarchical Priority Map
# ═══════════════════════════════════════════════════════════════
# A requesting stage is BLOCKED only by locks from stages with
# EQUAL or HIGHER priority. Lower-priority locks are overridden.
#
# Example: Grammar (3) requesting on a Spelling (2) lock → ALLOWED
# Example: Punctuation (1) requesting on a Spelling (2) lock → BLOCKED
# Example: Anything requesting on a Protection (99) lock → BLOCKED
STAGE_PRIORITY = {
    'punctuation': 1,
    'spelling': 2,
    'grammar': 3,
    'protection': 99,
}


class StageLocker:
    """Protects corrected ranges in CURRENT_TEXT from being overwritten by later stages."""

    def __init__(self):
        self.locked_spans: list = []  # list of (start, end, owner)

    def lock(self, start: int, end: int, owner: str):
        """Lock a range in CURRENT_TEXT coordinates."""
        self.locked_spans.append((start, end, owner))
        if PIPELINE_DEBUG:
            logger.debug(f"[StageLocker] LOCK [{start}:{end}] owner={owner}")

    def is_locked(self, start: int, end: int) -> bool:
        """Check if [start, end) in CURRENT_TEXT overlaps any locked range.

        ABSOLUTE check — ignores hierarchy. Any lock blocks.
        Kept for backward compatibility and protection-level checks.
        """
        for ls, le, _ in self.locked_spans:
            if start < le and end > ls:
                if PIPELINE_DEBUG:
                    logger.debug(f"[StageLocker] BLOCKED [{start}:{end}]")
                return True
        return False

    def is_locked_for(self, start: int, end: int, requesting_stage: str) -> bool:
        """Hierarchy-aware lock check.

        Returns True (BLOCKED) only if an overlapping lock has EQUAL or
        HIGHER priority than the requesting stage.

        Returns False (ALLOWED) if the requester outranks all overlapping locks.

        Phase 11 examples:
          is_locked_for(0, 5, 'grammar')     on spelling lock → False (grammar > spelling)
          is_locked_for(0, 5, 'punctuation') on spelling lock → True  (spelling > punctuation)
          is_locked_for(0, 5, 'grammar')     on protection lock → True (protection > grammar)

        Phase 14 (StageLocker relaxation):
          Grammar requesting on a spelling lock uses RELAXED overlap:
          only blocked if >50% of the grammar diff falls inside the spelling lock.
          This allows grammar to fix words ADJACENT to spelling-fixed words
          (the "Collision Dataset" bug — spelling locks were bleeding into
          neighboring words and blocking valid grammar corrections).
        """
        req_priority = STAGE_PRIORITY.get(requesting_stage, 0)
        for ls, le, owner in self.locked_spans:
            if start < le and end > ls:
                owner_priority = STAGE_PRIORITY.get(owner, 0)
                if owner_priority >= req_priority:
                    if PIPELINE_DEBUG:
                        logger.debug(
                            f"[StageLocker] HIERARCHY BLOCKED [{start}:{end}] "
                            f"requester={requesting_stage}({req_priority}) "
                            f"owner={owner}({owner_priority})"
                        )
                    return True  # Blocked: owner is same or higher priority

                # ── Phase 14: Relaxed overlap for grammar on spelling locks ──
                # Grammar (3) outranks spelling (2) in priority, BUT we still
                # want to protect the EXACT word spelling fixed. The relaxation:
                # allow grammar if the overlap is < 50% of the grammar diff's
                # width (i.e., the grammar diff is mostly OUTSIDE the lock).
                # This catches boundary touches and small overlaps that happen
                # when spelling locks bleed past word boundaries.
                if requesting_stage == 'grammar' and owner == 'spelling':
                    overlap_start = max(start, ls)
                    overlap_end = min(end, le)
                    overlap_width = max(0, overlap_end - overlap_start)
                    diff_width = max(1, end - start)
                    overlap_ratio = overlap_width / diff_width
                    if overlap_ratio > 0.5:
                        # Grammar diff is mostly inside spelling lock — block
                        logger.info(
                            f"[StageLocker] Grammar blocked (overlap={overlap_ratio:.0%}): "
                            f"grammar[{start}:{end}] vs spelling[{ls}:{le}]"
                        )
                        return True
                    else:
                        # Grammar diff is mostly outside — allow
                        if PIPELINE_DEBUG or overlap_width > 0:
                            logger.info(
                                f"[StageLocker] Grammar ALLOWED (overlap={overlap_ratio:.0%}): "
                                f"grammar[{start}:{end}] vs spelling[{ls}:{le}]"
                            )
                        continue
                else:
                    if PIPELINE_DEBUG:
                        logger.debug(
                            f"[StageLocker] HIERARCHY OVERRIDE [{start}:{end}] "
                            f"requester={requesting_stage}({req_priority}) "
                            f"overrides owner={owner}({owner_priority})"
                        )
        return False  # Not blocked: requester outranks all overlapping locks

    def is_locked_by(self, start: int, end: int):
        """Return (locked_start, locked_end, owner) if locked, else None.

        ABSOLUTE check — ignores hierarchy.
        """
        for ls, le, owner in self.locked_spans:
            if start < le and end > ls:
                return (ls, le, owner)
        return None

    def is_locked_by_for(self, start: int, end: int, requesting_stage: str):
        """Hierarchy-aware lock info check.

        Returns (locked_start, locked_end, owner) if the range is blocked
        by a lock with EQUAL or HIGHER priority than the requesting stage.
        Returns None if the requester outranks all overlapping locks.
        """
        req_priority = STAGE_PRIORITY.get(requesting_stage, 0)
        for ls, le, owner in self.locked_spans:
            if start < le and end > ls:
                owner_priority = STAGE_PRIORITY.get(owner, 0)
                if owner_priority >= req_priority:
                    return (ls, le, owner)
        return None

    def unlock(self, start: int, end: int) -> None:
        """FIX-18: Remove lock for a specific range (used when punctuation cap removes patches)."""
        self.locked_spans = [
            (ls, le, owner) for ls, le, owner in self.locked_spans
            if not (ls == start and le == end)
        ]

    def update_via_mapper(self, mapper) -> None:
        """
        Shift all locked spans to match the new CURRENT_TEXT after mutation.

        Calls mapper.forward_map_range(start, end) for each span.
        The method name 'forward_map_range' is self-documenting:
          it maps from CURRENT_TEXT(before) → CURRENT_TEXT(after).

        StageLocker does NOT need to know or reason about which direction
        is 'forward' — the OffsetMapper API name handles that.

        COMPRESSION WARNING: If a span shrinks by >50%, a warning is
        logged. This detects drift from deletions inside locked ranges
        without silently accepting potentially detached spans.
        """
        if not self.locked_spans:
            return

        updated = []
        for ls, le, owner in self.locked_spans:
            new_ls, new_le = mapper.forward_map_range(ls, le)
            if new_le > new_ls:
                # Compression warning: detect anomalous span shrinkage
                old_width = le - ls
                new_width = new_le - new_ls
                if old_width > 0 and new_width < old_width * 0.5:
                    logger.warning(
                        f"[StageLocker] COMPRESSION WARNING: [{ls}:{le}] ({owner}) "
                        f"shrunk by {100 - int(new_width / old_width * 100)}% → [{new_ls}:{new_le}]. "
                        f"Span may have partially detached from intended text."
                    )
                updated.append((new_ls, new_le, owner))
                if PIPELINE_DEBUG:
                    logger.debug(
                        f"[StageLocker] SHIFT [{ls}:{le}] → [{new_ls}:{new_le}] ({owner})"
                    )
            else:
                if PIPELINE_DEBUG:
                    logger.debug(f"[StageLocker] DROP [{ls}:{le}] ({owner})")
        self.locked_spans = updated
