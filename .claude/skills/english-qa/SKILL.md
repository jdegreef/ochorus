---
name: english-qa
description: Review and repair the ENGLISH source text of a book, sermon, or biography — extraction artifacts, OCR slips, invented text, misspelled names, broken small caps, orphaned quotations. Use after importing or writing anything in English, when `import_ochorus` reports defects, when a reader or translator reports that the English reads wrong, or when asked to audit the English library. Reports every finding and repairs only what is unambiguous. This is a living playbook — append new defect classes and fixes as we find them.
---

# Ochorus English source QA

English is the source language. Every defect in it is copied faithfully into
every translation — a translator's job is to render what is there, not to
second-guess it — so an error caught here costs one fix, and the same error
caught during translation costs four to seven.

That is not hypothetical. *Humility* ch04 shipped with an invented objection
about Christians owning "land, cars, and lots of businesses" — **cars, in an
1895 devotional** — in place of "The poor, who have nothing in themselves". By
the time anyone noticed, Luganda, Arabic and Swahili had all reproduced it, and
repairing it took four editions plus a migration.

## The one rule that matters

**Do not improve the author.** These are public-domain classics. Archaic
spelling, 17th-century punctuation, forty-word sentences and "shew" are the
text, not errors in it. Anything that reads as an improvement but changes what
the author wrote is a defect you introduced.

Three channels exist and each has its own meaning. Put every fix in the right
one:

| Channel | For | Reaches production? |
| --- | --- | --- |
| `corrections.BODY_CORRECTIONS` | what the **extractor** got wrong in the body | **Yes, every deploy** — `apply_body_corrections` is in the release chain |
| `corrections.CORRECTIONS` (`chapter_titles`) | extractor mistakes in **metadata** | **No** — consulted only by the importer; needs a data migration (precedent: `0070_fix_millennium_title`) |
| `source_fixes.py` | what the **source itself** got wrong, keyed `(slug, order)` | Applies in **any** language — use when the defect already propagated |
| `contemporize-book` skill | modernizing period style | A separate, **labelled** Modern English edition. Never in place. |

`apply_body_corrections` also carries two RULES rather than lists, each run for
every work, not just the ones with a declared entry:

- **the line-break hyphen rejoin** — closes "self- righteous";
- **`strip_footnote_markers`** — removes LONE footnote-reference superscripts, an
  empty `<sup></sup>` or a bare `<sup>4</sup>`, the residue left when a note was
  dropped in extraction. It fires only on a lone marker: a WELDED footnote
  (`<sup>1</sup><sup>1</sup>Note text…`, the tracked `welded-footnote` class) is
  excluded by lookbehind/lookahead so its note text is never stranded, and inline
  `[1]`/`[a]` brackets are left alone (they are usually the author's own
  enumeration, "three things: [1] Wisdom. [2] Authority." — content the page
  keeps; the reader strips those for the ear only, in `listenText.ts`).

**Declared pairs run first**, so a hand-written repair always beats a rule:
`the-inner-chamber` declares "scales- only" → "scales — only", where the trailing
hyphen is a flattened dash, and with the rule first that em dash was lost.

`apply_body_corrections` calls `.save()`, so the FTS hooks fire and search
vectors stay in step. A fix applied with `queryset.update()` instead would
leave `search_vector` **stale, not NULL** — the release backfill only repairs
NULLs, so search would silently keep matching the old text.

## Commands

```bash
cd backend
# what the importer prints automatically, on demand:
DJANGO_DEBUG=true uv run python manage.py audit_english <slug> --examples 0
DJANGO_DEBUG=true uv run python manage.py audit_english                 # whole corpus
DJANGO_DEBUG=true uv run python manage.py audit_english --class anachronism
DJANGO_DEBUG=true uv run python manage.py audit_english --json /tmp/findings.json
DJANGO_DEBUG=true uv run python manage.py audit_english --update-baseline

# after adding a declared repair, bring the committed fixture in line. THREE
# steps, in this order: normalize fixes body_html ONLY, and the other two
# re-derive from it. Skip either and the fixture disagrees with itself — a
# split-word rejoin ("Je rusalem" -> "Jerusalem") drops the token count:
DJANGO_DEBUG=true uv run python manage.py normalize_english_fixture --write
DJANGO_DEBUG=true uv run python manage.py rederive_body_text --write
DJANGO_DEBUG=true uv run python manage.py rederive_word_count --write
```

Only the FIRST of those three is English-only, and nothing settles a
translation's fixture for you — see the failure mode at the end.

The corpus scan covers **books, sermons and author biographies** — bios come
out of `authors.json`, and are exempt from the anachronism check because we
write them, in modern English, about people who died a century ago.

The checks live in `library/english_audit.py`. **All seven English ingest paths**
run them on what they have just written — `import_ochorus`, the five that go
through `ingest.upsert_book` (`import_ccel`, `import_gutenberg`, `import_web`,
`import_archive`, `import_pdf`), and `import_sermons`. They audit DB rows, not
the fixture: at that moment the fixture still describes the *previous* import.

## Triage — what to do with each class

Only **one** class may be applied unattended. `english_audit.AUTO_FIXABLE`
holds it, and a test pins the set, because widening it means a machine starts
rewriting a public-domain author.

