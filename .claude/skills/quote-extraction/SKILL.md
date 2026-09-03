---
name: quote-extraction
description: Extract and curate an author's quotations for their Ochorus quote page, growing it toward the ~50-per-author goal, and add them to library/quote_seed.py. Use when asked to add or grow quotes for an author, "extract quotes", or work toward the 50-quotes-per-author target — especially after new books by that author are imported. Encodes the extraction method, the paragraph-resolution gate, and the review/auto-publish semantics. This is a living playbook — append new gotchas as we find them.
---

# Extracting Ochorus author quotations

Quote pages (`/quotes/<author>`) are the one page type with **no primary text
under them** — the card *is* the page — so they are the classic thin-content /
doorway-page SEO risk, which is why the seed grew deliberately (a Spurgeon pilot
first, then a handful of authors at a time) and why **every quotation is gated
behind a human sign-off**. Respect both: quality over quantity, and never
publish under a real person's name without approval (see *Review* below).

Everything lives in **`backend/library/quote_seed.py`** — one `AUTHOR_NAME = [...]`
list per author, plus an `APPROVED` frozenset. It is registered in
`content_sources.json`, so editing it rebuilds the reader. `manage.py
seed_quotes` upserts the rows; `manage.py approve_quotes` is the takedown/approve
command.

## The row format

```python
{
    "slug": "andrew-murray-3272b680",          # "<author-slug>-<hash>", unique, PERMANENT (see freeze below)
    "text": "Faith in Jesus is the secret …",  # ONE whole sentence, verbatim
    "chapter": ("holy-in-christ", 19),         # (book-slug, chapter_order) …
    "paragraph": 5,                            # … OR "sermon": "<sermon-slug>"
}
```

`text` must be the **served, whitespace-normalised** sentence, character for
character (curly `’ “ ”`, em-dashes and all), or the resolution gate fails.

## The slug is frozen: repair text in place, never re-hash an existing row

The `slug` is not only the seed's dedupe key — it is the quotation's **permanent
public address**. The per-quote-URL plan serves each quotation at
`/quotes/<author>/<slug>/`, so a slug that moves is a URL that 404s and a lost
page. Treat every slug already in `quote_seed.py` as immutable.

- **Repairing an existing quotation** — a typo, an OCR slip, a punctuation fix
  (the `english-qa` channels): edit that row's `text` and **leave its `slug`
  literal exactly as it is**. `seed_quotes` matches on the slug, so it updates
  the row in place — same address, approval intact. (Guarded by
  `test_repairing_text_under_the_same_slug_updates_in_place`.)
- **Never regenerate slugs for rows that already exist.** Do not re-run the
  extraction/hash tool over an author to "refresh" their rows — a recomputed
  hash mints a NEW row, strands the approved original, and (once URLs ship)
  breaks every inbound link. Run extraction only to ADD genuinely new
  quotations; hand-edit existing ones.
- **A fresh hash means a genuinely new quotation** — a different sentence, not a
  reworked version of one already present. That is the deliberate "reworded ⇒
  new row, re-gated for review" behaviour (`Quote` slug comment, `seed_quotes`
  docstring); keep it for new text, don't trigger it for a fix.

## Method (what the seed docstring describes)

1. **Mechanical pass** over the author's on-site English works: shortlist
   self-contained sentences of **12–34 words**. Drop dangling openers
   (`And/But/So/For/Yet/Then/Thus/Therefore/Now/Because …`), mid-sentence
   citations (`ch.`, `v.`, `1:5`, roman-numeral refs), quotation marks
   (`" “ ”` — the gate forbids them), parentheticals, and sentences **about the
   book** rather than the faith.
2. **Drop verse-tracking lines.** A sentence that closely tracks a Scripture
   verse prints the Bible under the author's name — exactly the misattribution a
   sourced card exists to beat. Drop "Holy, holy, holy, Lord God of hosts", "God
   is love; and he that abideth in love …", etc. Also skip prayer-addresses
   ("Lord Jesus, reveal Thyself …") — they are prayers, not maxims.
2a. **Watch for an editor's voice inside the author's own book.** Many public-
   domain editions wrap the author's text in editorial framing — an Editor's
   Preface, an Introduction, connecting summaries, third-person narration — and
   a sentence lifted from those prints the *editor's* words under the author's
   name (the same misattribution as a verse-tracking line). *The Life of Trust*
   is George Müller's narrative from ch. 4 on, but ch. 1–3 are H. L. Wayland's
   Editor's Preface + Introduction; the tell is third person ("Müller was led
   to…", "the Author") where the author's own chapters are first person. Check
   the chapter titles for the editorial boundary, keep the author's voice only,
   and when unsure print the block's opening words alongside each candidate so
   you can see whose voice it is before shipping.
3. **Scoring pass** favours contrast (`not … but`, `yet`, `though`), brevity,
   and a recognisable subject (God, Christ, prayer, faith, grace, holiness …).
4. **Read the shortlist and choose.** This is judgement, and it is NOT the human
   approval (that is the PR review — see below). Spread across the source books;
   avoid overlapping the author's existing rows.

Target ~20–25 new rows to move an author toward fifty. Mine the **newly added
books first** — that is where fresh, non-overlapping material is.

## The paragraph-resolution gate (the one that bites)

