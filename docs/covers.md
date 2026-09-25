# Covers — the map

How a book's cover gets onto the shelf, into a share preview and into search.
This page is the map; the detail lives in the docstrings it points at, which are
thorough and stay authoritative. Read this first, then the file you are about to
change.

**Doing a task?** Paint a plate-covered book → [`level-up-cover`](../.claude/skills/level-up-cover/SKILL.md)
(choose the art) then `backend/scripts/paint_covers.py` (everything else).
Topic emblems → [`topic-emblems`](../.claude/skills/topic-emblems/SKILL.md).
Sermon/topic/page share cards → [`og-cards`](../.claude/skills/og-cards/SKILL.md).

---

## 1. The idea in one paragraph

A cover is a **ground** with **type** over it. The ground is a committed image
that carries no words — a museum painting, a crop of a photograph, or a flat
colour plate with a topic emblem. The type — byline, title, subtitle, series
numeral, ornament — is drawn by the browser in `BookCover.svelte`, per edition,
in a face chosen for the author's century. That split is why one painting can
serve eight languages, why an Arabic title is shaped as Arabic, and why a cover
can be set in a webfont at all. The one exception is the **designed** cover: a
hand-made raster with its words already in its pixels, which nothing may redraw.

## 2. The four tiers

`cover_url` on each edition row says which tier it wears.

| Tier | `cover_url` | Words in the file? | Serves | Registry |
|---|---|---|---|---|
| **Designed** | `/covers/<slug>.jpg\|png` | yes | English only | `designed_covers.DESIGNED` (frozen, by digest) |
| **Shared ground** | `/covers/art/<slug>.jpg` | no | every language it names | one of three tables, below |
| **Plate** | `/covers/<slug>.svg` (per-language copies under `/covers/<lang>/`) | no | its edition | none — drawn from `cover_color` + topic emblem |
| *(none yet)* | `""` | — | — | admin import before its ground is drawn; `BookCover` paints a CSS plate |

A **shared ground** comes from one of three places — `covers.shares_a_ground()`
is the single test for all three:

| Table | What the file is | English wears | Written by |
|---|---|---|---|
| `curated_art.CURATED` | a museum painting (Met / Cleveland / Art Institute) | the painting | `manage.py build_curated_covers` |
| `designed_covers.DERIVED_GROUND` | a crop of the English designed cover's photograph | its designed cover | `scripts/build_derived_grounds.py` |
| `curated_art.CURATED_GROUND` | a museum painting, for works whose designed cover had nothing croppable | its designed cover | `manage.py build_curated_covers` |

**Two rules the gates enforce:** a hand-made cover is frozen (`DESIGNED` records
each file's SHA-256; replacing one on purpose is a two-line diff), and a
translated edition never wears another edition's words (it wears a wordless
ground, or its own plate).

## 3. The type

Drawn once, in two renderers kept identical by a parity test:
`BookCover.svelte` (the app) and `coverCardMarkup.ts` (the share-twin script).
The look is `components/cover-type.css`; *which* look is `coverStyles.ts`.

| Decides | Where | Keyed by |
|---|---|---|
| house style (face, ornament, arrangement) | `BOOK_STYLE` → `AUTHOR_STYLE` → `ERA_STYLE` in `coverStyles.ts` | book, then author, then century |
| the words set as the title — `cover_title` when a book has one ("Rooted"), else `title`; cover-only, the aria-label and every other surface keep `title` | `coverTitle.ts`, used by both renderers; `build_rooted.COVER_TITLE` for the house devotional series | book edition |
| series numeral over the title | `series_position` on the Book row (fixture), set by `volumeNumeral` in `coverStyles.ts` | book edition |
| script corrections (Arabic, Devanagari, Cyrillic) | `COVER_SCRIPTS` + the `.script-*` blocks in `cover-type.css` | the edition's language, via `Intl.Locale` |
| scrim under the type on a painting | `art_scrim.py` / `coverScrim.ts` | work — **measured**, by `tune_art_scrim.py` |
| layout and hue of a painting (band, box, split, fade, diagonal, duotone, wash, rail; default framed) | `AUTHOR_LAYOUT` in `coverLayouts.ts`; the `.cover-layout-*` / `.cover-hue-*` blocks in `cover-type.css` | author |
| topic emblem on a plate | `backend/library/data/emblems/topics.json` | the book's first topic |

A **layout** replaces the framed composition on a painting only: paper panels
drawn over the ground carry dark ink, so a layout needs no scrim. It is chosen
per author, so an author's books look alike; an author not in `AUTHOR_LAYOUT`
stays framed. Changing one redraws their twins — run `npm run og:covers`.

