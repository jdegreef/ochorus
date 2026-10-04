#!/usr/bin/env python3
"""Build "Earning Links": a print-ready A4 brief (4 pages) on earning backlinks
and mentions for Ochorus, idea #1 of the top-ten SEO list. Rendered BLACK AND
WHITE (the palette below is greyscale on purpose — James asked for monochrome
PDFs), with Fraunces + Hanken Grotesk embedded as base64 woff2. Same
self-contained convention as docs/build_seo_ideas_pdf.py.

Fonts come from the frontend's @fontsource-variable packages. Point
OCHORUS_FONTS at another @fontsource-variable directory if frontend/node_modules
is not installed (e.g. `npm pack @fontsource-variable/fraunces
@fontsource-variable/hanken-grotesk` and extract each tarball's `package/` into
<dir>/fraunces and <dir>/hanken-grotesk).

No statistics about Ochorus's own traffic or links are claimed here; the
counts quoted (books, editions, locales) come from the content fixtures."""
import base64
import os
from pathlib import Path

FONTS = Path(os.environ.get(
    "OCHORUS_FONTS",
    Path(__file__).resolve().parents[1] / "frontend/node_modules/@fontsource-variable"))
OUT = Path(__file__).parent / "backlinks-plan.html"


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


fraunces = b64(FONTS / "fraunces/files/fraunces-latin-wght-normal.woff2")
fraunces_i = b64(FONTS / "fraunces/files/fraunces-latin-wght-italic.woff2")
hanken = b64(FONTS / "hanken-grotesk/files/hanken-grotesk-latin-wght-normal.woff2")
hanken_i = b64(FONTS / "hanken-grotesk/files/hanken-grotesk-latin-wght-italic.woff2")

