---
name: book-export
description: Produce the free PDF and EPUB downloads for one Ochorus book edition — add it to the export pilot, generate the PDF with headless Chrome, bundle its cover for the EPUB, check the front matter (cover, title page, About Ochorus, About the Author, contents), ship, and verify both downloads live. Use when asked to make a book downloadable, create/regenerate a book's PDF or ePub, widen the download pilot, or when a download looks wrong (missing cover, missing bio page, stale text). This is a living playbook — append new failure modes as we find them.
---

# Book export (PDF + EPUB)

One edition = one `(slug, language)`. Both formats are built from the same parts
in `backend/library/book_export.py`, in this order:

1. **Cover** — the cover *as the site shows it* (`cover_image_url`): a designed
   cover is its own image; a painting/plate is wordless, so its og twin
   (`/covers/<slug>.png`, `/covers/<lang>/<slug>.png`) is used.
2. **Title page**
3. **About Ochorus** — `STRINGS[lang]["ochorus_html"]`
4. **About the Author** — the author's SHORT bio (`Author.bio`; for another
   language `AuthorTranslation.bio`), life dates, and a link to the full bio.
   No English fallback and none for an imprint author → no page.
5. **Contents** (PDF page; EPUB uses the reader's nav) → About this work →
   chapters → colophon (rights, AI-review notice for `ai_unreviewed`).

**The two formats ship differently — this is the thing to remember:**

| | EPUB | PDF |
|---|---|---|
| Built | per request by the API (`BookEpubView`) from live DB rows | once, off-server, by `export_book` + headless Chrome |
| Lives | `GET /api/library/books/<slug>/download.epub?language=<lang>` | `frontend/static/pdfs/<export_filename>` (committed), `Book.pdf_url` |
| Goes stale when | never (text), but the cover is the bundled copy | ANY change to text, bio, cover, back matter or CSS → regenerate |

## 1. Pre-flight (don't export a book that isn't ready)

- Published, and its text is clean — run `english-qa` / `founder-kit:book-qa`
  first. The PDF freezes whatever is in the DB.
- A raster cover exists for it on the site (designed jpg, or the og twin png).
- The author has a short `bio` in that language. English: `authors.json`
  `bio`. Other languages: an `AuthorTranslation` with `bio` (see
  `write-biography` / `approve_author_translation`). Without one the book simply
  has no About-the-Author page — decide if that's acceptable.
- **Is the book actually public domain?** A living author's book (Gareth Evans,
  Growing in Wisdom) still carries `source_type=public_domain` — the schema has no
  licensed value — so the colophon would CLAIM public domain. Give every edition an
  `attribution` opening with "©" (e.g. "© Gareth Evans. Shared free on Ochorus with
  the author's permission."); `book_export.is_in_copyright` then prints that line
  instead of the public-domain one. The wording is the founder's call — ask.
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
3. Set the edition's fixture `pdf_url` to `/pdfs/<export_filename>` —
   `<slug>.pdf` for English, `<slug>.<lang>.pdf` otherwise. Some fixture rows
   have NO `pdf_url` key at all (older serializer) — insert it after `cover_url`
   rather than assuming a replace will hit. `PilotTests` fails when an exportable
   edition has no `pdf_url` or its file is missing.
   Non-English back matter lives in `backend/library/export_strings.json`
   (merged into `STRINGS`); its vision line is the site catalogue's
   `about_vision_quote`.

## 3. Generate (in your worktree)

```bash
cd backend
cp ../../ochorus/backend/.env .env           # sqlite dev DB; no prod creds needed
uv run python manage.py migrate -v0 && uv run python manage.py seed_books -v0
uv run python manage.py seed_author_translations -v0   # else translations get NO bio page
PUBLIC_SITE_URL=https://ochorus.com uv run python manage.py export_book <slug> --language <lang> --format pdf
PUBLIC_SITE_URL=https://ochorus.com uv run python manage.py export_book <slug> --language <lang> --format epub --out /tmp/<slug>.epub
```

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
  python3 -c "import fitz;d=fitz.open('frontend/static/pdfs/<file>.pdf');[d[i].get_pixmap(dpi=90).save(f'/tmp/p{i}.png') for i in range(6)]"
  ```
  Page 1 cover, 2 title, 3 About Ochorus, 4 About the Author, 5 Contents, 6 first
  part — and the contents numbers match where chapters actually start.
- EPUB: `unzip -l` shows `OEBPS/cover.*` and `about-author.xhtml`; the OPF has
  `properties="cover-image"`; spine order is ochorus → author → about.
- Arabic/RTL: `dir="rtl"` and `page-progression-direction="rtl"`; Devanagari
  shapes correctly in the PDF (Chrome does the shaping).
- `uv run python manage.py test library.tests_book_export` — includes the gate
  that each pilot edition's bundled cover equals the site's file.

## 5. Ship + verify live

PR (diff = export_policy line, fixture `pdf_url`, the PDF, the bundled cover,
any STRINGS) → merge on green → **two deploys**, and they land far apart:

- **API** (~2–3 min): the EPUB endpoint, and the book API's `pdf_url`/`epub_url`.
- **Web** (~20–40 min, longer if queued): the PDF file under `/pdfs/` and the
  book page. The web service builds ONE deploy at a time — if a build is already
  running when you merge, yours waits for it (#3378: PDFs 404'd for ~35 min while
  EPUBs already worked). Check before worrying:
  `gh api repos/jdegreef/ochorus/deployments --jq '.[:6][]|.sha[:8]+" "+.environment'`
  — no `ochorus-web` row for your merge commit yet = still queued, not broken.

```bash
# EPUB (API)
curl -s -o /tmp/e.epub "https://api.ochorus.com/api/library/books/<slug>/download.epub?language=<lang>"
unzip -l /tmp/e.epub | grep -E "cover|about-author"
# PDF file (web) — compare bytes to what merged, not just the status code
curl -s https://ochorus.com/pdfs/<file>.pdf | md5; git show origin/main:frontend/static/pdfs/<file>.pdf | md5
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

- **Stale PDF.** EPUB follows the DB; the PDF doesn't. After a text fix, bio
  edit, cover change or a change to `book_export.py`'s pages/CSS, regenerate
  every pilot PDF and commit them.
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
- **Repo weight.** Each PDF is ~1–2 MB committed; 38 of Gareth's added ~64 MB.
- **Life dates** print `1847–1929`; a living author prints `1938–`.
