#!/usr/bin/env python3
"""Build "Forty SEO Ideas": a print-ready A4 brief in the Ochorus paper theme,
rendered BLACK AND WHITE (the palette below is greyscale on purpose — James
asked for a monochrome PDF), with Fraunces + Hanken Grotesk embedded as base64
woff2. Render to PDF with headless Chrome (see render command at bottom).

Evidence is from the 2026-09-04 audit of the live site: curl probes of ~60
URLs, the sitemap children, Lighthouse 12 (mobile) on /, /books/ and a chapter,
and the English content fixtures. Same self-contained convention as the other
docs/build_*_pdf.py builders."""
import base64
from pathlib import Path

FONTS = Path.home() / "dev/ochorus/frontend/node_modules/@fontsource-variable"
OUT = Path(__file__).parent / "seo-ideas.html"


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


fraunces = b64(FONTS / "fraunces/files/fraunces-latin-wght-normal.woff2")
hanken = b64(FONTS / "hanken-grotesk/files/hanken-grotesk-latin-wght-normal.woff2")
hanken_i = b64(FONTS / "hanken-grotesk/files/hanken-grotesk-latin-wght-italic.woff2")

CSS = """
@font-face { font-family:'Fraunces'; src:url(data:font/woff2;base64,FRAUNCES) format('woff2'); font-weight:100 900; font-display:block; }
@font-face { font-family:'Hanken'; src:url(data:font/woff2;base64,HANKEN) format('woff2'); font-weight:100 900; font-display:block; }
@font-face { font-family:'Hanken'; src:url(data:font/woff2;base64,HANKENI) format('woff2'); font-weight:100 900; font-style:italic; font-display:block; }
/* Greyscale palette: the house tokens, with every hue collapsed to ink and
   paper so the brief prints cleanly on a monochrome printer. */
:root{
  --bg:#ffffff; --surface:#ffffff; --surface-2:#f3f3f3; --text:#111111; --muted:#555555;
  --accent:#111111; --gold:#444444; --border:#c8c8c8; --soft:#f1f1f1; --soft-b:#bdbdbd;
  --green:#222222; --red:#111111;
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
  text-transform:uppercase; color:#777; border-top:1px solid var(--border); padding-top:4px; }

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
.lede{ color:#333; margin:0 0 8px; font-size:9.4pt; }
.sec{ margin-bottom:9px; }
b, strong{ font-weight:700; }
em{ font-style:italic; }
code{ font-family:var(--mono); font-size:8pt; background:var(--soft); color:#222;
  border:1px solid var(--soft-b); border-radius:3px; padding:0 3px; white-space:nowrap; }
a{ color:var(--accent); text-decoration:none; }

.cols{ display:flex; gap:7mm; }
.cols > *{ flex:1; min-width:0; }

.callout{ background:var(--soft); border:1px solid var(--soft-b); border-radius:8px;
  padding:9px 12px; margin:0 0 8px; }
.callout .k{ font-weight:700; color:var(--accent); text-transform:uppercase;
  letter-spacing:.1em; font-size:7pt; display:block; margin-bottom:3px; }
.callout p:last-child{ margin-bottom:0; }

.num{ display:flex; gap:8px; margin:0 0 4.5px; page-break-inside:avoid; }
.num .i{ font-family:var(--serif); font-weight:600; font-size:12pt; color:var(--accent);
  line-height:1.1; min-width:20px; text-align:right; }
.num .b{ flex:1; }
.num .b h3{ margin:1px 0 1px; }
.num .b p{ font-size:8.4pt; color:#333; margin:0; }
.num .b p.ev{ color:var(--muted); font-size:7.9pt; margin-top:1px; }

table{ width:100%; border-collapse:collapse; margin:0 0 7px; font-size:8.2pt; }
th{ text-align:left; font-weight:700; font-size:7pt; letter-spacing:.09em; text-transform:uppercase;
  color:var(--accent); border-bottom:1.5px solid var(--soft-b); padding:0 6px 3px 0; vertical-align:bottom; }
td{ border-bottom:1px solid var(--border); padding:3px 6px 3px 0; vertical-align:top; line-height:1.28; }
tr:last-child td{ border-bottom:none; }
td.k{ font-weight:700; white-space:nowrap; }
td.r{ text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; }

ul{ margin:0 0 6px; padding-left:14px; }
li{ margin-bottom:2px; line-height:1.3; }
ul.tick{ list-style:none; padding-left:0; }
ul.tick li{ padding-left:15px; position:relative; }
ul.tick li:before{ content:'\\2713'; position:absolute; left:0; color:var(--green); font-weight:700; }

.mark{ font-family:var(--serif); font-weight:600; letter-spacing:.4em; color:var(--gold);
  font-size:9pt; text-indent:.4em; }
.rule{ width:46px; height:2px; background:var(--accent); margin:9px 0 12px; }
.byline{ color:var(--muted); font-size:8.6pt; margin-bottom:12px; }
.badge{ display:inline-block; font-size:6.4pt; font-weight:700; letter-spacing:.09em;
  text-transform:uppercase; padding:1px 5px; border-radius:3px; vertical-align:2px; margin-left:4px;
  background:#fff; color:#111; border:1px solid #111; }
.badge.lo{ background:#111; color:#fff; }
.badge.md{ background:#e2e2e2; color:#111; border-color:#e2e2e2; }
.badge.hi{ background:#fff; color:#111; border-color:#111; }
.legend{ font-size:7.6pt; color:var(--muted); margin:0 0 6px; }
"""
CSS = (CSS.replace("FRAUNCES", fraunces).replace("HANKENI", hanken_i)
          .replace("HANKEN", hanken))

