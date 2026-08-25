# Deploying Ochorus

Ochorus deploys as two Render services from one repo (via `render.yaml`):
a Dockerised Django API (`ochorus-api`) and a static SvelteKit reader
(`ochorus-web`). The database is **Supabase Postgres**, and login uses
**Supabase Auth**. The library (36 books) ships as a fixture and self-loads on
first deploy — no manual data step.

## 1. Supabase (database + auth)

1. Create a project at [supabase.com](https://supabase.com) (free tier is fine).
   Choose a region near your readers; save the database password.
2. **Settings → Database → Connection string → Session pooler** — copy it. This
   is `DATABASE_URL` (swap in your DB password).
3. **Settings → API** — copy:
   - **Project URL** (`https://<ref>.supabase.co`) → used for both
     `SUPABASE_URL` (backend, validates login tokens) and `PUBLIC_SUPABASE_URL`
     (frontend).
   - **`anon` / publishable key** → `PUBLIC_SUPABASE_ANON_KEY` (safe in the
     browser).
4. **Authentication → Providers → Email** — leave Email enabled (default). Add
   your site URL under **Authentication → URL Configuration → Site URL** after
   the frontend is deployed (step 4).

## 2. GitHub

Already done — the repo is at `github.com/jdegreef/ochorus`. Just make sure your
latest work is pushed:

```bash
cd ~/dev/ochorus && git push
```

## 3. Render (blueprint)

1. [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint** →
   connect the `ochorus` repo. Render reads `render.yaml` and proposes both
   services.
2. Fill in the prompted secrets:
   - `ochorus-api`: `DATABASE_URL`, `SUPABASE_URL`. Leave `DJANGO_ALLOWED_HOSTS`,
     `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` blank for now (step 4).
   - `ochorus-web`: `PUBLIC_SUPABASE_URL`, `PUBLIC_SUPABASE_ANON_KEY`. Leave
     `PUBLIC_API_BASE_URL` blank for now (step 4).
3. Apply. The first API deploy runs migrations and **auto-seeds the 36 books**
   from the committed fixture.

## 4. Wire the two services together

After the first deploy, both services have URLs (e.g.
`https://ochorus-api.onrender.com`, `https://ochorus-web.onrender.com`). Set:

- `ochorus-api` → `DJANGO_ALLOWED_HOSTS` = `ochorus-api.onrender.com`
- `ochorus-api` → `CORS_ALLOWED_ORIGINS` = `https://ochorus-web.onrender.com`
- `ochorus-api` → `CSRF_TRUSTED_ORIGINS` = `https://ochorus-web.onrender.com`
- `ochorus-web` → `PUBLIC_API_BASE_URL` = `https://ochorus-api.onrender.com`

Also set the Supabase **Site URL** (step 1.4) to the `ochorus-web` URL so login
redirects resolve. Render redeploys automatically on env change. Done — the site
is live with all 36 books, and login + cross-device sync work.

## 5. Custom domain (ochorus.com)

Point `ochorus.com` at the app. The setup below makes the bare apex
(`ochorus.com`) the primary/canonical host, redirects `www` to it, and gives the
API its own `api.ochorus.com` subdomain. Because ochorus.com previously served a
**WordPress** site, this is a cutover — do the app-config changes (step 5.2)
*before* flipping DNS so everything works the instant the new records resolve.

> ⚠️ **Before you start.** Screenshot the current DNS records at your registrar
> (the existing `@` A-record and `www`) — that's your rollback. **Do not touch
> `MX` or `TXT` records**: those carry email for `support@ochorus.com` plus
> SPF/DKIM, and deleting them breaks mail. This cutover only changes the *website*
> records (`A` / `CNAME`). Keep WordPress running until you've verified, then
> decommission it.

### 5.1 Add the domains in Render (no traffic moves yet)

- **`ochorus-web` → Settings → Custom Domains:** add `ochorus.com` **and**
  `www.ochorus.com`. Render serves both and 301-redirects `www` → apex.
- **`ochorus-api` → Settings → Custom Domains:** add `api.ochorus.com`.
- Render shows the exact DNS target for each — **use what Render displays.** As
  of writing that's an apex **A record → `216.24.57.1`** and **CNAME** targets of
  `ochorus-web.onrender.com` / `ochorus-api.onrender.com` for the subdomains.

### 5.2 Update app config (do this *before* the DNS flip)

**`ochorus-api` env vars** — add the new values, keep the onrender ones through
the transition:

```
DJANGO_ALLOWED_HOSTS   = ochorus-api.onrender.com,api.ochorus.com
CORS_ALLOWED_ORIGINS   = https://ochorus-web.onrender.com,https://ochorus.com,https://www.ochorus.com
CSRF_TRUSTED_ORIGINS   = https://ochorus-web.onrender.com,https://ochorus.com,https://www.ochorus.com
```

**`ochorus-web` env vars:**

```
PUBLIC_API_BASE_URL = https://ochorus-api.onrender.com   # ← keep the onrender host until api.ochorus.com's cert is Issued
PUBLIC_SITE_URL     = https://ochorus.com
```

> ⚠️ **Do not point `PUBLIC_API_BASE_URL` at `https://api.ochorus.com` until that
> domain shows *Certificate: Issued* in Render.** The frontend build prerenders
> every public page by **fetching this URL at build time**; if the custom API
> domain's TLS cert isn't live yet, every prerender fetch fails the TLS handshake
> (`ssl/tls alert handshake failure`, SSL alert 40) and the build exits 1. Ship on
> the always-valid `ochorus-api.onrender.com` host first (CORS already allows both
> origins, so the site is fully functional), then flip to `https://api.ochorus.com`
> and redeploy **after** the cert is issued. `PUBLIC_SITE_URL` has no such
> constraint — it's only baked into meta-tag strings, never fetched.

> `PUBLIC_SITE_URL` is baked into the prerendered pages (canonical / OG / sitemap)
> at **build** time, so after changing it run `ochorus-web` → **Manual Deploy →
> "Clear cache & deploy latest commit"**. A plain env save won't re-bake the
> static HTML (same trap as gotcha #2 below).

**Supabase → Authentication → URL Configuration:**

```
Site URL       = https://ochorus.com
Redirect URLs  = add  https://ochorus.com/**  and  https://www.ochorus.com/**
```

(otherwise magic-link / OAuth redirects bounce to the old onrender URL.)

### 5.3 Flip DNS at the registrar (GoDaddy)

GoDaddy → your domain → **DNS → Manage Zones / Records**, and make sure **Domain
→ Forwarding is OFF** (GoDaddy forwarding frames/masks the site). Edit the
existing parked `@` and `www` records rather than adding duplicates:

| Type  | Name  | Value                             | TTL  |
|-------|-------|-----------------------------------|------|
| A     | `@`   | `216.24.57.1` *(what Render shows)* | 600  |
| CNAME | `www` | `ochorus-web.onrender.com`        | 600  |
| CNAME | `api` | `ochorus-api.onrender.com`        | 600  |

Leave everything else (`MX`, `TXT`, …) untouched. **Tip:** a day ahead, lower the
TTL on the current `@`/`www` records to `600` so the switch propagates in minutes
and rollback is fast.

### 5.4 Verify

Allow a few minutes to ~an hour for DNS propagation and Render's automatic
Let's Encrypt certificates, then check:

- `https://ochorus.com` loads the reader with a valid padlock; `https://www.ochorus.com`
  redirects to it.
- A book page (e.g. `https://ochorus.com/books/godliness/`) renders with covers.
- **Login works** — this proves CORS + the Supabase redirect + `api.ochorus.com`
  are all wired.
- `https://api.ochorus.com/api/health/` returns OK.
- A legacy path redirects: `https://ochorus.com/author-biographies/` → `/biographies`,
  `https://ochorus.com/ochorus-books/` → `/books` (see the redirect rules in
  `render.yaml`; **`render.yaml` route changes only take effect after a
  Blueprint → Sync** in the Render dashboard — a plain push won't apply them).
- A retired WordPress media URL redirects rather than answering 200 with the app
  shell: `https://ochorus.com/wp-content/uploads/2025/08/FEASTING-AT-THE-TABLE.pdf`
  → `/books/feasting-at-the-table/`, and
  `…/2025/08/Normal-Christian-Life.jpg` → `/covers/art/the-normal-christian-life.jpg`.

**Rollback:** restore the old `@`/`www` values at the registrar — the low TTL
makes it quick.

## Refreshing / adding content later

Re-run the importers locally, regenerate the fixture, commit, and push (Render
auto-deploys). New content reaches the live database via the deploy's seed
commands (`seed_books`/`seed_sermons` run on every release). **Never run raw
`loaddata` against production** — it full-row-overwrites, silently reverting
approved review states (`source_type`).

```bash
cd backend
DJANGO_DEBUG=true uv run python manage.py import_ochorus   # re-scrape ochorus.com
uv run python scripts/regen_fixture.py   # pinned 6-model natural-key regen; NEVER bare `dumpdata library`
```

(`import_ccel` / `import_gutenberg` add public-domain titles from those sources.)

### Getting a data change onto the live site — two gotchas

1. **The live DB isn't re-seeded wholesale from the fixture.** `seed_if_empty`
   only fills an *empty* database. What carries a change to prod depends on the
   row:
   - **Book rows and sermon rows** — the fixture *is* the vehicle. `seed_books`
     and `seed_sermons` run on every release and **upsert** them: a new
     `(slug, language)` is created, a changed field (`title`, `cover_url`,
     `description`, `sort_order`, …) is updated. Regen the fixture and push; no
     migration, no Render-shell step.
   - **Everything else** — chapter text, author bios, taxonomy, anything an
     existing book's *chapters* carry — still needs a **data migration** (runs
     on deploy via `manage.py release`; see `0003_clean_chapter_titles`).
   - `source_type` and `is_published` are **create-only** in both seeds: they're
     owned by the review/unpublish workflow on the live DB, so the fixture never
     re-asserts them. Changing one on prod still needs a migration (or the
     `approve_translation` command).

2. **Only *declared* content paths refresh the prerendered pages.** The public
   `/books/<slug>` and `/authors/<slug>` pages are static HTML baked at *frontend
   build* time, and Render skips the `ochorus-web` build when a commit touches
   nothing the service's `buildFilter` names. That filter lists every root in
   `backend/library/content_sources.json` — the fixtures, plan and topic prose,
   and the author-bio data — so a commit to any of them rebuilds the reader.

   A backend change *outside* those roots (a view, a migration, a settings
   tweak) deliberately does **not** rebuild: the API and the client-side reader
   update immediately and the prerendered pages are unaffected because their
   content didn't change. If one of those changes *does* alter reader content —
   a data migration that edits chapter text, say — the prerendered pages stay
   frozen until a build runs. **Fix: manually redeploy the frontend** — Render →
   `ochorus-web` → **Manual Deploy → "Clear cache & deploy latest commit"**.

   To tell which case you are in, compare what the API is serving with what the
   repo holds:

   ```
   curl -s https://<api-host>/api/health/ | jq -r .content_version
   cd backend && uv run python manage.py content_version
   ```

   Equal means the reader's content is current. Different means a build is
   pending (or needed) — and the web build itself waits for the API to reach the
   repo's value before prerendering, so it can never bake the previous release's
   content (`frontend/scripts/await-api-release.mjs`).

   Adding a new kind of seed data? Add its directory to `content_sources.json`
   *and* to the `buildFilter`; `tests_fixture` fails if the two disagree, because
   the failure is otherwise silent — content ships and its pages never rebuild.
   A root may also be a single **file**, which is how `library/topic_seed.py`
   and `library/plan_seed.py` are named: they are Python, and a `/**` over a
   Python package sweeps in `__pycache__`, so the API image and the web build
   would digest identical content differently and the gate would never pass.