CSS = """
@font-face { font-family:'Fraunces'; src:url(data:font/woff2;base64,FRAUNCESN) format('woff2'); font-weight:100 900; font-display:block; }
@font-face { font-family:'Fraunces'; src:url(data:font/woff2;base64,FRAUNCESI) format('woff2'); font-weight:100 900; font-style:italic; font-display:block; }
@font-face { font-family:'Hanken'; src:url(data:font/woff2;base64,HANKENN) format('woff2'); font-weight:100 900; font-display:block; }
@font-face { font-family:'Hanken'; src:url(data:font/woff2;base64,HANKENI) format('woff2'); font-weight:100 900; font-style:italic; font-display:block; }
/* Greyscale palette: the house tokens, with every hue collapsed to ink and
   paper so the brief prints cleanly on a monochrome printer. */
:root{
  --bg:#ffffff; --text:#111111; --muted:#555555;
  --accent:#111111; --gold:#444444; --border:#c8c8c8; --soft:#f1f1f1; --soft-b:#bdbdbd;
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
.rh .t{ font-weight:700; font-size:7pt; letter-spacing:.14em; text-transform:uppercase; color:var(--gold); }
.rh .n{ font-family:var(--serif); font-size:8.5pt; color:var(--muted); }
.pfoot{ position:absolute; left:15mm; right:15mm; bottom:5mm; display:flex;
  justify-content:space-between; font-size:6.8pt; letter-spacing:.09em;
  text-transform:uppercase; color:#777; border-top:1px solid var(--border); padding-top:4px; }

h1.title{ font-family:var(--serif); font-weight:600; font-size:30pt; line-height:1.02;
  letter-spacing:-.015em; margin:0 0 6px; }
.deck{ font-family:var(--serif); font-style:italic; font-size:11.5pt; color:var(--muted);
  line-height:1.3; margin:0 0 10px; max-width:170mm; }
h2{ font-family:var(--serif); font-weight:600; font-size:14pt; margin:0 0 5px; letter-spacing:-.005em; }
h2 .kicker{ font-family:var(--sans); font-weight:700; font-size:7pt; letter-spacing:.14em;
  text-transform:uppercase; color:var(--accent); display:block; margin-bottom:2px; }
h3{ font-weight:700; font-size:9.4pt; margin:0 0 3px; }
h4{ font-weight:700; font-size:8pt; letter-spacing:.1em; text-transform:uppercase;
  color:var(--accent); margin:0 0 4px; }
p{ margin:0 0 5px; }
.lede{ color:#333; margin:0 0 7px; font-size:9.2pt; }
.sec{ margin-bottom:9px; }
b, strong{ font-weight:700; }
code{ font-family:var(--mono); font-size:7.6pt; background:var(--soft); color:#222;
  border:1px solid var(--soft-b); border-radius:3px; padding:0 3px; white-space:nowrap; }

.cols{ display:flex; gap:7mm; }
.cols > *{ flex:1; min-width:0; }

.callout{ background:var(--soft); border:1px solid var(--soft-b); border-radius:8px;
  padding:9px 12px; margin:0 0 8px; }
.callout .k{ font-weight:700; color:var(--accent); text-transform:uppercase;
  letter-spacing:.1em; font-size:7pt; display:block; margin-bottom:4px; }
.callout p:last-child{ margin-bottom:0; }
.five{ margin:0; padding:0; list-style:none; counter-reset:f; }
.five li{ counter-increment:f; position:relative; padding-left:20px; margin-bottom:5px; font-size:8.6pt; line-height:1.32; }
.five li:before{ content:counter(f); position:absolute; left:0; top:-1px; font-family:var(--serif);
  font-weight:600; font-size:11.5pt; }

/* A playbook channel: number, title + effort badge, then labelled rows. */
.ch{ display:flex; gap:8px; margin:0 0 6.5px; page-break-inside:avoid; }
.ch .i{ font-family:var(--serif); font-weight:600; font-size:12pt; line-height:1.1;
  min-width:18px; text-align:right; }
.ch .b{ flex:1; }
.ch h3{ margin:1px 0 2px; }
.ch .why{ font-size:8.4pt; color:#333; margin:0 0 2px; }
.ch dl{ display:grid; grid-template-columns:15mm 1fr; column-gap:6px; row-gap:1px; margin:0;
  font-size:8.1pt; line-height:1.3; }
.ch dt{ font-weight:700; font-size:6.6pt; letter-spacing:.09em; text-transform:uppercase;
  color:var(--muted); padding-top:1.5px; }
.ch dd{ margin:0; color:#222; }
.group{ font-family:var(--sans); font-weight:700; font-size:7pt; letter-spacing:.14em;
  text-transform:uppercase; border-bottom:1.5px solid var(--soft-b); padding-bottom:2px; margin:4px 0 6px; }

table{ width:100%; border-collapse:collapse; margin:0 0 7px; font-size:8.1pt; }
th{ text-align:left; font-weight:700; font-size:7pt; letter-spacing:.09em; text-transform:uppercase;
  border-bottom:1.5px solid var(--soft-b); padding:0 6px 3px 0; vertical-align:bottom; }
td{ border-bottom:1px solid var(--border); padding:3px 6px 3px 0; vertical-align:top; line-height:1.28; }
tr:last-child td{ border-bottom:none; }
td.k{ font-weight:700; white-space:nowrap; }

ul{ margin:0 0 6px; padding-left:14px; }
li{ margin-bottom:2px; line-height:1.3; }
ul.x{ list-style:none; padding-left:0; }
ul.x li{ padding-left:14px; position:relative; font-size:8.4pt; }
ul.x li:before{ content:'\\2715'; position:absolute; left:0; font-weight:700; font-size:7.5pt; top:1px; }
ul.tick{ list-style:none; padding-left:0; }
ul.tick li{ padding-left:15px; position:relative; }
ul.tick li:before{ content:'\\2713'; position:absolute; left:0; font-weight:700; }

.email{ border:1px solid var(--soft-b); border-left:3px solid #111; padding:6px 10px; margin:0 0 6px;
  font-size:8.2pt; line-height:1.34; background:#fafafa; }
.email .s{ font-weight:700; margin-bottom:3px; }
.email p{ margin:0 0 3px; }
.email p:last-child{ margin:0; }

.mark{ font-family:var(--serif); font-weight:600; letter-spacing:.4em; color:var(--gold);
  font-size:9pt; text-indent:.4em; }
.rule{ width:46px; height:2px; background:var(--accent); margin:9px 0 12px; }
.byline{ color:var(--muted); font-size:8.6pt; margin-bottom:11px; }
.badge{ display:inline-block; font-size:6.4pt; font-weight:700; letter-spacing:.09em;
  text-transform:uppercase; padding:1px 5px; border-radius:3px; vertical-align:1.5px; margin-left:5px;
  background:#fff; color:#111; border:1px solid #111; }
.badge.lo{ background:#111; color:#fff; }
.badge.md{ background:#e2e2e2; color:#111; border-color:#e2e2e2; }
.badge.hi{ background:#fff; color:#111; border-color:#111; }
.legend{ font-size:7.8pt; color:var(--muted); margin:0 0 6px; }
.small{ font-size:8.3pt; color:#333; }
.strip{ gap:5mm; border-top:1.5px solid var(--soft-b); padding-top:5px; }
.strip .small{ font-size:8pt; margin:0; }
"""
CSS = (CSS.replace("FRAUNCESN", fraunces).replace("FRAUNCESI", fraunces_i)
          .replace("HANKENN", hanken).replace("HANKENI", hanken_i))