TOTAL = 5


def page(i, body, title):
    return f"""<div class="page">
  <div class="rh"><span class="t">Forty SEO Ideas &nbsp;·&nbsp; {title}</span><span class="n">{i}</span></div>
  {body}
  <div class="pfoot"><span>SEO brief · Ochorus · Audit of 4 September 2026 · Prepared with Claude</span><span>Page {i} of {TOTAL}</span></div>
</div>"""


def idea(n, title, body, ev="", effort="md"):
    """One numbered idea. `effort` is the build cost: lo = an afternoon,
    md = a PR, hi = a project. Impact is carried by the ordering."""
    label = {"lo": "small", "md": "a PR", "hi": "project"}[effort]
    ev_html = f'<p class="ev">Seen: {ev}</p>' if ev else ""
    return (f'<div class="num"><div class="i">{n}</div><div class="b">'
            f'<h3>{title}<span class="badge {effort}">{label}</span></h3>'
            f'<p>{body}</p>{ev_html}</div></div>')


# ---------------------------------------------------------------- page 1 ----
P1 = r"""
<div class="mark">OCHORUS &nbsp;·&nbsp; SEARCH &nbsp;·&nbsp; AUDIT</div>
<div class="rule"></div>
<h1 class="title">Forty SEO Ideas</h1>
<p class="deck">What a review of the live site found on 4&nbsp;September&nbsp;2026, and forty things
that would help more readers find the library &mdash; ordered by impact within each group.</p>
<p class="byline">Method: curl probes of about sixty live URLs and every sitemap child; Lighthouse&nbsp;12 (mobile)
on the home page, <code>/books/</code> and a chapter; the head markup of each page type; and the English
content fixtures for counts. Google&rsquo;s PageSpeed API was quota-blocked, so the vitals below are lab numbers.</p>

<div class="sec">
  <h2><span class="kicker">Where the site stands</span>What is already strong</h2>
  <ul class="tick">
    <li>Every public route is <strong>prerendered</strong> with a self-referential canonical, per-locale <code>hreflang</code>
        with <code>x-default</code>, Open Graph tags and JSON-LD (Book, Chapter, Person, Quotation, BreadcrumbList, ItemList).</li>
    <li>The sitemap is an <strong>index over per-type and per-locale children</strong>, so Search Console can answer
        &ldquo;is Swahili indexing?&rdquo;; robots.txt buries the old WordPress URLs; www and http redirect cleanly.</li>
    <li>Time to first byte is <strong>30&nbsp;ms</strong> behind Cloudflare with Brotli; localized titles are written for
        the query (&ldquo;Humildad de Andrew Murray &mdash; lectura gratuita en l&iacute;nea&rdquo;).</li>
    <li>Author bios are genuinely translated (the Ukrainian and Hindi author pages are 2,000+ words in-script), so the
        all-locale author <code>hreflang</code> is honest.</li>
  </ul>
</div>

<div class="cols">
  <div class="sec">
    <h4>Measurements that drive the list</h4>
    <table>
      <tr><th>Signal</th><th class="r">Value</th></tr>
      <tr><td>No-slash detail URL (<code>/books/humility-2</code>)</td><td class="r">200, 5,764&nbsp;B shell</td></tr>
      <tr><td>Unknown path (<code>/nonexistent-page</code>)</td><td class="r">200, same shell</td></tr>
      <tr><td>Chapter URLs in sitemaps with <code>lastmod</code></td><td class="r">0 of 1,878</td></tr>
      <tr><td>Non-English works that are <code>ai_unreviewed</code></td><td class="r">220 of 220</td></tr>
      <tr><td>Book descriptions over 300 characters</td><td class="r">86 of 100</td></tr>
      <tr><td>English books with a publication year</td><td class="r">6 of 100</td></tr>
      <tr><td>Chapter titles with mid-title &ldquo;Of&rdquo;, &ldquo;The&rdquo;&hellip;</td><td class="r">237</td></tr>
      <tr><td>Chapter page links to the author page</td><td class="r">0</td></tr>
      <tr><td><code>/books/</code> HTML size (inline SVG covers)</td><td class="r">570&nbsp;KB (337&nbsp;KB)</td></tr>
      <tr><td>Mobile LCP: home / books / chapter</td><td class="r">6.2 / 5.6 / 4.3&nbsp;s</td></tr>
      <tr><td>Lighthouse SEO: home / books / chapter</td><td class="r">92 / 92 / 83</td></tr>
    </table>
  </div>
  <div class="sec">
    <h4>How to read the list</h4>
    <p class="legend">Each idea carries a build-cost tag: <span class="badge lo">small</span> an afternoon,
    <span class="badge md">a PR</span> one focused pull request, <span class="badge hi">project</span> several PRs
    or ongoing editorial work. Within each group the first items matter most.</p>
    <div class="callout">
      <span class="k">If you do five things first</span>
      <p><strong>1</strong> Redirect the no-slash detail URLs and return real 404s (ideas 1&ndash;2) &mdash; the shell
      is indexed as a duplicate of every book, chapter and author today.<br>
      <strong>2</strong> Turn scripture references into real links (idea 21) &mdash; the largest internal-linking win
      available, for 1,184 pages that currently have one inbound link each.<br>
      <strong>3</strong> Author in chapter titles and short meta descriptions (ideas 12, 14).<br>
      <strong>4</strong> Fix mobile LCP on text pages (idea 34).<br>
      <strong>5</strong> Decide the policy for unreviewed AI editions (idea 8) before the locale count grows again.</p>
    </div>
    <p class="legend">Groups: crawl and indexing (1&ndash;11) &middot; titles, snippets and structured data (12&ndash;20)
    &middot; internal linking and content (21&ndash;33) &middot; performance and Core Web Vitals (34&ndash;40).</p>
  </div>
</div>
"""

