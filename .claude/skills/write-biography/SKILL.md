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
   `bio_html` — and rewrite the file in the regen script's exact format so the
   diff stays one line per author:
   ```python
   rows = json.load(open(PATH));  # ... set fields ...
   out = "[\n" + ",\n".join(json.dumps(r, indent=1, ensure_ascii=False) for r in rows) + "\n]\n"
   ```
   Then verify with a scratch-DB loaddata (migrate + loaddata all ordered
   fixtures into a temp sqlite; assert the new lengths). Running the regen
   script afterwards is ideal when it works — but it aborts on any
   pre-existing field drift (new model fields not yet in DEFAULTED_OK), which
   is NOT your change's fault; the loaddata check is the gate that matters.
   NEVER bare `dumpdata library`.
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

7. **APPEND new rows to `authors.json` — never re-sort it.** The file is in
   creation order, not slug order; sorting turns a 45-line addition into a
   282-insert/237-delete diff. Append, then write with the regen renderer's
   exact format (records at column 0, `indent=1`, trailing newline).

## The portrait (optional, same page)

**Check first — the portrait may already exist.** Several authors carry a
`photo_url` and a file under `frontend/static/portraits/` even with an empty
`bio_html` (Torrey did). `ls frontend/static/portraits/ | grep <slug>` and curl
the live URL before doing any image work.

Without `photo_url` the page falls back to an initials monogram (which looks
fine — a portrait is not mandatory, and some Puritans have no known likeness).
House format: **grayscale JPEG, max 600px, `frontend/static/portraits/<slug>.jpg`,
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
7. Fixture regenerated.

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

_This is a living playbook — append tips and pitfalls as we write more._
