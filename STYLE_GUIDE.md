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
| `--border-strong` | Interactive control edges | `#7c7060` | `#968462` |
| `--danger` | Errors, destructive | `#e8857a` | `#b23a48` |
| `--warning` | Caution / needs attention | `#e0b45c` | `#7d5815` |

**Indigo + gold** is the signature pairing: indigo for interaction/primary, gold
for accents, eyebrows, and reading marks (highlights). Use gold sparingly — it's a
spice, not a base.

**Gold is ornament, never a message.** It measures 3.4–3.6:1 as text in the paper
and sepia themes, i.e. under AA, so anything that *says something* — a warning, a
status, "awaiting native review" — takes `--warning`, not `--gold`. Gold stays on
graphics and decoration: reading marks, the heatmap, the streak flame, the prefs
gear, hairline rules, the pull-quote bar. In lamplight `--warning` coincides with
gold, which already clears AA there; paper and sepia darken it until it does —
far enough to clear 4.5:1 against a `bg-warning/10` wash as well as a flat
surface, since the "awaiting native review" badge sets the ink on its own tint.

**`--border` is a hairline; `--border-strong` is an edge.** `--border` sits at
1.1–1.4:1 against its surfaces, which is right for a divider and far below the
3:1 that WCAG 1.4.11 asks of a control's boundary. Any control whose *only*
affordance is its outline — text inputs, selects, `.filter-field`, `.seg`,
`.chip`, `.widthctl` — uses `--border-strong`. Buttons keep `--border`: they are
identified by fill and label, and a strong edge on `.btn-ghost` makes the
low-emphasis button compete with the primary one beside it.

### Rules
- ✅ Use a token for every color. ✅ All **three** themes must be checked —
  lamplight, paper *and* sepia. Sepia is the one that has actually failed.
- ✅ External brand colors (e.g. a vendor sign-in button) are the only allowed raw
  hex, and only on that vendor's control.
- ✅ A generated book cover with no artwork may use its per-book `cover_color` —
  that's data, not a UI color. It is still **floored for contrast** when it is
  minted (`covers.ink_safe`, applied by `palette_from_artwork` and the admin
  import): the type on a plate is always white, so a colour too pale to carry a
  23px byline at 4.5:1 is darkened until it can. Data chooses the hue; the floor
  keeps it legible, and `CoverAssetTests` fails a stored colour that isn't.
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
| `.text-small` / `--fs-small` | `0.875rem` | 1.5 | Captions, helper text, meta |
| `.text-eyebrow` / `--fs-eyebrow` | `0.75rem` | 1.4 | Eyebrows / kickers |
| `.text-micro` / `--fs-micro` | `0.6875rem` | 1.4 | Dense micro-labels only |

`--fs-micro` is the floor, added for the one cluster that genuinely needed a
step below the eyebrow — heatmap day labels, cover badges, dense meta rows,
several of them width-constrained, where 0.75rem overflows. Reach for it only
when `--fs-eyebrow` has been tried and does not fit.

- **Reading prose** uses `.reading`: the serif at `1.18rem × --reading-scale`,
  leaded generously. Typeface, size, leading, and measure are reader-controllable
  (see `readerPrefs`) via `--reading-font / --reading-scale / --reading-leading /
  --reading-measure` — components read those custom properties, never hardcode.
- **Eyebrows/kickers** (e.g. "CHAPTER 1 · 7 MIN READ") use **`.eyebrow`**:
  `0.75rem`, 600, uppercase, `letter-spacing 0.08em`. The class does not set a
  colour — an eyebrow is accent above a page title, muted in a popover, white on
  a cover scrim — so every call site states its own. Don't hand-roll the recipe;
  it had drifted to 61 copies with ~11 letter-spacings before it had a class.
- **`.section-label`** is the neighbouring pattern and a step larger
  (`--fs-small`, muted, with its own bottom margin): the label above a *block of
  content* ("Continue reading"), not the kicker above a title.
- Constrain the reading column to a comfortable measure — the reader's **Width**
  control (narrow / normal / wide) maps to `--reading-measure`; `normal` is `42rem`.

---

## 3. Spacing, radius & layout

