#!/usr/bin/env python3
"""Build "Spreading the Word": a ten-page outreach and backlink playbook for
partners promoting Ochorus (first edition written for Odyssey Technologies,
Uganda). Print-ready A4 in the Ochorus Paper theme, drawn ink-light on purpose:
white paper, no filled panels or solid blocks, colour only in type and hairlines,
so a home or office printer spends almost nothing on it.

Fraunces + Hanken Grotesk are embedded as base64 woff2 and the logo is inlined
from frontend/src/lib/brand. Same self-contained convention as the other
docs/build_*_pdf.py builders; render command at the bottom."""
import base64
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = Path(os.environ.get(
    "OCHORUS_FONTS", ROOT / "frontend/node_modules/@fontsource-variable"))
LOGO = (ROOT / "frontend/src/lib/brand/ochorus-lockup.svg").read_text()
LOGO = LOGO[LOGO.index("<svg"):]
OUT = Path(__file__).parent / "outreach-playbook.html"


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
/* Paper theme tokens (STYLE_GUIDE.md section 1). Ink-light: the indigo and gold
   appear only as type and hairlines, never as filled areas. */
:root{
  --paper:#ffffff; --text:#221c15; --muted:#6e6358; --accent:#3f3d9a;
  --gold:#b07d22; --border:#e8dfcf; --edge:#968462;
  --serif:'Fraunces',Georgia,serif; --sans:'Hanken','Helvetica Neue',Arial,sans-serif;
}
@page { size:A4; margin:0; }
*{ box-sizing:border-box; }
html,body{ margin:0; padding:0; }
body{ font-family:var(--sans); color:var(--text); background:var(--paper);
  font-size:10.8pt; line-height:1.45; -webkit-print-color-adjust:exact; print-color-adjust:exact; }

.page{ width:210mm; height:297mm; padding:14mm 17mm 16mm; position:relative;
  page-break-after:always; overflow:hidden; }
.page:last-child{ page-break-after:auto; }

.rh{ display:flex; justify-content:space-between; align-items:center;
  border-bottom:0.75pt solid var(--gold); padding-bottom:5px; margin-bottom:14px; }
.rh .t{ font-weight:700; font-size:7.2pt; letter-spacing:.16em; text-transform:uppercase; color:var(--gold); }
.rh svg{ height:30px; width:auto; color:var(--accent); display:block; }
.pfoot{ position:absolute; left:17mm; right:17mm; bottom:7mm; display:flex;
  justify-content:space-between; font-size:7pt; letter-spacing:.1em;
  text-transform:uppercase; color:var(--muted); border-top:0.5pt solid var(--border); padding-top:5px; }

h1{ font-family:var(--serif); font-weight:600; font-size:23pt; line-height:1.08;
  letter-spacing:-.01em; margin:0 0 4px; color:var(--text); }
.eyebrow{ font-weight:700; font-size:7.6pt; letter-spacing:.16em; text-transform:uppercase;
  color:var(--gold); margin:0 0 4px; }
.deck{ font-family:var(--serif); font-style:italic; font-size:11.5pt; color:var(--muted);
  line-height:1.35; margin:0 0 14px; }
h2{ font-family:var(--serif); font-weight:600; font-size:13.5pt; color:var(--accent);
  margin:14px 0 6px; line-height:1.2; }
h3{ font-weight:700; font-size:10.2pt; margin:10px 0 4px; }
p{ margin:0 0 7px; }
strong{ font-weight:700; }
em{ font-style:italic; }
a{ color:var(--accent); text-decoration:none; }
.small{ font-size:9.4pt; color:var(--muted); }

.cols{ display:flex; gap:8mm; }
.cols > *{ flex:1; min-width:0; }

/* Numbered steps: outlined numerals, no fill. */
ol.steps{ list-style:none; counter-reset:s; margin:4px 0 8px; padding:0; }
ol.steps > li{ counter-increment:s; position:relative; padding-left:30px; margin:0 0 8px; page-break-inside:avoid; }
ol.steps > li:before{ content:counter(s); position:absolute; left:0; top:-1px; width:20px; height:20px;
  border:1pt solid var(--accent); border-radius:50%; text-align:center; line-height:18px;
  font-family:var(--serif); font-weight:600; font-size:10pt; color:var(--accent); }
ol.steps > li > b:first-child{ display:block; }
ol.plain{ margin:2px 0 8px; padding-left:18px; }
ol.plain li{ margin-bottom:3px; }
ol.plain li::marker{ color:var(--accent); font-weight:700; }
ul{ margin:2px 0 8px; padding-left:16px; }
ul li{ margin-bottom:3px; }
ul li::marker{ color:var(--gold); }
ul.check{ list-style:none; padding-left:0; }
ul.check li{ position:relative; padding-left:20px; }
ul.check li:before{ content:''; position:absolute; left:0; top:3px; width:10px; height:10px;
  border:1pt solid var(--edge); border-radius:2px; }
