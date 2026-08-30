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
   DJANGO_DEBUG=true uv run python manage.py import_ochorus the-masters-indwelling men-of-prayer-2 purity-of-heart talks-to-the-farmer
   ```
   Marker-style (CHAPTER N), font-title-style, and biography collections each
   stress different paths. **Do NOT re-import `the-inner-chamber` or
   `humility-2`**: both back seeded reading plans (PlanDay maps day → chapter
   order) and a re-import that picks up a previously-dropped Preface shifts
   every order. Snapshot counts+first-titles BEFORE the regression imports and
   diff after; restore any regressed book from its `fixtures/content/books/<slug>.<lang>.json` (delete
   its chapters, recreate from the fixture entries).

6. **Regenerate the fixture and commit:**
   ```bash
   uv run python scripts/regen_fixture.py   # pinned 6-model natural-key regen; NEVER bare `dumpdata library`
   ```
   If it aborts with `N unexpected new field(s)`, that's not your import — see
   the fixture-regen entry under Known failure modes.

7. **Ship it to prod (two gotchas — see DEPLOYMENT.md).** A book-data change
   doesn't reach the live site by pushing alone:
   - **The live DB isn't re-seeded wholesale from the fixture** (`seed_if_empty`
     only fills an empty DB). **Book rows** are fine — the release step's
     `seed_books` upserts them: a NEW book is created with its chapters, and a
     changed book field (`title`, `cover_url`, `description`, `sort_order`, …)
     is updated on the next deploy, straight from the fixture. But an existing
     book's **chapters** are left alone, so a re-import that rewrites chapter
     text, and any other transform over existing rows, still ships as a **data
     migration** (auto-runs via `manage.py release`; e.g.
     `0003_clean_chapter_titles`). `source_type` / `is_published` are
     create-only — the review and unpublish workflows own them.
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
- **Every chapter titled a bare "Chapter N", real title glued to the first
  paragraph** — a typographically FLAT PDF: the "CHAPTER 1" marker and the
  title below it are BOTH at body size, and the only larger size is the running
  header. `_titleish` sees no title (not larger, not ALL-CAPS), so nothing is
  borrowed, and `_merge_paragraphs` then fuses the unpunctuated title line into
  the epigraph that follows. `_flat_marker_title` takes the single short line
  after a marker as the title — and only when the normal borrow found nothing,
  so it can't change a book that already works.
  **Tune such a guard loose, then let length do the work.** The first cut
  (≤8 words, no terminal punctuation, no leading quote) still shipped 3 of 32
  chapters broken, because each guard rejected a real title: "Your Body Is the
  Temple of the Holy Ghost" (9 words), "Is Sickness a Chastisement?" (`?` ends
  titles too), "Ye Are the Branches" (titles get quoted). What actually
  separates a title from an epigraph is **length** (≤12 words) plus a
  *parenthesised verse citation* — the citation is the only thing that rejects
  `“Ye are the branches” (John 15:5).`, an epigraph that repeats its own
  chapter title almost word for word. Reject `[.,;:]` but never `?`/`!`, and
  reject lines that are only a scripture reference ("Mark 5 :25—34"), which sit
  under the title in this layout. *(Divine Healing, 2026-07)*
- **`import_ccel` reports "✓ N chapters" for whatever it found — ALWAYS check N
  against the source TOC.** It printed "✓ **2** chapters" for the 115-chapter
  *Imitation of Christ* and exited 0: the section-URL pattern matched only
  roman/numeric path segments, but CCEL also names parts with a **word**
  (`imitation.ONE.1.html`), so only two front/back-matter pages matched. Widened
  to any alphanumeric segment (and the TOC's self-link excluded, since it now
  matches too). The check takes one command — compare against the TOC's link
  count before trusting any import:
  ```bash
  curl -s https://ccel.org/ccel/<ref>/<work>.toc.html | grep -c '<work>\.[A-Za-z0-9_.]*\.html'
  ```
  *(2026-07; the general lesson is review-report finding #35 — importers assert
  almost nothing after the fact, so a dropped chapter looks like success.)*
- **CCEL footnotes inlined into the prose** — the drop selector was
  case-**sensitive**, so `class="Footnote"` sailed through and put the note text
  mid-sentence ("desires knowledge 2 Aristotle, Metaphysics, i. 1. ; but"), with
  the `Note`/`NoteRef` markers left as bare digits. Now `[class*=note i]` (the
  `i` flag) covers the whole apparatus. When adding a drop selector for a CCEL
  class, **assume capitalisation you haven't seen** and use `i`. *(2026-07)*
- **Every CCEL chapter restating its own heading** — bodies open
  `<h4>The Twenty-Second Chapter</h4><h3>{the title}</h3>` above prose the reader
  already sees titled. `extract_body(html, title)` drops a leading ordinal
  heading and a leading heading that restates the TOC title, stopping at the
  first heading that is neither — so Book III's "The Disciple" / "The Voice of
  Christ" speaker labels survive. Two traps: the ordinal matcher must accept only
  real counters (ordinal word / roman / digits) or it eats a genuine "Chapter
  Summary"; and `span.pb` must be decomposed *first*, since a page-break marker
  sitting before the heading otherwise counts as content and blocks the strip.
  *(2026-07)*
- **CCEL page numbers and spacer gaps in the body** — CCEL marks a print page
  break as `<span class="pb">17</span>` (lands mid-sentence, or alone at the top
  of a chapter) and uses `<p><br/></p>` for vertical space (a ragged gap when
  reflowed). Both now dropped in `ingest` — `span.pb` in `DROP_SELECTORS`, and
  the empty-block regex accepts `<br>`-only content. *(Waiting on God: 71 spacer
  paragraphs, 2026-07)*
- **A CCEL chapter opening with three stray one-line fragments that repeat the
  title** — most CCEL works mark the heading as a real `<h2>`; a few set it as
  consecutive one-line paragraphs ("First Day." / "WAITING ON GOD:" / the
  title). `import_ccel.fold_leading_heading` joins a leading run of 2+ very
  short paragraphs into one `<h2>`. CCEL also sets **poetry and verse epigraphs
  one line per paragraph**, so an unguarded run eats Scripture — or the whole
  chapter. Four guards, all earned: stop at a quoted OR dashed line (the
  epigraph and its `—Ps. 62:5` citation), cap the run, refuse a fold that would
  leave nothing behind, and require at least one line that reads as a heading
  (ALL-CAPS or ending in a colon) so two short narrative paragraphs — "He was
  gone." / "She did not know." — are left alone. *(Waiting on God, 2026-07)*
- **Dry-running a body-cleaning change over STORED chapters understates it.**
  The natural check for a fold/clean change is to run it over every stored
  chapter and count what would change — but stored HTML was produced by the
  *old* cleaner. Here a leading `<p><br/></p>` used to be what STOPPED the
  fold, and the new empty-block rule deletes it first, so the fold reached
  further than the dry run showed. Pipe each stored chapter through
  `clean_fragment` (the new rules) **before** applying the change under test.
  *(2026-07)*
- **Shipping a structural re-chapterization** (counts/orders change, not just
  titles): a title-transform migration can't help — write a migration that
  reads the book's `fixtures/content/books/` file, deletes the affected books' chapters, and
  bulk-creates the corrected sets (safe: nothing FKs Chapter; progress/marks are
  localStorage slug+order — but CHECK PlanDay: reading plans soft-reference
  chapters by (book_slug, chapter_order), so an order shift breaks seeded
  plans). Pattern: `0009_rechapterize_bio_collections`. Ship only books that
  MATERIALLY changed — a re-import that merely adds a Preface as ch1 shifts
  every chapter_order, breaking the book's seeded plan and readers' saved
  positions (we excluded the-inner-chamber for exactly this). *(2026-07)*
- **Prose starting with "chapter" split a real sentence** ("The first /
  chapter deals with the doctrines…" became a phantom chapter titled "Chapter
  Deals With"). `_CHAP_RE` matches any word after CHAPTER, so BOTH the marker
  pre-pass AND the `is_font` fallback now reject a body-size match whose label
  isn't a parseable number. *(the-key-in-my-hand 16→15 ch, 2026-07)*
- **Trailing page/section number absorbed at chapter end** ("…Amen. 4",
  "…evermore!”10" — inside OR just outside the final `</p>`).
  `ingest.strip_trailing_pagenum` runs on every import; requires terminal
  punctuation first so verse refs ("Psalm 145:7") and years are safe.
  *(till-he-come ch2–22, 2026-07)*
- **Publisher back-catalogue imported as extra chapters at the end of a
  Gutenberg book** ("Valuable Works", "Works for Church Members" — priced ad
  pages: "PUBLISHED BY GOULD AND LINCOLN … 12mo, cloth, $1.25"). Dropped by
  `import_gutenberg._catalogue_start`, which cuts from the first trailing section
  whose HEAD carries an ALL-CAPS `PUBLISHED BY <name>` imprint to the end (the
  continuation pages have no imprint of their own). **The clean signal is only
  the imprint** — a bare price ($x.xx) fires on a parable's "$10.00", and a
  binding word (octavo/quarto/cloth) on Portuguese "décimo quarto versículo", so
  both were tried and cut. **Imprint-at-HEAD, not anywhere:** some texts fold the
  ad into the LAST chapter's tail (`around-the-wicket-gate` ch11 ends "…PUBLISHED
  BY THE American Tract Society"); cutting the whole section would delete a real
  chapter, so only a section that BEGINS with the imprint counts, and the scan is
  limited to the trailing ~5 sections. Regression-check any change here by
  scanning the whole corpus for head-imprints (expect 0) and re-importing a
  couple of Gutenberg books to confirm counts hold. *(the-life-of-trust, 2026-08)*
- **A stray page-number divider heading ("[364]")** — one chapter's Gutenberg
  chapter-divider heading was a bracketed page number, not the title, and the
  real title sat in an `<h3>` at the top of the body. Heuristics can't infer the
  title from a page number; fix per-book: `corrections.chapter_titles` restores
  the title, and a `BODY_CORRECTIONS` `replacements` pair drops the now-duplicated
  `<h3>` so the body opens like its siblings. *(the-life-of-trust ch23, 2026-08)*
- **OCR letter-splits** ("blesse d!", "lif e.", "conversatio n.") and
  **image-drop-cap first letters** lost from the text layer: recorded as
  explicit literal pairs / letters in `corrections.py` `BODY_CORRECTIONS`
  (never a clever regex — "Song i." is a citation, not an error), applied on
  every import by both importer paths and backfillable over stored rows via
  `manage.py apply_body_corrections`. *(around-the-wicket-gate all 11 caps +
  13 OCR pairs across 6 books, 2026-07)*
- **A chapter that lost its paragraphing** in the SOURCE transcription (not on
  import) goes in the same table under `paragraph_breaks`, as `(tail, head)`
  prose seams — a plain-text pair would also match the tagless `body_text`.
  Find the breaks with the scan-indent method, never by block length: see the
  english-qa skill's "Restoring lost paragraphing".
  *(the-reformed-pastor ch04, 5 breaks, 2026-08)*
- **Repeated book-title counts are NOT running headers by themselves** — Torrey
  writes "Baptism with the Holy Spirit" 27–39×/chapter as prose; "Jesus
  Himself" is the sermon's refrain. Confirm with inspect_pdf (isolated
  heading-size blocks near page edges) before treating as noise. Likewise
  10–15k-word chapters can be the author's real structure (Torrey, Nee) —
  check the PDF TOC before splitting. *(2026-07)*
- **Known limits (unfixed):** a book whose Introduction heading is fused with
  its body text in one block loses that intro (feasting-at-the-table); a drop
  cap belonging mid-paragraph after a scripture-ref merge isn't reattached
  ("Ephesians 2:11-22 aul writes").
- **A CCEL work whose leaf sections are too small to be chapters** — Augustine's
  *Confessions* is 278 leaves of 150–900 words titled "Chapter I" … "Chapter
  XXXVIII", and those titles **repeat in every one of the thirteen Books**, so a
  flat import is unreadable and trips `qa.duplicate_title` ~265 times. Set
  `group_parts=True` on the `BookEntry`: `toc_parts` groups leaves under their
  part divider and takes that divider's title ("Book I"). It is deliberately
  opt-in — the part-vs-leaf choice is an editorial judgement about the reading
  and citation unit, not something to auto-detect, and a flag cannot regress the
  books already shipped. Two things to know before using it:
  - **Joined leaf headings are `<h3>`**, matching `import_gutenberg`'s
    `group_daily_entries` / tiny-section merge. Same construct, same level — an
    `<h2>` renders a size larger than every Gutenberg book that does this.
  - **`corrections.chapter_titles` can no longer reach those titles.** It is
    keyed by chapter `order`, and a leaf title is now markup inside a chapter
    body. A leaf-title fix in a grouped book has to be a general `clean_title`
    rule (which is why *Confessions* ships with `Chapter XXi`/`Chapter Xi`
    unfixed). If a second grouped book needs per-leaf fixes, add a hook rather
    than widening `clean_title` again. *(2026-07)*
- **CCEL two-level section numbering** (`<work>.i.ii.html` = part i, chapter ii).
  The `toc_sections` pattern matched only single-segment `<work>.iii.html`, so a
  parts-divided work imported as 1 chapter. Regex now allows one-or-more dotted
  roman/numeric segments; single-level works are unaffected. *(meyer/into_holiest,
  2026-07)*
- **CCEL part-divider / half-title leaking in as a chapter** — with multi-level
  matching, the one-level parent page (`<work>.i.html` = "THE WAY INTO THE
  HOLIEST:") is a structural divider, not prose. `toc_sections` now drops any
  section whose stem is a strict prefix of another's (parent of `i.ii`); no-op
  for single-level works. *(2026-07)*
- **CCEL importer never ran `clean_title`** — earlier CCEL sources happened to be
  Title Case so it was never needed; Meyer's TOC is ALL-CAPS with roman prefixes
  ("II. THE DIGNITY OF CHRIST"). `import_ccel` now applies `clean_title`, and
  `clean_title` gained an ALL-CAPS→Title-Case pass (gated on *every* letter being
  uppercase, so mixed-case titles like "D. L. Moody" are untouched) plus a
  roman-numeral-prefix strip guarded to never eat personal initials. *(2026-07)*
- **Order matters: `is_front_matter` must run on the RAW title, before
  `clean_title`.** `clean_title` strips a trailing "Contents", so a TOC section
  titled "Contents" cleans to `""`, slips past `is_front_matter`, and leaks in as
  a phantom "Chapter N" (inflated till-he-come 23→24). Gate front matter first,
  then clean the survivors. *(2026-07)*
- **A `catalog.py` author slug that doesn't match `authors.json` silently forks
  the author on re-import.** `upsert_book` creates whatever slug the
  `AuthorEntry` names, so a mismatch produces a SECOND author row carrying only
  the catalog stub — no `bio_html`, no photo — and re-points that book at it.
  It can't fire on deploy (release runs `seed_books` off the fixture), so it
  waits for exactly what step 5 above tells you to do — re-import for regression
  testing, then regen the fixture, which commits the duplicate. Found and fixed
  2026-07-26: `catalog.py` said `charles-spurgeon` for five books while the
  fixture and prod had only `charles-h-spurgeon`.
  `AuthorBioDataIntegrityTests.test_every_catalog_slug_exists_in_authors_json`
  now fails CI on any such mismatch, so a new entry can't reintroduce it — but
  when ADDING an author, take the slug from `authors.json` rather than inventing
  one. *(2026-07)*
- **Adding the FIRST book for a biography-only author needs a `catalog.AUTHORS`
  stub first.** Many authors have a full `bio_html` in `authors.json` but NO
  entry in `catalog.AUTHORS` (they were biography-only). `upsert_book` opens with
  `AUTHORS[entry.author_slug]`, so importing their first book `KeyError`s until
  you add an `AuthorEntry`. Write a SHORT `bio` stub (one to three sentences —
  `test_catalog_bios_stay_short_stubs` caps it); `authors.json` stays the source
  of truth and the stub is create-only, so it never overwrites the real bio.
  *(jeanne-guyon → A Short and Easy Method of Prayer, 2026-08)*
- **Adding a book for an author who already exists in the DB with a scraped bio:**
  ~~Copy the existing bio verbatim into the new `AuthorEntry`.~~ **No longer
  needed — fixed at the root (PR #449).** `upsert_book` used to push the catalog
  stub through `defaults=`, so importing ANY book truncated that author's real
  bio; the workaround was to paste the long bio back into `catalog.py`, which is
  why 14 of 17 catalog bios became hand-synced copies of `authors.json`.
  `bio`/`birth_year`/`death_year` now go in **`create_defaults`**: they apply
  only when the author row is first created and never overwrite an existing one.
  `authors.json` stays the source of truth (the rule `seed_books` already
  followed). **Write a one-line stub, never a full biography** — the seven
  pasted-in bios were shortened back, and
  `AuthorBioDataIntegrityTests.test_catalog_bios_stay_short_stubs`
  (tests_fixture.py) caps catalog bio length so the trap can't be re-set by
  hand. Since 2026-07-26 `seed_books` / `seed_sermons` also **upgrade** a stub:
  on every deploy they sync an existing author from `authors.json`, replacing a
  `bio` that is empty or still a verbatim catalog stub (see
  `library/author_sync.py`). Reviewed prose always wins, and `bio_html` /
  `photo_url` / years are fill-only, and every author in the fixture is synced —
  not just those with a book, since 9 of 36 are biography-only. So a **short
  `bio`** written into `authors.json` now reaches prod on its own, where
  0049/0051 needed a hand-written migration. Two things it still does NOT cover:
  **`bio_html`** is fill-only, so REPLACING a long-form biography on a live row
  still ships as a migration with a digest anchor (the 0052 pattern); and a
  **brand-new author with no book or sermon** is never CREATED by either seed
  (only updated), so adding one still needs a migration the way 0053 did.
  Prerender caveat: author pages bake the bio at BUILD time, so the sync lands
  on the API first and the public page only picks it up on the next frontend
  deploy. *(hit amy-carmichael,
  f-b-meyer, susanna-wesley, george-muller, andrew-murray before the fix)*
- **Editing the WORDING of an existing catalog stub? Move the old text into
  `author_sync.RETIRED_STUBS`, don't just overwrite it.** A stub is recognised
  by exact string match, so the old wording is how the sync knows a live row is
  still a placeholder. Delete it and every prod row carrying that text is
  stranded on the stub forever — nothing else upgrades a non-empty bio, and
  there is no error to notice. Only matters for authors whose row was created
  by an import rather than from `authors.json`. *(2026-07)*
- **`chapter_title_overrides` now applies in `upsert_book`** (was only in
  `import_ochorus`), so per-book title corrections work for every source. Apply
  `clean_title` to the override in BOTH paths so the same correction yields the
  same stored title. *(2026-07)*
- **A `clean_title` change silently regresses existing books on their NEXT
  re-import — and some books (Humility, the Murray/Spurgeon CCEL set) are
  imported at DEPLOY, not seeded from the fixture, so the regression only shows
  in prod.** After ANY clean_title edit, re-import a diverse sample AND diff every
  title vs its `fixtures/content/books/` file (see the gutenberg-title-diff pattern in the
  transcript). Real regressions this caught: an un-gated roman-prefix strip
  dropping Murray's "I. Humility: …" numeral; ordinal "1st"→"1St";
  "II CORINTHIANS"→"Ii Corinthians".
- **ALL-CAPS→Title-Case rules that hold:** gate the roman-numeral-prefix strip to
  ALL-CAPS headings only (mixed-case "I. Humility: …" / "II. Timothy" must keep
  the numeral); block the strip only on an actual initial (`L.` in "D. L. MOODY"),
  not an article (`A` in "IX. A WARNING"); PRESERVE whole-token roman numerals in
  the caps pass ("PSALM CXIX", "II CORINTHIANS"); never uppercase a letter that
  follows a digit ("1st"). Titles in this library are uniformly Title Case, so an
  ALL-CAPS or "Ii"/"Iii" stored title is a red flag. *(2026-07)*
- **Internet Archive OCR import** (`import_archive`, `source="archive"`): reflow
  is the whole job. A DjVu text layer is hard-wrapped and double-spaced with page
  furniture that INTERRUPTS paragraphs (a bare page number + a running header
  mid-paragraph). Rules that worked: drop bare-number lines; treat a blank/furniture
  line as a paragraph break ONLY when the buffer ends on terminal punctuation
  (else it's a mid-paragraph page break — keep accumulating); de-hyphenate
  end-of-line splits and rejoin space-split compounds ("fifty- four"). *(susanna-
  wesley-clarke, 2026-07)*
- **Archive running-header vs. letter signature:** the header "60 SUSANNA WESLEY."
  and the letter signature "SUSANNA WESLEY." differ by one thing — the header
  carries a PAGE NUMBER. Detect a header as "line contains a digit AND its
  letters-only core is ALL CAPS"; that keeps signatures (no digit) and all-caps
  prose openings (have lowercase) as prose. Tolerates OCR-mangled page digits
  (`'60`, `€2`, `•94`, `]26`) that a `^\d` regex would miss. *(2026-07)*
