# SEO edge rules — the redirects the static host can't do

Two duplicates of every page need a real HTTP 301, and neither can be written
in `render.yaml` (it explains why at the end of its `routes:` list). Today the
app forwards both with JavaScript (`frontend/src/lib/canonicalRedirect.ts`),
which a crawler only follows if it renders the page, and doesn't on a 404.

**Order matters.** `render.yaml` no longer has the `/* -> /200.html` catch-all,
so once its Blueprint is synced a no-slash detail URL (`/books/humility`)
answers **404** instead of the noindex 200 shell. Add rule 1 **first**, then
sync the Blueprint, or old no-slash backlinks will 404 for crawlers until you do.

## 1. No-slash → slash 301 (Cloudflare, `ochorus.com` zone)

**Rules → Redirect Rules → Create rule → Custom filter expression**

```
(http.host eq "ochorus.com"
 and not ends_with(http.request.uri.path, "/")
 and not http.request.uri.path contains "."
 and not http.request.uri.path contains "/admin/"
 and (
   http.request.uri.path in {"/articles" "/authors" "/originals" "/quotes" "/scripture" "/series" "/es/articles" "/es/authors" "/es/originals" "/es/quotes" "/es/scripture" "/es/series" "/sw/articles" "/sw/authors" "/sw/originals" "/sw/quotes" "/sw/scripture" "/sw/series" "/lg/articles" "/lg/authors" "/lg/originals" "/lg/quotes" "/lg/scripture" "/lg/series" "/pt/articles" "/pt/authors" "/pt/originals" "/pt/quotes" "/pt/scripture" "/pt/series" "/ar/articles" "/ar/authors" "/ar/originals" "/ar/quotes" "/ar/scripture" "/ar/series" "/hi/articles" "/hi/authors" "/hi/originals" "/hi/quotes" "/hi/scripture" "/hi/series" "/uk/articles" "/uk/authors" "/uk/originals" "/uk/quotes" "/uk/scripture" "/uk/series" "/fr/articles" "/fr/authors" "/fr/originals" "/fr/quotes" "/fr/scripture" "/fr/series" "/am/articles" "/am/authors" "/am/originals" "/am/quotes" "/am/scripture" "/am/series"}
   or http.request.uri.path wildcard "/articles/*" or http.request.uri.path wildcard "/*/articles/*"
   or http.request.uri.path wildcard "/authors/*" or http.request.uri.path wildcard "/*/authors/*"
   or http.request.uri.path wildcard "/books/*" or http.request.uri.path wildcard "/*/books/*"
   or http.request.uri.path wildcard "/plans/*" or http.request.uri.path wildcard "/*/plans/*"
   or http.request.uri.path wildcard "/quotes/*" or http.request.uri.path wildcard "/*/quotes/*"
   or http.request.uri.path wildcard "/scripture/*" or http.request.uri.path wildcard "/*/scripture/*"
   or http.request.uri.path wildcard "/series/*" or http.request.uri.path wildcard "/*/series/*"
   or http.request.uri.path wildcard "/sermons/*" or http.request.uri.path wildcard "/*/sermons/*"
   or http.request.uri.path wildcard "/topics/*" or http.request.uri.path wildcard "/*/topics/*"
   or http.request.uri.path wildcard "/biographies/era/*" or http.request.uri.path wildcard "/*/biographies/era/*"
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
