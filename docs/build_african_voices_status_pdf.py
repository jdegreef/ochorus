#!/usr/bin/env python3
"""Build "African Voices on Ochorus — Progress Report" — a print-ready 7–10 page
status & recommendations PDF documenting the initiative to grow Ochorus's African
authorship within its public-domain constraint. Emits a self-contained HTML file
(Fraunces + EB Garamond embedded as base64 woff2, earthy manuscript palette, @page
print CSS) which is then rendered to PDF with headless Chrome. Shares the house
method of docs/build_african_voices_pdf.py and docs/build_perquote_seo_pdf.py."""
import base64
import html
from pathlib import Path

FONTS = Path.home() / "dev/ochorus/frontend/node_modules/@fontsource-variable"
OUT = Path(__file__).parent / "african-voices-status.html"


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


fraunces_n = b64(FONTS / "fraunces/files/fraunces-latin-wght-normal.woff2")
fraunces_i = b64(FONTS / "fraunces/files/fraunces-latin-wght-italic.woff2")
garamond_n = b64(FONTS / "eb-garamond/files/eb-garamond-latin-wght-normal.woff2")
garamond_i = b64(FONTS / "eb-garamond/files/eb-garamond-latin-wght-italic.woff2")


def esc(s):
    return html.escape(s)


# --- content model -----------------------------------------------------------

# Shipped books built/merged in this push.
SHIPPED = [
    dict(
        title="Samuel Ajayi Crowther",
        work="Journal of an Expedition up the Niger (1855)",
        meta="5 chapters · PR #1333 · full cover",
        flag="First sub-Saharan African book",
        paras=[
            "Ochorus's <b>first sub-Saharan African book.</b> Crowther was freed "
            "from a slave ship as a boy and became the first African Anglican "
            "bishop; his 1855 expedition journal is clear first-person English.",
            "The one cost was the source: importing it meant repairing "
            "<b>~350 OCR errors</b> in the 1855 scan by hand.",
        ],
    ),
    dict(
        title="Jarena Lee",
        work="Religious Experience and Journal (1849)",
        meta="8 chapters · PR #1359 · cover + ~1,500-word biography + verified PD portrait",
        flag=None,
        paras=[
            "The first woman authorized to preach in the AME Church, and the "
            "first African American woman to publish an autobiography. Converted "
            "under Richard Allen, who is already live on the site.",
        ],
    ),
    dict(
        title="Julia A. J. Foote",
        work="A Brand Plucked from the Fire (1879)",
        meta="30 chapters · PR #1377 · cover + ~1,500-word biography + verified PD portrait",
        flag=None,
        paras=[
            "The first woman ordained a deacon in the AME Zion Church. With Lee "
            "and the already-live Amanda Berry Smith, the <b>early Black women "
            "preachers cluster</b> is now well represented.",
        ],
    ),
]

# Already live from parallel work — context, not built in this push.
PARALLEL = [
    ("Amanda Berry Smith", "An Autobiography", "41 chapters"),
    ("Richard Allen", "The Life, Experience, and Gospel Labours", "11 chapters"),
]

# The current African library — authors with works, then bio-only.
WITH_WORKS = [
    ("Andrew Murray", "South Africa", "11"),
    ("Athanasius of Alexandria", "Egypt", "2"),
    ("Augustine of Hippo", "North Africa", "2"),
    ("Samuel Ajayi Crowther", "Nigeria", "1"),
    ("Richard Allen", "African-American", "1"),
    ("Amanda Berry Smith", "African-American", "1"),
    ("Jarena Lee", "African-American", "1"),
    ("Julia A. J. Foote", "African-American", "1"),
    ("Hannah Buyinza", "Uganda", "1"),
]

BIO_ONLY = [
    "Cyprian of Carthage",
    "Lemuel Haynes",
    "Festo Kivengere",
    "Simeon Nsibambi",
    "Erica Sabiti",
]

