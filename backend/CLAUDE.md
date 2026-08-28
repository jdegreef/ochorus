# Ochorus backend — Django conventions

Bounded-context apps: `library` (content), `accounts` (auth), `reading`
(per-user state), `common`. Don't grow a god-module — `admin_views` is a
*package* (split from a 1190-line file); keep it that way.

## Security / auth

- DRF defaults are `SupabaseJWTAuthentication` + **`AllowAny`**. So every
  private/admin endpoint MUST set `permission_classes = [IsAdminEmail]` (or
  stricter) explicitly — forgetting it ships an open, DB-mutating endpoint.
- Supabase exposes the `public` schema over its anon API; RLS is what gates it —
  one table reachable by the anon key without RLS is a data leak. Every public
  table has RLS enabled (no policies = deny-all for non-owners; Django connects
  as the table owner and bypasses it), and the anon/authenticated roles hold no
  grants on the schema at all.
  **You no longer have to remember this**: `accounts/tests_rls.py` reads the live
  catalogue and fails on any table without RLS, naming the model and the exact
  `ALTER` to write. That test is the rule; this bullet is just context. Nineteen
  tables were once missed precisely because six were done by hand and nothing
  checked.

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
- Content HTML is sanitized to a tag allowlist **at every write path**
  (`library/sanitize.py`); the reader trusts stored HTML and renders it with
  `{@html}`. Never store un-sanitized HTML; never sanitize hopefully at render.
  Two profiles, and picking the wrong one is destructive:
  `clean_fragment` for chapter/sermon bodies (narrow, **no attributes**), and
  `clean_bio_html` for author bios, which legitimately carry
  `<aside class="prayer">` callouts, `<cite>` attributions and internal links —
  the chapter profile would unwrap 323 asides, 478 cites and 7 links across the
  172 bio files, deleting a feature silently.
  Model output is untrusted input: the `translate_*` / `contemporize_book`
  commands sanitize before storing (a `</content></invoke>` artifact reached a
  live page before they did). The Django admin's HTML textareas sanitize via
  their `ModelForm`.
  Sanitizing is deliberately **not** in `Model.save()`: BeautifulSoup
  round-trips entities (`&quot;` → `"`), which renders identically but would
  rewrite 743 of 3,033 stored rows on the next deploy. `tests_sanitize.py` is
  the enforcement instead — it scans every shipped row, so a write path that
  forgets fails the build rather than shipping.

## Migrations & seeds

- **New seed data needs a home in `library/content_sources.json`.** The reader is
  prerendered, so content only goes live when something notices it changed. That
  file lists the roots holding reader-visible content; render.yaml's
  `buildFilter`, the `/api/health/` content digest and the web build's prebuild
  gate all derive from it, and `tests_fixture` fails if they disagree. Data
  outside those roots ships to the API and its pages **never rebuild** — which is
  what happened to plan and topic prose when they moved into `data/`.
  `manage.py content_version` prints the digest; compare it with
  `/api/health/`'s to tell "the reader is stale" from "something else is wrong".
  A root is normally a directory; a single file is allowed and is how the seed
  DATA modules (`topic_seed.py`, `plan_seed.py`, `corrections.py`) are covered —
  keep reader-visible seed literals in those, not in the `seed_*` commands, which
  nothing watches.
  **You no longer have to remember this**: `tests_fixture.ReleaseProseSourceCoverageTests`
  walks the release chain, follows its `library` imports, finds the modules
  carrying prose, and fails on any that is neither a declared root nor explicitly
  exempt (with a reason). `corrections.py` was missing for exactly as long as
  nothing checked — `apply_body_corrections` rewrites chapter and sermon
  `body_html` on every deploy, so a prose fix reached the API, moved no digest,
  and never rebuilt the page showing it.
- **Reviewing a content diff: `manage.py content_diff`.** Raw, a one-word fix in
  a chapter is a 36 KB diff of escaped HTML (the body is a single JSON line); as
  prose it is one line that names the chapter and paragraph. `--install` wires
  the same rendering into `git diff` for this clone.
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
  (`<slug>.short.txt` + `<slug>.html`, one file per author per field — the two
  surviving `short.json` are empty migration-0024 inputs, never written);
  `seed_author_translations` upserts unreviewed
  rows from them. Reviewed rows keep the approver's wording — only a
  still-empty field lands there, re-gating review. No new migration per batch,
  and don't hand-edit prod rows: the files win on the next deploy.
- **Three columns are derived from `body_html`, and `save()` keeps all three**:
  `body_text`, `word_count` (both `library/text.py`) and `search_vector`
  (library/fts.py). A body written THROUGH the model is therefore in step, and
  a derived column is not a fact a fixture gets to assert — don't compare one
  against a fixture value in a seed, or the seed "repairs" it and `save()`
  derives it straight back, every deploy, forever.
  The routes that BYPASS `save()` are the hazard: `loaddata`, a
  `queryset.update()`, a data migration's historical model. Each column has a
  release-chain keeper for them (`backfill_body_text`, `backfill_word_count`,
  `backfill_search_vectors`) but **all three repair only what is empty** — so a
  bypassing route that writes a WRONG non-empty value repairs nowhere, and must
  set the derived columns itself (the quote-mark migrations show the shape).
  The tsvector is the sharpest case: a bulk text change leaves vectors STALE
  rather than NULL, so search silently keeps matching the old prose. NULL
  `search_vector` on the touched rows, or run
  `manage.py backfill_search_vectors --all`.

## Shared logic

- Content-quality heuristics live once in `library/qa.py` (`chapter_flags` +
  thresholds), shared by the admin content audit and the import preview. Don't
  re-implement them — a second copy drifts (it already did once).
- English *source* defects (extraction artifacts, OCR slips, invented text) live
  in `library/english_audit.py`, shared by `import_ochorus` (which audits each
  book it writes) and `manage.py audit_english`. Every check carries a precision
  test in `tests_english_audit.py` — the first version of this scanner reported
  8,917 findings, nearly all false, and a report nobody trusts gets skimmed.
  `tests_english_audit.py` also ratchets the per-class counts, so an import
  can't quietly add defects. See the `english-qa` skill for the repair channels.

## Dev

- `cd backend && DJANGO_DEBUG=true uv run python manage.py <cmd>`; tests:
  `manage.py test`. Give each worktree's runserver its own port — a silent
  "port in use" makes your curls hit another clone's DB.
