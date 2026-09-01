"""Manual, per-book corrections applied after automatic PDF extraction.

The importer gets most things right, but some books have quirks the heuristics
can't infer — e.g. a chapter whose title is formatted inline rather than as a
separate heading. Record those fixes here, keyed by book slug, so they survive
every re-import. Keep this list small and specific; if a pattern recurs across
books, prefer improving the importer over adding one-off entries here.

Shape:
    CORRECTIONS = {
        "<book-slug>": {
            "chapter_titles": {<order:int>: "<exact final title>"},
        },
    }
"""

from __future__ import annotations

import re as _re
from collections.abc import Sequence

# Catalogue slugs to skip on a full import (e.g. duplicate/teen editions we don't
# want in the library). An explicit `import_ochorus <slug>` still imports them.
EXCLUDED_SLUGS: set[str] = {
    # Teens edition of "The Person and Work of the Holy Spirit"; we keep the
    # adult original (the-person-and-work-of-the-holy-spirit).
    "the-person-and-work-of-the-holy-spirit-2",
    # NOT public domain (copyright audit 2026-07-10) — unpublished in migration
    # 0020 and kept out of re-import. Watchman Nee's English editions (1957–1983,
    # Kinnear/CLC/CFP) and Amy Carmichael's "If" (1938, URAA-restored).
    "the-normal-christian-life",
    "grace-for-grace-2",
    "the-body-of-christ-a-reality",
    "the-body-of-christ-teens",
    "let-us-pray-2",
    "if",
}

CORRECTIONS: dict[str, dict] = {
    "separation-and-service": {
        # Taylor's exposition falls into an Introductory section and three Parts
        # (I Separation to God, II The Blessing of God, III Princely Service).
        # The importer took each chapter's SCRIPTURE REFERENCE ("Numb. vi. 1-21")
        # as the title and left the descriptive heading in the body; these
        # restore the Part names for a readable TOC. The 39 sub-section headings
        # survive as <h3> inside the bodies.
        "chapter_titles": {
            1: "Introductory",
            2: "Separation to God",
            3: "The Blessing of God",
            4: "Princely Service",
        },
    },
    "on-loving-god": {
        # The Patmore edition prints a long ALL-CAPS "argument" as each chapter
        # heading, wrapped across two OCR lines; the archive importer took the
        # first line as the title and left the ALL-CAPS remainder as the opening
        # paragraph (stripped in the matching BODY_CORRECTIONS entry). Titles
        # here are each chapter's own lead clause, for a readable TOC.
        "chapter_titles": {
            1: "Why We Ought to Love God",
            2: "God's Right to Our Love",
            3: "The Christian's Greater Motive to Love",
            4: "Who Finds Comfort in God",
            5: "The Duty to Love God",
            6: "A Summary",
            7: "The Reward of Loving God",
            8: "The First Degree of Love",
            9: "The Second and Third Degrees of Love",
            10: "The Fourth Degree of Love",
            11: "Perfect Love After the Resurrection",
        },
    },
    "a-short-and-easy-method-of-prayer": {
        # Marston's 1875 edition prints a 30–50-word analytical "argument" as
        # each chapter heading (and the ALL-CAPS→Title-Case pass leaves the word
        # after an em-dash lowercased: "Pray—prayer"). Replace with each
        # chapter's own lead clause — faithful, and a readable TOC. Chapter 7's
        # short "Mysteries"/"Virtue" sections merged in as <h3> subheads (under
        # 300 words), so its title names the group.
        "chapter_titles": {
            3: "All Are Commanded to Pray",
            4: "The First Degree of Prayer",
            5: "The Second Degree: The Prayer of Simplicity",
            6: "Abandonment to God",
            7: "Suffering, Mysteries, and Virtue",
            8: "Of Perfect Conversion",
            9: "The Simple Presence of God",
            10: "Rest in the Presence of God",
            11: "Self-Examination and Confession",
            12: "Distractions and Temptations",
            13: "Prayer and Sacrifice",
            14: "Prayer as Noble Action",
            15: "Interior and Exterior Actions",
            16: "A Word to Preachers",
            17: "The Way to Divine Union",
        },
    },
    "the-life-of-trust": {
        # One chapter's Gutenberg divider heading is a stray page number
        # ("[364]") instead of the title; the real title sits in an <h3> at the
        # top of the body (see the matching BODY_CORRECTIONS entry that removes
        # the now-duplicated heading). Every other chapter's title came through
        # cleanly.
        "chapter_titles": {23: "A New Victory of Faith"},
    },
    "mortification-of-sin": {
        # CCEL's TOC titles these "Chapter I."…"Chapter XIV.", which the
        # numbering-cleanup leaves blank so the reader shows a bare "Chapter N"
        # — and the Preface takes slot 1, so those numbers are one ahead of
        # Owen's own. Each title below is the lead clause of Owen's own chapter
        # summary, which the edition prints as the chapter's opening line.
        "chapter_titles": {
            2: "The foundation of the whole discourse, laid in Romans viii. 13",
            3: "The necessity of mortification: the duty of the best believers",
            4: "The Spirit is the only author of this work",
            5: "The usefulness of mortification to the vigour of our spiritual lives",
            6: "What it is to mortify a sin, negatively considered",
            7: "The mortification of sin in particular described",
            8: "General rules, without which no lust will be mortified",
            9: "Without universal sincerity, no one lust will be mortified",
            10: "Consider the dangerous symptoms of any lust",
            11: "Get a clear sense of the guilt, danger and evil of the sin",
            12: "Load thy conscience with the guilt of the perplexing distemper",
            13: "Thoughtfulness of the excellency of the majesty of God",
            14: "When the heart is disquieted by sin, speak no peace to it "
                "until God speak it",
            15: "Act faith on Christ for the killing of thy sin",
        },
    },
    "the-bruised-reed": {
        # Grosart's scan carries its chapter titles on the marker line, where
        # they both truncate and pick up the worst of the OCR. Each title below
        # is the full heading transcribed from the scan (marker line plus its
        # wrapped continuation), with the misreads repaired: "ivill"->will,
        # "Rides"->Rules, "Eeproof"->Reproof, "he\epresenteth"->he representeth,
        # "unto its"->unto us. Chapters 1, 9 and 21 were cut mid-phrase by the
        # page edge and are completed from the 1878 printing's contents page.
        "chapter_titles": {
            1: "The Text opened and divided. What the Reed is, and what the bruising",
            2: "Those that Christ hath to do withal are bruised",
            3: "Christ will not break the Bruised Reed",
            4: "Signs of one truly bruised. Means and measure of bruising, and comfort to such",
            5: "Grace is little at first",
            6: "Grace is mingled with Corruption",
            7: "Christ will not quench small and weak beginnings",
            8: "Tenderness required in ministers toward young beginners",
            9: "Governors should be tender of weak ones, and also private Christians",
            10: "Rules to try whether we be such as Christ will not quench",
            11: "Signs of smoking flax which Christ will not quench",
            12: "Scruples hindering comfort removed",
            13: "Set upon Duties notwithstanding Weaknesses",
            14: "The case of Indisposition resolved, and Discouragements",
            15: "Of infirmities. No cause of discouragement, in whom they are, "
                "and how to recover peace lost",
            16: "Satan not to be believed, as he representeth Christ unto us",
            17: "Reproof of such as sin against this merciful disposition in Christ. "
                "Of quenching the Spirit",
            18: "Of Christ's judgment in us, and his victory: what it is",
            19: "Christ is so mild that yet he will govern those that enjoy "
                "the comfort of his mildness",
            20: "The spiritual government of Christ is joined with judgment and wisdom",
            21: "Where true wisdom and judgment is, there Christ sets up his government",
            22: "Christ's government is victorious",
            23: "Means to make Grace victorious",
            24: "All should side with Christ",
            25: "Christ's government shall be openly victorious",
            26: "Christ alone advanceth this government",
            27: "Victory not to be had without fighting",
        },
    },
    "union-and-communion": {
        # CCEL's TOC labels the foreword "Forward" (a period typo); fix it.
        # After the bare "Title" page is dropped as front matter, the foreword
        # is order 1.
        "chapter_titles": {1: "Foreword"},
    },
    "the-normal-christian-life": {
        # Ch.12's title is inline ("Chapter 12: The Cross and the Soul Life") in
        # the PDF, so it isn't detected as a standalone heading. From the TOC:
        "chapter_titles": {12: "The Cross and the Soul Life"},
    },
    "jesus-himself-2": {
        # Ch.2's title is a long quoted sentence that wraps across lines in the
        # PDF, so the title-borrow captured only the final word ("You"). Full
        # title from the PDF's table of contents:
        "chapter_titles": {2: "I will come and dwell with you, and I will never leave you"},
    },
    "godliness": {
        # Ch.11's ALL-CAPS subtitle ("AN ADDRESS DELIVERED IN EXETER HALL") sits
        # at body size right under the size-18 title, so the title-borrow absorbs
        # it. Ch.13's parenthetical is mis-cased by the title-caser. Both from the
        # PDF's own table of contents (house style: Title Case throughout):
        "chapter_titles": {
            11: "Enthusiasm And Full Salvation",
            13: "Addresses On Holiness In Exeter Hall (First Address)",
        },
    },
    "purpose-in-prayer": {
        # EDITORIAL TITLES, not a repair. Unlike Bounds' other three books —
        # which CCEL carries with their own chapter titles — the 1920 Purpose in
        # Prayer numbers its chapters and never names them, so the import was
        # right to leave all 13 blank and the reader showed a bare "1", "2", "3".
        # These were written from each chapter's own argument, using Bounds' own
        # phrasing wherever he gives a usable one ("prayerless praying", "pray
        # and never faint", "put the men to praying"), so the book reads like the
        # rest of the shelf. They are OURS, not his: if a titled edition ever
        # turns up, prefer its titles to these.
        "chapter_titles": {
            1: "God Shapes the World by Prayer",
            2: "Prayer Changes the Purpose of God",
            3: "We Have Not Because We Ask Not",
            4: "Men Who Prayed With a Purpose",
            5: "Prayer Is a Trade to Be Learned",
            6: "Pray and Never Faint",
            7: "Men Ought Always to Pray",
            8: "Put the Men to Praying",
            9: "Reaching the Ear of God",
            10: "Prayerless Praying",
            11: "The Prayer of Faith Never Fails",
            12: "Revivals Are Born in Prayer",
            13: "Christ Our Example in Prayer",
        },
    },
    "talks-to-the-farmer": {
        # Ch.1's title block is fused with the subhead and opening body text in
        # one oversized block ("THE SLUGGARD'S FARM  Introduction  From a
        # neglected field…"), so no title can be borrowed. From the TOC:
        "chapter_titles": {1: "The Sluggard's Farm"},
    },
    "susanna-wesley-clarke": {
        # OCR misread two ALL-CAPS chapter headings (R->E): "THE HOME EEBUILT",
        # "THE SUPERNATUEAL NOISES". Corrected from the front-page TOC.
        "chapter_titles": {9: "The Home Rebuilt", 11: "The Supernatural Noises"},
    },
    "way-into-holiest": {
        # Ch.7's CCEL heading is a mixed-case quoted phrase ("VI. \"Perfect through
        # sufferings\""), so the roman-prefix strip — which only fires on ALL-CAPS
        # headings — leaves the "VI." in place. Give the clean title directly.
        "chapter_titles": {7: "Perfect through sufferings"},
    },
    "the-unselfishness-of-god": {
        # Ch.12's title lost the possessive apostrophe and its title-casing
        # ("Friends testimonies"), and ch.13's second word was left lowercase.
        # Both are title-caser misses, not the author: the bodies speak of
        # "Friends' testimonies" and "Quaker scruples" in ordinary prose, and
        # the house style for chapter titles is Title Case throughout.
        "chapter_titles": {
            12: "Friends' Testimonies Against Fiction, Music, And Art",
            13: "Quaker Scruples",
        },
    },
    "necessity-of-prayer": {
        # CCEL numbers this TOC "I. Prayer and Faith" … "XIV. Prayer and the
        # House of God", and the reader prints the chapter order itself — so it
        # rendered "2. I. Prayer and Faith", two numbers that do not even agree
        # (the Foreword is chapter 1). `clean_title` strips a roman prefix only
        # from an ALL-CAPS heading, which is why its sibling Prayer and Praying
        # Men needs no entry here and this book does.
        #
        # Per-book rather than a widened rule: dropping the ALL-CAPS gate would
        # also strip Edwards's twelve numbered SIGNS in religious-affections,
        # where the numeral is the structure the book is cited by.
        "chapter_titles": {
            2: "Prayer and Faith",
            3: "Prayer and Faith (Continued)",
            4: "Prayer and Trust",
            5: "Prayer and Desire",
            6: "Prayer and Fervency",
            7: "Prayer and Importunity",
            8: "Prayer and Importunity (Continued)",
            9: "Prayer and Character and Conduct",
            10: "Prayer and Obedience",
            11: "Prayer and Obedience (Continued)",
            12: "Prayer and Vigilance",
            13: "Prayer and the Word of God",
            14: "Prayer and the Word of God (Continued)",
            15: "Prayer and the House of God",
        },
    },
    "stepping-stones-2": {
        # Ch.30's title misspells Millennium; the chapter body spells it
        # correctly. Found by the English audit. This lives here rather than in
        # BODY_CORRECTIONS because that only rewrites body_html, so a defect in
        # a title is out of its reach entirely.
        "chapter_titles": {30: "Into A New Millennium"},
    },
}