# Recommendations. status ∈ {inprog, todo, copy}. Each has a pill + rationale.
RECS = [
    dict(
        n="01", status="inprog", statuslabel="In progress",
        title="Finish or defer Zilpha Elaw",
        who="Memoirs (1846) · the last of the three Black women preachers",
        paras=[
            "Completing the trio would give the diaspora a chorus, but this is the "
            "hardest of the four. The only public-domain source is a single "
            "<b>badly OCR'd Internet Archive scan</b> (systematic damage like "
            "&ldquo;tliis&rdquo;&rarr;this, plus whole garbage lines), and the "
            "memoir is a <b>continuous narrative with no chapter divisions</b> — "
            "it needs editorial chapter-splitting on top of Crowther-level repair.",
            "Assessment is complete; the decision to push through now is pending. "
            "<b>Recommended:</b> decide explicitly, given the cost.",
        ],
    ),
    dict(
        n="02", status="todo", statuslabel="Recommended",
        title="North African church fathers, via CCEL",
        who="The single biggest African gap · a clean source",
        paras=[
            "CCEL carries clean transcriptions, so these import fast. "
            "<b>Cyprian of Carthage</b> already has a bio but no works — start "
            "with <i>On the Lord's Prayer.</i> Then <b>Tertullian</b> "
            "(<i>On Prayer</i>, <i>To the Martyrs</i>), <b>Perpetua</b> "
            "(<i>The Passion of Perpetua and Felicity</i> — the earliest "
            "surviving writing by a Christian woman), <b>Clement of "
            "Alexandria</b>, <b>Origen</b> (<i>On Prayer</i>), and "
            "<b>Macarius of Egypt.</b>",
            "Watch the translation-copyright gate: use pre-1929 translators.",
        ],
    ),
    dict(
        n="03", status="todo", statuslabel="Recommended",
        title="Lemuel Haynes' sermons",
        who="Would be Ochorus's first African-authored sermons",
        paras=[
            "Haynes has a bio but no works, and Ochorus has <b>zero sermons by "
            "any African author, in any language.</b> His preaching is compact "
            "and quotable — start with his famous <i>Universal Salvation.</i>",
        ],
    ),
    dict(
        n="04", status="copy", statuslabel="Bio-only",
        title="East African Revival honour bios",
        who="Pure writing — no import",
        paras=[
            "Deepen <b>Kivengere, Nsibambi, Sabiti</b>, and add <b>Apolo "
            "Kivebulaya</b>, <b>Tiyo Soga</b>, and <b>Bernard Mizeki.</b> Their "
            "own writings remain in copyright, so these can only ever be bio "
            "pages — say so plainly on each.",
        ],
    ),
    dict(
        n="05", status="todo", statuslabel="Recommended",
        title="More works for the Africans already here",
        who="The import machinery and audience already exist",
        paras=[
            "Crowther's episcopal <i>Charges</i> and <i>Experiences with "
            "Heathens and Mohammedans in West Africa</i>; more Augustine "
            "(<i>On Christian Doctrine</i>, <i>Homilies on the First Epistle of "
            "John</i>); and Athanasius' <i>Festal Letters.</i>",
        ],
    ),
    dict(
        n="06", status="todo", statuslabel="Recommended",
        title="Multiply reach",
        who="Translation, quotes, collection & reading plan",
        paras=[
            "Translate African-authored works into <b>Swahili and Luganda</b> "
            "(already-live languages) via the translate-book pipeline, and grow "
            "each author's quote page.",
            "Build an <b>African Voices</b> collection page and a reading plan — "
            "<i>From Carthage to Kampala</i> — threading Perpetua &rarr; Cyprian "
            "&rarr; Augustine &rarr; Crowther &rarr; the Revival.",
        ],
    ),
]

# Lessons & constraints — closing section.
LESSONS = [
    ("Public-domain gate",
     "Modern figures — the Revival generation — can be honoured with bio pages "
     "only; their books won't be public domain for decades."),
    ("Source cleanliness is everything",
     "CCEL, Gutenberg and DocSouth are clean transcriptions (an import is about "
     "an hour); Internet Archive OCR is hours of hand-repair per book (Crowther "
     "~350 fixes; Elaw comparable). Always prefer a clean source; when only OCR "
     "exists, budget for it."),
    ("Survey before building",
     "The library moves fast — parallel sessions shipped Allen and Smith. Always "
     "check the catalog, authors.json and fixtures first; a near-duplicate of "
     "Allen was caught this way."),
    ("New author + book needs no migration",
     "The seed creates them together. A bio-only new author, however, does need "
     "a migration."),
]


