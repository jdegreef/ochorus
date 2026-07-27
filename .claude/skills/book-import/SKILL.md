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
- **OCR letter-splits** ("blesse d!", "lif e.", "conversatio n.") and
  **image-drop-cap first letters** lost from the text layer: recorded as
  explicit literal pairs / letters in `corrections.py` `BODY_CORRECTIONS`
  (never a clever regex — "Song i." is a citation, not an error), applied on
  every import by both importer paths and backfillable over stored rows via
  `manage.py apply_body_corrections`. *(around-the-wicket-gate all 11 caps +
  13 OCR pairs across 6 books, 2026-07)*
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
  `photo_url` / years are fill-only. So writing a real biography into
  `authors.json` now reaches prod on its own — it no longer needs a
  hand-written per-author data migration the way 0049/0051/0052/0053 did. *(hit amy-carmichael, f-b-meyer, susanna-wesley, george-muller,
  andrew-murray before the fix)*
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

## Adding a public-domain book NOT on ochorus.com

**Vet US public-domain status by PUBLICATION year, not author death.** A work
first published before 1929 is US-PD regardless of when the author died — and a
long-lived author can have both PD and still-copyrighted books. Amy Carmichael
(d. 1951): *Things as They Are* (1903) is safe; *If*, *Gold Cord*, *Rose from
Brier* (1930s–40s) are very likely still under US copyright. Pick an early
edition; when a "restored/complete" modern reprint exists (e.g. Finney's
*Memoirs*), use the original pre-1929 scan, not the copyrighted reprint.

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
   `python manage.py generate_covers <slug> ...` writes an on-brand SVG to
   `frontend/static/covers/<slug>.svg` and sets `cover_url`.

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
- **`cover_url`** — run `manage.py generate_covers <slug>`, then **rasterize a
  600×800 PNG twin**: `library.tests_fixture` fails with "generated SVG cover
  without its .png twin" (social scrapers reject SVG og:images). No committed
  script; from `frontend/`:
  ```bash
  npm i -D --no-save @resvg/resvg-js   # --no-save: not an app dep
  node -e "const{Resvg}=require('@resvg/resvg-js'),f=require('fs');for(const s of ['SLUG']){f.writeFileSync('static/covers/'+s+'.png',new Resvg(f.readFileSync('static/covers/'+s+'.svg','utf8'),{fitTo:{mode:'width',value:600},font:{loadSystemFonts:true}}).render().asPng())}"
  ```

Get the new book into the fixture with `scripts/regen_fixture.py` — it picks up
a new book from the dev DB along with everything else. If it aborts, that is a
pre-existing field-drift problem and NOT your import: see the
`N unexpected new field(s)` entry above rather than hand-writing the file.

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