# ---------------------------------------------------------------- page 2 ----
P2 = (r"""
<div class="sec">
  <h2><span class="kicker">Group one</span>Crawl and indexing hygiene</h2>
  <p class="lede">The site&rsquo;s biggest leaks are not missing tags but URLs that answer when they should not, and
  dates that say nothing. Every item here is deterministic and testable from a shell.</p>
"""
+ idea(1, "Redirect no-slash detail URLs to the slash form",
       "<code>/books/humility-2</code>, <code>/books/humility-2/1</code> and <code>/authors/andrew-murray</code> all "
       "return 200 with the empty SPA shell: no title, no body, a duplicate of every real page. A 301 at the host or "
       "Cloudflare layer gives each page one indexable address.",
       "curl of the three URLs; 5,764-byte response, identical for every slug.", "lo")
+ idea(2, "Return a real 404",
       "Unknown paths also serve the shell with 200, so Google files them as soft 404s and keeps recrawling. Ship a "
       "<code>404.html</code> with a 404 status; as a safety net give the fallback shell a title and "
       "<code>&lt;meta name=\"robots\" content=\"noindex\"&gt;</code>.",
       "<code>/nonexistent-page</code> and <code>/books/nonexistent-book/</code> both 200.", "lo")
+ idea(3, "Fix the robots.txt error",
       "<code>Feed:</code> is not a directive; Lighthouse marks the file invalid on every page. Move the line into a "
       "comment and keep <code>Sitemap:</code>.",
       "Lighthouse <em>robots-txt</em> audit, &ldquo;Unknown directive&rdquo;.", "lo")
+ idea(4, "noindex the client-only pages",
       "<code>/search</code> is neither disallowed nor noindexed, and disallowed pages (<code>/login</code>, "
       "<code>/settings</code>, <code>/notebook</code>) can still be indexed from links. A robots meta on each closes the gap.",
       "<code>/search/</code> has a title and no robots meta.", "lo")
+ idea(5, "One trailing-slash policy for list pages",
       "<code>/books</code> and <code>/books/</code> both serve identical HTML and the canonical says <code>/books</code>, "
       "while detail pages canonicalize to the slash form. Redirect one form to the other so equity does not split.",
       "Both return 570,048 bytes; canonical differs from the detail convention.", "lo")
+ idea(6, "Add lastmod to the chapter, author, scripture and quote sitemaps",
       "Only books and sermons carry it. Chapter text is re-baked often (the rebuild markers in the route files "
       "record why), so real dates let Google recrawl what changed instead of sampling nearly two thousand URLs blindly.",
       "0 of 1,878 English chapter URLs have <code>lastmod</code>; 198 of 198 book URLs do.", "md")
+ idea(7, "Real dates in feed.xml",
       "Every entry&rsquo;s <code>published</code> and <code>updated</code> is the build timestamp, so each deploy "
       "announces the whole library as new. Use the row&rsquo;s creation date.",
       "All entries stamped 2026-09-04T12:53, the last build.", "lo")
+ idea(8, "Decide how to handle unreviewed AI editions",
       "Every non-English work is <code>ai_unreviewed</code>, and all are advertised through hreflang and sitemaps. "
       "Google&rsquo;s scaled-content policy makes that a risk. Either prioritize native review for Spanish and "
       "Portuguese, or gate a locale&rsquo;s sitemap on a reviewed share.",
       "220 of 220 translated books and sermons; about 1,900 localized chapter URLs.", "hi")
+ idea(9, "Register with Bing Webmaster Tools and IndexNow",
       "Cloudflare can push IndexNow pings on deploy. Bing and Yandex share is higher for the Ukrainian and Hindi "
       "audiences than for English.",
       "no IndexNow key or Bing verification present.", "lo")
+ idea(10, "A post-deploy SEO gate",
       "The prerender race that bakes the empty shell has struck at least six times per the rebuild markers. A deploy "
       "step that fetches a sample of sitemap URLs and fails if any is the 5,764-byte shell catches it before Google does.",
       "six &ldquo;Rebuild marker&rdquo; comments in <code>books/[slug]/+page.ts</code>.", "md")
+ idea(11, "Search Console coverage in the admin",
       "The sitemap was split per locale for exactly this question. Pulling per-sitemap indexed-versus-submitted counts "
       "through the Search Console API into the existing coverage tab makes it a weekly glance.",
       "", "md")
+ "</div>")

