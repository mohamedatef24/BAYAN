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
  const TAB = { CORRECT: 'correct', SUMMARIZE: 'summarize' };

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

  // Summary tab
  const summaryInputText = document.getElementById('summary-input-text');
  const summaryCharCount = document.getElementById('summary-char-count');
  const btnSummarize = document.getElementById('btn-summarize');
  const summaryResultSection = document.getElementById('summary-result-section');
  const summaryText = document.getElementById('summary-text');
  const summaryMeta = document.getElementById('summary-meta');
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
  let debounceTimer = null;

  const SCORE_CIRCUMFERENCE = 440;
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
  // Score ring
  // ══════════════════════════════════════════════════════════
  function updateScore(spelling, grammar, punctuation) {
    const score = calculateWritingScore(spelling, grammar, punctuation);
    const total = spelling + grammar + punctuation;

    scoreSection.classList.remove('is-hidden');

    if (scoreValue) scoreValue.textContent = score > 0 || total > 0 ? score.toLocaleString('ar-EG') : '--';
    if (scoreCircle) {
      const offset = SCORE_CIRCUMFERENCE - (score / 100) * SCORE_CIRCUMFERENCE;
      scoreCircle.style.strokeDashoffset = String(offset);
    }
    if (scoreHint) scoreHint.textContent = getScoreHint(score, total);
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
        const suggestions = sortSuggestions(data.suggestions || []);
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
    showToast('✓ تم تطبيق جميع التصحيحات');
  });

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

      if (data.contextAction === TAB.CORRECT) {
        inputText.value = data.contextText;
        updateCounts(inputText, charCount, wordCount);

        const correctTab = document.querySelector(`[data-tab="${TAB.CORRECT}"]`);
        if (correctTab) correctTab.click();

        // Auto-analyze immediately
        setTimeout(() => runAnalysis(data.contextText), 100);

      } else if (data.contextAction === TAB.SUMMARIZE) {
        summaryInputText.value = data.contextText;
        updateCounts(summaryInputText, summaryCharCount, null);

        const summarizeTab = document.querySelector(`[data-tab="${TAB.SUMMARIZE}"]`);
        if (summarizeTab) summarizeTab.click();

        setTimeout(() => btnSummarize.click(), 100);
      }

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

      if (action === TAB.CORRECT) {
        inputText.value = text;
        updateCounts(inputText, charCount, wordCount);

        const correctTab = document.querySelector(`[data-tab="${TAB.CORRECT}"]`);
        if (correctTab) correctTab.click();

        runAnalysis(text);

      } else if (action === TAB.SUMMARIZE) {
        summaryInputText.value = text;
        updateCounts(summaryInputText, summaryCharCount, null);

        const summarizeTab = document.querySelector(`[data-tab="${TAB.SUMMARIZE}"]`);
        if (summarizeTab) summarizeTab.click();

        setTimeout(() => btnSummarize.click(), 100);
      }

      chrome.runtime.sendMessage({ type: 'CLEAR_CONTEXT' });
    });
  }
});
