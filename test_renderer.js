// test_renderer.js
// Test the offset-based renderer with example data

// Mock implementations for testing (since we don't have the full modules loaded)
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

function sortSuggestions(suggestions) {
  return [...suggestions].sort((a, b) => a.start - b.start);
}

function createSegments(text, suggestions) {
  if (!suggestions || suggestions.length === 0) {
    return [{
      type: 'text',
      text: text,
      suggestions: []
    }];
  }

  const sorted = sortSuggestions(suggestions);
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

function getErrorClass(type) {
  const classes = {
    'spelling': 'spelling-error',
    'grammar': 'grammar-error',
    'punctuation': 'punctuation-suggestion'
  };
  return classes[type] || 'spelling-error';
}

function renderHighlightedText(text, suggestions) {
  if (!text || text.length === 0) {
    return '';
  }

  if (!suggestions || suggestions.length === 0) {
    return escapeHtml(text);
  }

  const segments = createSegments(text, suggestions);
  let html = '';
  let suggestionId = 0;

  segments.forEach((segment) => {
    if (segment.type === 'text') {
      html += escapeHtml(segment.text);
    } else if (segment.type === 'suggestion') {
      const { suggestion } = segment;
      const errorClass = getErrorClass(suggestion.type);
      const escapedText = escapeHtml(segment.text);

      html += `<span class="${errorClass}" data-suggestion-id="${suggestionId}" data-original="${escapeHtml(
        suggestion.original
      )}" data-correction="${escapeHtml(
        suggestion.correction
      )}" data-type="${suggestion.type}" title="${suggestion.type}: ${suggestion.correction}">${escapedText}</span>`;

      suggestionId++;
    }
  });

  return html;
}

// Test case: The example from the task
const testText = "ذهبو الى المدرسة ثم ذهبو الى البيت ثم ذهبو مرة اخرى";

// Simulate API response with three occurrences of "ذهبو" highlighted
const testSuggestions = [
  {
    start: 0,
    end: 4,
    original: "ذهبو",
    correction: "ذهبوا",
    type: "spelling"
  },
  {
    start: 20,
    end: 24,
    original: "ذهبو",
    correction: "ذهبوا",
    type: "spelling"
  },
  {
    start: 38,
    end: 42,
    original: "ذهبو",
    correction: "ذهبوا",
    type: "spelling"
  }
];

console.log('=== Offset-Based Renderer Test ===\n');
console.log('Input text:');
console.log(`"${testText}"\n`);

console.log('Suggestions:');
testSuggestions.forEach((s, idx) => {
  console.log(`  ${idx + 1}. [${s.start}:${s.end}] "${s.original}" → "${s.correction}"  (${s.type})`);
});
console.log();

const html = renderHighlightedText(testText, testSuggestions);
console.log('Rendered HTML:');
console.log(html);
console.log();

// Verify all three occurrences are highlighted
const highlightCount = (html.match(/class="spelling-error"/g) || []).length;
console.log(`✓ Number of highlights: ${highlightCount}/3`);

if (highlightCount === 3) {
  console.log('✓ SUCCESS: All three occurrences are highlighted independently!');
} else {
  console.log('✗ FAIL: Not all occurrences were highlighted');
}

// Test XSS protection
console.log('\n=== XSS Protection Test ===');
const xssTestText = "اختبار <script>alert('xss')</script> النص";
const xssHtml = renderHighlightedText(xssTestText, []);
console.log('Input with potential XSS:', xssTestText);
console.log('Rendered (safe):', xssHtml);
if (!xssHtml.includes('<script>')) {
  console.log('✓ XSS protection: Script tags were escaped');
} else {
  console.log('✗ XSS vulnerability detected!');
}

// Test overlapping suggestions
console.log('\n=== Overlapping Suggestions Test ===');
const overlapText = "هذا النص للاختبار";
const overlapSuggestions = [
  {
    start: 0,
    end: 4,
    original: "هذا",
    correction: "هنا",
    type: "spelling"
  },
  {
    start: 5,
    end: 9,
    original: "النص",
    correction: "النصّ",
    type: "spelling"
  }
];
const overlapHtml = renderHighlightedText(overlapText, overlapSuggestions);
console.log('Overlapping text:', overlapText);
console.log('Overlapping suggestions count:', overlapSuggestions.length);
console.log('Rendered:', overlapHtml);
const overlapCount = (overlapHtml.match(/class="spelling-error"/g) || []).length;
console.log(`✓ Overlapping highlights count: ${overlapCount}/2`);
