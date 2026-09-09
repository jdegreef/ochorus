# Cutting Supabase egress: cache + bound reads at the CDN

## What happened

In 2026-09 the Supabase project went over its egress quota — ~14 GB/day against
3 monthly active users. That mismatch is the tell: this is **machine traffic**,
not readers. In Ochorus, Supabase is only the Postgres database, so "egress" is
bytes the DB ships to the Django API over the pooler. With three users, the load
is crawlers hitting the public API, whose responses are read from Postgres.

`pg_stat_statements` confirmed it: the heaviest rows shipped were repeated
`library_chaptercitation` scans (scripture/quote pages) and whole-book
`body_html` reads, driven by huge call counts (millions) — an anonymous crawl of
every content URL, amplified by per-request query fan-out.

## What shipped in code

**`get_opening` no longer reads the whole book.** The book-detail page shows one
40–65 word opening paragraph, but `get_opening` was materialising *every*
chapter's `body_html` (a `values_list("body_html")` that bypassed the view's
TOC-only prefetch) to produce it — so a crawl of every book URL pulled the whole
corpus, repeatedly. It now fetches bodies for only the ≤ `MAX_DEPTH` candidate
chapters. See `library/opening.py` (`_non_apparatus`, `opening_candidate_orders`)
and `BookDetailSerializer.get_opening`.

## What belongs at the CDN (not the app)

The other half — a rate bound on anonymous reads — must **not** live in Django.
A per-IP app throttle can't tell an abusive crawl from the site's own prerender
build, which fetches every content URL from a single build IP with no token. And
`frontend/src/lib/api.ts` retries only `>= 500`/network during prerender, so a
`429` throws and `svelte.config.js` fails the build. An app throttle therefore
breaks deploys (and 429s readers behind a shared NAT). Bound and cache at the
edge instead — it also *caches*, which is the bigger win.

### Cloudflare checklist (in front of `ochorus-api`)

1. **Cache the public content GETs.** They already emit
   `Cache-Control: public, max-age=60, stale-while-revalidate=600` and a per-URL
   `ETag` (`library/http_cache.py`). Add a cache rule on `/api/library/*` GETs.
   Repeat crawler/reader reads become edge hits — this stops the
   `ChapterCitation`/quote re-reads cold, the single biggest egress win.
   - **Cache key must include the query string** (`?language=…`).
   - **Cache despite the `Authorization` header.** These reads are
     reader-invariant (the mixin docstring verifies nothing reads
     `request.user`), so it is safe, but Cloudflare bypasses cache on
     `Authorization` by default — override it for this rule.
   - Cache `200`s only (the origin sets `Cache-Control` only on `200`).
2. **Rate-limit + bot-fight at the edge.** A WAF rate rule on `/api/*` for
   unauthenticated traffic — the read bound, where it can't touch the build.
3. **Allowlist the build.** Point the prerender build's `API_BASE_URL` at the
   **origin** (bypassing Cloudflare), or exempt the build's egress IP from the
   WAF rule, so deploys are never rate-limited.
4. **`robots.txt`: disallow `/api/`.** The whole corpus is already on the
   prerendered static site; bots have no reason to hit the API.

### Verify

After ~a day: Cloudflare cache-hit ratio up, Supabase egress down (Dashboard →
Reports → Database). `pg_stat_statements` call counts on the content endpoints
should fall sharply.
