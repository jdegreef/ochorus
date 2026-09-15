---
name: level-up-cover
description: Level up a flat plate-covered book to a CURATED painted ground — pick a public-domain artwork per book, run the cover pipeline, repoint fixtures, and ship one PR per author. Use when asked to "do the covers" for an author, replace generated colour-plate covers with real art, add a book to the CURATED tier, or continue the plate → art level-up (author-by-author; ~35 plates remain after Murray/Bounds/Nee/Spurgeon/Torrey). Encodes the exact command order, the sourcing method, and the gotchas that bite each run. This is a living playbook — append new failure modes as we find them.
---

# Levelling up a plate cover to CURATED art

A plate-covered book (`cover_url` = `/covers/<slug>.svg`) is a flat colour ground
with a topic emblem — the shelf's "unfinished" look. Levelling it up means giving
it a **wordless public-domain painting** under the `CURATED` tier, over which
`BookCover` draws the per-language title. One painting serves every language.

**Do it author-by-author, one PR per author.** `revival`/`house`/`devotional` etc.
are the *type* recipe (`coverStyles.ts`), unchanged unless the author's era default
is wrong for their register (a closet-prayer writer in the missionary era → add
`devotional` to `AUTHOR_STYLE`, as Bounds/Murray/Meyer/Smith/Carmichael).

## 0. Scope the author

```bash
# which of the author's books are PUBLISHED plates? (skip is_published:false — e.g. Nee's
# unpublished teaching titles) and which languages each has (repoint ALL of them)
python3 -c "..."   # read backend/library/fixtures/content/books/<slug>.<lang>.json fields
```
Confirm `is_published`, `cover_url` (`.svg` = plate), `subtitle`, `langs`, author
`birth_year` (→ era → recipe). Only published plate books get levelled.

## 1. Source the art (the sourcing method that actually works)

Met Open Access API. See memory `met-api-pd-art-sourcing`: **search by SUBJECT
word** (`?q=<subject>&hasImages=true`) — `artistOrCulture`, artist-name, and
`departmentId`/`medium` params all return nothing or 403. Then fetch each object
and filter `isPublicDomain && classification=="Paintings" && primaryImage`, exclude
religious/portrait subjects, prefer Western landscape/architecture (a Chinese
landscape for a Chinese subject is right — Nee). **One facet/subject per book**, a
different painter each, so an author's shelf reads as one without N identical
scenes. Verify every finalist's PD flag before building. Record it in
`backend/library/curated_art.py` `CURATED` with a one-line rationale + per-work
`focus` (0–1 crop bias along the overflowing axis; tall hanging scrolls → ~0.3).

**On "public domain" here (founder steer, 2026-09-15): be reasonable, not
rigid.** Cover grounds don't have to be strictly PD — freely-licensed (CC0/CC BY)
or plainly reuse-intended art is fine too. The Met Open-Access `isPublicDomain`
filter stays the default only because it's the easiest *reliable* pipeline (and
`build_curated_covers` re-verifies that flag), not because PD is the sole
acceptable licence. If you pull a ground from another free source, record its
licence + source in the `CURATED` rationale; skip only the genuinely
risky (commercial/stock/watermarked, or actively policed).

## 2. Build (exact order — from `backend/`, `DJANGO_DEBUG=true uv run python …`)

```bash
find . -name __pycache__ -type d -exec rm -rf {} + ; find . -name '*.pyc' -delete   # GOTCHA A
uv run python manage.py migrate                                                     # GOTCHA B
uv run python manage.py build_curated_covers <slug…>        # writes covers/art/<slug>.jpg, re-verifies PD
# delete EVERY orphaned plate svg, incl per-language (es/, lg/, sw/…):
#   find frontend/static/covers -name "<slug>.svg" -delete   (build_cover_assets HARD-FAILS if left)
uv run python scripts/build_cover_assets.py                 # webp variants; also repoints DB cover_url
# repoint the fixtures (the shipped truth) — cover_url for EVERY language row → /covers/art/<slug>.jpg
#   textual one-field edit (content_fixtures.persist_field shape); build_cover_assets often already did it
( cd ../frontend && npm run og:covers )                     # composed og twins (needs node_modules symlink)
uv run python scripts/tune_art_scrim.py                     # measured scrim so white type clears AA
```

`cover_url` is **NOT create-only** in `seed_books` (`CREATE_ONLY_FIELDS =
{source_type, is_published}`), so the fixture edit reaches prod on deploy — **no
data migration.** Verify covers by reading the og twin PNGs (`covers/<slug>.png`)
— they are the composed cover.

## 3. Scope-clean, gate, ship

```bash
# og:covers deterministically re-touches a few ALREADY-SHIPPED twins of other books
# (pre-existing manifest drift, non-deterministic PNG bytes). Revert them — the gate
# hashes manifest INPUT digests, not PNG bytes, so it stays green:
git checkout origin/main -- <non-target covers/*.png>
uv run python manage.py test library.tests_fixture library.tests_covers   # 111 must pass
```
Diff must be **only** this author's slugs + `curated_art.py` + `art_scrim.py` +
`coverScrim.ts` + `og-manifest.json` (+ the `AUTHOR_STYLE` line if you added one).
Data-only diff → **skip** the `/simplify`+`/code-review` pass. PR, then merge on
green + deploy (`founder-kit:deploy`), verifying API `cover_url` flips + web art
serves + prerendered pages reference it.

## Gotchas (each has bitten a run)

- **A · `__pycache__` staleness** — `build_curated_covers` reports "Not in the
  curated manifest" for slugs you just added to `CURATED`. Stale `.pyc`. Clear
  ALL of `backend/**/__pycache__` (a `find … -exec rm` in the *same* compound
  command doesn't reliably take — run it as its own step) then re-run.
- **B · worktree DB is stale** — `OperationalError: no such column …`. The copied
  `db.sqlite3` predates a migration on `main`. `manage.py migrate` first (memory
  `local-backend-dev-state-2026-09`). A fresh worktree also needs the seeded
  `db.sqlite3` + `.env` copied in and `manage.py seed_books` so the books exist
  (the local dev DB is a subset).
- **C · translation-race** — a parallel translation session adds a NEW per-language
  plate edition of a book you're CURATED-ing between your branch and merge; CI (which
  tests the merge) fails `test_curated_editions_share_one_painting`
  (`[(slug, es, /covers/es/<slug>.svg)] != []`). Fix: `git rebase origin/main`,
  repoint the new lang's `cover_url`, delete its plate svg, `npm run og:covers`,
  amend, force-push. Do it FAST (branch→ship one session) and the window shrinks.
  (memory `cover-levelup-translation-race`.)
- **D · web-deploy stall** — during a migration-leaf deploy thrash the `ochorus-web`
  build queue starves; API flips `cover_url` but art files 404 site-wide (other
  sessions' frontend PRs also undeployed). Not your PR. It self-heals as the queue
  clears, else Render dashboard → ochorus-web → Deploy latest commit (user-only).
- **E · per-language plates** — a translated plate book has `covers/<lang>/<slug>.svg`
  too; delete ALL of them or `build_cover_assets` fails, and repoint every `<slug>.<lang>.json`.

## Done so far
Murray #1701 (5), Bounds #1745 (6), Nee #1768 (1), Spurgeon #1771 (4), Torrey #1858 (3).
Remaining plates ~35: a few 2-plate authors (Simpson, Carmichael, Wesley, Athanasius,
Hudson Taylor, Originals) + ~19 single-plate authors (best as one batched sweep).