ul.no{ list-style:none; padding-left:0; }
ul.no li{ position:relative; padding-left:18px; }
ul.no li:before{ content:'\\2715'; position:absolute; left:1px; color:var(--accent); font-weight:700; font-size:9pt; }

/* Callouts: a gold rule on the left, no background. */
.tip{ border-left:2pt solid var(--gold); padding:3px 0 3px 12px; margin:8px 0 10px; }
.tip .k{ display:block; font-weight:700; font-size:7.4pt; letter-spacing:.14em;
  text-transform:uppercase; color:var(--gold); margin-bottom:2px; }
.tip p:last-child{ margin-bottom:0; }
.box{ border:0.75pt solid var(--edge); border-radius:6px; padding:9px 13px; margin:8px 0 10px; }
.box .k{ display:block; font-weight:700; font-size:7.4pt; letter-spacing:.14em;
  text-transform:uppercase; color:var(--accent); margin-bottom:3px; }
.box p:last-child, .box ul:last-child, .box ol:last-child{ margin-bottom:0; }

table{ width:100%; border-collapse:collapse; margin:4px 0 10px; font-size:9.7pt; }
th{ text-align:left; font-weight:700; font-size:7.2pt; letter-spacing:.11em; text-transform:uppercase;
  color:var(--accent); border-bottom:1pt solid var(--edge); padding:0 8px 4px 0; vertical-align:bottom; }
td{ border-bottom:0.5pt solid var(--border); padding:5px 8px 5px 0; vertical-align:top; line-height:1.35; }
tr:last-child td{ border-bottom:none; }
td.k{ font-weight:700; }
td.c{ text-align:center; }

/* Message templates: dashed edge, monospace-free so they paste cleanly. */
.tpl{ border:0.75pt dashed var(--edge); border-radius:6px; padding:9px 13px; margin:6px 0 10px;
  font-size:9.8pt; line-height:1.42; page-break-inside:avoid; }
.tpl .h{ font-weight:700; font-size:7.4pt; letter-spacing:.14em; text-transform:uppercase;
  color:var(--accent); margin-bottom:4px; }
.tpl p{ margin:0 0 5px; }
.fill{ color:var(--accent); font-weight:600; }

/* Cover */
.cover{ display:flex; flex-direction:column; height:100%; }
.cover .logo svg{ height:92px; width:auto; color:var(--accent); display:block; margin:14mm 0 12mm; }
.cover h1{ font-size:36pt; line-height:1.02; margin-bottom:10px; }
.cover .deck{ font-size:13.5pt; max-width:150mm; margin-bottom:16mm; }
.rule{ width:56px; height:0; border-top:1.5pt solid var(--gold); margin:0 0 12px; }
.toc{ width:100%; border-collapse:collapse; font-size:10.5pt; }
.toc td{ padding:6px 0; border-bottom:0.5pt solid var(--border); }
.toc td.n{ width:30px; font-family:var(--serif); font-weight:600; color:var(--accent); }
.toc td.p{ text-align:right; color:var(--muted); font-variant-numeric:tabular-nums; }
.prepared{ margin-top:auto; font-size:9pt; color:var(--muted); border-top:0.5pt solid var(--border); padding-top:8px;
  display:flex; justify-content:space-between; }
.line{ display:inline-block; min-width:52mm; border-bottom:0.5pt solid var(--edge); }
"""
CSS = (CSS.replace("FRAUNCESN", fraunces).replace("FRAUNCESI", fraunces_i)
          .replace("HANKENN", hanken).replace("HANKENI", hanken_i))

TOTAL = 10


def page(i, section, body):
    return f"""<div class="page">
  <div class="rh"><span class="t">{section}</span>{LOGO}</div>
  {body}
  <div class="pfoot"><span>Spreading the Word &middot; An Ochorus outreach playbook</span><span>Page {i} of {TOTAL}</span></div>
</div>"""


# ---------------------------------------------------------------- cover ----
COVER = f"""<div class="page"><div class="cover">
<div class="logo">{LOGO}</div>
<div class="eyebrow">Outreach &amp; backlink playbook &middot; October 2026</div>
<h1>Spreading the Word</h1>
<div class="rule"></div>
<p class="deck">A practical guide to introducing Ochorus to churches, Christian schools,
homeschool families and ministries &mdash; and earning the website links that help
people find it.</p>
<table class="toc">
  <tr><td class="n">1</td><td>Ochorus in one page &mdash; what we are sharing</td><td class="p">2</td></tr>
  <tr><td class="n">2</td><td>Backlinks, explained simply</td><td class="p">3</td></tr>
  <tr><td class="n">3</td><td>The outreach method: seven steps for every contact</td><td class="p">4</td></tr>
  <tr><td class="n">4</td><td>Working with churches</td><td class="p">5</td></tr>
  <tr><td class="n">5</td><td>Christian schools, colleges and seminaries</td><td class="p">6</td></tr>
  <tr><td class="n">6</td><td>Homeschool families and organizations</td><td class="p">7</td></tr>
  <tr><td class="n">7</td><td>More partners and online link sources</td><td class="p">8</td></tr>
  <tr><td class="n">8</td><td>Ready-to-use message templates</td><td class="p">9</td></tr>
  <tr><td class="n">9</td><td>The 90-day plan, reporting and ground rules</td><td class="p">10</td></tr>
