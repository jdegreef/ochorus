---
name: add-reading-plan
description: Add a curated reading plan to Ochorus — a multi-book journey (or a single-book plan) that readers follow one chapter a day, shipped as a data tuple in library/plan_seed.py. Use when asked to add, draft, or propose a reading plan, "add a plan", grow the /plans shelf, or turn a set of existing books into a guided journey. Encodes the two things that bite: the per-language prose the coverage test demands, and the chapter-pacing check that keeps a plan readable. This is a living playbook — append new gotchas as we find them.
---

# Adding an Ochorus reading plan

A plan walks a reader through one or more **already-published** books, **one
chapter per day**, days numbered sequentially across the books. Plans are pure
data — no new content, no migration. Two kinds live in
`backend/library/plan_seed.py`:

- **`LAUNCH_PLANS`** — one book, split over N days: `(slug, book_slug, title, description)`.
- **`CURATED_PLANS`** — several books read in full, in order:
  `(slug, title, description, [ordered book slugs])`.

Adding a plan is appending one tuple. The work is in getting the two gotchas
below right, then verifying.

## Recipe

1. **Choose published books.** Every source book must be `is_published: true`
   in English. Confirm against `backend/library/fixtures/content/books/`.
   A curated plan is created only in a language where **every** source book is
   present and published — a partial set is skipped, not shipped half-empty.

2. **Run the pacing check (this is easy to get wrong).** A plan reads **one
   chapter per day**, so the book's chapter structure *is* the plan's daily
   rhythm. Before committing to a book, look at words-per-chapter, not just the
   chapter count:
   - **Treatise-sized chapters are unusable.** `treatises-of-cyprian` has 12
     "chapters" that are whole treatises (one is 41k words) — a day cannot be
     41k words. Exclude such books.
   - **Dozens of tiny sections make a thin, over-long plan.**
     `first-epistle-of-clement` (59 sections, ~200 words each) and
     `on-the-incarnation` (57 sections) yield 100+ two-minute days. Acceptable
     for a deliberately slow "read the Fathers" plan, but say so in the
     description and know the total.
   - Good daily size is roughly 300–2000 words. Ballpark the total days
     (sum of chapters) and sanity-check the span (÷7 ≈ weeks) before writing
     the description's duration claim.

   Quick measurement:
   ```python
   import json, re
   d = json.load(open(f'backend/library/fixtures/content/books/{slug}.en.json'))
   wc = [len(re.sub('<[^>]+>', ' ', r['fields'].get('body_html','')).split())
         for r in d if r.get('model') == 'library.chapter']
   print(len(wc), 'chapters', sum(wc), 'words', sorted(wc)[len(wc)//2], 'median')
   ```

3. **Write the tuple** in `plan_seed.py` (append before `first-steps-for-teens`,
   or anywhere in the list). Match the house voice of the existing
   descriptions: name the authors and what each contributes, lead with a rough
   duration ("Six weeks…", "A longer journey…"). Order the books as a reading
   arc (invitation → journey → testimony; framework → depth; chronological).

4. **Add per-language prose for every language the plan can ship in — or the
   build fails.** This is the trap. `seed_plans` creates a Plan row in **every
   language where all the source books are published**, and takes its
   title/description from `backend/library/data/plan_translations/<lang>.json`.
   A language with no entry does **not** fall back to English — before the
   guard it published an English-titled card on a translated page (the #819
   defect); now `tests_fixture.PlanTranslationCoverageTests` fails the build.

   So: compute the intersection of languages in which **all** source books are
   published (excluding `en`). For each such language, add an entry to that
   `<lang>.json` — quoting the **shipped book titles verbatim** so the card and
   the books it opens agree — **in this same PR**. English-only plans (any one
   source book has no other-language edition) need nothing extra.

   ```python
   import json, glob, collections
   pub = collections.defaultdict(set)
   for fp in glob.glob('backend/library/fixtures/content/books/*.json'):
       for r in json.load(open(fp)):
           f = r.get('fields', {})
           if r.get('model') == 'library.book' and f.get('is_published'):
               pub[f['slug']].add(f['language'])
   books = ['slug-a', 'slug-b', 'slug-c']
   print('ships in:', set.intersection(*(pub[b] for b in books)))  # minus 'en' = needs prose
   ```

5. **Verify, then ship.** Both `plan_seed.py` and `data/plan_translations` are
   declared content roots in `content_sources.json`, so the prerendered
   `/plans/<slug>/` page rebuilds on deploy — nothing extra to wire.
   ```
   cd backend && DJANGO_DEBUG=true uv run python manage.py test \
       library.tests_fixture library.tests_topics_plans
   uv run ruff check .            # backend CI lint gate
   uv run python manage.py makemigrations --check --dry-run   # expect: no changes
   ```
   Data-only, so no `/simplify` or `/code-review` pass is needed. After the
   Render deploy, spot-check the live `/plans/<slug>/` page, and for any
   translated card confirm the `/<lang>/plans/<slug>/` page renders in that
   language rather than the English fallback.

## Gotchas

- **The coverage test is the whole game.** Local tests passing without
  `PlanTranslationCoverageTests` is not enough — run it explicitly. Its error
  names `<language>/<slug>` for every row that would ship English-titled.
- **Plans and Topics share slug spelling but not namespace** — a Topic named
  the same thing does not collide with a Plan. (There is a `voices-of-the-early-church`
  parallel, for instance.) Don't let a Topic of the same name talk you out of a
  plan slug.
- **`seed_plans` needs a migrated, seeded DB.** A fresh worktree's SQLite is
  empty (`no such table: library_book`); that's an environment state, not a
  code fault — the fixture-only `PlanTranslationCoverageTests` validates the
  real invariant without a DB.
- **Books can appear in more than one plan.** `around-the-wicket-gate` backs
  both `the-pilgrims-way` and `first-steps-for-teens` — reuse is fine.