def chapter_title_overrides(slug: str) -> dict[int, str]:
    return CORRECTIONS.get(slug, {}).get("chapter_titles", {})


# --- Body-text corrections ------------------------------------------------------
# Defects inside chapter bodies that heuristics can't fix — mostly extraction
# artifacts, but ALSO what the source transcription itself lost, where the fix
# has to reach a deployed reader page. `source_fixes.py` is the usual home for a
# source defect and is still right when the defect has propagated into other
# languages; it is wrong here, because it reaches production only through a
# hand-written migration and is not a root in `content_sources.json`, so a
# repair there moves no content digest and the prerendered page keeps the old
# prose. This table is a root and runs on every deploy.
#
#   dropcap_letters: {order: "G"} — the chapter's opening letter was an IMAGE
#     drop cap in the source, so the text layer starts one letter short
#     ("reat numbers…"). The letter is unambiguous from context; we restore it.
#   replacements: [(old, new)] — exact-string repairs for OCR damage (a letter
#     split off before punctuation: "blesse d!" → "blessed!"). Kept as literal
#     pairs — no clever regex — so scripture citations like "Song i." are never
#     touched. Verify each in context before adding.
#   paragraph_breaks: [(tail, head)] — the source transcription ran one
#     paragraph into the one before it, and the break is put back between these
#     two exact strings ("…their own experience." / "Alas!"). Not a
#     `replacements` pair; `restore_paragraph_breaks` says why.
#
# Applied on every import AND backfillable over stored rows (management command
# `apply_body_corrections`, plus a data migration for prod).

