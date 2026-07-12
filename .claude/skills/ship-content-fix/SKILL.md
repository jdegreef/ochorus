---
name: ship-content-fix
description: Ship a book/content data change to the LIVE Ochorus library the right way — data migration vs fixture refresh vs corrections.py, plus the static-page redeploy step. Use whenever chapter text, titles, book metadata, authors, or plans change in the database and the change must reach production — after a book import/repair, a title cleanup, a taxonomy edit, or any bulk content transform.
---

# Shipping content changes to the live library

**The core rule: production is NEVER re-seeded.** `seed_if_empty` only fills an
EMPTY database. A content change that only lands in the fixture will apply to
fresh installs but silently skip prod. Every live-data change needs an explicit
vehicle.

## Decision table

| Change | Vehicle |
|---|---|
| Transform of existing rows (title clean, text derivation, bulk fix) | **Data migration** (`migrations.RunPython`) — auto-runs on deploy via `manage.py release`. Import real helpers (e.g. `library.text.html_to_text`) so migration and `save()` derive identically. |
| Rows fixture loads can't populate (loaddata BYPASSES custom `save()`) | Data migration **plus** an idempotent release-step command for fresh DBs (pattern: `backfill_body_text`) |
| Per-book manual override that must survive re-imports | `library/corrections.py` (applied on every import) |
| Re-import / new book | `import_ochorus <slug>` locally → then this checklist |
| New seeded content (e.g. plans) | Idempotent `seed_*` command wired into `release` |

Never edit prod data by hand (Render shell `loaddata` is a last resort and
must be noted to the user).

## Checklist

1. Make the change locally (import fix / corrections.py / migration).
2. **Write the prod vehicle** per the table above. Test both paths locally:
   ```bash
   DJANGO_DEBUG=true uv run python manage.py migrate      # existing-DB path
   rm backend/db.sqlite3 && migrate && seed_if_empty && release-steps  # fresh-DB path
   ```
3. **Refresh the fixture** so fresh installs match prod:
   ```bash
   DJANGO_DEBUG=true uv run python manage.py dumpdata library -o library/fixtures/launch.json
   ```
4. Run `manage.py test` — content invariants live in library/tests.py.
5. Ship via the **deploy** skill, and remember its gotcha #2: a backend-only
   commit does NOT rebuild the static frontend, so prerendered
   `/books/<slug>` + `/authors/<slug>` pages keep the OLD data. Manually
   redeploy ochorus-web (Clear cache & deploy latest commit) after the api
   is live.
   **THE CONTENT-RACE (bites when the SAME PR changes a migration AND
   frontend):** both services autoDeploy in parallel, so the web build's
   PRERENDER can run BEFORE the api migration lands and bake the OLD data —
   even though the web DID rebuild (so it looks fine). Symptom: the API has the
   new value but the prerendered page still shows the old one (my portraits:
   `/biographies` baked 13, not 18). Fix is a SECOND rebuild AFTER the api is
   live: a one-line frontend touch (a dated comment on the relevant `+page.ts`)
   → merge → re-prerender. This recurs constantly — see the "Refresh … prerender
   (content-race)" PRs #50/#53/#58/#64. Client-side nav already shows the new
   data (the load re-fetches); only the prerendered initial HTML / SEO is stale.
6. Verify on prod: hit the changed item's API endpoint AND its prerendered
   page (check the CONTENT — grep the baked value, e.g. the portrait count or
   `photo_url` — not just status; the SPA catch-all serves 200 for everything).
   If the API is right but the page is stale, it's the content-race → do step 5's
   refresh, don't re-debug.

## Text-change etiquette

Fix extraction artifacts freely; NEVER rewrite an author's actual words
without the user's sign-off.
