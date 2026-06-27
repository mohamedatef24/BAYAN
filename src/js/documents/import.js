// Document import — TXT and DOCX

/**
 * Import a .txt file via FileReader
 * @param {File} file
 */
function importTxtFile(file) {
  if (!validateFileSize(file)) {
    showDocToast('الملف كبير جداً. الحد الأقصى ٢ ميغابايت.', 'error');
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const text = normalizeImportedText(e.target.result);
      loadDocumentText(text, { filename: file.name });
      showDocToast('تم تحميل الملف بنجاح', 'success');
    } catch (err) {
      console.error('TXT import error:', err);
      showDocToast('تعذر قراءة الملف النصي', 'error');
    }
  };
  reader.onerror = () => {
    showDocToast('فشل قراءة الملف', 'error');
  };
  reader.readAsText(file, 'UTF-8');
}

/**
 * Import a .docx file via Mammoth extractRawText
 * @param {File} file
 */
async function importDocxFile(file) {
  if (typeof mammoth === 'undefined') {
    try {
      await loadVendorScript('/js/vendor/mammoth.browser.min.js');
    } catch {
      showDocToast('تعذّر تحميل مكتبة Word', 'error');
      return;
    }
  }

  if (!validateFileSize(file)) {
    showDocToast('الملف كبير جداً. الحد الأقصى ٢ ميغابايت.', 'error');
    return;
  }

  try {
    const arrayBuffer = await file.arrayBuffer();
    const result = await mammoth.extractRawText({ arrayBuffer });

    if (result.messages && result.messages.length) {
      console.warn('Mammoth messages:', result.messages);
    }

    const text = normalizeImportedText(result.value || '');
    if (!text.trim()) {
      showDocToast('الملف لا يحتوي على نص', 'error');
      return;
    }

    loadDocumentText(text, { filename: file.name });
    showDocToast('تم تحميل مستند Word بنجاح', 'success');
  } catch (err) {
    console.error('DOCX import error:', err);
    showDocToast('تعذر قراءة ملف Word. قد يكون تالفاً.', 'error');
  }
}

/**
 * Route file to correct importer by extension
 * @param {File} file
 */
async function handleImportFile(file) {
  if (!file) return;

  const ext = getFileExtension(file.name);

  if (ext === 'txt' || file.type === 'text/plain') {
    importTxtFile(file);
    return;
  }

  if (ext === 'docx' || file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
    await importDocxFile(file);
    return;
  }

  showDocToast('نوع الملف غير مدعوم. استخدم .txt أو .docx', 'error');
}
