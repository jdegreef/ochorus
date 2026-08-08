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
# Extraction artifacts inside chapter bodies that heuristics can't fix:
#
#   dropcap_letters: {order: "G"} — the chapter's opening letter was an IMAGE
#     drop cap in the source, so the text layer starts one letter short
#     ("reat numbers…"). The letter is unambiguous from context; we restore it.
#   replacements: [(old, new)] — exact-string repairs for OCR damage (a letter
#     split off before punctuation: "blesse d!" → "blessed!"). Kept as literal
#     pairs — no clever regex — so scripture citations like "Song i." are never
#     touched. Verify each in context before adding.
#
# Applied on every import AND backfillable over stored rows (management command
# `apply_body_corrections`, plus a data migration for prod).

import re as _re

BODY_CORRECTIONS: dict[str, dict] = {
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
        "replacements": [
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
        "replacements": [("<p>Iwas", "<p>I was"), ("<p>Iwell", "<p>I well")],
    },
    "how-to-manage-a-library": {
        "replacements": [("<p>Alibrary", "<p>A library"), ("<p>Agood", "<p>A good")],
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
        "replacements": [("L ORD", "LORD")],
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
    """
    entry = BODY_CORRECTIONS.get(slug)
    if entry:
        for old, new in entry.get("replacements", []):
            body_html = body_html.replace(old, new)
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
