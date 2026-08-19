"""Repairs to imported book text that the SOURCE itself got wrong.

Distinct from `corrections.py`, which fixes what the PDF *extractor* got wrong
(drop caps, borrowed titles, stray page numbers). These are defects in the text
we were given: a quotation that is not the verse it cites, a block the source
duplicated. They were found by translators, who hit them in five languages at
once and could not silently paper over them.

Two callers must agree, so the logic lives here and not in either of them:

* `scripts/` / the fixture, so a fresh database is built clean;
* migration 0058, so the rows already in production are repaired.

`seed_books` only creates chapters for a book it has never seen — it never
rewrites an existing book's chapter bodies (it reports the drift and moves on).
So a fixture edit alone would leave production exactly as wrong as it is now.
That is why the migration exists, and why editing these functions after they
have shipped changes nothing on its own.

Keyed by `(slug, order)` and applied to a chapter body in ANY language: each
repair either matches that language's text or no-ops.
"""

from __future__ import annotations

import re

_PARA = re.compile(r"<p>(.*?)</p>", re.S)

# ch01 prints the text of 2 Corinthians 10:13 under the reference "1 Corinthians
# 12:11", and then argues "Here, will is ascribed to the Spirit" — which only
# the real verse supports. Every replacement below is that edition's OWN
# rendering of the verse in ch20, so nothing is invented and a reader who meets
# the verse twice now meets it the same way. Luganda and Arabic already quote it
# correctly (their translators caught the error and quoted the real verse), so
# they need no entry.
WRONG_VERSE = [
    (
        "But we will not boast beyond limits, but will boast only about the "
        "area of influence God assigned to us, to reach even to you.",
        "All these are empowered by the same Spirit, who apportions to each "
        "one individually as he wills.",
    ),
    (
        "Pero nosotros no nos gloriaremos desmedidamente, sino conforme a la "
        "medida de la regla que Dios nos repartió, para llegar también hasta "
        "vosotros",
        "Mas todas estas cosas obra uno y el mismo Espíritu, repartiendo "
        "particularmente a cada uno como quiere",
    ),
    (
        "Lakini sisi hatutajisifu kupita kiasi, bali kwa kadiri ya eneo la "
        "utumishi Mungu alilotugawia, hata kuwafikia ninyi.",
        "Lakini kazi hizi zote huzitenda Roho yule mmoja, yeye yule, "
        "akimgawia kila mtu peke yake kama apendavyo yeye.",
    ),
    # OCR split inside the John 7:17 quotation repaired below.
    ("on my author ity", "on my authority"),
]


def fix_wrong_verse(body_html: str) -> str:
    for bad, good in WRONG_VERSE:
        body_html = body_html.replace(bad, good)
    return body_html


# "Humility and Faith" ch09 asks whether the Syrophenician mother, told "O
# woman, great is thy faith!", had not "accepted the name of God" — but the
# name she accepted was *dog*, the one Jesus had just used, and she pressed her
# plea from underneath it: "yet even the dogs eat the crumbs" (Matthew 15:27),
# which the very next clause of our own text still quotes. Read as printed, the
# illustration argues the opposite of the chapter: Murray's point is that her
# faith was great BECAUSE her humility would take the humiliating name. Checked
# against another edition of Humility before changing (worldinvisible.com's
# text of ch09 and BibleStudyTools' — both read "the name of dog").
#
# Each edition gets its own pair: both translators reproduced the defect
# faithfully, which is correct of a translator and is what makes it fixable
# here rather than silently papered over. The Arabic pair was added with that
# edition (below); only its final word differs from the text as translated, and
# the verse it quotes two clauses later already reads "and the dogs eat of the
# crumbs", so the correction is anchored by the translation's own wording.
NAME_OF_DOG = [
    ("accepted the name of God, and said", "accepted the name of dog, and said"),
    ("teyakkiriza erinnya lya Katonda", "teyakkiriza erinnya ly'embwa"),
    ("قبِلت اسم الله", "قبِلت اسم الكلب"),
]


def fix_name_of_dog(body_html: str) -> str:
    for bad, good in NAME_OF_DOG:
        body_html = body_html.replace(bad, good)
    return body_html


