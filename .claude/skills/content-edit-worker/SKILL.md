---
name: content-edit-worker
description: Process the Ochorus content-edit job queue — GitHub issues labeled content-edit, filed by the admin book page's "Fix title" control — one job per run, end to end (edit the fixture → ship via PR → close the issue). Use when asked to "process the content-edit queue", "work the content-edit jobs", "do the title fixes", or when a content-edit issue needs handling. This is a living playbook — append new job types and failure modes as we find them.
---

# Content-edit queue worker

**One run = at most ONE job, end to end.** The queue lets an admin flag a bad
chapter title and walk away; this skill is the contract that makes a fresh
session turn that flag into a shipped fix reliably. Parallel sessions may take
different jobs.

## Why this is a queue, not a live edit

A chapter title is **fixture-owned prose**, not a live DB field (see
`backend/CLAUDE.md`). Two facts force the shape of the fix:

1. The reader is **prerendered from committed fixtures** — a live DB edit moves
   no content digest, so the page never rebuilds and the fix never reaches the
   site.
2. `seed_books` **syncs every chapter to the fixture on deploy** (by `order`:
   drifted title/body updated through `save()`, new orders appended, nothing
   deleted or renumbered — since 2026-09-23; before that it synced nothing and
   every job needed a data migration too). So a DB-only edit is walked back on
   the next deploy, and a fixture edit is all a chapter fix needs.

So the fix is **one fixture edit in one PR** (below), and prod holds no credentials to
author that — which is why the admin files a job and you ship it. GitHub is the
queue because worker sessions can reach GitHub but not the Render API. State is
derived: **queued** = open issue, **in progress** = `in-progress` label,
**done** = you closed the issue (the title then deploys via the fixture).

Backend that files these: `library/admin_views/content_jobs.py`.

## The job

Every job is a **`content-edit`**-labelled issue with a deterministic title and a
JSON block in the body naming the target. One open job per `(kind, target)` — the
filer guards duplicates, per kind (a title and a body job for the same chapter can
coexist). Three kinds share the queue:

- **`retitle`** — a chapter title. Title `[edit] retitle book:<slug>/<lang>#<order>`,
  JSON `{"job": "retitle", "type": "book", "slug": …, "language": …, "order": N}`.
  The body quotes the current and proposed titles. **The fix is below** (steps 4–5).
- **`revise`** — a chapter's **text**. Title `[edit] revise book:<slug>/<lang>#<order>`,
  JSON `{"job": "revise", …, "order": N}`. The body quotes the reporter's note (what's
  wrong). Same fixture-only shape as a retitle, but the body is sanitised prose:
  - **Edit 1 (fixture):** set `body_html` of the `order` chapter in
    `books/<slug>.<lang>.json`. Sanitise to the **chapter** profile
    (`sanitize.clean_fragment` — narrow, no attributes; NOT `clean_bio_html`), and
    write the **settled form** (`corrections.settled_chapter_body`), or
    `apply_body_corrections` reverts your change on the next deploy (see
    `backend/CLAUDE.md`, "the sibling rule for prose").
  - `seed_books` carries it to prod through `save()`, so `body_text`, `word_count`
    and `search_vector` all refresh. Confirm with `manage.py content_diff`.
- **`rewrite-bio`** — an author biography. Title `[edit] rewrite-bio author:<slug>/<lang>`
  (no `#order`), JSON `{"job": "rewrite-bio", "type": "author", "slug": …, "language": …}`.
  The body carries an optional emphasis note. Use the **`write-biography`** skill, and
  the **`clean_bio_html`** sanitiser profile (bios carry `<aside class="prayer">`,
  `<cite>` and internal links — the chapter profile would strip them):
  - **English (`en`):** set the `Author` row's `bio` (short plain text) + `bio_html`
    (long-form HTML). Ships in `authors.json` alone — `author_sync` makes both fixture-wins
    on deploy (since 2026-09-23); no migration.
  - **Translated:** an `AuthorTranslation` ships as files under
    `migrations/data/author_bios_<lang>/` (`<slug>.short.txt` + `<slug>.html`);
    `seed_author_translations` upserts unreviewed rows on deploy — no per-batch migration,
    the files win. Never hand-edit a reviewed row (see `backend/CLAUDE.md`).

The retitle protocol below is the template; a `revise`/`rewrite-bio` job follows the
same claim → worktree → edit → verify → ship loop, with the per-kind edits above.

## Protocol (follow in order)

1. **List** open issues labeled `content-edit` (GitHub MCP `list_issues`,
   oldest first). None → report "queue empty" and stop.
2. **Claim.** Pick the oldest un-claimed job. If it carries `in-progress`
   updated < 6h ago, it's a live claim — skip to the next; ≥ 6h is a stale
   claim (crashed run) you may reclaim (comment, keep the label). Otherwise add
   the `in-progress` label and comment that you're on it.
3. **Set up** an isolated worktree off `origin/main` (see the `dev-setup`
   founder-kit skill). One PR per job.
4. **Edit the fixture (the source of truth — fresh installs AND prod).** In
   `backend/library/fixtures/content/books/<slug>.<language>.json`, find the
   `library.chapter` row whose `fields.order` == the job's `order` and set its
   `fields.title` to the proposed title. A title is **plain text** — no
   sanitiser, no `settled_*` / body-correction concerns, and it does **not**
   touch `body_html`/`body_text`/`word_count` (those stay as they are).
5. **No migration.** `seed_books` updates the live row on deploy through
   `save(update_fields=["title"])`, which refreshes the weight-A search vector.
   Never "help" with `queryset.update()` anywhere — it leaves search stale.
6. **Verify locally.** Run `manage.py seed_books` against a DB seeded BEFORE
   your edit: it should log `~ <slug> [<lang>] chapters: 0 added, 1 updated`,
   the chapter reads the new title, and a search for a distinctive word of it
   finds it. `manage.py content_diff` renders the fixture change as one line.
   A fixture change triggers the web build too (render.yaml `buildFilter`), and
   the prebuild gate waits for the API to hold it, so no touch is needed.
   After deploy, check the static page. If it's stale, add a marker per
   `frontend/prerender-refresh/README.md`.
7. **Ship.** Open a PR (`/simplify` + `/code-review high` if anything is
   logic-bearing; a plain retitle usually isn't). Reference the issue. On green,
   squash-merge (the user's standing instruction), then **close the issue**.

## Gotchas

- **Only a chapter SET change needs a migration.** Deleting, merging or
  renumbering chapters is beyond `seed_books` (order is a public contract) — that
  is not a content-edit job; hand it back.
- **Don't hand-edit prod.** The fixture is the source of truth and `seed_books`
  carries it to prod. Editing the DB directly leaves no record and is walked back
  on the next deploy.
- **Order is a public contract.** Never change a chapter's `order` to "fix" a
  title — readers' saved positions and prerendered URLs key on it.