BODY_CORRECTIONS: dict[str, dict] = {
    "separation-and-service": {
        # Two chapters open with an <h3> that merely restates the chapter title
        # (the importer borrowed the scripture ref as the title and left the
        # descriptive heading in the body — the matching chapter_titles entry
        # fixes the title). Drop the redundant leading heading so the chapter
        # doesn't echo its own name. ch2's leading <h3> is a genuine sub-heading
        # ("THE INSTITUTION OF THE ORDER OF NAZARITES") and is left alone.
        "replacements": [
            ("<h3>INTRODUCTORY.</h3> ", ""),
            ("<h3>Princely Service.</h3> <h3> Numb. vii.</h3> ", ""),
        ],
    },
    "pilgrims-progress": {
        # The 1678 text carries an editor's marginal glosses. The extractor
        # emitted each note's in-text marker AND its label at the foot of the
        # page as two superscripts, then ran the note body straight into
        # Bunyan's line:
        #
        #   Should prove <i>ad infinitum</i>,<sup>1</sup><sup>1</sup>Without end. and eat out
        #
        # which a reader sees as "ad infinitum,11Without end. and eat out". Nine
        # of these, and ch02's lands inside the book's most-quoted sentence —
        # "a certain place where was a den,33Bedford jail, in which the author
        # was imprisoned for conscience' sake and laid me down in that place to
        # sleep". The gloss is a later editor's, not Bunyan's, and there is no
        # footnote surface to move it to, so it comes out and the line reads as
        # written. Recoverable from this diff if footnotes are ever added.
        "replacements": [
            ("<sup>1</sup><sup>1</sup>Without end. and eat out", " and eat out"),
            ("<sup>2</sup><sup>2</sup>Hint, whisper, insinuation. of it", " of it"),
            ("<sup>3</sup><sup>3</sup>Bedford jail, in which the author was "
             "imprisoned for conscience\u2019 sake and laid me down", " and laid me down"),
            ("<sup>4</sup><sup>4</sup>Slight knowledge. of him", " of him"),
            ("<sup>5</sup><sup>5</sup>Wish a curse to. him for his counsel!",
             " him for his counsel!"),
            ("<sup>6</sup><sup>6</sup>The Holy Spirit. where he knocked", " where he knocked"),
            ("<sup>7</sup><sup>7</sup>Of the flesh and blood of Christ. "
             "John 6:54-57; Heb. 9:14; (you know physicians", " (you know physicians"),
            ("<sup>8</sup><sup>8</sup>A musical instrument. so she played", " so she played"),
            ("<sup>9</sup><sup>9</sup>A gold angel was a coin of the value of ten "
             "shillings sterling and according to the comparative value of money "
             "in Bunyan\u2019s time, equal at least to a guinea at the present time. "
             "in his hand", " in his hand"),
        ],
    },
    "union-and-communion": {
        # Same defect. Hudson Taylor's own notes on the Song of Solomon, welded
        # into the verse lines he is expounding — "For Thy love11 Loves =
        # endearments, caresses. is better than wine." Four of the five sit in
        # the refrain "Until she please", which the note makes unreadable.
        "replacements": [
            ("<sup>1</sup><sup>1</sup> Loves = endearments, caresses. is better",
             " is better"),
            ("<sup>2</sup><sup>2</sup> The pronoun here and in chapter iii. 5, and "
             "viii. 4, should not be \u201che\u201d as A. V., nor \u201cit\u201d as R.V., but "
             "\u201cshe\u201d. please.", " please."),
            ("<sup>3</sup><sup>3</sup> [The pronoun here should not be \u201che\u201d as "
             "A. V., nor \u201cit\u201d as R.V., but \u201cshe\u201d.] please.", " please."),
            ("<sup>4</sup><sup>4</sup> The Church of Popular Opinion, as pointed out "
             "by the Rev. Charles Fox in an address at Keswick, as the Church of "
             "Philadelphia is the Church of Brotherly Love. Church:", " Church:"),
            ("<sup>5</sup><sup>5</sup> [The pronoun here should not be \u201che\u201d as "
             "A. V., nor \u201cit\u201d as R.V., but \u201cshe\u201d.] please?", " please?"),
        ],
    },
    "till-he-come": {
        # A doubled marker with no note behind it — the digits "11" render at
        # the end of the quotation and point at nothing.
        "replacements": [("<sup>1</sup><sup>1</sup></p>", "</p>")],
    },
    "revival-lectures": {
        # Here the notes sit at the END of their paragraph rather than inside a
        # sentence, so the prose is intact and only the doubled marker shows.
        # The notes are the editor's and worth keeping ("This was said in
        # 1833."), so only the marker comes out — no content is lost.
        "replacements": [
            ("communion.<sup>1</sup><sup>1</sup>Why not", "communion. Why not"),
            ("destruction?\u201d<sup>2</sup><sup>2</sup>Edwards\u2019 Works.",
             "destruction?\u201d Edwards\u2019 Works."),
            ("order a battle.<sup>3</sup><sup>3</sup>This was said in 1833.",
             "order a battle. This was said in 1833."),
            ("of doing it.<sup>4</sup><sup>4</sup>This was said with pain",
             "of doing it. This was said with pain"),
            ("since the world began.<sup>5</sup><sup>5</sup>This was in 1831.",
             "since the world began. This was in 1831."),
            ("less and less powerful.<sup>6</sup><sup>6</sup>The strange opposition",
             "less and less powerful. The strange opposition"),
            ("need to make you feel so.\u201d<sup>7</sup><sup>7</sup>I believe the reporter",
             "need to make you feel so.\u201d I believe the reporter"),
        ],
    },
    "on-loving-god": {
        # Strip the ALL-CAPS heading-remainder paragraph the archive importer
        # left at the top of nine chapters (the wrapped tail of the chapter
        # title; see the chapter_titles entry). Chapters 6 and 9 open straight
        # into prose and need no strip. Exact strings, so each matches once.
        "replacements": [
            ("<p>OUGHT TO LOVE HIM.</p>", ""),
            ("<p>BECAUSE OF HIS GIFTS TO SOUL AND BODY. HOW THESE SHOULD BE "
             "CONFESSED, AND NOT TURNED AGAINST HIM WHO GAVE THEM.</p>", ""),
            ("<p>INFIDELS, TO LOVE GOD.</p>", ""),
            ("<p>OF GOD ; AND WHO ARE FITTEST TO FEEL LOVE FOR HIM.</p>", ""),
            ("<p>FOR CHRISTIANS.</p>", ""),
            ("<p>GOD. THE HEART OF MAN IS NOT TO BE SATISFIED BY EARTHLY "
             "THINGS.</p>", ""),
            ("<p>US THE FIRST DEGREE OF LOVE.</p>", ""),
            ("<p>ONLY FOR GOD.</p>", ""),
            ("<p>AFTER THE GENERAL RESURRECTION.</p>", ""),
            # Chapter 6 lost its opening drop-cap "I" ("Fateor" — "I confess").
            ("<p>CONFESS that God deserves", "<p>I CONFESS that God deserves"),
            # The 1884 edition's quotation marks OCR'd as guillemets throughout;
            # they never occur legitimately in this English text, so map the pair
            # to curly double quotes (drop the space the opener carried).
            ("« ", "“"),
            ("«", "“"),
            ("»", "”"),
        ],
    },
    "the-life-of-trust": {
        # The stray-page-number heading (see CORRECTIONS above) left the real
        # title as an <h3> at the top of ch23's body, which now duplicates the
        # chapter title. Every other chapter's body opens on its <h4> date line.
        "replacements": [("<h3>A NEW VICTORY OF FAITH.</h3>", "")],
    },
    "prayer-and-praying-men": {
        # Two words glued together in CCEL's own text (verified upstream, so
        # not something our cleaning introduced). Both produce a NON-word, and
        # the seam is forced by the sentence — there is no reading in which
        # "fromheaven" or "isthat" is Bounds's own spelling:
        #
        #   fromheaven  ch10  "at the third call fromheaven, when he recognized
        #                     God's voice" — Samuel, 1 Samuel 3
        #   isthat      ch15  "the evidence of sincerity in a true seeker of
        #                     religion isthat it can be said of him, 'Behold he
        #                     prayeth.'"
        "replacements": [
            ("call fromheaven", "call from heaven"),
            ("religion isthat", "religion is that"),
        ],
    },
    "spurgeon-on-prayer": {
        # CCEL transcription slips in the printed Pulpit text, each unambiguous
        # from context (verified in the sermon, not introduced by our cleaning):
        #   Sis- ters  ch3  "my Brothers and Sis- ters" — a word split on a
        #               line-break hyphen that survived into the transcription.
        #   1 can say   ch9  "O Lord, 1 can say no more" — a digit-1 misread of
        #               the pronoun "I" inside a quoted prayer.
        #   Yet ,       ch11 "Yet , doubtless" — a stray space before the comma.
        "replacements": [
            ("Brothers and Sis- ters", "Brothers and Sisters"),
            ("O Lord, 1 can say no more", "O Lord, I can say no more"),
            ("Yet , doubtless", "Yet, doubtless"),
        ],
    },
    "all-of-grace": {
        # Four OCR slips in the English text, found while translating the book
        # to Hindi. All four are single occurrences and none changes meaning —
        # each mis-read produces a NON-WORD, so there is no reading in which
        # they are Spurgeon's period spelling rather than the scanner's error:
        #
        #   everasting  ch08  quoting John 4:14, "springing up into everlasting
        #                     life" — the l is simply dropped
        #   wordly      ch11  "wordly cares"; the book spells worldly correctly
        #                     elsewhere (ch07, "worldly lusts")
        #   which l would ch11 quoting Romans 7:18, "how to perform that which I
        #                     would I find not" — the classic l/I confusion, and
        #                     the same sentence is quoted correctly in ch01
        #   mutrition   ch13  "the whole process of nutrition"
        #
        # English-only: the es and lg editions already read eterna/nutrición/
        # mundanas and obulamu/emmere/ensi, so all three translators read
        # through the damage and nothing propagated. That is why this is a
        # BODY_CORRECTIONS entry and not a source_fixes one.
        #
        # Each pair carries a following word so it cannot match anywhere else.
        "replacements": [
            ("into everasting life", "into everlasting life"),
            ("with wordly cares", "with worldly cares"),
            ("that which l would I find not", "that which I would I find not"),
            ("process of mutrition", "process of nutrition"),
        ],
    },
    # --- lost-space word fusion (english_audit `word-fusion`) ----------------
    #
    # Seventeen sites where a space vanished INSIDE a sentence, so two words
    # were stored as one: "all my children weresafe". `run-together` only ever
    # caught the same defect after a full stop, so these sat unreported.
    #
    # Here as well as in the fixture because `seed_books` deliberately never
    # touches an existing book's chapters (see its `chapter_drift` note) — a
    # fixture edit alone reaches a fresh database and never a deployed one.
    "confessions": {
        "replacements": [("his socalled constellations", "his so-called constellations")],
    },
    "grace-for-grace-2": {
        "replacements": [("this hard-todeal-with", "this hard-to-deal-with")],
    },
    "plain-account-christian-perfection": {
        "replacements": [("as given in aninstant?", "as given in an instant?")],
    },
    "consolation-in-the-furnace": {
        "replacements": [("He is near youthis day", "He is near you this day")],
    },
    "baptism-with-the-holy-spirit": {
        # Source defects (OCR) in the English text, found while translating the
        # book to Portuguese. Both are scripture references only — the prose is
        # untouched. The surrounding reference lists use hyphenated ranges
        # ("Acts 9:17, 20-22"), so the stray colon is plainly a mis-read; and
        # the Saul/Jabesh-Gilead passage quoted is 1 Samuel 11:6, "11" being an
        # OCR of the roman "I".
        "replacements": [
            ("Acts 4:8:13", "Acts 4:8-13"),
            ("(11 Samuel 11:6)", "(1 Samuel 11:6)"),
            # The scan rendered 20 quote marks as a PAIR OF APOSTROPHES. Found
            # while translating the book to Ukrainian, and the reason it is
            # worth fixing at the source rather than per edition: all five
            # existing translations (ar/es/lg/pt/sw) already carry zero of them,
            # each having silently resolved the same damage its own way. The
            # English is the only edition still showing it.
            #
            # There is no blanket rule to apply. 15 of the 20 are OPENING
            # marks, 3 are CLOSING, one is a spurious SECOND closer sitting
            # right after a real one, and one is a wholly garbled passage. An
            # alternating toggle would invert everything after the first
            # mis-classification, which is the documented way this repair goes
            # wrong, so each site carries enough context to be unique.
            # Openers:
            ("Jesus said, &#x27;&#x27;", "Jesus said, “"),
            ("we read &#x27;&#x27;All of them", "we read “All of them"),
            ("spoken of as &#x27;&#x27;the promise", "spoken of as “the promise"),
            ("Holy Ghost: &#x27;&#x27;Well, my brother", "Holy Ghost: “Well, my brother"),
            ("“yes” or &#x27;&#x27;no.”", "“yes” or “no.”"),
            ("Spirit does &#x27;&#x27;mortify", "Spirit does “mortify"),
            ("Acts 1:8. &#x27;&#x27;But you will receive", "Acts 1:8. “But you will receive"),
            ("her children &#x27;&#x27;in the nurture", "her children “in the nurture"),
            ("that Jesus &#x27;&#x27;charged them", "that Jesus “charged them"),
            ("which, &#x27;&#x27;For John baptized", "which, “For John baptized"),
            ("Then, &#x27;&#x27;Full of the Holy Ghost", "Then, “Full of the Holy Ghost"),
            ("proclaims Himself &#x27;&#x27;anointed to preach", "proclaims Himself “anointed to preach"),
            ("next generation, &#x27;&#x27;And to your children", "next generation, “And to your children"),
            ("blessing came. &#x27;&#x27;everything that does not", "blessing came. “everything that does not"),
            ("Holy Spirit?” &#x27;&#x27;I don", "Holy Spirit?” “I don"),
            # Closers:
            ("the promise of the Father,&#x27;&#x27; and in Luke", "the promise of the Father,” and in Luke"),
            ("the promise of the Holy Ghost. &#x27;&#x27; It would seem", "the promise of the Holy Ghost.” It would seem"),
            ("baptism with the Holy Spirit,&#x27;&#x27; and you have", "baptism with the Holy Spirit,” and you have"),
            ("with the Holy Spirit.”&#x27;&#x27; They were not", "with the Holy Spirit.” They were not"),
            # Moses striking the rock: the hyphen dropped out of the verse
            # range, welding 10 and 12 into "1012" -- the one citation in the
            # book a reader cannot act on. All five translations print
            # "20:10-12", so the intended range is not in doubt, and the
            # numerals are unlocalized, so the pair is written WITHOUT the book
            # name and repairs every edition -- the uk translation reproduced
            # the defect faithfully, and this reaches it on the next deploy.
            # "20:1012" occurs exactly twice corpus-wide, both at this site.
            ("20:1012", "20:10-12"),
            # ch01's worst site: "say positively, “yes, “or” no, ' ' to the
            # question" — two marks transposed and an apostrophe pair left
            # stranded. Every other edition prints a clean "yes" or "no" here
            # (pt “sim”/“não”, es «si»/«no», ar «نعم»/«لا»), which is what
            # settles the intended reading.
            ("positively, “yes, “or” no, &#x27; &#x27; to the question", "positively, “yes” or “no” to the question"),
        ],
    },
    "the-key-in-my-hand": {
        # Source defects found while translating the book to Portuguese.
        # The verse-range typo also reached the sw/lg/pt editions, so the
        # replacement is written to match in any language (the book name is
        # localized around it, the numerals are not).
        "replacements": [
            ("18:19-10", "18:19-20"),          # quoted text is Matt 18:20
            ("armor of God of God", "armor of God"),
            ("God sees they as a sinner", "God sees them as a sinner"),
        ],
    },
    "the-way-to-god": {
        # Source defect (Gutenberg #30449, ch. 8): the epigraph line lost its
        # quotation and opening paren — only "Colossians iii. 11.)" remains.
        #
        # The rest are misprinted chapter/verse numbers, found by
        # `audit_citations` and by the translators of job #419. Only the numeral
        # moves; Moody's wording, and the house Roman-numeral style, are left
        # exactly as printed. This class is worth repairing before a work is
        # translated: a translator reproduces a printed reference faithfully —
        # as they should — so one wrong citation becomes one per language.
        "replacements": [
            ("<p>Colossians iii. 11.)</p>", "<p>(Colossians iii. 11.)</p>"),
            # "Two men went up into the temple to pray" is Luke 18:10; 17:10 is
            # the unprofitable servants.
            ("Luke xvii. 10.", "Luke xviii. 10."),
            # "The heart is deceitful above all things" is Jeremiah 17:9.
            ("(Jer. xxii. 9)", "(Jer. xvii. 9)"),
            # Peter's confession is Matthew 16:16 — the second 6 was dropped.
            ("(Matthew xvi. 1;", "(Matthew xvi. 16;"),
            # 20:2 is "I am Jehovah thy God"; the first commandment is 20:3.
            ("(Exod. xx. 2)", "(Exod. xx. 3)"),
            # "I am the truth" is John 14:6; 14:5 is Thomas asking the way.
            ("(John xiv. 5.)", "(John xiv. 6.)"),
            # Peter's "yet will I never be offended" is Matthew 26:33; 26:23 is
            # the sop.
            ("(Matt. xxvi. 23.)", "(Matt. xxvi. 33.)"),
        ],
    },
    "a-call-to-the-unconverted": {
        # Misprinted references, from `audit_citations`. Baxter's own wording is
        # untouched — each of these moves a numeral only.
        #
        # Plus one welded footnote (see pilgrims-progress for the defect): the
        # note naming the gentleman and the bridge sits between two sentences of
        # Baxter's story about the Severn.
        "replacements": [
            ("<sup>1</sup><sup>1</sup>Mr. R. Rowley, of Shrewsbury, upon Acham "
             "bridge. A man was driving", " A man was driving"),
            # "O that there were such a heart in this people" is Deut 5:29;
            # 5:20 is the ninth commandment.
            ("Deut. v. 20.", "Deut. v. 29."),
            # "O that they were wise" is Deut 32:29, in the Song of Moses;
            # 33:29 is "Happy art thou, O Israel".
            ("Deut. xxxiii. 29.", "Deut. xxxii. 29."),
            # "Do you thus requite the Lord" is Deut 32:6; 22:6 is the bird's
            # nest. An x dropped from xxxii.
            ("Deut. xxii. 6.", "Deut. xxxii. 6."),
        ],
    },
    "all-things-for-good": {
        "replacements": [
            # "My servant Job shall pray for you" is Job 42:8 — xlii misread as
            # xiii. The "lob" in the same sentence is a separate OCR slip in the
            # quoted text and is left for the English pass, which owns wording.
            ("(Job xiii. 8)", "(Job xlii. 8)"),
        ],
    },
    "around-the-wicket-gate": {
        # Image drop caps (Gutenberg source) — first letter of every chapter.
        "dropcap_letters": {
            1: "G",   # G(reat numbers of persons…)
            2: "W",   # W(e cannot, too often…)
            3: "T",   # T(here is a wretched tendency…)
            4: "T",   # T(o many, faith seems…)
            5: "I",   # I(t is an odd product…)
            6: "I",   # I(t may be that the reader…)
            7: "T",   # T(o help the seeker…)
            8: "A",   # A(lthough it is by no means…)
            9: "I",   # I(n these days…)
            10: "S",  # S(ome think it hard…)
            11: "F",  # F(riends, if now you have begun…)
        },
    },
    "divine-healing": {
        # OCR damage in the English, found by the pt translator, who rendered
        # the intended word correctly throughout — so these close a gap between
        # the editions rather than opening one. The digit ZERO standing in for
        # a capital O is this book's signature defect.
        "replacements": [
            ("Bless the Lord, 0 my soul", "Bless the Lord, O my soul"),
            ("0 arm of the Lord", "O arm of the Lord"),
            ("cry unto Hun day", "cry unto Him day"),
            ("Let us. try to understand", "Let us try to understand"),
            ("to ask he Lord", "to ask the Lord"),
            ("signs and w6nders", "signs and wonders"),
            ("we may torn part of them", "we may form part of them"),
            ("extends it~ powerful", "extends its powerful"),
            ("Un-confessed sin", "Unconfessed sin"),
            # Numerals the extractor split, and one colon it moved. Left as a
            # literal each time rather than a rule: a space inside a reference
            # is period typography in the 17c texts and an artifact here, and
            # nothing mechanical separates the two.
            ("Mark 5 :25", "Mark 5:25"),
            ("Acts 4:29\u20143 1", "Acts 4:29\u201431"),
            ("Romans 4:19\u20142 1", "Romans 4:19\u201421"),
            # A closing curly quote the text layer rendered as a tilde pair,
            # and a quotation that opens single and closes double with no
            # terminal stop. Both inside quotations of Matthew 17.
            ("impossible to you~~", "impossible to you\u201d"),
            (
                "us: \u2018Because of your unbelief\u201d The",
                "us: \u201cBecause of your unbelief.\u201d The",
            ),
            # Found by the ar translators (job #764), who read every sentence of
            # all 32 chapters. Only defects with ONE possible intended reading
            # are repaired here; the ambiguous ones are named in that PR and
            # deliberately left alone (ch26's "an ultimate communion with God"
            # for "intimate", and ch19's your-sicknesses/my-sins voice shift,
            # where fixing means guessing the author's words).
            ("dine healing", "divine healing"),
            ("the healing of their sick-ness", "the healing of their sickness"),
            ("Thus is becomes those", "Thus it becomes those"),
            ("ignorant of his Y devices", "ignorant of his devices"),
            ("if ever miracles Were superfluous", "if ever miracles were superfluous"),
            ("must needs be Visible in the body", "must needs be visible in the body"),
            ("awaken Some special conviction", "awaken some special conviction"),
            ("and later on she become a zealous", "and later on she became a zealous"),
            # Typographic damage: a tilde for a semicolon, a tilde for nothing,
            # a bracket that opens round and closes square, a doubled stop, and
            # a period welded to a book name.
            ("unique in the creation~ it makes man", "unique in the creation; it makes man"),
            ("(or nature]", "(or nature)"),
            ("them\u201d~ (Mark 11:24", "them\u201d (Mark 11:24"),
            ("in your heart,. and count", "in your heart, and count"),
            (".James 5:15", "James 5:15"),
            # "Jdb" for "Job" - the quoted words verify against Job 42:6.
            ("(Jdb 42:6)", "(Job 42:6)"),
            # Found by the hi translators (job #707), same single-reading OCR
            # classes as above: split verse number, digit zero for the vocative
            # O, J for I, "eider" for "elder", stray capital/comma/apostrophe,
            # and a doubled single-open mark where the book's double belongs.
            # Language-agnostic on purpose: pt and ar reproduced the split
            # faithfully ("Lucas 15:3 1", "لوقا 15:3 1"), so repair the digits.
            ("15:3 1", "15:31"),
            ("and so J did not enjoy", "and so I did not enjoy"),
            ("The eider son", "The elder son"),
            ("A minister once told me That,", "A minister once told me that,"),
            ("thoughts of Thee, 0 God", "thoughts of Thee, O God"),
            ("\u201c0 Christ", "\u201cO Christ"),
            ("0 beloved brethren", "O beloved brethren"),
            ("Not unto us, 0 Lord", "Not unto us, O Lord"),
            ("began to pour its\u2019 sap", "began to pour its sap"),
            ("Christ, the, heavenly Vine", "Christ, the heavenly Vine"),
            ("one may say, \u2018\u2018pray", "one may say, \u201cpray"),
        ],
    },
    "the-gospel-of-healing": {
        # The same digit-zero defect as divine-healing, in the same quotation
        # of Psalm 103. Found while fixing that book; the two were extracted
        # from the same kind of scan.
        "replacements": [("Bless the Lord, 0 my soul", "Bless the Lord, O my soul")],
    },
    "godliness": {
        # ch01: "may be styled an Antinomian faith" — the sentence needs the
        # verb, not the adverb.
        "replacements": [("maybe styled an Antinomian", "may be styled an Antinomian")],
    },
    "jesus-himself-2": {
        # ch01: a verse RANGE whose hyphen the extractor dropped, welding the
        # two numbers together. The passage quoted is Luke 22:28-29.
        "replacements": [("Luke 22: 2829", "Luke 22:28-29")],
    },
    "the-unselfishness-of-god": {
        "replacements": [
            ("blesse d!", "blessed!"),
            ("crystallize d,", "crystallized,"),
            ("scepti c!", "sceptic!"),
            ("lif e.", "life."),
            ("evangelical s,", "evangelicals,"),
            # ch22 ended without its closing full stop.
            ("filled me with joy</p>", "filled me with joy.</p>"),
            # ch2/ch19/ch23: drop cap fused to the word after it.
            ("<p>Iwas", "<p>I was"),
            ("<p>Ihave", "<p>I have"),
            # The PDF layer splits words mid-token — a different artifact from
            # the line-break hyphen, because there is no hyphen to rejoin on
            # and so no rule can find them. Found by the pt translator, who
            # rendered the intended word correctly in every case; these close
            # the gap between the editions rather than opening one.
            #
            # The leading SPACE in " th e" is what makes the first pair safe:
            # it fires only where "th" stands alone as a word, so the 19 "with
            # e…" sequences in this book are untouched while all ten real ones
            # ("far th e best", " th erefore", " th eir") are repaired.
            (" th e", " the"),
            ("unselfishne ss", "unselfishness"),
            ("pray er of our Lord", "prayer of our Lord"),
            ("He does the wo rks", "He does the works"),
            ("of her te rror", "of her terror"),
            ("my life have p assed", "my life have passed"),
            ("clapping of h ands", "clapping of hands"),
            ("there, bu t nothing", "there, but nothing"),
            ("home again last nig ht", "home again last night"),
            ("succeed beau tifully", "succeed beautifully"),
            ("an accent of p ity", "an accent of pity"),
            ("as wel l as she could", "as well as she could"),
            ("my s ister says", "my sister says"),
            ("better men and wom en", "better men and women"),
            ("in ce rtain circles", "in certain circles"),
            # Spaced hyphens the rejoin rule cannot reach: it anchors on a word
            # character immediately before the hyphen, and here the space is on
            # both sides.
            ("\u201cgrown - ups", "\u201cgrown-ups"),
            ("the best - loved man", "the best-loved man"),
            # Found by the ar translators (job #760), who read every sentence
            # of all 32 chapters. Same PDF-split class as the entries above —
            # each pair matched exactly once in the fixture (short fragments
            # are scoped with surrounding words precisely because bare "o f" /
            # "n ot" match legitimate cross-word sequences 132 and 7 times).
            # Ambiguous findings are NOT here; they are named in that PR.
            ("t hey", "they"),
            ("seem ed", "seemed"),
            ("B ut", "But"),
            ("ci rcle", "circle"),
            ("Hav e", "Have"),
            ("hea vy", "heavy"),
            ("mann er", "manner"),
            ("bestow ed", "bestowed"),
            ("thou ma y wait", "thou may wait"),
            ("Com mandments", "Commandments"),
            ("m ight", "might"),
            ("Frie nds", "Friends"),
            ("s prinkled", "sprinkled"),
            ("stand they m ust", "stand they must"),
            ("stra ight", "straight"),
            ("mys tery", "mystery"),
            ("e quivalent", "equivalent"),
            ("once m ore", "once more"),
            ("the ir", "their"),
            ("Hi s spirit", "His spirit"),
            ("trut h", "truth"),
            ("wate r", "water"),
            ("salvati on", "salvation"),
            ("m aterial", "material"),
            ("try G od\u2019s", "try God\u2019s"),
            ("him l ie down", "him lie down"),
            ("convi nced", "convinced"),
            ("cont rary", "contrary"),
            ("the lov e of God", "the love of God"),
            ("som ething", "something"),
            ("N othing", "Nothing"),
            ("supr emely", "supremely"),
            ("be tter", "better"),
            ("there fore", "therefore"),
            ("c ould", "could"),
            ("des pair", "despair"),
            ("Chr ist", "Christ"),
            ("meaning ha d I", "meaning had I"),
            ("prac tically", "practically"),
            ("provo ked", "provoked"),
            ("must m ean", "must mean"),
            ("kno wn", "known"),
            ("rem oval", "removal"),
            ("C hristian", "Christian"),
            ("he aring", "hearing"),
            ("Metho dist", "Methodist"),
            ("con vinced", "convinced"),
            ("the bl ue", "the blue"),
            ("myse lf", "myself"),
            ("greates t", "greatest"),
            ("step ped", "stepped"),
            ("betwe en", "between"),
            ("alway s", "always"),
            ("tha t", "that"),
            ("ab ove", "above"),
            ("consequen ce", "consequence"),
            ("a n indescribable", "an indescribable"),
            ("yo ung or old", "young or old"),
            ("applie d", "applied"),
            ("Praise d forever", "Praised forever"),
            ("with in the fold", "within the fold"),
            ("and sa id:", "and said:"),
            ("v iolent", "violent"),
            ("crea ture", "creature"),
            ("ag ainst", "against"),
            ("is yo ur Master", "is your Master"),
            ("b rought", "brought"),
            ("a v erse", "a verse"),
            ("Christian li fe", "Christian life"),
            ("c ompanions", "companions"),
            ("h ours", "hours"),
            ("the ju st", "the just"),
            ("ea rnest", "earnest"),
            ("f eelings", "feelings"),
            ("suff er", "suffer"),
            ("prese nt", "present"),
            ("e poch", "epoch"),
            ("pi ece", "piece"),
            ("th rough", "through"),
            ("imputin g", "imputing"),
            ("satis fy", "satisfy"),
            ("shal l", "shall"),
            ("God a rise", "God arise"),
            ("O h Thou", "Oh Thou"),
            ("exactl y", "exactly"),
            ("cam e to England", "came to England"),
            ("understa nd", "understand"),
            ("righteous ness", "righteousness"),
            ("acc ept", "accept"),
            ("acc ompanying", "accompanying"),
            ("ap ostle", "apostle"),
            ("gre ater", "greater"),
            ("bre ak", "break"),
            ("wo nder", "wonder"),
            ("u tterly", "utterly"),
            ("pl ace", "place"),
            ("c hance", "chance"),
            ("i t is vain", "it is vain"),
            ("is i t?", "is it?"),
            ("know n ot", "know not"),
            ("all m y heart", "all my heart"),
            ("contained f or them", "contained for them"),
            ("God f or His", "God for His"),
            ("it w as never", "it was never"),
            ("he w as refused", "he was refused"),
            ("not o f the letter", "not of the letter"),
            ("isn\u2019t t his", "isn\u2019t this"),
            ("was al l the blessing", "was all the blessing"),
            ("an d I always", "and I always"),
            ("nor d id we", "nor did we"),
            ("Yes T o every", "Yes To every"),
            ("tease d him", "teased him"),
            # Same spaced-hyphen class as the two pairs above.
            ("Self -introversion", "Self-introversion"),
            ("awe - inspiring", "awe-inspiring"),
            ("broad -brimmed", "broad-brimmed"),
            ("church -going", "church-going"),
            ("dove -coloured", "dove-coloured"),
            ("grown - up", "grown-up"),
            ("heart -burnings", "heart-burnings"),
            ("leg -of", "leg-of"),
            ("man - made", "man-made"),
            ("self - assertive", "self-assertive"),
            ("self - sacrifice", "self-sacrifice"),
            ("so -and", "so-and"),
            ("sugar - scoop", "sugar-scoop"),
            ("sugar -scoop", "sugar-scoop"),
            ("to -day", "to-day"),
            # A curly closing double quote OCR\u2019d as two right single
            # quotes after "gay".
            ("\u201cgay\u2019\u2019", "\u201cgay\u201d"),
            # ch18\u2019s three citations carry stray OCR bullet markers
            # ("x 1 John 5:1", "</p><p>x John 3:24"), and the middle one
            # miscites John 5:24 as 3:24 \u2014 the quoted words are 5:24
            # verbatim ("Verily, verily \u2026 passed from death unto life").
            # All three pairs are written to match in ANY language (the
            # key-in-my-hand precedent): pt/sw/lg reproduce the bullets and
            # the miscitation around localized book names, es already
            # corrected silently, and each pattern occurs nowhere else in any
            # edition of this work.
            ("</p><p>x ", "</p><p>"),
            (": x 1 ", ": 1 "),
            ("3:24: \u201c", "5:24: \u201c"),
        ],
    },
    "the-inner-chamber": {
        # ch5: hyphens standing in for em-dashes, and a dropped closing full
        # stop; ch25: dropped closing full stop. (This book backs a seeded plan,
        # so it's never re-chapterized — these are body-only, order-safe fixes.)
        "replacements": [
            ("the scales- only practice", "the scales — only practice"),
            ("makes perfect- set yourself", "makes perfect — set yourself"),
            ("apply the needed first lessons</p>", "apply the needed first lessons.</p>"),
            ("seat of His light and Holy Spirit</p>", "seat of His light and Holy Spirit.</p>"),
            # ch8/ch16: drop cap fused to the word after it (see the dropcap note).
            ("<p>Ithink", "<p>I think"),
            ("<p>Ithank", "<p>I thank"),
            # OCR slips found by the hi translator, each settled by the sentence
            # it sits in rather than by taste. Every pair carries enough context
            # to be unique, so none can fire on a word the author meant.
            ("this editorial consciousness", "this mediatorial consciousness"),
            ("our personnel need", "our personal need"),
            # "accumulation of Scripture knowledge only darkness and hardens":
            # the sentence needs two verbs, and it already has the second.
            ("only darkness and hardens", "only darkens and hardens"),
            # ch15 is the chapter ON meditation and spells it correctly nine
            # times; these four are the misses.
            ("element of true mediation", "element of true meditation"),
            ("J oshua. 1: 8", "Joshua. 1: 8"),
            ("all too littell the case", "all too little the case"),
            ("every promise implicity", "every promise implicitly"),
            # Matthew 5:3, in a list that runs poor / meek / hungry — the
            # beatitude order is what fixes which word was lost.
            ("the poor in heart, the meek", "the poor in spirit, the meek"),
            ("prejudices and prepositions", "prejudices and presuppositions"),
            # ch21 argues from a SECOND inadequacy, not from a boast: "My
            # importance is still greater" reverses the paragraph.
            ("My importance is still greater", "My impotence is still greater"),
            # ch22's epigraph carries an explicit Matthew 6:10 citation, so the
            # crib governed every translation and all five print "Thy/Your
            # kingdom come". The English is the only edition that is wrong.
            (
                "Our kingdom come, Your will be done",
                "Your kingdom come, Your will be done",
            ),
            # ch31 says "fullness of God" correctly three other times.
            ("all the fitness of God", "all the fullness of God"),
            # ch01, quoting Isaiah 27:3: "I will water it every moment".
            ("I will wter it every mom", "I will water it every moment"),
        ],
    },
    "the-body-of-christ-teens": {
        # ch1's section heading was fused into the first sentence of the body.
        "replacements": [
            (
                "<p>Understanding the Life God Gives Us When God saves you,",
                "<h3>Understanding the Life God Gives Us</h3><p>When God saves you,",
            ),
        ],
    },
    "feasting-at-the-table": {
        # ch7: drop cap fused to the word after it.
        "replacements": [
            ("repea t:", "repeat:"), ("wif e!", "wife!"),
            ("<p>Itrust", "<p>I trust"),
        ],
    },
    "the-christians-secret-of-a-happy-life-4": {
        # ch4/8/14/16: drop cap fused to the word after it.
        # ch13: small caps split, so GOD reads "G OD" (see the audit note on
        # he-holds-my-tomorrows for why the rejoin test is what makes this safe).
        "replacements": [
            ("sel f,", "self,"),
            ("<p>Ihave", "<p>I have"),
            ("<p>Ionce", "<p>I once"),
            ("<p>Amajor", "<p>A major"),
            ("<p>Agreat", "<p>A great"),
            ("Lord G OD", "Lord GOD"),
            # Lost-space word fusion (english_audit `word-fusion`).
            ("in our socalled temporal life", "in our so-called temporal life"),
        ],
    },
    "men-of-prayer-2": {
        "replacements": [("conversatio n.", "conversation.")],
    },
    "susanna-wesley-clarke": {
        # Archive OCR artifacts. Opening-word errors at two chapter starts
        # (ch.7 "OP the next" -> "OF the next"; ch.12 "MBS. WESLEY" -> "MRS.
        # WESLEY") and compound words/numbers whose hyphen or space the OCR lost.
        "replacements": [
            ("<p>OP the next", "<p>OF the next"),
            ("<p>MBS. WESLEY", "<p>MRS. WESLEY"),
            ("fiftyseven", "fifty-seven"),
            ("twentyeight", "twenty-eight"),
            ("twentyseven", "twenty-seven"),
            ("twentyone", "twenty-one"),
            ("earlypart", "early part"),
            # Nine more of exactly that class, which nothing reported until
            # `word-fusion` existed: a space lost INSIDE a sentence, where
            # `run-together` only ever saw the loss after a full stop.
            ("in after life towrite down", "in after life to write down"),
            ("public worship, tospend the time", "public worship, to spend the time"),
            ("all my children weresafe,", "all my children were safe,"),
            ("amiss for you tospeak of it", "amiss for you to speak of it"),
            ("sight of, and nointelligence of his fate", "sight of, and no intelligence of his fate"),
            ("him little or nohappiness.", "him little or no happiness."),
            ("which is tomend men", "which is to mend men"),
            ("for me which hehad at Oxford", "for me which he had at Oxford"),
            ("she was still sogenerous that", "she was still so generous that"),
            # --- ten OCR-damaged guillemets -----------------------------------
            #
            # Found by the widened quote guard in #1132 and repaired in the
            # fixture there; here so they reach a database that already holds
            # the book. Not one of the ten is a quotation mark — this is a
            # wholly straight-quoted work (796 marks, zero curly), so every «
            # and » in it is damage.
            #
            # Two are CORRUPTED LETTERS, which is the reason they survived every
            # other gate: they read as a stray mark rather than as a misspelling,
            # so no dictionary check was ever going to see them.
            ("a French refugee, a «ilk-weaver", "a French refugee, a silk-weaver"),
            (
                "it was evident that her «nd was approaching",
                "it was evident that her end was approaching",
            ),
            # Four are extraction garbage sitting between sentences. None of
            # these four is anchored on `<p>`: `body_text` carries the same
            # prose with the tags stripped, so a tag-anchored pair repairs
            # only `body_html` and leaves the fixture disagreeing with
            # itself — the drift #1146 exists to stop.
            ("**•»#* ' ' Of temperance", "' ' Of temperance"),
            # Cut at the garbage run rather than carrying the quotation that
            # follows it: the mark is not part of the defect, and a pair holding
            # a straight `"` cannot be checked by `test_no_replacement_pair_is_dead`,
            # which matches against the JSON-SERIALIZED corpus where it is `\"`.
            ("it is but aiming. #»••*.»# ", "it is but aiming. "),
            # Three are a stray mark where the letterpress had none.
            ("« Epworth, June 7th, 1705.", "Epworth, June 7th, 1705."),
            ("MY LORD, « Lincoln Castle,", "MY LORD, Lincoln Castle,"),
            (
                "and get «my children over into the street",
                "and get my children over into the street",
            ),
            # And one stands where a full stop belongs, ending the sentence.
            (
                "which led to my study » I could not find",
                "which led to my study. I could not find",
            ),
            # ch11's `» f:` sits at a quotation boundary. Rather than invent an
            # opening quote the source may or may not have had, close the
            # sentence and leave the structure alone.
            (
                "the intruding agency » f:My brother",
                "the intruding agency. My brother",
            ),
        ],
    },
    "the-person-and-work-of-the-holy-spirit": {
        "replacements": [
            ("Jesu s,", "Jesus,"),
            ("faithfulnes s.", "faithfulness."),
            ("eart h”", "earth”"),
            ("saved i. e. ,", "saved i.e.,"),
            ("salvatio n,", "salvation,"),
        ],
    },
    "blessed-adversity": {
        # Two transcription slips in Gutenberg #23438 ("A Ribband of Blue"),
        # both in the opening paragraph and both plainly errors rather than
        # period spelling: the Psalm 23 allusion names the SHEPHERD, and the
        # sentence reads "days of prosperity also".
        "replacements": [
            ("SHEPERD", "SHEPHERD"),
            ("days of prosperity aso", "days of prosperity also"),
        ],
    },
    # --- Drop caps that lost the space after them -----------------------------
    # An oversized first letter is a separate text run in the PDF, and where the
    # space between it and the rest of the line was lost the two words fused:
    # "Ithink" for "I think". Always the first word of a paragraph, which is why
    # each pattern is anchored to <p> — unanchored, "Iwas" would also match
    # inside a word. Distinct from `dropcap_letters` below, which handles the
    # other failure: the letter dropped out altogether.
    "soar-like-the-eagle-3": {
        "replacements": [
            ("<p>Iwas", "<p>I was"),
            ("<p>Iwell", "<p>I well"),
            # Lost-space word fusion: "excommunication from society, no ability
            # to obtain or keep employment". `notability` is a real word, but
            # not the one meant here.
            ("from society, notability to obtain", "from society, no ability to obtain"),
        ],
    },
    "if": {
        # Unpublished (copyright audit), but the row is in the fixture and would
        # ship wrong if it were ever republished.
        "replacements": [("<p>Ihave", "<p>I have")],
    },
    "humility-2": {
        # The other failure mode, mid-chapter so `dropcap_letters` (first
        # paragraph only) can't reach it: the H is simply gone. The paragraph
        # above it opens "Humility is the path to death", which is what settles
        # the missing letter.
        #
        # ch04: the import put words in Murray's mouth. Where he wrote "The
        # poor, who have nothing in themselves, to them the kingdom comes; the
        # meek, who seek nothing in themselves, theirs the earth shall be", the
        # imported text substitutes a fabricated objection and answer about
        # Christians "owning land, cars, and lots of businesses" — cars, in an
        # 1895 devotional. Same class as the machine-written chapter summaries
        # and the "name of God"/"name of dog" inversion: an ochorus.com import
        # artifact, and the worst kind, because a public-domain library's whole
        # claim is that the words are the author's.
        #
        # The repair is written for all four editions. Corrections are keyed by
        # slug and every language shares it, so each pair matches only its own
        # edition; the translations reproduced the interpolation faithfully,
        # which is what a translator should do, and they have to be repaired
        # with the English or they translate text that no longer exists.
        # Paragraph boundaries are preserved so the editions stay parallel.
        "replacements": [
            ("<p>umility is the blossom", "<p>Humility is the blossom"),
            # -- en
            ("The poor, who have given up everything for the sake of Christ, to"
             " them the kingdom comes. One might say: “But some Christians"
             " are really wealthy, owning land, cars, and lots of businesses."
             "”",
             "The poor, who have nothing in themselves, to them the kingdom"
             " comes."),
            ("Yes, that can be very possible, especially as children of the Most"
             " High, but if they consider it vanity, they can easily give it"
             " away for the gospel; they are poor in the Spirit. The meek,",
             "The meek,"),
            # -- lg
            ("Abaavu, abaawaayo buli kimu ku lwa Kristo, be bajjirwa obwakabaka."
             " Omuntu ayinza okugamba nti: &ldquo;Naye Abakristaayo abamu bagagga"
             " nnyo, nga balina ettaka, emmotoka, n'obusuubuzi bungi.&rdquo;",
             "Abaavu, abatalina kantu mu bo bennyini, be bajjirwa obwakabaka."),
            ("Yee, ekyo kiyinza okubaawo, naddala nga bwe bali abaana b'Oyo Ali"
             " Waggulu Ennyo; naye bwe bakitwala nga butaliimu, bayinza mangu"
             " okukiwaayo ku lw'enjiri; abo baavu mu Mwoyo. Abawombeefu,",
             "Abawombeefu,"),
            # -- ar
            ("المساكين، الذين تركوا كل شيء من أجل المسيح، إليهم يأتي الملكوت. وقد"
             " يقول قائل: “ولكنّ بعض المسيحيين أغنياء حقًّا، يملكون الأراضي"
             " والسيارات وأعمالًا كثيرة.”",
             "المساكين، الذين لا يملكون في أنفسهم شيئًا، إليهم يأتي الملكوت."),
            ("نعم، هذا ممكن جدًّا، ولا سيما لأولاد العلي؛ ولكنهم إن حسبوا ذلك"
             " باطلًا، سهُل عليهم أن يبذلوه في سبيل الإنجيل؛ فهم مساكين بالروح."
             " والودعاء،",
             "والودعاء،"),
            # -- sw
            ("Maskini, ambao wameacha kila kitu kwa ajili ya Kristo, kwao ufalme"
             " huja. Mtu aweza kusema: “Lakini baadhi ya Wakristo ni"
             " matajiri kweli, wana ardhi, magari, na biashara nyingi.”",
             "Maskini, wasio na kitu ndani yao wenyewe, kwao ufalme huja."),
            ("Naam, laweza kuwezekana kabisa, hasa wakiwa watoto wa Aliye Juu"
             " Sana; lakini wakiihesabu kuwa ubatili, waweza kwa urahisi kuitoa"
             " kwa ajili ya injili; wao ni maskini wa Roho. Wenye upole,",
             "Wenye upole,"),
            # OCR run-together, ch09/ch10.
            ("selfexaltation", "self-exaltation"),
            ("allpervading", "all-pervading"),
        ],
    },
    # --- found by the English audit (scan of all 65 books + 28 sermons) -------
    # Small caps split by the PDF extractor, so LORD reads "L ORD". The test
    # that finds these without drowning in false positives is that the pieces
    # REJOIN into a real word: "L"+"ORD" is LORD, where "A"+"SHORT" is not a
    # word and is just a small-caps opening.
    "he-holds-my-tomorrows": {
        "replacements": [
            ("L ORD", "LORD"),
            # A name, so it is fixed rather than left as printed (english-qa's
            # misspelling rule). The book spells it correctly elsewhere.
            ("To Nicodemas He said", "To Nicodemus He said"),
        ],
    },
    "stepping-stones-2": {
        "replacements": [
            ("L ORD", "LORD"),
            # Real people and places, misspelled by the import. Left as printed
            # in the translations until now, per the leave-his-reference rule,
            # but these are transcription errors rather than the author's own.
            ("Bob Beamer", "Bob Beamon"),
            ("Nicki Cruz", "Nicky Cruz"),
            # The same family is "Wiebe" in ch13 and ch14.
            ("Eileen Weibe", "Eileen Wiebe"),
            ("Cuidad Victoria", "Ciudad Victoria"),
            # Qualified with "city of" because the bare string also occurs
            # inside "Brazilian" five times, which is correct and must not move.
            ("city of Brazilia", "city of Brasília"),
            ("Stocklholm", "Stockholm"),
            ("Guatamalan", "Guatemalan"),
            ("Malasia", "Malaysia"),
            ("Chapultapek", "Chapultepec"),
            ("Deja Vue", "Déjà vu"),
        ],
    },
    "prevailing-prayer": {
        # The three Roman brothers are the Horatii (Livy I.24-25); Moody's
        # printed text spells them correctly two sentences earlier.
        "replacements": [("Heratii", "Horatii")],
    },
    # OCR read "ears" as "cars" — the c/e confusion that also gave "L ORD" its
    # split. In Wesley it wrecks a scripture quotation outright: "he that hath
    # cars to hear, let him hear" (Matthew 11:15).
    "sermons-on-several-occasions": {
        "replacements": [("cars to hear", "ears to hear")],
        # Wesley's Standard Sermons carry the 1872 editor's footnotes, and the
        # importer doubled every marker and inlined every note (the same defect
        # PR #1243 unwelded by hand elsewhere). 122 of them are a pure
        # transcription stamp — "[text from the 1872 edition]" — welded into a
        # "Sermon N" number-heading, saying nothing a reader wants. This flag
        # runs `strip_transcription_footnotes`, which removes exactly those and
        # nothing else. The genuine notes in this book (each sermon's "Preached
        # at ... 1738" dateline, the series descriptions, the editor's
        # commentary on the Great Assize) are left welded on purpose — they are
        # content, and placing them where they read well is a separate pass.
        "strip_transcription_footnotes": True,
    },
    "ten-commandments": {
        "replacements": [
            ("hands, and eyes, and cars", "hands, and eyes, and ears"),
            ("carries the devil in his car", "carries the devil in his ear"),
        ],
    },
    "talks-to-the-farmer": {
        # Six misattributed citations, every one naming the wrong BOOK rather
        # than a slipped digit. Five were found by the Swahili translators of
        # job #420 and confirmed against the ASV; the sixth (ch15) was reported
        # by that chapter's translator and independently confirmed by
        # `audit_citations` once its rival search could look outside the cited
        # book. Only the reference moves — Spurgeon's wording is untouched.
        #
        # ch03's is the one that settles the class: the SAME chapter cites this
        # clause correctly as Psalm 147 in its opening paragraph and quotes it
        # six more times, then miscites it here.
        "replacements": [
            # "Who can stand before his cold?" — Job 37:22 is the golden splendour.
            ("(Job 37:22, ESV)", "(Psalm 147:17, ESV)"),
            # "eat, O friends; drink, yea, drink abundantly, O beloved" —
            # Isaiah 55:1 is "Ho, every one that thirsteth".
            ("(Isaiah 55:1)", "(Song of Solomon 5:1)"),
            # "He takes up the isles like a very little thing" — Psalm 136:16
            # is the leading through the wilderness.
            ("(Psalm 136:16)", "(Isaiah 40:15)"),
            # "Hear, O heavens, and give ear, O earth" — Jeremiah 7:28 is
            # "this is the nation that hath not hearkened".
            ("(Jeremiah 7:28)", "(Isaiah 1:2)"),
            # "a sharp threshing instrument with teeth" — Jeremiah 51:20 is the
            # battle-axe.
            ("(Jeremiah 51:20)", "(Isaiah 41:15)"),
            # "under the rod of the covenant" — Psalm 89:32 visits transgression
            # with the rod, which is a different rod.
            ("(Psalm 89:32)", "(Ezekiel 20:37)"),
            # --- the same six, as they reached the shipped translations ------
            # A wrong reference is the one English defect that survives
            # translation intact: a careful translator reproduces what is
            # printed, so each of these became one defect per language. Book
            # names taken from the shipped corpora, not guessed — lg "Zabbuli"
            # (128 uses), "Isaaya" (60), "Oluyimba lwa Sulemaani" (6);
            # sw "Zaburi" (77), "Isaya" (66), "Ezekieli" (7),
            # "Wimbo Ulio Bora" (7).
            ("(Yobu 37:22)", "(Zabbuli 147:17)"),
            ("(Isaaya 55:1)", "(Oluyimba lwa Sulemaani 5:1)"),
            ("(Zabbuli 136:16)", "(Isaaya 40:15)"),
            ("(Yeremiya 7:28)", "(Isaaya 1:2)"),
            ("(Yeremiya 51:20)", "(Isaaya 41:15)"),
            # lg's Psalm 89:32 -> Ezekiel 20:37 is deliberately NOT repaired:
            # the whole Luganda corpus contains one Ezekiel reference and it is
            # an untranslated English abbreviation, "(Ezek. xviii. 32)", so
            # there is no attested Luganda form to correct it to. Guessing a
            # Bible book name in a language I cannot check is how a repair
            # becomes a new defect. Left for a Luganda reviewer.
            ("(Ayubu 37:22)", "(Zaburi 147:17)"),
            ("(Isaya 55:1)", "(Wimbo Ulio Bora 5:1)"),
            ("(Zaburi 136:16)", "(Isaya 40:15)"),
            ("(Yeremia 7:28)", "(Isaya 1:2)"),
            ("(Yeremia 51:20)", "(Isaya 41:15)"),
            ("(Zaburi 89:32)", "(Ezekieli 20:37)"),
        ],
    },
    "christ-all-in-all": {
        # "I am the way, the truth, and the life" is John 14:6; John 10 is the
        # sheepfold. Almost certainly a dropped "xiv." — the house style here is
        # roman chapters, so the repair keeps that and supplies the verse the
        # printed reference omits.
        #
        # Worth recording WHY this belongs on the English rather than in each
        # edition: the three existing translations already handle it three
        # different ways — es silently corrects it to "(Juan 14)", pt reproduces
        # it AND leaves the roman numeral untranslated as "(João x.)", and ar
        # reproduces it as "(يوحنّا 10)". Fixing the source is what stops a
        # fourth reading appearing with the next language.
        # The Swahili edition (job #424) reproduced it faithfully as
        # "(Yohana 10)", so it is repaired here too, in that edition's own
        # house style — Western digits, tight C:V. es already reads "(Juan 14)"
        # and needs nothing; pt and ar are left for their reviewers, since
        # "(João x.)" also carries an untranslated roman numeral and that is a
        # second decision, not this one.
        "replacements": [
            ("(John x.)", "(John xiv. 6.)"),
            ("(Yohana 10)", "(Yohana 14:6)"),
        ],
    },
    "waiting-on-god": {
        # Found by the Spanish translators of job #514, and by running
        # `audit_citations` over an in-memory copy of the book — the sweep is
        # blind to it as it stands, because this is the corpus's only work that
        # sets its quotations in straight SINGLE quotes and both PAIR and LEAD
        # require `“ ”` or `"`. Converted, it reads 37 pairs and flags the first
        # entry below.
        #
        # THREE MISCITED REFERENCES, which is the class worth the entry: a
        # translator reproduces a printed reference faithfully, so each one
        # becomes a defect per language.
        "replacements": [
            # The book's own motto verse. "My soul, wait thou only upon God; for
            # my expectation is from Him. He only is my rock and my salvation" is
            # Psalm 62:5-6 — and ch01 of this same book cites it correctly as
            # "Ps. 62:5". The Spanish edition already reads "Sal. 62:5,6", so it
            # needs nothing here.
            ("—Isa. 62:5,6.", "—Ps. 62:5,6."),
            # Contents entry 4. Psalm 114 has eight verses, so 114:14-15 cannot
            # exist; ch06 prints the same epigraph correctly as "Ps. 145:14, 15".
            ("Ps. 114:14, 15", "Ps. 145:14, 15"),
            ("Sal. 114:14, 15", "Sal. 145:14, 15"),
            # ch25 walks through Isaiah 63 verse by verse. "Why hast Thou
            # hardened my heart from Thy fear? Return for Thy servants' sake" is
            # 63:17; 63:19 is "We are become as they over whom thou never barest
            # rule". The adjacent "(ver. 15.)" in the same paragraph is right,
            # which is what makes this a slipped digit rather than a different
            # verse numbering.
            ("(ver. 19.)", "(ver. 17.)"),
            ("(v. 19)", "(v. 17)"),
            # Contents entry 15. "They soon forgot His works: they waited not
            # for His counsel" is Ps. 106:13, and chapter 15's own epigraph
            # cites it so; Ps. 56:12 ("Thy vows are upon me, O God") has
            # nothing to do with counsel. Found by the Swahili run of job #531.
            ("For His Counsel.—Ps. 56:12.", "For His Counsel.—Ps. 106:13."),
            ("Por Su Consejo.—Sal. 56:12.", "Por Su Consejo.—Sal. 106:13."),
            # Contents entry 16. "I wait for the Lord, my soul doth wait" is
            # Ps. 130:5-6, and chapter 16's epigraph cites it so; Ps. 80:5-6 is
            # the bread of tears. Same find, same run.
            ("Heart.—Ps. 80:5, 6.", "Heart.—Ps. 130:5, 6."),
            ("Corazón.—Sal. 80:5, 6.", "Corazón.—Sal. 130:5, 6."),
            # --- lost word spaces, all extraction artifacts -------------------
            # These were found by hand, and the note here said a general check
            # would need a dictionary the audit does not carry: splitting on
            # "both halves are corpus words" yields 746 candidates corpus-wide,
            # nearly all real compounds ("waterfall") or archaic verb forms
            # ("delightest"). `english_audit.word-fusion` is now that check —
            # the library's own word counts ARE the dictionary, and requiring a
            # function-word head and a rare fused form is what made it precise.
            # It found `andhappiness` below independently, plus sixteen more
            # across seven other works.
            ("God Himselfmust work", "God Himself must work"),
            ("life andhappiness", "life and happiness"),
            # The same defect made by markup rather than by a lost character:
            # the italic opens hard against "is", so a browser renders "isthe".
            ("it is<i>the God</i> who works", "it is <i>the God</i> who works"),
            ("afresh forboldness", "afresh for boldness"),
            ("freshfulfilment", "fresh fulfilment"),
            ("in that day,Lo", "in that day, Lo"),
            ("our God;we have waited", "our God; we have waited"),
            ("only</i>upon Him", "only</i> upon Him"),
            # --- word slips, each decidable from the sentence itself ----------
            # Verbless as printed; "Just bow … before His great glory, and be
            # still" restores it.
            ("Just how in emptiness", "Just bow in emptiness"),
            # Luke 2:38, "all them that looked for redemption".
            ("to all then that looked", "to all them that looked"),
            # The hymn's line is "in woe or in weal"; the stanza rhymes
            # feel/heal/weal/still.
            ("in woo or in weal", "in woe or in weal"),
            ("Thirtieth-First Day", "Thirty-First Day"),
            # The chapter's own title reads "Its Certainty of Blessing".
            ("It Certainty of Blessing", "Its Certainty of Blessing"),
            # Contents entry 26; the chapter title reads "In Holy Expectancy".
            ("In Holy Expectency", "In Holy Expectancy"),
            ("With Additonal Extracts", "With Additional Extracts"),
            ("to work us in by His Son", "to work in us by His Son"),
            # Subject is "He", so "shall"; Psalm 37:34.
            ("And He shalt exalt thee", "And He shall exalt thee"),
            # Psalm 104:27-28, "that thou mayest give them their meat". The <i>
            # sits inside the phrase, so the pair has to carry it.
            ("that thou may <i>give</i>", "that thou mayest <i>give</i>"),
            # The same quotation is set with a capital at its four other sites.
            ("'Rest in the lord, and wait", "'Rest in the Lord, and wait"),
        ],
    },
    "the-reformed-pastor": {
        # RESTORED PARAGRAPHING, not an OCR repair — this puts a block boundary
        # back rather than mending a word. CCEL's transcription runs five of
        # chapter 4's paragraphs into the one before them, leaving 7,689 words in 19
        # blocks — 405 to a block against a corpus median of 92, which is what
        # `english_audit._lost_paragraphing` flags. (The defect long predates
        # the finding: it sat at ~385 until #1189 removed the heading that
        # restated the chapter's own title, and one block fewer put the mean
        # over the bar.)
        #
        # Where a paragraph breaks is a judgement about the prose, so none of
        # these five was guessed from block length: each was READ OFF THE SCAN
        # of the edition this text is a transcription of — Brown's 1862 printing
        # (archive.org `reformedpastor00baxtgoog`, section pages 19-46). Its OCR
        # word coordinates carry the compositor's first-line indent, ~85 units
        # against a body margin that varies by under ±15 on every page, so every
        # paragraph opening in the section is legible; and the whole section
        # holds exactly 23 of them. The five below are the ones the stored text
        # had lost.
        #
        # The other long blocks stay whole because the scan shows them whole:
        # "When man was made perfect" (577 words) and "Content not yourselves"
        # (637) each run unbroken across three pages. Baxter writes long, and
        # splitting to satisfy a mean would be inventing his paragraphing rather
        # than restoring it. The stored text also carries one break the 1862
        # printing does NOT have — before "When you are studying what to say to
        # your people", which begins mid-line there — and it is left alone: this
        # repair only puts back what was lost.
        #
        # Each seam carries the tail of the preceding sentence, so it matches
        # its one site and nowhere else in the book.
        "paragraph_breaks": [
            ("riches of the gospel from their own experience.", "Alas!"),
            ("will not do so small a matter to attain it.", "It is a palpable error"),
            ("so much skill and zeal as to awake them!", "Moreover, what skill"),
            ("and to the trouble of the Church?", "What skill is necessary to deal"),
            ("one poor ignorant soul for his conversion!", "O brethren! do you not shrink"),
        ],
    },
}