</table>
<div class="prepared">
  <span>Prepared for <strong>Odyssey Technologies</strong>, Uganda</span>
  <span>Printer-friendly: prints well in black and white</span>
</div>
</div></div>"""

# ---------------------------------------------------------------- p2 -------
P2 = """
<div class="eyebrow">Section 1</div>
<h1>Ochorus in one page</h1>
<p class="deck">Know what you are offering before you offer it. Everything here is true today and safe to say to anyone.</p>

<div class="box"><span class="k">The 30-second pitch</span>
<p>&ldquo;Ochorus is a free online library of the great Christian classics &mdash; books and sermons by
writers like Charles Spurgeon, Andrew Murray, John Bunyan and Augustine, plus East African Revival voices
such as Festo Kivengere and Janani Luwum. It is free, with no adverts and no sign-up needed, it reads
beautifully on a phone, and many works are available in Luganda, Swahili and other languages.&rdquo;</p></div>

<div class="cols">
<div>
<h2>What is in the library</h2>
<table>
  <tr><th>Item</th><th>Count</th></tr>
  <tr><td>Classic books (English)</td><td>189</td></tr>
  <tr><td>Book editions, all languages</td><td>600+</td></tr>
  <tr><td>Sermons</td><td>800+</td></tr>
  <tr><td>Authors, with life stories</td><td>~100</td></tr>
  <tr><td>Languages</td><td>10</td></tr>
</table>
<p class="small">Languages: English, Luganda, Swahili, Amharic, French, Spanish, Portuguese, Arabic, Hindi and Ukrainian.</p>
</div>
<div>
<h2>Why people say yes</h2>
<ol class="plain">
  <li><strong>Free forever.</strong> No adverts, no fees, no login to read.</li>
  <li><strong>Local languages.</strong> 32 works already in Luganda and 65 in Swahili &mdash; rare anywhere else online.</li>
  <li><strong>Made for phones.</strong> Comfortable to read on any smartphone, even on slow data.</li>
  <li><strong>Young readers.</strong> Children&rsquo;s and teens&rsquo; editions of classics such as <em>The Pilgrim&rsquo;s Progress</em>.</li>
  <li><strong>Ready for groups.</strong> Daily reading plans, topics and sermon study questions.</li>
  <li><strong>Downloads.</strong> Free PDF and EPUB copies of selected books.</li>
</ol>
</div>
</div>

<h2>The pages worth sharing</h2>
<table>
  <tr><th style="width:28%">Page type</th><th style="width:36%">Best for</th><th>How to find the link</th></tr>
  <tr><td class="k">A book</td><td>A school reading list, a sermon series</td><td>Open the book on ochorus.com and copy the address bar</td></tr>
  <tr><td class="k">An author page</td><td>Church heritage pages, history lessons</td><td>Click the author&rsquo;s name on any book</td></tr>
  <tr><td class="k">A reading plan</td><td>Small groups, youth fellowships</td><td>&ldquo;Plans&rdquo; in the site menu</td></tr>
  <tr><td class="k">A topic shelf</td><td>Prayer, revival, holiness, missions</td><td>&ldquo;Topics&rdquo; in the site menu</td></tr>
  <tr><td class="k">A language edition</td><td>Luganda- or Swahili-speaking groups</td><td>Switch the site language, then copy the address</td></tr>
</table>

<div class="tip"><span class="k">Golden rule</span>
<p>Always share the <strong>most specific page</strong> that fits the person &mdash; a book, an author or a plan &mdash;
not just the home page. Specific links help readers more and count for more with search engines.</p></div>
"""

# ---------------------------------------------------------------- p3 -------
P3 = """
<div class="eyebrow">Section 2</div>
<h1>Backlinks, explained simply</h1>
<p class="deck">A backlink is a link to Ochorus from someone else&rsquo;s website. Each good one is a public
recommendation &mdash; and Google listens to recommendations.</p>

<div class="cols">
<div>
<h2>Why they matter</h2>
<ol class="plain">
  <li><strong>Search ranking.</strong> Google treats links from trusted sites as votes of confidence, so
  Ochorus shows up higher when people search for &ldquo;Spurgeon sermons&rdquo; or &ldquo;Christian books in Luganda&rdquo;.</li>
  <li><strong>Direct visitors.</strong> People click the link and start reading today.</li>
  <li><strong>Trust.</strong> A link from a church or a college tells readers the library is safe and sound.</li>