# ---------------------------------------------------------------- page 3 ----
P3 = (r"""
<div class="sec">
  <h2><span class="kicker">Group two</span>Titles, snippets and structured data</h2>
  <p class="lede">The head markup is complete but not yet written for the searcher: chapter titles omit the author,
  descriptions are book blurbs, and the structured data leaves out the dates and language that make a Book entity whole.</p>
"""
+ idea(12, "Put the author in chapter titles",
       "Today: &ldquo;The Glory Of The Creature &mdash; Humility &mdash; Ochorus&rdquo;. People search "
       "&ldquo;andrew murray humility chapter 1&rdquo;, so &ldquo;&hellip; &mdash; Humility by Andrew Murray&rdquo; "
       "earns the query for 1,878 pages at once.",
       "chapter <code>&lt;title&gt;</code> on the live page.", "lo")
+ idea(13, "Fix title-casing glitches in chapter titles",
       "Small words are capitalized mid-title: &ldquo;Importance Of Prayer&rdquo;, &ldquo;The Love Of Jesus&mdash;what "
       "It Is&rdquo;. They show in SERPs, breadcrumbs and JSON-LD.",
       "237 English chapter titles match the pattern.", "md")
+ idea(14, "Dedicated meta descriptions for books",
       "Most English descriptions run past 300 characters and end in a &ldquo;Contents:&rdquo; list, so Google "
       "truncates them mid-sentence. Add a short summary field, or cut at the first sentence boundary under 155 characters.",
       "86 of 100 over 300 characters; none under 160.", "md")
+ idea(15, "A site-wide default og:image",
       "The home page and every chapter page have none, so shares of the site&rsquo;s most-linked pages render as bare "
       "text cards. A branded fallback in <code>Seo.svelte</code> covers every route that has nothing better.",
       "no <code>og:image</code> on <code>/</code> or on chapter pages.", "lo")
+ idea(16, "Proper 1200&times;630 social cards for books and authors",
       "Book pages use the 443&times;668 cover JPEG and authors use the portrait, both the wrong shape. Sermons already "
       "have <code>/og/sermons/&lt;slug&gt;.png</code> twins; generate the same for books and authors.",
       "<code>/covers/humility-2.jpg</code> is 443&times;668.", "md")
+ idea(17, "Enrich the Book JSON-LD",
       "Add <code>datePublished</code>, <code>inLanguage</code>, <code>isAccessibleForFree</code>, a "
       "<code>hasPart</code> chapter list and <code>workTranslation</code> links between editions. The year has to "
       "be backfilled first.",
       "6 of 100 English books carry a <code>publication_year</code>.", "md")
+ idea(18, "Enrich the Chapter JSON-LD",
       "Add <code>wordCount</code>, <code>datePublished</code>, the author at chapter level and <code>publisher</code>, "
       "so the book-to-chapter graph is explicit rather than inferred.",
       "Chapter carries name, position, isPartOf, inLanguage only.", "lo")
+ idea(19, "Organization and editorial-policy signals",
       "Expand the Organization JSON-LD with founders, the Victoria and Kampala addresses and social <code>sameAs</code>; "
       "add a footer-linked page on how texts are sourced and how translations are reviewed. This is the trust story "
       "for a site that republishes public-domain text.",
       "About page names both cities; no policy page exists.", "md")
+ idea(20, "Transliterated author names per locale",
       "Hindi and Arabic titles mix scripts (&ldquo;Andrew Murray &#2342;&#2381;&#2357;&#2366;&#2352;&#2366;&rdquo;), "
       "but Hindi searchers type the name in Devanagari. A per-language author name field fixes titles, headings and "
       "Person markup together.",
       "<code>/hi/books/humility-2/</code> title.", "md")
+ "</div>")