# --- rendering ---------------------------------------------------------------

def status_pill(status, label):
    return f'<span class="pill {status}">{esc(label)}</span>'


def shipped_html(c):
    flag = (f'<span class="ship-flag">{esc(c["flag"])}</span>'
            if c["flag"] else "")
    paras = "\n      ".join(f"<p>{p}</p>" for p in c["paras"])
    return f"""<div class="card ship">
    <div class="card-head">
      <h3>{esc(c['title'])}{flag}</h3>
      {status_pill('shipped', 'Shipped')}
    </div>
    <p class="work"><i>{esc(c['work'])}</i></p>
    <p class="meta-line">{esc(c['meta'])}</p>
      {paras}
  </div>"""


def rec_html(c):
    paras = "\n      ".join(f"<p>{p}</p>" for p in c["paras"])
    return f"""<div class="card rec">
    <div class="num">{c['n']}</div>
    <div class="card-body">
      <div class="card-head">
        <h3>{esc(c['title'])}</h3>
        {status_pill(c['status'], c['statuslabel'])}
      </div>
      <p class="who">{esc(c['who'])}</p>
      {paras}
    </div>
  </div>"""


shipped_cards = "\n".join(shipped_html(c) for c in SHIPPED)
rec_cards = "\n".join(rec_html(c) for c in RECS)

parallel_rows = "".join(
    f'<tr><td class="auth">{esc(a)}</td><td class="origin"><i>{esc(w)}</i></td>'
    f'<td class="num">{esc(ch)}</td></tr>'
    for a, w, ch in PARALLEL
)

works_rows = "".join(
    f'<tr><td class="auth">{esc(a)}</td><td class="origin">{esc(o)}</td>'
    f'<td class="num">{esc(n)}</td></tr>'
    for a, o, n in WITH_WORKS
)

bio_list = " · ".join(esc(b) for b in BIO_ONLY)

lessons_html = "\n".join(
    f'<div class="lesson"><div class="lesson-k">{esc(k)}</div>'
    f'<p>{body}</p></div>'
    for k, body in LESSONS
)


DOC = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>African Voices on Ochorus — Progress Report</title>
<style>
@font-face {{ font-family:'Fraunces'; src:url(data:font/woff2;base64,{fraunces_n}) format('woff2'); font-weight:100 900; font-style:normal; font-display:block; }}
@font-face {{ font-family:'Fraunces'; src:url(data:font/woff2;base64,{fraunces_i}) format('woff2'); font-weight:100 900; font-style:italic; font-display:block; }}
@font-face {{ font-family:'Garamond'; src:url(data:font/woff2;base64,{garamond_n}) format('woff2'); font-weight:400 800; font-style:normal; font-display:block; }}
@font-face {{ font-family:'Garamond'; src:url(data:font/woff2;base64,{garamond_i}) format('woff2'); font-weight:400 800; font-style:italic; font-display:block; }}

:root{{
  --ground:#f3ede1;
  --surface:#faf6ec;
  --surface-2:#efe7d6;
  --ink:#231c14;
  --ink-soft:#4f4636;
  --ink-faint:#8a7d68;
  --line:#ddd0b8;
  --line-strong:#c9b895;
  --indigo:#31406b;
  --clay:#a8482b;
  --gold:#9a6b12;
  --green:#3f6b3a;      /* shipped */
  --green-bg:#e2ebda;
  --amber:#8a5f10;      /* in progress */
  --amber-bg:#efe6cf;
  --grey:#6a6152;       /* bio-only / in-copyright */
  --grey-bg:#e6ddcc;
  --shadow:rgba(60,44,20,.10);
  --serif:'Fraunces',Georgia,serif;
  --body:'Garamond','Spectral',Georgia,serif;
  --mono:'SF Mono','SFMono-Regular','Menlo','Consolas',monospace;
}}

