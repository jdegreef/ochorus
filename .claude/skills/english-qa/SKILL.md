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

`apply_body_corrections` also carries one RULE rather than a list — the
line-break hyphen rejoin — and it runs for every work, not just the 22 with a
declared entry. **Declared pairs run first**, so a hand-written repair always
beats the rule: `the-inner-chamber` declares "scales- only" → "scales — only",
where the trailing hyphen is a flattened dash, and with the rule first that em
dash was lost.

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

# after adding a rule-based repair, bring the committed fixture in line:
DJANGO_DEBUG=true uv run python manage.py normalize_english_fixture          # dry run
DJANGO_DEBUG=true uv run python manage.py normalize_english_fixture --write
```

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
| `anachronism` | **Read the original edition.** Never guess | This is how invented text shows up. The author may also be quoting someone, or the check may be firing on "car" inside a place name |
| `misspelling` | Fix if it's a name or place; leave period spellings | Moody's "Heratii" is wrong two sentences after he spells Horatii correctly. But a 17th-century spelling is not a misspelling |
| `orphan-close-quote` | Read the passage | A close with nothing open usually means an attribution broke mid-sentence — the surrounding text is the real defect |
| `run-together` | Fix — a missing space after a full stop | Mechanical, but confirm it isn't an ellipsis or an abbreviation |
| `title-case-vs-body` | Pick the reading the body supports | Fires only on a lone letter after a hyphen ("Type-a" vs "Type-A") |
| `hyphen-space` | **Already normalized — read the survivors** | `corrections.rejoin_linebreak_hyphens` closes "self- righteous" on every import and every deploy, which took 434 to 26. What is left is what the rule refuses to guess: a resumption with a CAPITAL (either a flattened dash, "thus- Moses", or a real compound, "non- Israelite" — not separable mechanically), a suspended compound ("two- and twenty"), or a hyphen at a `</p>` boundary, which is a verse line |
| `lost-paragraphing` | **Read the chapter and put the breaks back.** Never mechanical | A whole CHAPTER whose blocks average 400+ words against a corpus median of 92 — `the-gospel-of-healing` ch03 is 4,602 words in two blocks, and `life-of-antony` sets 28 of its 45 chapters as a single block, one of them carrying an enumerated list inside it. The extraction lost the paragraphing; where it goes back is a judgement about the prose, so this reports and a person repairs. Deliberately measured per CHAPTER: four per-paragraph rules were tried and every one flooded, because a long paragraph is often the period's own voice and there is no oracle to ask. **There is an oracle after all — see "Restoring lost paragraphing" below.** Repair through the fixture AND `BODY_CORRECTIONS` — `seed_books` never rewrites an existing book's chapters — and re-pin the baseline |
| `space-before-punct` | **Report only. Do not write string pairs** | 197 instances. Deliberately NOT normalized: the space is often the visible edge of a deeper defect — a fused page marker ("everlasting xxivthings ?"), a broken sentence — and closing it up conceals the symptom. It is also bimodal (777/647/586 in the 17c texts, where it is the era's typography), so a global sweep would sand the period off Baxter. `english_audit.MECHANICAL` marks it |

## Restoring lost paragraphing

Do not choose the breaks by block length. **Read them off a scan of the edition
the text is a transcription of** — the compositor's first-line indent is the
oracle, and it survives into archive.org's OCR coordinates.

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
5. **Apply**, then re-run the audit for that slug and confirm the class is gone.
6. **Regenerate the fixture** (`uv run python scripts/regen_fixture.py`) — the
   fixture is what a fresh build loads and what the ratchet measures.
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
