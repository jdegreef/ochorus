# SEO edge rules — the redirects the static host can't do

Two duplicates of every page would ideally get a real HTTP 301, and neither can
be written in `render.yaml` (it explains why at the end of its `routes:` list).
The app forwards both with JavaScript (`frontend/src/lib/canonicalRedirect.ts`),
which a crawler only follows if it renders the page, and doesn't on a 404.

**There is no Cloudflare zone for `ochorus.com` today (checked 2026-09-30).**
DNS is at GoDaddy (`ns21/ns22.domaincontrol.com`). The `server: cloudflare`
response header comes from Render's own CDN, which we can't configure. So rule 1
below can't be applied. It is kept, and `edgeRules.test.ts` keeps it matched to
`isSlashedPath`, for the day the domain moves onto a Cloudflare zone of our own.

**What ships instead (decided 2026-09-30):** `render.yaml` has no
`/* -> /200.html` catch-all, so after a Blueprint Sync a no-slash detail URL
(`/books/humility`) answers **404** with the app shell. A human reader is still
forwarded to `/books/humility/` by the shell's JavaScript. Crawlers see the 404.
Every link we emit (pages, sitemaps, canonicals, hreflang) is already slashed,
so this costs only old external backlinks to no-slash URLs. That trade bought
honest 404s for typo'd slugs, dead URLs and untranslated editions.

**Render keeps a removed route after a sync.** Deleting a rule from `render.yaml`
doesn't delete it from the live service. The old `/* -> /200.html` catch-all
survived the 2026-10-01 sync, so unknown and no-slash paths still answered 200.
Delete it by hand: **Dashboard → ochorus-web → Redirect/Rewrite Rules → delete `/*`**.
Check: `curl -s -o /dev/null -w '%{http_code}' https://ochorus.com/books/no-such-book/` → `404`.

## 1. No-slash → slash 301 (Cloudflare — NOT APPLIED: needs an `ochorus.com` zone we don't have)

**Rules → Redirect Rules → Create rule → Custom filter expression**

```
(http.host eq "ochorus.com"
 and not ends_with(http.request.uri.path, "/")
 and not http.request.uri.path contains "."
 and not http.request.uri.path contains "/admin/"
 and (
   http.request.uri.path in {"/articles" "/authors" "/originals" "/quotes" "/rss" "/scripture" "/series" "/teens" "/young-readers" "/es/articles" "/es/authors" "/es/originals" "/es/quotes" "/es/rss" "/es/scripture" "/es/series" "/es/teens" "/es/young-readers" "/sw/articles" "/sw/authors" "/sw/originals" "/sw/quotes" "/sw/rss" "/sw/scripture" "/sw/series" "/sw/teens" "/sw/young-readers" "/lg/articles" "/lg/authors" "/lg/originals" "/lg/quotes" "/lg/rss" "/lg/scripture" "/lg/series" "/lg/teens" "/lg/young-readers" "/pt/articles" "/pt/authors" "/pt/originals" "/pt/quotes" "/pt/rss" "/pt/scripture" "/pt/series" "/pt/teens" "/pt/young-readers" "/ar/articles" "/ar/authors" "/ar/originals" "/ar/quotes" "/ar/rss" "/ar/scripture" "/ar/series" "/ar/teens" "/ar/young-readers" "/hi/articles" "/hi/authors" "/hi/originals" "/hi/quotes" "/hi/rss" "/hi/scripture" "/hi/series" "/hi/teens" "/hi/young-readers" "/uk/articles" "/uk/authors" "/uk/originals" "/uk/quotes" "/uk/rss" "/uk/scripture" "/uk/series" "/uk/teens" "/uk/young-readers" "/fr/articles" "/fr/authors" "/fr/originals" "/fr/quotes" "/fr/rss" "/fr/scripture" "/fr/series" "/fr/teens" "/fr/young-readers" "/am/articles" "/am/authors" "/am/originals" "/am/quotes" "/am/rss" "/am/scripture" "/am/series" "/am/teens" "/am/young-readers"}
   or http.request.uri.path wildcard "/articles/*" or http.request.uri.path wildcard "/*/articles/*"
   or http.request.uri.path wildcard "/authors/*" or http.request.uri.path wildcard "/*/authors/*"
   or http.request.uri.path wildcard "/books/*" or http.request.uri.path wildcard "/*/books/*"
   or http.request.uri.path wildcard "/for/*" or http.request.uri.path wildcard "/*/for/*"
   or http.request.uri.path wildcard "/plans/*" or http.request.uri.path wildcard "/*/plans/*"
   or http.request.uri.path wildcard "/quotes/*" or http.request.uri.path wildcard "/*/quotes/*"
   or http.request.uri.path wildcard "/scripture/*" or http.request.uri.path wildcard "/*/scripture/*"
   or http.request.uri.path wildcard "/series/*" or http.request.uri.path wildcard "/*/series/*"
   or http.request.uri.path wildcard "/sermons/*" or http.request.uri.path wildcard "/*/sermons/*"
   or http.request.uri.path wildcard "/topics/*" or http.request.uri.path wildcard "/*/topics/*"
   or http.request.uri.path wildcard "/biographies/era/*" or http.request.uri.path wildcard "/*/biographies/era/*"
   or http.request.uri.path wildcard "/biographies/tradition/*" or http.request.uri.path wildcard "/*/biographies/tradition/*"
   or http.request.uri.path wildcard "/biographies/place/*" or http.request.uri.path wildcard "/*/biographies/place/*"
 ))
```