def fix_duplicated_block(body_html: str) -> str:
    """Collapse ch08's duplicated paragraphs 10-12 back into one.

    The source repeats itself here, and in the repetition it mangles a verse.
    Paragraph 10 opens a thought, then breaks off mid-quotation with a clause
    carried over from paragraph 9 — so it has Jesus saying, at John 7:17,
    "...he is saved there on the spot", which is not that verse and not
    anything he says. Paragraph 11 then repeats the tail of 9 and the head of
    10, and only paragraph 12 states the thought properly, verse and all.

    What the author wrote is paragraph 10's opening sentence followed by
    paragraph 12. Recover exactly that, and drop the wreckage.

    Deliberately structural rather than a list of strings to match: the same
    duplication was faithfully reproduced by every translator, so this has to
    work in five languages. Splitting on the first sentence is what does that —
    on the four editions that repeat themselves verbatim it agrees exactly with
    the longest-common-span the duplication itself defines, and it still works
    on the Arabic, which varied the wording between the two copies the way
    Arabic prose does.
    """
    paras = _PARA.findall(body_html)
    if len(paras) != 20:
        return body_html  # already repaired, or not the chapter we mean
    opening, _, rest = paras[9].partition(".")
    if not rest:
        return body_html
    merged = f"{opening}. {paras[11]}"
    kept = paras[:9] + [merged] + paras[12:]
    return "".join(f"<p>{p}</p>" for p in kept)


# "Jesus Himself" ch02 opens by quoting a promise — "I will come and dwell with
# you, and I will never leave you" — and prints "Matthew 28:20." after it. That
# is not Matthew 28:20, and the same chapter quotes the real verse ("Behold, I
# am with you always, to the end of the age") under that same reference FOUR
# more times. So the edition's own usage settles it: the words here are the
# author's composite of John 14:23 and Hebrews 13:5, and the reference is a
# false pointer appended to them.
#
# Found independently in two languages: the hi translator flagged it as an
# unverifiable paraphrase (it is also the chapter title), and the pt translator
# of `divine-healing` refused it as a crib entry — the mined crib offered it
# because `jesus-himself-2.pt.json` already ships it that way.
#
# The repair DELETES the reference and touches nothing else. Re-labelling it
# John 14:23 / Hebrews 13:5 would invent an editorial decision about a sentence
# the author wrote as one promise; the chapter title, which is the same words,
# is left exactly as printed.
#
# THREE EDITIONS ARE DELIBERATELY NOT LISTED. es, lg and sw resolved this the
# other way round on their own, and their text is correct as it stands: each
# replaced the promise's second clause with the real verse ("y he aquí, yo
# estoy con vosotros todos los días", "era Ndi nammwe bulijjo", "na hakika mimi
# niko pamoja nanyi siku zote"), so quotation and reference agree. Deleting
# their label would break work that is already right. That leaves the corpus
# split — four editions quoting the author with no reference, three quoting the
# verse with one — and both halves are honest, which the status quo is not. A
# reviewer who wants them uniform has to change the AUTHOR's words in the
# English and the chapter title with them, and that is not a repair.
#
# Anchored on the QUESTION MARK, which is what separates this site from the
# four correct ones in the same chapter: every one of those follows a full
# stop. Written per edition rather than as one pattern precisely so the three
# repaired editions cannot be caught by it.
MISCITED_2820 = [
    ("?\u201d Matthew 28:20.", "?\u201d"),
    ("? (Mateus 28:20).", "?"),
    ("?\u201d \u092e\u0924\u094d\u0924\u0940 28:20\u0964", "?\u201d"),
    ("\u00bb? \u041c\u0430\u0442\u0442\u0435\u044f 28:20.", "\u00bb?"),
]


def fix_miscited_matthew_2820(body_html: str) -> str:
    """Drop the Matthew 28:20 label from ch02's opening promise. Idempotent."""
    for bad, good in MISCITED_2820:
        body_html = body_html.replace(bad, good)
    return body_html