# First lowercase letter opening the first paragraph of a body.
_FIRST_LOWER = _re.compile(r"<p[^>]*>\s*([a-z])")


# A word broken across a line in the source PDF arrives as "self-" + a line
# break + "righteous", and the importer's paragraph merge rejoins the pieces
# with a space: "self- righteous". 434 of these are stored across 41 works, and
# a reader sees exactly that on the page — in *All of Grace*, four sentences
# away from "self-righteous" spelled correctly.
#
# This closes the space and NOTHING ELSE. It never removes the hyphen, and that
# restraint is the whole reason the rule is safe to run unattended:
#
#   self- righteous  -> self-righteous     the common case
#   to- day          -> to-day             Wesley's spelling, PRESERVED.
#                                          "today" would edit the author.
#   whole- hearted   -> whole-hearted      likewise; not "wholehearted"
#   Acts 1- 8        -> Acts 1-8           a verse range closes up correctly
#   perdi- tion      -> perdi-tion         still wrong, but no stray space;
#                                          "perdition" needs the source read
#
# Dropping the hyphen instead would be the modernisation `contemporize-book`
# exists to keep out of the original text: of the 24 cases where the unhyphenated
# form is attested elsewhere in the same work, several are period spellings
# ("to-day", "over-much", "four-fold") where the author's hyphen is the point.
#
# Two exclusions, both because the rule cannot prove the join:
#
# * a SUSPENDED compound — "two- and three-fold", "day- to day" — where the
#   space is correct English. Four cases corpus-wide.
# * anything resuming with a CAPITAL. A broken word never resumes capitalised,
#   so these are either a flattened dash or a proper-noun compound, and the two
#   are not separable without reading them:
#       "thus- Moses, the man of God"      a dash; joining welds a clause shut
#       "I ask- What does this mean?"      a dash
#       "non- Israelite king"              a real compound; joining is right
#       "Golden- Mouthed"                  a real compound
#   21 cases. Leaving ~7 genuine compounds unjoined is the cheaper mistake.
#
# Digits stay joinable, so a verse range closes up: "Acts 1- 8" -> "Acts 1-8".
_HYPHEN_LINEBREAK = _re.compile(r"(\w)-[ \t]+(?!(?:and|or|nor|to)\b)(?=[a-z0-9])")