- **Radius:** four values, no more. `rounded-card` / `--radius-card` = **12px**
  (cards, banners, panels), `rounded-sm` / `--radius-sm` = **9px** (buttons,
  inputs, chips-with-corners), `rounded-full` for pills, and `rounded-[2px]` on
  the heatmap's 11px cells, where 9px would round them into circles.

  > Both tokens live in `@theme`, which is how Tailwind's own `--radius-*`
  > namespace is meant to be replaced. Don't re-declare them in `:root`: that
  > shadows Tailwind's value by source order rather than replacing it, which is
  > what `--radius-sm` used to do, and a minor version bump could have flipped
  > every `rounded-sm` in the app at once. Don't write
  > `var(--radius-card, 12px)` either — the fallbacks that existed disagreed
  > with the real values and would have been wrong the moment they fired.
- **Spacing:** Tailwind's own steps, in two bands. Avoid arbitrary
  `mb-[13px]`-style gaps, and don't invent half-steps outside this list.

  | Band | Steps (Tailwind) | Pixels | Use |
  |---|---|---|---|
  | Component | `0.5 1 1.5 2 2.5 3 4 5 6` | 2–24px | Padding, gaps, label-to-field |
  | Page | `8 10 12 14 16 20` | 32–80px | Section rhythm, page top/bottom |

  > This replaces a six-step list (`1 / 2 / 3 / 4 / 6 / 10`) that the code had
  > never matched: roughly 360 uses of `5`, `1.5`, `8`, `2.5` and `0.5` sat
  > outside it, so neither a reviewer nor a codemod could tell deliberate
  > spacing from drift. The list above is what the app actually uses, with the
  > handful of true one-offs (`3.5`, `7`, `9`) folded into their neighbours. A
  > scale nobody follows is not a standard.

  `scroll-mt-*` is not spacing — it offsets an anchor jump for the sticky bar,
  and should track that bar's height rather than this rhythm.
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
- **Breakpoints:** use Tailwind's (`sm` 640, `md` 768, `lg` 1024, `xl` 1280),
  including in hand-written media queries — `max-width: 767.98px` rather than a
  bespoke 760px. The nav used to collapse at 760px while the markup above it
  reflowed at 768px, leaving a sliver where the two disagreed.
- **Reading measure** is separate. `--reading-measure` (from
  `readerPrefs.measure`) governs the prose column *inside* a chapter and is
  capped near 52rem for readability. Don't conflate the two: page width is
  chrome, reading measure is typography.
- **Focus mode:** the reader's immersive toggle (`readerUi`) collapses the global
  header/footer and reader chrome to just the text, for a calm flow.
- **Direction-aware by default — Arabic is a shipped locale.** Reach for the
  **logical** property, never the physical one: `padding-inline-start` not
  `padding-left`, `border-inline-start` not `border-left`, `inset-inline-start`
  not `left`, `margin-inline-start: auto` not `margin-left: auto`, and Tailwind's
  `ms-*`/`me-*`/`ps-*`/`pe-*` rather than `ml-*`/`mr-*`/`pl-*`/`pr-*`.

  A physical property doesn't *break* under `dir="rtl"` — it quietly puts the
  thing on the wrong side, which is why these survive review. The topic page's
  scripture epigraph carried its accent bar on `border-left` and so drew it on
  the far side of the Arabic text instead of the reading edge; the sermon row's
  era rail uses `inset-inline-start` and mirrors correctly. Check any new
  decorative edge, icon gap or auto-margin at `/ar/…` before shipping.

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

- **Sizes:** `.btn` is the default; add **`.btn-sm`** for a compact button and
  **`.btn-icon`** for a square icon-only one. Don't hand-roll padding — five
  different compact sizes existed before these did.
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

Four surfaces, all `--border` and `--radius-card` (12px). Three are a
`--surface` fill; the sermon plate's ground is its own hue wash.

**Which hue a surface wears** is not per-surface taste, it follows one rule:
**in a list, the hue tracks what the list is sorted or grouped by; standing
alone, an item wears the hue of its own art.** So the sermons index tints by
the preacher's era (that shelf reads as a timeline) while the same sermon's own
page and its Sermon-of-the-week panel tint from its emblem. That is why one
emblem can appear in two tints a click apart — it is the shelf's colour there
and its own colour here.

