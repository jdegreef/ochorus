#!/usr/bin/env python3
"""Build docs/scrollreader_lessons.html — a four-page brief on what Ochorus can
learn from scrollreader.com (an audio-first library of the same public-domain
Christian classics) — in the house style of docs/ideas.html (its exact <style>,
embedded fonts and all) retinted to strict black and white for printing, then render it to docs/scrollreader_lessons.pdf with
headless Chrome.

Run:  python3 docs/build_scrollreader_lessons_pdf.py
"""
from __future__ import annotations
import html
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "ideas.html"  # borrow its <style> + embedded fonts
OUT_HTML = HERE / "scrollreader_lessons.html"
OUT_PDF = HERE / "scrollreader_lessons.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def head_from_ideas() -> str:
    doc = SRC.read_text(encoding="utf-8")
    end = doc.index("</style>") + len("</style>")
    return doc[:end]


def esc(s: str) -> str:
    return html.escape(s, quote=False)


EXTRA_STYLE = """<style>
.cover{ height:auto; padding:6mm 0 4mm; page-break-after:avoid; text-align:start; align-items:flex-start; }
.cover h1{ font-size:26pt; margin:6px 0 4px; }
.cover .sub{ font-size:10.5pt; }
.cover .rule{ margin:8px 0; }
.cover .meta{ margin-top:6px; }
.page{ page-break-before:always; }
.page h2, .intro h2{ font-family:var(--serif); font-size:16pt; margin:0 0 6px; }
.lede{ font-size:10.2pt; color:var(--muted); margin:0 0 10px; }
.take{ display:flex; gap:10px; margin-bottom:9px; page-break-inside:avoid; }
.take .num{ flex:0 0 26px; height:26px; border-radius:999px; background:var(--accent); color:#fff; font-family:var(--sans); font-weight:700; font-size:10pt; display:flex; align-items:center; justify-content:center; }
.take h3{ margin:2px 0 3px; font-size:11.5pt; }
.take p{ margin:0 0 3px; font-size:9.8pt; }
.grp{ font-family:var(--sans); font-size:8.4pt; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); margin:14px 0 7px; padding-bottom:3px; border-bottom:1px solid var(--border); }
.grp:first-of-type{ margin-top:2px; }
.les{ display:flex; gap:8px; margin:0 0 9px; page-break-inside:avoid; font-size:10.2pt; line-height:1.42; }
.les .n{ flex:0 0 20px; font-family:var(--sans); font-weight:700; color:var(--accent); font-size:9.5pt; padding-top:1px; }
.les b{ font-family:var(--sans); }
.st{ display:inline-block; font-family:var(--sans); font-size:7.2pt; letter-spacing:.06em; text-transform:uppercase; padding:1px 6px; border-radius:999px; margin-left:5px; vertical-align:1px; border:1px solid var(--border); color:var(--muted); }
.st.new{ background:var(--accent); color:#fff; border-color:var(--accent); }
.st.part{ background:var(--surface); }
.two{ display:grid; grid-template-columns:1fr 1fr; gap:0 16px; }
table{ width:100%; border-collapse:collapse; font-size:9.3pt; margin:6px 0 12px; page-break-inside:avoid; }
th,td{ text-align:left; vertical-align:top; padding:6px 8px; border-bottom:1px solid var(--border); }
th{ font-family:var(--sans); font-size:8pt; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); background:var(--surface); }
td.k{ font-family:var(--sans); font-weight:700; white-space:nowrap; }
.small{ font-size:9pt; color:var(--muted); }
.foot{ margin-top:6px; }
.key{ font-size:8.6pt; color:var(--muted); margin:0 0 8px; }
/* Strictly black and white, for printing: retint every token, drop fills and rounded chrome. */
:root{ --bg:#fff; --surface:#fff; --surface-2:#fff; --text:#000; --muted:#000; --accent:#000; --gold:#000;
  --border:#000; --soft:#fff; --soft-b:#000; }
body{ background:#fff; color:#000; }
.intro p, .idea-body>p{ color:#000; }
.take .num{ background:#fff; color:#000; border:1.5px solid #000; }
.st{ border-color:#000; color:#000; background:#fff; border-radius:0; }
.st.new{ background:#000; color:#fff; }
.st.part{ background:#fff; }
.callout{ background:#fff; border:1px solid #000; border-left:4px solid #000; border-radius:0; }
th{ background:#fff; border-bottom:1.5px solid #000; }
.cover .rule{ background:#000; }
.foot{ border-top:1px solid #000; }
</style>"""

