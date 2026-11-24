# Building the reader without crawling the production API

**Status:** built and OFF. With `OCHORUS_BUILD_API` unset — as it is today —
the web build does exactly what it did before. This page is the design, what
the local API cannot know, and the steps to switch it on.

## Why

`ochorus-web` is a static site prerendered from the API. Its build fetches
every public page's data from `PUBLIC_API_BASE_URL`, which on Render is the live
`ochorus-api`: one 512 MB Starter instance serving the whole site in one burst
while it also serves readers. From 2026-11-16 to 11-19 that crawl kept
restarting the instance and every web deploy failed. The 11-19 mitigations
(`MALLOC_ARENA_MAX=2`, worker recycling) make it survive. They do not change the
fact that each deploy load-tests production.

CI never had this problem. Its "Frontend build, prerender guards, browser smoke
(real API)" job seeds an API from the checkout (SQLite), runs gunicorn on
localhost and builds against that. This option does the same in the Render
build.

## How it works (`OCHORUS_BUILD_API=local`)

```
npm ci && npm run build                  (render.yaml's buildCommand, unchanged)
 ├─ prebuild
 │   ├─ scripts/local-api.mjs start      ← new; prints one line and exits when the flag is off
 │   │    1. uv (from PATH; if missing, installs uv==0.13.7 with python3 -m pip into the work dir)
 │   │    2. uv sync --frozen --no-dev into <work dir>/venv  (never backend/.venv)
 │   │    3. manage.py release        on a fresh <work dir>/api.sqlite3 (production's deploy chain)
 │   │    4. manage.py build_bible_store                     (as the API's Dockerfile does)
 │   │    5. manage.py apply_build_facts <facts>             (production's DB-owned facts, below)
 │   │    6. gunicorn on 127.0.0.1:8765 under a detached supervisor; wait for /api/health/
 │   ├─ await-api-release.mjs            skips: the local API holds this checkout by construction
 │   └─ fetch-live-locales.mjs           asks the LOCAL API which languages are live
 ├─ vite build (prerender)               hooks.server.ts sends API requests to 127.0.0.1
 └─ postbuild
     └─ scripts/local-api.mjs stop       first step; the rest of postbuild is unchanged
```

**`PUBLIC_API_BASE_URL` stays production.** The client bundle, the CSP and the
URL SvelteKit stores each inlined response under all use it. A page whose
inlined `fetch` was keyed `http://127.0.0.1:…` would miss its inlined data on
hydration and fetch everything again from the live API. So only the network
request moves: `handleFetch` passes the build's fetch chain
(`$lib/buildFetch`, chapter batches included) a `fetch` that retargets
API-origin URLs to the local origin (`$lib/buildApi.retarget`). `request.url`
keeps its production value.

The backend runs with a **clean environment**: PATH, HOME, locale and temp
variables pass through, and nothing else. `DATABASE_URL` is always the SQLite
file and `DJANGO_DEBUG=true`, as in CI. Whatever the web service's environment
holds, this server cannot reach a real database. `apply_build_facts` also
refuses to run against anything but SQLite.

Knobs (all optional except the flag):

| Variable | Default | Meaning |
|---|---|---|
| `OCHORUS_BUILD_API` | unset | `local` turns the mode on |
| `OCHORUS_BUILD_FACTS` | — | facts file path, `https://` URL, or `none`. **Required on Render** |
| `OCHORUS_BUILD_FACTS_TOKEN` | — | sent as `Authorization: Bearer` when fetching the facts URL |
| `OCHORUS_BUILD_API_PORT` | `8765` | local port |
| `OCHORUS_BUILD_API_DIR` | `$TMPDIR/ochorus-build-api` | venv, SQLite file, log |
| `OCHORUS_BUILD_API_WORKERS` | `2` | gunicorn worker processes |
| `OCHORUS_BUILD_API_TTL_MIN` | `120` | the supervisor kills the API after this, if `stop` never runs (a failed `vite build` skips postbuild) |
| `PRERENDER_CONCURRENCY` | `1` | can rise with a local API (CI uses 8) |

## Step 1: what production has that a repo-seeded DB does not

The seeds re-run on every deploy, so any field a workflow owns after creation
is **create-only** (backend/CLAUDE.md). That is the right rule for production,
and it means those decisions are stored nowhere except production's DB. The
table lists every one that reaches a prerendered page. The local build gets each
from the facts export (`library/build_facts.py`).

