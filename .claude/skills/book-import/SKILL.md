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

6. **Write the book's fixture file and commit.** `regen_fixture.py` does NOT
   pick up a new import (it round-trips the committed fixtures and never reads
   your dev DB) — serialize the book to `books/<slug>.<lang>.json` yourself; see
   "`regen_fixture.py` will NOT pick your new book up" below. NEVER bare
   `dumpdata library`. A regen afterwards is an optional check: it is
   byte-stable, so on a healthy fixture it leaves `git status` clean. If it
   aborts with `N unexpected new field(s)`, that's not your import — see the
   fixture-regen entry under Known failure modes.

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
- **Lone footnote-marker superscripts left after the note is gone** — a
  non-CCEL source (an ochorus.com PDF) has no `note` class to drop, so a
  reference superscript survives as unstyled residue pointing at a note that
  was never extracted: `<sup></sup>` (number lost) or `<sup>4</sup>`. It is junk
  for the eye and reads aloud as "…grace FOUR" for the ear.
  `corrections.strip_footnote_markers` (a corpus-wide rule inside
  `apply_body_corrections`, so it runs on import AND on every deploy) removes the
  LONE ones. It deliberately leaves a WELDED footnote alone
  (`<sup>1</sup><sup>1</sup>Note…`, the `welded-footnote` class — repair those
  per work) and never touches inline `[1]`/`[a]` brackets, which are usually the
  author's enumeration and stay as content. After it lands you must bring the
  committed fixture in line: `normalize_english_fixture --write`, then
  `rederive_body_text --write` and `rederive_word_count --write`. *(2026-09)*
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
  plans; and CHECK TRANSLATION PARITY: a book with translations must keep the
  SAME chapter count and order in every language — `tests_translation_markup`
  compares English chapter-for-chapter against each translation, and the reader's
  hreflang assumes `/books/<slug>/<N>/` resolves in every locale a chapter
  exists in. So adding/removing/reordering an English chapter of a translated
  book breaks parity unless you make the same change in every language
  (translating any new chapter — which ships unreviewed) or register the gap in
  `tests_translation_markup.KNOWN_CHAPTER_GAPS`. This is why the on-site
  `talks-to-the-farmer` was left one chapter short of the Gutenberg edition
  rather than "completed" with `Meal-Time in the Cornfields`). Pattern:
  `0009_rechapterize_bio_collections`. Ship only books that
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
- **A Gutenberg `<h3>Transcriber's Notes</h3>` block leaks into the LAST
  chapter.** The trailing transcriber note is an `<h3>` nested inside the final
  `<h2>` chapter (below the tag `split_by_heading` split on), so it is never its
  own section and `is_front_matter` never sees it — it rides in the last
  chapter's body, and its stripped page refs ("On page ,") show up as
  `space-before-punct`. Fix per-book: a `BODY_CORRECTIONS` replacement removing
  the exact `<h3>Transcriber's Notes</h3>…` trailing string (capture the bytes
  from the DB rather than hand-typing the curly quotes). Common enough across
  Gutenberg editions that a general ingest strip may be worth it if it recurs.
  *(ministry-of-intercession, 2026-09)*
