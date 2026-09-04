#!/usr/bin/env python3
"""Build an on-brand (Ochorus paper theme) HTML doc of the design-consistency
audit — the 10 issues to fix first (with how-to), then the full A–G backlog —
with Fraunces + Hanken Grotesk embedded as base64 woff2. Render to PDF with
headless Chrome (see docs/ochorus-docs-pdf-recipe)."""
import base64
import html
from pathlib import Path

FONTS = Path.home() / "dev/ochorus/frontend/node_modules/@fontsource-variable"
OUT = Path(__file__).parent / "design-consistency.html"


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


fraunces = b64(FONTS / "fraunces/files/fraunces-latin-wght-normal.woff2")
hanken = b64(FONTS / "hanken-grotesk/files/hanken-grotesk-latin-wght-normal.woff2")

# --- the 10 to do first ------------------------------------------------------
# (n, title, tag, what, model, how, guard)
FIRST10 = [
    (1, "Unify the page-title suffix",
     "1 line each · sitewide",
     "The browser-tab title ends “ — Ochorus” on 39 pages and “ · Ochorus” on 7 (book, quotes, articles, both scripture pages; the era page mixes both).",
     "Seo.svelte already documents “ — Ochorus” as the suffix.",
     "Move the suffix into Seo.svelte so no page types it, then pass just the page name from each caller. For the five pages that still hand-write <svelte:head>, this rides along with fix 2. One em dash, spaces on both sides; leaf pages read “Title — Author — Ochorus”.",
     "Add a Seo.test.ts assertion that no route sets a literal “· Ochorus” / “— Ochorus” in a title string."),
    (2, "One page header, one head block",
     "4 headers + 5 heads",
     "Era, Quotes, Scripture and Articles hand-roll their <header>; five browse pages hand-write <svelte:head>. Each differs in margins and one tagline is a size small.",
     "Topics for the header; the Seo component for the head.",
     "Swap each hand-rolled header for <PageHeader eyebrow title tagline meta>, and each <svelte:head> for <Seo…>. PageHeader already applies .text-h1 and the mb-8 rhythm, so the size and spacing drift disappears for free.",
     "Add the four routes to BROWSE_PAGES in pageShell.test.ts; it then fails any browse page missing <PageHeader>."),
    (3, "One shell padding",
     "codemod",
     "The page shell is py-10 on twelve pages, py-6 on five, py-8 on one — so the content edge jumps vertically on every navigation.",
     "py-10 (the majority).",
     "Fold the vertical padding into .page-col itself (py-10) and delete the per-page py-* utilities, or run a codemod replacing them with py-10. Keep px-5. Drop the stray mt-5/mt-4 between breadcrumb and title while you are there.",
     "Extend pageShell.test.ts to reject a py-\\d+ utility on the .page-col element."),
    (4, "No page crashes or lies on a failed fetch",
     "reader-stranding",
     "Biographies, the era page and Quotes have unguarded loaders that crash to the error route; Articles and Scripture swallow the error and tell the reader the shelf is empty — the exact anti-pattern loadShelf() was written to end.",
     "Topics: loadShelf() then <EmptyState onRetry>.",
     "Route all five loaders through loadShelf(), which returns {items, loadError}. Render <EmptyState message={t('common.loadError')} onRetry/> when loadError is true. The page then shows Try again instead of a false “nothing here” or a white error screen.",
     "A grep test that every browse +page.ts awaiting a list helper wraps it in loadShelf."),
    (5, "One empty state",
     "8 renderings → 1",
     "The same “nothing to show” moment is drawn eight ways: a bare centered paragraph (Books, era, Search), a message with no button (Sermons), a hand-copied panel (Search), and five smaller variants in drawers and popovers.",
     "The EmptyState component.",
     "Route every case through <EmptyState>, adding a compact prop for the drawer/popover variants. Filtered-to-nothing takes an action snippet that clears the filters; a genuine empty takes the read-English action.",
     "systemClasses.test.ts (new) can flag a <p class=\"py-16 text-center…\"> pattern outside EmptyState."),
    (6, "A way out of an empty language",
     "small",
     "When a language has no rows, Books offers “Read the English library” and Plans/Sermons show the nudge — but Topics gives a dead-end sentence and Biographies shows nothing.",
     "Books: CatalogLanguageNudge + an EmptyState action.",
     "Widen CatalogLanguageNudge's kind union from books|sermons|plans to include topics and authors, drop it into those two pages, and give Topics' EmptyState the same read-English action Books uses.",
     "—"),
    (7, "Filters that live in the URL",
     "2 pages",
     "Sermons' search + Bible-book and Plans' length are component state, so a filtered shelf can't be shared, reloaded, or recovered with the Back button — the problem urlFilters() already solved for Books and Biographies.",
     "Biographies' urlFilters() wiring.",
     "Replace the local $state with urlFilters({ defaults: { q: '', book: '' } }) on Sermons and { length: 'all' } on Plans. View preferences (grid/list, sort) correctly stay in localStorage — only the shelf-defining filters move to the URL.",
     "—"),
    (8, "One breadcrumb, matching its own data",
     "3 pages",
     "Author, Sermon and Reader hand-roll their breadcrumb <nav> with three different trails (with/without Home, with/without the current item). Worse, the sermon's visible trail (Sermons › Author) contradicts its BreadcrumbList JSON-LD (Home › Sermons › Title).",
     "The book page: one crumbs array feeds both.",
     "Build a single crumbs = [{name, href}, …] array on each page and pass it to <Breadcrumb items={crumbs}> and to the JSON-LD builder, so the picture and the structured data can never disagree. Home first, current item last with aria-current.",
     "A test that each leaf page's visible Breadcrumb items equal its BreadcrumbList itemListElement."),
    (9, "The unreviewed-translation badge, everywhere it should be",
     "safety rule",
     "SourceBadge sits under the byline on a book, after the text on a sermon — and is absent from the chapter reader and the author bio. So a reader inside an ai_unreviewed chapter, or reading a machine-translated biography, never sees the “awaiting native review” warning CLAUDE.md requires.",
     "The book page: badge under the byline.",
     "Render <SourceBadge> under the byline on every leaf head, and add it to the reader's eyebrow line and the author-bio band whenever source_type is ai_unreviewed. This is a correctness fix, not just a visual one — it is the one item on this list that changes what a reader is told.",
     "readerDirection.test.ts already guards the reader; add a sibling asserting the reader references source_type."),
    (10, "An <h2> is one size",
     "many files",
     "A section heading renders at four sizes depending on the page: .text-h1 via SectionHeader on Home, .text-h2 on Settings/About, .text-h3 on leaf pages, .section-label on shelves — 37 distinct class combinations in all.",
     "The rule: label-above-a-list = .section-label; titled prose section = .text-h3; SectionHeader drops to .text-h2; .text-h1 is the page <h1> only.",
     "Settle the rule in STYLE_GUIDE §5, change SectionHeader to render .text-h2, then sweep the pages onto the two roles. Best done as its own PR because it touches many files and is pure find-replace once the rule is fixed.",
     "A guard that .text-h1 appears only on an <h1>, and .text-display only on the home hero (the latter already exists)."),
]