| Fact | Who sets it in production | Where the build reads it | Carried by facts? |
|---|---|---|---|
| **Which languages are live** (`Language.status`), plus `name`, `native_name`, `sort_order`, `rtl` and Bible label/credit | Admin Go live (`golive.py`), language admin screens | `fetch-live-locales.mjs` → `/api/library/languages/?all=1` → `LIVE_LOCALES` (which locales are prerendered, sitemap, hreflang, noindex on unadvertised locales, footer tiles and book counts, `ARTICLE_LOCALES`); `live_codes()` inside API views; Bible credit lines | yes |
| **Languages added from the admin**, e.g. Amharic (`am` is a UI locale but has no `language_seed.py` entry, so a repo DB has no row for it at all) | Admin → Add a language | same as above | yes (the row is created) |
| **`is_published`** on books, sermons, articles (plans and topics too) | Admin publish/unpublish (`admin_views/detail.py`), urgent copyright unpublishes in the DB | Every public list/detail endpoint filters on it, so it decides the prerender `entries()`, shelves, the sitemap and tombstones | yes |
| **`source_type`** review state (`ai_unreviewed` → `ai_reviewed`) | Review queue (`admin_views/quality.py`), `approve_translation` / `approve_sermon_translation` run against prod | `indexed_languages` → chapter-page hreflang; `sitemap.ts` `advertisesChapters` (which translated chapters are offered to search). Never shown to readers as a badge | yes |
| **`Quote.reviewed`** | `approve_quotes` run against prod; takedowns | `/quotes/<author>`, quote theme pages, quote counts on book, sermon and author pages, hub quote strips, the postbuild author and quote cards (read from inlined data) | yes |
| **Approved author-bio translations**: `reviewed=True` rows keep the approver's wording, and `seed_author_translations` never rewrites them | Review queue, `approve_author_translation` | Author pages in each locale (`bio`, `bio_html`, `faq`) | yes, reviewed rows only, text included (re-sanitized with `clean_bio_html`) |
| **Works only production has**: admin upload imports (`admin_import_views` → `upload_import.create_book/create_sermon`, plus a new `Author` they may create) | Admin import → Publish | Everything | **no.** Reported by `apply_build_facts`, and the build fails if more than 25 rows are missing (`--max-missing`). Land them as fixture files first |
| Rows deleted from the repo but still in production (seeds never delete) | — | — | n/a. The local build drops them, which is arguably more correct; `build-tombstones` covers their URLs (it fails above 300 at once) |

Checked and **not** a prerender gap:

- Search synonyms, pins and popular searches (`SearchDecision`,
  `SearchQueryLog`) are runtime only: the search page fetches them in `onMount`.
- Reader engagement (`reading` app) is not read by any public prerendered
  endpoint.
- `ContentRevision` feeds the ETag and the deploy hook. No page reads it.
- Admin-only tables (`LanguageHealthSnapshot`, `ReviewOutcome`,
  `TranslationNote`, `VerseReview`, `AuditDismissal`, `AdminAction`) and
  language thresholds/glossary don't reach pages.
- Content itself (fixtures, `corrections.py`, plan/topic/quote/bio seed data)
  comes from the checkout, and `release` runs the same chain production runs.
  That covers more than CI's subset (CI skips `apply_body_corrections`,
  `seed_author_translations`, `seed_topics`, …).

Differences that remain by construction:

- **SQLite, not Postgres.** CI has built the site this way for months and its
  prerender-coverage guards pass. But any shelf ordered by `title` with
  non-ASCII titles can sort differently (Postgres collation vs SQLite binary),
  and `search_vector` is unused on SQLite. Search is not prerendered.
- **Facts are as fresh as the export.** See the transport decision below.

## Step 2: the facts transport (decided: A, built)

**Option A is built** (2026-11-24): `GET /api/build-facts/`
(`library/build_facts_view.py`). It 404s unless `BUILD_FACTS_TOKEN` is set on
ochorus-api, and to any caller without `Authorization: Bearer <that token>`
(constant-time compare), so the route is invisible until configured. It is
exempt from the API guard (a server, no Origin; its own token gates it) and
answers `Cache-Control: no-store`. `local-api.mjs` already sends
`OCHORUS_BUILD_FACTS_TOKEN` as that bearer. The options as weighed:

The facts are one small JSON document: 268 KB for today's 1,851 books, 1,440
sermons, 985 articles, 584 quotes and 13 languages. `manage.py
export_build_facts` writes it. The export only reads, with about ten SELECTs
and no writes. What is not built yet is how it gets from production to the
build. The options:

- **A. Token-gated endpoint on the API (recommended).**
  `GET /api/build-facts/` returns `export_facts()` and needs a shared
  secret (`BUILD_FACTS_TOKEN` on ochorus-api; the same value as
  `OCHORUS_BUILD_FACTS_TOKEN` on ochorus-web). Each build makes **one request
  instead of thousands**, at build start, so the facts are always current. That
  matters because Go live, an approval and a publish toggle each fire a
  web-only rebuild (`invalidation.mark_content_changed`) that expects to see
  the change. This is a new auth surface on the API, which is why it is not in
  this PR. The document exposes unpublished slugs and review state, so it must
  not be public.