@page {{ size: A4; margin: 15mm 16mm; }}
*{{ box-sizing:border-box; }}
html,body{{ margin:0; padding:0; }}
body{{
  background:var(--ground);
  color:var(--ink);
  font-family:var(--body);
  font-size:11pt;
  line-height:1.5;
  -webkit-font-smoothing:antialiased;
}}
i,em{{ font-style:italic; }}
b,strong{{ font-weight:600; }}

.page{{ page-break-after:always; }}
.page:last-child{{ page-break-after:auto; }}

/* ---------- Cover ---------- */
.cover{{ height:267mm; display:flex; flex-direction:column; }}
.cover .top{{ flex:none; }}
.cover .mid{{ flex:1; display:flex; flex-direction:column; justify-content:center; }}
.cover .bottom{{ flex:none; }}
.cover .eyebrow{{
  font-family:var(--mono); font-size:10pt; letter-spacing:.24em; text-transform:uppercase;
  color:var(--clay); font-weight:500; margin:0;
}}
.cover .rule{{ width:60px; height:2px; background:var(--indigo); margin:16px 0 0; }}
.cover h1{{
  font-family:var(--serif); font-weight:500; font-size:50pt; line-height:1.04;
  letter-spacing:-.015em; margin:0 0 6px; max-width:155mm;
}}
.cover h1 em{{ font-style:italic; color:var(--indigo); }}
.cover .subtitle{{
  font-family:var(--serif); font-size:20pt; color:var(--clay); font-weight:400;
  margin:14px 0 0; letter-spacing:.01em;
}}
.cover .thesis{{
  font-family:var(--body); font-size:15pt; color:var(--ink-soft); font-style:italic;
  max-width:150mm; line-height:1.45; margin:22px 0 0;
}}
.cover .thesis b{{ color:var(--ink); font-style:normal; font-weight:600; }}
.cover .meta{{
  font-family:var(--mono); font-size:9.5pt; color:var(--ink-faint); letter-spacing:.03em;
  border-top:1px solid var(--line-strong); padding-top:14px; line-height:1.7;
}}
.cover .meta .big{{ color:var(--ink-soft); }}

/* ---------- Section titles ---------- */
.sec-eyebrow{{
  font-family:var(--mono); font-size:9.5pt; letter-spacing:.22em; text-transform:uppercase;
  color:var(--clay); font-weight:500; margin:0 0 10px;
}}
h2.sec{{
  font-family:var(--serif); font-weight:500; font-size:26pt; line-height:1.08;
  letter-spacing:-.01em; margin:0 0 14px; max-width:162mm;
}}
.lede{{ font-size:12.5pt; color:var(--ink-soft); max-width:165mm; margin:0 0 14px; }}
.lede b{{ color:var(--ink); font-weight:600; }}
.body-p{{ max-width:165mm; margin:0 0 12px; color:var(--ink-soft); }}
.body-p b{{ color:var(--ink); }}

