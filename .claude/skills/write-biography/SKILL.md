---
name: write-biography
description: Write a long-form biography of an Ochorus author (a preacher, missionary, or writer) and publish it to their author page. Use when adding or improving an author's biography. Each bio is 1500+ words, in a warm devotional tone, with the person's real quotes called out as pull-quotes and their key times of prayer and answers to prayer highlighted as callouts. The bio renders above the author's books and sermons.
---

# Writing an Ochorus biography

An author page (`/authors/<slug>`) shows, in order: the **biography**, then their
**books**, then their **sermons**. This skill covers writing the biography — the
long-form `Author.bio_html` field. The short `Author.bio` (a few sentences) stays
as the card/SEO summary; don't remove it.

Everything below assumes `~/dev/ochorus/backend`, Django via `uv run` with
`DJANGO_DEBUG=true` (local SQLite, no services).

## What a good bio is

- **1500 words or more.** A real narrative, not an encyclopedia stub.
- **A devotional arc**, roughly: early life → conversion / call → ministry and
  its fruit → trials and how faith met them → death and legacy. Let the shape
  follow the life; not every person fits the template.
- **Warm, reverent, readable** — the "Quiet Devotional" voice (see STYLE_GUIDE).
  Honour the person; don't hagiographize. Name real struggles (Spurgeon's
  depression, a missionary's failures) — they make the faith credible.
- **Accurate.** These are real people. Every fact and date should be verifiable.
- **A portrait where an honest one exists.** Try to ship the bio with a real
  public-domain likeness of the person, not just the initials monogram — see
  **The portrait** below.

## Research first — real quotes, real prayers, no invention

**Never fabricate a quote, a fact, a date, or a prayer story.** Devotional
readers trust this. Before writing:

1. **Search** for the person's life, conversion, ministry, and death. Use
   `WebSearch` / `WebFetch`. Prefer reputable sources (biographies, CCEL,
   Spurgeon Center, Banner of Truth, primary letters/autobiography).
2. **Collect real quotes** — the person's *own words*, verbatim, with attribution
   you can stand behind. Aim for 2–4 strong ones to call out. If a famous line's
   attribution is disputed (many viral "Spurgeon" quotes are spurious), **verify
   or drop it**. When in doubt, leave it out.
3. **Find the prayer moments** — this is a required ingredient. Look specifically
   for (a) **key times of prayer** (a habit, a vigil, a wrestling) and (b)
   **answers to prayer** (a provision, a healing, a conversion, a deliverance).
   Most of these lives are rich with them. Capture the real account, with enough
   detail to ring true.

If you genuinely can't verify enough for 1500 accurate words, tell the user what
you found and what's thin — don't pad with invention.

## The markup (what goes in `bio_html`)

Cleaned HTML, no inline styles — the author page styles these classes. Allowed
tags: `<p>`, `<h2>`, `<blockquote>`, `<cite>`, `<aside>`, `<em>`, `<strong>`,
`<a>`.

- **Paragraphs**: `<p>…</p>`.
- **Section headings** (optional, for a long life): `<h2>…</h2>`.
- **Pull-quote** — the person's own words, called out large and set apart:
  ```html
  <blockquote><p>I have learned to kiss the wave that throws me against the Rock of Ages.</p><cite>— Charles Spurgeon</cite></blockquote>
  ```
  Use 2–4 across the bio. Only for *their* words (or a contemporary about them);
  keep them short and quotable.
- **Prayer callout** — a key time of prayer, highlighted in gold:
  ```html
  <aside class="prayer"><p>Before every sermon he descended to the basement where hundreds knelt in prayer, calling it the church's "boiler room."</p></aside>
  ```
- **Answer-to-prayer callout** — add `answered` for an indigo "Answer to prayer"
  label:
  ```html
  <aside class="prayer answered"><p>They prayed through the night for the orphanage's rent; by morning an unsolicited gift met it to the penny.</p></aside>
  ```