# --- full backlog (A–G) --------------------------------------------------------
# (letter, name, [(id, title, fix), …])
BACKLOG = [
    ("A", "Shells, headers, titles", [
        ("A1", "Four hand-rolled page headers (era, quotes, scripture, articles), each with different margins; Scripture's tagline is a size small.", "→ <PageHeader> (Topics); add to BROWSE_PAGES."),
        ("A2", "Shell padding py-10 ×12, py-6 ×5, py-8 ×1; breadcrumb-to-title gap varies.", "→ py-10, no extra gap, folded into .page-col."),
        ("A3", "Two H1 registers: brand title under a nav-word eyebrow (Sermons, Biographies) vs the nav word itself; title tag ≠ h1 on those two.", "→ pick one register, document in §5."),
        ("A4", "Title suffix “ — Ochorus” ×39 vs “ · Ochorus” ×7.", "→ “ — Ochorus”, suffix inside Seo.svelte."),
        ("A5", "Five browse pages hand-write <svelte:head>; five use <Seo>.", "→ <Seo>."),
        ("A6", "Quotes/Scripture/Articles show a Home›X breadcrumb; the nav'd shelves don't.", "→ drop the visible trail, keep JSON-LD."),
        ("A7", "Author, Sermon and Reader hand-roll breadcrumbs with three trails; Sermon's contradicts its JSON-LD.", "→ <Breadcrumb>, one crumbs array feeding both."),
        ("A8", "The kind eyebrow (“Sermon · 12 min · 1855”) exists on only two of ten leaf pages.", "→ every leaf."),
        ("A9", "Settings and Notebook hand-roll headers; eyebrows are “Ochorus”, the nav word, or none.", "→ <PageHeader>."),
        ("A10", "Leaf prose measure hand-set at 36/40/42/44rem; .reading-page (About, Legal) is defined nowhere.", "→ one .prose-measure class."),
        ("A11", "Login/Reset use max-w-[26rem], invisible to the shell guard.", "→ .page-col--narrow; widen the regex."),
    ]),
    ("B", "Filters, counts, state", [
        ("B1", "Sermons' q/book and Plans' length are local state — a filtered shelf can't be shared or recovered with Back.", "→ urlFilters() (Biographies)."),
        ("B2", "“Clear filters” has three shapes across Books, Biographies and Sermons.", "→ FilterSummary onClear everywhere."),
        ("B3", "Counts in five formats; Biographies shows “Showing 35 of 35” unfiltered; Topics/Plans show none.", "→ PageHeader meta for the total; FilterSummary only when active."),
        ("B4", "Books defaults to “All”, Sermons to “By preacher”, with the same control order.", "→ one default; default option first."),
        ("B5", "Sort is a <select> on three shelves, a labelled toggle on Search; visible labels only on Plans/Search.", "→ <select> + aria-label."),
        ("B6", "Only Biographies pins its filter bar and collapses it on mobile; Books has more controls and neither.", "→ a FilterBar component."),
        ("B7", "Count badges beside labels styled six ways.", "→ one .count recipe."),
    ]),
    ("C", "Empty, error, loading", [
        ("C1", "Three loaders crash to the error route; two swallow the error and claim the shelf is empty.", "→ loadShelf + EmptyState onRetry (Topics)."),
        ("C2", "Eight empty-state renderings; one button loses its label to “…”.", "→ <EmptyState> with an action; a compact prop."),
        ("C3", "Zero rows in a language: way-out on Books, nudge on Plans/Sermons, dead end on Topics, nothing on Biographies.", "→ extend CatalogLanguageNudge; action on all."),
        ("C4", "Loading: Search's “Show more” replaces its label with “…”; seven surfaces show a bare “…”.", "→ keep label + .btn-spinner + aria-busy."),
    ]),
    ("D", "Sections, cards, related", [
        ("D1", "An <h2> renders at four sizes; 37 class combinations; SectionHeader is .text-h1.", "→ section-label above a list, text-h3 above prose; SectionHeader → .text-h2."),
        ("D2", "Grouped-shelf headings hand-rolled four ways (Books plain, Sermons portrait+link, Biographies sticky, Search label).", "→ the sermons recipe as GroupHeading."),
        ("D3", "Card hover: three lift depths, four colour treatments.", "→ lift for banded cards, border tint for rows."),
        ("D4", "ArticleCard bespoke (literal radius/durations, “Read →”, h3 under h1); quotes card has no heading.", "→ rebuild on the row family; h2 under the h1."),
        ("D5", "Home shelves and the 404 redraw cards that have components (ContinueReading, PlansProgress, error page).", "→ the components."),
        ("D6", "Related blocks use five components; the sermon's “More sermons” is unbounded; four leaf pages have none.", "→ card components, capped 4–6 (Book)."),
        ("D7", "Favorite is outside the .btn family; the sermon uses a btn-icon heart instead; only Author shows a label.", "→ rebuild on .btn.btn-sm; one label policy."),
        ("D8", "“Search in this X” is a ghost button / small ghost / text link; Author has no primary action; Plan's finished state is a <p> as a button.", "→ Book's action row."),
        ("D9", "Topic/scripture chip rows hand-rolled eight times, three colourways; sermon chips link to search where book chips link to /scripture.", "→ .chip + .eyebrow label; shared href logic."),
        ("D10", "Prev/next: a .btn pair in the reader, bespoke cards on the sermon; the exit-focus pill is pasted three times.", "→ the reader's pair; one .focus-exit class."),
        ("D11", "SourceBadge is absent from the chapter reader and author bio — an unreviewed translation is read with no warning.", "→ under the byline everywhere; add to the reader."),
        ("D12", "Language fallback is silent on six pages; Topic 404s instead; the reader reports the wrong language in JSON-LD.", "→ fallback + visible notice + lang from the served edition."),
        ("D13", "Summary is an h2+prose on Book, a bordered accent callout on Sermon.", "→ one treatment."),
        ("D14", "The sermon page overrides .eyebrow to micro size five times.", "→ plain .eyebrow."),
    ]),
    ("E", "Tokens and system classes", [
        ("E1", "Settings redefines .seg in scoped CSS as a pill, losing the strong edge — the same toggle looks different there.", "→ delete; a .seg--pill modifier if wanted."),
        ("E2", "Ten radii against the guide's four, incl. var(--radius-chip, 0.4rem) where the token is defined nowhere; bespoke breakpoints 30/34rem.", "→ --radius-sm/--radius-card; Tailwind breakpoints."),
        ("E3", "Literal durations in ArticleCard, FavoriteButton, the reader and app.css.", "→ --duration-*."),
        ("E4", "Two token vocabularies in scoped CSS (--color-border vs --border) plus re-declared font-stack fallbacks.", "→ bare tokens, no fallbacks."),
        ("E5", "Unicode glyphs as icons in eleven places; the hero search icon is the wrong stroke weight.", "→ <Icon>; add check/note/arrow-right."),
        ("E6", "Two inputs bypass .field; Login duplicates .btn as .google-btn; PwaToasts ships a solid indigo button.", "→ .field, .btn, .btn-primary."),
        ("E7", "Compact ghost buttons hand-roll py-1.5/py-2 in six places.", "→ .btn-sm."),
        ("E8", "Near-duplicate classes: .footer-heading≈.section-label, .sermon-row-ref≈.eyebrow, .navsearch≈a pill .field; --hl-* are fixed hex.", "→ fold or document."),
        ("E9", "Off-scale Tailwind sizes slip the guard: text-6xl, text-lg, text-base×2.", "→ --fs-*; extend the guard."),
    ]),
    ("F", "Chrome and reachability", [
        ("F1", "Articles, Scripture and Quotes are footer-only — absent from the command palette and from search.", "→ add to COMMANDS; an article hit kind."),
        ("F2", "The sitemap orders content types differently from the nav.", "→ derive both from one list."),
        ("F3", "Hard-coded English chrome on the English-only hubs and on Articles (which claims to be translation-ready).", "→ t() keys now."),
        ("F4", "Plan/Topic can ship an empty meta description; reader/articles/scripture emit no og:image; the reader emits no BreadcrumbList.", "→ localized fallback, one length, section OG cards."),
    ]),
    ("G", "Guide and guards", [
        ("G1", "STYLE_GUIDE drift: ghost-button border, body line-height, nav/footer description and §9 counts were stale.", "✓ fixed alongside the new page-design skill."),
        ("G2", "Guard gaps: pageShell omits Home/Articles/quotes-index/auth pages and misses max-w-xl/max-w-[…]; nothing checks durations, radius fallbacks, scoped overrides of system classes, solid bg-accent, or hard-coded English.", "→ add the routes; a systemClasses.test.ts; extend typeScaleGuard."),
    ]),
]


