---
name: book-export
description: Make one Ochorus book edition downloadable as a free PDF and EPUB — add it to the export pilot, point its pdf_url at the book-pdfs bucket, bundle its cover, preview the front matter (cover, title page, About Ochorus, About the Author, contents) locally, ship, and verify both downloads live once book-pdfs.yml has built and uploaded the PDF. Use when asked to make a book downloadable, create/regenerate a book's PDF or ePub, widen the download pilot, or when a download looks wrong (missing cover, missing bio page, stale text). This is a living playbook — append new failure modes as we find them.
---

# Book export (PDF + EPUB)

One edition = one `(slug, language)`. Both formats are built from the same parts
in `backend/library/book_export.py`, in this order:

1. **Cover** — the cover *as the site shows it* (`cover_image_url`): a designed
   cover is its own image; a painting/plate is wordless, so its og twin
   (`/covers/<slug>.png`, `/covers/<lang>/<slug>.png`) is used.
2. **Title page**
3. **About Ochorus** — `STRINGS[lang]["ochorus_html"]`
4. **About the Author** — the edition's export bio (see Pre-flight), life
   dates, and a link to the full bio. None for an imprint author.
5. **Contents** (PDF page; EPUB uses the reader's nav) → About this work →
   chapters → colophon (rights, AI-review notice for `ai_unreviewed`).

**The two formats ship differently — this is the thing to remember:**

| | EPUB | PDF |
|---|---|---|
| Built | per request by the API (`BookEpubView`) from live DB rows | after merge, by `.github/workflows/book-pdfs.yml` (`export_book --all --format pdf` + headless Chrome, text from the seeded FIXTURE) |
| Lives | `GET /api/library/books/<slug>/download.epub?language=<lang>` | Supabase Storage bucket `book-pdfs`, under `export_filename`, overwritten in place; `Book.pdf_url` points at it. **Never in git.** |
| Goes stale when | never (text), but the cover is the bundled copy | never, as long as the change goes through the fixture: a push to `main` that touches a book's fixture rebuilds that PDF; a push touching the pipeline (`book_export.py`, `export_policy.py`, `export_strings.json`, `export_bios/`, `export_covers/`, `print_fonts/`, `authors.json`, `export_book.py`) rebuilds them all |

The PDF is built from the FIXTURE, not production's DB: a fix that reached
production only by data migration isn't in a PDF until the fixture has it.
Re-run everything by hand from the Actions tab (Book PDFs → Run workflow).

## 1. Pre-flight (don't export a book that isn't ready)

- Published, and its text is clean — run `english-qa` / `founder-kit:book-qa`
  first. The PDF freezes whatever is in the DB.
- A raster cover exists for it on the site (designed jpg, or the og twin png).
- **Imprint-authored editions (Ochorus Originals — Brave for God, Rooted, the
  Portraits of Courage lives and their retellings) get NO About the Author page
  and need NO export bio:** `author_bio` returns "" for `is_imprint`. That's by
  design — don't add one, and don't read its absence in the PDF as a bug.
- Otherwise the author has an export bio, `backend/library/export_bios/<author-slug>.<lang>.txt`:
  3–4 paragraphs (blank-line separated), ~250–285 English words, written from
  the author's long `bio_html` — its facts and verbatim quotes only. `PilotTests`
  requires one for every exportable edition, rejects a file no edition uses, and
  pins in `export_bios/sources.json` the digest of the long bio each was checked
  against (`migrations/data/author_bios_<lang>/<slug>.html` when that language has one, else the English `bio_html`):
  when that test fails, re-read the bio against the new long bio, then update
  the digest. It must fit ONE A5 page — `export_book` fails a PDF whose author
  page spills onto the next (its `author-top`/`author-end` anchors land on
  different pages); `--all` still writes the others and fails at the end, and
  `book-pdfs.yml` uploads what passed. Swahili and
  Luganda run ~10% longer than English; Ukrainian fills the page at ~1,700
  characters. A translated export bio is AI-written and has no review state
  (unlike `AuthorTranslation`) — say so when you add one. Editing any of them
  makes `book-pdfs.yml` rebuild every PDF. (The code still falls back to the
  short `Author.bio` / `AuthorTranslation.bio`, but the test means no shipped
  download uses it.)
- **Is the book actually public domain?** A living author's book (Gareth Evans,
  Growing in Wisdom) still carries `source_type=public_domain` — the schema has no
  licensed value — so the colophon would CLAIM public domain. Give every edition an
  `attribution` opening with "©" (e.g. "© Gareth Evans. Shared free on Ochorus with
  the author's permission."); `book_export.is_in_copyright` then prints that line
  instead of the public-domain one. The wording is the founder's call — ask.
  Ochorus's own writing (Originals, the "(For Children)" / "(For Teens)"
  retellings) uses the established "© Ochorus. An Ochorus retelling for young
  readers of …" / "An Ochorus Original …" lines — no need to ask for those.
  A retelling goes in `EXPORT_PILOT`, never `ENGLISH_CLASSICS`: that list's back
  matter calls the text public domain, and `PilotTests` rejects a retelling or
  an imprint book there.
