// src/js/renderer.js
// Offset-based renderer for highlighted text with suggestions

/**
 * Escapes HTML special characters to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, (c) => map[c]);
}

/**
 * Sorts suggestions by start offset
 * @param {Array} suggestions - Array of suggestions with start/end offsets
 * @returns {Array} - Sorted suggestions
 */
function sortSuggestions(suggestions) {
  return [...suggestions].sort((a, b) => a.start - b.start);
}

/**
 * Creates a segment tree of text ranges with their suggestions
 * Handles overlapping ranges by merging them
 * @param {string} text - Original text
 * @param {Array} suggestions - Array of suggestions with start/end offsets
 * @returns {Array} - Array of segments with position and suggestion info
 */
function createSegments(text, suggestions) {
  const sorted = sortSuggestions(suggestions);
  const segments = [];
  let currentPos = 0;

  // Build event timeline
  const events = [];
  sorted.forEach((suggestion, idx) => {
    events.push({
      pos: suggestion.start,
      type: 'start',
      suggestionIdx: idx
    });
    events.push({
      pos: suggestion.end,
      type: 'end',
      suggestionIdx: idx
    });
  });

  // Sort events by position
  events.sort((a, b) => a.pos - b.pos || (a.type === 'end' ? 1 : -1));

  const activeSuggestions = [];

  events.forEach((event) => {
    const pos = event.pos;

    // Add unsuggestioned text segment up to this position
    if (currentPos < pos) {
      segments.push({
        type: 'text',
        text: text.slice(currentPos, pos),
        suggestions: []
      });
    }

    // Track active suggestions
    if (event.type === 'start') {
      activeSuggestions.push(sorted[event.suggestionIdx]);
    } else {
      activeSuggestions.splice(
        activeSuggestions.findIndex((s) => s === sorted[event.suggestionIdx]),
        1
      );
    }

    currentPos = pos;
  });

  // Add remaining text
  if (currentPos < text.length) {
    segments.push({
      type: 'text',
      text: text.slice(currentPos),
      suggestions: []
    });
  }

  // Now rebuild segments with suggestion ranges
  const finalSegments = [];
  let segStart = 0;

  sorted.forEach((suggestion, idx) => {
    const { start, end } = suggestion;

    // Add text before suggestion
    if (segStart < start) {
      finalSegments.push({
        type: 'text',
        text: text.slice(segStart, start),
        suggestions: []
      });
    }

    // Add suggested text
    finalSegments.push({
      type: 'suggestion',
      text: text.slice(start, end),
      suggestion: suggestion
    });

    segStart = end;
  });

  // Add remaining text
  if (segStart < text.length) {
    finalSegments.push({
      type: 'text',
      text: text.slice(segStart),
      suggestions: []
    });
  }

  return finalSegments;
}

/**
 * Gets CSS class for suggestion type
 * @param {string} type - Suggestion type (spelling, grammar, punctuation)
 * @returns {string} - CSS class name
 */
function getErrorClass(type) {
  const classes = {
    'spelling': 'spelling-error',
    'grammar': 'grammar-error',
    'punctuation': 'punctuation-suggestion'
  };
  return classes[type] || 'spelling-error';
}

/**
 * Renders text with highlighted suggestions
 * @param {string} text - Original text
 * @param {Array} suggestions - Array of suggestions with start/end offsets
 * @returns {string} - Safe HTML string with highlights
 */
function renderHighlightedText(text, suggestions) {
  if (!text || text.length === 0) {
    return '';
  }

  if (!suggestions || suggestions.length === 0) {
    // No suggestions, return escaped text only
    return escapeHtml(text);
  }

  const segments = createSegments(text, suggestions);
  let html = '';
  let suggestionId = 0;

  segments.forEach((segment) => {
    if (segment.type === 'text') {
      // Regular text segment - just escape it
      html += escapeHtml(segment.text);
    } else if (segment.type === 'suggestion') {
      // Highlighted suggestion segment
      const { suggestion } = segment;
      const errorClass = getErrorClass(suggestion.type);
      const escapedText = escapeHtml(segment.text);

      html += `<span class="${errorClass}" data-suggestion-id="${suggestionId}" data-original="${escapeHtml(
        suggestion.original
      )}" data-correction="${escapeHtml(
        suggestion.correction
      )}" data-type="${suggestion.type}" title="${suggestion.type}: ${escapeHtml(suggestion.correction)}">${escapedText}</span>`;

      suggestionId++;
    }
  });

  return html;
}

/**
 * Main renderer function
 * Accepts text and suggestions array, returns highlighted HTML
 * @param {Object} input - Object with text and suggestions
 * @param {string} input.text - Original text
 * @param {Array} input.suggestions - Array of suggestions with { start, end, original, correction, type }
 * @returns {string} - Safe HTML with highlights
 */
function render(input) {
  const { text = '', suggestions = [] } = input;
  return renderHighlightedText(text, suggestions);
}

// Export for use in modules (if using ES6 modules)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    render,
    renderHighlightedText,
    escapeHtml,
    createSegments,
    sortSuggestions,
    getErrorClass
  };
}
