#!/usr/bin/env python3
"""Build "African Voices on Ochorus" — a print-ready ~10-page roadmap for growing
Ochorus's African authorship. Emits a self-contained HTML file (Fraunces + EB
Garamond embedded as base64 woff2, earthy manuscript palette, @page print CSS)
which is then rendered to PDF with headless Chrome. Source of substance:
scratchpad/african-voices-roadmap.html."""
import base64
import html
from pathlib import Path

FONTS = Path.home() / "dev/ochorus/frontend/node_modules/@fontsource-variable"
OUT = Path(__file__).parent / "african-voices.html"


def b64(p: Path) -> str:
    return base64.b64encode(p.read_bytes()).decode()


fraunces_n = b64(FONTS / "fraunces/files/fraunces-latin-wght-normal.woff2")
fraunces_i = b64(FONTS / "fraunces/files/fraunces-latin-wght-italic.woff2")
garamond_n = b64(FONTS / "eb-garamond/files/eb-garamond-latin-wght-normal.woff2")
garamond_i = b64(FONTS / "eb-garamond/files/eb-garamond-latin-wght-italic.woff2")


def esc(s):
    return html.escape(s)


# --- content model -----------------------------------------------------------
# A card: number, title, who, chips, flagship?, paragraphs.
# Each paragraph is (kind, html). kind "p" = body, "titles" = the import list,
# "note" = small faint aside. Inline <i>/<b> markup is authored by hand.

