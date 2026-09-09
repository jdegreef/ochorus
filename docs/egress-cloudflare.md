# Cloudflare config for cutting Supabase egress

The concrete config behind [egress-cdn.md](egress-cdn.md). Put `api.ochorus.com`
behind Cloudflare (proxied / orange-cloud); everything below is on that zone.
The single biggest win is the cache rule — it turns the anonymous read crawl
into edge hits, so the repeated `ChapterCitation`/quote/book reads never reach
Postgres.

## 1. Cache rule — the egress win (Caching → Cache Rules)

**Match:**
```
(http.host eq "api.ochorus.com" and http.request.method eq "GET"
 and starts_with(http.request.uri.path, "/api/library/")
 and not starts_with(http.request.uri.path, "/api/library/search"))
```
Excludes `search/` and `search-click/`: search writes a `SearchQueryLog` row per
query, so edge-caching it would starve the popular-searches data. Everything else
under `/api/library/` (books, chapters, authors, sermons, articles, plans,
topics, languages, quotes, scripture) is public and reader-invariant.

**Settings:**
- **Cache eligibility: `Eligible for cache` (override).** The one that matters —
  it caches even when the reader's request carries `Authorization: Bearer`, which
  Cloudflare otherwise treats as uncacheable. Safe because these responses are
  reader-invariant (`library/http_cache.py` verifies nothing reads
  `request.user`).
- **Edge TTL: `Use cache-control header from origin`** — honors the origin's
  `max-age=60`. After 60s Cloudflare revalidates with `If-None-Match`, and
  `PublicContentCacheMixin.dispatch` answers `304` *before running the queryset*,
  so revalidation costs ~no DB egress. Raise to a fixed 5 min if slower
  admin-publish propagation is acceptable.
- **Cache key → Query string: `Include all`** (so `?language=…` is part of the
  key). Don't vary on cookies/headers.

## 2. Rate limit (Security → WAF → Rate limiting rules)

- **Expression:** `starts_with(http.request.uri.path, "/api/library/")`
- **Counting:** by IP · **Rate:** 200 / 1 min · **Action:** Block, 60s.

Trade-offs to know:
- **Block (429), not Managed Challenge** — reader calls are XHR/fetch and can't
  complete an interactive challenge, so a challenge breaks them too. Block is the
  pragmatic choice.
- **Shared-NAT readers** (church/library Wi-Fi) share an IP, so keep the
  threshold generous. On Pro the counter includes cache hits; the caching above
  still means most reader reads never reach origin, but only Business+ can count
  origin-only. Tune from WAF analytics.

## 3. Build carve-out (required, or deploys break)

The build's `PUBLIC_API_BASE_URL` (`frontend/src/lib/config.ts`) is baked once and
used by both build and runtime, so the build can't simply be repointed. The
prerender build crawls every content URL from one IP with no token — a 429 there
is not retried (`frontend/src/lib/api.ts` retries only `>= 500`) and fails the
build. So exempt it:
- **Simplest:** add an IP allow to the rate-limit rule —
  `and not ip.src in { <Render build egress IPs> }`.
- **Cleaner:** a DNS-only (grey-cloud) `origin-api.ochorus.com` → the Render
  service, with a build-vs-runtime split in `config.ts` so build traffic bypasses
  Cloudflare entirely.

## 4. Bot Fight Mode (Security → Bots)

Enable it; **allow verified bots** (Googlebot etc.) so SEO is untouched. With the
`robots.txt` below, good bots won't crawl `/api/` anyway; bad bots that ignore it
get challenged.

## 5. robots.txt

Served by Django on the API host (see `config/urls.py` — `robots_txt`):
`User-agent: * / Disallow: /`. Nothing under the API is for crawlers; the corpus
is on the prerendered reader.

## 6. Verify (after ~a day)

- Cloudflare **Caching → analytics**: cache-hit ratio climbing on `/api/library/*`.
- Supabase **Reports → Database**: egress dropping.
- `pg_stat_statements`: call counts on the content endpoints falling.