**Shelf card** (`<ShelfCard>` / `.shelf-card`) — the colour-washed card used by
Topics and Plans: a tinted band carrying an icon chip (or a portrait) and a fan
of covers, over a typographic body. Each card sets `--shelf-hue`, used **only
through `color-mix()`** for tints and the icon, never as body text, so contrast
holds in both themes. Hues come from:

| Surface | Hue source |
|---|---|
| Topics | `topicMeta(slug).accent` — curated per topic |
| Plans | `accentForSlug(slug)` — stable pick from the same palette |
| Sermon plate | `tintable(emblemHue(...))` — derived from the emblem's own art |
| Sermons index row | `hueForBirthYear(...)` — the preacher's era |

The band's far end takes a **fan of covers** (`covers`); the band does the
positioning, so an occupant only styles itself.

**Book card** (`.book-card`) — the cover is the visual, so the chrome stays
quiet: hairline, surface fill, no colour wash. Covers come in three tiers and
`BookCover` draws all of them: a **designed cover** (an image, with `srcset`
variants built by `scripts/build_cover_assets.py`), a **painting** under
`covers/art/` with the type drawn over it (one file per work, shared by every
language — a painting has no words, so it needs no translation), and the
**plate** for a book with no artwork: the book's colour, its title set as real
text, the emblem of its topic, and the lockup at the foot. The emblem is the
plate's SECOND variable — the colour already varies per book but the
composition didn't, so a grid of plates read as coloured slabs. It is the
drawing the book's topic already wears on the topics shelf, fitted to whatever
room the type leaves and omitted when there is none. (On a topic's own shelf
every book shares it, which is honest rather than useless: they do share the
topic, and that shelf is tinted for it anyway.) It is a placeholder in the house style, *not* a copy of the
generated cover — the copy it replaced drifted in every metric it duplicated and
never learned RTL or the non-Latin font stacks. Proportions may echo
`covers.py`; algorithms may not.

**Sermon plate** (`<SermonPlate>`) — a sermon's head, on its own page and in
Sermon of the week: the eyebrow/title/byline in a hue wash with the sermon's
emblem anchoring the far end, the same composition as its share card. Sermons
are **not** given 3:4 covers: that silhouette says *volume*, and differing
silhouettes are what tell a book from a sermon at a glance on a mixed shelf.
Its hue is `tintable(emblemHue(...))` — derived from the emblem's own art, so a
new sermon is coloured the moment its emblem is picked, then floored into a
lightness band, because a wash is only as visible as the hue is light.

The shelf card's band and the sermon plate share **`.hue-band`**, driven by
`--band-hue`: one wash rule, not one per surface. The topic hero still carries
its own, slightly weaker copy — see the note on `.hue-band` in `app.css`.

**Sermon row** (`.sermon-row`) — the sermons shelf is a **list, not a grid**:
one sermon per line, under its preacher, carrying the title, the passage it
expounds, the "In brief" and how long it runs. That is a deliberate exception to
the card families above, and the reason is the brief: it runs 300–400 characters,
a tile holding it is mostly body text with a title on top, and prose set across
the full page column is unreadable. A row lets the brief run the full
width of the box — spreading it over fewer lines keeps the shelf short — with
the reading length at the top right, opposite the passage. Row heights vary
freely — rows stack, so there is no bottom edge to level. `--row-hue` is the
writer's era (same source as a shelf card), used only through `color-mix()`.

> ⚠️ **A Tailwind utility cannot override one of these classes.** The component
> classes in `app.css` are **unlayered**; Tailwind's utilities live in
> `@layer utilities`, and unlayered CSS wins over layered CSS **whatever the
> specificity**. So `class="book-card flex-row"` silently keeps `column`.
>
> What makes this genuinely nasty is that `!important` utilities *do* win — so
> on `class="book-card flex-row !p-4"` the padding applies and the direction
> doesn't, and the element looks half-styled rather than obviously broken.
>
> Add a modifier next to the base class instead (`.book-card--row`). Reach for a
> utility only for properties the component class doesn't set — which is why
> `.sermon-row-brief` can take `line-clamp-5`: it sets no clamp of its own.

**Equal heights — one item per card, or bound the variance.** A card grid must
never set `items-start`; let `.shelf-card`/`.book-card`'s `height:100%` plus an
`mt-auto` footer level the bottoms. (`items-stretch` states it, but grid items
stretch by default, so the grids that omit it are fine as they are.)