CARDS = [
    # ---- TRACK A ----
    dict(track="A", n="01", flagship=True,
         title="Give Samuel Ajayi Crowther his own writings",
         who="Nigeria (Yorùbá) · 1809–1891 · currently bio-only",
         chips=[("pd", "public domain"), ("eff", "medium"), ("imp", "high")],
         paras=[
             ("p", "The first African Anglican bishop — freed from a slave ship as a boy, he became a scholar, linguist and missionary statesman — and Ochorus's single most important untapped African author. He would be the site's <b>first sub-Saharan African with real books.</b>"),
             ("p", "His name currently carries only a biography, yet the writings that made him a landmark of the nineteenth-century church are all public domain and simply waiting to be imported — clear first-person English that needs little contemporizing, and the anchor for the whole &ldquo;African Voices&rdquo; thread."),
             ("titles", "Import: <i>Journal of an Expedition up the Niger</i> (1841 &amp; 1854), his episcopal <i>Charges</i> and addresses, and <i>Experiences with Heathens and Mohammedans in West Africa</i>."),
         ]),
    dict(track="A", n="02", flagship=False,
         title="Expand Andrew Murray from 11 books toward ~20",
         who="South Africa · 1828–1917 · 11 books, 0 sermons",
         chips=[("pd", "public domain"), ("eff", "low"), ("imp", "high volume")],
         paras=[
             ("p", "Ochorus's best-loved author is himself African, and he wrote <b>~240 works</b> — the import and translate pipelines already know his voice, so each new title is nearly free to add. It is the lowest-friction volume play on the list: no new author record, no fresh bio, and every title is an immediate candidate for the Swahili and Luganda pipelines."),
             ("titles", "Next tier: <i>Abide in Christ</i>, <i>The Two Covenants</i>, <i>The Spirit of Christ</i>, <i>The Full Blessing of Pentecost</i>, <i>Like Christ</i>, <i>Working for God</i>, <i>Money</i>, <i>The Prayer Life</i>, <i>Be Perfect</i>."),
         ]),
    dict(track="A", n="03", flagship=False,
         title="Grow Augustine beyond the Confessions",
         who="Hippo, North Africa (Algeria) · 354–430 · 1 book",
         chips=[("pd", "public domain"), ("eff", "medium"), ("imp", "high")],
         paras=[
             ("p", "The towering North African. One book here badly under-represents the man who shaped Western theology more than any figure between Paul and the Reformation. The trick is sequencing: reach for the short, warm, pastoral works first so the shelf grows readable rather than forbidding."),
             ("titles", "Add the accessible ones first: <i>The Enchiridion</i> (Handbook on Faith, Hope &amp; Love), <i>Ten Homilies on the First Epistle of John</i>, <i>On Christian Doctrine</i>, then selected <i>Sermons</i>. Save an abridged <i>City of God</i> for later."),
         ]),
    dict(track="A", n="04", flagship=False,
         title="Round out Athanasius of Alexandria",
         who="Alexandria, Egypt · 296–373 · 2 books",
         chips=[("pd", "public domain"), ("eff", "medium"), ("imp", "medium")],
         paras=[
             ("p", "You already host <i>On the Incarnation</i> and his <i>Life of Antony</i>, so the author page and audience exist — this is filling out a shelf, not founding one."),
             ("titles", "Add his devotional gem <i>Letter to Marcellinus on the Psalms</i> — a reader-friendly doorway into praying the Psalter — plus <i>Against the Heathen</i> and selected <i>Festal Letters</i>."),
         ]),
    dict(track="A", n="05", flagship=False,
         title="Give Cyprian of Carthage his first works",
         who="Carthage (Tunisia) · 200–258 · currently bio-only",
         chips=[("pd", "public domain"), ("eff", "medium"), ("imp", "high")],
         paras=[
             ("p", "A bishop-martyr with a bio but no books. His short treatises are ideal reader-length — a single sitting each — which makes him quick to import and easy to translate."),
             ("titles", "<i>On the Lord's Prayer</i>, <i>On the Mortality</i>, <i>On Works and Alms</i>, <i>On the Unity of the Church</i>, and selected <i>Epistles</i>."),
         ]),
    dict(track="A", n="06", flagship=False,
         title="Give Richard Allen his autobiography",
         who="African-American · founder of the AME Church · 1760–1831 · bio-only",
         chips=[("pd", "public domain"), ("eff", "low"), ("imp", "medium")],
         paras=[
             ("p", "A foundational voice of the Black church, and his own account of it is short, vivid and entirely free — a low-effort import that turns a bare biography into a reading experience."),
             ("titles", "<i>The Life Experience and Gospel Labours of the Rt. Rev. Richard Allen</i>, with his <i>Address to Those Who Keep Slaves</i>."),
         ]),
    dict(track="A", n="07", flagship=False,
         title="Give Amanda Berry Smith her Autobiography",
         who="African-American evangelist · missionary in Liberia &amp; Sierra Leone · 1837–1915 · bio-only",
         chips=[("pd", "public domain"), ("eff", "low"), ("imp", "high")],
         paras=[
             ("p", "<i>An Autobiography: The Story of the Lord's Dealings with Mrs. Amanda Smith</i> (1893) is a holiness classic — and eight of its years are a first-hand <b>West African missionary narrative</b>, bridging the diaspora and the continent in a single life."),
             ("p", "It is the rare book that speaks to two of Ochorus's audiences at once, and it lands cheaply: the full text is public domain and needs no abridgement."),
         ]),
    dict(track="A", n="08", flagship=False,
         title="Give Lemuel Haynes his sermons",
         who="African-American · first Black man ordained in the USA · 1753–1833 · bio-only",
         chips=[("pd", "public domain"), ("eff", "low"), ("imp", "medium")],
         paras=[
             ("p", "Ochorus has <b>no sermons by any African author yet</b> — Haynes breaks that duck. His preaching is compact, argued and quotable, exactly the material the empty sermons shelf needs."),
             ("titles", "Lead with his famous <i>Universal Salvation</i>, plus <i>The Nature and Importance of True Republicanism</i> and other collected sermons."),
         ]),

    # ---- TRACK B ----
    dict(track="B", n="09", flagship=True,
         title="Add Tertullian of Carthage",
         who="Carthage (Tunisia) · c.155–220 · new author",
         chips=[("pd", "public domain"), ("eff", "medium"), ("imp", "high")],
         paras=[
             ("p", "The first great theologian to write in Latin, wholly North African — and conspicuously absent from the library. A major gap to close, and one that visibly strengthens the ancient-Africa cluster the roadmap is building."),
             ("titles", "Bio + <i>On Prayer</i>, <i>On Patience</i>, <i>To the Martyrs</i>, and the <i>Apology</i>."),
         ]),
    dict(track="B", n="10", flagship=False,
         title="Add Clement of Alexandria",
         who="Alexandria, Egypt · c.150–215 · new author",
         chips=[("pd", "public domain"), ("eff", "medium"), ("imp", "medium")],
         paras=[
             ("p", "Not the Clement of Rome you already host — a distinction worth stating plainly on the page so the two are never confused."),
             ("titles", "Start with the short, warm <i>Who Is the Rich Man That Shall Be Saved?</i>, then <i>The Instructor (Paedagogus)</i>."),
         ]),
    dict(track="B", n="11", flagship=False,
         title="Add Origen of Alexandria",
         who="Alexandria, Egypt · c.184–253 · new author",
         chips=[("pd", "public domain"), ("eff", "medium"), ("imp", "medium")],
         paras=[
             ("p", "His <i>On Prayer</i> is one of the earliest and richest treatises on the Lord's Prayer — a natural fit for a library already thick with prayer classics, and a title that reads devotionally rather than as a controversy."),
         ]),
    dict(track="B", n="12", flagship=False,
         title="Add Macarius of Egypt",
         who="Egyptian desert · c.300–391 · new author",
         chips=[("pd", "public domain"), ("eff", "medium"), ("imp", "medium")],
         paras=[
             ("p", "His <i>Fifty Spiritual Homilies</i> shaped John Wesley directly — a ready-made link to the Wesley material already on Ochorus, and deeply devotional in its own right. Cross-linking the two turns an obscure name into a discoverable one."),
         ]),
    dict(track="B", n="13", flagship=False,
         title="Add Perpetua of Carthage",
         who="Carthage (Tunisia) · martyred 203 · new author",
         chips=[("pd", "public domain"), ("eff", "low"), ("imp", "high")],
         paras=[
             ("p", "<i>The Passion of Perpetua and Felicity</i> preserves her prison diary — the <b>earliest surviving writing by a Christian woman</b>, and it is African. A short, unforgettable read that also adds a woman's voice to the ancient set."),
             ("p", "Low effort, high resonance: it is brief enough to import in an afternoon, and it opens the reading plan on a note no other library can match."),
         ]),
    dict(track="B", n="14", flagship=False,
         title="Add the Desert Fathers of Egypt",
         who="Egyptian desert · 3rd–5th c. · new author/collection",
         chips=[("pd", "public domain"), ("eff", "medium"), ("imp", "medium")],
         paras=[
             ("p", "Antony the Great already appears through Athanasius's <i>Life</i>; give him his own page with the <i>Letters of Antony</i>, and add a curated <i>Sayings of the Desert Fathers</i> selection — the seedbed of Christian monasticism, entirely African."),
         ]),
    dict(track="B", n="15", flagship=False,
         title="Add the Black women preachers of the holiness tradition",
         who="African-American · 19th c. · new authors (a cluster)",
         chips=[("pd", "public domain"), ("eff", "medium"), ("imp", "high")],
         paras=[
             ("p", "An underrepresented seam of vivid spiritual memoir, and one that pairs naturally with Amanda Smith to give the diaspora a chorus rather than a single voice. Bios + full texts, all free."),
             ("titles", "<b>Jarena Lee</b> (<i>Religious Experience and Journal</i>), <b>Julia A. J. Foote</b> (<i>A Brand Plucked from the Fire</i>), and <b>Zilpha Elaw</b> (<i>Memoirs</i>)."),
         ]),
    dict(track="B", n="16", flagship=False,
         title="Add the AME founders around Richard Allen",
         who="African-American · late 18th–19th c. · new authors",
         chips=[("pd", "public domain"), ("eff", "low"), ("imp", "medium")],
         paras=[
             ("p", "Completing the founding generation of the independent Black church alongside Allen turns a single entry into a coherent movement readers can follow."),
             ("titles", "<b>Daniel A. Payne</b> (<i>Recollections of Seventy Years</i>) and <b>Absalom Jones</b> (<i>A Thanksgiving Sermon</i>, 1808)."),
         ]),
    dict(track="B", n="17", flagship=False,
         title="Build the East African Revival as a bio cluster",
         who="Uganda, Rwanda, South Africa · 19th–20th c. · bios only",
         chips=[("copy", "in copyright → bio only"), ("eff", "low"), ("imp", "medium")],
         paras=[
             ("p", "Deepen the pages you already have (Kivengere, Nsibambi, Sabiti) and add <b>Apolo Kivebulaya</b>, <b>William Wadé Harris</b>, <b>Bernard Mizeki</b>, and <b>Tiyo Soga</b> — the first ordained Black South African, who translated <i>Pilgrim's Progress</i> into Xhosa (a lovely tie to a book you already host)."),
             ("note", "These are honour pages, not book pages — their own writings remain in copyright. Say so plainly on each."),
         ]),

    # ---- TRACK C ----
    dict(track="C", n="18", flagship=False,
         title="Translate African authors into your African languages",
         who="Swahili &amp; Luganda — already live on Ochorus",
         chips=[("eff", "low–medium"), ("imp", "high")],
         paras=[
             ("p", "You already run <b>sw</b> and <b>lg</b>. Push Murray, Crowther, Augustine and Cyprian through the translate-book pipeline into both — African works, read by African readers, in African languages."),
             ("p", "The content from Tracks A and B is the raw material here; this is the move that turns a growing shelf into genuine reach on the continent itself."),
         ]),
    dict(track="C", n="19", flagship=False,
         title="Open new African target languages — and staff the review gate",
         who="Hausa · Yorùbá · Amharic · Zulu/Xhosa · French",
         chips=[("eff", "medium"), ("imp", "high")],
         paras=[
             ("p", "The Language registry takes a new language from the admin with <b>no deploy</b>. The real bottleneck isn't machine translation — it's <b>native review</b> to lift <span class=\"mono-inline\">ai_unreviewed</span> to approved."),
             ("p", "Recruiting African reviewers is therefore the highest-leverage non-code move on this list: it is the one step that lets everything else ship as trustworthy, native-checked text rather than a badge of caution."),
         ]),
    dict(track="C", n="20", flagship=False,
         title="Curate and merchandise an “African Church” thread",
         who="Collection page · reading plan · quotes · covers",
         chips=[("eff", "low–medium"), ("imp", "high")],
         paras=[
             ("p", "Tie it together so readers discover it: an <b>African Voices</b> collection and a reading plan — <i>From Carthage to Kampala</i> — threading Perpetua &rarr; Cyprian &rarr; Augustine &rarr; the Desert Fathers &rarr; Crowther &rarr; the Revival."),
             ("p", "Then grow each author's quote page and commission covers, so these voices surface on the homepage and in search rather than waiting to be looked up by name."),
         ]),
]

