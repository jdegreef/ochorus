---
name: translate-book
description: Translate an Ochorus book into another language via the AI-translate-then-review pipeline (translate_book management command), producing a new Book row (same slug, new language) flagged ai_unreviewed until approve_translation upgrades it. Use when asked to translate a book, add a language to the library, review/approve a machine translation, or add a new target language to the pipeline. This is a living playbook — append new failure modes and language notes as we find them.
---

# Translating a book (AI-translate → review)

**STATUS: pipeline BUILT and browser-verified (2026-07-09).** Engine in
`backend/library/translation.py`; commands `translate_book` /
`approve_translation`. Pilot languages: Spanish (es), Swahili (sw),
Luganda (lg).

## How it works

1. **Source** is the English Book row's chapters (`body_html`, canonical after
   book-import QA) — never the PDF.
2. **Scripture is never machine-translated.** `translation.py` detects Bible
   references (English book names → USFM), fetches those chapters in the
   target language from the **Take Root Bible API**
   (`api.takeroot.bible/api/bible/<code>/<usfm>/<ch>/` — es→rv1858,
   sw→swhonen, lg→lug, all complete Bibles) and supplies them to the model as
   `<authoritative_scripture>` — quoted verses must use that wording.
3. **Model**: `claude-opus-4-8`, adaptive thinking, `--effort high` default
   (doctrinal fidelity > speed), streaming. Chapters travel in
   `<chapter_title>`/`<chapter_body>` wrappers; HTML structure must round-trip
   exactly (marks/highlights anchor to paragraph indices — structure drift
   breaks reader anchors).
4. **Per-language glossary** in `LANGUAGES` pins theological terms
   (justification/sanctification/atonement/…). Grow it when review finds an
   inconsistency.
5. Target Book row: same slug, `source_type=ai_unreviewed`, copies
   cover/sort, **pdf_url deliberately empty** (the PDF is the English
   edition). `body_text` derives via `Chapter.save()`.

## Commands

```bash
# needs ANTHROPIC_API_KEY (backend/.env is dotenv-loaded, or export it)
manage.py translate_book <slug> --language es [--chapters 1,2] [--force] [--effort high] [--dry-run]
manage.py approve_translation <slug> --language es    # after native review ONLY
```

Idempotent/resumable: existing target chapters are skipped unless `--force`,
so a failed run is just re-run. Cost/time: an Opus chapter of ~1,000 words ≈
1–3 minutes; run long books with nohup + a log tail.

## UI plumbing (already wired — don't rebuild)

- Language picker: gear menu → Language; appears automatically when a second
  language has ≥1 published book (`/api/library/languages/` is derived from
  Book rows). Labels come from `LANGUAGE_NAMES` in `library/views.py`.
- Trust badge on the book page: `ai_unreviewed` → gold "AI translation —
  awaiting native review" pill; `ai_reviewed` → muted "reviewed" pill.
- UI strings: `frontend/src/lib/i18n.svelte.ts` `MESSAGES` dicts (en/es/sw/lg;
  missing keys fall back to EN). **Adding a language = LANGUAGES entry in
  translation.py + LANGUAGE_NAMES entry + a MESSAGES dict.**

## Review gate (required before ai_reviewed)

- A native / theologically-literate reviewer reads: first chapter, one middle
  chapter, and every scripture-quoting passage.
- Check: meaning fidelity (no doctrinal drift), scripture quotes match the
  target Bible wording, glossary terms consistent across chapters, natural
  register (not translationese).
- The UI dictionaries are ALSO ai-drafted — include them in the language's
  first review.
- Only the user decides to run `approve_translation` — never auto-promote.

## Shipping translations to prod

Translations are **new Book+Chapter rows** → ship per ship-content-fix:
regenerate the fixture (canonical shape: strip `body_text` keys + plan rows),
plus a data migration that inserts the translated books from the fixture
(match books by fixture-pk→slug, resolve Author by slug, set body_text via
`library.text.html_to_text`); then the manual `ochorus-web` redeploy for
prerendered pages. Search FTS: es/en stem properly on prod Postgres; sw/lg use
"simple" config (exact-word match only) — acceptable, note it.

## Known failure modes & language notes (append as we learn)

- **No ANTHROPIC_API_KEY on the machine** → the command dies with "Could not
  resolve authentication method". Backend `settings.py` dotenv-loads
  `backend/.env`, so the user can put the key there (never paste keys into
  chat). Check `ant auth status` too before asking.
- **Placeholder key pasted verbatim** — a user given `echo 'ANTHROPIC_API_KEY=sk-ant-...'`
  may run it literally. Verify WITHOUT printing the secret:
  `awk -F= '/^ANTHROPIC_API_KEY=/{print length($2)}' .env` — a real key is
  ~100+ chars; ~10 means the literal `sk-ant-...` placeholder. Also dedupe
  repeated lines (`sed -i '' '/^ANTHROPIC_API_KEY=/d'` then re-add once).
- **Key-less pilot path**: for a small pilot (a few chapters), Claude Code can
  translate in-session using the same `scripture_context()` helpers + glossary
  + wrapper protocol, writing rows through the same ai_unreviewed path — no
  API key needed. The `translate_book` command is for unattended scale.
- **Model response missing wrapper tags** → `translate_chapter` raises; the
  run is resumable. Usually a truncation (`max_tokens`) on a huge chapter —
  split with `--chapters` or raise max_tokens.
- **Book has no `original_language` field** — the model docstring mentions the
  concept but the column doesn't exist on Book; don't set it.
- **Nested dropdowns clip in the gear menu** — `.prefs-menu` needs
  `overflow: visible` (fixed 2026-07-09).
- Reference detection covers `Book C:V` patterns with full English book names
  (Psalm/Psalms, Song of Solomon/Songs variants). Abbreviations ("Ps. 23:1")
  are NOT detected yet — add to `_REF_RE` when a book needs it.