- **B. Export during the API's `release`, uploaded to a private Supabase
  Storage bucket**, with `OCHORUS_BUILD_FACTS` set to a signed URL. This adds
  no endpoint, but the facts are only as fresh as the last API deploy. A
  web-only rebuild after Go live would miss the launch unless
  `mark_content_changed` also re-exports.
- **C. Manual.** Run `export_build_facts` in the ochorus-api shell and host the
  file somewhere. Only good for a trial.

`OCHORUS_BUILD_FACTS=none` builds with the repo's defaults. The live set is
then the seed's `INITIALLY_LIVE` (en, es, sw, lg, pt), and nothing approved in
production is reflected. The script requires `none` to be set on purpose before
it will do that on Render.

## Step 3: switch-on steps

1. **Set the token.** Generate one long random secret and set it as
   `BUILD_FACTS_TOKEN` on ochorus-api and `OCHORUS_BUILD_FACTS_TOKEN` on
   ochorus-web (render.yaml declares both, `sync: false`). Set ochorus-web's
   `OCHORUS_BUILD_FACTS` to `https://<ochorus-api host>/api/build-facts/`.
   Check it: `curl -H "Authorization: Bearer $TOKEN" <that URL> | head -c 300`.
2. **Prove it on a preview, not on production.** Open a manual Render preview
   (or a scratch static site on this branch) with `OCHORUS_BUILD_API=local`
   and `OCHORUS_BUILD_FACTS` set. Check its log for:
   - `local build API:` lines showing uv or python3 was found (Render's native
     build image is expected to have Python 3, and possibly uv, but **this is
     unverified**; the script installs uv with pip when it is missing),
   - the `release` time (about **16 minutes locally** on 4 shared cores,
     against a 1.4 GB SQLite file; this is the main cost),
   - `✓ local build API: serving this checkout`,
   - `apply_build_facts` listing the same live languages as production, and no
     `production-only` lines,
   - a build that finishes inside Render's build limits (disk: ~1.5 GB for the
     DB; memory: gunicorn ×2 plus the prerender).
3. **Compare the output with production's.** Fetch
   `https://ochorus.com/published-pages.txt` and the preview's, then diff them.
   Expect only the pages a content change explains. Spot-check a translated
   chapter's hreflang, a quote page and an author bio in a reviewed locale.
4. **Switch on**: set `OCHORUS_BUILD_API=local`, `OCHORUS_BUILD_FACTS` and, if
   using option A, `OCHORUS_BUILD_FACTS_TOKEN` (`sync: false`) on ochorus-web.
   Use the dashboard, or add them to render.yaml and run Blueprint → Sync.
   Optionally raise `PRERENDER_CONCURRENCY`. Then deploy.
5. **After that**, the web build no longer waits for the API deploy
   (`await-api-release` skips), so `API_RELEASE_TIMEOUT_MS` stops mattering. The
   deploy train can still move both services together. Nothing now requires
   it.

**Rollback:** unset `OCHORUS_BUILD_API` and redeploy. The build is back to
crawling `PUBLIC_API_BASE_URL`, byte for byte today's path.

## If the Render build image cannot run the backend

If the preview shows no python3 and no uv, or the build runs out of time or
memory, the alternative is CI's job. It already produces this exact site
against a local API on GitHub's runners. Publishing that output needs a host
that accepts uploaded files (Render static sites build from the repo only), so
this means moving static hosting, for example to Cloudflare Pages or R2 via a
GitHub Actions deploy. That is a bigger change, and only worth it if step 2
fails. A "prebuilt API snapshot" does not avoid the problem: the snapshot still
needs Python to serve it.

Seeding is the slow step. A later speed-up is caching the seeded SQLite between
builds, keyed by the content digest (`manage.py content_version`) plus the
migrations' hash.

## Code map

- `backend/library/build_facts.py`: `export_facts` / `apply_facts`, and what
  each fact is.
- `manage.py export_build_facts [--out F]`: read-only, run against production.
- `manage.py apply_build_facts F [--max-missing N]`: SQLite only, run against
  the build DB.
- `frontend/scripts/local-api.mjs`: start and stop the build API.
- `frontend/src/lib/buildApi.ts`: the flag, the build-time API base,
  `retarget`.
- `frontend/src/hooks.server.ts`: retargets the build's API requests.
- Tests: `library/tests_build_facts.py`, `src/lib/buildApi.test.ts`.
