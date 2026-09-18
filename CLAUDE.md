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
- A **young-reader edition** is a separate same-language Book row, not a
  language variant: slug `<base>-children` / `<base>-teens`, title suffixed
  "(For Children)" / "(For Teens)", parent author kept. Nothing in the model
  joins it to the full text — the slug convention IS the link (mirrors how the
  Modern English edition is derived from slug + language, not a FK), and the
  book page's `editions` cross-link derives the full ⇄ teens ⇄ children family
  from it (`serializers.sibling_editions`). So don't reuse one of those suffixes
  for an unrelated work, and don't drop the convention without checking who
  reads it.
- AI translations ship `source_type=ai_unreviewed` and are promoted to reviewed
  only when **the user** runs `approve_translation` / `approve_sermon_translation`.
  Never auto-approve. This review state is **admin-only**: it drives the review
  dashboard and readiness reports, and is deliberately **never shown to readers**
  — there is no public "awaiting native review" / AI-translation badge. Do not
  add one back (a founder product decision: native + AI QA happen through the
  admin system, not by warning the reader).

## Covers

- **A hand-made cover is frozen.** The designed rasters under `/covers/<slug>.<ext>`
  carry a judgement no data records, so nothing may redraw one: they are
  registered with their digests in `library/designed_covers.py` and two fixture
  gates fail the build if a file's bytes move or a new one goes unregistered.
  Every other cover — plate, painting, derived ground, webp variant, og twin —
  IS output, and its script may draw it again. Replacing a designed cover on
  purpose is a two-line diff: new file, new digest.
- A cover with WORDS in it serves one language. A wordless ground under
  `/covers/art/` serves them all, because `BookCover` draws the title over it per
  edition. So a translated edition never wears another edition's designed file —
  the sixteen works in `DERIVED_GROUND` keep the English cover in English and
  wear a crop of its photography everywhere else (`scripts/build_derived_grounds.py`).

## Sourcing (be reasonable, not rigid)

- The **reader's classics** — the book/sermon texts themselves — are public
  domain. That's the product and the legal footing for reproducing whole works;
  keep it.
- **Everything around them — author photos, cover art, supplementary images —
  does NOT have to be strictly public domain.** Freely-licensed (Creative
  Commons; the `Author.photo_attribution` + `photo_source_url` fields exist to
  carry the credit and show it on the page), offered for reuse, or plainly
  low-risk is fine. Use judgement; don't default to a monogram or skip a good
  image out of excess PD-purism. Reserve the caution for what's actually risky —
  clearly commercial, watermarked/stock, or an image someone is actively
  policing. When it's a genuine judgement call, surface it to the founder rather
  than silently dropping the asset. (Founder steer, 2026-09-15.)

## The fixture (now a friendly edge)

- Content lives in `backend/library/fixtures/content/` — **one file per work**:
  `authors.json`, `books/<slug>.<language>.json` (book row then its chapters),
  `sermons/<slug>.<language>.json`, `plans.json`. Natural-key format: **no
  integer pks**; a book's `"author"` is `["author-slug"]`, a chapter's
  `"book"` is `["slug", "lang"]`. See `library/content_fixtures.py`.
- **Adding a work = writing ONE NEW FILE** (serialize with Django's serializer,
  `use_natural_primary_keys=True, use_natural_foreign_keys=True`; book row
  first, then chapters). No splicing, no pk math, no tail conflicts — parallel
  sessions cannot collide. New authors are appended to `authors.json`.
- CI (`tests_fixture`) rejects pk rows, duplicate identities, dangling refs,
  and files whose name/contents disagree; the seeds hard-fail on old-format
  rows. Full regens only via `backend/scripts/regen_fixture.py`.
- Because seeds re-upsert every deploy, any field a workflow owns after creation
  (review state, hand-edits) must be **create-only** in the seed — else a deploy
  reverts it. See `backend/CLAUDE.md`.

## Working agreements

- Each task gets its own branch off `origin/main` — a local git **worktree**, or
  the session's `claude/ochorus-dev-*` branch. Never the shared checkout, never
  a Dropbox path. One PR per feature.
- **One job per branch: suffix the session branch, `claude/ochorus-dev-<id>-<job>`.**
  Two sessions were once given the same `claude/ochorus-dev-*` name, so the
  second one's book landed on the branch of the first one's open sermon PR and
  the two shipped together under a sermon-shaped title — one-PR-per-feature is
  not achievable from inside a session when the branch is shared. If you do land
  on someone else's branch: **rebase onto their commits, never force-push over
  them**, and settle whether your own file survived with `md5` against
  `git show HEAD:<path>` — a rebase that replaces your file with theirs leaves
  the tree *clean*, so `git status` will tell you nothing is wrong.
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
- **in-repo `.claude/skills/`**: `translation-worker`, `content-edit-worker`
  (the admin book page's "Fix title" queue), `book-import`, `english-qa`,
  `contemporize-book`, `write-biography`, `quote-extraction`, `write-article`,
  `page-design` (page anatomy + the design-consistency backlog).
