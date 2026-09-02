#!/usr/bin/env python3
"""Build "Per-Quote Indexable URLs": a 2-page, print-ready A4 implementation
plan in the Ochorus paper theme, with Fraunces + Hanken Grotesk embedded as
base64 woff2. Render to PDF with headless Chrome (see render command at bottom).

Shares the paper-theme CSS with build_claude_playbook_pdf.py (kept inline per
the convention that each docs/build_*_pdf.py is self-contained)."""
import base64
from pathlib import Path

FONTS = Path.home() / "dev/ochorus/frontend/node_modules/@fontsource-variable"
OUT = Path(__file__).parent / "perquote-seo.html"


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


fraunces = b64(FONTS / "fraunces/files/fraunces-latin-wght-normal.woff2")
hanken = b64(FONTS / "hanken-grotesk/files/hanken-grotesk-latin-wght-normal.woff2")
hanken_i = b64(FONTS / "hanken-grotesk/files/hanken-grotesk-latin-wght-italic.woff2")

CSS = """
@font-face { font-family:'Fraunces'; src:url(data:font/woff2;base64,FRAUNCES) format('woff2'); font-weight:100 900; font-display:block; }
@font-face { font-family:'Hanken'; src:url(data:font/woff2;base64,HANKEN) format('woff2'); font-weight:100 900; font-display:block; }
@font-face { font-family:'Hanken'; src:url(data:font/woff2;base64,HANKENI) format('woff2'); font-weight:100 900; font-style:italic; font-display:block; }
:root{
  --bg:#faf6ef; --surface:#ffffff; --surface-2:#f6f1e7; --text:#221c15; --muted:#6e6358;
  --accent:#3f3d9a; --gold:#b07d22; --border:#e6dccb; --soft:#ecebf7; --soft-b:#d9d7f0;
  --green:#2f6b4f; --red:#a4402f;
  --serif:'Fraunces',Georgia,serif; --sans:'Hanken','Helvetica Neue',Arial,sans-serif;
  --mono:'SF Mono','SFMono-Regular','Menlo','Consolas',monospace;
}
@page { size:A4; margin:0; }
*{ box-sizing:border-box; }
html,body{ margin:0; padding:0; }
body{ font-family:var(--sans); color:var(--text); background:var(--bg);
  font-size:9.1pt; line-height:1.35; -webkit-print-color-adjust:exact; print-color-adjust:exact; }

.page{ width:210mm; height:297mm; padding:11mm 15mm 13mm; position:relative;
  page-break-after:always; overflow:hidden; background:var(--bg); }
.page:last-child{ page-break-after:auto; }

.rh{ display:flex; justify-content:space-between; align-items:baseline;
  border-bottom:1px solid var(--border); padding-bottom:4px; margin-bottom:7px; }
.rh .t{ font-family:var(--sans); font-weight:700; font-size:7pt; letter-spacing:.14em;
  text-transform:uppercase; color:var(--gold); }
.rh .n{ font-family:var(--serif); font-size:8.5pt; color:var(--muted); }
.pfoot{ position:absolute; left:15mm; right:15mm; bottom:5mm; display:flex;
  justify-content:space-between; font-size:6.8pt; letter-spacing:.09em;
  text-transform:uppercase; color:#a1968a; border-top:1px solid var(--border); padding-top:4px; }

h1.title{ font-family:var(--serif); font-weight:600; font-size:30pt; line-height:1.02;
  letter-spacing:-.015em; margin:0 0 6px; }
.deck{ font-family:var(--serif); font-style:italic; font-size:11.5pt; color:var(--muted);
  line-height:1.3; margin:0 0 10px; max-width:165mm; }
h2{ font-family:var(--serif); font-weight:600; font-size:14pt; margin:0 0 5px; letter-spacing:-.005em; }
h2 .kicker{ font-family:var(--sans); font-weight:700; font-size:7pt; letter-spacing:.14em;
  text-transform:uppercase; color:var(--accent); display:block; margin-bottom:2px; }
h3{ font-family:var(--sans); font-weight:700; font-size:9.4pt; margin:0 0 3px; letter-spacing:-.002em; }
h4{ font-family:var(--sans); font-weight:700; font-size:8pt; letter-spacing:.1em;
  text-transform:uppercase; color:var(--accent); margin:0 0 4px; }
p{ margin:0 0 5px; }
.lede{ color:#463d33; margin:0 0 8px; font-size:9.4pt; }
.sec{ margin-bottom:9px; }
b, strong{ font-weight:700; }
em{ font-style:italic; }
code{ font-family:var(--mono); font-size:8pt; background:var(--soft); color:#322d5a;
  border:1px solid var(--soft-b); border-radius:3px; padding:0 3px; white-space:nowrap; }
a{ color:var(--accent); text-decoration:none; }

.cols{ display:flex; gap:7mm; }
.cols > *{ flex:1; min-width:0; }
.tight p{ margin-bottom:3px; }

.card{ background:var(--surface); border:1px solid var(--border); border-radius:8px;
  padding:7px 10px; margin-bottom:5px; }
.card.acc{ border-left:3px solid var(--accent); }
.card.gold{ border-left:3px solid var(--gold); }
.card.green{ border-left:3px solid var(--green); }
.card.red{ border-left:3px solid var(--red); }
.card p:last-child{ margin-bottom:0; }
.card .why{ color:var(--muted); font-size:8.4pt; }

.callout{ background:var(--soft); border:1px solid var(--soft-b); border-radius:8px;
  padding:9px 12px; margin:0 0 8px; }
.callout .k{ font-weight:700; color:var(--accent); text-transform:uppercase;
  letter-spacing:.1em; font-size:7pt; display:block; margin-bottom:3px; }
.callout p:last-child{ margin-bottom:0; }
.callout.gold{ background:#fbf4e6; border-color:#ecd9b0; }
.callout.gold .k{ color:var(--gold); }

.num{ display:flex; gap:8px; margin:0 0 5px; }
.num .i{ font-family:var(--serif); font-weight:600; font-size:12pt; color:var(--accent);
  line-height:1.1; min-width:16px; }
.num .b{ flex:1; }
.num .b h3{ margin:1px 0 1px; }
.num .b p{ font-size:8.5pt; color:#463d33; margin:0; }

table{ width:100%; border-collapse:collapse; margin:0 0 7px; font-size:8.2pt; }
th{ text-align:left; font-weight:700; font-size:7pt; letter-spacing:.09em; text-transform:uppercase;
  color:var(--accent); border-bottom:1.5px solid var(--soft-b); padding:0 6px 3px 0; vertical-align:bottom; }
td{ border-bottom:1px solid var(--border); padding:3px 6px 3px 0; vertical-align:top; line-height:1.28; }
tr:last-child td{ border-bottom:none; }
td.k{ font-weight:700; white-space:nowrap; }
td code{ white-space:normal; overflow-wrap:anywhere; }

ul{ margin:0 0 6px; padding-left:14px; }
ol{ margin:0 0 6px; padding-left:16px; }
li{ margin-bottom:2px; line-height:1.3; }
li::marker{ color:var(--accent); }
ul.tick{ list-style:none; padding-left:0; }
ul.tick li{ padding-left:15px; position:relative; }
ul.tick li:before{ content:'\\2713'; position:absolute; left:0; color:var(--green); font-weight:700; }

.mark{ font-family:var(--serif); font-weight:600; letter-spacing:.4em; color:var(--gold);
  font-size:9pt; text-indent:.4em; }
.rule{ width:46px; height:2px; background:var(--accent); margin:9px 0 12px; }
.byline{ color:var(--muted); font-size:8.6pt; margin-bottom:12px; }
.badge{ display:inline-block; font-size:6.6pt; font-weight:700; letter-spacing:.09em;
  text-transform:uppercase; padding:1px 5px; border-radius:3px; vertical-align:1px;
  background:var(--soft); color:var(--accent); border:1px solid var(--soft-b); }
.badge.g{ background:#e9f2ec; color:var(--green); border-color:#c3ddcd; }
.badge.o{ background:#fbf1de; color:var(--gold); border-color:#ecd9b0; }
.badge.r{ background:#f7e7e3; color:var(--red); border-color:#e6c3ba; }
"""
CSS = (CSS.replace("FRAUNCES", fraunces).replace("HANKENI", hanken_i)
          .replace("HANKEN", hanken))