TRACKS = {
    "A": ("Deepen the Africans already on Ochorus",
          "Eight authors are on the site now. Give them their actual books and sermons — the fastest wins, since the import machinery and their audience already exist."),
    "B": ("New African authors — bios, and books where they're free",
          "The continent's own catalogue is deep. These names aren't on Ochorus at all yet; most bring genuine public-domain works, and the modern ones bring bios."),
    "C": ("Multiply the reach of everything above",
          "Content is only half the goal — these three moves put African voices in front of African readers, in their own languages."),
}

# Appendix: the concrete public-domain source works named across the roadmap.
APPENDIX = [
    ("Samuel Ajayi Crowther", "Journal of an Expedition up the Niger (1841 &amp; 1854); episcopal Charges &amp; addresses; Experiences with Heathens and Mohammedans in West Africa"),
    ("Andrew Murray", "Abide in Christ; The Two Covenants; The Spirit of Christ; The Full Blessing of Pentecost; Like Christ; Working for God; Money; The Prayer Life; Be Perfect"),
    ("Augustine of Hippo", "The Enchiridion; Ten Homilies on the First Epistle of John; On Christian Doctrine; selected Sermons; an abridged City of God"),
    ("Athanasius of Alexandria", "Letter to Marcellinus on the Psalms; Against the Heathen; selected Festal Letters"),
    ("Cyprian of Carthage", "On the Lord's Prayer; On the Mortality; On Works and Alms; On the Unity of the Church; selected Epistles"),
    ("Richard Allen", "The Life Experience and Gospel Labours of the Rt. Rev. Richard Allen; Address to Those Who Keep Slaves"),
    ("Amanda Berry Smith", "An Autobiography: The Story of the Lord's Dealings with Mrs. Amanda Smith (1893)"),
    ("Lemuel Haynes", "Universal Salvation; The Nature and Importance of True Republicanism; collected sermons"),
    ("Tertullian of Carthage", "On Prayer; On Patience; To the Martyrs; Apology"),
    ("Clement of Alexandria", "Who Is the Rich Man That Shall Be Saved?; The Instructor (Paedagogus)"),
    ("Origen of Alexandria", "On Prayer"),
    ("Macarius of Egypt", "Fifty Spiritual Homilies"),
    ("Perpetua of Carthage", "The Passion of Perpetua and Felicity"),
    ("Desert Fathers", "Letters of Antony; a curated Sayings of the Desert Fathers"),
    ("Black women preachers", "Jarena Lee — Religious Experience and Journal; Julia A. J. Foote — A Brand Plucked from the Fire; Zilpha Elaw — Memoirs"),
    ("AME founders", "Daniel A. Payne — Recollections of Seventy Years; Absalom Jones — A Thanksgiving Sermon (1808)"),
]


