---
name: dev-setup
description: Bootstrap (or verify) a local Ochorus development environment in an isolated git worktree — branch, env files, dependencies, seeded database, launch config. Use when starting any Ochorus code task, when a fresh worktree is needed, or when a local environment is behaving oddly and needs its setup verified. Idempotent — safe to run as a checklist against an existing worktree.
---

# Ochorus dev environment setup

Every code task runs in its own worktree off `main` (per the standing
worktree directive). NEVER develop in a Dropbox path; the canonical clone is
`~/dev/ochorus`.

## 1. Worktree

```bash
cd ~/dev/ochorus && git fetch origin && git worktree add -b <branch> ../ochorus-<task> origin/main
cd ~/dev/ochorus-<task>
```

## 2. Env files (gitignored — every worktree needs its own)

```bash
# frontend/.env
printf 'PUBLIC_API_BASE_URL=http://localhost:8000\nPUBLIC_SUPABASE_URL=\nPUBLIC_SUPABASE_ANON_KEY=\n' > frontend/.env
# backend/.env — CORS must list every port you'll serve the frontend from
printf 'DJANGO_DEBUG=true\nCORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5180,http://localhost:4173,http://127.0.0.1:4173\n' > backend/.env
```

Supabase keys stay empty locally — the login UI hides itself and everything
else degrades gracefully. Only set them when specifically testing auth/sync.

## 3. Dependencies

```bash
cd backend  && uv run python manage.py check        # uv creates .venv on first run
cd frontend && npm install && npm run prepare       # svelte-kit sync
```

## 4. Database (local SQLite, no services needed)

```bash
cd backend
DJANGO_DEBUG=true uv run python manage.py migrate
DJANGO_DEBUG=true uv run python manage.py seed_if_empty        # 36 books / ~527 chapters from fixture
DJANGO_DEBUG=true uv run python manage.py backfill_body_text   # fixture loads bypass save(); search needs this
DJANGO_DEBUG=true uv run python manage.py seed_plans           # reading plans
```

## 5. Launch config (worktree-local .claude/launch.json)

Three servers; ports must match the CORS list above:
- `ochorus-backend`: `uv run python manage.py runserver 8000` (cwd backend)
- `ochorus-frontend`: `npm run dev -- --port 5180 --strictPort` (cwd frontend)
- `ochorus-web-preview`: `npm run preview -- --port 4173 --strictPort` (cwd frontend)

## 6. Smoke test

```bash
curl -s http://localhost:8000/api/health/                                  # {"status":"ok"}
curl -s "http://localhost:8000/api/library/books/?language=en" | head -c 120  # book JSON
cd frontend && npm run check                                               # 0 errors
```

## Gotchas

- `npm run check` fails with "no exported member 'PUBLIC_API_BASE_URL'" →
  frontend/.env is missing (step 2).
- Preview-panel MCP tools bind to the session's original project root, not the
  worktree — start worktree servers via Bash (`nohup ... &`) instead.
- Cleanup when the task ships: `git worktree remove ../ochorus-<task>`.