def page(i, body, title):
    return f"""<div class="page">
  <div class="rh"><span class="t">Per-Quote Indexable URLs &nbsp;·&nbsp; {title}</span><span class="n">{i}</span></div>
  {body}
  <div class="pfoot"><span>Implementation plan · Ochorus · Prepared with Claude</span><span>Page {i} of 2</span></div>
</div>"""


# ---------------------------------------------------------------- page 1 ----
P1 = r"""
<div class="mark">OCHORUS &nbsp;·&nbsp; QUOTES &nbsp;·&nbsp; SEO</div>
<div class="rule"></div>
<h1 class="title">Per-Quote Indexable URLs</h1>
<p class="deck">Giving every sourced quotation its own crawlable page &mdash; the library&rsquo;s single
biggest organic-search lever, and the one most able to backfire if built as thin pages on an unstable slug.</p>
<p class="byline">Against the current stack: SvelteKit&nbsp;5 static-adapter (<code>prerender</code> + <code>entries()</code>)
+ Django/DRF. 267 reviewed quotations across 10 authors today; an ~50-per-author goal ahead.</p>

<div class="callout gold">
  <span class="k">The one decision that gates the build</span>
  <p>The quote <code>slug</code> today is <em>author-slug + a hash of the text</em>. But your text is
  actively repaired &mdash; the <code>english-qa</code> and <code>book-import</code> skills fix OCR slips and
  punctuation. If a URL is minted from the text, <strong>every repair silently changes the URL</strong> and
  throws away that page&rsquo;s ranking equity and every inbound link. Freeze a stable identifier
  <em>before</em> a single URL is exposed. Everything else here is reversible; this is not.</p>
</div>

<div class="sec">
  <h2><span class="kicker">The change</span>What it is</h2>
  <p class="lede">A dedicated, crawlable page per quotation &mdash; <code>/quotes/&lt;author&gt;/&lt;quote&gt;/</code>
  &mdash; instead of quotes living only as <code>&lt;li&gt;</code> rows inside the author page.</p>
  <p>The data model is already 90% ready: <code>Quote</code> has a unique slug, a <code>reviewed</code>
  publication gate, and a resolvable source (chapter/sermon + paragraph). The backend gains a single-quote
  view beside <code>QuotePageView</code>; the frontend gets a <code>[quote]</code> route with
  <code>prerender = true</code> + an <code>entries()</code> generator &mdash; the exact machinery the chapter
  pages already use. ~267 static pages today; low thousands at the 50/author goal, which a static build
  handles easily (books already prerender far more).</p>
</div>

<div class="sec">
  <h2><span class="kicker">SEO understanding</span>Why it matters</h2>
  <div class="num"><div class="i">1</div><div class="b"><h3>It matches how quotes are actually searched</h3>
    <p>The dominant query is the <em>exact string</em>, pasted in. A list row is a weak target; a page with
    its own title, description, canonical and <code>Quotation</code> JSON-LD is a strong one &mdash; ~267 focused
    pages instead of ~11 list pages.</p></div></div>
  <div class="num"><div class="i">2</div><div class="b"><h3>You own the answer nobody else sources</h3>
    <p>Unsourced aggregators rank for these strings now. A page that <em>is</em> the citation (book, chapter,
    paragraph, full-text link) is the E-E-A-T edge &mdash; and the natural citation target for AI answer engines,
    which increasingly quote with attribution.</p></div></div>
  <div class="num"><div class="i">3</div><div class="b"><h3>It anchors every other quote win</h3>
    <p>Per-quote <code>og:image</code>, a real share destination (today &ldquo;Copy&rdquo; points at a book
    paragraph, not a quote page), and Google&rsquo;s quote treatments all need a canonical per-quote URL to attach to.</p></div></div>
  <div class="num"><div class="i">4</div><div class="b"><h3>It densifies the internal-link graph</h3>
    <p>Each page links up to the author&rsquo;s quotes hub, out to the work, and across to the bio &mdash;
    turning a flat list into a cluster that lifts the whole <code>/quotes</code> neighbourhood.</p></div></div>
</div>

<div class="callout">
  <span class="k">Recommended &mdash; a stable, text-independent slug</span>
  <p>Mint the slug <strong>once at creation and store it</strong>; never recompute it from text. Freeze the current
  <code>author-slug + hash</code> value into a column and stop re-deriving it (readable, keyword-bearing), rather
  than switching to an opaque id. The non-negotiable: a text edit must not move the URL. Add a <code>301</code>
  redirect map for any slug that has already shifted, and treat an unpublish (<code>reviewed</code>&nbsp;&rarr;&nbsp;false)
  as a redirect / <code>410</code> to the author page &mdash; not a bare <code>404</code>.</p>
</div>
"""