# ---------------------------------------------------------------- page 4 ----
P4 = (r"""
<div class="sec">
  <h2><span class="kicker">Group three</span>Internal linking and content</h2>
  <p class="lede">Chapters are 81% of the site&rsquo;s URLs and each one is a dead end: it links to its book and the
  next chapter, nothing else. Fixing the link graph is worth more than any new page type.</p>
"""
+ idea(21, "Make scripture references real links",
       "Chapter bodies wrap verses in <code>&lt;a class=\"scripture-ref\"&gt;</code> with no href, which Lighthouse "
       "flags as uncrawlable. Pointing them at <code>/scripture/&lt;book&gt;/&lt;chapter&gt;/</code> gives the scripture "
       "pages thousands of contextual inbound links; keep the popover on click.",
       "Lighthouse <em>crawlable-anchors</em>; 1,184 scripture URLs reachable only from the hub.", "md")
+ idea(22, "Author and related-work links on chapter pages",
       "A short &ldquo;About the author&rdquo; block with a link to the bio, plus &ldquo;More by&rdquo; and topic chips, "
       "densifies the graph for the largest page type.",
       "0 links to <code>/authors/</code> or other books on the sampled chapter.", "md")
+ idea(23, "Deepen book pages",
       "The main content is about 450 words. Add an author-bio excerpt, a first-chapter teaser, the publication year and "
       "a &ldquo;Readers also read&rdquo; shelf by topic.",
       "454 words inside <code>&lt;main&gt;</code> on <code>/books/humility-2/</code>.", "md")
+ idea(24, "Chapter-by-chapter summaries on book pages",
       "&ldquo;&lt;book&gt; summary&rdquo; is a large query class that the description&rsquo;s &ldquo;Contents:&rdquo; "
       "list half-serves. A structured synopsis section targets it properly.", "", "hi")
+ idea(25, "Ship the per-quote indexable URLs plan",
       "The plan in <code>docs/perquote-seo.html</code> is written; each sourced quotation is a query in its own right "
       "and the pages anchor the quote-card and share features.",
       "12 authors have quote pages today.", "hi")
+ idea(26, "Grow quote pages toward fifty per author",
       "&ldquo;&lt;author&gt; quotes&rdquo; is among the highest-volume patterns for these names; the "
       "quote-extraction playbook already encodes the method.", "", "hi")
+ idea(27, "Scale the Articles section",
       "Five articles exist and they are the only pages answering question-shaped queries. Two a month, each funnelling "
       "into books and sermons, compounds.",
       "5 URLs under <code>/articles/</code> in the pages sitemap.", "hi")
+ idea(28, "Expand topics from ten to thirty or forty",
       "Faith, holiness, revival, suffering, assurance and the like each deserve a hub with a 300-word editorial "
       "introduction, not only a shelf.",
       "10 topics in the ItemList on <code>/topics/</code>.", "hi")
+ idea(29, "More hub facets for biographies",
       "Era landings exist; add country, tradition and century hubs (African authors first, per the African-voices "
       "push) as crawlable entry points to the 89 author pages.", "", "md")
+ idea(30, "Prev and next on scripture pages",
       "<code>/scripture/john/3/</code> is unique content but reachable only from the hub. Chapter-to-chapter links "
       "and a short introduction on high-demand chapters (Psalm 23, John 3, Romans 8) would help.", "", "md")
+ idea(31, "Section headings inside chapters",
       "The sampled chapter has no H2 in its body; only the footer has them. The import already added headings to 175 "
       "chapters, so extending that pass helps both readers and passage ranking.", "", "md")
+ idea(32, "Free PDF and EPUB downloads",
       "Book rows carry a <code>pdf_url</code>; &ldquo;&lt;title&gt; pdf&rdquo; is a strong intent. Offer the download "
       "on the book page with a canonical header pointing back at the HTML edition.", "", "md")
+ idea(33, "Link-earning outreach for the unique assets",
       "The scripture index (&ldquo;which classics treat John 3&rdquo;) and the sourced quotes have no equivalent "
       "elsewhere. Pitch them to Bible-study bloggers, seminary libraries and the external-links sections of author "
       "Wikipedia articles.", "", "hi")
+ "</div>")

