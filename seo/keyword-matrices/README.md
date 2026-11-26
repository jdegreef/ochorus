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

## The next languages (fr, am, ko, vi)

`build_localized.py` writes one CSV per entity and language, `books-<lang>.csv`,
`authors-<lang>.csv` and `topics-<lang>.csv`, in the `*-localized.csv`
columns, straight from the fixtures:

    python3 seo/keyword-matrices/build_localized.py fr am ko vi

Re-run it before a language goes live, and after a batch of translations
lands, so the sheet matches what ships. CSV only (no workbook). Bible books
are left out: their searches are passages ("psaume 23"), which belong to the
Bible pages. The modifiers are natural phrasings, **not volume-validated**.
Have a native speaker read the tier-1 rows before they set a title tag.

| File | Phrases (2026-11-26) |
|---|---|
| `books-fr.csv` / `authors-fr.csv` / `topics-fr.csv` | 1,282 / 473 / 99 |
| `books-am.csv` / `authors-am.csv` / `topics-am.csv` | 1,155 / 371 / 99 |
| `books-ko.csv` / `authors-ko.csv` / `topics-ko.csv` | 907 / 302 / 99 |
| `books-vi.csv` / `authors-vi.csv` / `topics-vi.csv` | 719 / 373 / 99 |

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
