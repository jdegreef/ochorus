---
name: translate-book
description: Translate an Ochorus book into another language via the AI-translate-then-review pipeline, producing a new Book row (same slug, new language) flagged ai_unreviewed until human review upgrades it. Use when asked to translate a book, add a language to the library, or review/approve a machine translation. NOTE — the translation pipeline is not built yet; until it exists this skill defines the contract and the review gate, and any invocation should first confirm scope with the user.
---

# Translating a book (AI-translate → review)

**STATUS: pipeline not yet built.** What exists today: the data model and the
frontend language plumbing. If invoked before the pipeline lands, tell the
user what's missing and offer to build it — don't improvise a one-off.

## The locked design (decisions from 2026-06)

- One `Book` row PER LANGUAGE, same `slug` — `(slug, language)` unique. The
  shared slug is what ties translations together; there is no "Work" row.
- `source_type` drives trust labelling:
  `public_domain` (original) → `ai_unreviewed` (machine, labelled "AI,
  unreviewed" in the UI) → `ai_reviewed` (after native/theological review).
- Reading progress, marks, and plans reference `book_slug` + language, so a
  reader's state carries per translation automatically.

## Pipeline contract (build to this)

1. **Source**: the English Book row's chapters (`body_html`, canonical after
   book-import QA). Never translate from the PDF.
2. **Translate per chapter**, preserving the HTML structure exactly (same tag
   set, same paragraph boundaries — marks anchor to paragraph indices, so
   structure drift breaks reader anchors across languages).
3. **Create** Author-translation metadata only if needed (author names stay
   canonical); Book row copies cover/pdf/sort fields, `source_type=ai_unreviewed`.
4. **Derived fields**: `body_text` comes free via `Chapter.save()`; word_count
   recompute; verify search works with the language's FTS config (stemmed:
   en/fr/es/pt; everything else uses "simple" — exact-word match only).
5. **Plans**: seeded plans are per-language — decide with the user whether to
   seed the language's plan variants.
6. **Ship** via ship-content-fix rules (fixture refresh + migration/seed path)
   — remember prod is never re-seeded.

## Review gate (required before ai_reviewed)

- A native / theologically-literate reviewer reads a sample: first chapter,
  one middle chapter, and any doctrinally dense passages flagged during
  translation.
- Check: meaning fidelity (no doctrinal drift), scripture quotations match a
  recognised translation in that language (do NOT machine-translate Bible
  quotes — substitute the established text), names/terms consistent across
  chapters.
- Only the user flips `source_type` to `ai_reviewed` — never auto-promote.

## Language priorities

Follow the Bible-language priorities memory (top-30 African languages research)
when the user asks "which language next" — reach + existing PD scripture
availability matter more than ease.