Include **at least one** prayer callout and, where the record supports it, **at
least one answer-to-prayer** callout. Don't overuse them — 2–4 total; they lose
force if every paragraph is a box.

## Publishing the bio

1. Write the HTML to a file, e.g. `/tmp/<slug>-bio.html` (one line or pretty —
   whitespace between tags is fine).
2. Set it on the author and add the short summary if missing:
   ```bash
   cd backend
   DJANGO_DEBUG=true uv run python manage.py shell -c "
   from library.models import Author
   a = Author.objects.get(slug='SLUG')
   a.bio_html = open('/tmp/SLUG-bio.html').read()
   # a.bio = 'One-sentence summary for cards + SEO.'  # set if empty
   a.save()
   print('saved', len(a.bio_html), 'chars')"
   ```
3. **Verify it renders**: run the app and open `/authors/SLUG` in light and dark —
   check the pull-quotes and prayer callouts look right and the prose reads well.
4. **Get the prose into the FIXTURE — the dev-DB write above does NOT carry.**
   `scripts/regen_fixture.py` regenerates from the COMMITTED fixture files via
   a scratch DB (loaddata → dumpdata round-trip); it never reads your dev DB.
   So edit `library/fixtures/content/authors.json` directly — set the row's
   `bio_html` — and rewrite the file in the format it is COMMITTED in, so the
   diff is only the lines you touched:
   ```python
   rows = json.load(open(PATH));  # ... set fields ...
   out = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
   ```
   That round-trip reproduces the committed file byte-for-byte. **The regen
   script's `render()` disagrees with what is on disk** — it writes records at
   column 0 with `indent=1`, which is ~2.7KB smaller and reformats every line.
   `authors.json` is the ODD ONE OUT: the `books/`, `sermons/` and `plans.json`
   fixtures really are in `render()` format, so don't carry `indent=2` over to
   them (see the book-import skill, which is correct for those).
   Do not follow its format, and do not run the regen script to save your edit:
   it would reformat the whole file and bury a 75-line addition in a full-file
   diff (this cost time on PR #1134).
   Verify with a scratch-DB loaddata (migrate + loaddata all ordered fixtures
   into a temp sqlite; assert the new lengths) — that is the gate that matters.
   Don't reach for the regen script as the check: it rewrites the files it
   reads, and it aborts on any pre-existing field drift (new model fields not
   yet in DEFAULTED_OK) that is NOT your change's fault. Full regens are a
   separate, deliberate job. NEVER bare `dumpdata library`.

   **Store the SETTLED (sanitized) `bio_html`, not your raw HTML.** The fixture
   loads via `loaddata`, which BYPASSES the model's sanitize step, and
   `tests_sanitize.py` fails on any stored row where `clean_bio_html(row) != row`.
   The trap is whitespace: `clean_bio_html` collapses the `\n\n` you put between
   block tags down to a single space, so a pretty-printed bio is "unsettled" and
   reddens the build. Run each bio through the sanitizer once and commit THAT:
   ```python
   from library.sanitize import clean_bio_html
   settled = clean_bio_html(raw_html)          # idempotent: clean(settled)==settled
   # set fields[...]["bio_html"] = settled, then dump the file (step above)
   ```
   Same trap, same fix, for a translated bio's `.html` file under
   `library/migrations/data/author_bios_<lang>/`.
5. **If the author ALREADY EXISTS on prod:** the short `bio` now ships from the
   fixture on its own; `bio_html` and `photo_url` still don't.

   Since 2026-07-26 every deploy runs `author_sync.sync_all_authors` (from
   `seed_books` / `seed_sermons`) over EVERY author in `authors.json`, including
   the biography-only ones. It replaces a `bio` that is empty **or still a
   verbatim `catalog.py` stub** — so writing the real short bio into the fixture
   is now enough, and 0049/0051-style short-bio migrations are obsolete. It will
   NOT touch a bio that is anything else: reviewed prose, a hand edit and a
   translated-then-approved value all win.

   `bio_html` and `photo_url` are **fill-only** — they move `""` to the fixture's
   value and never overwrite. REPLACING either on a live row still needs a
   migration (step below). Two more traps that still hold:
   - `seed_if_empty` only fills an EMPTY database;
   - **`content_sync.backfill_bios_and_sermons` is RETIRED** — it detects the
     natural-key fixture and no-ops by design (the old 0017/0036 migrations
     predate the format switch). Do NOT copy those; a migration calling it is a
     silent no-op and the bio never reaches the live site.

   **The author PAGE lags by one deploy.** `/authors/<slug>` is prerendered and
   bakes the bio at BUILD time from the live API, so the deploy that performs
   the sync still serves the old text. Redeploy `ochorus-web` afterwards
   (Manual Deploy → "Clear cache & deploy latest commit").

   **Replacing an English bio flags its translations stale.** Every
   `AuthorTranslation` of that author's short bio gets `source_stale=True`, the
   deploy log names the languages (`~ author x (bio — es/sw translation(s) now
   stale)`), and the count surfaces on the founder dashboard. Nothing
   re-translates on its own — the wording is untouched and `translate_author`
   still needs `--force` — so treat that log line as a to-do.

   **Never signal this by clearing `reviewed`.** That field also tells
   `seed_author_translations` "an approver owns this wording, don't overwrite
   it", and it runs LATER in the same release (`seed_books` → `seed_sermons` →
   `seed_author_translations`). Clearing it drops the protection, so the same
   deploy replaces the native reviewer's text with the repo's AI translation —
   silently. That bug was written, measured doing exactly this, and replaced
   with the separate `source_stale` flag; the two facts are independent.

   To REPLACE non-empty `bio_html`/`photo_url`, write a data migration that
   reads `content/authors.json` and updates the row, with fill-only or
   anchored semantics so it can't clobber later prose. Model:
   `0051_torrey_biography.py` —
   ```python
   Author.objects.filter(slug=SLUG, bio_html="").update(bio_html=bio_html)
   # replacing NON-empty prose: anchor on the exact previous text, so a hand
   # edit or a later deploy's wording always wins
   Author.objects.filter(slug=SLUG, bio=PREVIOUS_TEXT).update(bio=bio)
   ```
   Verify all four paths before shipping: fresh-DB seed, prod-shaped row,
   idempotent re-run, and a hand-edited value surviving the migration.

   Only a brand-new author arriving with its own books can skip this (seed_books
   creates it from the fixture, bio and all).

   Also fixed 2026-07-26: a `catalog.py` author slug that `authors.json` doesn't
   have used to fork the author on re-import (`charles-spurgeon` vs
   `charles-h-spurgeon`). CI now fails on any such mismatch — take an author's
   slug FROM `authors.json`.