def esc(s):
    return html.escape(s)


def first_html(n, title, tag, what, model, how, guard):
    guard_row = f"""<p><span class="lbl gd">Guard</span>{esc(guard)}</p>""" if guard != "—" else ""
    return f"""<div class="do">
      <div class="num">{n}</div>
      <div class="do-body">
        <div class="do-head"><h3>{esc(title)}</h3><span class="tagchip">{esc(tag)}</span></div>
        <p><span class="lbl">Problem</span>{esc(what)}</p>
        <p><span class="lbl md">Model</span>{esc(model)}</p>
        <p><span class="lbl">How</span>{esc(how)}</p>
        {guard_row}
      </div>
    </div>"""


def row_html(gid, title, fix):
    return f"""<div class="row">
      <span class="rid">{esc(gid)}</span>
      <span class="rtx"><b>{esc(title)}</b> <span class="fix">{esc(fix)}</span></span>
    </div>"""


dos = "\n".join(first_html(*x) for x in FIRST10)

groups = ""
for letter, name, items in BACKLOG:
    rows = "\n".join(row_html(*i) for i in items)
    groups += f"""<section class="cat">
      <div class="cat-head"><span class="badge">{letter}</span><h2>{esc(name)}</h2><span class="count">{len(items)}</span></div>
      {rows}
    </section>\n"""

