# Ochorus — Style Guide

The canonical reference for Ochorus's visual design. **Every page, control, and
component should follow this guide so the product feels like one consistent
whole.** When something here conflicts with a one-off in the code, this guide
wins — fix the code.

The single source of truth in code is **`frontend/src/app.css`** (design tokens +
component classes). This document explains and governs it.

> **Shared design system with [Take Root](https://takeroot.bible).** Ochorus and
> Take Root are sibling apps and deliberately share one look and feel — the same
> **colour tokens, typefaces, type scale, spacing, radii, and component
> philosophy**. The tokens in §1–§3 are kept **identical** across both repos; when
> one changes a shared value, change it in both. UI patterns (nav, menus, cards,
> buttons, empty states) should match Take Root's unless the reading domain
> genuinely demands otherwise.

> **Brand metaphor — the ONE deliberate difference.** Each app carries its own
> theme through iconography, illustration, naming, empty states, and microcopy:
>
> - **Take Root** — *gardening & growth*: plant a seed, take root, grow, bear
>   fruit. Sprouts, leaves, trees, watering, harvest.
> - **Ochorus** — *books & learning*: book, library, shelf, page, bookmark,
>   study, learn, read. Open books, bookmarks, reading lamps, shelves, scrolls,
>   marginalia.
>
> When Take Root would reach for a sprout, Ochorus reaches for a bookmark. New
> icons, illustrations, feature names, and copy should draw from the reading/
> library register — never the garden one (and vice versa in Take Root).

> **Design direction — "Quiet Devotional."** Warm, calm, and reverent. The **text
> is the hero**; the UI is a quiet frame around it. Soft over bold, tinted over
> loud, generous whitespace, a printed-page feeling for the reading itself.

---

## 1. Color

Colors are **semantic tokens**, defined once in `app.css` and switched at runtime
between two themes via `[data-theme]`. **Never hardcode a hex value in a component**
— always use a token (`var(--…)` or the Tailwind `*-surface` / `*-accent` / etc.
utilities that map to them).

Default theme is **Lamplight** (dark); `[data-theme='light']` is **Paper**. These
values are identical to Take Root's.

| Token | Role | Lamplight (dark) | Paper (light) |
|---|---|---|---|
| `--bg` | Page background | `#16130f` | `#faf6ef` |
| `--surface` | Card / input surface | `#201b15` | `#ffffff` |
| `--surface-2` | Recessed / neutral button | `#2a241c` | `#f4eee3` |
| `--text` | Primary text | `#ece3d4` | `#221c15` |
| `--muted` | Secondary text | `#998e7d` | `#6e6358` |
| `--accent` | Brand indigo (links, primary) | `#9c9af2` | `#3f3d9a` |
| `--accent-contrast` | Text on solid accent | `#16130f` | `#ffffff` |
| `--accent-soft` | Soft indigo fill | `#221f33` | `#ecebf7` |
| `--accent-soft-border` | Soft indigo border | `#36324f` | `#d9d7f0` |
| `--gold` | Secondary accent (eyebrows, marks) | `#e0b45c` | `#b07d22` |
| `--border` | Hairlines, dividers | `#2d261d` | `#e8dfcf` |
| `--danger` | Errors, destructive | `#e8857a` | `#b23a48` |

**Indigo + gold** is the signature pairing: indigo for interaction/primary, gold
for accents, eyebrows, and reading marks (highlights). Use gold sparingly — it's a
spice, not a base.

### Rules
- ✅ Use a token for every color. ✅ Both themes must be checked.
- ✅ External brand colors (e.g. a vendor sign-in button) are the only allowed raw
  hex, and only on that vendor's control.
- ✅ A generated book cover with no artwork may use its per-book `cover_color` —
  that's data, not a UI color.
- ❌ No raw hex in routes/components for UI color. ❌ No new ad-hoc greys/indigos —
  extend the token set instead (and mirror it into Take Root).

---

## 2. Typography

Two typefaces, loaded as variable woff2 (plus OpenDyslexic as a reader option):

- **Fraunces** (`--font-display`) — the serif. Headings, the wordmark, and the
  **reading prose itself**. Warm, literary, devotional.
- **Hanken Grotesk** (`--font-sans`) — the sans. All UI, body, labels, controls.

Headings are weight **600**. Body is normal. Never set headings in the sans, or UI
body in the serif (long-form reading prose is the deliberate exception).

### Type scale — modular ratio 1.25 (major third), anchored at 1rem

Use the `--fs-*` tokens or the `.text-*` utility classes. **Never invent a size
with `text-[1.02rem]`-style arbitrary values** — pick the nearest step.

| Token / class | Size | Line-height | Use |
|---|---|---|---|
| `.text-display` / `--fs-display` | `clamp(2rem, 5vw, 2.75rem)` | 1.1 | Hero only |
| `.text-h1` / `--fs-h1` | `1.953rem` | 1.15 | Page title (`<h1>`) |
| `.text-h2` / `--fs-h2` | `1.563rem` | 1.2 | Section (`<h2>`) |
| `.text-h3` / `--fs-h3` | `1.25rem` | 1.3 | Sub-section (`<h3>`) |
| `.text-body` / `--fs-body` | `1rem` | 1.6 | Body |
| `.text-small` / `--fs-small` | `0.875rem` | 1.5 | Captions, helper, eyebrows |
| `--fs-eyebrow` | `0.75rem` | — | Eyebrows / kickers |

- **Reading prose** uses `.reading`: the serif at `1.18rem × --reading-scale`,
  leaded generously. Typeface, size, leading, and measure are reader-controllable
  (see `readerPrefs`) via `--reading-font / --reading-scale / --reading-leading /
  --reading-measure` — components read those custom properties, never hardcode.
- **Eyebrows/kickers** (e.g. "CHAPTER 1 · 7 MIN READ") are `0.75rem`, uppercase,
  `letter-spacing ~0.08em`, muted.
- Constrain the reading column to a comfortable measure — the reader's **Width**
  control (narrow / normal / wide) maps to `--reading-measure`; `normal` is `42rem`.

---

## 3. Spacing, radius & layout

- **Radius:** `--radius` = **12px** (`--radius-card`, cards/banners), `--radius-sm`
  = **9px** (buttons, inputs), `999px` for pills.
- **Spacing:** keep to a small rhythm — `4 / 8 / 12 / 16 / 24 / 40px`
  (Tailwind `1 / 2 / 3 / 4 / 6 / 10`). Avoid arbitrary `mb-[13px]`-style gaps.
- **Page column — one width, everywhere.** Every top-level browse surface wraps
  its content in **`.page-col`**. Do **not** give a page its own `mx-auto
  max-w-*`.

  > This rule replaces the old "max-w-2xl/3xl/5xl per surface" guidance, which
  > licensed exactly the drift it was meant to prevent: the six browse pages
  > ended up at five different widths (Books `6xl`, Topics `5xl`, Biographies
  > `4xl`, Plans/Sermons `3xl`, Home a mix), so the content edge jumped on every
  > navigation.

  `.page-col` reads `--pw` from the **`pageWidth`** store — five steps,
  48/62/76/90/104rem, default 76rem — which the quick-settings **Page width**
  stepper drives. It breaks out of its container and centres on the viewport,
  direction-aware so RTL doesn't shift sideways.

  The exceptions are genuine prose blocks, not page shells: the home hero's
  centred text and empty-state copy keep their own narrower measure.
- **Reading measure** is separate. `--reading-measure` (from
  `readerPrefs.measure`) governs the prose column *inside* a chapter and is
  capped near 52rem for readability. Don't conflate the two: page width is
  chrome, reading measure is typography.
- **Focus mode:** the reader's immersive toggle (`readerUi`) collapses the global
  header/footer and reader chrome to just the text, for a calm flow.

---

## 4. Iconography

Ochorus uses an **inline-SVG line-icon set**, served by `Icon.svelte`: 24-unit
viewBox, no fill, `currentColor` stroke **1.8**, round caps/joins, inheriting
text colour. Add new glyphs to that component's `IconName` union rather than
importing an icon font, an image file, or a second library.

Always pair an icon-only control with an `aria-label`.

Do **not** import Take Root's garden/growth illustrations; that botanical
imagery is Take Root's brand surface, not Ochorus's. Ochorus draws from the
reading/library register (see the brand-metaphor note at the top).

---

## 5. Components

### Buttons — one soft, consistent family

Three roles, all sharing the `.btn` base (`--radius-sm`, `0.6rem 1.1rem` padding,
weight 600, a 150ms transition).

| Role | Class | Fill | Text | Border | When |
|---|---|---|---|---|---|
| **Primary** | `.btn .btn-primary` | `--accent-soft` | `--accent` | `--accent-soft-border` | The main action on a view (one per context) |
| **Default** | `.btn` | `--surface-2` | `--text` | `--border` | Secondary actions |
| **Ghost** | `.btn .btn-ghost` | transparent | `--muted`/`--text` | transparent | Low-emphasis (dismiss, back) |

- **Primary is soft, not bold** — a brand-tinted button (accent-soft fill, accent
  text, `--accent-soft-border`), never a solid filled indigo block. It reads as
  "the main thing" without shouting.
- Hover: default → `--surface` + accent-soft border; primary → border to `--accent`.
- ❌ Don't invent bespoke button styles per page — extend the system.

### Page header

Every top-level browse page uses **`<PageHeader>`** — optional eyebrow, `<h1>`,
optional tagline, optional counts line. Don't hand-roll a header; the six pages
previously had six sets of margins and two different title sizes.

The `<h1>` is **`.text-h1`**. `.text-display` is the **home hero only**.

### Cards

Two families, both `--surface` fill, `--border`, `--radius-card` (12px).

**Shelf card** (`<ShelfCard>` / `.shelf-card`) — the colour-washed card used by
Topics, Plans and Sermons: a tinted band carrying an icon chip (or a portrait)
and a fan of covers, over a typographic body. Each card sets `--shelf-hue`, used
**only through `color-mix()`** for tints and the icon, never as body text, so
contrast holds in both themes. Hues come from:

| Surface | Hue source |
|---|---|
| Topics | `topicMeta(slug).accent` — curated per topic |
| Plans | `accentForSlug(slug)` — stable pick from the same palette |
| Sermons | `hueForBirthYear(author.birth_year)` — the writer's era |

Use **`.shelf-card--static`** when the card is a container rather than a link
(it holds its own links). It sizes to content instead of filling the grid row.

**Book card** (`.book-card`) — the cover is the visual, so the chrome stays
quiet: hairline, surface fill, no colour wash.

**Equal heights.** For grids of *similar* cards (topics, plans, books) use
`items-stretch` and let `.shelf-card`/`.book-card`'s `height:100%` plus an
`mt-auto` footer level the bottoms; clamp descriptions with `.shelf-card-desc`.
For grids whose cards hold **variable-length lists** (sermons), use
`items-start` **and** `.shelf-card--static` — stretching those left 700px of
dead space under the short ones. Note `items-start` alone is not enough: a
percentage height still resolves against the grid row.

### Filter controls

One family for every browse page's filter row: **`.filter-row`** (the wrapper),
**`.filter-field`** (inputs and selects; add `.grow` to the free-text one),
**`.seg`** (segmented toggle, active option gets `.active`), **`.chip`** (filter
pills, active gets `.active`).

Active states are **soft** (`--accent-soft` fill, `--accent` text) — never a
solid `bg-accent` block.

### Inputs
`--surface` fill, `--border`, `--radius-sm`. Focus uses the global `:focus-visible`
ring (2px accent outline). Labels/placeholders are muted. The search box and the
note editor follow this.

### Navigation
Sticky top bar: `--bg/90` with backdrop blur and a hairline bottom border. Wordmark
left; destinations (About / Books / Biographies / Contact) with active =
`--text`; right cluster holds search, language picker, theme toggle, account menu.
Active link carries `aria-current="page"`. Hidden in reader focus mode.

### Footer
Compact and identical on every page: wordmark + one-line mission, an "Explore" link
group, and contact. Hidden in focus mode.

### Reader surfaces (Ochorus-specific)
- **Reader controls popover** (`ReaderControls`): size / spacing / width / typeface,
  in a `--surface` card; the active option in each group is accent-outlined.
- **Selection bar** (`SelectionBar`): floating `--surface` toolbar on text
  selection — Copy quote, Share, Highlight, Note.
- **Marks**: paragraph highlights use a soft **gold** wash (`--gold`, low alpha);
  notes get a gold left-border. Gold = the reading-mark colour, matching Take Root.
- **Breadcrumb / sticky context**: muted breadcrumb (`Books › Author › Book`); once
  the chapter title scrolls off, the sticky bar shows it.

---

## 6. Accessibility

- **Contrast:** target WCAG **AA** (4.5:1 text) in **both** themes. Verify
  muted-on-bg and accent-on-surface pairings when adding them.
- **Focus:** every interactive element has a visible focus ring
  (`:focus-visible` → 2px accent outline, 2px offset). Don't remove it.
- **Names:** icon-only controls get an `aria-label`; nav/footer link groups are
  labelled; async results (search) should be discoverable.
- **Motion:** respect `prefers-reduced-motion` (a global block disables
  transitions/animations under it).

---

## 7. Motion

Quiet and quick: 120–240ms ease for hover/reveal. Nothing bouncy. All motion
should be disabled under `prefers-reduced-motion`.

---

## 8. Enforcement checklist

Before any UI change ships, it must:

1. **Use tokens for every color** — no raw hex (except a vendor's own brand control
   or a book's `cover_color`).
2. **Use the type scale** (`--fs-*` / `.text-*`) — no arbitrary `text-[…]` sizes.
3. **Use the button/card/input system** — no bespoke one-off controls.
4. **Keep primary actions soft** (accent-soft), never solid-indigo blocks.
5. **Work in both themes** with AA contrast and a visible focus state.
6. **Match icon weight** (currentColor, stroke 1.8) and the spacing rhythm.
7. **Keep shared tokens (§1–§3) identical to Take Root** — change both repos together.
8. **Verify** on the relevant page(s) in light + dark before merge.

---

## 9. Current compliance (snapshot)

The colour, type, and layout foundations are **shared with Take Root and in place**.
Known gaps to close (tracked as follow-ups):

- ✅ **Colour tokens, typefaces, type scale, radii** — identical to Take Root.
- ✅ **Themes, focus rings, nav, footer, reader focus mode** — in place.
- ✅ **Soft primary button** — `.btn-primary` now uses the soft treatment
  (accent-soft fill, accent text, `--accent-soft-border`), matching §5 / Take Root.
- ✅ **`prefers-reduced-motion`** — honoured by a global block that disables
  transitions/animations under it.
- ✅ **Icons** — a real inline-SVG line set (`Icon.svelte`), stroke 1.8,
  `currentColor`. The old Unicode-glyph note is retired.
- ✅ **One page width** — every browse surface uses `.page-col`, driven by the
  `pageWidth` store (#718).
- ✅ **One page header + one title size** — `<PageHeader>` across the browse
  pages; `.text-display` is the home hero only (#720).
- ✅ **One filter-control family** — `.filter-row` / `.filter-field` / `.seg` /
  `.chip`, soft active states (#720).
- ✅ **One card language** — `.shelf-card` (Topics, Plans, Sermons) and
  `.book-card`, with levelled heights.
- ⚠️ **Class naming** differs slightly from Take Root (`.btn-primary`/`.btn-ghost`
  vs `.primary`/`.ghost`) — harmless, but worth converging if the systems merge.
- ⚠️ **Detail pages still use `.text-display`** for their titles
  (`topics/[slug]`, `biographies/era/[era]`), as does `/notebook` and the admin
  surface. Deliberate for now — a different class of page — but they should get
  a pass of their own.
- ⚠️ **Cover art** — roughly half the library's covers are generated
  typographic placeholders rather than artwork. A content problem, not a CSS
  one, but it is the biggest thing holding the shelf back visually.
- ❌ **No automated guard.** Nothing stops a new page hand-rolling its own
  shell, header or filter row; the rules above are convention only. A CI check
  asserting browse pages use `.page-col` + `<PageHeader>` is the obvious next
  step.

_Last reviewed: 2026-08-01. Update this section as gaps close._