# ---------------------------------------------------------------- page 5 ----
P5 = (r"""
<div class="sec">
  <h2><span class="kicker">Group four</span>Performance and Core Web Vitals</h2>
  <p class="lede">The server answers in 30&nbsp;ms and the page still takes four to six seconds to paint its largest
  text on a phone. The wait is fonts, a stack of render-blocking stylesheets and oversized images.</p>
"""
+ idea(34, "Cut LCP on text pages",
       "The LCP element is a paragraph, so the delay is web fonts plus six or more render-blocking CSS files. Inline the "
       "critical CSS, merge the per-component stylesheets, and confirm <code>font-display: swap</code> or "
       "<code>optional</code>.",
       "LCP 6.2&nbsp;s home, 4.3&nbsp;s chapter; FCP 3.1&ndash;3.5&nbsp;s with 30&nbsp;ms TTFB.", "md")
+ idea(35, "Shrink the /books page",
       "The HTML carries 86 inline cover SVGs and 2,232 DOM nodes. Serve generated covers as <code>&lt;img&gt;</code> "
       "files (some already are) and paginate or lazy-render the shelf.",
       "570&nbsp;KB HTML, 337&nbsp;KB of it SVG; Lighthouse <em>dom-size</em> at 0.5.", "md")
+ idea(36, "Responsive portraits",
       "Home serves 45&ndash;75&nbsp;KB JPEGs for 44-pixel avatars. Generate thumbnail sizes with <code>srcset</code>, "
       "as the cover pipeline already does for WebP.",
       "Lighthouse <em>uses-responsive-images</em>: 434&nbsp;KB wasted on <code>/</code>.", "md")
+ idea(37, "Longer browser cache on images",
       "Covers and portraits ship <code>max-age=0</code>, so every repeat visit revalidates each image. A day or more "
       "is safe for files that only change with a deploy.",
       "<code>cache-control: public, max-age=0, s-maxage=300</code> on <code>/covers/</code>.", "lo")
+ idea(38, "Preconnect to api.ochorus.com",
       "Add the preconnect and make sure the client-side personal blocks never delay first paint on prerendered pages.",
       "Lighthouse <em>uses-rel-preconnect</em>: about 180&nbsp;ms.", "lo")
+ idea(39, "Trim JavaScript on chapter pages",
       "Two chunks waste about 120&nbsp;KB per page. Splitting the reader&rsquo;s text-to-speech, marks and offline "
       "features out of the shared bundle lowers the cost of the largest page type.",
       "<em>unused-javascript</em>: 119&nbsp;KB on the chapter, 236&nbsp;KB on home.", "md")
+ idea(40, "Investigate the same-URL redirect Lighthouse reports",
       "On <code>/</code> and <code>/books/</code> Lighthouse charges six to seven seconds to a navigation to the same "
       "URL. It looks like a service-worker or hydration re-navigation; if real users hit it, it is the single largest "
       "vitals fix available.",
       "<em>redirects</em> audit: 7,240&nbsp;ms on <code>/</code>, 6,190&nbsp;ms on <code>/books/</code>.", "md")
+ r"""
</div>
<div class="sec">
  <h2><span class="kicker">Sequence</span>A sensible order</h2>
  <table>
    <tr><th>Wave</th><th>Ideas</th><th>Why this order</th></tr>
    <tr><td class="k">1 &middot; Stop the leaks</td><td>1, 2, 3, 4, 5, 7, 15, 37, 38</td><td>All small; each removes a defect Google can see today.</td></tr>
    <tr><td class="k">2 &middot; Write for the query</td><td>12, 13, 14, 17, 18</td><td>Title, snippet and entity changes across every page in one prerender.</td></tr>
    <tr><td class="k">3 &middot; Wire the graph</td><td>21, 22, 6, 10, 30</td><td>Internal links plus dated sitemaps and a deploy gate that keeps them honest.</td></tr>
    <tr><td class="k">4 &middot; Paint faster</td><td>34, 35, 36, 39, 40</td><td>Vitals work; measure with Lighthouse before and after each PR.</td></tr>
    <tr><td class="k">5 &middot; Grow</td><td>8, 23&ndash;29, 31&ndash;33, 9, 11, 16, 19, 20</td><td>Editorial and policy work that compounds once the plumbing is sound.</td></tr>
  </table>
</div>
"""
)

DOC = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
       "<title>Forty SEO Ideas — Ochorus</title><style>"
       + CSS + "</style></head><body>"
       + page(1, P1, "What was found")
       + page(2, P2, "Crawl and indexing")
       + page(3, P3, "Titles, snippets and structured data")
       + page(4, P4, "Internal linking and content")
       + page(5, P5, "Performance and sequence")
       + "</body></html>")

OUT.write_text(DOC, encoding="utf-8")
print(f"wrote {OUT} ({len(DOC)//1024} KB, fonts embedded)")

# Render to PDF (A4, 5 pages, black and white by palette):
#   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
#     --disable-gpu --no-pdf-header-footer --virtual-time-budget=6000 \
#     --print-to-pdf=seo-ideas.pdf "file://$PWD/seo-ideas.html"
