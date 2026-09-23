#!/usr/bin/env python
"""Generate the Language Admin Manual PDF — a branded, illustrated handbook.

The manual is served to language admins from the account menu
(``AdminLanguageManualView`` → ``library/assets/language-admin-manual.pdf``).
Everything it needs is committed, so it is reproducible:

  * the content and design live in this script (the ``build_html`` below),
  * the Ochorus lockup is read from ``library/data/brand/ochorus-lockup.svg``,
  * the admin screenshots are committed under ``library/assets/manual/``.

Rendering uses headless Chrome (the same engine as the super-admin manual), so
the page can carry the real brand type (Fraunces + Hanken Grotesk), the logo and
full-colour screenshots — things PyMuPDF's Story CSS subset could not. Regenerate
after editing the content, the design, or the screenshots:

    cd backend && uv run python scripts/build_language_admin_manual.py

Chrome is found at ``$CHROME`` or the macOS default. To refresh the screenshots
themselves you re-run the local admin and recapture (see the docs-PDF recipe);
the images here are the committed inputs.
"""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # backend/
ASSETS = ROOT / "library" / "assets"
SHOTS = ASSETS / "manual"
LOGO_SVG = (ROOT / "library" / "data" / "brand" / "ochorus-lockup.svg").read_text()
OUT = ASSETS / "language-admin-manual.pdf"

# Strip the leading XML comment and lift the <svg>'s inner paths into a <symbol>
# we can <use> at any size; a wrapper `color:` recolours it (fill=currentColor).
_svg_inner = LOGO_SVG.split("-->", 1)[-1]
_svg_inner = _svg_inner.split(">", 1)[1].rsplit("</svg>", 1)[0]
LOGO_SYMBOL = (
    '<svg style="display:none" aria-hidden="true">'
    f'<symbol id="mark" viewBox="0 0 1020.6 616.3">{_svg_inner}</symbol></svg>'
)


def shot(name: str) -> str:
    """A committed screenshot as a data URI, so the render has no file deps."""
    data = base64.b64encode((SHOTS / f"{name}.jpg").read_bytes()).decode()
    return f"data:image/jpeg;base64,{data}"


def figure(name: str, caption: str) -> str:
    return (
        f'<figure class="shot"><img src="{shot(name)}" alt="{caption}">'
        f"<figcaption>{caption}</figcaption></figure>"
    )