TOTAL = 4


def page(i, body, title):
    return f"""<div class="page">
  <div class="rh"><span class="t">Earning Links &nbsp;·&nbsp; {title}</span><span class="n">{i}</span></div>
  {body}
  <div class="pfoot"><span>Authority brief · Ochorus · 3 October 2026 · Prepared with Claude</span><span>Page {i} of {TOTAL}</span></div>
</div>"""


EFFORT = {"lo": "quick win", "md": "weekly habit", "hi": "project"}


def ch(n, title, why, who, offer, point, effort):
    """One playbook channel. `effort`: lo = a few hours once, md = a standing
    weekly slot, hi = something to build or a campaign to run."""
    return (f'<div class="ch"><div class="i">{n}</div><div class="b">'
            f'<h3>{title}<span class="badge {effort}">{EFFORT[effort]}</span></h3>'
            f'<p class="why">{why}</p><dl>'
            f'<dt>Target</dt><dd>{who}</dd>'
            f'<dt>Offer / ask</dt><dd>{offer}</dd>'
            f'<dt>Point at</dt><dd>{point}</dd></dl></div></div>')


# ---------------------------------------------------------------- page 1 ----
P1 = r"""
<div class="mark">OCHORUS &nbsp;·&nbsp; SEARCH &nbsp;·&nbsp; AUTHORITY</div>
<div class="rule"></div>
<h1 class="title">Earning Links</h1>
<p class="deck">A backlink and authority plan for Ochorus &mdash; how a free library of public-domain classics earns the
links and mentions that make Google crawl more of it, index more of it, and choose it as the home of each text.</p>
<p class="byline">Idea #1 of the top-ten SEO list. Grounded in the repo: about 185 English books and some 600 book editions
across ten languages, 800+ sermon files, 100 author pages, quote pages, the scripture index, reading plans and the
free PDF/EPUB pilot. No traffic or link numbers for Ochorus are assumed &mdash; the measurement plan on page&nbsp;4 sets the baseline.</p>

<div class="sec">
  <h2><span class="kicker">The diagnosis</span>Why authority is now the bottleneck</h2>
  <div class="cols">
    <div>
      <h3>Crawl budget follows authority</h3>
      <p class="small">The technical work is done: prerendered pages, canonicals, <code>hreflang</code>, per-type and
      per-locale sitemaps, JSON-LD and IndexNow pings. What remains is how much attention Google chooses to spend.
      Its crawl demand scales with how important a site looks, and inbound links from sites it already trusts are the
      strongest outside signal of that.</p>
      <h3>The &ldquo;Discovered &ndash; not indexed&rdquo; pile</h3>
      <p class="small">Search Console shows URLs Google knows about but has not yet fetched. That is the classic symptom
      of a site whose inventory (thousands of chapter, locale and scripture URLs) has outgrown its perceived importance.
      More sitemaps will not move it; more reasons to care will.</p>
    </div>
    <div>
      <h3>Duplicate-canonical competition</h3>
      <p class="small">The English texts also live on CCEL, Project Gutenberg, Wikisource, the Internet Archive and many
      small sites. When Google sees near-identical text it picks one URL to show. Links pointing to a <em>specific</em>
      Ochorus book page are one of the few levers that tilt that choice &mdash; alongside what only Ochorus has: the
      translations, the Modern English and young-reader editions, sourced quotes, and the scripture cross-index.</p>
      <h3>The upside is concentrated</h3>
      <p class="small">A link to a book or author page passes value down through its chapters and across its locale
      siblings via internal links and <code>hreflang</code>. A few dozen good deep links do more than hundreds of
      directory listings to the home page.</p>
    </div>
  </div>
</div>

<div class="cols">
  <div class="sec">
    <h4>What a good link looks like for Ochorus</h4>
    <table>
      <tr><th>Better</th><th>Weaker</th></tr>
      <tr><td><strong>Deep</strong>: to <code>/books/humility-2/</code>, <code>/authors/andrew-murray/</code>, a quote or scripture page</td><td>The home page only</td></tr>
      <tr><td><strong>Topical</strong>: a church, seminary, ministry, Christian writer or library guide</td><td>Generic directories, unrelated blogs</td></tr>
      <tr><td><strong>Language-matched</strong>: a Swahili church site to <code>/sw/&hellip;</code>, a Brazilian blog to <code>/pt/&hellip;</code></td><td>Every locale pointed at the English page</td></tr>
      <tr><td><strong>Editorial</strong>: placed because it helps the reader, in body text or a curated list</td><td>Footers, sidebars, profile fields, widgets</td></tr>
      <tr><td><strong>Lasting</strong>: a reading list, syllabus, resource page or Wikidata statement</td><td>A one-day social post</td></tr>
    </table>
    <p class="legend">Natural anchors are fine (&ldquo;read <em>Humility</em> free online&rdquo;, &ldquo;Ochorus&rdquo;).
    Never ask for exact-match keyword anchors &mdash; that pattern is what spam systems look for.</p>
  </div>
  <div class="sec">
    <div class="callout">
      <span class="k">If you do five things first</span>
      <ol class="five">
        <li><strong>Set the baseline this week.</strong> Export the Search Console Links report and the per-sitemap
        indexing counts, so every later step can be judged (page&nbsp;4).</li>
        <li><strong>Reclaim the easy ones.</strong> Find existing mentions of Ochorus (and the old WordPress URLs) that
        carry no link or a broken one, and ask for a fix (channel&nbsp;12).</li>
        <li><strong>Pitch library and seminary guides.</strong> Ten librarians a week, each offered the two or three
        book pages that fit their guide (channel&nbsp;1).</li>
        <li><strong>Build one linkable asset.</strong> An &ldquo;A&ndash;Z of Christian classics&rdquo; or a
        printable reading-plan pack gives every pitch something better to point at (channel&nbsp;9).</li>
        <li><strong>Start one language partnership.</strong> A Swahili or Luganda church or ministry network in East
        Africa, where the team already has relationships (channel&nbsp;4).</li>
      </ol>
    </div>
    <p class="legend">Effort tags on pages 2&ndash;3: <span class="badge lo">quick win</span> a few hours once &middot;
    <span class="badge md">weekly habit</span> a standing slot &middot; <span class="badge hi">project</span> something
    to build or a campaign to run.</p>
  </div>
</div>

<div class="sec">
  <h4>What only Ochorus can offer a linker</h4>
  <div class="cols strip">
    <div><h3>Ten languages</h3><p class="small">Swahili, Luganda, Amharic, Hindi, Arabic, Ukrainian, Spanish, Portuguese
    and French editions &mdash; the reason a regional church links here rather than to CCEL.</p></div>
    <div><h3>Readable editions</h3><p class="small">Modern English and young-reader (children / teens) editions of
    the same works, cross-linked as one edition family on each book page.</p></div>
    <div><h3>Free downloads</h3><p class="small">Print-ready PDF and EPUB for a growing set of books, with an About the
    Author page &mdash; what librarians and group leaders ask for.</p></div>
    <div><h3>Context pages</h3><p class="small">Author biographies, sourced quote pages, the scripture-by-chapter index,
    reading plans and articles: pages the plain-text archives do not have.</p></div>
  </div>
</div>
"""