The eight styles: `inscriptional`, `devotional`, `press`, `enlightenment`,
`revival`, `house` (by century); `originals` (Ochorus' own imprint);
`young` (the For Young Readers shelf, by book).

## 4. What each cover becomes outside the page

| Output | Where | Made by | When |
|---|---|---|---|
| webp variants (320 / 640) | beside each raster | `scripts/build_cover_assets.py` | by hand; committed |
| **og twin** — the cover with its type, rasterised | `/covers/<slug>.png`, `/covers/<lang>/<slug>.png` | `npm run og:covers` (Chromium) | by hand; committed; `og-manifest.json` records its inputs |
| **landscape share card**, 1200×630 | `/og/covers/<lang>/<slug>.jpg` | `scripts/build-share-cards.mjs` (`postbuild`) | **every build**; never committed |
| image-sitemap entry | `sitemap-books.xml` | `lib/sitemap.ts` | every build |

The rule for "which raster stands for this edition" is one function,
`coverArt.shareImage()`: a designed cover is itself; a plate or painting is its
twin; no cover is nothing. `shareCard()` wraps it for link previews. A book page
sends the landscape card as `og:image` and the cover as `Book.image`.

## 5. Tools and the order they run in

The level-up of a plate to a painting — the common job — is one command after
the art is chosen:

```bash
cd backend && DJANGO_DEBUG=true uv run python scripts/paint_covers.py <slug> [<slug> …]
```

Its stages and their order are its docstring (`--help`). **The order is
load-bearing:** the scrim must be measured before the twins are drawn with it,
and the retired plates must be gone before `build_cover_assets`, which refuses to
run past a leftover one. A committed painting is kept while it was cut from its
current entry (`library/art_sources.py` records what each was cut from); change
the entry's artwork or `focus` and it is redrawn.

The other tools, for jobs `paint_covers` does not cover:

| Tool | Job |
|---|---|
| `scripts/build_derived_grounds.py` | cut a translation ground from a designed cover |
| `scripts/localize_covers.py` | give translated editions their own cover (plate or shared ground) |
| `manage.py generate_covers` | draw plate grounds into the DB (admin imports) |
| `npm run covers:bars` | re-measure the scan borders a laid-out painting is cropped past (`groundBars.ts`); after a ground is added or redrawn |
| `scripts/build_portrait_assets.py` | author portraits and their variants |
| `npm run emblem:art`, `emblem:hues` | emblem drawings and accents (see `topic-emblems`) |

## 6. The gates, and what each one is protecting

| Gate | Fails when |
|---|---|
| `tests_fixture` — designed covers | a designed file's bytes changed, or a new one is unregistered |
| `tests_fixture` — shared grounds | a curated edition doesn't point at its painting; a painting is missing; a plate was left behind; a painting wasn't cut from its current entry |
| `tests_fixture` — per-language | a translated edition wears another language's file |
| `tests_fixture` — twins | an edition that needs a twin has none, or its twin was drawn from an older cover or title |
| `coverOgManifest.test.ts` | twins drawn with an older stylesheet, markup, style or series number; the manifest is **out of order or has a duplicate entry** |
| `coverMarkupParity.test.ts` | the app and the share-twin script would draw different trees |
| `coverLayouts.test.ts` | a layout or hue has no CSS (or CSS names one the table doesn't), a laid-out author has no painting in English, a railed title is too long for the rail, or a hue's paper/ink/band drops below contrast |
| `groundBars.test.ts` | `groundBars.ts` no longer matches the grounds on disk (run `npm run covers:bars`) |
| `coverStyles.test.ts` | a style has no CSS, names a face nothing loads, asks a face for a weight it lacks, or the young-readers table drifts from the shelf |
| `coverArt.test.ts` | a published edition's share source is missing, or twin/landscape sizes drift |
| e2e `smoke.spec.ts` | the built site doesn't serve a book's landscape card as a JPEG |

**The manifest is generated** — don't hand-edit `og-manifest.json`. If a
translation needs a twin, run `npm run og:covers`; it redraws only what changed.

## 7. Known sharp edges

- **A redrawn twin means its inputs moved.** The generator skips a twin whose
  recorded inputs are unchanged, so if a run redraws one outside your works,
  something about it really changed — don't restore its old bytes, which would
  leave the manifest vouching for a picture it no longer describes.
  `paint_covers` lists any such twins.
- **A twin digests the byline.** Renaming an author or retitling a book makes
  that edition's twin stale though the painting is untouched.
- **Translation races.** A new translation of a work you are painting can land
  between your branch and merge; CI then fails the shared-ground gate for the new
  language. Rebase, re-run `paint_covers` for the work, push.
- **The landscape card is built, not committed.** It exists only in `build/`;
  in `npm run dev` its URL 404s, which is expected.