| Class | Do | Why |
| --- | --- | --- |
| `broken-smallcaps` | **Auto-fix.** Add the literal pair to `BODY_CORRECTIONS` | The repair is forced: the pieces rejoin into exactly one real word ("L ORD" → "LORD"). Seven of the eight live instances are inside scripture quotations |
| `dropcap-fused` | Fix after reading the block | "Ithink" → "I think" is usually right, but confirm it isn't a genuine word the check's tail-list missed |
| `anachronism` | **Read the original edition.** Never guess | This is how invented text shows up (a modern transcriber's note is the common shape — `way-into-holiest` ch01 carries "readable to the computer audience … e-mail me at rlarryh@teleport.com"). The author may also be quoting someone. **`car`/`cars` no longer fires** — it scored 41 false / 0 true corpus-wide (railroad cars, streetcars, balloon cars, biblical chariots), so the trigger was removed; don't re-add it (see the `ANACHRONISM` comment in `english_audit.py`) |
| `misspelling` | Fix if it's a name or place; leave period spellings | Moody's "Heratii" is wrong two sentences after he spells Horatii correctly. But a 17th-century spelling is not a misspelling |
| `orphan-close-quote` | Read the passage | A close with nothing open usually means an attribution broke mid-sentence — the surrounding text is the real defect |
| `orphan-open-quote` | **Read each against a second printing** | Fires only at density (>20 per 10k words): a scan's margin rules read as openers mid-sentence. Most are bare strays, but some stand where a LETTER was lost ("“ruth from truth") — pair those first, then strip the rest from the English rows in a migration, never a `BODY_CORRECTIONS` transform (it reaches translations) |
| `run-together` | Fix — a missing space after a full stop | Mechanical, but confirm it isn't an ellipsis or an abbreviation |
| `title-case-vs-body` | Pick the reading the body supports | Fires only on a lone letter after a hyphen ("Type-a" vs "Type-A") |
| `hyphen-space` | **Already normalized — read the survivors** | `corrections.rejoin_linebreak_hyphens` closes "self- righteous" on every import and every deploy, which took 434 to 26. What is left is what the rule refuses to guess: a resumption with a CAPITAL (either a flattened dash, "thus- Moses", or a real compound, "non- Israelite" — not separable mechanically), a suspended compound ("two- and twenty"), or a hyphen at a `</p>` boundary, which is a verse line |
| `lost-paragraphing` | **Read the chapter and put the breaks back.** Never mechanical | A whole CHAPTER whose blocks average 400+ words against a corpus median of 92 — `the-gospel-of-healing` ch03 is 4,602 words in two blocks, and `life-of-antony` sets 28 of its 45 chapters as a single block, one of them carrying an enumerated list inside it. The extraction lost the paragraphing; where it goes back is a judgement about the prose, so this reports and a person repairs. Deliberately measured per CHAPTER: four per-paragraph rules were tried and every one flooded, because a long paragraph is often the period's own voice and there is no oracle to ask. **There is an oracle after all — see "Restoring lost paragraphing" below.** Repair through the fixture AND `BODY_CORRECTIONS` — `seed_books` never rewrites an existing book's chapters — and re-pin the baseline |
| `space-before-punct` | **Report only. Do not write string pairs** | 197 instances. Deliberately NOT normalized: the space is often the visible edge of a deeper defect — a fused page marker ("everlasting xxivthings ?"), a broken sentence — and closing it up conceals the symptom. It is also bimodal (777/647/586 in the 17c texts, where it is the era's typography), so a global sweep would sand the period off Baxter. `english_audit.MECHANICAL` marks it |

## Restoring lost paragraphing

Do not choose the breaks by block length. **Read them off a scan of the edition
the text is a transcription of** — the compositor's first-line indent is the
oracle, and it survives into archive.org's OCR coordinates.

**When the book was imported from a PDF, that PDF is the oracle — not a random
archive.org scan.** `the-gospel-of-healing` (book #3, PR #1633, the corpus's
worst case: four Simpson chapters welded into 2-4 blocks of 1-2k words) was keyed
from the CMA PDF, and the archive.org scan is a DIFFERENT edition — its chapters
run in a different order (Principles before Objections) and would map breaks onto
the wrong prose. The source PDF is the same edition our text came from, so the
mapping is exact. Use PyMuPDF (`fitz`) on it and take the per-line left-x0 and
top-y0. **Two signals, and x0 alone finds only half the breaks:** (a) an x0
DEPARTURE from the page's modal body x0 — a numbered/hanging-indent item
out-dents (here to 108, body at 126, full-margin prose at 90); (b) a blank-line
VERTICAL GAP (~2x the median line gap) at the SAME x0 — the sub-paragraphs and
lettered sub-points (A./B./C.) inside a long item. Detect per page (margins drift
recto/verso). Skip a line that starts with a quote (displayed verse) and
LEAVE existing block boundaries alone — a gap-check tells a real paragraph
(gap≈2x median) from a spurious mid-paragraph split, and additive-only is the
rule. Two more traps this book hit, both worth internalising:
- **A seam applies BOOK-WIDE.** `apply_body_corrections` runs a slug's whole
  `paragraph_breaks` list against EVERY chapter, so a `(tail, head)` unique
  within its own chapter can still fire in another. Verify each pair matches
  once across the WHOLE book, and diff the other chapters' `<p>` counts
  before/after — extra breaks only LOWER the mean, so the audit never catches a
  leak.
- **`grep '"<slug>"'` the WHOLE of `corrections.py` first** (both dicts). This
  book already had a one-pair `BODY_CORRECTIONS` entry; a fresh second key made
  the paragraph_breaks silently dead (last key wins) until merged in.

1. **Check upstream first — the defect is usually not ours.** CCEL's own page
   for `the-reformed-pastor` ch04 carries the same 19 blocks with the same word
   counts, so nothing was lost on import and no importer change would help.
   reformedreader.org is the SAME etext lineage (it still reads "hut much more"
   where CCEL fixed the typo), so it is not an independent witness.
2. **Find the edition on archive.org** and pull `_djvu.xml`, not `_djvu.txt`.
   The text dump loses indentation, and its blank lines lie in both directions:
   page furniture swallows a real break at a page boundary, and a gathering
   signature at a page foot ("2", "o 3") manufactures a false one.
   ```bash
   curl -sS -L -o djvu.xml \
     "https://archive.org/download/<identifier>/<identifier>_djvu.xml"
   ```
3. **Measure the indent.** Each `<WORD coords="left,bottom,right,top,baseline">`;
   take each `<LINE>`'s min-left, and per page compare against the median (drop
   the running head and the "d by Google" footer first — the scan's own left
   margin drifts by hundreds of units between pages, so the threshold has to be
   per-page). On the 1862 Brown printing a paragraph opening sits ~85 units
   right of a body margin that varies by under ±15 — an unmissable gap. This
   also catches the openings at the TOP of a page, which is exactly where the
   text-dump heuristic is blind.
4. **Add only what was lost.** Count the scan's paragraphs against the stored
   blocks. Long blocks the scan shows whole stay whole (Baxter runs 577 and 637
   words unbroken across three pages each); a break the stored text has and the
   scan does not is left alone too. Splitting to satisfy the mean is inventing
   the author's paragraphing, not restoring it.
5. **Declare it as `paragraph_breaks`, never `replacements`.** A seam is plain
   prose with no markup in it, so a pair spelling out `"…experience."` →
   `"…experience.</p> <p>"` matches the derived, tagless `body_text` just as
   happily and writes block tags into a field that must never hold any.
   `corrections.restore_paragraph_breaks` takes `(tail, head)` seams and is
   guarded on the body actually carrying `</p>`; `Chapter.save()` re-derives
   `body_text` from the corrected HTML, so that field needs nothing.
   ```python
   "the-reformed-pastor": {
       "paragraph_breaks": [
           ("riches of the gospel from their own experience.", "Alas!"),
       ],
   },
   ```
   **Do not key the seams by chapter order** the way `dropcap_letters` is,
   however tempting the neighbouring precedent. A seam identifies itself by its
   prose, so leaving it unkeyed costs a few string scans over the book's other
   chapters and survives a renumbering — which is precisely what happened to
   this book when #1189 dropped a chapter's restated-title heading.
   `body_text` and `word_count` are unchanged by a pure re-paragraphing, so
   stored search vectors stay correct — no `backfill_search_vectors --all`.

## Procedure

1. **Run the audit** on the slug. The importer already printed the summary; get
   the detail with `--examples 0`.
2. **Read every non-mechanical finding in context** — open the chapter, not just
   the excerpt. The excerpt is 130 characters and will not tell you whether an
   anachronism is invented text or a quotation.
3. **Check the original** for anything you are about to change the *meaning* of.
   If you cannot check it, report it and stop; do not guess at what the author
   wrote.
4. **Has it already propagated?** If the work is translated, grep the other
   language fixtures for the same defect before fixing only the English:
   ```bash
   grep -l "<the wrong text>" backend/library/fixtures/content/books/<slug>.*.json
   ```
   Write the `BODY_CORRECTIONS` replacement to match in **any** language where
   the defect is numeric or a proper name (the `the-key-in-my-hand` entry does
   this); use `source_fixes.py` where the prose around it is localized.
   **When the defect propagated as DIFFERENT localized words per language**
   (`divine-songs-for-children`: an OCR "play"-for-"pray" in the EN body, echoed
   as Swahili `hawachezi`-for-`hawaombi`), neither of those fits — one pair can't
   match both, and `source_fixes` is one `(slug, order)` replacement across
   languages. Put **one language-scoped pair per edition in the SAME slug's
   `replacements`** (each bites only its own language, so `("but never play;",…)`
   and `("hawachezi kamwe",…)` coexist and reach prod on deploy). A translation
   pair still leaves its fixture stale — settle each edition by hand (see the
   translation failure mode), and check the Luganda/other editions before
   assuming they're wrong: here `lg` had already rendered the correct `batasaba`
   ("never pray") and needed no change.
5. **Apply**, then re-run the audit for that slug and confirm the class is gone.
6. **Settle the fixture** with the three commands above (`normalize_english_fixture`,
   `rederive_body_text`, `rederive_word_count`, each `--write`) — the fixture is
   what a fresh build loads and what the ratchet measures. NOT
   `regen_fixture.py`: it round-trips the committed files and never reads the
   DB, so it cannot carry a repair into them.
7. **Re-pin the baseline**: `manage.py audit_english --update-baseline`, and say
   in the commit message *what you fixed*, not just that the number moved.
   `tests_english_audit.py` fails if the baseline is stale in either direction.
8. **Report back** in the format below.

## Report format

Keep it short. The point is that someone can see what changed without reading
the diff.

```
<slug> — N findings, M fixed, K reported

Fixed
  • broken-smallcaps ×3 — "L ORD" → "LORD" (ch02, ch07, ch11); inside scripture
    quotations, so all three also affected the sw and lg editions
  • misspelling ×1 — "Heratii" → "Horatii" (ch04); spelled correctly two
    sentences later in the same paragraph

Reported, not fixed
  • anachronism ×1 (ch09) — "credit cards" in an 1897 text. Could not check the
    original edition from here; needs the source before anything is changed
  • hyphen-space ×17 — deferred to the normalization pass
```

## Failure modes seen so far

- **Fixing the fixture and thinking production is fixed.** `seed_books` never
  rewrites an existing book's chapter bodies — it runs `corrections.chapter_drift`
  and *reports* the disagreement, deliberately, because the same create-only rule
  that protects an approver's review state is what stops the seed overwriting
  bodies. So watch the seed output for drift, and remember: body text reaches
  production through `BODY_CORRECTIONS`; metadata needs a migration.
- **Reversed initials in a two-initial name (`A. R. Torrey` for R. A. Torrey).**
  A real defect class the audit can't see. Sweep: build canonical `X. Y. Surname`
  names from `authors.json` (`name`/`display_name`), then grep ALL book/sermon/bio
  content for the REVERSED order of each, and separately flag any surname that
  appears in BOTH orders; finish by dumping every `\b[A-Z]\. [A-Z]\. [A-Z][a-z]`
  mention and eyeballing the real figures (most hits are noise — `A. M.`/`P. M.`
  times, `M. E. Church`). Chapter/section TITLES that name a person by initials
  are the highest-risk visible spot, and — because titles are create-only (see
  the fixture-vs-prod note above) — a title already corrected in the fixture can
  still be wrong on prod, so verify those against the LIVE API, not just the file.
  The fix is the same metadata migration (Torrey `men-of-prayer-2` ch.6, #2459 →
  `0152`, model on `0121_recase_chapter_titles`). A migration under
  `migrations/` is not a content root, so after the API deploy is live, add a
  follow-up marker per `frontend/prerender-refresh/README.md` to re-prerender
  the page. 2026-09-16 sweep found no other cases.
- **Verifying a split-word sweep with a stranded-LETTER scan, or with the
  audit.** A pervasive-spacing repair (`feasting-at-the-table`, PRs #1356/#1370)
  is a hand-built list, and the audit is no safety net: `audit_english` has no
  split-word class, so it read 0 both before and after while `spirit ual` still
  shipped. A quick "any lone 1–2 char token left?" scan is no net either — it
  misses a split into a valid word plus a ≥3-char tail (`spirit`+`ual`,
  `resurrecti`+`on`, `follow`+`ed`). The only real check is to re-run the FULL
  detector — the one that flags a two-token pair whose concatenation is a word
  the corpus knows but whose pieces aren't both words — against the SETTLED
  fixture after `normalize`/`rederive`, and confirm zero real survivors. Skip
  that and the list ships one pair short, invisibly, past a green audit.
- **A `BODY_CORRECTIONS` pair whose `old` is plain prose.** Every declared pair
  is applied to `body_html` AND handed `body_text` by
  `tests_english_audit.test_the_fixture_is_clean`, which requires a no-op on
  both. A pair carrying markup or an entity (`<p>Amajor`) can only match the
  HTML and is safe; a pair that is pure text matches the tagless field too. This
  is what made paragraph restoration need its own key.
- **Widening the auto-fix set** because a class "looks mechanical". `hyphen-space`
  looks mechanical and is 434 instances of a job that belongs in the ingest
  pipeline.
- **Trusting the excerpt.** It is a 130-character window with the HTML stripped;
  quotation nesting and paragraph boundaries are invisible in it.
- **Adding a check without a precision test.** The first version of this scanner
  reported 8,917 findings and was useless — it flagged 17th-century spaced
  punctuation as an artifact and every capitalised word starting with I as a
  fused drop cap. Every check in `english_audit.py` carries a test in
  `tests_english_audit.py` that separates the defect from the convention. A
  check without one will re-flood the report and the report will stop being read.
- **"Fixing" a book when the DETECTOR is what's wrong.** When a whole book or a
  whole class lights up, suspect the trigger before the text and measure its
  corpus-wide precision first — `audit_english --class <cls> --json`, then eyeball
  the trigger word in every hit. `amanda-smith-autobiography` audited as 18
  anachronisms and was clean: `cars?` fired on railroad cars, streetcars, balloon
  cars and biblical chariots, scoring **41 false / 0 true across the whole corpus**
  (an author before ~1905 cannot mean a motor-car except in invented text). The
  repair was to DELETE the trigger and re-pin, not to touch a single book. A
  trigger near 0% precision isn't triaging — it trains the reader to skim the
  class — so removing it is the fix; if the real defect it once guarded still
  matters, replace it with a narrower check that has its own precision test
  (`cars?` guarded invented COMMODITY LISTS, not the word — that shape wants its
  own detector). Shipped in #1609.
- **Reading GROWTH as a new defect without checking.** The ratchet says a work
  that grew has a new defect — usually true, but a neighbouring edit can tip a
  PRE-EXISTING chapter over a threshold without touching its prose.
  `the-reformed-pastor` ch04 sat at ~385 words/block, just under
  `MEAN_BLOCK_MAX` (400); when #1189 stripped the `<h2>` restating the chapter's
  own title, one block fewer put the mean at 405 and `lost-paragraphing`
  appeared. Nothing about the paragraphing had changed — and per **Restoring
  lost paragraphing** above, CCEL carries the same 19 blocks, so it was never
  ours to begin with. Before repairing or re-pinning, get the block distribution
  and ask whether the defect is new or newly VISIBLE. The repair is the same
  either way, but what belongs in the commit message — and how hard you should
  look at the edit that "caused" it — are not.
- **A second `BODY_CORRECTIONS` entry for a slug that already has one.**
  `BODY_CORRECTIONS` is a dict literal, so two `"slug": {...}` keys don't merge —
  the LAST one silently wins and the first is dead. `feasting-at-the-table`
  already carried a 3-pair ch7 drop-cap entry, and a fresh 66-pair entry added
  above it did nothing until the two were folded into one. `grep -n '"<slug>"'
  library/corrections.py` before adding; if it's there, MERGE into it. The tell
  is `normalize_english_fixture` reporting "0 fields" when you expected edits.
  **And the entry `grep` finds may be the WRONG dict.** `CORRECTIONS` (metadata:
  `chapter_titles`, importer-only) and `BODY_CORRECTIONS` (body, deploy chain) are
  keyed independently, so `grep '"<slug>"'` can land you on a `chapter_titles`
  entry and tempt you to add your body `replacements` there — where nothing reads
  them. `apply_body_corrections` only walks `BODY_CORRECTIONS`, so the pairs are
  dead with the SAME "0 fields" tell. `way-into-holiest` had a `CORRECTIONS`
  `chapter_titles` entry and NO `BODY_CORRECTIONS` one; the fix was a fresh
  `BODY_CORRECTIONS` entry, not a merge. Confirm which dict the match is in, and
  before running the three settle commands, verify the pairs bite:
  `apply_body_corrections(slug, order, body) != body` in a shell.
- **A quote-insertion pair anchored at end-of-string is not idempotent.** A pair
  that only ADDS a mark and whose `old` is a suffix of its `new` (`its power.` ->
  `its power.”`) re-fires forever — `apply_body_corrections` is run twice by
  `SettledBodyIdempotenceTests`, giving `power.””`. Anchor the trailing context
  so `old` can't recur: `its power.</p>` -> `its power.”</p>` (a no-op on the
  tagless `body_text`, which is fine — `rederive_body_text` carries the mark
  there from the fixed HTML). A mark inserted mid-string breaks the substring on
  its own and is already idempotent.

  **That anchor trick runs out, and then you need a GUARD.** Any pure insertion
  has `old` inside `new`, so the rule is general, not a quirk of quote marks —
  and consuming the preceding context only works when there IS preceding
  context. Restoring `ministry-of-intercession` ch18's six deleted `<h4>`
  headings, five could anchor on the `</p> <p>` seam ahead of them and the
  sixth could not, because it opens the chapter. Hence `restored_blocks`, a
  fourth `BODY_CORRECTIONS` key beside `replacements`, `paragraph_breaks` and
  `dropcap_letters`: `restore_dropped_blocks` takes `(anchor, block)` and skips
  a body that already carries the block. It restores a `<h4>` note heading in
  `ministry-of-intercession` and a `<p>` sermon TEXT in
  `selected-sermons-edwards` — hence the general name. Guarding on the OUTPUT is idempotent
  wherever the insertion lands, needs no anchor gymnastics, and reads as what it
  means. Anchor each on its `<p>` so it cannot touch `body_text`, and add the
  key to `test_no_replacement_pair_is_dead` or nothing will notice when the
  paragraph it titles is edited out from under it.
- **A display line UNWRAPPED to loose text is `wrapped_blocks`, not
  `restored_blocks`.** The Gutenberg importer once handed centred `<div>` lines
  (headings, datelines, drop-cap opening paragraphs) to the sanitizer, which
  kept the text and dropped the tags. Nothing is missing, so inserting would say
  it twice. `wrap_loose_blocks` takes `(head, tag)` (or `(head, tag, tail)` when
  the line ran into a loose caption) and wraps the run exactly as
  `ingest.display_line` would emit it, guarded so it disarms on a re-import.
  Check every entry against the importer's own output from the edition's
  markup (`HurlbutDisplayLineTests` shows how), and do every edition at once.
- **Two keys on one book can defeat each other, and neither PR's tests see
  it until both land** (`a-retrospect`, 2026-09-24: #3401 cut ch12's MIDI
  transcriber's note with a `replacements` pair while #3404 wrapped that same
  note and the verse after it in `wrapped_blocks`). `apply_body_corrections`
  runs `replacements` → `paragraph_breaks` → `restored_blocks` → `back_matter`
  → `wrapped_blocks`, and two failures follow from that order:
  - A pair whose OLD or NEW ends on a line that a later wrap gives a `<p>` is
    dead in the settled fixture ("</p> 2. Why live" becomes "</p> <p>2. Why
    live"). Anchor it on the text BEFORE the cut instead ("other spheres.</p>
    [<i>Transcriber's…] " → "other spheres.</p>").
  - A wrap entry for a line another key CUTS names nothing. The cut wins
    (apparatus is not the author's text), so drop the wrap entry and lower its
    test's per-edition line count.
  When a merge conflicts inside a book fixture, don't pick a side. Run both
  sides' chapter through the MERGED `settled_chapter_body`. If they settle to
  the same text, write that text (re-derive `body_text`/`word_count` from it,
  as `Chapter.save()` does). If they don't, the difference is one of these
  interactions. Then check that the text production holds (the fixture before
  either PR) settles to exactly what you wrote.
- **A STRUCTURAL repair must land in every edition at once.**
  `tests_translation_markup` pins a translation's ordered TAG SEQUENCE against
  its English, so adding six headings to the English alone fails it — and that
  gate, not taste, is why a repair to shipped text has to be tag-neutral unless
  you do every language in the same commit. Check the editions
  run in lockstep before you promise it: `ministry-of-intercession` ch18 has the
  six notes at the same paragraph indices in en and hi, which is what made the
  headings restorable at all. Diff `re.findall(r'<(/?\w+)', body_html)` per
  chapter across the editions as your own check — the test only tells you
  afterwards, and only that something moved. And spell the restored element with
  the tag the SOURCE used, not the one that merely looks right: the guard is a
  string match, so a heading declared `<h3>` where Gutenberg had `<h4>` fails to
  recognise its own repair once the importer stops eating it, and a re-import
  then carries BOTH. Declared with the source's tag, the correction disarms
  itself the day the root cause is fixed.
- **Forgetting the baseline is corpus-wide, so it collides in parallel.**
  `english_audit_baseline.json` is generated from every fixture, so ANY two PRs
  that touch ANY fixture collide on it — and invisibly, because each branch
  re-pins correctly against a corpus that lacks the other's edit. Both CI runs
  pass; main fails the moment the second one lands. That is exactly how
  #1189/#1190 left main red on 2026-08-28. If you re-pin, fetch first and
  re-pin again right before merge; if main is already red on
  `tests_english_audit`, check whether a fix is already open before writing one.
  **Resolving the conflict: take the UNION of both sides' removals.** When your
  branch and main each cleared a *different* work's finding, git shows the two
  entries as an either/or hunk — but each side legitimately deleted its own, so
  keep NEITHER (drop both blocks), not one. Confirm against the merge-base (both
  entries were present there) and prove the resolution by running the ratchet:
  `python manage.py test library.tests_english_audit.EnglishAuditRatchetTests`
  — it is a `SimpleTestCase` that rescans the fixtures (no DB), so a green run
  means the resolved baseline matches the corpus work-for-work (PR #1611).
- **A translation/re-import PR can re-serialize a whole `*.en.json` and collide
  with your targeted fixes — do NOT hand-merge it** (2026-09-07: PT batch #1861
  re-serialized all of `gleanings-among-the-sheaves.en.json` — 305/306 lines —
  while en-fix #1862 changed 15 lines; `git merge` produced one huge asymmetric
  conflict spanning every chapter). A raw JSON three-way merge here silently
  drops fixes or mangles bodies. Resolve by REBUILDING, not by editing markers:
  take main's version of the file (`git checkout origin/main -- <file>`), re-run
  your declared repairs through `normalize_english_fixture --write` +
  `rederive_body_text --write` + `rederive_word_count --write` so the fixes land
  on the current serialization AND the derived columns re-derive, then re-pin the
  baseline. Because the fix lives in `BODY_CORRECTIONS` (not hand-typed into the
  fixture), rebuilding is lossless — that is the whole point of declaring it there.
- **A `replacements` pair containing a straight `"` fails the dead-pair gate,
  even when the fix is correct** (the seven-sermon es cleanup, 2026-09-05).
  `test_no_replacement_pair_is_dead` builds its corpus with `json.dumps`, so a
  stored straight double-quote reads back **JSON-escaped** (`\"`); a pair whose
  `old`/`new` carries a literal `"` then matches neither the raw text (already
  settled) nor the escaped corpus, and is flagged dead. Curly `“ ”` are not
  escaped by `json.dumps`, so they are fine — this bites only straight-quoted
  works (the pauls-praise sermon here). Anchor such a pair on the words BESIDE
  the quote, keeping the `"` out of the pair entirely (`it to be able to
  apprehend` -> `is to be able to apprehend`, not `"know mysteries" it…`). The
  fix still applies correctly to `body_html`; you have only moved the anchor.
- **A pair written for a TRANSLATION leaves that fixture stale, silently.**
  `apply_body_corrections` is keyed by slug alone, so its command visits every
  language's stored rows and production repairs them all. Nothing does that to
  the committed file: `normalize_english_fixture` globs `*.en.json`, and so does
  `tests_english_audit.test_the_fixture_is_clean` — so a non-English pair is
  applied nowhere in the repo and no gate says a word. Settle that fixture by
  hand in the same commit (apply `apply_body_corrections` per chapter, write
  with `content_fixtures.render_rows`), then let `rederive_body_text` and
  `rederive_word_count` — which ARE every-language — catch the derived columns.
  Check first that the corrections are a no-op on that language apart from your
  own pairs: the hyphen rejoin and `strip_footnote_markers` are rules, they run
  on every body, and neither was written against Devanagari or Arabic.
- **A defect class the audit cannot see: DROPPED ANCHOR TEXT — and its cause is
  ONE SELECTOR.** `ministry-of-intercession` shipped five bare `()` and one lone
  `)` where Gutenberg had `(<a href="#nt.A" class="pginternal">Note A.</a>)`,
  six cross-references to endnotes the book still carries. Not OCR, and not the
  importer: `sanitize.DROP_SELECTORS` carries `"[class*=pginternal]"`, and
  `_clean` **decomposes** the drop-selectors before it unwraps everything else —
  so a non-allowlisted `<a>` normally survives as its text, but a *Gutenberg*
  one is deleted whole. Gutenberg puts `class="pginternal"` on every internal
  link, so this reaches every one of the 17 English works that name Gutenberg
  as their source. Check it in one line:
  ```python
  clean_fragment('<p>x (<a class="pginternal" href="#n">Note A.</a>)</p>')
  # '<p>x ()</p>'      — without the class: '<p>x (Note A.)</p>'
  ```
  The SAME line eats the `<h4>` heading each reference points AT: the heading's
  only child is that anchor, so decompose empties it and `_clean`'s empty-block
  regex then deletes the heading itself. One cause, two symptoms — and neither
  the grep below nor `stray-parens` sees the second, so if a work has an endnote
  or glossary chapter, read its opening lines too. **A SECOND selector does the
  same thing to a heading, and it is not Gutenberg-specific**: `"[class*=note i]"`
  was written for CCEL's footnote apparatus and substring-matches anything with
  `note` in a class, including Gutenberg's own `<h3 class="note">NOTE A.</h3>`
  and `<div class="footnote">`. That is how `holy-in-christ` ch33 lost all seven
  of its `NOTE A.`–`NOTE G.` headings and every footnote block pointing at them,
  leaving seven bare `<hr/>`s where the notes divide — and, unnoticed until the
  corpus was measured, the SCRIPTURE TEXT of four Edwards sermons (`p.note`), so
  each opened mid-argument with no text.
  **The selector is FIXED** — `sanitize.KEEP_PREDICATES` keeps the exact
  lowercase token `note`, which is the one value neither transcriber's
  vocabulary shares, and `scripts/audit_keep_predicates.py --rule note` is the
  corpus-wide measurement (2 of 36 works change; CCEL untouched). The footnote
  BLOCKS stay dropped by design: their markers are dropped too, so restoring the
  blocks alone would orphan the note text.
  Shipped rows are never re-imported, so each needs its own repair with
  `restored_blocks` on the book's `corrections.py` key, as
  `ministry-of-intercession` does. **Edwards is DONE** — the four sermon texts
  were restored that way (PR #1575), and the pattern there is worth copying:
  the correction restores the block, the fixture ships the settled form written
  with `content_fixtures.render_rows`, and a test strips the block back out and
  asserts the correction replaces it (asserting the settled fixture alone passes
  with the correction deleted, while the live rows silently revert).
  **`holy-in-christ` is DONE too** — ch33's seven `NOTE A.`–`NOTE G.` headings
  and ch5's `NOTE.` were restored the same way (PR #1929, test
  `test_a_stripped_note_heading_comes_back`), and the es/fr/pt/sw editions were
  translated from the repaired English, so they carry them already. Watch
  `quote_seed` on any such repair: it anchors a quote by 0-indexed BLOCK
  position, so inserting a paragraph shifts every anchor below it.
  ```bash
  grep -c ' ()' backend/library/fixtures/content/books/*.json
  ```
  Corpus-wide that was 8 sites in 3 works and every one real, so the bare-`()`
  shape is now the `stray-parens` audit class (exact, and cheaper than this
  grep); an unbalanced-paren check would NOT be (57 rows, mostly period prose),
  and that is why there isn't one. Six of the eight were `holy-in-christ` ch10 —
  the same selector, the same book-internal cross-references
  (`(<a class="pginternal">ch. 3</a>)`) — repaired 2026-09-05 along with a
  seventh that both the grep and the check miss: ch12's
  `(see ‘<a>Sixth Day</a>’)` shipped as `(see ‘’)`, which is not an EMPTY pair.
  **The shipped text still has to be repaired by string pair,
  even after the selector is fixed**: a re-import runs `upsert_book`, which
  deletes and recreates every chapter and re-runs the title heuristics. Restore
  the headings too — `restored_blocks`, in every edition at once (see the
  structural-repair rule below); an earlier draft of this bullet said the repair
  had to be tag-neutral, and that was only true of a repair to ONE edition.
- **A restored cross-reference needs TWO questions answered, not one.** "What
  did the anchor say" is the Gutenberg HTML's to answer; "did the author print a
  reference here at all" is only the scan's, and for `holy-in-christ` ch10 the
  printings disagree. Two 1887/1888 scans (`holyinchristthou00murr`,
  `holyinchristtho00murrgoog`) run the sentence with NO references — "deep
  Restfulness, humble Reverence, entire Surrender" — while the Revell printing
  Gutenberg was keyed from (`holyinchristthou00murruoft`, p. 88) prints
  "(ch. 3)" … "(ch. 8)". Had only the first two existed, restoring the anchors
  would have put a later editor's apparatus into Murray's prose and called it a
  repair. Match the scan to the transcription before trusting either: the page
  numbers line up (Gutenberg's `pgmark` against the scan's running header) and
  that is the cheapest way to tell which printing you are reading.
- **Verifying a citation needs the scan, but not `_djvu.xml`.** The XML is for
  paragraphing, where indent coordinates are the oracle. To settle whether a
  wrong reference is the author's or ours, `_djvu.txt` is enough and far
  cheaper — and it is the difference between `BODY_CORRECTIONS` and
  `source_fixes` + a migration. `ministry-of-intercession` ch13 cites Luke ix.
  15 for a quotation of Luke 9:18; the 1898 printing (archive.org
  `ministryofinterc00murruoft`, p. 135) has the error, so it is Murray's, and
  Gutenberg only carried it forward. Find the scan by identifier with
  `archive.org/advancedsearch.php?q=title:(...) AND creator:(...)`, then take
  the OLDEST printing — a 1982 reprint is usually borrow-only, with no text.
- **A `source_fixes` migration: copy 0069, NOT 0066/0075.** Those two each wrote
  `re.sub(r"<[^>]+>", " ", html)` inline to rebuild `body_text`, because a
  historical model runs no `save()` hook — and that sub is subtly wrong twice
  over: it spaces EVERY tag (so an inline `<em>` before a comma yields "power .
  Our"), and it never unescapes. `backfill_body_text` only fills an EMPTY
  `body_text`, so the drift NEVER self-corrects; 0084 says so in its own
  docstring and 0085/0094 exist to clean up after them. Two ways out, and the
  second is better for a reference swap:
  - re-derive with the canonical helpers — `text.html_to_text(fixed)` and
    `text.word_count(fixed)`, what `save()` actually calls (0084, 0103);
  - or **apply the same replacement to `body_text` directly** (0069), which
    cannot drift at all because it touches only the characters you meant. A
    citation survives tag-stripping intact, so the pair matches; and a reference
    swap is one token for one token, so `word_count` needs no write. Do NULL
    `search_vector` either way, or search keeps matching the old reference.

  The cheap proof that you got it right, before you push — reconstruct the
  pre-fix row from `git show origin/main:<fixture>`, run it through
  `apply_source_fixes` then `settled_chapter_body` then `html_to_text` /
  `word_count`, and assert all three columns equal the committed fixture and
  that a second pass is a no-op. That is the whole deploy path in ten lines, per
  language, and it is what turns "the tests pass" into "production converges".
- **Back matter shipped as the last chapter's closing paragraphs** (2026-09-24,
  found measuring #3355). Gutenberg texts fold the back of the printed book into
  the final section: `reality-of-prayer` ch16 ran Bounds's last line into
  "Printed in the United States of America" and 60 blocks of Revell's catalogue;
  `how-to-bring-men-to-christ` ch13 ended on Meyer ad blurbs and a merged
  "Transcriber's Notes" `<h3>`; `life-and-diary-of-david-brainerd` ch12 on the
  transcriber's errata note, headless, reading as Edwards's own words. The
  audit sees none of it, and the es and sw editions TRANSLATED it. Repair with
  the `back_matter` key: `(last, first)` seams, one per edition, where `last`
  is the author's closing block (ending `</p>`) and `first` opens what follows.
  `strip_back_matter` cuts only where the two stand together, so it cannot fire
  in another chapter; `ShippedBackMatterTests` checks every declared edition
  from the declarations alone. Find more with a grep of every body for
  `transcriber|printed in the united states|\b\d{1,2}mo\b` — and remember a
  note whose heading was dropped won't say "transcriber" (Brainerd's didn't).
  `import_gutenberg` now drops note boxes, "Transcriber's Note" sections and a
  last-section colophon's tail (#3377). **Still shipped, not yet repaired:**
  `separation-and-service` ch4 and `things-as-they-are` ch35 (a transcriber's
  note, the latter after a "LONDON: MORGAN AND SCOTT" imprint), and the inline
  MIDI note in `a-retrospect` ch12.
- **A defect class the audit CANNOT see: the stored "English" is a modern AI
  PARAPHRASE, not the author's public-domain text** (2026-09-06). Some books
  stored `source_type=public_domain` were run through a modernization pass that
  swapped the KJV the author quoted for a modern (ESV) version, and at worst
  SILENTLY DELETED author sentences. `the-secret-of-guidance` (Meyer) shipped the
  meta-artifact "Not possible to remove the adverb." 4× (ch06, ch07×3), each
  replacing a real Meyer sentence; also garbled Job 23, and 8 chapters where the
  genuine has 9. `audit_english` sees NONE of this — a smooth deletion or a
  reworded sentence leaves no flag, and modern scripture is valid text. Detect
  with a KJV-archaism density scan (thee|thou|thy|unto|shalt|hath|saith|cometh…)
  per 10k words: genuine 19th-c classics run 15–190; the altered cluster runs
  1.5–4.5 (modern-authored bios/compilations are legitimately ~0). Confirm by
  diffing one scripture quote against the KJV, or a chapter against the
  CCEL/Gutenberg genuine text. **Repair is a genuine RE-IMPORT** (`book-import` /
  `import_ccel`), NOT `BODY_CORRECTIONS` string pairs — a paraphrase that left a
  fingerprint on 4 deletions has likely deleted others invisibly, so patching
  can't restore what's gone. This matters most before translating: the altered
  English propagates into every translation (already reached es for `humility-2`
  and `the-inner-chamber`). Confirmed altered: secret-of-guidance (damaged),
  god-of-all-comfort, humility-2, the-inner-chamber; full catalog is a backlog
  (see memory `modernized-scripture-in-pd-classics`).
- **An audit that calls a book clean can be describing its own blind spots.**
  `the-bruised-reed` (re-imported from Pickering's 1838 scan, #1943) passed
  `english_audit` at every stage while shipping ~180 stray opening quote marks
  (scanned margin rules; `orphan-close-quote` looks only the other way), a
  sentence the scan lost a whole line from, and ~90 misreads that land on REAL
  words (`derived rot God`, `the Sear of the Lord`, `eat the it of your own
  ways`). What found them: align the whole text word by word against a second
  printing (here Grosart's 1862, the edition it replaced) and READ every
  difference, not just the non-dictionary ones. Most differences are the
  witness's own damage or house style (`burthen`, `Isai.`, `Balthasar`), so the
  witness is consulted, not obeyed — and it overturns reviewers too (Grosart
  reads "and **blessed** God afterwards", not the `blesseth` a review proposed).
  The `orphan-open-quote` class now sees that shape. **A content-blind
  transform must not go in `BODY_CORRECTIONS`**: an entry reaches every
  language edition of its slug on every deploy, and "no `”` in this body" is
  NOT a proof it sets no quotes — 126 translated bodies quote with `‘…’` or
  `„…“` and carry no `”`. Do a one-off strip of the English rows in a
  migration (0138) instead. String PAIRS on stored text are fine there — they
  cannot match another language — and reach prod through
  `apply_body_corrections` on deploy with no migration; a chapter TITLE needs
  one (`seed_books` never rewrites it).
  **A stored-text pair that rewrites an earlier raw-scan pair's OUTPUT kills
  that pair** — neither side is left in the fixture, and
  `test_no_replacement_pair_is_dead` fails. Change the earlier pair to write
  the final text directly; the stored-text pair then only ever fires on prod.
- **Quotations closed with the WRONG MARK — a class the quote-style test could
  not see** (2026-09-11, 390 pairs across 25 works). Two shapes: a curly opener
  closed by a straight mark (`‘Search the scriptures', says` — the Whitefield
  sermons, `christ-the-believers-wisdom` en+pt, `waiting-on-god` ×4 editions),
  and an OPENER standing as the closer (`it is written “the living God“;` —
  `evening-by-evening` ×13, every quotation in pt `all-things-for-good`
  ch9–11). `QuoteStyleTests` counts double marks only, and a straight single is
  also an apostrophe, so neither registered. `quote_marks.mispaired_marks` is
  the rule now, and `test_no_quotation_closes_with_the_wrong_mark` holds the
  corpus at zero. It deliberately skips the ambiguous shapes — a closer whose
  space sits on the wrong side (`“Oh “says one`), a straight mark followed by a
  lowercase word (`‘is in them that do excel' in virtue`, or a possessive
  plural, `disciples' heads`) — so read for those by hand.
  **Root cause of the backwards closers: `quote_marks.convert`** (used by
  `normalize_quotes.py`, migration 0084 and the `build_*` commands for
  morning/evening, our-daily-walk, thoughts-for-the-quiet-hour) counted ANY
  tag's `>` as opening context, so `"<i>seen</i>"` became `“<i>seen</i>“`.
  Fixed: an inline tag is transparent and only a block start opens. When a
  corpus class clusters after one character, look for the converter that wrote
  it before writing 100 pairs.
  Three things bit, worth knowing before the next sweep:
  - **Fixing a backwards closer GROWS `orphan-close-quote`.** `_orphan_quotes`
    keeps a running depth across blocks, so every `“` used as a closer counted
    as an opener and masked a genuine orphan further down. Five surfaced
    (our-daily-walk's Isa 38:15 and Jacob's speech, comfort-for-the-desponding's
    verse lines, …); all pre-existing, none at a repaired site. Diff the
    findings before/after (`english_audit._orphan_quotes` over
    `git show origin/main:<fixture>`) before re-pinning, and say they were
    newly visible. **The verse-consistency ratchet does the same**: once pt
    all-things-for-good's quotations closed, its fragments of 2Tm 1:9 and Rm
    7:18 became readable as quotations and showed as "divergent" renderings.
    Partial quotes of one verse aren't a conflict, so the right answer is to
    re-pin (`audit_verse_consistency --update-baseline`), not to reword.
  - **A tagless pair must be unique in `body_text` too.** A tag becomes a space
    there, so `" redemption.' "` — unique in the HTML — also matched a
    legitimately straight-quoted `'…redemption.'</p>` in the rendered text, and
    `test_the_fixture_is_clean` failed. Check a pair's `old` against
    `html_to_text` of every edition, not just `body_html`.
  - **Three hundred pairs want a generator, not a hand list** — and the
    generator must never let a pair's context reach a site not yet repaired, or
    the later pair rewrites the earlier one's `new` and the earlier one reads as
    dead. Prove the lot the way the deploy does: `settled_*_body(fixture)` must
    equal your target for every row of every edition, and settle again to a
    no-op. Several translation fixtures turned out already unsettled (English
    name repairs — "Deja Vue", "Stocklholm" — also match the sw/es/lg text), so
    assert `settled(target) == settled(fixture)` rather than `== target`. Then
    prove the PRODUCTION path too, which starts from already-settled text: load
    `git show origin/main:backend/library/corrections.py` as a module and
    assert `settled_new(settled_old(fixture)) == settled_new(target)` per row.
  - **The `--write` settle commands re-serialise whole files.**
    `rederive_body_text` / `rederive_word_count` write with `render_rows`, and
    11 of this sweep's 40 fixtures don't round-trip through it (the known
    whitespace drift), so `--write` would have turned a one-mark fix into a
    whole-file diff. Check `render_rows(json.loads(t)) == t` first; where it
    fails, substitute the three encoded values (`body_html`, `body_text`,
    `word_count`) in place, then run the commands WITHOUT `--write` and expect
    "0 rows".
  **`sermons-on-several-occasions` is NOT ours**: its ~140 unpaired marks
  (`“of one heart “and one soul?”`) are in CCEL's text and in the Wesley
  Center's transcription of the 1872 Jackson edition alike. Settle each against
  a printed scan; don't guess from context.
