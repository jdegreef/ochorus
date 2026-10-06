#!/usr/bin/env python
"""Generate the Admin Manual PDF — the super-admin's guide to the whole console.

The manual is served to super admins from the account menu
(``AdminManualView`` → ``library/assets/admin-manual.pdf``). Version 1.0 was
rendered by hand outside the repo, so it could not be refreshed when the admin
moved on; this script makes it reproducible like its sibling
(``build_language_admin_manual.py``, whose brand CSS, logo and Chrome lookup it
reuses):

  * the content lives in this script (``build_html`` below),
  * the screenshots are committed under ``library/assets/manual/admin/`` —
    captured from a local admin running against the committed fixture plus a
    few sample readers, grants, feedback items and emails,
  * rendering is headless Chrome, so the page carries the brand type and logo.

Regenerate after editing the content or the screenshots:

    cd backend && uv run python scripts/build_admin_manual.py

Chrome is found at ``$CHROME`` or the usual install paths. When the admin
changes, update the chapter that describes it (and its screenshot) here —
the PDF is an output, never edited directly.
"""

from __future__ import annotations

import base64
import os
import subprocess
import tempfile
from pathlib import Path

from build_language_admin_manual import CSS as BASE_CSS
from build_language_admin_manual import LOGO_SYMBOL, find_chrome

ROOT = Path(__file__).resolve().parent.parent  # backend/
ASSETS = ROOT / "library" / "assets"
SHOTS = ASSETS / "manual" / "admin"
OUT = ASSETS / "admin-manual.pdf"

VERSION = "2.0"
UPDATED = "October 2026"

CSS = (
    BASE_CSS.replace(
        "Ochorus — Language Administrator's Manual", "Ochorus — Admin System Manual"
    )
    + """
/* Named pages (`page: cover`) print the cover onto page 2, over the contents,
   in current headless Chromium; `:first` does the same job without the bug. */
@page :first { margin:0; @bottom-left{content:none;} @bottom-right{content:none;} }
.cover { page:auto; }
.toc .part { font-family:var(--sans); font-weight:700; letter-spacing:2pt; text-transform:uppercase;
  font-size:7.5pt; color:var(--muted); margin:4mm 0 0; padding:0; border:none; display:block; }
.toc .part::before { content:none; }
.toc li.part, .toc li.app { counter-increment:none; }
.toc li.app::before { content:attr(data-n); }
.toc ol { margin-top:2mm; columns:2; column-gap:9mm; }
.toc li { break-inside:avoid; }
.toc .part:first-child { margin-top:0; }
h3, h4 { break-after:avoid; }
.toc li { padding:0.55mm 0; gap:2.5mm; }
.toc { padding-top:0; }
.toc li::before { width:7mm; font-size:10.5pt; }
.toc li .d { font-size:7.8pt; }
.toc h2 { margin-bottom:0; }
.toc li .t { font-size:10.5pt; }
.toc li .d { margin-top:0; }
.shot img { max-height:158mm; object-fit:cover; object-position:top; }
.shot.half img { max-height:105mm; }
.pair { display:grid; grid-template-columns:1fr 1fr; gap:5mm; align-items:start; }
.access { font-size:9pt; color:var(--muted); border-top:1px solid var(--border); padding-top:2.5mm; margin-top:5mm; }
.access strong { color:var(--accent); }
code, .k { font-family:ui-monospace,Menlo,monospace; font-size:8.6pt; background:#f3ecdb; border:1px solid var(--border);
  border-radius:3px; padding:0 1.2mm; color:var(--ink-strong); }
.new { display:inline-block; font-family:var(--sans); font-weight:700; font-size:6.5pt; letter-spacing:1pt;
  text-transform:uppercase; color:#fff; background:var(--gold); border-radius:2px; padding:0.3mm 1.4mm; vertical-align:2pt; margin-left:2mm; }
.chapter .num .app { color:var(--gold); }
"""
)


def shot(name: str) -> str:
    """A committed screenshot as a data URI, so the render has no file deps."""
    data = base64.b64encode((SHOTS / f"{name}.jpg").read_bytes()).decode()
    return f"data:image/jpeg;base64,{data}"


def figure(name: str, caption: str, cls: str = "") -> str:
    return (
        f'<figure class="shot {cls}"><img src="{shot(name)}" alt="">'
        f"<figcaption>{caption}</figcaption></figure>"
    )


def opener(label: str, title: str, new: bool = False) -> str:
    badge = '<span class="new">New</span>' if new else ""
    return (
        '<div class="opener"><div class="num">'
        '<svg class="mk"><use href="#mark"/></svg> '
        f"{label}</div><h2>{title}{badge}</h2></div>"
    )


def access(text: str) -> str:
    return f'<p class="access">Access: {text}</p>'


def callout(kind: str, tag: str, body: str) -> str:
    return (
        f'<div class="callout {kind}"><span class="tag">{tag}</span><p>{body}</p></div>'
    )


# (part, [(title, subtitle)]) — the contents page, in chapter order.
TOC = [
    (
        "Getting oriented",
        [
            (
                "Welcome to the admin",
                "What this room is for — and what changed in this edition",
            ),
            (
                "How content reaches readers",
                "The one idea that explains every workflow",
            ),
            (
                "Access levels at a glance",
                "Capabilities, verbs, roles and language scope",
            ),
            (
                "Signing in & finding your way",
                "The navigation rail and the account menu",
            ),
        ],
    ),
    (
        "The daily surfaces",
        [
            ("The dashboard", "The snapshot you open every day"),
            ("Needs attention & worklists", "Turning signals into action"),
            ("Coverage matrix", "Work × language, and queueing the gaps"),
            ("Language health", "One score per language, ranked"),
        ],
    ),
    (
        "Building the library",
        [
            ("Importing a document", "From a file to a published work"),
            ("The book page", "Publishing, reader drop-off, and fixing titles & text"),
            ("The sermon page", ""),
            ("The content-edit queue", "Titles, body text, audit fixes & biographies"),
            ("Authors & biographies", ""),
        ],
    ),
    (
        "Reviewing & quality",
        [
            ("The review queue", "Lanes, verse checks and maker–checker"),
            ("Content audit", "Integrity, quality, the nightly scan and the fix queue"),
            ("Reader feedback", "Triage what readers and language admins send in"),
            (
                "Search analytics & demand",
                "Reading — and answering — what readers can't find",
            ),
            ("Engagement analytics", ""),
            ("The activity log", "Every change, and the translation-job tracker"),
        ],
    ),
    (
        "Languages",
        [
            ("Administering a language", "Readiness, the bar, settings & going live"),
            ("Adding a new language", ""),
        ],
    ),
    (
        "Readers & email",
        [
            (
                "Users & reader profiles",
                "The directory, one reader's page, writing to a reader",
            ),
            ("Email health", "How lifecycle email and broadcasts are landing"),
            (
                "Composing a broadcast",
                "Audience, blocks, checks, translation and sending",
            ),
            ("Automated emails", "What goes out on its own, and when"),
        ],
    ),
    (
        "People & access",
        [
            ("Team & access", "Granting, changing and removing admin access"),
            ("Help & roles page", ""),
        ],
    ),
]
APPENDICES = [
    ("A", "Capability & verb reference"),
    ("B", "What the activity log records"),
    ("C", "Glossary"),
    ("D", "Troubleshooting & FAQ"),
]


def toc_html() -> str:
    items = []
    n = 0
    for part, chapters in TOC:
        items.append(f'<li class="part">{part}</li>')
        for title, sub in chapters:
            n += 1
            d = f'<div class="d">{sub}</div>' if sub else ""
            items.append(f'<li><span><span class="t">{title}</span>{d}</span></li>')
    items.append('<li class="part">Reference</li>')
    for letter, title in APPENDICES:
        items.append(
            f'<li class="app" data-n="{letter}"><span><span class="t">{title}</span></span></li>'
        )
    return "\n".join(items)


def chapter_label(n: int) -> str:
    part = next(p for p, ch in _numbered() if n in ch)
    return f"Chapter {n} · {part}"


def _numbered():
    n = 0
    for part, chapters in TOC:
        nums = list(range(n + 1, n + 1 + len(chapters)))
        n += len(chapters)
        yield part, nums


def ch(n: int, title: str, body: str, new: bool = False) -> str:
    return f'<section class="chapter">{opener(chapter_label(n), title, new)}\n{body}\n</section>'