- **Archive OCR residue** goes in `corrections.py` `replacements` as literal
  pairs: opening-word drop-cap misreads ("OP the"→"OF the", "MBS."→"MRS."),
  R↔E title misreads (fix via `chapter_titles`), and number-word merges
  ("twentyone"→"twenty-one"). Scan for merges with a "digit-word glued to
  [a-z]" regex, but hand-filter — "eighteenth"/"understand" are real words.
  *(2026-07)*
- **A Victorian edition's quotation marks OCR as guillemets `« »`.** The Patmore
  Bernard scanned every quote as `«`/`»` (22 of them) — a mark that never occurs
  legitimately in English, so map the pair to curly quotes in `corrections.py`
  (`("« ", "“")`, `("«", "“")`, `("»", "”")`). `normalize_quotes.py` only touches
  STRAIGHT quotes, so it leaves guillemets alone — they must be corrected before
  it runs. *(on-loving-god, 2026-08)*
- **A wrapped ALL-CAPS chapter heading leaves its tail as the first paragraph.**
  When the printed heading runs across two OCR lines ("WHY WE OUGHT TO LOVE GOD,
  AND HOW WE" / "OUGHT TO LOVE HIM."), `import_archive` takes the first line as
  the title and the ALL-CAPS remainder becomes the opening `<p>`. Same shape as
  the Guyon/Marston long headings: set a short `chapter_titles` lead clause and
  strip the tail paragraph with a `BODY_CORRECTIONS` `("<p>TAIL.</p>", "")` per
  chapter. Don't strip by a leading-ALL-CAPS regex — Victorian prose opens on a
  small-caps word ("THOSE who…", "LET us…") that flattens to caps and would be
  eaten. *(on-loving-god, 2026-08)*
- **`regen_fixture.py` aborts with `N unexpected new field(s)`** — nothing to do
  with your import. Someone added a model field with a blank/false default, so
  dumpdata now materializes it on every older row while the committed fixtures
  lack it. The abort names the culprit as `model.field×count`. Decide per field:
  a semantically-inert default (optional text, a flag) goes in the script's
  `DEFAULTED_OK` as a `(model, field)` pair; anything load-bearing should be
  excluded from the dump instead. Then re-run — the first regen after the fix
  legitimately rewrites every affected file, so diff-check that the only change
  is the new key. (Fields declared `serialize=False`, like `search_vector`,
  never dump and are never the cause.) *(Sermon.summary, 61 sermons, 2026-07)*
- **THE READER PRINTS THE CHAPTER NUMBER ITSELF, so any numbering left in a
  stored title renders twice.** `TocDrawer.svelte`, `SearchDrawer.svelte` and
  `notebook/+page.svelte` all render `{ch.order}. {ch.title}`, so a title of
  "1. Men of Prayer Needed" reads "1. 1. Men of Prayer Needed" — and CCEL
  numbers its own TOC entries constantly. `clean_title` now strips a bare
  `N.`/`N)` prefix and empties a bare "Chapter N", alongside the older
  `Chapter N.` rule. Two things NOT stripped, both deliberate: a roman prefix on
  a MIXED-CASE title (Edwards's twelve "signs" in religious-affections are
  referential), and "Section N"/"Part N", which name a unit the reader does not
  number. **Before adding any strip, count what it hits corpus-wide** — the
  arabic rule hit 245 stored titles across waiting-on-god (×6 languages) and
  selected-sermons-whitefield, all of which still read doubled until a migration
  rewrites them; `seed_books` never re-syncs an existing book's chapters.
  *(2026-08)*
- **A chapter may legitimately have NO title.** Bounds's *Purpose in Prayer* is
  thirteen untitled chapters (CCEL lists them "Chapter I" … and the pages carry
  only an epigraph). `Chapter.title` is `blank=True`; `upsert_book` no longer
  substitutes `"Chapter {order}"`, which only ever stood between an untitled
  chapter and the reader. The reader names them: all three `{order}. {title}`
  sites fall back to `settings.chapterN` ("Chapter N", translated everywhere),
  with the number INSIDE the fallback so it cannot double up. Before this the
  fallback was `plans.day`, the reading-plan label, so an untitled chapter would
  have read "1. Day 1". *(2026-08)*
- **An untitled "start reading" button on a CCEL TOC decides chapter ORDER.**
  It links past the front matter straight to chapter one, in ABSOLUTE-URL form,
  and first-seen order took its target as section one — so *Prayer and Praying
  Men*'s INTRODUCTION, real prose, imported second. Order now comes from the
  titled TOC entries. Eight CCEL works carry the button; in seven it points past
  a Title Page that `is_front_matter` drops anyway, which is why this hid for so
  long. Note a plain `grep` for the relative href MISSES these — they are written
  `https://ccel.org/ccel/<a>/<w>/<w>.ii.html`. *(2026-08)*
- **`[ivxlcdm]+` is not a roman numeral — it also spells "civil", "mild",
  "livid", "mimic", "did", "mill".** Any rule that strips a leading roman
  numeral must use a STRICT numeral (the `_ROMAN_WORD` construction in
  `ingest.py`, or `_LEAD_COUNTER` in `import_ccel.py`), or a heading whose first
  word merely looks roman will match a title it only precedes. Test the rule
  against those words explicitly. *(2026-08)*
- **A trailing "(Continued)" defeats an ALL-CAPS test.** CCEL sets the heading
  in caps and the continuation marker in title case, so `is_allcaps` went False
  and three of *Prayer and Praying Men*'s sixteen headings kept their numeral
  and stayed SHOUTING beside title-cased siblings from the same TOC. Judge caps
  on the heading with a trailing parenthetical removed. *(2026-08)*

### Verifying a change to shared import logic (the method that works)

- **Isolate your change from upstream drift** by running the OLD and NEW
  predicate over the SAME freshly-fetched HTML for every CCEL book and diffing
  the *decisions*. Reasoning about blast radius is not enough — do this.
- **For a `clean_title` change, measure the corpus BASELINE both ways**: count
  the stored titles `clean_title` would change on `main`, then on your branch.
  The delta is your change; the baseline is pre-existing drift and is not your
  problem (it was 28, then 273 once the arabic rule landed).
- **Replicate the REAL code path, not a simplified one.** A hand-rolled harness
  said the section-ordering fix would reorder two shipped books; running it
  through the actual `toc_parts` (which drops part dividers via `_parent_urls`)
  showed it changes nothing for them. The cruder check was wrong in the
  dangerous direction. Chapter order is a public contract — `PlanDay`, saved
  positions, prerendered URLs — so settle it against the real path.
- **`audit_english <slug>` reads the committed FIXTURE, not your DB**, so it
  reports "0 findings" for a freshly imported book until you write the fixture.
  Inspect with `english_audit.audit_book(book)` before that point.
- Recurring audit FALSE positives, all faithful to the source: a spaced ellipsis
  ("the Holy One . . . .") as `space-before-punct`; a real but corpus-rare word
  as `word-fusion` ("soother" read as "so"+"other"); and "box car letters" in a
  1921 book as an `anachronism` on "car". Repair only what is genuinely fused
  ("call fromheaven", "religion isthat" — both present in CCEL's own text) and
  pin the rest with `audit_english --update-baseline`.

### Two working-practice traps this loop hit

- **`git stash` on a CLEAN tree is a no-op, so a following `git stash pop` pops
  somebody ELSE's stash.** Stashing to compare against `main` is a natural move
  during a review; if everything is already committed there is nothing to stash,
  and the pop landed an unrelated `fix/slash-followups` stash as conflict markers
  in two frontend files. Use `git stash -u` and CHECK it created an entry, or
  better, compare with `git show main:<path>` / a detached worktree instead.
- **A parallel session may ship your author or catalog entry from the other
  side while you are in review.** Rebase onto their commits and keep theirs
  where both had an answer — then RE-IMPORT so the book row takes their catalog
  values, and rewrite the fixture. `seed_books` syncs `subtitle`/`cover_color`
  FROM THE FIXTURE, so a fixture left on your values has each deploy asserting
  one subtitle and each re-import the other. Redraw the plate and its og twin
  after, since both encode the subtitle. *(#1166 vs #1170, 2026-08)*

## Adding a public-domain book NOT on ochorus.com

**For a TRANSLATED work, the translation is the thing that must be PD — and CCEL
hosts in-copyright ones.** An ancient author guarantees nothing: CCEL's
`augustine/confessions` is Albert Outler's translation, **first published 1955**,
hosted there by the copyright holder's permission — permission that does not
extend to us. The PD alternative sat one slug away: `augustine/confess`, Pusey's
1838 translation. Both are "Augustine's Confessions" on the same site. Before
importing any translated work (the Fathers, à Kempis, Guyon, anything not
originally English), open a section page and read the title page for the
translator and date:
```bash
curl -s https://ccel.org/ccel/<ref>/<work>.i.html | sed 's/<[^>]*>/ /g' | grep -iE "translat|copyright|first published"
```
A translator's name with a 20th-century date means stop. Record the translator in
the book's `subtitle` and `attribution` so the next person can see which edition
this is without re-deriving it. *(Confessions, 2026-07)*

**NO named translator is also a stop for a translated work.** CCEL's Bernard
`bernard/loving_god` is a Fordham Internet Medieval Sourcebook e-text ("Made
available… by Paul Halsall") with no translator or date anywhere — and the only
modern edition it could be, Robert Walton's (Cistercian Fathers Series, 1970s),
is in copyright. Unverifiable provenance is not clearance: fall back to a dated,
pre-1929 edition you CAN name (the Patmore 1881/1884 translation on the Internet
Archive, `saintbernardlove00bernuoft`, records NOT_IN_COPYRIGHT). *(On Loving
God, 2026-08)*

**A Gutenberg ebook id can be an AUDIOBOOK — no text to import.** `#21152` "On
Loving God" is a LibriVox recording: its `/files/` holds only `m4b`/`mp3`/`ogg`
zips, and every `import_gutenberg` fetch URL 404s. Before adding a Gutenberg
`BookEntry`, open `gutenberg.org/ebooks/<id>` and confirm an HTML/txt format
exists; a lone audiobook means look elsewhere for the text. *(2026-08)*

**A curated ANTHOLOGY — one book compiled from many individual sermon pages
across volumes — fits no single-work importer.** `import_ccel`/`import_web` each
take ONE `source_ref` (a work TOC or a single URL); a book gathering, say,
twelve Spurgeon sermons from twelve different Pulpit volumes can't be a
`catalog.BookEntry` without breaking that one-source invariant. Don't force it
into the catalog. Instead:
- **Seeding is fixture-driven, so no `catalog.BOOKS` entry is needed.**
  `seed_books` reads `fixtures/content/books/<slug>.en.json`, not `BOOKS`, and
  creates the book with its chapters on deploy. The fixture is the whole
  deliverable; the catalog is just dev import-input.
- **Write a one-purpose `build_<name>` management command** that holds the
  ordered `(title, ccel_url, expected_ref)` list + an editorial intro as module
  constants, and REUSES `import_sermons.extract(fetch(url))` for the clean CCEL
  sermon body (masthead stripped, scripture kept as a `<blockquote>`).
  `extract()` returns `(body, scripture_ref, preached_on)` — assert `body`'s ref
  `startswith` your expected prefix to catch a wrong leaf URL (CCEL's scripRef is
  sometimes terser than the verse: `1 John 3` for 3:22–24, `Jude` for 20).
- **Store the SETTLED form.** Wrap each body in
  `corrections.settled_chapter_body(slug, order, body)` (NOT bare
  `apply_body_corrections`) — the deploy re-applies the settled form (+ trailing
  page-number strip), so a fixture built without it churns on every seed. Create
  chapters through `Chapter.objects.create` (per-row, so `save()` derives
  `body_text`/`word_count`/`search_vector`); don't `bulk_create`, don't pass
  `word_count`. Put `source_type`/`is_published`/`sort_order` in
  `create_defaults` only. Wrap `handle()` in `@transaction.atomic` and raise
  `CommandError` (not `return`) on a short body, so an abort can't leave a
  partial book — and inside an `except` clause chain it `... from None`, or ruff
  B904 fails CI. `sort_order` isn't derivable from `BOOKS` — hardcode `max+1`.
- **Then run the standard new-book finish:** serialize the row to the fixture
  (Django serializer, `indent=1`, natural keys — NOT `json.dump(indent=1)`,
  which indents the top-level list and every sibling fixture does not);
  `scripts/normalize_quotes.py <slug>` then `manage.py rederive_body_text
  --write` (early CCEL volumes mix straight + curly quotes, tripping a
  `tests_fixture` gate); `manage.py generate_covers <slug>` then
  `cd frontend && npm run og:covers` for the required raster twin. The house
  cover's emblem comes from the book's TOPIC (`topic_seed.py` +
  `covers.emblem_for_book`) — add the slug to the fitting topic to get an emblem
  (and the right shelf) rather than a blank ground.
- **Faithful vs. defect:** early sermons (New Park Street era) genuinely run
  long paragraphs and use running multi-paragraph quotes — `lost-paragraphing`
  and `orphan-close-quote` on them are FALSE positives; baseline them with
  `audit_english --update-baseline` (whole-corpus; diff the baseline JSON to
  confirm only your work's entry moved). Fix only unambiguous OCR slips via
  `corrections.py`.
If a SECOND such anthology ever appears, THEN lift the URL list into a catalog
sidecar consumed by a shared importer — one is bespoke, two is a pattern.
*(Mighty Power in Prayer — 12 Spurgeon sermons on prayer, 2026-08)*

**Vet US public-domain status by PUBLICATION year, not author death.** A work
first published before 1929 is US-PD regardless of when the author died — and a
long-lived author can have both PD and still-copyrighted books. Amy Carmichael
(d. 1951): *Things as They Are* (1903) is safe; *If*, *Gold Cord*, *Rose from
Brier* (1930s–40s) are very likely still under US copyright. Pick an early
edition; when a "restored/complete" modern reprint exists (e.g. Finney's
*Memoirs*), use the original pre-1929 scan, not the copyrighted reprint.

**Decide Book vs Sermon by STRUCTURE, not by the word "addresses".** Many
preachers' PD corpus is collections of addresses, and the two shapes import
differently. Hudson Taylor is the worked example: *Separation and Service* (1898,
PG 26384) is described as addresses but is one continuous ~57k-word exposition of
Numbers 6–7 across 30 short sections — that is a **book**, and importing its
sections as sermons would file a book's chapters on the sermon shelf. *A Ribband
of Blue* (1899, PG 23438) is eight self-contained studies of 2–8k words, each on
its own passage — those are **sermons**. The test: does the piece stand alone with
its own text and argument, or does it depend on the previous section? Sermon-shelf
entries also want a real `scripture_ref`; a section titled "The Burnt-Offering"
that continues the last one has no standalone reference to give. Check the length
distribution too — existing sermons run ~1,000–8,300 words, so a 57k-word "set of
addresses" is a book by size alone. *(Taylor sermon sourcing, 2026-08)*

When the catalogue lacks a wanted title (e.g. more Spurgeon), source it from
elsewhere. Preference order — cleaner text first: **CCEL** (`source="ccel"`,
`<author>/<work>` path) → **Project Gutenberg** (`source="gutenberg"`, ebook id)
→ **arbitrary web** (`source="web"`, per-chapter URLs in `catalog.WEB_CHAPTERS`,
`import_web`) → **Internet Archive OCR** (`source="archive"`, item id,
`import_archive`). The first two are transcription-clean; Archive is an OCR text
layer and needs a cleanup/verify pass (see below). **Wikisource caveat:** a work
can be only partially transcribed — Clarke's *Susanna Wesley* lists 16 chapters
but Wikisource has only 5, so it would import as a truncated book. Always count
the transcribed chapters against the work's own TOC before choosing it.

1. Add a `BookEntry` to `library/catalog.py`. For CCEL, first check the TOC
   section count — `inspect`/curl `<work>.toc.html`; 10–40 sections is good, 2
   means it won't chapter well (skip), Gutenberg books with no headings import as
   one giant chapter (skip).
2. Import: `import_ccel <slug>` / `import_gutenberg <slug>` / `import_web <slug>`
   / `import_archive <slug>` (all read `catalog.py`, not ochorus.com).
3. **Consolidate the author.** These importers create an author from the catalog
   slug; reassign the new book(s) to the canonical DB author (e.g.
   `charles-h-spurgeon`) and delete the duplicate, so they group correctly on the
   shelf and share one bio.
4. **Generate a cover** — CCEL/Gutenberg books have none:
   `python manage.py generate_covers <slug> ...` writes a house-style SVG and
   sets `cover_url`. Three things to know:
   - **Per language.** English writes `covers/<slug>.svg`; every other language
     writes `covers/<lang>/<slug>.svg`, from THAT row's translated title.
   - **It only sets `cover_url` in the DB**, which is enough here because the
     fixture is dumped from that row a few steps later (§Ship). It is NOT enough
     for a book that already shipped: `seed_books` re-asserts `cover_url` from
     the committed fixture every deploy, so for an existing work — a new
     translation, or a locale still wearing the English cover — run
     `uv run python scripts/localize_covers.py <slug>` instead. That draws the
     cover in each language (including recompositing a curated painting under
     the translated title) and repoints the fixture rows, which is the half
     `generate_covers` cannot reach.
   - **It never overwrites artwork.** A row whose `cover_url` is `.jpg`/`.png`
     is skipped even under `--force`; `--force` means "redraw the generated
     ones". Safe to run over the whole library.
   - `--dry-run` reports what would change. The drawing lives in
     `library/covers.py`, the file/row handling in the command.
5. **Flagship titles get real artwork** (optional). Add the slug to
   `library/curated_art.py` and run `python manage.py build_curated_covers
   <slug>`: it pulls a public-domain image from the Met, crops it, and
   composites the same house-style type over it, once per language. Two rules
   that the manifest's docstring explains at length and that are easy to get
   wrong:
   - **Landscape, architecture, sky, water, path — no figurative devotional
     painting.** The Met's religious holdings are overwhelmingly Catholic and
     medieval; a saint or Madonna sits wrong on a Protestant evangelical
     classic. The first pass returned Barocci's *Saint Francis* for a Moody
     revival book.
   - **Never a portrait standing in for a named person.** A portrait on a
     cover reads as a portrait OF that person. Susanna Wesley is excluded for
     exactly this reason, with a test asserting it.

   Licence comes from the Met's `isPublicDomain` flag, re-checked at download
   rather than trusted from the manifest — so use the Met (or another source
   with a per-object licence flag), not a general image search.

## Two kinds of fix

- **Improve the importer** (`import_ochorus.py`) when the pattern recurs across
  books — that's the durable win. Always re-check the sample for regressions.
- **Per-book correction** (`library/corrections.py`) when a book has a quirk the
  heuristics genuinely can't infer (e.g. a chapter whose title is inline in the
  PDF). Keep these few and specific; they're applied on every re-import. Example:
  Normal Christian Life ch12 → "The Cross and the Soul Life".

## Adding a NEW book from the catalog (not ochorus.com)

`catalog.py` declares books with a `source` — `ccel` / `gutenberg` / `pdf` /
`web` / `archive` — each with its own importer (`import_ccel`, `import_pdf`, …).
A title can be **declared in the catalog but never imported**: check
`library/fixtures/content/books/<slug>.en.json` before assuming it's missing.
Also check the catalog before scraping — a book absent from ochorus.com (whose
`/books/<slug>/` soft-404s with a 200 and no `<title>`) is often already
declared against a CCEL or PDF source.

A brand-new book needs **no data migration**: the deploy's `manage.py release`
runs `seed_books`, which creates a new book *with its chapters* straight from
the fixture (and is a clean no-op on re-run). Prove it before shipping by
seeding a scratch DB from every fixture EXCEPT the new one, then running
`seed_books`. Two things the importers do NOT give a new book, both caught late:

- **`description`** — every other book has one; without it the book page falls
  back to the author bio. Write it from the book's own preface, not memory.
- **`cover_url`** — run `manage.py generate_covers <slug>`, then **regenerate
  the og:image twin**: `library.tests_fixture` fails for a cover that cannot be
  its own share card (social scrapers reject SVG, and a `covers/art/` painting
  carries no words). From `frontend/`:
  ```bash
  npm run og:covers          # writes only the twins whose bytes changed
  ```
  This replaces an ad-hoc resvg one-liner that used to live here, and the
  one-liner is why the committed twins went a design generation stale: it
  rendered with `loadSystemFonts`, so the type came out in whatever serif the
  machine had, and nothing re-ran it when the cover design changed. The gate can
  only see that a twin EXISTS, never that it is current — so run this whenever a
  cover, title or subtitle changes, not only when adding a book.

**`regen_fixture.py` will NOT pick your new book up — write its fixture file
yourself.** The script is a fixture→fixture round-trip (fresh scratch DB →
`loaddata` every committed fixture → `dumpdata`); it never reads your dev DB, so
a freshly imported book is simply absent from its output and the import silently
ships as nothing. Serialize the book yourself, then re-run the regen to
canonicalise the formatting and prove the file loads:
```bash
DJANGO_DEBUG=true uv run python manage.py shell -c "
import json; from django.core import serializers; from library.models import Book
b = Book.objects.get(slug='SLUG', language='en')
rows = json.loads(serializers.serialize('json', [b, *b.chapters.order_by('order')],
    use_natural_primary_keys=True, use_natural_foreign_keys=True))
for r in rows: r.pop('pk', None)
open('library/fixtures/content/books/SLUG.en.json','w').write(
    json.dumps(rows, ensure_ascii=False, indent=1) + '\n')"
DJANGO_DEBUG=true uv run python scripts/regen_fixture.py   # rewrites it in dumpdata style
```
The second step matters for more than tidiness: `json.dump(indent=1)` indents the
top-level list items and `dumpdata` does not, so skipping it commits a file that
differs from every other fixture. If the regen aborts, that is a pre-existing
field-drift problem and NOT your import: see the `N unexpected new field(s)`
entry above. *(Confessions, 2026-07)*

**ochorus.com no longer serves `/pdfs/<slug>.pdf`** (404 as of 2026-07) — every
`import_ochorus` re-import fails at the fetch. It fails safely, leaving existing
rows untouched, but it means the ochorus-sourced books are effectively frozen:
the skill's "re-import a few diverse books" regression step can no longer run.
Regression-test `chapterize` changes against the `pdf`-source books instead
(`import_pdf the-gospel-of-healing` — diff titles + word counts), and prefer
changes that can only fire where the old code produced nothing.

**Regression-testing a change to shared cleaning (`ingest.DROP_SELECTORS`,
`clean_html`, `toc_sections`) without re-importing the library:** re-importing
every book pollutes the dev DB and its fixtures with unrelated drift, and a
fresh CCEL fetch differs from the committed fixture anyway (content drifts
upstream — `till_he_come` was 13 words off before any change of mine). Two
cheaper, sharper checks:

1. **Isolate the change from upstream drift** by running the OLD and NEW logic
   against the same freshly-fetched page and diffing the *outputs* — for a
   `toc_sections` change, build both section lists in one throwaway script and
   assert the URL lists are identical for every existing CCEL work.
2. **Re-import one book that the change is most likely to break**, then compare
   to its committed fixture body-by-body. Byte-identical is the bar. (Murray's
   *Waiting on God* is the sensitive one for heading logic — it is the book
   `fold_leading_heading` exists for.)

Ship only the new book's fixture file. A one-line `updated_at` churn in an
otherwise identical fixture is noise — `git checkout` it.

**A word-count GAIN against the fixture is a failure signal, not good news.**
The instinct is to read "recovered content" as a win, but for a
furniture-stripping change it usually means the rule stopped matching real
furniture. Tightening the trailing-nav guard made Simpson's *Himself* come back
three words heavier; the three words were `Back to Biblebelievers.com`. Diff
what appeared before congratulating yourself — the byte comparison catches
loosening as readily as breakage, in both directions.

**Furniture regexes over-match devotional prose, because the phrases are
ordinary English.** The trailing-nav rule matched any closing paragraph
containing "back to" or "return to", which silently deleted `Return to the LORD
thy God` (Joel 2:13), `Return to me, saith the LORD of hosts` (Zechariah 1:3),
and any preacher's `Back to our text, then…`. No error, just a missing last
line. Before shipping a furniture pattern, run it against a handful of real
sentences that *legitimately* contain the phrase — scripture first. The fix
shape: require the phrase to also name what it points at (`import_web.NAV_TARGET`
— a section word or a bare domain), and leave self-identifying phrases like
"table of contents" unguarded.

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