# `The Inner Chamber` ch15 ("Meditation") closes its list of proof texts with
# "1 Timothy 5: 15." — Psalm 1:1-2, Joshua 1:8, Psalm 119, and then a verse
# about young widows turning aside after Satan. 1 Timothy 4:15 is "Meditate
# upon these things; give thyself wholly to them", which is the chapter's whole
# subject and the only member of the list that belongs.
#
# The Swahili translator had already reached the same conclusion unprompted and
# wrote "1 Timotheo 4:15" — which is also why sw is the one edition this repair
# leaves alone: it closes the list without the parenthesis the others carry, so
# there is nothing here to match, and nothing to fix.
#
# Every other edition prints the numerals unlocalized and closes the list the
# same way, so matching the parenthesis that ends it covers them all. The
# English spaces its colons ("5: 15") and the translations do not.
# The English spaces its colons ("5: 15") and the translations do not; the
# Hindi ends the sentence with a danda rather than a full stop.
_TIM_MEDITATE = re.compile(r"5:( ?)15([.।]\))")


def fix_meditation_proof_text(body_html: str) -> str:
    return _TIM_MEDITATE.sub(r"4:\g<1>15\2", body_html)


# ch23 ("Feeding On The Word") quotes the treasure hidden in a field —
# Matthew 13:44 — under the reference "Matthew 13:4", which is the sower. The
# quotation itself is what settles it, and three translators had already made
# the correction on their own: the ar, lg and pt editions print 13:44 or drop
# the reference.
#
# The lookahead is what makes this idempotent: without it the repair would run
# on its own output and produce 13:444.
_MATT_1344 = re.compile(r"13:4(?!\d)")


def fix_treasure_in_a_field(body_html: str) -> str:
    return _MATT_1344.sub("13:44", body_html)


# `He Holds My Tomorrows` ch07 lists five occasions of offence and cites, for
# Judas objecting to the ointment, "John 12:14" — the entry into Jerusalem on a
# young ass. John 12:4 is "Then saith one of his disciples, Judas Iscariot",
# which is the disciple and the objection the sentence is about.
def fix_judas_objection(body_html: str) -> str:
    return body_html.replace("12:14", "12:4")


# ch08 ("Enoch") carries three reference slips, each contradicted by the clause
# it is attached to:
#
#   "without which it is impossible to please God (Hebrews 11:16)"  -> 11:6
#       11:16 is "he hath prepared for them a city", which ch12 of this same
#       book quotes correctly under 11:16 — so the book itself distinguishes
#       them, and this repair is scoped to ch08 for exactly that reason.
#   "the mystery of the kingdom (Mark 13:11)"                       -> 4:11
#       13:11 is the Spirit giving words under trial; 4:11 is "unto you it is
#       given to know the mystery of the kingdom of God".
#   "our new life of grace (Romans 6:4-6 and Romans 9-11)"          -> 6:9-11
#       Romans 9-11 is the election of Israel. Romans 6:9-11 continues the
#       verses already cited beside it: "reckon ye also yourselves to be dead
#       indeed unto sin, but alive unto God".
#
# All six editions print the numerals unlocalized, so the pairs are numeric.
# The Romans pair is a regex rather than a literal so the repair is a fixed
# point: "9-11)" is still a substring of its own output, and a plain replace
# would build "6:6:9-11)" the second time the release chain ran it.
HE_HOLDS_CH08 = [("11:16)", "11:6)"), ("13:11)", "4:11)")]
_ROMANS_6 = re.compile(r"(?<!:)9-11\)")


def fix_enoch_references(body_html: str) -> str:
    for bad, good in HE_HOLDS_CH08:
        body_html = body_html.replace(bad, good)
    return _ROMANS_6.sub("6:9-11)", body_html)


# (slug, chapter order) -> repairs, applied in order.
SOURCE_FIXES = {
    ("humility-2", 9): [fix_name_of_dog],
    ("the-person-and-work-of-the-holy-spirit", 1): [fix_wrong_verse],
    ("the-person-and-work-of-the-holy-spirit", 8): [
        fix_duplicated_block,
        fix_wrong_verse,
    ],
    ("jesus-himself-2", 2): [fix_miscited_matthew_2820],
    ("the-inner-chamber", 15): [fix_meditation_proof_text],
    ("the-inner-chamber", 23): [fix_treasure_in_a_field],
    ("he-holds-my-tomorrows", 7): [fix_judas_objection],
    ("he-holds-my-tomorrows", 8): [fix_enoch_references],
}


def apply_source_fixes(slug: str, order: int, body_html: str) -> str:
    for fix in SOURCE_FIXES.get((slug, order), ()):
        body_html = fix(body_html)
    return body_html