def app(letter: str, title: str, body: str) -> str:
    return f'<section class="chapter">{opener(f"Appendix {letter} · Reference", title)}\n{body}\n</section>'


def build_html() -> str:
    chapters = [
        ch(
            1,
            "Welcome to the admin",
            f"""
<p class="lead">The admin is the room where the Ochorus library is built, reviewed, and taken live.
Everything a reader eventually sees — a new translation, a fixed chapter title, a biography, a
language going live, an email in their inbox — begins here.</p>
<p>Ochorus is a free reader for public-domain Christian classics, offered in many languages across
the web and mobile. The public site is deliberately simple: a reader opens a book and reads. All of
the judgement behind that simplicity — which works to carry, which translations are trustworthy,
which languages are ready to advertise, what to say to readers — lives in the admin console at
<code>/admin</code>.</p>
<p>This manual walks through every screen and every workflow, in the order you are likely to need
them. Each chapter stands on its own, opens with a screenshot of the screen it describes, and ends
with the access it needs.</p>
{callout("gold", "The core idea", "The public site is built ahead of time from the project's source files, not edited live. So most changes to what a reader <em>reads</em> are not instant database edits — you file a job, and it ships as a reviewed change on the next build. A few things are immediate: publishing or unpublishing an edition, recording a review decision, search synonyms and pins, and sending email. Those are the levers gated most tightly.")}
<h3>What changed since version 1.0</h3>
<p>The admin has grown a great deal since September. The headline changes:</p>
<ul>
  <li><strong>Email.</strong> Three new rail sections — <em>Emails</em> (delivery health),
    <em>Compose email</em> (broadcasts with a block editor, pre-send checks and AI translation), and
    a one-to-one <em>Email this reader</em> panel on a reader's page. Chapters 22–25.</li>
  <li><strong>Reader feedback.</strong> A triage queue for suggestions sent from the reader,
    including highlighted-text corrections, with a one-click route into the content-edit queue
    (Chapter 16).</li>
  <li><strong>Super-admin-only levers.</strong> Importing documents, queuing translations, email and
    team management are now reserved for super admins (a founder decision, 21 September). Language
    admins do reader-facing content QA in their languages.</li>
  <li><strong>A richer review queue</strong> — lanes, per-verse checks, mechanical checks, bulk
    approval of the clean lane, and an approve button that waits until you have scrolled to the end
    (Chapter 14).</li>
  <li><strong>The content audit</strong> now runs nightly, emails the super admins when a new
    integrity defect appears, sends quality findings straight to the fix queue, and shows where
    readers stop (Chapter 15).</li>
  <li><strong>Search triage</strong> — answer an unanswered search with a synonym, a pinned result, a
    queued translation, or mark it wanted / out of scope (Chapter 17).</li>
  <li><strong>Coverage, language health, team and activity</strong> were all reworked; their
    chapters are rewritten throughout.</li>
</ul>
{callout("indigo", "A note on the screenshots", "Every screen is captured from a local copy of the admin running against the real library fixture, plus a handful of invented readers, team members, feedback items and emails (all at example.com). Counts are illustrative; layout, controls and wording are the real thing.")}
""",
        ),
        ch(
            2,
            "How content reaches readers",
            f"""
<p class="lead">One idea shapes almost every workflow in the admin. Spend two minutes here and the
rest of the manual will feel obvious.</p>
<h3>The site is pre-built, not live</h3>
<p>The reader at ochorus.com is a set of pages generated in advance from the project's committed
source files (its "fixtures"). That makes the site fast, cheap to serve and reliable. The trade-off
is that a change to a book's words does not appear the moment someone edits a database row —
nothing would notice, and the pre-built page would never be regenerated.</p>
<h3>So prose changes ship as jobs</h3>
<p>When you want to change something a reader reads — a chapter title, a paragraph of text, a
translation, an author biography — the admin does not edit it in place. It <strong>files a
job</strong>: a tracked GitHub issue that a person, usually working with an assisted workflow, turns
into a proper source change, reviewed and shipped on the next build. You will see this pattern in
several places:</p>
<ul>
  <li><strong>Translate / Queue</strong> on the coverage matrix, a language page or the search screen
    files a <em>translation job</em>.</li>
  <li><strong>Fix title</strong> and <strong>Flag text</strong> on a book page,
    <strong>send to fix queue</strong> on the content audit, <strong>File as content-edit job</strong>
    on a feedback item and <strong>Request bio</strong> on the authors worklist file a
    <em>content-edit job</em>.</li>
  <li><strong>Draft with AI</strong> in the email composer files a translation job for an email's
    words.</li>
</ul>
<p>Filing a job changes nothing on its own. It queues work — which is exactly why a contributor can
be trusted to file one without being able to alter the live site.</p>
<h3>What is immediate</h3>
<table><tr><th>Lever</th><th>Effect</th></tr>
<tr><td>Publish / unpublish an edition</td><td>Shows or hides it in the reader's API at once; the
pre-built pages catch up on the next (throttled) rebuild.</td></tr>
<tr><td>Confirm a review decision</td><td>Promotes an AI translation to reviewed in every admin
report. (Readers never see review state.)</td></tr>
<tr><td>Search synonyms and pinned results</td><td>Change what a search returns straight away.</td></tr>
<tr><td>Send an email</td><td>A direct email goes immediately; a broadcast starts on the next email
run (every 15 minutes).</td></tr>
<tr><td>Take a language live</td><td>Records the launch and triggers a rebuild — the language appears
once the build has shipped.</td></tr>
<tr><td>Grant or remove admin access</td><td>Takes effect on the person's next request.</td></tr>
</table>
{callout("gold", "Why it's built this way", "Every prose change becoming a reviewable job is a feature, not friction: nothing reaches a reader without a record of who changed what and why. The production site holds no content-authoring credentials, so there is no way to quietly rewrite a live page.")}
<h3>A word on AI translations</h3>
<p>Ochorus uses AI to draft translations but never treats one as finished on its own. A fresh AI
translation ships <em>unreviewed</em> and waits in the review queue (Chapter 14) until a person
approves it. This review state is <strong>admin-only</strong>: there is no public "awaiting review"
or AI-translation badge, by design. Quality is handled here, not by warning the reader.</p>
""",
        ),
        ch(
            3,
            "Access levels at a glance",
            f"""
<p class="lead">Ochorus grants admin access in graduated levels, so you can invite help without handing
over the keys. Every grant pairs an <em>area</em> with <em>how far</em> you can go in it, and is scoped
to one or more languages.</p>
<h3>The two dimensions</h3>
<p>A grant pairs a <strong>capability</strong> (an area of the admin, such as review or publishing)
with a <strong>verb</strong>. The verbs form a ladder — each includes the ones below it:</p>
<table><tr><th>Verb</th><th>What it lets you do</th></tr>
<tr><td><strong>View</strong></td><td>See the reports and queues in an area.</td></tr>
<tr><td><strong>Suggest</strong></td><td>File a job; apply nothing to the live site yourself.</td></tr>
<tr><td><strong>Act</strong></td><td>Apply changes: record a review decision, publish an edition,
triage feedback.</td></tr>
<tr><td><strong>Approve</strong></td><td>Confirm other people's work, and pull the high-privilege
levers.</td></tr></table>
<h3>The roles</h3>
<p>Most people are given a <strong>role</strong> — a bundle of grants — rather than hand-picked ones.
You choose the languages when you grant it.</p>
<table class="cando"><tr><th>Role</th><th>Can</th></tr>
<tr><td>Contributor</td><td>Views the library and its queues; files fixes to titles and text
(content-edit jobs). Applies nothing live.</td></tr>
<tr><td>Reviewer</td><td>Everything a contributor can, plus records review decisions in their
languages — provisionally, until an approver confirms (Chapter 14).</td></tr>
<tr><td>Language admin</td><td>Runs their languages: publishes and unpublishes editions, confirms
reviews, triages feedback, accepts audit findings, files fixes. Sees a language's readiness but
cannot change its bar, its settings, or take it live. No user data, no email.</td></tr>
<tr><td>Super admin</td><td>Everything, in every language — including importing, queuing
translations, email, user analytics, granting access and taking a language live.</td></tr></table>
{callout("indigo", "Language scope", "Every grant below super admin names its languages (or “all languages, including ones added later”). A reviewer for Swahili sees only Swahili in their queues and has no reach into Spanish unless separately granted. Reader feedback with no language goes to super admins only.")}
{callout("gold", "Where super admins come from", "Super admins are defined by the <code>ADMIN_EMAILS</code> allowlist in the deploy environment, outside the grant system — so nobody can accidentally revoke the last one. A grant (and the allowlist) only counts for a signed-in account whose email is verified.")}
<p>The exact bundles are in Appendix A.</p>
""",
        ),
        ch(
            4,
            "Signing in & finding your way",
            f"""
<p class="lead">You reach the admin at <code>/admin</code> once you are signed in with an account that
holds any access. Everything hangs off a single left-hand rail.</p>
<h3>The navigation rail</h3>
<p>The rail is capability-aware: it lists only what your access opens. Its heading reads
<em>Admin</em> for a super admin and <em>Language Admin</em> for everyone else. In order:</p>
<table><tr><th>Section</th><th>Needs</th></tr>
<tr><td>Dashboard · Coverage matrix · Language health · Activity · Engagement · Search</td><td>Reporting</td></tr>
<tr><td>Import document</td><td>Super admin</td></tr>
<tr><td>Review queue</td><td>Content review</td></tr>
<tr><td>Feedback</td><td>Reader feedback</td></tr>
<tr><td>Content audit</td><td>Content audit</td></tr>
<tr><td>Emails · Compose email</td><td>Super admin</td></tr>
<tr><td>Users</td><td>User analytics</td></tr>
<tr><td>Team &amp; access</td><td>Super admin</td></tr>
<tr><td>Help &amp; roles</td><td>Any admin access</td></tr></table>
<p>Book, sermon and language pages are not in the rail — you reach them from the dashboard, the
coverage matrix and the worklists. <strong>← View site</strong> sits at the foot of the rail (on
phones the rail becomes a scrolling row of pills).</p>
<h3>The account menu</h3>
<p>The avatar in the top-right opens the account menu. Anyone with access sees a link to the admin.
Super admins also see <strong>Admin Manual PDF</strong> — this document. Other admins see
<strong>Language Admin Manual PDF</strong>, the shorter handbook written for them. Both open in the
browser's PDF viewer.</p>
{callout("gold", "Tip", "Not sure why someone can't see a section? Send them to <strong>Help &amp; roles</strong> (Chapter 27): it lists their exact access and says, for every missing section, what it needs.")}
""",
        ),
        ch(
            5,
            "The dashboard",
            f"""
<p class="lead">The dashboard is the snapshot you open every day: what the library contains, how it
breaks down by language, and what needs you now.</p>
{figure("dashboard", "Figure 5.1 — The content dashboard: the attention hub and chips, headline totals, and the per-language breakdown.")}
<h3>What you're looking at</h3>
<ul>
  <li><strong>Needs attention</strong> — a ranked hub of what to act on (Chapter 6).</li>
  <li><strong>Chips</strong> — amber shortcuts to the worklists behind the biggest signals:
    unpublished books and sermons, unreviewed AI translations, authors without a bio, empty
    chapters.</li>
  <li><strong>Headline totals</strong> — works, books (and how many are published), chapters, words
    (with reading hours), sermons, plans, authors (and how many have a bio), languages with
    content.</li>
  <li><strong>By language</strong> — books, chapters, sermons, plans, bios, articles and words per
    language, and a <em>Source</em> column. Click a row to open that language's page (Chapter 20).
    Super admins get <strong>+ Add a language</strong> beneath it (Chapter 21).</li>
  <li><strong>Books by source</strong> and <strong>Recently added books</strong>.</li>
</ul>
{callout("indigo", "Reading the source column", "<strong>PD</strong> is public domain (the originals). <strong>AI·</strong> marks AI translations not yet reviewed; <strong>AI✓</strong> those a person has confirmed; a gold <strong>+N</strong> is work queued to translate. A language sitting on a pile of AI· is your cue to open the review queue for it.")}
<h3>Exporting</h3>
<p><strong>Export CSV</strong> downloads an inventory of every book, sermon and plan edition (slug,
language, title, author, source, published, chapters or days, words, source URL);
<strong>Export JSON</strong> adds the authors. <strong>Refresh</strong> re-pulls the figures.</p>
{access("<strong>Reporting · View</strong>, which every role includes.")}
""",
        ),
        ch(
            6,
            "Needs attention & worklists",
            f"""
<p class="lead">The attention hub turns raw counts into a ranked to-do list, and each signal links to
a worklist you can act on.</p>
<h3>How it ranks</h3>
<p>The hub gathers signals that otherwise live one per page and orders them by reader impact:</p>
<ol class="steps">
  <li><strong>Empty chapters</strong> and <strong>books with no chapters</strong> — integrity
    defects readers hit (→ content audit). When both are zero, a single line says
    <em>Data integrity is clean</em>.</li>
  <li><strong>AI translations awaiting review</strong> (→ review queue).</li>
  <li><strong>Searches that found nothing</strong> in the last 30 days, with their share of all
    searches (→ search).</li>
  <li><strong>A live language with no books</strong> (→ that language's page).</li>
</ol>
<p>An <em>Also:</em> line lists the quieter items — unpublished books and sermons, authors without a
bio. When nothing applies, it says so.</p>
<h3>The worklists</h3>
<div class="pair">
{figure("unpublished", "Figure 6.1 — Books and sermons that aren't live, each with “Publish →”.", "half")}
{figure("authors-without-bio", "Figure 6.2 — Authors with no biography, most works first, each with “Request bio”.", "half")}
</div>
<p>The unpublished list links each work to its admin page, where the publish toggle lives (Chapters
10–11). The authors list excludes imprints and ranks people by how many works they carry; its
<strong>Request bio</strong> button files a biography job (Chapter 13).</p>
{access("<strong>Reporting · View</strong>.")}
""",
        ),
        ch(
            7,
            "Coverage matrix",
            f"""
<p class="lead">The coverage matrix shows which works exist in which languages, where the gaps are,
and which translations have fallen behind their English — and lets a super admin queue the gaps.</p>
{figure("coverage", "Figure 7.1 — Works down the side, languages across; summary cards and lens chips on top.")}
<h3>Reading the grid</h3>
<p>Tabs switch between <strong>All</strong>, Books, Sermons, Plans, Biographies and Articles. Each
cell shows the state of that work in that language:</p>
<table><tr><th>Mark</th><th>Means</th></tr>
<tr><td>PD · ●</td><td>Original / present.</td></tr>
<tr><td>AI✓ · AI (gold)</td><td>AI translation, reviewed · still unreviewed. Clicking a gold cell opens
that item in the review queue.</td></tr>
<tr><td>◷ · ◐</td><td>Queued · being translated.</td></tr>
<tr><td>Dashed, empty</td><td>Missing. A number inside is readers asking for it.</td></tr>
<tr><td>Red ↻</td><td>The English has changed since this translation was made.</td></tr>
<tr><td>⊘ · © under copyright</td><td>Blocked — the work cannot be translated or published.</td></tr></table>
<p>Lens chips (Original text, Reviewed, Unreviewed AI, Missing, Queued, English changed, Under
copyright…) highlight one state. The summary cards — <em>Open gaps</em>, <em>Works awaiting review</em>,
<em>Works out of date</em>, <em>In flight</em> — each filter the grid. You can order by priority or
completeness, group by type, author or series, choose which languages show, compact the rows, copy a
link to the current view, and <strong>Download CSV</strong> of it.</p>
<h3>Translate next, and queuing</h3>
<p>The <strong>Translate next</strong> panel ranks open gaps by readers × failed searches, each with a
<strong>Queue</strong> button. Super admins can also click an empty cell to queue it, use
<strong>+N</strong> on a row or column to queue all its gaps, or ⇧-click / ⌘-click to select a range
and <strong>Queue N</strong>. A bulk queue confirms first and shows progress you can stop.</p>
{callout("indigo", "Out-of-date translations (↻)", "When an English text moves on, its translations are marked ↻. If you have checked that the translation still matches — the change was a typo fix, say — <strong>mark still current</strong> re-baselines it and clears the mark (needs Review · Act in that language).")}
{access("viewing, <strong>Reporting · View</strong>; queuing, super admin only.")}
""",
            new=False,
        ),
        ch(
            8,
            "Language health",
            f"""
<p class="lead">The language-health scoreboard distils each language into one 0–100 score and ranks
them, so you can see where an hour of work does the most good.</p>
{figure("language-health", "Figure 8.1 — Each language scored and ranked, with its components, its trend and its next best action.")}
<h3>What the score is made of</h3>
<table><tr><th>Component</th><th>Measures</th><th>Weight</th></tr>
<tr><td>Readiness</td><td>How much of the go-live bar is met (partial credit toward each count).</td><td>35%</td></tr>
<tr><td>Coverage</td><td>The share of the English shelf present — books 50%, sermons 25%, bios 15%,
plans 10%.</td><td>30%</td></tr>
<tr><td>Review</td><td>The share of its translations a person has confirmed.</td><td>20%</td></tr>
<tr><td>Engagement</td><td>Readers in the last 90 days, against a target of 25.</td><td>15%</td></tr></table>
<p>Scores band as <strong>Strong</strong> (75+), <strong>Fair</strong> (45–74) and
<strong>Weak</strong> (under 45). English is shown as the source reference row, not ranked. Summary
tiles count live languages, the median score, items awaiting review and languages blocked from going
live. Each row shows its status (<em>Live</em>, <em>Live · failing…</em>, <em>Ready to launch →</em>, <em>Not
live</em>), an eight-week sparkline with the week's change, and a <strong>Biggest gain</strong> next
action. <em>How the score works</em> expands the detail.</p>
{callout("gold", "How to use it", "A language high on coverage but low on review is a backlog of drafts waiting for a native speaker — a reviewer grant will unlock it. A language with one blocking check is often one push from going live. (The Bible check is skipped here for speed; the language page runs the real one.)")}
{access("<strong>Reporting · View</strong>.")}
""",
        ),
        ch(
            9,
            "Importing a document",
            f"""
<p class="lead">The import screen turns a Word document or text PDF into a structured book or sermon —
parsed, previewed, edited, then published.</p>
{figure("import", "Figure 9.1 — The import screen: type, author, language and document.", "half")}
<ol class="steps">
  <li><strong>Choose book or sermon</strong>, then the <strong>author</strong> — or <strong>+ New
    author</strong> to add a name-only author record.</li>
  <li><strong>Choose the language</strong> the edition is in.</li>
  <li><strong>Choose the document</strong> (.docx or a text PDF, up to 25 MB) and press <strong>Read
    document</strong>. Parsing only builds a preview; nothing is saved. Scanned image PDFs aren't
    supported.</li>
  <li><strong>Edit the preview</strong> — the title, each chapter title, subtitle, first-published year,
    cover accent colour and attribution note for a book; the scripture reference for a sermon; the
    source URL for both.</li>
  <li><strong>Publish book</strong> / <strong>Publish sermon</strong> — or <strong>Start over</strong>.</li>
</ol>
{callout("stop", "Publishing here is immediate", "Unlike most prose changes, an import creates a live, public-domain edition at once and triggers a rebuild. Confirm the work is genuinely public domain and the source is clean first — the parser structures what you give it but cannot rescue a poor scan. Titles on the copyright blocklist are imported unpublished.")}
{access("super admin only (adding an author is logged as <em>Author created</em>).")}
""",
        ),
        ch(
            10,
            "The book page",
            f"""
<p class="lead">Every book has an admin page gathering all its language editions, with the publish
control, a chart of where readers stop, and the fix controls for each chapter.</p>
{figure("book", "Figure 10.1 — A book's admin page: each edition with its source, size, state and publish control, then its chapters.")}
<h3>Each edition</h3>
<p>Each language card shows the edition's title, its source (<em>Public domain</em>, <em>AI ·
reviewed</em>, <em>AI · unreviewed</em>), chapters and words, whether it is <em>live on site</em>, and
links to its source and original PDF.</p>
<h3>Publishing an edition</h3>
<p><strong>Publish</strong> acts in one click. <strong>Unpublish</strong> asks <em>Hide from the
site?</em> first. Either takes effect in the reader's API immediately, and a deploy will not revert it.
Works on the copyright blocklist refuse to publish.</p>
<h3>Where readers stop</h3>
<p>Above the chapter list, a reach curve shows how far readers get through the edition, with the
steepest drop marked — the place to look first for a confusing chapter or a broken split.</p>
<h3>Fixing a chapter</h3>
<ul>
  <li><strong>Fix title</strong> — opens <em>New chapter title</em>, pre-filled. Edit it and
    <strong>Queue fix</strong>; the control confirms with a link to the job (or tells you one is
    already queued).</li>
  <li><strong>Flag text</strong> — asks <em>What's wrong with this chapter's text?</em> and files a job
    for someone to correct the prose.</li>
</ul>
<p>Neither edits the book directly — both file a content-edit job (Chapter 12). Chapter rows also show
any quality flags and are the targets of the audit's <em>Open chapter</em> links.</p>
{callout("gold", "Why a title isn't just editable", "A chapter title is part of the pre-built source and feeds the search index. Filing a job means the source, the live rows and search all move together in one reviewed change.")}
{access("publishing, <strong>Publishing · Act</strong> in the edition's language; fixes, <strong>Content-edit · Suggest</strong>.")}
""",
        ),
        ch(
            11,
            "The sermon page",
            f"""
<p class="lead">Sermons work like books minus the chapters: one document per language.</p>
{figure("sermon", "Figure 11.1 — A sermon's admin page: its language editions, each with its scripture reference and publish control.")}
<p>Each edition shows its source, word count, scripture reference and state, with the same
<strong>Publish</strong> / <strong>Unpublish</strong> control as a book — immediate, and confirmed
before hiding. There are no per-chapter fix buttons; a correction to a sermon's text comes in through
reader feedback or is filed directly as a content-edit job.</p>
{access("<strong>Publishing · Act</strong> in the edition's language.")}
""",
        ),
        ch(
            12,
            "The content-edit queue",
            f"""
<p class="lead">The content-edit queue is the single channel for fixing the words a reader reads.
Every fix filed anywhere in the admin lands here as a GitHub issue labelled
<code>content-edit</code>.</p>
<table><tr><th>Kind</th><th>Filed from</th><th>You provide</th></tr>
<tr><td>Title</td><td>“Fix title” on a chapter row</td><td>The corrected title.</td></tr>
<tr><td>Body</td><td>“Flag text” on a chapter row; “File as content-edit job” on feedback</td><td>A note
on what is wrong (and the reader's suggested text, from feedback).</td></tr>
<tr><td>Audit fix</td><td>“send to fix queue” on the content audit</td><td>Nothing — the job carries
every affected chapter for one check in one edition.</td></tr>
<tr><td>Bio</td><td>“Request bio” on the authors worklist</td><td>An optional note on what to
emphasise.</td></tr></table>
<h3>What happens to a job</h3>
<p>A worker session picks the job up, makes the fix in the project's source files, and ships it as a
pull request; it reaches readers after review and the next build. You need do nothing after filing.
The activity log (Chapter 19) records each filing.</p>
{callout("indigo", "One job per problem", "If a job of the same kind is already open for the same target, filing again returns the existing one. A title fix and a text fix for the same chapter can both be open — they are different work.")}
{access("<strong>Content-edit · Suggest</strong> for the language. The queue needs the server's GitHub token; without it, filing reports that the queue isn't configured.")}
""",
        ),
        ch(
            13,
            "Authors & biographies",
            f"""
<p class="lead">Authors carry the biographies that appear on their pages. The admin finds who is
missing one and files the work to write it.</p>
<ol class="steps">
  <li><strong>Open the worklist</strong> from the dashboard chip (Figure 6.2). It lists every author
    with no biography, excluding imprints, most works first.</li>
  <li><strong>Click Request bio.</strong> Add an optional note (<em>Anything to emphasise?</em>) and
    <strong>Request</strong>.</li>
</ol>
<p>This files a biography job in the content-edit queue. Biography <em>translations</em> are queued
like any other work — from the Biographies tab of the coverage matrix — and reviewed in the review
queue alongside books and sermons. New author records are created from the import screen.</p>
{access("<strong>Reporting · View</strong> to see the list; <strong>Content-edit · Suggest</strong> to request.")}
""",
        ),
        ch(
            14,
            "The review queue",
            f"""
<p class="lead">The review queue is where AI translations become trustworthy. It sorts the work into
lanes, checks the scripture a translator rendered, and runs on a maker–checker principle: one person
proposes, another confirms.</p>
{figure("review", "Figure 14.1 — The review queue: lanes across the top, language tabs, type and sort, then the items.")}
<h3>Lanes and filters</h3>
<table><tr><th>Lane</th><th>Means</th></tr>
<tr><td>Ready to read</td><td>Examined, nothing flagged. Can be bulk-approved.</td></tr>
<tr><td>Verses to check</td><td>Settle each verse the translator rendered.</td></tr>
<tr><td>Not examined</td><td>No scripture notes — read it in full.</td></tr>
<tr><td>Needs work</td><td>Sent back for re-translation.</td></tr></table>
<p>Language tabs, a type filter (book, sermon, author bio) and a sort (waiting longest, fewest verses
left, most unverified, largest first) narrow the queue. Each row shows its verse progress, mechanical
checks (runs short or long, tag sequence, mixed quotes) and how long it has waited.</p>
<h3>Reviewing an item</h3>
<p><strong>Review</strong> opens the text side by side, chapter by chapter, with a <em>Verses to
check</em> list: mark each <strong>Rendering is right</strong> or <strong>Needs work</strong>. The
approve button stays disabled until you have <strong>scrolled to the end of the text</strong>.
<strong>Needs work</strong> asks what needs work and sends the item back.</p>
<h3>Maker–checker</h3>
<p>If you hold review at <em>act</em> (a reviewer), your button reads <strong>Submit for
approval</strong>: the decision is recorded as provisional and nothing changes until someone with
<em>approve</em> (a language admin or super admin) presses <strong>Confirm</strong>. An approver's own
<strong>Approve</strong> applies at once. Only an approver can change a confirmed decision; a reviewer
can still undo their own unconfirmed proposal.</p>
<h3>Bulk approval</h3>
<p><strong>Select N ready on this page</strong> ticks the clean items; <strong>Approve N
selected</strong> applies them. Only the <em>Ready to read</em> lane qualifies — the server re-checks
and holds back anything with unverified verses, with a reason.</p>
{callout("gold", "Readers never see this", "Confirming promotes a translation from AI-unreviewed to reviewed in the coverage, health and readiness reports. It does not change what readers see — there is no public review badge.")}
{access("<strong>Review · View</strong> to see; <strong>Act</strong> to propose; <strong>Approve</strong> to confirm — each in the item's language.")}
""",
        ),
        ch(
            15,
            "Content audit",
            f"""
<p class="lead">The content audit is the library's standing quality report — the structural and
textual defects worth a human's attention — now scanned nightly and wired to the fix queue.</p>
{figure("audit", "Figure 15.1 — The content audit: the scan status, worst books first, data integrity and content quality.")}
<h3>Two kinds of finding</h3>
<p><strong>Data integrity</strong> — broken plan days, books with no chapters, empty chapters,
chapter-order gaps — are defects readers hit. They are marked <em>fix these</em> and cannot be
accepted away.</p>
<p><strong>Content quality</strong> are advisory heuristics that expect false positives, grouped by how
much readers notice: <em>Readers see it</em> (mid-sentence splits, missing drop caps, fragmented
paragraphs, text outside paragraphs), <em>Navigation</em> (generic or missing titles, duplicate titles,
tiny chapters under 150 words) and <em>Probably fine</em> (giant chapters over 8,000 words).</p>
<h3>Acting on a finding</h3>
<ul>
  <li><strong>Open chapter</strong> jumps to the row on the book page.</li>
  <li><strong>send to fix queue</strong> files one audit-fix job for that check in that edition
    (Chapter 12); the button then shows the job's status.</li>
  <li><strong>accept</strong> marks a false alarm as known and removes it; <strong>Undo</strong>
    restores it.</li>
</ul>
<p>Keyboard triage: <span class="k">j</span>/<span class="k">k</span> move,
<span class="k">Enter</span> expands, <span class="k">a</span> accepts, <span class="k">o</span>
opens the chapter. <strong>Worst books first</strong> ranks editions by open flags, and <strong>Readers
stop here</strong> lists the steepest single-chapter drop-offs — a hard chapter, or a broken one.</p>
<h3>The nightly scan</h3>
<p>The audit runs every night; when it finds a <em>new</em> integrity defect it emails the super
admins. The header shows when the last scan ran, whether the alert went out, and when the next is
due. <strong>Re-run</strong> forces a fresh scan.</p>
{access("<strong>Audit · View</strong> to see; <strong>Audit · Act</strong> to accept; filing a fix needs <strong>Content-edit · Suggest</strong>.")}
""",
        ),
        ch(
            16,
            "Reader feedback",
            f"""
<p class="lead">Readers and language admins can send suggestions from anywhere in the reader. The
feedback queue is where they are triaged.</p>
{figure("feedback", "Figure 16.1 — Reader feedback: status chips and filters, then each item with its passage, suggestion and triage controls.")}
<h3>What arrives</h3>
<p>A signed-in reader picks a category — Language / translation, Content, Feature idea, Bug, Other —
and writes a note, from the account menu, the floating feedback button, or by highlighting text.
Each item carries the page, the work, language and chapter, and — for highlights — the selected text
and the reader's suggested replacement. The submitter's role is recorded too, so a language admin's
suggestion stands out.</p>
<h3>Triage</h3>
<ul>
  <li><strong>Status</strong> — new, triaging, planned, in progress, done, declined, duplicate. Saves as
    you change it.</li>
  <li><strong>Assign to me</strong>, and <strong>Add a note…</strong> / <strong>Save note</strong>.</li>
  <li><strong>Open the passage →</strong> deep-links to the exact paragraph.</li>
  <li><strong>File as content-edit job</strong> (book chapters) turns the quote, note and suggestion
    into a body-text job, moves the item to <em>Planned</em> and links the job in the note.</li>
</ul>
<p>“N similar” flags other items about the same passage.</p>
{callout("indigo", "Scoped and masked", "Language admins see only feedback in their languages; feedback with no language goes to super admins. Non-super admins see submitter emails masked.")}
{access("<strong>Feedback · View</strong> to read; <strong>Feedback · Act</strong> to triage, in the item's language.")}
""",
            new=True,
        ),
        ch(
            17,
            "Search analytics & demand",
            f"""
<p class="lead">The search screen shows what readers look for — and lets you answer the searches that
came back empty.</p>
{figure("search", "Figure 17.1 — Search: volume and rates, where searches end, top queries, found-but-not-opened, and unanswered searches by language.")}
<h3>The signals</h3>
<p>Cards show searches, the zero-result rate, how many opened a result, and distinct queries, against
the previous period. <strong>Where searches end</strong> separates a content gap (nothing found) from
a ranking problem (found, but not opened). <strong>Found, but not opened</strong> lists queries whose
results nobody clicked, each with <strong>Pin a result…</strong>.</p>
<h3>Answering an unanswered search</h3>
<table><tr><th>Action</th><th>Effect</th></tr>
<tr><td>Elsewhere?</td><td>Checks other languages for a match and offers <strong>Queue
&lt;Language&gt;</strong> to file the translation (super admin).</td></tr>
<tr><td>Synonym…</td><td>Maps the query to a word that does match — preview, then save. Immediate.</td></tr>
<tr><td>Pin a result…</td><td>Puts the right work at the top for that query. Immediate.</td></tr>
<tr><td>Wanted · Out of scope</td><td>Records the decision so the query leaves the open list.</td></tr></table>
<p>Decided queries move to the <em>Handled</em> or <em>Wanted</em> tab, and <strong>Undo</strong>
reverses any of them.</p>
{callout("indigo", "Anonymous by design", "Search analytics are aggregate: what was searched, never who searched it.")}
{access("statistics, <strong>Reporting · View</strong>; triage, <strong>Translate · Act</strong> in the query's language; queuing a translation, super admin.")}
""",
        ),
        ch(
            18,
            "Engagement analytics",
            f"""
<p class="lead">The engagement screen shows how the library is actually read.</p>
{figure("engagement", "Figure 18.1 — Engagement: the week in one sentence, the pulse, reading time and when people read.")}
<p>Choose a range (7d, 30d, 90d, All) and optionally compare with the period before. The sections:</p>
<ul>
  <li><strong>This week</strong> — a one-sentence summary you can copy.</li>
  <li><strong>Pulse</strong> and <strong>Weekly readers</strong> — active readers and the trend.</li>
  <li><strong>Reading time</strong> — sitting lengths, in sittings or minutes.</li>
  <li><strong>When people read</strong> — a weekday × hour heatmap, the busiest hour and a suggested
    send time.</li>
  <li><strong>Do readers stay?</strong> — weekly cohorts.</li>
  <li><strong>Rising</strong>, <strong>Top content</strong> (books, sermons, authors, articles — with
    a mini chart of where readers stop), <strong>Where readers mark</strong>, <strong>Most
    loved</strong>.</li>
  <li><strong>Plans</strong> — the started → came back → completed funnel per plan.</li>
  <li><strong>By language</strong> — which feeds the engagement part of the health score.</li>
</ul>
{callout("indigo", "Aggregate only", "Engagement reports counts and rollups, never a named reader's activity. Individual readers live under the separate, more sensitive Users capability (Chapter 22).")}
{access("<strong>Reporting · View</strong>.")}
""",
        ),
        ch(
            19,
            "The activity log",
            f"""
<p class="lead">The activity log is the admin's memory: an append-only record of every change made
here — who did what, to what, and when — plus a tracker for the translation jobs in flight.</p>
{figure("activity", "Figure 19.1 — Activity: today's summary, the translation-job tracker, filters, and each action as a row.")}
<h3>Reading the log</h3>
<p>Cards show actions today (and how many were reader-facing), the week's most active admin, the last
go-live and the last publish. Filter by category (language, content, review, translation, author,
access), by admin, or by searching target and detail. A person's or a work's history opens with
<code>?target=</code> — the Team page links straight to it. <strong>Export CSV</strong> downloads what
you are looking at. Appendix B lists every action recorded.</p>
<h3>Translation jobs</h3>
<p>The jobs panel tracks every translation filed: <em>Open</em>, <em>Stalled</em> (claimed but idle 6
hours or more), <em>Closed not shipped</em> (waiting on a merge or deploy) and <em>Need your
approval</em> (shipped, awaiting review). The <em>Job status</em> filter narrows the log to any of
them.</p>
{callout("gold", "Why it exists", "The log is append-only on purpose — nothing edits or deletes a row — which is what makes it worth trusting. It records the actor as plain text so the record survives the account. Non-super admins see other admins' emails masked.")}
{access("<strong>Reporting · View</strong>.")}
""",
        ),
        ch(
            20,
            "Administering a language",
            f"""
<p class="lead">Each language has its own page — what it has, what readers are asking for, its
readiness, its bar, its settings, and the go-live switch.</p>
{figure("language", "Figure 20.1 — A language's page: progress against English, readiness, what readers are asking for, settings and the work to do next.")}
<h3>Readiness</h3>
<p>The checklist a language must pass to go live: <strong>Bible</strong> (a working translation,
verified live), <strong>Bible attribution</strong> (a licensed Bible needs a credit line),
<strong>Glossary</strong> (every theological term defined), <strong>Interface strings</strong>, and
enough <strong>Books</strong>, <strong>Sermons</strong>, <strong>Biographies</strong>, <strong>Reading
plans</strong> and <strong>Topic shelves</strong>. Review state is deliberately not a check.</p>
<h3>The bar for this language</h3>
<p>The counts each language must reach — books, sermons, biographies, plans — plus whether every topic
shelf and the whole interface must be translated. Set 0 to drop a requirement; saving re-checks at
once.</p>
<h3>Going live</h3>
<p><strong>Go live</strong> is enabled when every check is clear. It confirms, re-runs the checks on
the server, records the launch and triggers a rebuild — the language appears once the build ships.
With failing checks you may <strong>launch anyway</strong>, except for hard blockers such as a missing
interface catalogue. Once live, <strong>Has it shipped?</strong> checks the live sitemap.</p>
<h3>The rest of the page</h3>
<ul>
  <li><strong>Readers are asking for</strong> — the top works people read in another language or
    searched for here and didn't find.</li>
  <li><strong>Next to work on</strong>, per type, with <strong>Translate</strong> and <strong>Queue all
    N</strong> buttons (super admin); a queued item becomes a link to its job.</li>
  <li><strong>Translation settings</strong> — Bible code, credit line, names, direction and glossary.
    Languages defined in the project's code are read-only here.</li>
</ul>
{callout("indigo", "The Bible check makes a live call", "Readiness verifies scripture against an external service, so it can take a moment. If that service is unreachable the check reports unknown rather than failing.")}
{access("readiness, <strong>Language admin · View</strong>; the bar and settings, <strong>Act</strong>; going live, <strong>Approve</strong>. Language admins hold only View, so these stay with the super admin.")}
""",
        ),
        ch(
            21,
            "Adding a new language",
            f"""
<p class="lead">A new language begins with a single registry entry; until it exists, nothing can be
translated into it.</p>
<p>Under the dashboard's <em>By language</em> table, <strong>+ Add a language</strong> opens the form.
It suggests likely next languages, and asks for:</p>
<ul>
  <li>the <strong>code</strong> (2–3 letters, optional subtag), English name and native name;</li>
  <li>the <strong>Bible</strong> — its code (verified live) and label;</li>
  <li>a complete <strong>theological glossary</strong>. <em>Copy prompt for Claude</em> gives you a
    prompt to draft one; paste the result back in.</li>
</ul>
<p>A new language is always created as a draft, and appears at once in the by-language table and the
coverage matrix with honest zeros. Then:</p>
<ol class="steps">
  <li><strong>Queue translations</strong> from its page, the coverage matrix or search demand.</li>
  <li><strong>Review the drafts</strong> as they arrive (Chapter 14).</li>
  <li><strong>Add the credit line</strong> and the interface catalogue.</li>
  <li><strong>Tune the bar</strong> and watch the checks clear (Chapter 20).</li>
  <li><strong>Go live.</strong></li>
</ol>
{access("<strong>Language admin · Act</strong> — in practice, a super admin.")}
""",
        ),
        ch(
            22,
            "Users & reader profiles",
            f"""
<p class="lead">The Users section covers the people who read Ochorus — growth, the directory and each
reader's page — under a permission separate from, and more sensitive than, the aggregate
analytics.</p>
{figure("users", "Figure 22.1 — Users: registrations, the funnel from sign-up to habit, and sign-ups per week.")}
<h3>The directory</h3>
<p>Cards and charts show registered, activated and dormant accounts; the funnel <em>Registered →
Activated → Came back another day → Finished something</em>; sign-ups per week; and breakdowns by
sign-in method, where readers started, preferred language, theme, country and timezone. The
<strong>All users</strong> table searches by name or email, sorts by newest, last seen, most active or
name, and exports CSV.</p>
{figure("user-profile", "Figure 22.2 — One reader's page: their totals, reading calendar and what they are reading now.")}
<h3>A reader's page</h3>
<p>Works started and finished, time reading, favourites, highlights, bookmarks, days read and streak;
a reading calendar; what they are reading and have finished; plans, sittings, highlights and notes,
bookmarks and a recent-activity timeline. It is read-only, except for email.</p>
<h3>Writing to one reader</h3>
<p><strong>Email this reader</strong> opens a short form — subject, language, optional heading, message,
optional button — and sends it immediately in the standard layout with the unsubscribe footer. It is
blocked for readers who bounced, complained or unsubscribed from everything. The panel lists the last
50 emails they were sent and how each landed.</p>
{callout("stop", "Personal data — handle with care", "This section shows identifiable people, which is why it has its own capability. Emails are masked on screen until you choose <em>Reveal emails</em>; anyone other than a super admin receives them masked by the server, cannot search by email, and gets a masked export. Grant it only to those who need it.")}
{access("<strong>User analytics · View</strong>; email, super admin only.")}
""",
        ),
        ch(
            23,
            "Email health",
            f"""
<p class="lead">The Emails page shows how Ochorus's email is landing — aggregate counts only, never
individual recipients.</p>
{figure("emails", "Figure 23.1 — Emails: the overview, subscribers, and results by lifecycle step and by broadcast.")}
<ul>
  <li><strong>Overview</strong> — sent (and delivered), open rate, click rate, bounce rate, complaints
    and failed sends. Open rates are directional — privacy proxies inflate them; <em>click rate is the
    reliable engagement signal</em>.</li>
  <li><strong>Subscribers</strong> — readers who want announcements, those unsubscribed from
    everything, and those suppressed after a bounce or complaint.</li>
  <li><strong>By lifecycle step</strong> and <strong>By broadcast</strong> — the same rates per email.</li>
</ul>
<p>Test sends are excluded. Open and click rates are over delivered mail; bounce and complaint rates
over sent.</p>
{access("super admin only.")}
""",
            new=True,
        ),
        ch(
            24,
            "Composing a broadcast",
            f"""
<p class="lead">A broadcast is an email to a segment of readers, written in blocks, checked before it
goes, and sent in paced batches.</p>
{figure("compose-editor", "Figure 24.1 — The broadcast editor: the audience with its live count, and per-language blocks beside a live preview.")}
<h3>Starting</h3>
<p><strong>New broadcast</strong> creates a draft; <strong>Start from a template</strong> copies a saved
layout. The list shows each broadcast's status — draft, scheduled, sending, paused, sent, canceled.</p>
<h3>Audience</h3>
<p>Filter by language, activity (active in the last 7 or 30 days, lapsed 30+ days, never seen), reading
plan, and sign-up prompt; the live count shows who matches. Readers who opted out or are suppressed are
always excluded at send time.</p>
<h3>Content</h3>
<p>One tab per language, each with a subject, optional inbox preview text, and a list of blocks —
Heading, Text, Button, Quote, Divider, and library blocks for a Book, Sermon or Reading plan, which
render that work's edition in the email's language. <code>{{name}}</code> becomes the reader's first
name. The preview toggles desktop and mobile. <strong>+ Add language</strong> copies the current
layout; <strong>Draft with AI</strong> files a translation job for the words — when the draft comes
back you read it, fix anything, and <strong>Approve</strong> it; it cannot be sent until you do.</p>
<h3>Before you send</h3>
<p>The checklist marks each issue <strong>Must fix</strong>, <strong>Warning</strong> or OK. Must-fix
items — an empty subject, a broken button link, a library block naming an unpublished work, an
unapproved AI draft — block sending and scheduling. Warnings cover readers whose language isn't
written, no test sent, a changed source, sending switched off, and poor sender health.</p>
<h3>Sending</h3>
<ul>
  <li><strong>Send test to me</strong> — to your own address only; repeat as often as you like.</li>
  <li><strong>Schedule</strong> for a date and time, or <strong>Send now</strong>. Either queues the
    broadcast: it goes out in batches of 50 from the next email run (every 15 minutes), each reader at
    most once.</li>
  <li>While sending: progress, <strong>Pause</strong> / <strong>Resume</strong> and <strong>Cancel
    sending</strong>. Once sending starts, the content and audience are locked.</li>
</ul>
{callout("stop", "The guardrail", "After 100 sends, a broadcast pauses itself if complaints pass 0.3% or bounces pass 5%. Resuming asks you to confirm and turns the guardrail off for that broadcast — read the numbers first.")}
{access("super admin only. Every create, edit, test, schedule, send, pause and cancel is in the activity log.")}
""",
            new=True,
        ),
        ch(
            25,
            "Automated emails",
            """
<p class="lead">Some email goes out on its own. There are no buttons for it here, but you should know
what readers receive.</p>
<table><tr><th>Stream</th><th>What and when</th></tr>
<tr><td>Onboarding</td><td>Welcome; pick a plan (day 2+, no plan started); finish your first book
(day 3+); a classic (day 4+); come back (quiet 7+ days); win back (quiet 30+ days). Each once, at most
one per run and never two within 20 hours.</td></tr>
<tr><td>Continue the series</td><td>After a reader finishes a book in a series, the next volume in
their language — once per volume.</td></tr>
<tr><td>Reading milestones</td><td>At 3, 5, 10, 25, 50 and 100 finished books.</td></tr>
<tr><td>Reading-plan reminders</td><td>Only if the reader asked, at their chosen time, on reading days
they haven't read yet; after three idle days, one “paused” note and then nothing.</td></tr>
<tr><td>Announcements</td><td>Your broadcasts (Chapter 24).</td></tr></table>
<p>Readers manage every stream from their email preferences; all start on. The scheduler runs every
15 minutes and also triggers the nightly content-audit scan. Results appear on the Emails page
(Chapter 23).</p>
""",
            new=True,
        ),
        ch(
            26,
            "Team & access",
            f"""
<p class="lead">The Team &amp; access page is where a super admin grants, changes and removes admin
access. It is the only place grants are managed.</p>
{figure("team", "Figure 26.1 — Team & access: the grant form, the granted members with their status, and the super admins.")}
<h3>Granting access</h3>
<ol class="steps">
  <li><strong>Enter the person's email.</strong> Access is tied to it; it works once they sign in with
    that email verified.</li>
  <li><strong>Choose a role</strong> — Contributor, Reviewer or Language admin. <em>Compare roles</em>
    opens the table on the Help page.</li>
  <li><strong>Choose the languages</strong> — at least one, or <em>All languages, including ones added
    later</em>.</li>
  <li><strong>Grant.</strong> A sentence previews exactly what they will get first. Granting to someone
    who already has access replaces their role.</li>
</ol>
<h3>The members list</h3>
<p>Each member shows their role and languages, and whether they have signed in (<em>Invited · not
signed in yet</em>, <em>Active · seen…</em>, <em>Last seen…</em>). Ochorus does not email the invitation —
tell the person yourself. <strong>Manage</strong> opens the same role and language picker, the member's
history, a link to all their activity, and <strong>Remove all access…</strong>. A removal can be
<strong>Undone</strong> from the bar that follows. When a role has gained abilities since someone was
granted it, their card says <em>Out of date</em> with <strong>Update to current role</strong>.</p>
{callout("gold", "Start small, widen deliberately", "Grant Contributor first so a helper can learn the library and file suggestions; upgrade to Reviewer for their language once you have seen their judgement. Reviewer approvals are provisional, so you keep the final say while they do the volume.")}
{callout("indigo", "Why this is super-admin only", "The power to grant access is the power to grant any access, so it is never delegated. Super admins themselves are listed read-only — they come from <code>ADMIN_EMAILS</code> in the deploy environment, by design.")}
{access("super admin only. Every grant and removal is logged.")}
""",
        ),
        ch(
            27,
            "Help & roles page",
            f"""
<p class="lead">The in-admin Help &amp; roles page is a living summary of how the admin works and —
most usefully — of the viewer's own access. Anyone with admin access can open it.</p>
{figure("help", "Figure 27.1 — Help & roles: your access and what it opens, the verb staircase and the roles.")}
<ul>
  <li><strong>Your access</strong> — your role and languages, then a ✓/✕ list of abilities, each with
    <em>Open →</em> or the grant it needs.</li>
  <li><strong>What “access” means</strong> — the verb staircase.</li>
  <li><strong>The roles</strong> — the role cards and <em>Exactly what each role can do</em>, with your
    own role marked.</li>
  <li><strong>Where things live</strong> — every section, marked <em>You have this</em> or with what it
    needs.</li>
  <li><strong>Reviewing</strong>, <strong>How changes reach readers</strong>, <strong>Good to
    know</strong> and a short glossary.</li>
</ul>
{callout("gold", "The fastest answer to “why can't I…?”", "Point a teammate here first. Because it reads their access live, it is always right for the person looking — and nine times in ten it answers the question without this manual.")}
""",
        ),
    ]

    appendices = [
        app(
            "A",
            "Capability & verb reference",
            """
<h3>Capabilities</h3>
<table><tr><th>Capability</th><th>Governs</th></tr>
<tr><td>Reporting &amp; analytics</td><td>Dashboard, coverage, language health, engagement, search statistics, activity.</td></tr>
<tr><td>User analytics (PII)</td><td>The Users directory and reader pages.</td></tr>
<tr><td>Content audit &amp; quality</td><td>The audit report; accepting findings.</td></tr>
<tr><td>Content review</td><td>The review queue; marking a translation still current.</td></tr>
<tr><td>Publishing &amp; imports</td><td>The publish toggles.</td></tr>
<tr><td>Translation queue</td><td>Search triage (queuing itself is super-admin only).</td></tr>
<tr><td>Content-edit queue</td><td>Title, text, audit and biography fixes.</td></tr>
<tr><td>Author records</td><td>Creating authors.</td></tr>
<tr><td>Language administration</td><td>Readiness (view), the bar and settings (act), go-live (approve).</td></tr>
<tr><td>Email campaigns</td><td>Reserved — email is super-admin only.</td></tr>
<tr><td>Reader feedback queue</td><td>Reading (view) and triaging (act) feedback.</td></tr></table>
<h3>Roles as bundles</h3>
<table><tr><th>Area</th><th>Contributor</th><th>Reviewer</th><th>Language admin</th></tr>
<tr><td>Reporting</td><td>View</td><td>View</td><td>View</td></tr>
<tr><td>Content audit</td><td>View</td><td>View</td><td>Act</td></tr>
<tr><td>Content review</td><td>View</td><td>Act</td><td>Approve</td></tr>
<tr><td>Translation queue</td><td>Suggest</td><td>Suggest</td><td>Act</td></tr>
<tr><td>Content-edit queue</td><td>Suggest</td><td>Suggest</td><td>Act</td></tr>
<tr><td>Publishing</td><td>—</td><td>—</td><td>Act</td></tr>
<tr><td>Author records</td><td>—</td><td>—</td><td>Act</td></tr>
<tr><td>Reader feedback</td><td>—</td><td>—</td><td>Act</td></tr>
<tr><td>Language administration</td><td>—</td><td>—</td><td>View</td></tr>
<tr><td>User analytics · Email</td><td>—</td><td>—</td><td>—</td></tr></table>
<p>A super admin holds every capability at Approve, in every language, plus the super-admin-only
levers: importing, queuing translations, email, and Team &amp; access.</p>
""",
        ),
        app(
            "B",
            "What the activity log records",
            """
<table><tr><th>Area</th><th>Actions</th></tr>
<tr><td>Languages</td><td>Language created · settings changed · readiness thresholds changed · taken live</td></tr>
<tr><td>Content</td><td>Document published · unpublished · content-edit job filed · author created</td></tr>
<tr><td>Review</td><td>Review decision recorded · undone · translation confirmed current with its English</td></tr>
<tr><td>Translation</td><td>Translation job filed</td></tr>
<tr><td>Audit</td><td>Finding accepted as known · acceptance undone</td></tr>
<tr><td>Search</td><td>Unanswered search triaged · triage undone</td></tr>
<tr><td>Feedback</td><td>Reader feedback triaged</td></tr>
<tr><td>Email</td><td>Broadcast created · edited · deleted · test sent · scheduled · sent · paused · resumed ·
canceled · template saved · template deleted · translation requested · draft checked for · translation
approved · email sent to a reader</td></tr>
<tr><td>Access</td><td>Admin access granted · revoked</td></tr></table>
<p>Read-only actions (previews, counts, searches of the library) are not logged.</p>
""",
        ),
        app(
            "C",
            "Glossary",
            """
<dl class="glossary">
<dt>Edition</dt><dd>One language version of a work. Books, sermons and plans exist as per-language
editions sharing a slug.</dd>
<dt>Fixture / source</dt><dd>The committed project files the public site is built from. Prose changes
are made here, via jobs.</dd>
<dt>Job</dt><dd>A tracked GitHub issue asking for a source change — a translation, a title, a text fix,
an audit fix, a biography. Filing one changes nothing live.</dd>
<dt>Publish state</dt><dd>Whether an edition is visible to readers. An immediate switch.</dd>
<dt>Source type</dt><dd>Public domain, AI-reviewed or AI-unreviewed.</dd>
<dt>Unreviewed</dt><dd>An AI translation not yet confirmed by a person. Admin-only; never shown to
readers.</dd>
<dt>Provisional</dt><dd>A reviewer's approval recorded but not yet confirmed by an approver.</dd>
<dt>Out of date (↻)</dt><dd>A translation whose English has changed since it was made.</dd>
<dt>Copyright-blocked</dt><dd>A work on the blocklist: it cannot be published or translated.</dd>
<dt>Readiness / the bar</dt><dd>The checklist a language must pass to go live, and the per-language
counts it must reach.</dd>
<dt>Go live</dt><dd>Advertising a language to readers; it records the launch and triggers a rebuild.</dd>
<dt>Broadcast</dt><dd>An email to a segment of readers, sent in paced batches.</dd>
<dt>Lifecycle email</dt><dd>An automatic email triggered by what a reader has (or hasn't) done.</dd>
<dt>Suppressed</dt><dd>A reader address that bounced or complained; nothing is sent to it.</dd>
<dt>Capability · Verb · Scope</dt><dd>The area a grant opens · how far it goes · the languages it
covers.</dd>
<dt>Super admin</dt><dd>Full access, from the <code>ADMIN_EMAILS</code> allowlist outside the grant
system.</dd>
</dl>
""",
        ),
        app(
            "D",
            "Troubleshooting & FAQ",
            """
<h4>A section is missing from my rail.</h4>
<p>You don't hold its capability, or it is super-admin only. Help &amp; roles shows exactly what each
section needs.</p>
<h4>I filed a fix but the site hasn't changed.</h4>
<p>Expected. A job queues a reviewed change that ships on the next build (Chapter 2). The control links
to the job; the activity log tracks it.</p>
<h4>My approval says “Submitted for approval”.</h4>
<p>You hold review at Act, so your approvals are provisional until a language admin or super admin
confirms them (Chapter 14).</p>
<h4>The Approve button is greyed out.</h4>
<p>Scroll to the end of the text — approval unlocks once you have read it all.</p>
<h4>A language admin can't change the bar or go live.</h4>
<p>By design: the role holds Language administration at View only. Those levers stay with the super
admin (Chapter 20).</p>
<h4>The readiness check is slow or shows “unknown”.</h4>
<p>The Bible check calls an external service. An unknown does not block a launch; try again later.</p>
<h4>“Send now” didn't send anything yet.</h4>
<p>Broadcasts start on the next email run, within 15 minutes, and go out in batches. Check the
progress panel; if a warning said sending is switched off on the server, every email is recorded as
skipped.</p>
<h4>A broadcast paused itself.</h4>
<p>The guardrail tripped on complaints or bounces. Look at the rates on the Emails page before
resuming.</p>
<h4>I can't email a particular reader.</h4>
<p>They bounced, complained, or unsubscribed from everything; the panel says which.</p>
<h4>I granted someone access but they see nothing.</h4>
<p>They must sign in with that exact email, verified. Their card shows <em>Invited · not signed in
yet</em> until they do.</p>
<h4>Where do I find this manual again?</h4>
<p>Account menu (avatar, top-right) → <strong>Admin Manual PDF</strong>. Super admins only.</p>
""",
        ),
    ]

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Ochorus Admin Manual</title><style>{CSS}</style></head><body>
{LOGO_SYMBOL}

