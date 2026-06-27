/**
 * Bayan Chrome Extension — Patch Engine Tests
 *
 * Tests for HIGH-1 fix: applyAndRebase()
 * Run with: node extension/tests/test_patches.js
 *
 * Test scenarios:
 *   1. Shorter replacement (delta < 0)
 *   2. Longer replacement (delta > 0)
 *   3. Same-length replacement (delta = 0)
 *   4. Multiple sequential applies
 *   5. Apply first suggestion (edge case)
 *   6. Apply last suggestion (edge case)
 *   7. Dismiss (no rebase needed)
 *   8. Apply all patches
 */

// ── Load modules (Node.js — no DOM required) ──
// These are global-scope scripts, so we eval them
const fs = require('fs');
const path = require('path');

function loadModule(filename) {
  const code = fs.readFileSync(path.join(__dirname, '..', 'shared', filename), 'utf-8');
  eval(code);
}

// Load in dependency order
loadModule('config.js');
loadModule('bayan-renderer.js');
loadModule('bayan-ui.js');
loadModule('bayan-patches.js');

// ── Test utilities ──
let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (condition) {
    passed++;
    console.log(`  ✅ ${message}`);
  } else {
    failed++;
    console.error(`  ❌ ${message}`);
  }
}

function assertEqual(actual, expected, message) {
  if (actual === expected) {
    passed++;
    console.log(`  ✅ ${message}`);
  } else {
    failed++;
    console.error(`  ❌ ${message}`);
    console.error(`     Expected: "${expected}"`);
    console.error(`     Actual:   "${actual}"`);
  }
}

// ══════════════════════════════════════════════════════════
// Test data: Arabic text with 3 suggestions
// ══════════════════════════════════════════════════════════
//
// Text: "أنا ذاهب الى البت والمدرسه"
//        0123456789012345678901234567
//
// Suggestion A: "الى" → "إلى"     (start:10, end:13)  — same length (3→3, delta=0)
// Suggestion B: "البت" → "البيت"   (start:14, end:17)  — longer (+1, delta=+1)
// Suggestion C: "المدرسه" → "المدرسة" (start:19, end:26) — same length (7→7, delta=0)
//

const TEXT = 'أنا ذاهب الى البت والمدرسه';

function makeSuggestions() {
  return [
    { id: 'a', start: 10, end: 13, original: 'الى', correction: 'إلى', type: 'grammar' },
    { id: 'b', start: 14, end: 17, original: 'البت', correction: 'البيت', type: 'spelling' },
    { id: 'c', start: 19, end: 26, original: 'المدرسه', correction: 'المدرسة', type: 'spelling' },
  ];
}

// ══════════════════════════════════════════════════════════
// TEST 1: Same-length replacement (delta = 0)
// ══════════════════════════════════════════════════════════
console.log('\n── TEST 1: Same-length replacement (delta = 0) ──');
{
  const suggestions = makeSuggestions();
  const result = applyAndRebase(TEXT, suggestions[0], 'إلى', suggestions);

  assertEqual(result.text, 'أنا ذاهب إلى البت والمدرسه', 'Text: "الى" → "إلى"');
  assert(result.suggestions.length === 2, 'Removed applied suggestion (2 remaining)');
  assertEqual(result.suggestions[0].start, 14, 'Suggestion B start unchanged (14)');
  assertEqual(result.suggestions[0].end, 17, 'Suggestion B end unchanged (17)');
  assertEqual(result.suggestions[1].start, 19, 'Suggestion C start unchanged (19)');
  assertEqual(result.suggestions[1].end, 26, 'Suggestion C end unchanged (26)');
}

// ══════════════════════════════════════════════════════════
// TEST 2: Longer replacement (delta > 0)
// ══════════════════════════════════════════════════════════
console.log('\n── TEST 2: Longer replacement (delta > 0) ──');
{
  const suggestions = makeSuggestions();
  // Apply B: "البت" (3 chars) → "البيت" (5 chars), delta = +2
  const result = applyAndRebase(TEXT, suggestions[1], 'البيت', suggestions);

  assertEqual(result.text, 'أنا ذاهب الى البيت والمدرسه', 'Text: "البت" → "البيت"');
  assert(result.suggestions.length === 2, 'Removed applied suggestion (2 remaining)');

  // A is BEFORE B — should NOT shift
  assertEqual(result.suggestions[0].start, 10, 'Suggestion A start unchanged (10)');
  assertEqual(result.suggestions[0].end, 13, 'Suggestion A end unchanged (13)');

  // C is AFTER B — should shift by +2
  assertEqual(result.suggestions[1].start, 21, 'Suggestion C start shifted 19→21 (+2)');
  assertEqual(result.suggestions[1].end, 28, 'Suggestion C end shifted 26→28 (+2)');

  // Verify the shifted offsets are correct
  assertEqual(result.text.substring(result.suggestions[1].start, result.suggestions[1].end),
    'المدرسه', 'Rebased offset C extracts correct text');
}

// ══════════════════════════════════════════════════════════
// TEST 3: Shorter replacement (delta < 0)
// ══════════════════════════════════════════════════════════
console.log('\n── TEST 3: Shorter replacement (delta < 0) ──');
{
  // Custom text for this test
  const text = 'هذا النصص خاطئ والكلمه خطأ';
  // "النصص" (5) → "النص" (4), delta = -1
  const suggestions = [
    { id: 'x', start: 4, end: 9, original: 'النصص', correction: 'النص', type: 'spelling' },
    { id: 'y', start: 17, end: 23, original: 'والكلمه', correction: 'والكلمة', type: 'spelling' },
  ];

  const result = applyAndRebase(text, suggestions[0], 'النص', suggestions);

  assertEqual(result.text, 'هذا النص خاطئ والكلمه خطأ', 'Text: "النصص" → "النص"');
  assert(result.suggestions.length === 1, '1 remaining');
  assertEqual(result.suggestions[0].start, 16, 'Suggestion Y start shifted 17→16 (-1)');
  assertEqual(result.suggestions[0].end, 22, 'Suggestion Y end shifted 23→22 (-1)');
  assertEqual(result.text.substring(result.suggestions[0].start, result.suggestions[0].end),
    'والكلمه', 'Rebased offset Y extracts correct text');
}

