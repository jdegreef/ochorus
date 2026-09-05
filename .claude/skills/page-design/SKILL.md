---
name: page-design
description: Build or change an Ochorus page so it looks like the pages beside it — the anatomy of a browse shelf, a leaf page, a reading surface and a utility page, which existing page is the MODEL for each part, the chrome every new content type must be wired into, and the guards to extend. Use when adding a route, a list/index page, a detail page, a section on an existing page, or when a page "looks different from the others". Carries the design-consistency backlog from the 2026-09-04 audit. This is a living playbook — tick items off as they ship and append new drift as it is found.
---

# Ochorus page design — one anatomy per page kind

`STYLE_GUIDE.md` governs *atoms*: tokens, type scale, buttons, cards, fields.
This skill governs *pages*: which atoms go where, in what order, and which
existing page to copy. It exists because the atoms were already consistent in
September 2026 and the pages still weren't — the site had 40 public routes, and
a reader walking Books → Sermons → Quotes → Articles met four page-header
shapes, three top paddings, two `<title>` suffixes, three breadcrumb trails,
eight empty-state renderings and section headings at four sizes. Every one of
those pages used the right tokens. What they didn't share was an anatomy.

## Rule 0 — copy the model page, don't compose from the guide

Every new page is one of four kinds. Open the **model** for its kind, copy its
skeleton (shell → header → controls → body → states → `<Seo>`), and only then
layer in what is special about the new page. A page built up from the style
guide's parts list will match the guide and still not match its neighbours.

| Kind | What it is | Model | Also look at |
|---|---|---|---|
| **Browse shelf** | An index of one content type: `/books /sermons /topics /plans /biographies /quotes /scripture /articles /search` | `routes/topics/+page.svelte` for the bare shell; `lib/components/BooksShelf.svelte` for a filtered shelf | Biographies for URL-backed filters + `FilterSummary` + `EmptyState` with a clear action |
| **Leaf page** | One item, reached from a shelf: `/books/[slug] /authors/[slug] /plans/[slug] /topics/[slug] /quotes/[author] /articles/[slug] /scripture/…` | `routes/books/[slug]/+page.svelte` | Sermon page for the kind eyebrow and `lang=` on the title |
| **Reading surface** | The text itself: `/books/[slug]/[order]`, `/sermons/[slug]` | The chapter reader | Answers to `--reading-measure`, not `.page-col` (STYLE_GUIDE §3) |
| **Utility / prose** | `/about /contact /legal /login /reset-password /settings /notebook /+error` | Settings (app-like) or About (prose) | These are the least consistent set today — see the backlog |

## Anatomy of a browse shelf

In this order, and nothing else at the top level:

1. **Shell** — `<div class="page-col px-5 py-10">`. `py-10`, not `py-6`/`py-8`.
   (Twelve shells say `py-10`, six say something else; the content edge should
   not jump vertically on navigation.)
2. **`<PageHeader>`** — always. `title` is the **nav word** (`Books`, `Topics`,
   `Reading Plans`); `tagline` is one sentence; `meta` is the total, formatted
   `N books · M authors`. `eyebrow` is only for a page whose h1 is *not* the nav
   word (Sermons: eyebrow `Sermons`, title `The Preached Word`). Pick one
   register per page and keep `<title>` = the nav word either way.
3. **`<CatalogLanguageNudge kind=…>`** — when the current language has fewer
   rows than English. Extend its `kind` union rather than skipping it.
4. **Secondary section** (optional) — `h2.section-label` above it (`Continue
   reading`, `Sermon of the week`), hidden while the reader is filtering.
5. **`.filter-row`** — controls in this order: free-text `.filter-field.grow`
   (placeholder `Filter by …`) · scope `<select class="filter-field">` · sort
   `<select>` · group `.seg` · then a `.chip` row underneath for taxonomy. No
   visible "Sort:" / "Length:" label — put it in `aria-label`. No "Clear"
   button in the row: clearing is `FilterSummary`'s job.
6. **`<FilterSummary>`** — rendered **only while a filter is active**, with
   `onClear`. Never "Showing 35 of 35".
