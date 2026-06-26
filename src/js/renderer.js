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
  // Pipeline Hardening v3.3: Track which suggestion we're rendering for UUID lookup
  let suggestionIdx = 0;

  segments.forEach((segment) => {
    if (segment.type === 'text') {
      // Regular text segment - just escape it
      html += escapeHtml(segment.text);
    } else if (segment.type === 'suggestion') {
      // Highlighted suggestion segment
      const { suggestion } = segment;
      const errorClass = getErrorClass(suggestion.type);
      const escapedText = escapeHtml(segment.text);
      // Pipeline Hardening v3.3: Use suggestion.id (UUID) if available, fallback to index
      const sid = suggestion.id || suggestionIdx;

      html += `<span class="${errorClass}" data-suggestion-id="${sid}" data-original="${escapeHtml(
        suggestion.original
      )}" data-correction="${escapeHtml(
        suggestion.correction
      )}" data-type="${suggestion.type}" title="${suggestion.type}: ${escapeHtml(suggestion.correction)}">${escapedText}</span>`;

      suggestionIdx++;
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

/**
 * Walk all text nodes in a DOM subtree in document order
 */
function walkTextNodes(root, callback) {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
  let node;
  while ((node = walker.nextNode())) {
    callback(node);
  }
}

/**
 * Remove existing error highlight spans without destroying content
 * Unwraps the spans back to plain text nodes
 */
function clearOverlays(editor) {
  const errorSpans = editor.querySelectorAll('.spelling-error, .grammar-error, .punctuation-suggestion');
  errorSpans.forEach(span => {
    // Skip spans inside quran-applied (they shouldn't be there, but safety)
    if (span.closest('.quran-applied')) return;
    const parent = span.parentNode;
    while (span.firstChild) {
      parent.insertBefore(span.firstChild, span);
    }
    parent.removeChild(span);
  });
  editor.normalize(); // merge adjacent text nodes
}

/**
 * Overlay suggestion highlights on the editor DOM without replacing innerHTML.
 * This preserves all formatting (bold, italic, underline, font, etc.)
 *
 * @param {HTMLElement} editor - The editor element
 * @param {Array} suggestions - Sorted array of suggestions with { start, end, original, correction, type }
 */
function overlaySuggestions(editor, suggestions) {
  // 1. Clear old overlays
  clearOverlays(editor);

  if (!suggestions || suggestions.length === 0) return;

  // 2. Collect text nodes with their character offsets (skip quran-applied)
  const textNodes = [];
  let offset = 0;
  walkTextNodes(editor, (node) => {
    // Skip text inside quran-applied spans (protected from analysis)
    if (node.parentElement && node.parentElement.closest('.quran-applied')) {
      offset += node.length; // still count offset to keep positions correct
      return;
    }
    textNodes.push({ node, start: offset, end: offset + node.length });
    offset += node.length;
  });

  if (textNodes.length === 0) return;

  // 3. Process suggestions in REVERSE order to avoid offset shifts
  const sorted = [...suggestions].sort((a, b) => b.start - a.start);

  sorted.forEach((suggestion, reverseIdx) => {
    const { start, end } = suggestion;
    const errorClass = getErrorClass(suggestion.type);

    // Find text nodes that overlap with this suggestion range
    const overlapping = textNodes.filter(tn => tn.start < end && tn.end > start);
    if (overlapping.length === 0) return;

    // Create the wrapper span
    const wrapper = document.createElement('span');
    wrapper.className = errorClass;
    // Pipeline Hardening v3.3: Use suggestion.id (UUID) instead of array index
    wrapper.dataset.suggestionId = suggestion.id || String(reverseIdx);
    wrapper.dataset.original = suggestion.original || '';
    wrapper.dataset.correction = suggestion.correction || '';
    wrapper.dataset.type = suggestion.type || 'spelling';
    wrapper.title = `${suggestion.type}: ${suggestion.correction}`;

    if (overlapping.length === 1) {
      // Simple case: suggestion falls within a single text node
      const tn = overlapping[0];
      const localStart = Math.max(0, start - tn.start);
      const localEnd = Math.min(tn.node.length, end - tn.start);

      // Split the text node
      const textContent = tn.node.textContent;
      const beforeText = textContent.slice(0, localStart);
      const errorText = textContent.slice(localStart, localEnd);
      const afterText = textContent.slice(localEnd);

      const parent = tn.node.parentNode;
      const errorTextNode = document.createTextNode(errorText);
      wrapper.appendChild(errorTextNode);

      // Replace the original text node
      if (afterText) {
        parent.insertBefore(document.createTextNode(afterText), tn.node.nextSibling);
      }
      parent.insertBefore(wrapper, tn.node.nextSibling || null);
      if (beforeText) {
        parent.insertBefore(document.createTextNode(beforeText), wrapper);
      }
      parent.removeChild(tn.node);

    } else {
      // Complex case: suggestion spans multiple text nodes
      // We use a Range to extract and wrap the content
      try {
        const range = document.createRange();

        const firstTN = overlapping[0];
        const lastTN = overlapping[overlapping.length - 1];
        const rangeStart = Math.max(0, start - firstTN.start);
        const rangeEnd = Math.min(lastTN.node.length, end - lastTN.start);

        range.setStart(firstTN.node, rangeStart);
        range.setEnd(lastTN.node, rangeEnd);

        range.surroundContents(wrapper);
      } catch (e) {
        // surroundContents can fail if the range crosses element boundaries
        // In that case, just wrap the text of the first overlapping node
        const tn = overlapping[0];
        const localStart = Math.max(0, start - tn.start);
        const localEnd = Math.min(tn.node.length, end - tn.start);

        if (localEnd > localStart) {
          const textContent = tn.node.textContent;
          const beforeText = textContent.slice(0, localStart);
          const errorText = textContent.slice(localStart, localEnd);
          const afterText = textContent.slice(localEnd);

          const parent = tn.node.parentNode;
          wrapper.appendChild(document.createTextNode(errorText));
          if (afterText) parent.insertBefore(document.createTextNode(afterText), tn.node.nextSibling);
          parent.insertBefore(wrapper, tn.node.nextSibling || null);
          if (beforeText) parent.insertBefore(document.createTextNode(beforeText), wrapper);
          parent.removeChild(tn.node);
        }
      }
    }

    // Rebuild textNodes array after modification (for next iteration)
    textNodes.length = 0;
    offset = 0;
    walkTextNodes(editor, (node) => {
      textNodes.push({ node, start: offset, end: offset + node.length });
      offset += node.length;
    });
  });
}

// Export for use in modules (if using ES6 modules)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    render,
    renderHighlightedText,
    escapeHtml,
    createSegments,
    sortSuggestions,
    getErrorClass,
    overlaySuggestions,
    clearOverlays
  };
}