TAKEAWAYS = [
    ("Audio is the whole product, not a feature",
     "Every book page opens on a player: chapters, 15-second skips, speed, sleep timer, download and a synced "
     "transcript. Ochorus has a fine reader with text-to-speech attached. The lesson is that listening deserves "
     "first-class surfaces — a Listen page, a mini-player, a Downloads list — not a button inside the reader."),
    ("One text, packaged three ways",
     "Each book feeds the library, a community quote feed and an “Articles &amp; Excerpts” blog of chapters "
     "retitled with magazine headlines (“The Christmas Pudding That Made an Atheist Believe” is a Mildred Cable "
     "chapter). Ochorus already has quotes and Articles; the gap is headline craft and volume."),
    ("Everything works signed out",
     "Favorites, bookmarks, quotes, history and preferences live on the device under a plain “saved to your "
     "device — no account needed”. Sign-in only unlocks cross-device stats. The free promise is stated, not implied: "
     "“172 audiobooks — all free, forever. No subscription needed.”"),
    ("Missionary biography is the lead genre",
     "Roughly a third of the shelf is biography, and the Region topics — China, India, Congo, Sierra Leone, Nepal, "
     "Mongolia — do heavy lifting on the home page. That validates the African voices push and argues for Region "
     "as a browsing dimension of its own."),
]

# (title, body, status) — status: have | part | new
LESSONS = {
    "Discovery and browsing": [
        ("Duration on every card", "“4h 16m” tells the listener what they are committing to before they tap. "
         "Ochorus cards show reading time; keep it, and add it to sermon and plan cards where it is missing.", "have"),
        ("Continue Listening first", "A returning visitor sees a Continue strip above everything else, with the cover "
         "and chapter. Ochorus does this for reading; the listen position should resume the same way.", "part"),
        ("Recent Additions as the lead row", "First row on the home page, with a “Browse all, newest first” link. "
         "Ochorus adds works weekly and only exposes that in the RSS feed and admin.", "new"),
        ("Trending this week", "A row driven by real play counts. Ochorus has progress data to do the same for "
         "“most read this week”.", "new"),
        ("Topics in parent groups", "53 topics sit under eight groups — Spiritual Disciplines, Missions, Doctrine, "
         "Region — each chip carrying a count. Ochorus topics are one flat list.", "new"),
        ("Region as a topic dimension", "Africa, China, India, Japan and Mongolia each get a page. Ochorus has the "
         "content for Africa, Uganda and Tanzania pages already.", "new"),
        ("Author list with dates and counts", "Life dates, a book count, an A-to-Z rail and three sort orders "
         "(name, most books, most listened), led by a Prolific Authors row.", "part"),
        ("A century timeline of authors", "The Authors page links a Church History Timeline. Theirs is broken; "
         "Ochorus already has an era strip on Biographies and spans Ignatius to Müller. Promote it.", "part"),
        ("More like this, ten deep", "Related titles on every book page with a Load More. Ochorus shows related "
         "works; the list is short.", "part"),
        ("Category plus hashtag topics", "One category and clickable #topics on the book page, both leading to "
         "browse pages.", "have"),
    ],
    "Reading and listening": [
        ("Tap a line to seek", "Read Along shows the transcript; tap any line and the audio jumps there. Ochorus "
         "text-to-speech follows the spoken paragraph; tapping a paragraph should start speech from it.", "part"),
        ("Long-press to quote", "Quote capture lives inside the transcript, not on a separate page. A long-press on "
         "any line opens “Save quote from here”.", "part"),
        ("Sleep timer, skip interval, chapter buttons", "All present and all configurable; the skip interval is a "
         "setting (5 to 60 s). Ochorus has the sleep timer; add the skips and a chapter step.", "part"),
        ("A visible Download", "A Download button per book and a Downloads page make the offline promise concrete. "
         "Ochorus caches through the service worker but never says so.", "part"),
        ("Persistent mini-player", "On mobile the player pins above the tab bar and survives navigation. Ochorus "
         "has a listen bar inside the reader only.", "part"),
        ("Live font-size preview", "The Read Along font setting shows a sample quote at the chosen size. Ochorus’ "
         "Aa panel previews already; extend it to the listen transcript.", "have"),
    ],
    "Quotes and sharing": [
        ("Community quotes with counts", "The home page shows quotes with save and share counts. Ochorus has "
         "curated author quote pages; a community feed with reactions is the next step.", "part"),
        ("Configurable quote images", "Include a link back, include the title, wrap in quotation marks. Ochorus’ "
         "share card is fixed; three toggles would cover most asks.", "part"),
        ("An “example output” preview", "Under the quote settings sits a rendered example, so people see the "
         "share before they share.", "new"),
        ("My Data, listed", "A section that names what you own — favorites, bookmarks, saved quotes, stats — with a "
         "note that it stays on the device.", "new"),
    ],
    "Content strategy": [
        ("Blurbs written as invitations", "Every page opens with a one-paragraph hook, then a longer About behind "
         "Read more. Ochorus descriptions are catalogue copy.", "new"),
        ("Chapters retitled as articles", "Their Articles are chapters with headlines. Ochorus Articles shipped this "
         "month; mine existing chapters the same way before writing new pieces.", "part"),
        ("A “From the book” badge", "Articles drawn from a book carry a badge linking back to the chapter, so the "
         "article sells the book.", "new"),
        ("Printed Books page", "Every title paired with where to buy a physical copy, ranked by popularity. Check "
         "affiliate terms; goodwill links are fine.", "new"),
        ("Syndicate the audio", "“Available on YouTube and Spotify” on each book, linking back. Ochorus TTS audio "
         "could be published the same way once voices are good enough.", "new"),
        ("Show the published year", "“Published 1936” under the author. Ochorus has the field and emits it only in "
         "structured data; put it on the page.", "part"),
    ],
    "Product and trust": [
        ("Customisable tab bar and player", "Pick up to five mobile tabs and four player actions, drag to reorder. "
         "Ambitious; the memorable part is that the player row is user-chosen.", "new"),
        ("Push for new books", "Opt-in push for new additions, with a clear “blocked by browser, tap the lock icon” "
         "when denied.", "new"),
        ("Free, forever, said out loud", "A banner that says free with no subscription, and a Donate link beside "
         "About. Ochorus says free in the tagline only.", "part"),
        ("A useful 404", "The not-found page lists recent audiobooks and recent articles instead of a dead end.", "new"),
    ],
}