# ---------------------------------------------------------------- page 2 ----
P2 = (r"""
<div class="sec">
  <h2><span class="kicker">The playbook &middot; part one</span>Where the links will come from</h2>
  <p class="lede">Twelve channels, grouped by who is on the other end. Each says whom to approach, what to offer, and
  which Ochorus page to send them to. The common thread: offer something that helps <em>their</em> readers, and make the
  page you point at the best version of that text on the web.</p>
  <div class="group">Libraries, schools and reference</div>
"""
+ ch(1, "Seminary, college and church library guides",
     "Academic libraries keep subject guides (often on LibGuides) listing free primary sources; Bible colleges and church "
     "libraries keep reading lists. They link out readily when a resource is free, stable, ad-free and needs no account.",
     "Theological and Bible-college librarians; subject guides on church history, spirituality, Puritans, revival, "
     "missions; church reading-room and discipleship lists.",
     "One short email naming the guide and the two or three works that fit it, plus the free PDF/EPUB where it exists. "
     "Mention the translations for guides serving international students.",
     "Book pages (<code>/books/the-reformed-pastor/</code>, <code>/books/religious-affections/</code>), author pages, "
     "<code>/biographies/era/&hellip;</code> hubs.", "md")
+ ch(2, "Open-access and free-ebook directories",
     "Curated catalogues of free books are where many readers and librarians start. Listings are slow to earn but tend "
     "to last for years.",
     "Open Library and Internet Archive records (where external links are accepted), free-ebook and public-domain lists, "
     "Christian e-book directories, digital-humanities project lists, open-educational-resource repositories.",
     "Submit the downloadable editions individually, with clean metadata (title, author, year, language, licence). Only "
     "where the directory&rsquo;s rules invite it.",
     "Each book page that offers PDF/EPUB; the <code>/books/</code> shelf for directory-level entries.", "md")
+ r"""<div class="group">Ministries, missions and Bible societies</div>"""
+ ch(3, "Legacy organisations tied to specific authors",
     "Many authors on Ochorus have a living institution, society, college, mission or museum that keeps their memory. "
     "Their &ldquo;read his works&rdquo; or &ldquo;resources&rdquo; pages are the most relevant links that exist.",
     "Organisations descended from or devoted to authors such as Charles H. Spurgeon, Andrew Murray, Hudson Taylor, "
     "D.&thinsp;L. Moody, William and Catherine Booth, George M&uuml;ller, Amy Carmichael, Mary Slessor and John Wesley; "
     "historical societies for the Puritans and the church fathers.",
     "Offer Ochorus as a free reading home for the works they mention, especially in languages they cannot serve "
     "themselves. Ask for nothing more than a link where it helps their visitors.",
     "Author pages (<code>/authors/hudson-taylor/</code>), the author&rsquo;s quote page, translated editions.", "md")
+ ch(4, "Mission organisations, Bible societies and churches in each language",
     "The translations are what no competitor has. The natural linkers are bodies that already serve readers in "
     "Swahili, Luganda, Amharic, Hindi, Arabic, Spanish, Portuguese, French and Ukrainian.",
     "National Bible societies; mission agencies and theological colleges in East Africa, Latin America, India, "
     "francophone Africa and Ukraine; denominational networks; diaspora churches; Kampala-area churches the team knows.",
     "A language-specific resource list they can publish (&ldquo;ten free classics in Swahili&rdquo;), a reading plan for "
     "small groups, printable PDFs for areas with poor connectivity. A local partner reviewing a translation is a natural "
     "reason for a credited link (review state stays admin-only).",
     "Locale pages: <code>/sw/books/&hellip;</code>, <code>/lg/authors/&hellip;</code>, <code>/pt/plans/&hellip;</code>, "
     "and the African Voices authors (Crowther, Nsibambi, Kivengere, Luwum).", "hi")
+ r"""<div class="group">Writers, podcasters and newsletters</div>"""
+ ch(5, "Christian bloggers and newsletter writers",
     "People who write about prayer, holiness, revival or church history quote these authors constantly and usually link "
     "to whatever free copy they find first.",
     "Devotional and church-history bloggers, Substack and newsletter writers, pastors who publish sermon notes, "
     "homeschool curriculum writers.",
     "When they quote an author, suggest the exact page with the passage. Offer resources they can embed or reuse: "
     "quote cards, a reading plan, the free PDF/EPUB.",
     "Quote pages (<code>/quotes/e-m-bounds/</code>), chapter pages, <code>/plans/humility-12-days/</code>.", "md")
+ ch(6, "Podcasts and video channels",
     "Show notes are durable, crawlable pages, and hosts need free primary sources to send listeners to.",
     "Church-history, theology and devotional podcasts; YouTube channels that read or discuss the classics.",
     "Point to the free text for the work discussed in an episode; offer a guest conversation on a hook such as an "
     "anniversary (channel&nbsp;11) or on making classics readable in African languages.",
     "The book page for the episode&rsquo;s work; the Modern English edition where one exists.", "md")
+ "</div>")