6. **A brand-new author with NO books needs its own create-migration.**
   `seed_books`/`seed_sermons` create authors only as a side effect of
   importing a work, so a biography-only author never reaches prod from the
   fixture alone. Pattern (`0053_three_new_biography_authors.py`, updating
   `0026_add_biography_authors` for the split-fixture layout): read
   `fixtures/content/authors.json`, `get_or_create` each new slug, and **guard
   on `if not Book.objects.exists(): return`** — on a fresh install
   `seed_if_empty` runs right after migrate and its loaddata would collide by
   slug with rows created here. Verify three paths: fresh install, prod-shaped
   create, idempotent re-run.

   **Take the next migration number from `origin/main`, not from your local
   directory.** `ls library/migrations/` shows what YOUR branch has; two
   branches cut from the same commit both see the same tail and both pick the
   same integer, and Django then has two leaf nodes and refuses to run. Fetch
   first and number against the remote:
   ```bash
   git fetch origin main
   git ls-tree --name-only origin/main backend/library/migrations/ | tail -3
   ```
   If a collision has already landed on main, do NOT renumber someone else's
   migration. Renumber YOURS to sit after theirs and point `dependencies` at
   the current leaf — a merge migration if main made one. Then prove the graph
   is linear again before you push:
   ```bash
   DJANGO_DEBUG=true uv run python manage.py makemigrations --check --dry-run
   DJANGO_DEBUG=true uv run python manage.py showmigrations library | tail -4
   ```

