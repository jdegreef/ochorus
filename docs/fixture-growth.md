# The content fixture: what it costs, and what to do about it

**Status:** design note, August 2026; §4 updated after the two real problems it
identified were acted on. Written to close finding #50 of the August 2026 code
review, which asked for a projection and an evaluation of three options before
anyone starts moving 79 MB of JSON around.

**Conclusion up front: do not restructure the fixture.** The review's stated
mechanism — "grows with whole-file rewrites per edit" — does not hold, and the
measurement below shows the alternative it proposed would make the repository
*larger*. There are two real problems in this area, neither of which is repo
size, and both have cheaper fixes than a layout migration.

---

## 1. Where things actually stand

Measured on `main`, August 2026:

| | |
|---|---|
| `backend/library/fixtures/content/` | **79 MB** across **258** files |
| — books | 71 MB, 140 files, **513 KB** average |
| — sermons | 7.6 MB, 116 files |
| Largest file | 7.1 MB (`sermons-on-several-occasions.en.json`, 144 chapters) |
| Files over 1 MB | 9 |
| Longest single line | **190,000 characters** (one chapter's `body_html`) |
| Whole-repo pack | **55.6 MB**, of which the fixture's entire history is **26.1 MB** (533 blob versions) |
| Fixture commits, last 90 days | 39 |
| Works × locales today | 64 works; en 64, sw 18, lg 18, es 16, ar 11, pt 10, uk 3 |
| Published rows the fixture seeds | 134 books / 2,475 chapters / 116 sermons |

The layout is one file per work per language (`books/<slug>.<language>.json`,
book row then its chapters), natural keys, no integer pks. That shape was chosen
so adding a work is writing one new file — no splicing, no pk arithmetic, and no
way for two parallel sessions to collide. `library/content_fixtures.py` defines
it, `tests_fixture` enforces it, `scripts/regen_fixture.py` is the only thing
allowed to rewrite it wholesale.

---

## 2. The premise, tested

The concern was that a one-word fix rewrites a multi-megabyte JSON file, so the
repository grows by something like that much every time. Git does not work that
way, and it is worth having the number rather than the intuition.

**Experiment.** Take the largest fixture (7.1 MB, 144 chapters). Build two
repositories from the same content — one with today's whole-file layout, one
split into a file per chapter. Apply ten realistic `english-qa`-style edits
(one word changed in one chapter each), committing each. Repack both.

```
whole-file : base   1680 KB ->   1686 KB   (+6 KB for 10 edits)
per-chapter: base   1830 KB ->   1836 KB   (+6 KB for 10 edits)
```

Both layouts cost **~600 bytes per edit**. Delta compression finds the changed
region regardless of how the file is cut up, so splitting buys nothing — and the
per-chapter repository starts **9% larger**, because 144 files carry 144 lots of
object overhead and lose the cross-chapter deltas that a single blob gets for
free.

Put against real churn: the last 90 days saw 39 fixture commits, +46,600 /
−3,305 lines. The additions are overwhelmingly *new works and new translations*
— genuinely new bytes, which any layout must store — and the deletions are the
edit traffic the finding was about. At ~600 bytes each, that traffic costs
tens of kilobytes a quarter. It is not the problem.

**The one place the intuition is right** is the working clone *between* garbage
collections. An edit writes a fresh loose object holding the entire file, so ten
edits to the 7 MB book leave ~21 MB of loose objects — about **2.1 MB per
edit** — until `git gc` runs and folds them down to 6 KB. Git triggers that
automatically at 6,700 loose objects, so it is self-correcting, costs local disk
only, and never reaches the remote (push sends deltas). Worth knowing when a
worktree looks unaccountably fat; not worth a migration.

---

## 3. What the growth curve actually looks like

Repository size tracks **content volume**, not file layout. Today 79 MB of
working-tree fixture — *and every past version of it* — packs to 26.1 MB, a
ratio of about 0.33; JSON-wrapped HTML prose compresses roughly threefold. The
roadmap is 8 locales across 65+ works, plus contemporized English editions:

| | Book files | Working tree | Packed history |
|---|---|---|---|
| Today | 140 | 79 MB | 26 MB |
| Full 8×65 matrix | ~520 | ~265 MB | ~90 MB |
| …plus `en-modern` | ~585 | ~300 MB | ~100 MB |

Translations delta poorly against each other — different languages share almost
no byte sequences — so this scales close to linearly with (works × locales), and
the projection above deliberately assumes no cross-locale delta benefit at all.

A clone in the low hundreds of megabytes is slow to fetch once and ordinary
thereafter. GitHub's advisory threshold is 1 GB and its hard limit 5 GB, so the
full roadmap lands at roughly a tenth of the advisory figure. **Revisit this
note if the packed repository passes ~500 MB**, which would mean roughly
doubling both the locale count and the catalogue beyond what is planned.

---

## 4. The two real problems

Neither is size, and neither needs the fixture restructured.

**(a) The diffs are unreviewable.** — *fixed, August 2026.* A chapter's
`body_html` is one line, up to 190,000 characters, so any change to it rendered
as that entire line removed and re-added. Measured on `humility-2.en.json`: a
one-word fix printed **36 KB** of escaped HTML with the change buried in it
(`--word-diff` only got it to 24 KB). Nobody reviews that, which is the wrong
outcome for a pipeline whose whole premise is that a human approves AI
translations before they ship (`source_type=ai_unreviewed` until someone runs
`approve_translation`).

Fixed by rendering fixtures as prose rather than by moving them:
`library/content_prose.py` emits one numbered line per paragraph. The same
one-word fix is now **1.3 KB** and reads:

```
@@ -245,3 +245,3 @@ book.is_published: True
 [12.1] “He who humbles himself will be exalted.” Luke 14:11, 18:14.
-[12.2] “Humble yourselves before the Lord, and he will exalt you.” James. 4:10.
+[12.2] “Humble yourselves before teh Lord, and he will exalt you.” James. 4:10.
 [12.3] “Humble yourselves, therefore, under the mighty hand of God…” 1 Peter 5:6.
```

Two ways in: `manage.py content_diff`, which needs no configuration (CI, PR
review, fresh clones), and `git diff` itself via `.gitattributes` — that one
needs a one-time `manage.py content_diff --install`, because git refuses to let
a repository install a textconv command (it would be code execution on clone).
A bonus that turned out to matter: a reformat-only change now reports
"formatting only", so a 193-line churn that ships no content edit says so.

**(b) Which commits rebuild the reader** — *the correctness half fixed, the cost
half not.* Two separate problems were tangled here.

*The correctness half, now fixed:* `buildFilter` named only
`backend/library/fixtures/**`, so plan prose, topic prose and translated author
bios — all of which reach prerendered pages — rebuilt **nothing** when they
changed. Their pages kept the previous prose until an unrelated commit happened
to trigger a build. The roots now live in `library/content_sources.json`, which
the filter, the `/api/health/` content digest and the web build's prebuild gate
all derive from, and `tests_fixture` fails if they disagree.

*The cost half, not fixed:* correcting one typo still re-prerenders all ~2,700
content pages, because that is what prerendering means — the pages that render
that content have to be rebuilt. Trigger changes cannot help; only incremental
prerendering can, and `adapter-static` has no such mode. Doing it would mean
diffing the content digest against the previous build, computing which routes
the changed works appear on (a book page, its chapters, its author, its topics,
the shelves, the feed, the sitemap), and prerendering only those — with a
correctness risk that is exactly the one this repo keeps hitting: a page that
should have rebuilt and didn't. **Not recommended until build time is actually
hurting.** If it is, the first cheap step is measuring which of the ~2,700 pages
dominate, not building the machinery.

---

## 5. The three options the review asked about

**(a) One file per chapter — rejected.** Measured above: no packed-size benefit,
9% larger baseline, and it multiplies 258 files into roughly 2,800. It would
narrow the parallel-session conflict boundary from a work to a chapter, but the
current boundary is already a work, and a work is translated by one session at a
time — so the conflict it prevents is one we do not have. It would also mean
rewriting `content_fixtures.py`, `tests_fixture` and `regen_fixture.py`, and
re-verifying that `manage.py release` still seeds correctly inside the Docker
build context.

**(b) Git LFS — rejected, for now.** LFS solves *pack* growth, which the
measurement shows we do not have. It would add a required client-side install,
break `git show HEAD:<path>` and the plain-file reads that `content_fixtures.py`
and the CI gate depend on, and put content behind a bandwidth quota. Its cost is
paid by everyone on every clone; its benefit here is currently zero.

**(c) Object-store-backed content, metadata only in git — rejected, and the
most expensive of the three.** `manage.py release` seeds from files in the
Docker build context; moving bodies to an object store means the release chain
grows a network dependency at deploy time, a fresh-DB rebuild stops being
reproducible from a checkout, and the fixture stops being the auditable record
of what the site published. The content is public-domain text whose whole value
is that it is inspectable and diffable in the repository.

---

## 6. What to do

1. **Nothing to the fixture layout.** It is doing its job.
2. **Make content diffs readable** — the pipeline's review promise depends on
   it, and it is the cheapest real win here (problem *a*).
3. **Cost out decoupling content deploys from full site rebuilds** (problem
   *b*), keeping #49's deploy-order guarantee intact.
4. **Re-measure when the catalogue roughly doubles**, or if the packed
   repository passes ~500 MB. The experiment in §2 is a few minutes' work and
   should be re-run rather than re-argued.

The measurement scripts behind §2 and §3 are not checked in — they are twenty
lines of `subprocess` around `git count-objects`, and the numbers matter more
than the harness. To reproduce §3's ratio:
`git rev-list --objects HEAD -- backend/library/fixtures/content | awk '{print $1}' | git cat-file --batch-check='%(objecttype) %(objectsize:disk)' | awk '$1=="blob" {s+=$2} END {print s/1048576 " MB"}'`