# --- rendering ---------------------------------------------------------------

def chip_html(kind, label):
    cls = {"pd": "chip pd", "copy": "chip copy", "eff": "chip eff",
           "imp": "chip imp"}.get(kind, "chip")
    return f'<span class="{cls}">{label}</span>'


def para_html(kind, body):
    if kind == "titles":
        return f'<p class="titles">{body}</p>'
    if kind == "note":
        return f'<p class="note">{body}</p>'
    return f"<p>{body}</p>"


def card_html(c):
    flag = " flagship" if c["flagship"] else ""
    chips = "".join(chip_html(k, l) for k, l in c["chips"])
    paras = "\n      ".join(para_html(k, b) for k, b in c["paras"])
    return f"""<div class="card{flag}">
    <div class="num">{c['n']}</div>
    <div class="card-body">
      <h3>{esc(c['title'])}</h3>
      <p class="who">{c['who']}</p>
      <div class="chips">{chips}</div>
      {paras}
    </div>
  </div>"""


def track_section(letter):
    name, sub = TRACKS[letter]
    cards = "\n".join(card_html(c) for c in CARDS if c["track"] == letter)
    return f"""<section class="track track-{letter}">
  <div class="track-head">
    <span class="track-tag">{letter}</span>
    <h2>{esc(name)}</h2>
  </div>
  <p class="track-sub">{esc(sub)}</p>
  {cards}
</section>"""