7. **The list** — one card family per content type (§ Cards below). Grouped
   shelves head each group with the **group heading** recipe (§ below), in a
   `<section>` whose `scroll-margin-top` tracks the sticky bar, not `scroll-mt-20`.
8. **States** — three, all `<EmptyState>`:
   - *no rows in this language* → `message` + `action` = "Read the English library";
   - *filtered to nothing* → `message` + `action` = clear filters;
   - *load failed* → `message={t('common.loadError')} onRetry`.
   Never a bare `<p class="py-16 text-center">`, never a hand-rolled panel.
   The *no-rows* action is usually just `<CatalogLanguageNudge kind=…>` above
   the list, not a second button inside the panel: the nudge already renders on
   an empty shelf (it shows whenever English has more items), so a read-English
   button in the EmptyState too is redundant — that's why Topics/Plans/Sermons
   carry only the nudge. Extend the nudge's `kind` union rather than skipping a
   surface. On an English-only hub the error message still localises
   (`t('common.loadError')` — it is chrome), while the *empty* message may stay
   an English literal (it describes English-only content; F3 tracks localising
   those).
9. **Data** — the loader routes the shelf's PRIMARY list through `loadShelf()`
   so a failed fetch is *reported* (a `loadError` the page turns into
   `<EmptyState onRetry>`), not crashed to the 500 route or baked as a false
   empty shelf. Only the primary list: **decoration keeps its own silent
   try/catch** — the biographies cover-strip books degrade to `[]` so the bios
   still render, and routing them through `loadShelf` would either raise the
   whole-page error panel when only a strip failed or leave a `loadError` no one
   reads. Filter values that describe *what is shown* live in the URL via
   `urlFilters()`; view preferences (grid/list, sort) live in localStorage.
10. **`<Seo>`** — not a hand-written `<svelte:head>`. Title `Books — Ochorus`
    (em dash). Description falls back to a localized string, never empty.

**No visible breadcrumb** on a top-level shelf. Biographies removed its trail
first, with the reason on file; Quotes, Scripture and Articles followed in
#1430, so none of the shelves shows one now. Keep the BreadcrumbList JSON-LD —
build it with `breadcrumbLd(crumbs)` (§ leaf-page step 9).

## Anatomy of a leaf page

1. **Shell** — `page-col px-5 py-10`.
2. **`<Breadcrumb items={crumbs}>`** — `Home › Section › This page`, and the
   **same `crumbs` array feeds the JSON-LD**. Never hand-roll the `<nav>`; the
   three that did (author, sermon, reader) each ended up with a different trail,
   and the sermon's visible trail contradicts its structured data.
3. **Head** —
   - **kind eyebrow**: `.eyebrow` reading `KIND · N UNITS · TIME`
     (`Sermon · 12 min · 1855`; `Book · 7 chapters · 34 min`); every leaf gets
     one, not just the sermon and the chapter;
   - **`<h1 class="text-h1" lang={contentLang(item.language)}>`** — `lang` from
     the *served* language, so a fallback edition is announced correctly;
   - **byline** as a link to `/authors/<slug>` (the quotes page currently has
     the name only in the h1 and no link);
   - **`<SourceBadge>` directly under the byline** whenever
     `source_type === 'ai_unreviewed'` — the reading surfaces must show it too;
   - **hero visual** on the end side: cover, portrait, plate or `CoverStrip`.
4. **Action row** — `.btn.btn-primary` for the one start verb (`Begin reading`,
   `Start the plan`, `Start with <book>`), `<FavoriteButton>` (the component,
   not a `btn-icon` heart), `.btn.btn-ghost` for `Search in this …`. All the
   same size. A finished/complete state is a muted status line, not a `<p>`
   wearing `.btn`.
5. **Summary** — `h2.text-h3` + prose (`About this book`). One treatment, not a
   heading here and a bordered "In brief" callout there.
6. **Sections** — `h2.section-label` above a *list* (contents, quotes, passages);
   `h2.text-h3` above *prose*. A count in a heading is `(N)` in
   `text-small font-normal text-muted`, or absent — not both styles.
7. **Related** — capped at 4–6, rendered with the content type's **card
   component** (`BookCard`, `SermonCard`, `PersonCard`), headed `More …`. Never
   an unbounded `<ul>` of text links.
