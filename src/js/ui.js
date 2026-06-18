// Bayan UI helpers — score, suggestions list, mobile nav, bottom sheet

const TYPE_LABELS = {
  spelling: 'إملائي',
  grammar: 'نحوي',
  punctuation: 'ترقيم'
};

const SCORE_CIRCUMFERENCE = 440;

/**
 * Calculate writing score from suggestion counts
 */
function calculateWritingScore(spelling, grammar, punctuation) {
  const score = 100 - spelling * 8 - grammar * 6 - punctuation * 3;
  return Math.max(0, Math.min(100, score));
}

/**
 * Update the score ring UI
 */
function updateWritingScore(spelling, grammar, punctuation) {
  const score = calculateWritingScore(spelling, grammar, punctuation);
  const valueEl = document.getElementById('score-value');
  const circleEl = document.getElementById('score-circle');
  const hintEl = document.getElementById('score-hint');

  if (valueEl) {
    valueEl.textContent = score > 0 || (spelling + grammar + punctuation) > 0
      ? score.toLocaleString('ar-EG')
      : '--';
  }

  if (circleEl) {
    const offset = SCORE_CIRCUMFERENCE - (score / 100) * SCORE_CIRCUMFERENCE;
    circleEl.style.strokeDashoffset = String(offset);
  }

  if (hintEl) {
    const total = spelling + grammar + punctuation;
    if (total === 0) {
      hintEl.innerHTML = 'ابدأ الكتابة لرؤية تقييمك<br><span class="text-xs">تحسين القواعد يرفع التقييم</span>';
    } else if (score >= 90) {
      hintEl.textContent = 'كتابة ممتازة! استمر.';
    } else if (score >= 70) {
      hintEl.textContent = 'جيد — راجع الاقتراحات لتحسين النص.';
    } else {
      hintEl.textContent = 'يحتاج النص إلى بعض التحسينات.';
    }
  }

  const sheetCount = document.getElementById('mobile-suggestion-count');
  if (sheetCount) {
    const total = spelling + grammar + punctuation;
    sheetCount.textContent = total.toLocaleString('ar-EG');
  }
}

/**
 * Build HTML for a single suggestion card
 */
function buildSuggestionCardHTML(suggestion, index) {
  const badgeClass = `badge-${suggestion.type}`;
  const label = TYPE_LABELS[suggestion.type] || suggestion.type;
  const alts = suggestion.alternatives || [suggestion.correction, suggestion.original];

  let altsHTML = '';
  alts.forEach((alt, i) => {
    const isKeep = alt === suggestion.original;
    const isMain = i === 0;
    const cls = isKeep ? 'alt-chip alt-chip--keep' : (isMain ? 'alt-chip alt-chip--main' : 'alt-chip');
    const chipLabel = isKeep ? `${escapeHtml(alt)} ✓` : escapeHtml(alt);
    altsHTML += `<button class="${cls}" data-card-alt="${escapeHtml(alt)}" data-card-index="${index}" type="button">${chipLabel}</button>`;
  });

  return `
    <div class="suggestion-card" role="listitem" tabindex="0"
      data-suggestion-index="${index}"
      aria-label="${label}: ${suggestion.original} إلى ${suggestion.correction}">
      <span class="suggestion-card-badge ${badgeClass}">${label}</span>
      <div class="suggestion-card-change">
        <span class="suggestion-card-original">${escapeHtml(suggestion.original)}</span>
        <span class="suggestion-card-arrow">←</span>
      </div>
      <div class="suggestion-card-alts">${altsHTML}</div>
    </div>`;
}

/**
 * Render suggestions into sidebar and bottom sheet lists
 */
function updateSuggestionsList(suggestions) {
  const lists = [
    document.getElementById('suggestions-list'),
    document.getElementById('bottom-sheet-list')
  ].filter(Boolean);

  const applyAllBtn = document.getElementById('apply-all-btn');
  const applyAllSheet = document.getElementById('apply-all-sheet');

  if (!suggestions || suggestions.length === 0) {
    const emptyHTML = `
      <div class="empty-state">
        <div class="empty-state__icon">
          <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
        </div>
        <div class="empty-state__title">لا توجد اقتراحات</div>
        <div class="empty-state__desc">ابدأ بكتابة نص عربي وسيتم تحليله تلقائياً</div>
      </div>`;

    lists.forEach((el) => { el.innerHTML = emptyHTML; });
    if (applyAllBtn) applyAllBtn.classList.add('is-hidden');
    if (applyAllSheet) applyAllSheet.classList.add('is-hidden');
    return;
  }

  const cardsHTML = suggestions.map((s, i) => buildSuggestionCardHTML(s, i)).join('');

  lists.forEach((el) => {
    el.innerHTML = cardsHTML;
    bindSuggestionCardEvents(el);
  });

  const showApplyAll = suggestions.length >= 2;
  if (applyAllBtn) applyAllBtn.classList.toggle('is-hidden', !showApplyAll);
  if (applyAllSheet) applyAllSheet.classList.toggle('is-hidden', !showApplyAll);
}