BETTER = [
    ("Multilingual", "Scroll Reader is English only. Ochorus’ per-language editions and review badges have no equivalent."),
    ("Author biographies", "Their author page is a name, an initial and a cover grid. Ochorus bio pages carry 1,500-word lives, dates and quotes."),
    ("Reading plans", "Nothing comparable on Scroll Reader."),
    ("Prerendered pages", "Book and author pages are client-rendered; a slug with an apostrophe, the About page and the "
     "timeline link all returned Not Found or a blank shell. Ochorus prerenders and gates fixtures in CI."),
    ("Designed covers", "Their covers are AI paintings, attractive but uniform. Ochorus hand-made covers are frozen by rule."),
    ("Typography for reading", "Their transcript is a utility panel. Ochorus is a reader first: drop caps, measure, margins."),
]

TOP5 = [
    ("Recent Additions and Most Read rows on the home page",
     "Two list endpoints ordered by created date and by reading events in the last seven days; two rows under "
     "Continue Reading. A day of work, and it makes weekly imports visible."),
    ("Tap-to-speak and long-press-to-quote in the reader",
     "While speech is playing, tapping a paragraph restarts speech from it; a long-press opens the existing quote "
     "card pre-filled. Both hang off code that already exists in listen.svelte.ts and the share card."),
    ("Region as a topic group, and grouped topics",
     "Add a group field to Topic (Discipline, Doctrine, Missions, Region, Life), render the topics page as grouped "
     "chips with counts. Region pages for Africa, Uganda and Tanzania land with the African voices work."),
    ("Article headlines mined from existing chapters",
     "Pick twenty chapters with a story in them, give each a headline and a two-sentence hook, publish as Articles "
     "with a “From the book” link back. Content only; no code beyond the badge."),
    ("Say what is free and what is saved",
     "A one-line “Free, forever, no subscription” on the home page, a visible Download on the book page, a My Data "
     "block in settings, and the published year on the book page. Copy and small components."),
]

STATUS_LABEL = {"have": "Have", "part": "Partial", "new": "New"}


def lesson_html(n: int, title: str, body: str, status: str) -> str:
    return (f'<div class="les"><div class="n">{n}</div><div><b>{esc(title)}</b>'
            f'<span class="st {status}">{STATUS_LABEL[status]}</span> {body}</div></div>\n')