/* ---------- Status pills ---------- */
.pill{{
  font-family:var(--mono); font-size:8pt; letter-spacing:.06em; text-transform:uppercase;
  padding:3px 10px; border-radius:20px; font-weight:600; white-space:nowrap; flex:none;
}}
.pill.shipped{{ color:var(--green); background:var(--green-bg); }}
.pill.inprog{{ color:var(--amber); background:var(--amber-bg); }}
.pill.todo{{ color:var(--indigo); background:#e0e4ef; }}
.pill.copy{{ color:var(--grey); background:var(--grey-bg); }}

/* ---------- Constraint / thesis callout ---------- */
.constraint{{
  border-left:3px solid var(--clay); background:var(--surface);
  padding:15px 20px; border-radius:0 8px 8px 0; margin:16px 0 0;
  box-shadow:0 1px 2px var(--shadow); max-width:170mm;
}}
.constraint .k{{
  font-family:var(--mono); font-weight:600; font-size:8.5pt; letter-spacing:.08em;
  text-transform:uppercase; color:var(--clay); display:block; margin-bottom:6px;
}}
.constraint p{{ margin:0; font-size:11pt; color:var(--ink-soft); }}
.constraint b{{ color:var(--ink); }}

/* ---------- Cards (shipped + recommendations) ---------- */
.card{{
  background:var(--surface); border:1px solid var(--line); border-radius:10px;
  padding:13px 18px; margin:0 0 9px; box-shadow:0 1px 2px var(--shadow);
  page-break-inside:avoid;
}}
.card-head{{ display:flex; align-items:baseline; justify-content:space-between; gap:12px; }}
.card h3{{
  font-family:var(--serif); font-weight:600; font-size:14pt; margin:0;
  line-height:1.18; letter-spacing:-.005em;
}}
.card p{{ margin:6px 0 0; font-size:10.4pt; color:var(--ink-soft); line-height:1.42; }}
.card .work{{ color:var(--ink); font-size:11pt; margin-top:4px; }}
.card .meta-line{{
  font-family:var(--mono); font-size:8.4pt; color:var(--ink-faint); letter-spacing:.01em;
  margin-top:4px;
}}
.card .who{{
  font-family:var(--mono); font-size:8.6pt; color:var(--ink-faint); letter-spacing:.01em;
  margin:3px 0 0;
}}
.ship-flag{{
  font-family:var(--mono); font-size:7.6pt; letter-spacing:.06em; text-transform:uppercase;
  color:var(--gold); border:1px solid var(--line-strong); border-radius:4px;
  padding:1px 7px; margin-left:10px; white-space:nowrap; font-weight:600;
  vertical-align:middle;
}}

/* recommendation cards carry a number gutter */
.card.rec{{ display:grid; grid-template-columns:34px 1fr; gap:0 16px; padding:12px 18px 12px 12px; }}
.card.rec .num{{
  font-family:var(--mono); font-size:12.5pt; font-weight:600; color:var(--ink-faint);
  padding-top:2px; font-variant-numeric:tabular-nums; border-right:1px solid var(--line);
  text-align:center; padding-right:5px;
}}
.card.rec .card-body p:first-of-type{{ margin-top:6px; }}

/* ---------- State stats ---------- */
.state{{
  display:grid; grid-template-columns:repeat(3,1fr); gap:1px;
  background:var(--line); border:1px solid var(--line); border-radius:10px;
  overflow:hidden; margin:0 0 18px;
}}
.stat{{ background:var(--surface); padding:20px 18px; }}
.stat .n{{
  font-family:var(--serif); font-weight:500; font-size:42pt; line-height:1;
  color:var(--indigo); font-variant-numeric:tabular-nums;
}}
.stat .n.zero{{ color:var(--clay); }}
.stat .l{{
  font-family:var(--mono); font-size:8.6pt; letter-spacing:.03em; text-transform:uppercase;
  color:var(--ink-faint); margin-top:11px; line-height:1.5;
}}

/* ---------- Tables ---------- */
.tbl{{
  width:100%; border-collapse:collapse; margin:0 0 4px; font-size:10.5pt;
  border:1px solid var(--line); border-radius:10px; overflow:hidden;
}}
.tbl caption{{
  font-family:var(--mono); font-size:9pt; letter-spacing:.14em; text-transform:uppercase;
  color:var(--clay); text-align:left; margin-bottom:9px; font-weight:500;
}}
.tbl th, .tbl td{{ text-align:left; padding:8px 14px; border-bottom:1px solid var(--line); }}
.tbl thead th{{
  font-family:var(--mono); font-size:8.5pt; letter-spacing:.06em; text-transform:uppercase;
  color:var(--ink-faint); font-weight:600; background:var(--surface-2);
}}
.tbl tbody tr{{ background:var(--surface); }}
.tbl tbody tr:last-child td{{ border-bottom:none; }}
.tbl td.auth{{ font-weight:600; color:var(--ink); }}
.tbl td.origin{{ color:var(--ink-soft); }}
.tbl td.num{{ font-family:var(--mono); font-variant-numeric:tabular-nums; color:var(--indigo); text-align:right; }}
.tbl th.num{{ text-align:right; }}

.subhead{{
  font-family:var(--mono); font-size:9pt; letter-spacing:.14em; text-transform:uppercase;
  color:var(--clay); font-weight:500; margin:20px 0 9px;
}}
.biobox{{
  border:1px dashed var(--line-strong); border-radius:10px; background:var(--surface);
  padding:12px 16px; margin:14px 0 0;
}}
.biobox .k{{
  font-family:var(--mono); font-size:8.5pt; letter-spacing:.06em; text-transform:uppercase;
  color:var(--grey); font-weight:600; display:block; margin-bottom:5px;
}}
.biobox p{{ margin:0; font-size:10.4pt; color:var(--ink-soft); }}
.biobox b{{ color:var(--ink); }}

/* ---------- Gap banner ---------- */
.gap{{
  background:var(--indigo); color:#f6efe0; border-radius:10px;
  padding:13px 20px; margin:16px 0 0;
}}
.gap .k{{
  font-family:var(--mono); font-size:8pt; letter-spacing:.1em; text-transform:uppercase;
  color:#c7b6d9; font-weight:600; display:block; margin-bottom:4px;
}}
.gap p{{ margin:0; font-size:11.5pt; color:#f6efe0; }}
.gap b{{ color:#fff; font-weight:600; }}

/* ---------- Lessons ---------- */
.lesson{{
  border-left:3px solid var(--gold); background:var(--surface);
  padding:12px 18px; border-radius:0 8px 8px 0; margin:0 0 9px;
  box-shadow:0 1px 2px var(--shadow); page-break-inside:avoid;
}}
.lesson-k{{
  font-family:var(--serif); font-weight:600; font-size:12.5pt; color:var(--ink);
  margin-bottom:3px;
}}
.lesson p{{ margin:0; font-size:10.6pt; color:var(--ink-soft); line-height:1.42; }}
.lesson b{{ color:var(--ink); }}

footer{{
  margin-top:22px; font-family:var(--mono); font-size:8.5pt; color:var(--ink-faint);
  letter-spacing:.04em; text-align:center;
}}
</style></head><body>

<!-- ===== PAGE 1 — TITLE ===== -->
<section class="page cover">
  <div class="top">
    <p class="eyebrow">Ochorus · Initiative Progress Report</p>
    <div class="rule"></div>
  </div>
  <div class="mid">
    <h1>African Voices<br>on <em>Ochorus</em></h1>
    <p class="subtitle">Progress Report &amp; Recommendations</p>
    <p class="thesis">Growing Ochorus's African authorship — the bios, books and
      sermons of African and African-diaspora authors — <b>within its
      public-domain constraint.</b></p>
  </div>
  <div class="bottom">
    <p class="meta">
      <span class="big">Ochorus &mdash; a free reader of public-domain Christian classics</span><br>
      3 September 2026 &nbsp;·&nbsp; Web &amp; mobile &nbsp;·&nbsp; Multilingual &nbsp;·&nbsp; Status verified as of 3 Sep 2026
    </p>
  </div>
</section>

<!-- ===== PAGE 2 — EXECUTIVE SUMMARY ===== -->
<section class="page">
  <p class="sec-eyebrow">1 · Executive summary</p>
  <h2 class="sec">Five African-authored books, and Ochorus's first sub-Saharan voice.</h2>
  <p class="lede">This initiative adds African and African-diaspora authors — their
    bios, books and sermons — to Ochorus, and deepens those already present.
    Ochorus is <b>public-domain only</b>, and that single constraint shapes every
    choice below.</p>
  <p class="body-p">Since it began, <b>five African-authored books have shipped</b>
    — three of them built in this push. Together they gave Ochorus its first
    sub-Saharan African book and completed a cluster of early Black women
    preachers, a seam of vivid nineteenth-century spiritual memoir that now reads
    as a chorus rather than a single voice.</p>
  <p class="body-p">The chief lesson of the work so far is a practical one about
    where effort goes. It is not the writing or the import that is expensive — it
    is the state of the source text.</p>

  <div class="constraint">
    <span class="k">The lesson that governs every estimate</span>
    <p><b>Source cleanliness governs effort.</b> Clean transcriptions — CCEL,
      Project Gutenberg, DocSouth — import in about an hour. Internet Archive OCR
      scans cost <b>hours of per-book text repair</b> (Crowther's journal alone
      needed some 350 corrections). Always prefer a clean source; when only OCR
      exists, budget for it.</p>
  </div>
</section>

<!-- ===== PAGE 3 — WHAT'S BEEN DONE ===== -->
<section class="page">
  <p class="sec-eyebrow">2 · What's been done</p>
  <h2 class="sec">Shipped this push.</h2>
  <p class="lede">Three books built and merged — all with covers; the two women
    also received full ~1,500-word biographies and verified public-domain
    portraits.</p>

  {shipped_cards}

  <p class="subhead">Already live from parallel work</p>
  <table class="tbl">
    <thead><tr><th>Author</th><th>Work</th><th class="num">Chapters</th></tr></thead>
    <tbody>{parallel_rows}</tbody>
  </table>
  <p class="body-p" style="margin-top:12px">Together with Lee, Smith and Foote, the
    <b>early Black women preachers cluster</b> is now well represented — alongside
    Richard Allen, who converted Lee.</p>
</section>

<!-- ===== PAGE 4 — CURRENT STATE OF THE LIBRARY ===== -->
<section class="page">
  <p class="sec-eyebrow">3 · Current state of the African library</p>
  <h2 class="sec">Nine authors with a work. Still no sermons.</h2>

  <table class="tbl">
    <caption>African authors with works today</caption>
    <thead><tr><th>Author</th><th>Origin</th><th class="num">Books</th></tr></thead>
    <tbody>{works_rows}</tbody>
  </table>

  <div class="biobox">
    <span class="k">Bio-only — no works yet</span>
    <p>{bio_list}. Kivengere, Nsibambi and Sabiti are the modern
      <b>East African Revival</b> figures.</p>
  </div>

  <div class="gap">
    <span class="k">Key gap</span>
    <p><b>Zero sermons by any African author, in any language.</b></p>
  </div>
</section>

<!-- ===== PAGE 5 — IN PROGRESS ===== -->
<section class="page">
  <p class="sec-eyebrow">4 · In progress</p>
  <h2 class="sec">Zilpha Elaw — the hardest of the four.</h2>
  <p class="lede">The last of the three Black women preachers — and the one that
    combines both of the problems the others posed separately.</p>

  <div class="card">
    <div class="card-head">
      <h3>Zilpha Elaw</h3>
      {status_pill('inprog', 'In progress')}
    </div>
    <p class="work"><i>Memoirs (1846)</i></p>
    <p>The only public-domain source is a single <b>badly OCR'd Internet Archive
      scan</b> — systematic damage like &ldquo;tliis&rdquo;&rarr;this, plus whole
      garbage lines. On top of that, the memoir is a <b>continuous narrative with
      no chapter divisions</b>, so it needs editorial chapter-splitting.</p>
    <p>That makes it the hardest of the four: Crowther-level OCR repair
      <i>and</i> the chapterization that Lee's journal required, in one book.</p>
    <p><b>Status:</b> assessment complete; decision pending on whether to push
      through now.</p>
  </div>
</section>

<!-- ===== PAGES 6–8 — RECOMMENDATIONS then LESSONS (one flow) ===== -->
<section class="page">
  <p class="sec-eyebrow">5 · What needs doing — recommendations</p>
  <h2 class="sec">Prioritized next moves.</h2>
  <p class="lede">Ordered by leverage against the public-domain constraint — clean
    sources and empty shelves first.</p>

  {rec_cards}

  <div class="lessons-block">
    <p class="sec-eyebrow" style="margin-top:26px">6 · Lessons &amp; constraints</p>
    <h2 class="sec">What the work has taught, in four lines.</h2>

    {lessons_html}
  </div>

  <footer>Ochorus · African Voices initiative · progress report · 3 September 2026</footer>
</section>

</body></html>"""

OUT.write_text(DOC, encoding="utf-8")
print("wrote", OUT, f"({len(DOC)//1024} KB, fonts embedded)")
