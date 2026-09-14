---
name: sermon-questions
description: Write answered "study questions" for Ochorus sermon pages and ship them as a content fixture. Use when asked to add study/reflection questions to sermons, generate the sermon-questions pilot or a batch, or scale them across the sermon library. Four answered questions per sermon, question-shaped for search and answered STRICTLY from the sermon's own text, stored in the sermon fixture and rendered as a "Questions for reflection" section plus FAQPage JSON-LD. Authored by the agent (NOT an API-key command). This is a living playbook — append new gotchas as we find them.
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

## Verify, then ship

- JSON valid across the touched fixtures; run `tests_fixture`, `tests_sanitize`,
  `tests_sermon_payload` (all green). Rendering is proven by #2330 — identical data
  shape, no need to re-verify the browser for a pure content batch.
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
