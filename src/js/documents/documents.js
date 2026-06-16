// Document management — UI wiring and initialization

function initDocuments() {
  const importBtn = document.getElementById('doc-import-btn');
  const importInput = document.getElementById('doc-import-input');
  const exportTrigger = document.getElementById('doc-export-trigger');
  const exportMenu = document.getElementById('doc-export-menu');
  const mobileExportTrigger = document.getElementById('doc-mobile-export-trigger');
  const exportSheet = document.getElementById('doc-export-sheet');

  if (importBtn && importInput) {
    importBtn.addEventListener('click', () => importInput.click());
    importInput.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) handleImportFile(file);
      importInput.value = '';
    });
  }

  if (exportTrigger && exportMenu) {
    exportTrigger.addEventListener('click', (e) => {
      e.stopPropagation();
      const open = exportMenu.classList.toggle('is-open');
      exportTrigger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    exportMenu.querySelectorAll('[data-export-format]').forEach((item) => {
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        const format = item.dataset.exportFormat;
        closeExportMenu();
        if (format === 'txt') exportTxtFile();
        else if (format === 'docx') exportDocxFile();
        else if (format === 'pdf') exportPdfFile();
      });
    });
  }

  if (mobileExportTrigger && exportSheet) {
    mobileExportTrigger.addEventListener('click', () => {
      exportSheet.classList.add('open');
      exportSheet.setAttribute('aria-hidden', 'false');
      mobileExportTrigger.setAttribute('aria-expanded', 'true');
    });

    const backdrop = document.getElementById('doc-export-sheet-backdrop');
    const closeBtn = document.getElementById('doc-export-sheet-close');
    const close = () => {
      exportSheet.classList.remove('open');
      exportSheet.setAttribute('aria-hidden', 'true');
      mobileExportTrigger.setAttribute('aria-expanded', 'false');
    };
    if (backdrop) backdrop.addEventListener('click', close);
    if (closeBtn) closeBtn.addEventListener('click', close);

    exportSheet.querySelectorAll('[data-export-format]').forEach((item) => {
      item.addEventListener('click', () => {
        const format = item.dataset.exportFormat;
        close();
        if (format === 'txt') exportTxtFile();
        else if (format === 'docx') exportDocxFile();
        else if (format === 'pdf') exportPdfFile();
      });
    });
  }

  document.addEventListener('click', () => closeExportMenu());

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeExportMenu();
      const sheet = document.getElementById('doc-export-sheet');
      if (sheet && sheet.classList.contains('open')) {
        sheet.classList.remove('open');
        sheet.setAttribute('aria-hidden', 'true');
        const mobileTrigger = document.getElementById('doc-mobile-export-trigger');
        if (mobileTrigger) mobileTrigger.setAttribute('aria-expanded', 'false');
      }
    }
  });

  const editor = getEditorElement();
  if (editor) {
    editor.addEventListener('input', () => {
      updateExportButtonStates();
    });
  }

  updateExportButtonStates();
}

function closeExportMenu() {
  const menu = document.getElementById('doc-export-menu');
  const trigger = document.getElementById('doc-export-trigger');
  if (menu) menu.classList.remove('is-open');
  if (trigger) trigger.setAttribute('aria-expanded', 'false');
}
