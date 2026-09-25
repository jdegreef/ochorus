---
name: level-up-cover
description: Level up a flat plate-covered book to a CURATED painted ground — choose a public-domain artwork per book, run `paint_covers`, and ship one PR per author. Use when asked to "do the covers" for an author, replace generated colour-plate covers with real art, add a book to the CURATED tier, or continue the plate → art level-up (author-by-author; ~35 plates remain after Murray/Bounds/Nee/Spurgeon/Torrey). Encodes the sourcing method and the gotchas that bite each run; the command order lives in `backend/scripts/paint_covers.py`. This is a living playbook — append new failure modes as we find them.
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
# unpublished teaching titles) and which languages each has (paint_covers repoints them all)
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

It runs every stage in its load-bearing order — the stages, and why the order
matters, are its docstring (`paint_covers.py --help`) — and stops at the first
failure. `--dry-run` prints the plan, including every plate it would delete;
`--no-check` skips the gates. A committed painting is kept while it was cut from
its entry; change the entry's artwork or `focus` and the next run redraws it
(`library/art_sources.py` records each painting's recipe, and a gate fails a
painting whose entry moved without one). `--recrop` redraws regardless. It refuses a slug not in
`CURATED`. If it reports twins redrawn **outside** your works, their inputs
really changed — look before committing. Needs `frontend/node_modules` and Node
22 on PATH.

`cover_url` is **NOT create-only** in `seed_books` (`CREATE_ONLY_FIELDS =
{source_type, is_published}`), so the fixture edit reaches prod on deploy — **no
data migration.** Verify covers by reading the og twin PNGs (`covers/<slug>.png`)
— they are the composed cover. The whole system is mapped in `docs/covers.md`.

## 3. Scope-check, ship

