---
name: write-article
description: Write a devotional/theological SEO article for the Ochorus Articles section (footer-linked, /articles) and ship it as a content fixture. Use when asked to write an article, add to the Articles section, or produce SEO content that funnels readers into the library. Each article is 1500–2000 words, has 7+ Scriptures, carries no author/byline, and ends with a "Read next" funnel of real books/sermons/bios. This is a living playbook — append new gotchas as we find them.
---

# Writing an Ochorus article

Articles are original site writing — the SEO layer that answers the questions
people search ("how to trust God", "what does it mean to abide in Christ") and
funnels them into the library via a **Read next** block. They live at `/articles`
(footer, not header), carry **no author/byline**, and are per-language rows like
books (English only for now). Model + API + frontend shipped in PRs #1395/#1396;
the design brief is `docs/articles.pdf`. See also [[write-biography]] (the nearest
sibling) and the `articles-section` memory.

Everything below assumes a worktree off `origin/main` and `backend/` with
`DJANGO_DEBUG=true uv run`.

## What a good article is

- **1500–2000 words.** Verified, not eyeballed (see the word-count gotcha).
- **≥7 Scriptures** (the user's standing floor), each carrying the point, varied
  across articles so a reader moving between them isn't seeing the same handful.
- **Answer-first intro** (2–3 sentences), then 4–6 `<h2>` sections that each read
  as their own mini-answer, then a closing. Warm, plain, pastoral.
- **A real funnel.** `related` is a list of `{type, slug}` soft-refs
  (book/sermon/author) that the API resolves to Read-next cards. Point only at
  works that actually exist — pull the live catalogue first
  (`curl .../api/library/books/?language=en`) and confirm the slugs.
- **Quote discipline (critical).** Only genuine, public-domain direct quotations,
  in `<blockquote>…<cite>Name</cite></blockquote>`. **Never invent a quote and
  attribute it to a real person.** When unsure, *describe* the author's teaching
  instead of quoting. Two confirmed examples in use: Hudson Taylor's "pressure"
  line, Spurgeon's "kiss the wave."

## The fixture

One file per article: `backend/library/fixtures/content/articles/<slug>.en.json`,
natural-key format (no pk), one `library.article` row. Fields: `slug`, `language`,
`h1` (warm headline), `meta_title` (SEO `<title>`; blank → h1), `description`
(meta + standfirst), `body_html` (rich profile), `related`, `source_url`,
`sort_order`, `is_published`, `created_at`, `updated_at`.

Build the file with a Python script (triple-quoted `body_html` → `json.dumps`) —
hand-escaping large HTML into JSON is error-prone. Body HTML uses the **rich/bio**
sanitize allowlist: `p h2 h3 blockquote em strong ul ol li a cite` (NOT the
chapter profile — it strips links/cite). Write Scripture refs as plain text
("Romans 8:28"): `ArticleDetailSerializer.get_body_html` runs
`annotate_references` on read, so every ref becomes a tappable `.scripture-ref`
that opens the verse popover on the article page — you get this for free, so
don't hand-wrap refs in the fixture.

## Gotchas (each cost time at least once)

- **`word_count` runs ~1.6× LOWER than your visual estimate.** A body that "feels"
  like 1600 words counts ~1000. Write much fuller than feels right, then verify —
  budget for one or two expansion passes.
- **Store the SETTLED form.** `clean_bio_html` round-trips HTML entities to unicode
  (`&mdash;`→—, `&rsquo;`→’), so a raw-entity body is not byte-stable. Run each
  body through `clean_bio_html` and write THAT, or the fixture drifts on deploy.
- **Curly quotes only.** `tests_fixture.QuoteStyleTests` fails a work that mixes
  straight and curly marks. Watch H2 headings and hand-typed edits — use `’ “ ”`
  (or `&rsquo; &ldquo; &rdquo;`, which settle to curly), never `' "`.
- **Verify every `related` slug resolves.** A dead ref is silently dropped, so the
  Read-next block just goes short. Seed locally and check the detail API returns
  the expected count.
- **Tag the new article to its topics.** Add its slug to the matching topic(s) in
  `TOPIC_ARTICLES` in `library/topic_seed.py` so it appears on the topic pages
  ("Articles about X") and shows topic chips — the bidirectional funnel. Topic
  slugs: prayer, holy-spirit, deeper-life, grace-and-comfort,
  revival-and-missions, faith-and-guidance, the-gospel-call, the-way-of-holiness.
  `seed_topics` upserts them.
- **Edit the builder's `body_html` with HTML only.** When expanding a
  triple-quoted `body_html` string, the replacement text must be plain HTML —
  never paste `"""` or Python (`.replace(...)`) into it, or you close the string
  literal early and corrupt the file. Bit this three times in one session; run
  `python3 -c "import ast; ast.parse(open(f).read())"` after each builder edit.

## Verify + ship

```bash
# after generating: settle through clean_bio_html, then verify
DJANGO_DEBUG=true uv run python manage.py shell -c "..."   # word_count 1500–2000, 7+ refs, 0 straight quotes
DJANGO_DEBUG=true uv run python manage.py seed_articles     # then hit the detail API: related resolves N/N
DJANGO_DEBUG=true uv run python manage.py test library.tests_fixture library.tests_sanitize library.tests_articles
```

Ship as a **content-only PR** (just the fixture files). The article fixtures live
under `library/fixtures/content` (a declared content root), so a deploy reseeds
the API (`seed_articles`) AND rebuilds the web service, and the two self-order
(the web build waits on the API digest). No frontend change needed — the
`/articles` routes already prerender. Follow `founder-kit:deploy` and verify the
live page with the trailing slash (`/articles/<slug>/`) — a no-slash URL is the
SPA shell that 200s forever.

## Batching

Parallel article fixtures never collide (one file per work). But `main` moves
fast: expect a migration merge-leaf conflict if another session's PR added one
(`makemigrations --merge`), and ship batches sequentially off an updated `main`
so a held batch doesn't restack the same conflict.