That levelling only helps if no one card can tower over its row, so a card does
one of two things:

1. **Holds one item** — one topic, one plan, one book. Text still varies, but by
   a line or two, and the `mt-auto` footer absorbs it. Clamp long descriptions
   with `.shelf-card-desc`.
2. **Bounds every variable dimension inside it** — what `AuthorBioCard` does: the
   bio is `line-clamp`ed, the cover rail is capped at five with a "+N" tile, and
   `BookCover` holds a fixed 3:4 box, so a writer with seven books is the same
   height as one with none.

What is **not** allowed is an unbounded list inside a card. Sermons briefly had
one — a card per *writer* holding that writer's sermons — which made the cards as
uneven as the corpus (1 sermon against 13, so a 168px card sat beside a 1073px
one). Neither way out was good: levelling them left ~700px of dead space under
the short ones, and sizing to content left the grid ragged along the bottom. If
a card wants an unbounded list, that list is a **section of the page**, not a
card — give it a heading and one-item cards beneath, the way the grouped Books
shelf and the sermon shelf's preacher sections do.

**And if the item's own content is long-form, don't reach for a card at all** —
`.sermon-row` is the worked example. A grid buys you scannable equal-height
tiles; it costs you measure. When the thing worth showing is a paragraph, the
list wins.

### Filter controls

One family for every browse page's filter row: **`.filter-row`** (the wrapper),
**`.filter-field`** (inputs and selects; add `.grow` to the free-text one),
**`.seg`** (segmented toggle, active option gets `.active`), **`.chip`** (filter
pills, active gets `.active`).

Active states are **soft** (`--accent-soft` fill, `--accent` text) — never a
solid `bg-accent` block.

### Inputs
Every text input, select and textarea uses **`.field`** (`.filter-field` is the
same class under its original name, for the browse pages' filter rows):
`--surface` fill, `--border-strong` edge, `--radius-sm`, one height. Focus uses
the global `:focus-visible` ring (2px accent outline); placeholders are muted.

`.field` is unlayered, so a `px-3` or `rounded-lg` beside it silently loses —
if a control needs different metrics, that is a modifier here, not a utility at
the call site. Width and margin utilities are fine: the class doesn't set them.

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

- **Contrast:** target WCAG **AA** (4.5:1 text) in **all three** themes, and
  check a pairing against `--surface-2` as well as `--bg` — surface-2 is the
  tightest of the three grounds and is where `--muted` failed in sepia. Verify
  muted-on-bg and accent-on-surface pairings when adding them.
- **Touch targets:** ~44px minimum under `@media (pointer: coarse)` (see the
  block in `app.css`). Desktop chrome stays compact; only touch pays the height.
  Round controls keep their disc and grow an invisible centred hit area rather
  than reflowing a tight nav bar.
- **Native chrome:** `color-scheme` is declared per theme, so select dropdowns,
  scrollbars and autofill follow the page instead of rendering light-on-dark.
- **Focus:** every interactive element has a visible focus ring
  (`:focus-visible` → 2px accent outline, 2px offset). Don't remove it.
- **Names:** icon-only controls get an `aria-label`; nav/footer link groups are
  labelled; async results (search) should be discoverable.
- **Motion:** respect `prefers-reduced-motion` (a global block disables
  transitions/animations under it).
- **Busy states:** never replace a control's label with `…` — that leaves it
  announcing as "…, dimmed, button" with no accessible name. Keep the label, add
  `.btn-spinner` beside it and `aria-busy`.
- **Form errors:** render into an always-present `role="alert"` region and point
  the offending fields at it with `aria-describedby` + `aria-invalid`, so a
  failure is announced rather than silently repainted.

---

## 7. Motion

Quiet and quick. Three steps, as tokens — `--duration-fast` (150ms, hover and
reveal), `--duration-base` (250ms, panels and layout), `--duration-slow` (400ms,
a bar filling). Nothing bouncy. All motion is disabled under
`prefers-reduced-motion` by a global block.

Don't write a literal duration: eight of them had accumulated, including a
`0.28s` and a `0.3s` that nobody chose between, and two drawers that opened at a
different speed from the panels beside them.

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
8. **Verify** on the relevant page(s) in all three themes before merge.

Most of these are now enforced in CI rather than left to review. A convention
without a gate loses to the next person in a hurry — and, on this repo, to the
next parallel session:

| Guard | Catches |
|---|---|
| `colorTokens.test.ts` | raw hex outside `app.css`/admin, unless a comment says why (`hex-ok:` / `hex-ok-file:`) |
| `typeScaleGuard.test.ts` | arbitrary `text-[…]`, literal `font-size` in markup, scoped CSS or app.css; `.text-display` outside the home hero |
| `pageShell.test.ts` | a browse page dropping `.page-col` or `<PageHeader>` |
| `rtl.test.ts` | physical utilities **and** physical CSS in `<style>` blocks |
| `messageCatalogues.test.ts` | a locale's UI catalogue drifting from `messages/*.json` |
| `readerDirection.test.ts` | reader surfaces losing their direction handling |

Rules 4 (soft primaries), 5 (contrast + focus), 6 (icon weight, spacing), 7
(Take Root parity) and 8 (verify in all three themes) remain review-time checks:
they need a pair of eyes, not a regex.

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
- ✅ **Contrast** — sepia's `--muted` was under AA (4.42:1 on `--bg`, 3.98:1 on
  `--surface-2`) and is now `#716048` (5.14 / 5.57 / 4.63). Lamplight and paper
  were measured at the same time and already passed, so they are unchanged.
  `--warning` and `--border-strong` were added (see §1) and the OS-theme `dark:`
  utilities — which keyed on `prefers-color-scheme`, not `[data-theme]`, and put
  the reader's "remove highlight" at 2.64:1 — now use `--danger`.
