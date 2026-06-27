/**
 * Bayan — FNV-1a Hash (Single Implementation)
 *
 * 32-bit FNV-1a hash. Fast, zero dependencies.
 * Used for text deduplication in cache layers.
 *
 * @param {string} str
 * @returns {string} Base-36 hash string
 */
function bayanHash(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(36);
}