def rejoin_linebreak_hyphens(body_html: str) -> str:
    """Close "self- righteous" to "self-righteous". Idempotent."""
    return _HYPHEN_LINEBREAK.sub(r"\1-", body_html)


# How a restored break is spelled, matching the block separator the fixture
# already uses between paragraphs. Named so the hygiene test can ask for the
# applied spelling instead of restating it.
PARAGRAPH_BREAK = "</p> <p>"


#: A footnote whose marker the extractor DOUBLED and whose text it inlined into
#: a heading, where the note is only a transcription-provenance stamp — which
#: 1872 reprint the etext was keyed from. See the `welded-footnote` audit class
#: and PR #1243 for the defect; this is the sub-case that is pure noise. The
#: doubled SAME-numbered marker and the `</h2>` lookahead together mean this can
#: only ever fire on such a heading — never on a real reference, an ordinal, or
#: a note carrying content — so it strips the marker and the stamp and leaves
#: the heading text. Opt-in per work (`strip_transcription_footnotes`), because
#: "1872 edition" is specific to Wesley's Sermons and no global rule should scan
#: every book for it. Genuine notes ("Preached at St. Mary\'s, Oxford, 1738")
#: are deliberately NOT matched here — they are kept and re-placed by hand.
_TRANSCRIPTION_FOOTNOTE = _re.compile(
    r"\s*<sup>(\d+)</sup>\s*<sup>\1</sup>"
    r"\s*[\[(]\s*text (?:from|of) (?:the )?1872 (?:edition|ed)\.?\s*[\])]"
    r"\s*(?=</h2>)",
    _re.IGNORECASE,
)