8. **Source line** — `mt-8 text-small text-muted`, no rule above it.
9. **`<Seo>`** with `ogImage` (the cover twin, a portrait, or the section's
   `/og/<section>.png`) and both the item's LD and the BreadcrumbList. Build the
   BreadcrumbList with `breadcrumbLd(crumbs)` from `$lib/seo` (feeds off the same
   `{name, href}` array as the visible `<Breadcrumb>`) — never hand-write
   `jsonLd(breadcrumb(crumbs.map(...)))`, whose `c.href`→`c.url` retype ships a
   broken trail with no error.

**Language fallback is one policy.** `localized()` serves English when the
language has no row; the page must then *say so* ("Not yet available in
Swahili — showing the English edition"), and no page 404s instead.

## Reading surfaces and utility pages

The chapter reader and the sermon page are governed by `--reading-measure`
and their own chrome (STYLE_GUIDE §3, §5). What they still share with leaf
pages: the breadcrumb rule (2), the eyebrow (3), `SourceBadge`, prev/next as
a `.btn` pair (ghost previous, soft-primary next), and one shared
`.focus-exit` pill rather than three pasted copies.

Settings and Notebook are app pages: `page-col px-5 py-10`, `<PageHeader>`
(eyebrow `Ochorus` is not an eyebrow — use the section name or none), sections
as `h2.text-h2`, sub-sections `h3.text-h3`, every control from the `.btn` /
`.field` / `.seg` / `.chip` families **without scoped overrides**. About,
Contact and Legal are prose at their own measure; that measure needs a real
class — `.reading-page` is referenced by two of them and defined nowhere.

## Cards and hover

| Content | Card | Hover |
|---|---|---|
| Book | `.book-card` (grid) / `.book-card--row` (row) | overlay + border |
| Topic, Plan | `<ShelfCard>` | lift −2px + shadow |
| Sermon on the shelf | `<SermonCard variant="row">` | hue-mixed border, no lift |
| Author | `<AuthorBioCard>` one-per-row | border-accent |
| Article, Quotes-author | *should be* `.book-card--row`-family rows | row tint |

Two hover languages only: **lift** for banded cards, **border tint** for rows.
A card directly under the `<h1>` titles itself with `<h2>`; a card under a
group `<h2>` uses `<h3>`. Home shelves, the error page's "three to try" and the
plans-progress panel must use these same components, not re-drawn tiles.

## Group heading (grouped shelves, search result groups)

`h2.mb-4.flex.items-center.gap-2.5.text-h3.text-muted` — optional 32px portrait,
the name **as a link** when it has a page, the count as `tabular-nums opacity-70`.
This is the sermons shelf's recipe; Books (plain text, no link), Biographies
(sticky, `text-text`) and Search (`section-label`) should converge on it.
`<SectionHeader>` is *not* this — it renders `h2.text-h1` and is the home page's
"shelf title + See all" pattern. (It should drop to `.text-h2`; see backlog.)

## Chrome parity — the checklist for a new content type

A content type is not shipped until it is reachable from every surface that
lists content types, **in the same order** everywhere:

- [ ] top nav `NAV` in `routes/+layout.svelte` (if it earns a nav slot)
- [ ] footer **Explore** group (same file)
- [ ] `COMMANDS` in `lib/components/CommandPalette.svelte`
- [ ] `SearchHit` kinds in `lib/library-public.ts` + the search page's facet rail
- [ ] `lib/sitemap.ts` static pages (nav order) and a sitemap section
- [ ] `CatalogLanguageNudge`'s `kind` union
- [ ] a `/og/<section>.png` card for pages without their own image
- [ ] the guard lists in `lib/pageShell.test.ts` (`BROWSE_PAGES` / `LEAF_PAGES`)

Articles, Scripture and Quotes each failed several of these: footer-only,
absent from the palette and from search.

## Copy conventions

- `<title>`: `{Page} — Ochorus` — em dash with spaces, everywhere. Leaf pages
  `{Title} — {Author} — Ochorus`. Not `· Ochorus`.
  - **A copy fix to a string that lives in a catalogue must touch all eight
    `messages/*.json`, not just `en.json`.** The title suffix rides inside
    translatable keys (`book_title_tag`), so fixing English alone leaves the
    book reading `— Ochorus` in English and `· Ochorus` in Swahili — invisible
    until a reader of that language opens the tab. `messageCatalogues.test.ts`
    now fails any catalogue carrying `· Ochorus`; add the same shape of guard
    when you normalise the next catalogue-borne label. A value-only edit needs
    no `sync:catalogues` (that snapshot tracks keys, not values).
- Counts: `N books · M authors` (middle dot, spaces). Never "Showing N of N".
- Chrome strings — crumbs, "Home", "Read", "Topics:", plurals — go through
  `t()` / `m.*()` even on an English-only hub; only *content* may be literal.
- Icons come from `<Icon name>`; never `▦ ☰ ✕ ▶ ✓ ♥ 🔖 📝 ✦ →` as glyphs.
- Compact buttons are `.btn-sm`, never `py-1.5` / `py-2` on `.btn`.

## Guards to extend when a page ships

`lib/pageShell.test.ts` — add the route to `BROWSE_PAGES` (shell + PageHeader)
or `LEAF_PAGES` (shell). `lib/typeScaleGuard.test.ts`, `colorTokens.test.ts`
and `rtl.test.ts` scan every `.svelte` automatically. Gaps still open (see
backlog G): Tailwind's default `text-lg`/`text-6xl` steps, literal durations,
undefined `var(--radius-*, …)` fallbacks, scoped redefinition of `.seg`/`.chip`/
`.field`/`.btn`, and arbitrary `max-w-[…]` on a shell.

## Re-auditing (how the backlog was produced)

Three read-only agents in parallel, one per page kind — browse shelves, leaf
pages, chrome + utility pages + `app.css` + the guard tests — each asked for a
**comparison matrix** (shell, header, filters, counts, states, headings, cards,
related, badge, SEO) and then only the cells that differ *without a stated
reason in the file*. Grep-verify the headline counts afterwards (`class="page-col…"`,
`— Ochorus` vs `· Ochorus`, `<PageHeader`, `radius-chip`, `text-(6xl|lg|base)`).
Pair it with a live-site pass at 1280px: one screenshot per shelf, one leaf of
each kind, the reader, the 404 and About. The in-app Browser pane cannot scroll
or hover while hidden — scroll with `window.scrollTo` via `javascript_tool`,
and expect a blank screenshot right after a JS scroll; read the footer with
`read_page` instead.

## Converting an existing page onto the system

- **`<svelte:head>` → `<Seo>` is output-equivalent** when the hand-written head
  is the standard set: `title` (also the `og:title` default), `description`
  (also `og:description`), `canonical` (also `og:url`), the `hreflang`
  alternates + x-default, `og:type=website`, `og:image`, `twitter:card`, and the
  JSON-LD blocks. Map an `{#if x.length}{@html xLd}{/if}` gate to
  `structuredData={x.length ? [xLd] : []}`. A page that destructured
  `const { alternates, xDefault } = hreflangAll(...)` for the loop passes the
  whole object instead: `const hreflang = hreflangAll(...)`. There is **no**
  shared canonical helper — `${SITE_URL}${localizeHref(path)}` is the repo-wide
  idiom (16 files); `absUrl()` is wrong here (it omits the locale prefix).
- **`<header>` → `<PageHeader>`** carries the eyebrow/title/tagline; keep a
  page hand-rolled only when its `<h1>` is genuinely composite (the era page's
  name + date-range badge), and then match PageHeader's metrics exactly
  (`header mb-8`, `h1 text-h1 mb-2`, `tagline max-w-2xl text-body text-muted`).
- Verifying locally needs the Django API for data, so the browse pages that go
  through `loadShelf` show their converted head above an EmptyState while the
  unguarded ones (still on the C1 backlog) hit the error route — both still
  prove the head/`PageHeader` rendered. Confirm the head with
  `javascript_tool`: one `<title>`, right canonical/og. On Node 25 the pure
  file-reading guards run under `npx vitest run --environment node <files>`
  (the jsdom store suite needs the pinned Node 22 — CI has it).

## Verify before merge

Open the new page **and its two neighbours** (the shelf it hangs off, and a
sibling leaf) in lamplight, paper and sepia; at `/ar/…` for direction; at 375px
for the filter row. The question is not "does this page follow the guide" but
"can you tell where this page ends and the next begins".

---

## Backlog — design-consistency audit, 2026-09-04

Findings from a code + live-site pass over all 40 public routes. Grouped;
within a group, most reader-visible first. `→` names the model to converge on.
Tick and date an item when its PR merges; append new drift at the end of the
relevant group.

### A. Shells, headers, titles

- [x] **A1** _(shipped #1419 — quotes/scripture/articles on `<PageHeader>` + BROWSE_PAGES; era kept hand-rolled as the composite-title exception; settings/notebook are A9)_ Four hand-rolled `<header>` blocks — `biographies/era/[era]`,
  `quotes`, `scripture`, `articles` — each with different margins; Scripture's
  tagline is `text-small`. → `<PageHeader>` (Topics); add all four to
  `BROWSE_PAGES`.
- [x] **A2** _(shipped #1419 — folded into `.page-col px-5 py-10`, guarded)_ Shell padding is `py-10` on 12 pages, `py-6` on 5 (quotes ×2,
  scripture ×3, articles ×2), `py-8` on Biographies; breadcrumb-to-title gap is
  `mt-5` (book), `mt-4` (topic), 0 elsewhere. → `py-10`, no extra gap; or fold
  the padding into `.page-col`.
- [ ] **A3** H1 register: Sermons/Biographies carry a brand h1 under a nav-word
  eyebrow; Books/Topics/Plans/Search use the nav word; Quotes/Scripture use a
  descriptive sentence with no eyebrow. `<title>` ≠ `<h1>` on Sermons and
  Biographies. → decide one register, document it in STYLE_GUIDE §5.
- [x] **A4** _(shipped #1419 — all 8 catalogues, guarded)_ `<title>` suffix: ` — Ochorus` ×39, ` · Ochorus` ×7 (book, quotes,
  articles, scripture ×2, era mixes both). → ` — Ochorus`, and put the suffix
  in `Seo.svelte` so nobody types it.
- [x] **A5** _(shipped #1419)_ Five browse pages hand-write `<svelte:head>` (books, biographies,
  topics, plans, sermons); five use `<Seo>`. → `<Seo>`.
- [x] **A6** _(shipped #1430 — visible trail dropped from the three index hubs, JSON-LD kept)_ Quotes/Scripture/Articles indexes show a `Home › X` breadcrumb;
  the nav'd shelves don't (Biographies removed it, reason on file). → drop the
  visible trail, keep JSON-LD.
- [x] **A7** _(shipped #1430 — one `crumbs` array feeds both `<Breadcrumb>` and the head on Author/Sermon/Reader; JSON-LD side then folded into `breadcrumbLd(crumbs)` in #1431)_ Author, Sermon and Reader hand-roll their breadcrumb `<nav>` with
  three different trails (with/without Home, with/without the current item);
  Sermon's visible trail contradicts its BreadcrumbList. → `<Breadcrumb>` with
  one `crumbs` array feeding both (Book).
- [ ] **A8** The kind eyebrow (`Sermon · 12 min · 1855`) exists on Sermon and
  Reader only. → every leaf (Book: `Book · 7 chapters · 34 min`; Plan:
  `Reading plan · 27 days`).
- [ ] **A9** Settings and Notebook hand-roll headers; eyebrows are `Ochorus`
  (legal, notebook), the nav word (about, contact), or none. → `<PageHeader>`;
  section name or no eyebrow.
- [ ] **A10** Leaf prose measure is hand-set: `max-w-[40rem]` ×3 on Author,
  `max-w-xl` on Plan and Book, `max-w-2xl` on Quotes. `.reading-page` on
  About/Legal is defined nowhere. → one `.prose-measure` class (or
  `--reading-measure`). _(Articles: the list cap is gone — it fills `.page-col`
  like Sermons; the article prose sits at `--reading-measure` with
  `<ReaderControls>` like the sermon/bio, but its `.article-body` hand-consumes
  the `--reading-*` vars — a fourth copy of that recipe to fold into the shared
  class when this lands.)_
- [ ] **A11** Login/Reset use `mx-auto max-w-[26rem]`, invisible to the shell
  guard (regex only matches `max-w-2xl…7xl`). → `.page-col--narrow`; widen the
  regex.

### B. Filters, counts, state

- [ ] **B1** Sermons' `q`/`book` and Plans' `length` are local `$state`, so a
  filtered shelf can't be shared or returned to with Back. → `urlFilters()`
  (Biographies).
- [ ] **B2** "Clear filters" has three shapes: `FilterSummary` link (Books), link
  + ghost button in the EmptyState (Biographies), a `Clear` ghost button inside
  the filter row with its own copy key (Sermons). → FilterSummary `onClear`
  everywhere; retire `sermons.clear`.
- [ ] **B3** Result counts in five formats; Biographies renders "Showing 35 of 35
  writers" unfiltered; Topics/Plans show none; Quotes buries the total in the
  tagline. → `PageHeader` `meta` for the total, `FilterSummary` only when active.
- [ ] **B4** Default grouping: Books `all`, Sermons `preacher`, with the same seg
  order on both (so Books' default is the second option). → one default; the
  default option first.
- [ ] **B5** Sort is a `<select>` on three shelves and a labelled `.seg` on
  Search; visible `Length:` / `Sort:` labels exist only on Plans/Search. →
  `<select>` + `aria-label`.
- [ ] **B6** Only Biographies pins its filter bar and collapses it on mobile;
  Books has more controls and neither. Books/Sermons hard-code `scroll-mt-20`
  where Biographies/Search measure the bar. → a `FilterBar` component.
- [ ] **B7** Count badges beside labels are styled six ways (`opacity-60`,
  `tabular-nums opacity-70`, `text-small font-normal text-muted`, an
  accent-soft pill, `text-muted/70`, `text-eyebrow`). → one `.count` recipe.

### C. Empty, error, loading

- [x] **C1** _(shipped #1424)_ Load failures: Biographies, era and Quotes loaders are unguarded and
  crash to the error route; Articles and Scripture swallow the error and claim
  the shelf is empty — the exact anti-pattern `loadShelf()` was written to end.
  → `loadShelf` + `EmptyState onRetry` (Topics).
- [~] **C2** _(partly shipped #1424 — articles/quotes/era on `<EmptyState>`; the drawer/popover `compact` variants + Search's panel remain)_ Eight empty-state renderings. Filtered-to-nothing is a bare
  `<p class="py-16 text-center">` on Books, era and Search; Sermons' EmptyState
  says "try clearing the filters" with no button; Search hand-rolls a copy of
  the EmptyState panel. → `<EmptyState>` with an `action` (Biographies); add a
  `compact` prop for drawers/popovers.
- [x] **C3** _(shipped #1424)_ Zero rows in a language: Books offers "Read the English library",
  Plans/Sermons get the nudge, Topics gets a dead-end message, Biographies gets
  nothing. → extend `CatalogLanguageNudge` to `topics`/`authors`; action on all.
- [ ] **C4** Loading: Search's "Show more" replaces its label with `…` (STYLE_GUIDE
  §6 forbids this); seven surfaces show a bare `…` paragraph. → keep the label
  + `.btn-spinner` + `aria-busy`; one `<LoadingLine>` using `t('common.loading')`.

### D. Sections, cards, related

- [ ] **D1** An `<h2>` renders at four sizes: `.text-h1` via `<SectionHeader>` on
  Home, `.text-h2` on Settings/About, `.text-h3` on leaf pages, `.section-label`
  on shelves — 37 distinct class combinations. → `.section-label` above a list,
  `.text-h3` above prose, `SectionHeader` drops to `.text-h2`; `.text-h1` is
  the `<h1>` only.
- [ ] **D2** Grouped-shelf headings are hand-rolled four ways (Books plain text,
  Sermons portrait + link, Biographies sticky `text-text`, Search
  `section-label`). → the sermons recipe as a `GroupHeading`.
- [ ] **D3** Card hover: three lift depths and four colour treatments across
  `.shelf-card`, `.article-card`, `.sermon-row`, the quotes card,
  `AuthorBioCard`, `BookListRow`, `PersonCard`, `AuthorTile`. → lift for banded
  cards, border tint for rows; nothing else.
- [ ] **D4** `ArticleCard` is bespoke: `border-radius: 0.75rem`, `0.15s` literal
  transitions, literal `Read →`, an `<h3>` directly under the `<h1>`. The quotes
  index card has no heading at all; `BookCard`'s title is a `<div>`. → rebuild
  on the row family; `<h2>` under the h1.
- [ ] **D5** Home shelves re-draw cards that have components: `ContinueReading`
  (bespoke row + scoped gradient) vs `.book-card--row`; `PlansProgress` vs
  `ShelfCard`; the error page's "three to try" as bare covers with floating
  captions. → the components.
- [ ] **D6** Related blocks use five different components; the sermon's "More
  sermons on X" is an **unbounded** text list; Plan, Topic, Quotes and Scripture
  have none. → card components, capped at 4–6 (Book).
- [ ] **D7** Favorite: `FavoriteButton` is outside the `.btn` family (own padding,
  `0.15s` literals); the sermon page uses a `btn-icon btn-ghost` heart instead;
  only Author passes `showLabel`. → rebuild on `.btn.btn-sm`; one label policy.
- [ ] **D8** Action rows: "Search in this X" is `btn-ghost` (Book), `btn-sm
  btn-ghost` (Author), a text link with `→` (Topic); Author has no
  `.btn-primary` although it has a start verb; Plan's finished state is
  `<p class="btn btn-ghost">✓ Finished</p>`. → Book's row.
- [ ] **D9** Topic/scripture chip rows are hand-rolled eight times in three
  colourways (bordered muted, bordered text, filled surface-2) with three label
  styles; Sermon's scripture chips always link to search where Book's link to
  `/scripture/…`. → `.chip` + `.eyebrow` label; shared href logic.
- [ ] **D10** Prev/next: a `.btn` pair in the reader, bespoke bordered cards on
  the sermon page. The exit-focus pill is pasted verbatim into Author, Sermon
  and Reader. → the reader's pair; one `.focus-exit` class.
- [ ] **D11** `SourceBadge` sits under the byline on Book, after the text card on
  Sermon, and is **absent from the chapter reader and the author bio** — an
  `ai_unreviewed` chapter never shows "awaiting native review" (CLAUDE.md
  rule). → under the byline everywhere; add to the reader eyebrow line.
- [ ] **D12** Language fallback: `localized()` silently serves English with no
  notice on six pages; Topic 404s instead; Book's `<h1>` has no `lang`; the
  reader's JSON-LD `inLanguage` reports the UI locale, not the served edition.
  → fallback + visible notice + `lang` from the served language, everywhere.
- [ ] **D13** Summary: Book's "About this book" is an `h2` + prose; Sermon's "In
  brief" is a bordered callout with an accent eyebrow and `text-small` body. →
  one treatment.
- [ ] **D14** Sermon page overrides `.eyebrow` to `--fs-micro` four times;
  `SermonCard` does it once more. → plain `.eyebrow`.

### E. Tokens and system classes

- [ ] **E1** Settings re-declares `.seg` in scoped CSS as a pill group, losing the
  `--border-strong` edge — the same toggle looks different on Settings and
  Sermons. → delete; a `.seg--pill` modifier in `app.css` if wanted.
- [ ] **E2** Radii: ten values in use against the guide's four, including
  `var(--radius-chip, 0.4rem)` on Quotes and Scripture where `--radius-chip`
  is defined nowhere, so the fallback always fires. Bespoke breakpoints
  `30rem` (SermonPlate) and `34rem` (Scripture). → `--radius-sm`/`--radius-card`;
  Tailwind breakpoints.
- [ ] **E3** Literal durations survive in `ArticleCard`, `FavoriteButton`, the
  reader (`0.15s`, `1.1s`) and `app.css` (`btn-spin 0.7s`). → `--duration-*`.
- [ ] **E4** Two token vocabularies in scoped CSS (`--color-border` on Topic,
  Quotes, Article, Scripture; bare `--border` on Author, Sermon and the
  components) plus re-declared font-stack fallbacks
  (`var(--font-display, Georgia, serif)`). → bare tokens, no fallbacks.
- [ ] **E5** Unicode glyphs as icons in eleven places (`▦ ☰` view toggle, `✕`
  recent-search chips, `▶` ×2, `✓`, `♥` ×2, `🔖 📝`, `✦`, `→` in "see all"
  links); the hero search `<svg>` is stroke 2. → `<Icon>`; add `check`, `note`,
  `arrow-right`.
- [ ] **E6** Two text inputs bypass `.field` (home hero, command palette).
  Login duplicates `.btn` as `.google-btn`, declares `.mail-badge` twice, and
  its password-reveal control is pasted into Reset. `PwaToasts` ships a solid
  `bg: var(--accent)` button. → `.field`, `.btn`, `.btn-primary`.
- [ ] **E7** Compact ghost buttons hand-roll `py-1.5`/`py-2` on Settings ×4,
  Sermons and `CatalogLanguageNudge`. → `.btn-sm`.
- [ ] **E8** Near-duplicate classes: `.footer-heading` ≈ `.section-label`,
  `.sermon-row-ref` ≈ `.eyebrow`, `.navsearch` ≈ a pill `.field`; the topic
  hero still carries its own weaker `.hue-band`. `.stat-number` is admin-only
  but lives with the public classes; `--hl-*` are fixed hex that don't follow
  the theme. → fold or document.
- [ ] **E9** Off-scale Tailwind sizes slip the type guard: `text-6xl` (error
  page), `text-lg`, `text-base` ×2. → `--fs-*`; extend the guard.

### F. Chrome and reachability

- [ ] **F1** Articles, Scripture and Quotes are footer-only (English): absent
  from the command palette and from search (`SearchHit` has no such kinds).
  → palette `COMMANDS`; an `article` hit kind.
- [ ] **F2** Sitemap lists Sermons before Topics; nav, footer and palette agree
  on Topics · Plans · Sermons. → derive all four from one list.
- [ ] **F3** Hard-coded English chrome on the English-only hubs (`Home` crumbs,
  `Read →`, `quotation(s)` pluralisation, empty-state copy) and on Articles,
  whose loader says it is translation-ready. → `t()` keys now.
- [ ] **F4** Meta: Plan and Topic can ship an empty description; slice lengths
  are 155/250/300; the reader, articles and scripture pages emit no `og:image`;
  the reader emits no BreadcrumbList. → localized fallback, one length, section
  OG cards (Book).

### G. Guide and guards

- [ ] **G1** STYLE_GUIDE drift: §5 says ghost buttons have a transparent border
  (`app.css` gives them `--border`); §2 says body line-height 1.6 (`app.css`
  1.65); §5 describes a nav (About/Books/Biographies/Contact + language picker)
  and a three-block footer that no longer exist; §9 counts are stale.
  → **fixed in the same PR as this skill** (guide §5/§9 rewritten).
- [ ] **G2** Guard gaps: `pageShell` omits Home, Articles ×2, the Quotes index
  and the auth pages, and its `max-w` regex misses `max-w-xl`/`max-w-[…]`;
  `typeScaleGuard` misses Tailwind's default steps; nothing checks literal
  durations, undefined `--radius-*` fallbacks, scoped redefinition of `.seg`/
  `.chip`/`.field`/`.btn`/`.eyebrow`/`.page-col`, solid `bg-accent`, or
  hard-coded English. → add the routes; a `systemClasses.test.ts`; extend
  `typeScaleGuard` to durations and radii fallbacks.

### Suggested order

1. **A1 + A2 + A4 + A5** — mechanical, four pages, one afternoon; the biggest
   visible jump per line changed.
2. **C1 + C2 + C3** — the only items that strand a reader.
3. **B1 + B2 + B3** — one `urlFilters` call and a `FilterSummary` each.
4. **A8 + D12** — leaf heads, and the unreviewed-translation gap (A7 shipped #1430; D11 shipped #1427).
5. **D1 + D2** — heading sizes; touches many files, best as its own PR.
6. **G2** — the guards, so none of the above regresses.
