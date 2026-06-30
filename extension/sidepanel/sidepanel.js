/**
 * Bayan Chrome Extension — Side Panel Logic
 *
 * Persistent workspace panel — reuses shared modules.
 *
 * Key differences from popup.js:
 *   - Persistent: panel stays open across page navigations
 *   - Auto-analysis: text injected from context menu auto-analyzes
 *   - Debounced live updates: re-analyzes on user edits (500ms debounce)
 *   - Write-back-to-page: can apply corrections/results to the source field
 *   - State persistence: last analysis saved to chrome.storage.session
 */

document.addEventListener('DOMContentLoaded', () => {
  // ── Tab constants ──
  const TAB = { CORRECT: 'correct', SUMMARIZE: 'summarize', DIALECT: 'dialect', QURAN: 'quran' };

  // ── Element references ──
  const inputText = document.getElementById('input-text');
  const charCount = document.getElementById('char-count');
  const wordCount = document.getElementById('word-count');
  const btnCorrect = document.getElementById('btn-correct');
  const btnClear = document.getElementById('btn-clear');
  const btnApplyAll = document.getElementById('btn-apply-all');
  const btnApplyPage = document.getElementById('btn-apply-page');
  const btnCopyText = document.getElementById('btn-copy-text');
  const scoreSection = document.getElementById('score-section');
  const suggestionsSection = document.getElementById('suggestions-section');
  const suggestionsList = document.getElementById('suggestions-list');
  const timingSection = document.getElementById('timing-section');
  const timingText = document.getElementById('timing-text');
  const loadingOverlay = document.getElementById('loading-overlay');
  const loadingTextEl = document.getElementById('loading-text');

  // Summary tab
  const summaryInputText = document.getElementById('summary-input-text');
  const summaryWordCountInput = document.getElementById('summary-word-count-input');
  const btnSummarize = document.getElementById('btn-summarize');
  const summaryResultSection = document.getElementById('summary-result-section');
  const summaryText = document.getElementById('summary-text');
  const summaryStats = document.getElementById('summary-stats');
  const summaryWordCount = document.getElementById('summary-word-count');
  const summaryCompression = document.getElementById('summary-compression');
  const btnCopySummary = document.getElementById('btn-copy-summary');

  // Score
  const scoreValue = document.getElementById('score-value');
  const scoreCircle = document.getElementById('score-circle');
  const scoreHint = document.getElementById('score-hint');
  const countSpelling = document.getElementById('count-spelling');
  const countGrammar = document.getElementById('count-grammar');
  const countPunctuation = document.getElementById('count-punctuation');

  // ══════════════════════════════════════════════════════════
  // State
  // ══════════════════════════════════════════════════════════
  let currentSuggestions = [];
  let analyzedText = '';
  let isStale = false;
  let isAnalyzing = false;
  let contextConsumed = false;
  let sourceSelectionText = '';
  let summaryMode = 'paragraph';

  const SCORE_CIRCUMFERENCE = 440;

  // ══════════════════════════════════════════════════════════
  // Tab switching
  // ══════════════════════════════════════════════════════════
  document.querySelectorAll('.sp-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      const targetTab = tab.dataset.tab;
      document.querySelectorAll('.sp-tab').forEach((t) => {
        t.classList.toggle('active', t.dataset.tab === targetTab);
        t.setAttribute('aria-selected', t.dataset.tab === targetTab ? 'true' : 'false');
      });
      document.querySelectorAll('.sp-panel').forEach((p) => {
        p.classList.toggle('active', p.id === `panel-${targetTab}`);
      });
      saveState();
    });
  });

  // ══════════════════════════════════════════════════════════
  // Character & word counter
  // ══════════════════════════════════════════════════════════
  function updateCounts(textarea, charEl, wordEl) {
    const text = textarea.value;
    const chars = text.length;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    if (charEl) charEl.textContent = chars.toLocaleString('ar-EG');
    if (wordEl) wordEl.textContent = words.toLocaleString('ar-EG');
  }

  inputText.addEventListener('input', () => {
    updateCounts(inputText, charCount, wordCount);
    saveState();

    if (currentSuggestions.length > 0 && inputText.value !== analyzedText) {
      markStale();
    }
  });

  summaryInputText.addEventListener('input', () => {
    const text = summaryInputText.value.trim();
    const words = text ? text.split(/\s+/).length : 0;
    if (summaryWordCountInput) summaryWordCountInput.textContent = words.toLocaleString('ar-EG');
    saveState();
  });

  // ══════════════════════════════════════════════════════════
  // Staleness management
  // ══════════════════════════════════════════════════════════
  function markStale() {
    if (isStale) return;
    isStale = true;
    if (suggestionsSection) suggestionsSection.classList.add('sp-stale');
    showToast('⚠ النص تغيّر — أعد التحليل لتحديث الاقتراحات', 4000);
    btnCorrect.innerHTML = `
      <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h5M20 20v-5h-5M4 9a8 8 0 0114-3M20 15a8 8 0 01-14 3"/></svg>
      إعادة التحليل`;
  }

  function clearStale() {
    isStale = false;
    if (suggestionsSection) suggestionsSection.classList.remove('sp-stale');
    btnCorrect.innerHTML = `
      <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4"/></svg>
      تحليل وتصحيح`;
  }

  // ══════════════════════════════════════════════════════════
  // Loading & Toast
  // ══════════════════════════════════════════════════════════
  function setLoading(show, text = 'جارٍ التحليل...') {
    loadingOverlay.classList.toggle('is-hidden', !show);
    loadingTextEl.textContent = text;
  }

  function showToast(message, duration = 2500) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('is-visible');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.remove('is-visible'), duration);
  }

  // ══════════════════════════════════════════════════════════
  // Write-back to the page field (panel → background → content script)
  // ══════════════════════════════════════════════════════════
  function writeBackToPage(text, mode = 'auto', source = 'correct', find = '') {
    try {
      chrome.runtime.sendMessage(
        { type: 'WRITE_BACK_TO_PAGE', text, mode, source, find },
        (resp) => {
          if (resp && resp.ok) {
            sourceSelectionText = text;
            showToast('✓ تم تطبيق التغييرات في الصفحة');
          } else showToast('تعذّر الكتابة في الصفحة — انسخ النص يدوياً');
        }
      );
    } catch {
      showToast('تعذّر الكتابة في الصفحة — انسخ النص يدوياً');
    }
  }

  // ══════════════════════════════════════════════════════════
  // Score ring
  // ══════════════════════════════════════════════════════════
  function updateScore(spelling, grammar, punctuation) {
    const score = calculateWritingScore(spelling, grammar, punctuation);
    const total = spelling + grammar + punctuation;

    scoreSection.classList.remove('is-hidden');

    if (scoreValue) {
      const hasText = inputText.value.trim().length > 0;
      scoreValue.textContent = (hasText || total > 0) ? score.toLocaleString('ar-EG') : '--';
    }
    if (scoreCircle) {
      const offset = SCORE_CIRCUMFERENCE - (score / 100) * SCORE_CIRCUMFERENCE;
      scoreCircle.style.strokeDashoffset = String(offset);
    }
    if (scoreHint) {
      const hasText = inputText.value.trim().length > 0;
      if (total === 0 && hasText) {
        scoreHint.textContent = 'كتابة ممتازة! استمر.';
      } else if (total === 0) {
        scoreHint.innerHTML = 'ابدأ الكتابة لرؤية تقييمك<br><span class="sp-score-hint-sub">تحسين القواعد يرفع التقييم</span>';
      } else {
        scoreHint.textContent = getScoreHint(score, total);
      }
    }
    if (countSpelling) countSpelling.textContent = spelling.toLocaleString('ar-EG');
    if (countGrammar) countGrammar.textContent = grammar.toLocaleString('ar-EG');
    if (countPunctuation) countPunctuation.textContent = punctuation.toLocaleString('ar-EG');
  }

  // ══════════════════════════════════════════════════════════
  // Render suggestions list
  // ══════════════════════════════════════════════════════════
  function renderSuggestions(suggestions) {
    currentSuggestions = suggestions;

    if (!suggestions || suggestions.length === 0) {
      btnApplyAll.classList.add('is-hidden');
      if (analyzedText) {
        suggestionsSection.classList.remove('is-hidden');
        suggestionsList.innerHTML = '<div class="sp-empty-state"><svg class="sp-empty-state-icon" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg><p class="sp-empty-state-text">نصك ممتاز! لم نجد أي أخطاء</p></div>';
      } else {
        suggestionsSection.classList.add('is-hidden');
      }
      return;
    }

    suggestionsSection.classList.remove('is-hidden');
    suggestionsList.innerHTML = suggestions.map((s, i) => buildSuggestionCardHTML(s, i)).join('');

    suggestionsList.querySelectorAll('.bayan-alt-chip').forEach((chip) => {
      chip.addEventListener('click', (e) => {
        e.stopPropagation();

        if (isStale) {
          showToast('⚠ أعد التحليل أولاً — النص تغيّر');
          return;
        }

        const suggestionId = chip.dataset.cardId;
        const altText = chip.dataset.cardAlt;
        const suggestion = currentSuggestions.find((s) => String(s.id || '') === String(suggestionId));
        if (!suggestion) return;

        if (altText === suggestion.original) {
          currentSuggestions = removeSuggestion(currentSuggestions, suggestion.id);
        } else {
          const result = applyAndRebase(analyzedText, suggestion, altText, currentSuggestions);
          analyzedText = result.text;
          currentSuggestions = result.suggestions;
          inputText.value = analyzedText;
          updateCounts(inputText, charCount, wordCount);
        }

        const counts = countByType(currentSuggestions);
        updateScore(counts.spelling, counts.grammar, counts.punctuation);
        renderSuggestions(currentSuggestions);
        saveState();
        showToast('✓ تم التصحيح');
      });
    });

    // Show apply-all with count
    btnApplyAll.textContent = 'تطبيق الكل (' + suggestions.length.toLocaleString('ar-EG') + ')';
    btnApplyAll.classList.remove('is-hidden');
  }

  // ══════════════════════════════════════════════════════════
  // Core analysis function
  // ══════════════════════════════════════════════════════════
  async function runAnalysis(text) {
    if (!text || text.trim().split(/\s+/).length < 2) {
      showToast('أدخل كلمتين على الأقل');
      return;
    }
    if (text.length > CONFIG.MAX_ANALYZE_LENGTH) {
      showToast('النص طويل جداً (الحد الأقصى ٥٠٠٠ حرف)');
      return;
    }

    isAnalyzing = true;
    setLoading(true, 'جارٍ التحليل...');
    clearStale();

    try {
      const data = await bayanAnalyze(text);

      if (data.status === 'success' || data.status === 'partial') {
        const suggestions = sortSuggestions(data.suggestions || []);
        currentSuggestions = suggestions;
        analyzedText = data.original;

        inputText.value = analyzedText;
        updateCounts(inputText, charCount, wordCount);

        const counts = countByType(suggestions);
        updateScore(counts.spelling, counts.grammar, counts.punctuation);
        renderSuggestions(suggestions);

        if (data.timing_ms) {
          timingSection.classList.remove('is-hidden');
          timingText.textContent = `التحليل: ${data.timing_ms.total_ms || 0}ms`;
        }

        saveState();
      } else {
        showToast('تعذّر التحليل — حاول مرة أخرى');
      }
    } catch (error) {
      console.error('[Bayan SP] Analysis error:', error);
      showToast('خطأ في الاتصال — تحقق من الإنترنت');
    } finally {
      isAnalyzing = false;
      setLoading(false);
    }
  }

  // ══════════════════════════════════════════════════════════
  // State persistence (side panel survives navigation)
  // ══════════════════════════════════════════════════════════
  function getStorage() {
    return chrome.storage?.session || chrome.storage?.local;
  }

  function saveState() {
    const storage = getStorage();
    if (!storage) return;

    const activeTabEl = document.querySelector('.sp-tab.active');
    const activeTab = activeTabEl ? activeTabEl.dataset.tab : 'correct';

    storage.set({
      spLastText: analyzedText,
      spLastSuggestions: currentSuggestions,
      spLastInput: inputText.value,
      spLastSummarize: (document.getElementById('summary-input-text') || {}).value || '',
      spLastDialect: (document.getElementById('dialect-input-text') || {}).value || '',
      spLastQuran: (document.getElementById('quran-input-text') || {}).value || '',
      spActiveTab: activeTab
    }).catch(() => {});
  }

  async function restoreState() {
    const storage = getStorage();
    if (!storage) return false;

    try {
      const data = await storage.get(['spLastText', 'spLastSuggestions', 'spLastInput', 'spLastSummarize', 'spLastDialect', 'spLastQuran', 'spActiveTab']);

      if (data.spLastSummarize) {
        const sInput = document.getElementById('summary-input-text');
        if (sInput) {
          sInput.value = data.spLastSummarize;
          const words = data.spLastSummarize.trim() ? data.spLastSummarize.trim().split(/\s+/).length : 0;
          if (summaryWordCountInput) summaryWordCountInput.textContent = words.toLocaleString('ar-EG');
        }
      }
      if (data.spLastDialect) {
        const dInput = document.getElementById('dialect-input-text');
        if (dInput) { dInput.value = data.spLastDialect; updateCounts(dInput, document.getElementById('dialect-char-count'), null); }
      }
      if (data.spLastQuran) {
        const qInput = document.getElementById('quran-input-text');
        if (qInput) { qInput.value = data.spLastQuran; updateCounts(qInput, document.getElementById('quran-char-count'), null); }
      }

      if (data.spActiveTab) {
        const tabBtn = document.querySelector(`.sp-tab[data-tab="${data.spActiveTab}"]`);
        if (tabBtn) tabBtn.click();
      }

      if (!data.spLastText || !data.spLastSuggestions) return false;

      analyzedText = data.spLastText;
      currentSuggestions = data.spLastSuggestions;
      inputText.value = data.spLastInput || analyzedText;
      updateCounts(inputText, charCount, wordCount);

      const counts = countByType(currentSuggestions);
      updateScore(counts.spelling, counts.grammar, counts.punctuation);
      renderSuggestions(currentSuggestions);

      return true;
    } catch {
      return false;
    }
  }

  // ══════════════════════════════════════════════════════════
  // Button handlers
  // ══════════════════════════════════════════════════════════
  btnCorrect.addEventListener('click', () => {
    const text = inputText.value.trim();
    runAnalysis(text);
  });

  btnClear.addEventListener('click', () => {
    inputText.value = '';
    analyzedText = '';
    sourceSelectionText = '';
    updateCounts(inputText, charCount, wordCount);
    scoreSection.classList.add('is-hidden');
    suggestionsSection.classList.add('is-hidden');
    timingSection.classList.add('is-hidden');
    currentSuggestions = [];
    clearStale();
    const storage = getStorage();
    if (storage) storage.remove(['spLastText', 'spLastSuggestions', 'spLastInput']).catch(() => {});
  });

  btnApplyAll.addEventListener('click', () => {
    if (currentSuggestions.length === 0) return;
    if (isStale) {
      showToast('⚠ أعد التحليل أولاً — النص تغيّر');
      return;
    }

    analyzedText = applyAllPatches(analyzedText, currentSuggestions);
    inputText.value = analyzedText;
    updateCounts(inputText, charCount, wordCount);
    currentSuggestions = [];
    updateScore(0, 0, 0);
    renderSuggestions([]);
    saveState();
    writeBackToPage(analyzedText, 'auto', 'correct', sourceSelectionText);
    showToast('✓ تم تطبيق جميع التصحيحات');
  });

  if (btnApplyPage) {
    btnApplyPage.addEventListener('click', () => {
      if (!analyzedText && !inputText.value.trim()) { showToast('لا يوجد نص للتطبيق'); return; }
      if (isStale) { showToast('⚠ أعد التحليل أولاً — النص تغيّر'); return; }
      const finalText = currentSuggestions.length > 0
        ? applyAllPatches(analyzedText, currentSuggestions)
        : (analyzedText || inputText.value.trim());
      writeBackToPage(finalText, 'auto', 'correct', sourceSelectionText);
    });
  }

  if (btnCopyText) {
    btnCopyText.addEventListener('click', () => {
      const text = inputText.value || '';
      navigator.clipboard.writeText(text)
        .then(() => showToast('✓ تم نسخ النص'))
        .catch(() => showToast('تعذّر النسخ'));
    });
  }

  // ══════════════════════════════════════════════════════════
  // Summary mode toggle (paragraph / bullets)
  // ══════════════════════════════════════════════════════════
  document.querySelectorAll('.sp-mode-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      summaryMode = btn.dataset.mode;
      document.querySelectorAll('.sp-mode-btn').forEach((b) => {
        b.classList.toggle('active', b.dataset.mode === summaryMode);
      });
    });
  });

  // ══════════════════════════════════════════════════════════
  // Summarize
  // ══════════════════════════════════════════════════════════
  btnSummarize.addEventListener('click', async () => {
    const text = summaryInputText.value.trim();
    if (!text) { showToast('أدخل نصاً للتلخيص'); return; }
    if (text.length < CONFIG.MIN_SUMMARIZE_LENGTH) { showToast('النص قصير جداً للتلخيص'); return; }

    const lengthValue = parseInt(document.querySelector('input[name="summary-length"]:checked')?.value || '2', 10);
    setLoading(true, 'جارٍ التلخيص...');

    try {
      const data = await bayanSummarize(text, lengthValue);
      if (data.status === 'success' && data.summary) {
        summaryResultSection.classList.remove('is-hidden');

        const summaryContent = data.summary;

        if (summaryMode === 'bullets') {
          const sentences = summaryContent.split(/[.،؛]\s*/).filter(s => s.trim().length > 2);
          const ul = document.createElement('ul');
          ul.style.cssText = 'list-style: disc; padding-right: 1.5rem; direction: rtl; text-align: right;';
          sentences.forEach(s => {
            const li = document.createElement('li');
            li.textContent = s.trim();
            li.style.marginBottom = '8px';
            ul.appendChild(li);
          });
          summaryText.textContent = '';
          summaryText.appendChild(ul);
        } else {
          summaryText.textContent = summaryContent;
        }

        const origWords = text.trim().split(/\s+/).length;
        const sumWords = summaryContent.trim().split(/\s+/).length;
        const compression = origWords > 0 ? Math.round((1 - sumWords / origWords) * 100) : 0;

        if (summaryStats) {
          summaryStats.classList.remove('is-hidden');
          if (summaryWordCount) summaryWordCount.textContent = sumWords.toLocaleString('ar-EG');
          if (summaryCompression) summaryCompression.textContent = compression.toLocaleString('ar-EG') + '٪';
        }

        showToast('✓ تم التلخيص');
      } else {
        showToast('تعذّر التلخيص — حاول مرة أخرى');
      }
    } catch (error) {
      console.error('[Bayan SP] Summarization error:', error);
      showToast('خطأ في الاتصال — تحقق من الإنترنت');
    } finally {
      setLoading(false);
    }
  });

  btnCopySummary.addEventListener('click', () => {
    const text = summaryText.innerText || summaryText.textContent || '';
    navigator.clipboard.writeText(text)
      .then(() => showToast('✓ تم نسخ الملخص'))
      .catch(() => showToast('تعذّر النسخ'));
  });

  const btnApplySummary = document.getElementById('btn-apply-summary');
  if (btnApplySummary) {
    btnApplySummary.addEventListener('click', () => {
      const text = summaryText.innerText || summaryText.textContent || '';
      if (!text) { showToast('لا يوجد ملخص للتطبيق'); return; }
      writeBackToPage(text, 'auto', 'summarize', sourceSelectionText);
    });
  }

  // ══════════════════════════════════════════════════════════
  // Summary: File import (.txt / .docx)
  // ══════════════════════════════════════════════════════════
  const summaryImportInput = document.getElementById('summary-import-input');
  if (summaryImportInput) {
    summaryImportInput.addEventListener('change', (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;

      if (file.name.endsWith('.txt')) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          summaryInputText.value = ev.target.result;
          const words = summaryInputText.value.trim() ? summaryInputText.value.trim().split(/\s+/).length : 0;
          if (summaryWordCountInput) summaryWordCountInput.textContent = words.toLocaleString('ar-EG');
          showToast('✓ تم استيراد الملف');
          saveState();
        };
        reader.readAsText(file, 'UTF-8');
      } else if (file.name.endsWith('.docx')) {
        if (typeof mammoth !== 'undefined') {
          const reader = new FileReader();
          reader.onload = (ev) => {
            mammoth.extractRawText({ arrayBuffer: ev.target.result })
              .then((result) => {
                summaryInputText.value = result.value;
                const words = result.value.trim() ? result.value.trim().split(/\s+/).length : 0;
                if (summaryWordCountInput) summaryWordCountInput.textContent = words.toLocaleString('ar-EG');
                showToast('✓ تم استيراد الملف');
                saveState();
              })
              .catch(() => showToast('خطأ في قراءة الملف'));
          };
          reader.readAsArrayBuffer(file);
        } else {
          showToast('صيغة .docx غير مدعومة — استخدم .txt');
        }
      }
      e.target.value = '';
    });
  }

  // ══════════════════════════════════════════════════════════
  // Summary: Export dropdown (.txt / .docx / .pdf)
  // ══════════════════════════════════════════════════════════
  const btnExportSummary = document.getElementById('btn-export-summary');
  const summaryExportMenu = document.getElementById('summary-export-menu');

  if (btnExportSummary && summaryExportMenu) {
    btnExportSummary.addEventListener('click', (e) => {
      e.stopPropagation();
      summaryExportMenu.classList.toggle('is-hidden');
    });

    document.addEventListener('click', () => {
      summaryExportMenu.classList.add('is-hidden');
    });

    summaryExportMenu.addEventListener('click', (e) => {
      e.stopPropagation();
    });

    summaryExportMenu.querySelectorAll('.sp-export-item').forEach((item) => {
      item.addEventListener('click', () => {
        const format = item.dataset.format;
        const text = (summaryText.innerText || summaryText.textContent || '').trim();
        if (!text) { showToast('لا يوجد ملخص للتصدير'); return; }

        summaryExportMenu.classList.add('is-hidden');
        exportSummary(format, text);
      });
    });
  }

  function exportSummary(format, text) {
    if (format === 'txt') {
      downloadFile(text, 'ملخص-بيان.txt', 'text/plain;charset=utf-8');
      showToast('✓ تم تصدير الملخص');
    } else if (format === 'docx') {
      if (typeof docx === 'undefined') { showToast('مكتبة Word غير محمّلة'); return; }
      try {
        const paragraphs = text.split(/\n+/).filter(p => p.trim());
        const children = paragraphs.map(block =>
          new docx.Paragraph({
            bidirectional: true,
            alignment: docx.AlignmentType.RIGHT,
            children: [new docx.TextRun({ text: block, rightToLeft: true, font: 'Arial' })]
          })
        );
        const doc = new docx.Document({ sections: [{ properties: { rightToLeft: true }, children }] });
        docx.Packer.toBlob(doc).then((blob) => {
          downloadBlob(blob, 'ملخص-بيان.docx');
          showToast('✓ تم تصدير الملخص كـ Word');
        }).catch(() => showToast('تعذر تصدير ملف Word'));
      } catch { showToast('تعذر تصدير ملف Word'); }
    } else if (format === 'pdf') {
      if (typeof html2pdf === 'undefined') { showToast('مكتبة PDF غير محمّلة'); return; }
      showToast('جاري تصدير PDF...');
      const html = '<div dir="rtl" style="font-family:Arial,sans-serif;font-size:16px;line-height:2;text-align:right;padding:20px;">' +
        text.split(/\n+/).map(p => '<p>' + p + '</p>').join('') + '</div>';
      html2pdf().set({
        margin: [15, 15, 15, 15],
        filename: 'ملخص-بيان.pdf',
        image: { type: 'jpeg', quality: 0.95 },
        html2canvas: { scale: 1.5, useCORS: true, backgroundColor: '#ffffff' },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
      }).from(html, 'string').save()
        .then(() => showToast('✓ تم تصدير الملخص كـ PDF'))
        .catch(() => showToast('تعذر تصدير PDF'));
    }
  }

  function downloadFile(text, filename, mime) {
    const blob = new Blob([text], { type: mime });
    downloadBlob(blob, filename);
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // ══════════════════════════════════════════════════════════
  // Dialect → MSA conversion
  // ══════════════════════════════════════════════════════════
  const dialectInput = document.getElementById('dialect-input-text');
  const dialectCharCount = document.getElementById('dialect-char-count');
  const btnDialect = document.getElementById('btn-dialect');
  const dialectResultSection = document.getElementById('dialect-result-section');
  const dialectText = document.getElementById('dialect-text');
  const btnCopyDialect = document.getElementById('btn-copy-dialect');

  if (dialectInput) {
    dialectInput.addEventListener('input', () => {
      const chars = dialectInput.value.length;
      if (dialectCharCount) dialectCharCount.textContent = chars.toLocaleString('ar-EG');
      saveState();
    });

    btnDialect.addEventListener('click', async () => {
      const text = dialectInput.value.trim();
      if (!text) { showToast('أدخل نصاً للتحويل'); return; }

      setLoading(true, 'جارٍ التحويل...');
      try {
        const data = await bayanDialect(text);
        if (data.status === 'success' && data.converted_text) {
          dialectResultSection.classList.remove('is-hidden');
          dialectText.textContent = data.converted_text;
          showToast('✓ تم التحويل');
        } else {
          showToast(data.error || 'تعذّر التحويل — حاول مرة أخرى');
        }
      } catch (error) {
        console.error('[Bayan SP] Dialect error:', error);
        showToast('خطأ في الاتصال — تحقق من الإنترنت');
      } finally {
        setLoading(false);
      }
    });

    btnCopyDialect.addEventListener('click', () => {
      navigator.clipboard.writeText(dialectText.textContent || '')
        .then(() => showToast('✓ تم نسخ النص'))
        .catch(() => showToast('تعذّر النسخ'));
    });

    const btnApplyDialect = document.getElementById('btn-apply-dialect');
    if (btnApplyDialect) {
      btnApplyDialect.addEventListener('click', () => {
        const text = dialectText.textContent || '';
        if (!text) { showToast('لا يوجد نص للتطبيق'); return; }
        writeBackToPage(text, 'auto', 'dialect', sourceSelectionText);
      });
    }
  }

  // ══════════════════════════════════════════════════════════
  // Quran verification + translation (matching popup)
  // ══════════════════════════════════════════════════════════
  const quranInput = document.getElementById('quran-input-text');
  const quranCharCount = document.getElementById('quran-char-count');
  const btnQuran = document.getElementById('btn-quran');
  const quranResultSection = document.getElementById('quran-result-section');
  const quranUthmani = document.getElementById('quran-uthmani');
  const quranReference = document.getElementById('quran-reference');
  const btnCopyQuran = document.getElementById('btn-copy-quran');
  const quranLangSelect = document.getElementById('quran-lang-select');
  const quranTransSection = document.getElementById('quran-translation-section');
  const quranTransText = document.getElementById('quran-trans-text');
  const quranTransRef = document.getElementById('quran-trans-ref');

  let _quranQuery = '';
  let _quranVerse = '';
  let _quranRef = '';
  let _quranTransText = '';
  let _quranTransRef = '';

  if (quranInput) {
    quranInput.addEventListener('input', () => { updateCounts(quranInput, quranCharCount, null); saveState(); });

    btnQuran.addEventListener('click', async () => {
      const text = quranInput.value.trim();
      if (!text) { showToast('أدخل آية للتدقيق'); return; }

      _quranQuery = text;
      setLoading(true, 'جارٍ التدقيق...');
      quranTransSection.classList.add('is-hidden');
      quranLangSelect.value = '';

      try {
        const data = await bayanQuran(text);
        quranResultSection.classList.remove('is-hidden');

        if (data.error) {
          quranUthmani.textContent = data.error;
          quranReference.textContent = '';
          return;
        }

        const seg = data.matched_segment || '';
        const refMatch = seg.match(/【([^】]+)】/);
        const verseText = seg.replace(/\s*【[^】]+】\s*$/, '').replace(/^\(/, '').replace(/\)$/, '');
        const reference = refMatch ? refMatch[1] : '';

        _quranVerse = verseText;
        _quranRef = reference;
        quranUthmani.textContent = verseText;
        quranReference.textContent = reference ? `[${reference}]` : '';
        showToast('✓ تم التدقيق');
      } catch (error) {
        console.error('[Bayan SP] Quran error:', error);
        quranResultSection.classList.remove('is-hidden');
        quranUthmani.textContent = 'خطأ في الاتصال — تحقق من الإنترنت';
        quranReference.textContent = '';
      } finally {
        setLoading(false);
      }
    });

    quranLangSelect.addEventListener('change', async () => {
      const lang = quranLangSelect.value;
      if (!lang || !_quranQuery) return;

      quranTransSection.classList.remove('is-hidden');
      quranTransText.textContent = '⏳ جاري الترجمة...';
      if (quranTransRef) quranTransRef.style.display = 'none';

      try {
        const data = await bayanQuran(_quranQuery, lang);

        if (data.error) {
          quranTransText.textContent = data.error;
          return;
        }

        const seg = data.matched_segment || '';
        const refMatch = seg.match(/【([^】]+)】/);
        const transText = seg.replace(/\s*【[^】]+】\s*$/, '').replace(/^\(/, '').replace(/\)$/, '');
        const transRef = refMatch ? refMatch[1] : '';

        _quranTransText = transText;
        _quranTransRef = transRef;

        quranTransText.textContent = transText;
        if (quranTransRef && transRef) {
          quranTransRef.textContent = `[${transRef}]`;
          quranTransRef.style.display = '';
        }
        const transActions = document.getElementById('quran-trans-actions');
        if (transActions) transActions.style.display = 'flex';
      } catch (error) {
        console.error('[Bayan SP] Quran translation error:', error);
        quranTransText.textContent = 'حدث خطأ في الترجمة';
      }
    });

    btnCopyQuran.addEventListener('click', () => {
      const text = (_quranVerse || '') + (_quranRef ? ` [${_quranRef}]` : '');
      navigator.clipboard.writeText(text)
        .then(() => showToast('✓ تم النسخ'))
        .catch(() => showToast('تعذّر النسخ'));
    });

    const btnApplyQuran = document.getElementById('btn-apply-quran');
    if (btnApplyQuran) {
      btnApplyQuran.addEventListener('click', () => {
        const verse = _quranVerse || '';
        if (!verse) { showToast('لا يوجد نص قرآني للتطبيق'); return; }
        const textWithRef = verse + (_quranRef ? ` [${_quranRef}]` : '');
        writeBackToPage(textWithRef, 'auto', 'quran', sourceSelectionText);
      });
    }

    const btnCopyQuranTrans = document.getElementById('btn-copy-quran-trans');
    if (btnCopyQuranTrans) {
      btnCopyQuranTrans.addEventListener('click', () => {
        const text = (_quranTransText || '') + (_quranTransRef ? ` [${_quranTransRef}]` : '');
        navigator.clipboard.writeText(text)
          .then(() => showToast('✓ تم نسخ الترجمة'))
          .catch(() => showToast('تعذّر النسخ'));
      });
    }

    const btnApplyQuranTrans = document.getElementById('btn-apply-quran-trans');
    if (btnApplyQuranTrans) {
      btnApplyQuranTrans.addEventListener('click', () => {
        const text = _quranTransText || '';
        if (!text) { showToast('لا يوجد ترجمة للتطبيق'); return; }
        const textWithRef = text + (_quranTransRef ? ` [${_quranTransRef}]` : '');
        writeBackToPage(textWithRef, 'auto', 'quran', sourceSelectionText);
      });
    }
  }

  // ══════════════════════════════════════════════════════════
  // Status check
  // ══════════════════════════════════════════════════════════
  (async function checkStatus() {
    const statusDot = document.querySelector('.sp-status-dot');
    const statusText = document.getElementById('status-text');
    try {
      await bayanHealthCheck();
      if (statusDot) statusDot.classList.add('online');
      if (statusText) statusText.textContent = 'متصل';
    } catch {
      if (statusDot) statusDot.classList.add('offline');
      if (statusText) statusText.textContent = 'غير متصل';
    }
  })();

  // ══════════════════════════════════════════════════════════
  // Context menu pickup
  // ══════════════════════════════════════════════════════════
  function runContextAction(action, text) {
    sourceSelectionText = text;
    if (action === TAB.CORRECT) {
      inputText.value = text;
      updateCounts(inputText, charCount, wordCount);
      document.querySelector(`[data-tab="${TAB.CORRECT}"]`)?.click();
      setTimeout(() => runAnalysis(text), 100);
    } else if (action === TAB.SUMMARIZE) {
      summaryInputText.value = text;
      const words = text.trim() ? text.trim().split(/\s+/).length : 0;
      if (summaryWordCountInput) summaryWordCountInput.textContent = words.toLocaleString('ar-EG');
      document.querySelector(`[data-tab="${TAB.SUMMARIZE}"]`)?.click();
      setTimeout(() => btnSummarize.click(), 100);
    } else if (action === TAB.DIALECT && dialectInput && btnDialect) {
      dialectInput.value = text;
      const chars = text.length;
      if (dialectCharCount) dialectCharCount.textContent = chars.toLocaleString('ar-EG');
      document.querySelector(`[data-tab="${TAB.DIALECT}"]`)?.click();
      setTimeout(() => btnDialect.click(), 120);
    } else if (action === TAB.QURAN && quranInput && btnQuran) {
      quranInput.value = text;
      updateCounts(quranInput, quranCharCount, null);
      document.querySelector(`[data-tab="${TAB.QURAN}"]`)?.click();
      setTimeout(() => btnQuran.click(), 120);
    }
  }

  async function tryPickupContext(retryCount = 0) {
    if (typeof chrome === 'undefined' || !chrome.storage) return;
    if (contextConsumed) return;

    const storage = getStorage();
    if (!storage) return;

    try {
      const data = await storage.get(['contextAction', 'contextText', 'contextTimestamp']);

      if ((!data.contextAction || !data.contextText) && retryCount < 2) {
        setTimeout(() => tryPickupContext(retryCount + 1), 300);
        return;
      }

      if (!data.contextAction || !data.contextText) {
        await restoreState();
        return;
      }

      const age = Date.now() - (data.contextTimestamp || 0);
      if (age > 15000) {
        chrome.runtime.sendMessage({ type: 'CLEAR_CONTEXT' });
        await restoreState();
        return;
      }

      contextConsumed = true;
      console.log(`[Bayan SP] Context action: ${data.contextAction}, text: ${data.contextText.length} chars`);
      runContextAction(data.contextAction, data.contextText);
      chrome.runtime.sendMessage({ type: 'CLEAR_CONTEXT' });

    } catch (err) {
      console.warn('[Bayan SP] Context action check failed:', err);
      await restoreState();
    }
  }

  tryPickupContext(0);

  // ══════════════════════════════════════════════════════════
  // Listen for NEW context actions while panel is already open
  // ══════════════════════════════════════════════════════════
  if (chrome.storage?.session?.onChanged || chrome.storage?.onChanged) {
    const storageApi = chrome.storage;
    storageApi.onChanged.addListener((changes, area) => {
      if (area !== 'session' && area !== 'local') return;
      if (!changes.contextAction || !changes.contextText) return;

      const action = changes.contextAction.newValue;
      const text = changes.contextText.newValue;
      if (!action || !text) return;

      console.log(`[Bayan SP] Storage changed — new context: ${action}, ${text.length} chars`);
      runContextAction(action, text);
      chrome.runtime.sendMessage({ type: 'CLEAR_CONTEXT' });
    });
  }
});


// ── Theme Toggle Logic ──
(function initBayanThemeToggle() {
  const toggleBtn = document.getElementById('ext-theme-toggle');

  chrome.storage.local.get(['theme'], (result) => {
    const currentTheme = result.theme || 'dark';
    document.documentElement.setAttribute('data-theme', currentTheme);
  });

  chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'local' && changes.theme) {
      document.documentElement.setAttribute('data-theme', changes.theme.newValue);
    }
  });

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      let theme = document.documentElement.getAttribute('data-theme') || 'dark';
      let targetTheme = theme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', targetTheme);
      chrome.storage.local.set({ theme: targetTheme });
    });
  }
})();
