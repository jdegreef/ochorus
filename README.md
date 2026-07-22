# Ochorus

A free, multilingual reading app for public-domain Christian classics — Andrew
Murray, Charles Spurgeon, and more. Web and mobile, totally free.

Sibling project to Take Root; reuses the same stack (SvelteKit + Paraglide,
Django + DRF, Supabase auth, Render deploy, Capacitor mobile wrapper).

## Layout

- `backend/` — Django 6 + DRF API. Apps: `accounts` (Supabase JWT auth),
  `library` (`Author` / `Book` / `Chapter`).
- `frontend/` — SvelteKit reader (added in a later phase).

## Backend — local dev

```bash
cd backend
cp .env.example .env          # DJANGO_DEBUG=true → runs on SQLite, no services
uv sync                       # install deps into .venv
uv run python manage.py migrate
uv run python manage.py import_ccel humility   # ingest a book
uv run python manage.py runserver
```

API: `GET /api/library/books/`, `/api/library/books/<slug>/`,
`/api/library/books/<slug>/chapters/<order>/` (all accept `?language=en`).

## Content model

A canonical work is identified by `Book.slug`. Each *language* of that work is a
separate `Book` row sharing the slug, unique by `(slug, language)`. The
`source_type` field distinguishes public-domain originals from AI translations
(reviewed / unreviewed).

<!-- branch-protection probe: safe to delete -->
