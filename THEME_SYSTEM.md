# Bayan Theme System — Implementation Reference

**Status**: Implemented  
**Source of truth**: `src/css/tokens.css`  
**Consumers**: `src/css/base.css`, `src/css/components.css`

All editor UI consumes CSS variables. Do not hardcode hex/rgba in components.

---

## Theme Switching

- Attribute: `data-theme="dark"` | `data-theme="light"` on `<html>`
- Persistence: `localStorage` key `bayan-theme`
- Script: `src/js/theme.js`

---

## Token Map

| Category | Variable | Dark | Light |
|----------|----------|------|-------|
| Background | `--color-bg` | `#0B1120` | `#F8FAFC` |
| Surface | `--color-surface` | `#151D2E` | `#FFFFFF` |
| Elevated | `--color-surface-elevated` | `#1E293B` | `#F1F5F9` |
| Editor | `--color-editor` | `#1A2332` | `#FFFFFF` |
| Primary | `--color-primary` | `#3B82F6` | `#2563EB` |
| Secondary | `--color-secondary` | `#8B5CF6` | `#7C3AED` |
| Accent | `--color-accent` | `#06B6D4` | `#0891B2` |
| Success | `--color-success` | `#22C55E` | `#16A34A` |
| Warning | `--color-warning` | `#F59E0B` | `#D97706` |
| Error | `--color-error` | `#EF4444` | `#DC2626` |
| Text | `--color-text-primary` | `#F1F5F9` | `#0F172A` |
| Text secondary | `--color-text-secondary` | `#94A3B8` | `#475569` |
| Text muted | `--color-text-muted` | `#64748B` | `#64748B` |
| Border | `--color-border` | `rgba(255,255,255,0.08)` | `rgba(15,23,42,0.08)` |
| Border strong | `--color-border-strong` | `rgba(255,255,255,0.16)` | `rgba(15,23,42,0.16)` |
| Focus ring | `--focus-ring` | `rgba(59,130,246,0.45)` | `rgba(37,99,235,0.35)` |

---

## Highlights

| Type | Dark bg | Dark border | Light bg | Light border |
|------|---------|-------------|----------|--------------|
| Spelling | `rgba(239,68,68,0.18)` | `#EF4444` | `#FEF2F2` | `#DC2626` |
| Grammar | `rgba(245,158,11,0.18)` | `#F59E0B` | `#FFFBEB` | `#D97706` |
| Punctuation | `rgba(34,197,94,0.18)` | `#22C55E` | `#F0FDF4` | `#16A34A` |

Tokens: `--highlight-{type}-bg`, `--highlight-{type}-border`

---

## Typography

Font stack: `Cairo` → `Tajawal` → `Noto Sans Arabic`

| Role | Token | Value |
|------|-------|-------|
| Display | `--font-size-display` | 48px / 700 |
| H1 | `--font-size-h1` | 36px / 700 |
| H2 | `--font-size-h2` | 30px / 600 |
| H3 | `--font-size-h3` | 20px / 600 |
| Body | `--font-size-body` | 16px / 400 |
| Editor | `--font-size-editor` | 18px / 400 |
| Caption | `--font-size-caption` | 14px / 500 |
| Label | `--font-size-label` | 12px / 600 |
| Editor line-height | `--line-height-editor` | 1.9 |

Utility classes: `.text-display`, `.text-h1`, `.text-body`, `.text-secondary`, `.text-muted`, etc.

---

## Component Guidelines (enforced in CSS)

- **Cards**: `--radius-card` (16px), `--shadow-card`, `--color-border`
- **Editor**: `--color-editor`, `--shadow-editor`, no pure black/white text
- **Buttons**: min-height 44px, `--color-text-inverse` on primary
- **Popovers**: `--shadow-popover`, opacity transition
- **Loading**: `--color-accent` spinner
- **Overlays**: `--color-overlay`

---

## Legacy Aliases

For Element SDK and marketing pages:

`--primary-color`, `--text-color`, `--background-color`, `--surface-color` → map to canonical tokens.

---

## Remaining Hardcoded Colors

Marketing pages in `index.html` (Home, Features, Pricing) still use inline `style=""` with hex values. Editor and shell are fully tokenized. Migrate marketing sections to `.marketing-card`, `.feature-icon--*`, `.demo-callout--*` utilities when simplifying those pages.
