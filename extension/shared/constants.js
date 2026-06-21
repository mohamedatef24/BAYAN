/**
 * Bayan — Shared Constants (Single Source of Truth)
 *
 * ALL shared configuration lives here.
 * No hardcoded API URLs, timeouts, or limits elsewhere.
 *
 * Used by: background.js, analysis-controller.js, config.js (legacy alias)
 */
const BAYAN = {
  /** Backend API base URL (HuggingFace Spaces) */
  API_BASE: 'https://bayan10-bayan-api.hf.space',

  /** Network timeout for API calls (ms) */
  API_TIMEOUT_MS: 20000,

  /** Max retries on network failure */
  MAX_RETRIES: 1,

  /** Cache TTL (ms) — 5 minutes */
  CACHE_TTL_MS: 300000,

  /** Max cache entries */
  CACHE_MAX_ENTRIES: 20,

  /** Max text length for analysis */
  MAX_TEXT_LENGTH: 5000,

  /** Min text length to trigger analysis */
  MIN_TEXT_LENGTH: 15,

  /** Min Arabic characters required */
  MIN_ARABIC_CHARS: 5,

  /** Min text length for summarization */
  MIN_SUMMARIZE_LENGTH: 10,

  /** Protected hosts — disable contenteditable injection */
  PROTECTED_HOSTS: [
    'mail.google.com',
    'docs.google.com',
    'sheets.google.com',
    'slides.google.com',
    'notion.so',
    'www.notion.so',
  ],
};
