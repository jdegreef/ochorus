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
from html import escape as _escape

from library.text import html_to_text

# NOT public domain (copyright audit 2026-07-10), and no permission: Watchman
# Nee's English editions (1957–1983, Kinnear/CLC/CFP) and Amy Carmichael's "If"
# (1938, URAA-restored). Every edition in EVERY language stays unpublished — a
# translation of these is a derivative of the protected English. Migration 0022
# unpublished the rows that existed in July; translations filed later slipped
# through and went live (grace-for-grace-2 es/fr/pt, 2026-09-24), so this set is
# now enforced in CI (tests_fixture), by the admin translation-job filer, and
# by migration 0164. Remove a slug only with the rights holder's permission.
COPYRIGHT_BLOCKED_SLUGS: frozenset[str] = frozenset({
    "the-normal-christian-life",
    "grace-for-grace-2",
    "the-body-of-christ-a-reality",
    "the-body-of-christ-teens",
    "let-us-pray-2",
    "if",
})

# Catalogue slugs to skip on a full import (e.g. duplicate/teen editions we don't
# want in the library). An explicit `import_ochorus <slug>` still imports them.
EXCLUDED_SLUGS: set[str] = {
    # Teens edition of "The Person and Work of the Holy Spirit"; we keep the
    # adult original (the-person-and-work-of-the-holy-spirit).
    "the-person-and-work-of-the-holy-spirit-2",
    # Kept out of re-import too.
    *COPYRIGHT_BLOCKED_SLUGS,
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
        # Transcribed from Grosart's scan, where the titles sat on the marker
        # line and both truncated and picked up the worst of the OCR (marker
        # line plus its wrapped continuation, misreads repaired: "ivill"->will,
        # "Rides"->Rules, "Eeproof"->Reproof, "he\epresenteth"->he representeth,
        # "unto its"->unto us; 1, 9 and 21 completed from the 1878 contents
        # page). They carry over unchanged to Pickering's 1838 printing, the
        # current source: its headings read the same, one for one.
        #
        # Pickering has TWENTY-EIGHT chapters. Grosart's scan lost the
        # "XXVIII." marker and merged the last two, which is why this list
        # stopped at 27 and ch28 shipped with the importer's truncated first
        # heading line. (Not, as #1943 claimed, 17-27 under wrong titles:
        # every earlier title matched its body.)
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
            28: "Be encouraged to go on cheerfully, with confidence of prevailing",
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
    "school-of-prayer": {
        # CCEL titles each lesson "First Lesson. ‘Lord, teach us to pray;’ Or,
        # The Only Teacher" — the reader already numbers the chapter, and the
        # motto is the verse the lesson opens with. Title each by its own "Or,"
        # subtitle, as the four-lesson `lord-teach-us-to-pray-2` already does
        # (CCEL's TOC also misspells "Ninteenth", which this sidesteps). Ch33
        # is Murray's closing note on Müller, spelled as the library spells him.
        "chapter_titles": {
            2: "The Only Teacher",
            3: "The True Worshippers",
            4: "Alone with God",
            5: "The Model Prayer",
            6: "The Certainty of the Answer to Prayer",
            7: "The Infinite Fatherliness of God",
            8: "The All-Comprehensive Gift",
            9: "The Boldness of God’s Friends",
            10: "Prayer Provides Labourers",
            11: "Prayer Must Be Definite",
            12: "The Faith That Takes",
            13: "The Secret of Believing Prayer",
            14: "The Cure of Unbelief",
            15: "Prayer and Love",
            16: "The Power of United Prayer",
            17: "The Power of Persevering Prayer",
            18: "Prayer in Harmony with the Being of God",
            19: "Prayer in Harmony with the Destiny of Man",
            20: "Power for Praying and Working",
            21: "The Chief End of Prayer",
            22: "The All-Inclusive Condition",
            23: "The Word and Prayer",
            24: "Obedience the Path to Power in Prayer",
            25: "The All-Prevailing Plea",
            26: "The Holy Spirit and Prayer",
            27: "Christ the Intercessor",
            28: "Christ the High Priest",
            29: "Christ the Sacrifice",
            30: "Our Boldness in Prayer",
            31: "The Ministry of Intercession",
            32: "A Life of Prayer",
            33: "George Müller, and the Secret of His Power in Prayer",
        },
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
#   wrapped_blocks: [(head, tag)] — the sanitizer UNWRAPPED a display line to
#     loose text; the run opening with `head` goes back into `<tag>`. See
#     `wrap_loose_blocks`.
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
        "replacements": [
            ('unto him, "Thus saith', 'unto him, \u201cThus saith'),
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
        # link, not what Murray printed. These pairs are English-only: the es,
        # fr, pt and sw editions were all translated after #1929 from the
        # repaired English, so they shipped with the references and the ch33
        # headings in their own words and need no pairs of their own.
        #
        # ch33 (Notes) lost all seven of its `NOTE A.`–`NOTE G.` headings to a
        # DIFFERENT selector: `[class*=note i]`, written for CCEL's footnote
        # apparatus, also matched Gutenberg's own `class="note"`. That selector
        # is FIXED at the source now (`sanitize._is_gutenberg_note_content`), so
        # no future import loses them — but these rows are never re-imported, so
        # ch33 shipped as seven bare `<hr/>`s with no headings until #1929.
        #
        # They go back via `restored_blocks`, the mechanism
        # `ministry-of-intercession` uses for byte-identical damage from the
        # sibling selector — not `replacements` pairs, because a pure insertion
        # re-fires on every deploy (see `restore_dropped_blocks`). Restored with
        # the SOURCE's own tags, `<h3>` for the note letter and `<h4>` for its
        # subtitle (NOTE D and NOTE E have no subtitle in the print, so they get
        # none here), spelled EXACTLY as the fixed sanitizer would produce them,
        # so the guard recognises its own work and a re-imported edition would
        # not carry the heading twice. That is PER-HEADING, not a house rule:
        # A-G wear a leading space because the source writes
        # `<h3 class="note"> <a id="note_A">NOTE A.</a></h3>` and the anchor
        # leaves one behind, while ch5's bare `NOTE.` has no anchor
        # (`<h3 class="note">NOTE.</h3>`) and so must have none. Getting that
        # backwards breaks nothing today — it breaks on the re-import, by
        # inserting a second heading beside the first.
        #
        # Each anchor is unique across the WHOLE book, not merely its chapter:
        # `restore_dropped_blocks` is applied to every chapter in turn, so an
        # anchor that also matched elsewhere would insert a heading into the
        # wrong one. An eighth heading, a bare `NOTE.`, belongs to ch5 rather
        # than the Notes chapter and is restored there.
        #
        # The footnote BLOCKS that pointed at them stay dropped, by design: the
        # markers referencing them are dropped too, so restoring the blocks
        # alone would orphan the note text mid-chapter.
        "restored_blocks": [
            ("<p>The connection between the fear of God and holiness is most i",
             "<h3>NOTE.</h3>"),
            ("<p>In a little book\u2014Holiness, as understood by the Writers o",
             "<h3> NOTE A.</h3> <h4>Holiness as Proprietorship.</h4>"),
            ("<p>The proper meaning of the Hebrew word for holy, <i>kadosh",
             "<h3> NOTE B.</h3> <h4>On the Word for Holiness.</h4>"),
            ("<p>There is not a word so exclusively scriptural, so distinc",
             "<h3> NOTE C.</h3> <h4>The Holiness of God.</h4>"),
            ("<p>\u2018Our holiness does not consist in our changing and becomi",
             "<h3> NOTE D.</h3>"),
            ("<p>Let me once more refer all students of holiness to Marsha",
             "<h3> NOTE E.</h3>"),
            ("<p>\u2018According to the Spirit of Holiness. The word <i>hagios",
             "<h3> NOTE F.</h3> <h4>Note from Bengel on Rom. i. 4.</h4>"),
            ("(<i>From an address by Pastor Stockmaiev.</i>) <p>\u2018Who gave ",
             "<h3> NOTE G.</h3> <h4>\u2018Freed\u2019 and \u2018Possessed\u2019\u2014The Twofold Result of "
             "Redemption.</h4>"),
        ],
        "replacements": [
            ("deep Restfulness ()", "deep Restfulness (ch. 3)"),
            ("humble Reverence ()", "humble Reverence (ch. 4)"),
            ("entire Surrender ()", "entire Surrender (ch. 5)"),
            ("joyful Adoration ()", "joyful Adoration (ch. 6)"),
            ("simple Obedience ()", "simple Obedience (ch. 7)"),
            ("the Divine Indwelling ()", "the Divine Indwelling (ch. 8)"),
            ("His Glory and Majesty (see ‘’)", "His Glory and Majesty (see ‘Sixth Day’)"),
            # ch33's own cross-reference back to NOTE A, lost the same way.
            ("made in the note to ‘Sixth Day,’ on .</p>",
             "made in the note to ‘Sixth Day,’ on Holiness as Proprietorship.</p>"),
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
        # ch9 (Notes) lost FIVE page references the same way the sermon texts
        # were lost, but to the SIBLING selector — `pginternal`, decomposing the
        # cross-reference whole and leaving "see note, p. ." for the reader to
        # follow. Three of the five are what `english_audit`'s
        # `space-before-punct` class pinned at 3 for this book; a fourth sits
        # inside parentheses so that class never saw it, and the fifth is the
        # Introduction reference. All five numbers read off #34632.
        "replacements": [
            ("for the press (see Introduction, p. ). The manuscript",
             "for the press (see Introduction, p. xxix). The manuscript"),
            ("cf. n. here following, p. .", "cf. n. here following, p. 162."),
            ("\u201cAnd consider here more particularly\u201d (p. ).",
             "\u201cAnd consider here more particularly\u201d (p. 89)."),
            # The dropped `[6]` footnote marker left a space behind the `<p>`.
            ("</p> <p> See note, p. .", "</p> <p>See note, p. 179."),
            ("prepared for preaching, see note p. .",
             "prepared for preaching, see note p. 157."),
        ],
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
    "a-ribband-of-blue": {
        # The sermon's own title line was lost, and with it the end of a
        # sentence: the body read "…to introduce the wearing of the" and then
        # moved on to "GOD would have all His people wear a badge." Gutenberg
        # #23438 sets the missing words as a centred display line,
        # `<div class="c1"><small>"RIBBAND OF BLUE."</small></div>`, and
        # `import_sermons.extract_gutenberg_section` collected only headings,
        # `<p>` and `<blockquote>` — so a `div` was skipped outright, not
        # sanitized away. It keeps display lines now, as exactly this `<p>`.
        # Restored as its own `<p>`, the block it would be had the importer
        # kept it, with the small caps flattened as everywhere else in the body.
        #
        # One pair PER EDITION, each anchored on that language's next paragraph
        # so it can only bite its own row: the fr and sw translations were made
        # from the damaged English and carry the same truncation at the same
        # block. All three move together or `tests_translation_markup`'s tag
        # parity breaks. The fr follows its title ("Un cordon bleu"); the sw
        # follows its title ("Uzi wa Rangi ya Samawi", Union Version wording).
        # The sw translation notes' `block_index` values after the new block
        # shifted by one in the same commit; the one quote anchored in this
        # sermon (`quote_seed`, paragraph 6) sits above it.
        "restored_blocks": [
            ("<p>GOD would have all His people wear a badge.",
             '<p>"RIBBAND OF BLUE."</p>'),
            ("<p>Dieu voulait que tout son peuple portât un signe.",
             "<p>« CORDON BLEU ».</p>"),
            ("<p>MUNGU alitaka watu wake wote wavae alama.",
             '<p>"UZI WA RANGI YA SAMAWI."</p>'),
        ],
    },
    # --- The rest of Gutenberg #23438, "A Ribband of Blue" --------------------
    # The same root cause as the entry above, at scale. The edition sets every
    # in-study section heading as a centred small-caps display line —
    # `<div class="c1"><small>THE UNSEEN HEDGE</small>.</div>` — and every
    # displayed scripture line and opening epigraph the same way, and
    # `import_sermons.extract_gutenberg_section` collected none of them: 23 lines
    # across six studies. Two losses were text, not typography:
    # `blessed-prosperity` block 10 ends "Further, the truly blessed man--" and
    # its sentence finished on the lost line "Standeth not in the way of
    # sinners."; `blessed-adversity` block 14 answers "in the words which we
    # have already quoted" with a Job 1:21 that was never on the page.
    #
    # The importer keeps these lines now (`ingest.display_line`), and
    # every English block below is spelled EXACTLY as it emits them: a line set
    # wholly in capitals is an `<h3>` with the source's own wording and stops;
    # anything else is a `<p>`; a leading quotation is the epigraph
    # `<blockquote>`. So a re-import finds each one present and the guard
    # skips it. `coming-to-the-king` lost nothing.
    #
    # Translations were made from the damaged English, so each edition carries
    # its own pairs, anchored on that language's following paragraph, and all
    # move together or `tests_translation_markup`'s tag parity breaks. The
    # verse lines take each edition's own wording where its body already
    # quotes the verse (Job 1:21 in every `blessed-adversity`, Ruth 2:12 in
    # `a-full-reward`), and the language's registry Bible otherwise; the fr and
    # hi "seat of the scornful" follow their block 13, which names it a SEAT
    # ("banc", "आसन"), rather than Segond's "compagnie" / IRV's "मण्डली".
    # Quote anchors (`quote_seed`) and translation-note `block_index` values
    # below each insertion shifted in the same commit. The English epigraph of
    # `a-full-reward` keeps Gutenberg's "they father" (for "thy") — reported,
    # not fixed: unchecked against a printing.
    "blessed-prosperity": {
        "restored_blocks": [
            # en
            ("<p>There is a prosperity which",
             "<p>Meditations On The First Psalm.</p>"),
            ("<p>There is a prosperity which", "<h3>INTRODUCTORY.</h3>"),
            ("<p>More literally, O the blessings,",
             "<h3>THE NEGATIVE CONDITIONS OF BLESSING</h3>"),
            ("<p>More literally, O the blessings,",
             '<p><em>"Blessed is the man that walketh not in the counsel of the ungodly."</em></p>'),
            ("<p>Birds of a feather flock",
             "<p><em>Standeth not in the way of sinners.</em></p>"),
            ("<p>The seat of the scornful",
             '<p><em>"Nor sitteth in the seat of the scornful."</em></p>'),
            ("<p>We have considered the",
             "<h3>THE POSITIVE CONDITIONS OF BLESSING.</h3>"),
            ("<p>We next proceed to notice", "<h3>THE OUTCOME IN BLESSING.</h3>"),
            ("<p>It is not necessary to", "<h3>THE CONTRAST.</h3>"),
            ("<p>It is not necessary to", '<p><em>"The ungodly are not so."</em></p>'),
            # fr
            ("<p>Il existe une prospérité",
             "<p>Méditations sur le premier Psaume.</p>"),
            ("<p>Il existe une prospérité", "<h3>INTRODUCTION.</h3>"),
            ("<p>Plus littéralement : ô",
             "<h3>LES CONDITIONS NÉGATIVES DE LA BÉNÉDICTION</h3>"),
            ("<p>Plus littéralement : ô",
             "<p><em>« Heureux l’homme qui ne marche pas selon le conseil des méchants. »</em></p>"),
            ("<p>Qui se ressemble s’assemble",
             "<p><em>Qui ne s’arrête pas sur la voie des pécheurs.</em></p>"),
            ("<p>Le banc des moqueurs est",
             "<p><em>« Et qui ne s’assied pas au banc des moqueurs. »</em></p>"),
            ("<p>Nous avons considéré les",
             "<h3>LES CONDITIONS POSITIVES DE LA BÉNÉDICTION.</h3>"),
            ("<p>Nous en venons ensuite", "<h3>L’ISSUE EN BÉNÉDICTION.</h3>"),
            ("<p>Il n’est pas nécessaire", "<h3>LE CONTRASTE.</h3>"),
            ("<p>Il n’est pas nécessaire",
             "<p><em>« Il n’en est pas ainsi des méchants. »</em></p>"),
            # hi
            ("<p>एक ऐसी समृद्धि है जो धन्य", "<p>पहले भजन पर मनन।</p>"),
            ("<p>एक ऐसी समृद्धि है जो धन्य", "<h3>भूमिका।</h3>"),
            ("<p>और भी अक्षरशः कहें तो,", "<h3>आशीष की निषेधात्मक शर्तें</h3>"),
            ("<p>और भी अक्षरशः कहें तो,",
             '<p><em>"क्या ही धन्य है वह मनुष्य जो दुष्टों की योजना पर नहीं चलता।"</em></p>'),
            ("<p>एक ही जाति के पक्षी एक",
             "<p><em>न पापियों के मार्ग में खड़ा होता।</em></p>"),
            ("<p>ठट्ठा करनेवालों का आसन",
             '<p><em>"और न ठट्ठा करनेवालों के आसन पर बैठता है।"</em></p>'),
            ("<p>हमने उन बातों पर विचार", "<h3>आशीष की सकारात्मक शर्तें।</h3>"),
            ("<p>अब हम इस भजन के तीसरे पद", "<h3>आशीष का परिणाम।</h3>"),
            ("<p>इस विरोधाभास पर अधिक विस्तार", "<h3>विरोधाभास।</h3>"),
            ("<p>इस विरोधाभास पर अधिक विस्तार",
             '<p><em>"दुष्ट लोग ऐसे नहीं होते।"</em></p>'),
        ],
    },
    "a-full-reward": {
        "restored_blocks": [
            # en
            ("<p>In this interesting narrative",
             '<blockquote><em>"It hath fully been shewed me, all that thou hast done ... and how thou hast left they father and thy mother, and the land of thy nativity, and art come unto a people which thou knewest not heretofore. The LORD recompense thy work, and a full reward be given thee of the LORD GOD of Israel, under whose wings thou art come to trust" (Ruth ii. 11, 12).</em></blockquote>'),
            # fr
            ("<p>Dans ce récit plein d’intérêt,",
             "<blockquote><em>« On m’a rapporté tout ce que tu as fait ... et comment tu as quitté ton père et ta mère et le pays de ta naissance, pour aller vers un peuple que tu ne connaissais point auparavant. Que l’Éternel te rende ce que tu as fait, et que ta récompense soit entière de la part de l’Éternel, le Dieu d’Israël, sous les ailes duquel tu es venue te réfugier » (Ruth 2:11, 12).</em></blockquote>"),
            # hi
            ("<p>इस रोचक वृत्तान्त में हमें",
             '<blockquote><em>"जो कुछ तूने ... किया है, और तू किस प्रकार अपने माता पिता और जन्म-भूमि को छोड़कर ऐसे लोगों में आई है जिनको पहले तू न जानती थी, यह सब मुझे विस्तार के साथ बताया गया है। यहोवा तेरी करनी का फल दे, और इस्राएल का परमेश्वर यहोवा जिसके पंखों के तले तू शरण लेने आई है, तुझे पूरा प्रतिफल दे" (रूत 2:11, 12)।</em></blockquote>'),
        ],
    },
    "self-denial-versus-self-assertion": {
        "restored_blocks": [
            # en
            ("<p>We might naturally have",
             '<blockquote><em>"If any man will come after Me, let him deny himself, and take up his cross daily, and follow Me.</em>--LUKE ix. 23.</blockquote>'),
        ],
    },
    "all-sufficiency": {
        "restored_blocks": [
            # en
            ("<p>How pleasant to the heart",
             '<blockquote><em>"The LORD GOD is a Sun and Shield:<br/> the LORD will give grace and glory:<br/> "No good thing will He withhold from them<br/> that walk uprightly."<br/></em>--PSALM LXXXIV. 11.</blockquote>'),
        ],
    },
    "under-the-shepherds-care": {
        "restored_blocks": [
            # en
            ('<blockquote>"For ye were as', "<h3>A NEW YEAR'S ADDRESS.</h3>"),
        ],
    },
    # --- Gutenberg #65066, "The Life and Diary of David Brainerd" ------------
    # The same kind of loss in a BOOK. Every chapter heading of this edition
    # sits in its own `<div class="chapter">`, so `import_gutenberg.
    # split_by_heading` fell back to its tree walk, and that walk dropped every
    # div that was not hand-made poem markup. What the edition sets in divs is
    # exactly what went: the date range centred under each chapter heading
    # ("April 20, 1718-Feb. 1741."), the datelines heading each letter-journal
    # section ("Forks of Delaware, Oct. 1745."), chapter X's subtitle, and four
    # verse passages set as ebookmaker `lg-container` line groups — two of
    # which the prose around them introduces ("Those lines turned in my mind
    # with pleasure," / "Dr. Watts' Psalm,") and then never shows.
    #
    # The importer keeps these now (`ingest.display_line`, and a line group
    # becomes one `<blockquote>` with `<br/>` between its lines), and every
    # English block below is spelled EXACTLY as `extract_chapters` emits it —
    # pinned by `tests_import.BrainerdRestoredBlocksMatchImporterTests` — so a
    # re-import finds each present and the guard skips it. The stray “ opening
    # the June 17 dateline is the edition's own. In ch9 two lines precede the
    # same paragraph; `restore_dropped_blocks` inserts each directly before
    # the anchor, so list order is reading order.
    #
    # NOT restored: the preface's signature `<h3>JONATHAN EDWARDS.</h3>`. It
    # is the last block of ch1, so there is no following block to anchor on,
    # and this mechanism only inserts in front of one. Nor the front and back
    # matter the importer now also emits (the "LIFE / OF / REV. DAVID
    # BRAINERD." half-title, the donors' imprint, the transcriber's note).
    #
    # The Swahili edition runs in lockstep with the English (same tags, same
    # indices in every chapter), so each line goes in at the same position,
    # anchored on that edition's own following paragraph. Months and places
    # are spelled as its body already spells them (Okt., Februari, Machi;
    # "Forks of Delaware, huko Pennsylvania"; its own surviving dateline
    # "Crossweeksung, (New-Jersey,) Agosti, 1745."); chapter X's subtitle
    # follows its REFLECTION IV ("kumbukumbu zilizotangulia"), the death verse
    # its own lead-in ("mauti na kutokufa"), and the Watts line Psalm 127:1 as
    # the Swahili Bible has it ("kuijenga nyumba"). No quote or translation
    # note in this book is anchored by block position.
    "life-and-diary-of-david-brainerd": {
        "restored_blocks": [
            # en
            ("<p>David Brainerd was born April", "<p>April 20, 1718-Feb. 1741.</p>"),
            ("<p>In the spring of 1742 Brainerd", "<p>April 1, 1742-July 29, 1742.</p>"),
            ("<p>“The Lord refreshed my soul",
             "<blockquote>“Farewell, vain world; my soul can bid Adieu<br/>“My Savior taught me to abandon you.<br/>“Your charms may gratify a SENSUAL mind;<br/>“But cannot please a soul for God design’d.<br/>“Forbear t’ entice; cease then my soul to call;<br/>“’Tis fixed through grace; my God shall be my ALL.<br/>“While he thus lets me heavenly glories view,<br/>“Your beauties fade, my heart’s no room for you.”</blockquote>"),
            ("<p><i>April 27.</i> “I arose",
             "<blockquote>“Lord, I’m a stranger here alone;<br/>“Earth no true comforts can afford;<br/>“Yet, absent from my dearest one,<br/>“My soul delights to cry ‘My Lord!’<br/>“Jesus, my Lord, my only love,<br/>“Possess my soul, nor thence depart:<br/>“Grant me kind visits, heavenly Dove;<br/>“My God shall then have all my heart.”</blockquote>"),
            ("<p><i>July 30, 1742.</i>—“Rode", "<p>July 30.-Nov. 25, 1742.</p>"),
            ("<p><i>Nov. 26, 1742.</i>—“Had", "<p>Nov. 26, 1742.—March 31, 1743.</p>"),
            ("<p><i>April 1, 1743.</i> “I rode", "<p>April 1, 1743.—June 12, 1744.</p>"),
            ("<p>“In evening prayer, God was",
             "<blockquote>“Come death, shake hands; I’ll kiss thy bands;<br/>“’Tis happiness for me to die.—<br/>“What!—dost thou think that I will shrink?<br/>“I’ll go to immortality.”</blockquote>"),
            ("<p><i>June 13, 1744.</i> [At Elizabeth", "<p>June 13, 1744.—June 18, 1745.</p>"),
            ("<p>[We are now come to that part", "<p>June 19.—Nov. 5, 1745.</p>"),
            ("<p><i>June 19.</i>—“I had spent",
             "<p>“<i>Crossweeksung, in New-Jersey, June 17, 1745.</i></p>"),
            ("<p><i>Lord’s day, July 14.</i>—“Discoursed",
             "<p><i>Forks of Delaware, in Pennsylvania, July, 1745.</i></p>"),
            ("<p><i>Lord’s day, Sept. 1.</i>—“Preached",
             "<p><i>Forks of Delaware, in Pennsylvania, Sept. 1745.</i></p>"),
            ("<p><i>Sept. 13.</i>—“After having", "<p><i>Shaumoking, Sept. 1745.</i></p>"),
            ("<p><i>Sept. 19.</i>—“Visited an", "<p><i>Juncauta, Sept. 1745.</i></p>"),
            ("<p><i>Oct. 1.</i>—“Discoursed", "<p><i>Forks of Delaware, Oct. 1745.</i></p>"),
            ("<p><i>Oct. 5.</i>—“Preached", "<p><i>Crossweeksung, Oct. 1745.</i></p>"),
            ("<p><i>Lord’s day, Nov. 24.</i>—“Preached", "<p>Nov. 5, 1745.—June 19, 1746.</p>"),
            ("<p><i>Lord’s day, Nov. 24.</i>—“Preached",
             "<p><i>Crossweeksung, New-Jersey, 1745.</i></p>"),
            ("<p><i>Lord’s day, Feb. 16.</i>—“Knowing",
             "<p><i>Forks of Delaware, February, 1746.</i></p>"),
            ("<p><i>March 1.</i>—“Catechised", "<p><i>Crossweeksung, March, 1746.</i></p>"),
            ("<p>and having recommended them",
             "<blockquote>If God to build the house deny &amp;c.</blockquote>"),
            ("<p><i>Lord’s day, June 29, 1746.</i>", "<p>[June 19, 1746—October 9, 1747.]</p>"),
            ("<p>In the life of Brainerd we may see",
             "<p><i>Reflections on the preceding Memoirs.</i></p>"),
            # sw
            ("<p>David Brainerd alizaliwa Aprili", "<p>Aprili 20, 1718-Feb. 1741.</p>"),
            ("<p>Katika masika ya mwaka 1742", "<p>Aprili 1, 1742-Julai 29, 1742.</p>"),
            ("<p>“Bwana aliiburudisha nafsi yangu",
             "<blockquote>“Kwaheri, ulimwengu wa ubatili; nafsi yangu yaweza kukuaga<br/>“Mwokozi wangu alinifundisha kukuacha.<br/>“Mvuto wako waweza kuiridhisha nia ya KIMWILI;<br/>“Lakini hauwezi kuipendeza nafsi iliyokusudiwa kwa Mungu.<br/>“Acha kunishawishi; basi, koma kuiita nafsi yangu;<br/>“Imethibitika kwa neema; Mungu wangu atakuwa YOTE kwangu.<br/>“Maadamu ananijalia hivi kuutazama utukufu wa mbinguni,<br/>“Uzuri wako wafifia, moyo wangu hauna nafasi kwako.”</blockquote>"),
            ("<p><i>Aprili 27.</i> “Niliamka",
             "<blockquote>“Bwana, mimi ni mgeni hapa peke yangu;<br/>“Dunia haiwezi kutoa faraja ya kweli;<br/>“Lakini, nikiwa mbali na mpenzi wangu mkuu,<br/>“Nafsi yangu hufurahi kulia ‘Bwana wangu!’<br/>“Yesu, Bwana wangu, pendo langu pekee,<br/>“Uimiliki nafsi yangu, wala usiondoke humo:<br/>“Unijalie ziara za upole, Hua wa mbinguni;<br/>“Ndipo Mungu wangu atakapokuwa na moyo wangu wote.”</blockquote>"),
            ("<p><i>Julai 30, 1742.</i>—“Nilikwenda", "<p>Julai 30.-Nov. 25, 1742.</p>"),
            ("<p><i>Novemba 26, 1742.</i>—“Bado", "<p>Nov. 26, 1742.—Machi 31, 1743.</p>"),
            ("<p><i>Aprili 1, 1743.</i> “Nilipanda", "<p>Aprili 1, 1743.—Juni 12, 1744.</p>"),
            ("<p>“Katika maombi ya jioni, Mungu",
             "<blockquote>“Njoo, mauti, tushikane mikono; nitabusu vifungo vyako;<br/>“Ni furaha kwangu kufa.—<br/>“Nini!—wadhani kwamba nitarudi nyuma?<br/>“Nitakwenda kwenye kutokufa.”</blockquote>"),
            ("<p><i>Juni 13, 1744.</i> [Huko Elizabeth", "<p>Juni 13, 1744.—Juni 18, 1745.</p>"),
            ("<p>[Sasa tumefika sehemu ile", "<p>Juni 19.—Nov. 5, 1745.</p>"),
            ("<p><i>Juni 19.</i>—“Nimetumia",
             "<p>“<i>Crossweeksung, huko New-Jersey, Juni 17, 1745.</i></p>"),
            ("<p><i>Siku ya Bwana, Julai 14.</i>—“Niliwazungumzia",
             "<p><i>Forks of Delaware, huko Pennsylvania, Julai, 1745.</i></p>"),
            ("<p><i>Siku ya Bwana, Sept. 1.</i>—“Niliwahubiria",
             "<p><i>Forks of Delaware, huko Pennsylvania, Sept. 1745.</i></p>"),
            ("<p><i>Sept. 13.</i>—“Baada ya", "<p><i>Shaumoking, Sept. 1745.</i></p>"),
            ("<p><i>Sept. 19.</i>—“Nilitembelea", "<p><i>Juncauta, Sept. 1745.</i></p>"),
            ("<p><i>Okt. 1.</i>—“Niliwazungumzia", "<p><i>Forks of Delaware, Okt. 1745.</i></p>"),
            ("<p><i>Okt. 5.</i>—“Niliwahubiria", "<p><i>Crossweeksung, Okt. 1745.</i></p>"),
            ("<p><i>Siku ya Bwana, Nov. 24.</i>—“Nilihubiri", "<p>Nov. 5, 1745.—Juni 19, 1746.</p>"),
            ("<p><i>Siku ya Bwana, Nov. 24.</i>—“Nilihubiri",
             "<p><i>Crossweeksung, New-Jersey, 1745.</i></p>"),
            ("<p><i>Siku ya Bwana, Feb. 16.</i>—“Kwa kujua",
             "<p><i>Forks of Delaware, Februari, 1746.</i></p>"),
            ("<p><i>Machi 1.</i>—“Nilifundisha", "<p><i>Crossweeksung, Machi, 1746.</i></p>"),
            ("<p>na baada ya kuwakabidhi wao",
             "<blockquote>Mungu akikataa kuijenga nyumba n.k.</blockquote>"),
            ("<p><i>Siku ya Bwana, Juni 29, 1746.</i>", "<p>[Juni 19, 1746—Oktoba 9, 1747.]</p>"),
            ("<p>Katika maisha ya Brainerd twaweza",
             "<p><i>Tafakari juu ya Kumbukumbu Zilizotangulia.</i></p>"),
        ],
    },
    # Gutenberg #57109 (Hudson Taylor, *Unfailing Springs*) sets the address's
    # text as a centred display line directly under its <h2> —
    # `<div class="center">"Whosoever will, let him take the water of life
    # freely"<br> (Rev. 22:17)</div>` — and the importer dropped it for the
    # same reason as "The rest of Gutenberg #23438" above. The English block is
    # spelled exactly as `ingest.display_line` now emits it. Each
    # translation takes its registry Bible's wording of the clause (Arabic
    # without the Van Dyck vowel marks, as this edition quotes John 4:10; the
    # Luganda apostrophe straight, as this edition writes it), its own quotation
    # marks and its corpus's name for the book. `quote_seed` anchors and the uk
    # translation notes' `block_index` values below it shifted by one.
    "unfailing-springs": {
        "restored_blocks": [
            # en
            ("<p>THE best evidence of Christianity",
             '<p>"Whosoever will, let him take the water of life freely"<br/> (Rev. 22:17)</p>'),
            # ar
            ("<p>إنّ خير برهان على المسيحية",
             "<p>«من يرد فليأخذ ماء حياة مجانًا»<br/> (رؤيا 22:17)</p>"),
            # es
            ("<p>La mejor evidencia del cristianismo",
             "<p>«El que quiere, tome del agua de la vida de balde»<br/> (Apocalipsis 22:17)</p>"),
            # fr
            ("<p>LA meilleure preuve du christianisme",
             "<p>« Que celui qui veut, prenne de l’eau de la vie, gratuitement »<br/> (Apocalypse 22:17)</p>"),
            # hi
            ("<p>मसीही विश्वास का सबसे उत्तम प्रमाण",
             '<p>"जो कोई चाहे वह जीवन का जल सेंत-मेंत ले"<br/> (प्रकाशितवाक्य 22:17)</p>'),
            # lg
            ("<p>Obujulizi obusinga obulungi",
             "<p>\"Buli ayagala ajje anywe ku mazzi ag'obulamu ag'obuwa\"<br/> (Okubikkulirwa 22:17)</p>"),
            # pt
            ("<p>A MELHOR evidência do cristianismo",
             '<p>"Quem quiser beba de graça da água da vida"<br/> (Apocalipse 22:17)</p>'),
            # sw
            ("<p>Ushahidi bora wa Ukristo",
             '<p>"Kila anayetaka na anywe maji ya uzima bure"<br/> (Ufunuo 22:17)</p>'),
            # uk
            ("<p>Найкращий доказ християнства",
             "<p>«Хто хоче, нехай приймає воду життя дармо»<br/> (Одкриттє 22:17)</p>"),
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
        #
        # The four after it are a DIFFERENT shape of the dropped-anchor defect,
        # and the most damaging one in the corpus: this transcriber wraps each
        # word he corrected in an internal link, so `[class*=pginternal]` did
        # not delete a reference — it deleted a word out of Müller's sentence,
        # leaving "Even about the of this century". Restored from the source's
        # own correction, which names the word it is supplying. The selector is
        # qualified now (#1573); these are the rows already on the shelf.
        "replacements": [
            ("<h3>A NEW VICTORY OF FAITH.</h3>", ""),
            (" of the Lord Jesus. Even about the of this century",
             " of the Lord Jesus. Even about the commencement of this century"),
            ("large piece of ground in the of Bristol",
             "large piece of ground in the neighborhood of Bristol"),
            ("Again, four from among the -school children",
             "Again, four from among the Sunday-school children"),
            ("if one is enabled to God\u2019s own time",
             "if one is enabled to wait God\u2019s own time"),
        ],
    },
    "things-as-they-are": {
        # The dropped-anchor defect: Gutenberg spells a cross-reference as an
        # internal link, and `[class*=pginternal]` decomposed it whole instead
        # of unwrapping it, so the reference vanished and only the punctuation
        # around it survived. The selector is qualified now
        # (`sanitize.KEEP_PREDICATES`, #1573) — this is the row already on the
        # shelf, which is never re-imported. Each target was read off the
        # Gutenberg source, not inferred from position.
        #
        # Three chapter cross-references in Carmichael's picture captions and
        # asides — "one of the old dames seen in ." for "seen in chapter vi."
        "replacements": [
            ("one of the old dames seen in . A capital typical face",
             "one of the old dames seen in chapter vi. A capital typical face"),
            ('stuff on the stone is the "Imp" of . <p>Then a Caste meeting',
             'stuff on the stone is the "Imp" of chapter xx. <p>Then a Caste meeting'),
            ('the "rabbits" mentioned in . She saw us',
             'the "rabbits" mentioned in Chapter I. She saw us'),
        ],
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
            # ar ch6 rendered Rev. 22:17 itself; take the registry Bible's
            # (Van Dyck) wording, as `unfailing-springs` does, so the language
            # quotes the verse one way (`tests_verse_consistency`).
            ("مَن يشأ فليأخذ من ماء الحياة مجانًا", "من يرد فليأخذ ماء حياة مجانًا"),
        ],
    },
    "the-bruised-reed": {
        # Pickering's 1838 printing sets every chapter's opening letter as a
        # decorative IMAGE cap, so the text layer starts one letter short: "HE
        # prophet Isaiah" for "THE prophet Isaiah". Three caps mis-scanned into
        # junk rather than vanishing (ch5's F as "T,.", ch17's E as "*", ch27's
        # O simply lost), which is a wrong string to replace, not a letter to
        # prepend.
        #
        # NOT `dropcap_letters`, the natural-looking channel, which does not
        # work here: it only fires while the body still opens LOWERCASE, and
        # Sibbes opens every chapter on a small-caps run ("HIS bruising…"), so
        # it never fired on the plain cases — and on the ten below it fired on
        # the leaked tail instead, putting the letter in the wrong place
        # ("Tand what the bruising. HE prophet").
        #
        # Those ten are the second defect, folded into the same pair: this
        # edition prints a two- or three-line summary under each chapter marker,
        # the importer takes the first line as the title, and the remainder
        # stays as the body's opening words. Same shape as `on-loving-god`'s
        # wrapped ALL-CAPS headings.
        #
        # Each pair carries ~34 characters of the following sentence, and every
        # one was checked to occur exactly once in its own chapter and nowhere
        # else in the book — a bare "<p>HE" would fire on any paragraph opening
        # "HE", and four chapters share that opening.
        "replacements": [
            ('<p>and what the bruising.</p><p>HE prophet Isaiah being lifted up, a',
             '<p>THE prophet Isaiah being lifted up, a'),  # ch1
            ('<p>HIS bruising is required before conve',
             '<p>THIS bruising is required before conve'),  # ch2
            ('<p>HE second point is, That Christ will',
             '<p>THE second point is, That Christ will'),  # ch3
            ('<p>bruising : and comfort to such.</p><p>UT how shall we know, whether we are',
             '<p>BUT how shall we know, whether we are'),  # ch4
            ('<p>T,.OR the second branch; God will not q',
             '<p>FOR the second branch; God will not q'),  # ch5
            ('<p>UT grace is not only little, but min',
             '<p>BUT grace is not only little, but min'),  # ch6
            ('<p>OW for the second observation, Chris',
             '<p>NOW for the second observation, Chris'),  # ch7
            ('<p>beginners.</p><p>IVINES had need to take heed therefore h',
             '<p>DIVINES had need to take heed therefore h'),  # ch8
            ('<p>also private Christians.</p><p>O in the censures of the church, it',
             '<p>SO in the censures of the church, it'),  # ch9
            ('<p>will not quench.</p><p>OR trial, to let us see whether we b',
             '<p>FOR trial, to let us see whether we b'),  # ch10
            ('<p>quench, HESE things premised, let us know for ',
             '<p>THESE things premised, let us know for '),  # ch11
            ('<p>ROM the meditation of these rules and',
             '<p>FROM the meditation of these rules and'),  # ch12
            ('<p>ERE is a use of encouragement to duty',
             '<p>HERE is a use of encouragement to duty'),  # ch13
            ('<p>Discouragements.</p><p>ROM what hath been spoken, with some ',
             '<p>FROM what hath been spoken, with some '),  # ch14
            ('<p>whom they are. And how to recover Peace lost.</p><p>ND among other causes of discouragem',
             '<p>AND among other causes of discouragem'),  # ch15
            ('<p>Christ unto us.</p><p>INCE Christ is thus comfortably set ou',
             '<p>SINCE Christ is thus comfortably set ou'),  # ch16
            ('<p>What it is.</p><p>W* come to the third part, the const',
             '<p>WE come to the third part, the const'),  # ch17
            ('<p>enjoy the comfort of his mildness.</p><p>HE first conclusion from the connexi',
             '<p>THE first conclusion from the connexi'),  # ch18
            ('<p>Judgment and wisdom.</p><p>HE second conclusion is, that Christ',
             '<p>THE second conclusion is, that Christ'),  # ch19
            ('<p>sets up has government.</p><p>HE second branch is, that wheresoeve',
             '<p>THE second branch is, that wheresoeve'),  # ch20
            ('<p>HE third conclusion is, that this go',
             '<p>THE third conclusion is, that this go'),  # ch21
            ('<p>OR the second, that is, directions.<',
             '<p>FOR the second, that is, directions.<'),  # ch22
            ('<p>F Christ will have the victory, the',
             '<p>IF Christ will have the victory, the'),  # ch23
            ('<p>T is not only said, judgment shall ',
             '<p>IT is not only said, judgment shall '),  # ch24
            ('<p>HE fifth conclusion is, that this go',
             '<p>THE fifth conclusion is, that this go'),  # ch25
            ('<p>HE sixth conclusion is, that this pr',
             '<p>THE sixth conclusion is, that this pr'),  # ch26
            ('<p>of prevailing.</p><p>FR conclusion and general applicatio',
             '<p>FOR conclusion and general applicatio'),  # ch27
            # --- OCR slips, each verified in context against the scan. One
            # class dominates: a stray letter glued to the front of a word
            # ("ithis", "ifallen", "ifmen"), which is this scanner reading the
            # previous word's terminal stroke into the next. Literal pairs, never
            # a regex — "i" opens real words too.
            ('Iam black, saith the church',
             'I am black, saith the church'),  # ch10
            ('at Wariance and odds',
             'at variance and odds'),  # ch12
            ('look upon ithis text',
             'look upon this text'),  # ch12
            ('oppose ais nature and office',
             'oppose his nature and office'),  # ch16
            ('he cannot deny himelf',
             'he cannot deny himself'),  # ch16
            ('his Father hath aidupon him',
             'his Father hath laid upon him'),  # ch16
            ('Those therefore ithat are enemies',
             'Those therefore that are enemies'),  # ch19
            ('Satan and antiwchrist',
             'Satan and antichrist'),  # ch19
            ('we keep fire ifrom powder',
             'we keep fire from powder'),  # ch22
            ('And being ifallen, in our raisings',
             'And being fallen, in our raisings'),  # ch25
            ('Christ that must ydo the',
             'Christ that must do the'),  # ch25
            ('further degree ithan we had',
             'further degree than we had'),  # ch25
            ('when we are ifallen, and by falls',
             'when we are fallen, and by falls'),  # ch25
            ('Rey. xix.1',
             'Rev. xix. 1'),  # ch27
            ('God will notalways suffer',
             'God will not always suffer'),  # ch27
            ('religion \\on the latter-spring',
             'religion in the latter-spring'),  # the backslash ate the "i" of
            # "in" — Grosart reads "reformation of religion IN the
            # latter-spring", so stripping the mark and keeping "on" would have
            # shipped a wrong preposition.
            ('gospel, ifmen had not been',
             'gospel, if men had not been'),  # ch27
            ('of all tha hath been',
             'of all that hath been'),  # ch27
            # ch17's summary heading wraps mid-WORD ("merciful dispo-" /
            # "sition in Christ"), so its tail leaks as the body's opening and
            # the drop cap follows it. Same shape as the ten above.
            ('<p>sition in Christ. Of quenching the Spirit.</p><p>E are now to take notice',
             '<p>WE are now to take notice'),
            # A stray rule-mark the scanner kept mid-sentence, the same class as
            # the one before "CHAP. XXVI." in the source.
            ('divers sorts of men \\ that offend', 'divers sorts of men that offend'),
            # --- the lost left edge of page 75 (and two strays elsewhere).
            # The scan clipped the first character or two off eight consecutive
            # lines, and the remnants are real-looking words ("ut then", "a
            # sceptre f mercy", "hen we think"), which is why the English audit
            # calls the chapter clean. Most restore themselves from English, but
            # "his * ae is then to present" does not — GROSART settles it as
            # "his manner", and the same witness confirms "father, brother,
            # head, all is", "the Evangelist", "she would not be cured",
            # "Here we know where" and Isaiah's "Destroy it not". The critical
            # edition is unusable as a READING text and is still the right thing
            # to collate a doubtful word against.
            ('one saith, Destroy ut not',
             'one saith, Destroy it not'),  # ch7
            ('his * ae is then to present',
             'his manner is then to present'),  # ch16
            ('against us : ut then let us',
             'against us : but then let us'),  # ch16
            ('holding out a sceptre f mercy',
             'holding out a sceptre of mercy'),  # ch16
            ('arms to receive us. hen we think',
             'arms to receive us. When we think'),  # ch16
            ('John the Evangeist',
             'John the Evangelist'),  # ch16
            ('with delight, as f mild and sweet',
             'with delight, as of mild and sweet'),  # ch16
            ('when we think f Christ, we shou!d',
             'when we think of Christ, we should'),  # ch16
            ('all meekness. Ifthe sweetness',
             'all meekness. If the sweetness'),  # ch16
            ('in husband, Sather, brother, head, allis but a beam',
             'in husband, father, brother, head, all is but a beam'),  # ch16
            ('weak, but we.are his',
             'weak, but we are his'),  # ch16
            ('Babylon, and she ould not be cured',
             'Babylon, and she would not be cured'),  # ch16
            ('as it were in hell. ere we know where',
             'as it were in hell. Here we know where'),  # ch25
            # --- the last of the scan junk, every reading settled against
            # Grosart: a stray backslash rule-mark eating a letter ("\\whey" for
            # "they", "king\\doms"), and a guillemet standing where a letter was
            # lost ("»emptation", "em»raced", "thi»"). The guillemets matter
            # twice over: `QuoteStyleTests` counts « » as CURLY, so they pass
            # the quote gate while leaving a French quotation mark mid-sentence.
            ('forsake thee, \\I will not',
             'forsake thee, I will not'),  # ch2
            ('make the bruise \\the more painful',
             'make the bruise the more painful'),  # ch4
            ('In time of »emptation rather believe',
             'In time of temptation rather believe'),  # ch15
            ('as freely as we em»raced it before',
             'as freely as we embraced it before'),  # ch20
            ('we have just cause \\to be humbled',
             'we have just cause to be humbled'),  # ch23
            ('when the king\\doms of the earth',
             'when the kingdoms of the earth'),  # ch25
            ('disguised ; »goodness shall appear',
             'disguised ; goodness shall appear'),  # ch25
            ('to the darkness of »ur own heart',
             'to the darkness of our own heart'),  # ch26
            ('counteth it a generous thi» not to be awed',
             'counteth it a generous thing not to be awed'),  # ch27
            ('God’s time may »roceed yet further west',
             'God’s time may proceed yet further west'),  # ch28
            ('until Christ hath »rought all under one head',
             'until Christ hath brought all under one head'),  # ch28
            ('my will is that \\whey be where I am',
             'my will is that they be where I am'),  # ch28
            ('and against that \\which is ill',
             'and against that which is ill'),  # ch28
            ('carried matters often \\inconsiderately',
             'carried matters often inconsiderately'),  # ch28
            ('What had oecome of that great work',
             'What had become of that great work'),  # ch28
            ('outstride all lets, apon this faith',
             'outstride all lets, upon this faith'),  # ch28
            ('was Christ’s, and that the would not be wanting',
             'was Christ’s, and that he would not be wanting'),  # ch28
            # --- the OCR pass, settled by ALIGNMENT against Grosart.
            # Grosart's 1862 edition is a different printing of the same work,
            # so aligning the two word-by-word says what a damaged token should
            # read without anyone inventing it — which is how `adeidiney` is
            # known to be "authority" and `poate` to be "working". Every pair
            # carries enough of the preceding sentence to occur exactly once in
            # the book.
            #
            # The alignment also surfaces differences that are NOT damage, and
            # those are rejected: Pickering writes `Isai.` where Grosart writes
            # `Isa.`, `burthen` for `burden`, `mayst` for `mayest`, and
            # `dependance`/`dependant` (both twice in the scan, so its own
            # spelling). Grosart is sometimes the damaged one — it reads
            # `beliovest` where Pickering is right — so the witness is consulted,
            # not obeyed.
            #
            # A soft hyphen the scan read as `‘` at a line start ("con-" /
            # "‘ceits") needs no pair: `import_archive` drops the mark and the
            # hyphen-join closes the word. The same goes for the bare strays
            # earlier pairs here spelled with their mark.
            ('so that both these together, @',
             'so that both these together, a'),  # ch1
            ('of those that have obtained merey,',
             'of those that have obtained mercy,'),  # ch1
            ('his blood: so he is @',
             'his blood: so he is a'),  # ch3
            ('only our friend, but our brothey',
             'only our friend, but our brother'),  # ch3
            ('the word of God, Isa. |xvi.',
             'the word of God, Isa. lxvi.'),  # ch4
            ('violence against it: else favouring oursevles,',
             'violence against it: else favouring ourselves,'),  # ch4
            # The scan lost a whole LINE here ("take off ourselves too soon, nor
            # pull off the plaster be-"), so repairing the one garbled word
            # left a verbless sentence that looked fixed. Grosart supplies it.
            ('not fore the cure be erowiglt',
             'not take off ourselves too soon, nor pull off the plaster before '
             'the cure be wrought,'),  # ch4
            ('muzzle the mouth of the oa,',
             'muzzle the mouth of the ox,'),  # ch4
            ('careful was he that Peter vand',
             'careful was he that Peter and'),  # ch4
            ('former; yet more glorious than ithe',
             'former; yet more glorious than the'),  # ch5
            ('into it. The Lord of ithe',
             'into it. The Lord of the'),  # ch5
            ('own temple. The pupil of ithe',
             'own temple. The pupil of the'),  # ch5
            ('Christ to perfume them, and s0',
             'Christ to perfume them, and so'),  # ch6
            ('we perish? Mat. viii. 25, ery',
             'we perish? Mat. viii. 25, cry'),  # ch6
            ('with an issue did but towch,',
             'with an issue did but touch,'),  # ch7
            ('being an advantage to poverty ef',
             'being an advantage to poverty of'),  # ch7
            ('This example doth not countenance lwkewarmness,',
             'This example doth not countenance lukewarmness,'),  # ch8
            ('mingle bitterness and passion with adeidiney',
             'mingle bitterness and passion with authority'),  # ch9
            ('miserable persons, if humbled, is cbecnly',
             'miserable persons, if humbled, is unseemly'),  # ch9
            ('be called a, son, Luke xy.',
             'be called a, son, Luke xv.'),  # ch10
            ('in the soul is because, towether',
             'in the soul is because, together'),  # ch11
            ('speaks of, All you that hindle',
             'speaks of, All you that kindle'),  # ch11
            ('light, the candle of the wiched',
             'light, the candle of the wicked'),  # ch11
            ('intendment to kill Nabal, and dlesseth',
             'intendment to kill Nabal, and blessed'),  # ch11
            ('no grace, but they contradict themselyes',
             'no grace, but they contradict themselves'),  # ch11
            ('desires springing from faith and loye,',
             'desires springing from faith and love,'),  # ch11
            ('I were more free from ithese',
             'I were more free from these'),  # ch11
            ('walking with God, and to "aise',
             'walking with God, and to raise'),  # ch12
            ('when men give themselves to carna!',
             'when men give themselves to carnal'),  # ch12
            ('comfortable in the evidence. It 48',
             'comfortable in the evidence. It is'),  # ch12
            ('offend us now, than by igiving',
             'offend us now, than by giving'),  # ch12
            ('shed, lost. And as every gravc',
             'shed, lost. And as every grace'),  # ch13
            ('thee so are they the erief',
             'thee so are they the grief'),  # ch13
            ('make way to shew his oftice',
             'make way to shew his office'),  # ch14
            ('give a sharp sentence against themselyes,',
             'give a sharp sentence against themselves,'),  # ch15
            ('not make use of so zracious',
             'not make use of so gracious'),  # ch15
            ('way for acting his own gart',
             'way for acting his own part'),  # ch16
            ('seasonable time ; he cannot nold',
             'seasonable time ; he cannot hold'),  # ch16
            ('he answers the woman of Janaan,',
             'he answers the woman of Canaan'),  # ch16
            ('a word; 2. Then gives ner',
             'a word; 2. Then gives her'),  # ch16
            ('an answer tending to her resroach,',
             'an answer tending to her reproach,'),  # ch16
            ('favour to comfort him; so Jhrist',
             'favour to comfort him; so Christ'),  # ch16
            ('power to uphold us, than vhen',
             'power to uphold us, than when'),  # ch16
            ('heart carry in them some eport,',
             'heart carry in them some report,'),  # ch16
            ('but a reflection of his ove',
             'but a reflection of his love'),  # ch16
            ('As Christ did in his eximple',
             'As Christ did in his example'),  # ch16
            ('whatsoever he calleth us to vuffer,',
             'whatsoever he calleth us to suffer,'),  # ch16
            ('better learn to relieve and sity',
             'better learn to relieve and pity'),  # ch16
            ('In his desertion in the sarden,',
             'In his desertion in the garden,'),  # ch16
            ('the presence of his Father, oth',
             'the presence of his Father, both'),  # ch16
            ('for a time for us, nd',
             'for a time for us, and'),  # ch16
            ('seeth it fit we should aste',
             'seeth it fit we should taste'),  # ch16
            ('Son drank so deep, that ve',
             'Son drank so deep, that we'),  # ch16
            ('is, that Christ drank the lregs',
             'is, that Christ drank the dregs'),  # ch16
            ('that little taste of his disHeasure',
             'that little taste of his displeasure'),  # ch16
            ('sorrows for us; he was woken,',
             'sorrows for us; he was broken,'),  # ch16
            ('conceit, that his master was @',
             'conceit, that his master was a'),  # ch17
            ('their own, that C will suifer',
             'their own, that Christ will suffer'),  # ch17
            ('Lamb can be angry, and ney',
             'Lamb can be angry, and they'),  # ch17
            ('out her hand and men efuse,',
             'out her hand and men refuse,'),  # ch17
            ('made men shall have no nercy',
             'made men shall have no mercy'),  # ch17
            ('what love and mercy hath heen',
             'what love and mercy hath been'),  # ch17
            ('suffering our spirits to be opypressed',
             'suffering our spirits to be oppressed'),  # ch17
            ('as first, holy communion, whereby sone',
             'as first, holy communion, whereby one'),  # ch17
            ('argument to enforce a sacrificing oursselyes',
             'argument to enforce a sacrificing ourselves'),  # ch17
            ('as if he should say, vunless',
             'as if he should say, Unless'),  # ch17
            ('our faith to ourselves, Rom. xiy.',
             'our faith to ourselves, Rom. xiv.'),  # ch17
            ('then especially when it is wheré',
             'then especially when it is where'),  # ch17
            ('spiritual misery of others: join isuch',
             'spiritual misery of others: join such'),  # ch17
            ('Saviour, who counteth the love vand',
             'Saviour, who counteth the love and'),  # ch17
            ('government and ordinances, that are vadshamed',
             'government and ordinances, that are ashamed'),  # ch17
            ('of the gospel, that count jpreaching',
             'of the gospel, that count preaching'),  # ch17
            ('whereby they may give the ibetter',
             'whereby they may give the better'),  # ch17
            ('is so gentle and tender vover.',
             'is so gentle and tender over.'),  # ch19
            ('Christ died and rose again vand',
             'Christ died and rose again and'),  # ch19
            ('Lord of the dead and iliving,',
             'Lord of the dead and living,'),  # ch19
            ('to enjoy any liberty of ithe',
             'to enjoy any liberty of the'),  # ch19
            ('Christ as he ruleth us, 80',
             'Christ as he ruleth us, so'),  # ch19
            ('likewise from an inward principle vand',
             'likewise from an inward principle and'),  # ch19
            ('whence those reasons have their wchief',
             'whence those reasons have their chief'),  # ch19
            ('are made partakers of the idivine',
             'are made partakers of the divine'),  # ch19
            ('of darkness, and ruleth in darkmess',
             'of darkness, and ruleth in darkness'),  # ch20
            ('to preserve the manner of poate',
             'to preserve the manner of working'),  # ch20
            ('think that Satan had no nand',
             'think that Satan had no hand'),  # ch20
            ('he findeth in us. But Shere',
             'he findeth in us. But there'),  # ch20
            ('our nature to incline in genewal',
             'our nature to incline in general'),  # ch20
            ('and when convincingly he shall disover',
             'and when convincingly he shall discover'),  # ch20
            ('when we work as we hould',
             'when we work as we should'),  # ch20
            ('to be ill from an znward',
             'to be ill from an inward'),  # ch20
            ('the understanding shall judge and dertermine',
             'the understanding shall judge and determine'),  # ch21
            ('his way and loveth to lve',
             'his way and loveth to live'),  # ch21
            ('any corruption or temptation is va',
             'any corruption or temptation is a'),  # ch22
            ('As Joshua said when he sset',
             'As Joshua said when he set'),  # ch22
            ('brings in a commanding light linto',
             'brings in a commanding light into'),  # ch22
            ('where he begins to rule, ihe',
             'where he begins to rule, he'),  # ch22
            ('For the same power that ithe',
             'For the same power that the'),  # ch22
            ('overcome by suffering; here lambs sovercome',
             'overcome by suffering; here lambs overcome'),  # ch22
            ('Canaan, yet they must fight iit',
             'Canaan, yet they must fight it'),  # ch22
            ('by the experience of that vannoyance',
             'by the experience of that annoyance'),  # ch22
            ('to comfort, he will terrify ifirst',
             'to comfort, he will terrify first'),  # ch22
            ('being dearer to us than vour',
             'being dearer to us than our'),  # ch22
            ('if we had liberty to schoose',
             'if we had liberty to choose'),  # ch22
            ('and a voluntary people, and aot',
             'and a voluntary people, and not'),  # ch22
            ('hand of the dial points iwell,',
             'hand of the dial points well,'),  # ch22
            ('in that particular case, the neart',
             'in that particular case, the heart'),  # ch22
            ('again. A fire in the theart',
             'again. A fire in the heart'),  # ch23
            ('likewise teacheth us wherein our weakimess',
             'likewise teacheth us wherein our weakness'),  # ch23
            ('male and female asunder. This jeajlousy',
             'male and female asunder. This jealousy'),  # ch23
            ('will lead us out to vicitory,',
             'will lead us out to victory,'),  # ch23
            ('us ; Christ so honoureth ithe',
             'us ; Christ so honoureth the'),  # ch23
            ('and victory unto our care wof',
             'and victory unto our care of'),  # ch23
            ('subtle their conveyance of things nath',
             'subtle their conveyance of things hath'),  # ch25
            ('when there shall be no slory',
             'when there shall be no glory'),  # ch25
            ('Even now there is a ecret',
             'Even now there is a secret'),  # ch25
            ('victory ; then Christ will wlead',
             'victory ; then Christ will plead'),  # ch25
            ('shall no longer be called Jheresy',
             'shall no longer be called heresy'),  # ch25
            ('opposite hinderances; 4. And by advanicing',
             'opposite hinderances; 4. And by advancing'),  # ch26
            ('and strength we have, or velse',
             'and strength we have, or else'),  # ch26
            ('humility, that goeth out of itllvself',
             'humility, that goeth out of itself'),  # ch26
            ('of Christ’s bringing forth judgment tp',
             'of Christ’s bringing forth judgment to'),  # ch26
            ('discovered, and thence we are srought',
             'discovered, and thence we are brought'),  # ch26
            ('ground of this dispensation is, jhat',
             'ground of this dispensation is, that'),  # ch26
            ('in a jealous fear and rembling,',
             'in a jealous fear and trembling,'),  # ch26
            ('12, lest by unreverent and preumptuous',
             '12, lest by unreverent and presumptuous'),  # ch26
            ('him cause to suspend his ssracious',
             'him cause to suspend his gracious'),  # ch26
            ('under Christ’s government have the pirit',
             'under Christ’s government have the spirit'),  # ch26
            ('see and feel a divine wower',
             'see and feel a divine power'),  # ch26
            ('God under signs of his ilispleasure,',
             'God under signs of his displeasure,'),  # ch26
            ('power preserving patience, nay joy wm',
             'power preserving patience, nay joy in'),  # ch26
            ('mourning, inward peace in the idst',
             'mourning, inward peace in the midst'),  # ch26
            ('for us, and we for i¢',
             'for us, and we for it'),  # ch26
            ('a distempered body, of which moisome',
             'a distempered body, of which noisome'),  # ch27
            ('cause : for the end vof',
             'cause : for the end of'),  # ch27
            ('bird, that maketh her fly ithe',
             'bird, that maketh her fly the'),  # ch27
            ('to Satan, that he should Jabour',
             'to Satan, that he should labour'),  # ch28
            ('not things in motion till Clirist',
             'not things in motion till Christ'),  # ch28
            ('into one fold, that there aay',
             'into one fold, that there may'),  # ch28
            ('one sheepfold, and one shepherd, Jobn',
             'one sheepfold, and one shepherd, John'),  # ch28
            ('No creature can hinder the sourse',
             'No creature can hinder the course'),  # ch28
            ('stop the influence of heaven, )aor',
             'stop the influence of heaven, nor'),  # ch28
            ('they thou hast given unto jime',
             'they thou hast given unto me'),  # ch28
            ('these are they that have takén',
             'these are they that have taken'),  # ch28
            ('reign with me. And then hae',
             'reign with me. And then he'),  # ch28
            ('other rule and authority, and yoower,',
             'other rule and authority, and power,'),  # ch28
            # The residue the alignment could not auto-accept — multi-token
            # spans, and places where GROSART is the damaged side. Each was read
            # in context and settled by hand. Rejected as faithful to Pickering
            # rather than damage: `Isai.`/`Psalm`/`Ephes.`/`Answ.` (its own
            # abbreviations, where Grosart writes `Isa.`/`Ps.`/`Eph.`/`Ans.`),
            # `burthen`, `loth`, `mayst`, `irreconcileable`, `enterprizes`,
            # `judgement`, `mispersuasions`, `perfiteth`, and the proper names
            # `Gedeon` (KJV Heb. xi. 32) and `Jehosaphat` — a name is the one
            # thing never to "correct" without a witness. `believest`,
            # `lodgeth`, `man's nature` and `voluntaries` are right here and
            # damaged in Grosart.
            ('them, and so is his ofice.',
             'them, and so is his office.'),  # ch6
            ('to poverty of spirit, than ereatness',
             'to poverty of spirit, than greatness'),  # ch7
            ('men refuse, then Wisdom will langh',
             'men refuse, then Wisdom will laugh'),  # ch17
            ('2¢',
             'it'),  # ch3
            ('and_short',
             'and short'),  # ch4
            ('Led erat',
             'hell. Therefore'),  # ch4
            ('Zech. iy. 10',
             'Zech. iv. 10'),  # ch5
            ('wigour',
             'vigour'),  # ch5
            ('yplaces',
             'places'),  # ch5
            ('pluces',
             'places'),  # ch8
            ('candlesticks, Rey.',
             'candlesticks, Rev.'),  # ch6
            ("Christ's, (Rey.",
             "Christ's, (Rev."),  # ch25
            ('Psalm Ixy.',
             'Psalm lxv.'),  # ch7
            ('diswr ustful',
             'distrustful'),  # ch10
            ('therplant',
             'the plant'),  # ch10
            ('themselves zn',
             'themselves in'),  # ch10
            ('Sire, walh',
             'fire, walk'),  # ch11
            ('SOTTOW',
             'sorrow'),  # ch11
            ('wefineth',
             'refineth'),  # ch11
            ('wovld?',
             'would?'),  # ch13
            ('J¢ zs',
             'It is'),  # ch14
            ('qlorieth,',
             'glorieth,'),  # ch14
            ('tuled',
             'ruled'),  # ch15
            ('zearer',
             'nearer'),  # ch16
            ('righteousness pierceth eeper than',
             'righteousness pierceth deeper than'),  # ch16
            ('Jhrist’s',
             'Christ’s'),  # ch16
            ('underaken',
             'undertaken'),  # ch16
            ('jpirits',
             'spirits'),  # ch16
            ('pase,',
             'case,'),  # ch17
            ('detruction:',
             'destruction:'),  # ch17
            ('vpon ourselves,',
             'upon ourselves,'),  # ch17
            ('sgranted,',
             'granted,'),  # ch17
            ('therefore thang',
             'therefore hang'),  # ch17
            ('&c. Jabour',
             '&c. labour'),  # ch17
            ('wpon him,',
             'upon him,'),  # ch17
            ('voffence',
             'offence'),  # ch17
            ('king; ihe',
             'king; he'),  # ch19
            ('lkings',
             'kings'),  # ch19
            ('UHereupon',
             'Hereupon'),  # ch20
            ('gudgeth',
             'judgeth'),  # ch20
            ('hatha spite',
             'hath a spite'),  # ch20
            ('conyersation.',
             'conversation.'),  # ch20
            ('and the devil loth but promote',
             'and the devil doth but promote'),  # ch20
            ('25, theaven',
             '25, heaven'),  # ch22
            ('as ithe',
             'as the'),  # ch22
            ('chanyed',
             'changed'),  # ch22
            ('wictory',
             'victory'),  # ch22
            ('imeans',
             'means'),  # ch22
            ('wnder',
             'under'),  # ch22
            ('is-come into',
             'is come into'),  # ch22
            ('imaketh',
             'maketh'),  # ch22
            ('sshews',
             'shews'),  # ch22
            ('duities',
             'duties'),  # ch22
            ('FSrom us,',
             'From us,'),  # ch22
            ('a sdevise.',
             'a devise.'),  # ch23
            ('vReepeth himself,',
             'keepeth himself,'),  # ch23
            ('prosper: reigion',
             'prosper: religion'),  # ch24
            ('him; nuch',
             'him; much'),  # ch25
            ('Jingers',
             'fingers'),  # ch26
            ('undervitake.',
             'undertake.'),  # ch26
            ('stand out.</p><p>wn greater, because',
             'stand out in greater, because'),  # ch26
            ('itronger',
             'stronger'),  # ch26
            ('corruption undisserned',
             'corruption undiscerned'),  # ch26
            ('work acsording',
             'work according'),  # ch26
            ('And therefore we hould work out',
             'And therefore we should work out'),  # ch26
            ('asvaulted',
             'assaulted'),  # ch26
            ('compassed with roubles,',
             'compassed with troubles,'),  # ch26
            ('apholding us?',
             'upholding us?'),  # ch26
            ('laboursy',
             'labours'),  # ch27
            ('ithinketh',
             'thinketh'),  # ch27
            ('recewe',
             'receive'),  # ch27
            ('Lordjund',
             'Lord and'),  # ch28
            ('vallings,',
             'callings,'),  # ch28
            ('iy. 13,',
             'iv. 13,'),  # ch28
            ('finward',
             'inward'),  # ch20
            ('as smoking Bax.</p><p>‘ It is well',
             'as smoking flax.</p><p>Answ. It is well'),  # ch16
            ('no mercy on them, saz, xxvii. 11',
             'no mercy on them, Isai. xxvii. 11'),  # ch17
            ('compassion ; @ prince of peace',
             'compassion ; a prince of peace'),  # ch3
            ('bondage, Isai. 1xi, 1, 2',
             'bondage, Isai. lxi. 1, 2'),  # ch10
            ('but for ithe truth,',
             'but for the truth,'),  # ch22
            ('in istate',
             'in a state'),  # ch26
            # The tail the alignment could not reach, because Grosart's span
            # around each differs too much for a clean one-for-one swap. Mostly
            # a LOST SPACE ("Godin him", "asa grain of mustardseed", "foundin
            # Christ") — the scan closes a word gap as readily as it opens one —
            # plus a running header that leaked into ch16's prose ("saith the
            # AND SMOKING FLAX. Ke smoking flax"), and `stodamnus`, which
            # Grosart reads "us to damn us".
            ('we must see Godin him',
             'we must see God in him'),  # ch1
            ('tender care, wntil judgment',
             'tender care, until judgment'),  # ch1
            ('keep ourselves under Jithis work',
             'keep ourselves under this work'),  # ch4
            ('he therefore ap(plieth himself',
             'he therefore applieth himself'),  # ch4
            ('grace is asa grain of mustardseed',
             'grace is as a grain of mustard seed'),  # ch5
            ('contrite spirit, Psalm xxxiy. 18',
             'contrite spirit, Psalm xxxiv. 18'),  # ch6
            ('truth, if it be nota truth',
             'truth, if it be not a truth'),  # ch8
            ('kill. Wesee even contrary',
             'kill. We see even contrary'),  # ch9
            ('as well as the wholeelement',
             'as well as the whole element'),  # ch10
            ('Deut. vi. 5. Inthe covenant',
             'Deut. vi. 5. In the covenant'),  # ch10
            ('fear him, Psalm cxly. 19',
             'fear him, Psalm cxlv. 19'),  # ch14
            ('in mercy, Psalm Ixxyili. 39',
             'in mercy, Psalm lxxviii. 39'),  # ch15
            ('but shake acedar,',
             'but shake a cedar,'),  # ch15
            ('therefore, poor vecause we know',
             'therefore, poor because we know'),  # ch15
            ('who ever neglected his‘own members',
             'who ever neglected his own members'),  # ch16
            ('saith the AND SMOKING FLAX. Ke smoking flax',
             'saith the smoking flax'),  # ch16
            ('Christ may act the part ofan enemy',
             'Christ may act the part of an enemy'),  # ch16
            ('heart under contrary uppearances',
             'heart under contrary appearances'),  # ch16
            ('flax ; and Jhrist again undertaking',
             'flax ; and Christ again undertaking'),  # ch16
            ('the Father, appearag before him',
             'the Father, appearing before him'),  # ch16
            ('us blameless -efore him',
             'us blameless before him'),  # ch16
            ('as mariners do, cast unchor',
             'as mariners do, cast anchor'),  # ch16
            ('what his Son’s ove was',
             'what his Son’s love was'),  # ch16
            ('is all to be foundin Christ',
             'is all to be found in Christ'),  # ch16
            ('as, 1. Such as go on inall ill courses',
             'as, 1. Such as go on in all ill courses'),  # ch17
            ('as that unprojitable servant',
             'as that unprofitable servant'),  # ch17
            ('God hath not made stodamnus.',
             'God hath not made us to damn us.'),  # ch17
            ('government, because itis called',
             'government, because it is called'),  # ch20
            ('highest reason ofall; and therefore',
             'highest reason of all; and therefore'),  # ch20
            ('us out ofall troublesome',
             'us out of all troublesome'),  # ch22
            ('therefore, that itis dangerous',
             'therefore, that it is dangerous'),  # ch26
            ('evidences of nis just displeasure',
             'evidences of his just displeasure'),  # ch16
            # The last of it. Mostly the lost-space class again, plus a handful
            # of single-letter misreads. `blew up the decaying sparks` is left
            # alone — it is Sibbes's own idiom, not damage.
            ('your own levices, Proy. i. 31',
             'your own devices, Prov. i. 31'),  # ch17
            ("intended to stir'us up",
             'intended to stir us up'),  # ch17
            ('comfort tous; hereuponit is',
             'comfort to us; hereupon it is'),  # ch18
            ('exaltation that ihe may turn',
             'exaltation that he may turn'),  # ch19
            ('As God isein himself',
             'As God is in himself'),  # ch20
            ('conscience maketh aman a king',
             'conscience maketh a man a king'),  # ch22
            ('prevail, either uy to make us',
             'prevail, either to make us'),  # ch22
            ('accursed and daa enemies',
             'accursed and damned enemies'),  # ch22
            ('accompany the wguilt ofsin;',
             'accompany the guilt of sin;'),  # ch22
            ('out of a thick icloud;',
             'out of a thick cloud;'),  # ch22
            ('the pride of all fleshlow.',
             'the pride of all flesh low.'),  # ch22
            ('for ever with ous thereafter',
             'for ever with us thereafter'),  # ch23
            ('openly forth to victoryWhence we observe',
             'openly forth to victory. Whence we observe'),  # ch25
            ('King of kings, and Lordof lords',
             'King of kings, and Lord of lords'),  # ch25
            ('you can do alittle, but nothing',
             'you can do a little, but nothing'),  # ch26
            ("sit in judgment upon'them that judge",
             'sit in judgment upon them that judge'),  # ch27
            ('his enemies as wellas ours',
             'his enemies as well as ours'),  # ch28
            ('given him Sor vis possession',
             'given him for his possession'),  # ch28
            ('and we shalls ee the salvation',
             'and we shall see the salvation'),  # ch28
            # The last two guillemets, both a lost letter rather than a quote —
            # Grosart supplies "a right judgment" and "hope in a state
            # hopeless". `QuoteStyleTests` counts « » as CURLY, so these would
            # have passed the quote gate while printing a French quotation mark
            # mid-sentence.
            ("light a right » judgment of things",
             "light a right judgment of things"),
            ("and hope in «, state hopeless",
             "and hope in a state hopeless"),
            ("with fears and «doubts?", "with fears and doubts?"),
            # The one column rule that fused to its neighbour rather than
            # standing alone, so the reflow's strip could not reach it.
            ("the weak, Ezek. |) xxxiv. 15", "the weak, Ezek. xxxiv. 15"),
            # Standalone junk marks the scanner left between words — a stray
            # `~`, `}`, `©`, `=`, `%`, `_`, `¢`. Done as literal pairs rather
            # than a reflow rule like the column bars: `*` is a real footnote
            # marker in `susanna-wesley-clarke`, and a class wide enough to
            # catch these would have rewritten that book's shipped fixture too.
            ('ruised reeds. 2. Smoking wear. = ',
             'ruised reeds. 2. Smoking flax. '),  # ch1
            ('annel, that as sin bred grief, } ',
             'annel, that as sin bred grief, '),  # ch4
            ('o be led withal in all things. © ',
             'o be led withal in all things. '),  # ch8
            (' gracious men have a spiritual " ',
             ' gracious men have a spiritual '),  # ch11
            ('im. 2. Strength in himself, as _ ',
             'im. 2. Strength in himself, as '),  # ch16
            ('he mighty God, Isaiah ix. 6 3. _ ',
             'he mighty God, Isaiah ix. 6. 3. '),  # ch16
            ('as if it were in vain to go to ~ ',
             'as if it were in vain to go to '),  # ch17
            ('f or in our application of it. _ ',
             'f or in our application of it. '),  # ch17
            ('his plough and neglect tillage ¢ ',
             'his plough and neglect tillage? '),  # ch17
            ('rit floweth into the soul, and _ ',
             'rit floweth into the soul, and '),  # ch17
            ('able as the sun in its course, _ ',
             'able as the sun in its course, '),  # ch20
            ('en we fall not upon that which * ',
             'en we fall not upon that which '),  # ch20
            ('e heart of a Christian is like _ ',
             'e heart of a Christian is like '),  # ch21
            ('as at the best, a city compact _ ',
             'as at the best, a city compact '),  # ch21
            ('tereth not so much what ill is _ ',
             'tereth not so much what ill is '),  # ch22
            ('hich we shall enjoy in heaven. _ ',
             'hich we shall enjoy in heaven. '),  # ch23
            ('midst of our hearts, Psalm cx. } ',
             'midst of our hearts, Psalm cx. '),  # ch27
            (', it is a comfortable thing to _ ',
             ', it is a comfortable thing to '),  # ch28
            # The same junk where it abuts a word or punctuation rather than
            # standing alone. Two carry meaning the mark displaced: "25%" is
            # the print's "25;", and "vic-~ tory" is a line-break hyphen the
            # scan turned into a tilde.
            ('Gen. xxxiv. 25% but Christ',
             'Gen. xxxiv. 25; but Christ'),  # ch3
            ('divine; upon _long experience',
             'divine; upon long experience'),  # ch9
            ('good duties, "because they feel',
             'good duties, because they feel'),  # ch13
            ('yet even there some} like cruel',
             'yet even there some, like cruel'),  # ch17
            ('government within us_ principally',
             'government within us principally'),  # ch18
            ('so he is to him; he~ ascribes',
             'so he is to him; he ascribes'),  # ch20
            ('notice of by us;_ 1. Whether',
             'notice of by us; 1. Whether'),  # ch22
            ('to itself. Look _back to former',
             'to itself. Look back to former'),  # ch23
            ('counsels from the }Lord, shall walk',
             'counsels from the Lord, shall walk'),  # ch25
            ('assured vic-~ tory, which we may',
             'assured victory, which we may'),  # ch28
            ('took not advantage of}, his errors',
             'took not advantage of his errors'),  # ch28
            # Two bare apostrophes standing where the scan lost a word.
            ("of his poor ' disciples ?",
             'of his poor disciples ?'),  # ch7
            ("but addeth ' to a lustre",
             'but addeth a lustre'),  # ch17
            # --- 2026-09-11: the damage #1943 shipped. These pairs run on the
            # STORED text (the pairs above run on the raw scan), so the deploy's
            # `apply_body_corrections` carries them to prod with no migration.
            #
            # The OCR read this edition's margin rules as OPENING quote marks —
            # 163 `‘` and 15 `“` against no `”`, because it sets no quotation
            # marks at all. Migration 0138 strips the plain ones from the stored
            # English rows (a transform here would reach every language edition
            # of the slug, and translations do quote). These are the fourteen
            # standing where a LETTER was, which stripping alone would leave as
            # "ruth from truth"; each word is settled against Grosart.
            ('believe “ruth from truth', 'believe truth from truth'),  # ch15
            ('from us. “he influence', 'from us. The influence'),  # ch16
            ('let him ‘rust in the name', 'let him trust in the name'),  # ch16
            ('given up ‘ito give over', 'given up to give over'),  # ch17
            ('that there car’ hardly', 'that there can hardly'),  # ch17
            ('stream of ‘ur own nature', 'stream of our own nature'),  # ch20
            ('only he ‘math engraven', 'only he hath engraven'),  # ch20
            ('any earthly ‘oss or gain', 'any earthly loss or gain'),  # ch22
            ('came near ‘nome to', 'came near home to'),  # ch22
            ('flesh, and “he course', 'flesh, and the course'),  # ch22
            ('glory of ‘nis excellencies', 'glory of his excellencies'),  # ch25
            ('will declare ‘0 all the world', 'will declare to all the world'),  # ch25
            ('towards “hose in whom', 'towards those in whom'),  # ch25
            ('to whom ‘0 return', 'to whom to return'),  # ch26
            # The same repairs as a re-import now reads them: `import_archive`
            # drops a line-initial rule mark itself, so a raw scan arrives as
            # "ruth from truth", mark already gone. The with-mark spellings stay
            # (the last is in the Grosart group below) — 0138 settles the stored
            # rows through them before it strips.
            ('believe ruth from truth', 'believe truth from truth'),  # ch15
            ('from us. he influence', 'from us. The influence'),  # ch16
            ('let him rust in the name', 'let him trust in the name'),  # ch16
            ('given up ito give over', 'given up to give over'),  # ch17
            ('stream of ur own nature', 'stream of our own nature'),  # ch20
            ('only he math engraven', 'only he hath engraven'),  # ch20
            ('any earthly oss or gain', 'any earthly loss or gain'),  # ch22
            ('came near nome to', 'came near home to'),  # ch22
            ('flesh, and he course', 'flesh, and the course'),  # ch22
            ('glory of nis excellencies', 'glory of his excellencies'),  # ch25
            ('towards hose in whom', 'towards those in whom'),  # ch25
            ('many out on a dangerous', 'many out of a dangerous'),  # ch20
            # The same rules read as a CLOSING mark after a word. Not left to a
            # rule: `’` is also this text's apostrophe ("Jonas’ gourd").
            ('without making’ a noise', 'without making a noise'),  # ch1
            ('if gently’ handled', 'if gently handled'),  # ch7
            ('upon lesser’ errors', 'upon lesser errors'),  # ch9
            ('his disciples more’ than', 'his disciples more than'),  # ch17
            ('spirit of Christ,’ brought', 'spirit of Christ, brought'),  # ch21
            ('Isai. xy.8, We ’ see', 'Isai. lxv. 8. We see'),  # ch7
            # Three places the scan lost more than a letter, supplied from
            # Grosart — each read as a real sentence with a word or line gone.
            ('let us not fore the cure be wrought,',
             'let us not take off ourselves too soon, nor pull off the plaster '
             'before the cure be wrought,'),  # ch4
            ('given us o Christ, and Christ giveth us back again to the lather.',
             'given us to Christ, and Christ giveth us back again to the Father.'),  # ch16
            ('when he hall clearly discover what is spelled in particular, we re carried',
             'when he shall clearly discover what is good in particular, we are carried'),  # ch20
            # Misreads that land on a REAL word ("derived rot God", "eat the it
            # of your own ways"), so a spellcheck scan calls them clean. Found by
            # aligning the whole text against Grosart word by word and reading
            # every difference; the 400-odd where Grosart is the damaged side,
            # or where the editions simply differ, are left as Pickering prints
            # them.
            ('2. Smoking wear. ', '2. Smoking flax. '),  # ch1
            ('as smoking flax, G They are', 'as smoking flax. They are'),  # ch1
            ('termeth poor a spirit', 'termeth poor in spirit'),  # ch1
            ('majesty, go he hath bowels', 'majesty, so he hath bowels'),  # ch3
            ('a ghost, it is J, Matt.', 'a ghost, it is I, Matt.'),  # ch3
            ('which are rung from them', 'which are wrung from them'),  # ch4
            ('in itself, mot the least', 'in itself, not the least'),  # ch5
            ('quenched not D that little light', 'quenched not that little light'),  # ch7
            ('make them east off', 'make them cast off'),  # ch8
            ('temper of tags times', 'temper of these times'),  # ch8
            ('authority derived rot God', 'authority derived from God'),  # ch9
            ('moderation dhan rigour', 'moderation than rigour'),  # ch9
            ('carriage toward! miserable', 'carriage toward miserable'),  # ch9
            ('labour to hill Christ', 'labour to kill Christ'),  # ch9
            ('unbrother in 2 passion', 'unbrother in a passion'),  # ch9
            ('though net seen', 'though not seen'),  # ch10
            ('sins laid E upon him', 'sins laid upon him'),  # ch10
            ('as the san in the spring', 'as the sun in the spring'),  # ch11
            ('Can a dead mam complain', 'Can a dead man complain'),  # ch11
            ('holiness and ais own', 'holiness and his own'),  # ch11
            ('most contrary 10 God', 'most contrary to God'),  # ch12
            ('which the ruth of God', 'which the truth of God'),  # ch12
            ('cannot pray ; O J am', 'cannot pray ; O I am'),  # ch13
            ('giveth the r will and', 'giveth the will and'),  # ch13
            ('some little k addition', 'some little addition'),  # ch14
            ('It is not J, saith', 'It is not I, saith'),  # ch14
            ('the desire is as earnest', 'the desire is an earnest'),  # ch14
            ('qualified, re we must', 'qualified, there we must'),  # ch15
            ('sick man his e;', 'sick man his ague;'),  # ch15
            ('we are weary, sand would', 'we are weary, and would'),  # ch15
            ('Wee must know', 'We must know'),  # ch15
            ('he seemeth so be an enemy', 'he seemeth to be an enemy'),  # ch16
            ('with us, us with Jacob', 'with us, as with Jacob'),  # ch16
            ('the vizard tom his face', 'the vizard from his face'),  # ch16
            ('covenant, vet she would', 'covenant, yet she would'),  # ch16
            ('when he vas furthest', 'when he was furthest'),  # ch16
            ('find in bis heart', 'find in his heart'),  # ch16
            ('his care to is. The eyes', 'his care to us. The eyes'),  # ch16
            ('the east love we have', 'the least love we have'),  # ch16
            ('only a nan, but a curse', 'only a man, but a curse'),  # ch16
            ('that C will suffer them', 'that Christ will suffer them'),  # ch17
            ('those that pill the potion', 'those that spill the potion'),  # ch17
            ('Christ in e ways of his mercy', 'Christ in the ways of his mercy'),  # ch17
            ('should eat the it of your own ways',
             'should eat the fruit of your own ways'),  # ch17
            ('men shall think, G that', 'men shall think, that'),  # ch17
            ('encouragement herd from', 'encouragement here from'),  # ch17
            ('in some eases peace', 'in some cases peace'),  # ch17
            ('they may ido well', 'they may do well'),  # ch17
            ('the Church whieh thou lovest', 'the Church which thou lovest'),  # ch17
            ('Lord, this igh Christian', 'Lord, this poor Christian'),  # ch17
            ('any corwuption favoured', 'any corruption favoured'),  # ch17
            ('Jude 4. AInfirmities are', 'Jude 4. Infirmities are'),  # ch17
            ('to tule us', 'to rule us'),  # ch19
            ('as he its pure', 'as he is pure'),  # ch19
            ('grace supposeth mature as', 'grace supposeth nature as'),  # ch20
            ('of ene holy wise man', 'of one holy wise man'),  # ch20
            ('many out on a ‘dangerous', 'many out of a dangerous'),  # ch20
            ('issueth from fin is', 'issueth from them is'),  # ch20
            ('with little meril,', 'with little peril,'),  # ch20
            ('at all in as. God', 'at all in us. God'),  # ch20
            ('the Sear of the Lord', 'the fear of the Lord'),  # ch21
            ('flesh, shad die', 'flesh, shall die'),  # ch21
            ('foiled vat first', 'foiled at first'),  # ch22
            ('that as born of God', 'that is born of God'),  # ch22
            ('that is im us', 'that is in us'),  # ch22
            ('troublesome and idark', 'troublesome and dark'),  # ch22
            ('It is I good, therefore', 'It is good, therefore'),  # ch23
            ('could a devise', 'could devise'),  # ch23
            ('consult mot with', 'consult not with'),  # ch23
            ('that the ascribeth', 'that he ascribeth'),  # ch23
            ('ordinances the draws near', 'ordinances he draws near'),  # ch23
            ('sun n the firmament', 'sun in the firmament'),  # ch25
            ('which us called', 'which is called'),  # ch25
            ('mother Eye will', 'mother Eve will'),  # ch25
            ('ourselves, thow easily', 'ourselves, how easily'),  # ch26
            ('yet thow heardest', 'yet thou heardest'),  # ch6
            ('which ss higher', 'which is higher'),  # ch26
            ('minded is K death', 'minded is death'),  # ch27
            ('division, mot only', 'division, not only'),  # ch27
            ('he is as rel for the falling as the wising',
             'he is as well for the falling as the rising'),  # ch27
            ('giveth up hinds that', 'giveth up those that'),  # ch27
            ('Satan and this factors', 'Satan and his factors'),  # ch27
            ('sheep is Father hath', 'sheep his Father hath'),  # ch28
            ('think if the calling', 'think of the calling'),  # ch28
            ('present ) ill to his', 'present all to his'),  # ch28
            ('and et ourselves', 'and set ourselves'),  # ch28
            # Stray marks and fused punctuation (`short.of`, `inward:rule`).
            ('embrace Christ,- and in him', 'embrace Christ, and in him'),  # ch1
            ('three things: - First,', 'three things:—First,'),  # ch1
            ('all ye that ure weary', 'all ye that are weary'),  # ch1
            ('Psalm vi. &e. The Lord', 'Psalm vi. &c. The Lord'),  # ch4
            ('came short.of the outward', 'came short of the outward'),  # ch5
            ('gentle -a Saviour', 'gentle a Saviour'),  # ch8
            ('stooping - unto them', 'stooping unto them'),  # ch8
            ('moderation: it-is but', 'moderation: it is but'),  # ch8
            ('and not-for Christ', 'and not for Christ'),  # ch14
            ('in the world.. Heb. Xi.', 'in the world, Heb. xi.'),  # ch14
            ('he mighty God, Isaiah ix. 6 3.', 'he mighty God, Isaiah ix. 6. 3.'),  # ch16
            ('Prov. i. 31. ;', 'Prov. i. 31;'),  # ch17
            ('neglect tillage Hence', 'neglect tillage? Hence'),  # ch17
            ('for the wisdom. from above', 'for the wisdom from above'),  # ch17
            ('than.a thousand', 'than a thousand'),  # ch17
            ('inward:rule', 'inward rule'),  # ch18
            ('savour.the things', 'savour the things'),  # ch18
            ('our base affec(tions.', 'our base affections.'),  # ch19
            ('prince of the world, H is judged', 'prince of the world, is judged'),  # ch20
            ('St. Paul, [f we live', 'St. Paul, If we live'),  # ch21
            ('enemies, [f we resist', 'enemies, If we resist'),  # ch22
            ('after -union with', 'after union with'),  # ch22
            ('will b , because', 'will be, because'),  # ch23
            ('all good l,occasions', 'all good occasions'),  # ch23
            ('we may / gain more', 'we may gain more'),  # ch23
            ('false - glasses', 'false glasses'),  # ch25
            ('will yield : possession', 'will yield possession'),  # ch27
            ('able-fo remove', 'able to remove'),  # ch28
            # Scripture references: roman `l` read as `I`/`1`, and digits the
            # scan misread. Only where Grosart AND the verse itself agree —
            # `Mat. ix. 24` (for Mark) and `Luke x. 42` are Pickering's own
            # slips, not the scan's, and are left.
            ('Jam. y. 14', 'Jam. v. 14'),  # ch4
            ('Isa. Ixvi. 2', 'Isa. lxvi. 2'),  # ch4
            ('Isa. lili. 2', 'Isa. liii. 2'),  # ch5
            ('Rom. vii. 34, saith', 'Rom. vii. 24, saith'),  # ch6
            ('candle, Psalm xviii. 26,', 'candle, Psalm xviii. 28,'),  # ch11
            ('Psalm Ixxiii. 22', 'Psalm lxxiii. 22'),  # ch12
            ('their teeth, Proy. x. 29', 'their teeth, Prov. x. 29'),  # ch17
            ('a blessing, 1 Cor. 16;', 'a blessing, 1 Cor. xv. 57, 58;'),  # ch17
            ('Psalm Ixxii. 1', 'Psalm lxxii. 1'),  # ch18
            ('Ps. 1xxxiv. 10', 'Ps. lxxxiv. 10'),  # ch20
            ('Psalm cxxii. 3:', 'Psalm cxxii. 5:'),  # ch21
            ('Eph. il. 6', 'Eph. ii. 6'),  # ch22
            ('Psalm Ixxxvi. 11', 'Psalm lxxxvi. 11'),  # ch23
            ('fight, Psalm xiv. 1', 'fight, Psalm cxliv. 1'),  # ch26
            ('2 Chron. xx. 21:', '2 Chron. xx. 12:'),  # ch26
            # Three of this entry's own earlier repairs, undone on the stored
            # text: `intreaty` is Sibbes's spelling, not a slip to modernise
            # (that pair is gone); `religion` follows a colon in lowercase, as
            # everywhere in this edition; and the answer marker is Pickering's
            # `Answ.`. Their raw-scan pairs above now write the right text.
            ('an affectionate entreaty', 'an affectionate intreaty'),  # ch17
            ('prosper: Religion', 'prosper: religion'),  # ch24
            ('flax.</p><p>Ans. It is well', 'flax.</p><p>Answ. It is well'),  # ch16
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
        # Its eight section headings and the Job 1:21 display line, in all nine
        # editions — see "The rest of Gutenberg #23438" above.
        "restored_blocks": [
            # en
            ("<p>In our meditations on the", "<h3>INTRODUCTORY.</h3>"),
            ("<p>In the 8th verse of the", "<h3>GOD'S TESTIMONY AND CHALLENGE.</h3>"),
            ("<p>In the 8th verse of the",
             '<p><em>"The LORD gave, and the LORD hath taken away; blessed be the Name of the LORD</em>."--Job i.21.</p>'),
            ("<p>The reply of Satan is noteworthy.", "<h3>THE UNSEEN HEDGE.</h3>"),
            ("<p>Reverting to the history", "<h3>THE TESTING OF JOB</h3>"),
            ("<p>And soon Satan showed the", "<h3>SATAN'S MALIGNITY.</h3>"),
            ("<p>But He who sent the trial", "<h3>GRACE SUFFICIENT.</h3>"),
            ("<p>Job's trial, however, was", "<h3>DEEPER TRIALS.</h3>"),
            ("<p>Nor was the blessing GOD",
             "<h3>THE LOVING-KINDNESS OF THE LORD.</h3>"),
            # fr
            ("<p>Dans nos méditations sur", "<h3>INTRODUCTION.</h3>"),
            ("<p>Au huitième verset du premier",
             "<h3>LE TÉMOIGNAGE ET LE DÉFI DE DIEU.</h3>"),
            ("<p>Au huitième verset du premier",
             "<p><em>« L’ÉTERNEL a donné, et l’ÉTERNEL a ôté ; que le nom de l’ÉTERNEL soit béni</em> ! » — Job 1:21.</p>"),
            ("<p>La réponse de Satan est", "<h3>LA HAIE INVISIBLE.</h3>"),
            ("<p>Pour en revenir à l’histoire", "<h3>L’ÉPREUVE DE JOB</h3>"),
            ("<p>Et bientôt Satan montra", "<h3>LA MALIGNITÉ DE SATAN.</h3>"),
            ("<p>Mais Celui qui envoya l’épreuve", "<h3>LA GRÂCE SUFFISANTE.</h3>"),
            ("<p>L’épreuve de Job, cependant,",
             "<h3>DES ÉPREUVES PLUS PROFONDES.</h3>"),
            ("<p>La bénédiction que DIEU", "<h3>LA BONTÉ DU SEIGNEUR.</h3>"),
            # es
            ("<p>En nuestras meditaciones", "<h3>INTRODUCCIÓN.</h3>"),
            ("<p>En el versículo 8 del capítulo",
             "<h3>EL TESTIMONIO Y EL DESAFÍO DE DIOS.</h3>"),
            ("<p>En el versículo 8 del capítulo",
             '<p><em>"El SEÑOR dio, y el SEÑOR quitó; sea el Nombre del SEÑOR bendito</em>."—Job 1:21.</p>'),
            ("<p>La respuesta de Satanás", "<h3>EL VALLADO INVISIBLE.</h3>"),
            ("<p>Volviendo a la historia", "<h3>LA PRUEBA DE JOB</h3>"),
            ("<p>Y pronto mostró Satanás", "<h3>LA MALIGNIDAD DE SATANÁS.</h3>"),
            ("<p>Pero Aquel que envió la", "<h3>GRACIA SUFICIENTE.</h3>"),
            ("<p>La prueba de Job, sin embargo,", "<h3>PRUEBAS MÁS PROFUNDAS.</h3>"),
            ("<p>Ni fue pequeña la bendición", "<h3>LA MISERICORDIA DEL SEÑOR.</h3>"),
            # pt
            ("<p>Em nossas meditações sobre", "<h3>INTRODUÇÃO.</h3>"),
            ("<p>No versículo 8 do capítulo",
             "<h3>O TESTEMUNHO E O DESAFIO DE DEUS.</h3>"),
            ("<p>No versículo 8 do capítulo",
             '<p><em>"O SENHOR deu, e o SENHOR tomou; bendito seja o Nome do SENHOR</em>."—Jó 1:21.</p>'),
            ("<p>A resposta de Satanás é", "<h3>A SEBE INVISÍVEL.</h3>"),
            ("<p>Voltando à história de", "<h3>A PROVAÇÃO DE JÓ</h3>"),
            ("<p>E logo Satanás mostrou", "<h3>A MALIGNIDADE DE SATANÁS.</h3>"),
            ("<p>Mas Aquele que enviou a", "<h3>GRAÇA SUFICIENTE.</h3>"),
            ("<p>A provação de Jó, contudo,", "<h3>PROVAÇÕES MAIS PROFUNDAS.</h3>"),
            ("<p>Nem foi pequena a bênção", "<h3>A BENIGNIDADE DO SENHOR.</h3>"),
            # sw
            ("<p>Katika tafakari zetu juu", "<h3>UTANGULIZI.</h3>"),
            ("<p>Katika mstari wa 8 wa sura",
             "<h3>USHUHUDA NA CHANGAMOTO YA MUNGU.</h3>"),
            ("<p>Katika mstari wa 8 wa sura",
             '<p><em>"BWANA alitoa, na BWANA ametwaa; jina la BWANA na lihimidiwe</em>."--Ayubu 1:21.</p>'),
            ("<p>Jibu la Shetani lastahili", "<h3>BOMA LISILOONEKANA.</h3>"),
            ("<p>Kurudi katika historia", "<h3>KUJARIBIWA KWA AYUBU</h3>"),
            ("<p>Na mara Shetani alionyesha", "<h3>UBAYA WA SHETANI.</h3>"),
            ("<p>Lakini yeye aliyepeleka", "<h3>NEEMA YA KUTOSHA.</h3>"),
            ("<p>Lakini jaribu la Ayubu,", "<h3>MAJARIBU MAZITO ZAIDI.</h3>"),
            ("<p>Wala baraka ambayo MUNGU", "<h3>FADHILI ZA BWANA.</h3>"),
            # lg
            ("<p>Mu kufumiitiriza kwaffe", "<h3>ENNYANJULA.</h3>"),
            ("<p>Mu lunyiriri olw’omunaana",
             "<h3>OBUJULIZI N’OKUSOOMOOZA KWA KATONDA.</h3>"),
            ("<p>Mu lunyiriri olw’omunaana",
             '<p><em>"Mukama ye yawa era Mukama y’aggyeewo, erinnya lya Mukama Katonda lyebazibwe</em>."—Yobu 1:21.</p>'),
            ("<p>Okuddamu kwa Setaani kwa", "<h3>OLUKOMERA OLUTALABIKA.</h3>"),
            ("<p>Nga tudda ku byafaayo bya", "<h3>OKUGEZESEBWA KWA YOBU</h3>"),
            ("<p>Amangu ago Setaani yalaga", "<h3>OBUKYAYI BWA SETAANI.</h3>"),
            ("<p>Naye oyo eyaweereza okugezesebwa", "<h3>EKISA EKIMALA.</h3>"),
            ("<p>Naye okugezesebwa kwa Yobu",
             "<h3>OKUGEZESEBWA OKUSINGAWO OBUZITO.</h3>"),
            ("<p>So n’omukisa Katonda gwe",
             "<h3>OKWAGALA OKUTAGGWAAWO OKWA MUKAMA.</h3>"),
            # uk
            ("<p>У наших роздумах над першою", "<h3>ВСТУП.</h3>"),
            ("<p>У 8-му вірші 1-го роздїлу", "<h3>БОЖЕ СВІДОЦТВО Й ВИКЛИК.</h3>"),
            ("<p>У 8-му вірші 1-го роздїлу",
             "<p><em>«Господь дав, Господь і взяв; нехай буде імя Господнє благословенне</em>!» — Йов 1:21.</p>"),
            ("<p>Відповідь Сатани прикметна.", "<h3>НЕВИДИМА ЗАГОРОДА.</h3>"),
            ("<p>Вертаючись до історії Йова:", "<h3>ПРОБА ЙОВОВА</h3>"),
            ("<p>І скоро Сатана виявив злобу", "<h3>ЗЛОБА САТАНИ.</h3>"),
            ("<p>Але Той, хто послав пробу,", "<h3>ДОСИТЬ БЛАГОДАТИ.</h3>"),
            ("<p>Одначе проба Йовова не", "<h3>ГЛИБШІ ПРОБИ.</h3>"),
            ("<p>І благословеннє, яке Бог", "<h3>МИЛОСТЬ ГОСПОДНЯ.</h3>"),
            # hi
            ("<p>पहले भजन पर अपने मनन में", "<h3>भूमिका।</h3>"),
            ("<p>पहले अध्याय के आठवें पद", "<h3>परमेश्वर की साक्षी और चुनौती।</h3>"),
            ("<p>पहले अध्याय के आठवें पद",
             '<p><em>"यहोवा ने दिया और यहोवा ही ने लिया; यहोवा का नाम धन्य है</em>।"—अय्यूब 1:21।</p>'),
            ("<p>शैतान का उत्तर ध्यान देने", "<h3>अदृश्य बाड़ा।</h3>"),
            ("<p>अय्यूब के वृत्तान्त पर", "<h3>अय्यूब की परीक्षा</h3>"),
            ("<p>और शीघ्र ही शैतान ने उस", "<h3>शैतान की दुष्टता।</h3>"),
            ("<p>परन्तु जिसने परीक्षा भेजी", "<h3>पर्याप्त अनुग्रह।</h3>"),
            ("<p>तथापि, जैसा हमने देखा,", "<h3>और गहरी परीक्षाएँ।</h3>"),
            ("<p>और न ही परमेश्वर ने अपने", "<h3>प्रभु की करुणा।</h3>"),
            # ar
            ("<p>في تأمّلاتنا في المزمور", "<h3>مقدّمة.</h3>"),
            ("<p>في العدد الثامن من الأصحاح", "<h3>شهادة الله وتحدّيه.</h3>"),
            ("<p>في العدد الثامن من الأصحاح",
             "<p><em>«الربّ أعطى والربّ أخذ، فليكن اسم الربّ مباركًا</em>». — أيّوب 1:21.</p>"),
            ("<p>وجواب الشيطان جديرٌ بالملاحظة.", "<h3>السياج غير المنظور.</h3>"),
            ("<p>ونعود إلى تاريخ أيّوب:", "<h3>امتحان أيّوب</h3>"),
            ("<p>وسرعان ما أظهر الشيطان", "<h3>خبث الشيطان.</h3>"),
            ("<p>ولكنّ الذي أرسل التجربة", "<h3>نعمة كافية.</h3>"),
            ("<p>على أنّ تجربة أيّوب لم", "<h3>تجارب أعمق.</h3>"),
            ("<p>ولم تكن البركة التي أعطاها", "<h3>رحمة الربّ.</h3>"),
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
    "school-of-prayer": {
        # Every lesson's body opens by restating its heading as three blocks —
        # "<h2>FIRST LESSON.</h2>", the motto, and the "Or, …" subtitle — above
        # the verse the lesson actually begins with. The reader shows the title
        # already and the verse carries the motto, so the run goes. The
        # importer's own strip misses it: "First Lesson" is not a CHAPTER
        # ordinal, and no single block restates the whole TOC title. Also the
        # Preface's "——0——" ornament, and ch33's heading, which CCEL broke
        # across an <h2> and a <p> (the chapter title carries it).
        "replacements": [
            ("<p>——0——</p> ", ""),
            ("<h2>GEORGE MULLER, AND THE SECRET OF HIS</h2> <p>POWER IN PRAYER</p> ", ""),
            # CCEL dates the Preface 1895; the book is 1885, and Murray's own
            # note (ch33) has Müller, born 1805, "now eighty years of age".
            ("<p>WELLINGTON, 28<i><sup>th</sup> October</i> 1895 </p>",
             "<p>WELLINGTON, 28<i><sup>th</sup> October</i> 1885 </p>"),
            # Ch21's opening verse lost its opening quote (every sibling has it).
            ("<p>I go unto the Father. And whatsoever", "<p>‘I go unto the Father. And whatsoever"),
            # Spaces the transcription left before a comma.
            ("in the Spirit of Christ , the Spirit", "in the Spirit of Christ, the Spirit"),
            ("<p>‘LORD , TEACH US TO", "<p>‘LORD, TEACH US TO"),
            ("how to use God’s word , and to trust", "how to use God’s word, and to trust"),
            ("room for thirty children , and in", "room for thirty children, and in"),
            # Ch18's NOTE quotes a quotation: the inner mark opens with a
            # closing curl (‘” where ‘“ is meant).
            ("<p>‘”<i>God hears prayer</i>.”", "<p>‘“<i>God hears prayer</i>.”"),
            ("<h2>FIRST LESSON.</h2> <h3>‘Lord, teach us to pray;’</h3> <h3><i>Or, The Only Teacher</i> . </h3>  ", ""),
            ("<h2>SECOND LESSON.</h2> <h3>‘In spirit and truth.’</h3> <h3>Or, The True Worshippers.</h3> ", ""),
            ("<h2>THIRD LESSON.</h2> <h3>‘Pray to thy Father, which is in secret;’</h3> <h3><i>Or, Alone with God</i>. </h3>  ", ""),
            ("<h2>FOURTH LESSON</h2> <h3>‘After this manner pray;’</h3> <h3>Or, The Model Prayer.</h3>  ", ""),
            ("<h2>FIFTH LESSON.</h2> <h3>'Ask, and it shall be given you'</h3> <h3>Or, The Certainty of the Answer to Prayer.</h3>  ", ""),
            ("<h2>SIXTH LESSON.</h2> <h3>‘How much more?’</h3> <h3>Or, The Infinite Fatherliness of God.</h3>  ", ""),
            ("<h2>SEVENTH LESSON.</h2> <h3>‘How much more the Holy Spirit;</h3> <h3>Or, The All-Comprehensive Gift.</h3>  ", ""),
            ("<h2>EIGHTH LESSON.</h2> <h3>‘Because of his importunity;’</h3> <h3>Or, The Boldness of God’s Friends.</h3>  ", ""),
            ("<h2>NINTH LESSON.</h2> <h3>‘Pray the Lord of the harvest;’</h3> <h3><i>Or, Prayer provides Labourers</i>. </h3>  ", ""),
            ("<h2>TENTH LESSON.</h2> <h3>‘What wilt thou?’</h3> <h3>Or, Prayer must be Definite.</h3>  ", ""),
            ("<h2>ELEVENTH LESSON.</h2> <h3>‘Believe that ye have received;’</h3> <h3>Or, The Faith that Takes.</h3>  ", ""),
            ("<h2>TWELFTH LESSON.</h2> <h3>‘Have faith in God;’</h3> <h3>Or, The Secret of Believing Prayer.</h3>  ", ""),
            ("<h2>THIRTEENTH LESSON.</h2> <h3>‘Prayer and fasting;’</h3> <h3><i>Or, The Cure of Unbelief</i>. </h3>  ", ""),
            ("<h2>FOURTEENTH LESSON.</h2> <h3>‘When ye stand praying, forgive;’</h3> <h3><i>Or, Prayer and Love</i>. </h3>  ", ""),
            ("<h2>FIFTEENTH LESSON.</h2> <h3>‘If two agree;’</h3> <h3>Or, The Power of United Prayer</h3>  ", ""),
            ("<h2>SIXTEENTH LESSON.</h2> <h3>‘Speedily, though bearing long;’</h3> <h3>Or, The Power of Persevering Prayer.</h3>  ", ""),
            ("<h2>SEVENTEENTH LESSON.</h2> <h3>‘I know that Thou hearest me always;’</h3> <h3>Or Prayer in Harmony with the Being of God.</h3>  ", ""),
            ("<h2>EIGHTEENTH LESSON</h2> <h3>‘Whose is this image?’</h3> <h3><i>Or, Prayer in Harmony with the Destiny of Man</i>. </h3>  ", ""),
            ("<h2>NINTEENTH LESSON.</h2> <h3>‘I go unto the Father!’</h3> <h3>Or, Power for Praying and Working.</h3>  ", ""),
            ("<h2>TWENTIETH LESSON.</h2> <h3>‘That the Father may be glorified;’</h3> <h3>Or, The Chief End of Prayer.</h3>  ", ""),
            ("<h2>TWENTY-FIRST LESSON.</h2> <h3>‘If ye abide in me;’</h3> <h3><i>Or The All-Inclusive Condition</i>. </h3>  ", ""),
            ("<h2>TWENTY-SECOND LESSON.</h2> <h3>‘My words in you.’</h3> <h3><i>Or, The Word and Prayer</i>. </h3>  ", ""),
            ("<h2>TWENTY-THIRD LESSON</h2> <h3>‘Bear fruit, that the Father may give what ye ask;’</h3> <h3><i>Or, Obedience the Path to Power in Prayer</i>. </h3>  ", ""),
            ("<h2>TWENTY-FOURTH LESSON.</h2> <h3> ‘In my Name;’</h3> <h3><i>Or, The All-prevailing Plea</i>. </h3>  ", ""),
            ("<h2>TWENTY-FIFTH LESSON.</h2> <h3>‘At that day;’</h3> <h3>Or, The Holy Spirit and Prayer.</h3>  ", ""),
            ("<h2>TWENTY-SIXTH LESSON.</h2> <h3>‘I have prayed for thee;’</h3> <h3>Or, Christ the Intercessor.</h3>  ", ""),
            ("<h2>TWENTY-SEVENTH LESSON.</h2> <h3>‘Father, I will;’</h3> <h3>Or, Christ the High Priest</h3>  ", ""),
            ("<h2>TWENTY-EIGHTH LESSON.</h2> <h3>‘Father! Not what I will;’</h3> <h3>Or, Christ the Sacrifice.</h3>  ", ""),
            ("<h2>TWENTY-NINTH LESSON.</h2> <h3>‘According to His will;</h3> <h3><i>Or, Our Boldness in Prayer</i>. </h3>  ", ""),
            ("<h2>THIRTIETH LESSON.</h2> <h3>‘An holy priesthood;’</h3> <h3>Or, The Ministry of Intercession.</h3>  ", ""),
            ("<h2>THIRTY-FIRST LESSON.</h2> <h3>‘Pray without ceasing;’</h3> <h3>Or, A Life of Prayer.</h3>  ", ""),
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

# OCR/typo slips found while translating Murray's book to Portuguese (batch 6); scattered one-word mechanical errors, each grammar- or KJV-forced.
BODY_CORRECTIONS.setdefault('true-vine', {}).setdefault("replacements", []).extend([
    ('what as unspeakable blessedness', 'what an unspeakable blessedness'),
    ('pleases and edified', 'pleases and edifies'),
    ('may posses me', 'may possess me'),
    ('receive it from the vine sap', 'receive from the vine sap'),
    ('shaper than any two-edged', 'sharper than any two-edged'),
    ('much more cloth us', 'much more clothe us'),
    ('how He ask and claims', 'how He asks and claims'),
    ('He point us to the love', 'He points us to the love'),
    ('he hold nothing back', 'he holds nothing back'),
    ('tells us plainly out of how', 'tells us plainly how'),
    ('who do so few realize it', 'why do so few realize it'),
    ('and My Words, Abide in You', 'and My Words Abide in You'),
    ('keep us. we thought', 'keep us. We thought'),
])

# OCR slips in Whitefield's sermon (batch 6); each grammar/sense-forced. 'not removed'->'now removed': as printed the clause is a flat contradiction (sword not removed YET free access given to the tree of life).
BODY_CORRECTIONS.setdefault('christ-the-believers-wisdom', {}).setdefault("replacements", []).extend([
    ('they do or ill enjoy', 'they do or will enjoy'),
    ('is not removed, and free access', 'is now removed, and free access'),
    ('Christ is mad to you', 'Christ is made to you'),
    ('that Chris is their Emmanuel', 'that Christ is their Emmanuel'),
    ('become string; so strong', 'become strong; so strong'),
    ('esteem it o:', 'esteem it so:'),
    ('they will the very being of sin', 'then will the very being of sin'),
    ('but this I what we are', 'but this is what we are'),
    ('trump of God given the general', 'trump of God give the general'),
    ('to build you hopes of salvation', 'to build your hopes of salvation'),
])

# OCR/citation slips in Edwards's sermon (batch 6). 'divine divinity'->'divine dignity' (the phrase Edwards uses 4x elsewhere). Three misprinted refs corrected to the verse actually quoted: Matt 11:28-30 ('Come unto me'), Ps 65:7 ('stilleth the noise of the seas'), Ps 89:8 ('O Lord God of hosts').
BODY_CORRECTIONS.setdefault('the-excellency-of-christ', {}).setdefault("replacements", []).extend([
    ('committed himself God.', 'committed himself to God.'),
    ('not so torment them', 'not to torment them'),
    ('his divine divinity and glory', 'his divine dignity and glory'),
    ('Matt. 9:28 30', 'Matt. 11:28-30'),
    ('Psalm 115:7', 'Psalm 65:7'),
    ('Psalm 139:8f', 'Psalm 89:8f'),
])

# OCR slip found while translating the sermon to Portuguese (batch 5): the
# opening hymn line (Spurgeon quotes a couplet) begins with a drop-cap "OH"
# and a closing quote after "praise?" but no opening quote — clears the
# audit's orphan-close-quote (baseline re-pinned).
BODY_CORRECTIONS.setdefault("the-shameful-sufferer", {}).setdefault("replacements", []).append(
    ("<p>OH what shall I do", "<p>“OH what shall I do")
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
    # sw job #2595. Goodwin's Paul "sits nearest the God-man ... in glory"; "fits"
    # is the long-s/f misread (es "se sienta", fr "siège").
    ("fits nearest the God-man", "sits nearest the God-man"),
    # to "put up" a prayer, as the same sermon says three times; "put us" is a
    # one-letter slip (es "elevabais", fr "faisant monter").
    ("when ye put us these prayers", "when ye put up these prayers"),
    # dropped "of": "to the honor of Christianity" (pt/es/fr all render it so).
    ("to the honor Christianity", "to the honor of Christianity"),
    # two possessives that lost their "s" ("God's sake" is spelled out 3x here).
    ("sitting on Christ' right hand", "sitting on Christ's right hand"),
    ("creatures for God' sake", "creatures for God's sake"),
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

# Found while translating True Vine to Spanish (batch 2): ch04's "The branch has
# no cure" is an OCR slip for "no care" — the sentence's point is that the branch
# is free of anxiety because "the vine provides all; it has but to yield itself
# and receive". A cure/care r/u misread; the context is decisive.
BODY_CORRECTIONS.setdefault("true-vine", {}).setdefault("replacements", []).extend([
    ("The branch has no cure;", "The branch has no care;"),
])

# OCR/extraction slips found while translating batch 3 to Spanish. All are
# unambiguous letter/dittography damage with a single reading.
# Transcription slips in CCEL's files of Fox's Book of Martyrs (Forbush ed.).
BODY_CORRECTIONS.setdefault("foxes-book-of-martyrs", {}).setdefault("replacements", []).extend([
    # A pound sign mis-encoded as &#156; (cp1252 "œ"): Sands's sureties were
    # "each one bound in £500".
    ("each one bound in œ500,", "each one bound in £500,"),
    # Missing spaces.
    ("was only alarmed thathis Savior's", "was only alarmed that his Savior's"),
    ("articles of faith.With him suffered", "articles of faith. With him suffered"),
    # Stray space before a comma.
    ("on pain of death , to throw", "on pain of death, to throw"),
])
BODY_CORRECTIONS.setdefault("separation-and-service", {}).setdefault("replacements", []).extend([
    # "know th Master's" -> "know the Master's".
    ("know th Master's", "know the Master's"),
])
# Gutenberg #26384 closes ch4 on the printed "THE END." and then its own
# transcriber's note (a `div.tn`, "Mismatched and inconsistent punctuation has
# been retained…"), which shipped as the chapter's last block and the es edition
# translated. The book ends on "THE END."
BODY_CORRECTIONS["separation-and-service"]["back_matter"] = [
    ("crucified for us.</p> <p>THE END.</p>", "<p>Transcriber's Note:<br/>"),
    ("crucificado por nosotros.</p> <p>FIN.</p>", "<p>Nota del transcriptor:<br/>"),
]
BODY_CORRECTIONS.setdefault("the-fourfold-gospel", {}).setdefault("replacements", []).extend([
    # "lie will lead" -> "He will lead" (l/H, ie/e misread).
    ("and lie will lead you", "and He will lead you"),
    # doubled word.
    ("crowd until until they", "crowd until they"),
    # dittography: "material idea of the material idea of the millennial".
    ("material idea of the material idea of the millennial",
     "material idea of the millennial"),
])
BODY_CORRECTIONS.setdefault("a-short-and-easy-method-of-prayer", {}).setdefault("replacements", []).extend([
    # section heading lowercased "god" -> "God".
    ("Mysteries—god Gives Them", "Mysteries—God Gives Them"),
])
# OCR slips found while translating batch 4 (Richard Allen's autobiography).
BODY_CORRECTIONS.setdefault("life-experience-gospel-labours", {}).setdefault("replacements", []).extend([
    # Philadelphia's Lombard Street (spelled correctly elsewhere in the text).
    ("near Lobard street", "near Lombard street"),
    # "photograph" is impossible in an 1833 text; OCR for "paragraph" (a
    # paragraph in Carey's 2d edition).
    ("censorious photograph,", "censorious paragraph,"),
])
# OCR slips found while translating batch 5 (E. M. Bounds's prayer books).
BODY_CORRECTIONS.setdefault("essentials-of-prayer", {}).setdefault("replacements", []).extend([
    # Stray scan page-markers left mid-line inside two hymn stanzas.
    ("breasts [Pg 104]<br/>", "breasts<br/>"),
    ("give, [Pg 58]<br/>", "give,<br/>"),
    # The Spanish edition was translated before the pairs above landed and
    # carried both markers over; the es fixture is settled by hand to match.
    ("compasivos [Pg 104]<br/>", "compasivos<br/>"),
    ("que dar, [Pg 58]<br/>", "que dar,<br/>"),
])
BODY_CORRECTIONS.setdefault("purpose-in-prayer", {}).setdefault("replacements", []).extend([
    # "sifts" -> "gifts" (s/g misread): "They are God's gifts."
    ("God’s sifts", "God’s gifts"),
    # "abot" -> "about".
    ("hedge abot a single night", "hedge about a single night"),
    # "(f" -> "if" (paren for the ascender of i).
    ("but (f the prayer", "but if the prayer"),
    # "tune" -> "time": "At another time he puts on record".
    ("At another tune he puts on record", "At another time he puts on record"),
    # "theme" -> "them" (Exodus 32:10, "that I may destroy them").
    ("that I may destroy theme—But Moses", "that I may destroy them—But Moses"),
    # "St. Patti" -> "St. Paul".
    ("epistle of St. Patti is", "epistle of St. Paul is"),
    # Stray leading periods from OCR joins.
    ("much .longer than we do", "much longer than we do"),
    ("for his .ministry, that", "for his ministry, that"),
    ("praying warmed into. life a new life", "praying warmed into life a new life"),
])
# OCR slips found while translating batch 6 (E. M. Bounds's prayer books).
BODY_CORRECTIONS.setdefault("reality-of-prayer", {}).setdefault("replacements", []).extend([
    # "words" -> "worlds" (parallel to "conserves all interests"): "touches all worlds".
    ("touches all words, conserves", "touches all worlds, conserves"),
    # "and" -> "are": "God's great and most precious gifts are conditioned on asking".
    ("gifts and conditioned on asking", "gifts are conditioned on asking"),
    # "preadventure" -> "peradventure".
    ("preadventure", "peradventure"),
])
# Gutenberg #73032 prints the Revell colophon and a nine-page "EVANGELISTIC WORK"
# catalogue (Hillis, Torrey, Sundar Singh … "Hartford Courant.") after Bounds's
# last paragraph, inside ch16's section, and the es edition translated all sixty
# blocks of it. The book ends on "prevailing prayer." in the 1924 printing.
BODY_CORRECTIONS["reality-of-prayer"]["back_matter"] = [
    ("definite, prevailing prayer.</p>",
     "<p><i>Printed in the United States of America</i></p>"),
    ("definida y prevaleciente.</p>",
     "<p><i>Impreso en los Estados Unidos de América</i></p>"),
]
# Gutenberg #29426 ends ch35 on the printer's imprint, "LONDON: MORGAN AND
# SCOTT", then its own "Transcriber's Notes" (`div.tnote`: punctuation repaired,
# page 146 taken from the 1903 edition). Both shipped as the chapter's tail, and
# the sw edition translated the notes. The book ends on "you will pray more."
BODY_CORRECTIONS["things-as-they-are"]["back_matter"] = [
    ("you will pray more.</p>", "<br/><br/><br/><br/> LONDON: MORGAN AND SCOTT<br/>"),
    ("mtaomba zaidi.</p>", "<br/><br/><br/><br/> LONDON: MORGAN AND SCOTT<br/>"),
]
# Gutenberg #65066 follows "…revival of true religion! Amen." with the ATS
# donors' line and the transcriber's `tnotes` endnote. The note's heading was
# never collected, so its three paragraphs read as Edwards's own last words —
# and the sw edition translated them as such.
BODY_CORRECTIONS.setdefault("life-and-diary-of-david-brainerd", {})["back_matter"] = [
    ("true religion! <i>Amen.</i></p>",
     "<p>The frequent dated quotations from Brainerd’s diaries"),
    ("dini ya kweli! <i>Amina.</i></p>",
     "<p>Manukuu ya mara kwa mara yenye tarehe kutoka shajara za Brainerd"),
]
# Gutenberg #51931 follows Torrey's last paragraph with a page break and the
# Revell ad page for F. B. Meyer (its price tables were dropped; the Moody,
# Stalker and Kempis blurbs survived), and then a sub-300-word "Transcriber's
# Notes" section that the importer merged into ch13 as an <h3> and its errata.
BODY_CORRECTIONS.setdefault("how-to-bring-men-to-christ", {})["back_matter"] = [
    ("before God can use them.</p>",
     "<p>“<i>Few books of recent years are better adapted to instruct"),
]
BODY_CORRECTIONS.setdefault("prayer-and-praying-men", {}).setdefault("replacements", []).extend([
    # "Betelguese" -> "Betelgeuse".
    ("Betelguese", "Betelgeuse"),
    # "pats" -> "puts".
    ("prayer pats God into", "prayer puts God into"),
    # dittography: "from heaven falls from heaven".
    ("No fire from heaven falls from heaven", "No fire falls from heaven"),
    # transposition (1 Kings 17:18): "What have I to do with thee".
    ("What have I do to with thee", "What have I to do with thee"),
    # missing space.
    ("a mere vaporing ofintellectual", "a mere vaporing of intellectual"),
    # stray period.
    ("The united prayer. of the praying king", "The united prayer of the praying king"),
    # "hopelessly" -> "hopeless".
    ("nothing is hopelessly to God", "nothing is hopeless to God"),
    # "be" -> "he".
    ("where be really had the life", "where he really had the life"),
    # biblical name: "Eleazer" -> "Eleazar".
    ("whose son Eleazer was appointed", "whose son Eleazar was appointed"),
    # missing space.
    ("the prayers ofan illiterate", "the prayers of an illiterate"),
    # lowercase sentence start after a period.
    ("business of praying. it gives us", "business of praying. It gives us"),
    # "authentative" -> "authoritative".
    ("directory and authentative", "directory and authoritative"),
    # "wess" -> "west".
    ("getting wess out of Manchester", "getting west out of Manchester"),
    # "Thee" -> "Three".
    ("Thee days was he without sight", "Three days was he without sight"),
    # "wrok" -> "work".
    ("Paul work his wrok", "Paul work his work"),
    # scripture (Acts 16:26): "every one's bands were loosed".
    ("every one’s ban was loosed", "every one’s bands were loosed"),
    # "prefunctory" -> "perfunctory".
    ("in a routine, prefunctory manner", "in a routine, perfunctory manner"),
    # biblical name (Acts 13:1): "Manean" -> "Manaen".
    ("of Cyrene, and Manean, which", "of Cyrene, and Manaen, which"),
    # "tetrach" -> "tetrarch".
    ("Herod the tetrach", "Herod the tetrarch"),
    # "though" -> "through".
    ("salvation though your prayer", "salvation through your prayer"),
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


# A block's opening or closing tag, for `wrap_loose_blocks`: where a loose run
# ends, and whether a position already sits inside a block.
_EDGE_BREAKS = _re.compile(r"^(?:\s|<br\s*/?>)+|(?:\s|<br\s*/?>)+$")
_LEAD_BREAKS = _re.compile(r"^(?:\s|<br\s*/?>)+")
_BLOCK_EDGE = _re.compile(r"<(/?)(?:p|h[1-6]|blockquote|ul|ol|li|table|hr)\b[^>]*>", _re.I)


def wrap_loose_blocks(body_html: str, blocks: Sequence[tuple[str, ...]]) -> str:
    """Give a flattened display line back its block: `(head, tag)` wraps the
    loose run that opens with `head` in `<tag>…</tag>`.

    The Gutenberg importer once handed a centred display line — a `<div>`
    heading, dateline, signature, or a whole paragraph set as a drop-cap div —
    to the sanitizer, which unwrapped it. The text shipped, but as loose text
    between blocks: an opening paragraph with no `<p>`, a heading as an
    unmarked run. `ingest.display_line` keeps them now; this repairs the rows
    imported before it, which are never re-imported.

    Not `restored_blocks`: nothing is missing, so inserting would say it twice.
    Not a `replacements` pair either: the run is often a whole paragraph, and
    a pair would have to quote all of it. `head` names where the line starts;
    it ends where the next block begins, where another of the work's heads
    begins (two lines flattened into one run: "MARY'S SONG" and the song under
    it), or — given a third element, `(head, tag, tail)` — right after `tail`,
    for a line that ran into loose text which is NOT a display line (an
    illustration's caption). A `<br>` at the line's edge goes, as
    `display_line` drops it; an `<h3>` holds plain text, as `display_line`
    writes it. So each wrap is exactly the block a re-import emits, which is
    what `tests_english_audit` checks, entry by entry, against the importer.

    Idempotent by GUARD, like `restore_dropped_blocks`: a `head` that already
    sits inside a block is skipped — the settled form, and a future re-import
    that emits the block itself. `body_html` ONLY: the wrap adds tags.
    """
    if "<" not in body_html:
        return body_html  # tagless: `body_text`, which must never gain tags
    heads = [entry[0] for entry in blocks]
    for head, tag, *tail in blocks:
        start = 0
        while (i := body_html.find(head, start)) >= 0:
            start = i + len(head)
            edges = list(_BLOCK_EDGE.finditer(body_html, 0, i))
            if edges and not edges[-1].group(1) and not edges[-1].group(0).lower().startswith("<hr"):
                continue  # inside a block: already wrapped
            m = _BLOCK_EDGE.search(body_html, i)
            end = m.start() if m else len(body_html)
            for other in heads:
                j = body_html.find(other, i + 1, end)
                if other != head and j >= 0:
                    end = j
            if tail:
                j = body_html.find(tail[0], i, end)
                if j < 0:
                    break  # the line is not what this entry describes
                end = j + len(tail[0])
            text = _EDGE_BREAKS.sub("", body_html[i:end])
            if tag == "h3":
                # The same text rule as `display_line`: a space at each <br>,
                # other markup joined ("<span>ALL</span>." is "ALL.").
                text = _escape(html_to_text(text), quote=False)
            rest = _LEAD_BREAKS.sub("", body_html[end:])
            body_html = f"{body_html[:i]}<{tag}>{text}</{tag}> {rest}".rstrip()
            break
    return body_html


def strip_back_matter(body_html: str, seams: Sequence[tuple[str, str]]) -> str:
    """Cut the publisher's or transcriber's back matter off a work's last chapter.

    Each seam is `(last, first)`: the closing block of the author's text (ending
    on `</p>`) and the opening block of what the importer carried in after it —
    a colophon, a catalogue, a transcriber's note. Only where the two stand
    together does everything after `last` go, so it cannot fire anywhere but
    the one place it was written for, and it is idempotent because the cut
    removes `first`.

    `body_html` ONLY: both halves carry block tags, which the tagless
    `body_text` never holds; `Chapter.save()` re-derives it from the cut HTML.
    """
    for last, first in seams:
        at = _re.search(_re.escape(last) + r"\s*" + _re.escape(first), body_html)
        if at:
            body_html = body_html[: at.start() + len(last)]
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

    The structural keys run after the replacements, so a replacement must not
    reach into text one of them rewrites: anchor a deletion on what comes
    BEFORE it, or `test_no_replacement_pair_is_dead` finds neither side (the
    a-retrospect MIDI note). Back matter is cut before `wrapped_blocks` wraps,
    so a wrap can never run on into a tail that is about to go.
    """
    entry = BODY_CORRECTIONS.get(slug)
    if entry:
        for old, new in entry.get("replacements", []):
            body_html = body_html.replace(old, new)
        body_html = restore_paragraph_breaks(body_html, entry.get("paragraph_breaks", ()))
        body_html = restore_dropped_blocks(body_html, entry.get("restored_blocks", ()))
        body_html = strip_back_matter(body_html, entry.get("back_matter", ()))
        body_html = wrap_loose_blocks(body_html, entry.get("wrapped_blocks", ()))
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


# --- PT batch 7: English source fixes (companion to PT PR #1861) ---
# Gleanings Among the Sheaves (Spurgeon), Catholic Spirit (Wesley),
# God Glorified in Man's Dependence (Edwards). OCR/formatting defects the PT
# translators surfaced; the PT ships the corrected reading (fix-forward).
BODY_CORRECTIONS.setdefault('gleanings-among-the-sheaves', {}).setdefault("replacements", []).extend([
    # ch16 leaked Gutenberg back-matter (INDEX page-list + Transcriber's Notes)
    # fused onto the final reading; not Spurgeon. Same strip ships in the PT
    # fixture. Remove the whole block.
    ("<h2>INDEX.</h2> PAGE 5 7 8 10 11 13 16 18 21 23 24 27 30 32 34 37 39 41 41 42 44 47 48 49 51 53 54 56 57 58 59 60 61 62 63 64 66 67 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 89 91 92 93 94 95 97 99 101 103 104 106 106 107 108 109 110 111 111 112 113 114 115 116 117 118 120 122 123 123 124 124 125 127 128 129 130 132 134 136 137 139 139 140 141 142 145 145 146 146 147 149 150 152 153 155 156 157 158 160 162 165 166 167 169 172 173 174 176 177 178 181 182 184 185 187 190 192 194 196 197 199 202 207 209 212 214 218 221 <hr/> <p>Transcriber's Notes: Blank pages have been eliminated. Variations in spelling and hyphenation have been left as in the original. A few typographical errors have been corrected. </p>", ""),
    # (Three scripture quotations also lost their opening quote in OCR — Phil
    # 4:8 ch02, Job 42:10 ch03, Ps 37:4 ch18. Those openers are repaired
    # directly in the fixture, not here. The reason given was that a
    # straight-quote `new` could not satisfy the corrections-hygiene guard,
    # which read the JSON-serialised fixture where a straight quote is escaped
    # as \" — THAT CONSTRAINT IS GONE: the guard now reads the field values, so
    # a straight-quoted pair is fine and these three could move into
    # BODY_CORRECTIONS if anyone wants them re-applied on every deploy. Left in
    # the fixture for now because nothing is broken by it.)
    # ch05 dropped letter; ch08 KJV spelling; ch13 2 Pet 3:11 ("what manner of
    # persons ought ye to be", KJV) garbled to "manner or person".
    ('take way his own power', 'take away his own power'),
    ('per-adventure', 'peradventure'),
    ('What manner or person ought', 'What manner of persons ought'),
])
BODY_CORRECTIONS.setdefault('catholic-spirit', {}).setdefault("replacements", []).extend([
    # The fifth numbered head lost its period (every sibling reads "N.").
    ('<p>5 I mean, Secondly', '<p>5. I mean, Secondly'),
    # "convinced of this, act according to the law" — the comma turns the OCR'd
    # run-on back into Wesley's imperative.
    ('convinced of this act according', 'convinced of this, act according'),
])
BODY_CORRECTIONS.setdefault('god-glorified-in-mans-dependence', {}).setdefault("replacements", []).extend([
    # Two misprinted citations: the promise of the Spirit is Acts 2:33 (2:13 is
    # the mockers) and Eph 1:13 (Ephesians has six chapters, not thirty-three).
    ('Acts 2:13.', 'Acts 2:33.'),
    ('Eph. 1:33. This', 'Eph. 1:13. This'),
    # "in making the soul" — leading "in" clipped to a bare "m".
    ('perfection, m making the soul', 'perfection, in making the soul'),
])
# OCR slips found while translating Wesley's sermon to Swahili (#2593). CCEL and
# the Wesley Center share one bad transcription, so each pair is checked against
# two independent printings of Sermons on Several Occasions (archive.org
# sermonsonseveral0001revj, 1825, and sermonsonseveral0001wesl, 1852), which
# agree on every reading. Their period spacing ("obscurity ?", "him ;”") stays.
BODY_CORRECTIONS.setdefault('the-circumcision-of-the-heart', {}).setdefault("replacements", []).extend([
    ('a liar form the beginning', 'a liar from the beginning'),
    ('world; thought he would choose', 'world; though he would choose'),
    # Eph 1:19-20 ("the exceeding greatness of his power ... when he raised
    # Christ"); the hyphen welded "to quicken", and Rom 8:11's opening quote
    # was printed as a closer.
    ('the exceeding greatness of this power,” who, as he raise up Christ from the dead, so is able to-quicken us, dead in sin,” by his',
     'the exceeding greatness of his power,” who, as he raised up Christ from the dead, so is able to quicken us, dead in sin, “by his'),
    # Eccl 9:10.
    ('“whatever his findeth to do', '“whatever his hand findeth to do'),
    ('which is no subject to the law', 'which is not subject to the law'),
    ('the sole End, us well as Source', 'the sole End, as well as Source'),
    ('Have no end, to ultimate end', 'Have no end, no ultimate end'),
    ('“whereby be is very far gone', '“whereby he is very far gone'),
    # 2 Cor 4:18.
    ('the things that arc seen, which are temporal, but at the things that arc not seen',
     'the things that are seen, which are temporal, but at the things that are not seen'),
    ('the Inspirer an Perfecter', 'the Inspirer and Perfecter'),
    ('learn, that it none is truly', 'learn, that none is truly'),
    ('a view to own happiness ! Nay', 'a view to our own happiness! Nay'),
    ('one who v. as “conceived', 'one who was “conceived'),
    ('them to perform ? — as if', 'them to perform? — as if'),
    ('nor grace was sufficient for them.?</p>', 'nor his grace was sufficient for them?</p>'),
    ('without taking any pains at all. Vain hope !', 'without taking any pains at all. Vain hope!'),
    ('<p>8. What lees than this', '<p>8. What less than this'),
    # 2 Cor 6:4-5 ("in afflictions ... in distresses"); 1 Cor 13:3.
    ('living “ill infirmities', 'living “in infirmities'),
    ('and have not love, it profit me nothing', 'and have not love, it profiteth me nothing'),
    # 1 Cor 9:26: the closing quote and "By" were lost, fusing the verse into
    # Wesley's next clause.
    ('one that beateth the air which he plainly teaches', 'one that beateth the air:” By which he plainly teaches'),
    ('Let it be continual offered up', 'Let it be continually offered up'),
    ('This is the way where in those', 'This is the way wherein those'),
    ('<p>5. this is that lowliness', '<p>5. This is that lowliness'),
    ('No man I say, has A title', 'No man, I say, has a title'),
    ('the world, the one who follow him not', 'the world, the men who follow him not'),
])


# --- Quotation marks closed with the wrong mark (2026-09-11) -----------------
#
# Found while repairing the-bruised-reed, then swept corpus-wide: quotations
# whose CLOSING mark is the wrong glyph, in two shapes that
# `tests_fixture.QuoteStyleTests` could not see (it counts double marks, and a
# straight single is also an apostrophe):
#
#   * a curly opener closed by a STRAIGHT mark — ‘Search the scriptures', says
#     … (the Whitefield sermons, christ-the-believers-wisdom en+pt,
#     waiting-on-god in four editions): the singles half-curled;
#   * an OPENER used as the closer — it is written “the living God“; — thirteen
#     of them in evening-by-evening alone, and every quotation in pt
#     all-things-for-good ch9–11. Most follow an inline tag (`“<i>seen</i>“`):
#     `quote_marks.convert` counted ANY tag's `>` as opening context. That is
#     fixed at the source now, so a rebuild through it cannot set them again.
#
# Typography only: each pair turns one mark (or moves the space beside it) and
# no word changes, apart from the one OCR slip the niger scan confirms. Each
# pair carries just enough context to match ONCE across every edition of its
# slug, because an entry reaches every language on every deploy.
# `QuoteStyleTests.test_no_quotation_closes_with_the_wrong_mark` now holds the
# corpus at zero. (The English-audit baseline GREW by five `orphan-close-quote`
# findings: each backwards closer had counted as an opener and masked a real
# orphan further on. All five predate this repair.)
#
# NOT repaired here: sermons-on-several-occasions. Its unpaired marks ("of one
# heart “and one soul?”") are in CCEL's text and in the Wesley Center's
# transcription of the 1872 Jackson edition alike, so they are not ours, and
# each one needs a printed scan to settle.
# a-retrospect: two “…“ closers.
BODY_CORRECTIONS.setdefault("a-retrospect", {}).setdefault("replacements", []).extend([
    ("chï fu mu</i>“ ", "chï fu mu</i>” "),
    ("convenience!</i>“ ", "convenience!</i>” "),
])
# Gutenberg #26744 sets "The Missionary Call" in ch12 as a score image (title and
# verse 1) with its own note under it offering MIDI files; the image was dropped
# and the note shipped between the chapter's last paragraph and verse 2, links
# gone ("by clicking here for an organ version"). The es edition translated it.
# Mid-chapter, so a pair rather than a back-matter seam, anchored on the
# paragraph before it. Not on the verse after it: `wrapped_blocks` below gives
# that verse its `<p>`, so a pair ending "</p> 2. Why live" would leave nothing
# in the settled text for `test_no_replacement_pair_is_dead` to find.
BODY_CORRECTIONS["a-retrospect"]["replacements"].extend([
    ("other spheres.</p> [<i>Transcriber's Note: You can listen to this music (MIDI file) by"
     " clicking</i> here for an <br/>organ version or here for a piano version.] ",
     "other spheres.</p>"),
    ("otras esferas.</p> [<i>Nota del transcriptor: Puede escuchar esta música (archivo MIDI)"
     " haciendo clic</i> aquí para una <br/>versión de órgano o aquí para una versión de piano.] ",
     "otras esferas.</p>"),
])
# absolute-surrender: “…love“? (en, and the sw that mirrors it).
BODY_CORRECTIONS.setdefault("absolute-surrender", {}).setdefault("replacements", []).extend([
    ("Spirit is love<i>“?", "Spirit is love<i>”?"),
    ("ni upendo<i>“?", "ni upendo<i>”?"),
])
# all-things-for-good: pt ch9–11 closed EVERY quotation with an opener, “…“ — 64 of them; the other chapters and the English are right.
BODY_CORRECTIONS.setdefault("all-things-for-good", {}).setdefault("replacements", []).extend([
    ("chamados.</i>“ ", "chamados.</i>” "),
    ("escolhidos</i>“ (Mt 20:", "escolhidos</i>” (Mt 20:"),
    ("éreis trevas</i>“ ", "éreis trevas</i>” "),
    ("éramos fracos</i>“ ", "éramos fracos</i>” "),
    ("Espírito Santo</i>“ ", "Espírito Santo</i>” "),
    ("teu sangue</i>“ ", "teu sangue</i>” "),
    ("sua força</i>“ ", "sua força</i>” "),
    (" palavra</i>“ ", " palavra</i>” "),
    ("teu poder</i>“ ", "teu poder</i>” "),
    (" vocação</i>“ (2T", " vocação</i>” (2T"),
    ("santidade</i>“ (Is", "santidade</i>” (Is"),
    ("santidade</i>“ ", "santidade</i>” "),
    ("celestial</i>“ (At", "celestial</i>” (At"),
    ("vontade?</i>“ ", "vontade?</i>” "),
    ("para trás?</i>“ ", "para trás?</i>” "),
    ("ser salvo?</i>“ ", "ser salvo?</i>” "),
    (" de Deus</i>“ ", " de Deus</i>” "),
    ("chamados</i>“ (1C", "chamados</i>” (1C"),
    ("teu agrado</i>“ ", "teu agrado</i>” "),
    ("eterna glória</i>“ ", "eterna glória</i>” "),
    ("escolhidos</i>“ ", "escolhidos</i>” "),
    ("suas vestes</i>“ ", "suas vestes</i>” "),
    ("irrevogáveis</i>“ ", "irrevogáveis</i>” "),
    ("sua glória</i>“ ", "sua glória</i>” "),
    (" herança</i>“ ", " herança</i>” "),
    ("ressurreição</i>“ ", "ressurreição</i>” "),
    ("iniquidade</i>“ ", "iniquidade</i>” "),
    (" vocação</i>“ ", " vocação</i>” "),
    (" Senhor!</i>“ ", " Senhor!</i>” "),
    ("promessa</i>“ ", "promessa</i>” "),
    ("inimigos</i>“ ", "inimigos</i>” "),
    ("diante de mim</i>“ ", "diante de mim</i>” "),
    (" justiça</i>“ ", " justiça</i>” "),
    ("justificados</i>“ ", "justificados</i>” "),
    ("no Senhor</i>“ (Ef", "no Senhor</i>” (Ef"),
    ("agora vejo</i>“ ", "agora vejo</i>” "),
    ("maravilhosa luz</i>“ ", "maravilhosa luz</i>” "),
    (" pecados</i>“ ", " pecados</i>” "),
    (" da vida</i>“ ", " da vida</i>” "),
    ("está em mim</i>“ ", "está em mim</i>” "),
    ("eu faça?</i>“ ", "eu faça?</i>” "),
    ("celestial</i>“ ", "celestial</i>” "),
    ("o sempre</i>“ ", "o sempre</i>” "),
    (" Satanás</i>“ ", " Satanás</i>” "),
    ("Caindo em si</i>“ ", "Caindo em si</i>” "),
    ("chamados</i>“ ", "chamados</i>” "),
    ("peculiar</i>“ ", "peculiar</i>” "),
    ("esta regra</i>“ ", "esta regra</i>” "),
    (" geração</i>“ ", " geração</i>” "),
    ("no Senhor</i>“ ", "no Senhor</i>” "),
    ("alegrar-se</i>“ ", "alegrar-se</i>” "),
    ("sua cabeça</i>“ ", "sua cabeça</i>” "),
    ("corteses</i>“ ", "corteses</i>” "),
    (" de Hete</i>“ ", " de Hete</i>” "),
    ("salvar alguns</i>“ ", "salvar alguns</i>” "),
    ("propósito</i>“ ", "propósito</i>” "),
    ("de Deus.</i>“ ", "de Deus.</i>” "),
    ("que quer</i>“ ", "que quer</i>” "),
    (" e graça</i>“ ", " e graça</i>” "),
    ("naquele dia</i>“ ", "naquele dia</i>” "),
    ("fôssemos santos</i>“ ", "fôssemos santos</i>” "),
    (" eleição</i>“ ", " eleição</i>” "),
    ("santificação</i>“ ", "santificação</i>” "),
    ("de Cristo</i>“ ", "de Cristo</i>” "),
])
# christ-the-believers-wisdom: curly ‘ openers closed by a straight ' — 25 in en, 49 in pt.
BODY_CORRECTIONS.setdefault("christ-the-believers-wisdom", {}).setdefault("replacements", []).extend([
    (" redemption.'</p><p>W", " redemption.’</p><p>W"),
    ("Wisdom, righteousness, sanctification, and redemption'.", "Wisdom, righteousness, sanctification, and redemption’."),
    ("made unto us', th", "made unto us’, th"),
    ("in his hands'.", "in his hands’."),
    (" where I am.' ", " where I am.’ "),
    ("of the world';", "of the world’;"),
    ("of the world'.", "of the world’."),
    ("of the Father'.", "of the Father’."),
    ("made unto us',", "made unto us’,"),
    (" in the Lord'.", " in the Lord’."),
    (" redemption.'</p>", " redemption.’</p>"),
    ("he possesses';", "he possesses’;"),
    ("riches for others';", "riches for others’;"),
    ("Know thyself',", "Know thyself’,"),
    ("righteousness':", "righteousness’:"),
    ("that believeth'.", "that believeth’."),
    ("that condemns?' ", "that condemns?’ "),
    ("of great joy';", "of great joy’;"),
    ("Savior is born'.", "Savior is born’."),
    ("say, rejoice'.", "say, rejoice’."),
    ("righteousness'.", "righteousness’."),
    ("Jesus our Lord',", "Jesus our Lord’,"),
    ("are become new',", "are become new’,"),
    ("fullness of God'.", "fullness of God’."),
    ("thus with men!' ", "thus with men!’ "),
    (" e redenção.'</p><p>S", " e redenção.’</p><p>S"),
    ("feito por Deus'.", "feito por Deus’."),
    ("‘sabedoria, justiça, santificação e redenção'.", "‘sabedoria, justiça, santificação e redenção’."),
    ("feito por Deus':", "feito por Deus’:"),
    ("prosperaria na sua mão'.", "prosperaria na sua mão’."),
    ("onde eu estou.' ", "onde eu estou.’ "),
    ("fundação do mundo';", "fundação do mundo’;"),
    ("fundação do mundo'.", "fundação do mundo’."),
    (" por meu Pai'.", " por meu Pai’."),
    ("feito por Deus',", "feito por Deus’,"),
    ("somente no Senhor'.", "somente no Senhor’."),
    (" e redenção.'</p>", " e redenção.’</p>"),
    ("bens que possui';", "bens que possui’;"),
    ("suas riquezas';", "suas riquezas’;"),
    ("te a ti mesmo',", "te a ti mesmo’,"),
    ("sabedoria, justiça':", "sabedoria, justiça’:"),
    ("aquele que crê'.", "aquele que crê’."),
    ("que condena?' ", "que condena?’ "),
    ("grande alegria';", "grande alegria’;"),
    (" um Salvador'.", " um Salvador’."),
    (" alegrai-vos'.", " alegrai-vos’."),
    ("justiça nossa'.", "justiça nossa’."),
    ("nosso Senhor',", "nosso Senhor’,"),
    (" se fez novo' ", " se fez novo’ "),
    ("plenitude de Deus'.", "plenitude de Deus’."),
    ("com os homens!'?", "com os homens!’?"),
    ("santificação.' ", "santificação.’ "),
    ("concupiscência',", "concupiscência’,"),
    ("não cobiçarás'.", "não cobiçarás’."),
    ("santificação'.", "santificação’."),
    ("amamos os irmãos.' ", "amamos os irmãos.’ "),
    ("redenção</i>.'", "redenção</i>.’"),
    ("diz ‘Haja luz',", "diz ‘Haja luz’,"),
    ("Deus justiça',", "Deus justiça’,"),
    (": ‘foi feito';", ": ‘foi feito’;"),
    ("que eu tenho'.", "que eu tenho’."),
    ("no último dia'.", "no último dia’."),
    ("vinde ao juízo';", "vinde ao juízo’;"),
    ("claro que o sol'.", "claro que o sol’."),
    ("tua vitória?'", "tua vitória?’"),
    ("Sobe para cá';", "Sobe para cá’;"),
    ("contra a carne'.", "contra a carne’."),
    ("desta morte?' ", "desta morte?’ "),
    ("se nos disse'.", "se nos disse’."),
    ("aquele que crê.' ", "aquele que crê.’ "),
    ("e sem preço.' ", "e sem preço.’ "),
    ("pecadores. ‘A nós',", "pecadores. ‘A nós’,"),
    (", idólatras.' ", ", idólatras.’ "),
    ("santificação e redenção'.", "santificação e redenção’."),
])
# comfort-for-the-desponding: “Oh “says one, pit! “But, earnest? “O, Jesus—“It — the closer's space on the wrong side; and ”‘Oh, a closer used as the opener.
BODY_CORRECTIONS.setdefault("comfort-for-the-desponding", {}).setdefault("replacements", []).extend([
    ("matters.</i> “Oh “s", "matters.</i> “Oh” s"),
    (" to the pit! “B", " to the pit!” B"),
    ("not earnest? “O", "not earnest?” O"),
    ("you may say, ”‘", "you may say, “‘"),
    ("Christ Jesus—“I", "Christ Jesus—” I"),
])
# divine-healing: a “… .“ closer (en, hi, pt).
BODY_CORRECTIONS.setdefault("divine-healing", {}).setdefault("replacements", []).extend([
    ("give ear... .“ ", "give ear... .” "),
    ("कान लगाए...।“ ", "कान लगाए...।” "),
    ("ouvidos... .“ ", "ouvidos... .” "),
])
# evening-by-evening: “seen“, “If“ ×5, “and“ … — thirteen backwards closers.
BODY_CORRECTIONS.setdefault("evening-by-evening", {}).setdefault("replacements", []).extend([
    ("“<i>seen</i>“ ", "“<i>seen</i>” "),
    ("was there;</i>“ ", "was there;</i>” "),
    ("condescension</i>“ ", "condescension</i>” "),
    ("clean hands</i>“ ", "clean hands</i>” "),
    ("<i>weeping</i>“.", "<i>weeping</i>”."),
    ("said nots</i>“ ", "said nots</i>” "),
    (". “<i>If</i>“ ", ". “<i>If</i>” "),
    ("me--“<i>if</i>“ ", "me--“<i>if</i>” "),
    ("temptation--“<i>if</i>“ ", "temptation--“<i>if</i>” "),
    ("--“<i>if</i>“ ", "--“<i>if</i>” "),
    (", “<i>if</i>“ ", ", “<i>if</i>” "),
    (" “<i>and</i>“ ", " “<i>and</i>” "),
    ("<i>Christ</i>“-", "<i>Christ</i>”-"),
])
# grace-for-grace-2: “it is finished. “Many — the closer's space on the wrong side; and “presentings, left open.
BODY_CORRECTIONS.setdefault("grace-for-grace-2", {}).setdefault("replacements", []).extend([
    ("is finished. “M", "is finished.” M"),
    ("presentings, ", "presentings,” "),
])
# journal-of-an-expedition-up-the-niger: ‘ denge,' / ‘ Mary,' closers; and 'got oft“ by', which the 1855 scan reads "got off by backing the engine" (OCR: oflF).
BODY_CORRECTIONS.setdefault("journal-of-an-expedition-up-the-niger", {}).setdefault("replacements", []).extend([
    ("she was got oft“ ", "she was got off "),
    ("called ‘ denge,' ", "called ‘ denge,’ "),
    ("schooner ‘ Mary,' ", "schooner ‘ Mary,’ "),
])
# let-us-pray-2: a “…priesthood“ closer.
BODY_CORRECTIONS.setdefault("let-us-pray-2", {}).setdefault("replacements", []).extend([
    ("royal priesthood“ ", "royal priesthood” "),
])
# life-and-diary-of-david-brainerd: a stray “ after one of its 160 dated entries ("<i>Nov. 4.</i>—" everywhere else).
BODY_CORRECTIONS.setdefault("life-and-diary-of-david-brainerd", {}).setdefault("replacements", []).extend([
    ("<i>Nov. 4.</i>“—", "<i>Nov. 4.</i>—"),
])
# morning-by-morning: “Nevertheless“--, “shall be filled“, “taste“, “thou“--.
BODY_CORRECTIONS.setdefault("morning-by-morning", {}).setdefault("replacements", []).extend([
    ("Nevertheless</i>“-", "Nevertheless</i>”-"),
    ("be filled</i>“ ", "be filled</i>” "),
    ("<i>taste</i>“ ", "<i>taste</i>” "),
    ("“<i>thou</i>“-", "“<i>thou</i>”-"),
])
# order-and-argument-in-prayer: a “…thy will.“ closer (en, pt, sw).
BODY_CORRECTIONS.setdefault("order-and-argument-in-prayer", {}).setdefault("replacements", []).extend([
    ("thy will.</i>“ ", "thy will.</i>” "),
    ("vontade.</i>“ ", "vontade.</i>” "),
    ("mapenzi yako.</i>“ ", "mapenzi yako.</i>” "),
])
# our-daily-walk: “running over “ (, “I AM _____ “ says, conquerors! “ These, “…Abide in Me“--.
BODY_CORRECTIONS.setdefault("our-daily-walk", {}).setdefault("replacements", []).extend([
    (" “I AM _____ “ ", " “I AM _____” "),
    (" conquerors! “ ", " conquerors!” "),
    ("running over “ ", "running over” "),
    ("Abide in Me</b>“-", "Abide in Me</b>”-"),
])
# purpose-in-prayer: a “…kicked you out?“ closer.
BODY_CORRECTIONS.setdefault("purpose-in-prayer", {}).setdefault("replacements", []).extend([
    ("kicked you out?“ ", "kicked you out?” "),
])
# selected-sermons-whitefield: curly ‘ openers closed by a straight ' (the same text as the walking-with-god and christ-the-believers-wisdom sermons). "disciples' heads" is a possessive and stays.
BODY_CORRECTIONS.setdefault("selected-sermons-whitefield", {}).setdefault("replacements", []).extend([
    ("created he them.' ", "created he them.’ "),
    (" not strewed'.", " not strewed’."),
    ("walked with God'.", "walked with God’."),
    ("God took him'.", "God took him’."),
    (" against him'.", " against him’."),
    (" pleased God';", " pleased God’;"),
    ("walked with God.' ", "walked with God.’ "),
    ("walked with God';", "walked with God’;"),
    ("and I did eat'.", "and I did eat’."),
    ("God himself.' ", "God himself.’ "),
    ("present with him';", "present with him’;"),
    ("regenerated.' ", "regenerated.’ "),
    (" are agreed?' ", " are agreed?’ "),
    ("dwelling in us'.", "dwelling in us’."),
    ("and with them';", "and with them’;"),
    (" also walked'.", " also walked’."),
    ("walked with God', th", "walked with God’, th"),
    (" to strength';", " to strength’;"),
    (" of the Lord'. In", " of the Lord’. In"),
    ("known to all men'.", "known to all men’."),
    ("Jesus Christ'.", "Jesus Christ’."),
    ("walked with God',", "walked with God’,"),
    ("the scriptures',", "the scriptures’,"),
    ("testify of me'.", "testify of me’."),
    ("unto his paths';", "unto his paths’;"),
    ("day and night'.", "day and night’."),
    ("thyself to reading',", "thyself to reading’,"),
    ("of thy mouth'.", "of thy mouth’."),
    ("It is written'.", "It is written’."),
    ("of the Spirit'.", "of the Spirit’."),
    ("None like this'.", "None like this’."),
    ("the holy mount';", "the holy mount’;"),
    (" your hearts':", " your hearts’:"),
    ("secret prayer''", "secret prayer’'"),
    ("Praying always',", "Praying always’,"),
    ("supplication.' ", "supplication.’ "),
    ("Watch and pray',", "Watch and pray’,"),
    (" temptation.' ", " temptation.’ "),
    (" my God here'.", " my God here’."),
    ("and meditation',", "and meditation’,"),
    ("I was musing',", "I was musing’,"),
    ("fire kindled.' ", "fire kindled.’ "),
    ("in the flesh',", "in the flesh’,"),
    ("heavenly Father'.", "heavenly Father’."),
    ("thyself from idols':", "thyself from idols’:"),
    ("me thy heart'.", "me thy heart’."),
    ("from providence',", "from providence’,"),
    ("to feed upon.' ", "to feed upon.’ "),
    ("Spirit of God',", "Spirit of God’,"),
    ("commandments, blameless'.", "commandments, blameless’."),
    (" of the Lord'.", " of the Lord’."),
    (" ‘My delight',", " ‘My delight’,"),
    ("that do excel' ", "that do excel’ "),
    (" his friend?' ", " his friend?’ "),
    ("with the king'.", "with the king’."),
    ("delighteth to honor?' ", "delighteth to honor?’ "),
    ("delighteth to honor.' ", "delighteth to honor.’ "),
    ("of his master'.", "of his master’."),
    (" ungodliness'.", " ungodliness’."),
    (" paths peace'.", " paths peace’."),
    ("in the world'.", "in the world’."),
    ("perfect freedom'.", "perfect freedom’."),
    ("you speak of?' ", "you speak of?’ "),
    (" of this way',", " of this way’,"),
    ("them falsely'.", "them falsely’."),
    ("exceeding glad',", "exceeding glad’,"),
    ("everlasting life'.", "everlasting life’."),
    ("quantam et qualem',", "quantam et qualem’,"),
    ("seventy years',", "seventy years’,"),
    ("presence of my God?' ", "presence of my God?’ "),
    ("and lofty One',", "and lofty One’,"),
    (" at my word.' ", " at my word.’ "),
    (" of my mouth'.", " of my mouth’."),
    ("us wisdom, righteousness, sanctification, and redemption.' ", "us wisdom, righteousness, sanctification, and redemption.’ "),
    ("Wisdom, righteousness, sanctification, and redemption'.", "Wisdom, righteousness, sanctification, and redemption’."),
    ("made unto us', th", "made unto us’, th"),
    ("in his hands'.", "in his hands’."),
    (" where I am.' ", " where I am.’ "),
    ("of the world';", "of the world’;"),
    ("of the world'.", "of the world’."),
    ("of the Father'.", "of the Father’."),
    ("made unto us',", "made unto us’,"),
    (" in the Lord'.", " in the Lord’."),
    (" redemption.' </p> <p", " redemption.’ </p> <p"),
    ("he possesses';", "he possesses’;"),
    ("riches for others';", "riches for others’;"),
    ("Know thyself',", "Know thyself’,"),
    ("righteousness':", "righteousness’:"),
    ("that believeth'.", "that believeth’."),
    ("that condemns?' ", "that condemns?’ "),
    ("of great joy';", "of great joy’;"),
    ("Savior is born'.", "Savior is born’."),
    ("say, rejoice'.", "say, rejoice’."),
    ("righteousness'.", "righteousness’."),
    ("Jesus our Lord',", "Jesus our Lord’,"),
    ("are become new',", "are become new’,"),
    ("fullness of God'.", "fullness of God’."),
    ("thus with men!' ", "thus with men!’ "),
])
# spurgeon-on-prayer: a “…thy will.“ closer (en, sw).
BODY_CORRECTIONS.setdefault("spurgeon-on-prayer", {}).setdefault("replacements", []).extend([
    ("thy will.</i>“ ", "thy will.</i>” "),
    ("mapenzi yako.</i>“ ", "mapenzi yako.</i>” "),
])
# stepping-stones-2: lg ‘…' closers (the straight marks inside words are Luganda orthography and stay).
BODY_CORRECTIONS.setdefault("stepping-stones-2", {}).setdefault("replacements", []).extend([
    ("‘okuyitibwa,' ", "‘okuyitibwa,’ "),
    ("Abooluganda.'", "Abooluganda.’"),
    ("Abooluganda?' ", "Abooluganda?’ "),
    ("eky'‘eddiini.' ", "eky'‘eddiini.’ "),
    ("okutuuka ku balala' ", "okutuuka ku balala’ "),
])
# the-immutability-of-god: a fully reversed pair, ”shall be“ (en, hi, pt, sw); two fr ‘…' closers.
BODY_CORRECTIONS.setdefault("the-immutability-of-god", {}).setdefault("replacements", []).extend([
    ("Nevertheless it says ”<i>shall be</i>“ ", "Nevertheless it says “<i>shall be</i>” "),
    ("voilà à terre;' ", "voilà à terre;’ "),
    ("à ta maison.' ", "à ta maison.’ "),
    (" वहाँ अब भी ”<i>ठहराया जाएगा</i>“ ", " वहाँ अब भी “<i>ठहराया जाएगा</i>” "),
    ("está escrito ”<i>será</i>“.", "está escrito “<i>será</i>”."),
    ("hivyo inasema ”<i>atahukumiwa</i>“ ", "hivyo inasema “<i>atahukumiwa</i>” "),
])
# the-inner-chamber: “to help him “; and a ‘…!' closer (en, hi).
BODY_CORRECTIONS.setdefault("the-inner-chamber", {}).setdefault("replacements", []).extend([
    ("and keep it!&#x27; ", "and keep it!’ "),
    ("“to help him “;", "“to help him”;"),
    ("और मानते हैं!&#x27; ", "और मानते हैं!’ "),
])
# the-life-of-trust: a “…fear him.“ closer.
BODY_CORRECTIONS.setdefault("the-life-of-trust", {}).setdefault("replacements", []).extend([
    ("fear him.</i>“", "fear him.</i>”"),
])
# the-normal-christian-life: two ‘ quotations closed straight, one of them opened with a backtick. (The book's other `…' quotations are a separate, unrepaired class.)
BODY_CORRECTIONS.setdefault("the-normal-christian-life", {}).setdefault("replacements", []).extend([
    ("will of God?&#x27; T", "will of God?’ T"),
    ("which says, `Get all you can for as little as possible. ‘T", "which says, ‘Get all you can for as little as possible.’ T"),
])
# thoughts-for-the-quiet-hour: “the living God“; and three more.
BODY_CORRECTIONS.setdefault("thoughts-for-the-quiet-hour", {}).setdefault("replacements", []).extend([
    ("living God</i>“;", "living God</i>”;"),
    ("than these!</i>“—", "than these!</i>”—"),
    ("be safe!</i>“—", "be safe!</i>”—"),
    ("<i>sincere</i>“—", "<i>sincere</i>”—"),
])
# waiting-on-god: ‘…' closers in ch07/13/20/28, in every edition that mirrors them (en, hi, pt, sw).
BODY_CORRECTIONS.setdefault("waiting-on-god", {}).setdefault("replacements", []).extend([
    ("all the day.' </i>Wai", "all the day.’ </i>Wai"),
    ("inherit the land.' ", "inherit the land.’ "),
    ("waited for Him.' ", "waited for Him.’ "),
    ("will hear me.' A", "will hear me.’ A"),
    ("हता रहता हूँ।' </i>दिन", "हता रहता हूँ।’ </i>दिन"),
    ("िकारी होंगे।' ", "िकारी होंगे।’ "),
    ("ोहते आए हैं।' क", "ोहते आए हैं।’ क"),
    ("मेरी सुनेगा।' ए", "मेरी सुनेगा।’ ए"),
    (" o dia todo.' </i>Esp", " o dia todo.’ </i>Esp"),
    ("herdarão a terra.' ", "herdarão a terra.’ "),
    ("esperamos por ele.' ", "esperamos por ele.’ "),
    ("vai me ouvir.' U", "vai me ouvir.’ U"),
    ("mchana kutwa.' </i>Kun", "mchana kutwa.’ </i>Kun"),
    ("watairithi nchi.' ", "watairithi nchi.’ "),
    ("Tumemngojea.' ", "Tumemngojea.’ "),
    (" atanisikia.' Tar", " atanisikia.’ Tar"),
])
# walking-with-god: curly ‘ openers closed by a straight ' — 71.
BODY_CORRECTIONS.setdefault("walking-with-god", {}).setdefault("replacements", []).extend([
    (" not strewed'.", " not strewed’."),
    ("walked with God'.", "walked with God’."),
    ("God took him'.", "God took him’."),
    (" against him'.", " against him’."),
    (" pleased God';", " pleased God’;"),
    ("walked with God.' ", "walked with God.’ "),
    ("walked with God';", "walked with God’;"),
    ("and I did eat'.", "and I did eat’."),
    ("God himself.' ", "God himself.’ "),
    ("present with him';", "present with him’;"),
    (" are agreed?' ", " are agreed?’ "),
    ("dwelling in us'.", "dwelling in us’."),
    ("and with them';", "and with them’;"),
    (" also walked'.", " also walked’."),
    ("walked with God', th", "walked with God’, th"),
    (" to strength';", " to strength’;"),
    (" of the Lord'. In", " of the Lord’. In"),
    ("known to all men'.", "known to all men’."),
    ("Jesus Christ'.", "Jesus Christ’."),
    ("walked with God',", "walked with God’,"),
    ("the scriptures',", "the scriptures’,"),
    ("testify of me'.", "testify of me’."),
    ("unto his paths';", "unto his paths’;"),
    ("day and night'.", "day and night’."),
    ("thyself to reading',", "thyself to reading’,"),
    ("of thy mouth'.", "of thy mouth’."),
    ("It is written'.", "It is written’."),
    ("of the Spirit'.", "of the Spirit’."),
    ("None like this'.", "None like this’."),
    ("the holy mount';", "the holy mount’;"),
    (" your hearts':", " your hearts’:"),
    ("secret prayer''", "secret prayer’'"),
    ("Praying always',", "Praying always’,"),
    ("supplication.' ", "supplication.’ "),
    ("Watch and pray',", "Watch and pray’,"),
    (" temptation.' ", " temptation.’ "),
    (" my God here'.", " my God here’."),
    ("and meditation',", "and meditation’,"),
    ("I was musing',", "I was musing’,"),
    ("fire kindled.' ", "fire kindled.’ "),
    ("in the flesh',", "in the flesh’,"),
    ("heavenly Father'.", "heavenly Father’."),
    ("thyself from idols':", "thyself from idols’:"),
    ("me thy heart'.", "me thy heart’."),
    ("from providence',", "from providence’,"),
    ("to feed upon.' ", "to feed upon.’ "),
    ("Spirit of God',", "Spirit of God’,"),
    ("commandments, blameless'.", "commandments, blameless’."),
    (" of the Lord'.", " of the Lord’."),
    (" ‘My delight',", " ‘My delight’,"),
    ("that do excel' ", "that do excel’ "),
    (" his friend?' ", " his friend?’ "),
    ("with the king'.", "with the king’."),
    ("delighteth to honor?' ", "delighteth to honor?’ "),
    ("delighteth to honor.' ", "delighteth to honor.’ "),
    ("of his master'.", "of his master’."),
    (" ungodliness'.", " ungodliness’."),
    (" paths peace'.", " paths peace’."),
    ("in the world'.", "in the world’."),
    ("perfect freedom'.", "perfect freedom’."),
    ("you speak of?' ", "you speak of?’ "),
    (" of this way',", " of this way’,"),
    ("them falsely'.", "them falsely’."),
    ("exceeding glad',", "exceeding glad’,"),
    ("everlasting life'.", "everlasting life’."),
    ("quantam et qualem',", "quantam et qualem’,"),
    ("seventy years',", "seventy years’,"),
    ("presence of my God?' ", "presence of my God?’ "),
    ("and lofty One',", "and lofty One’,"),
    (" at my word.' ", " at my word.’ "),
    (" of my mouth'.", " of my mouth’."),
])

# Transcription artifacts in the SermonIndex sermons (Tozer / Lloyd-Jones),
# each forced by grammar or the KJV text quoted — stray spaces before
# punctuation, a spaced ellipsis, a suspended hyphen written as "health- or",
# and one fused word. Per-slug and English-only; keeps the corpus English audit
# flat on import.
BODY_CORRECTIONS.setdefault("the-salt-of-the-earth", {}).setdefault("replacements", []).append(
    ("health- or life-giving", "health-giving or life-giving")
)
BODY_CORRECTIONS.setdefault("god-or-mammon", {}).setdefault("replacements", []).append(
    ("income tax return .... ! Certainly", "income tax return...! Certainly")
)
BODY_CORRECTIONS.setdefault("jesus-on-prayer", {}).setdefault("replacements", []).append(
    ('their reward." ,</p>', 'their reward."</p>')
)
BODY_CORRECTIONS.setdefault("the-parable-of-the-prodigal-son", {}).setdefault("replacements", []).append(
    ("same chapter , they", "same chapter, they")
)
BODY_CORRECTIONS.setdefault("working-out-our-own-salvation", {}).setdefault("replacements", []).append(
    ("socalled", "so-called")
)
BODY_CORRECTIONS.setdefault("the-wrath-of-god", {}).setdefault("replacements", []).extend([
    ('sinned . . .".', 'sinned...".'),
    ("this mean ? I", "this mean? I"),
])

# Transcription artifacts in the R. A. Torrey sermons (SermonIndex): a doubled
# comma, and parenthetical/clause dashes typed as a spaced hyphen ("-a personal
# friend-") — restored to em dashes. Per-slug and English-only; keeps the corpus
# English audit flat on re-import.
BODY_CORRECTIONS.setdefault("refuges-of-lies", {}).setdefault("replacements", []).extend([
    ("Brooklyn,, he", "Brooklyn, he"),
    ("dying- His wife", "dying—His wife"),
])
BODY_CORRECTIONS.setdefault("excuses", {}).setdefault("replacements", []).extend([
    ("to me -a personal friend- and", "to me—a personal friend—and"),
    ("under guard -for they dared not trust him alone- and",
     "under guard—for they dared not trust him alone—and"),
])
BODY_CORRECTIONS.setdefault("the-most-important-question", {}).setdefault("replacements", []).extend([
    ("to-night -I care not what position in society you hold- I charge",
     "to-night—I care not what position in society you hold—I charge"),
    ("mighty grip -and it was a mighty grip- and",
     "mighty grip—and it was a mighty grip—and"),
])
BODY_CORRECTIONS.setdefault("the-way-of-salvation-made-plain", {}).setdefault("replacements", []).append(
    ("to be -my Lord, having right to the absolute control of my life- I will",
     "to be—my Lord, having right to the absolute control of my life—I will")
)
BODY_CORRECTIONS.setdefault("heroes-and-cowards", {}).setdefault("replacements", []).extend([
    ("cheeks -he was a little white-haired Swedish boy- and",
     "cheeks—he was a little white-haired Swedish boy—and"),
    ("think of it- to have", "think of it—to have"),
])
BODY_CORRECTIONS.setdefault("the-drama-of-life-in-three-acts", {}).setdefault("replacements", []).extend([
    ("his own way- It is either", "his own way—It is either"),
    ("their feebleness- The old man", "their feebleness—The old man"),
])

# Corrie ten Boom "How to Forgive" (SermonIndex) opens with an emcee's spoken
# introduction — two paragraphs that are not ten Boom — before she takes over
# ("Corrie? I'm so glad I am again here."). Strip the introduction so the sermon
# begins with her own words. Removing it also clears the hyphen-space audit
# finding it carried ("Corrie Ten- Corrie Tenboom").
BODY_CORRECTIONS.setdefault("how-to-forgive", {}).setdefault("replacements", []).append(
    (
        "<p>It's a real pleasure to introduce Corrie Ten- Corrie Tenboom to you. "
        "To many of you, I don't think she needs an introduction. But I'm going to "
        "introduce her by what she calls herself, a tramp for Jesus.</p><p>That's "
        "just a servant of Jesus. I think that's the best way that we could say "
        "Corrie is just a servant of Jesus Christ, just like all of us are here "
        "this morning. And if his servant comes, as his servants are sitting out "
        "there, let's just listen to what Jesus wants to say to us in a personal "
        "way today.</p><p>Corrie? ",
        "<p>",
    )
)

# Isaac Watts, Divine Songs, "Against evil Company" st.1 l.3 — an OCR slip read
# "but never pray" as "but never play", flattening the stanza's contrast (children
# who curse/swear but never PRAY). The wrong word was copied faithfully into the
# Swahili edition ("hawachezi kamwe", they never play → "hawaombi kamwe", they never
# pray); the Luganda edition already rendered the correct sense. Each pair only bites
# its own language. Found while translating into Luganda, 2026-09-18.
BODY_CORRECTIONS.setdefault("divine-songs-for-children", {}).setdefault("replacements", []).extend([
    ("but never play;", "but never pray;"),
    ("hawachezi kamwe", "hawaombi kamwe"),
])

# Christmas Evans, "The Triumph of Calvary": two slips in the Gutenberg text.
# "the devil arid his legions" is an OCR misreading of "and". "the Son of
# Righteousness shall shine" misquotes Malachi 4:2, paired with "the bright and
# Morning Star" as the sun rising after the star, so the intended word is "Sun".
# The editions AGREE: es ("el Sol de justicia" / "el diablo y sus legiones"), fr
# ("le soleil de la justice" / "le diable et ses légions") and sw ("Jua la Haki" /
# "Ibilisi na majeshi yake") all render the corrected reading. Found while
# translating into Swahili (#2594).
BODY_CORRECTIONS.setdefault("the-triumph-of-calvary", {}).setdefault("replacements", []).extend([
    ("the devil arid his legions", "the devil and his legions"),
    ("“the Son of Righteousness” shall shine", "“the Sun of Righteousness” shall shine"),
])

# Finney, Lectures on Revivals of Religion — the print edition's page numbers,
# 414 of them (pp. 4-445), left in the running text by OCR. Two shapes:
#
# * BETWEEN blocks, a bare "</p>16<p>" where a page broke at a paragraph end.
#   Listed by page number: the shape is anchored on markup, so it can never
#   match the tagless body_text.
# * IN PROSE, usually fused to the next word ("the 10excitability", "object.
#   19Even"), a handful spaced or wedged between tags ("encouraged, 336
#   <i>before", "</i>387<i>in", "ghost.</p> 92 <p>There"). Listed as the defective string, each unique
#   across the whole book; `_unpage` deletes the number and nothing else.
#
# Not a corpus rule. A digit welded to a word is also an ordinal ("a 7th of
# Romans experience", "the 15th Psalm" — both in this book), and what proved
# each of these a page number is that together they count up the book one page
# at a time, with only the unnumbered chapter-opening pages missing. That is
# evidence about one edition, not a pattern safe to run over every work.
_REVIVAL_PAGES_BETWEEN_BLOCKS = (
    4, 16, 26, 42, 51, 59, 68, 74, 77, 81, 84, 89, 103, 116, 117, 123, 125, 126,
    131, 132, 146, 164, 165, 170, 173, 177, 182, 198, 216, 219, 245, 253, 258,
    274, 278, 279, 291, 302, 305, 318, 320, 327, 330, 331, 337, 347, 359, 362,
    366, 371, 379, 384, 386, 395, 417, 423, 430, 431, 438
)
_REVIVAL_PAGES_IN_PROSE = (
    "texts, 5and", "the 10excitability", "reasoning 11may", "done 12in", "among 13its",
    "that 14there", "backslidden 15state,", "clearness 17in", "requested 18to",
    "object. 19Even", "own 20agency", "of 21missions,", "proportion 23to", "of 24such",
    "there 25is", "the 27wicked", "salvation 28of", "minister 29put", "come 30without",
    "church 31all", "confession 32of", "not 33mean", "city; 34and", "the 36heart,",
    "on 37any", "and 38write", "was 39still", "Look 40round", "religion, 41and",
    "deception 43is", "have 44weakened", "will 45recollect", "up 46a", "as 47it",
    "Spirit 49of", "expect 50to", "comforted. 52He", "or 53importunity", "pray 54for",
    "prevailing 55prayer,", "I 56have", "God, 57whose", "fellow 58creatures,",
    "nothing 60but", "exceptions 61about", "plunge, 62and", "is 63often", "hope 64of",
    "prayers 65more", "persevere 66in", "necessary 69to", "bread 70to", "come 71in",
    "ought 72to", "not 73understand", "not 75stand", "I 76sent", "and 78asked",
    "parable 79of", "And 80it", "converted? 82One", "of 85sinners", "been 86amazed",
    "willing 87to", "I 88do", "any 90feeling", "selfishness. 91The",
    "ghost.</p> 92 <p>There", "all 93saints,", "receive 94it", "as 95in",
    "considered 96rather", "minds 97to", "I 98want", "God, 99and", "I 100have",
    "his 102influences", "If 104they", "conscience 105gripping", "controversy 106with",
    "conviction. 107In", "is 108great,", "the 109best", "his 110body", "know 111how",
    "ministers 113and", "to 114use", "my 115own", "in 119prayer.", "I 120began",
    "mock 121God,", "would 122naturally", "confidence 124in", "any 127thing",
    "young 128converts", "say 129they", "confess 130their", "sectional 133prayer",
    "sort 135of", "he 136knows", "you 137believed", "a 138full", "children 139that",
    "that 140they", "East, 141who", "man 142always", "and 143paid",
    "are 144determined", "sinners 145would", "It 147says,", "churches 148could",
    "the 150man", "be 151dormant,", "another, 152and", "work, 153which",
    "many 154people", "disappointment, 155or", "took 156his", "individual, 157and",
    "golden 158rule", "they 159have", "the 160work", "proceeded, 161her",
    "that 163the", "efforts 167that", "requires 168more", "and 169run", "out 171and",
    "manner, 172I", "them 174again", "skillfully 175adapt", "should 176do.",
    "Christ, 178without", "be 179such,", "educated 180on", "bless 181a", "age 183and",
    "seminary, 184to", "overlooked 186the", "shall 187plunge", "heart 188is",
    "go 189to", "regulate 190practice.", "hunt 191them", "little 192else", "by 193and",
    "impassioned, 194the", "preaching, 195another", "predestination, 196free-agency,",
    "his 197mind", "people 199do", "ancient 200history,", "audience, 201and",
    "feel 202what", "Christian 203religion.", "Christ 204pleaded", "medicine 205to",
    "as 206to", "is 207only", "writing, 208is", "them, 209and", "fiction, 210should",
    "down 211the", "so 212sure", "if 214they", "take 215open", "it, 217and",
    "church 218openly,", "a 220revival,", "so 221proper,", "for 222their",
    "for 223you", "they 224are", "whole 225souls", "became 226depressed",
    "own 227house", "wasting 228his", "meeting. 229If", "to 230watch",
    "</i> 231<i>doing", "amount 232of", "their 233minister", "raise 234them",
    "I 235have", "pay 236this", "never 237succeed,", "the 239dark",
    "soldiers. 240They", "in 241the", "hardly 242worship", "a 243time,",
    "Presbyterian 244church,", "years, 246female", "tear 247off", "of 248divinity,",
    "they 249were", "the 250A", "doubtless 251be", "Otherwise 252Christians",
    "heart 254is", "were 255anxious", "When 256he", "now 257built,",
    "them 259complain", "men 260in", "power 261and", "order.” 262We",
    "and 264distract", "Lord. 265If", "hundred 266years", "members 267have",
    "a 268great", "of 269residence", "work, 270unless", "opposition, 271and",
    "on 272any", "their 273minds.", "deplore. 275To", "them, 276and", "itself 277put",
    "they 280have", "revivals.” 281And", "consented. 283They", "circulated, 284and",
    "I 285know", "exclude 286persons", "Every 287body", "us 288on", "It 289is",
    "better. 290I", "vain 292to", "that 293the", "the 295object.", "in 296to",
    "children, 297even", "attend 298to", "accordingly, 299so", "prevailing 300prayer,",
    "influences 301are", "individuals 303agree", "</i> 304<i>sinners</i>.",
    "the 306members", "thwart 307each", "praying 308for", "meaning, 309as",
    "for 310the", "then 311undo", "united 312may", "promoting 313revivals",
    "understand 314all", "duty; 315let", "Multitudes 316of", "a 319precise",
    "And 321therefore", "has 322always", "as 323Nicodemus", "distressed, 324for",
    "his 325distress.", "converted, 326for", "church 328uses", "delighted 329with",
    "conviction 332so", "may 333be", "your 334son", "all 335his",
    "encouraged, 336 <i>before</i>", "benefited 338by", "Christ. 339Just",
    "are 340unwilling", "different 341sense", "friends 342had", "conflict 343with",
    "them 344with", "gone, 346they", "various 348as", "there 349has", "and 350obliged",
    "believer, 351and", "common 352life,", "Maker, 353and", "he 354leave",
    "meant 355by", "their 356hands.", "not 357in", "a 358Christian.", "you,” 360and",
    "and 361plainly", "the 363soul,", "thou 365me", "and 367make", "up. 368They",
    "whenever 369they", "government, 370or", "themselves 372up",
    "respecting 373individuals", "that, 374with", "months. 375Where",
    "experience, 376if", "he 377shall", "<i>re-converted</i>, 378and",
    "<i>presumption</i>, 380that", "judgment, 381so", "not 382mean", "for 383the",
    "Instead 385of", "</i>387<i>in", "of 388the", "go 389with", "when 390they",
    "that 391money,", "to 393religion,", "are 394not", "give 396just",
    "understand 397 <i>what", "living 398generally.", "hypocritical 399face",
    "are 400young", "some 401of", "should 402be", "converts, 403and", "her 404young",
    "of 405such", "after 406a", "like 407the", "of 408young", "untaught, 409useless",
    "young 410converts.", "sinners. 411And", "stereotyped 413formal",
    "</p>414 <p>“Reason", "but 415conviction", "the 416poor,", "regarded 418as",
    "condemnation. 419He", "encouraged 420us", "I 421fear,", "is 422particular",
    "fall 424into", "anxieties 425are", "world 426are", "No 427longer", "with 429God",
    "of 432one", "confusion, 433and", "with 434him.", "may 435become",
    "complaints 436of", "and 437body", "and 439less", "monomaniacs, 440and",
    "endure 441the", "men 442have", "Christian 443intelligence.", "of 444heart",
    "been 445converted.",
)


def _unpage(defective: str) -> str:
    """Drop the one page number from a declared _*_PAGES_IN_PROSE string."""
    # One space survives if the number had one on either side: "the 10excitability"
    # -> "the excitability", "</p>414 <p>" -> "</p> <p>", "</i>387<i>" -> "</i><i>",
    # "had 36 been" -> "had been", "word.”—66And" -> "word.”—And".
    return _re.sub(
        r"(\s?)(?<=[\s>—])\d{1,3}(\s?)(?=[^\s\d])",
        lambda m: " " if m[1] or m[2] else "",
        defective,
        count=1,
    )


BODY_CORRECTIONS.setdefault("revival-lectures", {}).setdefault("replacements", []).extend(
    [(f"</p>{page}<p>", "</p> <p>") for page in _REVIVAL_PAGES_BETWEEN_BLOCKS]
    + [(defective, _unpage(defective)) for defective in _REVIVAL_PAGES_IN_PROSE]
)

# --- hurlbuts-life-of-christ: display lines flattened to loose text ------------
# Gutenberg #40460 sets each chapter's drop-cap opening paragraph as a
# `<div class="cap">`, and its centred headings ("MARY'S SONG", the title
# over the cross) and displayed verse as divs too. The importer handed those
# divs to the sanitizer, which unwrapped them: the text shipped, but as loose
# runs between blocks — 118 of them, in 103 of the 104 chapters. The importer
# keeps them now (`ingest.display_line`, PR #3355); these rows are never
# re-imported, so `wrap_loose_blocks` puts each back in the block the
# importer now emits, byte for byte (`tests_english_audit` checks every
# entry against the importer). English only: there is no translation.
# A third element ends a line that ran into an illustration's caption, which
# is not a display line and stays as it was.
BODY_CORRECTIONS.setdefault("hurlbuts-life-of-christ", {})["wrapped_blocks"] = [
    # ch1
    ('THERE HAVE been many famous', 'p'),
    ('"In the shipyard stood the', 'p'),
    # ch2
    ('FIRST OF ALL, let us take a', 'p'),
    # ch3
    ('NEARLY ALL the people living', 'p'),
    # ch4
    ('IN THE land of Palestine one', 'p'),
    ('"If I forget thee, O', 'p'),
    # ch5
    ('FOR OUR next story we visit', 'p'),
    # ch6
    ('AFTER THE visit of the angel', 'p'),
    ("MARY'S SONG", 'h3'),
    ('My soul beholds the greatness', 'p'),
    # ch7
    ("NOT LONG after Mary's visit,", 'p'),
    ('"And you, O child, shall be', 'p', 'the tender mercy of God."'),
    # ch8
    ('FOR A FEW months after their', 'p'),
    ('"Glory to God in the highest,', 'p'),
    # ch9
    ('ALTHOUGH JESUS was born in a', 'p'),
    ('"Now, Lord, thou mayest let', 'p'),
    # ch10
    ('WHILE JOSEPH and Mary with', 'p'),
    # ch11
    ('ON THE night after their', 'p'),
    # ch12
    ('THE LITTLE Jesus must have', 'p'),
    # ch13
    ('JESUS STAYED at the school in', 'p'),
    # ch14
    ('FOR EIGHTEEN years after the', 'p'),
    # ch15
    ('WHILE JESUS was still living', 'p'),
    # ch16
    ('AFTER SOME months the news', 'p', 'for baptizing the people.'),
    # ch17
    ('AFTER HIS baptism Jesus felt', 'p'),
    # ch18
    ('AFTER HIS forty days in the', 'p'),
    # ch19
    ('SOON AFTER Jesus met the men', 'p'),
    # ch20
    ('THE SPRING-TIME of the year', 'p'),
    # ch21
    ('AFTER THE Passover, Jesus', 'p'),
    # ch23
    ('SOON AFTER the visit to Cana,', 'p'),
    ('"The Spirit of the Lord is', 'p'),
    # ch24
    ('THE PLACE which Jesus chose', 'p'),
    # ch25
    ('THE STORY of the great catch', 'p'),
    # ch26
    ('FROM THE city of Capernaum', 'p'),
    # ch27
    ('SO GREAT were the crowds', 'p'),
    # ch28
    ('THE TIME came for another', 'p'),
    # ch29
    ('THE QUESTION whether Jesus', 'p'),
    # ch30
    ('ABOUT TWELVE miles southwest', 'p'),
    # ch31
    ('AT CAPERNAUM there was an', 'p'),
    # ch32
    ('JESUS WENT on a journey for', 'p'),
    # ch33
    ('WHILE JESUS was passing through southern', 'p'),
    # ch34
    ('AFTER HIS journey through', 'p'),
    # ch35
    ('SOON AFTER his journey', 'p'),
    # ch36
    ('HERE IS another parable story', 'p'),
    # ch37
    ('AFTER THE day of teaching in', 'p'),
    # ch38
    ('A GREAT CROWD of people were', 'p'),
    # ch39
    ('AS JESUS was coming out of', 'p'),
    # ch40
    ('JESUS HAD now preached in', 'p'),
    # ch41
    ('DURING NEARLY all the year of', 'p'),
    # ch42
    ('THE NEWS that King Herod had', 'p'),
    # ch43
    ('ON THE night after the multitude was fed', 'p'),
    # ch44
    ('ON THE morning after the day', 'p'),
    # ch45
    ('WITH HIS sermon on "The Bread', 'p'),
    # ch46
    ('JESUS SOON found that if he', 'p'),
    # ch47
    ('FROM THE land of the Ten', 'p'),
    # ch48
    ('FROM BETHSAIDA by the Sea of', 'p'),
    # ch49
    ('AT ONE time while Jesus was', 'p'),
    # ch50
    ('WHEN JESUS and his three', 'p'),
    # ch51
    ('WHILE JESUS was passing through Galilee for', 'p'),
    # ch52
    ('WHILE JESUS was still in', 'p'),
    # ch53
    ('AFTER MOST of those who were', 'p'),
    # ch54
    ('WHILE JESUS was on his way to', 'p'),
    # ch55
    ('AT THE TIME when Jesus came', 'p'),
    # ch56
    ('AFTER THE Feast of Tents', 'p'),
    # ch57
    ('ON A SABBATH morning, which', 'p'),
    # ch58
    ('AT THE SIDE of the Temple', 'p'),
    # ch59
    ('AFTER LEAVING Jerusalem, at', 'p'),
    # ch60
    ('WHILE JESUS was still at', 'p'),
    # ch61
    ('JESUS DID not stay long in', 'p'),
    # ch62
    ('WHILE JESUS was in Perea, on', 'p'),
    # ch63
    ('AT THIS TIME while Jesus was', 'p'),
    # ch64
    ('THE PHARISEES were very', 'p'),
    ('The Ninety and Nine', 'p'),
    ('There were ninety and nine', 'p'),
    # ch65
    ('YOU REMEMBER that the enemies', 'p'),
    # ch66
    ('AT THIS TIME Jesus gave to', 'p'),
    # ch67
    ('JESUS KNEW that the', 'p'),
    # ch68
    ('JESUS TOLD his disciples a', 'p'),
    # ch69
    ('WHILE JESUS was still passing', 'p'),
    # ch70
    ('JESUS EXPLAINED by a parable', 'p'),
    # ch71
    ('JESUS HAD now ended his work', 'p'),
    # ch72
    ('BUT BLIND Bartimeus was not', 'p'),
    # ch73
    ('FROM JERICHO to Jerusalem was', 'p'),
    # ch74
    ('THE NEWS that Jesus was at', 'p'),
    # ch75
    ('AFTER THE royal coming of', 'p'),
    # ch76
    ('AGAIN ON Tuesday morning of', 'p'),
    # ch77
    ('IMMEDIATELY after answering', 'p'),
    ('"The stone which the builders', 'p'),
    # ch78
    ('THE ENEMIES of Jesus thought', 'p', 'they could destroy Jesus.'),
    # ch79
    ('WE HAVE heard much in the', 'p'),
    # ch80
    ('WHILE JESUS was talking in', 'p'),
    ('"The Lord said to my Lord,', 'p'),
    # ch81
    ('THE ROOM in the Temple where', 'p'),
    # ch82
    ('JESUS WALKED across the Court', 'p'),
    # ch83
    ('AT THE CLOSE of a long talk', 'p', ' of the Ten Bridesmaids."'),
    # ch84
    ('THE SECOND of the three', 'p'),
    # ch85
    ('AFTER THE two parables of', 'p'),
    # ch86
    ('TUESDAY HAD been a busy day', 'p'),
    # ch87
    ('WHILE THEY were eating the', 'p'),
    # ch88
    ('JESUS SAW that his disciples', 'p'),
    # ch89
    ('JESUS WENT on giving his last', 'p'),
    # ch90
    ('DURING THE week of the', 'p'),
    # ch91
    ('THE MEN who took Jesus as', 'p'),
    # ch92
    ('THE HIGH PRIEST Caiaphas,', 'p'),
    # ch93
    ('ALTHOUGH the high council of', 'p'),
    # ch94
    ('HEROD, to whom Jesus had been', 'p'),
    # ch95
    ('WHEN PILATE sent Jesus to', 'p'),
    # ch96
    ('IN OUR TIME, and in all', 'p'),
    # ch97
    ('IT WAS the custom of the', 'p'),
    ('THIS IS JESUS OF NAZARETH', 'h3'),
    ('"They shared my garments', 'p'),
    ('"In my thirst they gave me', 'p'),
    # ch98
    ('YOU REMEMBER that from the', 'p'),
    # ch99
    ('IT WAS FRIDAY evening at', 'p'),
    # ch100
    ('All THE FOUR gospels agree in', 'p'),
    # ch101
    ('WHEN JESUS was seen after he', 'p'),
    # ch102
    ('THE MEETING place of all who', 'p'),
    # ch103
    ('ON THE NIGHT before the death', 'p'),
    # ch104
    ('SOON AFTER the appearance of', 'p'),
]

# --- a-retrospect: display lines flattened to loose text ----------------------
# Gutenberg #26744 sets each chapter's opening paragraph as a centred `<div>`
# (the drop-cap "THE following account…"), every journal dateline as a
# `<div class="right">` ("<i>January 10th.</i>"), and each displayed verse as a
# single `<div class="poem">` — the importer handed those divs to the
# sanitizer, which unwrapped them, and they shipped as 47 loose runs across the
# 20 chapters (a 48th, ch12's MIDI transcriber's note, is cut by a
# `replacements` pair above instead). Where a poem's div also held the prose
# line after it ("seemed particularly appropriate…", "To be absent from the
# body!…", "but also that when we fail…"), the importer now emits two blocks,
# and the second head splits the run.
# `ingest.display_line` keeps these (PR #3355); `wrap_loose_blocks` puts each
# back in the block the importer emits, byte for byte but for the quotation
# marks, curled in the fixture since (`tests_english_audit` checks every
# English entry against the importer). ch18's opener keeps the fixture's
# "[3]" footnote marker, which the importer does not carry.
#
# Every edition at once — `tests_translation_markup` pins the tag sequence.
# The es edition carries the same 47 runs in the same places, so its entries
# follow the English one for one, each headed by the Spanish run's own opening.
# Left loose: ch20's back matter "or" / "or to" between the mission addresses
# (a two-letter head would split every other run it occurs in) and the map
# caption, whose line is `<b>MAP OF CHINA</b>` — the importer's `<h3>` there is
# not a wrap of loose text.
BODY_CORRECTIONS.setdefault("a-retrospect", {})["wrapped_blocks"] = [
    # --- en ---
    # ch1
    ('THE following account', 'p'),
    # ch2
    ('THE first joys of conversion', 'p'),
    # ch3
    ('HAVING now the twofold', 'p'),
    # ch4
    ('THE remarkable and gracious', 'p'),
    # ch5
    ('I MUST not now attempt', 'p'),
    # ch6
    ('ONE day the doctor coming', 'p'),
    # ch7
    ('RETURNING to London when', 'p'),
    # ch8
    ('SOON after this the time', 'p'),
    ('Hearken, O daughter,', 'p'),
    # ch9
    ('ON landing in Shanghai', 'p'),
    # ch10
    ('A JOURNEY taken in the', 'p'),
    ('<i>Thursday, April 26th,', 'p'),
    ('“The perils of the sea,', 'p'),
    ('seemed particularly appropriate', 'p'),
    ('“We speak of the realms', 'p'),
    ('To be absent from the', 'p'),
    # ch11
    ('AFTER the retaking of', 'p'),
    ('<i>January 8th, 1856.</i>', 'p'),
    ('<i>January 10th.</i>', 'p'),
    ('<i>January 11th.</i>', 'p'),
    ('<i>January 12th.</i>', 'p'),
    ('“He that dwelleth in', 'p'),
    ('<i>Sunday, January 13th.</i>', 'p'),
    ('<i>Monday, January 14th.</i>', 'p'),
    ('“Ill that God blesses', 'p'),
    # ch12
    ('HAVING to leave the neighbourhood', 'p'),
    ('“O Lord, how happy should', 'p'),
    ('“And I will go!', 'p'),
    ('2. Why live I here? the', 'p'),
    # ch13
    ('IT is interesting to', 'p'),
    ('<i>August 4th, 1856.</i>', 'p'),
    ('<i>August 5th.</i>', 'p'),
    ('<i>August 6th.</i>', 'p'),
    ('<i>August 7th.</i>', 'p'),
    # ch14
    ('IT now seemed very clear', 'p'),
    ('Through midnight gloom', 'p'),
    # ch15
    ('THE autumn of 1856 was', 'p'),
    ('“They who trust Him wholly', 'p'),
    ('but also that when we', 'p'),
    ('“Sufficient is His arm', 'p'),
    # ch16
    ('NOT infrequently our', 'p'),
    ('<i>November 18th, 1857.</i>', 'p'),
    # ch17
    ('A SOMEWHAT different', 'p'),
    # ch18
    ('“My thoughts are not your', 'p'),
    ('“Blind unbelief is <i>sure</i>', 'p'),
    # ch19
    ('IT was thus that in the', 'p'),
    # ch20
    ('THE events sketched in', 'p'),
    # --- es ---
    # ch1
    ('EL siguiente relato', 'p'),
    # ch2
    ('LOS primeros gozos de', 'p'),
    # ch3
    ('Teniendo ahora el doble', 'p'),
    # ch4
    ('El notable y bondadoso', 'p'),
    # ch5
    ('No debo intentar ahora', 'p'),
    # ch6
    ('UN día, al entrar el', 'p'),
    # ch7
    ('AL REGRESAR a Londres,', 'p'),
    # ch8
    ('POCO después de esto', 'p'),
    ('Oye, hija, y considera,', 'p'),
    # ch9
    ('AL desembarcar en Shanghái', 'p'),
    # ch10
    ('Un viaje realizado en', 'p'),
    ('<i>Jueves, 26 de abril', 'p'),
    ('«Los peligros del mar,', 'p'),
    ('parecía particularmente', 'p'),
    ('«Hablamos de las mansiones', 'p'),
    ('¡Estar ausentes del', 'p'),
    # ch11
    ('DESPUÉS de la reconquista', 'p'),
    ('<i>8 de enero de 1856.</i>', 'p'),
    ('<i>10 de enero.</i>', 'p'),
    ('<i>11 de enero.</i>', 'p'),
    ('<i>12 de enero.</i>', 'p'),
    ('«El que habita al abrigo', 'p'),
    ('<i>Domingo 13 de enero.</i>', 'p'),
    ('<i>Lunes 14 de enero.</i>', 'p'),
    ('«El mal que Dios bendice', 'p'),
    # ch12
    ('TENER que dejar así,', 'p'),
    ('«¡Oh Señor, cuán felices', 'p'),
    ('«¡Y yo iré!', 'p'),
    ('2. ¿Por qué vivo aquí?', 'p'),
    # ch13
    ('Es interesante observar', 'p'),
    ('<i>4 de agosto de 1856.</i>', 'p'),
    ('<i>5 de agosto.</i>', 'p'),
    ('<i>6 de agosto.</i>', 'p'),
    ('<i>7 de agosto.</i>', 'p'),
    # ch14
    ('Ahora parecía muy claro', 'p'),
    ('Desde Macedonia, entre', 'p'),
    # ch15
    ('El otoño de 1856 estaba', 'p'),
    ('«Los que en Él confían', 'p'),
    ('sino también de que,', 'p'),
    ('«Suficiente es Su brazo', 'p'),
    # ch16
    ('No pocas veces nuestro', 'p'),
    ('<i>18 de noviembre de', 'p'),
    # ch17
    ('A comienzos del año', 'p'),
    # ch18
    ('«Mis pensamientos no', 'p'),
    ('«La ciega incredulidad', 'p'),
    # ch19
    ('Fue así como, en el año', 'p'),
    # ch20
    ('LOS acontecimientos esbozados', 'p'),
]
# Baxter, A Call to the Unconverted — the same OCR residue as revival-lectures
# above, 124 page numbers (pp. 30-156, chapters 3-6): fused ("the 50world"),
# spaced mid-sentence ("had 36 been"), or bare between blocks ("</p>32<p>").
# Proved by the same count up the book; pp. 60, 104 and 123 are absent from the
# OCR. Left alone: the ordinals "the 18th of Ezekiel" and "from the 20th to the
# end", and chapter 2's run of verse numbers, which also counts up but is
# scripture citation ("Isa. lv. 1, 2, 3."). The es and pt editions never carried
# the numbers, so this bites the English only.
_CALL_PAGES_BETWEEN_BLOCKS = (
    32, 53, 65, 75, 76, 81, 87, 91, 99, 110, 114, 138,
)
_CALL_PAGES_IN_PROSE = (
    "the 30work", "if 31we", "law. 33Few", "please 34 God.”—“Now", "believe. 35For",
    "had 36 been", "and 37 sustenation,", "them, 38if", "guilty 39 of",
    "forgetfulness 40 or", "not 41 wicked,", "disposition 42of", "amiss: 43 and",
    "rebels, 44on", "so 45neither", "health, 46and", "religion, 47 and",
    "religious, 48yet", "must 49needs", "the 50world,", "trade 51that", "and 52set",
    "will 54shortly", "to 55seeing;", "condemned? 56 It", "praise? 57And",
    "many 58thousands,", "to 59 betake", "magnify 61his", "neither 62of", "not 63 to",
    "unto 64himself", "word.”—66And,", "save 67none", "another 68should", "of 69its",
    "man, 70I", "manifesting 71 his", "life, 72which", "in 73meat,", "thou 74did",
    "God: 77He", "and 78persuade", "they 79will", "disobey 80God,", "well, 82and",
    "them, 83what", "renounce 84the", "his 85displeasure", "But 86Christ", "yet 88art",
    "turn: 89 He", "that 90will", "in 92 rioting", "How 93many", "of 94Christianity,",
    "where 95thou", "it? 96It", "know 97my", "to 98doubt", "myself.—100I",
    "ungodly, 101and", "God 102saith,", "confess 103 that", "any 105reason",
    "for 106the", "durst 107not", "that 108you", "but 109wide", "foolishness 111 with",
    "God 112 to", "praise 113 the", "not 115turn,", "reason 116that", "rather 117 die",
    "in 118your", "that 119 hath", "excellency 120 of", "thoughts 121of", "what 122is",
    "He 124hath", "delay?” 125Life", "forced 126you", "stand 127over", "5. 128“Hear,",
    "you 129put", "upon 130you,", "themselves, 131that", "darkness. 132 What!",
    "died 133for", "the 134Lord;", "assign 135each", "and 136therefore", "your 137own",
    "to 139 sin)", "you, 140and", "most 141 highly", "strait; 142 and", "all 143their",
    "not 144hear", "do 145 that", "you 146had", "heaven, 147 if",
    "habitually 148willing,", "it, 149(though", "little 150before", "work 151against",
    "everlasting 152 glory,", "before 153 God,", "of 154earnest", "over 155 your",
    "are 156reading,",
)


BODY_CORRECTIONS.setdefault("a-call-to-the-unconverted", {}).setdefault("replacements", []).extend(
    [(f"</p>{page}<p>", "</p> <p>") for page in _CALL_PAGES_BETWEEN_BLOCKS]
    + [(defective, _unpage(defective)) for defective in _CALL_PAGES_IN_PROSE]
)

# Spacing slips in the Ochorus-original collection, found translating it to French
# (#2776): a stray space inside the compound "Golden-Mouthed" (ch02) and before the
# punctuation that follows four unmarked book titles (ch04, ch06, ch10).
BODY_CORRECTIONS.setdefault("men-who-tended-the-flock-2", {}).setdefault("replacements", []).extend([
    ("Golden- Mouthed", "Golden-Mouthed"),
    ("The Temple , published", "The Temple, published"),
    ("Surprising Work of God , ", "Surprising Work of God, "),
    ("The Cost of Discipleship . The", "The Cost of Discipleship. The"),
    ("Papers from Prison , ", "Papers from Prison, "),
])
