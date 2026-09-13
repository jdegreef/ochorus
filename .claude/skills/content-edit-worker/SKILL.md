---
name: content-edit-worker
description: Process the Ochorus content-edit job queue — GitHub issues labeled content-edit, filed by the admin book page's "Fix title" control — one job per run, end to end (edit the fixture + write a data migration → ship via PR → close the issue). Use when asked to "process the content-edit queue", "work the content-edit jobs", "do the title fixes", or when a content-edit issue needs handling. This is a living playbook — append new job types and failure modes as we find them.
---

# Content-edit queue worker

**One run = at most ONE job, end to end.** The queue lets an admin flag a bad
chapter title and walk away; this skill is the contract that makes a fresh
session turn that flag into a shipped fix reliably. Parallel sessions may take
different jobs — but see the migration-collision note under **Ship**.

## Why this is a queue, not a live edit

A chapter title is **fixture-owned prose**, not a live DB field (see
`backend/CLAUDE.md`). Two facts force the shape of the fix:

1. The reader is **prerendered from committed fixtures** — a live DB edit moves
   no content digest, so the page never rebuilds and the fix never reaches the
   site.
2. `seed_books` deliberately **syncs neither** a fixture chapter nor an existing
   live row — so a DB-only edit drifts from the fixture and is walked back on a
   fresh install, and a fixture-only edit never reaches the existing prod row.

So the fix is **two edits in one PR** (below), and prod holds no credentials to
author that — which is why the admin files a job and you ship it. GitHub is the
queue because worker sessions can reach GitHub but not the Render API. State is
derived: **queued** = open issue, **in progress** = `in-progress` label,
**done** = you closed the issue (the title then deploys via the fixture +
migration).

Backend that files these: `library/admin_views/content_jobs.py`.

## The job

- Label **`content-edit`**, deterministic title
  **`[edit] retitle book:<slug>/<lang>#<order>`**, and a JSON block in the body:
  `{"job": "retitle", "type": "book", "slug": "...", "language": "...", "order": N}`.
  The body also quotes the current and proposed titles.
- One open job per `(slug, language, order)` — the filer guards duplicates.
- Today the only job is **`retitle`** (a chapter title). Append new kinds here.

## Protocol (follow in order)

1. **List** open issues labeled `content-edit` (GitHub MCP `list_issues`,
   oldest first). None → report "queue empty" and stop.
2. **Claim.** Pick the oldest un-claimed job. If it carries `in-progress`
   updated < 6h ago, it's a live claim — skip to the next; ≥ 6h is a stale
   claim (crashed run) you may reclaim (comment, keep the label). Otherwise add
   the `in-progress` label and comment that you're on it.
3. **Set up** an isolated worktree off `origin/main` (see the `dev-setup`
   founder-kit skill). One PR per job.
4. **Edit 1 — the fixture (source of truth; fixes a fresh install).** In
   `backend/library/fixtures/content/books/<slug>.<language>.json`, find the
   `library.chapter` row whose `fields.order` == the job's `order` and set its
   `fields.title` to the proposed title. A title is **plain text** — no
   sanitiser, no `settled_*` / body-correction concerns, and it does **not**
   touch `body_html`/`body_text`/`word_count` (those stay as they are).
5. **Edit 2 — a data migration (reaches the existing prod row).** Add a
   migration under `backend/library/migrations/` that loads the chapter and
   goes **through `save()`** so the derived search vector refreshes:

   ```python
   def _retitle(apps, schema_editor):
       Chapter = apps.get_model("library", "Chapter")
       # Guard on the OLD title: idempotent (a rerun no-ops), safe on a fresh
       # DB (the fixture already set the new title, so this no-ops), and it
       # won't clobber a later hand-edit that moved on from the old wording.
       ch = Chapter.objects.filter(
           book__slug="<slug>", book__language="<lang>", order=<order>,
           title="<old title>",
       ).first()
       if ch is not None:
           ch.title = "<new title>"
           ch.save(update_fields=["title"])   # NOT queryset.update()
   ```

   **`save()`, never `queryset.update()`.** `title` is weight-A in the chapter
   search vector (`library/fts.py`); a bulk `update()` bypasses `save()` and
   leaves search matching the OLD title (stale, not null — the backfill won't
   repair it). `save(update_fields=["title"])` triggers `fts.refresh_chapter`.
   Historical model in a migration has no custom `save`, so if you write the
   migration against `apps.get_model` you must refresh the vector yourself — the
   simplest correct form is to import the real model in the RunPython (the
   quote-mark migrations show the shape), or null the row's `search_vector` and
   let `backfill_search_vectors` rebuild it. When in doubt, follow an existing
   title/quote-mark migration in this repo.
6. **Verify locally.** `manage.py migrate`, then confirm the chapter reads the
   new title AND that a search for a distinctive word of the new title finds it
   (proves the vector refreshed). `manage.py content_diff` renders the fixture
   change as one readable line.
7. **Ship.** Open a PR (`/simplify` + `/code-review high` if anything is
   logic-bearing; a plain retitle usually isn't). Reference the issue. On green,
   squash-merge (the user's standing instruction), then **close the issue**.

## Gotchas

- **Migration-leaf races.** `main` moves fast and every job adds a migration, so
  expect leaf collisions on merge. Standing decision: **accept-and-cure** — add a
  merge migration and redeploy; do not renumber. See the `deploy` founder-kit
  skill.
- **Both edits or neither ships correctly.** Fixture-only → the live row never
  changes. Migration-only → a fresh install (and `seed_books`' `chapter_drift`
  warning) disagrees with prod. The PR is incomplete without both.
- **Don't hand-edit prod.** The fixture is the source of truth; the migration is
  how the decision reaches an already-seeded DB. Editing the DB directly leaves
  no record and is walked back.
- **Order is a public contract.** Never change a chapter's `order` to "fix" a
  title — readers' saved positions and prerendered URLs key on it.
