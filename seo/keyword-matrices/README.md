# SEO keyword matrices

Target-phrase matrices for Ochorus, generated from the content fixtures. Each
workbook has a **Read me** tab, a wide **Matrix** tab (one row per entity), and
a **Keywords (long)** tab (one phrase per row, tier-banded, import-ready for
Ahrefs/SEMrush/a rank tracker). Every phrase maps to a real URL.

Each workbook's long sheet is also committed as a UTF-8 `.csv` of the same
basename (`books-en.csv`, …) — the diff-friendly, tool-importable form. The
`.xlsx` are the richer artifact (three tabs, formatting); the `.csv` are the
review- and import-friendly companion. Regenerate the CSVs from the long tab.

| File | Entity | URL pattern | Phrases |
|---|---|---|---|
| `books-en.xlsx` | 108 English books | `/books/<slug>` | 756 |
| `books-localized.xlsx` | books in es/sw/pt/hi | `/<lang>/books/<slug>` | 763 |
| `authors-en.xlsx` | 90 authors (+ short-name variants) | `/authors/<slug>` | 486 |
| `authors-localized.xlsx` | authors in es/sw/pt/hi | `/<lang>/authors/<slug>` | 583 |
| `topics-en.xlsx` | 30 topic shelves | `/topics/<slug>` | 156 |
| `topics-localized.xlsx` | translated shelves, es/sw/pt/hi | `/<lang>/topics/<slug>` | 150 |

## Conventions

- **Access-intent tiers** — Tier 1 = transactional/navigational (optimize the
  page `<title>`/H1 for these); Tier 2 = supporting; Tier 3 = informational.
- **Content gating** — a facet only appears where the content exists. Authors:
  Books/Sermons/Quotes facets fire only where that author has such content;
  bio-only authors get Name/Biography/Who-was only. The **Who-was** facet
  targets the FAQPage schema already on every bio.
- **Localized gating is per-locale** — books/sermons/bios counted from the
  `.<lang>.json` fixtures; the **Quotes facet is dropped** in localized author
  sheets (sourced quotes are English-only). Topics: only shelves actually
  translated in a locale appear (topic prose has no English fallback).
- **Author names stay in Latin script** in every locale.
- **Short-name variants** (authors-en) are only token-differing forms
  (`charles spurgeon`, `tozer`, `george mueller`) — punctuation-only variants
  are omitted because Google ignores them.
- **Localized felt-need queries are intentionally absent** from
  `topics-localized.xlsx` — "how to pray" etc. are idiomatic and need a
  native-speaker pass; translate from the English set in `topics-en.xlsx`.
- **sw/hi modifiers** are natural but not volume-validated — native review
  before committing title tags.

## Source of truth

Regenerate from `backend/library/fixtures/content/{books,sermons}/*.json`,
`backend/library/fixtures/content/authors.json`, `backend/library/topic_seed.py`,
`backend/library/data/topic_translations/<lang>.json`, and
`backend/library/migrations/data/author_bios_<lang>/`.
