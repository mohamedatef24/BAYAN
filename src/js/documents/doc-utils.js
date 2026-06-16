// Document utilities — normalize, download, paragraph splitting

const MAX_IMPORT_BYTES = 2 * 1024 * 1024; // 2MB
const EXPORT_TXT_FILENAME = 'bayan-document.txt';
const EXPORT_DOCX_FILENAME = 'bayan-document.docx';
const EXPORT_PDF_FILENAME = 'bayan-document.pdf';

/**
 * Normalize imported plain text
 * @param {string} text
 * @returns {string}
 */
function normalizeImportedText(text) {
  if (typeof text !== 'string') return '';
  let normalized = text.replace(/^\uFEFF/, '');
  normalized = normalized.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  return normalized;
}

/**
 * Split editor text into paragraphs for DOCX export
 * @param {string} text
 * @returns {string[]}
 */
function splitIntoParagraphs(text) {
  if (!text || !text.trim()) return [];

  const byDouble = text.split(/\n\s*\n/).map((s) => s.trim()).filter(Boolean);
  if (byDouble.length > 1) return byDouble;

  if (text.includes('\n')) {
    return text.split('\n').map((s) => s.trim()).filter((s) => s.length > 0);
  }

  return [text.trim()];
}

/**
 * Download a blob with file-saver or fallback
 * @param {Blob} blob
 * @param {string} filename
 */
function downloadBlob(blob, filename) {
  if (typeof saveAs === 'function') {
    saveAs(blob, filename);
    return;
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/**
 * Validate file size before import
 * @param {File} file
 * @returns {boolean}
 */
function validateFileSize(file) {
  return file && file.size <= MAX_IMPORT_BYTES;
}

/**
 * Get file extension lowercase
 * @param {string} name
 * @returns {string}
 */
function getFileExtension(name) {
  const parts = name.split('.');
  return parts.length > 1 ? parts.pop().toLowerCase() : '';
}
