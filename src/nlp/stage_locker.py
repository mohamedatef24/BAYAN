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
  is_locked():          checks if a range in CURRENT_TEXT overlaps any owned range
  update_via_mapper():  shifts all spans forward when CURRENT_TEXT mutates
"""
import logging

logger = logging.getLogger(__name__)

# Set to True for structured debug logging across all pipeline components
PIPELINE_DEBUG = False


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
        """Check if [start, end) in CURRENT_TEXT overlaps any locked range."""
        for ls, le, _ in self.locked_spans:
            if start < le and end > ls:
                if PIPELINE_DEBUG:
                    logger.debug(f"[StageLocker] BLOCKED [{start}:{end}]")
                return True
        return False

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
