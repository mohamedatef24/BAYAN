/**
 * Bayan Chrome Extension — Renderer
 *
 * Functions reused from: src/js/renderer.js
 * All functions preserve original behavior exactly.
 * Source line references documented per Phase 0 audit.
 */

/**
 * Escapes HTML special characters to prevent XSS.
 * Source: src/js/renderer.js L9-18 (direct copy)
 *
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;',
  };
  return text.replace(/[&<>"']/g, (c) => map[c]);
}

/**
 * Sorts suggestions by start offset.
 * Source: src/js/renderer.js L25-27 (direct copy)
 *
 * @param {Array} suggestions - Array of suggestions with start/end offsets
 * @returns {Array} Sorted suggestions
 */
function sortSuggestions(suggestions) {
  return [...suggestions].sort((a, b) => a.start - b.start);
}

/**
 * Gets CSS class for suggestion type.
 * Source: src/js/renderer.js L138-145 (direct copy)
 *
 * @param {string} type - Suggestion type (spelling, grammar, punctuation)
 * @returns {string} CSS class name
 */
function getErrorClass(type) {
  const classes = {
    spelling: 'bayan-spelling-error',
    grammar: 'bayan-grammar-error',
    punctuation: 'bayan-punctuation-suggestion',
  };
  return classes[type] || 'bayan-spelling-error';
}

/**
 * Creates a segment tree of text ranges with their suggestions.
 * Handles overlapping ranges by merging them.
 * Source: src/js/renderer.js L36-131 (direct copy)
 *
 * @param {string} text - Original text
 * @param {Array} suggestions - Array of suggestions with start/end offsets
 * @returns {Array} Array of segments with position and suggestion info
 */
function createSegments(text, suggestions) {
  const sorted = sortSuggestions(suggestions);
  const finalSegments = [];
  let segStart = 0;

  sorted.forEach((suggestion) => {
    const { start, end } = suggestion;

    // Add text before suggestion
    if (segStart < start) {
      finalSegments.push({
        type: 'text',
        text: text.slice(segStart, start),
        suggestions: [],
      });
    }

    // Add suggested text
    finalSegments.push({
      type: 'suggestion',
      text: text.slice(start, end),
      suggestion: suggestion,
    });

    segStart = end;
  });

  // Add remaining text
  if (segStart < text.length) {
    finalSegments.push({
      type: 'text',
      text: text.slice(segStart),
      suggestions: [],
    });
  }

  return finalSegments;
}

/**
 * Renders text with highlighted suggestions as HTML string.
 * Source: src/js/renderer.js L153-191 (adapted for extension CSS classes)
 *
 * @param {string} text - Original text
 * @param {Array} suggestions - Array of suggestions with start/end offsets
 * @returns {string} Safe HTML string with highlights
 */
function renderHighlightedText(text, suggestions) {
  if (!text || text.length === 0) return '';
  if (!suggestions || suggestions.length === 0) return escapeHtml(text);

  const segments = createSegments(text, suggestions);
  let html = '';

  segments.forEach((segment) => {
    if (segment.type === 'text') {
      html += escapeHtml(segment.text);
    } else if (segment.type === 'suggestion') {
      const { suggestion } = segment;
      const errorClass = getErrorClass(suggestion.type);
      const escapedText = escapeHtml(segment.text);
      const sid = suggestion.id || '';

      html += `<span class="${errorClass}" data-suggestion-id="${sid}" data-original="${escapeHtml(
        suggestion.original
      )}" data-correction="${escapeHtml(
        suggestion.correction
      )}" data-type="${suggestion.type}" title="${suggestion.type}: ${escapeHtml(
        suggestion.correction
      )}">${escapedText}</span>`;
    }
  });

  return html;
}

/**
 * Main renderer function.
 * Source: src/js/renderer.js L201-204 (direct copy)
 *
 * @param {Object} input - { text, suggestions }
 * @returns {string} Safe HTML with highlights
 */
function bayanRender(input) {
  const { text = '', suggestions = [] } = input;
  return renderHighlightedText(text, suggestions);
}
