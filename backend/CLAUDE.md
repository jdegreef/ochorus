# Ochorus backend — Django conventions

Bounded-context apps: `library` (content), `accounts` (auth), `reading`
(per-user state), `common`. Don't grow a god-module — `admin_views` is a
*package* (split from a 1190-line file); keep it that way.

## Security / auth

- DRF defaults are `SupabaseJWTAuthentication` + **`AllowAny`**. So every
  private/admin endpoint MUST set `permission_classes = [IsAdminEmail]` (or
  stricter) explicitly — forgetting it ships an open, DB-mutating endpoint.
- Supabase exposes the `public` schema over its anon API; RLS is what gates it.
  Before adding a model, confirm RLS covers the new table — one reachable by the
  anon key without RLS is a data leak. (See the RLS notes.)

## Data model

- `TextChoices` for enumerated values (e.g. `Book.SourceType`) — never bare
  string literals (a typo becomes a silent never-matches filter).
- Explicit `related_name` on every FK — the default reverse accessor changes
  silently when a model is renamed.
- Enforce invariants in the DB (`UniqueConstraint`, indexes, `on_delete`), not
  only in Python — the Supabase DB is also touched by the SQL editor and scripts.
- Languages live in the `Language` registry, and it is the *runtime* source:
  identity, Bible code, glossary, readiness thresholds and the live switch. The
  `translate_*` commands read it, which is what lets an admin add a language
  without a deploy. `library/language_seed.py` is the repo-owned seed for the
  built-in six (identity re-asserted every deploy); a language added from the
  admin is DB-owned and the seed never touches it.
- Content HTML is sanitized to a tag allowlist **once on ingest**
  (`ingest.clean_fragment`); the reader trusts stored HTML. Never store
  un-sanitized HTML; never sanitize hopefully at render.

## Migrations & seeds

- Migrations are immutable once deployed — never edit one that ran against prod.
  Parallel sessions cause divergent leaves; resolve with a merge migration,
  don't renumber.
- `manage.py release` runs the deploy chain: migrate → seed_if_empty →
  backfill_body_text → apply_body_corrections → seed_books → seed_plans →
  seed_sermons → seed_author_translations → seed_topics →
  backfill_search_vectors → trim_search_log. Seeds are idempotent and
  **re-run every deploy**.
  backfill_search_vectors is last on purpose: vectors derive from body_text
  and bake in seed-created rows (library/fts.py).
- Therefore any field a workflow owns after creation — review state
  (`source_type`), an approver's edit — must be **create-only** in the seed, or
  a deploy walks it back. (This bit us; there's a regression test guarding it.)
- A fresh DB loads the fixture *after* migrate runs, so a data migration that
  depends on fixture rows no-ops on a rebuild — put the same fact in the
  fixture, not only the migration. (The historical pk-parsing migrations no-op
  loudly on the natural-key fixture via format guards — keep that pattern for
  any new fixture-reading migration.)
- For models with no fixture (AuthorTranslation), the fact lives in an
  idempotent seed step instead: translated author bios ship (and get
  corrected) as files under `library/migrations/data/author_bios_<lang>/`
  (short.json + `<slug>.html`); `seed_author_translations` upserts unreviewed
  rows from them. Reviewed rows keep the approver's wording — only a
  still-empty field lands there, re-gating review. No new migration per batch,
  and don't hand-edit prod rows: the files win on the next deploy.
- Chapter/Sermon carry stored `search_vector` tsvectors kept fresh by `save()`
  hooks (library/fts.py); the release backfill repairs **NULL vectors only**.
  A data migration or command that changes chapter/sermon text, titles, or
  author names via `queryset.update()` or historical-model `.save()` (which
  lacks the hooks) leaves vectors STALE, not NULL — search silently keeps
  matching the old text. Such a change must also NULL `search_vector` on the
  touched rows (the release backfill then repairs them) or run
  `manage.py backfill_search_vectors --all`.

## Shared logic

- Content-quality heuristics live once in `library/qa.py` (`chapter_flags` +
  thresholds), shared by the admin content audit and the import preview. Don't
  re-implement them — a second copy drifts (it already did once).

## Dev

- `cd backend && DJANGO_DEBUG=true uv run python manage.py <cmd>`; tests:
  `manage.py test`. Give each worktree's runserver its own port — a silent
  "port in use" makes your curls hit another clone's DB.
