/**
 * Bayan Chrome Extension — API Client
 *
 * Reused from: src/js/api.js (L2-20)
 * Adaptation:  Relative paths replaced with CONFIG.API_BASE.
 *              Only analyzeText and summarizeText are needed (Phase 0 audit).
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
