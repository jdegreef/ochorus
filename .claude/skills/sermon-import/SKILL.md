---
name: sermon-import
description: Add new English sermons to the Ochorus sermon shelf, end to end — choose them, import the text (CCEL / Gutenberg / web / SermonIndex via import_sermons), repair the English, write the summary + study questions, assign topics, draw the share cards, and ship one PR per author batch. Use when asked to add sermons, grow the sermon count, "do a <preacher> batch", or import a specific sermon. Encodes the traps that cost earlier batches a re-run (CCEL's modernised Spurgeon text, order-of-service trailers, sermons already inside an anthology book, the og generator redrawing every card). This is a living playbook — append new failure modes as we find them.
---

# Importing sermons

A sermon on Ochorus is not one file. A shipped English sermon carries, and CI
or the page expects, all of:

| Piece | Where | Checked by |
|---|---|---|
| Catalog entry (source, URL, overrides) | `backend/library/sermon_catalog.py` | `tests_import` |
| The fixture row (body, ref, date, source_url) | `backend/library/fixtures/content/sermons/<slug>.en.json` | `tests_fixture`, `tests_sanitize`, `tests_english_audit` |
| OCR / keying repairs | `BODY_CORRECTIONS` in `backend/library/corrections.py` | `SettledBodyIdempotenceTests` |
| `summary` + four `study_questions` | inside the fixture row | `tests_sermon_payload`; the [[sermon-questions]] rules |
| Topic shelf membership | `TOPIC_SERMONS` in `backend/library/topic_seed.py` | the topic shelves |
| Share card + manifest line | `frontend/static/og/sermons/<slug>.png`, `og-manifest.json` | `SermonShareCardTests`, `sermonCards.test.ts` |

Work in **author batches of ~10–14, one PR per batch** (title like "Spurgeon
sermons, batch 2 (18 → 31)"). Parallel sessions can each take an author.

## 1. Choose

- **Public domain first.** The reader's classics are PD — that is the legal
  footing (root CLAUDE.md). CCEL and Gutenberg are the default sources. The
  SermonIndex block in the catalog carries some in-copyright speakers "with
  permission"; don't extend that to a new living or recent author without the
  founder saying so.
- **Curation rule** (top of `sermon_catalog.py`): themed to the library's
  readers — prayer, comfort in trial, assurance and grace, warm evangelistic
  appeal. A readable dozen or two per author; never bulk-import a volume.
- **Read every pick in full before shipping it**, and drop any that carry a
  demeaning passage about a people (the Simpson batch dropped a Jews-and-money
  trope; Spurgeon batch 2 dropped *The Sin of Unbelief* for the "unbelief made
  the Jew murder Christ and wander" passage), or are bound to an occasion (a
  building-fund or Hospital-Sunday collection appeal, a farewell).
- **Collision checks** — a slug is shared across languages and must be new:
  `ls backend/library/fixtures/content/sermons/<slug>.*`. Then check the sermon
  isn't already a CHAPTER of a book — Spurgeon's are gathered in
  *Spurgeon on Prayer*, *Spurgeon on the Holy Spirit* and others (*The Throne
  of Grace*, *The Comforter*, *Prayer, the Cure for Care* live there):

  ```python
  # titles of every English chapter, to grep candidate titles against
  import json, glob
  for f in glob.glob('backend/library/fixtures/content/books/*.en.json'):
      for r in json.load(open(f)):
          if r['model'] == 'library.chapter': print(f, '|', r['fields']['title'])
  ```

- **Check the TEXT, not just the titles.** Authors reworked sermons into
  books under new titles: Ryle's *Let Any Man Come* (The Upper Room) is
  *Holiness* ch. 18 word for word, and a quarter of *The Good Way* is *Old
  Paths* ch. 15. Index every 10-word run of the English library (books and
  sermons) and measure each candidate against it; anything over a few percent
  is the same text. Shared Scripture alone scores 0–2%.

  ```python
  # in a Django shell over the scratch DB: share of each new sermon's 10-grams
  # that already occur somewhere in the English fixture
  import json, glob, re, collections
  from library.models import Sermon
  N = 10
  toks = lambda t: re.findall(r"[a-z]+", t.lower())
  idx = collections.defaultdict(set)
  for f in glob.glob('library/fixtures/content/books/*.en.json') + glob.glob('library/fixtures/content/sermons/*.en.json'):
      for r in json.load(open(f)):
          w = toks(r['fields'].get('body_text') or '')
          for i in range(len(w) - N):
              idx[' '.join(w[i:i + N])].add(f.split('/')[-1] + '#' + str(r['fields'].get('order', '')))
  for s in Sermon.objects.all():
      w = toks(s.body_text); grams = [' '.join(w[i:i + N]) for i in range(0, len(w) - N, N)]
      hits = collections.Counter(l for g in grams for l in idx.get(g, ()) if not l.startswith(s.slug + '.'))
      print(s.slug, [(l, round(100 * n / len(grams))) for l, n in hits.most_common(2)])
  ```

### SermonIndex: some authors' texts are modernised rewrites

SermonIndex serves the printed text for some speakers (M'Cheyne, Simpson) and
gracegems-style modernisations for others. Its Samuel Davies and Octavius
Winslow pages score ~0 on the archaism density below, and Davies's *Sinners
Entreated* opens on the NIV ("We are therefore Christ's ambassadors"), a
copyrighted translation the preacher never used. Screen every SermonIndex
speaker with the same density check before trusting it. Its Bonar pages are
mostly short devotional excerpts (≤1,200 words). M'Cheyne lives at
`/speakers/robert-murray-mcheyne/…`; the `m%27cheyne` URLs only redirect.
SermonIndex also drops the sermon's Bible text, so set `scripture_ref` in the
catalog.

### CCEL Spurgeon: take the printed text, not the modernised one

CCEL's 63 Spurgeon volumes (`sermons01`…`sermons63`, ~3,540 sermons; each has a
`sermonsNN.toc.html`) are **two transcriptions**. The early New Park Street
volumes (1855–~1861) and a scattering of later sermons are the Pulpit as
printed, quoting the Authorised Version. Most sermons from ~1862 on are a later
digital text that **silently modernised his Scripture** ("all you that labor"
for "all ye that labour") and also **splits paragraphs mid-sentence at page
breaks** ("It is not al- / ways so"). Screen every candidate by KJV-archaism
density before importing (method from `build_spirit_anthology`):

```python
import re
ARCH = r"\b(thee|thou|thy|thine|ye|hath|unto|doth|art|shalt|wilt)\b"
def density(text):
    w = len(text.split()) or 1
    return (round(len(re.findall(ARCH, text, re.I)) * 1e4 / w),   # printed: ~90–400
            round(len(re.findall(r"\b\w+eth\b", text)) * 1e4 / w))  # printed: mostly 8+
```

Printed texts run ~90–400 archaisms per 10k words; the modernised ones under
~50 with ~0 `-eth` verbs, and their epigraph reads "you"/"has". Run
`extract(fetch(url))` from `import_sermons` over candidates in a Django shell to
get density, word count, ref and date for a whole shortlist before committing
to any. (Batch 2 had to swap out 9 of 16 first picks for this.)

## 2. Import

Scratch SQLite DB (no Postgres needed):

```bash
cd backend && uv sync && export DJANGO_DEBUG=true
uv run python manage.py migrate -v0
```

The importer creates a missing author from `SERMON_AUTHORS`, which only lists
three, so load the real author rows into the scratch DB first:

```python
import json
from library.models import Author
for r in json.load(open('library/fixtures/content/authors.json')):
    f = r['fields']
    Author.objects.get_or_create(slug=f['slug'], defaults={'name': f['name'], 'bio': f.get('bio', '')})
```

Add `SermonEntry` rows at the END of `SERMONS` (`sort_order` is the list index)
with a comment saying what the batch is and what was left out, then:

```bash
uv run python manage.py import_sermons <slug> <slug> …
```

The importer fetches, strips the masthead, keeps the epigraph as a blockquote,
parses ref + date (CCEL), drops trailing order-of-service notes ("PORTION OF
SCRIPTURE READ BEFORE SERMON…", an exposition, "HYMNS FROM 'OUR OWN HYMN
BOOK'…" — `extract(…, strip_service_notes=True)`; the anthology builders call
`extract` without it and keep the reading line), applies `BODY_CORRECTIONS`,
and prints `audit_english` findings per sermon. Two sermons shipped before the
strip (`consolation-in-the-furnace`, `order-and-argument-in-prayer`) still end
on their reading line.

Write the fixture files from the scratch DB — natural keys, the one byte-stable
writer, and keep any summary/questions already in an existing file:

```python
# uv run python manage.py shell -v0 < write_fixtures.py
import json
from django.core import serializers
from library.models import Sermon
from library.content_fixtures import render_rows, sermon_fixture_path
for s in Sermon.objects.all():
    rows = json.loads(serializers.serialize("json", [s], use_natural_primary_keys=True, use_natural_foreign_keys=True))
    for r in rows:
        r.pop("pk", None); r["fields"].pop("search_vector", None)
    p = sermon_fixture_path(s.slug, "en")
    if p.exists():
        old = json.loads(p.read_text())[0]["fields"]
        for k in ("summary", "study_questions", "created_at"):
            if old.get(k): rows[0]["fields"][k] = old[k]
    p.write_text(render_rows(rows))
```

## 3. Repair the English ([[english-qa]])

The audit only sees some defect classes. Run all four passes:

1. `uv run python manage.py audit_english <slugs> --examples 0` — usually
   `orphan-close-quote` (a dropped opening mark: find the quotation's real
   start, often the KJV verse) and `space-before-punct`. The excerpt shows the
   FIRST `”` in the block, not necessarily the orphan — count marks per block.
2. **Rare words**: every token in the new sermons that appears nowhere else in
   the English corpus. This is what finds OCR slips: `whieh`, `sincereIy`,
   `backs1ider`, `righteousuess`, `theLord`, `secood`.
3. **Fusions**: tokens absent from the corpus that split into two common words
   (`willgiveyou`, `ofjudging`, `ownliving`).
4. **Ends and starts**: print the first and last ~300 characters of each body —
   trailers, publisher notices ("…the only authorized edition"), letters from
   Mentone and bracketed notes all sit there.

Repairs go in `BODY_CORRECTIONS` as `(old, new)` pairs (one block per batch at
the end of `corrections.py`, a `{slug: [pairs]}` dict looped into
`BODY_CORRECTIONS`). When you add a second round to that dict, merge it into the
existing slug's list: a repeated key silently drops the first list (ruff
`F601` catches it). Each pair must be **unique in the body and idempotent** — the
new text must not contain the old. Match the stored HTML, not the plain text:
`he feel himself <i>utterly` needed its tag. Re-import, rewrite the fixtures,
and confirm every pair applied (`old not in body and new in body`) and
`settled_sermon_body(slug, body) == body`. Fix only what is unambiguous; period
spellings ("bemean", "to-morrow", "Saviour") stay, and so does the preacher's
own slip (Spurgeon names Elijah's servant "Gehazi") — the text is his. A slip
whose intended word isn't certain ("and shell on the strength of that promise")
is left too, rather than guessed.

Have the question-writers (step 4) also report OCR slips, demeaning passages
and occasion-bound endings: reading every word, they find what the scans
miss. The middle-tier batch took ~45 slips from them, and two Moody sermons were dropped on
their reports (*The Blood*: the Jews' "honour of killing the Christian's God";
*Results of True Repentance*: a quoted illustration making Black skin the
picture of sin).

## 4. Summary + study questions ([[sermon-questions]])

Per sermon: a 2–3 sentence `summary` (~50–80 words, present tense, ends where
the sermon lands) and exactly four grounded `study_questions`. Reading
~90,000 words of Spurgeon is the bulk of a batch, so fan it out: dump each
body to its own text file and give helper agents 3–4 sermons each, with the
house-style example from an existing fixture and the rule that every quoted
phrase is copied verbatim. Then verify mechanically that every `"…"` span in
each answer occurs in its sermon's text, and read the output yourself. Agents
also turn up OCR slips while reading — fold those into step 3 and adjust any
quote that carried the slip.

Insert the two fields into the fixture rows (they sit after `summary`'s slot,
which the serializer order already provides) and rewrite with `render_rows`.

## 5. Topics

Append each slug to one or two lists in `TOPIC_SERMONS` (`topic_seed.py`):
`prayer`, `grace-and-comfort`, `faith-and-guidance`, `the-gospel-call`,
`christ-and-the-cross`, `deeper-life`, `holy-spirit`, …

## 6. Share cards ([[og-cards]])

```bash
cd frontend && npm ci && npm run og:sermons
git status --short static/og        # expect 1 new PNG per sermon + the manifest
```

**The run may rewrite every existing PNG** — in a cloud container the encoder
did not reproduce the committed bytes (333 cards "changed", none visibly). The
manifest's digests are of the INPUTS, so keep only the new PNGs and the
manifest: `git diff --name-only -- static/og | grep '\.png$' | xargs git checkout --`.
If you drop a sermon after drawing its card, delete its PNG and re-run the
generator (then the same revert) so its manifest line goes too.

## 7. Verify and ship

```bash
cd backend
uv run python manage.py test library.tests_fixture library.tests_sanitize \
  library.tests_sermon_payload library.tests_english_audit library.tests_import
uv run ruff check library/
cd ../frontend && npx vitest run src/lib/sermonCards.test.ts
```

A new sermon with audit findings left standing needs its baseline pinned
(`audit_english --update-baseline`, whole corpus); a clean batch leaves the
baseline alone. The PR body names the picks, what was screened out and why,
and the repairs. Run `/simplify` and `/code-review` if the importer changed.

## Ledger

- 2026-10-28 — Spurgeon batch 2: 13 sermons from the printed 1855–1871 text
  (18 → 31). Added the trailer strip to `import_sermons.extract`.
- 2026-10-29 — Middle tier batch 1: M'Cheyne ×3 (SermonIndex), Ryle ×3 (CCEL
  *The Upper Room*), Maclaren ×4 (CCEL *Expositions*), Moody ×2 (PG 33015).
  264 → 276.
