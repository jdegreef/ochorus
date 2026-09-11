---
name: og-cards
description: Generate or regenerate Ochorus Open Graph share cards — the 1200×630 PNGs a forwarded link shows — for sermons, topics and browse pages. Use when adding a share card for a new content type, when an og-manifest / ShareCard gate fails, when a card looks stale or wrong, or when `npm run og:*` won't render (fonts). Living playbook — append failure modes as we hit them.
---

# Ochorus Open Graph share cards

A forwarded link is how this library spreads, so the `og:image` is the one
surface where missing or stale art actually costs readers. Every card is a
1200×630 PNG, committed as a static asset and pointed at by the leaf page's
`<Seo ogImage>`.

## The family — one ground, per-type generators

All landscape cards share **`frontend/scripts/og-card.mjs`** (the ground,
palette, faces and `drawCard`/`renderCard`), so a forwarded Ochorus link is
recognisable whatever it points at. Generators (`frontend/scripts/`, hand-run,
output committed — NOT in CI):

| Command | Draws | Content source | Accent |
|---|---|---|---|
| `npm run og:sermons` | `/og/sermons/<slug>.png` | sermon JSON fixtures | derived `emblemHue` |
| `npm run og:topics` | `/og/topics/<slug>.png` | `topic_seed.py` (via export, below) | **curated** `TOPIC_META.accent`, `liftToContrast`-ed |
| `npm run og:pages` | `/og/<page>.png` (7 fixed) | hardcoded `CARDS` | brand gold |

**Book covers are NOT part of this family.** `og:covers`
(`generate-cover-og.mjs`) screenshots `BookCover` with **Playwright/Chromium** —
it does not import `og-card.mjs` and is unaffected by font/ground changes here.

## Fonts are vendored in-repo — `npm run og:*` runs on any OS

satori needs a real TTF. The faces (Liberation 2.1.5, SIL OFL) live at
**`frontend/scripts/fonts/`** and `og-card.mjs` resolves them relative to
itself. Before 2026-09 this was a hardcoded `/usr/share/fonts/...` Linux path,
so generation was impossible on macOS (can't write `/usr/share` under SIP) and
editing the path cascaded (below). Vendored → deterministic everywhere. If you
ever swap the faces, the render bytes change and every card regenerates.

## Editing `og-card.mjs` cascades — know the blast radius

Its bytes are in the **composition digest** gated by BOTH
`sermonCards.test.ts` and `topicCards.test.ts`. So *any* edit to it (even a
comment) stales those manifests → you must re-run `og:sermons` **and**
`og:topics` and commit. The generators byte-compare and only rewrite a PNG when
the render actually changed, and vendored Liberation 2.1.5 renders
byte-identically — so in practice only each manifest's `composition` hash moves,
not 93 sermon PNGs. `og:pages` uses `og-card.mjs` too but is **not**
composition-gated (no manifest); `og:covers` doesn't use it at all.

## The topic content bridge (why og:topics shells to Python)

Sermon content is JSON fixtures the Node generator reads directly. **Topic**
title/description/scripture live in `backend/library/topic_seed.py`, and the
generator has no Django or DB. So `generate-topic-og.mjs` spawns
**`backend/scripts/export_topic_cards.py`**, which prints that content as JSON.
`topic_seed.py` is a pure, side-effect-free data module, so the exporter uses
the Django-free-script pattern — `sys.path.insert(0, BACKEND)` +
`from library.topic_seed import TOPICS, TOPIC_SCRIPTURE` (the same way
`library/covers.py` reads it), not an AST parse. The accent + emblem come from
the TS catalogue (`emblemNames`/`emblems`), read directly.

## The gate pattern — two-sided, mirror it for any new card type

Each card type ships an `og-manifest.json` of INPUT digests, split by who can
recompute them:

- **content** — the strings off the fixture/seed. Recomputed in Python
  (`SermonShareCardTests` / `TopicShareCardTests` in `tests_fixture.py`), the
  side that can read them. Also asserts a PNG exists per item.
- **art** — the emblem, its drawing, and the accent. Recomputed in vitest
  (`sermonCards.test.ts` / `topicCards.test.ts`), which can read the TS catalogue.
- **composition** — the bytes of the generator + `og-card.mjs`. In the vitest
  side. This is the half that catches a *design* change nobody redrew for.

Existence alone is not enough — a retitled item keeps shipping its old card
(the bug that bit the book twins for months). After ANY change, re-run the
generator to refresh the manifest, and commit PNGs + manifest together.

## Gotchas

- **satori: a `<div>` with children needs an explicit `display`.** A childless
  or empty node throws "Expected <div> to have explicit display…". Build
  children arrays with `.filter(Boolean)` and drop absent lines (e.g. a topic
  with no scripture) rather than emitting an empty box.
- **English only, one card per slug.** A translated page shares the English
  card; the leaf page points `og:image` unconditionally at `/og/<type>/<slug>.png`.
- **Requirements:** Node ≥ 22.18 (unprompted TS type-stripping) and, for topics,
  `python3` on PATH. `satori` + `@resvg/resvg-js` are devDependencies (`npm install`).

## Ledger

- sermons, pages: pre-existing. **topics: shipped** (per-topic cards replacing
  the one generic `/og/topics.png`; PR — branch `topic-og-images`). Fonts
  vendored in the same change.
