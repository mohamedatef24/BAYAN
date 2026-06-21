/**
 * Bayan Chrome Extension — UI Helpers
 *
 * Functions reused from: src/js/ui.js
 * All functions preserve original behavior exactly.
 * Source line references documented per Phase 0 audit.
 */

/**
 * Arabic labels for suggestion types.
 * Source: src/js/ui.js L3-7 (direct copy)
 */
const TYPE_LABELS = {
  spelling: 'إملائي',
  grammar: 'نحوي',
  punctuation: 'ترقيم',
};

/**
 * Resolve alternatives for a suggestion, falling back to [correction, original].
 * Source: src/js/ui.js L67-71 (direct copy)
 *
 * @param {Object} suggestion
 * @returns {Array<string>}
 */
function resolveAlternatives(suggestion) {
  return suggestion.alternatives && suggestion.alternatives.length > 0
    ? suggestion.alternatives
    : [suggestion.correction, suggestion.original];
}

/**
 * Calculate writing score from suggestion counts.
 * Source: src/js/ui.js L14-17 (direct copy)
 *
 * @param {number} spelling
 * @param {number} grammar
 * @param {number} punctuation
 * @returns {number} Score 0-100
 */
function calculateWritingScore(spelling, grammar, punctuation) {
  const score = 100 - spelling * 8 - grammar * 6 - punctuation * 3;
  return Math.max(0, Math.min(100, score));
}

/**
 * Build HTML for a single suggestion card.
 * Source: src/js/ui.js L73-100 (adapted for extension CSS classes)
 *
 * @param {Object} suggestion
 * @param {number} index
 * @returns {string} HTML string
 */
function buildSuggestionCardHTML(suggestion, index) {
  const badgeClass = `bayan-badge-${suggestion.type}`;
  const label = TYPE_LABELS[suggestion.type] || suggestion.type;
  const alts = resolveAlternatives(suggestion);
  const suggestionId = suggestion.id || index;

  let altsHTML = '';
  alts.forEach((alt, i) => {
    const isKeep = alt === suggestion.original;
    const isMain = i === 0;
    const cls = isKeep
      ? 'bayan-alt-chip bayan-alt-chip--keep'
      : isMain
        ? 'bayan-alt-chip bayan-alt-chip--main'
        : 'bayan-alt-chip';
    const chipLabel = isKeep ? `${escapeHtml(alt)} ✓` : escapeHtml(alt);
    altsHTML += `<button class="${cls}" data-card-alt="${escapeHtml(alt)}" data-card-id="${suggestionId}" type="button">${chipLabel}</button>`;
  });

  return `
    <div class="bayan-suggestion-card" role="listitem" tabindex="0"
      data-suggestion-id="${suggestionId}"
      aria-label="${label}: ${escapeHtml(suggestion.original)} إلى ${escapeHtml(suggestion.correction)}">
      <span class="bayan-suggestion-badge ${badgeClass}">${label}</span>
      <div class="bayan-suggestion-change">
        <span class="bayan-suggestion-original">${escapeHtml(suggestion.original)}</span>
        <span class="bayan-suggestion-arrow">←</span>
        <span class="bayan-suggestion-correction">${escapeHtml(suggestion.correction)}</span>
      </div>
      <div class="bayan-suggestion-alts">${altsHTML}</div>
    </div>`;
}

/**
 * Generate score hint text.
 *
 * @param {number} score
 * @param {number} total - total suggestion count
 * @returns {string}
 */
function getScoreHint(score, total) {
  if (total === 0) return 'ابدأ الكتابة لرؤية تقييمك';
  if (score >= 90) return 'كتابة ممتازة! استمر.';
  if (score >= 70) return 'جيد — راجع الاقتراحات لتحسين النص.';
  return 'يحتاج النص إلى بعض التحسينات.';
}
