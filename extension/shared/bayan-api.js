/**
 * Bayan Chrome Extension — API Client
 *
 * Reused from: src/js/api.js (L2-20)
 * Adaptation:  Relative paths replaced with CONFIG.API_BASE.
 *
 * Endpoints: analyze, summarize, dialect, quran, autocomplete, health.
 */

/**
 * Send text to the unified analysis pipeline.
 * Backend: /api/analyze (Spelling → Grammar → Punctuation)
 *
 * @param {string} text - Arabic text to analyze
 * @param {AbortSignal} [signal] - Optional abort signal
 * @returns {Promise<Object>} { original, corrected, suggestions[], timing_ms, status }
 */
async function bayanAnalyze(text, signal) {
  const response = await fetch(`${CONFIG.API_BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
    signal,
  });
  if (!response.ok) {
    throw new Error(`Analyze API error: ${response.status}`);
  }
  return await response.json();
}

/**
 * Summarize Arabic text.
 * Backend: /api/summarize
 *
 * @param {string} text - Arabic text to summarize
 * @param {number} [length=2] - Summary length (1=short, 2=medium, 3=long)
 * @param {boolean} [fullText=true] - Summarize full text or first paragraph
 * @returns {Promise<Object>} { summary, status, original_length, summary_length }
 */
async function bayanSummarize(text, length = 2, fullText = true) {
  const response = await fetch(`${CONFIG.API_BASE}/api/summarize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, length, full_text: fullText }),
  });
  if (!response.ok) {
    throw new Error(`Summarize API error: ${response.status}`);
  }
  return await response.json();
}

/**
 * Convert dialectal Arabic to Modern Standard Arabic (MSA).
 * Backend: /api/dialect
 *
 * @param {string} text - Dialectal Arabic text
 * @param {AbortSignal} [signal] - Optional abort signal
 * @returns {Promise<Object>} { original_text, converted_text, status }
 */
async function bayanDialect(text, signal) {
  const response = await fetch(`${CONFIG.API_BASE}/api/dialect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
    signal,
  });
  if (!response.ok) {
    throw new Error(`Dialect API error: ${response.status}`);
  }
  return await response.json();
}

/**
 * Verify / search Quranic text.
 * Backend: /api/quran
 *
 * @param {string} text - Text to verify against the Quran
 * @param {string} [language='تدقيق الايات'] - Target operation type
 * @param {AbortSignal} [signal] - Optional abort signal
 * @returns {Promise<Object>} { matched_segment, full_verse, ... } or { error }
 */
async function bayanQuran(text, language = 'تدقيق الايات', signal, topN = 1) {
  const body = { text, language };
  if (topN > 1) body.top_n = topN;
  const response = await fetch(`${CONFIG.API_BASE}/api/quran`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  // Quran endpoint returns 404 with a JSON {error} body on "no match" —
  // treat that as a normal (non-throwing) result so the UI can show it.
  if (!response.ok && response.status !== 404) {
    throw new Error(`Quran API error: ${response.status}`);
  }
  return await response.json();
}

/**
 * Get autocomplete suggestions for Arabic text.
 * Backend: /api/autocomplete
 *
 * @param {string} context - Text before the cursor
 * @param {number} [n=3] - Number of suggestions to return
 * @param {AbortSignal} [signal] - Optional abort signal
 * @returns {Promise<Object>} { suggestions: string[], status }
 */
async function bayanAutocomplete(context, n = 3, signal) {
  const response = await fetch(`${CONFIG.API_BASE}/api/autocomplete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ context, n }),
    signal,
  });
  if (!response.ok) {
    throw new Error(`Autocomplete API error: ${response.status}`);
  }
  return await response.json();
}

/**
 * Check backend health.
 * Backend: /api/health
 *
 * @returns {Promise<Object>} { status, mode, models }
 */
async function bayanHealthCheck() {
  const response = await fetch(`${CONFIG.API_BASE}/api/health`, {
    method: 'GET',
  });
  if (!response.ok) {
    throw new Error(`Health check error: ${response.status}`);
  }
  return await response.json();
}