- **A Gutenberg edition can set an ornamental `<div class="chaptertitle">CHAPTER
  N</div>` ABOVE the real `<h2>` title**, so the h2 is borrowed correctly but the
  bare "CHAPTER N" label leaks in and every body opens "CHAPTER 1 …". Fixed in
  `sanitize.DROP_SELECTORS` by adding `.chaptertitle`, **qualified by a
  `KEEP_PREDICATE`** (`_is_not_bare_chapter_label`) so it drops only a div whose
  whole text is a bare `chapter|part|book [numeral]` label and never a real
  title. **The numeral guard must use a STRICT roman** (the `ingest._ROMAN_WORD`
  construction), never `[ivxlcdm]+` — that class also spells "civil"/"mill"/"did",
  so a real `.chaptertitle` title reducing to "Part Civil" would be wrongly
  dropped (caught in code review). Also: Hurlbut's Preface is genuine front
  matter `is_front_matter` won't drop (the skill deliberately keeps "Preface");
  for a NEW book, delete that chapter in the DB and renumber before serializing
  the fixture rather than adding a blanket rule. *(hurlbuts-life-of-christ,
  Gutenberg #40460, 104 ch, 2026-09)*
- **This-edition-only chapter titles live in the CONTENTS, not the chapter
  openings.** Some Gutenberg editions (e.g. Murray #29296) open each chapter
  with a bare "CHAPTER N" then the scripture epigraph — no descriptive title in
  the body at all — so every core chapter imports untitled. The titles are in
  the Contents table (as ALL-CAPS text beside page-number links); read them from
  there and supply a per-book `chapter_titles`. *(2026-09)*
- **An extract collection (many tiny standalone pieces) → thematic chapters via
  a one-off build script, NOT the importer.** Spurgeon's *Gleanings Among the
  Sheaves* (#42657) is 146 short titled extracts with no grouping;
  `import_gutenberg` makes 146 flat chapters or (worse) drops them all under the
  300-word `_TINY_SECTION_WORDS` filter that `extract_chapters` applies. Instead
  write a committed build script (`scripts/build_gleanings.py` is the model):
  reuse `split_by_heading(root, "h3")` — which cleans each body with
  `clean_fragment` but does NOT stub-filter — apply a title→theme mapping (the
  editorial content, kept in the script for reproducibility), and upsert the
  Book + N chapters through the model, each chapter concatenating its extracts
  as `<h3>{title}</h3>{body}` in source order. **Give it NO `catalog.py` entry**,
  or a stray `import_gutenberg <slug>` re-imports it flat and clobbers the
  grouping. Two gotchas: `RestatedChapterHeadingTests` fails if a chapter opens
  with an `<h3>` that repeats its own title, so order any extract whose title
  equals the theme LAST (a stable sort on `title.casefold() == theme.casefold()`
  does it); and lint runs in CI before the tests — `ruff check scripts/<file>.py`
  locally, the seeds/gates don't catch C408 (`dict()` → literal) etc. *(2026-09)*
- **The OPPOSITE shape — one heading over a huge undivided section (a long
  journal/diary) → split into reading chapters via a `build_<name>` command.**
  Jarena Lee's *Religious Experience and Journal* (Gutenberg #66953) has three
  authorial headings, and the third runs unbroken through her whole 44k-word
  travelling journal — one endless scroll on a phone. `extract_chapters` gives
  the three clean sections; the build command keeps the short ones and splits the
  long one into ~7k-word chapters at block boundaries, folding a short tail back.
  Two things earned the hard way: (1) **split on ALL top-level blocks, not just
  `<p>`** — a `re.findall(r'<p>.*?</p>')` split silently DROPPED 746 words of the
  hymns she quotes in `<blockquote>`; iterate `BeautifulSoup(body).children`
  instead and assert word-count parity with the source before trusting it.
  (2) Title the chunks **`Part I/II/…` (a `_roman(n)` generator, not a fixed
  list), not year-ranges** — a diarist who recounts past and future years within
  one entry makes min/max-year titles overlap and mislead; Part N is honest, and
  duplicate bare "The Journal" titles trip `qa.duplicate_title`. A brand-new
  author arriving WITH a book needs NO migration — `seed_books` `get_or_create`s
  the author from `authors.json` (full bio and all) while creating the book;
  verify the prod path by deleting both from the dev DB and running `seed_books`.
  *(religious-experience-and-journal, 2026-09)*
- **A VERSE collection (a hymnbook / children's songs) → a `build_<name>` that
  splits on the song markers and PRESERVES the stanzas.** Isaac Watts's *Divine
  Songs* (Gutenberg #13439) marks each song as a `<p>Song N. <i>Title</i></p>`
  line (NOT a heading), then one `<p>` per stanza with lines separated by `<br>`.
  Split on the `Song N.` markers, group the songs into a few reading chapters,
  and render each as `<h3>{title}</h3>` + its stanza `<p>`s. Keep the verse
  intact: `<br>` and `<p>` survive `clean_fragment` (both in the sanitizer
  allowlist — a `<br>`-only block is dropped, but a stanza has text so it stays),
  so line and stanza breaks come through — do NOT reflow verse to prose. Watch
  the tail: this edition appends a CCEL *addendum* of later moral songs (with
  metre notation like `12,8,12,8`) after a transcriber note — detect the note
  ("addendum"/"ccel") and stop before it, shipping only Watts's original text. A
  brand-new author (Isaac Watts) needs only an `authors.json` entry appended
  (byte-clean: `json.dumps(o, indent=2, ensure_ascii=False)+"\n"` round-trips it)
  — `seed_books` get_or_creates from it, no migration. `build_divine_songs` is
  the model. *(divine-songs-for-children, 2026-09)*
- **An `is_published:false` book may be a COPYRIGHT hold, not a draft — check
  migration `0022_unpublish_copyrighted_books` before ever publishing or
  re-importing one.** `the-body-of-christ-teens` (a 1978 CFP Nee translation) and
  `if` (Carmichael 1938, URAA-restored to ~2033) are hidden on prod because they
  are still under US copyright, and their fixtures are MISLABELLED
  `source_type: public_domain`; `corrections.py` also excludes them from
  re-import. Publishing them (a fixture flip + a data migration — the very
  pattern 0022 uses to UNpublish) would put copyrighted content live. Don't. When
  a book is unpublished, find out WHY first. *(2026-09)*
- **A two-part CONTINUOUS NARRATIVE (an allegory/story with no chapters) → a
  `build_<name>` that splits on EPISODE anchor phrases, not word-count chunks.**
  Godolphin's *Pilgrim's Progress in Words of One Syllable* (Gutenberg #7088) is
  27k words under only PART I / PART II `<h2>`s — two endless scrolls. Unlike the
  Jarena Lee diary (arbitrary ~7k chunks), a beloved story wants its real
  episodes as chapters, and Godolphin KEPT Bunyan's proper names (Slough of
  Despond, Vanity Fair, Doubting Castle…), so define `CHAPTERS = [(title,
  opening-phrase), …]` and split by finding each anchor in `content_root(...)`'s
  `<p>` list IN ORDER (sequential search from the last boundary, so a repeated
  phrase only matches at its episode). Robust across Gutenberg's `-h.htm` vs
  `cache/epub` markup variants (which have DIFFERENT `<p>` indexing — anchors
  survive, absolute indices don't). Assert exactly N anchors found + a
  word-count-parity floor; skip divider `<p>`s ("END OF FIRST PART."). **Confirm
  the chapter list/titles with the founder before writing them** (a flagship
  book's structure is a lasting editorial artifact — `book-import` says to ask).
  This is a SEPARATE edition from the full original — new slug, same author
  (Bunyan), the retelling named in the subtitle. `build_pilgrims_progress_words`
  is the model. *(pilgrims-progress-words-of-one-syllable, 14 episode chapters,
  2026-09)*
- **A new-book gotcha: `cover_color` must clear WCAG AA for the white byline, or
  `tests_fixture.CoverAssetTests.test_plate_colours_can_carry_white_type` reds.**
  A warm mid-tone like `#b5791f` is only 3.51:1. Floor it with
  `covers.ink_safe(hex)` (→ `#99661a`, still warm) and store the floored value.
  The og twin's `ground` digest is independent of `cover_color`, so re-running
  `og:covers` after a colour change needs no manifest edit.
- **`og:covers` on macOS re-renders UNRELATED stale twins** (Playwright/font
  rendering differs from the canonical CI bytes), so a fresh-worktree run reports
  "wrote 5 of 279" when you added one. `coverOgManifest.test.ts` /
  `CoverAssetTests` only check each twin's `ground`/`style` digest (NOT the PNG
  bytes), so `git checkout` the unrelated PNGs (keep canonical bytes) and add ONLY
  your slug to `og-manifest.json`. **Do NOT `sorted()` the whole twins dict** to
  place your entry — parallel sessions append `fr/`/`pt/`/`sw/` twins out of
  order, so a re-sort is a huge spurious diff; insert your key in-place after its
  neighbour (`json.dumps(obj, indent=1, ensure_ascii=False)+"\n"` round-trips the
  committed file byte-for-byte). *(pilgrims-progress, 2026-09)*
- **Creating a genuinely NEW topic shelf (not just adding a book to one) is a
  regen QUARTET, or CI reds.** In `topic_seed.py`: the `TOPICS` entry (append
  LAST so no existing book's plate emblem shifts — the FIRST topic holding a book
  wins its emblem), `TRANSLATION_PENDING` (ship English-only, no 7-language
  prose), and a `TOPIC_SCRIPTURE` epigraph. In `frontend/`: a `TOPIC_META` entry
  (unique emblem, ≥3-colour art in `emblems.ts`) then `node
  scripts/generate-emblem-art.mjs` (topics.json + the `.svg`), `npm run
  emblem:hues` (emblemHues.ts), and `node scripts/generate-topic-og.mjs` (the
  share card `.png` + og-manifest — `TopicShareCardTests` fails without it).
  `TOPIC_QA` is optional. *(for-young-readers shelf, 2026-09)*
- **A calendar devotional with a MORNING and EVENING reading per day → two
  month-chaptered books from ONE source, via a `build_<name>` command.**
  Spurgeon's *Morning and Evening* is best known as its two separately-published
  halves — *Morning by Morning* (1866) and *Evening by Evening* (1868) — and
  Ochorus follows that split. Neither the catalog path nor `import_ccel` fits:
  the daily→month folding (`group_daily_entries`) lives ONLY in
  `import_gutenberg`, Gutenberg has none of Spurgeon's devotionals (checked
  Spurgeon/Meyer/Moody — Gutenberg is empty of them), and CCEL serves this work
  as ~730 per-reading leaves (`morneve.d0101am`/`…pm`) with no grouping AND one
  source must yield TWO books. So `build_morning_and_evening` fetches CCEL's
  single combined file — **`cache/<work>.html3`** (one 1.9 MB static HTML with
  every reading; far better than 730 leaf fetches; the `.txt` twin and the
  `Rights: Public Domain` line are there too), buckets each reading's blocks by
  its `d{MM}{DD}{am|pm}` id, splits AM→one book / PM→the other, and folds each
  half's 366 days into 12 month chapters (`<h3>January 1</h3>` + verse + reading)
  — the Simpson `days-of-heaven-upon-earth` shape. Three things earned:
  - **Bucket only BLOCK tags (`p/h2/h3/h4/blockquote`), never `find_all(id=True)`
    bare.** A nested `<a>`/`<span>` carries an id with the SAME reading prefix
    (the "Go To Evening Reading" cross-ref link, inline scripRefs), so an
    unfiltered bucket re-renders it as a stray paragraph. Filtering to block tags
    leaves those anchors inside their parent's inner HTML, where `clean_fragment`
    unwraps them.
  - The CCEL transcription is uniformly STRAIGHT-quoted; curl it with
    `quote_marks.convert(body, outer_guillemets=False)` + `assert_punctuation_only`
    baked into the build (NOT `convert_work`, which no-ops on an unmixed work) —
    the corpus uses curly double quotes and STRAIGHT apostrophes (Simpson: 324
    straight `'` vs 4 curly), so leave apostrophes alone. `--` em-dashes are left
    faithful (Spurgeon's own `cheque-book` ships 98 of them).
  - Attributed to the existing `charles-h-spurgeon` author (no migration); add
    both slugs to a `topic_seed` topic (put them with Simpson in
    `faith-and-guidance`) so the generated cover gets an emblem and the right
    shelf. Verse counts don't match reading counts (736 `scripPassage` vs 731
    `passage`) — some readings carry a ref with no verse or two refs — so the
    verse/ref folding must handle an orphan reference, not assume one-of-each.
  *(morning-by-morning + evening-by-evening, 2026-09)*
- **A calendar devotional whose day markers are a plain `<div class="date">`
  (not a heading) → a `build_<name>` splitting on those divs.** Moody's
  *Thoughts for the Quiet Hour* (Gutenberg #37292) marks each day
  `<div class="date">January 1st.</div>` — an ordinal date in a div — so
  `import_gutenberg`'s heading-splitter (and `group_daily_entries`, which needs a
  `January 1`-style heading *title*) chapters nothing. Reuse `import_gutenberg`'s
  `fetch_html` + `content_root` (fetch + PG-boilerplate strip), then walk the
  body splitting on the date divs. Four things earned, each caught by verifying
  day COUNT and spot-reading first/last/recovered days — never trust the build's
  own success line:
  - **A day's comment can live in a non-`<p>` container.** Five days' meditations
    are `<div class="poem">` (verse form), so a `<p>`-only collector silently
    dropped them (Jan 31 came out verse-only). Collect the poem divs too.
    Decorative divs (`figcenter`/`figright`) carry no text; front matter
    (`author`/`copyright`/`bbox`/`center` — the title page and Scripture index)
    all precedes the first date div, so a `current is None` gate drops it.
  - **`content_root` strips the LICENSE footer but NOT the trailing transcriber's
    note.** A `<div class="tnote">` + its `<p>`s sits after the last reading and
    rode into December 31. Close the current day (`current = None`) at the tnote.
  - **Date-marker OCR/period quirks:** old-style bare-`d` ordinals ("May 3d." =
    3rd — widen the ordinal alt to `st|nd|rd|th|d`) and a one-off month misread
    ("Match"→"March", a tiny startswith fixup). A genuinely ABSENT calendar day
    (Oct 3, marker jumps 2nd→4th) is left faithful, not invented — 364 readings.
  - Attributed to the existing `dwight-l-moody` author as the volume's *editor*
    (it is a compilation, each day bylined `—<i>Author.</i>` to its writer).
  *(thoughts-for-the-quiet-hour, 2026-09)*
- **Precept Austin (preceptaustin.org) hosts PD devotional text by month — a
  usable source when a work is calendar-shaped but not on CCEL/Gutenberg, but its
  markup is messy and carries its own study apparatus, so parse defensively.**
  Meyer's *Our Daily Walk* (1913) is on neither CCEL nor Gutenberg (Archive/
  HathiTrust had only a 1951 reprint stub); Precept serves it as twelve per-month
  pages, each day a bold theme + a bold scripture line + the meditation `<p>`s +
  Meyer's own closing "PRAYER … AMEN." Legal basis is the work's own PD year
  (judge by first publication, 1913), NOT the host's permission. `build_our_daily_walk`
  is the model; four things it earned the hard way:
  - **URLs are irregular and the month-nav is incomplete.** Suffixes are clipped
    unevenly (`_-_jan`/`_-_feb`/`_-_mar`/`_-_may`/`_-_aug`/`_-_oct`/`_-_nov`/`_-_dec`
    but `_-_june`/`_-_july`/`_-_sept` spelled long), and **April has no suffix at
    all — it lives at the bare slug `/our_daily_walk`**, absent from the on-page
    month list. Hardcode the 12 URLs explicitly; don't derive them.
  - **The body-field `<div>` is unusable as a content bound.** Precept's markup is
    malformed enough that both `html.parser` AND `lxml` leave the reading `<p>`s as
    siblings OUTSIDE `div.field--name-body` (it parses with zero `<p>` children).
    Parse the WHOLE document's `<p>`s instead, bounded by day markers.
  - **The day marker varies per page — use a hybrid.** Some months set the date as
    `<p><b>January 1</b></p>`, others as a bare `<b>January 1</b>` in a bordered
    box, and Precept OMITS the `<a name>` anchor on some days (April 2, Sept 22's
    heading). Detect a boundary as EITHER an `<a name="january 1">` anchor OR any
    `<b>`/`<p>` whose exact text is "January 1". A day genuinely absent from the
    transcription (Sept 22 — heading jumps 21→23) is left faithful, not invented.
  - **Precept decorates every scripture ref with its own commentary links —
    strip them.** `Php 3:13-note`, `Heb 12:1KJV-note`, `Col 3:3KJV`, and the
    hyphen can even carry a space (`21- notes`). Strip `-note`/`-notes`/`KJV`
    ANCHORED TO THE REF DIGIT so Meyer's own prose (`love-notes`, `key-note`)
    survives, tolerate `\s*` around the hyphen, and then close the space the
    suffix left before a comma/period. The "dry-run understates" trap bites here:
    a later pipeline step collapses `21- notes`→`21-notes`, so the regex must
    match the *pre-collapse* form seen at strip time, not the stored form. Drop
    the trailing on-page search widgets with a SPECIFIC guard (`^Search for
    comments`, not a bare `^Search ` — that would truncate a "Search me, O God…"
    meditation). Meyer's own "See …" cross-refs and Spurgeon mentions are prose,
    not apparatus, and stay. *(our-daily-walk, 2026-09)*
- **`npm run og:covers` rewrites any PRE-EXISTING stale twin it finds, not only
  your new book's — keep the PR focused.** A fresh run wrote my 2 twins AND
  redrew 4 unrelated `painting`-tier twins whose committed bytes had drifted from
  the current generator on `main`. Include only yours: `git checkout` the
  unrelated PNGs, then hand-add ONLY your slugs to `og-manifest.json` and
  re-serialize it the way the committed file is written — **`JSON.stringify(obj,
  null, 1)` (1-space indent), `twins` sorted by `localeCompare`** — NOT the
  generator's current `'\t'` output (main predates that switch, so a full run
  reformats the whole file). The manifest gate recomputes INPUT digests, not PNG
  bytes, so a hand-added entry with the right `ground`/`style`/`script`/`art`/
  `scrim` passes. *(2026-09)*
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
  - **When the work has NO internal part dividers, `group_parts` can't help** —
    a `part=`-extracted NPNF work like Augustine's *Enchiridion* is 124 tiny
    numbered sections under one implicit part, so `group_parts` fuses the whole
    thing into a single 35k-word chapter. Import it flat, then regroup with a
    committed build script keyed by editorial order-ranges: `GROUPS = [(title,
    lo, hi), …]` covering every raw section, each chapter concatenating its
    sections as `<h3>{section-title}</h3>{body}` through `clean_fragment`
    (`scripts/build_enchiridion.py` is the model — idempotent: reads the raw
    chapters, deletes, writes the grouped ones; asserts the raw count first; no
    `catalog.py` entry). Same `RestatedChapterHeading` and local-`ruff` cautions
    as the Gleanings build. **The trap (bit the Enchiridion, #1349):** an NPNF
    section body OPENS with its own running title, `<p>Chapter N.—<title>.</p>`,
    so wrapping it in an `<h3>` of the same title renders EVERY sub-heading
    twice. `RestatedChapterHeadingTests` only checks a chapter's *first* block
    against the chapter title, so it never sees the internal repeats — strip that
    leading title paragraph per section before concatenating, and eyeball the
    rendered sub-structure, not just the gates. *(2026-09)*
  - **When the sub-work IS a collection of works (each a real part divider),
    `group_parts=True` works — but keeps two things you don't want.** Cyprian's
    treatises are `schaff/anf05` under stem `iv.v`: `part="iv.v"` alone
    over-splits into 205 per-paragraph leaves; `group_parts=True` gives 13 clean
    chapters (one per treatise), but includes the ANF editor's trailing
    **"Elucidations"** (scholarly notes, not the author) and restates a redundant
    `<p>Treatise N.</p><p>Title.</p>` at each chapter head. Drop/strip both with a
    `build_<name>` command that reuses `import_ccel.toc_parts` + `extract_body`
    (skip `is_front_matter(part_title) or "elucidation" in part_title.lower()`;
    `re.sub` the head with `count=1` — do NOT `\A`-anchor it, because a multi-leaf
    part carries the head AFTER its first `<h3>` leaf subheading). Cyprian already
    had a bio+portrait, so no authors.json/migration — `seed_books` creates the
    book on the existing author. `build_cyprian_treatises` is the model.
    *(treatises-of-cyprian, 2026-09)*
  - **A SINGLE work out of a Schaff volume whose chapters are the leaves imports
    FLAT (no `group_parts`, no build command) — but its ANF "Chapter N.—<argument>"
    titles need three things to agree.** 1 Clement is `schaff/anf01`,
    `part="ii.ii"` (the chapter-level stem `anf01.ii.ii.<roman>`, I–LIX = 59
    chapters; the editors' Introductory Notice at `.ii.i` is gated out as front
    matter). Set **`summary_titles=True`** so each argument ("Chapter I.—The
    salutation. Praise of the Corinthians before the breaking forth of schism…")
    reduces to a readable lead clause ("The salutation"). Getting there fixed a
    latent break in shared logic, so it will "just work" now but know why: (1)
    `clean_title` only stripped a `Chapter N.` prefix when a SPACE followed the
    separator — ANF abuts the em-dash (`.—`), so `_CHAPTER_PREFIX` now also
    accepts a period/colon-then-dash; (2) once the title loses its `Chapter N.—`,
    `restates_title._compared` must set aside the SAME `chapter <counter>` word so
    the body's restated heading still matches the stripped title (extended
    `_LEAD_COUNTER`), or the argument heading leaks into the chapter body; (3)
    `_section_body`/`extract_body` must get the FULL clean title, so the loop
    summarises AFTER computing the body, not before. All three verified corpus-
    safe (re-import the sensitive CCEL books + `on-the-incarnation`, byte-diff vs
    committed fixtures — 0 changes except the deliberate one below). `summary_title`'s
    length cap can end a long single-clause argument mid-phrase ("…in it from",
    "…the priestly") — fix those few with `corrections.chapter_titles` (flat
    import, so order-keyed titles still reach them). *(first-epistle-of-clement,
    2026-09)*
  - **That same fix improves `on-the-incarnation` (the other `summary_titles`
    book) on its NEXT re-import** — the loop now strips the 56 restated
    `§1. Introductory.—…` argument headings it used to keep. Its shipped fixture
    is untouched (I didn't re-import it), so prod is unchanged; a deliberate
    re-import + a `0092`-style strip-restated-headings migration would ship that
    cleanup as its own change. *(2026-09)*
  - **A work in TWO RECENSIONS printed on the SAME leaf pages cannot be split by
    stem — find a single-recension source instead.** Ignatius's genuine seven
    epistles exist in a shorter (authentic) and longer (interpolated) recension,
    and CCEL's ANF `schaff/anf01` prints BOTH on every chapter leaf, one after
    the other, with no per-block label — so any `part=anf01.v.…` scope doubles
    every chapter (the shorter is always the first `<p>`, but "keep the first
    `<p>`" is fragile: some chapters are single-block, and a multi-paragraph
    shorter would truncate). The clean fix was a different PD translation:
    **CCEL `lightfoot/fathers`** (J. B. Lightfoot's *Apostolic Fathers*, d. 1889)
    gives the genuine seven as one clean single-recension page each
    (`fathers.ii.iii`–`fathers.ii.ix`), imported one-chapter-per-epistle with a
    `build_<name>` command. Note Lightfoot renders καθολικὴ (Smyrn. 8) as
    "universal Church," not "catholic" — match whatever the chosen translation
    says when you quote it elsewhere (e.g. in a bio or life chapter).
    *(epistles-of-ignatius, 2026-09)*
  - **A build command that mixes FETCHED text with ORIGINAL prose must commit the
    original in the repo, not read it from `/tmp`.** *The Epistles of Ignatius*
    opens with five hand-written "life story" chapters; the first cut read them
    from the `/tmp` scratch dir the writer wrote to, so the build aborted on any
    fresh checkout and the only surviving copy of that original prose was the
    generated fixture (caught in code review). Commit editorial source beside the
    command (`library/management/commands/data/<slug>/…`, read via
    `Path(__file__).resolve().parent / "data" / …`) — the same rule the Gleanings
    / Enchiridion builds follow by holding their editorial content as module
    constants. Fetched public-domain text can come off the wire; anything you
    wrote yourself has to be in the repo. *(epistles-of-ignatius, 2026-09)*
  - **A CCEL edition can open every chapter with a front-block `extract_body`
    can't clear, and carry editorial appendices `is_front_matter` doesn't drop —
    a `build_<name>` with a title filter + a custom leading-strip is the answer.**
    William Law's *A Serious Call* (`law/serious_call`) has both: (1) the TOC
    lists 24 "Chapter I."…"Chapter XXIV." leaves plus three editorial
    **Appendices** (Methuen/Everyman intros, an e-text note), an index and
    acknowledgements — none of them the author, and none caught by
    `is_front_matter` (they are neither Contents/Title/Index nor a part divider),
    so a plain `import_ccel` keeps them. Filter to the leaves whose title begins
    "Chapter". (2) Each chapter page opens with the **book title split across two
    `<h2>`s** ("A SERIOUS CALL TO" / "A DEVOUT AND HOLY LIFE"), an
    `<h3>CHAPTER N</h3>`, and the **chapter title restated as a `<p>`, not a
    heading** — `extract_body` strips none of it (a split title never restates the
    whole `book_title`, a title-in-a-`<p>` isn't a heading, and its loop *breaks*
    at the first heading that doesn't match). Write a `_chapter_body` that soups
    the node, drops `DROP_SELECTORS` furniture, then decomposes leading blocks
    while each is empty / `_is_ordinal_heading` / `restates_title(_, title)` / a
    normalized substring of the book title, up to the first real prose block.
    **Add a build-time self-check** — assert the finished body's text does NOT
    open with the chapter title or "chapter n" — so a future CCEL re-flow fails
    the build loudly instead of silently shipping a chapter that repeats its own
    heading. `build_serious_call` is the model. *(a-serious-call, 2026-09)*
  - **Fixing an ALREADY-SHIPPED book: a title/body fix is just a fixture edit;
    a chapter set that SHRINKS or RENUMBERS still needs a data migration.** Since
    2026-09-23 `seed_books` syncs an existing book's chapters by `order` on every
    deploy — updates drifted titles/bodies (settled form), appends new orders —
    but never deletes or renumbers (chapter `order` is a public contract). Before
    that it synced nothing and 379 fixture-only fixes sat unshipped. So a
    re-chapterize that drops/merges chapters still ships a migration (see
    `ship-content-fix`; `0134` is the model); anything else doesn't — and a
    chapter migration WITHOUT the fixture edit is reverted by `seed_books` in the
    same release. A fixture change triggers the web build, and the prebuild
    gate waits for the API to hold it. Still check the static page once. If it's
    stale, add a marker per `frontend/prerender-refresh/README.md` (a new file,
    never a comment in a shared `+page.ts`). *(2026-09)*
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
- **A CCEL TOC set in TITLE CASE keeps its roman prefix — that book needs a
  per-book `chapter_titles`.** The roman-prefix strip (and the "Of/To/With"
  downcasing) is deliberately ALL-CAPS-gated, because a mixed-case numeral can be
  part of the name (Murray's "I. Humility", "II. Timothy"), so a Title-Case TOC
  like Meyer's *guidance* ("III. The Secret Of Christ's Indwelling") sails through
  with the numeral intact — and the reader prints the chapter number itself, so it
  renders doubled ("3. III. …"). No general `clean_title` change can tell the
  redundant numeral from Murray's referential one; supply a `CORRECTIONS`
  `chapter_titles` for all N chapters (clean text, "Of/To/With" downcased, period
  spellings like "Fulness" kept). Since #1572 the titles you write must satisfy
  `titlecase.recase_title(t) == t` or `tests_fixture` reds — the little-word rule
  and the ALL-CAPS `is_title_case` gate are the same one. *(the-secret-of-guidance,
  2026-09)*
- **Re-importing to REPLACE a book stored as a damaged AI paraphrase** (a modern
  rewrite shipped in place of the PD original, ch. count often off because it
  dropped chapters — see the english-qa skill for how one is caught): add a CCEL
  `BookEntry`, `import_ccel <slug>`, then finish like any re-chapterization. Two
  things a re-import PRESERVES for free via `upsert_book` (it refreshes only
  title/subtitle/source_url/cover_color): a **designed/frozen cover** (`cover_url`
  is left alone, so the registered `.jpg` stays — nothing to redraw), and
  `description`/`publication_year`. But `publication_year` can be absent on the
  dev row (the seed didn't set it) — set it back before you serialize, and fix any
  stale "Contents:" footer in the description while you are there. Because the
  chapter COUNT changed, ship the chapters with a delete-and-recreate migration
  (0009/0123 shape), not just the fixture — `seed_books` never rewrites an existing
  book's chapters. *(the-secret-of-guidance 8→9 ch, 2026-09)*
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
  hand. Since 2026-07-26 `seed_books` / `seed_sermons` sync an existing
  author from `authors.json` on every deploy (`library/author_sync.py`), for
  every author in the fixture, not just those with a book. Since 2026-09-23
  `bio` and `bio_html` are **fixture-wins** (a non-empty fixture value replaces a
  differing live one; never blanked), so a stub is upgraded and a long-form bio
  replaced with no migration; `photo_url` / years stay fill-only. What it still
  does NOT cover: a **brand-new author with no book or sermon** is never CREATED
  by either seed (only updated), so adding one still needs a migration the way
  0053 did.
  Prerender caveat: author pages bake the bio at BUILD time, so the sync lands
  on the API first and the public page only picks it up on the next frontend
  deploy. *(hit amy-carmichael,
  f-b-meyer, susanna-wesley, george-muller, andrew-murray before the fix)*
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
- **A heavily-damaged Archive scan can need HUNDREDS of OCR fixes, and the
  standard `[A-Za-z]*[a-z][A-Z]` mixed-case scan MISSES whole classes.** Crowther's
  1855 Niger journal (`journalofexpedit00crow`) needed ~350: a stray `^` caret
  sprinkled into words, `r` read as an apostrophe (`fi'om`→from, straight AND
  curly), `h` read as `li` (`witli`→with, `tlie`→the ×17), `w` read as `Av`
  (`Avas`→was), `E`/`Il` read for `R`/`H` in names, and hyphen-split words.
  **Verify cleanup with a spellcheck scan against `/usr/share/dict/web2`, and do
  NOT exclude capitalized tokens** — the `Av…`/`Il…`/`E…`-prefixed garbles wear a
  spurious capital and masquerade as proper nouns, so a scan that skips
  capitalized words reports "pristine" while dozens remain. web2 lacks many
  inflections/British spellings (feet, replied, favour), so filter those, and an
  OCR-aware corrector (try `li→h`, `rn→m`, `di→h`, `ii→n`… and keep any single
  edit that yields a web2 word) auto-resolves the bulk; hand-resolve the rest
  from context. **Best signal a capitalized garble is real:** its correct twin
  dominates the same text (`Hamaruwa` ×37 vs `Ilamaruwa` ×7). **The `w`→`Av`
  class needs a sentence-aware fix** (the capital A is spurious, so capitalise the
  result only when it opens a sentence), not a case-preserving word map.
  **A residue of mis-scanned foreign PROPER NOUNS is left faithful to the print**
  — "correcting" a transliterated place name without a gazetteer invents. For a
  book the importer can't chapter at all, this lives in a `build_<name>` command
  (the anthology pattern below): reuse `import_archive`'s `_reflow`, split at
  verified anchors, hold the fix tables as module constants there rather than
  bloating `corrections.py`, and wrap the body in `clean_fragment(...)` before
  `settled_chapter_body`. Estimate generously and say so early — this scan was
  under-called twice. *(journal-of-an-expedition-up-the-niger, 2026-09)*
- **A cleaner Archive scan with intact CHAPTER markers but ILLEGIBLE title-lines
  → build_<name> that splits on markers in DOCUMENT ORDER and applies the TOC
  titles.** Julia Foote's *A Brand Plucked from the Fire* (`brandpluckedfrom00footrich`)
  chaptered fine in `import_archive` (~1 defect), but every decorative title-line
  OCR'd to garbage ("Tu", "public ||fllot|f") and two markers were mis-scanned
  romans — **"CHAPTER XL" for XI, "CHAPTER XXL" for XXI** — and since `_roman`
  reads "XL" as 40 the sequence check dropped one, merging a chapter (29 vs 30).
  Fix: match all `^CHAP(TER)?\s+[IVXLC]+\.?$` lines and split on their ORDER, not
  the parsed numeral (so the garbled romans still count); read the real titles
  from the book's own Contents. Three cleanups the audit does NOT flag (it sees
  real-looking words): (1) **line-wrap space-splits** — the scan drops the EOL
  hyphen, leaving a space inside a word ("fright ened", "chil dren"); rejoin the
  pair when `a+b` is a web2 word and the second fragment is NOT itself a word
  (this is precise — it never merges a real pair; the both-are-words cases like
  "per son"→person are hand-added and MUST be `\b`-anchored, or a bare replace
  fuses "harper songs"). (2) **letter-substitution mangles** ("Tor"→For,
  "clay"→day, "rne"→me, "pea<;e"→peace) — hand-fix from context. (3) **garbled
  title-lines that leaked** — skip them by the small-caps opener: chapters open
  "FROM this…"/"I WAS…", so after the marker skip lines until the first whose
  first two letters are both uppercase. Verify no content lost with a
  word-count-parity check (book ÷ raw-source-body ≈ 0.97; the missing ~3% is
  running headers + page numbers + markers, NOT prose). Verse/hymn reflows to
  prose paragraphs — words preserved, line breaks flattened (acceptable).
  *(a-brand-plucked-from-the-fire, 2026-09)*
- **An Archive scan whose chapters are headed by a BARE ROMAN NUMERAL (no
  "CHAPTER" word) → build_<name> that detects heads structurally, because the
  running header IS the chapter title.** Bounds's *Possibilities of Prayer*
  (`possibilitiesofp0000boun`) heads each chapter with a lone "I"/"II"/… line
  above an ALL-CAPS title, and repeats that title as the running header on every
  page — so the title alone can't mark a chapter (it appears 10× a chapter), and
  `import_archive._CHAPTER` matches only the word "CHAPTER", finding nothing. A
  head is therefore *a short roman-ish line whose next real line is an ALL-CAPS
  title that is NOT the running book-title header* (exclude a title containing
  the book name or led by a page number); split on those in DOCUMENT ORDER and
  apply the Contents titles, because the numerals are mis-scanned (`Ill` for III,
  a stray `V.`) and `_roman` would mis-order them. Four things earned here:
  - **The end-of-line hyphen is `¬` (U+00AC), not ASCII `-`**, so
    `import_archive._HYPHEN_EOL` never fires and "reason¬"/"able" reflows to
    "reason- able". Normalise a trailing `¬` to `-` per line before the reflow's
    hyphen-join (one line: `if line.endswith("¬"): line = line[:-1] + "-"`).
  - **A "(Continued)" chapter's title line is mixed-case**, so a plain
    `letters.isupper()` head-test drops chapters III/V/VI/XI/XII (16→11). Strip a
    trailing `\([^)]*\)` parenthetical before the caps test, and drop that same
    title line (and a lone "(Continued)" fragment) from the epigraph.
  - **The drop-cap prose opener is small-caps** ("WITHOUT the", "THE ministry")
    and is the reliable epigraph/prose boundary — title-case its first word;
    chapter I's ornamental cap mis-scanned to "P^HE" (→ "The"), a one-entry
    special case. Everything above it (minus headers) is the italic epigraph.
  - **Normalise straight↔curly quotes IN the build** with
    `library.quote_marks.convert_work(bodies, f"{slug}.en.json")` (the same
    context-sensitive logic migration 0084 uses), NOT the post-hoc
    `normalize_quotes.py` script — a build-command book is regenerated, so baking
    the conversion in keeps it idempotent and passes `QuoteStyleTests`. Note a
    LONG multi-verse Scripture quotation legitimately opens a `“` on every verse
    and closes only once, so an open>close imbalance is faithful, not a defect
    (`orphan-close-quote` only flags close-without-open). **But an imbalance with
    ZERO closers is scan damage, not scripture:** *The Bruised Reed*
    (`bwb_C0-AVW-616`) shipped 163 `‘` + 15 `“` and no `”` — margin rules that
    archive.org's own OCR text layer reads as openers (they are in the
    `_djvu.txt`, mostly at a line start), some standing where a letter was lost
    (`“he influence`). The `orphan-open-quote` audit class now flags the shape
    (a mid-sentence opener before a lowercase word, nothing closing it, at
    density) as the import finishes. Repair the lost-letter ones as pairs first;
    strip the rest from the stored ENGLISH rows in a migration (0138's shape),
    never as a `BODY_CORRECTIONS` transform — that reaches every language
    edition of the slug, and translations quote.
    **`import_archive` now prevents the bulk of it.** The mark's POSITION is
    the signal, and only the raw line has it: `_reflow` drops a line-initial
    `‘`/`“` before a letter (`_RULE_QUOTE`, next to `_BAR_RULE`) when the
    work's `part` slice closes no `”` — asked of the slice, since the same
    volume's front matter and other treatises close 23. On a re-import that
    takes the Bruised Reed from 163 marks to 11 and its audit from 133
    `orphan-open-quote` findings to clean (the other archive books import
    byte-identical). What still arrives: 10 MID-line marks, mostly after a
    sentence end ("bitterly. ‘This reed") — the reflow can't tell those from a
    quote — and `‘6.` before a digit. A digit is left on purpose: `‘0 all` is
    a lost "t" only a pair restores. So a 0138-style strip is still needed
    after a re-import, just a much smaller one. Stripping also
    removes the evidence a pair keys on: a lost-letter pair must be spelled
    as the importer now emits it (`believe ruth from truth`, with enough
    context that `old` is not inside `new`), which is why the Bruised Reed
    entry keeps both spellings for its 0138 group. **Any importer rule that
    changes raw text pre-empts pairs — find them, don't guess:** run the old
    and new `chapterize` on the saved `_djvu.txt`, apply the entry's pairs IN
    ORDER to each, and list the pairs that fire on old only. Mark-removed `old`
    == `new` → prune (it protects nothing now); otherwise re-spell it. But a
    DEPLOYED migration that calls `settled_chapter_body` (0134, 0138) reads
    `corrections.py` at run time, so a pair whose `old` is in the
    pre-change fixture (`git show <sha>^:…json`) must keep its spelling — add
    a twin instead. **Limit:** "no `”`" also holds for an edition that quotes
    with SINGLE marks only, and for a scan OCR'd with STRAIGHT double quotes
    (`susanna-wesley-clarke`, `on-loving-god` — harmless there, 0 curly `‘`);
    in either, a real line-initial `‘` before a letter would be eaten.
    Count the curly `‘` in the slice before trusting the rule.
    *(2026-09)*
    **Read every difference against a second printing, not just the non-words:**
    a spellcheck scan passes `derived rot God`, `eat the it of your own ways`,
    `go he hath bowels`. **PD gate: judge by the
    work's FIRST publication year (1923), never the Archive item's reprint date**
    (this scan is a 1979/1991 Baker reprint of the 1923 Revell text).
  *(possibilities-of-prayer, 2026-09; the whole HFP-triage sourcing note is why
  Weapon of Prayer — 1931, PD only in 2027 — was NOT the one imported.)*
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
  `DEFAULTED_OK` as a `(model, field)` pair; a default that would be WRONG in a
  fixture (e.g. a derived `word_count` that loaddata leaves at 0, which
  `tests_fixture` rejects) goes in `DROPPED_IF_ABSENT`. Then re-run — the regen
  is byte-stable, so it writes neither kind into rows that lacked them and
  should leave `git status` clean; only `--normalize` materializes the inert
  defaults across the corpus. (Fields declared `serialize=False`, like
  `search_vector`, never dump and are never the cause.) *(Sermon.summary, 61
  sermons, 2026-07; ten author/book/sermon fields + Article, 2026-09)*
- **`regen_fixture.py` aborts with `ROW COUNT CHANGED`** — a content model is
  missing from the script's `MODELS` (articles were, until #3135). Add it there
  with an `identity()` branch and a `split_layout` destination;
  `tests_fixture.test_regen_dumps_every_content_model` now catches this in CI.
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
  rewrites them (now `seed_books` itself syncs titles on deploy).
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

### Working-practice traps this loop hit

- **Edit a tracked skill file (or any repo file) in the WORKTREE you commit from,
  not the main checkout.** Appending these very notes to
  `~/dev/ochorus/.claude/skills/book-import/SKILL.md` (the main checkout, on some
  unrelated stale branch) while the book work lived in a worktree stranded every
  edit uncommitted there — it never entered the PR and would have been lost. Each
  worktree has its OWN copy of tracked files. Edit the worktree's copy and commit
  it into the book's PR; if you've already edited the wrong one, `git diff` it,
  `git apply` the patch in the worktree, and `git checkout` the main copy clean.
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
- **Two NEW-book PRs collide at the same `catalog.py`/`corrections.py`
  insertion points.** Adding books back-to-back off `origin/main`, each puts an
  `AuthorEntry` at the same slot (both anchored before `hudson-taylor`), a
  `BookEntry` after the same neighbour, and a `CORRECTIONS`/`BODY_CORRECTIONS`
  entry at the dict top — so whichever merges second conflicts in exactly those
  two files. The resolution is always **keep BOTH entries** (`git merge
  origin/main`, un-nest the two blocks, close each). To avoid it, merge each
  book's PR before starting the next, or anchor new entries at distinct
  neighbours. *(#1238 Guyon vs #1239 Bernard, 2026-08)*

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

**Adding a single STANDALONE sermon** (a `SermonEntry` in `sermon_catalog.py`,
one per work, `source` = `ccel` | `gutenberg` | `web`; `import_sermons <slug>`;
then serialize `fixtures/content/sermons/<slug>.en.json`). `seed_sermons` upserts
on every deploy — NO migration, and NO author stub when the author already
exists in `authors.json` (`_author` resolves the DB row first). Source-picking
gotchas found adding one sermon each for Chrysostom/Finney/Luther *(2026-09)*:
  - **CCEL serves SOME works only through its JS reader** — a raw fetch of
    Finney's `ccel/finney/sermons/…` returns a 20 KB "loading" shell, 0 words,
    while Spurgeon/Wesley pages return full static HTML. When a CCEL sermon
    imports as 0 words, fetch the URL and check for `<title>loading` before
    blaming the extractor; fall back to a `web` source (gospeltruth.net carries
    Finney, already the source for Catherine Booth).
  - **A collected volume with PAGE-NUMBERED headings doesn't fit the gutenberg
    section matcher at all** *(2026-09, Christmas Evans, PG #42340)*. Its 22
    sermons are clean `<h3>SERMON IV.<br>FALL AND RECOVERY OF MAN</h3>`, but each
    heading carries a `<span class="pagenum">p. 108</span>` prefix, and
    `extract_gutenberg_section` matches `_norm_heading(h.get_text(" "))` whole —
    so `section` would have to embed the page number ("p. 108 SERMON IV. …"),
    which is absurd. When the source is a page-numbered collected edition,
    hand-extract the chosen sermons into fixtures and ship them **without a
    `sermon_catalog.py` entry** (the fixture is the source of truth — the
    Wesley/Booth batch did the same for its two hand-corrected sermons). Note
    also: Gutenberg italicizes a whole scripture epigraph word-by-word, so strip
    `<i>` from the opening verse (the blockquote already marks it) and fold
    `<span class="smcap">` to uppercase, as the Booth sermons preserve caps.
  - **A Gutenberg Postil can set every sermon AND its subsections at the same
    heading level** (Lenker's *Epistle Sermons*, id 28464, is all `<h4>`), so
    `extract_gutenberg_section` — which bounds a sermon on the next SAME-tag
    heading — returns only the first subsection. Verify the target's heading
    level is DISTINCT from its subsections in `pg<id>-images.html` before using
    a gutenberg section; else use a one-sermon-per-page `web` source
    (sermons.martinluther.us for the Lenker translation).
  - **A `web` sermon needs `body_starts`** (the literal opening of the first
    real paragraph) to cut a leading byline/nav, and its page may append a
    trailer the single-element nav rule can't reach: `extract_web_sermon` now
    also cuts the gospeltruth.net trailer (index link / copyright / nav menu /
    certification seal), a bare `<p>TOP</p>` jump link, BibleHub's "Parallel
    Verses" cross-reference block (+ ad-slot comments), and a collected-edition
    "END OF VOL." marker. After any such change, re-import the OTHER web sermons
    and confirm word counts are byte-unchanged. **Good web fallbacks by author:**
    gospeltruth.net (Finney), sermons.martinluther.us (Luther/Lenker),
    biblehub.com `/sermons/auth/…` (Calvin, and other PD anthology sermons in
    the Kleiser translation).
  - **Adding sermons can trip `ReleaseProseSourceCoverageTests`** — enough
    `body_starts`/title/comment text in `sermon_catalog.py` tips its prose
    detector, and it fails "modules … carry prose, but are neither a content
    root nor exempt." The reader sees a sermon's title/scripture from the
    FIXTURE (what `seed_sermons` upserts), not from `sermon_catalog.py`, so the
    module belongs in `NOT_READER_PROSE` (added, same as `catalog.py`), not in
    `content_sources.json`.
  - **A sermon needs a `summary`** (a shelf gate) and an **og:image twin**
    (`SermonShareCardTests`). The twin generator `frontend/scripts/og-card.mjs`
    reads Linux-only Liberation fonts from `/usr/share/fonts/…`, so
    `npm run og:sermons` FAILS on macOS (and the top-level manifest
    `composition` digest is gated by `sermonCards.test.ts`, so you can't fake
    it or run a modified generator and revert). Generate the twins where those
    fonts are installed (Linux / CI), or vendor the TTFs into the repo and point
    og-card at them (the file's own comment invites vendoring). **Proven CI
    recipe** (2026-09): add a throwaway workflow that `sudo apt-get install -y
    fonts-liberation`, `npm ci`, `npm run og:sermons`, then git-commits
    `frontend/static/og/sermons/` back to the branch (needs `permissions:
    contents: write`). Trigger it with **`on: push` scoped to the branch** — NOT
    `workflow_dispatch`, which GitHub only exposes from the DEFAULT branch, so
    `gh workflow run` 404s for a branch-only file. Its GITHUB_TOKEN push won't
    re-run CI (recursion guard); land the twins, then push your own follow-up
    (e.g. removing the workflow) to re-trigger `test-and-build` on a head that
    has them. NPNF homilies
    are faithfully set in a few very long numbered paragraphs — baseline the
    `lost-paragraphing` flag.
    - **Simpler than a CI workflow — generate the twins locally on macOS**
      *(2026-09, proven)*: download the real Liberation TTFs (official
      `liberationfonts` GitHub release, SIL OFL — the `/private/tmp/libfonts`
      copies a prior session left were HTML error pages, so `file` them first),
      then run `node --import <preload.mjs> scripts/generate-sermon-og.mjs`
      where `preload.mjs` wraps `fs.readFileSync`/`fs.openSync` to remap ONLY
      the two hardcoded `/usr/share/fonts/…/liberation/…` paths (SIP blocks
      creating that dir). The preload leaves the two generator scripts
      byte-identical, so the manifest's `composition` digest stays correct —
      editing og-card's font consts and reverting would NOT (nothing recomputes
      composition, but the manifest would then disagree with the committed
      script). Verify with a plain-node replica of `sermonCards.test.ts` (Node
      ≥22.18 strips the TS types) since a symlinked `node_modules` breaks vitest.
  - **Hand-writing a sermon fixture skips the per-work `english_audit` that
    `import_sermons` runs — so CI's corpus ratchet (`tests_english_audit`) is
    the FIRST thing to catch an OCR slip, one red round-trip later** *(2026-09)*.
    Before pushing new sermons, run `audit_english <slug…>`: FIX genuine defects
    (a gospeltruth Booth sermon read "into His cars" — an OCR misread of "ears",
    surfaced as an `anachronism` since cars = automobiles), then
    `--update-baseline` for the mechanical noise — `space-before-punct` (the
    era's " ?"/" !" typography, only flagged under 16 hits/work) and
    `orphan-close-quote` (an author's split scripture quote, e.g. Wesley's
    `"All things are possible to him that" thus "believeth"`). Diff the baseline
    JSON and confirm it touches ONLY your new works — `--update-baseline`
    re-pins the WHOLE corpus and would silently absorb another work's drift.

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

**A famous "sermon" title can be a BOOK CHAPTER — check length AND book-catalog
overlap before shipping it on the sermon shelf.** Ryle's "Assurance" is one of
his best-known pieces, but on CCEL it is chapter VII of *Holiness*
(`ryle/holiness.iii.vi.html`) and imports at ~15,600 words — twice the shelf's
longest, and a straight duplicate the day someone adds *Holiness* as a book. The
same title often exists as a genuinely standalone TRACT: gracegems carried Ryle's
1,880-word *Faith and Assurance*, which covers the theme, stands on its own, and
can't collide with a future book. Two habits: (1) if an imported sermon lands far
above ~8,300 words, suspect a book chapter and look for the standalone tract; (2)
before shipping a book-chapter-as-sermon, ask whether that book is a plausible
future book-catalog entry — if so, prefer the tract. *(Ryle, PR B, 2026-09.)*

**Adding a STANDALONE sermon — use `import_sermons`, don't hand-roll the
extractor.** A single sermon on the sermon shelf (not sermons compiled into a
book) has a maintained end-to-end path; a whole session was once spent
re-writing a CCEL/gospeltruth extractor + Django-serializing fixtures by hand,
all of which this command already does. The steps:
- **Add a `SermonEntry` to `SERMONS` in `library/sermon_catalog.py`.** `source`
  is `"ccel"` (one page per sermon, `source_ref` = full URL), `"gutenberg"`
  (`source_ref` = ebook id, `section` = the heading text), or `"web"`
  (`source_ref` = URL, `body_starts` = the literal text the first body paragraph
  begins with — this is how it finds the body under a gospeltruth masthead).
  `scripture_ref` / `preached_on` are overrides; leave blank to let the page
  parse them. An author with NO books yet also needs an `AuthorEntry` in
  `SERMON_AUTHORS` (use the slug `authors.json` uses); an author who already has
  books reuses the book catalog's entry.
- **`python manage.py import_sermons <slug>`** upserts the `Sermon` row:
  `extract()` drops the masthead, parses the date + scripture ref, keeps the
  scripture quote as an opening `<blockquote>` (CCEL) — web sermons keep the
  verse only in `scripture_ref`, body is plain `<p>` — stores the settled body,
  and runs `english_audit`. Both CCEL (Wesley/Spurgeon) and gospeltruth-style
  web pages (Booth, Finney) are supported.
- **Then the finish:** serialize the row to `fixtures/content/sermons/<slug>.<lang>.json`
  (Django serializer, `indent=1`, natural keys — NOT `json.dump`), and
  **`cd frontend && npm run og:sermons`** — `SermonShareCardTests` fails the
  build until each sermon has a committed `frontend/static/og/sermons/<slug>.png`
  + a matching `og-manifest.json` entry. A sermon with no curated emblem in
  `SERMON_EMBLEMS` (`frontend/src/lib/emblemNames.ts`) draws a fallback-pool
  emblem automatically — fine, no catalogue edit required.
- **macOS font gotcha for `og:sermons`.** `scripts/og-card.mjs` hardcodes Linux
  Liberation paths (`/usr/share/fonts/truetype/liberation/Liberation{Serif-Bold,
  Sans-Regular}.ttf`); SIP blocks creating that dir on a Mac. Fetch the real
  Liberation TTFs (SIL OFL, the `liberationfonts` GitHub release — the copies at
  `/private/tmp/libfonts` were once a broken HTML download) and run the
  generator under a tiny `--import` preload that remaps only those two
  `fs.readFileSync`/`openSync` paths. Editing `og-card.mjs` directly would
  poison the manifest's `composition` digest (bytes of the two scripts); the
  preload keeps it CI-correct because nothing recomputes composition, only
  re-running does. *(Wesley + Booth second sermons, 2026-09)*
- **A CCEL discourse collection can number its sermons "Sermon I…N" with NO
  descriptive titles — map each leaf to its TEXT by the first `scripRef`, not the
  TOC** *(John Newton's Messiah: Fifty Expository Discourses, `newton/messiah1-2`,
  2026-09-06)*. The TOC lists only "Sermon I" … "Sermon L", so you can't pick by
  title. Grep each leaf's FIRST `class="scripRef"` — that anchor is the discourse's
  text (later scripRefs are back-references to the previous sermon, so first-only):
  `curl -s <leaf> | grep -oE 'class="scripRef"[^>]*>[^<]+' | head -1`. Sermon I is
  `messiah1.iii.html` (i/ii are Title Page/Preface), so Sermon N = the (N+2)th leaf.
  Such a collection — many self-contained discourses each on its own text — is a
  rich, clean standalone-sermon source; the Newton refs parsed as full book names,
  so no `scripture_ref` pinning was needed.
- **A CCEL "sermon" leaf can be an ADDRESS split across `.i`/`.ii` sub-pages —
  it imports as the intro only** *(Torrey Revival Addresses, 2026-09-05)*. The
  parent page `revival.v.x.html` ("The Way of Salvation Made as Plain as Day")
  looks like one sermon but is a 347-word intro; its argument lives in
  `revival.v.x.i.html` / `.ii.html`, so `import_sermons` silently ships a
  truncated stub (`import_sermons` extracts ONE page — it does not follow
  children the way the book importer's `toc_sections` does). Before choosing a
  CCEL sermon, grep the collection TOC for child leaves of the target and pick a
  SINGLE-LEAF address (kids=0). In Torrey's `revival` half the addresses split
  (v.i, v.vi, v.vii, v.ix, v.x, v.xii, v.xiii, v.xvii); the single leaves
  (v.ii–v.v, v.viii, v.xi, v.xiv–v.xvi) carry their whole text. Signal to catch
  it after the fact: a word count far below the shelf's ~1,000-word floor.
  Also: a parsed CCEL scripRef can be ABBREVIATED ("Rom. 3:24") where the rest
  of the shelf writes the book in full ("Romans 3:24") — pin `scripture_ref` in
  the catalog so a re-import can't drift the fixture.
- **CCEL is not one layout — check each collection before trusting the
  masthead parser** *(Whitefield / Edwards / M'Cheyne, 2026-09-04)*. Wesley is
  `<h2>` + `<h3 class="scripRef">`; **Whitefield** is an `<h1>` title with the
  scripture INSIDE the first `<p>` as `<a class="scripRef">Ref</a> — “verse”`,
  and some sermons open straight into prose with no heading at all (Intercession's
  text is the verse it calls "the text"); **Edwards** was transcribed piecemeal —
  every masthead differs (title `<h1>`/`<h2>`, "A Sermon / by" rows, a bracketed
  `<h5>` note, the scripture in a `<blockquote>`, `<p>`, `<h3>` or `<h4>`, verse
  before OR after the ref). The stable rule: the block holding the FIRST
  `a.scripRef` is the epigraph; **decompose the anchor before taking the verse**
  (else the ref glues on — audit `run-together`) and strip the ` -- `/` — `
  separator on whichever side; keep in-body DOCTRINE/APPLICATION/Part One as
  `<h3>`. Pin `scripture_ref` (and `preached_on`) in the catalog for these.
- **A hand-built body must be SETTLED or `tests_sanitize`/QA reddens** — three
  triggers, each hit once: a bare `&` ("&c.") → emit `&amp;`; `<br>` → the
  sanitizer's `<br/>` (and drop a break dangling at a paragraph edge); NBSP
  (`&nbsp;` in "I.&nbsp;<i>The fact…") → a plain space.
- **`QuoteStyleTests` counts DOUBLE quotes only.** Apostrophes don't count, a
  wholly straight-quoted work passes (all five Edwards pages), and raw-HTML
  `"` counts include attribute quotes — mcheyne.info looked mixed and wasn't.
  When it IS mixed, `scripts/normalize_quotes.py <slug>` + `rederive_body_text
  --write`, then eyeball: it cased the elided `'tis` as an OPENER (`‘tis`) —
  correct to `’tis` by hand. `hyphen-space` fixes are per word: `with- out` →
  `without`, but `us- ward`/`dwelling- place` are real KJV-era hyphenations.
- **M'Cheyne: CCEL has no sermons.** mcheyne.info serves the printed Sermons
  one per page (WordPress `entry-content`): masthead `<p>` "SERMON XIV Robert
  Murray M‘Cheyne" (drop), his skeleton heading "Doctrine.—…" (keep; strip the
  site's welded blurb), the verse `<p>` with an erratic citation tail
  (`—MICAH vi. 6-8.`, `Hosea -vi., 4.`, `— Jer. xiv. 8,9.` — pin the ref), a
  trailing date line → `preached_on`, `<br>` poems, and a SITE-WIDE
  `<p class="footerPoem">` (about Baxter, identical on every page — drop). It
  sets a closing `”` in opener position after `—`/`-`. Only six sermons exist
  there (one an abridgement); no catalog entry — fixtures authoritative.
- **A green local suite does not prove CI's `makemigrations --check`.** The
  test runner only runs `migrate`, which tolerates multiple leaf migrations; CI
  runs `--check` as well, and it runs it on the PR's synthetic merge with
  *current* main. So after merging main into a branch, a local
  `makemigrations --merge` can say "No conflicts detected" while CI fails on
  two leaves that exist only in head + a main that moved after your fetch
  (Edwards #1408, 2026-09-04: `0112_flock_moderns…` vs `0113_topicarticle_rls`).
  Right before pushing a main-merge: `git fetch && git merge origin/main`
  again, then `DJANGO_DEBUG=true uv run python manage.py makemigrations
  --check --dry-run`; if it names leaves, `makemigrations --merge --no-input`
  and commit the no-op merge migration.
  **The SAME merge-ref trap hits `ruff`** — CI lints the PR merged into *current*
  main, so a rule a parallel session TIGHTENED after your branch base fails CI
  while your local `ruff check .` (older config) passes green. Bit the Pilgrim's
  Progress build with **B905 (`zip()` without `strict=`)**, added to the config
  upstream — local ruff said "All checks passed", CI red. So `git merge
  origin/main` and re-run `uv run ruff check .` before pushing, same as the
  migration check. (B905 fix: pass `strict=True`, but only after making the
  iterables equal length — `zip(items, bounds[:-1], bounds[1:], strict=True)`,
  not the mismatched `bounds`/`bounds[1:]`, which would raise at runtime.)
  *(pilgrims-progress-words-of-one-syllable, 2026-09)*
- **Batch several authors' sermons into ONE PR** when they land together
  *(Tier 2, #1418, 2026-09-04)*. Every sermon PR touches `og-manifest.json`,
  and catalog additions all insert at the same tail, so N parallel sermon PRs
  cost N−1 main-merge + manifest-regen rounds (Tier 1's three PRs did). "Top up
  five thin authors" is one job; one branch.
- **Source shapes met in Tier 2** — each round-trips through the importer,
  so give them catalog entries:
  - *BibleHub "sermons" by an author are NOT sermons.* `/sermons/auth/calvin/…`
    pages are ~150-word commentary snippets wrapped in ad scripts. Only the
    Kleiser anthology pages there (`/sermons/auth/various/…`) are real sermons,
    and Calvin has exactly one. No other clean PD Calvin standalone was found;
    the 16th-c. Golding translations are PD but Elizabethan.
  - *CCEL "Lectures on Revivals" (Finney)*: `<h2>LECTURE n</h2><h3>TITLE</h3>`,
    then `<p class="text">` = `Text.—verse—<a scripRef>ref</a>.` (strip the
    `Text.—` lead and the `—ref.` tail; the ref is `James v. 16` style, so pin
    it), footnotes present, `span.sc` small caps.
  - *NPNF treatises on CCEL (Chrysostom)*: `span.pb`/`a.page` page numbers,
    dozens of `sup.Note`/`span.mnote` footnotes, a three-paragraph masthead
    (A TREATISE / TO PROVE… / ————) before the first numbered paragraph,
    500-word paragraphs (baseline `lost-paragraphing`), no scripture text.
  - *Lenker Postil site (sermons.martinluther.us)*: flat `<p><span class="C-2">`
    lines; a "Content Page" nav line, byline/intro and the caps title before the
    first numbered paragraph (= `body_starts`); empty `<br>` spacers; ALL-CAPS
    short lines are section headings (keep as `<h3>`); one page repeats the
    title after the first heading; a `<a href="#top">TOP</a>` trailer. Spaced
    ellipses `. . .` are the site's style (baseline `space-before-punct`).
    Two-thirds of the Postil (61–117) is not on the site.
  - *gospeltruth Finney pages* end with a `Copyright (c)… Gospel Truth
    Ministries` paragraph (drop) and carry `[sic.]` editorial markers (drop).
  - *PG 23438 "A Ribband of Blue" (Taylor)*: `<h3>`-delimited studies, but the
    epigraph is a `<div class="c1"><em>"verse"</em>--1 Peter ii. 25.</div>`
    BEFORE the first `<p>`, sometimes preceded by an all-caps subtitle div; the
    whole book is wrapped in `<div>`s. `extract_gutenberg_section`'s
    "blockquote the first paragraph if it opens with a quote" would swallow a
    prose paragraph here — render only `<p>` and `div.c1`, and never skip a
    `<p>` merely for having a div ancestor.
- **A sermon may have no scripture text** (Luther's Good Friday Passion
  meditation, Chrysostom's treatise): leave `scripture_ref` blank rather than
  invent an anchor. Cards and pages render with the passage line empty.
- **A content-only sermon merge can ship its new pages as the SPA shell — and
  a frontend-only rebuild may not fix it** *(Tier 2 #1418 → #1420, 2026-09-04,
  confirmed)*. The web build prerenders whatever the API returns at build time;
  the Tier 2 build passed the digest gate yet baked eight 5.7 KB shells and
  stale author sermon-counts, while the API already served all 65. Render skips
  the web build unless `frontend/` changes, so a docs/backend-only push cannot
  rebuild it. And a frontend-ONLY touch risks the gate: the live API's baked
  `content_version` (b8ab6c…) did not match what a clean checkout of the same
  commit digests to (ae3ff9… under both `manage.py content_version` and the JS
  gate run with `RENDER_GIT_COMMIT` set), so a build with no API redeploy could
  wait its 15-min timeout and fail. What worked, first try: ONE PR touching a
  file under `backend/` (a comment beside `content_digest()`) AND one under
  `frontend/` (a note in `sermons/[slug]/+page.ts`) — both services redeploy
  together, the gate matches, every page prerenders. Verify with trailing-slash
  URLs: a prerendered sermon is 40–120 KB with a `<title>`; the shell is
  ~5.7 KB with none. Don't trust a LOCAL gate run to predict Render's: the two
  digests disagree for the same tree (open question, noted in #1420).
- **The worktree guard refuses long chains that mix `uv run` with git, or
  heredoc-laden `git commit -m "$(cat <<…)"`.** Write the commit message and
  PR body to files and use `git commit -F <file>` / `gh pr create --body-file
  <file>`; keep `manage.py` gates in their own command, prefixed with an
  explicit `cd <worktree>/backend &&`.

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

**Documenting the American South** (`import_docsouth`, `source="docsouth"`,
`source_ref` = the full `https://docsouth.unc.edu/...html` page URL) is the
cleanest source for early African-American / Southern texts — human-KEYED, not
OCR (Richard Allen's and Amanda Berry Smith's autobiographies came from here).
The whole book is ONE page; hazards worth knowing before reusing it:
  - **Isolate the transcribed text or docsouth's own front matter imports as
    phantom chapters.** The funding statement, source description and
    "Electronic Edition" title block are all set in `<h3>` like a chapter. The
    book proper begins at the first inlined print-page anchor
    (`<a name="allen3"> Page 3</a>`) and ends at docsouth's per-book nav block
    `<div class="links">` (the "Return to Menu Page…" links) — cut at that OR
    `<!-- footer inside begins -->`, WHICHEVER COMES FIRST. The links div sits
    just before the footer comment, so cutting only at the comment leaks four
    nav lines into the last chapter (shipped that way in Allen's book, fixed in
    #1330). Decompose the `<a name>` anchors (they carry the visible "Page N"
    text) and the illustration `<img>`s.
  - **Split on `<h3>` at the STRING level, not by walking BeautifulSoup
    siblings.** The centred summary sub-headings are malformed
    (`<P align="center">…</P></P></FONT>`), and lxml reparents later headings
    under a stray `<p>`, so a sibling walk silently merges and drops chapters
    (Smith came out 31 of 38). Regex-split on `<h3>`, then soup each chapter body
    in isolation, where the mangled nesting can't swallow a heading.
  - **A numbered chapter's real title leads its body.** docsouth prints
    "`<h3>CHAPTER I.</h3>`" then the title as an ALL-CAPS centred sub-heading,
    then the prose — so `import_gutenberg.resolve_title` would be right in spirit
    (borrow the next node) but it also CONSUMES the borrowed node and would eat a
    chapter's first sentence on any source whose numbered heading is followed by
    prose. Promote an ALL-CAPS lead paragraph to the title only, and only when
    the heading was a bare numeral. NB `clean_title` empties a bare *arabic*
    "Chapter 3" but keeps a *roman* "Chapter I" (which then doubles to "1.
    Chapter I") — detect the bare chapter yourself.
  - **`is_front_matter` gained "list of illustrations"/"illustrations"** (a plate
    list, no prose) — general, not docsouth-specific.
  - **19th-c. chapter "arguments" make poor titles verbatim** (100–300 chars,
    em-dash chains, OCR word-splits like "Wa Y"/"Florenc E"). Smith's are curated
    down to concise titles in `corrections.chapter_titles`, the same channel as
    `holy-in-christ` / `ministry-of-intercession`. Ask the user how they want the
    chapter list to read before hand-writing 36 titles.
  - **A compilation is not a chaptered book.** Allen's volume is autobiography +
    AME supplement + three devotional Acts + the 1793 yellow-fever narrative +
    two addresses; each `<h3>` section becomes a chapter, and the ones whose
    descriptive subtitle sits in the body get their title from `chapter_titles`.
  - Quote style: docsouth is uniformly STRAIGHT-quoted, which `QuoteStyleTests`
    (consistency, not curly) leaves alone — so keep titles/descriptions straight
    too rather than normalising.
  - **Fixing an ALREADY-SHIPPED book with an importer change reaches prod only
    through the fixture.** An importer fix alone helps nothing already imported;
    regenerate the fixture and `seed_books` syncs the chapter on deploy (since
    2026-09-23 — before that it never rewrote existing chapters, hence what
    follows). The Allen
    footer-nav fix (#1330: importer + fixture) deployed and left the live last
    chapter unchanged; it took a one-time `BODY_CORRECTIONS` replacement (#1336)
    to backfill the stale prod row. Prefer a correction over a hand-written
    migration for a body-text edit: `apply_body_corrections` runs it through
    `save()` every deploy, re-deriving `body_text`/`word_count`/`search_vector`
    (no manual column bookkeeping), and it no-ops on the already-fixed fixture.
    Confirm `stale.replace(old, "") == fixed_fixture_body` exactly so prod and
    fresh installs converge.

**A manuscript `.docx` the user hands you (an original biography/work, no
importer).** No source URL, no catalog entry — parse the file and build the
Book directly, then finish like any new book. What bit this loop:
  - **Parse OUTSIDE the uv venv.** `python-docx` isn't installed in the backend
    venv; run a system `python3` script that walks `doc.paragraphs` → a JSON
    intermediate, then `loaddata`-style build it in the Django shell (`shell <
    build.py`). Keep the docx parser and the ORM step in separate scripts.
  - python-docx `p.style.name` is `"Heading 1"` / `"Heading 2"` (WITH a space),
    not the `Heading1` styleId you'd see in raw `document.xml`. Map Heading1 →
    chapter boundary, Heading2 → `<h2>`, Heading3 → `<h3>`, Normal → `<p>`.
  - `html.escape(text)` defaults to `quote=True` and turns every apostrophe into
    `&#x27;` — pass `quote=False` so only `& < >` escape. Preserve real emphasis
    by reading `run.italic`/`run.bold` → `<em>`/`<strong>`; also convert any
    literal `*markdown*` italics the author left in.
  - Drop the title page + "Contents" chapter and a trailing "End of manuscript".
    Strip the reader-doubled "Chapter N — " from titles, but KEEP "Appendix A:"
    / "Introduction:" labels (the reader's number reads fine before them).
  - Then the standard new-book finish: `generate_covers`, write the fixture with
    the serializer (§"Write its fixture file yourself"), `normalize_quotes.py`
    (a no-op here — the source was already curly-double-quoted), `npm run
    og:covers`, `tests_fixture`. *(watchman-nee-a-life, 21ch from a .docx, 2026-09)*

**A biography ABOUT a person is filed under that person as the author**, with
the real author/description in the `subtitle` — NOT under `ochorus-originals`
and NOT crediting the subject as if they wrote it. Precedent: `susanna-wesley-
clarke` (Eliza Clarke's life of Susanna Wesley) sits on the `susanna-wesley`
author page, subtitle "A Biography by Eliza Clarke". So "make this a book for
X" → author `X`, subtitle carries the descriptive line. (Contrast the
`ochorus-originals` bio *collections* — many subjects in one volume — which are
their own author with per-chapter subject links.) *(watchman-nee-a-life, 2026-09)*

**An ORIGINAL, in-copyright book (the founder's own work, not a PD classic) is
filed under the `ochorus-originals` imprint with NO schema change.** The shelf is
otherwise public-domain, and `SourceType` has no `original` value — do NOT add
one just to ship a book. Follow the non-PD SermonIndex precedent:
  - `author` = `ochorus-originals` (the `is_imprint` house byline); `source_type`
    stays `public_domain` (the enum's least-wrong value); `publication_year` =
    the real (contemporary) year.
  - Leave `source_url` **blank** — the book page renders the "Public domain" line
    only when `source_url` AND `source_type == public_domain` are both set
    (`books/[slug]/+page.svelte`), so a blank URL suppresses the false claim.
  - The Book page does **not** surface the `attribution` field (the Sermon page
    does), so put the authorship + any Scripture-translation rights notice (e.g.
    NIV) in **`about_html`** (which IS rendered) — and also fill `attribution`
    for the record. This is the honest place to say "© <author>… Scripture from
    the NIV®" without touching the model.
  - Parse the `.docx` from `word/document.xml` directly (ElementTree, no
    python-docx needed): `pStyle` gives `Heading1`/`Heading2`; per-`<w:r>`
    `<w:b>`/`<w:i>` give the sub-headings that carry NO heading style — this book's
    convention was **bold = a heading** ("Reflection", "Prayer", numbered
    "1. …" items) and **italic = an epigraph/subtitle/emphasis**. Render bold-short
    lines as `<h3>`, italic runs as `<em>`, and strip emphasis from a trailing
    "— Book c:v" citation so refs read consistently across chapters.
  - Confirm the byline/scope/Scripture-translation decisions with the founder
    before building — they are brand calls, not defaults. *(growing-in-wisdom,
    original student guide, #2476, 2026-09-16)*

**`npm run og:covers` regenerates any DRIFTED twin, not just your new one, and
REWRITES the whole `og-manifest.json` in a different indent than committed** — so
a fresh-worktree run shows N unrelated PNGs modified + a 2000-line manifest
reformat. Don't commit that. `git checkout --` the unrelated PNGs and the
manifest, then splice ONLY your entry into the committed manifest with a script:
load it order-preserving (`object_pairs_hook=OrderedDict`), insert your slug
before the first BASE (no `/`) slug that sorts after it, and write back
`json.dump(indent=1)` + trailing `\n`. Do **NOT** `sorted()` the twins — the
committed order appends translation twins (`fr/`, `pt/`, `sw/`) at the END, not
alphabetically, so a re-sort explodes the diff. Verify `git diff --numstat` is
`7 0`. *(growing-in-wisdom, 2026-09-16)*

**Verifying a new book in the LOCAL browser 500s on EVERY book, not just yours —
it's the dev CSP, not your content.** The built/dev pages carry a hash-mode CSP
`<meta>` whose `connect-src` lists only the prod API hosts + `'self'`;
`svelte.config.js:directivesForThisBuild()` adds the local API origin from
`process.env.PUBLIC_API_BASE_URL`, but a plain `npm run dev` (preview_start /
launch.json) doesn't reliably get that into `process.env`, so client-side
`apiFetch` to `localhost:80xx` is CSP-blocked and the page throws to the 500
boundary. Confirm it's environmental by loading an existing book (it 500s too),
then verify via the API JSON (`/api/library/books/<slug>/`) + the backend gates
instead of chasing a screenshot. *(growing-in-wisdom, 2026-09-16)*

**The "Key Teachings of …" study-companion series (`build_key_teachings`).** These
are Ochorus's OWN house-written expositions ABOUT a classic teacher — not the
author's text — one shared 89-page digital-PDF template: title page, disclaimer,
Introduction, a titled biographical narrative, eighteen `CHAPTER N` chapters (each
ending in application points + a prayer), Conclusion, "A Reader's Guide". The
design is the point: quoting only the KJV and naming (never reproducing) the
author's works lets the series safely cover a STILL-COPYRIGHTED author (Watchman
Nee) as well as PD ones (Simpson, Edwards, Baxter) — QA every chapter to confirm
no in-copyright prose is quoted before shipping a copyrighted-author volume.
Filed under the SUBJECT as author with the Ochorus line in `subtitle`
(per the rule above); `source_type` has no house value so it ships `public_domain`
with the rights note in `attribution`. Committed source PDFs live in
`data/key-teachings/` (Ochorus's own prose, unfetchable). Why NOT `import_pdf`:
the generic PDF path mishandles this typographically rich source three ways, so
the command extracts font size AND weight per block (`page.get_text("dict")`,
bold = span flag `16` or "bold" in the font name):
- The small-caps running header ("N THE KEY TEACHINGS OF …") is set SMALLER than
  body (6pt vs 10pt), so it never becomes a heading-size block and dodges
  `chapterize`'s frequency ban — it leaks into every chapter body. Drop it by
  content (a small block that is not a chapter:verse citation is furniture).
- Bold in-chapter subheadings sit at BODY size, so `_merge_paragraphs` fuses each
  into the next paragraph ("The test There is a question…"). Promote a bold,
  short (≤10-word), unpunctuated body block to `<h2>` instead.
- The biographical narrative and "A Reader's Guide" carry neither a `CHAPTER N`
  marker nor a `_SECTION_RE` keyword, so the marker pass folds them into
  Introduction/Conclusion. Split on EVERY heading-size block (they're all one
  size) to get the full 22 chapters.
Font model per block: `>=body*1.11` title/boundary; `~body` prose (bold+short →
`<h2>`); `~body*0.80` set-apart Scripture → `<blockquote>`; `<body*0.72` small —
a chapter:verse ref is a kept epigraph citation, everything else furniture. Two
more traps: (1) build block text LINE-BY-LINE and de-hyphenate a line-end
`letter-` split (join next line, no space) — the digital PDF justifies with soft
hyphens, so a naive span-join yields "move- ment" ×232 (the stock importer ships
these). De-hyphenate at the PROSE-MERGE step too, not only within a block: a
page/column break splits a word across two BLOCKS ("Chris-" ‖ "tians"), which
`_merge_paragraphs` would rejoin with a space. And to tell a syllable break
("rev-elation" → drop hyphen) from a real compound ("self-righteousness" → keep),
DON'T lean on the dictionary alone — web2 lacks inflections and proper nouns, so
"concat-not-a-word → keep" wrongly keeps "won-dered", "Simp-son", "pub-lished"
(≈135 of 151). The rule that works: DROP by default (right ~98%), KEEP only for
`self-*` (keep unless the joined word is a known CLOSED self-word — a tiny
explicit set {selfish, selfless, selfsame, selfhood}; do NOT load
`/usr/share/dict/web2`, a hidden env/CI dependency that also mis-keeps proper
nouns) and number/ordinal-word compounds ("twenty-five"). (2) A chapter's OPENING-PAGE
number ("17", "21", …) is set in the Scripture size band and sits mid-paragraph —
match a bare arabic/roman block and drop it WITHOUT flushing prose, or it becomes
a `<blockquote>17</blockquote>` and breaks the paragraph around it. The
`online`/`freely available online` anachronism in a Reader's Guide is faithful
(the companion is written now) — baseline it. Land the series `is_published=False`
(create-only) for founder review. **A stale local DB can miss an author already
in `authors.json`** (Baxter, added after the dev DB was seeded) — the build's
`Author.objects.get` then fails though prod is fine (`seed_books` creates from
the fixture); refresh with `manage.py loaddata library/fixtures/content/authors.json`.
Covers: a "different tree per book" is a WORDLESS art ground under
`/covers/art/<slug>.svg` (output, `BookCover` overlays the title → multilingual),
NOT a frozen designed cover — those are RASTERS with the words baked in, and only
those need a `designed_covers.py` digest. `BookCover` centres the title, so keep
the tree in the LOWER third (crown clear of the subtitle), title floating in the
sky above. To PREVIEW one with the title overlay, inline the SVG into a
self-contained HTML mock (byline top, centred title/rule/subtitle, foot mark),
serve it with `python3 -m http.server` and screenshot in the Browser pane — a
`file://` URL cannot be screenshotted there. Finish steps that bit: (1) set
`cover_url = /covers/art/<slug>.svg` in the build (create AND update — art is
the whole point) and delete any earlier `generate_covers` plate at
`/covers/<slug>.svg`. (2) Run titles through `recase_title` in the build or
`tests_fixture` reds ("Days of Heaven **Upon** Earth" → "upon", "In Adam, **In**
Christ" → "in"). (3) The rights note is reader-visible ONLY through `about_html`
— `attribution` is not rendered on the book page. Give each book an `about_html`
(`<p>`-only, ≥150 words, sanitizer-clean, must not contain the `description`
verbatim) carrying the companion/rights note; the copyrighted-author volume
(Nee) carries the full "not affiliated with any rights-holder… obtain from
their rightful publishers" disavowal there. (4) og twins: `npm run og:covers`
(needs `npm install` + `npx playwright install chromium` in the worktree; it
uses chromium+webfonts, so NO Liberation-font gotcha — that is `og:sermons`
only). **The manifest trap:** the committed `og-manifest.json` is in an OLDER
format than the current generator (1-space indent + insertion order vs the
generator's tab + `localeCompare` sort), so a fresh `og:covers` rewrites the
whole ~4000-line file AND redraws any twin gone stale on your base (4 unrelated
Torrey twins here). Don't ship that. `git checkout HEAD --` the unrelated twin
PNGs, then merge ONLY your entries into the base manifest in ITS format —
`node -e` load base, copy your slugs' entries from the fresh manifest, write
`JSON.stringify(base,null,1)+"\n"` (match the base's indent, detected from the
file — 1 here). Result: a 28-line add, not a 4000-line reorder. Gates check
per-twin digests, not order/indent, so an unsorted 1-space manifest stays green.
BETTER, if you can: rebase onto CURRENT `origin/main` BEFORE running `og:covers`
— main's committed manifest is already in the generator's format, so the run
appends your entries as a clean +N-line diff with no whole-file rewrite. The
rewrite is a STALE-BASE artifact, not a permanent condition.
*(build_key_teachings: Simpson/Edwards/Baxter/Nee, 2026-09; one `WORKS` entry +
a committed PDF each; fixture-driven, no migration.)*

**A HOUSE-WRITTEN original collection (no source at all) → a `build_<name>` that
holds the original prose as committed module constants**, exactly like the
anthology/manuscript builds but with nothing fetched. File it under the existing
`ochorus-originals` author, `source_type: public_domain` (the house convention —
the Originals all use it), `source_url: ""`, and add the slug to its topic shelf.
Chapter bodies are plain `<p>` prose (no `<a>` links — `clean_fragment` strips
attributes; cross-link to subjects via `BookPerson`, not inline links). Two
gates to pre-check: colon-subtitle chapter titles ("Name: The Hook") must satisfy
`titlecase.recase_title(t) == t`, and keep quotes uniformly curly so
`QuoteStyleTests` (consistency) passes. For a CHILDREN's collection, short
chapters (~350–450 words) read better than long ones. `build_brave_for_god` (six
young-readers hero lives) is the model. *(brave-for-god, 2026-09)*

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

**A declared book may already be LIVE under a different slug — verify the WORK,
not just the declared slug's fixture.** `Talks to Farmers` (declared, Gutenberg
#42518) is the same book as the on-site `talks-to-the-farmer`, chapter for
chapter; `Humility` (= `humility-2`) was the same trap. A 404 on the declared slug is
necessary but not sufficient — search the live API for the title
(`/api/library/search/?q=…`) and compare the source TOC against any
similarly-titled existing book before importing, or you ship a second copy of a
book already on the shelf. *(2026-09)*

**The reverse trap: a similar title can be an EXCERPT, not the work.**
`school-of-prayer` was once listed here as "= `lord-teach-us-to-pray-2`", and
it isn't: that on-site book is Murray's first four lessons (~8k words, ending
"THE END"); the full work is 31 lessons plus the Müller note (~70k). Compare
chapter counts and word totals, not just titles — then decide deliberately.
The full work shipped alongside the excerpt, which keeps its translations, its
plan and its quotes. Two things that import needed, both reusable: CCEL's
"FIRST LESSON." heading run is not a CHAPTER ordinal, so `extract_body` keeps
it (strip it with literal `replacements`, the `separation-and-service`
precedent); and a CCEL transcription can carry a wrong date (its Preface said
1895 for 1885) — corroborate a year from the text before trusting it. *(2026-09)*

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
ships as nothing. Serialize the book yourself — and **write the serializer's own
`indent=1` output DIRECTLY**, which already IS the canonical dumpdata format
(record braces at column 0, no `pk`), so you do NOT need the full regen:
```bash
DJANGO_DEBUG=true uv run python manage.py shell -c "
from django.core import serializers; from library.models import Book
b = Book.objects.get(slug='SLUG', language='en')
out = serializers.serialize('json', [b, *b.chapters.order_by('order')],
    indent=1, use_natural_primary_keys=True, use_natural_foreign_keys=True)
open('library/fixtures/content/books/SLUG.en.json','w').write(out + '\n')"
```
Do NOT `json.loads` → `pop('pk')` → `json.dumps(indent=1)`: re-dumping indents
the top-level list items and `dumpdata` does not, so that path commits a file
that differs from every other fixture (the reason the old snippet then ran a
full regen). `serializers.serialize` with natural keys already omits `pk` and
formats it right — one file, no regen. (The regen is byte-stable since #3161,
so running it afterwards is a harmless check that should leave `git status`
clean; `--normalize` is the deliberate corpus-wide reformat. If it aborts with
`N unexpected new field(s)`, that is pre-existing field drift, not your import —
see that entry above.) *(verified byte-identical to committed fixtures, 2026-09)*

**Write the fixture file BEFORE `npm run og:covers`.** The og twin generator
enumerates books from the COMMITTED `content/books/*.json` files, not the DB, so
running it before the fixture exists reports the new book as absent and writes no
twin (`wrote 0 of N twins`) — and `tests_fixture` then reds on the missing raster
twin. Order: import → `generate_covers` → write fixture → `npm run og:covers`.
*(2026-09)*

**`npm run og:covers` on a FRESH worktree dies until Playwright's browser is
installed.** The twin generator renders with Playwright's chromium, which a
fresh `npm install` does NOT download; it fails with a Playwright banner
("Please run npx playwright install") that surfaces as a bare `Node.js vXX` line
and writes no twin — then `tests_fixture` reds on the missing raster. Run
`npx playwright install chromium` once; it caches under
`~/Library/Caches/ms-playwright`, so later worktrees on the same machine are
fine. *(2026-09)*

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
