# Deploying Ochorus

Ochorus deploys as two Render services from one repo (via `render.yaml`):
a Dockerised Django API (`ochorus-api`) and a static SvelteKit reader
(`ochorus-web`). The database is Supabase Postgres. The library content ships as
a fixture and self-loads on first deploy — no manual data step.

## 1. Supabase (database)

1. Create a project at [supabase.com](https://supabase.com) (free tier is fine).
2. Project Settings → **Database** → Connection string → **Session pooler**.
   Copy it; this is `DATABASE_URL`. (Swap in your DB password.)
3. Project Settings → **API** → copy the **Project URL**
   (`https://<ref>.supabase.co`); this is `SUPABASE_URL`.
   (Auth/login isn't wired into the app yet, but the API still validates against
   this URL once it is — set it now.)

## 2. Push to GitHub

```bash
cd ~/dev/ochorus
gh repo create ochorus --private --source=. --remote=origin --push
```

## 3. Render (blueprint)

1. [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint** →
   connect the `ochorus` repo. Render reads `render.yaml` and proposes both
   services.
2. Fill in the prompted secrets:
   - `ochorus-api`: `DATABASE_URL`, `SUPABASE_URL`. Leave
     `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`
     blank for now (filled in step 4).
   - `ochorus-web`: leave `PUBLIC_API_BASE_URL` blank for now.
3. Apply. The first deploy runs migrations and seeds the 10 books automatically.

## 4. Wire the two services together

After the first deploy, both services have URLs (e.g.
`https://ochorus-api.onrender.com`, `https://ochorus-web.onrender.com`). Set:

- `ochorus-api` → `DJANGO_ALLOWED_HOSTS` = `ochorus-api.onrender.com`
- `ochorus-api` → `CORS_ALLOWED_ORIGINS` = `https://ochorus-web.onrender.com`
- `ochorus-api` → `CSRF_TRUSTED_ORIGINS` = `https://ochorus-web.onrender.com`
- `ochorus-web` → `PUBLIC_API_BASE_URL` = `https://ochorus-api.onrender.com`

Trigger a redeploy of both (Render does this automatically on env change). Done —
`ochorus-web` is live with all 10 books.

## 5. Custom domain (optional)

Add your domain to `ochorus-web` in Render → Settings → Custom Domains, then add
it to `DJANGO_ALLOWED_HOSTS` / `CORS_ALLOWED_ORIGINS` / `CSRF_TRUSTED_ORIGINS`.

## Refreshing content later

Re-run the importers locally and regenerate the fixture, then commit:

```bash
cd backend
DJANGO_DEBUG=true uv run python manage.py import_ccel
DJANGO_DEBUG=true uv run python manage.py import_gutenberg
DJANGO_DEBUG=true uv run python manage.py dumpdata library --indent 1 -o library/fixtures/launch.json
```

(The seed step only runs on an *empty* database, so to push content updates to an
existing deployment, load the fixture from the Render shell:
`python manage.py loaddata launch`.)