appendix_rows = "\n".join(
    f'    <div class="src"><div class="src-author">{esc(a)}</div>'
    f'<div class="src-works">{w}</div></div>'
    for a, w in APPENDIX
)

DOC = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>African Voices on Ochorus</title>
<style>
@font-face {{ font-family:'Fraunces'; src:url(data:font/woff2;base64,{fraunces_n}) format('woff2'); font-weight:100 900; font-style:normal; font-display:block; }}
@font-face {{ font-family:'Fraunces'; src:url(data:font/woff2;base64,{fraunces_i}) format('woff2'); font-weight:100 900; font-style:italic; font-display:block; }}
@font-face {{ font-family:'Garamond'; src:url(data:font/woff2;base64,{garamond_n}) format('woff2'); font-weight:400 800; font-style:normal; font-display:block; }}
@font-face {{ font-family:'Garamond'; src:url(data:font/woff2;base64,{garamond_i}) format('woff2'); font-weight:400 800; font-style:italic; font-display:block; }}

:root{{
  --ground:#f3ede1;        /* parchment, ochre-biased */
  --surface:#faf6ec;
  --surface-2:#efe7d6;
  --ink:#231c14;           /* warm near-black */
  --ink-soft:#4f4636;
  --ink-faint:#8a7d68;
  --line:#ddd0b8;
  --line-strong:#c9b895;
  --indigo:#31406b;        /* deep indigo — primary */
  --clay:#a8482b;          /* burnt sienna accent */
  --gold:#9a6b12;          /* muted manuscript gold */
  --pd:#3f6b3a;            /* public-domain green */
  --pd-bg:#e2ebda;
  --copyright:#8a5f10;     /* bio-only amber */
  --copyright-bg:#efe6cf;
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
.mono-inline{{ font-family:var(--mono); font-size:9.4pt; }}

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
  font-family:var(--serif); font-weight:500; font-size:52pt; line-height:1.03;
  letter-spacing:-.015em; margin:0 0 6px; max-width:150mm;
}}
.cover h1 em{{ font-style:italic; color:var(--indigo); }}
.cover .thesis{{
  font-family:var(--body); font-size:16pt; color:var(--ink-soft); font-style:italic;
  max-width:150mm; line-height:1.4; margin:20px 0 0;
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
  font-family:var(--serif); font-weight:500; font-size:27pt; line-height:1.06;
  letter-spacing:-.01em; margin:0 0 16px; max-width:160mm;
}}
.lede{{ font-size:12.5pt; color:var(--ink-soft); max-width:165mm; margin:0 0 16px; }}
.lede b{{ color:var(--ink); font-weight:600; }}
.body-p{{ max-width:165mm; margin:0 0 12px; color:var(--ink-soft); }}
.body-p b{{ color:var(--ink); }}

/* ---------- Constraint callout ---------- */
.constraint{{
  border-left:3px solid var(--clay); background:var(--surface);
  padding:16px 20px; border-radius:0 8px 8px 0; margin:18px 0 0;
  box-shadow:0 1px 2px var(--shadow); max-width:170mm;
}}
.constraint .k{{
  font-family:var(--mono); font-weight:600; font-size:8.5pt; letter-spacing:.08em;
  text-transform:uppercase; color:var(--clay); display:block; margin-bottom:6px;
}}
.constraint p{{ margin:0; font-size:11pt; color:var(--ink-soft); }}
.constraint b{{ color:var(--ink); }}

