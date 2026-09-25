# Prerender refresh markers

A file here exists only to change something under `frontend/`, which makes
Render rebuild the static reader (`ochorus-web`). Nothing reads these files:
SvelteKit builds from `src/` and `static/`, Render publishes `build/`, and
ESLint skips `.txt`.

## You usually don't need one

A content PR (fixtures, `data/*_translations`, bio files, seed modules,
`corrections.py`, anything in `backend/library/content_sources.json`) already
rebuilds the reader through render.yaml's `buildFilter`. It also can't bake
the old content: `prebuild` runs `scripts/await-api-release.mjs`, which holds
the build until `/api/health/` reports this checkout's content digest. A
dated comment in a `+page.ts` adds nothing to that. It only made every pair of
parallel translation PRs conflict (2026-09-24).

## When you do

- The API started serving different prose **without** a content root
  changing, e.g. a seed-code change like #3237. Add the marker in a
  follow-up PR **after** that API deploy is live. In the same PR, the gate
  sees an unchanged digest and prerenders against the old API.
- You checked the raw prerendered HTML after a deploy (trailing-slash URL,
  `curl`, not the browser) and it's stale or the ~6 KB SPA shell.
- A web build failed and you need a rebuild but can't reach the Render
  dashboard or `manage.py bump_content_revision`.

## How

Add ONE new file. Never edit an existing one: a new file can't conflict with
another session's.

    frontend/prerender-refresh/<YYYY-MM-DD>-<slug>[-<lang>].txt

Put one line in it saying why, e.g. `#3237 synced existing chapters; rebake`.

**Pruning:** delete markers older than 30 days in the same commit. Deleting a
file can't conflict either, even if another PR deletes it too.