- ✅ **Touch targets, `color-scheme`, focus rings, form-error announcement** —
  see §6. The three `outline-none` declarations that stripped the global focus
  ring are gone.
- ✅ **Type scale** — 52 arbitrary `text-[…rem]` utilities and 36 literal
  `font-size` declarations are back on the `--fs-*` steps, with `--fs-micro`
  added for the dense-label cluster. Guarded by `typeScaleGuard.test.ts`.
- ✅ **One eyebrow** — `.eyebrow` replaces 61 hand-written copies that carried
  ~11 letter-spacings between them.
- ✅ **One control family** — `.field` covers all 45 remaining inputs, selects
  and textareas; `.settings-select` and eight other bespoke shells are gone.
- ✅ **Button sizes** — `.btn-sm` / `.btn-icon` / `.stat-number` replace five
  hand-rolled compact paddings, and the 123 `!important` utilities that existed
  to work around a specificity problem buttons never had (`.btn` is layered) are
  down to one genuinely load-bearing case, on the unlayered `.book-card`.
- ✅ **Tokens for shadows, durations and the cover fallback**; radii down from
  twelve values to four; breakpoints on Tailwind's scale.
- ⚠️ **Admin still diverges** in places the tokens can't reach — `.text-display`
  page titles and its own table/tile layouts. Worth a pass of its own.
- ⚠️ **Owed to Take Root.** §1 tokens are meant to stay identical across both
  repos. The sepia `--muted` retune and the two new tokens have **not** been
  mirrored into Take Root yet — do that before the sets drift.
- ⚠️ **Class naming** differs slightly from Take Root (`.btn-primary`/`.btn-ghost`
  vs `.primary`/`.ghost`) — harmless, but worth converging if the systems merge.
- ⚠️ **Detail pages still use `.text-display`** for their titles
  (`topics/[slug]`, `biographies/era/[era]`), as does `/notebook` and the admin
  surface. Deliberate for now — a different class of page — but they should get
  a pass of their own.
- ⚠️ **Cover art** — roughly half the library's covers are generated
  typographic placeholders rather than artwork. A content problem, not a CSS
  one, but it is the biggest thing holding the shelf back visually.
- ⚠️ **Partial automated guard.** Type sizes and RTL are now enforced in CI (see
  §8). Nothing yet stops a new page hand-rolling its own shell or header: a
  check asserting browse pages use `.page-col` + `<PageHeader>` is the next
  one to write, and `<PageHeader>` still covers only 5 of 26 pages.

_Last reviewed: 2026-08-19. Update this section as gaps close._