DOC = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<style>
@font-face {{ font-family:'Fraunces'; src:url(data:font/woff2;base64,{fraunces}) format('woff2'); font-weight:100 900; font-display:block; }}
@font-face {{ font-family:'Hanken'; src:url(data:font/woff2;base64,{hanken}) format('woff2'); font-weight:100 900; font-display:block; }}
:root{{
  --bg:#faf6ef; --surface:#ffffff; --surface-2:#f4eee3; --text:#221c15; --muted:#6e6358;
  --accent:#3f3d9a; --gold:#b07d22; --border:#e8dfcf; --soft:#ecebf7; --soft-b:#d9d7f0;
  --serif:'Fraunces',Georgia,serif; --sans:'Hanken','Helvetica Neue',Arial,sans-serif;
  --mono:'SF Mono','SFMono-Regular','Menlo','Consolas',monospace;
}}
@page {{ size: A4; margin: 17mm 15mm; }}
*{{ box-sizing:border-box; }}
html,body{{ margin:0; padding:0; }}
body{{ font-family:var(--sans); color:var(--text); background:var(--bg); font-size:10.5pt; line-height:1.5; }}

/* Cover */
.cover{{ height:263mm; display:flex; flex-direction:column; justify-content:center; text-align:center; page-break-after:always; }}
.cover .mark{{ font-family:var(--serif); font-weight:600; letter-spacing:.42em; color:var(--gold); font-size:13pt; text-indent:.42em; }}
.cover .rule{{ width:54px; height:2px; background:var(--accent); margin:20px auto 26px; }}
.cover h1{{ font-family:var(--serif); font-weight:600; font-size:38pt; line-height:1.06; letter-spacing:-.01em; color:var(--text); margin:0 0 14px; }}
.cover .sub{{ font-family:var(--serif); font-size:15.5pt; color:var(--muted); font-style:italic; margin:0 auto; max-width:135mm; line-height:1.35; }}
.cover .meta{{ margin-top:38px; color:var(--muted); font-size:9.5pt; }}
.cover .tag{{ margin-top:6px; font-size:8.5pt; letter-spacing:.04em; }}

