# Ochorus content-growth plan

A plan for growing reader-visible content — articles, quotes, biographies — as
the site's main SEO lever. Written to be picked up in a **Node-capable session**
where the in-repo skills, seeds and CI can actually run.

## Why content is the lever

Three content types, three SEO jobs:

- **Articles** — the `Article` model calls itself *"the SEO layer"*: each one
  answers a real search query and funnels the reader into the library via its
  "Read next" block (and now carries the free-account CTA). Highest compounding
  ROI.
- **Quotes** — an author's quotations power both `/quotes/<author>` and the
  per-theme `/quotes/<author>/<topic>` pages (which are prerendered and
  sitemap-listed once a pair is deep enough). Growing quotes turns
  already-shipped infrastructure into ranking surface.
- **Biographies** — a rich author page ranks and supplies E-E-A-T for the whole
  cluster of books/sermons/quotes beneath it.

## Prioritisation method (run at session start — don't guess)

- **Quotes:** rank the quote authors by their reviewed-quote count; target the
  ones **below the ~50/author goal that have the most source material** (books
  and sermons already imported = raw quotations available to extract). As of the
  last check, Spurgeon (~97), E. M. Bounds (~55), Andrew Murray (~50) and
  Augustine (~50) are at goal; the remaining authors are the gap.
- **Articles:** list the article topic-shelves and their counts. Thin,
  high-intent shelves are the fill-in targets — **On Prayer (~7)** and **Faith &
  Guidance (~8)** were the smallest at last look, against Deeper Life (~21),
  Gospel Call (~18), Grace & Comfort (~13). Once the `plausible-analytics` work
  lands, re-rank by real impressions rather than intuition.
- **Biographies:** find authors with a blank/short `bio` but published books —
  those pages rank weakly today and already receive inbound links from their
  quote and book pages.

## A concrete first batch (~one PR set)

1. **Quotes:** pick the **two highest-material sub-50 authors** and run
   `quote-extraction` to ~50 each. Side effect: new `/quotes/<author>/<topic>`
   pages appear wherever a theme crosses the server-side depth threshold.
2. **Articles:** write **3–4 articles** on the thinnest high-intent shelves
   (Prayer, Faith & Guidance) — each 1500–2000 words, 7+ Scriptures, attributed
   to Ochorus (a byline + schema author, never an individual), ending in a
   "Read next" funnel to a **real** book/sermon/bio.
3. **Biographies:** write **1–2** for quoted authors with thin bios — their
   quote page and book pages both link in, so the bio catches that traffic.

## Workflow & guardrails (the repo's own conventions)

- Use the in-repo skills exactly: **`quote-extraction`**, **`write-article`**,
  **`write-biography`**. They encode the fixture format, the paragraph-resolution
  gate for quotes, the Scripture/funnel requirements for articles, and the
  review / auto-publish semantics.
- **One new file per work** (fixture convention). New authors append to
  `authors.json`.
- **English originals** ship `source_type=public_domain` — no translation-review
  dance. Never hand-edit prod rows: seeds re-run every deploy, so anything a
  workflow owns after creation (review state) must be **create-only** in the
  seed.
- New reader-visible content must live under a root declared in
  `library/content_sources.json`, or the prerendered page never rebuilds — the
  reader is static, so the build only regenerates a page when something notices
  the content changed. `tests_fixture` enforces this.
- Before requesting merge: `/simplify`, then `/code-review high`, then
  `npm run check` + `npm run test` + the fixture tests — and fold the findings
  in. One PR per feature.
- **Link every new piece into the mesh:** an article's "Read next" → books /
  sermons / bios; a new bio → the author's quotes; a book already links to its
  author's quotes (feat/book-author-quotes-link). The interlinking is what
  compounds authority.

## Cadence & measurement

- A clean, reviewable batch is roughly **two authors' quotes + 3–4 articles +
  1–2 bios**, split as one PR per feature.
- Steer with data once analytics is live: prioritise the next batch by real
  impressions/clicks, not intuition.
- Between content batches, pick up the **no-Node** mesh/polish items — the
  page-design consistency backlog (in the `page-design` skill) and the
  chapter-reader follow-up to the book→quotes link.

## What a session needs

The Node/uv toolchain (skills, seeds, `sync:catalogues` if any UI strings
change), the backend DB for `quote-extraction`'s paragraph resolution, and CI to
gate. Everything here is content + fixtures — no schema or infrastructure work.
