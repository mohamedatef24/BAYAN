/**
 * Bayan — Legacy Config (popup.js / sidepanel.js compatibility)
 *
 * This file provides the CONFIG object expected by popup.js and sidepanel.js.
 * All values are derived from BAYAN constants (shared/constants.js) where available,
 * or defined here for popup/sidepanel-specific settings.
 *
 * NOTE: popup.html and sidepanel.html load constants.js BEFORE this file,
 * so BAYAN is available here.
 */
const CONFIG = {
  API_BASE: typeof BAYAN !== 'undefined' ? BAYAN.API_BASE : 'https://bayan10-bayan-api.hf.space',
  MAX_ANALYZE_LENGTH: typeof BAYAN !== 'undefined' ? BAYAN.MAX_TEXT_LENGTH : 5000,
  MIN_ANALYZE_LENGTH: typeof BAYAN !== 'undefined' ? BAYAN.MIN_TEXT_LENGTH : 15,
  ANALYZE_DEBOUNCE_MS: 3000,
  MIN_SUMMARIZE_LENGTH: typeof BAYAN !== 'undefined' ? BAYAN.MIN_SUMMARIZE_LENGTH : 10,
};
