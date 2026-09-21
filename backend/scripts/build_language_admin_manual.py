#!/usr/bin/env python
"""Generate the Language Admin Manual PDF from the HTML source below.

Unlike the super-admin ``admin-manual.pdf`` (a bare committed binary with no
source), this handbook is reproducible: the content lives here as HTML, and
``fitz.Story`` (PyMuPDF — already a runtime dependency) flows it across pages.
Edit ``BODY`` and re-run to regenerate:

    cd backend && uv run python scripts/build_language_admin_manual.py

The output is written to ``library/assets/language-admin-manual.pdf``, which
``AdminLanguageManualView`` streams to language admins from the account menu.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

OUT = Path(__file__).resolve().parent.parent / "library" / "assets" / "language-admin-manual.pdf"

# A restrained print stylesheet — PyMuPDF's Story supports a subset of CSS, so
# this stays to fonts, weights, colours, spacing and alignment.
CSS = """
* { font-family: sans-serif; }
h1 { font-size: 22px; color: #1f2937; margin: 0 0 2px 0; }
.subtitle { font-size: 11px; color: #6b7280; margin: 0 0 18px 0; }
h2 { font-size: 14px; color: #b45309; margin: 20px 0 6px 0; }
p, li { font-size: 10.5px; color: #1f2937; line-height: 1.45; }
p { margin: 0 0 8px 0; }
ul { margin: 0 0 8px 0; }
li { margin: 0 0 4px 0; }
.lead { font-size: 11.5px; color: #374151; }
.note { font-size: 9.5px; color: #6b7280; margin-top: 24px; }
strong { font-weight: bold; }
"""

# The manual. Reader-facing prose — keep it warm, plain and accurate to what a
# language admin can actually do (mirror the /admin/help "roles" copy).
BODY = """
<h1>Ochorus — Language Admin Manual</h1>
<p class="subtitle">Your guide to running a language on Ochorus</p>

<p class="lead">Welcome, and thank you. As a <strong>Language Admin</strong> you are
the native-speaker conscience of one (or a few) of Ochorus's languages. Your work
is quality: making sure the classics read faithfully and beautifully for the
readers who share your tongue. This short manual explains what you can do, what is
handled by the site owner, and how your decisions reach readers.</p>

<h2>What a Language Admin is</h2>
<p>Ochorus has two kinds of administrator. The <strong>Super Admin</strong> (the
site owner) runs the platform end to end. A <strong>Language Admin</strong> is
granted access to the admin console to look after the content in their
language(s). You see the same console, trimmed to the work that is yours.</p>

<h2>Your dashboard</h2>
<p>Signing in and opening <strong>Language Admin</strong> from the account menu
takes you to your dashboard — a snapshot of the library: how much exists in each
language, what has been added recently, and what needs attention (unreviewed
translations, empty chapters, and the like). It is where each day's work starts.</p>

<h2>Your core work: review &amp; approve</h2>
<p>AI-assisted translations arrive marked <strong>unreviewed</strong>. They are
never shown to readers as finished until a native speaker has checked them — that
is you. In the <strong>Review queue</strong> you read a translation against its
English source, verse by verse where Scripture is quoted, and record a decision:</p>
<ul>
  <li><strong>Approve</strong> — the translation reads faithfully and well; it is
  promoted to reviewed.</li>
  <li><strong>Needs work</strong> — note what is wrong so it can be revised.</li>
</ul>
<p>Approving a translation is the single most valuable thing you do on Ochorus.
Take the time it deserves.</p>

<h2>The coverage matrix (read-only)</h2>
<p>The <strong>Coverage matrix</strong> shows every work against every language —
where each is translated and where the gaps are. As a Language Admin you can
read it freely to understand your language's coverage and see what has been
queued for translation. <strong>Choosing what to queue for translation is
reserved to the Super Admin</strong>, who curates the pipeline for the whole
library; you will see queued and in-progress items, but the queueing controls
themselves are not shown to you.</p>

<h2>What is reserved to the Super Admin</h2>
<p>A few levers are deliberately kept with the site owner. This is not a
limitation on your judgement — it keeps the global, hard-to-reverse decisions in
one pair of hands. As a Language Admin you do <strong>not</strong>:</p>
<ul>
  <li><strong>Queue translation work</strong> — from the dashboard, the coverage
  matrix, or a language's page. The Super Admin decides what enters the pipeline;
  you review what comes out of it.</li>
  <li><strong>Import documents</strong> — uploading a Word or PDF file to create a
  new book or sermon is a Super Admin task.</li>
  <li><strong>See reader email addresses in full</strong> — reader emails are
  personal information and are shown to you masked.</li>
  <li><strong>Administer languages</strong> — creating a language, editing its
  settings or readiness thresholds, and taking it live stay with the Super Admin.</li>
  <li><strong>Manage team access</strong> — inviting or removing admins.</li>
</ul>

<h2>How your changes reach readers</h2>
<p>Ochorus's reader site is pre-rendered for speed, so content goes live when the
site is rebuilt after a change — not the instant you click. An approval is
recorded straight away; the reader-facing update follows with the next build.
Approvals and edits are not lost in the meantime, so there is no need to redo
them.</p>

<h2>Good to know</h2>
<ul>
  <li>Every action in the admin console is logged to the Activity record — who did
  what, and when. This protects everyone.</li>
  <li>The admin console is English-only, even though the content you steward is
  not.</li>
  <li>If a control you expect is missing, it is almost certainly one of the
  Super-Admin-only levers above — ask the site owner rather than assuming a bug.</li>
</ul>

<p class="note">Ochorus — a free reader for public-domain Christian classics.
Questions about your access? Contact the site owner.</p>
"""

HTML = f"<html><head><style>{CSS}</style></head><body>{BODY}</body></html>"


def build() -> Path:
    story = fitz.Story(html=HTML)
    writer = fitz.DocumentWriter(str(OUT))
    mediabox = fitz.paper_rect("letter")
    where = mediabox + (54, 54, -54, -60)  # ~0.75in margins
    more = True
    while more:
        device = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(device)
        writer.end_page()
    writer.close()
    return OUT


if __name__ == "__main__":
    path = build()
    size = path.stat().st_size
    print(f"wrote {path} ({size:,} bytes)")