<section class="cover">
  <svg class="logo"><use href="#mark"/></svg>
  <div class="eyebrow">Ochorus · Operators' Handbook</div>
  <h1>The Admin System&nbsp;Manual</h1>
  <div class="rule"></div>
  <p class="tagline">A complete guide to running the Ochorus library — reviewing translations,
    publishing editions, writing to readers, managing your team, and keeping every language
    healthy.</p>
  <div class="cover-foot"><span class="m">Ochorus</span>
    <span>For super admins · Covers the full /admin console</span>
    <span>Version {VERSION} · {UPDATED}</span></div>
</section>

<section class="toc">
  <div class="kicker">Contents</div><h2>What's inside</h2>
  <ol>
{toc_html()}
  </ol>
</section>

{"".join(chapters)}
{"".join(appendices)}

<section class="end"><svg class="mk"><use href="#mark"/></svg>
  <p>Ochorus Admin Manual · Version {VERSION} · {UPDATED}</p></section>
</body></html>"""


def main() -> None:
    html = build_html()
    chrome = find_chrome()
    with tempfile.TemporaryDirectory() as td:
        hp = Path(td) / "manual.html"
        hp.write_text(html)
        subprocess.run(
            [
                chrome,
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                # Chrome refuses to run as root without it (CI / cloud containers).
                *(["--no-sandbox"] if os.geteuid() == 0 else []),
                "--virtual-time-budget=12000",
                f"--print-to-pdf={OUT}",
                f"file://{hp}",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