</ol>
</div>
<div>
<h2>What makes a link valuable</h2>
<ol class="plain">
  <li><strong>Relevance</strong> &mdash; a Christian site, a school or a library.</li>
  <li><strong>Trust</strong> &mdash; an established organization, a real website people visit.</li>
  <li><strong>Placement</strong> &mdash; inside a resource list or article, not hidden in a footer.</li>
  <li><strong>Words</strong> &mdash; clear link text such as &ldquo;free Christian classics in Luganda&rdquo;.</li>
</ol>
</div>
</div>

<h2>Good links and bad links</h2>
<table>
  <tr><th style="width:50%">Good &mdash; please pursue</th><th>Bad &mdash; never pursue</th></tr>
  <tr><td>A church&rsquo;s &ldquo;Resources&rdquo; or &ldquo;Recommended reading&rdquo; page</td><td>Paying anyone to place a link</td></tr>
  <tr><td>A college or seminary library guide</td><td>&ldquo;Link exchange&rdquo; deals: we link you, you link us</td></tr>
  <tr><td>A homeschool curriculum blog or co-op website</td><td>Comment spam on blogs and forums</td></tr>
  <tr><td>A news story or blog post about Ochorus</td><td>Link directories that accept anyone for a fee</td></tr>
  <tr><td>A ministry&rsquo;s training-materials page</td><td>Sites about gambling, adult content or loans</td></tr>
  <tr><td>A real Christian resource directory</td><td>Many links from one site&rsquo;s every page (footers, sidebars)</td></tr>
</table>

<h2>Four words you will hear</h2>
<table>
  <tr><th style="width:24%">Word</th><th>What it means for you</th></tr>
  <tr><td class="k">Anchor text</td><td>The clickable words. Suggest natural ones: &ldquo;Ochorus free Christian library&rdquo; or the book&rsquo;s title. Vary them.</td></tr>
  <tr><td class="k">Referring domain</td><td>A website that links to us. Ten links from ten churches beat ten links from one church.</td></tr>
  <tr><td class="k">Deep link</td><td>A link to a specific page (a book or author), not the home page. Our favourite kind.</td></tr>
  <tr><td class="k">Nofollow</td><td>A link that passes less search value (Wikipedia and social media). Still worth having for visitors.</td></tr>
</table>

<div class="tip"><span class="k">Checking a link went live</span>
<p>Open the partner&rsquo;s page, press <strong>Ctrl+F</strong> (or &ldquo;Find on page&rdquo; on a phone),
search for &ldquo;ochorus&rdquo;, click the link to confirm it opens the right page, and record the address in the tracker.</p></div>
"""

# ---------------------------------------------------------------- p4 -------
P4 = """
<div class="eyebrow">Section 3</div>
<h1>The outreach method</h1>
<p class="deck">Use these seven steps for every church, school or website. They turn cold contacts into partners
and keep our reputation clean.</p>

<ol class="steps">
  <li><b>Find the prospect.</b> Look for organizations whose readers would love Ochorus: churches, schools,
  homeschool groups, ministries, Christian bloggers. Use Google, Facebook, denominational directories and your own network.</li>
  <li><b>Check the fit.</b> Is the website active (updated in the last two years)? Does it already link to
  resources or books? Is it clearly Christian, educational or family-focused? If not, skip it.</li>
  <li><b>Find the right person.</b> The pastor, communications officer, librarian, head teacher or blog author &mdash;
  a named person, not &ldquo;info@&rdquo;. A warm introduction through someone you know is best of all.</li>
  <li><b>Find the gap.</b> What would Ochorus add for <em>them</em>? A Luganda edition for their members, a free
  copy of a book on their syllabus, a reading plan for their youth group, a working link to replace a broken one.</li>
  <li><b>Make the ask &mdash; short and personal.</b> Under 120 words. Use their name, mention their page, name one
  specific Ochorus page, and suggest exactly where it could go. Templates are on page 9.</li>
  <li><b>Follow up once.</b> If there is no reply after 7 days, send one polite reminder. After that, let it go
  and move on &mdash; never pester.</li>
  <li><b>Record everything.</b> Log each contact in the shared tracker the same day, including &ldquo;no&rdquo;
  answers. When a link goes live, check it and record its address.</li>
</ol>

