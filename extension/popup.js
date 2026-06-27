/**
 * Bayan Chrome Extension — Popup Logic
 *
 * Fixes applied:
 *   HIGH-1: Offset rebasing via applyAndRebase() after each individual apply
 *   MED-1:  Clipboard .catch() on all writeText() calls
 *   MED-2:  Staleness detection — locks corrections when user edits after analysis
 */

document.addEventListener('DOMContentLoaded', () => {
  // ── Element references ──
  const inputText = document.getElementById('input-text');
  const charCount = document.getElementById('char-count');
  const wordCount = document.getElementById('word-count');
  const btnCorrect = document.getElementById('btn-correct');
  const btnClear = document.getElementById('btn-clear');
  const btnApplyAll = document.getElementById('btn-apply-all');
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

  // Summary tab elements
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

  /**
   * MED-2: Snapshot of the text that was last analyzed.
   * All suggestion offsets are relative to THIS text.
   * applyAndRebase() mutates this alongside suggestions.
   */
  let analyzedText = '';

  /**
   * MED-2: Whether the analysis results are stale.
   * Set to true when the user edits the textarea after analysis.
   * When stale, suggestion actions are blocked.
   */
  let isStale = false;

  // ══════════════════════════════════════════════════════════
  // Tab switching
  // ══════════════════════════════════════════════════════════
  document.querySelectorAll('.bayan-tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      const targetTab = tab.dataset.tab;
      document.querySelectorAll('.bayan-tab').forEach((t) => {
        t.classList.toggle('active', t.dataset.tab === targetTab);
        t.setAttribute('aria-selected', t.dataset.tab === targetTab ? 'true' : 'false');
      });
      document.querySelectorAll('.bayan-panel').forEach((p) => {
        p.classList.toggle('active', p.id === `panel-${targetTab}`);
      });
    });
  });

  // ══════════════════════════════════════════════════════════
  // Character & word counter (shared: bayan-core.js)
  // ══════════════════════════════════════════════════════════

  inputText.addEventListener('input', () => {
    updateCounts(inputText, charCount, wordCount);

    // MED-2: Detect user edit after analysis → mark stale
    if (currentSuggestions.length > 0 && inputText.value !== analyzedText) {
      markStale();
    }
  });

  summaryInputText.addEventListener('input', () => updateCounts(summaryInputText, summaryCharCount, null));

  // ══════════════════════════════════════════════════════════
  // MED-2: Staleness management
  // ══════════════════════════════════════════════════════════

  /**
   * Mark analysis results as stale (user edited textarea).
   * Disables suggestion actions and shows a re-analysis prompt.
   */
  function markStale() {
    if (isStale) return; // already stale
    isStale = true;

    // Visual indicator: dim the results area
    if (resultSection) resultSection.classList.add('bayan-stale');
    if (suggestionsSection) suggestionsSection.classList.add('bayan-stale');

    // Show re-analysis toast
    showToast('⚠ النص تغيّر — أعد التحليل لتحديث الاقتراحات', 4000);

    // Update button text to indicate re-analysis needed
    btnCorrect.innerHTML = `
      <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h5M20 20v-5h-5M4 9a8 8 0 0114-3M20 15a8 8 0 01-14 3"/></svg>
      إعادة التحليل`;
  }

  /**
   * Clear staleness (after re-analysis or clear).
   */
  function clearStale() {
    isStale = false;
    if (resultSection) resultSection.classList.remove('bayan-stale');
    if (suggestionsSection) suggestionsSection.classList.remove('bayan-stale');

    // Restore button text
    btnCorrect.innerHTML = `
      <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4"/></svg>
      تحليل وتصحيح`;
  }

  // ══════════════════════════════════════════════════════════
  // Loading state
  // ══════════════════════════════════════════════════════════
  function setLoading(show, text = 'جارٍ التحليل...') {
    loadingOverlay.classList.toggle('is-hidden', !show);
    loadingTextEl.textContent = text;
  }

  // Score ring — shared via bayan-core.js (updateScore)

  // ══════════════════════════════════════════════════════════
  // Render suggestions list
  // ══════════════════════════════════════════════════════════
  function renderSuggestions(suggestions) {
    currentSuggestions = suggestions;

    if (!suggestions || suggestions.length === 0) {
      suggestionsSection.classList.add('is-hidden');
      return;
    }

    suggestionsSection.classList.remove('is-hidden');
    const html = suggestions.map((s, i) => buildSuggestionCardHTML(s, i)).join('');
    suggestionsList.innerHTML = html;

    // Bind suggestion card events
    suggestionsList.querySelectorAll('.bayan-alt-chip').forEach((chip) => {
      chip.addEventListener('click', (e) => {
        e.stopPropagation();

        // MED-2: Block if stale
        if (isStale) {
          showToast('⚠ أعد التحليل أولاً — النص تغيّر');
          return;
        }

        const suggestionId = chip.dataset.cardId;
        const altText = chip.dataset.cardAlt;
        const suggestion = currentSuggestions.find((s) => String(s.id || '') === String(suggestionId));
        if (!suggestion) return;

        if (altText === suggestion.original) {
          // Dismiss — remove from list, no text change, no rebase needed
          currentSuggestions = removeSuggestion(currentSuggestions, suggestion.id);
          if (suggestion.type === 'spelling' && typeof BayanAuth !== 'undefined') {
            BayanAuth.addDismissedWord(suggestion.original);
          }
        } else {
          // ═══════════════════════════════════════════════════
          // HIGH-1 FIX: Apply + Rebase via atomic function
          // ═══════════════════════════════════════════════════
          const result = applyAndRebase(analyzedText, suggestion, altText, currentSuggestions);
          analyzedText = result.text;
          currentSuggestions = result.suggestions;

          // Sync textarea with the rebased text
          inputText.value = analyzedText;
          updateCounts(inputText, charCount, wordCount);
        }

        // Re-render score and suggestions
        const counts = countByType(currentSuggestions);
        updateScore(counts.spelling, counts.grammar, counts.punctuation);
        renderSuggestions(currentSuggestions);

        // Re-render highlighted text with updated offsets
        resultText.innerHTML = renderHighlightedText(analyzedText, currentSuggestions);

        showToast('✓ تم التصحيح');
      });
    });

    // Show apply-all only when >= 2
    btnApplyAll.classList.toggle('is-hidden', suggestions.length < 2);
  }

  // ══════════════════════════════════════════════════════════
  // Clear button
  // ══════════════════════════════════════════════════════════
  btnClear.addEventListener('click', () => {
    inputText.value = '';
    analyzedText = '';
    updateCounts(inputText, charCount, wordCount);
    scoreSection.classList.add('is-hidden');
    resultSection.classList.add('is-hidden');
    suggestionsSection.classList.add('is-hidden');
    timingSection.classList.add('is-hidden');
    currentSuggestions = [];
    clearStale();
  });

  // ══════════════════════════════════════════════════════════
  // Correct button
  // ══════════════════════════════════════════════════════════
  btnCorrect.addEventListener('click', async () => {
    const text = inputText.value.trim();
    if (!text) {
      showToast('أدخل نصاً للتحليل');
      return;
    }
    if (text.length < CONFIG.MIN_ANALYZE_LENGTH) {
      showToast('النص قصير جداً (الحد الأدنى ١٥ حرفاً)');
      return;
    }
    if (text.length > CONFIG.MAX_ANALYZE_LENGTH) {
      showToast('النص طويل جداً (الحد الأقصى ٥٠٠٠ حرف)');
      return;
    }

    setLoading(true, 'جارٍ التحليل...');
    clearStale(); // MED-2: Clear stale on re-analysis

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

        // MED-2: Snapshot the analyzed text — all offsets reference THIS string
        analyzedText = data.original;
        // Sync textarea to the exact text the backend analyzed
        inputText.value = analyzedText;
        updateCounts(inputText, charCount, wordCount);

        // Show corrected text with highlights
        resultSection.classList.remove('is-hidden');
        resultText.innerHTML = renderHighlightedText(analyzedText, suggestions);

        // Update score
        const counts = countByType(suggestions);
        updateScore(counts.spelling, counts.grammar, counts.punctuation);

        // Render suggestion cards
        renderSuggestions(suggestions);

        // Show timing
        if (data.timing_ms) {
          timingSection.classList.remove('is-hidden');
          timingText.textContent = `التحليل: ${data.timing_ms.total_ms || 0}ms (إملائي: ${data.timing_ms.spelling_ms || 0}ms، نحوي: ${data.timing_ms.grammar_ms || 0}ms، ترقيم: ${data.timing_ms.punctuation_ms || 0}ms)`;
        }

        if (suggestions.length === 0) {
          showToast('نصك ممتاز! لم نجد أي أخطاء ✨');
        }
      } else {
        showToast('تعذّر التحليل — حاول مرة أخرى');
      }
    } catch (error) {
      console.error('[Bayan] Analysis error:', error);
      showToast('خطأ في الاتصال — تحقق من الإنترنت');
    } finally {
      setLoading(false);
    }
  });

  // ══════════════════════════════════════════════════════════
  // Apply all button
  // ══════════════════════════════════════════════════════════
  btnApplyAll.addEventListener('click', () => {
    if (currentSuggestions.length === 0) return;

    // MED-2: Block if stale
    if (isStale) {
      showToast('⚠ أعد التحليل أولاً — النص تغيّر');
      return;
    }

    // Apply all patches using reverse-order (no rebase needed — all applied at once)
    analyzedText = applyAllPatches(analyzedText, currentSuggestions);
    inputText.value = analyzedText;
    updateCounts(inputText, charCount, wordCount);
    currentSuggestions = [];
    resultText.innerHTML = escapeHtml(analyzedText);
    updateScore(0, 0, 0);
    renderSuggestions([]);
    showToast('✓ تم تطبيق جميع التصحيحات');
  });

  // ══════════════════════════════════════════════════════════
  // Copy result (MED-1: .catch() for clipboard errors)
  // ══════════════════════════════════════════════════════════
  btnCopyResult.addEventListener('click', () => {
    const text = resultText.textContent || '';
    navigator.clipboard.writeText(text)
      .then(() => showToast('✓ تم نسخ النص'))
      .catch(() => showToast('تعذّر النسخ'));
  });

  // ══════════════════════════════════════════════════════════
  // Summarize button
  // ══════════════════════════════════════════════════════════
  btnSummarize.addEventListener('click', async () => {
    const text = summaryInputText.value.trim();
    if (!text) {
      showToast('أدخل نصاً للتلخيص');
      return;
    }
    if (text.length < CONFIG.MIN_SUMMARIZE_LENGTH) {
      showToast('النص قصير جداً للتلخيص');
      return;
    }

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
      console.error('[Bayan] Summarization error:', error);
      showToast('خطأ في الاتصال — تحقق من الإنترنت');
    } finally {
      setLoading(false);
    }
  });

  // ══════════════════════════════════════════════════════════
  // Copy summary (MED-1: .catch() for clipboard errors)
  // ══════════════════════════════════════════════════════════
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
        console.error('[Bayan] Dialect error:', error);
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

  if (quranInput) {
    quranInput.addEventListener('input', () => updateCounts(quranInput, quranCharCount, null));

    btnQuran.addEventListener('click', async () => {
      const text = quranInput.value.trim();
      if (!text) { showToast('أدخل آية للتدقيق'); return; }

      setLoading(true, 'جارٍ التدقيق...');
      try {
        const data = await bayanQuran(text);
        quranResultSection.classList.remove('is-hidden');
        if (data.error) {
          quranText.textContent = data.error;
          quranMeta.textContent = '';
        } else {
          quranText.textContent = data.full_verse || data.matched_segment || JSON.stringify(data);
          quranMeta.textContent = data.matched_segment && data.full_verse
            ? `المقطع المطابق: ${data.matched_segment}`
            : '';
          showToast('✓ تم التدقيق');
        }
      } catch (error) {
        console.error('[Bayan] Quran error:', error);
        showToast('خطأ في الاتصال — تحقق من الإنترنت');
      } finally {
        setLoading(false);
      }
    });

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
          acList.innerHTML = '<div class="bayan-ac-empty">لا توجد اقتراحات</div>';
          return;
        }

        acList.innerHTML = suggestions
          .map((s) => `<button class="bayan-alt-chip bayan-alt-chip--main bayan-ac-chip" type="button">${escapeHtml(s)}</button>`)
          .join('');

        acList.querySelectorAll('.bayan-ac-chip').forEach((chip) => {
          chip.addEventListener('click', () => {
            const needsSpace = acInput.value.length > 0 && !/\s$/.test(acInput.value);
            acInput.value += (needsSpace ? ' ' : '') + chip.textContent;
            updateCounts(acInput, acCharCount, null);
            acInput.focus();
            showToast('✓ تمت الإضافة');
          });
        });
      } catch (error) {
        console.error('[Bayan] Autocomplete error:', error);
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

  const DOWNLOAD_ICON = '<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1M12 4v12m0 0l-4-4m4 4l4-4"/></svg>';

  function addDownloadButton(headerEl, getText, filename) {
    if (!headerEl) return;
    const btn = document.createElement('button');
    btn.className = 'bayan-btn-icon';
    btn.type = 'button';
    btn.title = 'تنزيل كملف نصي';
    btn.innerHTML = DOWNLOAD_ICON;
    btn.addEventListener('click', () => downloadTxt((getText() || '').trim(), filename));
    headerEl.appendChild(btn);
  }

  addDownloadButton(
    btnCopyResult ? btnCopyResult.parentElement : null,
    () => resultText.textContent,
    'bayan-corrected.txt'
  );
  addDownloadButton(
    btnCopySummary ? btnCopySummary.parentElement : null,
    () => summaryText.textContent,
    'bayan-summary.txt'
  );

  // ══════════════════════════════════════════════════════════
  // Auth UI wiring (shared via bayan-core.js)
  // ══════════════════════════════════════════════════════════
  bayanInitAuth();

  // ══════════════════════════════════════════════════════════
  // Status check on load
  // ══════════════════════════════════════════════════════════
  (async function checkStatus() {
    const statusDot = document.querySelector('.bayan-status-dot');
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
  // Phase 4: Context Menu Pickup
  // ══════════════════════════════════════════════════════════
  // Fix #2: Guard against double execution
  // Fix #4: Tab name constants
  // Fix #5: Storage fallback (session → local)
  // ══════════════════════════════════════════════════════════

  const TAB_ACTIONS = { correct: 'correct', summarize: 'summarize' };
  let contextConsumed = false; // Fix #2

  (async function checkContextAction() {
    // Only available in extension context (not in test pages)
    if (typeof chrome === 'undefined' || !chrome.storage) return;

    // Fix #2: Prevent double-trigger
    if (contextConsumed) return;

    // Fix #5: Storage fallback
    const storage = chrome.storage?.session || chrome.storage?.local;
    if (!storage) return;

    try {
      const data = await storage.get(['contextAction', 'contextText', 'contextTimestamp']);
      if (!data.contextAction || !data.contextText) return;

      // Ignore stale actions (older than 15 seconds — matches background cleanup)
      const age = Date.now() - (data.contextTimestamp || 0);
      if (age > 15000) {
        chrome.runtime.sendMessage({ type: 'CLEAR_CONTEXT' });
        return;
      }

      // Fix #2: Mark as consumed BEFORE processing
      contextConsumed = true;

      console.log(`[Bayan] Context action: ${data.contextAction}, text length: ${data.contextText.length}`);

      if (data.contextAction === TAB_ACTIONS.correct) {
        // Fill the correction tab and auto-trigger analysis
        inputText.value = data.contextText;
        updateCounts(inputText, charCount, wordCount);

        // Switch to correction tab
        const correctTab = document.querySelector(`[data-tab="${TAB_ACTIONS.correct}"]`);
        if (correctTab) correctTab.click();

        // Auto-click the correct button after a brief delay for UI paint
        setTimeout(() => btnCorrect.click(), 150);

      } else if (data.contextAction === TAB_ACTIONS.summarize) {
        // Fill the summary tab and auto-trigger summarization
        summaryInputText.value = data.contextText;
        updateCounts(summaryInputText, summaryCharCount, null);

        // Switch to summarize tab
        const summarizeTab = document.querySelector(`[data-tab="${TAB_ACTIONS.summarize}"]`);
        if (summarizeTab) summarizeTab.click();

        // Auto-click the summarize button
        setTimeout(() => btnSummarize.click(), 150);
      }

      // Clear the context action so it doesn't re-trigger on next popup open
      chrome.runtime.sendMessage({ type: 'CLEAR_CONTEXT' });

    } catch (err) {
      console.warn('[Bayan] Context action check failed:', err);
    }
  })();

  // U4: Persist popup state to chrome.storage.session
  const _popupStorage = chrome.storage?.session || chrome.storage?.local;
  if (_popupStorage) {
    _popupStorage.get(['popup_state'], (d) => {
      if (d.popup_state && inputText && !inputText.value) {
        inputText.value = d.popup_state.text || '';
        if (charCount) charCount.textContent = inputText.value.length;
        var wc = inputText.value.trim().split(/\s+/).filter(w => w).length;
        if (wordCount) wordCount.textContent = wc;
      }
    });
    var _popupSaveTimer = null;
    if (inputText) {
      inputText.addEventListener('input', () => {
        clearTimeout(_popupSaveTimer);
        _popupSaveTimer = setTimeout(() => {
          _popupStorage.set({ popup_state: { text: inputText.value, ts: Date.now() } });
        }, 1000);
      });
    }
  }
});