/* ---------- State of play ---------- */
.state{{
  display:grid; grid-template-columns:repeat(3,1fr); gap:1px;
  background:var(--line); border:1px solid var(--line); border-radius:10px;
  overflow:hidden; margin:0 0 10px;
}}
.stat{{ background:var(--surface); padding:22px 18px; }}
.stat .n{{
  font-family:var(--serif); font-weight:500; font-size:46pt; line-height:1;
  color:var(--indigo); font-variant-numeric:tabular-nums;
}}
.stat .n .frac{{ font-size:22pt; color:var(--ink-faint); }}
.stat .l{{
  font-family:var(--mono); font-size:9pt; letter-spacing:.03em; text-transform:uppercase;
  color:var(--ink-faint); margin-top:12px; line-height:1.5;
}}
.state-note{{
  font-family:var(--mono); font-size:9.5pt; color:var(--ink-faint);
  margin:0 0 26px; text-align:right; letter-spacing:.02em;
}}

/* ---------- Current authors table ---------- */
.tbl{{
  width:100%; border-collapse:collapse; margin:0 0 4px; font-size:10.5pt;
  border:1px solid var(--line); border-radius:10px; overflow:hidden;
}}
.tbl caption{{
  font-family:var(--mono); font-size:9pt; letter-spacing:.14em; text-transform:uppercase;
  color:var(--clay); text-align:left; margin-bottom:10px; font-weight:500;
}}
.tbl th, .tbl td{{ text-align:left; padding:9px 14px; border-bottom:1px solid var(--line); }}
.tbl thead th{{
  font-family:var(--mono); font-size:8.5pt; letter-spacing:.06em; text-transform:uppercase;
  color:var(--ink-faint); font-weight:600; background:var(--surface-2);
}}
.tbl tbody tr{{ background:var(--surface); }}
.tbl tbody tr:last-child td{{ border-bottom:none; }}
.tbl td.auth{{ font-weight:600; color:var(--ink); }}
.tbl td.origin{{ color:var(--ink-soft); }}
.tbl td.num{{ font-family:var(--mono); font-variant-numeric:tabular-nums; color:var(--indigo); }}
.tbl td.dim{{ color:var(--ink-faint); font-style:italic; }}

/* ---------- Track headers ---------- */
.track-head{{
  display:flex; align-items:baseline; gap:12px;
  margin:0 0 6px; padding-bottom:10px; border-bottom:2px solid var(--line-strong);
}}
.track-tag{{
  font-family:var(--mono); font-weight:600; font-size:12pt; color:var(--surface);
  background:var(--indigo); padding:3px 12px; border-radius:5px; letter-spacing:.04em; flex:none;
}}
.track-head h2{{
  font-family:var(--serif); font-weight:500; font-size:19pt; margin:0; letter-spacing:-.01em;
}}
.track-sub{{ font-size:11pt; color:var(--ink-faint); margin:0 0 16px; font-style:italic; max-width:170mm; }}

/* ---------- Cards ---------- */
.card{{
  display:grid; grid-template-columns:38px 1fr; gap:0 16px;
  background:var(--surface); border:1px solid var(--line); border-radius:10px;
  padding:11px 16px 11px 12px; margin:0 0 8px; box-shadow:0 1px 2px var(--shadow);
  position:relative; page-break-inside:avoid;
}}
.num{{
  font-family:var(--mono); font-size:12.5pt; font-weight:600; color:var(--ink-faint);
  padding-top:2px; font-variant-numeric:tabular-nums; border-right:1px solid var(--line);
  text-align:center; padding-right:5px;
}}
.card.flagship{{ border-color:var(--line-strong); background:var(--surface-2); }}
.card.flagship::before{{
  content:"★ flagship"; position:absolute; top:-9px; left:54px;
  font-family:var(--mono); font-size:8pt; letter-spacing:.08em; text-transform:uppercase;
  color:var(--gold); background:var(--ground); padding:1px 8px; border-radius:4px; font-weight:600;
}}
.card h3{{
  font-family:var(--serif); font-weight:600; font-size:13pt; margin:0 0 3px;
  line-height:1.18; letter-spacing:-.005em;
}}
.who{{
  font-family:var(--mono); font-size:8.4pt; color:var(--ink-faint); letter-spacing:.01em; margin:0 0 8px;
}}
.card p{{ margin:0 0 6px; font-size:10.2pt; color:var(--ink-soft); line-height:1.4; }}
.card p:last-child{{ margin-bottom:0; }}
.card .titles{{ color:var(--ink); }}
.card .note{{ font-size:9.6pt; color:var(--ink-faint); font-style:italic; }}

