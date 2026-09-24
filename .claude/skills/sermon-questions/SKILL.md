---
name: sermon-questions
description: Write answered Questions & Answers for Ochorus content pages and ship them as a content fixture. Covers SERMON study questions (Sermon.study_questions, keys question/answer) and AUTHOR/BIO Q&A (Author.faq, keys q/a) — see the "Bios (author Q&A)" section for the different field, file, and serialization. Use when asked to add study/reflection questions or Q&A to sermons or author bios, generate a pilot or batch, or scale coverage. Question-shaped for search and answered STRICTLY from the work's own text; rendered as a Q&A section plus FAQPage JSON-LD. Authored by the agent (NOT an API-key command). Never call it "FAQ" in reader-facing prose. This is a living playbook — append new gotchas as we find them.
---

# Writing sermon study questions

Answered study questions turn a sermon page — otherwise the same public-domain
text a dozen other sites host — into unique content, and target the question-shaped
long tail ("what does this sermon say about X", "why does <author> argue Y"). The
model field, the reader's "Questions for reflection" section, and the `FAQPage`
JSON-LD all shipped in **#2330**; the generation approach and first batches in
**#2342**. See also [[write-article]], [[quote-extraction]], [[write-biography]]
(the sibling original-content skills) and the `dev-setup` playbook for the worktree.

## The one rule that decides everything: the agent writes these, not an API command

**Ochorus does not use the Anthropic API key for original content.** English
originals — biographies, articles, quotes, and these questions — are written by
**you, the agent, in-session**, exactly like [[write-article]] / [[write-biography]]
/ [[quote-extraction]]. Do NOT build or use a management command that calls
`anthropic.Anthropic()` for this (PR #2333 did, modelled on `translate_sermon`, and
it is a misfit — dev/prod have no key, so it can never run here). Read each sermon
and write its questions yourself.

## What to write

Per English sermon, **four answered questions**:

- **Question-shaped for search / study** — "What does this sermon say about…",
  "Why does the preacher argue…", "What does <name> mean by…" — never vague
  ("What can we learn?").
- **Answered strictly from the sermon's own content.** No invented doctrine,
  application, or fact the sermon does not make. An invented answer is worse than
  none — grounding is the whole reason ours beats the copies. Quote the sermon's
  own phrases where it helps.
- **1–3 plain-text sentences.** No HTML (rendered as escaped text — no sanitize
  path). Read the sermon in full first; don't skim.

## Where it lives (the mechanics)

- Field: `Sermon.study_questions` — a `JSONField`, a list of
  `{"question", "answer"}` objects, both plain text. Modelled on `summary`:
  AI-drafted off-server, shipped in the fixture, blank/empty = the reader shows
  nothing.
- It ships in the sermon fixture `backend/library/fixtures/content/sermons/<slug>.en.json`,
  inserted **right after `summary`**. It is **fixture-owned**: `seed_sermons` lists
  it in `SERMON_FIELDS` (not create-only), so it upserts from the fixture on every
  deploy. English only for now (per-language rows; a translated row simply omits it).
- **Write it with `library.content_fixtures.render_rows`** — the one byte-stable
  fixture writer (`indent=1, ensure_ascii=False`, one record at column 0). Never
  hand-format the JSON, and never dump the whole file with a different formatter
  (it reformats every line). Read the sermon's `body_text` (or strip `body_html`)
  straight from the fixture — no DB needed.

A tiny apply script per batch (insert-after-`summary` + `render_rows`) is the clean
tool; keep the questions in triple-quoted Python strings so the many `'`/`"` don't
need escaping. Two gotchas that cost a re-run each:

- **A `"""…"""` string may not END in a `"`.** A question like
  `"""…right...?""""` closes the triple-quote and leaves a dangling `"`
  (SyntaxError: unterminated string). If a question naturally ends on a quoted
  phrase, reword so the string ends on a letter/`?`/`.`, not `"`.
