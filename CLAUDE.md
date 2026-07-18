# Ochorus — conventions for Claude

Ochorus is a free reader for public-domain Christian classics — web + mobile,
multilingual. This file is the short constitution; detailed procedures live in
skills (see **Playbooks**). Keep it short — a long CLAUDE.md is a diluted one.
See also `backend/CLAUDE.md` and `frontend/CLAUDE.md`.

## Architecture (read before "fixing" the frontend)

- **SvelteKit static-adapter SPA + prerendered SEO pages**, talking to a
  *standalone* **Django REST (DRF) API**. Postgres on Supabase, deployed on
  Render. SvelteKit is **not** the server: no `+page.server.ts`, no form
  actions, no `locals`. Page data comes from the Django API via `$lib/api.ts`.
- **Auth**: a Supabase JWT (localStorage) sent as a Bearer token and validated
  by Django (`accounts.authentication.SupabaseJWTAuthentication` — lenient: a
  bad token resolves to anonymous, never a 500). Admin is gated by an email
  allowlist (`accounts.permissions.IsAdminEmail`).

## Content model (this shapes almost everything)

- Books / Sermons / Plans are **per-language rows** sharing one slug
  (`unique(slug, language)`); Topics are one row + a `TopicTranslation`
  side-table. There is **no English fallback** — a language with no row simply
  doesn't show that item.
- AI translations ship `source_type=ai_unreviewed` and wear an "awaiting native
  review" badge until **the user** runs `approve_translation` /
  `approve_sermon_translation`. Never auto-approve; never present an unreviewed
  translation as an original.

## The fixture (the sharp edge)

- `backend/library/fixtures/launch.json` (~50 MB) is the content source of
  truth; the `seed_*` commands upsert it into prod on every deploy.
- The fixture is **natural-key format: rows carry NO integer pks**. A book's
  `"author"` is `["author-slug"]`, a chapter's `"book"` is `["slug", "lang"]` —
  identity is the slug (+ language), so parallel appends cannot collide on a
  key. CI (`tests_fixture`) rejects any `pk` key, duplicate identities, and
  dangling references; the seeds hard-fail on old-format rows.
- **Appending content:** serialize the new rows with Django's serializer using
  `use_natural_primary_keys=True, use_natural_foreign_keys=True` and splice
  them in textually. Never hand-write pks, never `json.dumps`, never round-trip
  the 50 MB file — a full regen is only `backend/scripts/regen_fixture.py`
  (pinned 6-model recipe).
- Because seeds re-upsert every deploy, any field a workflow owns after creation
  (review state, hand-edits) must be **create-only** in the seed — else a deploy
  reverts it. See `backend/CLAUDE.md`.

## Working agreements

- Each task gets its own branch off `origin/main` — a local git **worktree**, or
  the session's `claude/ochorus-dev-*` branch. Never the shared checkout, never
  a Dropbox path. One PR per feature.
- `main` moves fast (many parallel sessions). Fetch and reconcile right before
  merging; expect fixture / migration conflicts. Squash-merge when CI is green
  ("merge when CI passes" is a standing instruction; where the user is steering,
  wait for their go-ahead).
- Run `/simplify`, then `/code-review high` for logic-bearing changes, before
  requesting merge — and fold the findings in.

## Shorthands

- **"pq"** = "process the translation queue" — run the
  `.claude/skills/translation-worker` skill exactly as if the user had typed the
  full phrase (one job per run, end to end).

## Playbooks (don't duplicate them here)

- **founder-kit skills**: `dev-setup`, `deploy`, `verify-local`,
  `ship-content-fix`, `translate-book`, `book-qa`.
- **in-repo `.claude/skills/`**: `translation-worker`, `book-import`,
  `contemporize-book`, `write-biography`.
