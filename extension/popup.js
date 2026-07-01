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
  const btnCopyText = document.getElementById('btn-copy-text');
  const scoreSection = document.getElementById('score-section');
  const suggestionsSection = document.getElementById('suggestions-section');
  const suggestionsList = document.getElementById('suggestions-list');
  const timingSection = document.getElementById('timing-section');
  const timingText = document.getElementById('timing-text');
  const loadingOverlay = document.getElementById('loading-overlay');
  const loadingTextEl = document.getElementById('loading-text');

  // Summary tab elements
  const summaryInputText = document.getElementById('summary-input-text');
  const summaryWordCountInput = document.getElementById('summary-word-count-input');
  const btnSummarize = document.getElementById('btn-summarize');
  const summaryResultSection = document.getElementById('summary-result-section');
  const summaryText = document.getElementById('summary-text');
  const summaryStats = document.getElementById('summary-stats');
  const summaryWordCount = document.getElementById('summary-word-count');
  const summaryCompression = document.getElementById('summary-compression');
  const btnCopySummary = document.getElementById('btn-copy-summary');

  // Score elements
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

  /**
   * MED-2: Snapshot of the text that was last analyzed.
   * All suggestion offsets are relative to THIS text.
   * applyAndRebase() mutates this alongside suggestions.
   */
  let analyzedText = '';

  const _dismissedWords = new Set(
    JSON.parse(localStorage.getItem('bayan_dismissed_words') || '[]')
  );
  function _saveDismissedWords() {
    try { localStorage.setItem('bayan_dismissed_words', JSON.stringify([..._dismissedWords])); } catch {}
  }

  /**
   * MED-2: Whether the analysis results are stale.
   * Set to true when the user edits the textarea after analysis.
   * When stale, suggestion actions are blocked.
   */
  let isStale = false;

  const SCORE_CIRCUMFERENCE = 440;

  // ══════════════════════════════════════════════════════════
  // State persistence — survive popup close/reopen
  // ══════════════════════════════════════════════════════════
  const STORAGE_KEY = 'bayan_popup_state';

  function saveState() {
    const activeTab = document.querySelector('.bayan-tab.active');
    const state = {
      tab: activeTab ? activeTab.dataset.tab : 'correct',
      inputText: inputText.value,
      summaryInput: summaryInputText.value,
      dialectInput: document.getElementById('dialect-input-text')?.value || '',
      quranInput: document.getElementById('quran-input-text')?.value || '',
    };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch { /* quota exceeded — ignore */ }
  }

  function restoreState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const state = JSON.parse(raw);

      if (state.inputText) {
        inputText.value = state.inputText;
        updateCounts(inputText, charCount, wordCount);
      }
      if (state.summaryInput) {
        summaryInputText.value = state.summaryInput;
        const words = state.summaryInput.trim() ? state.summaryInput.trim().split(/\s+/).length : 0;
        if (summaryWordCountInput) summaryWordCountInput.textContent = words.toLocaleString('ar-EG');
      }
      const dialectEl = document.getElementById('dialect-input-text');
      if (state.dialectInput && dialectEl) dialectEl.value = state.dialectInput;
      const quranEl = document.getElementById('quran-input-text');
      if (state.quranInput && quranEl) quranEl.value = state.quranInput;

      if (state.tab && state.tab !== 'correct') {
        const tabBtn = document.querySelector(`.bayan-tab[data-tab="${state.tab}"]`);
        if (tabBtn) tabBtn.click();
      }
    } catch { /* corrupt state — ignore */ }
  }

  restoreState();

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

    // MED-2: Detect user edit after analysis → mark stale
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
  // MED-2: Staleness management
  // ══════════════════════════════════════════════════════════

  /**
   * Mark analysis results as stale (user edited textarea).
   * Disables suggestion actions and shows a re-analysis prompt.
   */
  function markStale() {
    if (isStale) return;
    isStale = true;

    if (suggestionsSection) suggestionsSection.classList.add('bayan-stale');

    showToast('⚠ النص تغيّر — أعد التحليل لتحديث الاقتراحات', 4000);

    btnCorrect.innerHTML = `
      <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h5M20 20v-5h-5M4 9a8 8 0 0114-3M20 15a8 8 0 01-14 3"/></svg>
      إعادة التحليل`;
  }

  /**
   * Clear staleness (after re-analysis or clear).
   */
  function clearStale() {
    isStale = false;
    if (suggestionsSection) suggestionsSection.classList.remove('bayan-stale');

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

  // ══════════════════════════════════════════════════════════
  // Toast
  // ══════════════════════════════════════════════════════════
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
        scoreHint.innerHTML = 'ابدأ الكتابة لرؤية تقييمك<br><span class="bayan-score-hint-sub">تحسين القواعد يرفع التقييم</span>';
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
        suggestionsList.innerHTML = '<div class="bayan-empty-state"><svg class="bayan-empty-state-icon" width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg><p class="bayan-empty-state-title">نصك ممتاز!</p><p class="bayan-empty-state-desc">لم نجد أي أخطاء — أحسنت! ✨</p></div>';
      } else {
        suggestionsSection.classList.add('is-hidden');
      }
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
          // Dismiss — remove from list, add to permanent whitelist
          _dismissedWords.add(suggestion.original);
          _saveDismissedWords();
          currentSuggestions = removeSuggestion(currentSuggestions, suggestion.id);
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

        showToast('✓ تم التصحيح');
        saveState();
      });
    });

    // Show apply-all only when more than 1 suggestion
    if (suggestions.length > 1) {
      btnApplyAll.textContent = 'تطبيق الكل (' + suggestions.length.toLocaleString('ar-EG') + ')';
      btnApplyAll.classList.remove('is-hidden');
    } else {
      btnApplyAll.classList.add('is-hidden');
    }
  }

  // ══════════════════════════════════════════════════════════
  // Clear button
  // ══════════════════════════════════════════════════════════
  btnClear.addEventListener('click', () => {
    inputText.value = '';
    analyzedText = '';
    updateCounts(inputText, charCount, wordCount);
    scoreSection.classList.add('is-hidden');
    suggestionsSection.classList.add('is-hidden');
    timingSection.classList.add('is-hidden');
    currentSuggestions = [];
    clearStale();
    saveState();
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
    if (text.trim().split(/\s+/).length < 2) {
      showToast('أدخل كلمتين على الأقل');
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
        const suggestions = sortSuggestions(data.suggestions || []).filter(
          s => !_dismissedWords.has(s.original)
        );
        currentSuggestions = suggestions;

        // MED-2: Snapshot the analyzed text — all offsets reference THIS string
        analyzedText = data.original;
        // Sync textarea to the exact text the backend analyzed
        inputText.value = analyzedText;
        updateCounts(inputText, charCount, wordCount);

        // Show corrected text in textarea
        // (suggestions apply directly to textarea via chips or Apply All)

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

        saveState();
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
    updateScore(0, 0, 0);
    renderSuggestions([]);
    showToast('✓ تم تطبيق جميع التصحيحات');
    saveState();
  });

  // ══════════════════════════════════════════════════════════
  // Copy text from textarea (MED-1: .catch() for clipboard errors)
  // ══════════════════════════════════════════════════════════
  btnCopyText.addEventListener('click', () => {
    const text = inputText.value || '';
    navigator.clipboard.writeText(text)
      .then(() => showToast('✓ تم نسخ النص'))
      .catch(() => showToast('تعذّر النسخ'));
  });

  // ══════════════════════════════════════════════════════════
  // Summary mode toggle (paragraph / bullets)
  // ══════════════════════════════════════════════════════════
  let summaryMode = 'paragraph';

  document.querySelectorAll('.bayan-mode-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      summaryMode = btn.dataset.mode;
      document.querySelectorAll('.bayan-mode-btn').forEach((b) => {
        b.classList.toggle('active', b.dataset.mode === summaryMode);
      });
    });
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
    const text = summaryText.innerText || summaryText.textContent || '';
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
  // Quran verification + translation (matching website)
  // ══════════════════════════════════════════════════════════
  const quranInput = document.getElementById('quran-input-text');
  const quranCharCount = document.getElementById('quran-char-count');
  const btnQuran = document.getElementById('btn-quran');
  const quranResultSection = document.getElementById('quran-result-section');
  const quranMatchList = document.getElementById('quran-match-list');

  let _quranQuery = '';

  function _parseSegment(seg) {
    const refMatch = seg.match(/【([^】]+)】/);
    const verseText = seg.replace(/\s*【[^】]+】\s*$/, '').replace(/^\(/, '').replace(/\)$/, '');
    const reference = refMatch ? refMatch[1] : '';
    return { verseText, reference };
  }

  function _langOptionsHTML() {
    return '<option value="">— اختر لغة —</option>'
      + '<option value="english">English</option>'
      + '<option value="french">Français</option>'
      + '<option value="turkish">Türkçe</option>'
      + '<option value="persian">فارسی</option>'
      + '<option value="russian">Русский</option>'
      + '<option value="spanish">Español</option>'
      + '<option value="german">Deutsch</option>'
      + '<option value="indonesian">Indonesia</option>'
      + '<option value="malay">Melayu</option>'
      + '<option value="bengali">বাংলা</option>'
      + '<option value="bosnian">Bosanski</option>'
      + '<option value="portuguese">Português</option>'
      + ‘<option value="uzbek">O&#x2019;zbek</option>’;
  }

  function _renderMatchCards(matches) {
    quranMatchList.innerHTML = '';
    matches.forEach(function(m, i) {
      var parsed = _parseSegment(m.matched_segment || '');
      var card = document.createElement('div');
      card.className = 'bayan-quran-match-card';
      card.innerHTML = '<div class="bayan-quran-result-header">'
        + '<span style="color:#06b6d4;font-size:12px;font-weight:700;">✓ نتيجة ' + (i + 1) + '</span>'
        + '<button class="bayan-btn-icon qmc-copy" type="button" title="نسخ">'
        + '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" stroke-width="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" stroke-width="2"/></svg>'
        + '</button></div>'
        + '<p class="bayan-quran-uthmani" dir="rtl">' + _escHTML(parsed.verseText) + '</p>'
        + '<p class="bayan-quran-reference">' + (parsed.reference ? '[' + _escHTML(parsed.reference) + ']' : '') + '</p>'
        + '<div class="bayan-quran-translate">'
        + '<div class="bayan-quran-translate-row">'
        + '<span style="font-size:12px;font-weight:600;color:var(--text-secondary);">ترجمة الآية</span>'
        + '<select class="bayan-quran-lang-select qmc-lang">' + _langOptionsHTML() + '</select>'
        + '</div>'
        + '<div class="bayan-quran-translation is-hidden qmc-trans-section">'
        + '<p class="qmc-trans-text" dir="auto"></p>'
        + '<button class="bayan-btn-icon qmc-copy-trans" type="button" title="نسخ الترجمة" style="margin-top:4px;">'
        + '<svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="9" y="9" width="13" height="13" rx="2" stroke-width="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" stroke-width="2"/></svg>'
        + '</button></div></div>';

      card.querySelector('.qmc-copy').addEventListener('click', function() {
        var txt = parsed.verseText + (parsed.reference ? ' [' + parsed.reference + ']' : '');
        navigator.clipboard.writeText(txt)
          .then(function() { showToast('✓ تم النسخ'); })
          .catch(function() { showToast('تعذّر النسخ'); });
      });

      var langSel = card.querySelector('.qmc-lang');
      var transSec = card.querySelector('.qmc-trans-section');
      var transP = card.querySelector('.qmc-trans-text');
      var copyTransBtn = card.querySelector('.qmc-copy-trans');

      langSel.addEventListener('change', async function() {
        var lang = langSel.value;
        if (!lang || !_quranQuery) return;
        transSec.classList.remove('is-hidden');
        transP.textContent = '⏳ جاري الترجمة...';
        try {
          var data = await bayanQuran(_quranQuery, lang);
          if (data.error) { transP.textContent = data.error; return; }
          var seg = data.matched_segment || '';
          var p = _parseSegment(seg);
          transP.textContent = p.verseText;
        } catch (err) {
          transP.textContent = 'حدث خطأ في الترجمة';
        }
      });

      copyTransBtn.addEventListener('click', function() {
        navigator.clipboard.writeText(transP.textContent || '')
          .then(function() { showToast('✓ تم نسخ الترجمة'); })
          .catch(function() { showToast('تعذّر النسخ'); });
      });

      quranMatchList.appendChild(card);
    });
  }

  function _escHTML(s) { var d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

  if (quranInput) {
    quranInput.addEventListener('input', () => { updateCounts(quranInput, quranCharCount, null); saveState(); });

    btnQuran.addEventListener('click', async () => {
      const text = quranInput.value.trim();
      if (!text) { showToast('أدخل آية للتدقيق'); return; }

      _quranQuery = text;
      setLoading(true, 'جارٍ التدقيق...');

      try {
        const data = await bayanQuran(text, 'تدقيق الايات', null, 5);
        quranResultSection.classList.remove('is-hidden');

        if (data.error) {
          quranMatchList.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;padding:8px;">' + _escHTML(data.error) + '</p>';
          return;
        }

        var matches = data.matches || [data];
        _renderMatchCards(matches);
        showToast('✓ تم التدقيق');
      } catch (error) {
        console.error('[Bayan] Quran error:', error);
        quranResultSection.classList.remove('is-hidden');
        quranMatchList.innerHTML = '<p style="color:var(--text-secondary);font-size:13px;padding:8px;">خطأ في الاتصال — تحقق من الإنترنت</p>';
      } finally {
        setLoading(false);
      }
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

    summaryExportMenu.querySelectorAll('.bayan-export-item').forEach((item) => {
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

  // ── Close button: close the popup window ──
  const btnClosePopup = document.getElementById('btn-close-popup');
  if (btnClosePopup) {
    btnClosePopup.addEventListener('click', () => window.close());
  }

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
        const ctxWords = data.contextText.trim() ? data.contextText.trim().split(/\s+/).length : 0;
        if (summaryWordCountInput) summaryWordCountInput.textContent = ctxWords.toLocaleString('ar-EG');

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
});



// ── Theme Toggle Logic ──
(function initBayanThemeToggle() {
  const toggleBtn = document.getElementById('ext-theme-toggle');
  
  // Load theme from storage
  chrome.storage.local.get(['theme'], (result) => {
    const currentTheme = result.theme || 'dark'; // default to dark
    document.documentElement.setAttribute('data-theme', currentTheme);
  });

  // Sync theme changes instantly across all views
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