**Then:** Type **Dynamic** · Expression `concat(http.request.uri.path, "/")` ·
Status **301** · **Preserve query string** on.

It can't loop: it only fires on a path that does *not* end in `/`, and its target
always does. It is the edge copy of `isSlashedPath` (the paths whose route
exports `trailingSlash = 'always'`). The set was checked against that function
for every route shape in all ten locales. Index pages that are *not* slashed
(`/books`, `/biographies`, `/topics` …) are deliberately absent: they resolve to
`<page>.html` via Render rewrites. A **new locale** needs its six `"/xx/…"` index
entries added to the `in {…}` set. A **new slashed route** needs a line here
and in `isSlashedPath` (whose test walks the route tree).
`frontend/src/lib/edgeRules.test.ts` parses the expression above and fails
when it and `isSlashedPath` disagree on any route in any locale. Edit this file,
then paste the new expression into Cloudflare.

`wildcard` and `in {…}` work on every Cloudflare plan. No regex, so no Business
plan is needed.

**Check:** `curl -sI https://ochorus.com/books/humility` →
`301 location: https://ochorus.com/books/humility/`. Also
`curl -sI https://ochorus.com/books/humility/` → `200`, and
`curl -sI https://ochorus.com/books` → `200` (not redirected).

## 2. `ochorus-web.onrender.com` → off (Render dashboard)

Traffic to the `onrender.com` host never passes through Cloudflare, so no edge
rule can reach it. Render can switch the host off instead: **Dashboard →
ochorus-web → Settings → Custom Domains → Render Subdomain → Disabled.** After
that it answers 404 and the site exists once, at ochorus.com.

No code in the repo calls that host. `config.ts` only falls back to it when
`PUBLIC_SITE_URL` is unset (local/preview builds). **Preview** environments have
their own `onrender` hosts, which this setting doesn't touch. One thing to check
first: the API's `CORS_ALLOWED_ORIGINS` (a dashboard env var, first set to "the
ochorus-web URL") must include `https://ochorus.com`. It must already, or the
live site couldn't load. The onrender entry can go at the same time.

## 3. After both are live

- Search Console → URL Inspection on a no-slash URL should report the redirect.
- Run `node frontend/scripts/check-slashes.mjs --limit 40`. Its no-slash column
  should read 301.
- `canonicalRedirect.ts` can stay. It is harmless behind a real 301 and still
  covers local/preview hosts.
