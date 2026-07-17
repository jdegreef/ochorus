---
name: contemporize-book
description: Produce a "Modern English" edition of a classic English Ochorus book — modernizing archaic language so it reads easily for today's audience, while keeping the author's voice and the original text intact. Two passes share the translate-then-review workflow: a deterministic LIGHT pass (no model/key, ships today) and a model-backed CAREFUL pass. Use when asked to contemporize / modernize a book's English, when onboarding a new English book (run after book-qa), or to review/approve a modern edition. This is a living playbook — append new archaic forms and failure modes as we find them.
---

# Contemporizing a book (Modern English edition)

**STATUS: pipeline + reader toggle BUILT (2026-07-17). Light pass ships today;
careful pass needs a key. Once a modern edition is shipped, readers get a
per-book Modern English ⇄ Original toggle.**

A "Modern English" edition is a **separate `Book` row sharing the work's slug**,
in content language **`en-modern`**. The original English row is never touched,
so a reader can always compare against the authentic classic. This reuses the
exact `(slug, language)` shape and the `ai_unreviewed → ai_reviewed` review
workflow the translation pipeline already uses.

Engine: `backend/library/contemporize.py`. Command: `contemporize_book`.
Approval reuses `approve_translation ... --language en-modern`.

## Why an edition, not a replacement

These are revered classics; readers come to Ochorus for the authentic voice of
Spurgeon, Murray, Bunyan. So we **never overwrite the original** — we offer a
modern edition alongside it. That also contains the risk: any modernization
error is a separate, reviewable, discardable row, and the original is one click
away.

## The two passes

| Pass | Needs key? | What it does |
|------|-----------|--------------|
| **light** (default) | No | Deterministic. A curated, high-precision map of archaic pronouns (`thou/thee/thy`), verb forms (`hath`, `cometh`, `knowest`) and obsolete spellings (`shew`, `unto`, `whilst`). Precision over recall — anything not listed is left exactly as written, so it never guesses or shifts meaning. |
| **careful** | Yes (`ANTHROPIC_API_KEY`, run locally) | Model-backed. Modernizes vocabulary and untangles long Victorian sentences while preserving meaning, theology, Scripture wording and the author's voice. Reuses the translation pipeline's streaming + wrapper-tag protocol and the same MODEL. |

The light pass is honest about its scope: it does the safe mechanical fraction.
The careful pass handles the long tail (obsolete vocabulary, sentence structure)
and is the one you'd normally ship — light is the no-key fallback / first look.

Scripture is never re-worded by the light pass; the careful pass is instructed
to keep quoted Scripture as the author quoted it.

## Running it

```bash
# Light (deterministic, no key) — good for a quick first pass / preview:
manage.py contemporize_book <slug>                     # all chapters
manage.py contemporize_book <slug> --chapters 1,2      # subset
manage.py contemporize_book <slug> --dry-run           # show the plan

# Careful (model-backed; run locally with a key):
manage.py contemporize_book <slug> --mode careful --effort high

# Idempotent/resumable: existing chapters are skipped unless --force.

# After native review, drop the "unreviewed" badge:
manage.py approve_translation <slug> --language en-modern
```

Only public-domain English originals may be contemporized (the command refuses
an `ai_*` source, so you can't modernize a translation or a modern edition).

Ship the resulting rows to prod as data like any content change — see the
**ship-content-fix** skill (fixture refresh or data migration), then the
static-page redeploy step.

## Surfacing to readers (BUILT)

`en-modern` is a **content** language, deliberately NOT a Paraglide UI locale
(the switcher still shows only en/es/sw/lg). Because it has its own language
code, a modern edition is **invisible** to every existing query
(`?language=en` etc.) until something asks for `en-modern` — so shipping the
backend/data is safe and changes nothing for users until an edition exists.

How the reader surfaces it (PR, 2026-07-17):

- The API advertises availability: `BookDetailSerializer` /
  `ChapterDetailSerializer` return `has_modern_edition` (a published en-modern
  row exists for this English work) and `is_modern_edition` (this row IS it).
- The edition is a **reader-level mode carried in the URL** as
  `?edition=modern`, NOT the UI locale. The reader/book loads map it to content
  language `en-modern`; every in-reader chapter link (prev/next, TOC drawer,
  bookmarks) preserves the param so you stay in the edition as you navigate.
- The book page shows a "Read in Modern English" entry button when
  `has_modern_edition`; the reader chrome shows a compact **Modern ⇄ Original**
  toggle, and the chapter meta line tags the modern edition.
- Reading progress / marks stay keyed to the UI locale (not the edition), so a
  reader's place carries across a mid-book edition switch (chapter orders match
  1:1). Caveat: a character-offset highlight made on one edition may drift on
  the other's modernized wording — acceptable for v1; revisit if it bites.

## Extending the light map

Add archaic forms to `_PHRASES` / `_WORDS` in `contemporize.py`. Rules:

- **Precision over recall.** Only add a single word if it has *no* modern
  homograph. Bare `art`, `ye`, `wont`, `even` are deliberately absent (they mean
  something modern); `art`/`ye` are handled only inside unambiguous phrases like
  `thou art`.
- **No general `-eth`/`-est` rule** — it mangles irregulars (`cometh`→"coms").
  List each verb form explicitly.
- The maps run against sanitized chapter HTML directly; the tokens never collide
  with the tag/attribute vocabulary (`p`, `h2`, `blockquote`, `em`, `i`, `hr`,
  `class`), so only readable text is touched. If a new tag/attribute ever shares
  a word with the map, revisit this.
- Case of the first letter is preserved automatically (`Thou`→`You`).

Tests live in `library/tests.py` (`ContemporizeLightTests`,
`ContemporizeCommandTests`, `ContemporizeCarefulTests`) — add a case for every
new form or failure mode.