// ══════════════════════════════════════════════════════════
// TEST 4: Multiple sequential applies
// ══════════════════════════════════════════════════════════
console.log('\n── TEST 4: Multiple sequential applies ──');
{
  let text = TEXT;
  let suggestions = makeSuggestions();

  // Apply A first (same-length)
  let r1 = applyAndRebase(text, suggestions[0], 'إلى', suggestions);
  text = r1.text;
  suggestions = r1.suggestions;
  assertEqual(text, 'أنا ذاهب إلى البت والمدرسه', 'After apply A');
  assert(suggestions.length === 2, '2 remaining after A');

  // Apply B (longer, +2)
  let r2 = applyAndRebase(text, suggestions[0], 'البيت', suggestions);
  text = r2.text;
  suggestions = r2.suggestions;
  assertEqual(text, 'أنا ذاهب إلى البيت والمدرسه', 'After apply B');
  assert(suggestions.length === 1, '1 remaining after B');

  // Apply C (same-length) — offsets should be correctly rebased
  let r3 = applyAndRebase(text, suggestions[0], 'المدرسة', suggestions);
  text = r3.text;
  suggestions = r3.suggestions;
  assertEqual(text, 'أنا ذاهب إلى البيت والمدرسة', 'After apply C — fully corrected');
  assert(suggestions.length === 0, '0 remaining — all applied');

  // Verify final text matches applyAllPatches
  const expectedFull = applyAllPatches(TEXT, makeSuggestions());
  assertEqual(text, expectedFull, 'Sequential applies produce same result as applyAllPatches');
}

// ══════════════════════════════════════════════════════════
// TEST 5: Apply first suggestion (edge case)
// ══════════════════════════════════════════════════════════
console.log('\n── TEST 5: Apply first suggestion ──');
{
  const text = 'الخطاء في البداية ثم نص صحيح';
  const suggestions = [
    { id: 'f', start: 0, end: 6, original: 'الخطاء', correction: 'الخطأ', type: 'spelling' },
    { id: 'g', start: 20, end: 23, original: 'ثم ', correction: 'ثمّ ', type: 'grammar' },
  ];

  const result = applyAndRebase(text, suggestions[0], 'الخطأ', suggestions);
  assertEqual(result.text.substring(0, 5), 'الخطأ', 'First word replaced correctly');
  // delta = 5 - 6 = -1
  assertEqual(result.suggestions[0].start, 19, 'Second suggestion shifted by -1');
  assertEqual(result.suggestions[0].end, 22, 'Second suggestion end shifted by -1');
}

// ══════════════════════════════════════════════════════════
// TEST 6: Apply last suggestion (edge case)
// ══════════════════════════════════════════════════════════
console.log('\n── TEST 6: Apply last suggestion ──');
{
  const suggestions = makeSuggestions();
  // Apply C (last one) — no suggestions after it to rebase
  const result = applyAndRebase(TEXT, suggestions[2], 'المدرسة', suggestions);

  assertEqual(result.text, 'أنا ذاهب الى البت والمدرسة', 'Last suggestion applied');
  assert(result.suggestions.length === 2, '2 remaining');
  assertEqual(result.suggestions[0].start, 10, 'A unchanged (before C)');
  assertEqual(result.suggestions[1].start, 14, 'B unchanged (before C)');
}

// ══════════════════════════════════════════════════════════
// TEST 7: Dismiss (keep original)
// ══════════════════════════════════════════════════════════
console.log('\n── TEST 7: Dismiss (removeSuggestion) ──');
{
  const suggestions = makeSuggestions();
  const remaining = removeSuggestion(suggestions, 'b');
  assert(remaining.length === 2, '2 remaining after dismiss');
  assert(remaining.every(s => s.id !== 'b'), 'Dismissed suggestion removed');
  // Offsets of remaining should be unchanged (no rebase on dismiss)
  assertEqual(remaining[0].start, 10, 'A unchanged');
  assertEqual(remaining[1].start, 19, 'C unchanged');
}

// ══════════════════════════════════════════════════════════
// TEST 8: applyAllPatches
// ══════════════════════════════════════════════════════════
console.log('\n── TEST 8: applyAllPatches ──');
{
  const result = applyAllPatches(TEXT, makeSuggestions());
  assertEqual(result, 'أنا ذاهب إلى البيت والمدرسة', 'All patches applied correctly');
}

// ══════════════════════════════════════════════════════════
// TEST 9: countByType
// ══════════════════════════════════════════════════════════
console.log('\n── TEST 9: countByType ──');
{
  const counts = countByType(makeSuggestions());
  assertEqual(counts.spelling, 2, '2 spelling');
  assertEqual(counts.grammar, 1, '1 grammar');
  assertEqual(counts.punctuation, 0, '0 punctuation');
}

// ══════════════════════════════════════════════════════════
// Summary
// ══════════════════════════════════════════════════════════
console.log(`\n${'═'.repeat(50)}`);
console.log(`Results: ${passed} passed, ${failed} failed`);
console.log(`${'═'.repeat(50)}`);
process.exit(failed > 0 ? 1 : 0);
