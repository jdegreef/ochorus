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

- **Wikidata** (`wikidata`, added 2026-09-29 for Corrie ten Boom's Ruisdael *View
  of Haarlem*) — the escape hatch for a painting none of the three hold (the Dutch
  Golden Age is mostly in Amsterdam/The Hague/Haarlem, whose APIs key by strings).
  `object_id` = the number after the item's Q. The fetcher requires P6216 = public
  domain on the item AND a PD/CC0 file on Commons, and credits the item's English
  label, P170 creator label and P571 year — copy those verbatim (a label like "View
  of bleaching fields and Haarlem" is what the credit says, not the museum title).
  Find the item from the Commons file page's "Edit this at Wikidata" link.

**LOOK before you pick.** Both search APIs return junk mixed with gems, so
download the small images, montage them into a contact sheet, and Read it — then
mock the actual cover (3:4 crop + scrim + white title) so you judge the COVER,
not the painting. Exclude religious/portrait subjects, prefer landscape /
architecture / sky / water / path. **One facet/subject per book, a different
painter each**, so an author's shelf reads as one without N identical scenes.
Verify every finalist's PD flag before building. **Grep the object id before building**
(`grep -n '<object_id>' backend/library/curated_art.py`): 128+ paintings are
taken, and `test_no_painting_is_given_to_two_works` only fires at the END of
`paint_covers`, after the plate is deleted and the twins redrawn (Heade's *Point
Judith* for Pensées was already Amanda Smith's, 2026-09-28). **Reject a scan with its
frame baked in** (a gilt strip along an edge — Met Frère *Jerusalem*, 2026-09-28):
nothing crops it and `covers:bars` only measures DARK bars, so it ships on the cover.
**Copy the artist and year strings verbatim from the collection** —
`build_curated_covers` refuses a mismatch ("the manifest's year is not the
collection's": `c. 1643–45` ≠ `c. 1643–c. 1645`; `Joos de Momper II` ≠ `…, II`).
Record it in
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
22 on PATH. **Run `npm ci` in the worktree — don't symlink the shared checkout's
`node_modules`**: it lags `main`'s deps and `og:covers` dies `ENOENT … @fontsource/…`
(Batch 17, 2026-09-27).

**Read THIS file from `origin/main`** (`git show origin/main:.claude/skills/level-up-cover/SKILL.md`)
if you loaded it from the shared checkout — that copy is a stale detached HEAD and
still describes the old hand-run pipeline, not `paint_covers.py`.

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
- **A NEW painting, or swapping an ALREADY-curated one, also needs `npm run covers:bars`** —
  `paint_covers` doesn't run it, and `groundBars.test.ts` fails ("groundBars.ts is
  stale"; Sohlberg's letterboxed scan hit it on #4209). Run it BEFORE `og:covers`: a laid-out cover crops past the measured scan
  bar, so twins drawn with the old ground's bar are mis-cropped. Order slipped? `rm`
  those slugs' twin PNGs and re-run `og:covers`.
- **One painting, one work — now a gate.** `test_no_painting_is_given_to_two_works`
  fails a `(source, object_id)` already in `CURATED`/`CURATED_GROUND`. Before a pick,
  `grep -n '<object id>' backend/library/curated_art.py`; searches return used works
  (the Met hands back replaced ones too). #1771 re-used `till-he-come`'s Achenbach on
  the same author's shelf and it stood for weeks until the gate (Spurgeon, 2026-09-26).
- **"AIC is down/throttled" may be curl, not AIC.** The search URL's
  `query[term][is_public_domain]=true` has square brackets, which curl treats as a
  glob and silently mangles — the response is empty and `json.load` dies. Use
  `curl -g` (or `--globoff`). Cost a whole sourcing detour (Praying Hyde, 2026-09-29).
- **A new book needs no plate first.** `paint_covers <slug>` on a freshly written
  fixture with `cover_url: ""` fetches, crops, repoints and draws the twin directly.
- **A numbered SERIES spanning eras needs a `BOOK_STYLE` pin.** The face comes from
  the author's birth-year era, so volume 2 of *Portraits of Courage* (Hyde, b.1865 →
  `revival`) would not match volume 1 (Nee, b.1903 → `house`). Pin later volumes to
  volume 1's face in `coverStyles.BOOK_STYLE` (#4501).
- **The Met API 403s after a few dozen object fetches in a burst.** Throttle (~1/s) or
  switch to AIC (`api.artic.edu/api/v1/artworks/search?q=…&fields=id,title,
  artist_title,date_display,image_id,is_public_domain,classification_title`; IIIF image
  at `www.artic.edu/iiif/2/<image_id>/full/1686,/0/default.jpg` with a `Referer:
  https://www.artic.edu/` header).
- **`wash` fades the UPPER half of the ground into paper** (95% paper to ~30%, 78% at
  55%). A pale or misty painting goes near-blank (Murray's `divine-healing`,
  `waiting-on-god`), and a subject in the upper half is lost (the snow peaks on
  `holy-in-christ`'s Courbet; its chalet carries the cover). For a wash author, pick
  strongly coloured paintings whose subject sits in the LOWER half; else suggest `fade`.
- **`band` shows only the vertical MIDDLE ~44% of the ground** (a strip at y≈28–72% of
  the 3:4 crop). A subject at the top or foot is cropped out — `cheque-book`'s rainbow
  is. For a band author, preview `ground.crop((0, 223, 600, 577))` before picking.
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
  (the local dev DB is a subset). `paint_covers` step 1 only runs `seed_if_empty`,
  which SKIPS a copied (non-empty) DB — symptom: `<slug>: no Book rows, skipping`,
  then step 4 dies "wears a shared ground but has none" AFTER step 3 already deleted
  the plates. Run `seed_books` first; the re-run is safe (#4244, 2026-09-27).
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

- **EPUB-bundled covers must follow a repaint** (since #4261, 2026-09-28).
  `backend/library/export_covers/<slug>.<lang>.png` is a byte-exact copy of the
  og twin `covers/<slug>.png` for every EXPORTABLE edition (83 English classics),
  and `tests_book_export.CoverTests` fails when one is stale. After `og:covers`,
  check `ls backend/library/export_covers | grep <slug>`. For each hit, copy the
  new twin over it (or run `manage.py export_book <slug>`, whose `_bundle_cover`
  does exactly that). A cover PR racing an export PR hits the same test: whichever
  lands second refreshes the copies.

- **A LIGHT ground must pass every EDITION, not just English** (Brave for God
  poster, 2026-09-28). The tuner and the contrast gate measure fixed English-position
  bands (`INK_REGIONS`, subtitle y519–543). Translated titles and subtitles wrap
  longer: on Brave for God, lg/sw subtitles reached y595, and 20 of 26 editions put
  white text on pale snow, sand or sea (Swahili book 4 was unreadable) while every
  gate stayed green. The old dark grounds hid this. Before shipping a light ground,
  compose EVERY `<slug>.<lang>` edition (real `cover_title || title`, subtitle,
  script fonts) and measure its real rows at the tuner's scrim. Then keep the band
  where any edition's words can land a rich mid-tone, and put the bright elements
  above the title or below the lowest subtitle, clear of the mark box.

## Original illustrated grounds (Ochorus Originals — kids/teens) — SHIPPED tier

PD-painting sourcing (steps 1–2 above) does NOT apply to **Ochorus Originals**
(Brave for God series, Growing in Wisdom, teen/CYT flagships): there is no museum
painting, so `build_curated_covers` (Met/AIC fetch + `isPublicDomain` re-verify) is
the wrong intake. The ground is an **original wordless illustration** we draw.

**The tier: `ORIGINAL_GROUND`** (shipped PR #2877, 2026-09-18 — the FOURTH
shared-ground tier). An original ground is un-redrawable (no museum to re-fetch, no
designed cover to crop), so it is **frozen by SHA-256 like a designed cover** — but
NOT in `designed_covers.DESIGNED` (that registry is for *worded* rasters a row wears,
and `covers/art/` is exempt from its digest gate). It lives in
`curated_art.ORIGINAL_GROUND: dict[str, Original]` where `Original(sha256, why)`. Do
NOT put it in `CURATED` — that would make the museum-provenance table lie
(`credit()` returns None for originals). Wiring, once:
- `covers.shares_a_ground` → add `or slug in ORIGINAL_GROUND` (the ONE predicate;
  `generate_covers`/`build_cover_assets`/`localize_covers` all route through it).
  `keeps_english_designed` stays FALSE (English wears the art too, like `CURATED`).
- `localize_covers` tier-label ladder → add the `"original"` case.
- Gates in `tests_fixture.py`: `test_original_grounds_are_frozen` (digest freeze);
  `test_every_art_file_belongs_to_a_tier` (orphan gate — uses `shares_a_ground`, so
  it auto-covers new tiers); extend `test_curated_editions_share_one_painting` to
  `set(CURATED) | set(ORIGINAL_GROUND)`; add the 3 `ORIGINAL_GROUND` pairs to the
  disjointness gate. `tests_fixture`+`tests_covers` = 121 pass.

**Ship steps** (per slug, after the ground jpg is drawn): register it in
`ORIGINAL_GROUND` with its `shasum -a 256` → delete plate svgs
(`find covers -regex '.*/<slug>\.svg' -delete`, incl `lg/ sw/`) → `build_cover_assets.py`
(repoints EVERY lang row + webp) → `npm run og:covers` → `tune_art_scrim.py` →
`npm run og:covers` again (redraws the cards whose scrim moved). Same
tail as steps 2–3. `growing-in-wisdom` + teen flagships are next, same tier, no new
machinery.

**DESIGN GOTCHA — white type needs a DARK ground where the type falls.** `BookCover`
draws the title/byline/mark in WHITE over a measured scrim, ALWAYS (there is no
dark-ink variant). The ink bands on the 600×800 ground are byline y102–130, **title
y284–463 (the vertical MIDDLE)**, subtitle y519–543, mark y664–747 — so a bright sky
or a big centred sun in the title band kills legibility. Draw a **deep/twilight sky
with the sun-or-moon glow LOW at the horizon (~y470)**; keep the mark zone over dark
foreground. `tune_art_scrim` measures the WORST pixel per band, floors at 0.30× and
caps at 1.00× — CSS `opacity` clamps there, so the old 2.0× cap tuned scrims no page
drew (a too-pale ground fails as "unusable" — recrop/darken). Since 2026-09-29 the
bands are these fixed strips PLUS every framed edition's real line boxes, which
`og:covers` records as `rows` in `og-manifest.json` — so a translation whose title
wraps longer (Brave for God lg/sw subtitles at y539–595) is measured where it lands;
that is why `og:covers` must run BEFORE the tuner. Six known-thin paintings wait on
the founder in `covers.THIN_AT_FULL_SCRIM` (a ratchet: the gate fails if one is fixed
and not removed). Brave landed
0.65–0.80×. Verify by reading the composed og twin `covers/<slug>.png` (the real
render), or composite `covers.scrimmed(ground, strength, subtitle=True)` + white text
at the ink bands for a faithful preview before shipping.

**COMPOSITION RULES the ink bands impose (both bit growing-in-wisdom twice):**
(a) A foreground SUBJECT (hero, figure, tree) must sit ENTIRELY BELOW the title band —
keep its top at ≥ ~y470 (title bottom is 463), or the title text collides with it. So a
subject can only occupy the lower third; the drama in the upper 2/3 must come from the
SKY (deep gradient, dawn, mountains, stars), not a tall element.
(b) For a book WITH a subtitle, a horizon glow (the Editorial look) spills into the
subtitle band (y519–543) and fails its 4.5:1 bar. Raise the dark foreground ridge so
its TOP EDGE stays ABOVE y519 across the full width (glow only above it), which also
crops a ridge-cresting figure to head+shoulders against the light — the intended
"lone figure on the ridge" read. Measure all four bands (byline 4.5 / title 3.0 /
subtitle 4.5 / mark 3.0) on the rendered jpg before compositing the preview.

Two **audience design systems** for the Originals shelf (founder-approved 2026-09-18):
**Young Readers "Storybook"** (single-scene, one child hero lower-third, deep sky for
the white title, per-book palette+backdrop swap across a series with one shared frame —
shipped for Brave for God #2877) and **For Teens "Editorial"** (dark night→dawn,
starfield, distant mountains, a lone figure cresting a ridge toward a single dawn light
— shipped for growing-in-wisdom #2905). Both grounds stay wordless — `BookCover`
sets the type per language, so one ground translates. The vector route below is the
shipped production path.

**The two systems differ ONLY in artwork — the TYPE is identical.** `BookCover` draws
the same white house serif at the same fixed positions for EVERY art cover (kids or
teen); there is no per-book/per-audience type engine, so the locked Editorial prompt's
"bold bottom-anchored title" is NOT achievable — the title always sits mid-cover
(y284–463). The audience read comes from the ground alone (warm storybook scene vs dark
cinematic one). Don't promise a different type treatment.

**Reproducible vector-render recipe** (no image model needed; perfect series
consistency): author the scene as an inline-SVG HTML at 600×800, render with headless
Chrome, downscale with Pillow:
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
  --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --window-size=600,800 --screenshot=out@2x.png "file://$PWD/ground.html"
python3 -c "from PIL import Image; Image.open('out@2x.png').convert('RGB').resize((600,800),Image.LANCZOS).save('ground.jpg',quality=90)"
```
No cairosvg/rsvg/inkscape on this machine; Pillow + Chrome are present. Chrome CLI
`--screenshot` is fine on a STATIC local file (the memory-noted hang is Vite-HMR-only).
For a numbered series, hold hero/trail/frame/type CONSTANT and drive each book from a
`palette` dict + ONE horizon-backdrop SVG string (Brave for God: dawn hills → sea+boat
→ dusk mountains → forest) — that structure IS the series-consistency guarantee. Then
render every cover into a Pillow grid montage and LOOK before shipping (same discipline
as the Met "montage+mock+LOOK" gate): a set that doesn't read as one on the shelf is the
failure to catch here, not any single cover.

**Measure the ROWS THE WORDS REALLY FALL IN, not only the tuner's bands.** A
series layout (`young`, `originals`) sets type from the top with a volume ring,
so the subtitle can sit at y448–564 rather than 519–543. Rooted and the East
African pair (2026-09-28) passed the tuner but needed checking where the words
actually landed: A Hidden Fire's sparks cleared the fixed subtitle band while
failing the real subtitle row (2.9:1) until the fire was scaled 1.8× rather
than 2×. Render the composed og twin and measure its text rows.
**Check every edition's `cover_title`.** An edition with none sets its FULL
title on the cover. The Amharic Rooted rows had none, so "ሥር የሰደደ – … – መጽሐፍ 4"
ran up into the tree. The fix is the title's own first segment, as ar/hi do.
Shipped so far on this tier: Brave for God 1–4 (#2877), growing-in-wisdom
(#2905), Rooted 1–6 (first a soil cutaway, #4295; REPLACED 2026-09-28 by a watercolour
growing tree chosen from 10 concepts) + A Hidden Fire + Tukutendereza ("fires on the
hills"), Sons/Daughters of the King 1–3 (2026-09-28, "silhouettes done right",
chosen from 7 concepts). With these, no published book wears a plate.

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
Murray (2026-09-26; `school-of-prayer` plate → Français olives, 9 langs; `holy-in-christ`
Van Gogh → Courbet so his two 1889 cypress Van Goghs no longer pair; wash/sage kept),
Spurgeon (2026-09-26; `spurgeon-on-prayer` de-duplicated → Turner, AIC; Morning/Evening
plates → an Inness pair, AIC; band/oxblood kept),
Moody (2026-09-25; Kensett ×2 — `prevailing-prayer` re-picked from a Rubens,
`thoughts-for-the-quiet-hour` from its plate; layout duotone/indigo → wash/ochre),
Athanasius #2409 (2 — Huguet/Cole; also OPENED the `aic` source, see §1),
Wesley #2414 (2 — Constable/Inness), Hudson Taylor #2416 (2 — Chen Hongshou ink/Gifford),
Simpson #2419 (2 — Church/Daubigny, +lg/sw). Batch 16 #2891 (2 — both AIC):
Carmichael `things-as-they-are` (Church, *View of Cotopaxi* — the tropical source
the deferred note wanted; `focus=0.6` puts the dark valley in the title band, not
the sun) + Susanna Wesley `susanna-wesley-clarke` (Hobbema watermill). Batch 17 #4209
(2026-09-27, AIC — the "New to the Library" classics): Fox's (Ruisdael, Egmond
ruins), Finney memoirs (Gifford, Catskills sunset), Müller of Bristol (Sohlberg,
*Fisherman's Cottage* — a lit house in dark pines). Batch 18 #4244 (Bosworth — Bierstadt;
Wigglesworth — R. Wilson). Batch 19 (2026-09-28): Hurlbut (Vernet *Morning*), Cyprian
(Linton *Carthage*), Crowther (Fromentin *On the Nile* — the deferral lifted), Watts
*Divine Songs* (Cuyp, +lg/sw), Pilgrim's Progress one-syllable (Momper, +lg/sw), Meyer
*Our Daily Walk* (Dupré *On the Road*). That clears every non-Original plate. IN FLIGHT:
Church Fathers (5 — Rosa/Corot/Lane/H.Robert/Panini), African-American
autobiographies (4 — Heade/Chase/Inness/Duncanson).
Remaining (pre-Batch-19 note): the Puritan/English devotional group
(Owen, Sibbes, Law, Edwards, Meyer, Guyon, Bounds straggler). Carmichael's
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
