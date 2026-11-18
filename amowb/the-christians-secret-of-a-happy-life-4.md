You are a worker in jdegreef/ochorus. Your job is to re-quote ONE Amharic work's Scripture to the Open Word Bible. This is wave 1 of a library-wide move. Three pilots shipped first (#8366, #8368, #8369), and their lessons are built into these rules.

## Why
Founder decision, 2026-11-18: every Amharic work quotes **OWB Amharic, Balanced** (CC0). It replaces two things:
- the 1962 UBS Bible (© UBS, non-commercial), which the notes call "mined";
- translator-written wording, which the notes call "self_rendered".

The text is bundled at `backend/library/data/bible/owb-am-b.json.gz` and read offline:
`from library.translation import fetch_verse_text, fetch_chapter, Ref; fetch_verse_text("owb-am", "John 3:16")`

Read these first and follow them:
- `CLAUDE.md`, including the "Amharic quotes OWB everywhere" bullet.
- In `.claude/skills/translation-worker/SKILL.md`, the "Amharic is OWB for EVERY work" note (item 6 under "When the ENGLISH is wrong"), plus its fixture formatting, gate and self-merge rules.

## Your work: book `the-christians-secret-of-a-happy-life-4` (am): "The Christian’s Secret of a Happy Life"
Fixture: `backend/library/fixtures/content/books/the-christians-secret-of-a-happy-life-4.am.json` (book row, then its chapters; 519 quotes are listed in the notes).
Notes: `backend/library/fixtures/translation_notes/book/the-christians-secret-of-a-happy-life-4.am.json`.
A classic by a public-domain author: expect the author to argue from KJV wording (method step 3).

## Method
1. **Inventory. Don't trust the notes alone:** the pilots found they missed up to a third of the quotes.
   - Scan the ENGLISH for quoted Scripture: quoted text next to a citation (including roman numerals like "Prov. xxii. 19"), thee/thy/ye inside quote marks, and Scripture in HEADINGS.
   - Map each hit to its Amharic block and union that list with the notes.
   - Allusions and paraphrases in the author's own voice are prose. Leave them alone.
2. **Re-quote each one** with verbatim OWB, spliced by script and never typed:
   - Splice against the raw `body_html` by (chapter, block, exact old substring), and assert that the substring occurs exactly once. Quotes can wrap tags.
   - Whole verse → the whole OWB verse. Range → the OWB verses joined with a space.
   - Partial verse → the shortest contiguous OWB span that carries the clause. If no contiguous span carries it, quote the whole verse.
   - A heading's quote and the body's quote of the same words stay identical.
   - Keep the citation (book names as the Amharic library cites them: ዘኍልቍ, ዕብራውያን, 2ኛ ቆሮንቶስ, ቆላስይስ…), the file's quote marks and every tag. The ordered tag sequence must not change.
3. **Read the paragraph AFTER each quote.** OWB reorders clauses and drops KJV keywords, for example "good gift" becomes "perfect gift", and "bruised reed / smoking flax" becomes "bent reed / wick about to go out". Where the author argues from the old word, adjust the translated prose minimally. A one-time bridging gloss beats rewriting a recurring image. List every adjustment.
4. **Critical text.** OWB follows the critical Greek and lacks some KJV verses and clauses (Matt 5:44's extra clauses, Acts 8:37, the 1 John 5:7 comma, …).
   - Quote what OWB has.
   - Where OWB lacks the quoted words entirely, the quote must NOT stay verbatim 1962. Render those words yourself from the English, mark it `self_rendered`, and list it.
5. **Person or gender mismatches.** For example, OWB addresses a man where the author applies the verse to a woman. Decide each case, keep the verb agreement grammatical, mark it `self_rendered` if you changed OWB's words, and list it.
6. **Notes.**
   - Each re-quoted reference becomes `status: "mined"` with `source_file: "Open Word Bible (OWB), Balanced edition, Amharic"`, keeping its block/chapter index. Add rows for quotes the notes missed.
   - Rewrite the file's `note` header so it names OWB, not the 1962 text.
7. **Cross-work provenance.** Other works' notes may cite YOUR file as the `source_file` of a mined verse. Run:
   `grep -rl '"source_file": "the-christians-secret-of-a-happy-life-4.am.json"' backend/library/fixtures/translation_notes/`
   For each such row whose quoted text your re-quote removed, edit that other work's notes (metadata only, nothing else in that file):
   - If its text is now verbatim OWB, make it `mined` with the OWB source.
   - Otherwise make it `self_rendered` with no `source_file`.
   tests_mined_verification fails until you do.
8. Don't change `source_type`, any English, or any other work's content.

## Checks and ship
- Recompute each touched chapter's `word_count` (`library.text.word_count`).
- `scripts/regen_fixture.py` must report 0 rewritten (it's fixed on main as of #8372). Run with `DJANGO_DEBUG=true`, and put `backend/` on `sys.path` before `django.setup()` in standalone scripts.
- `manage.py audit_verse_consistency --update-baseline`: absorb the expected OWB-vs-1962 conflicts with other Amharic works (policy, not drift) and say so in the PR.
- Gate suites: tests_verse_consistency, tests_fixture, tests_translation_markup, tests_mined_verification, tests_english_audit, tests_series, and `audit_mined_notes` (0 contradicted). They take about 6 minutes, so run them in the background.
- Branch `claude/ochorus-dev-amowb-the-christians-secret-of-a-happy-life-4` off fresh `origin/main`, with ONE PR titled `Amharic re-quote to OWB: The Christian’s Secret of a Happy Life`. The body gives:
  - the counts: re-quoted, of which the notes missed N; left, and why; prose adjustments; critical-text and person cases;
  - three before/after samples;
  - the baseline absorbs;
  - any other works' notes rows you repointed.
- Self-merge gate:
  - CI test-and-build is green on the exact head, passed as expectedHeadSha.
  - Right before merging, check the merge-tree into FRESH main is clean, and re-run tests_verse_consistency and tests_mined_verification on the merged tree. ~27 Amharic re-quotes run in parallel, so main WILL move. If it has, rebase and regenerate the baseline; never hand-merge it.
  - Then squash-merge.
- Report with ONE send_message to session `@parent`. Include:
  - the merge SHA;
  - the counts;
  - the wall-clock time;
  - surprises worth telling the next wave.
- No model identifiers in commits or PRs.
- Concurrency: subagents are optional. For a big book, split it by chapter range across at most 6 subagents, launched two at a time, all sharing one conventions file (book names, quote marks, recurring-image decisions). Resume any that hit a 429. You alone splice, run the gates and push.