def strip_transcription_footnotes(body_html: str) -> str:
    """Remove doubled-marker transcription stamps welded into headings. Idempotent.

    `body_html` only, and safe on the tagless `body_text` besides: the pattern
    is anchored on `<sup>` markup and an `</h2>` lookahead, neither of which a
    stripped body carries, so it no-ops there.
    """
    return _TRANSCRIPTION_FOOTNOTE.sub("", body_html)


def restore_paragraph_breaks(body_html: str, seams: Sequence[tuple[str, str]]) -> str:
    """Split a run-together paragraph at each declared seam. Idempotent.

    `body_html` ONLY, which is why this is not a `replacements` pair: a seam is
    plain prose with no markup in it, so a pair spelling out "…experience." →
    "…experience.</p> <p>" would match the DERIVED, tagless `body_text` just as
    happily and write block tags into a field that must never hold any. The
    escape hatch the other keys use — anchoring `old` on markup a tagless body
    can never contain (`<p>Amajor`) — is not available mid-paragraph, so the
    guard below stands in for it: no `</p>`, no paragraphs to restore.
    `tests_english_audit.test_the_fixture_is_clean` is what feeds this function
    `body_text`; production never needs that field corrected, because
    `Chapter.save()` re-derives it from the HTML this has already fixed.
    """
    if not seams or "</p>" not in body_html:
        return body_html
    for tail, head in seams:
        body_html = body_html.replace(f"{tail} {head}", f"{tail}{PARAGRAPH_BREAK}{head}")
    return body_html