<h2>The shared tracker</h2>
<p>Keep one spreadsheet (Google Sheets works well) with these columns:</p>
<table>
  <tr><th>Column</th><th>Example</th></tr>
  <tr><td class="k">Organization &amp; type</td><td>St. Andrew&rsquo;s Church &middot; Church</td></tr>
  <tr><td class="k">Website page</td><td>The page where our link should go</td></tr>
  <tr><td class="k">Contact person &amp; channel</td><td>Rev. A. Name &middot; email / WhatsApp / visit</td></tr>
  <tr><td class="k">Ochorus page offered</td><td>The Luganda edition of <em>Humility</em></td></tr>
  <tr><td class="k">Date contacted &middot; follow-up date</td><td>6 Oct &middot; 13 Oct</td></tr>
  <tr><td class="k">Status</td><td>To contact &middot; Contacted &middot; Replied &middot; Link live &middot; Declined</td></tr>
  <tr><td class="k">Link address (when live)</td><td>The exact page that now links to Ochorus</td></tr>
</table>

<div class="tip"><span class="k">Remember</span>
<p>We are offering a gift, not asking a favour. Lead with what helps <em>their</em> people; the link follows naturally.</p></div>
"""

# ---------------------------------------------------------------- p5 -------
P5 = """
<div class="eyebrow">Section 4</div>
<h1>Working with churches</h1>
<p class="deck">Churches are our most natural partners: they want their members reading good books, and
Ochorus gives them a free library in their own language.</p>

<div class="box"><span class="k">A story that opens doors in Uganda</span>
<p>Ochorus carries the East African Revival &mdash; Simeon Nsibambi, Festo Kivengere, Janani Luwum, William
Nagenda and others &mdash; alongside the classics. For Anglican and evangelical congregations this is <em>their own</em>
heritage, freely available. Lead with it.</p></div>

<h2>How to approach a church</h2>
<ol class="steps">
  <li><b>Start with a person you know.</b> A member, a youth leader or a choir member can introduce you to the
  pastor or the communications team. Introductions work far better than cold emails.</li>
  <li><b>Meet or call, then follow with a message.</b> Show Ochorus on your phone in two minutes: open a Luganda
  or Swahili book, a reading plan, and an author&rsquo;s life story.</li>
  <li><b>Offer three ways to use it</b> (see the list below), and let them choose.</li>
  <li><b>Ask for the website link.</b> &ldquo;Would you add Ochorus to your website&rsquo;s resources page so
  members can find it?&rdquo; Offer the exact wording (page 9).</li>
  <li><b>Thank them and stay in touch.</b> Send a new reading plan or a seasonal book every few months.</li>
</ol>

<div class="cols">
<div>
<h2>Ways a church can use Ochorus</h2>
<ul>
  <li>A <strong>&ldquo;Resources&rdquo; page link</strong> on the church website</li>
  <li>A <strong>reading plan</strong> for small groups or a fasting season</li>
  <li>A <strong>&ldquo;book of the month&rdquo;</strong> announced from the pulpit</li>
  <li>A <strong>QR code</strong> in the bulletin or on a notice board</li>
  <li>Links shared in the church&rsquo;s <strong>WhatsApp</strong> groups and Facebook page</li>
  <li>Sermon study questions for <strong>Bible study</strong> leaders</li>
</ul>
</div>
<div>
<h2>Who to approach</h2>
<ul>
  <li><strong>Large city churches</strong> with active websites</li>
  <li><strong>Diocese and denominational offices</strong> &mdash; one link can reach many parishes</li>
  <li><strong>Churches with founders</strong> on Ochorus: Methodist (Wesley), Baptist (Spurgeon), Salvation Army (the Booths)</li>
  <li><strong>Youth and campus fellowships</strong></li>
  <li><strong>Women&rsquo;s and men&rsquo;s ministries</strong></li>
</ul>
</div>
</div>

<div class="tip"><span class="k">Tip</span>
<p>Many church websites have no resources page yet. Offer to help: a short paragraph about Ochorus plus a link
is often welcome &mdash; and Odyssey&rsquo;s web skills can make that easy for them.</p></div>
"""

# ---------------------------------------------------------------- p6 -------
P6 = """
<div class="eyebrow">Section 5</div>
<h1>Christian schools, colleges and seminaries</h1>
<p class="deck">Links from schools and universities (.ac.ug, .edu and similar) are among the most trusted on the
internet. Teachers and librarians link to anything that saves their students money.</p>

<div class="cols">
<div>
<h2>Who to approach</h2>
<ul>
  <li><strong>University and seminary librarians</strong> &mdash; they keep online lists of free study resources</li>
  <li><strong>Lecturers</strong> in church history, theology, missions and Christian ministry</li>
  <li><strong>Bible colleges</strong> and pastors&rsquo; training schools</li>
  <li><strong>Christian secondary schools</strong> &mdash; chaplains and Christian Religious Education teachers</li>
  <li><strong>Christian student unions</strong> on campus</li>
