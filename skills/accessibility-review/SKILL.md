---
name: accessibility-review
description: Use when auditing a React codebase for WCAG AA accessibility issues — interactive labelling, sortable table aria-sort, keyboard access on click handlers, nav landmarks, heading hierarchy, SVG semantics, colour contrast, and form labels.
---

# Accessibility Review

Systematic WCAG AA audit for a React frontend. Work through each section; fix issues as you find them.

## 1. Interactive element labels

Every interactive element needs an accessible name via one of:
- Visible text content
- `aria-label` on the element
- `aria-labelledby` pointing to visible text

**Icon + visible text** — icon gets `aria-hidden="true"`; the text is the accessible name. No `aria-label` needed on the control.

**Icon-only controls** (no visible text) — `aria-label` on the control, `aria-hidden="true"` on the icon.

## 2. Sortable table headers (`aria-sort`)

`<th>` elements with click-to-sort **must** carry `aria-sort`. Without it, screen readers cannot announce sort state.

```tsx
<th
  aria-sort={
    header.column.getIsSorted() === 'asc'
      ? 'ascending'
      : header.column.getIsSorted() === 'desc'
      ? 'descending'
      : 'none'
  }
  onClick={header.column.getToggleSortingHandler()}
>
```

Use `'none'` (not omit) for unsorted columns — omitting leaves the attribute ambiguous.

**Keyboard access:** `onClick` on a `<th>` is not keyboard accessible. Wrap the header content in a `<button>` or add `onKeyDown` alongside `onClick`.

## 3. Nav landmarks

Any `<nav>` element should carry `aria-label` to identify it:

```tsx
<nav aria-label="Main navigation">
```

Required when more than one `<nav>` appears; recommended even for a single nav.

## 4. Heading hierarchy

- `<h1>` — site/app title (sidebar brand or `<title>`)
- `<h2>` — page title (`PageTitle` component)
- `<h3>` — section title (`SectionTitle` component)

Never skip levels (e.g. `<h1>` → `<h3>`). Verify `PageTitle` renders `<h2>` and `SectionTitle` renders `<h3>`. If there is no `<h1>` on screen, the sidebar brand name is a natural candidate.

## 5. SVGs and decorative images

- Decorative icons (beside visible text): `aria-hidden="true"` ✓
- Meaningful charts/diagrams: wrap in `<figure aria-label="Description of chart">` so screen readers announce the chart's purpose

## 6. Colour contrast

WCAG AA thresholds:
- Normal text: **4.5:1** minimum
- Large text (≥18pt / ≥14pt bold) and UI components: **3:1** minimum

Common failure: muted placeholder/empty-state text. `text-gray-400` (`#9CA3AF`) on `bg-gray-50` (`#F9FAFB`) is approximately **1.9:1** — fails AA. Use `text-gray-500` (`#6B7280`) minimum, which gives ~**4.6:1** on white.

Tailwind safe combinations (light mode on white/gray-50):
| Class | Ratio | Pass |
|---|---|---|
| `text-gray-500` | ~4.6:1 | ✓ AA normal |
| `text-gray-400` | ~1.9:1 | ✗ Fails |

## 7. Form inputs

Every `<input>`, `<select>`, `<textarea>` needs an associated label:

```tsx
<label htmlFor="field-id">Label text</label>
<input id="field-id" ... />
// or
<input aria-label="Label text" ... />
```

## After fixing: document conventions in AGENTS.md

Add an `## Accessibility` section covering:

- Every interactive element must have an accessible name
- Icon-only controls: `aria-label` on the element, `aria-hidden="true"` on the icon
- Icon + text controls: `aria-hidden="true"` on the icon only; text provides the accessible name
- `<nav>` landmarks must carry `aria-label`
- Sortable `<th>` elements must carry `aria-sort` (`"ascending"` / `"descending"` / `"none"`)
- Heading hierarchy: `<h1>` site title, `PageTitle` → `<h2>`, `SectionTitle` → `<h3>` — never skip levels
- Placeholder/empty-state text: use `text-gray-500` minimum (not `text-gray-400`) to meet contrast
