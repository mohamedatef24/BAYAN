/**
 * Bayan — Inline Analysis Engine (Phase 7.1 Simplified)
 *
 * Dependencies: BayanController (analysis-controller.js)
 * State: local variables only (no external state manager)
 *
 * Architecture:
 *   1. DETECTION — find editable fields
 *   2. ANALYSIS  — debounced via BayanController → background.js
 *   3. OVERLAY   — highlights, tooltip, FAB (never modifies user DOM content)
 *
 * Safety:
 *   - Overlay-only rendering for ALL field types (never replaces innerHTML of user content)
 *   - Trusted Types for Gmail/Google Sites
 *   - Error boundary with graceful pause
 *   - Protected sites: disable contenteditable on Gmail/Docs/Notion
 */

(function () {
  'use strict';

  if (window.location.protocol === 'chrome-extension:') return;

  if (typeof BayanController === 'undefined') {
    console.error('[Bayan] BayanController not loaded.');
    return;
  }

  // ══════════════════════════════════════════════════════════
  // Trusted Types
  // ══════════════════════════════════════════════════════════
  let ttPolicy = null;
  try {
    if (window.trustedTypes?.createPolicy) {
      ttPolicy = window.trustedTypes.createPolicy('bayan-inline-policy', {
        createHTML: (input) => input,
      });
    }
  } catch {}

  function safeHTML(el, html) {
    try {
      el.innerHTML = ttPolicy ? ttPolicy.createHTML(html) : html;
    } catch {
      el.textContent = '';
      const t = document.createElement('template');
      t.innerHTML = html;
      el.appendChild(t.content.cloneNode(true));
    }
  }

  // ══════════════════════════════════════════════════════════
  // Local state (replaces BayanState — simpler, no extra file)
  // ══════════════════════════════════════════════════════════
  const IS_PROTECTED = BayanController.isProtectedSite();

  let activeField = null;
  let lastInteractedField = null; // persists after focus moves to side panel (Change 1)
  let pendingSelection = null;    // selection captured on right-click, for selection-only write-back
  let analysisSuppressed = false; // true after a non-correction model write-back (Change 3)
  let lastAnalyzedText = '';
  let suggestions = [];
  let paused = false;
  let analysisInProgress = false;
  const dismissedKeys = new Set();
  let floatingBtn = null;
  let tooltip = null;
  let overlayContainer = null;
  let badgeCount = null;
  let observer = null;
  let ancestorScrollCleanups = [];

  // ── Ghost-text autocomplete state ──
  let ghostEl = null;            // the ghost overlay element
  let ghostSuggestion = '';      // pending completion string (suffix to insert)
  let ghostBaseText = '';        // field text the ghost was computed against
  let acDebounceTimer = null;
  const AC_DEBOUNCE_MS = 450;
  const AC_MIN_CONTEXT = 3;

  // ══════════════════════════════════════════════════════════
  // 1. DETECTION — universal editable field finder
  // ══════════════════════════════════════════════════════════

  function isEditableField(el) {
    if (!el?.tagName) return false;
    const tag = el.tagName.toLowerCase();
    if (tag === 'textarea') return true;
    if (tag === 'input') {
      const type = (el.type || '').toLowerCase();
      return ['text', 'search', 'url', ''].includes(type);
    }
    if (el.isContentEditable && !IS_PROTECTED) return true;
    if (!IS_PROTECTED && (el.getAttribute('role') === 'textbox' || el.getAttribute('aria-multiline') === 'true')) return true;
    return false;
  }

  function getFieldText(field) {
    if (!field) return '';
    const tag = field.tagName.toLowerCase();
    if (tag === 'textarea' || tag === 'input') return field.value || '';
    return field.innerText || field.textContent || '';
  }

  // ══════════════════════════════════════════════════════════
  // 2. ANALYSIS (delegates to BayanController)
  // ══════════════════════════════════════════════════════════

  function onFieldInput(e) {
    if (paused || !activeField) return;

    const isUserKeystroke = !!e && e.isTrusted === true;
    if (isUserKeystroke && analysisSuppressed) analysisSuppressed = false;
    if (isUserKeystroke) pendingSelection = null;
    if (isUserKeystroke) dismissedKeys.clear();

    const text = getFieldText(activeField);

    scheduleGhost();

    if (analysisSuppressed) {
      clearHighlights();
      updateBadge(0);
      analysisInProgress = false;
      syncModalIfVisible();
      return;
    }

    // Immediately clear stale highlights when text changes — the old overlay
    // was rendered for a different string and its offsets are invalid now.
    if (text !== lastAnalyzedText && overlayContainer) {
      clearHighlights();
    }

    if (!BayanController.hasArabic(text)) {
      suggestions = [];
      lastAnalyzedText = '';
      clearHighlights();
      updateBadge(0);
      analysisInProgress = false;
      syncModalIfVisible();
      return;
    }

    analysisInProgress = true;
    updateBadge(-1);
    syncModalIfVisible();

    BayanController.scheduleAnalysis(
      text,
      (result) => {
        try { onAnalysisResult(result); } catch (err) {
          console.warn('[Bayan] Callback error:', err.message);
          handleFailure('callback_error');
        }
      },
      () => getFieldText(activeField)
    );
  }

  function onAnalysisResult(data) {
    if (!activeField) return;
    analysisInProgress = false;

    if (!data) {
      updateBadge(0);
      syncModalIfVisible();
      return;
    }

    suggestions = (data.suggestions || []).filter(s => !dismissedKeys.has(suggestionKey(s)));
    lastAnalyzedText = data.original || getFieldText(activeField);
    updateBadge(suggestions.length);

    if (suggestions.length > 0) {
      renderOverlay(activeField, lastAnalyzedText, suggestions);
    } else {
      clearHighlights();
    }
    syncModalIfVisible();
  }

  // ══════════════════════════════════════════════════════════
  // 2b. GHOST-TEXT AUTOCOMPLETE (textarea / input only)
  //
  // Mirrors the field (transparent text) and paints the predicted
  // completion in muted grey right at the caret (end of text). Tab
  // accepts, Escape dismisses. Best-effort and fully isolated: it
  // never throws into the analysis path, and only ever appends to
  // the field value on explicit accept (never mutates while typing).
  // ══════════════════════════════════════════════════════════

  function ghostEligible() {
    if (!activeField || paused) return false;
    const tag = activeField.tagName.toLowerCase();
    if (tag !== 'textarea' && tag !== 'input') return false;
    const val = activeField.value || '';
    if (activeField.selectionStart !== val.length) return false;
    if (activeField.selectionEnd !== val.length) return false;
    if (val.trim().length < AC_MIN_CONTEXT) return false;
    if (!/[\s ]$/.test(val)) return false;
    return /[؀-ۿ]/.test(val);
  }

  function scheduleGhost() {
    // Any keystroke invalidates a previously shown ghost.
    clearGhost();
    if (!ghostEligible()) return;

    const ctx = activeField.value;
    acDebounceTimer = setTimeout(() => {
      acDebounceTimer = null;
      fetchGhost(ctx);
    }, AC_DEBOUNCE_MS);
  }

  async function fetchGhost(ctx) {
    let data;
    try {
      const res = await fetch(`${BAYAN.API_BASE}/api/autocomplete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: ctx, n: 1 }),
      });
      if (!res.ok) return;
      data = await res.json();
    } catch {
      return; // network error — silent (autocomplete is best-effort)
    }

    // Staleness: field changed or caret moved during the fetch.
    if (!activeField || activeField.value !== ctx || !ghostEligible()) return;

    const list = (data && data.suggestions) || [];
    const word = list.find((s) => s && s.trim());
    if (!word) return;

    // Insertion suffix: prepend a space when the context does not already end
    // with whitespace — mirrors the website's accept behaviour.
    const needsSpace = ctx.length > 0 && !/\s$/.test(ctx);
    ghostSuggestion = (needsSpace ? ' ' : '') + word.trim();
    ghostBaseText = ctx;
    showGhost(ctx, ghostSuggestion);
  }

  function showGhost(baseText, suffix) {
    if (ghostEl) { ghostEl.remove(); ghostEl = null; }
    if (!activeField || !suffix) return;

    try {
      const rect = activeField.getBoundingClientRect();
      const cs = window.getComputedStyle(activeField);
      const sbW = activeField.offsetWidth - activeField.clientWidth;

      ghostEl = document.createElement('div');
      ghostEl.className = 'bayan-il-ghost';
      ghostEl.style.cssText = `position:fixed;top:${rect.top}px;`
        + `left:${rect.left}px;width:${rect.width - sbW}px;height:${rect.height}px;`
        + `font-family:${cs.fontFamily};font-size:${cs.fontSize};line-height:${cs.lineHeight};`
        + `padding:${cs.padding};border:${cs.border};border-color:transparent;`
        + `direction:${cs.direction};text-align:${cs.textAlign};`
        + `unicode-bidi:${cs.unicodeBidi};letter-spacing:${cs.letterSpacing};`
        + `word-spacing:${cs.wordSpacing};text-indent:${cs.textIndent};`
        + `overflow:hidden;pointer-events:none;z-index:2147483645;box-sizing:border-box;`
        + `white-space:pre-wrap;word-wrap:break-word;color:transparent;`;

      const html = esc(baseText) + `<span class="bayan-il-ghost-suffix">${esc(suffix)}</span>`;
      safeHTML(ghostEl, html);
      ghostEl.scrollTop = activeField.scrollTop;
      ghostEl.scrollLeft = activeField.scrollLeft;
      document.body.appendChild(ghostEl);
    } catch (err) {
      console.warn('[Bayan] Ghost render error:', err.message);
      clearGhost();
    }
  }

  function acceptGhost() {
    if (!ghostSuggestion || !activeField) return false;
    const tag = activeField.tagName.toLowerCase();
    if (tag !== 'textarea' && tag !== 'input') return false;
    // Only accept if the field still matches what the ghost was computed for.
    if (activeField.value !== ghostBaseText) { clearGhost(); return false; }

    const suffix = ghostSuggestion;
    activeField.value = ghostBaseText + suffix;
    const end = activeField.value.length;
    try { activeField.setSelectionRange(end, end); } catch {}
    clearGhost();
    // Notify the page + our own pipeline (re-analysis + next-word ghost).
    activeField.dispatchEvent(new Event('input', { bubbles: true }));
    return true;
  }

  function clearGhost() {
    if (acDebounceTimer) { clearTimeout(acDebounceTimer); acDebounceTimer = null; }
    if (ghostEl) { ghostEl.remove(); ghostEl = null; }
    ghostSuggestion = '';
    ghostBaseText = '';
  }

  function syncGhostScroll() {
    if (ghostEl && activeField) {
      ghostEl.scrollTop = activeField.scrollTop;
      ghostEl.scrollLeft = activeField.scrollLeft;
    }
  }

  function onFieldKeydown(e) {
    if (!ghostSuggestion) return;
    if (e.key === 'Tab') {
      e.preventDefault();
      e.stopPropagation();
      acceptGhost();
    } else if (e.key === 'Escape') {
      clearGhost();
    }
  }

  // ══════════════════════════════════════════════════════════
  // Error boundary
  // ══════════════════════════════════════════════════════════

  function handleFailure(reason) {
    paused = true;
    analysisInProgress = false;
    clearHighlights();
    BayanController.cancelAll();
    if (badgeCount) {
      badgeCount.textContent = '⏸';
      badgeCount.className = 'bayan-il-badge bayan-il-badge--paused';
    }
    console.warn(`[Bayan] Inline paused: ${reason}. Side Panel still works.`);
  }

  // ══════════════════════════════════════════════════════════
  // 3. OVERLAY — always overlay, never modify user content
  //
  // Task 10: ALL field types use overlay rendering.
  // This prevents formatting destruction on Medium, Slack,
  // WordPress, Ghost, Discourse, etc.
  // ══════════════════════════════════════════════════════════

  function renderOverlay(field, originalText, suggs) {
    clearHighlights();
    if (!field || !suggs?.length) return;

    const currentText = getFieldText(field);
    if (currentText !== originalText) return;

    try {
      const rect = field.getBoundingClientRect();
      const cs = window.getComputedStyle(field);
      const sbW = field.offsetWidth - field.clientWidth;

      overlayContainer = document.createElement('div');
      overlayContainer.className = 'bayan-il-overlay';
      overlayContainer.style.cssText = `position:fixed;top:${rect.top}px;`
        + `left:${rect.left}px;width:${rect.width - sbW}px;height:${rect.height}px;`
        + `font-family:${cs.fontFamily};font-size:${cs.fontSize};line-height:${cs.lineHeight};`
        + `padding:${cs.padding};border:${cs.border};border-color:transparent;`
        + `direction:${cs.direction};text-align:${cs.textAlign};`
        + `unicode-bidi:${cs.unicodeBidi};letter-spacing:${cs.letterSpacing};`
        + `word-spacing:${cs.wordSpacing};text-indent:${cs.textIndent};`
        + `overflow:hidden;pointer-events:none;z-index:2147483645;box-sizing:border-box;`
        + `white-space:pre-wrap;word-wrap:break-word;color:transparent;`;

      const sorted = [...suggs].sort((a, b) => a.start - b.start);
      let html = '';
      let pos = 0;

      sorted.forEach((s) => {
        if (pos < s.start) html += esc(originalText.slice(pos, s.start));
        html += `<span class="${errCls(s.type)} bayan-il-error bayan-il-overlay-mark" `
          + `data-bayan-sid="${s.id || ''}" data-bayan-original="${esc(s.original)}" `
          + `data-bayan-correction="${esc(s.correction)}" data-bayan-type="${s.type}" `
          + `data-bayan-start="${s.start}" data-bayan-end="${s.end}" `
          + `style="pointer-events:auto;cursor:pointer;">`
          + `${esc(originalText.slice(s.start, s.end))}</span>`;
        pos = s.end;
      });
      if (pos < originalText.length) html += esc(originalText.slice(pos));

      safeHTML(overlayContainer, html);
      overlayContainer.scrollTop = field.scrollTop;
      overlayContainer.scrollLeft = field.scrollLeft;
      document.body.appendChild(overlayContainer);

      overlayContainer.addEventListener('mousedown', (e) => e.preventDefault());

      field.addEventListener('scroll', syncOverlay);

      overlayContainer.querySelectorAll('.bayan-il-overlay-mark').forEach((mark) => {
        mark.addEventListener('click', (e) => {
          e.stopPropagation();
          showTooltip(mark, activeField);
        });
      });
    } catch (err) {
      console.warn('[Bayan] Overlay error:', err.message);
      handleFailure('render_error');
    }
  }

  function syncOverlay() {
    if (overlayContainer && activeField) {
      overlayContainer.scrollTop = activeField.scrollTop;
      overlayContainer.scrollLeft = activeField.scrollLeft;
    }
    syncGhostScroll();
  }

  function repositionOverlay() {
    if (!activeField) return;
    const rect = activeField.getBoundingClientRect();
    const sbW = activeField.offsetWidth - activeField.clientWidth;
    if (overlayContainer) {
      overlayContainer.style.top = `${rect.top}px`;
      overlayContainer.style.left = `${rect.left}px`;
      overlayContainer.style.width = `${rect.width - sbW}px`;
      overlayContainer.style.height = `${rect.height}px`;
      overlayContainer.scrollTop = activeField.scrollTop;
      overlayContainer.scrollLeft = activeField.scrollLeft;
    }
    if (ghostEl) {
      ghostEl.style.top = `${rect.top}px`;
      ghostEl.style.left = `${rect.left}px`;
      ghostEl.style.width = `${rect.width - sbW}px`;
      ghostEl.style.height = `${rect.height}px`;
      ghostEl.scrollTop = activeField.scrollTop;
      ghostEl.scrollLeft = activeField.scrollLeft;
    }
    if (floatingBtn) positionFab(activeField);
  }

  function watchAncestorScroll(field) {
    unwatchAncestorScroll();
    let el = field.parentElement;
    while (el && el !== document.body) {
      const ov = window.getComputedStyle(el).overflowY;
      if (ov === 'auto' || ov === 'scroll' || ov === 'overlay') {
        const handler = () => repositionOverlay();
        el.addEventListener('scroll', handler, { passive: true });
        const ref = el;
        ancestorScrollCleanups.push(() => ref.removeEventListener('scroll', handler));
      }
      el = el.parentElement;
    }
  }

  function unwatchAncestorScroll() {
    ancestorScrollCleanups.forEach((fn) => fn());
    ancestorScrollCleanups = [];
  }

  function clearHighlights() {
    if (overlayContainer) { overlayContainer.remove(); overlayContainer = null; }
    hideTooltip();
  }

  // ══════════════════════════════════════════════════════════
  // Tooltip
  // ══════════════════════════════════════════════════════════

  function showTooltip(el, field) {
    hideTooltip();

    const original = el.dataset.bayanOriginal;
    const correction = el.dataset.bayanCorrection;
    const type = el.dataset.bayanType;
    const start = parseInt(el.dataset.bayanStart, 10);
    const end = parseInt(el.dataset.bayanEnd, 10);
    const sid = el.dataset.bayanSid;

    if (!original || !correction) return;

    const suggestion = { id: sid, original, correction, type, start, end };
    const typeLabels = { spelling: 'خطأ إملائي', grammar: 'خطأ نحوي', punctuation: 'علامات ترقيم' };

    tooltip = document.createElement('div');
    tooltip.setAttribute('data-bayan-theme', currentBayanTheme);
    tooltip.className = 'bayan-il-suggestion-popover bayan-il-show';
    tooltip.dir = 'rtl';

    const typeLabel = typeLabels[type] || type;
    const typeClass = type === 'spelling' ? 'bayan-il-popover-type--spelling' : type === 'grammar' ? 'bayan-il-popover-type--grammar' : 'bayan-il-popover-type--punctuation';

    safeHTML(tooltip, `
        <div class="bayan-il-popover-type ${typeClass}">${typeLabel}</div>
        <div class="bayan-il-popover-original-word">
          <span class="bayan-il-popover-label">الكلمة:</span>
          <span class="bayan-il-tooltip-original">${esc(original)}</span>
          <span class="bayan-il-popover-arrow">←</span>
          <span class="bayan-il-popover-correction">${correction ? esc(correction) : '<s style="opacity:0.5">حذف</s>'}</span>
        </div>
        <div class="bayan-il-popover-alternatives">
          <button class="bayan-il-popover-alt-btn bayan-il-popover-alt-main" data-action="apply">
            ${correction ? '✓ ' + esc(correction) : '<s style="opacity:0.5">حذف</s>'}
          </button>
        </div>
        <button type="button" class="bayan-il-popover-dismiss" data-action="ignore" title="تجاهل هذا الاقتراح">تجاهل</button>
        <p class="bayan-il-popover-hint">اختر التصحيح المناسب · Escape للإغلاق</p>
    `);

    document.body.appendChild(tooltip);

    const r = el.getBoundingClientRect();
    tooltip.style.top = `${r.bottom + window.scrollY + 6}px`;
    tooltip.style.left = `${r.left + window.scrollX}px`;

    requestAnimationFrame(() => {
      if (!tooltip) return;
      const tr = tooltip.getBoundingClientRect();
      // U1: clamp horizontally (right edge) and to the left edge if it overflows.
      if (tr.right > window.innerWidth) tooltip.style.left = `${window.innerWidth - tr.width - 8}px`;
      if (tr.left < 0) tooltip.style.left = `${window.scrollX + 8}px`;
      // U1: clamp vertically — if the tooltip overflows the bottom of the
      // viewport, flip it above the highlighted mark instead of below.
      if (tr.bottom > window.innerHeight) {
        const flippedTop = r.top + window.scrollY - tr.height - 6;
        // Only flip if there's room above; otherwise pin to the top edge.
        tooltip.style.top = flippedTop > window.scrollY
          ? `${flippedTop}px`
          : `${window.scrollY + 8}px`;
      }
      tooltip.classList.add('bayan-il-tooltip--visible');
    });

    tooltip.querySelector('[data-action="apply"]').addEventListener('click', () => {
      applyFix(field, suggestion);
      hideTooltip();
    });

    tooltip.querySelector('.bayan-il-popover-dismiss').addEventListener('click', () => {
      dismissSuggestion(suggestion);
      hideTooltip();
    });

    setTimeout(() => document.addEventListener('click', outsideClick, { once: true }), 100);

    const escHandler = (e) => {
      if (e.key === 'Escape') { hideTooltip(); document.removeEventListener('keydown', escHandler); }
    };
    document.addEventListener('keydown', escHandler);
  }

  function outsideClick(e) {
    if (tooltip && !tooltip.contains(e.target)) hideTooltip();
  }

  function hideTooltip() {
    if (tooltip) { tooltip.remove(); tooltip = null; }
  }

  // ══════════════════════════════════════════════════════════
  // Fix application (overlay-only: modify field value, re-render overlay)
  // ══════════════════════════════════════════════════════════

  function applyFix(field, suggestion) {
    if (!field) return;

    const isInput = field.tagName.toLowerCase() === 'textarea' || field.tagName.toLowerCase() === 'input';
    const text = isInput ? field.value : getFieldText(field);
    const before = text.substring(0, suggestion.start);
    const after = text.substring(suggestion.end);
    const newText = before + suggestion.correction + after;

    const delta = suggestion.correction.length - (suggestion.end - suggestion.start);
    suggestions = suggestions
      .filter((s) => s.id !== suggestion.id)
      .map((s) => s.start >= suggestion.end ? { ...s, start: s.start + delta, end: s.end + delta } : s);

    lastAnalyzedText = newText;

    if (isInput) {
      field.value = newText;
      field.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
      // FIX-17: Use textContent instead of innerText for better compatibility
      // This preserves the DOM structure better than innerText assignment
      field.textContent = newText;
    }

    if (suggestions.length > 0) {
      renderOverlay(field, newText, suggestions);
    } else {
      clearHighlights();
      // FIX-21: Trigger re-analysis after applying last fix
      // This catches any remaining errors that were masked by the fixed one
      setTimeout(() => onFieldInput(), 500);
    }
    updateBadge(suggestions.length);
  }

  function suggestionKey(s) {
    return s.original + '|' + (s.correction || '') + '|' + s.type;
  }

  function dismissSuggestion(suggestion) {
    dismissedKeys.add(suggestionKey(suggestion));
    suggestions = suggestions.filter((s) => s.id !== suggestion.id);
    if (suggestions.length > 0) {
      renderOverlay(activeField, lastAnalyzedText, suggestions);
    } else {
      clearHighlights();
    }
    updateBadge(suggestions.length);
  }

  // ══════════════════════════════════════════════════════════
  // UI: FAB + Badge
  // ══════════════════════════════════════════════════════════

  // ── Draggable FAB state ──
  let fabDragging = false;
  let fabDragStartX = 0;
  let fabDragStartY = 0;
  let fabDragOffsetX = 0;
  let fabDragOffsetY = 0;
  let fabCustomPos = null; // {x, y} when user has dragged to a custom position
  let modalCustomPos = null; // {x, y} when user drags the modal

  function loadFabPosition() {
    try {
      const saved = localStorage.getItem('bayan_fab_pos');
      if (saved) fabCustomPos = JSON.parse(saved);
    } catch {}
  }

  function saveFabPosition() {
    try {
      if (fabCustomPos) localStorage.setItem('bayan_fab_pos', JSON.stringify(fabCustomPos));
    } catch {}
  }

  function createFloatingBtn() {
    if (floatingBtn) return;

    loadFabPosition();

    floatingBtn = document.createElement('div');
      floatingBtn.setAttribute('data-bayan-theme', currentBayanTheme);
    floatingBtn.className = 'bayan-il-fab';
    const fabLogoUrl = chrome.runtime.getURL('assets/icons/fab_logo.png');
    safeHTML(floatingBtn, `
      <img src="${fabLogoUrl}" alt="بيان" draggable="false" style="width: 100%; height: 100%; object-fit: cover; border-radius: 50%; display: block; pointer-events: none;" />
      <span class="bayan-il-badge">0</span>
    `);
    floatingBtn.title = 'Bayan — بيان';
    document.body.appendChild(floatingBtn);
    badgeCount = floatingBtn.querySelector('.bayan-il-badge');

    // ── Drag handling ──
    floatingBtn.addEventListener('pointerdown', (e) => {
      fabDragging = false;
      fabDragStartX = e.clientX;
      fabDragStartY = e.clientY;
      const rect = floatingBtn.getBoundingClientRect();
      fabDragOffsetX = e.clientX - rect.left;
      fabDragOffsetY = e.clientY - rect.top;
      floatingBtn.setPointerCapture(e.pointerId);
    });

    floatingBtn.addEventListener('pointermove', (e) => {
      if (!floatingBtn.hasPointerCapture(e.pointerId)) return;
      const dx = e.clientX - fabDragStartX;
      const dy = e.clientY - fabDragStartY;
      if (!fabDragging && (Math.abs(dx) > 4 || Math.abs(dy) > 4)) {
        fabDragging = true;
        floatingBtn.classList.add('bayan-il-fab--dragging');
      }
      if (fabDragging) {
        const x = Math.max(0, Math.min(window.innerWidth - 40, e.clientX - fabDragOffsetX));
        const y = Math.max(0, Math.min(window.innerHeight - 40, e.clientY - fabDragOffsetY));
        floatingBtn.style.position = 'fixed';
        floatingBtn.style.left = `${x}px`;
        floatingBtn.style.top = `${y}px`;
      }
    });

    floatingBtn.addEventListener('pointerup', (e) => {
      floatingBtn.releasePointerCapture(e.pointerId);
      if (fabDragging) {
        fabDragging = false;
        floatingBtn.classList.remove('bayan-il-fab--dragging');
        fabCustomPos = {
          x: parseInt(floatingBtn.style.left, 10),
          y: parseInt(floatingBtn.style.top, 10),
        };
        saveFabPosition();
        return;
      }
      // Click (no drag)
      e.stopPropagation();
      if (paused) {
        paused = false;
        updateBadge(0);
        onFieldInput();
        return;
      }
      showModal();
    });
  }

  function positionFab(field) {
    if (!floatingBtn || !field) return;
    if (fabCustomPos) {
      floatingBtn.style.position = 'fixed';
      floatingBtn.style.left = `${fabCustomPos.x}px`;
      floatingBtn.style.top = `${fabCustomPos.y}px`;
    } else {
      const rect = field.getBoundingClientRect();
      floatingBtn.style.position = 'fixed';
      floatingBtn.style.top = `${Math.max(4, rect.top + 6)}px`;
      floatingBtn.style.left = `${Math.max(4, rect.left + 6)}px`;
    }
    floatingBtn.classList.add('bayan-il-fab--visible');
  }

  function updateBadge(count) {
    if (!badgeCount) return;
    if (count === -1) {
      badgeCount.textContent = '…';
      badgeCount.className = 'bayan-il-badge bayan-il-badge--analyzing';
    } else if (count === 0) {
      badgeCount.textContent = '✓';
      badgeCount.className = 'bayan-il-badge bayan-il-badge--clean';
    } else {
      badgeCount.textContent = String(count);
      badgeCount.className = 'bayan-il-badge bayan-il-badge--errors';
    }
  }

  // ══════════════════════════════════════════════════════════
  // Utilities
  // ══════════════════════════════════════════════════════════

  function esc(text) {
    const m = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, (c) => m[c]);
  }

  function errCls(type) {
    return { spelling: 'bayan-il-spelling', grammar: 'bayan-il-grammar', punctuation: 'bayan-il-punctuation' }[type] || 'bayan-il-spelling';
  }

  // ══════════════════════════════════════════════════════════
  // Field lifecycle (Task 7: no listener tracking leak)
  //
  // Per-field listeners use direct add/remove (NOT _trackedListeners).
  // Global listeners use addEventListener directly (cleaned on unload).
  // ══════════════════════════════════════════════════════════

  function attachField(field) {
    if (activeField === field) return;
    detachField();

    activeField = field;
    lastInteractedField = field; // persists for write-back even after the panel takes focus
    suggestions = [];
    if (paused) paused = false;

    createFloatingBtn();
    positionFab(field);

    field.addEventListener('input', onFieldInput);
    field.addEventListener('keydown', onFieldKeydown);
    // Track the user's selection within the field so a later "apply" from the
    // side panel can splice the result into exactly that range — even when the
    // panel was opened via the FAB or was already open (not just right-click).
    field.addEventListener('mouseup', onFieldSelect);
    field.addEventListener('keyup', onFieldSelect);
    field.addEventListener('select', onFieldSelect);
    // FIX-20: Removed redundant 'keyup' listener (input event already fires on every change)

    watchAncestorScroll(field);

    if (BayanController.hasArabic(getFieldText(field))) {
      onFieldInput();
    }
  }

  function detachField() {
    if (activeField) {
      activeField.removeEventListener('input', onFieldInput);
      activeField.removeEventListener('keydown', onFieldKeydown);
      activeField.removeEventListener('mouseup', onFieldSelect);
      activeField.removeEventListener('keyup', onFieldSelect);
      activeField.removeEventListener('select', onFieldSelect);
      // FIX-20: keyup listener no longer attached
      activeField.removeEventListener('scroll', syncOverlay);
    }
    unwatchAncestorScroll();
    clearHighlights();
    clearGhost();
    BayanController.cancelAll();
    activeField = null;
    suggestions = [];
    if (floatingBtn) floatingBtn.classList.remove('bayan-il-fab--visible');
  }

  // ══════════════════════════════════════════════════════════
  // Write-back from the side panel (Change 1)
  //
  // The side panel cannot touch page DOM, so it relays text through
  // background.js → here. We write into the source field and dispatch
  // a synthetic `input` event so the host page registers the change.
  // For non-correction sources (summarize/dialect/quran) we set the
  // suppression flag first (Change 3) so the corrected/model output is
  // NOT immediately re-analyzed.
  // ══════════════════════════════════════════════════════════

  const NON_CORRECTION_SOURCES = ['summarize', 'dialect', 'quran'];

  // Snapshot the active field's selection whenever the user changes it. We keep
  // the LAST non-empty selection so that when focus later moves to the side
  // panel (which collapses the field's visible selection) we still know which
  // range the user meant to replace. A collapsed selection does NOT clear the
  // snapshot — only a real edit (handled in onFieldInput) or a fresh write does.
  function onFieldSelect(e) {
    const field = e && e.currentTarget;
    if (!field) return;
    const tag = field.tagName.toLowerCase();
    if (tag !== 'textarea' && tag !== 'input') return;
    const start = field.selectionStart;
    const end = field.selectionEnd;
    if (typeof start === 'number' && typeof end === 'number' && start !== end) {
      pendingSelection = { field, type: 'input', start, end };
      lastInteractedField = field;
    }
  }

  // Capture the field + selection range at right-click time. The context menu
  // flow always acts on the selected text, so we remember exactly what was
  // selected and splice the result into THAT range on write-back (Bug 2).
  function captureSelection(target) {
    const winSel = window.getSelection();

    // Prefer the already-tracked editable field (it's what write-back resolves
    // via lastInteractedField); fall back to the right-clicked target. For
    // contenteditable this avoids latching onto a child node of the root.
    let field = null;
    const tracked = lastInteractedField
      || (isEditableField(document.activeElement) ? document.activeElement : null);
    if (tracked) {
      const ttag = tracked.tagName.toLowerCase();
      if (ttag === 'textarea' || ttag === 'input') field = tracked;
      else if (tracked.isContentEditable && winSel && winSel.rangeCount > 0
        && tracked.contains(winSel.anchorNode)) field = tracked;
    }
    if (!field && isEditableField(target)) field = target;
    if (!field) { pendingSelection = null; return; }

    const tag = field.tagName.toLowerCase();
    if (tag === 'textarea' || tag === 'input') {
      const start = field.selectionStart;
      const end = field.selectionEnd;
      if (typeof start === 'number' && typeof end === 'number' && start !== end) {
        pendingSelection = { field, type: 'input', start, end };
      } else {
        pendingSelection = null;
      }
    } else if (field.isContentEditable) {
      if (winSel && winSel.rangeCount > 0 && !winSel.isCollapsed && field.contains(winSel.anchorNode)) {
        pendingSelection = { field, type: 'ce', range: winSel.getRangeAt(0).cloneRange() };
      } else {
        pendingSelection = null;
      }
    } else {
      pendingSelection = null;
    }

    // Persist a link to the field so write-back can re-find it after focus
    // moves to the side panel, even when this was a plain right-click.
    if (pendingSelection) {
      lastInteractedField = field;
      try { field.dataset.bayanSource = '1'; } catch {}
    }
  }

  document.addEventListener('contextmenu', (e) => {
    try { captureSelection(e.target); } catch { pendingSelection = null; }
  }, true);

  function writeTextToField(field, text, mode, source, find) {
    if (!field || typeof text !== 'string') return;

    const tag = field.tagName.toLowerCase();
    const suppress = NON_CORRECTION_SOURCES.includes(source);

    // ── find anchor: if the caller passed the original selected text, try to
    // locate it inside the field and replace ONLY that occurrence. This is the
    // most reliable way to scope a context-menu correction to the user's
    // selection — it survives focus loss and timing gaps.
    if (find && typeof find === 'string' && find.length > 0) {
      if (tag === 'textarea' || tag === 'input') {
        const idx = field.value.indexOf(find);
        if (idx !== -1) {
          const before = field.value.slice(0, idx);
          const after = field.value.slice(idx + find.length);
          field.value = before + text + after;
          const caret = idx + text.length;
          try { field.setSelectionRange(caret, caret); } catch {}
          if (suppress) analysisSuppressed = true;
          field.dispatchEvent(new Event('input', { bubbles: true }));
          pendingSelection = null;
          try { delete field.dataset.bayanSource; } catch {}
          return;
        }
      } else if (field.isContentEditable) {
        const content = field.innerText || field.textContent || '';
        const idx = content.indexOf(find);
        if (idx !== -1) {
          field.focus();
          const treeWalker = document.createTreeWalker(field, NodeFilter.SHOW_TEXT);
          let charCount = 0;
          let startNode = null, startOffset = 0, endNode = null, endOffset = 0;
          while (treeWalker.nextNode()) {
            const node = treeWalker.currentNode;
            const nodeLen = node.textContent.length;
            if (!startNode && charCount + nodeLen > idx) {
              startNode = node;
              startOffset = idx - charCount;
            }
            if (startNode && charCount + nodeLen >= idx + find.length) {
              endNode = node;
              endOffset = idx + find.length - charCount;
              break;
            }
            charCount += nodeLen;
          }
          if (startNode && endNode) {
            try {
              const range = document.createRange();
              range.setStart(startNode, startOffset);
              range.setEnd(endNode, endOffset);
              const winSel = window.getSelection();
              winSel.removeAllRanges();
              winSel.addRange(range);
              range.deleteContents();
              range.insertNode(document.createTextNode(text));
              winSel.collapseToEnd();
              if (suppress) analysisSuppressed = true;
              field.dispatchEvent(new Event('input', { bubbles: true }));
              pendingSelection = null;
              try { delete field.dataset.bayanSource; } catch {}
              return;
            } catch {}
          }
        }
      }
    }

    // Resolve the effective mode. 'auto' = replace the captured selection if we
    // have one for THIS field, otherwise replace the whole field.
    const sel = (pendingSelection && pendingSelection.field === field) ? pendingSelection : null;
    let effectiveMode = mode;
    if (mode === 'auto') effectiveMode = sel ? 'replaceSelection' : 'replaceAll';

    if (tag === 'textarea' || tag === 'input') {
      if (effectiveMode === 'replaceSelection' && sel && sel.type === 'input') {
        const before = field.value.slice(0, sel.start);
        const after = field.value.slice(sel.end);
        field.value = before + text + after;
        const caret = sel.start + text.length;
        try { field.setSelectionRange(caret, caret); } catch {}
      } else if (effectiveMode === 'replaceSelection'
        && typeof field.selectionStart === 'number'
        && field.selectionStart !== field.selectionEnd) {
        // Live selection still present (no captured range) — splice into it.
        const start = field.selectionStart;
        const end = field.selectionEnd;
        field.value = field.value.slice(0, start) + text + field.value.slice(end);
        const caret = start + text.length;
        try { field.setSelectionRange(caret, caret); } catch {}
      } else {
        field.value = text;
        const caret = field.value.length;
        try { field.setSelectionRange(caret, caret); } catch {}
      }
      // Set suppression BEFORE dispatching so onFieldInput sees it.
      if (suppress) analysisSuppressed = true;
      field.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
      // contenteditable — mirror the overlay-safe approach used by applyFix.
      field.focus();
      if (effectiveMode === 'replaceSelection' && sel && sel.type === 'ce') {
        // Restore the captured range, then replace its contents with the text.
        try {
          const winSel = window.getSelection();
          winSel.removeAllRanges();
          winSel.addRange(sel.range);
          sel.range.deleteContents();
          sel.range.insertNode(document.createTextNode(text));
          winSel.collapseToEnd();
        } catch {
          field.textContent = text;
        }
        if (suppress) analysisSuppressed = true;
        field.dispatchEvent(new Event('input', { bubbles: true }));
      } else if (effectiveMode === 'replaceSelection') {
        const winSel = window.getSelection();
        const hasLive = winSel && winSel.rangeCount > 0 && !winSel.isCollapsed && field.contains(winSel.anchorNode);
        if (hasLive) {
          winSel.getRangeAt(0).deleteContents();
          winSel.getRangeAt(0).insertNode(document.createTextNode(text));
        } else {
          field.textContent = text;
        }
        if (suppress) analysisSuppressed = true;
        field.dispatchEvent(new Event('input', { bubbles: true }));
      } else {
        field.textContent = text;
        if (suppress) analysisSuppressed = true;
        field.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }

    // Consume the captured selection + source tag now that the write succeeded.
    pendingSelection = null;
    try { delete field.dataset.bayanSource; } catch {}
  }

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg && msg.type === 'BAYAN_WRITE_BACK') {
      const field = lastInteractedField
        || document.querySelector('[data-bayan-source="1"]')
        || (isEditableField(document.activeElement) ? document.activeElement : null);
      // With all_frames:true this listener runs in every frame. A frame that
      // doesn't own the source field stays SILENT (return false, no response)
      // so it can't win the response race against the frame that does.
      if (!field) return false;
      try {
        writeTextToField(field, msg.text, msg.mode, msg.source, msg.find);
        sendResponse({ ok: true });
      } catch (err) {
        console.warn('[Bayan] Write-back error:', err.message);
        sendResponse({ ok: false, reason: 'write_error' });
      }
      return true;
    }
    return false;
  });

  // ══════════════════════════════════════════════════════════
  // Global listeners
  // ══════════════════════════════════════════════════════════

  document.addEventListener('focusin', (e) => {
    if (isEditableField(e.target)) attachField(e.target);
  }, true);

  document.addEventListener('focusout', () => {
    setTimeout(() => {
      if (!activeField) return;
      if (document.activeElement === activeField) return;
      const a = document.activeElement;
      if (tooltip?.contains(a)) return;
      if (floatingBtn?.contains(a)) return;
      if (overlayContainer?.contains(a)) return;
      if (modalPanel?.contains(a)) return;
      if (modalPanel?.contains(a)) return;
      if (document.querySelector('.bayan-il-tooltip')) return;
      if (document.querySelector('.bayan-il-suggestion-popover')) return;
      if (isEditableField(a)) return;
      BayanController.cancelAll();
      clearGhost();
    }, 300);
  }, true);

  window.addEventListener('scroll', () => {
    repositionOverlay();
  }, true);

  window.addEventListener('resize', () => {
    repositionOverlay();
    if (overlayContainer && activeField && suggestions.length > 0) {
      renderOverlay(activeField, lastAnalyzedText, suggestions);
    }
  }, { passive: true });

  // ── MutationObserver — detect removed fields AND newly added editable areas ──
  observer = new MutationObserver((mutations) => {
    if (activeField && !document.body.contains(activeField)) detachField();
    for (const m of mutations) {
      if (m.type !== 'childList') continue;
      for (const node of m.addedNodes) {
        if (node.nodeType !== 1) continue;
        if (isEditableField(node) && document.activeElement === node) {
          attachField(node);
          return;
        }
        const nested = node.querySelectorAll?.('textarea, input, [contenteditable="true"], [role="textbox"]');
        if (nested) {
          for (const el of nested) {
            if (isEditableField(el) && document.activeElement === el) {
              attachField(el);
              return;
            }
          }
        }
      }
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });

  // ── Log ──
  const mode = IS_PROTECTED ? 'protected' : 'full';
  console.log(`[Bayan] Inline engine v7.1 (mode: ${mode}, TT: ${ttPolicy ? 'yes' : 'no'})`);


  // ══════════════════════════════════════════════════════════
  // Modal Dialog — Full Analysis Panel
  // ══════════════════════════════════════════════════════════

  let modalPanel = null;

  const TYPE_LABELS = { spelling: 'إملائي', grammar: 'نحوي', punctuation: 'ترقيم' };
  const SCORE_CIRCUMFERENCE = 440;

  function calculateWritingScore(spelling, grammar, punctuation) {
    const raw = 100 - spelling * 8 - grammar * 6 - punctuation * 3;
    return Math.max(0, Math.min(100, raw));
  }

  function getScoreHint(score) {
    if (score >= 90) return 'كتابة ممتازة! استمر.';
    if (score >= 70) return 'جيد — راجع الاقتراحات لتحسين النص.';
    return 'يحتاج النص إلى بعض التحسينات.';
  }

  function resolveAlternatives(s) {
    if (s.alternatives && s.alternatives.length > 0) return s.alternatives;
    const alts = [];
    if (s.correction) alts.push(s.correction);
    alts.push(s.original);
    return alts;
  }

  function createModal() {
    if (modalPanel) return;

    modalPanel = document.createElement('div');
    modalPanel.className = 'bayan-il-modal-panel';
    modalPanel.setAttribute('data-bayan-theme', currentBayanTheme);
    modalPanel.dir = 'rtl';

    safeHTML(modalPanel, `
      <div class="bayan-il-modal-top-bar" id="bayan-modal-drag-handle">
        <div class="bayan-il-modal-brand">
           <a href="https://bayan10-bayan-api.hf.space/" target="_blank" rel="noopener noreferrer" class="bayan-il-modal-logo-link">
             <img src="${chrome.runtime.getURL('assets/icons/icon48.png')}" alt="بيان" style="width: 28px; height: 28px; object-fit: contain; border-radius: 6px;" draggable="false" />
           </a>
           <div class="bayan-il-header-divider"></div>
           <span class="bayan-il-modal-title">بيان</span>
        </div>
        <div class="bayan-il-modal-header-actions">
          <button id="bayan-modal-theme-toggle" class="bayan-il-modal-theme-toggle" type="button" title="تبديل السمة">
            <svg class="bayan-il-theme-icon-sun" width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
            <svg class="bayan-il-theme-icon-moon" width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>
          </button>
          <button class="bayan-il-modal-close" title="إغلاق"><svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg></button>
        </div>
      </div>

      <div class="bayan-il-modal-body-scroll">
        <div class="bayan-il-modal-sugg-card">
          <h3 class="bayan-il-modal-section-title">الاقتراحات</h3>
          <div id="bayan-modal-cards" class="bayan-il-modal-cards" role="list" aria-live="polite" aria-label="اقتراحات التصحيح"></div>
          <button id="bayan-modal-apply-all" class="bayan-il-modal-apply-all" style="display:none;" type="button">تطبيق الكل</button>
        </div>

        <div class="bayan-il-modal-score-card">
          <h3 class="bayan-il-modal-section-title">تقييم الكتابة</h3>
          <div class="bayan-il-modal-score-ring" role="img" aria-label="تقييم الكتابة">
            <svg viewBox="0 0 160 160" aria-hidden="true">
              <circle cx="80" cy="80" r="70" fill="none" stroke="rgba(236, 238, 242, 0.09)" stroke-width="10"/>
              <circle id="bayan-modal-score-circle" cx="80" cy="80" r="70" fill="none" stroke="url(#bayanModalScoreGradient)" stroke-width="10" stroke-linecap="round" stroke-dasharray="440" stroke-dashoffset="440" class="bayan-il-score-circle"/>
              <defs><linearGradient id="bayanModalScoreGradient" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#6BA3E0"/><stop offset="100%" stop-color="#A594E8"/></linearGradient></defs>
            </svg>
            <div class="bayan-il-modal-score-value"><span id="bayan-modal-score-value">--</span></div>
          </div>
          <p id="bayan-modal-score-hint" class="bayan-il-modal-score-hint">ابدأ الكتابة لرؤية تقييمك</p>
          <div class="bayan-il-modal-counts-row">
            <span class="bayan-il-modal-count bayan-il-modal-count--spelling"><strong id="bayan-modal-count-spelling">٠</strong> إملائي</span>
            <span class="bayan-il-modal-count bayan-il-modal-count--grammar"><strong id="bayan-modal-count-grammar">٠</strong> نحوي</span>
            <span class="bayan-il-modal-count bayan-il-modal-count--punctuation"><strong id="bayan-modal-count-punctuation">٠</strong> ترقيم</span>
          </div>
        </div>
      </div>
    `);

    document.body.appendChild(modalPanel);

    modalPanel.querySelector('.bayan-il-modal-close').addEventListener('click', hideModal);

    modalPanel.querySelector('#bayan-modal-apply-all').addEventListener('click', applyAllFixes);

    modalPanel.querySelector('#bayan-modal-theme-toggle').addEventListener('click', () => {
      currentBayanTheme = currentBayanTheme === 'dark' ? 'light' : 'dark';
      chrome.storage.local.set({ theme: currentBayanTheme });
      if (modalPanel) modalPanel.setAttribute('data-bayan-theme', currentBayanTheme);
      if (tooltip) tooltip.setAttribute('data-bayan-theme', currentBayanTheme);
      if (floatingBtn) floatingBtn.setAttribute('data-bayan-theme', currentBayanTheme);
    });

    document.addEventListener('keydown', onModalKeydown);

    let modalDragging = false;
    let modalDragStartX = 0;
    let modalDragStartY = 0;
    let modalDragOffsetX = 0;
    let modalDragOffsetY = 0;

    const dragHandle = modalPanel.querySelector('#bayan-modal-drag-handle');
    if (dragHandle) {
      dragHandle.addEventListener('mousedown', (e) => {
        if (e.target.closest('.bayan-il-modal-close') || e.target.closest('.bayan-il-modal-theme-toggle') || e.target.closest('.bayan-il-modal-logo-link')) return;
        modalDragging = true;
        modalDragStartX = e.clientX;
        modalDragStartY = e.clientY;
        modalDragOffsetX = parseInt(modalPanel.style.left || 0, 10);
        modalDragOffsetY = parseInt(modalPanel.style.top || 0, 10);
        e.preventDefault();
      });

      document.addEventListener('mousemove', (e) => {
        if (!modalDragging) return;
        const dx = e.clientX - modalDragStartX;
        const dy = e.clientY - modalDragStartY;
        modalPanel.style.left = `${modalDragOffsetX + dx}px`;
        modalPanel.style.top = `${modalDragOffsetY + dy}px`;
      });

      document.addEventListener('mouseup', () => {
        if (modalDragging) {
          modalDragging = false;
          modalCustomPos = {
            x: parseInt(modalPanel.style.left, 10),
            y: parseInt(modalPanel.style.top, 10),
          };
        }
      });
    }
  }

  function onModalKeydown(e) {
    if (e.key === 'Escape' && modalPanel?.classList.contains('bayan-il-modal-panel--visible')) {
      hideModal();
    }
  }

  function syncModalIfVisible() {
    if (modalPanel && modalPanel.classList.contains('bayan-il-modal-panel--visible')) {
      updateModalScore();
      renderModalSuggestions();
    }
  }

  function showModal() {
    createModal();

    modalPanel.setAttribute('data-bayan-theme', currentBayanTheme);

    updateModalScore();
    renderModalSuggestions();

    // Position modal
    if (!modalCustomPos) {
      if (activeField) {
        const fieldRect = activeField.getBoundingClientRect();
        modalPanel.style.position = 'fixed';
        let left = fieldRect.left + (fieldRect.width / 2) - 180;
        if (left < 10) left = 10;
        if (left + 360 > window.innerWidth) left = window.innerWidth - 370;
        modalPanel.style.left = `${left}px`;
        
        let top = fieldRect.bottom + 10;
        if (top + 400 > window.innerHeight) {
          top = Math.max(10, window.innerHeight - 410);
        }
        modalPanel.style.top = `${top}px`;
      } else if (floatingBtn) {
        const fabRect = floatingBtn.getBoundingClientRect();
        modalPanel.style.position = 'fixed';
        let left = fabRect.left - 370;
        if (left < 10) left = 10;
        modalPanel.style.left = `${left}px`;
        
        let top = fabRect.bottom - 400;
        if (top < 10) top = 10;
        modalPanel.style.top = `${top}px`;
      }
    } else {
      modalPanel.style.position = 'fixed';
      modalPanel.style.left = `${modalCustomPos.x}px`;
      modalPanel.style.top = `${modalCustomPos.y}px`;
    }

    requestAnimationFrame(() => {
      modalPanel.classList.add('bayan-il-modal-panel--visible');
    });
  }

  function hideModal() {
    if (modalPanel) modalPanel.classList.remove('bayan-il-modal-panel--visible');
  }



  function updateModalScore() {
    if (!modalPanel) return;

    const counts = { spelling: 0, grammar: 0, punctuation: 0 };
    suggestions.forEach((s) => {
      if (counts[s.type] !== undefined) counts[s.type]++;
    });

    const score = calculateWritingScore(counts.spelling, counts.grammar, counts.punctuation);
    const offset = 440 - (440 * score) / 100;

    const circle = modalPanel.querySelector('#bayan-modal-score-circle');
    const valueEl = modalPanel.querySelector('#bayan-modal-score-value');
    const hintEl = modalPanel.querySelector('#bayan-modal-score-hint');

    const toArabicNum = (n) => String(n).replace(/\d/g, (d) => '٠١٢٣٤٥٦٧٨٩'[d]);

    if (circle) {
      requestAnimationFrame(() => {
        circle.setAttribute('stroke-dashoffset', String(offset));
      });
    }
    const total = counts.spelling + counts.grammar + counts.punctuation;
    const fieldText = activeField ? getFieldText(activeField) : '';
    const hasArabicText = fieldText.trim().length > 0 && BayanController.hasArabic(fieldText);

    if (valueEl) {
      valueEl.textContent = (hasArabicText || total > 0) ? toArabicNum(score) : '--';
    }
    if (hintEl) {
      if (analysisInProgress && total === 0) {
        hintEl.textContent = 'جارٍ التحليل...';
      } else if (total > 0) {
        hintEl.textContent = getScoreHint(score);
      } else if (hasArabicText) {
        hintEl.textContent = getScoreHint(score);
      } else {
        hintEl.innerHTML = 'ابدأ الكتابة لرؤية تقييمك<br><span class="bayan-il-modal-score-hint-sub">تحسين القواعد يرفع التقييم</span>';
      }
    }

    const cSpelling = modalPanel.querySelector('#bayan-modal-count-spelling');
    const cGrammar = modalPanel.querySelector('#bayan-modal-count-grammar');
    const cPunctuation = modalPanel.querySelector('#bayan-modal-count-punctuation');
    if (cSpelling) cSpelling.textContent = toArabicNum(counts.spelling);
    if (cGrammar) cGrammar.textContent = toArabicNum(counts.grammar);
    if (cPunctuation) cPunctuation.textContent = toArabicNum(counts.punctuation);
  }

  function renderModalSuggestions() {
    if (!modalPanel) return;

    const container = modalPanel.querySelector('#bayan-modal-cards');
    const applyAllBtn = modalPanel.querySelector('#bayan-modal-apply-all');

    if (!container) return;

    // State 1: Errors exist — show suggestion cards (highest priority)
    if (suggestions.length > 0) {
      const toArabicNum = (n) => String(n).replace(/\d/g, (d) => '٠١٢٣٤٥٦٧٨٩'[d]);
      if (applyAllBtn) {
        if (suggestions.length > 1) {
          applyAllBtn.style.display = 'flex';
          applyAllBtn.textContent = 'تطبيق الكل (' + toArabicNum(suggestions.length) + ')';
        } else {
          applyAllBtn.style.display = 'none';
        }
      }

    let html = '';
    suggestions.forEach((s, idx) => {
      const alts = resolveAlternatives(s);
      const typeLabel = TYPE_LABELS[s.type] || s.type;

      html += `<div class="bayan-il-modal-card bayan-il-modal-card--${s.type}" data-suggestion-type="${s.type}" data-modal-idx="${idx}">`;
      html += `<span class="bayan-il-modal-card-badge bayan-il-modal-badge--${s.type}">${typeLabel}</span>`;
      html += `<div class="bayan-il-modal-card-change">`;
      html += `<span class="bayan-il-modal-card-original">${esc(s.original)}</span>`;
      html += `<span class="bayan-il-modal-card-arrow">←</span>`;
      html += `<span class="bayan-il-modal-card-fix">${s.correction ? esc(s.correction) : '<s style="opacity:0.5">حذف</s>'}</span>`;
      html += `</div>`;
      html += `<div class="bayan-il-modal-card-alts">`;

      alts.forEach((alt, ai) => {
        const isMain = alt === s.correction && ai === 0;
        const isKeep = alt === s.original;
        const label = isKeep ? esc(alt) + ' ✓' : esc(alt);
        const cls = isMain ? 'bayan-il-modal-alt-chip bayan-il-modal-alt-chip--main' : (isKeep ? 'bayan-il-modal-alt-chip bayan-il-modal-alt-chip--keep' : 'bayan-il-modal-alt-chip');
        html += `<button class="${cls}" data-modal-alt="${esc(alt)}" data-modal-sidx="${idx}" data-modal-keep="${isKeep ? '1' : ''}">${label}</button>`;
      });

      html += `</div></div>`;
    });

    safeHTML(container, html);

    container.querySelectorAll('.bayan-il-modal-alt-chip').forEach((chip) => {
      chip.addEventListener('click', (e) => {
        e.stopPropagation();
        const sidx = parseInt(chip.dataset.modalSidx, 10);
        const isKeep = chip.dataset.modalKeep === '1';
        const s = suggestions[sidx];
        if (!s) return;

        if (isKeep) {
          dismissSuggestion(s);
        } else {
          const altVal = chip.dataset.modalAlt;
          const fixSugg = { ...s, correction: altVal };
          applyFix(activeField || lastInteractedField, fixSugg);
        }

        updateModalScore();
        renderModalSuggestions();

        if (suggestions.length === 0) {
          setTimeout(hideModal, 600);
        }
      });
    });
      return;
    }

    // State 2: Loading — analysis in progress, no suggestions yet
    if (analysisInProgress) {
      safeHTML(container, '<div class="bayan-il-modal-empty"><div class="bayan-il-modal-loading-spinner"></div><div class="bayan-il-modal-empty-title">جارٍ التحليل...</div></div>');
      if (applyAllBtn) applyAllBtn.style.display = 'none';
      return;
    }

    // State 3: No text — textarea is empty or has no Arabic
    const fieldText = activeField ? getFieldText(activeField) : '';
    const hasArabicText = fieldText.trim().length > 0 && BayanController.hasArabic(fieldText);
    if (!hasArabicText) {
      safeHTML(container, '<div class="bayan-il-modal-empty"><div class="bayan-il-modal-empty-icon">📝</div><div class="bayan-il-modal-empty-title">لا توجد اقتراحات</div><div class="bayan-il-modal-empty-desc">ابدأ بكتابة نص عربي وسيتم تحليله تلقائياً</div></div>');
      if (applyAllBtn) applyAllBtn.style.display = 'none';
      return;
    }

    // State 4: Clean text — has Arabic text but no errors
    safeHTML(container, '<div class="bayan-il-modal-empty"><div class="bayan-il-modal-empty-icon">✨</div><div class="bayan-il-modal-empty-title">نصك ممتاز!</div><div class="bayan-il-modal-empty-desc">لم نجد أي أخطاء — أحسنت! ✨</div></div>');
    if (applyAllBtn) applyAllBtn.style.display = 'none';
  }

  function applyAllFixes() {
    const field = activeField || lastInteractedField;
    if (!field || suggestions.length === 0) return;

    while (suggestions.length > 0) {
      const last = suggestions.reduce((a, b) => a.start > b.start ? a : b);
      applyFix(field, last);
    }

    updateModalScore();
    renderModalSuggestions();
    setTimeout(hideModal, 600);
  }

  // ── Theme Sync for Inline UI ──
  let currentBayanTheme = 'dark';
  chrome.storage.local.get(['theme'], (res) => {
    currentBayanTheme = res.theme || 'dark';
    if (typeof tooltip !== 'undefined' && tooltip) tooltip.setAttribute('data-bayan-theme', currentBayanTheme);
    if (typeof floatingBtn !== 'undefined' && floatingBtn) floatingBtn.setAttribute('data-bayan-theme', currentBayanTheme);
    if (modalPanel) { modalPanel.setAttribute('data-bayan-theme', currentBayanTheme); }
  });

  chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'local' && changes.theme) {
      currentBayanTheme = changes.theme.newValue;
      if (typeof tooltip !== 'undefined' && tooltip) tooltip.setAttribute('data-bayan-theme', currentBayanTheme);
      if (typeof floatingBtn !== 'undefined' && floatingBtn) floatingBtn.setAttribute('data-bayan-theme', currentBayanTheme);
      if (modalPanel) { modalPanel.setAttribute('data-bayan-theme', currentBayanTheme); }
    }
  });

})();