# ---------------------------------------------------------------- page 2 ----
P2 = r"""
<div class="sec">
  <h2><span class="kicker">Thin-content mitigation</span>The page is a passage, not a one-liner</h2>
  <p class="lede">A page whose body is one sentence is the textbook thin page &mdash; Google crawls it and files it
  under &ldquo;Crawled, currently not indexed.&rdquo; You avoid that because you already resolve the source
  paragraph (the <code>?p=</code> unit). Each page carries:</p>
  <ul class="tick">
    <li>The quote as the hero, with author and the <strong>exact citation</strong> (chapter&nbsp;&para;).</li>
    <li>The <strong>surrounding paragraph</strong> as context (public-domain source), with &ldquo;Read the full chapter&nbsp;&rarr;&rdquo;.</li>
    <li>A short <strong>author card</strong> &mdash; portrait, one line, link to the bio (reuses the Person entity from the last PR).</li>
    <li><strong>3&ndash;6 related quotations</strong> by the same author (internal links).</li>
    <li>Share affordances &mdash; copy-with-attribution (already built) and a quote-card image.</li>
  </ul>
  <p>That converts a one-liner into a genuine, linkable passage page &mdash; the difference between indexed and ignored.</p>
</div>

<div class="cols">
  <div class="sec">
    <h4>Canonicals &mdash; one job per surface</h4>
    <table>
      <tr><th>URL</th><th>Targets</th><th>canonical</th></tr>
      <tr><td class="k"><code>/quotes/&lt;a&gt;/&lt;q&gt;/</code></td><td>the quote (exact string)</td><td>self</td></tr>
      <tr><td class="k"><code>/quotes/&lt;a&gt;/</code></td><td>the collection</td><td>self</td></tr>
      <tr><td class="k"><code>/books/&lt;s&gt;/&lt;n&gt;/</code></td><td>the reading</td><td>self</td></tr>
    </table>
    <p class="why">The same sentence now lives on three of your URLs. Self-canonical each, and frame the author
    page as a <em>collection</em> (the <code>ItemList</code> shipped last PR) so it never competes with the
    individual pages for the exact string.</p>
  </div>
  <div class="sec">
    <h4>Risks &amp; mitigations</h4>
    <table>
      <tr><th>Risk</th><th>Mitigation</th></tr>
      <tr><td class="k">Unstable slug <span class="badge r">gating</span></td><td>Freeze slug at creation; 301 map (p.1).</td></tr>
      <tr><td class="k">Thin content</td><td>Passage layout: paragraph + related + bio.</td></tr>
      <tr><td class="k">Self-competition</td><td>Self-canonicals; author page = collection.</td></tr>
      <tr><td class="k">Unpublish 404s</td><td>Redirect / 410 to author page, not bare 404.</td></tr>
      <tr><td class="k">Near-twin pages</td><td>Unique context paragraph + related set differ.</td></tr>
      <tr><td class="k">Sitemap bloat</td><td>Static prerender scales; watch past ~10k.</td></tr>
    </table>
  </div>
</div>

<div class="sec">
  <h2><span class="kicker">Sequence</span>How to build it &mdash; five waves</h2>
  <div class="num"><div class="i">0</div><div class="b"><h3>Decide &amp; freeze the slug <span class="badge o">gate &mdash; nothing ships before this</span></h3>
    <p>Add the stable-slug column + backfill; write the redirect map. This is the only step expensive to undo.</p></div></div>
  <div class="num"><div class="i">1</div><div class="b"><h3>Backend</h3>
    <p>Single-quote endpoint beside <code>QuotePageView</code> &mdash; quote + resolved source paragraph + neighbouring
    quotes + author blurb. Keep the <code>reviewed</code> gate; return 404 / 410 correctly.</p></div></div>
  <div class="num"><div class="i">2</div><div class="b"><h3>Frontend route</h3>
    <p><code>/quotes/[author]/[quote]/</code> with <code>prerender</code> + <code>entries()</code> from the reviewed set;
    passage layout; <code>Seo.svelte</code> head (self-canonical, <code>Quotation</code> + author <code>Person</code>&nbsp;<code>@id</code>,
    reusing this PR&rsquo;s helpers &mdash; <code>workHref</code> is already extracted); per-quote <code>og:image</code>.</p></div></div>
  <div class="num"><div class="i">3</div><div class="b"><h3>Wire the graph</h3>
    <p>Link each list-page quote to its page; add a &ldquo;Quotes from this book&rdquo; block on book pages; add every
    quote URL to <code>sitemap.ts</code> (English-only, matching the current quote pages).</p></div></div>
  <div class="num"><div class="i">4</div><div class="b"><h3>Validate before scaling</h3>
    <p>Ship <strong>one author</strong> first; confirm indexation in Search Console (Crawled vs Indexed) and
    rich-result validity, then generate the rest. Gates as ever: <code>check</code> + <code>test</code> green,
    <code>verify-local</code>, <code>/simplify</code> + <code>/code-review high</code>, squash-merge on green.</p></div></div>
</div>

<p class="lede" style="margin-top:2px"><strong>If you do one thing first:</strong> freeze the slug. It is the only
step that is expensive to undo &mdash; everything after it can be iterated in the open.</p>
"""

DOC = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
       "<title>Per-Quote Indexable URLs — Implementation Plan</title><style>"
       + CSS + "</style></head><body>"
       + page(1, P1, "The case &amp; the gating decision")
       + page(2, P2, "Design, canonicals, risks &amp; sequence")
       + "</body></html>")

OUT.write_text(DOC, encoding="utf-8")
print(f"wrote {OUT} ({len(DOC)//1024} KB, fonts embedded)")

# Render to PDF (A4, 2 pages):
#   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless \
#     --disable-gpu --no-pdf-header-footer --virtual-time-budget=6000 \
#     --print-to-pdf=perquote-seo.pdf "file://$PWD/perquote-seo.html"