def render() -> str:
    p = [head_from_ideas(), EXTRA_STYLE, "</head><body>\n"]

    # Page 1 — title block, what it is, four takeaways
    p.append(
        '<div class="cover">\n  <div class="mark">OCHORUS</div>\n  <div class="rule"></div>\n'
        '  <h1>Thirty Lessons from Scroll Reader</h1>\n'
        '  <div class="sub">What an audio-first library of the same classics gets right, what Ochorus already does '
        'better, and five things to act on</div>\n'
        '  <div class="meta"><span class="tag">Competitive notes · scrollreader.com · September 2026</span></div>\n</div>\n'
    )
    p.append(
        '<section class="intro">\n  <h2>What Scroll Reader is</h2>\n'
        '  <p>A free library of 172 public-domain Christian audiobooks by 111 authors — Bounds, Miller, Murray, '
        'Müller, Bunyan, Brooks, Watson, Flavel, Taylor, Paton, Carmichael — narrated in-house and distributed on the '
        'site, YouTube and Spotify. English only, no biographies, no plans, client-rendered. The overlap with the '
        'Ochorus shelf is large, which makes it a useful mirror: same books, opposite bet. They bet on the ear; we '
        'bet on the page and the world’s languages.</p>\n'
        '  <h2 style="margin-top:12px">Four big takeaways</h2>\n'
    )
    for i, (h, body) in enumerate(TAKEAWAYS, 1):
        p.append(f'  <div class="take"><div class="num">{i}</div><div>\n    <h3>{h}</h3>\n    <p>{body}</p>\n  </div></div>\n')
    p.append(
        '  <div class="callout">\n    <span class="k">The mirror</span>\n'
        '    Where they are strong — listening, packaging, plain promises — Ochorus is adequate. Where Ochorus is '
        'strong — languages, biographies, plans, typography, prerendering — they are absent. Borrow the first list; '
        'do not trade away the second.\n  </div>\n</section>\n'
    )

    # Pages 2–3 — the thirty lessons
    groups = list(LESSONS.items())
    page2 = groups[:2]
    page3 = groups[2:]
    n = 1
    for page_groups, heading, lede in (
        (page2, "The thirty lessons, part one",
         "Discovery and the listening surface. Each carries a status against the current Ochorus build."),
        (page3, "The thirty lessons, part two",
         "Quotes, content packaging and the small trust signals."),
    ):
        p.append(f'<section class="page">\n  <h2>{heading}</h2>\n  <p class="lede">{lede}</p>\n'
                 '  <p class="key"><span class="st">Have</span> Ochorus does this already &nbsp; '
                 '<span class="st part">Partial</span> a version exists, theirs goes further &nbsp; '
                 '<span class="st new">New</span> nothing comparable yet</p>\n')
        for grp, items in page_groups:
            p.append(f'  <div class="grp">{esc(grp)}</div>\n  <div class="two">\n')
            for title, body, status in items:
                p.append("    " + lesson_html(n, title, body, status))
                n += 1
            p.append('  </div>\n')
        p.append('</section>\n')
    assert n == 31, n

    # Page 4 — what Ochorus does better, top five
    p.append('<section class="page">\n  <h2>What Ochorus already does better</h2>\n'
             '  <p class="lede">Worth naming, so the borrowing does not become imitation.</p>\n'
             '  <table><tr><th>Strength</th><th>On Scroll Reader</th></tr>\n')
    for k, v in BETTER:
        p.append(f'    <tr><td class="k">{esc(k)}</td><td>{v}</td></tr>\n')
    p.append('  </table>\n  <h2 style="margin-top:10px">Five to act on</h2>\n'
             '  <p class="lede">Ordered by value per day of work. Each is one branch and one PR.</p>\n')
    for i, (h, body) in enumerate(TOP5, 1):
        p.append(f'  <div class="take"><div class="num">{i}</div><div>\n    <h3>{h}</h3>\n    <p>{body}</p>\n  </div></div>\n')
    p.append('  <div class="callout">\n    <span class="k">Not to copy</span>\n'
             '    The customisable tab bar, push notifications and the Printed Books page are real work for marginal '
             'return on a reading site. Note them; do not schedule them.\n  </div>\n'
             '  <div class="foot">OCHORUS · THIRTY LESSONS FROM SCROLL READER · PREPARED WITH CLAUDE</div>\n'
             '</section>\n</body></html>\n')
    return "".join(p)


def main() -> None:
    OUT_HTML.write_text(render(), encoding="utf-8")
    print("wrote", OUT_HTML, f"({OUT_HTML.stat().st_size // 1024} KB)")
    if not Path(CHROME).exists():
        sys.exit(f"Chrome not found at {CHROME}; open {OUT_HTML} and print to PDF")
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri()],
        check=True, capture_output=True,
    )
    print("wrote", OUT_PDF, f"({OUT_PDF.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
