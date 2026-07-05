---
name: book-import
description: Import books into the Ochorus library from ochorus.com PDFs, and review / fix / improve their formatting and text quality — chapter detection, chapter titles, paragraph flow, drop caps, front-matter, and extraction artifacts. Use when adding a book to Ochorus, or when an existing book reads wrong (bogus or generic chapter titles, chapters split mid-sentence, paragraphs broken into fragments, a missing first letter on a chapter, running-header noise, or front matter showing as a chapter). This is a living playbook — append new failure modes and fixes as we find them.
---

# Ochorus book import & repair

Books on **ochorus.com** are PDF downloads. The importer scrapes each book's
page (title, author, cover, PDF), extracts the PDF text with **PyMuPDF**, splits
it into chapters, cleans it, and upserts `Author` / `Book` / `Chapter` rows.

Everything below assumes you're in `~/dev/ochorus/backend` and run Django via
`uv run` with `DJANGO_DEBUG=true` (local SQLite, no services needed).

Key files:
- `library/management/commands/import_ochorus.py` — the importer (scrape, PDF →
  chapters, upsert). This is where the heuristics live.
- `library/corrections.py` — per-book manual overrides (applied on every import).
- `library/ingest.py` — shared HTML cleaning / word counting / `is_front_matter`.
- `.claude/skills/book-import/inspect_pdf.py` — PDF structure diagnostic.

## Commands

```bash
cd backend
DJANGO_DEBUG=true uv run python manage.py import_ochorus --list          # catalogue slugs
DJANGO_DEBUG=true uv run python manage.py import_ochorus <slug> [<slug>] # import/re-import specific books
DJANGO_DEBUG=true uv run python manage.py import_ochorus                 # whole catalogue
```

Explicit slugs import directly by book-page URL (so they work even if the
catalogue listing — which is inconsistent — omits the book). Re-importing one
book preserves its `sort_order`.

## Workflow for fixing a book

1. **Reproduce.** Read the book's chapters out of the DB and eyeball titles,
   boundaries, and the first line of each chapter:
   ```bash
   DJANGO_DEBUG=true uv run python manage.py shell -c "
   from library.models import Book; import re
   b=Book.objects.get(slug='SLUG')
   print(b.title, b.chapter_count)
   for c in b.chapters.all():
       body=re.sub(r'<[^>]+>',' ',c.body_html).strip()
       print(f'  ch{c.order:2}: {c.title[:50]!r} | {body[:55]!r}')"
   ```
   Cross-check the chapter count against the book's own table of contents.

2. **Diagnose the PDF** — the single most useful step (run from `backend/` so
   PyMuPDF is on the path):
   ```bash
   uv run python ~/dev/ochorus/.claude/skills/book-import/inspect_pdf.py SLUG --around "some chapter title"
   ```
   It prints the font-size distribution and the raw blocks around a boundary.
   Identify: the **body** size (the mode), the **real title** size, any
   **running-header** size (a heading-ish size whose text repeats every page),
   and **drop caps** (very large single letters, often out of reading order).

3. **Fix.** Prefer improving the importer if the pattern is general; use a
   per-book correction if it's a one-off (see "Two kinds of fix").

4. **Re-import and re-verify** the book (step 1).

5. **Check for regressions** — re-import a few diverse books and confirm their
   counts/titles are unchanged or better:
   ```bash
   DJANGO_DEBUG=true uv run python manage.py import_ochorus the-inner-chamber the-masters-indwelling men-of-prayer-2 purity-of-heart
   ```
   Marker-style (CHAPTER N), font-title-style, and biography collections each
   stress different paths.

6. **Regenerate the fixture and commit:**
   ```bash
   DJANGO_DEBUG=true uv run python manage.py dumpdata library --indent 1 -o library/fixtures/launch.json
   ```

7. **Ship it to prod (two gotchas — see DEPLOYMENT.md).** A book-data change
   doesn't reach the live site by pushing alone:
   - **The live DB isn't re-seeded from the fixture** (`seed_if_empty` only fills
     an empty DB). A transform over existing rows must ship as a **data
     migration** (auto-runs on deploy via `manage.py release`; e.g.
     `0003_clean_chapter_titles`). A re-import's new rows need `loaddata launch`
     from the Render shell, or the migration path.
   - **The prerendered `/books/<slug>` + `/authors/<slug>` pages won't refresh
     from a backend-only commit.** Render skips the `ochorus-web` build when
     nothing under `frontend/` changed, so the API + reader update but the static
     pages stay stale. Manually redeploy the frontend: Render → `ochorus-web` →
     **Manual Deploy → "Clear cache & deploy latest commit."**

## How chapter detection works (so you can fix it)