def apply_body_corrections(slug: str, order: int | None, body_html: str) -> str:
    """Apply a work's body corrections to one chapter's HTML. Idempotent.

    ``order`` selects a drop-cap letter and is chapter-only; pass ``None`` for a
    work that has no chapters (sermons), so a slug that happens to collide with
    a book's can never inject a stray capital.

    The line-break hyphen rejoin runs for EVERY work, not just those with a
    declared entry: it is a rule, not a list, which is the point — 434 instances
    across 41 works was never going to be hand-written string pairs.

    ORDER MATTERS. The declared replacements run FIRST, so a hand-written repair
    always beats the rule. `the-inner-chamber` is the case that proves it: it
    declares "the scales- only practice" -> "the scales — only practice", where
    the trailing hyphen is a DASH the extractor flattened, not a broken word.
    With the rule first, it closed to "scales-only", the declared pair no longer
    matched, and the em dash was lost. A regression test has guarded that string
    since long before this rule existed, and it caught this.

    Declared paragraph breaks run with the replacements, ahead of the rule, for
    the same reason: a seam is exact prose, and the rule could move a hyphen
    inside one out from under it.
    """
    entry = BODY_CORRECTIONS.get(slug)
    if entry:
        for old, new in entry.get("replacements", []):
            body_html = body_html.replace(old, new)
        body_html = restore_paragraph_breaks(body_html, entry.get("paragraph_breaks", ()))
        if entry.get("strip_transcription_footnotes"):
            body_html = strip_transcription_footnotes(body_html)
    body_html = rejoin_linebreak_hyphens(body_html)
    if not entry:
        return body_html
    letter = entry.get("dropcap_letters", {}).get(order)
    if letter:
        # Only when the first paragraph still starts lowercase (not yet fixed).
        m = _FIRST_LOWER.search(body_html, 0, 200)
        if m:
            body_html = body_html[: m.start(1)] + letter + body_html[m.start(1) :]
    return body_html


