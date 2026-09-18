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

Two collections, and **prefer the Art Institute of Chicago for landscapes**. The
Met's `?q=` search is visually blind — it ranks a landscape query by popularity
and buries actual landscapes under famous figure paintings (a "Frederic Edwin
Church" query returned Vermeer and El Greco). The **Art Institute of Chicago**
(`aic` source, added #2409) has a real search engine and CC0 images, and finds
the picture:

- **AIC** — `https://api.artic.edu/api/v1/artworks/search?q=<term>&fields=id,title,artist_title,is_public_domain,image_id,classification_title&query[term][is_public_domain]=true`.
  Filter `classification_title` contains `painting`. The IIIF pixels
  (`https://www.artic.edu/iiif/2/<image_id>/full/1686,/0/default.jpg`) 403 unless
  you send `Referer: https://www.artic.edu/` — that header, not a policy, is the
  whole reason AIC was long thought unusable (`build_curated_covers` now carries
  it via `REFERERS`). `image_id` is a UUID, NOT the object id. **AIC throttles a
  session that hammers its IIIF host** — after a few pools of contact-sheet
  downloads every fetch 403s for a while (even with the Referer), and backoff
  doesn't clear it fast. When that happens, switch to Cleveland (below) rather
  than waiting it out; download smalls with delays and reuse cached files.
- **Cleveland** (`cma`) — the clean fallback and, when AIC is throttling, the
  better first stop. `https://openaccess-api.clevelandart.org/api/artworks/?q=<term>&cc0=1&type=Painting&has_image=1&limit=20`
  is a real search with a `type=Painting` filter; images are on
  `openaccess-cdn.clevelandart.org` with NO hotlink protection (direct download,
  no Referer). Object `id` = the API path id = the `object_id` you record. Used
  for Wesley (Constable, Inness) when AIC blocked mid-batch. British/European
  landscapes are well represented (Constable, Gainsborough, Wilson, Turner).
- **Met** (`met`) — search by SUBJECT word (`?q=<subject>&hasImages=true`), fetch
  each object, filter `isPublicDomain && classification=="Paintings" &&
  primaryImage`. Still fine when you know the subject noun; weak for "find me a
  good landscape". See memory `met-api-pd-art-sourcing`.

**LOOK before you pick.** Both search APIs return junk mixed with gems, so
download the small images, montage them into a contact sheet, and Read it — then
mock the actual cover (3:4 crop + scrim + white title) so you judge the COVER,
not the painting. Exclude religious/portrait subjects, prefer landscape /
architecture / sky / water / path. **One facet/subject per book, a different
painter each**, so an author's shelf reads as one without N identical scenes.
Verify every finalist's PD flag before building. Record it in
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

## 2. Build — one command

With the `CURATED` entries written, everything else is mechanical:

```bash
cd backend && DJANGO_DEBUG=true uv run python scripts/paint_covers.py <slug…>
```

It runs the pipeline in its load-bearing order and stops at the first failure:
clear `__pycache__` (gotcha A) → `migrate` (gotcha B) → `build_curated_covers`
(fetch, crop, re-verify PD) → **delete every retired plate** `<slug>.svg` in every
language dir (gotcha E) → `build_cover_assets` (webp variants, and repoints
**every** edition row's `cover_url`, surgically) → `tune_art_scrim` → `og:covers`
(scrim first — a twin is drawn with it) → **restore any twin redrawn outside your
works** → the cover gates. `--dry-run` prints the plan; `--no-check` skips the
gates. It refuses a slug not in `CURATED`, and a dirty `static/covers` (it has to
tell your changes from the generator's noise). Needs `frontend/node_modules` and
Node 22 on PATH.

`cover_url` is **NOT create-only** in `seed_books` (`CREATE_ONLY_FIELDS =
{source_type, is_published}`), so the fixture edit reaches prod on deploy — **no
data migration.** Verify covers by reading the og twin PNGs (`covers/<slug>.png`)
— they are the composed cover. The whole system is mapped in `docs/covers.md`.

## 3. Scope-check, ship

Diff must be **only** this batch's slugs + `curated_art.py` + `art_scrim.py` +
`coverScrim.ts` + `og-manifest.json` (+ an `AUTHOR_STYLE` line if you added one).
**Never hand-edit `og-manifest.json`** — `coverOgManifest.test.ts` now fails an
entry that is out of order or duplicated (a hand-appended French card once was
both, and every later run re-sorted it into someone else's PR). If a twin is
missing, run `npm run og:covers`. Data-only diff → **skip** the
`/simplify`+`/code-review` pass. PR, then merge on green + deploy
(`founder-kit:deploy`), verifying API `cover_url` flips + web art serves +
prerendered pages reference it.

## Gotchas (each has bitten a run)

- **F · the og "ground" digest hashes the BYLINE, not just the painting** — it is
  `sha256(cover_bytes + "\0" + title + "\0" + subtitle + "\0" + author_name)`
  (`tests_fixture.test_every_twin_was_made_from_the_cover_it_stands_in_for`). So a
  change to a book's title/subtitle OR its author's display name makes that
  edition's twin STALE even though the painting is untouched — regenerate it (the
  file-missing trick: `rm covers/<slug>.png` then `npm run og:covers` redraws just
  the missing ones, no `--force`), and patch the manifest `ground` accordingly.
  A long author name also TRUNCATES the byline on the cover ("Frederick Brotherton
  Meyer" → "FREDERICK BROTHERTON M…"); rename to the publishing name. `name` is NOT
  seed-synced (author_sync syncs only `same_as`), so a rename is fixture
  authors.json + the `catalog.py` stub + a data migration, then regen the author's
  byline-drawn twins (#2443, F. B. Meyer). Designed rasters bake their own byline —
  a rename does not touch them.
- **A · `__pycache__` staleness** *(automated: `paint_covers` step 1)* — `build_curated_covers` reports "Not in the
  curated manifest" for slugs you just added to `CURATED`. Stale `.pyc`. Clear
  ALL of `backend/**/__pycache__` (a `find … -exec rm` in the *same* compound
  command doesn't reliably take — run it as its own step) then re-run.
- **B · worktree DB is stale** *(migrate is automated: step 2)* — `OperationalError: no such column …`. The copied
  `db.sqlite3` predates a migration on `main`. `manage.py migrate` first (memory
  `local-backend-dev-state-2026-09`). A fresh worktree also needs the seeded
  `db.sqlite3` + `.env` copied in and `manage.py seed_books` so the books exist
  (the local dev DB is a subset).
- **C · translation-race** — a parallel translation session adds a NEW per-language
  plate edition of a book you're CURATED-ing between your branch and merge; CI (which
  tests the merge) fails `test_curated_editions_share_one_painting`
  (`[(slug, es, /covers/es/<slug>.svg)] != []`). Fix: `git rebase origin/main`,
  re-run `paint_covers <slug>` (it deletes the new plate and repoints the row),
  amend, force-push. Do it FAST (branch→ship one session) and the window shrinks.
  (memory `cover-levelup-translation-race`.)
- **D · web-deploy stall** — during a migration-leaf deploy thrash the `ochorus-web`
  build queue starves; API flips `cover_url` but art files 404 site-wide (other
  sessions' frontend PRs also undeployed). Not your PR. It self-heals as the queue
  clears, else Render dashboard → ochorus-web → Deploy latest commit (user-only).
- **E · per-language plates** *(automated: `paint_covers` deletes every `<slug>.svg`
  in every dir, and `build_cover_assets` repoints every edition row)* — a translated
  plate book has `covers/<lang>/<slug>.svg` too, and each must go.
  The **plate files are the authoritative edition list**: `find frontend/static/covers
  -name "<slug>.svg"` (all dirs) BEFORE you build — a quick fixture-language scope can
  under-report (an `enchiridion.es` edition surfaced only via `es/enchiridion.svg`, and
  would otherwise have shipped still pointing at a deleted plate).

## Running the singles as a batched sweep
Too many single-plate authors to do per-book A/B/C. The method that works:
group them into **coherent sub-batches** (Church Fathers; African-American
autobiographies; Puritans/English devotional), curate **one** best pick per book,
mock them all, and present a **single grid** ("approve, or name any to swap") —
one PR per sub-batch (multi-author is fine here; the skill sanctions it). Two
principles that earned their place: **defer, don't mismatch** — Crowther's Niger
journal was held rather than wear a Dutch castle-river, because no African/tropical
source was reachable while AIC was throttling; and **painter-resonance** where it
honours the author — Duncanson (the pre-eminent Black American landscapist) for the
AME pioneers Lee and Allen. Each sub-batch stacks a new `curated_art` Batch; land
them in order and union-resolve the `curated_art`/scrim/manifest overlap on rebase.

## Done so far
Murray #1701 (5), Bounds #1745 (6), Nee #1768 (1), Spurgeon #1771 (4), Torrey #1858 (3),
Athanasius #2409 (2 — Huguet/Cole; also OPENED the `aic` source, see §1),
Wesley #2414 (2 — Constable/Inness), Hudson Taylor #2416 (2 — Chen Hongshou ink/Gifford),
Simpson #2419 (2 — Church/Daubigny, +lg/sw). IN FLIGHT: Church Fathers (5 —
Rosa/Corot/Lane/H.Robert/Panini), African-American autobiographies (4 —
Heade/Chase/Inness/Duncanson).
Remaining: Crowther (`journal-of-an-expedition-up-the-niger` — DEFERRED, wants an
AIC tropical/Church once AIC un-throttles) + the Puritan/English devotional group
(Owen, Sibbes, Law, Edwards, Meyer, Müller, Guyon, Bounds straggler, Carmichael
`things-as-they-are`). Carmichael's `if` and all four Watchman-Nee titles are
`is_published:false` — skip. Cyprian was on `feature/cyprian-treatises` — check
first. Susanna Wesley stays a generated cover on purpose (portrait trap).
