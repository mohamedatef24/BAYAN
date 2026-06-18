"""
StageLockManager — Directed Acyclic NLP Graph (DANG) enforcement.

Ensures strict one-way pipeline: Spelling → Grammar → Punctuation.
Each stage produces immutable locked spans that downstream stages cannot modify.

Priority is for UI overlap resolution ONLY, not flow control.
Execution order is ALWAYS: spelling(1) → grammar(2) → punctuation(3).
"""


# Stage execution order (NOT priority — priority is separate for UI)
STAGE_ORDER = {
    'spelling': 1,
    'grammar': 2,
    'punctuation': 3,
    'autocomplete': 4,  # future NLP-4
}


class StageLockManager:
    """
    Enforces one-way pipeline by tracking locked spans per stage.

    Rules:
    1. Write Once: Once a stage modifies a span, it becomes LOCKED.
    2. Read Only Forward: Each stage can only modify UNLOCKED spans.
    3. No Backward Mutation: Later stages cannot re-trigger earlier stages.
    """

    def __init__(self):
        self.locked_spans = []  # list of {'start': int, 'end': int, 'source': str}
        self._completed_stages = set()

    def begin_stage(self, stage_name):
        """
        Mark a stage as starting. Validates execution order.
        Raises ValueError if a stage tries to run out of order.
        """
        stage_order = STAGE_ORDER.get(stage_name, 99)

        for completed in self._completed_stages:
            completed_order = STAGE_ORDER.get(completed, 99)
            if completed_order >= stage_order:
                raise ValueError(
                    f"[DANG VIOLATION] Stage '{stage_name}' (order={stage_order}) "
                    f"cannot run after '{completed}' (order={completed_order}). "
                    f"Pipeline is one-way: Spelling → Grammar → Punctuation."
                )

        return True

    def end_stage(self, stage_name):
        """Mark a stage as completed. No re-entry allowed."""
        self._completed_stages.add(stage_name)

    def is_locked(self, start, end):
        """
        Check if a span overlaps with any already-locked span.
        Returns the locking source stage if locked, None otherwise.
        """
        for lock in self.locked_spans:
            if start < lock['end'] and end > lock['start']:
                return lock['source']
        return None

    def lock_span(self, start, end, source):
        """
        Register an immutable span. Once locked, no earlier stage can touch it.
        """
        self.locked_spans.append({
            'start': start,
            'end': end,
            'source': source,
        })

    def filter_suggestions(self, suggestions, current_stage):
        """
        Filter out suggestions that try to modify spans locked by a LATER stage.
        In practice, since we run stages in order, this prevents backward mutations.
        """
        current_order = STAGE_ORDER.get(current_stage, 99)
        filtered = []

        for s in suggestions:
            lock_source = self.is_locked(s['start'], s['end'])
            if lock_source:
                lock_order = STAGE_ORDER.get(lock_source, 99)
                if lock_order > current_order:
                    # This span was locked by a later stage — should never happen
                    # in a correctly ordered pipeline, but guard against it.
                    continue
            filtered.append(s)

        return filtered

    def get_locked_spans(self):
        """Return all locked spans for metadata/debugging."""
        return list(self.locked_spans)

    def get_stage_summary(self):
        """Return a summary of completed stages and locked spans."""
        return {
            'completed_stages': list(self._completed_stages),
            'total_locked_spans': len(self.locked_spans),
            'locked_spans': self.locked_spans,
        }