# --- the settled form: what the deploy leaves in the database ----------------
#
# `apply_body_corrections` is one of two steps that repair a chapter's prose;
# the other strips an absorbed trailing page number. The pair below name that
# composite, because SIX call sites have to agree on it and nothing made them:
# the two importers and `ingest.upsert_book`, which decide what a work looks
# like before it reaches the fixture; the `apply_body_corrections` command,
# which writes the settled form to the DB on every deploy; and `seed_sermons`
# and `seed_books`'s `chapter_drift`, which compare the fixture against the DB
# afterwards.
#
# The seeds are why this got a name. They compared the FIXTURE's uncorrected
# text against the DB's corrected text, so every deploy wrote
# `christ-all-in-all[sw]` back to its uncorrected body — losing a real repair
# (it cites John 14:6; the fixture says "Yohana 10") to a full-row UPDATE plus a
# tsvector rebuild, and pinning "Sermons: 0 created, N updated" permanently
# above zero. That line is the seed's only signal that a real edit shipped. The
# chapter side said the same thing in its own dialect: 13 books reported "body
# differs from fixture" on a FAITHFUL install, drowning the one warning that
# would have meant something.
#
# Both helpers are idempotent — `settled(settled(x)) == settled(x)`, guarded
# corpus-wide in tests_fixture.py — which is what lets the deploy converge: the
# corrections step writes the settled form, and the seeds recognise it as the
# fixture's own.
#
# NOTE this deliberately makes `chapter_drift` blind to one case: a human who
# runs `apply_body_corrections` against prod without regenerating the fixture.
# That is not a divergence anyone must act on — the release chain does exactly
# that on every deploy, by design. A data-migration transform or a hand edit
# produces text that is neither the fixture's nor the settled form, and is
# still reported.


def settled_chapter_body(slug: str, order: int | None, body_html: str) -> str:
    """A chapter body as the deploy's correction step leaves it. Idempotent."""
    # Deferred: `library.ingest` imports THIS module at import time, and it is
    # the heavier of the two (bs4, catalog, models). Called at import/deploy
    # time, long after both modules are loaded.
    from library.ingest import strip_trailing_pagenum

    return apply_body_corrections(slug, order, strip_trailing_pagenum(body_html))


def settled_sermon_body(slug: str, body_html: str) -> str:
    """A sermon body as the deploy's correction step leaves it. Idempotent.

    No page-number strip — that rule reads a chapter's absorbed page marker.
    """
    return apply_body_corrections(slug, None, body_html)
