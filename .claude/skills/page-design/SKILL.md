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
   **Book is the model (#3277):** the read verb lives in a *read card*
   (shared `.read-card` in app.css — the plan page uses it too for "Day N of M
   · today's reading"; chapter name + `ProgressBar` + one `.btn-primary`; Start over is a text
   link), and every other action is ONE quiet `.action-strip` row — Save,
   shelf, a single Download menu (`BookDownloadMenu`, never separate
   offline/EPUB/PDF buttons), Share/Search icon-only on desktop. When its
   host column (`.action-host`, a CSS container) is under 560px the same DOM
   becomes a 5-column icon-over-label strip (no second markup) — a container
   query, not a viewport breakpoint, because the column beside the cover on a
   tablet and long translations run out of room long before `md`. A sticky sub-nav CTA shows only once the hero CTA has scrolled
   away (IntersectionObserver), never two primaries on screen.
   Any dropdown (trigger + menu) closes via `use:dismissable={{ open,
   onDismiss }}` (`$lib/actions/dismissable`) on the wrapper — click-away,
   Escape, focus back to the trigger. Don't hand-roll a `<svelte:window>`
   handler, and don't `stopPropagation` on the trigger (it stops opening one
   menu from closing another); a full overlay uses `focusTrap` instead.
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

Two reader gotchas (both fixed in #2906, both scroll-vs-paged specific):
- **Paged mode slices the last line.** `.paged .pager` fills each CSS column
  with `column-fill: auto`, which starts a line whenever its TOP fits and lets
  the bottom spill past the content box; `article.paged`'s `overflow: hidden`
  then clips it into unreadable letter-tops — and that half-line is genuinely
  lost (multicol assigns it to one column, it does NOT repeat on the next page).
  Fix = reserve one prose line-height of bottom padding on the pager, sized as
  `calc(1.18rem * var(--reading-scale,1) * var(--reading-leading,1.85) + …)` so
  the slack tracks the reader's Size/Spacing. Never a fixed rem/em — `em` on the
  pager is base 16px, not the reading size.
- **Scroll mode** slices the same line differently: the fixed translucent
  `.progress-foot` bar the text scrolls under has a hard top edge. Fix = a short
  transparent→`--bg` scrim anchored `bottom:100%` of the bar (scroll mode only;
  paged is handled by the padding above). Spacing above the chapter title cluster
  is scroll-only too — scope with `article:not(.paged)`, since page mode zeroes
  the article padding and paginates from the top.
- **Verifying the reader locally against origin/main:** run the worktree
  frontend on **port 5180** (the backend's CORS allowlist is 5173/5180 only) vs
  the local seeded backend on :8000; the prod API blocks CORS from localhost.
  The browser pane caches the CSP document, so after a `csp.config`/env change
  navigate with a `?cb=<n>` cache-buster or the old `connect-src` keeps blocking.

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

One component: **`<GroupHeading>`** (`lib/components/GroupHeading.svelte`) —
`h2.mb-4.flex.items-center.gap-2.5.text-h3.text-muted`, an optional 32px portrait,
the name **as a link** when it has a page (`href`), and the count on the shared
`.count` class (tabular figures + muted). Books, Sermons and the search-result
groups render the default variant; Biographies passes `sticky` for its bordered
era heading (solid ink, pinned via `--pinned-offset`, count pushed to the end),
and a `detail` snippet carries the era's year range or Search's bespoke "N of M".
`<SectionHeader>` is *not* this — it renders `h2.text-h2` and is the home page's
"shelf title + See all" pattern.

The **topic leaf page** also uses `<GroupHeading>`: its Books section groups the
books by author when the topic is *author-clustered* — most of its books share
an author with another (the Puritans) — and stays a flat `book-grid` otherwise
(a diverse gallery like Women of Faith). The rule is one tested pure helper,
`lib/topicBookGroups.ts` (`groupBooksByAuthor` → groups | null); the
`section-label` "Books" heading stays, with the author `GroupHeading`s nested
under it. This is the adaptive-shared-anatomy approach — adapt from data, not a
per-topic bespoke layout — extend the topic page the same way, never with a
hand-built one-off. (The bare author-Map reduction now has three copies —
here, `sermons/+page.svelte`, `BooksShelf.svelte` — but the topic one's null
gate is topic-specific; a shared low-level `groupByAuthor` is a deferred
refactor, not this pattern's job.)

Same shape for the **order of the content sections**: Books / Sermons /
Articles are rendered in *prominence* order — the topic leads with the type it
has the most of and drops any that are empty (`lib/topicSections.ts`), so a
sermon-heavy topic (The Gospel Call, Christ & the Cross) surfaces its sermons
first and an article-heavy one (The Deeper Life, 21 articles) its articles,
while a balanced topic keeps the familiar Books → Sermons → Articles order.

**Verifying a page in the in-app Browser pane:** `npm run dev` binds IPv6
`[::1]` only, but the pane resolves `localhost`→IPv4, so navigation fails with
"denied or failed" — start it `--host 127.0.0.1`, and export
`PUBLIC_API_BASE_URL` so the dev CSP admits the API (see `verify-local`).

## Chrome parity — the checklist for a new content type

A content type is not shipped until it is reachable from every surface that
lists content types, **in the same order** everywhere:

- [ ] top nav `NAV` in `routes/+layout.svelte` (if it earns a nav slot)
- [ ] footer **Explore** group (same file)
- [ ] `COMMANDS` in `lib/components/CommandPalette.svelte`
- [ ] `SearchHit` kinds in `lib/library-public.ts` + the search page's facet rail
      _(Articles: done — `ArticleHit` + facet rail, see F1. Scripture/Quotes still absent by design.)_
- [ ] `lib/sitemap.ts` static pages (nav order) and a sitemap section — for a
      prerendered URL *family* (e.g. a topic-filtered shelf), the route's
      `entries()` and the sitemap section must advertise the **same** set, or
      `prerenderCoverage.test.ts` fails on the URL that was advertised but never
      built
- [ ] `CatalogLanguageNudge`'s `kind` union
- [ ] a `/og/<section>.png` card for pages without their own image
- [ ] the guard lists in `lib/pageShell.test.ts` (`BROWSE_PAGES` / `LEAF_PAGES`)

Articles, Scripture and Quotes each failed several of these: footer-only,
absent from the palette and from search.

## Adding a topic shelf (a topic ROW, not a new route)

The `/topics/[slug]` page and its chips are generated from data, so a new
shelf is one seed edit — but three separate build-time asset sets are each
guarded by a test that fails ONE AT A TIME, so you rediscover them the slow
way unless you regen all three up front:

- [ ] `backend/library/topic_seed.py` — the `TOPICS` tuple (`slug, title,
      description, [book slugs]`), plus `TOPIC_SERMONS`/`TOPIC_SCRIPTURE` if
      wanted. **Append LAST**: a plate-cover book draws the emblem of the
      *first* topic (seed order) that holds it, so inserting earlier silently
      re-skins existing covers. No migration — topics are seed data.
- [ ] English-only shelf → add the slug to `TRANSLATION_PENDING` in the same
      file, or the per-language coverage guard demands prose in all 7 langs.
- [ ] emblem identity in `frontend/src/lib/emblemNames.ts` `TOPIC_META`
      (`accent` + a **unique** `emblem` with ≥3 colours in `emblems.ts`
      `EMBLEM_ART`, per `emblems.test.ts`) — then **`npm run emblem:art`**
      (writes `backend/library/data/emblems/topics.json` + `<emblem>.svg`,
      read by `covers.py`) **and `npm run emblem:hues`** (`emblemHues.ts`).
      `emblemArt.test.ts` / `emblemHues.test.ts` fail on drift. Omit the
      `TOPIC_META` entry and the shelf uses a graceful fallback emblem — no
      art, no regen — but a flagship shelf earns its own.
- [ ] **`node scripts/generate-topic-og.mjs`** (= `npm run og:topics`) — the
      OG share card PNG + `static/og/topics/og-manifest.json` entry;
      `tests_fixture.TopicShareCardTests` (two tests) fail without it.

**Check `is_published` on PROD before choosing members — the fixture holds
UNPUBLISHED works.** A shelf shows only its *published* members, and no test
guards which ones you list, so an unpublished member just silently vanishes
from the live shelf. Verify each intended slug against the LIVE API
(`/api/library/books/<slug>/?language=en` → 200 = published; 404 = not) —
`is_published` is create-only in the seed and toggled live via the admin, so
the fixture value is not authoritative for prod. (Shipped a "For Teens" shelf
whose two most on-topic books, `the-body-of-christ-teens` and `if`, were
unpublished and so absent live — #2373.)

**A curated PLAN (`plan_seed.CURATED_PLANS`) is created ONLY in a language
where EVERY source book is published there** — one unpublished source book and
`seed_plans` silently skips it forever (logs the bland "Plans already seeded
(or source books missing)"), so the plan never appears on prod even though CI
was green. So: (a) pick source books confirmed 200-live, (b) keep the plan
English-only by anchoring on a published **English-only** book (else it becomes
creatable in other langs and the coverage guard demands `plan_translations`),
and (c) **verify creation locally** — nothing asserts a specific new plan
exists, so seed a DB and run it:
`manage.py seed_if_empty && manage.py seed_plans` then check
`Plan.objects.filter(slug=…)` has the row with its days. (The teen plan seeded
green in CI but never went live because two of its three books were unpublished
— #2380 reworked it onto published books.)

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
    no `sync:catalogues` unless it translates an English placeholder (that
    snapshot tracks missing and pending keys, not values).
  - **A NEW key you add to `en.json` needs a value in all eight catalogues
    (parity), and `messages.test.ts` also fails any non-English value that is
    byte-identical to English** — so a bare label with nothing to translate
    ("10–30 min": `min` is the standard minute abbrev in es *and* pt) trips the
    guard for those locales even when it's correct. That's what
    `SAME_AS_ENGLISH_OK` (`frontend/scripts/same-as-english.mjs`) is for — add the key there (not `PENDING_TRANSLATION`,
    which is for real un-done debt). The test throws on the first failing locale
    (es), so a second, silent collision (pt) waits behind it: fix the class, not
    the one it named. (Length-filter labels, #1899.)
- Counts: `N books · M authors` (middle dot, spaces). Never "Showing N of N".
- Chrome strings — crumbs, "Home", "Read", "Topics:", plurals — go through
  `t()` / `m.*()` even on an English-only hub; only *content* may be literal.
- Icons come from `<Icon name>`; never `▦ ☰ ✕ ▶ ✓ ♥ 🔖 📝 ✦ →` as glyphs.
- Compact buttons are `.btn-sm`, never `py-1.5` / `py-2` on `.btn`.

## Guards to extend when a page ships

Add a new route to `lib/pageShell.test.ts` — `BROWSE_PAGES` (shell + PageHeader
+ the `page-col px-5 py-10` padding) or `LEAF_PAGES` (shell only). **When a page
delegates its shell to a component** (as `books` points at `BooksShelf.svelte`,
and `articles` at `ArticleDetail`/`ArticleTopicShelf`), point the guard entry at
the **component** file, not the thin `+page.svelte` — the guard greps that file
for `.page-col`/`<PageHeader>`, so a router that only `{#if}`-switches between
components carries neither. **Five source-text guards now scan every `.svelte`
(admin exempt) — EXTEND them, don't re-add:**

- `pageShell.test.ts` — `.page-col`, `<PageHeader>` on browse, the `py-10` shell
  padding, and no `mx-auto max-w-{2xl…7xl}` shell.
- `typeScaleGuard.test.ts` — no `text-[…]`; no scoped literal `font-size`;
  `.text-display` = home hero only; `.text-h1` = the page `<h1>` only, never an
  `<h2>`–`<h6>`; and no Tailwind default size (`text-base`/`-lg`/`-xl`/`-6xl`…).
- `typeScaleGuard.test.ts` also forbids `var(--radius-*, …)` fallbacks (a
  fallback fires only on a MISSING token, so it hid the never-defined
  `--radius-chip`).
- `systemClasses.test.ts` — no scoped `<style>` redefinition of `.btn`/`.field`/
  `.seg`/`.chip`/`.eyebrow`/`.section-label`/`.count`/`.page-col`; add a modifier
  in `app.css` instead (`.btn-sm`, `.eyebrow-micro`). Exempts admin +
  `settings/+page.svelte` (its `.seg` is the E1 deferral — remove the exemption
  when E1 lands).
- `colorTokens.test.ts` (no raw hex) and `rtl.test.ts` (physical properties).

Still unguarded (deliberately or on the backlog): literal *transition* durations
— the remaining literals (a one-shot celebration keyframe, the spinner period,
the reduced-motion override) are non-transition timings that belong OFF the
three `--duration-*` tokens, so a duration guard would false-positive; and
hard-coded English on the English-only hubs (F3).

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
- **A fresh worktree has no `frontend/node_modules`.** Do a real
  `npm install --prefer-offline --no-audit --no-fund` in the worktree (~6s warm,
  and it compiles paraglide) — do NOT symlink the main checkout's `node_modules`,
  which breaks rolldown's realpath resolution (`Could not resolve 'node:module'`
  / `Tsconfig not found`) and fails every vitest/config load. `npm run check`
  then still errors once on `config.ts` (`$env/static/public has no exported
  member PUBLIC_API_BASE_URL`) until you `cp` the main checkout's
  `frontend/.env` in; that one error is env-only, not your diff.

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
> **Reconciled 2026-09-08.** Markers below were re-checked against `main` and flipped to match merged PRs; three E-group items are `[~]` because only part shipped (see each). This mirrors the STYLE_GUIDE §9 reconciliation of the same date.

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
- [x] **A8** _(shipped #1540 — kind eyebrow on the book and plan heads)_ The kind eyebrow (`Sermon · 12 min · 1855`) exists on Sermon and
  Reader only. → every leaf (Book: `Book · 7 chapters · 34 min`; Plan:
  `Reading plan · 27 days`).
- [ ] **A9** Settings and Notebook hand-roll headers; eyebrows are `Ochorus`
  (legal, notebook), the nav word (about, contact), or none. → `<PageHeader>`;
  section name or no eyebrow.
- [x] **A10** _(shipped #1537 — `.reading-page`, the one prose-page shell)_ Leaf prose measure is hand-set: `max-w-[40rem]` ×3 on Author,
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

- [x] **B1** _(shipped #1432 — Sermons & Plans filters live in the URL)_ Sermons' `q`/`book` and Plans' `length` are local `$state`, so a
  filtered shelf can't be shared or returned to with Back. → `urlFilters()`
  (Biographies).
- [x] **B2** _(shipped #1470 — one clear-filters affordance)_ "Clear filters" has three shapes: `FilterSummary` link (Books), link
  + ghost button in the EmptyState (Biographies), a `Clear` ghost button inside
  the filter row with its own copy key (Sermons). → FilterSummary `onClear`
  everywhere; retire `sermons.clear`.
- [x] **B3** _(shipped #1470 — count only while filtering)_ Result counts in five formats; Biographies renders "Showing 35 of 35
  writers" unfiltered; Topics/Plans show none; Quotes buries the total in the
  tagline. → `PageHeader` `meta` for the total, `FilterSummary` only when active.
- [x] **B4** _(shipped #1519 — seg order made consistent)_ Default grouping: Books `all`, Sermons `preacher`, with the same seg
  order on both (so Books' default is the second option). → one default; the
  default option first.
- [x] **B5** _(shipped #1519 — sort/label consistency)_ Sort is a `<select>` on three shelves and a labelled `.seg` on
  Search; visible `Length:` / `Sort:` labels exist only on Plans/Search. →
  `<select>` + `aria-label`.
- [ ] **B6** Only Biographies pins its filter bar and collapses it on mobile;
  Books has more controls and neither. Books/Sermons hard-code `scroll-mt-20`
  where Biographies/Search measure the bar. → a `FilterBar` component.
- [x] **B7** _(shipped #1519 — count badge)_ Count badges beside labels are styled six ways (`opacity-60`,
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
- [x] **C4** _(shipped #1536 — keeps the label + `aria-busy`; verified on `main`)_ Loading: Search's "Show more" replaces its label with `…` (STYLE_GUIDE
  §6 forbids this); seven surfaces show a bare `…` paragraph. → keep the label
  + `.btn-spinner` + `aria-busy`; one `<LoadingLine>` using `t('common.loading')`.

### D. Sections, cards, related

- [x] **D1** _(shipped 2026-09-08 — heading size set by role, not page. Leaf-page
  content-list headings moved `.text-h3` → `.section-label` (books: Contents /
  People / Related; authors: Books-by-X (N) / Sermons-by-X (N) / Appears-in /
  More-lives; sermons: More-on-X; ArticleDetail: Read-next) — the shelf model.
  Prose sub-sections stay `.text-h3` (books "About this book"). Contact's two
  section blocks moved `.text-h3` → `.text-h2` to match About/Settings/Legal.
  `<SectionHeader>` already renders `.text-h2`. **Group headings decided at
  `.text-h3` and left for D2** (grouped shelves + search result groups keep the
  text-h3 recipe). typeScaleGuard already reserves `.text-h1` for the `<h1>`; a
  list-vs-prose role check is not reliably automatable, so none was added.)_
  An `<h2>` renders at four sizes: `.text-h1` via `<SectionHeader>` on
  Home, `.text-h2` on Settings/About, `.text-h3` on leaf pages, `.section-label`
  on shelves — 37 distinct class combinations. → `.section-label` above a list,
  `.text-h3` above prose, `SectionHeader` drops to `.text-h2`; `.text-h1` is
  the `<h1>` only.
- [x] **D2** _(shipped 2026-09-08 — one `<GroupHeading>` component on the
  sermons recipe (`.text-h3` muted, optional portrait, linked name, `.count`)
  replaced all four hand-rolled headings: Books, Sermons, Biographies (its
  `sticky` variant) and the search-result groups. Search dropped `.section-label`
  and Biographies' count converged onto `.count`.)_ Grouped-shelf headings are
  hand-rolled four ways (Books plain text, Sermons portrait + link, Biographies
  sticky `text-text`, Search `section-label`). → the sermons recipe as a
  `GroupHeading`.
- [x] **D3** _(shipped 2026-09-08 — two hover recipes now, and only two:
  `.card-lift` (grid/banded rise) and `.card-tint` (row warm-in-place), shared
  opt-in classes in `app.css` on `--duration-fast`, each documented in
  STYLE_GUIDE §5. Every audited card wears one: book/shelf/library +
  continue-reading resume lift; sermon-row/card, article, `AuthorBioCard`,
  `PersonCard`, `AuthorTile`, `BookListRow` and the `/quotes` author card tint.
  PersonCard (border-only) and AuthorTile (bg-only) converged; the quotes card
  gained its missing ground shift. The book-cover "Begin reading →" plate is
  kept as a documented cover signature, not a second hover language.)_ Card
  hover: three lift depths and four colour treatments across `.shelf-card`,
  `.article-card`, `.sermon-row`, the quotes card, `AuthorBioCard`,
  `BookListRow`, `PersonCard`, `AuthorTile`. → lift for banded cards, border
  tint for rows; nothing else.
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
- [x] **D7** _(shipped 2026-09-08 — `FavoriteButton` rebuilt on the `.btn` family:
  labelled `.btn-sm` on leaf action rows, icon-only `.btn-icon` in reader
  toolbars; scoped CSS + literal durations deleted. All three leaf pages now pass
  `showLabel`; the sermon page dropped its hand-rolled `btn-icon` heart for
  `<FavoriteButton kind="sermon" …>`. Ships with J5.)_ Favorite: `FavoriteButton` is outside the `.btn` family (own padding,
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
  _(partial, #2426: the two shelf topic-**filter** rows — Books + Sermons —
  are now the shared `TopicFilterRow.svelte` (`.chip-scroller` container +
  `.eyebrow` label, props `topics`/`selected`/`onSelect`). Reuse it for any new
  shelf filter; the `/topics` browse chips and sermon scripture chips remain.
  Not to be confused with `TopicChips.svelte`, the "Browse by topic"
  anchor-link section.)_
- [ ] **D10** Prev/next: a `.btn` pair in the reader, bespoke bordered cards on
  the sermon page. The exit-focus pill is pasted verbatim into Author, Sermon
  and Reader. → the reader's pair; one `.focus-exit` class.
- [x] **D11** _(shipped #1427 — `SourceBadge` in the chapter reader and on author bios)_ `SourceBadge` sits under the byline on Book, after the text card on
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
- [x] **D14** _(shipped #1526 — documented `.eyebrow-micro`)_ Sermon page overrides `.eyebrow` to `--fs-micro` four times;
  `SermonCard` does it once more. → plain `.eyebrow`.

### E. Tokens and system classes

- [ ] **E1** Settings re-declares `.seg` in scoped CSS as a pill group, losing the
  `--border-strong` edge — the same toggle looks different on Settings and
  Sermons. → delete; a `.seg--pill` modifier in `app.css` if wanted.
- [~] **E2** _(partly shipped #1522 — radii back to the four and the phantom `--radius-chip` fallback gone; the bespoke `30rem` (SermonPlate) / `34rem` (Scripture) breakpoints remain)_ Radii: ten values in use against the guide's four, including
  `var(--radius-chip, 0.4rem)` on Quotes and Scripture where `--radius-chip`
  is defined nowhere, so the fallback always fires. Bespoke breakpoints
  `30rem` (SermonPlate) and `34rem` (Scripture). → `--radius-sm`/`--radius-card`;
  Tailwind breakpoints.
- [~] **E3** _(partly shipped — `ArticleCard`/`FavoriteButton` durations on the token; the reader (`0.15s`/`1.1s`) and `app.css` `btn-spin` (`0.7s`) literals remain)_ Literal durations survive in `ArticleCard`, `FavoriteButton`, the
  reader (`0.15s`, `1.1s`) and `app.css` (`btn-spin 0.7s`). → `--duration-*`.
- [ ] **E4** Two token vocabularies in scoped CSS (`--color-border` on Topic,
  Quotes, Article, Scripture; bare `--border` on Author, Sermon and the
  components) plus re-declared font-stack fallbacks
  (`var(--font-display, Georgia, serif)`). → bare tokens, no fallbacks.
- [x] **E5** _(shipped #1530 — icon-only controls use `<Icon>`; the residual glyphs are a decorative separator and admin (exempt))_ Unicode glyphs as icons in eleven places (`▦ ☰` view toggle, `✕`
  recent-search chips, `▶` ×2, `✓`, `♥` ×2, `🔖 📝`, `✦`, `→` in "see all"
  links); the hero search `<svg>` is stroke 2. → `<Icon>`; add `check`, `note`,
  `arrow-right`.
- [ ] **E6** Two text inputs bypass `.field` (home hero, command palette).
  Login duplicates `.btn` as `.google-btn`, declares `.mail-badge` twice, and
  its password-reveal control is pasted into Reset. `PwaToasts` ships a solid
  `bg: var(--accent)` button. → `.field`, `.btn`, `.btn-primary`.
- [x] **E7** _(shipped #1526 — compact buttons on `.btn-sm`)_ Compact ghost buttons hand-roll `py-1.5`/`py-2` on Settings ×4,
  Sermons and `CatalogLanguageNudge`. → `.btn-sm`.
- [ ] **E8** Near-duplicate classes: `.footer-heading` ≈ `.section-label`,
  `.sermon-row-ref` ≈ `.eyebrow`, `.navsearch` ≈ a pill `.field`; the topic
  hero still carries its own weaker `.hue-band`. `.stat-number` is admin-only
  but lives with the public classes; `--hl-*` are fixed hex that don't follow
  the theme. → fold or document.
- [~] **E9** _(partly shipped #1522 — the guard now names them; `text-6xl` (404) and `text-base` (settings/ReaderControls) remain as documented exceptions)_ Off-scale Tailwind sizes slip the type guard: `text-6xl` (error
  page), `text-lg`, `text-base` ×2. → `--fs-*`; extend the guard.

### F. Chrome and reachability

- [ ] **F1** Articles, Scripture and Quotes are footer-only (English): absent
  from the command palette and from search (`SearchHit` has no such kinds).
  → palette `COMMANDS`; an `article` hit kind.
  _Search half done (`claude/ochorus-dev-srch1-search-articles`): `ArticleHit`
  added end to end — backend `search.py` entity branch + caps + per-type page,
  `SearchHit` union, search-page facet rail, palette `hitItem()`, `type/group`
  catalogue keys ×8. English-gated by the per-language `Article` filter (no
  hard `en` check — a future translation ungates itself). **Product call:**
  Articles only; Scripture and Quotes are deferred to their own treatment —
  Scripture has no model (pages are synthesised from citations, and a reference
  query already routes to scripture-engaging sermons/chapters), and Quotes are
  review-gated sourced sentences aggregated into hub pages, not search entities.
  Flip to `[x]` once the palette-`COMMANDS` half
  (`claude/ochorus-dev-c3b9a9-reachability`) also lands on main._
- [x] **F2** _(shipped `claude/ochorus-dev-f2-chrome-order`)_ nav, footer and
  palette now derive their content-type order from one list (`$lib/contentNav`:
  `PRIMARY_NAV` + the English-only `ENGLISH_HUBS`), so the three can't drift;
  `contentNav.test.ts` pins the order. The three already **agreed** by the time
  this ran — the fix removes the triple-hardcoding that let them drift. The
  sitemap is deliberately **left out**: its section order answers a crawl /
  per-locale-coverage question (chapters-* first, topics/plans folded into
  `pages`), not a nav one — documented in `sitemap.ts` rather than force-fit.
- [x] **F3** _(shipped `claude/ochorus-dev-f3-hub-i18n`)_ The chrome on the
  Articles, Scripture and Quotes hubs — `Home`/hub crumbs (which also feed the
  BreadcrumbList JSON-LD), CTAs (`Read →`, `Browse by topic →`, `All of …`),
  section labels, `quotation(s)`/`passage(s)`/`writer(s)` counters, empty states,
  aria-labels, `Copy`/`Copied` — now goes through `t()`, filled for all 8
  advertised locales (≈47 new keys). Reuses existing keys where they exist
  (`common.home`, the `nav.*` words, `reader.previous/next`, `search.type*`).
  Pluralisation follows the `_one`/`_many` convention; scripture counts are
  always plural (a page exists only above the citation floor). The "deliberately
  English" comments on the scripture pages / CitingPassages are updated: the
  passage DATA and the SEO title/description prose stay English (they name /
  describe English-only content), but the surrounding chrome is catalogued.
  _Scope note: the content-embedding META title/description prose was left
  English by decision — see the chrome-only split. Non-English strings are a
  first pass pending native review, like the rest of the catalogues._
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
- [~] **G2** _(mostly shipped 2026-09-05: the four routes added; a
  `systemClasses.test.ts`; typeScaleGuard extended to Tailwind default sizes and
  `var(--radius-*,)` fallbacks; a `.text-h1`-reservation and a `py-10` shell-padding
  guard. LEFT: literal durations — deliberately not guarded, see above — and
  solid `bg-accent`.)_ Guard gaps: `pageShell` omits Home, Articles ×2, the Quotes index
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

---

## Backlog — second pass, 2026-09-05

A finer-grained pass over interaction/state and spacing/color/microcopy, run as
two read-only agents after the A–G sprint closed. These sit *beneath* the
structural items above: the pages now share an anatomy, so what's left is the
atom-level drift the shape guards don't yet see. Several sharpen an open A–G
item (cross-referenced with `cf.`); the rest are new. Same rules: tick and date
on merge, most reader-visible first within a group. Two agents independently
surfaced H2/I2/J1/K2/K5 — a good signal those are real, not noise.

### H. Cards & hover (cf. D3)

- [x] **H1** _(shipped 2026-09-08 with D3 — the documented two-recipe rule now
  exists: `.card-lift` / `.card-tint` shared classes in `app.css` + STYLE_GUIDE
  §5, on `--duration-fast`. The remaining stragglers converged — `PersonCard`
  (was border-only) and `AuthorTile` (was bg-only) now tint like `.sermon-card`,
  and the `/quotes` author card gained its ground shift. Row-card halves already
  shipped 2026-09-05.)_ Content cards hover in five languages:
  `.book-card`/`.shelf-card` and the sermon-of-week plate **lift**;
  `.sermon-row`, `.sermon-card`, `.article-card`, `.author-card` variously tint
  border/bg or do nothing. → two recipes only — grid card lifts, row card tints
  (this is the concrete form of D3).
- [ ] **H2** Card interior padding is five values across five families
  (`.book-card` 0.6rem, `.sermon-card` 0.85rem, `.shelf-card-body` 0.9rem,
  `.article-card` 1.1rem, `AuthorBioCard` p-5) — none on a shared band. → snap
  to `p-4`/`p-5`.
- [ ] **H3** `AuthorBioCard` is laid out two ways: one-per-row `space-y-4` on
  `/biographies` vs a two-up `grid items-start` on `era/[era]` — which also
  breaks §5's "a card grid must never set `items-start`". → era copies the
  index's `space-y-4`.

### I. Buttons & controls

- [x] **I1** _(shipped 2026-09-05 — `.btn:disabled` added; a working button that
  marks itself `aria-busy` keeps full opacity so the §6 spinner state still reads
  as working; guarded in `systemClasses.test.ts`)_ No `.btn:disabled` rule exists, so disabled Save/Sync/Export
  (settings), admin reloads and login resend render at full opacity with a normal
  cursor. → `.btn:disabled{opacity:.5;cursor:default;pointer-events:none}`.
- [x] **I2** _(shipped 2026-09-05 — the public `PwaToasts` update/undo CTA →
  `.btn btn-sm btn-primary`; `.pwa-cta` + its `filter:brightness` hover (I6)
  deleted. The admin language trio is exempt; the plan completed-day is a
  selected-state checkbox marker, not a CTA — left solid on purpose)_ Solid `bg-accent` CTAs violate §5's soft-primary rule: `PwaToasts`
  install toast (public), the plan completed-day marker, the admin language trio.
  → `.btn.btn-primary` (cf. E6, G2's "solid `bg-accent`").
- [ ] **I3** The busy-button pattern is split: spinner + kept label + `aria-busy`
  (login/reset/search) vs label swapped to a gerund with no spinner
  (`LanguageSettingsCard` "Saving…", admin "Refreshing…"). → the spinner pattern
  (cf. C4).
- [ ] **I4** `.google-btn` re-implements `.btn` with the default surface fill and
  no Google brand colour — not even the sanctioned vendor exception. →
  `class="btn w-full"` + the glyph (cf. E6).
- [ ] **I5** Disabled opacity disagrees where it is set at all: 0.4 (`.widthctl`),
  0.5 (`.google-btn`), 0.5 (a call site). → one value via I1.
- [x] **I6** _(shipped 2026-09-05 with I2 — `.pwa-cta:hover` removed)_ `.pwa-cta:hover` uses `filter:brightness(1.05)` — a hover used
  nowhere else. → fold into `.btn-primary` (rides with I2).

### J. Pills & badges

- [x] **J1** _(shipped 2026-09-05 — one `.tag` class in `app.css`; 9 hand-rolled
  copies across 8 files swapped; added to the `systemClasses` owned set.
  `TopicChips` keeps its own larger px-4/py-2 treatment on purpose)_ A "tag/related" nav pill is hand-rolled ~9 times (search, book ×2,
  sermon, author, article, reader, favorites, `TopicChips`) drifting on text
  colour, fill and padding. → one `.tag`/`.pill-link` class (this is the concrete
  form of D9).
- [ ] **J2** Two pill hover languages: `.chip:hover` → bg surface-2 (no accent)
  vs the nav pills → border+text-accent (no bg). → one pill hover.
- [ ] **J3** Notebook's colour filter active state skips the accent-soft fill
  every other selected filter gets (border+text-accent only). → render as
  `.chip.active`.
- [ ] **J4** Two accent-soft eyebrow badges, different padding: bio count px-1.5
  vs "FULL LIFE" px-2 py-0.5. → a shared `.badge-soft`.
- [x] **J5** _(shipped 2026-09-08 — one saved state everywhere: filled heart tinted
  `--accent` via the `text-accent` active convention the reader toggles already
  use; `--danger` is now destructive-only. Documented in STYLE_GUIDE §5. Ships
  with D7.)_ The saved-heart is red (`FavoriteButton` `--danger`) in one place and
  indigo (`text-accent`, sermon page) in another. → one token for "saved" (cf. D7).

### K. Colour & radius

- [ ] **K1** Blockquote/pull-quote left-rule uses four colours + two widths
  (`.reading` accent-soft, `.bio` gold, `.article-body` solid accent, the book
  "about" figure a 2px border) where §1 says gold. → one `.pullquote`.
- [ ] **K2** Two token vocabularies in scoped CSS: `--color-*` (12 files) vs bare
  `--*` (25 files). → bare tokens (this is E4, re-counted).
- [ ] **K3** The "·" middot separator is drawn at opacity-40/50/60 + bare
  `text-muted`, with varying margins. → one `.sep` helper.
- [ ] **K4** Secondary text is `text-muted` vs `text-muted/60` vs `/70` vs
  `opacity-*` interchangeably. → `text-muted` (or `.count` for figures).
- [ ] **K5** "Full-round" is written three ways: `rounded-full`, `999px`,
  `9999px`. → one (`--radius-pill`).
- [ ] **K6** `ArticleCard` + the article page use off-scale radii `0.75rem`,
  `0.5rem`, `0.25rem`. → tokens (cf. D4, E2).

### L. Spacing rhythm

- [ ] **L1** Leaf-page section separators range `mt-8`→`mt-16` for the same
  "next titled section" role (book mixes 8/12, author 14/16, sermon 12); the
  identical prev/next nav is `mt-14` on the reader, `mt-12` on the sermon. → one
  band value.
- [ ] **L2** Bordered-footer padding drifts `pt-5`/`pt-6`/`pt-8`. → one `pt-6`.
- [ ] **L3** Anchor scroll-offset is computed four ways; only two track the
  sticky bar (`calc(var(--pinned-offset)…)` vs hard-coded `scroll-mt-20` on
  sermons/books, `scroll-margin-top:5rem`, `scroll-mt-24`). → the `--pinned-offset`
  calc (cf. B6, §3).

### M. Duplication (forms, dividers, rows)

- [ ] **M1** The password-reveal control is copy-pasted between `login` and
  `reset-password` (the reset copy comments "Mirrors /login's"). → a
  `PasswordField.svelte` (cf. E6).
- [ ] **M2** `.mail-badge` is declared twice (the first copy dead) and
  triplicated, and is shape-identical to `.emblem-chip`. → delete the dead block;
  make it an `.emblem-chip` variant (cf. E6, E8).
- [ ] **M3** "Label between two hairlines" divider is built two ways: `.or-divider`
  (`--border`) vs the error page's `bg-gold/30` spans. → one divider helper.
- [ ] **M4** The search field has three chromes; two bypass `.field` and its
  `--border-strong` edge (CommandPalette, home hero use a `--border` hairline).
  → base both on `.field` (cf. E6).
- [ ] **M5** Settings re-implements the prefs row: `.setting-row`/`.setting-label`
  duplicate `app.css`'s `.prefs-row`/`.prefs-label` with drifted padding. →
  promote one shared class.

### N. Loading & state

- [ ] **N1** Seven bare "…" loading placeholders with no skeleton/spinner/
  `role=status` (notebook, settings, ScripturePopover, DefinePopover, NotesDrawer,
  TocDrawer, CommandPalette) while a skeleton pattern and `.btn-spinner` already
  exist. → one shared loading affordance (this is the drawer/popover half of C4).

### Second-pass order

1. ~~**I1 + I2 + H1 + J1** — the batch-of-four~~ _(shipped 2026-09-05: disabled
   buttons, public solid CTA, the two hue-less row-card hovers, the tag pill;
   `systemClasses.test.ts` extended with `tag` + a `.btn:disabled` assertion.)_
2. Everything else is lower-visibility cleanup — pull from it opportunistically,
   not as a push. K3 (`.sep`) and K4 (secondary text) touch the most files and
   are best folded into whatever leaf-page work comes next.
