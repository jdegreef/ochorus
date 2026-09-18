---
name: write-article
description: Write a devotional/theological SEO article for the Ochorus Articles section (footer-linked, /articles) and ship it as a content fixture. Use when asked to write an article, add to the Articles section, or produce SEO content that funnels readers into the library. Each article is 1500–2000 words, has 7+ Scriptures, is attributed to Ochorus the house (a byline + schema author, never an individual person), and ends with a "Read next" funnel of real books/sermons/bios. This is a living playbook — append new gotchas as we find them.
---

# Writing an Ochorus article

Articles are original site writing — the SEO layer that answers the questions
people search ("how to trust God", "what does it mean to abide in Christ") and
funnels them into the library via a **Read next** block. They live at `/articles`
(footer, not header) and are per-language rows like books (English only for now).
Model + API + frontend shipped in PRs #1395/#1396; the design brief is
`docs/articles.pdf`. See also [[write-biography]] (the nearest sibling) and the
`articles-section` memory.

**Attribution — the house, never a person.** An article has no per-article author
FK by design: it is original *site* writing, not a work by an individual. But the
house name **Ochorus** is surfaced as the byline and as the JSON-LD `author`
(Organization "Ochorus", mirroring the existing `publisher`), for reader trust and
E-E-A-T — and the kind eyebrow reads `Article · Ochorus · <time>`, matching the
sermon eyebrow's `KIND · … · TIME` shape (shipped `98f31dd8`, branch
`seo/article-ochorus-author`). `datePublished`/`dateModified` are unchanged. So:
attribute to Ochorus the organization, **never** invent or imply an individual
author (that is also why person-lives stay out of `/articles` — see below).

Everything below assumes a worktree off `origin/main` and `backend/` with
`DJANGO_DEBUG=true uv run`.

## No biographies in /articles (a person's life story goes on the author page)

A biography of a person — a "who was X" / person-and-theme life story — belongs
in the **biography section**, on that person's **author page** (`/authors/<slug>`,
written with [[write-biography]]), **never as an article**. Articles are about
*topics, questions, and works* (what is grace, how to pray, a guide to a book),
not about *people's lives*. Eight biography-articles were once written this way
and had to be retired (PRs #1547/#1549) because they duplicated the author-page
bios and split search authority. If someone asks for an article about a person,
write or improve their author-page biography instead, and — if the topic
warrants an article — write it around the *theme* (e.g. "how to trust God for
provision"), funnelling to that author's page and works rather than retelling
their life. `tests_fixture.NoBiographyArticlesTests` locks out the retired slugs;
keep new person-lives out of `/articles` entirely.

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
- **Inline `<a>` links in the BODY to detail routes MUST end with a trailing
  slash** — `/books/<slug>/`, `/authors/<slug>/`, `/sermons/<slug>/`. A bare
  `/books/<slug>` fails the frontend built-output guard
  `href.test.ts > "contains no bare (non-slash) detail-route links"` and reds the
  whole `test-and-build` (the aggregator fails 3s after the frontend job). The
  `related` funnel is slashed for you by the API; hand-written prose links are
  not — writer agents forget (batch of 4, 2026-09-18: 5 bare links across 2
  guides). Grep the fixture: `grep -oE 'href=\"/(books|authors|sermons)/[^\"/]+\"'`.
- **A book guide is cross-linked FROM its book page — so `related` ORDER now
  matters.** `BookDetailSerializer.guides` (`library/serializers.guides_for_book`,
  PR #2843) surfaces a "Reader's guide" section on `/books/<slug>/` for the article
  whose slug ends **`-guide`** AND whose `related` **leads with that book** (the
  first `type:book` ref). So for a book guide: keep the `<book>-guide`-style slug,
  and make the guided book the **first** `related` entry — sibling works go after
  it. A guide that lists another book first will attach to the wrong book's page
  (or none); a non-`-guide` slug won't cross-link at all.
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
- **Verify the count with the function, not the model — `Article` has no
  `word_count` column.** It mirrors `Sermon` *minus* the derived columns, so
  `article.word_count` raises `AttributeError`. Count with
  `from library.text import word_count; word_count(settled_body)` (a pure regex
  split, no DB needed — runs off `clean_bio_html` output alone).
- **Don't use `<q>` for quotations — it's not in the allowlist and vanishes.**
  `clean_bio_html` silently strips `<q>…</q>`, leaving the quoted Scripture with
  NO marks at all. Write quotations with literal curly `“ ”` in the body (a
  direct-speech attribution still goes in `<blockquote><cite>`). If you compose
  with `<q>` for readability, convert `<q>`→`“` / `</q>`→`”` *before* settling.
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

- **Guide-style articles need a length-ADJUST pass either way — verify, don't eyeball.**
  A narrative-heavy guide (Pilgrim's Progress: plot walk-through + symbols) came
  out at 2,350 counted words and needed three trim rounds; expository guides in
  the same batch (Religious Affections, On the Incarnation) came out UNDER the
  1,500 floor and needed expansion. The variable is how much plot/quotation you
  carry. Budget one adjust pass in whichever direction the first `word_count` shows.
- **Quote only what is on the site, in the site's translation.** For a guide to a
  classic, the safe quotations are the ones you can find verbatim in the work's
  own fixture (`books/<slug>.en.json`) — the Ochorus *Imitation* is Croft–Bolton,
  the *Confessions* is Pusey, so a line remembered from another translation will
  not match the text the reader clicks through to. Grep the fixture first.
  **Then VERIFY every blockquote against the book fixture — but normalise
  punctuation first.** An exact-substring check throws false MISSes because the
  guide's curly quotes / em-dashes differ from the fixture's glyphs; strip both
  sides to letters-and-spaces only (`re.sub(r'[^a-z ]',' ',s.lower())`) before
  the membership test. A real MISS after that = an invented/misremembered quote;
  drop it. (Batch of 4 study guides, 2026-09-18: 4 of 14 blockquotes looked
  missing under exact match and were all genuine once punctuation was stripped.)
- **A study guide is a book guide with a study shape.** Same `<slug>-guide` slug
  + `related`-leads-with-the-book contract (above), but the `<h2>` sequence is:
  what it is → its argument/structure → central themes → **Who should read it** →
  How to read it today → **For reflection** (3–5 questions). Put "Summary" or
  "Study Guide" in `meta_title` for the search intent. Fan out one writer per
  book (unique scratch paths, no shared builder), then one central builder that
  settles each body through `clean_bio_html` and fails out-of-band on
  word_count, `<7` refs, any straight quote, or a `related` that doesn't lead
  with the book — see the Fan-out notes below.
- **Book guides have a home topic: `enduring-classics`.** Its blurb already names
  Augustine, Bunyan and à Kempis. Tag guides there AND to their doctrinal topic.
  Append new slugs at the END of each `TOPIC_ARTICLES` list — order is display
  order on the topic page.
- **`cd` inside a compound Bash command moves the shell for the rest of the
  session.** Run builders and `manage.py` with absolute paths or a leading
  `cd /abs/path/backend &&` every time; the "No module named django" that follows
  a stray `cd` is the cwd, not the venv.

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