- **A long sermon's `body_text` can exceed the Read tool's ~25k-token cap.** Dump
  each sermon to its own scratch file (not one big file), and for the giants
  (Edwards' *Excellency of Christ*, Finney) split the body at a sentence boundary
  near the midpoint and read the halves — you must read the whole thing to ground
  the answers, so don't skim the tail.

## Rendering (already built, don't re-add)

`frontend/.../sermons/[slug]/+page.svelte` renders a "Questions for reflection"
`<dl>` and emits `FAQPage` JSON-LD via the shared `faqPage()` helper — both from the
one `study_questions` array, gated to `REVIEWED_UI_LOCALES` (`en/es/pt/fr`) so the
`sermon_questions_title` heading is never shown untranslated. Google restricted FAQ
*rich results* to authoritative sites in 2023, so the value is the unique content
and the clean entity signal, not a SERP accordion.

## Localizing the section heading (the shared `<QandA>` title)

The book/topic `<QandA>` `title` is a **catalogue key** (`qa_section_title`), NOT a
literal — set it with `t('qa.sectionTitle')`. Adding or changing a reader-facing UI
string is a fixed lifecycle, or `frontend/src/lib/messages.test.ts` fails the build:

1. Add the key to **all 9** `frontend/messages/*.json` (parity is enforced). The
   files are order-preserving-JSON: `json.dumps(obj, ensure_ascii=False, indent=2)
   + "\n"` round-trips them exactly, so load-modify-dump is byte-safe (a naive
   line-delete of a *trailing* key orphans a comma — reserialize instead).
2. Real translations for the reviewed locales **en/es/pt/fr**; the English source
   as a placeholder for **ar/hi/lg/sw/uk**, AND declare that key in
   `PENDING_TRANSLATION` (a two-way ratchet — an undeclared English placeholder
   fails, and so does leaving a now-translated key listed).
3. `npm run sync:catalogues` (the new placeholders join each locale's *pending*
   list in `backend/library/data/ui_catalogues.json`), then `npm run check` +
   `npm run test`.

A Q&A section only renders where per-row Q&A content exists for the locale, so an
English placeholder heading never actually reaches a reader. The admin readiness
report still counts it: each placeholder locale's Interface check is a
(forceable) FAIL until the key is translated.

## Editorial-only vs. a derived tier

Books ship **editorial-only** (founder decision): the book page shows only
hand-authored `book.qa` — `pickQa(editorialQa, [])`, no derived fallback. Topics
were always editorial-only. Only the **author** page keeps a two-tier
editorial-or-derived `faq`. Don't reintroduce a derived Q&A tier for books/topics.

## Verify, then ship

- JSON valid across the touched fixtures; run `tests_fixture`, `tests_sanitize`,
  `tests_sermon_payload` (all green). Rendering is proven by #2330 — identical data
  shape, no need to re-verify the browser for a pure content batch.
- **When the change touches BACKEND `.py` (any plumbing PR), also run
  `uv run ruff check library/` before pushing** — CI's "Backend — lint" job runs
  ruff and fails the whole run on a violation (an inline `import TOPICS, TOPIC_QA`
  that ruff wanted resorted to `TOPIC_QA, TOPICS` failed the first topic-PR run).
  The Django test command does NOT catch lint. Pure content-fixture batches skip
  this (no .py changed).
- It's a content-fixture change, so **ship via [[ship-content-fix]]**: the fixture
  edit moves the content digest, the prerendered pages rebuild, and `seed_sermons`
  upserts the field on deploy.
- CI: content-only PRs run `backend-tests` + `integration` and skip the Docker
  image and frontend-checks (the path filter from #2332).

## Batching

**The initial backfill is COMPLETE — all 93 English sermons have questions**
(finished 2026-09-14 across #2330/#2342/#2353/#2356/#2360/#2365). So this skill
now fires for the *maintenance* case: a newly-imported sermon that lacks
`study_questions`. List any such with
`grep -L study_questions backend/library/fixtures/content/sermons/*.en.json`
and author its four questions the same way. Only if a large new tranche arrives
does the batch cadence below apply again.

Batch cadence (for a fresh backlog): work in batches (pilot = 10, then 20s),
picking a spread across authors/eras so quality is judged broadly (the founder
reviews the diff before scaling). Read in sub-batches of ~5, author, write, verify.

**ONE PR PER BATCH — never keep pushing to a branch whose PR already merged.**
A squash-merge closes the PR and does NOT re-merge later pushes. #2342 was
squash-merged at its 10-sermon pilot state; the +20 and +10 that were then
pushed to the *same* branch went to a dead branch and never reached main — 30
sermons of authored questions sat stranded until a recovery PR (#2353) lifted
them off the closed branch and re-applied them onto main. The PR still showed
"MERGED" and accepted a retitle to "40 sermons", which masked the loss. So:
cut a fresh branch + PR for each batch, and if a batch's PR has merged, verify
main actually carries that batch (`git diff origin/main...HEAD`) before moving on.

**Count a batch against `origin/main...HEAD`, not the working tree.** #2330
shipped a few pilot examples straight to main, so those sermons already carry
`study_questions` on the branch — `grep -l study_questions .../sermons/*.en.json`
over-counts by exactly those. To state how many a PR *adds* (for the title/body),
count `git diff --name-only origin/main...HEAD -- .../sermons/` instead. (Once
reported the branch total 43 when the PR added 40.)

**Recovering stranded questions:** lift the `study_questions` array from the
closed branch (`git show <branch>:<path>`) and insert it after `summary` in
main's *current* file via `render_rows` — do NOT copy whole files over, or you
clobber any main-side body/summary edits made since the branch forked.

## Bios (author Q&A) — same idea, DIFFERENT mechanics

The unified Q&A rollout (`docs/questions-and-answers-plan.md`, doc in #2371)
extends this content type to **Bios, Books, and Topics**. Naming: always
**"Q&A" / "Questions and Answers", NEVER "FAQ"** in reader-facing / prose
contexts (founder rule) — the storage field is still literally `faq`, don't
rename it. Bios need **no plumbing** — everything already ships:

- **Field: `Author.faq` / `AuthorTranslation.faq`** — a `JSONField`, list of
  `{"q", "a"}` objects. **Keys are `q`/`a`, NOT `question`/`answer`** (sermons
  use the long keys — do not copy the sermon shape). Read `faq_for(language)`.
- **File: `authors.json`** (one shared file, not one-per-work), and it is
  **NOT written with `render_rows`.** authors.json is
  `json.dumps(rows, indent=2, ensure_ascii=False) + "\n"` — verified
  byte-identical; using `render_rows` reformats all ~5700 lines. (Confirmed by
  round-trip; the render_rows assumption was wrong.)
- **Deploy path:** `author_sync.SYNCED_FIELDS = ("same_as", "faq")` — fixture
  wins on EVERY deploy, but a row that OMITS the key is left untouched (the
  `field in fields` guard), so authoring `faq` deploys and authors without a set
  are never forced empty. No create-only concern.
- **Rendering (already built):** the author page renders `faq` as an accordion
  (editorial `author.faq` if ≥2 items, else a derived-from-page-facts fallback)
  and emits `FAQPage` JSON-LD via the shared `faqPage()` helper; nav chip
  "Questions". Do not re-add.

**House style:** ~9–10 items per author, answers ~500-char biographical prose
grounded STRICTLY in that author's own bio (dates, places, quotes, events) —
match the existing sets (andrew-murray is a good reference). Read the full bio
first.

**Authoring gotcha — the site-name test.** `tests_fixture.AuthorFaqShapeTests`
(`test_faq_entries_are_well_formed_plain_text`) fails if an answer contains the
string "ochorus" (case-insensitive), among other well-formedness/plain-text
checks. Bios routinely say "the volume Ochorus carries" — reword to name the
work instead (e.g. `In "The Secret of Guidance"…`). Run the same gate:
`tests_fixture tests_sanitize tests_sermon_payload`.

**Avoid the triple-quote gotcha entirely: use a JSON batch file, not Python
strings.** Author into `bio-batch-*.json` shaped `{slug: [[q, a], ...]}` (escape
internal `"` as `\"`), then apply with a tiny idempotent script that skips slugs
that already have a non-empty `faq` and writes with the exact
`json.dumps(indent=2, ensure_ascii=False)+"\n"` serialization. Verify the diff
is **additive** (`git diff --numstat` — expect ~N insertions, 1 benign deletion
from a `"same_as": []` gaining a trailing comma) and all 91 rows intact.

**Cadence:** 10 authors per PR (data-only, so skip the `/simplify`+`/code-review`
pass), then Books (a one-time plumbing PR first — Book has no Q&A field), then
Topics. Bio batch 1 = #2372 (coverage 29 → 39 of 91).

## Books (author-type Q&A on a per-language row) — needed PLUMBING

Books had NO Q&A field. The plumbing PR (mirrors sermon #2330) added:

- **`Book.qa` JSONField** (`default=list, blank=True`), items **`{question,
  answer}`** — the unified serializer-key contract new types adopt (NOT the
  legacy bio `q`/`a`). Book is per-language, so `qa` rides the row like
  `about_html`; no translation table, no `_for` accessor.
- **Serializer:** add `"qa"` to `BookDetailSerializer.Meta.fields` (plain field —
  list card omits it automatically).
- **seed_books:** add `"qa"` to `BOOK_FIELDS`, NOT to `CREATE_ONLY_FIELDS`, so it
  upserts from the fixture every deploy.
- **Migration:** `makemigrations library --name book_qa` (schema-only AddField;
  the data lives in the fixture, per backend/CLAUDE.md).
- **Frontend:** the book page ALREADY had a *derived* "Common questions" FAQ
  (hand-rolled JSON-LD). Made editorial `book.qa` the preferred tier with the
  derived set as fallback (`editorialQa.length >= 2 ? editorialQa : derivedFaq`),
  routed JSON-LD through the shared `faqPage()`, and extracted a shared
  **`$lib/components/QandA.svelte`** (visible `<dl>`; page owns the JSON-LD).
  Map stored `{question,answer}` → `{q,a}` for `faqPage()`, as the sermon page
  does. TS type: add `qa?` to `BookDetail` in `library-public.ts`.
- **Shape test:** `BookQaShapeTests` in `tests_fixture.py` mirrors
  `AuthorFaqShapeTests` but globs `BOOKS_DIR/*.json`, reads row-0's `qa`, and
  asserts `{question, answer}` keys (+ same 6–10 count / plain-text / no-site /
  no-URL guards). Also added `qa` payload+seed tests to `tests_about_work.py`.

**Byte-stability gotcha — book fixtures are NOT render_rows format.** Unlike
authors.json (`json.dumps indent=2`) and sermon files, book files carry **Django
serializer** formatting: `indent=1` nesting AND **per-file** unicode escaping
(some `\uXXXX`-escaped, some literal — mixed across the corpus). `render_rows`
(`ensure_ascii=False`) would reformat every non-ASCII char. So DON'T
load-modify-dump. Insert `qa` **textually**: build the block with
`json.dumps(qa, indent=1, ensure_ascii=<file has \\u ?>)`, re-indent +2 spaces to
the fields level, and splice it in right after the book row's `about_html` line.
Verify additive (`git diff --numstat` → N insertions, **0** deletions).

**Browser verification needs a BUILT preview, not `npm run dev`.** The dev CSP
`connect-src` has no localhost, so a book page that fetches
`http://localhost:8000` fails with "Something went wrong" in dev. The localhost
allowance is added only for a build, by `svelte.config.js` `directivesForThisBuild()`
reading **`process.env.PUBLIC_API_BASE_URL`** (from the shell env, NOT `.env`).
So: `PUBLIC_API_BASE_URL=http://localhost:8000 npm run build && … preview`.
**Never add localhost to `csp.config.js`** — `csp.test.ts` forbids `http://` and
`localhost` there. (Fastest sufficient proof is often the API curl +
`BookDetailSerializer` check + the passing check/unit gates; the visible `<dl>`
is extracted verbatim from the previously-shipping block.)

Then author Q&A (~8 per book), grounded in the book's `description` +
`about_html`; pick books whose `about_html` is non-empty (many are blank). Books
PR #1 = plumbing + 5 books (confessions, imitation-of-christ, the-bruised-reed,
the-reformed-pastor, all-of-grace).

## Topics (side-table Q&A, like authors) — needed PLUMBING

Topics are one base row + a `TopicTranslation` side-table (no per-language rows),
so Q&A rides BOTH, like author `faq`:

- **`Topic.qa` + `TopicTranslation.qa`** JSONFields (`default=list`), items
  `{question, answer}`. Add a **`qa_for(language)`** accessor — the list analogue
  of `description_for`. It CANNOT route through `Topic._localized` (that defaults
  to `""`; Q&A must default to `[]`), so write a dedicated method: English on the
  base row, the translated set for other langs, `[]` (not English) with no
  `fallback=True`.
- **Serializer:** `qa = SerializerMethodField()` + `get_qa` → `obj.qa_for(self._language())`, mirroring `get_scripture_ref` (TopicDetailSerializer).
- **Seeding:** topics have NO fixture — the English set is a `TOPIC_QA` dict in
  `library/topic_seed.py` (a declared content root, so edits trigger rebuilds; no
  content_sources.json change). `seed_topics` writes it into `Topic.qa` on create
  AND **refreshes it every deploy** (fixture-owned like the scripture epigraph —
  add `qa` to a `changed` list beside the scripture refresh, not create-only).
  Translated qa rides `TopicTranslation.qa` (English first; wire a translated-qa
  loader later).
- **Writing TOPIC_QA:** author into a JSON batch `{slug: [[q, a], ...]}`, then
  emit the Python literal with `json.dumps(obj, indent=4, ensure_ascii=False)` and
  append `TOPIC_QA = <that>` to `topic_seed.py` — valid Python (all strings), and
  it sidesteps the triple-quote gotcha. Verify it imports.
- **Frontend:** topic page imports the shared `pickQa` + `<QandA>`; topics have NO
  derived tier, so `pickQa(editorial, [])`. Add `qa.ld` to the `<Seo>`
  structuredData. TS type: `qa?` on `TopicDetail`.
- **Shape test:** `TopicQaShapeTests` reuses `assert_qa_wellformed` and also
  asserts each `TOPIC_QA` slug names a real topic in `TOPICS`. `qa_for`/serializer
  localization covered by `TopicQaTests` in `tests_topics_plans.py`.

**Stacked-PR pattern (important) — sibling content-type PRs share infra.** Book
and Topic BOTH introduce `QandA.svelte`, `pickQa` (seo.ts) and
`assert_qa_wellformed` (tests_fixture.py). Two branches off main would duplicate
them and collide. Instead **stack the second on the first**:
`git rebase --onto <first-branch> main <second-branch>` — identical add/adds
dedupe cleanly, so the stacked diff shows only the second type's own files.
Renumber the second's migration (`0144`→`0145`) to depend on the first's
`0144_*`, and open the PR with `--base <first-branch>` (GitHub auto-retargets to
main when the first merges). **Merge order: Book then Topic.** Topic PR #1 =
plumbing + 5 topics (prayer, the-puritans, the-east-african-revival, holy-spirit,
women-of-faith).
