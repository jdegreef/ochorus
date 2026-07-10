---
name: deploy
description: Ship Ochorus to production — push the branch, open/merge the PR, watch the Render deploy, and run post-deploy verification against the live site. Use when the user says to deploy, ship, release, merge to main, or "get this live", or when a PR is approved and ready to land. Encodes the Render deploy-ordering and build-skip gotchas. This is a living playbook — append new failure modes as we hit them.
---

# Deploying Ochorus

Merging `main` auto-deploys BOTH Render services from github.com/jdegreef/ochorus:
- **ochorus-api** (Docker, rootDir `backend/`) — runs `manage.py release`
  (migrate → seed_if_empty → backfill_body_text → seed_plans) as the
  preDeployCommand before the new version goes live.
- **ochorus-web** (static, rootDir `frontend/`) — `npm install && npm run build`.

Live URLs: https://ochorus-web.onrender.com · https://ochorus-api.onrender.com

## Pre-merge checklist

1. Working tree clean, branch pushed, PR open (`gh pr view --web` to eyeball).
2. Local gates pass:
   ```bash
   cd backend  && DJANGO_DEBUG=true uv run python manage.py test   # all OK
   cd frontend && npm run check && npm run build                    # 0 errors
   ```
3. If the frontend build/prerender calls a NEW backend endpoint, see
   "Deploy ordering" below **before** merging.

## Merge & watch

```bash
gh pr merge <N> --merge          # or --squash per user preference; ask if unsure
gh run list --limit 3            # not used by Render; watch via dashboard instead
```

Render has no CLI here — poll the live services instead:

```bash
# API is live when release finished and the new code is serving:
curl -s https://ochorus-api.onrender.com/api/health/
# WEB is live when the served entry-chunk hash CHANGES (NOT version.json):
curl -s https://ochorus-web.onrender.com/ | grep -o 'entry/app\.[A-Za-z0-9_-]*\.js'
```

Record the entry-chunk hash BEFORE merging so you can detect the flip.
A typical deploy takes ~5–10 min; poll every ~4 min.

## Deploy-ordering gotchas (each has bitten us)

1. **Frontend prerender needing a new backend endpoint**: both services deploy
   simultaneously; the web build can hit the OLD api and fail with a 404 →
   "Exited with status 1". A blueprint "Manual sync" does NOT retry a failed
   build ("Resources already up to date"). Fix: wait until the api is fully
   live, then Render → ochorus-web → **Manual Deploy → Deploy latest commit**.
2. **Backend-only commits freeze the static pages**: Render SKIPS the web build
   when nothing under `frontend/` changed, so prerendered `/books/<slug>` and
   `/authors/<slug>` pages keep serving stale data. If book DATA changed, also
   manually redeploy ochorus-web (Clear cache & deploy latest commit).
3. **render.yaml route changes** need a blueprint re-sync, or new pages fall
   back to the SPA shell.
4. `preDeployCommand` failures keep the old version live — check the Render
   deploy logs for the `release` output if the api hash never flips.
5. **Parallel PRs adding migrations → divergent leaves** (killed the PR #8
   deploy): another PR can land on main between your last fetch and your
   merge, adding a same-numbered migration; prod `migrate` then fails with
   "conflicting migrations / multiple leaf nodes" and the deploy dies in
   pre-deploy. Prevention: `git fetch && git log main..origin/main` right
   before merging, and re-check `ls backend/*/migrations/` for new numbers.
   Cure: `makemigrations --merge` (a merge migration) in a quick follow-up
   PR — see PR #12. The events page (dashboard → service → Events) shows
   which commit failed and which is live; the dashboard is the ONLY place
   deploy failures are visible (the old version keeps serving healthily).
6. Render's static host serves unknown extensions as binary/octet-stream —
   name web-served static files with known extensions (.json not
   .webmanifest; see PR #13).
7. **`launch.json` is a full `dumpdata` — a text-merge of two branches that both
   regenerated it produces DUPLICATE rows** (same `(book, order)` / same pk),
   which fails `SeedBooksTests` in CI with `UNIQUE constraint failed:
   library_chapter.book_id, library_chapter.order` (PR #41, 2026-07-10 — a
   parallel translation PR regenerated the fixture). A "clean" auto-merge with no
   conflict markers still corrupts it. Cure: DON'T hand-dedup — rebuild the
   fixture: `flush` → `loaddata` the base branch's version (`git show
   origin/main:backend/library/fixtures/launch.json > /tmp/main.json`) →
   re-run your import commands for the new/changed books → `dumpdata library
   --indent 1 -o library/fixtures/launch.json`. Verify zero duplicate
   `(book, order, language)` and zero duplicate `(model, pk)` before pushing.

## Post-deploy verification (adapt per feature shipped)

Always:
```bash
curl -s https://ochorus-api.onrender.com/api/health/                       # {"status":"ok"}
curl -s "https://ochorus-api.onrender.com/api/library/books/?language=en" | head -c 200
```

Feature-specific (2026-07 reader suite — keep pruning this list as features age):
```bash
# Full-text search on REAL Postgres (dev runs SQLite — this is its first exercise):
curl -s "https://ochorus-api.onrender.com/api/library/search/?q=prayer&language=en" | head -c 400
#   → ranked results, snippets containing ⟦…⟧ markers
# Reading plans seeded:
curl -s "https://ochorus-api.onrender.com/api/library/plans/?language=en"
# Reading sync requires auth:
curl -s -o /dev/null -w "%{http_code}" https://ochorus-api.onrender.com/api/reading/state/   # 401
# PWA served:
curl -s -I https://ochorus-web.onrender.com/service-worker.js | grep -i "200\|content-type"
curl -s -I https://ochorus-web.onrender.com/manifest.json | grep -i "200\|content-type"   # application/json
```

Then a quick browser pass on the live site (home, a chapter, search) if the
change was user-visible. Report the results to the user with the live URLs.

## Rollback

Render keeps previous deploys: dashboard → service → Deploys → Rollback.
For bad data migrations, write a reverse migration — never edit prod by hand.
