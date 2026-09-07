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
    "the-secret-of-guidance": {
        # CCEL's TOC sets these titles in Title Case with a roman-numeral prefix
        # ("III. The Secret Of Christ's Indwelling"). clean_title's roman strip is
        # ALL-CAPS-gated (so it keeps Murray's mixed-case "I. Humility"), so the
        # numerals survive here and the reader — which prints the chapter number
        # itself — would double them ("3. III. …"). Give the clean titles, also
        # normalising CCEL's capitalised "Of/To/With". Meyer's period spelling
        # "Fulness" is kept as-is (not "Fullness").
        "chapter_titles": {
            1: "The Secret of Guidance",
            2: "Where Am I Wrong?",
            3: "The Secret of Christ’s Indwelling",
            4: "Fact! Faith! Feeling!",
            5: "Why Sign the Pledge?",
            6: "Burdens, and What to Do with Them",
            7: "How to Bear Sorrow",
            8: "In the Secret of His Presence",
            9: "The Fulness of the Spirit",
        },
    },
    "life-experience-gospel-labours": {
        # A compilation: the autobiography ("LIFE, &c."), the AME African
        # Supplement, three devotional Acts, the 1793 yellow-fever Narrative, and
        # two addresses. Four section headings in the source are bare or their
        # descriptive subtitle sits in the body — give them their known titles.
        "chapter_titles": {
            2: "The Life of Richard Allen",
            7: "A Narrative of the Proceedings of the Coloured People",
            9: "An Address to Those Who Keep Slaves",
            11: "A Short Address to the Friends of Him Who Hath No Helper",
        },
    },
    "amanda-smith-autobiography": {
        # The 36 numbered chapters carry only long "arguments" as titles (the
        # source's own Contents). These are curated concise titles distilled from
        # each argument; the front matter, the Address (37) and the two guest
        # testimonies (38-39) keep their own headings.
        "chapter_titles": {
            3: "Birth, Parentage, and Deliverance from Slavery",
            4: "Removal to Pennsylvania",
            5: "Remembrances of My Girlhood Days",
            6: "Marriage and Conversion",
            7: "How I Bought My Sister Frances",
            8: "Disappointed Hopes and My Father's Death",
            9: "The Blessing of Sanctification",
            10: "My First Temptation",
            11: "His Presence and My Obedience",
            12: "Learning 'Thy Will Be Done'",
            13: "My Call to Go Out",
            14: "My Last Call, and How I Obeyed It",
            15: "Remembrances of Camp Meeting",
            16: "Kennebunk Camp Meeting",
            17: "At Dr. Taylor's Church, New York",
            18: "The National Camp Meeting at Knoxville",
            19: "Sea Cliff, and First Thoughts of Africa",
            20: "Pittman Church, Philadelphia",
            21: "The Call to Go to England",
            22: "Liverpool, and Pages from My Diary",
            23: "Scotland, London, and the Call to India",
            24: "On the Way to India",
            25: "India: Notes from My Diary",
            26: "The Great Meeting at Bangalore",
            27: "Africa: Arrival at Monrovia",
            28: "Temperance Work at Fortsville",
            29: "Conference at Monrovia",
            30: "Old Calabar, and the Women of Africa",
            31: "How I Came to Take Little Bob",
            32: "Among the People of Creektown",
            33: "Liberia: Its People and Schools",
            34: "Cape Palmas, and a Great Revival",
            35: "Emigration and the Schools of Liberia",
            36: "Letters and Testimonials",
            37: "An Address from the A. M. E. Zion Church, Sierra Leone",
            40: "Return to Liverpool, and Faith Healing",
            41: "Work in England, and Home Again",
        },
    },
    "true-vine": {
        # Murray gives two meditations the identical title "The Vine" (day 2 on
        # John 15:1, day 11 on John 15:5) — a duplicate title in the TOC.
        # Disambiguate by the verse each expounds.
        "chapter_titles": {
            2: "The Vine (John 15:1)",
            11: "The Vine (John 15:5)",
        },
    },
    "selected-sermons-edwards": {
        # Seven sermons (ch1 is the editor's Introduction, ch9 the editor's
        # Notes). The body headings became the titles carrying a roman prefix
        # (redundant with the reader number) and a trailing "°" footnote marker;
        # these give each sermon its clean, recognizable title (Gardiner's
        # Contents forms, but the famous name for the Divine-and-Supernatural-
        # Light sermon, whose formal heading ran to 130 characters).
        "chapter_titles": {
            2: 'God Glorified in Man’s Dependence',
            3: 'A Divine and Supernatural Light',
            4: 'Ruth’s Resolution',
            5: 'The Many Mansions',
            6: 'Sinners in the Hands of an Angry God',
            7: 'A Strong Rod Broken and Withered',
            8: 'A Farewell Sermon',
        },
    },
    "holy-in-christ": {
        # A thirty-one-day devotional. The 31 daily chapters imported all
        # titled "Holy in Christ" (the repeated running header); this edition
        # keeps the day THEMES only in the Contents. Titles from there (order
        # 2-32 = Day 1-31); ch1 Preface and ch33 Notes keep their own titles.
        "chapter_titles": {
            2: 'God’s Call to Holiness',
            3: 'God’s Provision for Holiness',
            4: 'Holiness and Creation',
            5: 'Holiness and Revelation',
            6: 'Holiness and Redemption',
            7: 'Holiness and Glory',
            8: 'Holiness and Obedience',
            9: 'Holiness and Indwelling',
            10: 'Holiness and Meditation',
            11: 'Holiness and Separation',
            12: 'The Holy One of Israel',
            13: 'The Thrice Holy One',
            14: 'Holiness and Humility',
            15: 'The Holy One of God',
            16: 'The Holy Spirit',
            17: 'Holiness and Truth',
            18: 'Holiness and Crucifixion',
            19: 'Holiness and Faith',
            20: 'Holiness and Resurrection',
            21: 'Holiness and Liberty',
            22: 'Holiness and Happiness',
            23: 'In Christ our Sanctification',
            24: 'Holiness and the Body',
            25: 'Holiness and Cleansing',
            26: 'Holiness and Blamelessness',
            27: 'Holiness and the Will of God',
            28: 'Holiness and Service',
            29: 'The Way into the Holiest',
            30: 'Holiness and Chastisement',
            31: 'The Unction from the Holy One',
            32: 'Holiness and Heaven',
        },
    },
    "first-epistle-of-clement": {
        # summary_titles reduces each ANF "argument" to its lead clause; four
        # long single-clause arguments have no early break, so the cap fell on a
        # word boundary and left the title ending mid-phrase ("…in it from",
        # "…the priestly", "…in the", "…peace has"). Concise, faithful titles.
        "chapter_titles": {
            3: 'The sad state of the church after sedition arose from envy',
            43: 'Moses stilled the contention concerning the priestly dignity',
            47: 'Your recent discord is worse than that in the times of Paul',
            59: 'The Corinthians exhorted to send back word that peace is restored',
        },
    },
    "ministry-of-intercession": {
        # This edition prints chapter titles only in the Contents (chapter
        # bodies open with a bare "CHAPTER N" then the scripture epigraph), so
        # the 15 numbered chapters imported untitled — titles from the Contents.
        # ch1 is the Havergal frontispiece poem; labelled Dedication.
        "chapter_titles": {
            1: 'Dedication',
            3: 'The Lack of Prayer',
            4: 'The Ministration of the Spirit and Prayer',
            5: 'A Model of Intercession',
            6: 'Because of His Importunity',
            7: 'The Life That Can Pray',
            8: 'Restraining Prayer—Is It Sin?',
            9: 'Who Shall Deliver?',
            10: 'Wilt Thou Be Made Whole?',
            11: 'The Secret of Effectual Prayer',
            12: 'The Spirit of Supplication',
            13: 'In the Name of Christ',
            14: 'My God Will Hear Me',
            15: 'Paul a Pattern of Prayer',
            16: 'God Seeks Intercessors',
            17: 'The Coming Revival',
        },
    },
    "essentials-of-prayer": {
        # Same roman-prefix redundancy as its companion volume (the reader prints
        # the chapter number), plus a spaced "( Continued )". Titles from the
        # Contents, roman prefix dropped.
        "chapter_titles": {
            1: "Prayer Takes in the Whole Man",
            2: "Prayer and Humility",
            3: "Prayer and Devotion",
            4: "Prayer, Praise and Thanksgiving",
            5: "Prayer and Trouble",
            6: "Prayer and Trouble (Continued)",
            7: "Prayer and God’s Work",
            8: "Prayer and Consecration",
            9: "Prayer and a Definite Religious Standard",
            10: "Prayer Born of Compassion",
            11: "Concerted Prayer",
            12: "The Universality of Prayer",
            13: "Prayer and Missions",
        },
    },
    "reality-of-prayer": {
        # The chapter headings carry a roman-numeral prefix (I … XVI) that only
        # duplicates the number the reader already prints, and the ALL-CAPS→Title
        # pass left a lowercase "the" and a spaced "( Continued )". clean_title
        # deliberately leaves roman prefixes on mixed-case titles (they are
        # referential in Edwards), so these are set per-book from the Contents.
        "chapter_titles": {
            1: "Prayer—A Privilege, Princely, Sacred",
            2: "Prayer—Fills Man’s Poverty with God’s Riches",
            3: "Prayer—The All-Important Essence of Earthly Worship",
            4: "God Has Everything to Do with Prayer",
            5: "Jesus Christ, the Divine Teacher of Prayer",
            6: "Jesus Christ, the Divine Teacher of Prayer (Continued)",
            7: "Jesus Christ an Example of Prayer",
            8: "Prayer Incidents in the Life of Our Lord",
            9: "Prayer Incidents in the Life of Our Lord (Continued)",
            10: "Our Lord’s Model Prayer",
            11: "Our Lord’s Sacerdotal Prayer",
            12: "The Gethsemane Prayer",
            13: "The Holy Spirit and Prayer",
            14: "The Holy Spirit Our Helper in Prayer",
            15: "The Two Comforters and Two Advocates",
            16: "Prayer and the Holy Ghost Dispensation",
        },
    },
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
    "how-to-bring-men-to-christ": {
        # Ch.7's heading alone is set in lower case ("Dealing with those who Lack
        # Assurance…") where every sibling is Title Case, and the print's
        # line-break hyphen in "Back-sliders" is transcribed as an en-dash inside
        # the word. Give the clean, consistent title.
        "chapter_titles": {7: "Dealing with Those Who Lack Assurance and with Backsliders"},
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
#   restored_blocks: [(anchor, block)] — the sanitizer DELETED a whole block
#     (see `restore_dropped_blocks`), and it goes back in front of the block
#     that followed it, identified by that block's opening. Not a
#     `replacements` pair either, and for a different reason than the seams
#     above: `restore_dropped_blocks` says why. Spell the block with the tag the
#     SOURCE used, so the guard recognises a body that already has it.
#
# Applied on every import AND backfillable over stored rows (management command
# `apply_body_corrections`, plus a data migration for prod).

BODY_CORRECTIONS: dict[str, dict] = {
    "way-into-holiest": {
        "replacements": [
            # Ch.1 (Preface): a modern digitiser's note was appended after Meyer's
            # own "F.B. MEYER." sign-off — it speaks of making the text "readable
            # to the computer audience" and gives an e-mail address. Not Meyer's
            # words; excise it and keep his sign-off. (Once `cars?` was dropped
            # from english_audit.py this was the corpus's only real anachronism.)
            (
                '<p>F.B. MEYER.</p> <p>Editors note.</p> <p>I have endeavored to '
                'remain true to the original manuscript as was delivered to me. I '
                'did, however, make some punctuation correction so as to make it '
                'more readable to the computer audience. Namely, I replaced a few '
                'hyphens where I saw them confusing the text. I also corrected a '
                'couple of obvious errors found in the original printing. If these '
                'changes cause any confusion I, alone, take full responsibility; '
                'please e-mail me at rlarryh@teleport.com and I will make any '
                'corrections necessary. </p> <p>Larry Hendrickson</p>',
                '<p>F.B. MEYER.</p>',
            ),
            # Ch.1: two spaces lost in extraction, inside Meyer's actual preface.
            ("or designationof church", "or designation of church"),
            ("the Authorshipof the", "the Authorship of the"),
            # Ch.20: Hosea 1:9's name lost its hyphen (glossed "Not my people").
            # Unique token, so keep the surrounding straight quotes out of the
            # pair (a literal `"` would trip the dead-pair gate).
            ("LoAmmi", "Lo-ammi"),
            # Ch.24: OCR b->h in the hymn "Once for all" ("brother, believe it!").
            ("all, hrother, believe it!", "all, brother, believe it!"),
            # Ch.26: the compound "fellow-Christians" kept a spurious space after
            # its hyphen. The line-break rejoin leaves a capitalised resumption
            # alone; here a human can see it is a real compound, not a dash.
            ("fellow- Christians", "fellow-Christians"),
        ],
    },
    # Seven classic sermons were translated into Spanish (#1462-#1468); reading
    # every sentence surfaced OCR/extraction slips in the ENGLISH source that no
    # detector class catches (each produces a valid-looking short word). Only
    # letter-level extraction damage with a single possible reading is repaired
    # here; grammar/style and damaged passages that need the source edition are
    # reported, not touched.
    "the-good-way-of-coming-before-the-lord": {
        "replacements": [
            # Zech 3:4 quotation: "clothe the" -> "clothe thee".
            ("clothe the with change of raiment", "clothe thee with change of raiment"),
            # "no far" -> "no fear".
            ("There is no far but the", "There is no fear but the"),
            # Matt 20:26 echo: "It shall no be" -> "It shall not be".
            ("It shall no be so among you", "It shall not be so among you"),
            # "amide" -> "amid".
            ("amide the billows", "amid the billows"),
        ],
    },
    "the-method-of-grace": {
        "replacements": [
            ("we cannot pt up a prayer", "we cannot put up a prayer"),
            ("you had o righteousness of your own", "you had no righteousness of your own"),
            ("have got o peace with God", "have got no peace with God"),
            ("How did Chris speak", "How did Christ speak"),
            ("you must keep u a tender", "you must keep up a tender"),
            # Ps 119:165: "love they law" -> "love thy law".
            ("that love they law", "that love thy law"),
            ("a matte of great importance", "a matter of great importance"),
            ("pray sometimes none times a-day", "pray sometimes nine times a-day"),
            # 2 Cor 7:5: "without were fightings" — "sightings" -> "fightings".
            ("what sightings may be without", "what fightings may be without"),
            # More OCR slips found while translating the sermon to Portuguese
            # (batch 1). Each is a one- or two-letter mechanical error that
            # breaks the grammar; the correct reading is forced by the sentence
            # and confirmed against the canonical text (biblebb.com/gw058, the
            # Glasgow 1741 sermon).
            ("unbelief of you heart", "unbelief of your heart"),
            ("otherwise believer in Christ", "otherwise believe in Christ"),
            # "could not bear the sight of Christ ... how will they [bear] the
            # sight of him" — a sight cannot be heard.
            ("they hear the sight of him", "they bear the sight of him"),
            # Comparison "such a man as Caesar"; the printed tradition (biblebb
            # included) carries the "a Caesar" slip, but the grammar is decisive.
            ("such a man a Caesar", "such a man as Caesar"),
            # NOT corrected, on purpose (documented so a later pass doesn't
            # "fix" them): "I am not talking of a matter of great importance",
            # "say the psalmist", and "say of his disciples" all stand in the
            # canonical text — the received wording, not extraction damage. The
            # Portuguese edition renders them faithfully.
        ],
    },
    "sinners-in-the-hands-of-an-angry-god": {
        # OCR slip found while translating the sermon to Portuguese (batch 1):
        # "generality" (a noun) cannot fill the adverbial slot before "persons
        # ... are passed over"; the canonical Edwards text reads "generally".
        "replacements": [
            ("how generality persons", "how generally persons"),
        ],
    },
    "compel-them-to-come-in": {
        # Typography slip found while translating the sermon to Portuguese
        # (batch 1): the quotation that opens the Hezekiah citation (Isa 38:1,
        # "Set thine house in order...") begins with a CLOSING curly quote. The
        # paragraph's marks don't balance otherwise (14 “ vs 16 ”), and every
        # other quotation in the sermon opens correctly.
        "replacements": [
            ("invitation is, ”", "invitation is, “"),
        ],
    },
    "pauls-praise-of-christian-love": {
        "replacements": [
            # Doubled period on a section number; markup-anchored so it is a
            # no-op on the tagless body_text.
            ("<p>2.. We see", "<p>2. We see"),
            ("service of others.To these", "service of others. To these"),
            # "it to be able" -> "is to be able", anchored on the words after the
            # source's straight quote (a quote char reads JSON-escaped in the
            # dead-pair check's corpus, so keep it out of the pair).
            ("it to be able to apprehend", "is to be able to apprehend"),
            ("6. Note bow forcibly", "6. Note how forcibly"),
            ("written concern ing the things", "written concerning the things"),
            # "old fence" -> "old offence" (the sentence is about an injury).
            ("hunt up an old fence to find the injury", "hunt up an old offence to find the injury"),
            # "abides fore" -> "abides forever" (truncation).
            ("which abides fore, all else", "which abides forever, all else"),
        ],
    },
    "fall-and-recovery-of-man": {
        "replacements": [
            # "wrath and rain" -> "wrath and ruin" (cf. "wrath and ruin" earlier).
            ("wrath and rain. Justice", "wrath and ruin. Justice"),
            # Eph 2:9: "least any man should boast" -> "lest".
            ("not of works, least any man should boast", "not of works, lest any man should boast"),
            # Wesley's hymn: "Pascal Lamb" -> "Paschal Lamb".
            ("“Pascal Lamb by God appointed", "“Paschal Lamb by God appointed"),
            # Rom 5:15 re-quote opens with a stray, never-closed single quote.
            ("“‘For if, through the offence", "“For if, through the offence"),
        ],
    },
    "life-experience-gospel-labours": {
        # A stray space before the period after a middle initial in the AME
        # supplement's petition ("Joseph B . McKean"). Faithful-looking but a
        # transcription slip; the rest of the audit's space-before-punct flags
        # sit inside the source's dash-redacted names ("Rev L-- G-- .") and are
        # left as the source has them.
        #
        # The second pair BACKFILLS a live row: this book was imported (#1319)
        # before the docsouth footer-nav fix (#1330), so prod's last chapter
        # still carries the "Return to Menu Page…" nav that #1330 removed from
        # the fixture. seed_books never rewrites an existing chapter, so the
        # deploy left it stale; apply_body_corrections does (through save()).
        # A no-op on the fixed fixture, which no longer contains the nav.
        "replacements": [
            ("Joseph B . McKean", "Joseph B. McKean"),
            (
                " <p>Return to Menu Page for The Life, Experience, and Gospel "
                "Labours of the Rt. Rev. Richard Allen... by Richard Allen</p> "
                "<p>Return to The Church in the Southern Black Community Home "
                "Page</p><p>Return to North American Slave Narratives Home "
                "Page</p> <p>Return to Documenting the American South Home "
                "Page</p>",
                "",
            ),
        ],
    },
    "amanda-smith-autobiography": {
        # A stray space before a comma ("our dinner , and"), a transcription slip.
        "replacements": [
            ("our dinner , and", "our dinner, and"),
        ],
    },
    "absolute-surrender": {
        # The CCEL text is uniformly curly; one opening double quote slipped
        # through the importer's straight->curly pass. Curl it (QuoteStyleTests).
        #
        # ch03 opens with an <h2> restating its own title ("SEPARATED UNTO THE
        # HOLY GHOST" against the title "Separated unto the Holy Spirit"), so the
        # reader prints the title twice. `strip_restated_headings` misses it \u2014
        # its title rule sees "Ghost" != "Spirit" \u2014 but it is the same
        # restatement (all-of-grace precedent), and Spanish collapses both to
        # "Esp\u00edritu Santo", so the es edition's <h2> is an exact restatement the
        # fixture gate rejects. Drop the heading in every edition; markup-anchored
        # so it is a no-op on body_text.
        "replacements": [
            ('unto him, "Thus saith', 'unto him, \u201cThus saith'),
            ("<h2>SEPARATED UNTO THE HOLY GHOST</h2> ", ""),
            # Same restated ch03 heading in the Portuguese edition (Portuguese
            # also collapses Ghost/Spirit to "Espírito Santo", so its <h2>
            # exactly restates the pt title); dropped to match the trimmed en
            # so the editions stay markup-coherent.
            ("<h2>POSTOS À PARTE PARA O ESPÍRITO SANTO</h2> ", ""),
        ],
    },
    "ministry-of-intercession": {
        # A Gutenberg <h3>Transcriber's Notes</h3> block (formatting notes, not
        # Murray) trailed the final Notes chapter; the two space-before-punct
        # findings were its stripped page refs. Remove the whole block.
        #
        # The twelve pairs after it repair the other half of that same import.
        # Gutenberg spells each cross-reference to the endnotes as a link —
        # `(<a href="#nt.A">Note A.</a>)` — and the extractor kept the
        # parentheses and dropped the anchor's text, leaving a reader five bare
        # `()` and, in ch13, a lone `)` (Gutenberg's own transcription drops
        # that one's opening paren; the 1898 Nisbet printing has it). All six
        # read `(Note A.)` … `(Note F.)` in the print, in chapter order, and
        # the notes they point at are all still here as ch18. Found by the
        # Hindi translator of chapters 11-13, who mirrored them faithfully —
        # which is correct of a translator, and is what makes them fixable.
        #
        # The hi pairs are the same repair in that edition's OWN vocabulary:
        # its ch18 is titled टिप्पणियाँ, so a single note is टिप्पणी. The note
        # LETTER stays Latin — it keys an endnote list that has nothing else to
        # key on. Nothing is invented but that one word.
        #
        # NOT `source_fixes`: the parentheses are what the extractor made of a
        # link, not what Murray printed. The hi fixture was settled by hand in
        # the same commit — see the translation-fixture failure mode in the
        # `english-qa` skill for why nothing in the repo does that for you.
        "replacements": [
            ('<h3>Transcriber’s Notes</h3><p>Minor errors and inconsistencies in punctuation and hyphenation have been silently corrected.</p> <p>On page , the heading “What the Health that Jesus Offers.” is as in the original text.</p> <p>As explained in the section on , on each daily page in the tract “Pray Without Ceasing”, several lines are ruled to leave room for “SPECIAL PETITIONS”. These are hidden on screen in this version, but can be displayed by following the instructions in the file header. The ruled lines will be displayed if the text is printed.</p>', ""),
            ("May God discover this to us. ()", "May God discover this to us. (Note A.)"),
            ("makes us reign in life. ()", "makes us reign in life. (Note B.)"),
            ("He will delight to give.” ()", "He will delight to give.” (Note C.)"),
            ("known by us in their power. ()", "known by us in their power. (Note D.)"),
            ("of His spirit to the Father. )", "of His spirit to the Father. (Note E.)"),
            ("Gods seeks intercessors. ()", "Gods seeks intercessors. (Note F.)"),
            ("प्रकट करे। ()", "प्रकट करे। (टिप्पणी A.)"),
            ("बढ़नेवाला। ()", "बढ़नेवाला। (टिप्पणी B.)"),
            ("प्रसन्न होगा।” ()", "प्रसन्न होगा।” (टिप्पणी C.)"),
            ("जानी जा सकती है। ()", "जानी जा सकती है। (टिप्पणी D.)"),
            ("सौंप देने की प्रार्थना। )", "सौंप देने की प्रार्थना। (टिप्पणी E.)"),
            ("ढूँढ़ता है। ()", "ढूँढ़ता है। (टिप्पणी F.)"),
            # ch13 opens "In my name—repeated six times over." where the other
            # twelve sites in the chapter, and the epigraph two lines above,
            # read "In My Name". The 1898 printing sets the chapter opening in
            # display capitals ("IN MY NAME — repeated six times over"), which
            # carries no lowercase evidence either way; Gutenberg's transcriber
            # down-cased it. Anchored on the `<p>` so it cannot touch body_text.
            ("<p>In my name—repeated six times over.",
             "<p>In My Name—repeated six times over."),
        ],
        # The other half of the `pginternal` damage: ch18's six note HEADINGS
        # (`restore_dropped_blocks` has the mechanism, and why this is not a
        # `replacements` pair). Restored verbatim from the 1898 printing, print
        # page numbers included: what was lost is the whole heading, and
        # trimming it would be an edit rather than a repair. `<h4>` because that
        # is the tag the source used AND this book's own for a mid-chapter
        # heading — its `<h3>` is the repeated "A PLEA FOR MORE PRAYER" banner.
        #
        # BOTH editions, at the same six paragraphs. They run in lockstep, and
        # `tests_translation_markup` pins a translation's ordered tag sequence
        # against its English, so six headings in one edition alone would fail
        # it. The hi wording is that edition's own: it already writes "अध्याय 7
        # की टिप्पणी" for the print's "the note to chap. vii.", so both nouns
        # and the arabic numerals come from its usage.
        "restored_blocks": [
            ("<p>Just this day I have been ", "<h4>NOTE A, Chap. VI. p. 73</h4>"),
            ("<p>आज ही मैं भारत से आई हुई ए", "<h4>टिप्पणी A, अध्याय 6. पृ. 73</h4>"),
            ("<p>Let me tell here a story t", "<h4>NOTE B, Chap. VII. p. 89</h4>"),
            ("<p>मैं यहाँ एक कहानी सुनाता ह", "<h4>टिप्पणी B, अध्याय 7. पृ. 89</h4>"),
            ("<p>Just yesterday again—three", "<h4>NOTE C, Chap. IX. p. 111</h4>"),
            ("<p>कल ही फिर—अध्याय 7 की टिप्", "<h4>टिप्पणी C, अध्याय 9. पृ. 111</h4>"),
            ("<p>Let me once again refer my", "<h4>NOTE D, Chap. X. p. 123</h4>"),
            ("<p>मैं अपने पाठकों को एक बार ", "<h4>टिप्पणी D, अध्याय 10. पृ. 123</h4>"),
            ("<p>There is a question, the d", "<h4>NOTE E, Chap. XI. p. 136</h4>"),
            ("<p>एक प्रश्न है, सबसे गहरा, ज", "<h4>टिप्पणी E, अध्याय 11. पृ. 136</h4>"),
            ("<p>I have more than once spok", "<h4>NOTE F, Chap. XIV. p. 177</h4>"),
            ("<p>मैं एक से अधिक बार मसीहियो", "<h4>टिप्पणी F, अध्याय 14. पृ. 177</h4>"),
        ],
    },
    "holy-in-christ": {
        # The same dropped-anchor defect as `ministry-of-intercession` above,
        # from the same transcriber (Project Gutenberg; this book is #26990)
        # and the same selector:
        # `sanitize.DROP_SELECTORS` carries `"[class*=pginternal]"`, and `_clean`
        # DECOMPOSES the drop-selectors before it unwraps everything else — so a
        # plain `<a>` survived as its text and a *Gutenberg* one was deleted
        # whole. Gutenberg puts that class on every internal link, so what a
        # reader got is the punctuation around a reference with the reference
        # gone. The selector is QUALIFIED now — `sanitize.KEEP_PREDICATES` keeps
        # a link whose text is a word — so no future import loses one; these
        # pairs stay because shipped rows are never re-imported (see
        # `restore_dropped_blocks` for why).
        #
        # ch10's closing recapitulation lost six book-internal cross-references
        # at once and shipped six bare `()`:
        #
        #   deep Restfulness (<a href="#day_3" class="pginternal">ch. 3</a>),
        #
        # Each target was read off the Gutenberg HTML rather than inferred from
        # position, and each `#day_N` anchor was followed to the heading it
        # names: day_3 "Third Day"/Holiness and Creation ... day_8 "Eighth
        # Day"/Holiness and Indwelling, which is also what the sentence's own
        # terms say (Restfulness ↔ Creation, the Divine Indwelling ↔ Indwelling).
        #
        # The references are Murray's publisher's, not Gutenberg's: the Revell
        # printing that #26990 was keyed from (archive.org
        # `holyinchristthou00murruoft`, p. 88) prints "(ch. 3)" … "(ch. 8)" in
        # exactly this order. Worth checking, because two other scans of the
        # same work carry the sentence with NO references at all
        # (`holyinchristthou00murr`, 1887; `holyinchristtho00murrgoog`, 1888)
        # — so "restore what Gutenberg had" and "restore what the author
        # printed" are genuinely two questions here, and it is only this
        # printing that makes them one answer.
        #
        # The seventh pair is the same selector in ch12: Gutenberg's
        # `(see ‘<a class="pginternal">Sixth Day</a>’)` left `(see ‘’)`, which
        # both printings above spell "(see 'Sixth Day')".
        #
        # NOT `source_fixes`: the parentheses are what the extractor made of a
        # link, not what Murray printed. English-only edition, so nothing to
        # settle by hand in a translation.
        #
        # ch33 (Notes) lost all seven of its `NOTE A.`–`NOTE G.` headings to a
        # DIFFERENT selector: `[class*=note i]`, written for CCEL's footnote
        # apparatus, also matched Gutenberg's own `class="note"`. That selector
        # is FIXED at the source now (`sanitize._is_gutenberg_note_content`), so
        # no future import loses them — but these rows are never re-imported, so
        # ch33 on the shelf is still seven bare `<hr/>`s with no headings.
        #
        # Repairing THOSE is `restored_blocks` on this same key, the mechanism
        # `ministry-of-intercession` uses for byte-identical damage from the
        # sibling selector — not more `replacements` pairs, because a pure
        # insertion re-fires on every deploy (see `restore_dropped_blocks`).
        # Deliberately left for that change: it has to settle the ordered-tag
        # parity `tests_translation_markup` enforces against this book's
        # translations, which is not this key's business.
        #
        # The footnote BLOCKS that pointed at them stay dropped, by design: the
        # markers referencing them are dropped too, so restoring the blocks
        # alone would orphan the note text mid-chapter.
        "replacements": [
            ("deep Restfulness ()", "deep Restfulness (ch. 3)"),
            ("humble Reverence ()", "humble Reverence (ch. 4)"),
            ("entire Surrender ()", "entire Surrender (ch. 5)"),
            ("joyful Adoration ()", "joyful Adoration (ch. 6)"),
            ("simple Obedience ()", "simple Obedience (ch. 7)"),
            ("the Divine Indwelling ()", "the Divine Indwelling (ch. 8)"),
            ("His Glory and Majesty (see ‘’)", "His Glory and Majesty (see ‘Sixth Day’)"),
        ],
    },
    "selected-sermons-edwards": {
        # Four sermons shipped with NO TEXT. Edwards sets each sermon's
        # scripture as its opening line, and this edition marks it
        # `<p class="note">` — which `sanitize.DROP_SELECTORS`'s
        # `"[class*=note i]"`, written for CCEL's footnote apparatus, matched
        # and decomposed whole. So ch2, ch3, ch4 and ch8 open mid-argument
        # ("Those Christians to whom the apostle directed this epistle…") with
        # nothing saying which apostle or which epistle. The selector is
        # QUALIFIED now (`sanitize.KEEP_PREDICATES`), so no future import loses
        # one; these are the rows already on the shelf, which are never
        # re-imported.
        #
        # The book is its own witness that a text belongs there: ch5, ch6 and
        # ch7 still carry theirs ("John xiv. 2.—In my Father's house are many
        # mansions."), because this edition marks THOSE `<p class="center">` —
        # which is not a drop selector, so they were never touched. That is the
        # only difference between the four that lost their text and the three
        # that kept it. Nothing is invented: each of the four is the source's
        # own paragraph, restored verbatim, and each is the text the sermon
        # then expounds.
        #
        # The anchor is the `<p><br/>` that opens each damaged chapter: the
        # spacer left behind where the text used to be, which is why these
        # chapters begin with a blank line. Restored as its own `<p>` and left
        # in front of that spacer, which reproduces ch5-7 exactly — there too
        # the text is its own paragraph followed by `<p><br/>`.
        #
        # English-only edition, so there is no translation to keep in lockstep.
        #
        # `quote_seed` anchors a quote by its 0-indexed BLOCK position, so
        # inserting a paragraph shifts every quote below it: eight Edwards
        # anchors in these four chapters moved by one, in the same commit.
        # `tests_quotes` is what catches that, and it is the reason a body
        # repair is never only a body repair.
        "restored_blocks": [
            (
                "<p><br/>Those Christians to whom the apostle",
                "<p>1 Cor. i. 29-31.—That no flesh should glory in his presence. "
                "But of him are ye in Christ Jesus, who of God is made unto us "
                "wisdom, and righteousness, and sanctification, and redemption: "
                "that according as it is written, He that glorieth, let him glory "
                "in the Lord.</p>",
            ),
            (
                "<p><br/>Christ says these words to Peter",
                "<p>Matt. xvi.—And Jesus answered and said unto him, Blessed art "
                "thou, Simon Barjona: for flesh and blood hath not revealed it "
                "unto thee, but my Father which is in heaven.</p>",
            ),
            (
                "<p><br/>The historical things in this book of Ruth",
                "<p>Ruth i. 16.—And Ruth said, Intreat me not to leave thee, or to "
                "return from following after thee: for whither thou goest, I will "
                "go; and where thou lodgest, I will lodge: thy people shall be my "
                "people, and thy God my God.</p>",
            ),
            (
                "<p><br/>The apostle, in the preceding part of the chapter",
                "<p>2 Cor. i. 14.—As also you have acknowledged us in part, that "
                "we are your rejoicing, even as ye also are ours in the day of the "
                "Lord Jesus.</p>",
            ),
        ],
    },
    "essentials-of-prayer": {
        # A quoted hymn line broke across a line and rejoined with a space
        # before the comma ("He has said He will , If we but trust"). Restore
        # the comma spacing.
        "replacements": [
            ("He has said He will ,<br/>", "He has said He will,<br/>"),
        ],
    },
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
    "selected-sermons-whitefield": {
        # ch41 ("Saul's Conversion") prints "(that I may draw towards a
        # conclusion()" — a doubled paren where the parenthesis should simply
        # close. The defect is CCEL's, and CCEL is this book's lineage: its own
        # page carries the identical "conclusion()", while Blue Letter Bible's
        # independent transcription reads "conclusion)". English-only; the book
        # has no translations to sweep.
        #
        # Three more CCEL slips in the SAME ch41 block, each settled against the
        # printed edition this text descends from — *Sermons on Important
        # Subjects* (London: Fisher, Son & Jackson, 1830), Sermon XLI, p. 480;
        # archive.org `sermonsonimport00whitgoog`. CCEL's page carries all three,
        # so none of them is ours:
        #
        #   Lord' seat   a dropped possessive s. The print reads "Though the
        #                Lord's seat is in heaven, yet he has respect to his
        #                saints"; "the Lord' seat" is not a reading, it is a
        #                lost character.
        #   rags         "so the rags of men and devils will increase also" —
        #                the print reads "so, the rage of men and devils will
        #                increase also", which is the sentence's own argument:
        #                it follows "the enmity which is in the hearts of
        #                natural men against Christ, will not suffer them to be
        #                quiet long".
        #   open quote   Whitefield quotes himself and the OPENING mark was
        #                lost, leaving a bare close. The print sets the
        #                quotation open after "if I may speak my own
        #                experience," and closes it at "for the sake of Jesus
        #                Christ." Restoring the opener balances the close that
        #                is already stored; nothing else in the block moves,
        #                and the insertion is mid-string, so `old` cannot recur
        #                and the pair is idempotent.
        #
        #                NOTE this is invisible to `orphan-close-quote`, and
        #                the class count for this book is unchanged by it (17
        #                before and after). `_orphan_quotes` carries a running
        #                depth across a chapter's blocks, deliberately, because
        #                a long quotation opens every paragraph and closes only
        #                the last; an earlier unclosed quotation in ch41 was
        #                holding depth above zero, so this block's extra close
        #                never read as orphaned. The repair rests on the print,
        #                not on a finding — do not expect the baseline to move.
        "replacements": [
            ("a conclusion()", "a conclusion)"),
            ("Though the Lord' seat", "Though the Lord's seat"),
            ("so the rags of men and devils", "so the rage of men and devils"),
            ("my own experience, I never enjoy",
             "my own experience, \u201cI never enjoy"),
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
            #   ()h        ch9  "and ()h may divine grace make it so with us!"
            #               — the capital O of "Oh" lost to a paren pair. Blue
            #               Letter Bible and the Spurgeon Library both read
            #               "and Oh may divine grace"; the modernised Answers
            #               in Genesis reprint lowercases it, and the two MTP
            #               transcriptions win. Unrelated to the `pginternal`
            #               anchor drop — this book is not from Gutenberg.
            ("and ()h may divine grace", "and Oh may divine grace"),
            #   hut.       ch9  "the will of his poor hut. favoured
            #               creature-man" — an h/b misread plus a spurious full
            #               stop, the same CCEL-lineage `hut`/`but` slip the
            #               `english-qa` skill records elsewhere. "hut" is a
            #               non-word here and the sentence needs the concessive.
            #               The Spurgeon Library carries the identical "poor
            #               hut.", so it is not an independent witness; two
            #               outside that lineage agree on the reading —
            #               spurgeongems.org's retype of the printed New Park
            #               Street Pulpit (No. 328) and Blue Letter Bible both
            #               have "his poor but favo(u)red creature-man". Only
            #               the two damaged characters are touched; the British
            #               "favoured" this text prints is left alone.
            ("his poor hut. favoured", "his poor but favoured"),
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
    "rest": {
        # Two OCR slips in Moody's "Rest" (Gutenberg #33015), each found
        # independently by the Swahili AND Luganda translators, and each with a
        # single possible reading that the already-shipped es/pt editions had
        # also resolved the same way (es "altar familiar" / "hallar descanso",
        # pt "altar de família"). English-only defects, so BODY_CORRECTIONS
        # rather than source_fixes; the strings carry enough context to be
        # unique.
        "replacements": [
            ("gamily altar", "family altar"),
            ("You can end rest on the bosom", "You can find rest on the bosom"),
        ],
    },
    "free-grace": {
        # Two OCR slips found while translating the sermon to Hindi (job #1109).
        # Both INVERT the sense, which is why they are repaired here rather than
        # only reported: a faithful rendering makes Spurgeon say the opposite of
        # what he wrote, and the Hindi edition would have shipped it.
        #
        # Both are settled by the editions we already ship, which is the test
        # this file uses for repairing a source rather than guessing at it:
        # "immortality" is how es and pt both render it (inmortalidad /
        # imortalidade), and "trust" is unanimous across ar, es and pt
        # (الثقة / confiar / confiar). Nothing had to be inferred.
        "replacements": [
            ("heirs of light and immorality", "heirs of light and immortality"),
            ("a proneness to truth in some fancied merit",
             "a proneness to trust in some fancied merit"),
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
        # ch01-04 are A. B. Simpson's numbered scriptural arguments (a scripture
        # list, practical directions, objections, principles), set with a hanging
        # indent + gap-separated sub-paragraphs that the PDF import welded into 2-4
        # blocks of 1,000-2,300 words (the corpus's worst lost-paragraphing). Breaks
        # restored from the source CMA PDF's own line coordinates: numbered items
        # out-dent to x0=108, prose sits at x0=90, continuation at 126, and further
        # paragraph breaks show as a blank-line vertical gap. Existing block boundaries
        # are left as-is (additive only). The deeper line-level importer fix is deferred
        # to its own PR; see the english-qa skill.
        "replacements": [
            # Pre-existing: digit-zero for the letter O in the Psalm 103 quotation.
            ("Bless the Lord, 0 my soul", "Bless the Lord, O my soul"),
        ],
        "paragraph_breaks": [
            # chapter 1
            ('any of the ordinances of the Gospel.', '2. Psa. cv. 37.'),
            ('too shall see the promise fulfilled.', '3. Job i. and ii. The story of'),
            ('and humility-he is healed.', '4. Ps. ciii. 2, 3.'),
            ('sin; and both must be healed together.', '5. II. Chron. xvi. 12, 13.'),
            ('And Asa slept with his fathers.&quot;', '6. Isaiah liii. 4, 5.'),
            ('with His stripes we are healed.&quot;', 'This the great Evangelical'),
            ('Blessed and glorious Burden Bearer.', 'Thus the ancient prophet beholds'),
            ('of shame and agony, the Dying Lamb.', '7. Matthew viii. 17.'),
            ('whole.&quot; He is still the same.', 'Now, this was the work of His'),
            ('as much as on the Lamb of Calvary.', 'It would take entirely too long'),
            ('this blessed power to die with Him?', '8. John xiv. 12.'),
            ('in the most unmistakable terms.', '9. Mark xvi. 15-18.'),
            ('saints? We turn with deep interest to', '10. James v. 14.'),
            ('they shall be forgiven him.&quot;', 'Now, let us notice first who'),
            ('the oversight of the flock of Christ.', 'Again, observe to whom this'),
            ('to continue till the end of the age.', 'Again, notice the time at which'),
            ('the ends of the world are come.&quot;', 'Again, observe the nature of the'),
            ('breathing into it His vital energy.', 'Again, observe that this is a'),
            ('childlike confidence; He will fulfill.', 'And once more, we must not'),
            ('may be claimed together in His name.', '11. III. John 2.'),
            ('will be even as our soul prospereth.', '12. Eph. v. 30.'),
            ('is ours, and it is all sufficient.', '13. Rom. viii. 11.'),
            ('us we shall experience the same works.', '14. II Cor. iv. 10, 11.'),
            ('all his gifts, is renewed day by day.', '15. Finally, as a voice that has'),
            # chapter 2
            ('of THE WORD OF GOD in this matter.', 'This is the only sure foundation'),
            ('and rested in the Word of God.', '2. Be fully assured of the WILL'),
            ('of the WILL OF GOD TO HEAL YOU.', 'Most persons are ready enough to'),
            ('despot, and an inexorable destiny.', '3. Be careful that you are'),
            ('that you are yourself RIGHT WITH GOD.', 'If your sickness has come to you'),
            ('and your body washed with pure water.', 'It is quite vain for us to try'),
            ('another, that ye may be healed.&quot;', 'Often our sickness is but a'),
            ('to the soul that seeketh Him.&quot;', 'The writer would illustrate this'),
            ('and has not been seriously ill since.', '4. Having become fully persuaded'),
            ('to His word that you have received it.', '5. ACT YOUR FAITH.'),
            ('it bringeth forth much fruit.&quot;', '6. BE PREPARED FOR TRIALS OF'),
            ('did, to the faith of the resurrection.', 'But, be the symptoms what they'),
            ('man is renewed day by day.&quot;', '7. USE YOUR NEW STRENGTH AND'),
            ('prosper even as our soul prospereth.', 'Nor is it enough for us to use'),
            ('shall keep it unto life eternal.&quot;', 'Thus let us claim, and keep and'),
            # chapter 3
            ('body, we have the same life and power.', 'What made the Apostles more'),
            ('he do because I go to My Father.&quot;', 'And, indeed, so long as the'),
            ('of time should be intensely alive.', '2. The same results as are'),
            ('as well as the spiritual world.', '3. The miracles of Christ and'),
            ('according to His own will.&quot;', 'There is also a current'),
            ('&quot;His heart is still the same:-', 'Kinsman, Friend and Elder'),
            ('to me, Living One of Bethany.&quot;', '4. A common objection is urged'),
            ('labors, both in India and Africa.', '5. Perhaps no objection is more'),
            ('strong heart, to bear and overcome.', '6. It is objected that it is'),
            ('we thus most effectually glorify God.', '7. We are told that there are'),
            ('personal sketches is most wonderful.', 'There are still cases of'),
            ('man&quot; be &quot;a liar.&quot;', '8. But we are told, if these'),
            ('corn that cometh in its season.&quot;', '9. We are asked by some, did not'),
            ('further, this much at least is clear:', 'First, that God has not'),
            ('that God has not prescribed medicine.', 'Secondly, He has prescribed'),
            ('actually commanded and enjoined it.', 'And thirdly, all the provisions'),
            ('too hard for the Lord.&quot;', '10. We will only refer in'),
            ('besides leading to other evils.', 'The same objection might be'),
            ('a living God and a returning Master.', 'Extravagances, perversions, and'),
            # chapter 4
            ('and not by mere natural treatment.', 'And again, on the supposition'),
            ('God and the Gospel of His Redemption.', '2. If the disease be the result'),
            ('upon, as secure as the Rock of Ages.', '4. But redemption finds its'),
            ('&quot;Far as the curse is found.&quot;', 'But, again, it is most'),
            ('through the blood of His Cross.', '5. But there is something higher'),
            ('Jesus manifested in our mortal flesh.', '6. It follows from this, that it'),
            ('through Christ that strengtheneth us.', '7. It follows from this that the'),
            ('the very Temple of the Holy Ghost.', '8. The great agent in bringing'),
            ('His Spirit that dwelleth in us.', '9. This new life must come, like'),
            ('OF MERIT OR RESPECT OF PERSONS.', 'Everything that comes through'),
            ('Let no other trust intrude.&quot;', 'If healing is to be sought by'),
            ('persons, and within the reach of all.', '10. The simple condition of this'),
            ('and all the blessings of the Gospel.', '11. Is there any principle'),
            ('simple and obedient child of God.', '12. The order of God'),
            ('regulated by certain fixed principles.', 'A. He works from within'),
            ('life, he can begin to heal the body.', 'B. There is a constant parallel'),
            ('of the Lord&#x27;s own life in us.', 'C. Hence, also, healing will'),
            ('great end in all His workings in us.', '13. The Limitations of Healing'),
            ('are also fixed by certain principles.', 'A. It is not the immortal life.'),
            ('and the natural life a hundredfold.', 'B. The next limitation has'),
        ],
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
        # Imported with pervasive extraction corruption: a stray space was
        # sprayed through almost every chapter, splitting words ("Je rusalem",
        # "spirit ual", "r ecipients") and stranding single letters ("t he
        # words", "God ’s", the whole "G od’s R iches A t C hrist’s E xpense"
        # acrostic). The first three pairs (ch7 drop cap + "repea t"/"wif e")
        # were an earlier pass; the rest were found chapter by chapter when the
        # book was translated to Luganda (the lg edition rendered the intended
        # reading, so only the English needed repair). Each pair is anchored on
        # enough context to match once; the derived body_text carries every fix
        # too. Also four non-spacing slips the same pass surfaced (a factual
        # "Moses’"→"Noah’s", "symbol"→"cymbal", "sever"→"seven",
        # "follow"→"following"), and ten dropped or mismatched quotation marks
        # closed to the reading the surrounding prose forces.
        "replacements": [
            # ch1 — Paul’s Prayer
            ("P aul writes:", "Paul writes:"),
            ("Creator and Hi s Son", "Creator and His Son"),
            ("yet t here was a hunger", "yet there was a hunger"),
            ("Ephesians’ fa ith and love", "Ephesians’ faith and love"),
            ("day , thi s scripture", "day , this scripture"),
            ("“… t hat He would grant", "“… that He would grant"),
            ("robbed the church of its power.</p>", "robbed the church of its power.”</p>"),
            # ch2 — In Him
            ("Consider this: Moses’ salvation", "Consider this: Noah’s salvation"),
            ("God looks upo n us", "God looks upon us"),
            ("the praise o f His glory", "the praise of His glory"),
            ("with every spirit ual blessing", "with every spiritual blessing"),
            ("GRACE - G od’s R iches A t C hrist’s E xpense", "GRACE - God’s Riches At Christ’s Expense"),
            ("Jesu s said that", "Jesus said that"),
            ("We are reckone d to have", "We are reckoned to have"),
            ("with the se words", "with these words"),
            ("praise of His glory!”", "praise of His glory!’"),
            # ch3 — Sealed and Seated
            ("‘wait in Je rusalem", "‘wait in Jerusalem"),
            ("the Holy Sp irit", "the Holy Spirit"),
            ("we are n ow called", "we are now called"),
            ("‘heavenly places’ i n Christ", "‘heavenly places’ in Christ"),
            ("this is G od’s will", "this is God’s will"),
            ("implying tha t it", "implying that it"),
            ("visit my h ome", "visit my home"),
            ("“I am seated in Gareth’s home, unless", "“I am seated in Gareth’s home”, unless"),
            # ch4 — A Body and a Building
            ("‘summed up’ in Ch rist", "‘summed up’ in Christ"),
            ("are a tem ple of God", "are a temple of God"),
            ("no r vice versa", "nor vice versa"),
            ("lost world wit h the hands", "lost world with the hands"),
            ("‘fo r good works’", "‘for good works’"),
            ("systems and bringin g glory", "systems and bringing glory"),
            ("many differi ng parts", "many differing parts"),
            ("one leg pu shes backward", "one leg pushes backward"),
            ("the ‘chief cornerstone (Eph 2:20)", "the ‘chief cornerstone’ (Eph 2:20)"),
            # ch5 — A Covenant People
            ("They were r ecipients", "They were recipients"),
            ("above al l other peoples", "above all other peoples"),
            ("Jesus will reveal Himsel f as", "Jesus will reveal Himself as"),
            ("those ceremoni es was", "those ceremonies was"),
            ("will obey your Wo rd", "will obey your Word"),
            ("elements ‘unworthily , i.e.", "elements ‘unworthily’, i.e."),
            # ch6 — The Privilege of Ministry
            ("Adifferent perspective", "A different perspective"),
            ("ministers for Christ Jes us", "ministers for Christ Jesus"),
            ("try to do God ’s work", "try to do God’s work"),
            ("build up the c hurch", "build up the church"),
            ("released me with t he words", "released me with the words"),
            # ch7 — The Christian Walk
            ("repea t:", "repeat:"),
            ("wif e!", "wife!"),
            ("<p>Itrust", "<p>I trust"),
            ("we have lea rned to", "we have learned to"),
            ("longsuffering, gentl eness, goodness", "longsuffering, gentleness, goodness"),
            ("the new n ature", "the new nature"),
            ("just as Chris t also loved", "just as Christ also loved"),
            ("filled with t he Spirit", "filled with the Spirit"),
            ("a groaning fo llowed by", "a groaning followed by"),
            ("The follow three pieces", "The following three pieces"),
            ("clanging symbol", "clanging cymbal"),
            # ch8 — Godly Relationships
            ("I bel ieve the emphasis", "I believe the emphasis"),
            ("to the vicious c ircle", "to the vicious circle"),
            ("book of Revela tion", "book of Revelation"),
            ("“all in heavenly places’ (the external", "“all in heavenly places” (the external"),
            ("“give the devil an opportunity’?", "“give the devil an opportunity”?"),
            # ch9 — Stand Firm
            ("but they ca n say", "but they can say"),
            ("understand th e tactics", "understand the tactics"),
            ("His glory, t o be strengthened", "His glory, to be strengthened"),
            ("tried by o ur circumstances", "tried by our circumstances"),
            ("up my gr eat career", "up my great career"),
            ("a resurrecti on for me", "a resurrection for me"),
            ("the sever churches of Asia", "the seven churches of Asia"),
            ("take ‘time out” to consider", "take ‘time out’ to consider"),
            ("love of God in Christ Jesus (Rom 8:39)", "love of God in Christ Jesus” (Rom 8:39)"),
            ("for the hope of the resurrection! (Acts 26:1-8 paraphrased)", "for the hope of the resurrection!” (Acts 26:1-8 paraphrased)"),
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


# --- Luganda: a doubled inflected verb, 23 sites across 10 lg editions -------
#
# The translations wrote e.g. "biteekeddwateekeddwa" where the word is
# "biteekeddwa" (prepared/appointed). It is NOT Luganda reduplication: a genuine
# reduplication doubles the STEM (okuteekateeka, okubuusabuusa, enkyukakyuka,
# mpolampola), whereas this doubles a fully INFLECTED form, suffixes and all.
# he-holds-my-tomorrows ch09 settles it by using both in one clause -- "mu
# nteekateeka Katonda gy'atuteekeddeteekedde" -- the real reduplicated noun
# standing beside the defect. The same files use the clean form freely (22 times
# in the-unselfishness-of-god alone).
#
# The repair collapses the repetition and KEEPS THE FIRST inflection, so the
# author's own voice survives: by'ateekedde stays active, biteekeddwa stays
# passive. Found while building the scripture crib for waiting-on-god -> lg
# (#1205), where 1 Cor 2:9 came back carrying one.
#
# Merged in below rather than threaded through the literal above so all twenty
# pairs stay together and reviewable, and so this class of defect -- our own
# translation output, not the extractor and not the source -- is visibly its own
# thing. They are Luganda strings and can never match another language's text.
# `waiting-on-god.en` ch07 opens a paragraph with a quotation mark that never
# closes: "<p> 'I SPOKE of an army...". Murray is recalling his own previous
# chapter, not quoting anyone, and the mark renders as a stray glyph in the
# reader. Repaired here rather than per-edition because the editions AGREE —
# all six shipped translations (es, pt, sw, hi, ar, uk) drop it, which is the
# bar this file uses for touching a source. Found while translating to lg (#1205).
BODY_CORRECTIONS.setdefault("waiting-on-god", {}).setdefault("replacements", []).append(
    ("<p> 'I SPOKE of an army", "<p> I SPOKE of an army")
)

# OCR/extraction slips found while translating Watson's book to Portuguese (batch 4). Watson's text is scripture-dense and heavily OCR-damaged; each fix is forced by the KJV verse quoted or by grammar/citation. Two orphan close-quotes clear audit findings (baseline re-pinned).
BODY_CORRECTIONS.setdefault('all-things-for-good', {}).setdefault("replacements", []).extend([
    ('The certainly of the privilege', 'The certainty of the privilege'),
    ('(2 Cor. v. l)', '(2 Cor. v. 1)'),
    ('hearts of Gods people', 'hearts of God’s people'),
    ('mercies of God world for good', 'mercies of God work for good'),
    ('servant lob shall pray', 'servant Job shall pray'),
    ('(Matt. xiii. 38 42)', '(Matt. xiii. 38-42)'),
    ('Almighty hath addicted me', 'Almighty hath afflicted me'),
    ('these good pips', 'these good figs'),
    ('scum boils up ñ much', 'scum boils up — much'),
    ('saints in addiction', 'saints in affliction'),
    ('sorrow shall he turned', 'sorrow shall be turned'),
    ('we should riot be judged', 'we should not be judged'),
    ('(Dan. xii. 31)', '(Dan. xii. 3)'),
    ('ointment which kids', 'ointment which kills'),
    ('(Job xiii. 10)', '(Job xlii. 10)'),
    ('thou hast addicted me', 'thou hast afflicted me'),
    ('(Thess. v. 18)', '(1 Thess. v. 18)'),
    ('(Psalm xlviii. 141)', '(Psalm xlviii. 14)'),
    ('love our Ford Jesus', 'love our Lord Jesus'),
    ('His gospel. which is the rod', 'His gospel, which is the rod'),
    ('it is rot lawful', 'it is not lawful'),
    ('God hath nor called', 'God hath not called'),
    ('do to he saved', 'do to be saved'),
    ('(Psalm cv. 2)', '(Psalm cx. 2)'),
    ('shall co operate', 'shall co-operate'),
    ('(2 Pet. i. 10).We make', '(2 Pet. i. 10). We make'),
    ('</i>l <i>thank', '</i> <i>thank'),
    ('obedience.” </b>', 'obedience. </b>'),
    ('appearing.” </b>', 'appearing. </b>'),
])

# OCR slips in Whitefield's sermon found while translating to Portuguese (batch 4); includes Luther's Latin 'articulus stantis aut cadentis ecclesiae' garbled by the scanner.
BODY_CORRECTIONS.setdefault('the-lord-our-righteousness', {}).setdefault("replacements", []).extend([
    ('Arians of Socinians', 'Arians or Socinians'),
    ('Artienlus statntis out cedentis Eichlesin,', 'Articulus stantis aut cadentis Ecclesiae,'),
    ('he never dies, he never will', 'he never does, he never will'),
    ('Stoddard or Northampton', 'Stoddard of Northampton'),
    ('God an in inducing', 'God as an inducing'),
    ('further to affirming', 'further to affirm'),
])

# OCR/extraction slips found while translating three works to Portuguese
# (batch 3). Each has one unambiguous reading, confirmed byte-exact in the
# source and against a canonical edition; the sense is forced by grammar or by
# the scripture the author is quoting. NOTE: several online reproductions
# (biblebb.com) share the same OCR lineage as our fixture, so the evidence is
# the quoted scripture / sense, not a cleaner edition. The pt editions render
# the corrected readings (fix-forward).
BODY_CORRECTIONS.setdefault("absolute-surrender", {}).setdefault("replacements", []).extend([
    # ch06: quoted words are Romans 8:2 (introduced as "the second verse"); the
    # printed "(Rom. 8:12)" contradicts it.
    ("(Rom. 8:12)", "(Rom. 8:2)"),
    # ch08: intrusive "need" — canonical "why do you not believe...".
    ("do you not need believe", "do you not believe"),
    # ch08: a graft "strikes" (takes root); "stroke" is no horticultural term.
    ("time to stroke", "time to strike"),
    # ch09: reversed closing quote after "nothing." (opening curly used to close).
    ("<i>nothing.</i>“", "<i>nothing.</i>”"),
])
BODY_CORRECTIONS.setdefault("marks-of-a-true-conversion", {}).setdefault("replacements", []).extend([
    # Ps 73:4 quotation: "no bands in their death" (KJV); "hands" is OCR.
    ("any hands in their death", "any bands in their death"),
    # idiom "now and then"; "not and then" does not parse.
    ("is not and then good-natured", "is now and then good-natured"),
    # "the guilt of Adam's sin" (imputed guilt); "guild" is meaningless.
    ("the guild of Adam", "the guilt of Adam"),
    # "done it before" — "lit" is a dropped-letter OCR.
    ("have not done lit before", "have not done it before"),
    # "be bold with your Father" (Abba, Father — boldness in prayer); "gold" OCR.
    ("be gold with your Father", "be bold with your Father"),
    # John 11:25: "the resurrection and the life"; "the live" is OCR.
    ("resurrection and the live", "resurrection and the life"),
    # "to see and know" — "se" is a dropped letter.
    ("thee to se and know", "thee to see and know"),
])
BODY_CORRECTIONS.setdefault("a-divine-and-supernatural-light", {}).setdefault("replacements", []).extend([
    # "concerned" — "concemed" is the classic rn->m scan error; not a word.
    ("are concemed and made use", "are concerned and made use"),
    # two dittographies (a clause printed twice); keep one copy. Canonical reads
    # each once. A verbatim clause-doubling is a mechanical artifact, never
    # authorial, so these are safe even though the online lineage shares them.
    ("when the light of the sun is cast upon them; so that the mind can better judge of them. As he that beholds the objects on the face of the earth, when the light of the sun is cast upon them,",
     "when the light of the sun is cast upon them,"),
    ("as the wise and prudent; and they are often hid from these things, as the wise and prudent; and they are often hid from these when",
     "as the wise and prudent; and they are often hid from these when"),
])

# OCR/extraction slips found while translating three works to Portuguese
# (batch 2). Each is a mechanical defect whose correct reading is forced by
# grammar or the surrounding text and confirmed against a canonical edition
# (Gutenberg #65115 for Bounds; spurgeon.org for "Christ Crucified"). The
# Portuguese editions render the corrected reading (fix-forward).
BODY_CORRECTIONS.setdefault("power-through-prayer", {}).setdefault("replacements", []).extend([
    # ch01: "in dependent" is a split of "independent" (a king's bearing is
    # independent, not dependent).
    ("royal, in dependent bearing", "royal, independent bearing"),
    # ch04: William Carey's Serampore Brotherhood; "Carrey" is an OCR doubling.
    ("Carrey’s Brotherhood", "Carey’s Brotherhood"),
    # ch07: Lancelot Andrewes — ch08 already spells it "Andrewes"; canonical agrees.
    ("Bishop Andrews", "Bishop Andrewes"),
    # ch11 (Edwards quotation): "distingushed" -> "distinguished".
    ("distingushed talents", "distinguished talents"),
    # ch11: canonical "neither arrested nor straitened" (narrowed), paired with
    # the channel being "broadened"; "straightened" inverts the image.
    ("neither arrested nor straightened", "neither arrested nor straitened"),
    # ch12 (Cecil epigraph): missing auxiliary "be" in the passive.
    ("heart will not borne home", "heart will not be borne home"),
    # ch13: closing quote after "Give me thy heart!" mangled to the glyph "Ý".
    ("thy heart!Ý is", "thy heart!” is"),
    # ch14: two em-dashes flattened to "?" and one to a stray apostrophe.
    ("and retain?the art", "and retain—the art"),
    ("an audience?he has", "an audience—he has"),
    ("such a thing’but there", "such a thing—but there"),
    # ch15: "he"->"be"; and in the verse couplet "silt"->"sin" (next line: "for sin").
    ("need to he refreshed", "need to be refreshed"),
    ("death to silt", "death to sin"),
    # ch16: canonical "pungent, penetrating heart-breaking force".
    ("pungent, perpetrating", "pungent, penetrating"),
    # ch16: canonical "the holy of holies".
    ("holy of holiest", "holy of holies"),
    # ch18: "an" -> "in".
    ("occupied an the spiritual life", "occupied in the spiritual life"),
])
BODY_CORRECTIONS.setdefault("the-almost-christian", {}).setdefault("replacements", []).extend([
    # subject "he" governs both verbs: "acts and speaks".
    ("all things act and speaks", "all things acts and speaks"),
    # three stray full stops mid-sentence (lowercase word after each confirms
    # the sentence continues); the second is inside a quotation of John 1:12.
    ("in general. the giving", "in general, the giving"),
    ("the sons of God. even to them", "the sons of God, even to them"),
    ("words and works. your business", "words and works, your business"),
    # NOTE (not corrected here): the sermon also has many sentence-initial "he/
    # his" left lowercase after a full stop — a pervasive capitalization artifact
    # better handled by a dedicated normalization pass than by fragile string
    # pairs. Flagged for the english-qa sweep.
])
BODY_CORRECTIONS.setdefault("christ-crucified", {}).setdefault("replacements", []).extend([
    # doubled genitive; parallel clause reads "his father's name was Joseph".
    ("his mothers’s name", "his mother’s name"),
    # canonical "work out its own conclusions" ("word" is a d/k OCR slip).
    ("to word out its own", "to work out its own"),
    # a "Greek" would call exclusive truth bigotry; "begot" is a slip for "bigot".
    ("I was a begot", "I was a bigot"),
    # canonical "accoutred as ye are" (the swim-in-armour image from Julius Caesar).
    ("plunge in, accounted as ye are", "plunge in, accoutred as ye are"),
    # John 20:16: standard transliteration "Rabboni".
    ("him “Rabonni.”", "him “Rabboni.”"),
])


_LG_DOUBLED_VERB: dict[str, list[tuple[str, str]]] = {
    "all-of-grace": [
        ('biteekeddwateekeddwa', 'biteekeddwa'),
        ('kikuteekeddeteekedde', 'kikuteekedde'),
    ],
    "godliness": [
        ('eteekeddwateekeddwa', 'eteekeddwa'),
    ],
    "he-holds-my-tomorrows": [
        ('abateekeddwateekeddwa', 'abateekeddwa'),
        ('akuteekeddeteekedde', 'akuteekedde'),
        ('atuteekeddeteekedde', 'atuteekedde'),
    ],
    "prayer-the-pulse-of-life": [
        ("by'akuteekeddeteekedde", "by'akuteekedde"),
    ],
    "stepping-stones-2": [
        ('atuteekeddeteekedde', 'atuteekedde'),
        ('biteekeddwateekeddwa', 'biteekeddwa'),
    ],
    "talks-to-the-farmer": [
        ('teriteekeddwateekeddwa', 'teriteekeddwa'),
    ],
    "the-god-of-all-comfort": [
        ('eteekeddwateekeddwa', 'eteekeddwa'),
    ],
    "the-inner-chamber": [
        ('amuteekeddeteekedde', 'amuteekedde'),
        ('obuteekeddwateekeddwa', 'obuteekeddwa'),
    ],
    "the-person-and-work-of-the-holy-spirit": [
        ('eteekeddwateekeddwa', 'eteekeddwa'),
    ],
    "the-unselfishness-of-god": [
        ('abateekeddwateekeddwa', 'abateekeddwa'),
        ('biteekeddwateekeddwa', 'biteekeddwa'),
        ("by'ateekeddeteekeddwa", "by'ateekedde"),
        ('eteekeddwateekeddwa', 'eteekeddwa'),
        ('guteekeddwateekeddwa', 'guteekeddwa'),
        ('nteekeddwateekeddwa', 'nteekeddwa'),
    ],
}

for _slug, _reps in _LG_DOUBLED_VERB.items():
    BODY_CORRECTIONS.setdefault(_slug, {}).setdefault("replacements", []).extend(_reps)

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


#: A LONE footnote-reference superscript: an empty ``<sup></sup>`` (the marker
#: whose number the extractor dropped, leaving pure residue) or a bare numbered
#: one, ``<sup>4</sup>``. In this corpus a ``<sup>`` is only ever a footnote
#: marker — never an exponent or an ordinal (an ordinal keeps its letters,
#: ``1<sup>st</sup>``, which the digit class below cannot match) — and the notes
#: they point at are gone (dropped with CCEL's ``[class*=note i]`` apparatus, or
#: never extracted), so the marker is unstyled residue that the reader has no
#: feature behind: junk for the eye, and read aloud as "…grace FOUR" for the ear.
#:
#: LONE is the whole point of the two guards. A WELDED footnote —
#: ``<sup>1</sup><sup>1</sup>Note text…`` — is a different, tracked defect
#: (`welded-footnote`), repaired per work by hand or by
#: :func:`strip_transcription_footnotes`, because removing only its markers would
#: strand the note text mid-prose. The lookbehind excludes the second marker of
#: such a pair and the lookahead the first, so this rule never touches one.
#:
#: Inline ``[1]`` / ``[a]`` brackets are deliberately NOT handled here: across the
#: corpus they are overwhelmingly the author's own enumeration ("three things: [1]
#: Wisdom. [2] Authority.") — prose the page must keep. Stripping *those* for the
#: ear only is the reader's job (`frontend/src/lib/listenText.ts`), not the
#: importer's, because the eye still needs them.
_LONE_FOOTNOTE_SUP = _re.compile(
    r"(?<!</sup>)\s?<sup>(?:\d{1,3}|\s*)</sup>(?!<sup>)"
)


def strip_footnote_markers(body_html: str) -> str:
    """Remove lone footnote-reference superscripts. Idempotent.

    ``body_html`` only, and a no-op on the tagless ``body_text`` besides: the
    pattern is anchored on ``<sup>`` markup, which a stripped body never carries.
    Welded footnotes and inline ``[n]`` enumeration are left untouched — see
    :data:`_LONE_FOOTNOTE_SUP`.
    """
    return _LONE_FOOTNOTE_SUP.sub("", body_html)


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


def restore_dropped_blocks(body_html: str, blocks: Sequence[tuple[str, str]]) -> str:
    """Put back a block the sanitizer deleted, before the block that followed it.

    Named for the shape, not the first case: it restores a `<h4>` note heading in
    `ministry-of-intercession` and a `<p>` sermon TEXT in
    `selected-sermons-edwards`, both deleted by an over-matching drop selector,
    both opening their chapter.

    `sanitize.DROP_SELECTORS` carries `[class*=pginternal]`, and `_clean`
    DECOMPOSES the drop-selectors before it unwraps everything else. A Gutenberg
    heading whose only child is its anchor was therefore emptied, and the
    empty-block regex a few lines down then removed the heading itself. Six of
    them went that way in `ministry-of-intercession` ch18.

    The selector is QUALIFIED now — `sanitize.KEEP_PREDICATES` keeps a link that
    carries a word — so no FUTURE import loses a heading this way. This stays
    for the rows already on the shelf, which are never re-imported:
    `ingest.upsert_book` deletes and recreates every chapter, and restoring
    markup in English alone would break the ordered-tag parity with the
    translations that `tests_translation_markup` enforces.

    Idempotent by GUARD rather than by anchor, and that is the whole reason this
    is not a `replacements` pair. A pure INSERTION has `old` as a substring of
    `new`, so it re-fires every time it runs — `SettledBodyIdempotenceTests`
    applies every correction twice precisely to catch that. The trick the other
    keys use, consuming the preceding `</p> ` boundary so the match cannot
    recur, is unavailable to a heading that OPENS a chapter: there is nothing in
    front of it. Checking whether the heading is already there works in both
    positions and reads as what it means.

    `body_html` ONLY. Each anchor carries its `<p>`, so nothing here can match
    the derived, tagless `body_text` — which is what keeps block tags out of a
    field that must never hold any. `Chapter.save()` re-derives that field from
    the HTML this has already fixed.
    """
    for anchor, block in blocks:
        if block in body_html or anchor not in body_html:
            continue
        body_html = body_html.replace(anchor, f"{block} {anchor}", 1)
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
        body_html = restore_dropped_blocks(body_html, entry.get("restored_blocks", ()))
        if entry.get("strip_transcription_footnotes"):
            body_html = strip_transcription_footnotes(body_html)
    body_html = rejoin_linebreak_hyphens(body_html)
    # A rule, not a list, like the rejoin above: lone footnote-marker residue
    # occurs across works and is unambiguous, so it comes out for every one. It
    # runs AFTER the declared replacements so a work's own welded-footnote repair
    # consumes its markers first, leaving this nothing to half-strip.
    body_html = strip_footnote_markers(body_html)
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