- **Scripture permissions travel into the download.** An edition quoting the
  ESV / NIV / NLT needs that publisher's notice in its `attribution` (the teen
  retellings of #5340 carry Crossway's); the ASV and KJV need none. Books whose
  Scripture accidentally reads as the ESV are held out in `HELD_ESV`.
- A translation still `ai_unreviewed` exports with the "awaiting review" notice
  in its colophon. That's correct; don't strip it.

## 2. Code changes

1. Add `(slug, lang)` to `EXPORT_PILOT` in `backend/library/export_policy.py`.
   (It's a prerender content root, already in `render.yaml`'s buildFilter — the
   book page's download row appears on the next web build.)
2. A new **language** needs every key of `STRINGS["en"]` in `STRINGS[lang]`
   (contents, about, chapter, published, rights, ai_unreviewed, read_online,
   more, author_title, full_bio, ochorus_title, ochorus_html) — Ochorus's own
   prose, no English fallback. `PilotTests` fails otherwise.
3. Set the edition's fixture `pdf_url` to the bucket file:
   `f"{export_policy.PDF_STORAGE_URL}{name}?download={name}"`, where `name` is
   `export_filename` — `<slug>.pdf` for English, `<slug>.<lang>.pdf` otherwise.
   Spelled out:
   `https://eywunobxqijvwymdzlwy.supabase.co/storage/v1/object/public/book-pdfs/<name>?download=<name>`
   (`?download=` makes Supabase send it as an attachment; a cross-origin
   `<a download>` is ignored). Some fixture rows have NO `pdf_url` key at all
   (older serializer) — insert it after `cover_url` rather than assuming a
   replace will hit. `PilotTests.test_every_stored_pdf_edition_links_its_bucket_file`
   fails on anything else. The URL 404s until `book-pdfs.yml` has run after merge.
4. Bundle the cover: `backend/library/export_covers/<slug>.<lang>.<ext>` must be
   byte-identical to the file the site serves for `cover_image_url` — for a
   plate or painting that's the og twin, so `cp frontend/static/covers/<slug>.png
   backend/library/export_covers/<slug>.en.png` does it (the §3 preview run
   writes it too). `CoverTests` fails when it is missing or stale.
   Non-English back matter lives in `backend/library/export_strings.json`
   (merged into `STRINGS`); its vision line is the site catalogue's
   `about_vision_quote`.

## 3. Preview locally (nothing here is committed except the bundled cover)

```bash
cd backend
cp ../../ochorus/backend/.env .env           # sqlite dev DB; no prod creds needed
                                             # (cloud container: `export DJANGO_DEBUG=true` instead)
uv run python manage.py migrate -v0 && uv run python manage.py seed_books -v0
uv run python manage.py seed_author_translations -v0   # else translations get NO bio page
PUBLIC_SITE_URL=https://ochorus.com uv run python manage.py export_book <slug> --language <lang> --format pdf --out <scratch>/<slug>.pdf
PUBLIC_SITE_URL=https://ochorus.com uv run python manage.py export_book <slug> --language <lang> --format epub --out <scratch>/<slug>.epub
```

- The local PDF is a PREVIEW. Write it to a scratch folder (`--out`) and never
  commit it — CI builds the real one. `frontend/static/pdfs/` is legacy (one
  old file lives there); nothing new goes in it.
- `PUBLIC_SITE_URL` is what the colophon / About pages link to — without it the
  PDF prints no links.
- Every run also refreshes the **bundled cover**
  `backend/library/export_covers/<slug>.<lang>.<ext>` from the file the site
  serves. Commit it. (The API image is built from `backend/` alone and its fetch
  of the cover from the site failed in production — every EPUB shipped
  cover-less and Apple Books drew a red placeholder. The bundle is why the
  EPUB has a cover now.)
- Needs Chrome (`CHROME_PATH` if not in the usual place). The PDF is printed
  twice so the contents page carries real page numbers.

## 4. Check before you ship

- Render the front matter and LOOK:
  ```bash
  uv run --with pymupdf python -c "import pymupdf;d=pymupdf.open('<scratch>/<slug>.pdf');[d[i].get_pixmap(dpi=90).save(f'<scratch>/p{i}.png') for i in range(6)]"
  ```
  Page 1 cover, 2 title, 3 About Ochorus, 4 About the Author (ONE page — the
  "Read the full biography" line must be on it), 5 Table of Contents, 6 first
  part — and the contents numbers match where chapters actually start. (An
  imprint edition has no page 4, so everything after it moves up one.) Check the
  last page too: the colophon's `©` line, and any Scripture notice.
- EPUB: `unzip -l` shows `OEBPS/cover.*` and `about-author.xhtml` (not for an
  imprint edition); the OPF has
  `properties="cover-image"`; spine order is ochorus → author → about.
- Arabic/RTL: `dir="rtl"` and `page-progression-direction="rtl"`; Devanagari
  shapes correctly in the PDF (Chrome does the shaping).
- `uv run python manage.py test library.tests_book_export` — includes the gate
  that each pilot edition's bundled cover equals the site's file.

## 5. Ship + verify live

PR (diff = export_policy line, fixture `pdf_url`, the bundled cover, any
STRINGS — **no PDF file**; see #5340 for the shape) → merge on green → three
things land, at different times:

- **Book PDFs workflow** (a few minutes after merge): builds the changed
  editions' PDFs and uploads them to the bucket. Until it finishes, `pdf_url`
  404s. If it fails, its log names the edition (most often an About the Author
  page that spilled onto a second page); the editions that passed are still
  uploaded.
- **API** (~2–3 min): the EPUB endpoint, and the book API's `pdf_url`/`epub_url`.
- **Web** (~20–40 min, longer if queued): the book page and its Download menu.
  The web service builds ONE deploy at a time — if a build is already running
  when you merge, yours waits for it. Check before worrying:
  `gh api repos/jdegreef/ochorus/deployments --jq '.[:6][]|.sha[:8]+" "+.environment'`
  — no `ochorus-web` row for your merge commit yet = still queued, not broken.

```bash
# EPUB (API)
curl -s -o /tmp/e.epub "https://api.ochorus.com/api/library/books/<slug>/download.epub?language=<lang>"
unzip -l /tmp/e.epub | grep -E "cover|about-author"
# PDF (bucket) — 200, application/pdf, and a fresh Last-Modified
curl -sI "https://eywunobxqijvwymdzlwy.supabase.co/storage/v1/object/public/book-pdfs/<file>.pdf" | grep -iE "^HTTP|content-type|last-modified"
# Book page (web): the links live in the page's INLINED DATA, not its markup
curl -s https://ochorus.com/<lang-prefix>/books/<slug>/ | grep -c 'download.epub?language=<lang>'
curl -s https://ochorus.com/<lang-prefix>/books/<slug>/ | grep -o 'pdf_url[^,]*'
```

**The download links are NOT in the page's HTML.** Since #3277 they sit in the
book header's **Download** menu (`BookDownloadMenu`: Download for offline ·
EPUB — For e-readers · PDF — For printing), which renders its links only when
opened. A grep for `href="…download.epub"` / `href="…/pdfs/…"` in the page
therefore finds nothing even when everything works — it reported "0 links" on
all of Gareth's pages while they were fine. Check `pdf_url`/`epub_url` in the
inlined `data-sveltekit-fetched` JSON (above), and for a final look open the
menu in a browser. Likewise never grep the word "epub": `datePublished`
contains it. Apple Books caches a book's cover: re-download a fresh copy to see
a fix.

## Gotchas

- **Stale PDF.** EPUB follows the DB; the PDF follows the FIXTURE, rebuilt by
  `book-pdfs.yml` on every push to `main` that touches it (one book's fixture →
  that book; the pipeline → all). A fix shipped only as a data migration never
  reaches the PDF — put it in the fixture. Never commit a PDF to "refresh" one.
- **Wordless cover.** Never export `cover_url` directly for a painting/plate —
  it has no title. `cover_image_url` handles it; keep it that way.
- **Page order is asserted** (`test_a_short_biography_follows_about_ochorus`);
  moving a page means updating that test deliberately.
- **RTL (Arabic).** English runs inside an RTL paragraph — the © line, URLs —
  get their "©", full stop and trailing "/" flung to the wrong end by bidi. The
  export marks the © line `dir="auto"` and every link `dir="ltr"`; keep that on
  anything new, and LOOK at an Arabic colophon (text extraction reorders RTL, so
  a grep "failure" there can be a false alarm — render the page).
- **Batch runs.** Loop `export_book` over editions with an OK/FAIL log (≈10 s per
  PDF); then check every colophon: `© …` present and no public-domain phrase in
  any language.
- **The old committed-PDF flow is gone.** Earlier versions of this playbook
  committed PDFs under `frontend/static/pdfs/` with `pdf_url=/pdfs/…`; that cost
  ~64 MB of repo for Gareth's 38 alone. Every exportable edition now lives in
  the bucket (`STORED_PDF_EDITIONS = EXPORT_EDITIONS`).
- **Life dates** print `1847–1929`; a living author prints `1938–`.
- **Previewing from a Linux cloud container** (runs as root). Chrome refuses to
  start as root without `--no-sandbox`: point `CHROME_PATH` at a two-line
  wrapper, `exec /opt/pw-browsers/chromium --no-sandbox "$@"`. EB Garamond is
  now bundled in `backend/library/print_fonts/`, so a Latin PDF embeds
  `EBGaramond-*` with no font setup (check with pymupdf's `page.get_fonts()`).
  Arabic and Devanagari still fall back to system fonts — CI installs
  `fonts-noto-core` for them; a container without it renders Hindi with broken
  matras, so don't judge a Hindi preview by its shaping.