.chips{{ display:flex; flex-wrap:wrap; gap:6px; margin:0 0 7px; }}
.chip{{
  font-family:var(--mono); font-size:8.4pt; letter-spacing:.02em; padding:2px 9px;
  border-radius:20px; border:1px solid var(--line-strong); color:var(--ink-soft); white-space:nowrap;
}}
.chip.pd{{ color:var(--pd); background:var(--pd-bg); border-color:transparent; font-weight:500; }}
.chip.copy{{ color:var(--copyright); background:var(--copyright-bg); border-color:transparent; font-weight:500; }}
.chip.eff::before{{ content:"effort "; color:var(--ink-faint); }}
.chip.imp::before{{ content:"impact "; color:var(--ink-faint); }}

/* ---------- Close ---------- */
.close{{
  padding:18px 24px; background:var(--indigo); color:var(--surface);
  border-radius:12px; margin:0 0 18px;
}}
.close h2{{ font-family:var(--serif); font-weight:500; font-size:19pt; margin:0 0 9px; color:#f6efe0; }}
.close p{{ margin:0 0 8px; font-size:10.6pt; line-height:1.45; color:#e9e0cd; }}
.close p:last-child{{ margin-bottom:0; }}
.close b{{ font-weight:600; color:#fff; }}

/* ---------- Appendix ---------- */
.appendix-head{{
  font-family:var(--serif); font-weight:500; font-size:17pt; margin:0 0 4px; letter-spacing:-.01em;
}}
.appendix-sub{{ font-size:10.2pt; color:var(--ink-faint); font-style:italic; margin:0 0 11px; }}
.src-list{{
  border:1px solid var(--line); border-radius:10px; overflow:hidden; background:var(--surface);
}}
.src{{ display:grid; grid-template-columns:50mm 1fr; gap:0 16px; padding:6px 16px; border-bottom:1px solid var(--line); page-break-inside:avoid; }}
.src:last-child{{ border-bottom:none; }}
.src-author{{ font-weight:600; color:var(--ink); font-size:9.8pt; }}
.src-works{{ color:var(--ink-soft); font-size:9.4pt; line-height:1.35; }}
.src-works i{{ font-style:italic; }}

footer{{
  margin-top:22px; font-family:var(--mono); font-size:8.5pt; color:var(--ink-faint);
  letter-spacing:.04em; text-align:center;
}}
</style></head><body>

<!-- ===== PAGE 1 — COVER ===== -->
<section class="page cover">
  <div class="top">
    <p class="eyebrow">Ochorus · Library Acquisition Roadmap</p>
    <div class="rule"></div>
  </div>
  <div class="mid">
    <h1>African Voices,<br><em>from Carthage<br>to Kampala</em></h1>
    <p class="thesis">Twenty moves to grow Ochorus's African authorship — <b>new bios, new books and sermons, and more works for the Africans already here</b> — ordered so the public-domain wins come first.</p>
  </div>
  <div class="bottom">
    <p class="meta">
      <span class="big">Ochorus &mdash; a free reader of public-domain Christian classics</span><br>
      Roadmap drafted 2 September 2026 &nbsp;·&nbsp; Web &amp; mobile &nbsp;·&nbsp; Multilingual &nbsp;·&nbsp; Kampala, Uganda
    </p>
  </div>
</section>

<!-- ===== PAGE 2 — EXECUTIVE SUMMARY ===== -->
<section class="page">
  <p class="sec-eyebrow">Executive summary</p>
  <h2 class="sec">The library is more African than its shelves show.</h2>
  <p class="lede">Nearly a quarter of Ochorus's authors were born, ministered, or have their heritage in Africa — yet the continent is almost invisible in what readers can actually open. This roadmap sets out <b>twenty concrete moves</b> to close that gap, grouped in three tracks and ordered so the cheapest, highest-impact public-domain wins come first.</p>
  <p class="body-p">The opportunity is unusually clean because the raw material already exists. The North African church fathers and South Africa's Andrew Murray are long out of copyright and, in several cases, already have an author page and an audience waiting on the site. The import and translation machinery is built. What is missing is not capability but <b>deliberate acquisition</b> — deciding which African works to add, and in what order.</p>
  <p class="body-p">Three tracks structure the plan. <b>Track A</b> deepens the eight Africans already on Ochorus by giving them their actual books and sermons. <b>Track B</b> brings on new African authors — full texts where their writing is free, honour pages where it is not. <b>Track C</b> multiplies the reach of everything above through translation into African languages and editorial curation. The single signature move is <b>importing Samuel Ajayi Crowther's own writings</b>, which would give Ochorus its first sub-Saharan African books.</p>

  <div class="constraint">
    <span class="k">The one constraint that shapes everything</span>
    <p>Ochorus is <b>public-domain only.</b> That splits the field cleanly. The richest African <b>books</b> are the North African church fathers (Tertullian, Cyprian, Augustine, Athanasius) and South Africa's Andrew Murray — all long out of copyright. Modern revival figures (Kivengere, Nsibambi, Sabiti) can be honoured with <b>bio pages</b>, but their writings are still in copyright and cannot be hosted as books. Every recommendation below is filed on the correct side of that line.</p>
  </div>
</section>

<!-- ===== PAGE 3 — STATE OF PLAY ===== -->
<section class="page">
  <p class="sec-eyebrow">State of play</p>
  <h2 class="sec">Twelve African authors. Four with a book. Zero sermons.</h2>
  <p class="lede">The gap isn't in who is catalogued — it is in what has actually been imported and made readable.</p>

  <div class="state">
    <div class="stat"><div class="n">12<span class="frac">/49</span></div><div class="l">Authors with an African birth, ministry or heritage</div></div>
    <div class="stat"><div class="n">4</div><div class="l">Of those who currently have any book on the site</div></div>
    <div class="stat"><div class="n">0</div><div class="l">Sermons by an African author, in any language</div></div>
  </div>
  <p class="state-note">Murray · 11 books &nbsp;|&nbsp; Augustine · 1 &nbsp;|&nbsp; Athanasius · 2 &nbsp;|&nbsp; Buyinza · 1 &nbsp;|&nbsp; eight others: bio only</p>

  <table class="tbl">
    <caption>African authors with a book today</caption>
    <thead><tr><th>Author</th><th>Origin</th><th>Books</th><th>Sermons</th></tr></thead>
    <tbody>
      <tr><td class="auth">Andrew Murray</td><td class="origin">South Africa · 1828–1917</td><td class="num">11</td><td class="dim">none</td></tr>
      <tr><td class="auth">Athanasius of Alexandria</td><td class="origin">Egypt · 296–373</td><td class="num">2</td><td class="dim">none</td></tr>
      <tr><td class="auth">Augustine of Hippo</td><td class="origin">Algeria · 354–430</td><td class="num">1</td><td class="dim">none</td></tr>
      <tr><td class="auth">Hannah Buyinza</td><td class="origin">Uganda · contemporary</td><td class="num">1</td><td class="dim">none</td></tr>
    </tbody>
  </table>
  <p class="body-p" style="margin-top:14px">The remaining eight — Crowther, Cyprian, Richard Allen, Amanda Berry Smith, Lemuel Haynes and the East African Revival figures among them — carry only a biography. Tracks A and B below turn as many of those bio-only pages as copyright allows into pages a reader can actually open, and the empty sermons column is the plainest single target on the whole site.</p>
</section>

<!-- ===== PAGES 4–5 — TRACK A ===== -->
<section class="page">
  {track_section("A")}
</section>

<!-- ===== PAGES 6–8 — TRACK B ===== -->
<section class="page">
  {track_section("B")}
</section>

<!-- ===== PAGE 9 — TRACK C ===== -->
<section class="page">
  {track_section("C")}
</section>

<!-- ===== PAGE 10 — WHERE TO START + APPENDIX ===== -->
<section class="page">
  <div class="close">
    <h2>Where I'd start this week</h2>
    <p><b>Highest impact, lowest cost:</b> #2 (more Murray — pure volume, machinery ready), #7 (Amanda Smith's autobiography — a diaspora-to-Africa bridge), and #13 (Perpetua — short, striking, and it adds a woman's voice to the ancient set).</p>
    <p><b>The signature move:</b> #1 — Crowther's own writings would give Ochorus its first sub-Saharan African books and anchor the whole &ldquo;African Voices&rdquo; thread.</p>
  </div>

  <p class="appendix-head">Appendix · Public-domain source works named in this roadmap</p>
  <p class="appendix-sub">Every title below is out of copyright and importable today; the copyright-bound Revival figures (item&nbsp;17) are deliberately absent — they are honour pages, not books.</p>
  <div class="src-list">
{appendix_rows}
  </div>

  <footer>Ochorus · public-domain Christian classics · roadmap drafted 2 Sep 2026</footer>
</section>

</body></html>"""

OUT.write_text(DOC, encoding="utf-8")
print("wrote", OUT, f"({len(DOC)//1024} KB, fonts embedded)")