7. **APPEND new rows to `authors.json` — never re-sort it.** The file is in
   creation order, not slug order; sorting turns a 45-line addition into a
   282-insert/237-delete diff. Append, then write in the committed file's
   format (`indent=2`, `ensure_ascii=False`, trailing newline — step 4).

   **Expect that append to conflict.** Because the rule is "always append",
   every concurrent session writes to the same last line, so two biography PRs
   in flight at once collide by construction. Resolve by keeping EVERY new row
   — take the three-way stages and diff each side against the base rather than
   picking a side, since "ours" and "theirs" each hold a row the other lacks:
   ```python
   g = lambda st: json.loads(subprocess.run(
       ['git','show',f':{st}:'+PATH], capture_output=True, text=True).stdout)
   base, ours, theirs = g(1), g(2), g(3)
   bslugs = {r['fields']['slug'] for r in base}
   new_theirs = [r for r in theirs if r['fields']['slug'] not in bslugs]
   new_ours   = [r for r in ours   if r['fields']['slug'] not in bslugs]
   merged = base + new_theirs + new_ours     # main's row first: creation order
   assert len({r['fields']['slug'] for r in merged}) == len(merged)
   ```
   Main's rows go first, because the file is in creation order and theirs
   landed first. Then re-dump in the committed format (step 4).

## The portrait (try for one, same page)

**Every new bio should try to ship with a portrait.** A face makes the page,
and most Ochorus authors — preachers, missionaries, reformers — have a
well-known, plainly public-domain likeness (Cranach's Luther, the classic
Calvin engraving, a Victorian studio photograph). So treat sourcing a good
portrait as a normal part of creating the bio, not an afterthought — go looking
for one every time. The monogram below is the honest fallback for when there
genuinely isn't one, not the default.

**Check first — the portrait may already exist.** Several authors carry a
`photo_url` and a file under `frontend/static/portraits/` even with an empty
`bio_html` (Torrey did). `ls frontend/static/portraits/ | grep <slug>` and curl
the live URL before doing any image work.

Without `photo_url` the page falls back to an initials monogram (which looks
fine — some Puritans have no known likeness, and a spurious face is worse than
initials). But don't settle for it while an honest portrait is gettable. House
format: **grayscale JPEG, max 600px, `frontend/static/portraits/<slug>.jpg`,
`photo_url="/portraits/<slug>.jpg"`.**

**Some subjects have no honest portrait.** William Law never permitted one to be
taken in life, so every later engraving is an imagined likeness — and Commons'
lead image for him is CC BY 4.0, not PD. When the only candidates are imagined
or non-PD, **ship the monogram** and say why in the bio; a spurious face is
worse than initials. (Checking the licence caught this: two of three portraits
in that batch were PD, the third was not.)

Source pre-1900 figures from Wikimedia Commons and **verify the licence** — never
assume. Find the lead portrait via the Wikipedia `pageimages` API, then check
`extmetadata.LicenseShortName == "Public domain"` via the Commons `imageinfo`
API before using it. Convert with PIL (`magick`/`convert` are NOT installed):

```python
im = Image.open(io.BytesIO(raw)).convert("L")   # "L" = the house B&W look
im.thumbnail((600, 600), Image.LANCZOS)
im.save(f"frontend/static/portraits/{slug}.jpg", "JPEG", quality=85, optimize=True)
```
Check the result visually (a contact sheet of several at once is quickest) — the
API's lead image is occasionally a statue, a book cover, or the wrong person.
Ship `photo_url` the same way as `bio_html` (step 5 above).