/* Intro */
.intro h2{{ font-family:var(--serif); font-weight:600; font-size:19pt; margin:0 0 8px; }}
.intro p{{ max-width:168mm; color:#3a332a; }}
.callout{{ background:var(--surface); border:1px solid var(--border); border-left:4px solid var(--accent);
  border-radius:10px; padding:14px 18px; margin:16px 0 8px; }}
.callout .k{{ font-family:var(--sans); font-weight:700; color:var(--accent); text-transform:uppercase; letter-spacing:.06em;
  font-size:8pt; display:block; margin-bottom:4px; }}
.callout strong{{ color:var(--text); }}

/* Section title */
.sec-title{{ page-break-before:always; }}
.sec-title h2{{ font-family:var(--serif); font-weight:600; font-size:20pt; margin:0 0 4px; }}
.sec-title .lede{{ color:var(--muted); margin:0 0 15px; max-width:168mm; }}

/* Do-first card */
.do{{ display:flex; gap:13px; background:var(--surface); border:1px solid var(--border); border-radius:10px;
  padding:13px 16px; margin-bottom:10px; page-break-inside:avoid; }}
.do .num{{ font-family:var(--serif); font-weight:600; font-size:19pt; color:var(--accent);
  min-width:26px; text-align:right; line-height:1; }}
.do-body{{ flex:1; }}
.do-head{{ display:flex; align-items:baseline; justify-content:space-between; gap:10px; margin-bottom:6px; }}
.do-head h3{{ font-family:var(--sans); font-weight:700; font-size:12pt; margin:0; color:var(--text); letter-spacing:-.005em; }}
.tagchip{{ font-family:var(--sans); font-weight:700; font-size:7pt; letter-spacing:.05em; text-transform:uppercase;
  color:var(--muted); background:var(--surface-2); border:1px solid var(--border); border-radius:20px; padding:2px 8px; white-space:nowrap; }}
.do-body>p{{ margin:0 0 4px; color:#3a332a; font-size:9.7pt; line-height:1.46; }}
.lbl{{ font-family:var(--sans); font-weight:700; font-size:7.4pt; text-transform:uppercase; letter-spacing:.07em;
  color:var(--accent); display:inline-block; min-width:52px; margin-right:3px; vertical-align:baseline; }}
.lbl.md{{ color:var(--gold); }}
.lbl.gd{{ color:var(--muted); }}

/* Backlog rows */
.cat{{ margin-top:16px; page-break-inside:avoid; }}
.cat-head{{ display:flex; align-items:center; gap:10px; border-bottom:1px solid var(--border); padding-bottom:7px; margin-bottom:9px; }}
.cat-head .badge{{ font-family:var(--serif); font-weight:600; color:#fff; background:var(--accent);
  width:26px; height:26px; border-radius:7px; display:flex; align-items:center; justify-content:center; font-size:12pt; }}
.cat-head h2{{ font-family:var(--serif); font-weight:600; font-size:16pt; margin:0; color:var(--text); flex:1; }}
.cat-head .count{{ font-family:var(--sans); font-weight:700; font-size:8pt; color:var(--muted);
  background:var(--surface-2); border-radius:20px; padding:2px 9px; }}
.row{{ display:flex; gap:9px; padding:5px 2px 6px; border-bottom:1px solid var(--border); page-break-inside:avoid; }}
.row:last-child{{ border-bottom:none; }}
.rid{{ font-family:var(--mono); font-weight:700; font-size:8.5pt; color:var(--accent); min-width:24px; padding-top:.5pt; }}
.rtx{{ flex:1; font-size:9.5pt; line-height:1.42; color:#3a332a; }}
.rtx b{{ color:var(--text); font-weight:600; }}
.fix{{ color:var(--muted); }}

.foot{{ text-align:center; color:var(--muted); font-size:8pt; letter-spacing:.05em; margin-top:22px; padding-top:10px; border-top:1px solid var(--border); }}
</style></head><body>

<div class="cover">
  <div class="mark">OCHORUS</div>
  <div class="rule"></div>
  <h1>Design Consistency</h1>
  <div class="sub">An audit of the website, the ten fixes to make first,<br>and the full backlog behind them</div>
  <div class="meta">
    A review of ochorus.com &mdash; all 40 public routes<br>
    <span class="tag">Prepared with Claude &middot; 4 September 2026</span>
  </div>
</div>

<section class="intro">
  <h2>What this is</h2>
  <p>A pass over every public page of Ochorus &mdash; read in code and walked on the live site &mdash; looking
  for the places where one page drifts from its neighbours. A list page should look like the other list pages,
  with its own features layered on; a book should look like a sermon looks like a plan. This is where they
  don&rsquo;t.</p>
  <div class="callout">
    <span class="k">The finding that shapes the list</span>
    The <strong>atoms are already consistent</strong> &mdash; colour tokens, the type scale, buttons, form
    fields and cards are shared and in good order. The drift has moved up a level, to <strong>anatomy</strong>:
    the order of parts on a page and which existing page to copy. A reader walking Books &rarr; Sermons &rarr;
    Quotes &rarr; Articles meets <strong>four page-header shapes, three top paddings, two title suffixes, three
    breadcrumb trails, eight empty-state renderings and headings at four sizes</strong> &mdash; every one built
    from the right tokens. The fix is a <em>page-design</em> playbook (now written) that says, for each kind of
    page, what goes where and which page is the model. The ten below are where to start.</p>
  </div>
  <p style="margin-top:12px;font-size:9.6pt;color:var(--muted)">Each of the ten is a single, shippable change.
  <b style="color:var(--text)">Model</b> names the page already doing it right; <b style="color:var(--text)">How</b>
  is the approach; <b style="color:var(--text)">Guard</b> is the test that keeps it from drifting back. The full
  A&ndash;G backlog &mdash; 46 items with file evidence &mdash; follows, and lives in the
  <span style="font-family:var(--mono);font-size:8.6pt">page-design</span> skill.</p>
</section>

<section class="sec-title">
  <h2>The ten to do first</h2>
  <p class="lede">Ordered by leverage: reader-visible, low-effort, and unblocking the rest. The first three are
  near-mechanical and touch the whole site at once; four through six stop a reader ever hitting a dead end;
  the rest bring the leaf pages and headings into one voice.</p>
  {dos}
</section>

<section class="sec-title">
  <h2>The full backlog</h2>
  <p class="lede">Everything the audit found, grouped by theme. Each line is a drift and the page to converge on;
  &ldquo;&rarr;&rdquo; names the model or the fix. The ten above are drawn from groups A, B, C and D.</p>
  {groups}
  <div class="foot">OCHORUS &middot; DESIGN CONSISTENCY AUDIT &middot; SEE THE PAGE-DESIGN SKILL FOR FILE EVIDENCE</div>
</section>

</body></html>"""

OUT.write_text(DOC, encoding="utf-8")
print("wrote", OUT, f"({len(DOC)//1024} KB, fonts embedded)")