`QuoteResolutionTests` (`tests_quotes.py`) is the hard gate. `paragraph` is the
**0-indexed top-level child of the SERVED body** (must be `> 0`) whose text
contains the quote verbatim. "Served" means after `library.scripture.
annotate_references` — the one transform the chapter/sermon serializer runs — so
**derive the index through the same transform**, not off the raw fixture, or you
ship off-by-one cards that link nowhere (eighteen of the first sixty Spurgeon
rows did). Count blocks exactly as the test does:

```python
from bs4 import BeautifulSoup
from library.scripture import annotate_references
served = annotate_references(body_html)
blocks = BeautifulSoup(f"<div>{served}</div>", "lxml").div.find_all(recursive=False)
# paragraph = i (the index of blocks[i] whose norm(get_text()) contains the sentence)
```

**Robust way to build the rows — DERIVE the index, don't transcribe it.** Write
an extraction script that emits candidates as `(book, order, i, sentence)`
straight from `blocks`, curate by eye, then a second script that, for each
chosen quote, **re-finds it by a distinctive fragment searched across every
block of the book** — and takes the `(order, paragraph)` from where it lands
plus the exact sentence text from that block. Two traps this avoids, both of
which bit the Gleanings batch:
- **Don't reuse the candidate list's paragraph index.** Re-derive it. The
  `annotate_references` + `find_all(recursive=False)` split must be identical to
  the gate's, and a transcribed `i` silently goes stale (or you fat-finger it).
- **Match on a fragment with NO apostrophe / em-dash / quote.** Apostrophes vary
  between books — the same "Peter's" is a straight `'` in one source and a curly
  `’` in another — so a prefix that includes one matches zero blocks in the book
  that uses the other. Search on a plain-ASCII middle fragment ("life-buoy",
  "not to define what the blessing"), assert it hits exactly one block AND one
  sentence, then store the sentence verbatim.

(Worked examples: Murray 27→50 by prefix — which then failed on Spurgeon's
Gleanings until rewritten to the fragment search above.)

## Review & the auto-publish trap

`seed_quotes` sets `reviewed = author_slug in APPROVED` **at creation, create-only**.
There is **no per-quote review state**. So:

- **New author** (not in `APPROVED`): rows seed `reviewed=False` and stay hidden
  until a person adds the slug to `APPROVED`. Safe.
- **Already-approved author** (adding more): the new rows seed **`reviewed=True`
  and publish on the next deploy** — without anyone re-reading the new ones. So
  **adding quotes to an approved author auto-publishes them; the PR review IS the
  human sign-off.** Say so in the PR, keep the quotes readable in the diff, and
  **do NOT self-merge** — leave the merge to the user. Record the addition in the
  `#: <author> — approved <date>, <count>` comment block.

Takedown is one-sided (mirrors `authors.json` portraits): clearing `reviewed` in
the DB pulls a live quote, and removing an author from `APPROVED` stops future
publication but never retracts a live row.

## Gates before the PR

```bash
cd backend && DJANGO_DEBUG=true uv run python manage.py test library.tests_quotes library.tests_quote_marks
```
covers: exactly one source; `paragraph > 0`; unique `<author>-…` slugs; whole
sentence (`^[A-Z“"]`, ends `[.!?]`, ≥ 8 words); no `&…;` entities; no `" “ ”`;
`set(QUOTES) == APPROVED`; **every quote resolves to its block**; and no quote
cites an `is_published=False` work (a dead card link). Then prove the seed:

```bash
uv run python manage.py seed_quotes   # on a fresh seeded DB; confirm the new rows appear
```

## Gotchas found in the field

- **A new author widens TWO sets, not one.** `test_the_curated_authors_are_the_reviewed_set`
  asserts `set(QUOTES) == APPROVED` AND `set(QUOTES) ==` a **hardcoded literal
  set** in `tests_quotes.py` (a deliberate scope tripwire). Adding an author to
  `QUOTES` + `APPROVED` still reds until you also add the slug to that literal.
  *(allen/smith, 2026-09)*
- **The sentence splitter must break at `." ` (closing quote before the space),
  or a Scripture quotation fuses into the next sentence and drags forbidden
  double-quotes into the row.** Allen's "…make them rest from their burthens."
  We wish you to consider…" merged under a naive `(?<=[.!?])\s+` split, so the
  clean maxim ("We wish you to consider, that God himself was the first pleader
  of the cause of slaves.") arrived wrapped in a `"…"` Pharaoh quote and would
  have failed the no-double-quotes gate. Split on `(?<=[.!?])[”"'’]?\s+`.
  *(2026-09)*
- **An autobiography / testimony source is mostly situational narrative, not
  maxims.** Raw subject-keyword scoring surfaces "the Lord gave me great liberty
  in speaking that night" a hundred times over. Penalise proper names (any
  capitalised word outside a God/Christ/Spirit/pronoun whitelist) and
  occasion markers ("that night", "the meeting", "got the blessing"), and boost
  gnomic present-tense forms (is/are/must/cannot/whoever/those who) to float the
  real aphorisms up. Expect a thin yield — Allen's plain narrative gave ~6, and
  quality-over-quantity is the rule. *(allen/smith, 2026-09)*
- **Prefer the author's own prose; a sourced card still shouldn't be Scripture
  the author merely quotes.** These two books quote the KJV constantly ("Greater
  love hath no man…", "without holiness no man shall see the Lord"); drop those,
  and drop reprinted devotional formulas (Allen's traditional "Acts of Faith /
  Hope / Love" are not his composition). The card cites the chapter, so ordinary
  authorial prose is fine even where the author draws on a tradition. *(2026-09)*

_Living playbook — append gotchas as we find them._
