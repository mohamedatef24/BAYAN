/**
 * Bayan Chrome Extension — Patch Application Engine
 *
 * Algorithms reused from: src/js/editor.js
 * Core logic: reverse-order offset replacement (editor.js L674-710)
 *
 * This module applies suggestion corrections to plain text
 * without requiring DOM manipulation.
 *
 * ═══════════════════════════════════════════════════════════
 * HIGH-1 FIX — Offset Rebasing Strategy
 * ═══════════════════════════════════════════════════════════
 *
 * When applying a single correction, the text length may change.
 * All remaining suggestions whose offsets come AFTER the applied
 * patch must be shifted by the length difference (delta).
 *
 * Strategy: LINEAR SHIFT
 *   delta = replacementText.length - (suggestion.end - suggestion.start)
 *   For every remaining suggestion S where S.start >= applied.end:
 *     S.start += delta
 *     S.end   += delta
 *
 * Edge cases:
 *   - Shorter replacement (delta < 0): offsets shift left
 *   - Longer replacement (delta > 0):  offsets shift right
 *   - Same-length (delta = 0):         offsets unchanged
 *   - Overlapping suggestions:         handled by PatchSet.resolve_overlaps()
 *     on the backend — we never receive overlapping suggestions
 *
 * This is O(n) per apply, which is fine for ≤50 suggestions.
 * ═══════════════════════════════════════════════════════════
 */

/**
 * Apply a single suggestion patch to text.
 * Source: src/js/editor.js L506-510 (offset-based replacement)
 *
 * @param {string} text - Original text
 * @param {Object} suggestion - { start, end, correction }
 * @returns {string} Text with correction applied
 */
function applyPatch(text, suggestion) {
  const before = text.substring(0, suggestion.start);
  const after = text.substring(suggestion.end);
  return before + suggestion.correction + after;
}

/**
 * Apply all suggestion patches to text.
 * CRITICAL: Sort in REVERSE order (highest start offset first)
 * to prevent offset shifts from invalidating subsequent patches.
 * Source: src/js/editor.js L674-710 (reverse-order algorithm)
 *
 * @param {string} text - Original text
 * @param {Array} suggestions - Array of { start, end, correction }
 * @returns {string} Fully corrected text
 */
function applyAllPatches(text, suggestions) {
  if (!suggestions || suggestions.length === 0) return text;

  // CRITICAL: Sort in REVERSE order (highest start offset first).
  // This is the exact same algorithm from editor.js L676.
  const sorted = [...suggestions].sort((a, b) => b.start - a.start);

  let result = text;
  sorted.forEach((s) => {
    result = result.substring(0, s.start) + s.correction + result.substring(s.end);
  });

  return result;
}

/**
 * Apply a specific alternative correction to text.
 * Source: src/js/editor.js L547-600 (alternative correction pattern)
 *
 * @param {string} text - Original text
 * @param {Object} suggestion - The suggestion being corrected
 * @param {string} alternativeText - The alternative correction to apply
 * @returns {string} Text with alternative correction applied
 */
function applyAlternativePatch(text, suggestion, alternativeText) {
  const before = text.substring(0, suggestion.start);
  const after = text.substring(suggestion.end);
  return before + alternativeText + after;
}

/**
 * Apply ONE correction and rebase ALL remaining suggestions.
 * This is the primary function for individual suggestion applies.
 *
 * HIGH-1 FIX: Atomic apply + rebase in a single call.
 *
 * @param {string} text - Current text (must match suggestion offsets)
 * @param {Object} appliedSuggestion - The suggestion being applied
 * @param {string} replacementText - The text to insert (correction or alternative)
 * @param {Array} allSuggestions - All current suggestions (including the one being applied)
 * @returns {{ text: string, suggestions: Array }} Updated text and rebased suggestions
 */
function applyAndRebase(text, appliedSuggestion, replacementText, allSuggestions) {
  // 1. Apply the patch to text
  const newText = text.substring(0, appliedSuggestion.start)
    + replacementText
    + text.substring(appliedSuggestion.end);

  // 2. Calculate delta: how much the text length changed
  const originalSpanLength = appliedSuggestion.end - appliedSuggestion.start;
  const delta = replacementText.length - originalSpanLength;

  // 3. Remove the applied suggestion and rebase remaining offsets
  const rebased = allSuggestions
    .filter((s) => s.id !== appliedSuggestion.id)
    .map((s) => {
      // Only shift suggestions that start AT or AFTER the applied patch's end.
      // Suggestions entirely before the patch are unaffected.
      // (Backend guarantees no overlapping suggestions via PatchSet.resolve_overlaps())
      if (s.start >= appliedSuggestion.end) {
        return { ...s, start: s.start + delta, end: s.end + delta };
      }
      return s;
    });

  return { text: newText, suggestions: rebased };
}

/**
 * Remove a suggestion from the list (after applying or dismissing).
 * Source: src/js/editor.js L520-523 (UUID-based filter)
 *
 * @param {Array} suggestions - Current suggestions array
 * @param {string} suggestionId - ID of suggestion to remove
 * @returns {Array} Filtered suggestions
 */
function removeSuggestion(suggestions, suggestionId) {
  return suggestions.filter((s) => s.id !== suggestionId);
}

/**
 * Count suggestions by type.
 * Source: src/js/editor.js L525-527 (type counting)
 *
 * @param {Array} suggestions
 * @returns {{ spelling: number, grammar: number, punctuation: number }}
 */
function countByType(suggestions) {
  return {
    spelling: suggestions.filter((s) => s.type === 'spelling').length,
    grammar: suggestions.filter((s) => s.type === 'grammar').length,
    punctuation: suggestions.filter((s) => s.type === 'punctuation').length,
  };
}
