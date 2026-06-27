/**
 * Bayan Chrome Extension — Side Panel Logic
 *
 * Phase 5: Persistent workspace panel
 *
 * Reuses:
 *   - bayanAnalyze(), bayanSummarize(), bayanHealthCheck() from bayan-api.js
 *   - renderHighlightedText(), escapeHtml() from bayan-renderer.js
 *   - buildSuggestionCardHTML(), calculateWritingScore(), getScoreHint() from bayan-ui.js
 *   - applyAndRebase(), applyAllPatches(), sortSuggestions(), countByType(), removeSuggestion() from bayan-patches.js
 *
 * Key differences from popup.js:
 *   - Persistent: panel stays open across page navigations
 *   - Auto-analysis: text injected from context menu auto-analyzes
 *   - Debounced live updates: re-analyzes on user edits (500ms debounce)
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
  const btnCopyResult = document.getElementById('btn-copy-result');
  const scoreSection = document.getElementById('score-section');
  const resultSection = document.getElementById('result-section');
  const resultText = document.getElementById('result-text');
  const suggestionsSection = document.getElementById('suggestions-section');
  const suggestionsList = document.getElementById('suggestions-list');
  const timingSection = document.getElementById('timing-section');
  const timingText = document.getElementById('timing-text');
  const loadingOverlay = document.getElementById('loading-overlay');
  const loadingTextEl = document.getElementById('loading-text');

  // Summary tab
  const summaryInputText = document.getElementById('summary-input-text');
  const summaryCharCount = document.getElementById('summary-char-count');
  const btnSummarize = document.getElementById('btn-summarize');
  const summaryResultSection = document.getElementById('summary-result-section');
  const summaryText = document.getElementById('summary-text');
  const summaryMeta = document.getElementById('summary-meta');
  const btnCopySummary = document.getElementById('btn-copy-summary');

  // ══════════════════════════════════════════════════════════
  // State
  // ══════════════════════════════════════════════════════════
  let currentSuggestions = [];
  let analyzedText = '';
  let isStale = false;
  let isAnalyzing = false;
  let contextConsumed = false;
  let debounceTimer = null;
  // The exact text the user had selected on the page when this action started
  // (from the right-click context menu). Used as a precise find/replace anchor
  // so write-back replaces ONLY that selection, never the whole field.
  let sourceSelectionText = '';

  const DEBOUNCE_MS = 500;

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
    });
  });

  // ══════════════════════════════════════════════════════════
  // Character & word counter (shared: bayan-core.js)
  // ══════════════════════════════════════════════════════════

  inputText.addEventListener('input', () => {
    updateCounts(inputText, charCount, wordCount);

    // Staleness detection
    if (currentSuggestions.length > 0 && inputText.value !== analyzedText) {
      markStale();
    }

    // Debounced live re-analysis
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const text = inputText.value.trim();
      if (text.length >= CONFIG.MIN_ANALYZE_LENGTH && !isAnalyzing) {
        runAnalysis(text);
      }
    }, DEBOUNCE_MS);
  });

  summaryInputText.addEventListener('input', () => {
    updateCounts(summaryInputText, summaryCharCount, null);
  });

  // ══════════════════════════════════════════════════════════
  // Staleness management
  // ══════════════════════════════════════════════════════════
  function markStale() {
    if (isStale) return;
    isStale = true;
    if (resultSection) resultSection.classList.add('sp-stale');
    if (suggestionsSection) suggestionsSection.classList.add('sp-stale');
  }

  function clearStale() {
    isStale = false;
    if (resultSection) resultSection.classList.remove('sp-stale');
    if (suggestionsSection) suggestionsSection.classList.remove('sp-stale');
  }

  // ══════════════════════════════════════════════════════════
  // Loading (Toast shared via bayan-core.js)
  // ══════════════════════════════════════════════════════════
  function setLoading(show, text = 'جارٍ التحليل...') {
    loadingOverlay.classList.toggle('is-hidden', !show);
    loadingTextEl.textContent = text;
  }

  // ══════════════════════════════════════════════════════════
  // Write-back to the page field (panel → background → content script)
  // The side panel is a separate document and cannot touch page DOM
  // directly; it relays through background.js. `source` lets the content
  // script decide whether to re-analyze (correct) or suppress (Change 3).
  //
  // `find` (optional) is the exact original selected text. When present, the
  // content script replaces ONLY that occurrence in the field — the most
  // reliable way to scope the replacement to the user's selection.
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

  // Score ring — shared via bayan-core.js (updateScore)

  // ══════════════════════════════════════════════════════════
  // Render suggestions list
  // ══════════════════════════════════════════════════════════
  function renderSuggestions(suggestions) {
    currentSuggestions = suggestions;

    if (!suggestions || suggestions.length === 0) {
      suggestionsSection.classList.add('is-hidden');
      btnApplyAll.classList.add('is-hidden');
      return;
    }

    suggestionsSection.classList.remove('is-hidden');
    suggestionsList.innerHTML = suggestions.map((s, i) => buildSuggestionCardHTML(s, i)).join('');

    // Bind alt-chip click events
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
          if (suggestion.type === 'spelling' && typeof BayanAuth !== 'undefined') {
            BayanAuth.addDismissedWord(suggestion.original);
          }
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
        resultText.innerHTML = renderHighlightedText(analyzedText, currentSuggestions);
        saveState();
        showToast('✓ تم التصحيح');
      });
    });

    btnApplyAll.classList.toggle('is-hidden', suggestions.length < 2);
  }

  // ══════════════════════════════════════════════════════════
  // Core analysis function
  // ══════════════════════════════════════════════════════════
  async function runAnalysis(text) {
    if (!text || text.length < CONFIG.MIN_ANALYZE_LENGTH) {
      showToast('النص قصير جداً (الحد الأدنى ١٥ حرفاً)');
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
        let suggestions = sortSuggestions(data.suggestions || []);

        if (typeof BayanAuth !== 'undefined') {
          const dismissed = await BayanAuth.getDismissedWords();
          if (dismissed.length > 0) {
            suggestions = suggestions.filter(s => !(s.type === 'spelling' && dismissed.includes(s.original)));
          }
        }

        currentSuggestions = suggestions;
        analyzedText = data.original;

        inputText.value = analyzedText;
        updateCounts(inputText, charCount, wordCount);

        resultSection.classList.remove('is-hidden');
        resultText.innerHTML = renderHighlightedText(analyzedText, suggestions);

        const counts = countByType(suggestions);
        updateScore(counts.spelling, counts.grammar, counts.punctuation);
        renderSuggestions(suggestions);

        if (data.timing_ms) {
          timingSection.classList.remove('is-hidden');
          timingText.textContent = `التحليل: ${data.timing_ms.total_ms || 0}ms`;
        }

        saveState();

        if (suggestions.length === 0) {
          showToast('نصك ممتاز! لم نجد أي أخطاء ✨');
        }
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
    storage.set({
      spLastText: analyzedText,
      spLastSuggestions: currentSuggestions,
      spLastInput: inputText.value,
    }).catch(() => {});
  }

  async function restoreState() {
    const storage = getStorage();
    if (!storage) return false;

    try {
      const data = await storage.get(['spLastText', 'spLastSuggestions', 'spLastInput']);
      if (!data.spLastText || !data.spLastSuggestions) return false;

      analyzedText = data.spLastText;
      currentSuggestions = data.spLastSuggestions;
      inputText.value = data.spLastInput || analyzedText;
      updateCounts(inputText, charCount, wordCount);

      resultSection.classList.remove('is-hidden');
      resultText.innerHTML = renderHighlightedText(analyzedText, currentSuggestions);

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
    resultSection.classList.add('is-hidden');
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
    resultText.innerHTML = escapeHtml(analyzedText);
    updateScore(0, 0, 0);
    renderSuggestions([]);
    saveState();
    writeBackToPage(analyzedText, 'auto', 'correct', sourceSelectionText);
    showToast('✓ تم تطبيق جميع التصحيحات');
  });

  // Explicit "apply corrected text to the page field" button (Bug 1).
  // Writes the current corrected text — with any still-pending suggestions
  // applied — back into the source field, honouring selection vs whole-field.
  if (btnApplyPage) {
    btnApplyPage.addEventListener('click', () => {
      if (!analyzedText) { showToast('لا يوجد نص للتطبيق'); return; }
      if (isStale) { showToast('⚠ أعد التحليل أولاً — النص تغيّر'); return; }
      const finalText = currentSuggestions.length > 0
        ? applyAllPatches(analyzedText, currentSuggestions)
        : analyzedText;
      writeBackToPage(finalText, 'auto', 'correct', sourceSelectionText);
    });
  }

  btnCopyResult.addEventListener('click', () => {
    const text = resultText.textContent || '';
    navigator.clipboard.writeText(text)
      .then(() => showToast('✓ تم نسخ النص'))
      .catch(() => showToast('تعذّر النسخ'));
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
        summaryText.textContent = data.summary;
        summaryMeta.textContent = `النص الأصلي: ${(data.original_length || 0).toLocaleString('ar-EG')} حرف → الملخص: ${(data.summary_length || 0).toLocaleString('ar-EG')} حرف`;
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
    const text = summaryText.textContent || '';
    navigator.clipboard.writeText(text)
      .then(() => showToast('✓ تم نسخ الملخص'))
      .catch(() => showToast('تعذّر النسخ'));
  });

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
    dialectInput.addEventListener('input', () => updateCounts(dialectInput, dialectCharCount, null));

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
  }

  // ══════════════════════════════════════════════════════════
  // Quran verification
  // ══════════════════════════════════════════════════════════
  const quranInput = document.getElementById('quran-input-text');
  const quranCharCount = document.getElementById('quran-char-count');
  const btnQuran = document.getElementById('btn-quran');
  const quranResultSection = document.getElementById('quran-result-section');
  const quranText = document.getElementById('quran-text');
  const quranMeta = document.getElementById('quran-meta');
  const btnCopyQuran = document.getElementById('btn-copy-quran');
  // Translation sub-UI
  const quranTranslateSection = document.getElementById('quran-translate-section');
  const quranLangSelect = document.getElementById('quran-lang-select');
  const quranTranslationResult = document.getElementById('quran-translation-result');
  const quranTranslationText = document.getElementById('quran-translation-text');
  const quranTranslationRef = document.getElementById('quran-translation-ref');
  const btnCopyQuranTranslation = document.getElementById('btn-copy-quran-translation');
  const btnApplyQuranTranslation = document.getElementById('btn-apply-quran-translation');
  let lastQuranQuery = '';

  // Parse the API's "(verse text) 【surah:ayah】" segment into {text, ref}.
  function parseQuranSegment(seg) {
    seg = seg || '';
    const refMatch = seg.match(/【([^】]+)】/);
    const text = seg.replace(/\s*【[^】]+】\s*$/, '').replace(/^\(/, '').replace(/\)$/, '');
    return { text, ref: refMatch ? refMatch[1] : '' };
  }

  if (quranInput) {
    quranInput.addEventListener('input', () => updateCounts(quranInput, quranCharCount, null));

    btnQuran.addEventListener('click', async () => {
      const text = quranInput.value.trim();
      if (!text) { showToast('أدخل آية للتدقيق'); return; }

      setLoading(true, 'جارٍ التدقيق...');
      try {
        const data = await bayanQuran(text);
        quranResultSection.classList.remove('is-hidden');
        // Reset translation UI for the new query.
        if (quranTranslateSection) quranTranslateSection.classList.add('is-hidden');
        if (quranTranslationResult) quranTranslationResult.classList.add('is-hidden');
        if (quranLangSelect) quranLangSelect.value = '';
        if (data.error) {
          quranText.textContent = data.error;
          quranMeta.textContent = '';
        } else {
          quranText.textContent = data.full_verse || data.matched_segment || JSON.stringify(data);
          quranMeta.textContent = data.matched_segment && data.full_verse
            ? `المقطع المطابق: ${data.matched_segment}`
            : '';
          // Enable translation now that we have a verified verse.
          lastQuranQuery = text;
          if (quranTranslateSection) quranTranslateSection.classList.remove('is-hidden');
          showToast('✓ تم التدقيق');
        }
      } catch (error) {
        console.error('[Bayan SP] Quran error:', error);
        showToast('خطأ في الاتصال — تحقق من الإنترنت');
      } finally {
        setLoading(false);
      }
    });

    // Translate the verified verse into the chosen language.
    if (quranLangSelect) {
      quranLangSelect.addEventListener('change', async () => {
        const lang = quranLangSelect.value;
        if (!lang || !lastQuranQuery) return;

        setLoading(true, 'جارٍ الترجمة...');
        try {
          const data = await bayanQuran(lastQuranQuery, lang);
          quranTranslationResult.classList.remove('is-hidden');
          if (data.error) {
            quranTranslationText.textContent = data.error;
            quranTranslationRef.textContent = '';
          } else {
            const parsed = parseQuranSegment(data.matched_segment || data.full_verse || '');
            quranTranslationText.textContent = parsed.text || data.full_verse || '';
            quranTranslationRef.textContent = parsed.ref ? `[${parsed.ref}]` : '';
            showToast('✓ تمت الترجمة');
          }
        } catch (error) {
          console.error('[Bayan SP] Quran translation error:', error);
          showToast('خطأ في الاتصال — تحقق من الإنترنت');
        } finally {
          setLoading(false);
        }
      });
    }

    if (btnCopyQuranTranslation) {
      btnCopyQuranTranslation.addEventListener('click', () => {
        navigator.clipboard.writeText(quranTranslationText.textContent || '')
          .then(() => showToast('✓ تم نسخ الترجمة'))
          .catch(() => showToast('تعذّر النسخ'));
      });
    }

    // Apply the translated verse straight into the page field (Req 2).
    // Routed as 'quran' so the content script suppresses correction re-analysis.
    if (btnApplyQuranTranslation) {
      btnApplyQuranTranslation.addEventListener('click', () => {
        const text = (quranTranslationText.textContent || '').trim();
        if (!text) { showToast('لا توجد ترجمة للتطبيق'); return; }
        writeBackToPage(text, 'auto', 'quran', sourceSelectionText);
      });
    }

    btnCopyQuran.addEventListener('click', () => {
      navigator.clipboard.writeText(quranText.textContent || '')
        .then(() => showToast('✓ تم النسخ'))
        .catch(() => showToast('تعذّر النسخ'));
    });
  }

  // ══════════════════════════════════════════════════════════
  // Autocomplete suggestions
  // ══════════════════════════════════════════════════════════
  const acInput = document.getElementById('autocomplete-input-text');
  const acCharCount = document.getElementById('autocomplete-char-count');
  const btnAutocomplete = document.getElementById('btn-autocomplete');
  const acResultSection = document.getElementById('autocomplete-result-section');
  const acList = document.getElementById('autocomplete-list');

  if (acInput) {
    acInput.addEventListener('input', () => updateCounts(acInput, acCharCount, null));

    btnAutocomplete.addEventListener('click', async () => {
      const text = acInput.value;
      if (!text.trim() || text.trim().length < 3) { showToast('اكتب ٣ أحرف على الأقل'); return; }

      setLoading(true, 'جارٍ الاقتراح...');
      try {
        const data = await bayanAutocomplete(text, 5);
        const suggestions = data.suggestions || [];
        acResultSection.classList.remove('is-hidden');

        if (suggestions.length === 0) {
          acList.innerHTML = '<div class="sp-ac-empty">لا توجد اقتراحات</div>';
          return;
        }

        acList.innerHTML = suggestions
          .map((s) => `<button class="bayan-alt-chip bayan-alt-chip--main sp-ac-chip" type="button">${escapeHtml(s)}</button>`)
          .join('');

        acList.querySelectorAll('.sp-ac-chip').forEach((chip) => {
          chip.addEventListener('click', () => {
            const needsSpace = acInput.value.length > 0 && !/\s$/.test(acInput.value);
            acInput.value += (needsSpace ? ' ' : '') + chip.textContent;
            updateCounts(acInput, acCharCount, null);
            acInput.focus();
            showToast('✓ تمت الإضافة');
          });
        });
      } catch (error) {
        console.error('[Bayan SP] Autocomplete error:', error);
        showToast('خطأ في الاتصال — تحقق من الإنترنت');
      } finally {
        setLoading(false);
      }
    });
  }

  // ══════════════════════════════════════════════════════════
  // Phase 5: Download corrected text / summary as .txt
  // downloadTxt shared via bayan-core.js
  // ══════════════════════════════════════════════════════════

  const SP_DOWNLOAD_ICON = '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1M12 4v12m0 0l-4-4m4 4l4-4"/></svg>';

  function addDownloadButton(anchorBtn, getText, filename) {
    if (!anchorBtn || !anchorBtn.parentElement) return;
    const btn = document.createElement('button');
    btn.className = 'sp-btn-icon';
    btn.type = 'button';
    btn.title = 'تنزيل كملف نصي';
    btn.innerHTML = SP_DOWNLOAD_ICON;
    btn.addEventListener('click', () => downloadTxt((getText() || '').trim(), filename));
    anchorBtn.parentElement.appendChild(btn);
    const docxBtn = document.createElement('button');
    docxBtn.className = 'sp-btn-icon';
    docxBtn.type = 'button';
    docxBtn.title = 'تنزيل كـ Word';
    docxBtn.innerHTML = '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>';
    docxBtn.addEventListener('click', () => {
      if (typeof downloadDocx === 'function') {
        downloadDocx((getText() || '').trim(), filename.replace('.txt', '.docx'));
      }
    });
    anchorBtn.parentElement.appendChild(docxBtn);
  }

  addDownloadButton(btnCopyResult, () => resultText.textContent, 'bayan-corrected.txt');
  addDownloadButton(btnCopySummary, () => summaryText.textContent, 'bayan-summary.txt');

  // ══════════════════════════════════════════════════════════
  // "Apply to page" buttons for summarize / dialect / quran results.
  // These write the model output back into the source page field via
  // Change 1's relay, tagging the write with its `source` so the content
  // script suppresses correction re-analysis on it (Change 3).
  // Injected programmatically to avoid touching sidepanel.html.
  // ══════════════════════════════════════════════════════════
  const SP_APPLY_PAGE_ICON = '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>';

  function addApplyToPageButton(anchorBtn, getText, source) {
    if (!anchorBtn || !anchorBtn.parentElement) return;
    const btn = document.createElement('button');
    btn.className = 'sp-btn-icon';
    btn.type = 'button';
    btn.title = 'تطبيق في الصفحة';
    btn.innerHTML = SP_APPLY_PAGE_ICON;
    btn.addEventListener('click', () => {
      const text = (getText() || '').trim();
      if (!text) { showToast('لا يوجد نص للتطبيق'); return; }
      writeBackToPage(text, 'auto', source, sourceSelectionText);
    });
    anchorBtn.parentElement.appendChild(btn);
  }

  addApplyToPageButton(btnCopySummary, () => summaryText.textContent, 'summarize');
  if (btnCopyDialect) addApplyToPageButton(btnCopyDialect, () => dialectText.textContent, 'dialect');
  if (btnCopyQuran) addApplyToPageButton(btnCopyQuran, () => quranText.textContent, 'quran');

  // ══════════════════════════════════════════════════════════
  // Auth UI wiring (shared via bayan-core.js)
  // ══════════════════════════════════════════════════════════
  bayanInitAuth();

  // ══════════════════════════════════════════════════════════
  // Cloud Documents (Phase 3.4)
  // Uses BayanDocuments REST API (bayan-documents.js)
  // ══════════════════════════════════════════════════════════
  const spDocTitle = document.getElementById('sp-doc-title');
  const spDocSave = document.getElementById('sp-doc-save');
  const spDocNew = document.getElementById('sp-doc-new');
  const spDocRefresh = document.getElementById('sp-doc-refresh');
  const spDocList = document.getElementById('sp-doc-list');

  let currentDocId = null;
  let currentDocTitle = 'لا يوجد مستند مفتوح';

  function _escDocHtml(str) {
    return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function _updateDocBar() {
    if (spDocTitle) spDocTitle.textContent = currentDocTitle;
  }

  async function _renderDocList() {
    if (!spDocList) return;

    if (typeof BayanAuth === 'undefined' || !BayanAuth.isAuthenticated()) {
      spDocList.innerHTML = `
        <div class="sp-doc-signin">
          <p>سجّل دخولك لحفظ مستنداتك في السحابة</p>
          <button class="sp-doc-signin-btn" id="sp-doc-signin-btn" type="button">الدخول بـ Google</button>
        </div>`;
      const signinBtn = document.getElementById('sp-doc-signin-btn');
      if (signinBtn) {
        signinBtn.addEventListener('click', () => {
          const loginBtn = document.getElementById('btn-auth-login');
          if (loginBtn) loginBtn.click();
        });
      }
      return;
    }

    spDocList.innerHTML = '<div class="sp-doc-loading">جاري التحميل...</div>';

    const docs = await BayanDocuments.loadDocuments();
    if (!docs.length) {
      spDocList.innerHTML = `
        <div class="sp-doc-empty">
          <div class="sp-doc-empty-icon">📄</div>
          <div>لا توجد مستندات بعد</div>
          <div>أنشئ مستنداً جديداً للبدء</div>
        </div>`;
      return;
    }

    spDocList.innerHTML = docs.map(doc => {
      const date = new Date(doc.updated_at).toLocaleDateString('ar-EG', { month: 'short', day: 'numeric' });
      const isActive = doc.id === currentDocId;
      return `
        <div class="sp-doc-item${isActive ? ' sp-doc-active' : ''}" data-doc-id="${doc.id}">
          <button class="sp-doc-item-open" data-doc-id="${doc.id}" type="button">
            <span class="sp-doc-item-icon">📄</span>
            <span class="sp-doc-item-title">${_escDocHtml(doc.title)}</span>
            <span class="sp-doc-item-date">${date}</span>
          </button>
          <div class="sp-doc-item-actions">
            <button class="sp-doc-item-action sp-doc-rename" data-doc-id="${doc.id}" data-doc-title="${_escDocHtml(doc.title)}" title="إعادة تسمية" type="button">✎</button>
            <button class="sp-doc-item-action sp-doc-delete" data-doc-id="${doc.id}" data-doc-title="${_escDocHtml(doc.title)}" title="حذف" type="button">✕</button>
          </div>
        </div>`;
    }).join('');

    spDocList.querySelectorAll('.sp-doc-item-open').forEach(btn => {
      btn.addEventListener('click', () => _openDoc(btn.dataset.docId));
    });
    spDocList.querySelectorAll('.sp-doc-rename').forEach(btn => {
      btn.addEventListener('click', (e) => { e.stopPropagation(); _renameDoc(btn.dataset.docId, btn.dataset.docTitle); });
    });
    spDocList.querySelectorAll('.sp-doc-delete').forEach(btn => {
      btn.addEventListener('click', (e) => { e.stopPropagation(); _deleteDoc(btn.dataset.docId, btn.dataset.docTitle); });
    });
  }

  async function _openDoc(id) {
    setLoading(true, 'جاري تحميل المستند...');
    try {
      const doc = await BayanDocuments.loadDocument(id);
      if (!doc) { showToast('تعذّر تحميل المستند'); return; }

      currentDocId = doc.id;
      currentDocTitle = doc.title;
      _updateDocBar();

      inputText.value = doc.content || '';
      updateCounts(inputText, charCount, wordCount);
      analyzedText = '';
      currentSuggestions = [];
      clearStale();
      scoreSection.classList.add('is-hidden');
      resultSection.classList.add('is-hidden');
      suggestionsSection.classList.add('is-hidden');
      timingSection.classList.add('is-hidden');

      document.querySelector('[data-tab="correct"]')?.click();

      _renderDocList();
      showToast('✓ تم فتح المستند');
    } catch (e) {
      console.error('[Bayan SP] Open doc error:', e);
      showToast('خطأ في تحميل المستند');
    } finally {
      setLoading(false);
    }
  }

  async function _createDoc() {
    if (typeof BayanAuth === 'undefined' || !BayanAuth.isAuthenticated()) {
      showToast('سجّل دخولك أولاً'); return;
    }
    const title = prompt('اسم المستند الجديد:', 'مستند جديد');
    if (title === null) return;

    setLoading(true, 'جاري الإنشاء...');
    try {
      const doc = await BayanDocuments.createDocument(title.trim() || 'مستند جديد', inputText.value || '');
      if (!doc) { showToast('تعذّر إنشاء المستند'); return; }

      currentDocId = doc.id;
      currentDocTitle = doc.title;
      _updateDocBar();
      await _renderDocList();
      showToast('✓ تم إنشاء المستند');
    } catch (e) {
      console.error('[Bayan SP] Create doc error:', e);
      showToast('خطأ في إنشاء المستند');
    } finally {
      setLoading(false);
    }
  }

  async function _saveDoc() {
    if (!currentDocId) {
      _createDoc();
      return;
    }
    setLoading(true, 'جاري الحفظ...');
    try {
      const ok = await BayanDocuments.saveDocument(currentDocId, inputText.value || '');
      if (ok) {
        if (spDocSave) spDocSave.classList.remove('sp-doc-dirty');
        showToast('✓ تم الحفظ');
      } else {
        showToast('تعذّر الحفظ');
      }
    } catch (e) {
      console.error('[Bayan SP] Save doc error:', e);
      showToast('خطأ في الحفظ');
    } finally {
      setLoading(false);
    }
  }

  async function _renameDoc(id, currentTitle) {
    const newTitle = prompt('الاسم الجديد للمستند:', currentTitle);
    if (!newTitle || newTitle === currentTitle) return;

    const ok = await BayanDocuments.renameDocument(id, newTitle);
    if (ok) {
      if (id === currentDocId) { currentDocTitle = newTitle; _updateDocBar(); }
      await _renderDocList();
      showToast('✓ تم التسمية');
    } else {
      showToast('تعذّر إعادة التسمية');
    }
  }

  async function _deleteDoc(id, title) {
    if (!confirm('هل تريد حذف "' + title + '"؟')) return;

    const ok = await BayanDocuments.deleteDocument(id);
    if (ok) {
      if (id === currentDocId) {
        currentDocId = null;
        currentDocTitle = 'لا يوجد مستند مفتوح';
        _updateDocBar();
      }
      await _renderDocList();
      showToast('✓ تم حذف المستند');
    } else {
      showToast('تعذّر الحذف');
    }
  }

  if (spDocNew) spDocNew.addEventListener('click', _createDoc);
  if (spDocSave) spDocSave.addEventListener('click', _saveDoc);
  if (spDocRefresh) spDocRefresh.addEventListener('click', _renderDocList);

  inputText.addEventListener('input', () => {
    if (currentDocId && spDocSave) spDocSave.classList.add('sp-doc-dirty');
  });

  if (typeof BayanAuth !== 'undefined') {
    BayanAuth.onAuthStateChange(() => _renderDocList());
  }

  _renderDocList();

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
  // Context menu pickup (from background.js → storage)
  // NOTE: background.js calls sidePanel.open() BEFORE storage.set()
  // to preserve the user gesture token. This means on first open,
  // storage may not be ready yet. We retry once after 300ms.
  // If the panel is ALREADY open, the storage.onChanged listener
  // below catches new actions in real-time.
  // ══════════════════════════════════════════════════════════

  // Dispatch a context action (correct/summarize/dialect/quran) by filling
  // the matching tab's input, switching to it, and auto-running its model.
  // Declared after all element refs so dialect/quran handles are in scope.
  function runContextAction(action, text) {
    sourceSelectionText = text;
    if (action === TAB.CORRECT) {
      inputText.value = text;
      updateCounts(inputText, charCount, wordCount);
      document.querySelector(`[data-tab="${TAB.CORRECT}"]`)?.click();
      setTimeout(() => runAnalysis(text), 100);
    } else if (action === TAB.SUMMARIZE) {
      summaryInputText.value = text;
      updateCounts(summaryInputText, summaryCharCount, null);
      document.querySelector(`[data-tab="${TAB.SUMMARIZE}"]`)?.click();
      setTimeout(() => btnSummarize.click(), 100);
    } else if (action === TAB.DIALECT && dialectInput && btnDialect) {
      dialectInput.value = text;
      updateCounts(dialectInput, dialectCharCount, null);
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

      // Storage not ready yet — retry once after 300ms
      if ((!data.contextAction || !data.contextText) && retryCount < 2) {
        setTimeout(() => tryPickupContext(retryCount + 1), 300);
        return;
      }

      if (!data.contextAction || !data.contextText) {
        // No context action after retries — restore previous state
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

  // Start context pickup with retry
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