A **heading** is a short block that is either a `CHAPTER X` marker OR set larger
than the body font. A heading-like block whose text **repeats >2×** across the
book is a running header/footer — it's banned from being a heading and dropped
from the body. Two passes: prefer `CHAPTER X` markers; if that yields <3
chapters, fall back to font-size headings. After a `CHAPTER X` marker, the next
large/ALL-CAPS block is borrowed as the descriptive title. Drop caps are pulled
out and reattached to the chapter's lowercase-starting paragraph. Paragraphs
split across line/page breaks are rejoined (a block that doesn't end a sentence
continues into the next). Front matter (contents / title page / index) is
dropped; chapters under 120 words are dropped as stubs.

## Known failure modes & fixes (append as we learn)

- **Paragraphs broken into fragments** (sentences split mid-thought). PyMuPDF
  emits one block per visual chunk. Fix lives in `_merge_paragraphs`: a block
  that doesn't end in `.?!` continues the previous one. *(2026-06)*
- **Redundant `Chapter N.` prefix in the title** (e.g. "Chapter One. The Morning
  Hour" — the reader already shows the number, so it renders "1. Chapter One.
  …"). Stripped by `ingest.clean_title` (`_CHAPTER_PREFIX`), applied by the
  importer to every title. Only strips when a descriptive title follows; a bare
  "Chapter 3" is left alone. *(Inner Chamber et al., 2026-07)*
- **Quotation marks in a title** ("Their eyes were opened…", `You"`, `"in Him"`).
  `ingest.clean_title` removes double quotes everywhere and edge single quotes,
  but **preserves apostrophes** in possessives/contractions (God's, Paul's) by
  only stripping a straight `'` that isn't flanked by letters. Also capitalises
  the first letter so a dequoted "in Him" → "In Him". *(Jesus Himself,
  Unselfishness of God, 2026-07)*
- **Title captured only the tail word** when the real title is a long quoted
  sentence that wraps across lines (title-borrow grabbed just "You" from "I will
  come and dwell with you…"). Heuristics can't infer the whole sentence — use a
  per-book `corrections.py` entry with the full title from the PDF's TOC.
  *(jesus-himself-2 ch2, 2026-07)*
- **Backfilling the live library after a title-rule change:** prod isn't
  re-seeded from the fixture (`seed_if_empty` only fills an empty DB), so a pure
  title transform ships as a **data migration** that calls `clean_title` (+ the
  corrections) over all existing `Chapter` rows. It runs automatically via
  `manage.py release` on deploy. See `0003_clean_chapter_titles`. *(2026-07)*
- **Paragraphs broken into fragments** (sentences split mid-thought). PyMuPDF
  emits one block per visual chunk. Fix lives in `_merge_paragraphs`: a block
  that doesn't end in `.?!` continues the previous one. *(2026-06)*
- **Generic `Chapter N` titles** when the real title is title-case (not
  ALL-CAPS) in a larger font. Title borrow is font-aware via `_titleish` /
  `_segment`. *(Normal Christian Life, 2026-06)*
- **Phantom chapter from a running header** (e.g. "Chapter 3" + page number
  "25" → a bogus "Chapter 3. 25" chapter opening mid-sentence). Running headers
  are frequency-banned in `chapterize`. *(2026-06)*
- **Missing first letter of a chapter** ("hat is" for "What is"). Drop caps are
  separate, often out-of-order blocks; `_repair_dropcaps` reattaches them.
  Quote-wrapped initials like `"A` are handled by `_dropcap_letter`. If the drop
  cap is an **image** (not in the text layer), it's unrecoverable — leave it.
  *(Inner Chamber = image caps; Normal Christian Life = text caps.)*
- **Front matter as a chapter** (Preface/Contents/Introduction). `is_front_matter`
  drops contents/title-page/index. Do **not** blanket-drop "Introduction" or
  "Preface" — some books have a real chapter by that name.
- **Over-splitting** on sub-headings or pull-quotes set larger than body — they
  usually fall below the 120-word stub threshold and merge away; if not, the
  running-header ban or a tighter `thresh` (currently `body*1.18`) helps.
- **Two-line wrapped titles captured only the tail** ("Chapter 1: Charles
  Spurgeon — The Prince of" + "Preachers Who Prayed" → title "Preachers Who
  Prayed"). `_merge_heading_runs` rejoins adjacent same-size heading blocks
  before segmentation. *(Ochorus Originals bio collections, 2026-07)*
- **Mixed-case trailing after "Chapter N:" was silently dropped** — the old
  code only kept an ALL-CAPS run. Now a ≤14-word trailing IS the title; longer
  trailing still splits into ALL-CAPS-title + body. *(2026-07)*
- **TOC lines as phantom chapters** ("Chapter 3: … ......."). Dot-leader lines
  (`_TOC_LINE_RE`, 4+ dots) are noise everywhere. *(2026-07)*
- **Appendix cross-references as phantom chapters** ("Chapter 1 — Charles
  Spurgeon" at body size inside a Scripture Appendix, RESTARTING the number
  sequence). When real markers are heading-size, a body-size marker is accepted
  only if it CONTINUES the sequence (prev+1) — Normal Christian Life's real
  "Chapter 6"/"Chapter 12" are body-size amid size-15 siblings and must stay.
  Sequence-aware pre-pass in `chapterize`. *(2026-07)*
- **Introduction/Conclusion/Appendix sections lost or mis-attached** — the
  marker pass used to drop the Introduction entirely and fold the Conclusion
  into the last chapter. `_SECTION_RE` headings at heading size now split
  alongside CHAPTER markers. `is_front_matter` still eats Contents/title-page/
  Index, not these. *(2026-07)*
- **"Introduction" subhead glued into the title block** ("THE BROKEN FENCE
  Introduction"). `_smart_title` strips a trailing "Introduction" when other
  words remain. *(Talks to the Farmer, 2026-07)*
- **Title block fused with subhead AND body text in one oversized block**
  ("THE SLUGGARD'S FARM  Introduction  From a neglected field…") — no heading
  to borrow; use a `corrections.py` title. The body keeping the fused lead text
  is a known cosmetic wart. *(talks-to-the-farmer ch1, 2026-07)*
- **Shipping a structural re-chapterization** (counts/orders change, not just
  titles): a title-transform migration can't help — write a migration that
  reads `fixtures/launch.json`, deletes the affected books' chapters, and
  bulk-creates the corrected sets (safe: nothing FKs Chapter; progress/marks are
  localStorage slug+order). Pattern: `0005_rechapterize_bio_collections`. NOTE:
  orders can shift (Inner Chamber gained a Preface as ch1), which nudges
  readers' saved positions by one chapter. *(2026-07)*
- **Known limits (unfixed):** a book whose Introduction heading is fused with
  its body text in one block loses that intro (feasting-at-the-table); a drop
  cap belonging mid-paragraph after a scripture-ref merge isn't reattached
  ("Ephesians 2:11-22 aul writes").

## Adding a public-domain book NOT on ochorus.com

When the catalogue lacks a wanted title (e.g. more Spurgeon), source it from
CCEL or Project Gutenberg instead:

1. Add a `BookEntry` to `library/catalog.py` (`source` = "ccel" with a
   `<author>/<work>` path, or "gutenberg" with the ebook id). For CCEL, first
   check the TOC section count — `inspect`/curl `<work>.toc.html`; 10–40 sections
   is good, 2 means it won't chapter well (skip), Gutenberg books with no
   headings import as one giant chapter (skip).
2. Import: `import_ccel <slug>` or `import_gutenberg <slug>` (these read
   `catalog.py`, not ochorus.com).
3. **Consolidate the author.** These importers create an author from the catalog
   slug; reassign the new book(s) to the canonical DB author (e.g.
   `charles-h-spurgeon`) and delete the duplicate, so they group correctly on the
   shelf and share one bio.
4. **Generate a cover** — CCEL/Gutenberg books have none:
   `python manage.py generate_covers <slug> ...` writes an on-brand SVG to
   `frontend/static/covers/<slug>.svg` and sets `cover_url`.

## Two kinds of fix

- **Improve the importer** (`import_ochorus.py`) when the pattern recurs across
  books — that's the durable win. Always re-check the sample for regressions.
- **Per-book correction** (`library/corrections.py`) when a book has a quirk the
  heuristics genuinely can't infer (e.g. a chapter whose title is inline in the
  PDF). Keep these few and specific; they're applied on every re-import. Example:
  Normal Christian Life ch12 → "The Cross and the Soul Life".

## Text & grammar quality

These are mostly the user's own edited public-domain texts, so the bar is a
clean, faithful reading copy — **fix extraction artifacts, do not rewrite the
author**. Safe fixes: reattach drop caps, rejoin split paragraphs, drop running
headers/page numbers, repair obviously mangled spacing. Risky (needs the user's
sign-off): changing wording, "modernizing", or any LLM rewrite pass — these can
silently alter meaning in devotional text, so propose and show diffs before
applying, and never do it silently across the library.

## QA scan (whole library)

```bash
DJANGO_DEBUG=true uv run python manage.py shell -c "
from library.models import Book; import re
for b in Book.objects.exclude(pdf_url='').order_by('author__name','title'):
    t=[c.title for c in b.chapters.all()]
    gen=sum(1 for x in t if re.fullmatch(r'Chapter \d+\.?',x))
    dup=len(t)-len(set(t))
    print(f'{len(t):3}ch {b.title[:34]:34}' + (f' [{gen} generic]' if gen else '') + (f' [{dup} dup]' if dup else ''))"
```
Flags generic/duplicate titles and odd counts. Use it before and after a change.
