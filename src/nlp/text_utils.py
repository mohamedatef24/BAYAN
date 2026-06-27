"""
Text processing utilities for the Bayan NLP pipeline.

Provides word-level diffing, offset mapping between text versions,
and edit-distance computation used across spelling/grammar/punctuation stages.
"""

import re
import difflib


def get_word_positions(text):
    """
    Returns a list of tuples (word, start_char_index, end_char_index)
    for all whitespace-separated words in the text.
    """
    positions = []
    for m in re.finditer(r'\S+', text):
        positions.append((m.group(), m.start(), m.end()))
    return positions


class OffsetMapper:
    """
    Single source of truth for coordinate transformations between
    two consecutive versions of CURRENT_TEXT.

    CONTRACT:
      Input:  text_before (str), text_after (str)
              — two consecutive states of CURRENT_TEXT
      Stores: Internal diff operations (PRIVATE)
      API:
        reverse_map_offset(pos)       → text_after pos → text_before pos
        forward_map_range(start, end) → text_before range → text_after range

    TERMINOLOGY:
      text_before = CURRENT_TEXT before this stage's mutation
      text_after  = CURRENT_TEXT after this stage's mutation
      forward     = text_before → text_after
      reverse     = text_after  → text_before

    RULES:
      All external code uses reverse_map_offset() or forward_map_range().
      ._opcodes is PRIVATE — no external access.
    """

    def __init__(self, text_before, text_after):
        self._text_before = text_before
        self._text_after = text_after
        self._opcodes = []
        self._build()

    def _build(self):
        s = difflib.SequenceMatcher(None, self._text_before, self._text_after)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            self._opcodes.append((i1, i2, j1, j2))

    def reverse_map_offset(self, pos_in_after, is_end=False):
        """
        Map a single position from text_after → text_before.
        (CURRENT_TEXT after mutation → CURRENT_TEXT before mutation)

        Used by PipelineContext.map_to_original() to walk the mapper
        chain in reverse, ultimately reaching ORIGINAL_TEXT coordinates.
        """
        matches = []
        for i1, i2, j1, j2 in self._opcodes:
            if j1 <= pos_in_after <= j2:
                matches.append((i1, i2, j1, j2))

        if not matches:
            return len(self._text_before)

        mapped_positions = []
        for i1, i2, j1, j2 in matches:
            if j2 == j1:
                mapped_positions.append(i2 if is_end else i1)
            else:
                ratio = (pos_in_after - j1) / (j2 - j1)
                mapped_positions.append(round(i1 + ratio * (i2 - i1)))

        return max(mapped_positions) if is_end else min(mapped_positions)

    def forward_map_range(self, start_in_before, end_in_before):
        """
        Map a range from text_before → text_after.
        (CURRENT_TEXT before mutation → CURRENT_TEXT after mutation)

        Used ONLY by StageLocker.update_via_mapper() to shift locked
        spans after a text mutation.

        MONOTONICITY GUARD: If independent point mapping produces an
        inverted range (start > end) due to non-monotonic edits,
        the end is clamped to max(new_start, new_end).
        """
        new_start = self._forward_map_pos(start_in_before)
        new_end = self._forward_map_pos(end_in_before)
        new_end = max(new_start, new_end)
        return new_start, new_end

    def _forward_map_pos(self, pos):
        """Map a single position text_before → text_after. PRIVATE."""
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


def get_word_diffs(original, corrected):
    """
    Identify differences between original and corrected text at the word level.
    Returns a list of suggestions with start and end character offsets.
    """
    orig_words = get_word_positions(original)
    corr_words = get_word_positions(corrected)
    s = difflib.SequenceMatcher(None, [w[0] for w in orig_words], [w[0] for w in corr_words])
    suggestions = []

    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == 'replace':
            if i1 < len(orig_words) and i2 - 1 < len(orig_words):
                start_char = orig_words[i1][1]
                end_char = orig_words[i2-1][2]
                suggestions.append({
                    'start': start_char,
                    'end': end_char,
                    'original': original[start_char:end_char],
                    'correction': " ".join([w[0] for w in corr_words[j1:j2]]),
                    'type': 'generic'
                })
        elif tag == 'delete':
            if i1 < len(orig_words) and i2 - 1 < len(orig_words):
                start_char = orig_words[i1][1]
                end_char = orig_words[i2-1][2]
                suggestions.append({
                    'start': start_char,
                    'end': end_char,
                    'original': original[start_char:end_char],
                    'correction': '',
                    'type': 'generic'
                })
        elif tag == 'insert':
            pos = orig_words[i1][1] if i1 < len(orig_words) else len(original)
            suggestions.append({
                'start': pos,
                'end': pos,
                'original': '',
                'correction': " ".join([w[0] for w in corr_words[j1:j2]]),
                'type': 'generic'
            })

    return suggestions


def levenshtein(a, b):
    """Damerau-Levenshtein distance — transpositions count as 1 edit.

    Better for Arabic typos like اقصتاديا→اقتصاديا (swap صت→تص):
    Standard Levenshtein says edit=2, Damerau says edit=1.

    FIX-45: Upgraded from standard Levenshtein.
    """
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )
            if (i > 1 and j > 1
                    and a[i - 1] == b[j - 2]
                    and a[i - 2] == b[j - 1]):
                dp[i][j] = min(dp[i][j], dp[i - 2][j - 2] + 1)
    return dp[m][n]