</ul>
</div>
<div>
<h2>What to offer them</h2>
<ul>
  <li><strong>Free primary sources:</strong> Augustine, Athanasius, Luther, Calvin, Wesley and more, readable on a phone</li>
  <li><strong>Reading lists</strong> by subject: early church, Reformation, revival, missions, African Christianity</li>
  <li><strong>African voices:</strong> Samuel Ajayi Crowther and the East African Revival</li>
  <li><strong>Downloads</strong> students can keep for offline study</li>
</ul>
</div>
</div>

<h2>Step by step</h2>
<ol class="steps">
  <li><b>Find the library&rsquo;s online resource pages.</b> Search: <em>&ldquo;[college name] library e-resources&rdquo;</em>
  or <em>&ldquo;[college name] theology free resources&rdquo;</em>. Note pages that already list free websites.</li>
  <li><b>Find the course outlines.</b> Which classic texts appear on theology or history reading lists? Check that Ochorus has them.</li>
  <li><b>Write to the librarian or lecturer by name.</b> Say which course or page it helps, and include direct links to the exact books.</li>
  <li><b>Offer a short demo</b> for staff or students &mdash; 15 minutes in a library session or a chapel announcement.</li>
  <li><b>Ask for a place on the resources page</b> and the course reading list. Thank them, then check and record the link.</li>
</ol>

<div class="box"><span class="k">Timing matters</span>
<p>Reading lists are written <strong>before each term or semester begins</strong>. Contact lecturers and
librarians 4&ndash;6 weeks before the term starts, when they are choosing materials.</p></div>

<div class="tip"><span class="k">Tip</span>
<p>Ask international contacts too. Seminaries in Kenya, Tanzania, Nigeria, the UK and the USA keep the same
kind of library guides. One well-placed email to a librarian can earn a link that other libraries copy.</p></div>
"""

# ---------------------------------------------------------------- p7 -------
P7 = """
<div class="eyebrow">Section 6</div>
<h1>Homeschool families and organizations</h1>
<p class="deck">Christian homeschoolers love the classics and are always looking for free, wholesome books.
They also blog and share generously &mdash; which makes them excellent sources of links.</p>

<h2>What makes Ochorus a good fit</h2>
<ol class="plain">
  <li><strong>Classic literature for every age.</strong> Children&rsquo;s and teens&rsquo; editions of works
  like <em>The Pilgrim&rsquo;s Progress</em>, plus the full originals for older students.</li>
  <li><strong>Free and ad-free</strong> &mdash; safe for children to use.</li>
  <li><strong>Life stories</strong> of missionaries and preachers for history and character lessons.</li>
  <li><strong>Daily reading plans</strong> that fit a school-day rhythm.</li>
</ol>

<h2>Who to approach</h2>
<table>
  <tr><th style="width:32%">Group</th><th style="width:34%">Where to find them</th><th>What to ask for</th></tr>
  <tr><td class="k">Homeschool associations &amp; co-ops</td><td>National association websites, Facebook groups</td><td>A spot on their &ldquo;free resources&rdquo; page or newsletter</td></tr>
  <tr><td class="k">Curriculum bloggers</td><td>Search: &ldquo;Christian homeschool free books&rdquo;, &ldquo;classical education reading list&rdquo;</td><td>A mention in a reading-list post</td></tr>
  <tr><td class="k">Charlotte Mason &amp; classical communities</td><td>Blogs, forums and podcasts on &ldquo;living books&rdquo;</td><td>A link beside the classics they recommend</td></tr>
  <tr><td class="k">Christian parenting sites</td><td>Family ministries and magazines</td><td>A short guest article on reading the classics with children</td></tr>
  <tr><td class="k">Local families</td><td>Churches, school networks, WhatsApp groups</td><td>Share it and tell friends; feedback for us</td></tr>
</table>

<h2>Step by step</h2>
<ol class="steps">
  <li><b>Search for existing &ldquo;free books&rdquo; lists</b> on homeschool sites (search strings above). These pages exist to link out.</li>
  <li><b>Read the list first.</b> Note which books they recommend that Ochorus offers free, or in another language.</li>
  <li><b>Write a friendly note</b> naming their list and one or two specific Ochorus books that would fit it.</li>
  <li><b>Offer something extra.</b> A short guest post such as <em>&ldquo;Five Christian classics to read aloud with your children.&rdquo;</em>
  A guest post with a link is often easier to say yes to than a bare link.</li>
</ol>

<div class="tip"><span class="k">Tip</span>
<p>Homeschool audiences are worldwide and mostly in English. Pitch the children&rsquo;s editions and missionary
biographies first &mdash; they are the easiest &ldquo;yes&rdquo;.</p></div>
"""

# ---------------------------------------------------------------- p8 -------
P8 = """
<div class="eyebrow">Section 7</div>
<h1>More partners and online link sources</h1>
<p class="deck">Beyond churches and schools, these partners and methods each bring links, readers or both.</p>