def find_chrome() -> str:
    env = os.environ.get("CHROME")
    if env and Path(env).exists():
        return env
    for c in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
    ):
        if c and Path(c).exists():
            return c
    raise SystemExit("Chrome not found — set $CHROME to its path.")


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Hanken+Grotesk:wght@400;500;600;700&display=swap');
:root {
  --paper:#fbf5e6; --page:#fffdf8; --ink:#3a2f1e; --ink-strong:#2a2114; --muted:#7a6e5c;
  --accent:#3f3d9a; --accent-soft:#ecebf7; --accent-border:#cfcdec;
  --gold:#b07d22; --gold-soft:#f6edd7; --gold-border:#e6d3a6; --border:#e6dcc6;
  --serif:'Fraunces',Georgia,'Times New Roman',serif;
  --sans:'Hanken Grotesk',ui-sans-serif,system-ui,-apple-system,sans-serif;
}
* { box-sizing:border-box; }
html { -webkit-print-color-adjust:exact; print-color-adjust:exact; }
body { margin:0; font-family:var(--sans); font-size:10.5pt; line-height:1.6; color:var(--ink); background:var(--page); }
@page { size:Letter; margin:20mm 20mm 18mm 20mm;
  @bottom-left { content:"Ochorus — Language Administrator's Manual"; font-family:'Hanken Grotesk',sans-serif; font-size:7.5pt; color:#b3a68f; }
  @bottom-right { content:counter(page); font-family:'Hanken Grotesk',sans-serif; font-size:8pt; color:#b3a68f; } }
@page cover { margin:0; @bottom-left{content:none;} @bottom-right{content:none;} }
@page nofolio { @bottom-left{content:none;} @bottom-right{content:none;} }
h1,h2,h3,h4 { font-family:var(--serif); color:var(--ink-strong); font-weight:600; line-height:1.2; }
.cover { page:cover; width:100%; height:271mm; background:radial-gradient(120% 80% at 50% 0%, #fefaf0 0%, var(--paper) 55%, #f3e9d1 100%);
  display:flex; flex-direction:column; align-items:center; padding:34mm 24mm 22mm; text-align:center; break-after:page; }
.cover .logo { color:var(--ink-strong); width:74mm; height:auto; margin-bottom:12mm; }
.cover .eyebrow { font-family:var(--sans); font-weight:600; letter-spacing:3.5pt; text-transform:uppercase; font-size:9pt; color:var(--gold); margin-bottom:6mm; }
.cover h1 { font-size:33pt; letter-spacing:-0.4pt; margin:0 0 5mm; }
.cover .tagline { font-family:var(--serif); font-style:italic; font-size:14pt; color:var(--muted); max-width:130mm; margin:0 auto; }
.cover .rule { width:46mm; height:2.5pt; background:var(--gold); border-radius:2pt; margin:9mm auto; }
.cover .cover-foot { margin-top:auto; font-family:var(--sans); font-size:9pt; color:var(--muted); display:flex; flex-direction:column; gap:2mm; }
.cover .cover-foot .m { color:var(--gold); font-family:var(--serif); font-size:11pt; letter-spacing:1pt; }
.toc { page:nofolio; break-after:page; padding-top:6mm; }
.toc h2 { font-size:20pt; margin:0 0 2mm; }
.toc .kicker { font-family:var(--sans); font-weight:600; letter-spacing:2.5pt; text-transform:uppercase; font-size:8pt; color:var(--gold); }
.toc ol { list-style:none; counter-reset:toc; padding:0; margin:8mm 0 0; }
.toc li { counter-increment:toc; display:flex; align-items:baseline; gap:4mm; padding:3mm 0; border-bottom:1px solid var(--border); }
.toc li::before { content:counter(toc,decimal-leading-zero); font-family:var(--serif); font-size:12pt; color:var(--gold); width:12mm; }
.toc li .t { font-family:var(--serif); font-size:12.5pt; color:var(--ink-strong); }
.toc li .d { font-size:8.5pt; color:var(--muted); margin-top:0.5mm; }
.chapter { break-before:page; }
.chapter > .opener { margin-bottom:7mm; padding-bottom:5mm; border-bottom:2px solid var(--gold); }
.chapter .num { font-family:var(--sans); font-weight:700; letter-spacing:2.5pt; text-transform:uppercase; font-size:8pt; color:var(--gold); display:flex; align-items:center; gap:3mm; }
.chapter .num .mk { width:5mm; height:5mm; color:var(--gold); }
.chapter h2 { font-size:22pt; margin:3mm 0 0; letter-spacing:-0.3pt; }
.chapter h3 { font-size:13pt; margin:8mm 0 2mm; color:var(--accent); }
.chapter h4 { font-size:10.5pt; font-family:var(--sans); font-weight:700; color:var(--ink-strong); margin:5mm 0 1mm; }
p { margin:0 0 3.2mm; }
.lead { font-family:var(--serif); font-size:12.5pt; line-height:1.55; color:var(--ink-strong); margin-bottom:5mm; }
ul { margin:0 0 3.5mm; padding-left:5.5mm; }
li { margin:0 0 1.6mm; }
strong { color:var(--ink-strong); font-weight:600; }
em { font-style:italic; }
.steps { counter-reset:step; list-style:none; padding:0; margin:3mm 0 4mm; }
.steps > li { counter-increment:step; position:relative; padding:0 0 3mm 11mm; break-inside:avoid; }
.steps > li::before { content:counter(step); position:absolute; left:0; top:-0.5mm; width:7mm; height:7mm; border-radius:50%;
  background:var(--accent-soft); border:1px solid var(--accent-border); color:var(--accent); font-family:var(--sans); font-weight:700; font-size:9pt;
  display:flex; align-items:center; justify-content:center; }
.callout { break-inside:avoid; border-radius:4px; padding:4mm 5mm; margin:4mm 0; font-size:9.8pt; }
.callout .tag { font-family:var(--sans); font-weight:700; font-size:7.5pt; letter-spacing:1pt; text-transform:uppercase; display:block; margin-bottom:1.6mm; }
.callout p:last-child { margin-bottom:0; }
.gold { background:var(--gold-soft); border:1px solid var(--gold-border); border-left:3px solid var(--gold); }
.gold .tag { color:var(--gold); }
.indigo { background:var(--accent-soft); border:1px solid var(--accent-border); border-left:3px solid var(--accent); }
.indigo .tag { color:var(--accent); }
.stop { background:#fbeceb; border:1px solid #ecccc9; border-left:3px solid #b4443c; }
.stop .tag { color:#b4443c; }
table { width:100%; border-collapse:collapse; margin:4mm 0; font-size:9.3pt; break-inside:avoid; }
th,td { text-align:left; vertical-align:top; padding:2.6mm 3mm; border-bottom:1px solid var(--border); }
th { font-family:var(--sans); font-size:7.6pt; text-transform:uppercase; letter-spacing:0.6pt; color:var(--muted); background:#f6efdd; border-bottom:1.5px solid var(--gold-border); }
.cando td:first-child { font-weight:600; color:var(--ink-strong); width:34%; }
.cross { color:#b4443c; font-weight:700; }
.cardgrid { display:grid; grid-template-columns:1fr 1fr; gap:4mm; margin:4mm 0; }
.card { break-inside:avoid; border:1px solid var(--border); border-radius:5px; padding:4mm 4.5mm; background:#fffdf6; }
.card h4 { margin:0 0 1.5mm; color:var(--accent); }
.card p { font-size:9.3pt; margin:0; }
.shot { break-inside:avoid; margin:5mm 0; }
.shot img { width:100%; display:block; border:1px solid var(--border); border-radius:5px; box-shadow:0 2px 10px rgba(58,47,30,0.10); }
.shot figcaption { font-family:var(--sans); font-size:8pt; color:var(--muted); margin-top:2mm; text-align:center; font-style:italic; }
.glossary dt { font-family:var(--serif); font-weight:600; color:var(--ink-strong); font-size:11pt; margin-top:4mm; }
.glossary dd { margin:0.5mm 0 0; font-size:9.6pt; }
.end { break-before:page; text-align:center; padding-top:40mm; }
.end .mk { width:40mm; color:var(--gold); margin:0 auto 8mm; display:block; }
.end p { color:var(--muted); font-family:var(--serif); font-style:italic; font-size:12pt; }
"""


def opener(num_word: str, title: str) -> str:
    return (
        '<div class="opener"><div class="num">'
        '<svg class="mk"><use href="#mark"/></svg> '
        f"Chapter {num_word}</div><h2>{title}</h2></div>"
    )


def build_html() -> str:
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Ochorus — Language Administrator's Manual</title><style>{CSS}</style></head><body>
{LOGO_SYMBOL}

<section class="cover">
  <svg class="logo"><use href="#mark"/></svg>
  <div class="eyebrow">Ochorus · Ministry Handbook</div>
  <h1>Language Administrator's&nbsp;Manual</h1>
  <div class="rule"></div>
  <p class="tagline">A guide to tending Ochorus in the languages entrusted to you — reading with
    care, vouching for the work, and passing the rest to the team.</p>
  <div class="cover-foot"><span class="m">Ochorus</span>
    <span>Free public-domain Christian classics · Edition 1 · 2026</span></div>
</section>

<section class="toc">
  <div class="kicker">Contents</div><h2>What's inside</h2>
  <ol>
    <li><span><span class="t">Welcome</span><div class="d">Who this is for, and the heart of the role</div></span></li>
    <li><span><span class="t">Your role at a glance</span><div class="d">What you tend, and the one loop it comes down to</div></span></li>
    <li><span><span class="t">Getting started</span><div class="d">Signing in, finding your tools, your languages</div></span></li>
    <li><span><span class="t">What you can and cannot do</span><div class="d">Your access, spelled out plainly</div></span></li>
    <li><span><span class="t">A tour of your dashboard</span><div class="d">Every screen you can open, and what it's for</div></span></li>
    <li><span><span class="t">Core workflows</span><div class="d">Approving translations, auditing, flagging, feedback</div></span></li>
    <li><span><span class="t">How your changes reach readers</span><div class="d">The two paths — instant flags and pull requests</div></span></li>
    <li><span><span class="t">Ways of working well</span><div class="d">The habits that keep a language trustworthy</div></span></li>
    <li><span><span class="t">What stays with the founder</span><div class="d">The levers reserved for the super admin</div></span></li>
    <li><span><span class="t">Help, and a glossary</span><div class="d">Where to turn, and the words we use</div></span></li>
  </ol>
</section>

<section class="chapter">{opener("One", "Welcome")}
  <p class="lead">Ochorus is a free reader for the great public-domain Christian classics — on the web
    and on phones, in many languages. You have been trusted with something specific and precious: the
    care of Ochorus in a language you know from the inside.</p>
  <p>Most of Ochorus's translations begin as careful machine drafts. They are honest, but they are not
    yet vouched for. A machine can render a sentence; it cannot feel whether it lands the way a native
    reader hears it, or whether a verse reads as Scripture rather than as prose. That judgement is
    yours. As a <strong>language administrator</strong> you read the work in your languages, tell us
    what is ready and what still needs a human hand, and — when you are satisfied — put your name to it
    so a reader can trust it.</p>
  <h3>The heart of the role</h3>
  <div class="cardgrid">
    <div class="card"><h4>Read</h4><p>Move through a book, a sermon, or a reader's suggestion in your
      language, the way a reader would.</p></div>
    <div class="card"><h4>Flag</h4><p>When something is off, you don't rewrite production. You file a
      precise note that becomes a proper fix.</p></div>
    <div class="card"><h4>Approve</h4><p>When a translation genuinely reads well, you approve it — the
      moment a draft becomes something a reader can trust.</p></div>
    <div class="card"><h4>Repeat</h4><p>Work by work, the library grows more faithful and more
      beautiful in the tongues you serve.</p></div>
  </div>
  <div class="callout indigo"><span class="tag">A steward, not an editor</span>
    <p>You will notice you cannot type new text straight into a live book. That is by design — Ochorus's
      pages are built from committed source files so nothing changes under a reader unseen. Your edits
      travel a safe path (Chapter Seven). Think of yourself as the one who <em>catches</em> and
      <em>vouches</em>, while the machinery does the writing-out.</p></div>
</section>

<section class="chapter">{opener("Two", "Your role at a glance")}
  <p class="lead">Everything here serves one sentence: you keep the library trustworthy in your
    languages, by reviewing what is drafted and flagging what is wrong — without ever having to touch
    production directly.</p>
  <h3>What you tend</h3>
  <ul>
    <li><strong>Translations awaiting review</strong> — books, sermons and biographies drafted by the
      AI pipeline, waiting for a native speaker to approve them or send them back.</li>
    <li><strong>Content quality</strong> — titles, paragraphs and text that read wrong, which you flag
      for a clean fix.</li>
    <li><strong>What's live</strong> — whether a particular edition is shown to readers.</li>
    <li><strong>Reader suggestions</strong> — if your founder gives you the feedback queue, the ideas
      and corrections readers send in.</li>
  </ul>
  <h3>Your scope</h3>
  <p>Your access is <strong>scoped to your languages</strong> — nothing else. The queues, filters and
    screens show you only your languages, and the tools quietly refuse anything outside them. You never
    see readers' personal information, and you never touch another language's work.</p>
  <div class="callout gold"><span class="tag">The one rule above all others</span>
    <p>Never approve a translation you have not truly read. The whole point of your approval is that a
      <em>human who knows the language</em> has vouched for it. Rubber-stamping doesn't just pass a bad
      sentence — it empties the promise your approval makes to every reader after you.</p></div>
</section>

<section class="chapter">{opener("Three", "Getting started")}
  <ol class="steps">
    <li><strong>Sign in to Ochorus</strong> with the account your founder granted access to — the same
      account you read with.</li>
    <li><strong>Open your avatar</strong> (top-right). Because you have admin access, the menu now shows
      a <strong>Language Admin</strong> link the ordinary reader never sees — and, right beneath it,
      this manual.</li>
    <li><strong>Land on your dashboard.</strong> A left-hand rail lists only the screens your access
      opens, so your console is naturally calmer than the founder's.</li>
    <li><strong>Read "Help &amp; roles"</strong> (bottom of the rail) any time you want a reminder of
      exactly what your account can do today.</li>
  </ol>
  {figure("dashboard", "Your dashboard — the library at a glance, and a rail trimmed to your languages.")}
  <div class="callout indigo"><span class="tag">If a screen says "not authorised"</span>
    <p>You've reached a tool outside your grant or your languages — the system doing its job, not a
      fault. If you believe you need it, ask your founder; access is a single line for them to add.</p></div>
</section>

<section class="chapter">{opener("Four", "What you can and cannot do")}
  <p class="lead">Here is your access in plain words. Everything below is scoped to your languages
    unless it is naturally global (like viewing a report).</p>
  <h3>What you can do</h3>
  <table class="cando"><thead><tr><th>You can…</th><th>Which means</th></tr></thead><tbody>
    <tr><td>Approve &amp; return translations</td><td>Work the review queue: mark a drafted book, sermon or bio as reviewed, or send it back as "needs work". Your signature task.</td></tr>
    <tr><td>Confirm others' review work</td><td>Where a contributor proposed a decision, you can confirm it — a second pair of eyes before a reader sees it.</td></tr>
    <tr><td>Work the content audit</td><td>See the quality checker's findings for your languages and accept or dismiss each one.</td></tr>
    <tr><td>Flag content fixes</td><td>Ask for a title, a chapter's text, or a missing biography to be corrected — filed as a job that becomes a clean pull request.</td></tr>
    <tr><td>Request translations</td><td>Queue a work to be translated into one of your languages.</td></tr>
    <tr><td>Publish &amp; unpublish editions</td><td>Show or hide a particular edition in your languages, instantly.</td></tr>
    <tr><td>Tend author records</td><td>Act on the authors behind the works in your languages.</td></tr>
    <tr><td>View reports &amp; your language cockpit</td><td>See the dashboard, coverage, language-health and your language's own readiness page (read-only).</td></tr>
  </tbody></table>
  <div class="callout gold"><span class="tag">Granted separately, if your founder chooses</span>
    <p><strong>The reader-feedback queue.</strong> Triaging the suggestions readers send in is its own
      grant. If your founder gives it to you, an extra "Feedback" screen appears; Chapter Six shows it.</p></div>
  <h3>What you cannot do</h3>
  <table class="cando"><thead><tr><th>You cannot…</th><th>Why it's reserved</th></tr></thead><tbody>
    <tr><td><span class="cross">✕</span> See readers' personal data</td><td>Names, emails and sign-in details are a separate, higher grant. Privacy by default.</td></tr>
    <tr><td><span class="cross">✕</span> Send emails or broadcasts</td><td>Reaching every reader's inbox is a heavy, one-way action kept with the founder.</td></tr>
    <tr><td><span class="cross">✕</span> Import documents</td><td>Raw ingestion is a super-admin task; your work is quality in your languages, not intake.</td></tr>
    <tr><td><span class="cross">✕</span> Grant or remove anyone's access</td><td>Managing the team is undelegated — only the super admin does it.</td></tr>
    <tr><td><span class="cross">✕</span> Take a language live, or change its thresholds</td><td>Going live is a public commitment; you can <em>see</em> readiness but not flip the switch.</td></tr>
    <tr><td><span class="cross">✕</span> Touch a language you don't tend</td><td>Your scope is enforced on every request, per item.</td></tr>
    <tr><td><span class="cross">✕</span> Rewrite live text directly</td><td>By design — content ships from committed source files. You flag; the pipeline writes it out.</td></tr>
  </tbody></table>
</section>

<section class="chapter">{opener("Five", "A tour of your dashboard")}
  <p class="lead">Your left-hand rail shows only what your access opens. Here is each screen you may
    see, and what it's for.</p>
  <h4>Dashboard</h4>
  <p>Your landing page — the state of the library at a glance, and chips pointing you to what needs
    attention in your languages: unreviewed translations, unpublished works, authors without a bio.</p>
  <h4>Coverage matrix &amp; Language health</h4>
  <p>Coverage is a grid of every work against every language, so you can see where your languages are
    complete and where the gaps are. Language health rolls interface, content, review and engagement
    into one ranked readiness score — your bird's-eye view.</p>
  {figure("language-health", "Language health — a ranked readiness score for every language.")}
  <h4>Your language cockpit</h4>
  <p>Open your own language to see its readiness in detail: what's translated, what's reviewed, what's
    still outstanding, and the requirements it must meet. You can read everything here; the heavier
    levers — thresholds, going live — stay with the founder.</p>
  {figure("cockpit", "The language cockpit — Luganda's readiness, in detail (read-only for you).")}
  <h4>Review queue, Content audit &amp; Feedback</h4>
  <p>The three screens where most of your work happens — each has its own walkthrough in Chapter Six.</p>
  <h4>Activity, Engagement &amp; Search</h4>
  <p>Read-only windows on what's happening — recent admin activity, how readers use the library, and
    what they search for. Useful context for where your attention is most needed.</p>
</section>

<section class="chapter">{opener("Six", "Core workflows")}
  <p class="lead">The step-by-step of the everyday. Start with the first — it is the reason the role
    exists.</p>
  <h3>6.1 · Approving a translation</h3>
  <p>When the pipeline translates a work, it ships marked <em>awaiting native review</em>, and a reader
    sees that badge until a human clears it. Clearing it is your call.</p>
  <ol class="steps">
    <li>Open the <strong>Review queue</strong> and filter to one of your languages.</li>
    <li>Pick a work and <strong>read it as a reader would</strong> — listening for whether it reads
      naturally and whether Scripture reads as Scripture. The checks on each row only say the machine
      found nothing, never that the prose is good.</li>
    <li>If it reads well, <strong>approve</strong> it — the badge clears. If it doesn't, mark it
      <strong>needs work</strong> and leave a note saying why.</li>
  </ol>
  {figure("review", "The review queue — translations awaiting a native-speaker check, grouped by language.")}
  <div class="callout stop"><span class="tag">Do not rubber-stamp</span>
    <p>Approving is not a queue to empty; it is a promise to keep. Approve only what you have truly read.
      An unread approval is worse than no approval, because it looks exactly like a real one.</p></div>
  <h3>6.2 · Working the content audit</h3>
  <p>The audit flags likely quality problems automatically. Your job is judgement over each one: accept
    a finding that is actually fine so it stops nagging, or flag a genuine problem for a fix (6.3).</p>
  {figure("audit", "The content audit — automatic quality findings, to accept or flag.")}
  <h3>6.3 · Flagging a content fix</h3>
  <p>When a title is wrong, a chapter reads badly, or an author has no biography, you file a precise
    job — <strong>Fix title</strong>, <strong>Flag text</strong>, or <strong>Request bio</strong>. You
    are not writing the fix; you are pointing at exactly what needs one, and a worker turns it into a
    proper, reviewable change (Chapter Seven).</p>
  <h3>6.4 · Requesting a translation &amp; publishing</h3>
  <p>From a work not yet in one of your languages, queue a translation — the pipeline produces a fresh
    draft that returns to you at 6.1. And <strong>publish / unpublish</strong> is the one instant, live
    content change: hold back an edition that isn't ready, or bring one forward once it is.</p>
  <h3>6.5 · The reader-feedback queue <em>(if granted)</em></h3>
  <p>Readers can send suggestions from anywhere on the site, each tagged with where they were — which
    book, which chapter, which language.</p>
  <ol class="steps">
    <li>Open <strong>Feedback</strong> and filter by status or type.</li>
    <li>Read the suggestion; a badge marks trusted submitters, so a native reviewer's note rises to the top.</li>
    <li><strong>Set a status</strong>, <strong>assign it to yourself</strong>, and leave a note — every
      change is recorded. Where a suggestion is really a content problem, flag it as a fix (6.3).</li>
  </ol>
  {figure("feedback", "The feedback queue — reader suggestions to triage, filter and assign.")}
</section>

<section class="chapter">{opener("Seven", "How your changes reach readers")}
  <p class="lead">Understanding this makes the whole role click: your actions travel two different
    roads, and knowing which is which explains why you flag some things and simply toggle others.</p>
  <div class="cardgrid">
    <div class="card"><h4>The instant road</h4><p>Approving a translation, accepting an audit finding,
      and publishing or unpublishing an edition change a live setting straight away. Safe to do
      directly; they take effect the moment you act.</p></div>
    <div class="card"><h4>The careful road</h4><p>Fixing a title, a chapter's text, or a biography
      changes the <em>source</em> the library is built from. So instead of editing production, you file
      a job — and a worker turns it into a reviewable pull request that ships the change properly.</p></div>
  </div>
  <p>This is why you cannot type a correction straight into a live book, and why that is a feature.
    Ochorus's reader pages are pre-built from committed source files, with no editing credentials in
    production at all. A change that skipped the source would vanish at the next rebuild — or reach one
    language and not its translations. The careful road keeps every language honest.</p>
  <div class="callout indigo"><span class="tag">The badge you're clearing</span>
    <p>An unreviewed translation wears an <em>"awaiting native review"</em> badge that readers can see.
      Your approval is precisely what removes it. Never present an unreviewed translation as an
      original, and never clear the badge for a language you don't truly read.</p></div>
</section>

<section class="chapter">{opener("Eight", "Ways of working well")}
  <p class="lead">A few habits separate a language readers can lean on from one that merely looks
    finished.</p>
  <h4>Read before you approve — every time.</h4>
  <p>The single habit the whole system rests on. If you haven't read it, it isn't reviewed.</p>
  <h4>Flag precisely; don't fix in a hurry.</h4>
  <p>A clear, specific job travels the careful road and lands as a clean change in every affected
    language. A rushed in-place edit helps no one downstream.</p>
  <h4>Lean on maker-checker as the team grows.</h4>
  <p>Your ability to <em>confirm</em> another person's review decision lets a contributor do the first
    pass and you the second — doubling the care without doubling the work.</p>
  <h4>Trust your scope.</h4>
  <p>You are meant to see only your languages and no reader data. That's not the tool holding you
    back — it's the tool keeping your responsibility clear and your conscience clean.</p>
  <h4>When in doubt, send it back.</h4>
  <p>"Needs work" with a kind, specific note is never the wrong call. A translation can always be
    approved tomorrow; an approval is hard to unsay.</p>
</section>

<section class="chapter">{opener("Nine", "What stays with the founder")}
  <p class="lead">A short list, so you know where the edges of your role are — and who to ask when you
    reach one.</p>
  <ul>
    <li><strong>Taking a language live</strong> and setting its readiness thresholds.</li>
    <li><strong>Creating a new language</strong> or changing a language's settings.</li>
    <li><strong>Importing documents</strong> — raw ingestion of new works.</li>
    <li><strong>Managing the team</strong> — granting or revoking anyone's access, yours included.</li>
    <li><strong>Readers' personal data</strong> — names, emails, sign-in providers.</li>
    <li><strong>Email &amp; broadcasts</strong> — anything that reaches readers' inboxes.</li>
  </ul>
  <p>If your work runs up against one of these — you think a language is ready to go live, or you need
    access to something new — that's a conversation with your founder, usually a one-line change on
    their side. You surface the judgement; they pull the lever.</p>
</section>

<section class="chapter">{opener("Ten", "Help, and a glossary")}
  <h3>Where to turn</h3>
  <ul>
    <li><strong>"Help &amp; roles"</strong> in your admin rail — a live description of what your own
      account can do right now.</li>
    <li><strong>The feedback button</strong> — you're a reader too; use it to send your own suggestions
      and questions straight into the queue.</li>
    <li><strong>Your founder</strong> — for access, for going live, and for anything reserved above.</li>
  </ul>
  <h3>The words we use</h3>
  <dl class="glossary">
    <dt>Awaiting native review</dt><dd>A translation drafted by the AI pipeline that no human native
      speaker has yet vouched for. Readers see a badge; your approval clears it.</dd>
    <dt>Reviewed / approved</dt><dd>A translation a language admin has read and vouched for.</dd>
    <dt>Review queue</dt><dd>The screen listing everything awaiting a native-speaker check.</dd>
    <dt>Content-edit job</dt><dd>A precise request to fix a title, a chapter's text, or a biography —
      the careful road that becomes a reviewable change rather than a live edit.</dd>
    <dt>Translation job</dt><dd>A request to translate a work into one of your languages.</dd>
    <dt>Edition</dt><dd>One work in one language. Publishing acts on a single edition.</dd>
    <dt>Scope</dt><dd>The set of languages your access covers. Every tool limits itself to it.</dd>
    <dt>Super admin</dt><dd>The founder — the account that holds every lever.</dd>
  </dl>
</section>

<section class="end"><svg class="mk"><use href="#mark"/></svg>
  <p>Thank you for tending Ochorus with such care.</p></section>
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
