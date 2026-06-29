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
  let floatingBtn = null;
  let tooltip = null;
  let overlayContainer = null;
  let badgeCount = null;
  let observer = null;

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

    const text = getFieldText(activeField);

    scheduleGhost();

    if (analysisSuppressed) {
      clearHighlights();
      updateBadge(0);
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
      return;
    }

    updateBadge(-1);

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

    if (!data) {
      updateBadge(0);
      return;
    }

    suggestions = data.suggestions || [];
    lastAnalyzedText = data.original || getFieldText(activeField);
    updateBadge(suggestions.length);

    if (suggestions.length > 0) {
      renderOverlay(activeField, lastAnalyzedText, suggestions);
    } else {
      clearHighlights();
    }
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
    // Only when the caret is collapsed at the very end of the text.
    if (activeField.selectionStart !== val.length) return false;
    if (activeField.selectionEnd !== val.length) return false;
    if (val.trim().length < AC_MIN_CONTEXT) return false;
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

      ghostEl = document.createElement('div');
      ghostEl.className = 'bayan-il-ghost';
      ghostEl.style.cssText = `position:fixed;top:${rect.top}px;`
        + `left:${rect.left}px;width:${rect.width}px;height:${rect.height}px;`
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

      overlayContainer = document.createElement('div');
      overlayContainer.className = 'bayan-il-overlay';
      overlayContainer.style.cssText = `position:fixed;top:${rect.top}px;`
        + `left:${rect.left}px;width:${rect.width}px;height:${rect.height}px;`
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
    const typeLabels = { spelling: 'إملائي', grammar: 'نحوي', punctuation: 'ترقيم' };

    tooltip = document.createElement('div');
    tooltip.setAttribute('data-bayan-theme', currentBayanTheme);
    tooltip.className = 'bayan-il-tooltip';
    tooltip.dir = 'rtl';

    safeHTML(tooltip, `
      <div class="bayan-il-tooltip-header">
        <span class="bayan-il-tooltip-badge bayan-il-badge-${type}">${typeLabels[type] || type}</span>
        <button class="bayan-il-tooltip-close" title="إغلاق">✕</button>
      </div>
      <div class="bayan-il-tooltip-body">
        <span class="bayan-il-tooltip-original">${esc(original)}</span>
        <span class="bayan-il-tooltip-arrow">←</span>
        <span class="bayan-il-tooltip-correction">${correction ? esc(correction) : '<s style="opacity:0.5">حذف</s>'}</span>
      </div>
      <div class="bayan-il-tooltip-actions">
        <button class="bayan-il-tooltip-apply" data-action="apply">تطبيق</button>
        <button class="bayan-il-tooltip-ignore" data-action="ignore">تجاهل</button>
      </div>
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

    tooltip.querySelector('[data-action="ignore"]').addEventListener('click', () => {
      dismissSuggestion(suggestion);
      hideTooltip();
    });

    tooltip.querySelector('.bayan-il-tooltip-close').addEventListener('click', () => hideTooltip());

    setTimeout(() => document.addEventListener('click', outsideClick, { once: true }), 100);
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

  function dismissSuggestion(suggestion) {
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
    safeHTML(floatingBtn, `
      <svg width="18" height="18" viewBox="0 0 100 100" fill="none">
        <circle cx="50" cy="50" r="46" fill="url(#blGrad)" />
        <path d="M30 55 Q35 35, 50 30 Q65 35, 70 55 Q65 65, 50 70 Q35 65, 30 55Z" fill="rgba(255,255,255,0.9)" />
        <circle cx="50" cy="42" r="4" fill="url(#blGrad)" />
        <defs>
          <linearGradient id="blGrad" x1="0" y1="0" x2="100" y2="100">
            <stop offset="0%" stop-color="#6366f1"/>
            <stop offset="100%" stop-color="#8b5cf6"/>
          </linearGradient>
        </defs>
      </svg>
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
      if (suggestions.length > 0) {
        try {
          pendingSelection = null;
          if (lastInteractedField) lastInteractedField.dataset.bayanSource = '1';
          chrome.runtime.sendMessage({ type: 'OPEN_SIDEPANEL', text: lastAnalyzedText });
        } catch {}
      }
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
      if (document.querySelector('.bayan-il-tooltip')) return;
      detachField();
    }, 300);
  }, true);

  window.addEventListener('scroll', () => {
    if (activeField && floatingBtn) positionFab(activeField);
    if (overlayContainer && activeField) {
      const rect = activeField.getBoundingClientRect();
      overlayContainer.style.top = `${rect.top}px`;
      overlayContainer.style.left = `${rect.left}px`;
    }
    if (ghostEl && activeField) {
      const rect = activeField.getBoundingClientRect();
      ghostEl.style.top = `${rect.top}px`;
      ghostEl.style.left = `${rect.left}px`;
    }
  }, { passive: true });

  window.addEventListener('resize', () => {
    if (activeField && floatingBtn) positionFab(activeField);
    // B4: a viewport resize can change the field's width/position, leaving the
    // overlay marks misaligned. Re-render the overlay (not just the FAB) so
    // highlights track the field. Guarded by suggestions to avoid needless work.
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


  // ── Theme Sync for Inline UI ──
  let currentBayanTheme = 'dark';
  chrome.storage.local.get(['theme'], (res) => {
    currentBayanTheme = res.theme || 'dark';
    if (typeof tooltip !== 'undefined' && tooltip) tooltip.setAttribute('data-bayan-theme', currentBayanTheme);
    if (typeof floatingBtn !== 'undefined' && floatingBtn) floatingBtn.setAttribute('data-bayan-theme', currentBayanTheme);
  });
  
  chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === 'local' && changes.theme) {
      currentBayanTheme = changes.theme.newValue;
      if (typeof tooltip !== 'undefined' && tooltip) tooltip.setAttribute('data-bayan-theme', currentBayanTheme);
      if (typeof floatingBtn !== 'undefined' && floatingBtn) floatingBtn.setAttribute('data-bayan-theme', currentBayanTheme);
    }
  });

})();