**A CC "own work" claim on a lifetime photo is copyfraud — reject it.** For a
20th-century subject (the era where PD runs out), Commons' only image is often a
real press/studio photograph from the person's life that a recent uploader
re-posted as "own work" under CC BY(-SA). The tell is
`extmetadata.DateTimeOriginal`: a file created *after* the subject died (Festo
Kivengere d. 1988, image dated 2016) cannot be the uploader's own work, so the
licence doesn't hold — and it isn't PD anyway, and the portrait system carries no
attribution field to satisfy CC BY. Treat it exactly like William Law: ship the
monogram. The honest route to a real face for these is a rights grant from the
holder (a ministry, estate, or archive), which is the founder's call to pursue,
not something to fake with a mislicensed upload. (Kivengere / Nsibambi both
stayed monograms this way — Nsibambi has no free image at all.)

**If the environment can't reach the image (blocked egress, no Commons access),
that is not "no portrait exists" — it's "couldn't fetch it here."** Don't
silently ship a monogram for someone with an obvious public-domain likeness.
Say so in the PR ("portrait deferred — Commons was unreachable in this session;
`<slug>` has a clear PD portrait to add") so it gets picked up, rather than
leaving a famous face as initials by accident. (Calvin and Luther shipped as
monograms this way on PRs #1276 / #1277.)

**Then give the file a focal point — this is a CI gate.**
`frontend/src/lib/portraits.ts` holds a `PORTRAIT_POSITION` table, and
`frontend/src/lib/portraits.test.ts` fails the build **both ways**: a file in
`frontend/static/portraits/` with no entry, or an entry with no file. A portrait
added without an entry is a red build (it happened on PR #1134). Add
`'<slug>': '50% N%',` in slug order, deriving `N` with the formula documented in
the table's header comment — for a source of aspect `a` (width ÷ height) with
the face centred at `fy` (a fraction of image height):

    y = (fy − 0.45·a) ÷ (1 − a)      clamped to 0–100

Measure `a` and `fy` off the file you just saved, not off the Commons original.
Tall plates with a high head clamp to `50% 0%`; a square source crops nothing, so
its value is inert — list it anyway to keep the table a complete inventory.

## Adding sermons (optional, same page)

Sermons render under the books. A sermon is a standalone piece — see the
`Sermon` model (`author`, `slug`, `language`, `title`, `scripture_ref`,
`preached_on`, `body_html`, `word_count`). Create one from cleaned public-domain
text (CCEL / Spurgeon Center / Gutenberg):
```bash
DJANGO_DEBUG=true uv run python manage.py shell -c "
from library.models import Author, Sermon
from library.ingest import clean_fragment, word_count   # reuse book cleaning
a = Author.objects.get(slug='SLUG')
body = clean_fragment(open('/tmp/sermon.html').read())
Sermon.objects.update_or_create(slug='sermon-slug', language='en', defaults=dict(
    author=a, title='TITLE', scripture_ref='John 3:16',
    body_html=body, word_count=word_count(body)))"
```
(`clean_fragment` cleans an HTML string; `word_count` counts it. Confirm the
current signatures in `library/ingest.py` before relying on them.)

## Quality checklist (before commit)

1. **≥ 1500 words** of real, accurate biography.
2. **2–4 real, verified quotes** called out as `<blockquote>` with a `<cite>`.
3. **≥ 1 prayer callout**, and an **answer-to-prayer** callout where the record
   supports one.
4. Facts, dates, and attributions **verifiable** — no invention, no spurious
   "quotes."
5. Only the allowed tags; no inline styles; valid, clean HTML.
6. Reads well and looks good in **both themes**; the short `bio` summary is set.
7. `authors.json` edited in place, in the committed format (step 4) — not
   regenerated.
8. **Tried for a portrait**: shipped a verified public-domain likeness, or — if
   none is honest/gettable — said so (and why) rather than defaulting to the
   monogram. Any new portrait has a `PORTRAIT_POSITION` entry
   (`portraits.test.ts`).

## Removing a bio, or withholding an author from the Biographies shelf

Withdrawing an author's biography (owner's request, etc.) has TWO independent
levers — know which the ask needs, because clearing the bio alone rarely does
what people mean by "remove them from biographies":

- **The bio text.** Clear `Author.bio` (and `bio_html`) in `authors.json`, and
  delete the `<slug>.short.txt` / `<slug>.html` files under
  `migrations/data/author_bios_<lang>/`. But the seeds only ever FILL, never
  blank (`author_sync.sync_author` skips an empty fixture bio;
  `seed_author_translations` leaves a stored value alone for a missing file), so
  the fixture/file edits reach only a FRESH DB. A **data migration** must clear
  the live `bio`/`bio_html` and `delete()` the author's `AuthorTranslation`
  rows on the existing prod DB. Both channels are mandatory — see PR #1389 and
  migration `0105`, and the general two-channel rule in `backend/CLAUDE.md`.
- **The Biographies shelf card.** `AuthorListView` lists anyone with **a bio OR
  a book/sermon** (so a writer with no bio yet isn't invisible), so clearing the
  bio does NOT remove the card of an author who has a work — it just loses its
  blurb. To take a real person off the shelf while keeping their work, set
  `Author.list_in_biographies = False` (default True; the person-level analogue
  of `is_imprint`, added in PR #1389 / migration `0106`). **Do NOT use
  `is_imprint` for this** — it asserts the byline is not a person and strips
  their schema.org `Person` markup and `same_as`. Ship it like `is_imprint`:
  field + migration flag + fixture flag + `seed_books` create-default + test.

Keeping the book means her author page stays reachable and prerendered (the
`entries` generator unions authors from `listBooks`), and it correctly drops out
of the Biographies *sitemap* section — the same accepted state as a book-subject
author like `simeon-nsibambi`. `prerenderCoverage.test.ts` only forbids
advertised-but-unbuilt, so built-but-unadvertised is fine.

## Pitfalls found in practice (2026-07-24, PR #387)

- **Use literal Unicode, never named HTML entities.** The author-page hero
  epigraph extracts the first `<blockquote>` as PLAIN TEXT, so `&lsquo;` /
  `&mdash;` / `&hellip;` in `bio_html` render RAW on the page ("&lsquo;stepping
  stones&rsquo;"). Write ’ — … £ é directly (the fixture is UTF-8 JSON). Keep
  only `&amp;` `&lt;` `&gt;`.
- **Replacing a NON-empty bio in a migration: anchor on the md5** of the exact
  previous `bio_html` (captured from the committed fixture) instead of pasting
  ~10KB of old prose into the migration. Update only when
  `md5(row.bio_html) == anchor` or the row is empty — a hand edit or newer
  deploy always wins; re-runs are no-ops. See `0052_site_bio_expansions.py`.
- **Sourcing from ochorus.com: bios live at `/biographies/<slug>/`**, NOT
  `/authors/<slug>/` (those are book-listing stubs; some even redirect to a
  portrait PNG — curl gives you image bytes). A few slugs differ from the
  app's (`amy-beatrice-carmichael`, `charles-spurgeon`,
  `reuben-archer-torrey`, `aurelius-augustinus`).
- **Verify site facts before adopting.** ochorus.com bios contain real errors
  (wrong parent names, date conflations); adjudicate contradictions against
  external sources and document per-author which claims were rejected.
- **Two biography PRs in flight collide TWICE, and both collisions are
  structural.** On 2026-09-02 three sessions added biography-only authors at
  once: Martin Luther (#1277), John Calvin (#1276) and Erica Sabiti (#1278).
  Luther and Calvin both took `0098` against the same `0097` parent, so main
  ended up resolving itself with `0099_merge_calvin_luther_biography_authors`
  — which then collided with #1278's own `0099`, forcing a second resolution
  to `0100`. `authors.json` conflicted in both rounds at the append point. The
  first PR merged silently; the second was `mergeable_state: dirty` for
  half an hour before anyone looked, and CI does not run on a conflicted PR, so
  the symptom was "no checks have started" rather than a conflict warning. If
  your PR shows no check runs, check mergeability before assuming a slow queue.

- **"I could not verify it" is a statement about your search, not about the
  world — write it down as such.** Four claims about Simeon Nsibambi (his
  father Walusimbi Kimanje, a chief; Mengo and Budo; the African Native
  Medical Corps and his decoration; that he buried his brother Blasio Kigozi)
  were recorded in `docs/verification/` as unverifiable, and two whole books
  were then written around the gap. All four are attested — the first research
  pass simply had not surfaced Christian History Institute's account. Worse,
  one draft correctly asserted the burial, and it was REMOVED as unverified
  and the removal reported as a defect caught. The removal was the defect.
  Two habits prevent this: search on the specific claim (`"<name>" "<school>"`,
  `"<name>" buried`) rather than only on the person, and record findings as
  "not found by these searches" rather than "not true".

- **Some of the best sources are egress-blocked.** `dacb.org` (Dictionary of
  African Christian Biography) and `en.wikipedia.org` both refuse `WebFetch`
  here. `WebSearch` still returns summaries of their content, which is how the
  Sabiti and Nsibambi material was recovered — so a blocked fetch is not a dead
  end, but it does mean you are working from summaries. Say so in the
  verification file rather than implying you read the source.


## Writing a BATCH at once (parallel subagents) — 2026-09-03, PR #1380

Seven East African Revival bios (Joe Church, Kinuka, Kigozi, Nagenda,
Kanamuzeyi, Luwum, Barham) were written in one pass this way, and it held
quality:

1. **One research subagent per figure, in parallel.** Brief each to return a
   structured dossier — life facts with dates+sources, 2–4 vouched verbatim
   quotes, the prayer moments, and an explicit **THIN/UNVERIFIABLE** section —
   under a hard "never fabricate; say 'not found by these searches'" rule.
   Expect `en.wikipedia.org` and `dacb.org` to REFUSE WebFetch; WebSearch
   summaries of them still come back, so a blocked fetch is not a dead end — but
   say you're working from summaries.
2. **Stage shared inputs as FILES**, not giant prompts: one `SPEC.md` (voice +
   the allowed-tags markup + the literal-Unicode-not-entities trap + the
   no-invention rule), the full text of an existing bio as the **voice template**
   (Sabiti's is a good one — same milieu), and one `dossier-<slug>.md` per figure.
3. **One writer subagent per figure, in parallel**, each told to read
   SPEC + template + its dossier and write `bio-<slug>.html`, then print
   `SHORT_BIO / BIRTH_YEAR / DEATH_YEAR`. Leave a year **NULL** when the dossier
   couldn't verify it — don't guess (Kanamuzeyi's birth and both of Barham's
   years shipped blank).
4. **Review every draft against its dossier yourself** — this is not optional;
   the subagents are disciplined but you own the accuracy. A fast mechanical
   scan catches the rest: `grep` the drafts for stray HTML entities (only
   `&amp;` allowed), for any year/word you told them to omit, and for
   disallowed tags.
5. **Assemble with a Django-aware script** (`django.setup()` after
   `sys.path.insert(0, os.getcwd())` from `backend/`): run each bio through
   `clean_bio_html` to store the SETTLED form, append the rows, dump
   `indent=2, ensure_ascii=False`. One create-migration covers the whole batch
   (a `NEW_SLUGS` set, mirroring `0100_erica_sabiti`). Verify BOTH create paths
   (fresh `seed_if_empty`; migration on a seeded DB with the rows deleted).

Cost: ~7 research + 7 writer agents. The `same_as` decision is per-figure — the
well-documented ones (Church, Luwum, Kanamuzeyi) got a verified Wikipedia URL;
the four with no confirmed standalone entity were registered blank in
`tests_author_entity` rather than given a guessed identifier. Portraits: a whole
20th-century batch is monograms — lifetime photos are copyfraud-risk, so none
shipped a face.

_This is a living playbook — append tips and pitfalls as we write more._