# ---------------------------------------------------------------- page 3 ----
P3 = (r"""
<div class="sec">
  <h2><span class="kicker">The playbook &middot; part two</span>Communities, assets and campaigns</h2>
  <div class="group">Community and reference</div>
"""
+ ch(7, "Q&amp;A sites and Christian communities",
     "Forum links are mostly <code>nofollow</code>, but they send readers, get Ochorus noticed by writers who do link, "
     "and teach you which questions the library answers. Treat it as service, not distribution.",
     "Reddit (r/Christianity, r/Reformed, r/TrueChristian), Quora, Stack Exchange Christianity and Biblical "
     "Hermeneutics. Read each community&rsquo;s self-promotion rules first; some forbid it outright.",
     "A genuine, complete answer that stands without the link; cite the passage, then link it. Disclose that you run "
     "Ochorus. Most answers should contain no Ochorus link at all.",
     "The specific chapter or quote that answers the question &mdash; never the home page.", "md")
+ ch(8, "Wikipedia and Wikidata, carefully",
     "Done wrongly this burns trust fast. Done properly it is the single most-copied source of external links on the "
     "web.",
     "Wikidata items for works that Ochorus hosts in full; Wikipedia articles only where an external link to the full "
     "text genuinely meets WP:EL and no equivalent link already exists.",
     "On Wikidata, the &ldquo;full work available at URL&rdquo; property (P953) is a legitimate, factual statement for "
     "a hosted work. On Wikipedia, as the site&rsquo;s owner you have a conflict of interest: propose on the article&rsquo;s "
     "talk page and let other editors decide. Never add links in bulk.",
     "Book pages; translated editions on the matching-language Wikipedia, where those exist.", "lo")
+ r"""<div class="group">Linkable assets to build</div>"""
+ ch(9, "Pages people link to on their own",
     "Outreach works far better with something worth linking. Most of these reuse content Ochorus already has.",
     "<strong>An &ldquo;A&ndash;Z of Christian classics&rdquo;</strong> &mdash; every work, author, era and language on "
     "one page. <strong>Author quote collections</strong> grown toward fifty per author. <strong>Scripture-by-book "
     "index</strong> (&ldquo;which classics discuss Romans&nbsp;8&rdquo;). <strong>Modern English and young-reader "
     "editions</strong> &mdash; nothing else like them. <strong>Print-ready PDFs</strong> for groups and prisons.",
     "<strong>Embeddable verse and quote cards</strong> that carry a credit link back to the source page. "
     "<strong>Reading-plan packs</strong> for Lent, Advent and small groups. Each asset should be the answer to a "
     "question a librarian, pastor or blogger already has.",
     "<code>/quotes/&hellip;</code>, <code>/scripture/romans/8/</code>, <code>/plans/&hellip;</code>, "
     "<code>/books/pilgrims-progress-children/</code>, a new A&ndash;Z page.", "hi")
+ ch(10, "Translation and accessibility stories",
     "&ldquo;Andrew Murray&rsquo;s <em>Humility</em>, free in ten languages including Luganda and Amharic&rdquo; is a "
     "story a regional Christian outlet can run; &ldquo;another free classics site&rdquo; is not.",
     "Christian news sites and magazines, regional and diaspora media, mission-agency blogs, ed-tech and digital-"
     "humanities writers.",
     "A short, factual story with a named founder quote and one or two images; offer the locale links directly.",
     "The <code>/sw/</code>, <code>/lg/</code>, <code>/am/</code> versions of a flagship book; the African Voices authors.", "hi")
+ r"""<div class="group">Campaigns and housekeeping</div>"""
+ ch(11, "Anniversary-led digital PR",
     "Dates give journalists and bloggers a reason to write this month. Plan pitches six to eight weeks ahead and verify "
     "every date before sending.",
     "Annual hooks: Reformation Day (31&nbsp;October; Luther and Calvin are on the site), Lent, Advent, birth and death "
     "anniversaries. Larger ones ahead: Andrew Murray&rsquo;s bicentenary (1828&ndash;2028), the 350th of <em>The "
     "Pilgrim&rsquo;s Progress</em> (1678&ndash;2028), the East African Revival&rsquo;s roots around 1929.",
     "A reading plan or collection timed to the date, a short essay from <code>/articles/</code>, quotes for social "
     "cards, and an offer of interviews.",
     "A themed plan, the author page, the anniversary article, and its translated twins.", "hi")
+ ch(12, "Unlinked mentions and broken-link reclamation",
     "The cheapest links are ones already half-given: people who name Ochorus without linking, or link to dead URLs.",
     "Search the web for &ldquo;Ochorus&rdquo; and old WordPress-era URLs; check Search Console for 404 targets with "
     "inbound links; find broken links to defunct free-classics sites on resource pages.",
     "A two-line thank-you with the exact working URL. For dead third-party links, suggest the matching Ochorus page as a "
     "replacement.",
     "Whatever page the mention is about; add 301s for any old URL still drawing links.", "lo")
+ r"""
</div>
<div class="callout">
  <span class="k">The rule behind every channel</span>
  <p>Point people at the <strong>most specific useful page</strong> in <strong>their language</strong>, and make sure that
  page deserves it: a clean title, the author linked, the downloads offered, the edition family visible. A link to a weak
  page wastes the outreach that earned it.</p>
</div>
""")

