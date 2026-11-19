You are a worker in jdegreef/ochorus. Your job is to re-quote ONE Amharic work's Scripture to the Open Word Bible. This is wave 2 of a library-wide move. Three pilots and 27 wave-1 works have shipped, and their lessons are built into these rules.

## Why
Founder decision, 2026-11-18: every Amharic work quotes **OWB Amharic, Balanced** (CC0). It replaces two things:
- the 1962 UBS Bible (© UBS, non-commercial), which the notes call "mined";
- translator-written wording, which the notes call "self_rendered".

The text is bundled at `backend/library/data/bible/owb-am-b.json.gz` and read offline:
`from library.translation import fetch_verse_text, fetch_passage_text, fetch_chapter, Ref; fetch_verse_text("owb-am", "John 3:16")`
**Ranges: use `fetch_passage_text("owb-am", "Psalm 46:1-3")`.** `fetch_verse_text` returns only a range's FIRST verse.

Read these first and follow them:
- `CLAUDE.md`, including the "Amharic quotes OWB everywhere" bullet.
- In `.claude/skills/translation-worker/SKILL.md`, the "Amharic is OWB for EVERY work" note (item 6 under "When the ENGLISH is wrong") and the FOUR RULES under it (verbatim recitations, "…"-joined pieces, Acts 9:6 → 22:10, Ps 68:31), plus its fixture formatting, gate and self-merge rules.

## Your work: {KIND} `{SLUG}` (am): "{TITLE}"
{FILES}
Notes: `backend/library/fixtures/translation_notes/{KIND}/{SLUG}.am.json`.
{EXTRA}

## Method
1. **Inventory. Don't trust the notes alone:** in wave 1 they missed 12% of quotes overall and up to 46% in a book (Bounds rarely cites).
   - Scan the ENGLISH block by block for quoted Scripture: quoted text next to a citation (including roman numerals like "Prov. xxii. 19"), thee/thy/ye inside quote marks, and Scripture in HEADINGS, chapter TITLES, prayers and refrains.
   - Scan the AMHARIC too: every «…», and 1962 wording with NO quote marks. A verbatim recitation without marks (Ps 91:2-6, Phil 2:13 "to will and to do", Heb 7:25) IS a quotation and is re-quoted (founder rule). Only a true allusion in the author's own voice stays prose.
   - Join notes rows to blocks by quoted TEXT, never by `block_index` alone: indexes drift (off by one, global instead of per-chapter, counting <p> inside blockquotes; up to +34). Some rows also carry the wrong reference.
   - Check the book row's `attribution` field (Originals): it may still credit the BSB or 1962.
   - Decide the conventions (recitation vs allusion, recurring words) in a shared CONVENTIONS file BEFORE splitting work across subagents.
