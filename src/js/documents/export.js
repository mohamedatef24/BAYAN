// Document export — TXT, DOCX, PDF

/**
 * Export editor content as UTF-8 .txt
 */
function exportTxtFile() {
  const text = getEditorText();
  if (!text || !text.trim()) {
    showDocToast('لا يوجد نص للتصدير', 'error');
    return;
  }

  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  downloadBlob(blob, EXPORT_TXT_FILENAME);
  showDocToast('تم تصدير الملف النصي', 'success');
}

/**
 * Export editor content as .docx with RTL Arabic support
 */
async function exportDocxFile() {
  const text = getEditorText();
  if (!text || !text.trim()) {
    showDocToast('لا يوجد نص للتصدير', 'error');
    return;
  }

  if (typeof docx === 'undefined') {
    try {
      await loadVendorScript('/js/vendor/docx.umd.js');
    } catch {
      showDocToast('تعذّر تحميل مكتبة Word', 'error');
      return;
    }
  }

  try {
    const paragraphs = splitIntoParagraphs(text);
    const children = paragraphs.map((block) =>
      new docx.Paragraph({
        bidirectional: true,
        alignment: docx.AlignmentType.RIGHT,
        children: [
          new docx.TextRun({
            text: block,
            rightToLeft: true,
            font: 'Arial'
          })
        ]
      })
    );

    if (children.length === 0) {
      showDocToast('لا يوجد نص للتصدير', 'error');
      return;
    }

    const document = new docx.Document({
      sections: [{
        properties: { rightToLeft: true },
        children
      }]
    });

    const blob = await docx.Packer.toBlob(document);
    downloadBlob(blob, EXPORT_DOCX_FILENAME);
    showDocToast('تم تصدير مستند Word', 'success');
  } catch (err) {
    console.error('DOCX export error:', err);
    showDocToast('تعذر تصدير ملف Word', 'error');
  }
}

/**
 * Build escaped HTML for PDF export (plain text only, no highlight markup)
 * @param {string} text
 * @returns {string}
 */
function buildPdfHtmlString(text) {
  const blocks = typeof splitIntoParagraphs === 'function'
    ? splitIntoParagraphs(text)
    : [];
  const parts = blocks.length ? blocks : [text];

  const paragraphStyle = [
    'margin:0 0 1em 0',
    'text-align:right',
    'direction:rtl',
    'unicode-bidi:embed',
    'font-family:\'Cairo\',\'Segoe UI\',\'Tahoma\',sans-serif',
    'font-size:18px',
    'line-height:1.9',
    'color:#1a1d21',
    'font-feature-settings:"liga" 1,"calt" 1',
    'word-wrap:break-word'
  ].join(';');

  const paragraphs = parts.map((block) => {
    const safe = escapeHtml(block).replace(/\n/g, '<br>');
    return `<p dir="rtl" lang="ar" style="${paragraphStyle}">${safe}</p>`;
  }).join('');

  return [
    '<div class="pdf-export-root" dir="rtl" lang="ar"',
    ' style="width:100%;padding:0;margin:0;',
    'font-family:\'Cairo\',\'Segoe UI\',\'Tahoma\',sans-serif;',
    'font-size:18px;line-height:1.9;text-align:right;direction:rtl;',
    'unicode-bidi:embed;color:#1a1d21;background:#ffffff;">',
    paragraphs,
    '</div>'
  ].join('');
}

/**
 * Apply RTL + font styles inside html2pdf's cloned document
 * @param {Document} clonedDoc
 */
function stylePdfClone(clonedDoc) {
  const root = clonedDoc.querySelector('.pdf-export-root');
  if (!root) return;

  root.setAttribute('dir', 'rtl');
  root.setAttribute('lang', 'ar');
  root.style.display = 'block';
  root.style.visibility = 'visible';
  root.style.opacity = '1';
  root.style.color = '#1a1d21';
  root.style.background = '#ffffff';
  root.style.fontFamily = "'Cairo', 'Segoe UI', 'Tahoma', sans-serif";
  root.style.fontSize = '18px';
  root.style.lineHeight = '1.9';
  root.style.textAlign = 'right';
  root.style.direction = 'rtl';
  root.style.unicodeBidi = 'embed';

  clonedDoc.querySelectorAll('.pdf-export-root p').forEach((p) => {
    p.setAttribute('dir', 'rtl');
    p.setAttribute('lang', 'ar');
    p.style.direction = 'rtl';
    p.style.unicodeBidi = 'embed';
    p.style.textAlign = 'right';
    p.style.fontFamily = "'Cairo', 'Segoe UI', 'Tahoma', sans-serif";
    p.style.fontFeatureSettings = '"liga" 1, "calt" 1';
  });
}

/**
 * Wait for Cairo font so Arabic glyphs render in the canvas snapshot
 */
async function waitForPdfFonts() {
  if (!document.fonts) {
    await new Promise((resolve) => setTimeout(resolve, 500));
    return;
  }
  try {
    await document.fonts.load('400 18px "Cairo"');
    await document.fonts.ready;
  } catch (_) {
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
}

/**
 * html2pdf options — foreignObjectRendering preserves Arabic shaping/RTL
 * @param {object} overrides
 */
function getPdfExportOptions(overrides = {}) {
  return {
    margin: [15, 15, 15, 15],
    filename: EXPORT_PDF_FILENAME,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#ffffff',
      logging: false,
      // Browser-native text layout — required for connected Arabic letters
      foreignObjectRendering: true,
      onclone: (clonedDoc) => stylePdfClone(clonedDoc),
      ...overrides
    },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
    pagebreak: { mode: ['css', 'legacy'] }
  };
}

/**
 * Export editor content as PDF via html2pdf
 */
async function exportPdfFile() {
  const text = getEditorText();
  if (!text || !text.trim()) {
    showDocToast('لا يوجد نص للتصدير', 'error');
    return;
  }

  if (typeof html2pdf === 'undefined') {
    try {
      await loadVendorScript('/js/vendor/html2pdf.bundle.min.js');
    } catch {
      showDocToast('تعذّر تحميل مكتبة PDF', 'error');
      return;
    }
  }

  // Show loading indicator
  if (typeof showToast === 'function') showToast('جاري تصدير PDF...');

  const html = buildPdfHtmlString(text);

  await waitForPdfFonts();
  // Let the UI update before heavy processing
  await new Promise((resolve) => setTimeout(resolve, 50));

  try {
    // Use non-foreignObject rendering (faster, avoids freeze on large texts)
    await html2pdf()
      .set(getPdfExportOptions({ foreignObjectRendering: false, scale: 1.5 }))
      .from(html, 'string')
      .save();

    showDocToast('تم تصدير PDF', 'success');
  } catch (err) {
    console.warn('PDF export failed:', err);
    showDocToast('تعذر تصدير PDF', 'error');
  }
}

/**
 * Check if editor has exportable content
 * @returns {boolean}
 */
function hasExportableContent() {
  const text = getEditorText();
  return !!(text && text.trim());
}

/**
 * Update export button disabled states
 */
function updateExportButtonStates() {
  const disabled = !hasExportableContent();
  document.querySelectorAll('[data-export-format]').forEach((btn) => {
    btn.disabled = disabled;
    btn.setAttribute('aria-disabled', disabled ? 'true' : 'false');
  });
}
