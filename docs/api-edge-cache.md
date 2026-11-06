# Serving the API close to readers

The reader's pages are static files on Render's CDN, so they're fast everywhere.
The **API** isn't. `render.yaml` gives `ochorus-api` no `region:`, so it runs in
Render's default region, **Oregon**. Every client-side page change, Continue
reading block and sync call from Kampala crosses the world and back, usually
more than once. These are the two settings changes that fix it, in order of
payoff. Both happen in dashboards, not in this repo.

The code side is already done: public library reads send `Cache-Control`
(browser: one minute plus stale-while-revalidate) and `CDN-Cache-Control`
(edge: the same minute, **no** stale-while-revalidate, so the prerender build
never gets an old shelf). See `backend/library/http_cache.py`.

## 1. Check that the API and the database are in the same region

1. Supabase dashboard → the project → **Project Settings → General** → *Region*.
2. Render's `ochorus-api` is in **Oregon (us-west)**.

If Supabase isn't in a US-West region, every database query also crosses that
distance, several times per API call. Render can't move an existing service, so
the fix is a new web service in the database's region: add `region: <name>` to
the `ochorus-api` block in `render.yaml` as a new service, deploy it, point
`api.ochorus.com` at it, then delete the old one. Do this before step 2: it
speeds up every request, cached or not.

## 2. Put a CDN in front of `api.ochorus.com`

Cloudflare's free plan is enough. The goal is that the ~1 minute public reads
are answered from an edge near the reader, while anything personal never is.

1. Add `ochorus.com` to Cloudflare (or only the `api` record, if DNS stays
   elsewhere) and set the `api` record to **Proxied**.
2. **Caching → Cache Rules → Create rule**:
   - *When*: hostname equals `api.ochorus.com` **and** URI path starts with
     `/api/library/`.
   - *Then*: **Eligible for cache**. Edge TTL: **Use cache-control header if
     present, bypass cache if not**. Browser TTL: **Respect origin**.
   - Nothing else. `/api/reading/`, `/api/auth/`, `/api/admin/` and search
     (which sends no `Cache-Control`) must never be cached at the edge.
3. **CORS must still be right per caller.** The API answers each allowed origin
   with its own `Access-Control-Allow-Origin` and `Vary: Origin`: the website,
   and the phone app's `capacitor://localhost` / `https://localhost`. Check that
   the edge keeps them apart (commands below). If it doesn't, add the `Origin`
   header to the cache key if your plan allows it. Otherwise point the app's
   `PUBLIC_API_BASE_URL` (`frontend/app-env/.env`) at the origin host
   (`ochorus-api.onrender.com`) so only the website uses the edge.

### Check it

```sh
U=https://api.ochorus.com/api/library/books/?language=en
# Run twice: the second should say cf-cache-status: HIT.
curl -sI "$U" -H 'Origin: https://ochorus.com' | grep -iE 'cf-cache-status|access-control-allow-origin|cdn-cache-control'
# The app's origin must get ITS OWN allow-origin back, not the website's.
curl -sI "$U" -H 'Origin: capacitor://localhost' | grep -iE 'cf-cache-status|access-control-allow-origin'
# Search and personal reads must never be cached: DYNAMIC or BYPASS.
curl -sI 'https://api.ochorus.com/api/library/search/?q=prayer' | grep -i cf-cache-status
```

## 3. Measure it

The `Page load` Plausible event (`frontend/src/lib/webVitals.ts`, a 10% sample
of first page loads) carries `ttfb` and `lcp` buckets per route and locale.
Plausible adds the country. Compare the share of `ttfb` in `<0.3s` and
`0.3-0.8s` for Uganda, Kenya and Tanzania for a week before and after each step.