<table>
  <tr><th style="width:27%">Partner</th><th style="width:38%">Why they care</th><th>What to ask for</th></tr>
  <tr><td class="k">Mission agencies &amp; ministries</td><td>Need training material in local languages</td><td>A link on their resources or training page</td></tr>
  <tr><td class="k">Christian radio &amp; TV</td><td>Need content and listener resources</td><td>An on-air mention; a link on the station website</td></tr>
  <tr><td class="k">Christian bloggers &amp; podcasters</td><td>Always need something useful to share</td><td>A review, a mention, or a guest post</td></tr>
  <tr><td class="k">Christian bookshops</td><td>Customers who cannot afford every book</td><td>A poster or QR code; a link on their site</td></tr>
  <tr><td class="k">Tech &amp; startup media</td><td>A Ugandan team supporting a free reading app is a good story</td><td>A short feature or interview</td></tr>
</table>

<h2>Three online methods</h2>
<h3>1. Fix broken links (our highest success rate)</h3>
<ol class="plain">
  <li>Find old Christian websites that have shut down (pages now showing &ldquo;Page not found&rdquo;).</li>
  <li>Use a backlink checker tool to list the pages that still link to them.</li>
  <li>Where we host the same book, write: &ldquo;Your link to [book] is broken &mdash; here is a free working copy.&rdquo;</li>
</ol>
<p class="small">This works because we are fixing a real problem for the website owner. Expect a much higher reply rate than ordinary outreach.</p>

<h3>2. Resource pages</h3>
<p>Search Google for pages that list free Christian books, for example
<em>&ldquo;free Christian classics online&rdquo;</em>, <em>&ldquo;Spurgeon sermons free&rdquo;</em> or
<em>&ldquo;vitabu vya Kikristo bure&rdquo;</em>. Point out what is missing from their list &mdash; usually a language
or a book they do not have &mdash; and offer our page.</p>

<h3>3. Directories and app listings</h3>
<p>Submit Ochorus to genuine, human-curated Christian resource directories and app review sites. Use the same
short description each time. Skip any directory that charges for a listing.</p>

<div class="box"><span class="k">Wikipedia: please leave this to us</span>
<p>Wikipedia has strict rules about people promoting their own websites, and breaking them can get Ochorus
blocked. Please <strong>do not add Ochorus links to Wikipedia</strong>. If you spot a Wikipedia article where
Ochorus would genuinely help, note it in the tracker and we will handle it.</p></div>
"""

# ---------------------------------------------------------------- p9 -------
P9 = """
<div class="eyebrow">Section 8</div>
<h1>Ready-to-use message templates</h1>
<p class="deck">Replace every <span class="fill">[bracketed]</span> part. Keep it short, personal and specific &mdash;
never send the same message unchanged to many people.</p>

<div class="tpl"><div class="h">A &middot; Church (email or WhatsApp)</div>
<p>Dear <span class="fill">[Pastor name]</span>,</p>
<p>I&rsquo;m <span class="fill">[your name]</span> from Odyssey Technologies. We&rsquo;re helping share Ochorus, a free online library of
Christian classics with no adverts or sign-up &mdash; including <span class="fill">[the East African Revival voices / books in Luganda]</span>.</p>
<p>I thought your members might enjoy <span class="fill">[book or reading plan + link]</span>. Would you consider adding Ochorus to
<span class="fill">[your website&rsquo;s resources page]</span>? I&rsquo;m happy to send a short description to paste in.</p>
<p>Blessings, <span class="fill">[name, phone]</span></p></div>

<div class="tpl"><div class="h">B &middot; Librarian or lecturer</div>
<p>Dear <span class="fill">[Name]</span>, I noticed your <span class="fill">[library guide / course page]</span> lists free study resources.
Ochorus offers free, phone-friendly editions of <span class="fill">[Augustine&rsquo;s Confessions, etc. + links]</span>, no login needed.
Would it be useful to add it to that page for your students? Thank you for your work, <span class="fill">[name]</span>.</p></div>

<div class="tpl"><div class="h">C &middot; Homeschool blogger or association</div>
<p>Hi <span class="fill">[Name]</span>, I enjoyed your post <span class="fill">[post title]</span>. You might like Ochorus: free, ad-free
Christian classics, including children&rsquo;s editions of <span class="fill">[book + link]</span>. It could fit nicely in your list
of <span class="fill">[topic]</span>. I&rsquo;d also be glad to write a short guest post if that helps. Thank you! <span class="fill">[name]</span></p></div>

<div class="tpl"><div class="h">D &middot; Broken link</div>
<p>Hello <span class="fill">[Name]</span>, on your page <span class="fill">[page address]</span>, the link to
<span class="fill">[book title]</span> no longer works. There&rsquo;s a free, ad-free copy here: <span class="fill">[Ochorus link]</span>, in case you&rsquo;d like to update it.
Kind regards, <span class="fill">[name]</span></p></div>

