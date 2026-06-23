# Bayan Phase 2 — UX Modernization & Professional Editor Experience

**Status**: Design Plan (Pre-Implementation)  
**Date**: June 15, 2026  
**Prerequisite**: Phase 1 complete (offset-based renderer, modular JS, API integration)  
**Scope**: Frontend UX only — no Supabase, auth, database, deployment, or backend architecture

---

## Table of Contents

1. [UX Audit](#1-ux-audit)
2. [Wireframes](#2-wireframes)
3. [Component Inventory](#3-component-inventory)
4. [Design System (Phase 2.1)](#4-design-system-phase-21)
5. [Layout Redesign (Phase 2.2)](#5-layout-redesign-phase-22)
6. [Theme System (Phase 2.3)](#6-theme-system-phase-23)
7. [Editor UX Improvements (Phase 2.4)](#7-editor-ux-improvements-phase-24)
8. [Responsive Design (Phase 2.5)](#8-responsive-design-phase-25)
9. [Accessibility Audit (Phase 2.6)](#9-accessibility-audit-phase-26)
10. [Performance Audit (Phase 2.7)](#10-performance-audit-phase-27)
11. [Implementation Roadmap](#11-implementation-roadmap)

---

## 1. UX Audit

### 1.1 Current Interface State

Phase 1 delivered a **functional** editor with real API analysis, offset-based highlighting, cursor preservation, and modular JS. The UI is a single `index.html` (~1,033 lines, 59 KB) with Tailwind CDN, inline styles, and CSS custom properties. Four pages share one nav: Home, Features, Editor, Pricing.

#### Screen 1 — Home (Landing)

```
┌─────────────────────────────────────────────────────────────────┐
│ [ب] بيان    الرئيسية  الميزات  المحرر  الأسعار   تسجيل | CTA  │ ← fixed nav
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────┐  ┌────────────────────────────────┐ │
│  │ مدعوم بالذكاء الاصطناعي │  │ ● ● ●  محرر بيان              │ │
│  │ اكتب العربية           │  │ ┌──────────────────────────┐  │ │
│  │ بثقة واحتراف           │  │ │ white editor mockup      │  │ │
│  │ [CTA] [demo]           │  │ │ red/yellow/green spans   │  │ │
│  │ +10M | 99% | +50K      │  │ └──────────────────────────┘  │ │
│  └──────────────────────┘  │ stats bar + floating card      │ │
│                             └────────────────────────────────┘ │
│  ميزات قوية ومتقدمة (4 cards)                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Observations**: Strong marketing layout. Hero mockup previews editor but uses static HTML, not live editor. Stats (+10M words, 99% accuracy) are placeholder marketing numbers.

#### Screen 2 — Editor (Core Product)

```
┌─────────────────────────────────────────────────────────────────┐
│ nav (same)                                                       │
├──────────────────────────────────────┬──────────────────────────┤
│ [كتابة] [تلخيص]        عدد الكلمات: ٠ │  تقييم الكتابة          │
│ ┌──────────────────────────────────┐ │  ┌────────┐            │
│ │ WHITE contenteditable area         │ │  │  --    │ score ring │
│ │ (contrasts with dark chrome)       │ │  └────────┘            │
│ │ min-height 500px                   │ │  الاقتراحات            │
│ └──────────────────────────────────┘ │  "لا توجد اقتراحات"    │
│ ● ٠ إملائي ● ٠ نحوي ● ٠ ترقيم       │  (static empty state)  │
│ [مسح الكل] [نسخ النص]                │                          │
└──────────────────────────────────────┴──────────────────────────┘
```

**Observations**: Editor works (Phase 1) but sidebar score ring and suggestions list are **not wired** to `editor.js`. Placeholder attribute exists (`data-placeholder`) but **no CSS** renders it. Editor surface is always white inside dark shell.

#### Screen 3 — Features / Pricing

Long-scroll marketing pages with repeated card patterns, demo suggestion boxes, and pricing tiers (Free / Pro / Enterprise). Login and CTA buttons are non-functional placeholders.

---

### 1.2 Problems Found

| # | Area | Problem | Severity |
|---|------|---------|----------|
| P1 | Visual hierarchy | Editor page splits 8/4 grid but sidebar feels disconnected; score + suggestions don't update | High |
| P2 | Theme consistency | Dark chrome + white editor creates harsh "document in a cave" feel; no light theme | High |
| P3 | Placeholder | `data-placeholder` set in JS but no `::before` / `data-empty` styling — empty editor shows blank white box | High |
| P4 | Suggestions panel | `#suggestions-list` never populated by `editor.js`; only inline highlights + tooltip work | High |
| P5 | Score widget | `#score-value` stays `--`; `#score-circle` stroke never animates | Medium |
| P6 | Navigation | No mobile hamburger; `hidden md:flex` hides all nav links on small screens | High |
| P7 | Inline styles | ~200+ `style=""` attributes mixed with CSS variables — hard to theme/maintain | Medium |
| P8 | Typography | Tajawal + Noto Kufi Arabic loaded but no systematic type scale (h1–body–caption) | Medium |
| P9 | Accessibility | Zero `aria-*` labels; contenteditable has no `role="textbox"`; tooltips not keyboard-accessible | High |
| P10 | Focus states | Editor `focus:ring-2` only; suggestion spans have no `:focus-visible` outline | Medium |
| P11 | Tooltip UX | Fixed-position tooltip can clip off-screen; no dismiss on outside click/Escape | Medium |
| P12 | Summarize tab | `generateSummary()` references `#editor-textarea` (removed) — summarize flow broken | High |
| P13 | Auth CTAs | "تسجيل الدخول" and pricing buttons lead nowhere — confusing for demo reviewers | Low |
| P14 | Performance | Tailwind CDN compiles full utility set at runtime; 59 KB monolithic HTML | Medium |
| P15 | Spacing | Inconsistent padding (`p-4`, `p-6`, `p-8`) without named scale | Low |
| P16 | Error highlights | Red/yellow/green underlines are functional but lack hover/active states and legend clarity | Medium |
| P17 | Footer | Copyright shows ٢٠٢٤; should be ٢٠٢٦ | Low |

---

### 1.3 Proposed Improvements

| Problem | Improvement |
|---------|-------------|
| P1–P2 | Unified layout shell with theme-aware editor surface; sidebar becomes live feedback panel |
| P3 | CSS pseudo-placeholder + subtle empty-state illustration |
| P4–P5 | Wire `updateSuggestionsList()` and `updateWritingScore()` in `editor.js` after each analyze |
| P6 | Collapsible mobile nav drawer with focus trap |
| P7 | Extract design tokens to `css/tokens.css` + Tailwind config; remove inline `style=""` |
| P8 | Adopt Cairo as primary font with documented type scale |
| P9–P10 | Full ARIA layer + keyboard suggestion navigation (Tab/Enter/Escape) |
| P11 | Popover component with collision detection and click-outside dismiss |
| P12 | Fix summarize to read from `getEditorText()` |
| P14 | Split CSS/JS; consider Tailwind build step or keep CDN with `tailwind.config` |
| P16 | Semantic highlight tokens per theme; legend in editor footer |

---

## 2. Wireframes

### 2.1 Editor — Desktop (≥1024px) — Proposed

```
┌──────────────────────────────────────────────────────────────────────────┐
│ HEADER                                                                   │
│ [ب] بيان          المحرر ▾          [🌙/☀️ theme]  [ابدأ الكتابة]      │
├──────────────────────────────────────────────────────────────────────────┤
│ EDITOR AREA (flex-1, max-w-5xl centered)     │ SUGGESTION PANEL (w-80)  │
│ ┌──────────────────────────────────────────┐ │ ┌──────────────────────┐ │
│ │ Toolbar: كتابة | تلخيص    ١٢٣ كلمة     │ │ │ Writing Score   ٨٥  │ │
│ ├──────────────────────────────────────────┤ │ │ ████████░░ ring      │ │
│ │                                          │ │ ├──────────────────────┤ │
│ │  ابدأ الكتابة هنا...                     │ │ │ 🔴 إملائي (٢)        │ │
│ │  (theme-aware surface, 1.9 line-height)  │ │ │  الصحيحه → الصحيحة   │ │
│ │                                          │ │ │ 🟡 نحوي (١)          │ │
│ │  [highlighted spans inline]              │ │ │  ذهبو → ذهب          │ │
│ │                                          │ │ ├──────────────────────┤ │
│ └──────────────────────────────────────────┘ │ │ [تطبيق الكل]         │ │
│ STATISTICS BAR                               │ └──────────────────────┘ │
│ ● إملائي ٢  ● نحوي ١  ● ترقيم ٠  │ مسح │ نسخ│                          │
├──────────────────────────────────────────────────────────────────────────┤
│ FOOTER (minimal): © ٢٠٢٦ بيان · الخصوصية · الشروط                       │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Editor — Mobile (<768px) — Proposed

```
┌─────────────────────────┐
│ [☰]  بيان        [🌙]  │
├─────────────────────────┤
│ [كتابة][تلخيص]  ٤٥ كلمة│
├─────────────────────────┤
│                         │
│   Editor (full width)   │
│                         │
├─────────────────────────┤
│ Score: ٨٥  │  ٣ اقتراحات│  ← tap opens bottom sheet
├─────────────────────────┤
│ ●٢ ●١ ●٠  │ مسح │ نسخ  │
└─────────────────────────┘

Bottom sheet (when "٣ اقتراحات" tapped):
┌─────────────────────────┐
│ ─── handle ───          │
│ الاقتراحات (٣)          │
│ [suggestion cards...]   │
└─────────────────────────┘
```

### 2.3 Home — Proposed (Simplified)

Reduce clutter: single hero + 4 features + one CTA. Move pricing to footer link. Focus graduation demo on **Editor** as primary entry.

---

## 3. Component Inventory

### 3.1 Existing (to refactor)

| Component | Location | Action |
|-----------|----------|--------|
| `NavBar` | `index.html` L241–254 | Extract; add mobile menu + theme toggle |
| `HeroSection` | L255–347 | Simplify; reduce animation |
| `FeatureCard` | L354–383 | Extract reusable card |
| `EditorToolbar` | L558–562 | Extract; responsive wrap |
| `EditorSurface` | `#editor-container` | Theme-aware; ARIA |
| `SuggestionTooltip` | `#editor-tooltip` | Replace with `SuggestionPopover` |
| `ScoreRing` | L611–621 | Wire to live score calculation |
| `SuggestionsList` | `#suggestions-list` | Wire to `currentSuggestions` |
| `StatsBar` | L591–605 | Extract; add legend tooltips |
| `SummarizePanel` | L572–589 | Fix API; theme tokens |
| `Footer` | L748–760 | Minimal; update year |

### 3.2 New Components (to create)

| Component | File | Purpose |
|-----------|------|---------|
| `ThemeProvider` | `js/theme.js` | Dark/light toggle + localStorage |
| `DesignTokens` | `css/tokens.css` | CSS variables per theme |
| `SuggestionCard` | `js/components/suggestion-card.js` | Sidebar list item |
| `SuggestionPopover` | `js/components/suggestion-popover.js` | Inline correction UI |
| `EmptyState` | `js/components/empty-state.js` | No suggestions / empty editor |
| `MobileNav` | `js/components/mobile-nav.js` | Hamburger drawer |
| `BottomSheet` | `js/components/bottom-sheet.js` | Mobile suggestions panel |
| `WritingScore` | `js/components/writing-score.js` | Score ring + label |
| `IconButton` | shared | Theme toggle, dismiss, etc. |
| `LoadingIndicator` | shared | Analysis in progress |

### 3.3 File Structure (proposed)

```
src/
├── index.html              (slim shell, imports only)
├── css/
│   ├── tokens.css          (design system variables)
│   ├── base.css            (typography, reset)
│   ├── components.css      (cards, tooltips, highlights)
│   └── themes.css          (dark/light class toggles)
├── js/
│   ├── theme.js
│   ├── editor.js           (existing, extended)
│   ├── renderer.js         (existing, token-based classes)
│   ├── selection.js        (existing)
│   ├── api.js              (existing)
│   └── components/
│       ├── suggestion-card.js
│       ├── suggestion-popover.js
│       ├── writing-score.js
│       ├── mobile-nav.js
│       └── bottom-sheet.js
```

---

## 4. Design System (Phase 2.1)

### 4.1 Colors — Dark Theme

| Token | Hex | Tailwind Classes | Usage |
|-------|-----|------------------|-------|
| Background | `#0B1120` | `bg-slate-950` | Page background |
| Surface | `#151D2E` | `bg-slate-900` | Cards, panels, nav |
| Surface Elevated | `#1E293B` | `bg-slate-800` | Editor chrome, dropdowns |
| Primary | `#3B82F6` | `bg-blue-500` `text-blue-500` | CTAs, active tabs, links |
| Secondary | `#8B5CF6` | `bg-violet-500` `text-violet-500` | Gradients, summarize accent |
| Accent | `#06B6D4` | `bg-cyan-500` `text-cyan-500` | Focus rings, highlights |
| Success | `#22C55E` | `bg-green-500` `text-green-500` | Punctuation fixes, applied state |
| Warning | `#F59E0B` | `bg-amber-500` `text-amber-500` | Grammar suggestions |
| Error | `#EF4444` | `bg-red-500` `text-red-500` | Spelling errors |
| Text Primary | `#F1F5F9` | `text-slate-100` | Headings, body on dark |
| Text Secondary | `#94A3B8` | `text-slate-400` | Captions, placeholders |
| Border | `rgba(255,255,255,0.08)` | `border-white/10` | Card borders |

**Editor surface (dark mode)**: `bg-slate-850` custom `#1A2332` with `text-slate-100` — not pure white.

**Highlight backgrounds (dark)**:
- Spelling: `bg-red-500/20 border-b-2 border-red-500`
- Grammar: `bg-amber-500/20 border-b-2 border-amber-500`
- Punctuation: `bg-green-500/20 border-b-2 border-green-500`

### 4.2 Colors — Light Theme

| Token | Hex | Tailwind Classes | Usage |
|-------|-----|------------------|-------|
| Background | `#F8FAFC` | `bg-slate-50` | Page background |
| Surface | `#FFFFFF` | `bg-white` | Cards, panels |
| Surface Elevated | `#F1F5F9` | `bg-slate-100` | Editor toolbar |
| Primary | `#2563EB` | `bg-blue-600` `text-blue-600` | CTAs |
| Secondary | `#7C3AED` | `bg-violet-600` `text-violet-600` | Accents |
| Accent | `#0891B2` | `bg-cyan-600` `text-cyan-600` | Focus |
| Success | `#16A34A` | `bg-green-600` `text-green-600` | Punctuation |
| Warning | `#D97706` | `bg-amber-600` `text-amber-600` | Grammar |
| Error | `#DC2626` | `bg-red-600` `text-red-600` | Spelling |
| Text Primary | `#0F172A` | `text-slate-900` | Body text |
| Text Secondary | `#64748B` | `text-slate-500` | Captions |
| Border | `rgba(0,0,0,0.08)` | `border-slate-200` | Dividers |

**Editor surface (light mode)**: `bg-white` with `shadow-sm border border-slate-200` — professional document feel.

**Highlight backgrounds (light)**:
- Spelling: `bg-red-50 border-b-2 border-red-500`
- Grammar: `bg-amber-50 border-b-2 border-amber-500`
- Punctuation: `bg-green-50 border-b-2 border-green-500`

### 4.3 CSS Variable Map

```css
/* css/tokens.css */
:root, [data-theme="dark"] {
  --color-bg: 11 17 32;           /* slate-950 custom */
  --color-surface: 21 29 46;
  --color-primary: 59 130 246;
  --color-secondary: 139 92 246;
  --color-accent: 6 182 212;
  --color-success: 34 197 94;
  --color-warning: 245 158 11;
  --color-error: 239 68 68;
  --spacing-xs: 0.25rem;  /* 4px  — Tailwind 1 */
  --spacing-sm: 0.5rem;   /* 8px  — Tailwind 2 */
  --spacing-md: 1rem;     /* 16px — Tailwind 4 */
  --spacing-lg: 1.5rem;   /* 24px — Tailwind 6 */
  --spacing-xl: 2rem;     /* 32px — Tailwind 8 */
}

[data-theme="light"] {
  --color-bg: 248 250 252;
  --color-surface: 255 255 255;
  --color-primary: 37 99 235;
  /* ... */
}
```

### 4.4 Typography

#### Font Evaluation

| Font | Readability | Modern Feel | RTL Support | Editor Suitability | Verdict |
|------|-------------|-------------|-------------|-------------------|---------|
| **Cairo** | ★★★★★ | ★★★★★ | Excellent | Excellent for UI + body | **Recommended primary** |
| Tajawal | ★★★★☆ | ★★★★☆ | Excellent | Good; slightly casual | Keep as fallback |
| IBM Plex Sans Arabic | ★★★★★ | ★★★★☆ | Excellent | Best for long documents | Optional editor-only |
| Noto Sans Arabic | ★★★★☆ | ★★★☆☆ | Excellent | Neutral, safe fallback | System fallback |

#### Decision: **Cairo** (primary)

**Justification**: Cairo is the most widely adopted Arabic UI font in modern SaaS products. It offers excellent readability at small sizes, clean geometric forms that feel professional without being corporate, and strong RTL kerning. It pairs well with both dark and light themes. Tajawal remains as fallback; Noto Sans Arabic as last resort for glyph coverage.

```html
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700&display=swap" rel="stylesheet">
```

#### Type Scale

| Role | Size | Weight | Tailwind | Line Height |
|------|------|--------|----------|-------------|
| Display | 3rem / 48px | 700 | `text-5xl font-bold` | 1.3 |
| H1 | 2.25rem / 36px | 700 | `text-4xl font-bold` | 1.35 |
| H2 | 1.875rem / 30px | 600 | `text-3xl font-semibold` | 1.4 |
| H3 | 1.25rem / 20px | 600 | `text-xl font-semibold` | 1.5 |
| Body | 1rem / 16px | 400 | `text-base` | 1.75 |
| Editor | 1.125rem / 18px | 400 | `text-lg` | 1.9 |
| Caption | 0.875rem / 14px | 500 | `text-sm font-medium` | 1.6 |
| Label | 0.75rem / 12px | 600 | `text-xs font-semibold uppercase tracking-wide` | 1.5 |

### 4.5 Spacing Scale

| Token | Value | Tailwind | Usage |
|-------|-------|----------|-------|
| xs | 4px | `p-1` `gap-1` `m-1` | Icon padding, tight gaps |
| sm | 8px | `p-2` `gap-2` | Button padding, list gaps |
| md | 16px | `p-4` `gap-4` | Card padding, section gaps |
| lg | 24px | `p-6` `gap-6` | Panel padding, grid gaps |
| xl | 32px | `p-8` `gap-8` | Page sections, hero spacing |

**Rule**: Use only these five steps. Editor padding = `lg`, card padding = `md`, toolbar = `sm` vertical / `md` horizontal.

### 4.6 Border Radius & Shadows

| Token | Value | Tailwind |
|-------|-------|----------|
| Radius sm | 8px | `rounded-lg` |
| Radius md | 12px | `rounded-xl` |
| Radius lg | 16px | `rounded-2xl` |
| Shadow card | — | `shadow-lg shadow-black/10` |
| Shadow popover | — | `shadow-xl shadow-black/20` |

---

## 5. Layout Redesign (Phase 2.2)

### 5.1 Section Architecture

```
┌─────────────────────────────────────┐
│ HEADER (h-16, sticky)               │  Logo · Nav · Theme · CTA
├──────────────────┬──────────────────┤
│ EDITOR AREA      │ SUGGESTION PANEL │  65% / 35% on xl; stacked on mobile
│ (primary focus)  │ (secondary)      │
├──────────────────┴──────────────────┤
│ STATISTICS BAR (inline with editor) │  Error counts · actions
├─────────────────────────────────────┤
│ FOOTER (compact)                    │  Legal links only on editor page
└─────────────────────────────────────┘
```

### 5.2 Hierarchy Principles

1. **Editor first** — largest visual weight, centered, min 60vh height
2. **Sidebar secondary** — collapsible on tablet; bottom sheet on mobile
3. **Marketing pages deprioritized** — graduation demo should land directly on Editor
4. **Reduce chrome** — remove decorative blur orbs on editor page
5. **Information density** — suggestion cards show type badge + original → correction + one-line reason

### 5.3 Editor Page Default Route

Change primary CTA and nav default for demo: `showPage('editor')` or URL hash `#/editor`.

---

## 6. Theme System (Phase 2.3)

### 6.1 Implementation Plan

```javascript
// js/theme.js
const THEME_KEY = 'bayan-theme';

function getPreferredTheme() {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(THEME_KEY, theme);
  updateThemeToggleIcon(theme);
}

function initTheme() {
  setTheme(getPreferredTheme());
}
```

### 6.2 Requirements Checklist

- [ ] Theme switcher in header (sun/moon icon button)
- [ ] Persist via `localStorage` key `bayan-theme`
- [ ] No page reload — toggle `data-theme` on `<html>`
- [ ] Editor surface, highlights, sidebar all respond to theme
- [ ] Respect `prefers-color-scheme` on first visit
- [ ] `color-scheme: dark` / `light` meta for native scrollbars

### 6.3 Theme Toggle UI

```
Dark active:  [☀️] aria-label="التبديل إلى الوضع الفاتح"
Light active: [🌙] aria-label="التبديل إلى الوضع الداكن"
```

---

## 7. Editor UX Improvements (Phase 2.4)

Inspired by Grammarly/LanguageTool patterns (not copied):

| Feature | Current | Proposed |
|---------|---------|----------|
| Placeholder | Invisible | Italic muted text via `[data-empty]::before` |
| Focus | Blue ring on white box | Theme-aware ring `ring-2 ring-accent/50` |
| Highlights | Static underline | Hover brightens + cursor pointer; active suggestion pulses once |
| Tooltip | Basic div | Popover with type icon, correction, "تطبيق" button, dismiss |
| Suggestion cards | Empty static | Live list; click scrolls to highlight in editor |
| Empty states | Generic checkmark SVG | Illustrated empty editor + "ابدأ بكتابة جملة عربية" |
| Analysis feedback | None | Subtle pulse on stats bar during API call |
| Apply all | Missing | Button when ≥2 suggestions |
| Keyboard | None | `Escape` dismiss popover; `Enter` apply; arrow keys navigate list |

### 7.1 Writing Score Formula

```
score = 100 - (spelling × 8) - (grammar × 6) - (punctuation × 3)
floor = 0, ceiling = 100
```

Display with animated SVG ring (`stroke-dashoffset` transition 600ms).

### 7.2 Suggestion Card Design

```
┌─────────────────────────────────────┐
│ [🔴 إملائي]                    [✓]  │
│ الصحيحه  →  الصحيحة                 │
│ التاء المربوطة مع الصفات المؤنثة    │
└─────────────────────────────────────┘
```

---

## 8. Responsive Design (Phase 2.5)

### 8.1 Breakpoints

| Name | Width | Layout |
|------|-------|--------|
| Mobile | <640px | Single column; bottom sheet for suggestions |
| Tablet | 640–1023px | Editor full width; sidebar below editor |
| Laptop | 1024–1279px | 7/5 column split |
| Desktop | ≥1280px | 8/4 column split (current) |

### 8.2 Requirements

- [ ] No horizontal scrolling at any breakpoint
- [ ] Toolbar wraps: tabs left, word count right; buttons stack on mobile
- [ ] Editor `min-height`: 50vh mobile, 60vh tablet, 500px desktop
- [ ] Touch targets ≥44×44px on mobile
- [ ] Suggestion panel → `BottomSheet` component below 1024px

### 8.3 Mobile Navigation

Hamburger → slide-in drawer from right (RTL), with focus trap and `aria-expanded`.

---

## 9. Accessibility Audit (Phase 2.6)

### 9.1 Current State (Failures)

| Criterion | Status | Issue |
|-----------|--------|-------|
| Keyboard navigation | ❌ | Cannot reach suggestions without mouse |
| Focus indicators | ⚠️ | Editor only; nav buttons lack `:focus-visible` |
| ARIA labels | ❌ | No labels on icon buttons, editor, or panels |
| Color contrast | ⚠️ | `--text-secondary` #cbd5e1 on #0f172a = 8.1:1 ✅; yellow grammar on white = 2.8:1 ❌ |
| Screen reader | ❌ | contenteditable changes not announced; suggestions not in live region |
| Motion | ⚠️ | `animate-float` and `hover:scale-105` — need `prefers-reduced-motion` |

### 9.2 Remediation Plan

```html
<!-- Editor -->
<div id="editor-container"
  role="textbox"
  aria-multiline="true"
  aria-label="محرر النص العربي"
  aria-describedby="editor-hint"
  contenteditable="true">
</div>
<p id="editor-hint" class="sr-only">اكتب نصاً عربياً. ستظهر الاقتراحات تلقائياً.</p>

<!-- Suggestions live region -->
<div id="suggestions-list" role="list" aria-live="polite" aria-label="اقتراحات التصحيح">

<!-- Theme toggle -->
<button aria-label="تبديل السمة" aria-pressed="false">
```

### 9.3 Contrast Validation Targets (WCAG AA)

| Pair | Dark Theme | Light Theme | Target |
|------|------------|-------------|--------|
| Body text / background | 15.4:1 ✅ | 16.1:1 ✅ | ≥4.5:1 |
| Grammar highlight text | 4.6:1 ✅ | Fix to amber-700 | ≥4.5:1 |
| Placeholder / surface | 4.8:1 ✅ | 4.5:1 ✅ | ≥4.5:1 |
| Error highlight | 5.2:1 ✅ | 5.8:1 ✅ | ≥3:1 (UI) |

### 9.4 Keyboard Map

| Key | Action |
|-----|--------|
| Tab | Navigate toolbar → editor → suggestion list |
| Enter | Apply focused suggestion |
| Escape | Close popover / mobile drawer |
| ↑/↓ | Navigate suggestion list |

---

## 10. Performance Audit (Phase 2.7)

### 10.1 Current Measurements

| Metric | Value | Assessment |
|--------|-------|------------|
| `index.html` size | 59 KB (1,033 lines) | Large monolith — split recommended |
| JS modules total | 21.5 KB (4 files) | Acceptable |
| Tailwind | CDN runtime compile | ~300ms first paint penalty |
| Google Fonts | 2 families (Tajawal + Noto Kufi) | Reduce to 1 (Cairo) |
| Analyze debounce | 500ms | Good UX balance |
| API `/api/analyze` | Spelling + Grammar + Punctuation sequential | Bottleneck when models loaded |

### 10.2 Estimated Latency (when all models loaded)

| Step | Typical Time | Notes |
|------|--------------|-------|
| Spelling inference | 1–4s | BERT seq2seq on CPU |
| Grammar inference | 3–8s | Gemma on CPU |
| Punctuation | 1–3s | Seq2Seq |
| **Total API** | **5–15s** | User sees no loading indicator |
| Render (client) | <16ms | Offset renderer is fast |
| DOM update + selection restore | <5ms | Efficient |

### 10.3 Bottlenecks

1. **No loading state** during analysis — user may think app is frozen
2. **Sequential model pipeline** on backend — cannot fix in Phase 2 (backend out of scope) but UI can show per-step progress
3. **Tailwind CDN** — compiles on every page load
4. **Monolithic HTML** — parses entire marketing pages even on editor route
5. **Full re-render** on every keystroke (after debounce) — acceptable for <5000 chars

### 10.4 Optimization Suggestions (Phase 2 scope)

| # | Suggestion | Impact | Effort |
|---|------------|--------|--------|
| O1 | Add analysis loading indicator + disable duplicate requests | High UX | Low |
| O2 | Extract CSS to external file (cacheable) | Medium | Low |
| O3 | Single font family (Cairo only) | Low-Medium | Low |
| O4 | `prefers-reduced-motion` disable animations | A11y | Low |
| O5 | Lazy-load marketing page content | Medium | Medium |
| O6 | Request cancellation via `AbortController` on rapid typing | Medium | Medium |
| O7 | Virtualize suggestion list when >50 items | Low | Medium |

---

## 11. Implementation Roadmap

### Phase 2.1 — Design System (2 days)
1. Create `css/tokens.css`, `base.css`, `components.css`
2. Add Cairo font; remove Noto Kufi Arabic
3. Document tokens in this file

### Phase 2.2 — Layout Redesign (2 days)
1. Extract header, editor layout, footer components
2. Wire sidebar to live data
3. Simplify home page for demo

### Phase 2.3 — Theme System (1 day)
1. Implement `theme.js`
2. Add toggle to header
3. Theme all surfaces including editor

### Phase 2.4 — Editor UX (2 days)
1. Placeholder CSS
2. SuggestionPopover component
3. SuggestionCard list + score ring
4. Fix summarize tab bug

### Phase 2.5 — Responsive (1 day)
1. Mobile nav + bottom sheet
2. Breakpoint testing

### Phase 2.6 — Accessibility (1 day)
1. ARIA layer
2. Keyboard navigation
3. `prefers-reduced-motion`
4. Contrast fixes for grammar highlight

### Phase 2.7 — Performance + Screenshots (1 day)
1. Loading states + AbortController
2. External CSS
3. Capture before/after screenshots for documentation

**Total estimate**: ~10 working days

---

## Before/After Screenshots Plan

Screenshots will be captured during implementation (Phase 2.7):

| Screen | Before | After |
|--------|--------|-------|
| Editor dark | Current white-on-dark | Theme-unified dark editor |
| Editor light | N/A (doesn't exist) | Professional document mode |
| Mobile editor | Broken nav | Bottom sheet suggestions |
| Suggestion popover | Basic tooltip | Rich popover with type badge |
| Empty state | Blank white box | Illustrated placeholder |

Store in `docs/screenshots/phase2/` as PNG files.

---

## Approval Gate

**No implementation code will be written until this design plan is reviewed.**

Please confirm:
1. Font choice (Cairo primary) — or prefer IBM Plex Sans Arabic for editor?
2. Default theme for graduation demo (dark vs light)?
3. Should marketing pages (Home/Features/Pricing) be simplified or kept as-is?
4. Proceed with file split (`css/`, `js/components/`) or keep monolithic `index.html`?

---

*Generated from Phase 1 completion state (June 15, 2026). Preserves all offset-based editor functionality.*
