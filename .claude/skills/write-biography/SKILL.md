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
4. **Regenerate the fixture and commit:**
   ```bash
   uv run python scripts/regen_fixture.py   # pinned 6-model natural-key regen; NEVER bare `dumpdata library`
   ```
5. **If the author ALREADY EXISTS on prod, the fixture is not enough** — prod is
   never re-seeded, and `seed_books` only CREATES missing rows, so a fixture-only
   bio silently reaches fresh installs and never the live site. Add a data
   migration that re-applies the fixture to live rows (it syncs `bio_html`,
   `bio`, and `photo_url`):
   ```python
   def backfill(apps, schema_editor):
       from library.content_sync import backfill_bios_and_sermons
       backfill_bios_and_sermons(apps)   # idempotent
   ```
   Copy `0017_backfill_moody_bio.py` / `0036_classic_author_bios_and_portraits.py`.
   Only a brand-new author arriving with its own books can skip this (seed_books
   creates it from the fixture, bio and all).

## The portrait (optional, same page)

Without `photo_url` the page falls back to an initials monogram (which looks
fine — a portrait is not mandatory, and some Puritans have no known likeness).
House format: **grayscale JPEG, max 600px, `frontend/static/portraits/<slug>.jpg`,
`photo_url="/portraits/<slug>.jpg"`.**

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

_This is a living playbook — append tips and pitfalls as we write more._
