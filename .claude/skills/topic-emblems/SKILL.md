---
name: topic-emblems
description: Give a topic (or plan) its own curated visual identity — a hand-drawn emblem + accent hue in TOPIC_META/PLAN_META — and regenerate the two derived artifacts the tests and the backend cover renderer depend on. Use when a topic/plan hero "looks flat" or falls back to the generic blue emblem, when adding emblems for uncurated topics, or when an emblem/emblemArt/emblemHues test fails. Living playbook — append failures and tick the ledger.
---

# Adding a topic/plan emblem + accent

Every topic and plan wears an `accent` hue + an `emblem` (a small 48×48
multicolour SVG). Curated ones live in `TOPIC_META` / `PLAN_META`
(`frontend/src/lib/emblemNames.ts`); the drawings live in `EMBLEM_ART`
(`frontend/src/lib/emblems.ts`). A slug **not** in the META table falls back to a
generic blue accent + a hash-picked emblem from `FALLBACK_POOL` — that is the
"flat hero" look.

## Rule 0 — accent and emblem are HARD-COUPLED

You cannot give a topic a curated accent without also giving it a **unique**
emblem. `emblems.test.ts` walks every `TOPIC_META`/`PLAN_META`/`SERMON_EMBLEMS`
entry and asserts (a) every emblem is unique across all three catalogues and
(b) a curated slug never wears a `FALLBACK_POOL` emblem. So "accents now,
emblems later" is not a thing — each curated topic needs its own drawing.

## Authoring an emblem (match the family)

- Inner markup for a **48×48** viewBox, `fill="none"` outer (see `Emblem.svelte`).
- Use **only the shared palette consts** at the top of `emblems.ts` (`${G}`,
  `${GR}`, `${R}`, `${CR}`, `${BRD}`, …) — not raw hex. They keep the set one family.
- **≥ 3 distinct colours** per emblem (`emblems.test.ts` enforces it) and
  **inert markup only** — no `<script|use|image|a>`, `href`, `on*`, `javascript:`.
- **Unique emblem name** across topics + plans + sermons; append to `EMBLEM_ART`.
- Keep compositions distinct — this catalogue leans heavily on light/fire/dawn
  motifs; vary the shapes so a shelf doesn't read as five sunrises.

## The regeneration pipeline (both, every time — or tests fail)

After editing `EMBLEM_ART` + `TOPIC_META`/`PLAN_META`, from `frontend/`:

```bash
npm run emblem:art     # writes backend/library/data/emblems/<name>.svg + topics.json
npm run emblem:hues    # writes src/lib/emblemHues.ts
```

- `emblem:art` exports the topic emblems as SVG files the **backend cover
  renderer `covers.py` reads** (the API image has rootDir `backend/` and cannot
  read `frontend/`). `emblemArt.test.ts` fails if the backend copies drift, and
  it asserts the backend dir holds **exactly** the topic-emblem set — no more, no
  fewer. Commit the new `.svg`s + `topics.json`.
- `emblem:hues` precomputes `EMBLEM_HUES` (the dominant ink of each drawing,
  used for sermon/share-card accents). `emblemHues.test.ts` fails on drift.

## Verify

```bash
# Node 25's built-in localStorage shadows jsdom's and breaks vitest (see dev-setup):
NODE_OPTIONS="--no-experimental-webstorage" npx vitest run \
  src/lib/emblems.test.ts src/lib/emblemArt.test.ts src/lib/emblemHues.test.ts
npx @inlang/paraglide-js compile --project ./project.inlang --outdir ./src/lib/paraglide && npm run check
```

Then look at the art. **The in-app browser cannot open `file://`** ("no open
project folder") — serve a scratch preview over a port instead:
`python3 -m http.server 8791` in the worktree, navigate to
`http://localhost:8791/<preview>.html`. Build the preview by inlining the palette
consts + the art strings into tinted chips (dark + light) so you judge it as it
appears on the hero. Do the full-app `/topics/<slug>/` hero pass once, when the
whole batch is in, before the PR (needs a seeded backend — `seed_topics`).

## Ledger — coverage

**All 30 topics are curated — none on the fallback.** Shipped in PR #2211
(branch `topic-emblems-accents`):

- Batch 1 (5): the-east-african-revival `dawn-over-hills`, the-puritans
  `candle-and-book`, to-the-ends-of-the-earth `mission-ship`,
  christ-and-the-cross `paschal-lamb`, women-of-faith `alabaster-jar`.
- Batch 2 (15): abiding-in-christ `grafted-branch`, voices-of-the-early-church
  `ichthys-fish`, day-by-day `sun-and-moon`, contemporary-voices `waymark`,
  the-inner-life `sheltered-lamp`, the-great-awakening `field-sunrise`,
  the-body-of-christ `loaf-and-cup`, for-those-who-lead `raised-lantern`,
  the-wesleys-and-early-methodism `warmed-heart`, foundations-of-the-faith
  `cornerstone`, saints-of-the-african-diaspora `river-sunrise`, the-grace-of-god
  `open-hands`, victory-over-sin `broken-chain`, faith-for-the-impossible
  `mountain-into-sea`, men-of-valour `sword-and-shield`.

**Next**: `PLAN_META` still carries only its original curated set — new/uncurated
plans fall back. Same recipe (`PLAN_META` + `planMeta`), but note `emblem:art`
exports **topic** emblems only, so a plan emblem needs no backend art export.
