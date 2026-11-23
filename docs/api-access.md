# Keeping the API for Ochorus

`api.ochorus.com` exists to serve Ochorus's own clients: the reader on
ochorus.com, the iOS and Android apps, and the web build that prerenders the
site. This page says what protects it, what can't, and how to switch the
protection on.

## The honest limit

The reader is a static site, and its JavaScript calls the API **from the
visitor's browser**. Whatever that browser can fetch, the person at it can
fetch too: open the network tab, copy the request, replay it from a script. A
key shipped to the browser is a key shipped to everyone. So no setting can
make a browser-called API *secret*, and nothing here pretends to.

What it can do is make the API useless as a free backend for anyone else:

- **Other websites can't use it from their pages.** A browser always sends the
  page's real `Origin`, and a page can't change it. Only our origins pass.
- **Casual scripts, bots and scrapers are turned away.** A bare
  `curl`/`requests` call sends no `Origin` and gets a 403. Getting past that
  takes deliberately forging browser headers, which is the point where rate
  limits and bot management at the edge take over (below).
- **Private data was never open.** Reading state, accounts and the admin API
  already require a Supabase sign-in token (and the admin allowlist); this adds
  nothing there and takes nothing away.

The library *content* is public on the reader's own pages anyway, so the goal
is "not a free API for others", not "nobody can ever see this JSON".

## What the API does (`backend/common/api_guard.py`)

Every `/api/` request passes if any one of these holds:

| Who | How it's recognised |
| --- | --- |
| The reader (ochorus.com), Googlebot's renderer | `Origin` is in `CORS_ALLOWED_ORIGINS` |
| iOS / Android app | `Origin` is `capacitor://localhost` / `https://localhost` (always in the CORS list) |
| A same-origin call or a plain link | no `Origin`, but a `Referer` from one of those origins |
| The web build (prerender + `fetch-live-locales`) | `X-Ochorus-Key` matches one of `API_SERVICE_KEYS` |
| Not our pages, so exempt | `/api/health/` (Render's health check, the build's release gate), `/api/emails/` (Resend's signed webhook, unsubscribe links), a book's `download.epub` link, `/robots.txt` |

Everything else gets `403 {"detail": "This API serves Ochorus's own apps only."}`.

`API_GUARD_MODE` decides what happens: `off`, `report` (let everything
through, log each request `enforce` would refuse as
`api_guard would refuse GET /api/... (reason) ua='...'`), or `enforce`.
**Production defaults to `report`** until it's switched, because the build
needs its key first or the next deploy's prerender would be refused.

The build's key lives in `OCHORUS_API_KEY` on ochorus-web, a private env var
(no `PUBLIC_` prefix, so it is never baked into the bundle). It is added only
on the build's own network request, after SvelteKit has recorded what to inline,
so no prerendered page ever contains it (`frontend/src/hooks.server.ts`).

## Switching it on (Render)

1. Make a key: `openssl rand -hex 32` (or any 64 random hex characters).
2. **ochorus-api → Environment**: add `API_SERVICE_KEYS` = that key. Leave
   `API_GUARD_MODE` unset (it means `report`).
3. **ochorus-web → Environment**: add `OCHORUS_API_KEY` = the same key.
4. Let the next deploy train run (or deploy both by hand).
5. A day later, **ochorus-api → Logs**, search `api_guard`. Expect scripts,
   uptime checkers and scrapers. If you see something of ours (a real browser
   user-agent with `origin https://...` naming a domain we use), add that
   origin to `CORS_ALLOWED_ORIGINS` first.
6. **ochorus-api → Environment**: set `API_GUARD_MODE` = `enforce` and save
   (Render restarts the API; no rebuild needed).
7. Check: `curl -s -o /dev/null -w '%{http_code}\n' https://api.ochorus.com/api/library/languages/`
   should print `403`, and the site, search and the app should work as before.

To undo instantly, set `API_GUARD_MODE` back to `report`. To rotate the key,
put `new,old` in `API_SERVICE_KEYS`, change `OCHORUS_API_KEY` to `new`, deploy,
then drop `old`.

Make sure `CORS_ALLOWED_ORIGINS` on ochorus-api lists every origin the reader
is served from (e.g. `https://ochorus.com`, and `https://ochorus-web.onrender.com`
while that is still used). The guard reads the same list.

## The edge (Cloudflare), for what the app can't do

The remaining gap is someone forging browser headers from a script. That is
answered by volume limits, which belong at the edge: per-instance limits inside
Django only see one worker's traffic. Once `api.ochorus.com` is behind
Cloudflare (proxied), see [egress-cloudflare.md](egress-cloudflare.md) for the
cache rule, and add:

1. **Rate limit** on `/api/library/` by IP (§2 there: ~200 req/min, Block).
2. **Bot Fight Mode** on, with verified bots allowed (§4).
3. **A WAF custom rule** that blocks `/api/` requests with no `Origin`, no
   `Referer` and no `X-Ochorus-Key`, except `/api/health/`, `/api/emails/`
   and `download.epub`. Same rule as the API's, refused before it costs a
   Render request.
4. **Before turning the proxy on**, change `NUM_PROXIES` in
   `backend/config/settings.py` from 1 to 2 (Cloudflare plus Render), or every
   visitor will share Cloudflare's address in the API's throttles and the busy
   ones will start getting 429s.