Diff must be **only** this batch's slugs + `curated_art.py` + `art_sources.py`
(build_curated_covers records each painting's `crop_recipe` here — expected, not
stray) + `art_scrim.py` + `coverScrim.ts` + `og-manifest.json` (+ an
`AUTHOR_STYLE` line if you added one).
**Never hand-edit `og-manifest.json`** — `coverOgManifest.test.ts` now fails an
entry that is out of order or duplicated (a hand-appended French card once was
both, and every later run re-sorted it into someone else's PR). If a twin is
missing, run `npm run og:covers`. Data-only diff → **skip** the
`/simplify`+`/code-review` pass. PR, then merge on green + deploy
(`founder-kit:deploy`), verifying API `cover_url` flips + web art serves +
prerendered pages reference it.

## Gotchas (each has bitten a run)

- **DERIVED grounds (translations of a DESIGNED cover) are tuned in
  `designed_covers.DERIVED_GROUND`, not here** (#3233, Gareth Evans). Knobs beyond
  the crop: `erase=(Erase(x0,y0,x1,y1,"dark"|"light"),…)` paints thin lettering out
  so a band can reach past a subtitle/URL/frame (strokes-only by default;
  `thin=False` for a hairline touching a bright shape); `foot=` lifts a low subject
  clear of the Ochorus mark (BookCover centres the title, mark at ~0.9 — a foot
  pushes the subject UP); `peak=` caps blown whites. **`tune_art_scrim` can answer
  >1.0 but `coverScrim.test.ts` forbids it** — gamma `lift` can't touch 255, so
  bring highlights down with `peak≈240`, re-draw, re-tune. Preview the REAL cover
  by cloning `scripts/generate-cover-og.mjs` into a scratch script that filters
  to your slugs and screenshots `coverPage()` to a dir (no API/dev server needed);
  delete it before committing.
- **A `cover-type.css`/font change makes `npm run og:covers` redraw EVERY twin**
  (the manifest's global `css`/`fonts` digests move) — ~350 PNGs of sub-1-level
  re-encode noise. Keep the manifest + your slugs' twins and `git checkout` the
  rest. A new `COVER_STYLE_IDS` recipe also needs a non-`.title` rule OUTSIDE the
  container gate (`coverComposition.test.ts`) and must not give the subtitle a face.

- **The `fonts` digest also moves with local `node_modules`** (a fontsource version
  differing from the last committer's), same symptom: every twin redrawn. Same cure —
  keep the manifest (its new `fonts` value, so the NEXT run doesn't repeat it) + your
  slugs' twins, `git checkout origin/main --` the rest. Confirm with a second plain
  `og:covers`: "wrote 0". (Moody, 2026-09-25.)
- **Swapping an ALREADY-curated painting also needs `npm run covers:bars`** —
  `paint_covers` doesn't run it, and `groundBars.test.ts` fails ("groundBars.ts is
  stale"). Run it BEFORE `og:covers`: a laid-out cover crops past the measured scan
  bar, so twins drawn with the old ground's bar are mis-cropped. Order slipped? `rm`
  those slugs' twin PNGs and re-run `og:covers`.
- **Met image CDN needs a User-Agent**: `curl` without `-A "Mozilla/5.0"` on
  `images.metmuseum.org` saves a ~1.3 KB error body named `.jpg`.
- **A cover that looks bad may be the AUTHOR LAYOUT, not the art.** Check
  `coverLayouts.AUTHOR_LAYOUT` first: `duotone` (grayscale + 0.65 contrast + a 70%
  tint) turned Moody's two dark paintings into identical purple slabs (→ `wash`). And
  `wash` is the one layout that SHOWS the subtitle, so switching to it surfaces
  untranslated subtitles (Moody's ar edition carried English) — check every edition's
  `subtitle` (it is upserted, so a fixture fix reaches prod).
- **F · the og "ground" digest hashes the BYLINE, not just the painting** — it is
  `sha256(cover_bytes + "\0" + title + "\0" + subtitle + "\0" + author_name)`
  (`tests_fixture.test_every_twin_was_made_from_the_cover_it_stands_in_for`). So a
  change to a book's title/subtitle OR its author's display name makes that
  edition's twin STALE even though the painting is untouched — regenerate it (the
  file-missing trick: `rm covers/<slug>.png` then `npm run og:covers` redraws just
  the missing ones, no `--force`, and rewrites their manifest entries).
  A long author name also TRUNCATES the byline on the cover ("Frederick Brotherton
  Meyer" → "FREDERICK BROTHERTON M…"); rename to the publishing name. `name` is NOT
  seed-synced (author_sync syncs only `same_as`), so a rename is fixture
  authors.json + the `catalog.py` stub + a data migration, then regen the author's
  byline-drawn twins (#2443, F. B. Meyer). Designed rasters bake their own byline —
  a rename does not touch them.
- **A · "Not in the curated manifest"** for slugs you just added to `CURATED`.
  First suspect the checkout, not Python: an edit made in one tree (the Dropbox
  copy, another worktree) and a command run in another looks exactly like this.
  Python recompiles a `.pyc` whenever its source changes size or mtime, so a
  stale bytecode cache is the unlikely cause; clearing `backend/**/__pycache__`
  is harmless if you want to rule it out. `paint_covers` checks `CURATED` before
  it runs anything, so it fails fast here either way.
- **B · worktree DB is stale** *(migrate is automated: `paint_covers` step 1)* — `OperationalError: no such column …`. The copied
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
  plate book has `covers/<lang>/<slug>.svg` too, and each must go. The **plate
  files are the authoritative edition list** — a quick fixture-language scope can
  under-report (an `enchiridion.es` edition surfaced only via `es/enchiridion.svg`),
  which is why `paint_covers` finds plates on disk rather than from the fixtures;
  `--dry-run` lists every one it would delete.
- **G · relanding a long-parked batch — it's probably already superseded.** A cover
  batch PR left open for weeks against fast-moving `main` is very likely NOT real
  work to land: parallel sessions re-curate the same books under newer, authoritative
  paintings, and #2481-style follow-ups ship the machinery in a better form. Do NOT
  trust a `git merge-tree` "N non-manifest changes" count — it diffs the branch's
  STALE merge-base and reads regeneration-vs-live-covers as new work. Verify per-slug
  against CURRENT `origin/main`: `git show origin/main:backend/library/curated_art.py
  | grep '"<slug>": Artwork'` and check the fixture `cover_url` already points at
  `/covers/art/<slug>.jpg`. Whatever `main` has is authoritative — never regenerate
  over it. What's genuinely un-landed is only the slugs `main` lacks AND that are
  `is_published:true` AND not under a documented deferral (a `curated_art.py` batch
  note or this skill's "Done so far" saying a book "waits for AIC" / "stays generated
  on purpose"). If nothing survives that filter, close the PR as superseded rather
  than rebase it. (PR #2482, curated-art-batch-3, closed superseded 2026-09-18: 14/21
  already live, 5 `is_published:false`, the last 2 deferred.)

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
Moody (2026-09-25; Kensett ×2 — `prevailing-prayer` re-picked from a Rubens,
`thoughts-for-the-quiet-hour` from its plate; layout duotone/indigo → wash/ochre),
Athanasius #2409 (2 — Huguet/Cole; also OPENED the `aic` source, see §1),
Wesley #2414 (2 — Constable/Inness), Hudson Taylor #2416 (2 — Chen Hongshou ink/Gifford),
Simpson #2419 (2 — Church/Daubigny, +lg/sw). Batch 16 #2891 (2 — both AIC):
Carmichael `things-as-they-are` (Church, *View of Cotopaxi* — the tropical source
the deferred note wanted; `focus=0.6` puts the dark valley in the title band, not
the sun) + Susanna Wesley `susanna-wesley-clarke` (Hobbema watermill). IN FLIGHT:
Church Fathers (5 — Rosa/Corot/Lane/H.Robert/Panini), African-American
autobiographies (4 — Heade/Chase/Inness/Duncanson).
Remaining: Crowther (`journal-of-an-expedition-up-the-niger` — DEFERRED, wants an
AIC tropical/Church once AIC un-throttles) + the Puritan/English devotional group
(Owen, Sibbes, Law, Edwards, Meyer, Müller, Guyon, Bounds straggler). Carmichael's
`if` and all four Watchman-Nee titles are `is_published:false` — skip. Cyprian was
on `feature/cyprian-treatises` — check first.

**REVERSING A "deliberately absent" book** (Susanna Wesley, #2891): a book can be
documented in the `curated_art.py` docstring AND guarded by a test as
intentionally plate-only. Susanna's reason was portrait-specific (every candidate
was a period portrait of a different real woman → reads as a likeness of her). A
**biography gets a landscape, never a portrait** — a wordless landscape retires
that objection. To reverse: update the docstring note AND the enforcing test in
`tests_covers.py` (there `test_susanna_wesley_has_no_artwork_on_purpose` asserted
her ABSENCE — repurposed to guard the KIND of art: present + `"portrait"` not in
its title). Get the founder's go-ahead before overriding a documented decision.