2. **Re-quote each one** with verbatim OWB, spliced by script and never typed:
   - Splice against the raw `body_html` by (chapter, block, exact old substring), and assert that the substring occurs exactly once. Quotes can wrap tags.
   - Whole verse → the whole OWB verse. Range → the OWB verses joined with a space.
   - Partial verse → the shortest contiguous OWB span that carries the clause. Where the AUTHOR elides with "…", you may join exact OWB pieces with "…" (founder rule). Otherwise, if no contiguous span carries it, quote the whole verse.
   - **Never edit inside an OWB span.** Once a span is spliced, its words are fixed; a later prose pass must not touch them (a wave-1 subagent changed Mark 1:41's word and it had to be undone).
   - OWB verses can carry their own speech marks mid-quote (Acts 1:8, Acts 5:3, Exod 3:7, 1 Cor 12:21): set them as ‹ › inside the outer « », and drop an unpaired mark at the edge. Psalm verse 1 includes the superscription.
   - An author's bracketed gloss inside a quote fails the OWB check: write «A» (gloss) «B».
   - Keep the sentence-final ። at quote ends; run a before/after punctuation diff. Keep each block's «» balance UNCHANGED (multi-paragraph quotes stay as the translator laid them out).
   - Byte-identical blocks defeat "unique in chapter": use a guarded replace-both step.
   - Children's / teens' epigraphs: the shortest OWB span of the MAIN verse carrying the core idea. Drop stitched clauses from other verses rather than quote whole ranges.
   - Acts 9:6's KJV question → quote OWB Acts 22:10 and cite it. Ps 68:31 where the author argues from "Ethiopia" → keep ኢትዮጵያ, `self_rendered`.
   - A heading's quote and the body's quote of the same words stay identical.
   - Keep the citation (book names as the Amharic library cites them: ዘኍልቍ, ዕብራውያን, 2ኛ ቆሮንቶስ, ቆላስይስ…), the file's quote marks and every tag. The ordered tag sequence must not change.
3. **Read the paragraph AFTER each quote.** OWB reorders clauses and drops KJV keywords, for example "good gift" becomes "perfect gift", and "bruised reed / smoking flax" becomes "bent reed / wick about to go out". Where the author argues from the old word, adjust the translated prose minimally. A one-time bridging gloss beats rewriting a recurring image. List every adjustment.
   - Wave-1 recurring words (reuse these glosses): Comforter → OWB ጠበቃ; Jehovah → እግዚአብሔር; John 16:8 "convict" → መሳሳቱን ያረጋግጣል; Isa 11:2 "might" → ብርታት; "the promise" → ተስፋ; Gen 6:6 / Num 23:19 / 1 Sam 15:29 "repent" (three OWB verbs, one gloss); 1 Thess 5:17 «መጸለይን አታቋርጡ» (the old wording was OWB Col 4:2); Murray's "Lord, teach us to pray" refrain = OWB Luke 11:1's span; Luke 14:23 "compel"; Ps 141:5 is opposite in OWB (Spurgeon follows AV → self_rendered).
   - Also search the chapter TITLE fields and the author's prayers for the old 1962 phrasing.
4. **Critical text.** OWB follows the critical Greek and lacks some KJV verses and clauses (Matt 5:44's extra clauses, Acts 8:37, the 1 John 5:7 comma, …).
   - Quote what OWB has.
   - Where OWB lacks the quoted words entirely, the quote must NOT stay verbatim 1962. Render those words yourself from the English, mark it `self_rendered`, and list it.
5. **Person or gender mismatches.** For example, OWB addresses a man where the author applies the verse to a woman. Decide each case, keep the verb agreement grammatical, mark it `self_rendered` if you changed OWB's words, and list it.
6. **Notes.**
   - Each re-quoted reference becomes `status: "mined"` with `source_file: "Open Word Bible (OWB), Balanced edition, Amharic"`, keeping its block/chapter index. Add rows for quotes the notes missed.
   - Rewrite the file's `note` header so it names OWB, not the 1962 text.
7. **Cross-work provenance.** Other works' notes may cite YOUR file as the `source_file` of a mined verse. Run:
   `grep -rl '"source_file": "{SLUG}.am.json"' backend/library/fixtures/translation_notes/`
   For each such row whose quoted text your re-quote removed, edit that other work's notes (metadata only, nothing else in that file):
   - If its text is now verbatim OWB, make it `mined` with the OWB source.
   - Otherwise make it `self_rendered` with no `source_file`.
   tests_mined_verification fails until you do.
   Cross-work rows are noisy (no chapter_order, shared prose only): repoint conservatively. If the other book's own re-quote PR has already merged and edited that row, its version wins: take main's copy of THAT notes file on rebase.
8. `backend/library/corrections.py` BODY_CORRECTIONS may hold Amharic pairs aimed at the OLD wording. Once your re-quote removes the target, the pair matches nothing and CorrectionsHygieneTests fails: delete the dead pairs for your work.
9. Don't change `source_type`, any English, or any other work's content. English-source citation slips (wrong verse numbers) are carried into the Amharic unchanged and listed under "Found, not fixed".

## Checks and ship
- Recompute each touched chapter's `word_count` (`library.text.word_count`).
- `scripts/regen_fixture.py` must report 0 rewritten (it's fixed on main as of #8372). Run with `DJANGO_DEBUG=true`, and put `backend/` on `sys.path` before `django.setup()` in standalone scripts.
- `manage.py audit_verse_consistency --update-baseline`: absorb the expected OWB-vs-1962 conflicts with other Amharic works (policy, not drift) and say so in the PR.
- Gate suites: tests_verse_consistency, tests_fixture, tests_translation_markup, tests_mined_verification, tests_english_audit, tests_series{GATES_EXTRA} (CorrectionsHygieneTests is in tests_english_audit), and `audit_mined_notes` (0 contradicted). **Run them ONE AT A TIME** (parallel runs hung >30 min; `--parallel 4` thrashes memory), and never while `regen_fixture` runs. Fresh container: `uv sync --frozen` first.
- Write fixtures in the file's existing layout (use `library.content_fixtures.render_rows`); edit notes files textually, as their indent varies.
- Bios: the OWB check now reads `author_bios_am/<slug>.html` + `.faq.json` (#8401). The FAQ repeats the bio's quotes; keep them identical.
- Branch `claude/ochorus-dev-amowb-{SLUG}` off fresh `origin/main`, with ONE PR titled `Amharic re-quote to OWB: {TITLE}`. The body gives:
  - the counts: re-quoted, of which the notes missed N; left, and why; prose adjustments; critical-text and person cases;
  - three before/after samples;
  - the baseline absorbs;
  - any other works' notes rows you repointed.
- Self-merge gate:
  - CI test-and-build is green on the exact head, passed as expectedHeadSha.
  - Right before merging, check the merge-tree into FRESH main is clean, AND re-run tests_verse_consistency and tests_mined_verification on the merged tree. A clean merge-tree can still fail the ratchet (a sibling's merge widened Rom 8:26 from 4 to 5 renderings). ~30 Amharic re-quotes run in parallel, so main WILL move. If it has, rebase, take main's `verse_consistency` baseline and regenerate it with `--update-baseline --absorb`; never hand-merge it. Don't rebase on every move of main: re-run the merged-tree gates and merge.
  - Then squash-merge.
- Report with ONE send_message to session `@parent`. Include:
  - the merge SHA;
  - the counts;
  - the wall-clock time;
  - surprises worth telling the next wave.
- No model identifiers in commits or PRs.
- Concurrency: subagents are optional. For a big book, split it by chapter range across at most 6 subagents, launched two at a time, all sharing one conventions file (book names, quote marks, recurring-image decisions, recitation rule). What worked in wave 1: a per-chapter WORKSHEET (aligned English block, raw Amharic block, OWB text for every cited reference) and ONE shared validator script (substring unique, replacement ⊂ OWB, tag sequence unchanged, «» balance unchanged, edits simulated in order). Subagents return a JSON splice spec (they can't write .md files) and iterate until the validator reports 0 errors; you splice once. Resume any that hit a 429. You alone splice, run the gates and push.
- Before pushing, do a residual scan over the whole book: every «…»(cite) should be contained in OWB verses v-1..v+1, or be listed as self_rendered.