# ---------------------------------------------------------------- page 4 ----
P4 = r"""
<div class="cols">
  <div class="sec">
    <h2><span class="kicker">Guard rails</span>What not to do</h2>
    <p class="small">Google&rsquo;s spam policies name these as link spam. Any one can undo the rest of this plan.</p>
    <ul class="x">
      <li><strong>Buying or selling links</strong>, including &ldquo;sponsored&rdquo; posts without <code>rel="sponsored"</code>.</li>
      <li><strong>Private blog networks</strong> or sites built only to link to Ochorus.</li>
      <li><strong>Link exchanges at scale</strong> (&ldquo;link to us and we&rsquo;ll link to you&rdquo;).</li>
      <li><strong>Comment, forum and profile spam</strong>; mass directory submissions.</li>
      <li><strong>AI-generated guest posts</strong> placed for the link; scaled low-value content of any kind.</li>
      <li><strong>Keyword-rich anchors</strong> requested from partners, or links hidden in widgets and footers.</li>
    </ul>
    <div class="email">
      <div class="s">Subject: The full text of the [author] passage you quoted</div>
      <p>Hello [name], I enjoyed your piece on [topic]. The [author] passage you quoted is free to read in context here:
      [chapter URL], if a link would help your readers. Thanks for keeping these writers in circulation. &mdash; [name]</p>
    </div>
  </div>
  <div class="sec">
    <h2><span class="kicker">Templates</span>Outreach, short and plain</h2>
    <div class="email">
      <div class="s">Subject: A free resource for your [guide name]</div>
      <p>Hello [name], I found your [guide] and thought this might help your students. Ochorus is a free reader for
      public-domain Christian classics &mdash; no ads, no sign-up. [Work] by [author] is here: [deep URL], with a free PDF
      and EPUB. If it fits your list, I&rsquo;d be glad. Either way, thank you for the guide. &mdash; [name], Ochorus</p>
    </div>
    <div class="email">
      <div class="s">Subject: Free Swahili edition of [work]</div>
      <p>Hello [name], your church serves Swahili readers, so I wanted you to know [work] is now free to read in Swahili:
      [/sw/ URL]. We would welcome your feedback on the translation, and you are welcome to share it.</p>
    </div>
  </div>
</div>

<div class="sec">
  <h2><span class="kicker">Measurement</span>How to know it is working</h2>
  <table>
    <tr><th>Measure</th><th>Where</th><th>Cadence</th><th>What good looks like</th></tr>
    <tr><td class="k">Referring domains</td><td>Search Console &rsaquo; Links (top linking sites); Bing Webmaster Tools backlinks</td><td>Monthly</td><td>Steady growth in relevant domains, not raw link count</td></tr>
    <tr><td class="k">Top linked pages</td><td>Search Console &rsaquo; Links (top linked pages)</td><td>Monthly</td><td>Book and author pages climbing, not only <code>/</code></td></tr>
    <tr><td class="k">Indexed vs submitted</td><td>Page indexing report filtered by each sitemap child</td><td>Monthly</td><td>Rising indexed share per locale and per type</td></tr>
    <tr><td class="k">Discovered &ndash; not indexed</td><td>Page indexing report, &ldquo;Why pages aren&rsquo;t indexed&rdquo;</td><td>Monthly</td><td>The pile shrinking; crawl stats rising</td></tr>
    <tr><td class="k">Canonical wins</td><td>Spot-check 20 book titles in search vs CCEL / Gutenberg</td><td>Quarterly</td><td>Ochorus shown for more of the sample</td></tr>
    <tr><td class="k">Outreach log</td><td>A simple sheet: target, page pitched, date, reply, link live</td><td>Weekly</td><td>Reply and win rates by channel guide the next month</td></tr>
  </table>
  <p class="legend">Links take months to show in indexing: judge on a quarter, and remember releases move the same numbers.</p>
</div>

<div class="sec">
  <h2><span class="kicker">The first quarter</span>A 90-day plan for a founder-led team</h2>
  <table>
    <tr><th style="width:21%">Month</th><th style="width:44%">Focus</th><th>Weekly targets</th></tr>
    <tr><td class="k">1 &middot; Baseline<br>and easy wins</td>
      <td>Record the baseline. Reclaim unlinked mentions and old URLs. Build target lists for library guides, legacy
      organisations and one East African partner network. Add Wikidata P953 statements for hosted works where they fit.</td>
      <td>5 library or legacy emails; 2 genuine community answers; 1 reclamation batch; partner shortlist done by week 4.</td></tr>
    <tr><td class="k">2 &middot; One asset,<br>steady outreach</td>
      <td>Ship one linkable asset (A&ndash;Z of classics or a reading-plan pack). Pitch it to bloggers, newsletters and
      podcasts. First language partnership conversations in Swahili or Luganda.</td>
      <td>10 outreach emails; 3 community answers; 1 directory submission batch; 1 partner call.</td></tr>
    <tr><td class="k">3 &middot; Campaign<br>and review</td>
      <td>Run one anniversary or seasonal campaign (Advent plan, or an early pitch for a 2028 bicentenary). Open a second
      language (Portuguese or Spanish). Review the numbers; drop the weakest channel, double the best.</td>
      <td>10 emails; 3 answers; 1 media pitch; month-end review against the baseline.</td></tr>
  </table>
  <p class="legend">Roughly four to six hours a week. Expect a modest number of strong links in the first quarter; the
  compounding comes from the assets and relationships, not the volume of emails.</p>
</div>

<div class="callout">
  <span class="k">Decisions for the founder</span>
  <p><strong>Who signs outreach</strong> &mdash; a named person earns far more replies than &ldquo;the Ochorus team&rdquo;.
  <strong>Which asset first</strong> &mdash; the A&ndash;Z page is cheapest; reading-plan packs suit churches best.
  <strong>Which second language</strong> &mdash; follow where a real partner relationship exists, not search volume alone.
  <strong>Embeds</strong> &mdash; whether quote cards may be hot-linked by other sites, and with what credit line.
  And a standing rule: <strong>no paid placements</strong>, however they are framed.</p>
</div>
"""

DOC = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
       "<title>Earning Links — Ochorus</title><style>"
       + CSS + "</style></head><body>"
       + page(1, P1, "Why authority now")
       + page(2, P2, "Playbook: who links")
       + page(3, P3, "Playbook: assets and campaigns")
       + page(4, P4, "Guard rails, measurement, 90 days")
       + "</body></html>")

OUT.write_text(DOC, encoding="utf-8")
print(f"wrote {OUT} ({len(DOC)//1024} KB, fonts embedded)")

# Render to PDF (A4, 4 pages, black and white by palette):
#   chrome --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
#     --virtual-time-budget=6000 --print-to-pdf=docs/backlinks-plan.pdf \
#     "file://$PWD/docs/backlinks-plan.html"