<div class="tpl"><div class="h">E &middot; Description they can paste on their website</div>
<p><strong>Ochorus &mdash; free Christian classics.</strong> Read hundreds of classic Christian books and sermons by
Spurgeon, Murray, Bunyan, Augustine and East African Revival leaders, free and without adverts, in English, Luganda,
Swahili and more. <span class="fill">[link: https://ochorus.com]</span></p></div>

<div class="tpl"><div class="h">F &middot; One polite follow-up (after 7 days)</div>
<p>Hi <span class="fill">[Name]</span>, just a gentle follow-up on my note about Ochorus. No pressure at all &mdash; if it would help your
<span class="fill">[members / students / readers]</span>, I&rsquo;m happy to send anything you need. Thank you, <span class="fill">[name]</span></p></div>
"""

# ---------------------------------------------------------------- p10 ------
P10 = """
<div class="eyebrow">Section 9</div>
<h1>The 90-day plan, reporting and ground rules</h1>
<p class="deck">A steady weekly rhythm beats a big burst. Aim for quality: one link from a real church beats ten from nowhere.</p>

<table>
  <tr><th style="width:20%">Weeks</th><th style="width:44%">Focus</th><th>Goal by the end</th></tr>
  <tr><td class="k">1&ndash;2</td><td>Set up the tracker; build a list of 100 prospects; learn the site; directory listings</td><td>100 prospects listed; 10 listings submitted</td></tr>
  <tr><td class="k">3&ndash;6</td><td>Churches and Ugandan schools; broken-link and resource-page outreach begins</td><td>60 contacts made; first 15 links live</td></tr>
  <tr><td class="k">7&ndash;10</td><td>Seminaries abroad, homeschool groups, bloggers, radio; follow-ups</td><td>150 contacts total; 40 links live</td></tr>
  <tr><td class="k">11&ndash;13</td><td>Double down on whatever is working best; thank partners</td><td>60+ links live; a short lessons-learned report</td></tr>
</table>

<div class="cols">
<div>
<h2>Weekly rhythm</h2>
<ol class="plain">
  <li><strong>Monday</strong> &mdash; find 20 new prospects</li>
  <li><strong>Tue&ndash;Thu</strong> &mdash; send 15&ndash;20 personal messages; make 2&ndash;3 visits or calls</li>
  <li><strong>Friday</strong> &mdash; follow-ups, check live links, update the tracker, send the weekly report</li>
</ol>
<h2>Weekly report (5 lines)</h2>
<ul class="check">
  <li>Contacts made this week</li>
  <li>Replies received</li>
  <li>New links live (with addresses)</li>
  <li>Best conversation or lesson</li>
  <li>Help needed from Ochorus</li>
</ul>
</div>
<div>
<h2>Ground rules</h2>
<ul class="no">
  <li>Never pay for a link or accept payment for one</li>
  <li>No link swaps, spam comments or mass emails</li>
  <li>Do not add links to Wikipedia &mdash; flag them to us</li>
  <li>Never promise features Ochorus does not have</li>
  <li>Do not describe how books were translated; just share the book</li>
  <li>Be honest that you are helping Ochorus</li>
  <li>Respect a &ldquo;no&rdquo; &mdash; one follow-up only</li>
</ul>
</div>
</div>

<div class="box"><span class="k">Contacts</span>
<p>Ochorus contact: <span class="line">&nbsp;</span> &nbsp; Email / WhatsApp: <span class="line">&nbsp;</span></p>
<p>Odyssey lead: <span class="line">&nbsp;</span> &nbsp; Shared tracker link: <span class="line">&nbsp;</span></p></div>

<p class="small" style="margin-top:8px">Thank you for helping more people discover these books. Every link is a doorway for someone to read
words that have strengthened believers for centuries.</p>
"""

DOC = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
       "<title>Spreading the Word — Ochorus outreach playbook</title><style>"
       + CSS + "</style></head><body>"
       + COVER
       + page(2, "Ochorus in one page", P2)
       + page(3, "Backlinks explained", P3)
       + page(4, "The outreach method", P4)
       + page(5, "Churches", P5)
       + page(6, "Schools, colleges &amp; seminaries", P6)
       + page(7, "Homeschool", P7)
       + page(8, "More partners", P8)
       + page(9, "Message templates", P9)
       + page(10, "Plan &amp; ground rules", P10)
       + "</body></html>")

OUT.write_text(DOC, encoding="utf-8")
print(f"wrote {OUT} ({len(DOC)//1024} KB, fonts embedded)")

# Render to PDF (A4, 10 pages):
#   chrome --headless=new --disable-gpu --no-pdf-header-footer \
#     --virtual-time-budget=6000 --print-to-pdf=outreach-playbook.pdf \
#     "file://$PWD/outreach-playbook.html"