function bindSuggestionCardEvents(container) {
  container.querySelectorAll('.suggestion-card').forEach((card) => {
    card.addEventListener('click', (e) => {
      if (e.target.closest('.alt-chip') || e.target.closest('.suggestion-card-apply')) return;
      const idx = parseInt(card.dataset.suggestionIndex, 10);
      scrollToSuggestion(idx);
      focusSuggestionInEditor(idx);
    });

    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const idx = parseInt(card.dataset.suggestionIndex, 10);
        applySuggestionByIndex(idx);
      }
    });
  });

  // Alt chip clicks
  container.querySelectorAll('.alt-chip').forEach((chip) => {
    chip.addEventListener('click', (e) => {
      e.stopPropagation();
      const idx = parseInt(chip.dataset.cardIndex, 10);
      const altText = chip.dataset.cardAlt;
      const suggestions = window.currentSuggestions || [];
      const suggestion = suggestions[idx];
      if (!suggestion) return;

      if (altText === suggestion.original) {
        dismissSuggestion(suggestion);
      } else {
        applyAlternativeCorrection(suggestion, altText);
      }
    });
  });

  container.querySelectorAll('.suggestion-card-apply').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const idx = parseInt(btn.dataset.applyIndex, 10);
      applySuggestionByIndex(idx);
    });
  });
}

function scrollToSuggestion(index) {
  const span = document.querySelector(`[data-suggestion-id="${index}"]`);
  if (span) {
    span.scrollIntoView({ behavior: 'smooth', block: 'center' });
    span.classList.add('highlight-active');
    setTimeout(() => span.classList.remove('highlight-active'), 1500);
    showTooltip(span);
  }
}

function focusSuggestionInEditor(index) {
  const span = document.querySelector(`[data-suggestion-id="${index}"]`);
  if (span) showTooltip(span);
}

function setAnalyzingState(isAnalyzing) {
  const editor = getEditorElement();
  const indicator = document.getElementById('analyzing-indicator');

  if (editor) {
    editor.classList.toggle('analyzing', isAnalyzing);
    editor.setAttribute('aria-busy', isAnalyzing ? 'true' : 'false');
  }
  if (indicator) {
    indicator.classList.toggle('active', isAnalyzing);
  }
}

/* ── Mobile navigation ── */
function initMobileNav() {
  const btn = document.getElementById('mobile-menu-btn');
  const drawer = document.getElementById('mobile-drawer');
  const backdrop = document.getElementById('mobile-drawer-backdrop');
  const closeBtn = document.getElementById('mobile-drawer-close');

  if (!btn || !drawer) return;

  function openDrawer() {
    drawer.classList.add('open');
    btn.setAttribute('aria-expanded', 'true');
    document.body.style.overflow = 'hidden';
  }

  function closeDrawer() {
    drawer.classList.remove('open');
    btn.setAttribute('aria-expanded', 'false');
    document.body.style.overflow = '';
  }

  btn.addEventListener('click', openDrawer);
  if (backdrop) backdrop.addEventListener('click', closeDrawer);
  if (closeBtn) closeBtn.addEventListener('click', closeDrawer);

  drawer.querySelectorAll('.mobile-drawer-link').forEach((link) => {
    link.addEventListener('click', () => {
      closeDrawer();
      const page = link.dataset.page;
      if (page) showPage(page);
    });
  });
}

/* ── Bottom sheet ── */
function initBottomSheet() {
  const trigger = document.getElementById('mobile-sheet-trigger');
  const sheet = document.getElementById('bottom-sheet');
  const backdrop = document.getElementById('bottom-sheet-backdrop');
  const closeBtn = document.getElementById('bottom-sheet-close');

  if (!trigger || !sheet) return;

  function openSheet() {
    sheet.classList.add('open');
    trigger.setAttribute('aria-expanded', 'true');
  }

  function closeSheet() {
    sheet.classList.remove('open');
    trigger.setAttribute('aria-expanded', 'false');
  }

  trigger.addEventListener('click', openSheet);
  if (backdrop) backdrop.addEventListener('click', closeSheet);
  if (closeBtn) closeBtn.addEventListener('click', closeSheet);
}

function initUI() {
  initMobileNav();
  initBottomSheet();
  updateWritingScore(0, 0, 0);
}

/**
 * Show non-blocking document operation toast
 * @param {string} message
 * @param {'success'|'error'|'info'} type
 */
function showDocToast(message, type = 'info') {
  let toast = document.getElementById('doc-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'doc-toast';
    toast.className = 'doc-toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = `doc-toast doc-toast--${type} is-visible`;
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => toast.classList.remove('is-visible'), 3500);
}

/**
 * Show/hide analysis length warning banner
 * @param {boolean} show
 */
function updateAnalysisLimitBanner(show) {
  const banner = document.getElementById('analysis-limit-banner');
  if (!banner) return;
  if (show) {
    banner.classList.remove('is-hidden');
    banner.textContent = 'النص أطول من الحد المسموح للتحليل. سيتم تحليل أول 5000 حرف فقط.';
  } else {
    banner.classList.add('is-hidden');
  }
}
