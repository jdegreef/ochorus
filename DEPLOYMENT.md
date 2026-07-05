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

## 5. Custom domain (optional)

Add your domain to `ochorus-web` (Render → Settings → Custom Domains), then add
it to `DJANGO_ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS`
(api) and the Supabase Site URL.

## Refreshing / adding content later

Re-run the importers locally, regenerate the fixture, commit, and push (Render
auto-deploys). The seed step only runs on an *empty* DB, so to push content
updates to the live database, load the fixture from the Render shell
(`python manage.py loaddata launch`).

```bash
cd backend
DJANGO_DEBUG=true uv run python manage.py import_ochorus            # re-scrape ochorus.com
DJANGO_DEBUG=true uv run python manage.py dumpdata library --indent 1 -o library/fixtures/launch.json
```

(`import_ccel` / `import_gutenberg` add public-domain titles from those sources.)

### Getting a data change onto the live site — two gotchas

1. **The live DB isn't re-seeded from the fixture.** `seed_if_empty` only fills
   an *empty* database, so a fixture change alone never reaches production. To
   update live data, ship it as a **data migration** (runs on deploy via
   `manage.py release`; see `0003_clean_chapter_titles`) — or, for a one-off,
   `loaddata launch` from the Render shell.

2. **A backend-only change does NOT refresh the prerendered pages.** The public
   `/books/<slug>` and `/authors/<slug>` pages are static HTML baked at *frontend
   build* time. Render skips the `ochorus-web` build when a commit touches
   nothing under `frontend/`, so after a data/migration-only change the API and
   the (client-side) reader update immediately, but the prerendered book/author
   pages stay frozen on the old content. **Fix: manually redeploy the frontend** —
   Render → `ochorus-web` → **Manual Deploy → "Clear cache & deploy latest
   commit"** — to re-prerender against the fresh API.
