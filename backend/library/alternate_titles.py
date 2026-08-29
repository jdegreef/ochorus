"""Other names the same work goes by.

A reader looking for Watson's *All Things for Good* may well type "A Divine
Cordial" — the title it was published under in 1663 — and a reader looking for
Athanasius may type *De Incarnatione*. Both are the same book; nothing on the
page said so, so neither search found it.

``alternateName`` is schema.org's word for exactly this, and the same strings
render on the page as an "also known as" line, because the reader who arrives
by the old name needs to see it confirmed.

Two kinds of name, kept apart because they behave differently:

* :data:`CITATION_TITLES` — the name the work is *cited* by in every language.
  Usually Latin, whether or not the work was composed in Latin: Athanasius
  wrote in Greek, but a Spanish, Swahili or Ukrainian edition of *On the
  Incarnation* is still catalogued as *De Incarnatione Verbi Dei*. Language
  independent, so every edition carries it.
* :data:`VARIANT_TITLES` — other names in ONE language. "A Divine Cordial" is
  an English fact and belongs on English editions only; a Spanish reader shown
  it would be looking at a title that names no book they can find.

Curated here rather than in the fixture because these are properties of the
WORK, and Ochorus has no work table — the slug is the work identity, and a
per-row column would mean copying the Latin title into every edition by hand
and keeping the copies in step. Recording it once, keyed by slug, is the same
choice ``corrections.py`` and ``designed_covers.py`` make for the same reason.

Every entry is attested, not derived: a title nobody published is a claim that
this page is about a book that does not exist, which is the failure mode
structured data punishes hardest. A work whose only name is its name simply
has no entry — most of the shelf is in that position, and should be.
"""

from __future__ import annotations

# slug -> names that hold in every language.
CITATION_TITLES: dict[str, tuple[str, ...]] = {
    "confessions": ("Confessiones",),
    "life-of-antony": ("Vita Antonii", "Βίος Ἀντωνίου"),
    "on-the-incarnation": (
        "De Incarnatione Verbi Dei",
        "Περὶ τῆς Ἐνανθρωπήσεως τοῦ Λόγου",
    ),
    "on-the-priesthood": ("De Sacerdotio", "Περὶ Ἱερωσύνης"),
    # Baxter published under this pseudonymous Latin head-title; "The Reformed
    # Pastor" was the second half of it and is all anyone says today.
    "the-reformed-pastor": ("Gildas Salvianus",),
    "the-imitation-of-christ": ("De Imitatione Christi",),
}

# (slug, language) -> names that hold in that language only.
VARIANT_TITLES: dict[tuple[str, str], tuple[str, ...]] = {
    ("a-call-to-the-unconverted", "en"): (
        "A Call to the Unconverted to Turn and Live",
    ),
    # Published 1663 as A Divine Cordial; still catalogued under both.
    ("all-things-for-good", "en"): ("A Divine Cordial",),
    ("answers-to-prayer", "en"): ("Answers to Prayer, from George Müller's Narratives",),
    ("baptism-with-the-holy-spirit", "en"): ("The Baptism with the Holy Spirit",),
    # American editions spell it "Check", and the work is as often sold as
    # Faith's Checkbook — three spellings of one title, one of them ours.
    ("cheque-book", "en"): (
        "The Check Book of the Bank of Faith",
        "Faith's Checkbook",
    ),
    ("confessions", "en"): ("The Confessions of Saint Augustine",),
    ("freedom-of-the-will", "en"): (
        "A Careful and Strict Enquiry into the Modern Prevailing Notions of "
        "That Freedom of Will Which Is Supposed to Be Essential to Moral Agency",
    ),
    ("grace-abounding", "en"): ("Grace Abounding",),
    # "If" alone is unsearchable; the full title is how it is actually cited.
    ("if", "en"): ("If: What Do I Know of Calvary Love?",),
    ("life-and-diary-of-david-brainerd", "en"): (
        "The Diary of David Brainerd",
        "An Account of the Life of the Late Reverend Mr. David Brainerd",
    ),
    ("life-of-antony", "en"): ("The Life of Saint Antony", "The Life of St. Anthony"),
    ("mortification-of-sin", "en"): (
        "Of the Mortification of Sin in Believers",
        "The Mortification of Sin",
    ),
    ("on-the-incarnation", "en"): ("On the Incarnation of the Word",),
    ("on-the-priesthood", "en"): (
        "Six Books on the Priesthood",
        "A Treatise on the Priesthood",
    ),
    ("pilgrims-progress", "en"): (
        "The Pilgrim's Progress from This World, to That Which Is to Come",
    ),
    ("plain-account-christian-perfection", "en"): (
        "A Plain Account of Christian Perfection, as Believed and Taught by "
        "the Reverend Mr. John Wesley",
    ),
    ("power-through-prayer", "en"): ("Preacher and Prayer",),
    ("prevailing-prayer", "en"): ("Prevailing Prayer: What Hinders It?",),
    ("religious-affections", "en"): ("Religious Affections",),
    # Ours is already the short name; these are the long and the alternate one.
    ("revival-lectures", "en"): (
        "Revival Lectures",
        "Lectures on Revival",
        "Revivals of Religion",
    ),
    ("sermons-on-several-occasions", "en"): (
        "Wesley's Standard Sermons",
        "The Standard Sermons of John Wesley",
    ),
    ("the-bruised-reed", "en"): ("The Bruised Reed and Smoking Flax",),
    ("the-imitation-of-christ", "en"): ("Of the Imitation of Christ",),
    ("the-person-and-work-of-the-holy-spirit", "en"): (
        "The Person and Work of the Holy Spirit as Revealed in the Scriptures "
        "and in Personal Experience",
    ),
    ("the-reformed-pastor", "en"): ("Gildas Salvianus, The Reformed Pastor",),
    ("the-unselfishness-of-god", "en"): (
        "The Unselfishness of God and How I Discovered It",
    ),
    ("the-way-to-god", "en"): ("The Way to God and How to Find It",),
    # "Things as They Are" names nothing on its own; the subtitle is the work.
    ("things-as-they-are", "en"): ("Things as They Are: Mission Work in Southern India",),
    ("union-and-communion", "en"): (
        "Union and Communion; or, Thoughts on the Song of Solomon",
    ),
    ("way-into-holiest", "en"): (
        "The Way into the Holiest: Expositions of the Epistle to the Hebrews",
    ),
}


def _key(title: str) -> str:
    """A title flattened for comparison — case and the curly/straight apostrophe.

    The fixture writes ``’`` and half these titles are quoted from catalogues
    that write ``'``; without folding them, "The Christian’s Secret" and "The
    Christian's Secret" read as two different books.
    """
    return title.casefold().replace("’", "'").strip()


def alternate_titles(slug: str, language: str, title: str = "") -> list[str]:
    """Every other name for this edition, in reading order, deduplicated.

    ``title`` is the edition's own name: an entry equal to it is dropped, so a
    retitle can never leave the page claiming ``alternateName`` == ``name``,
    which asserts nothing and reads to a crawler as noise.
    """
    seen = {_key(title)} if title else set()
    out: list[str] = []
    for name in CITATION_TITLES.get(slug, ()) + VARIANT_TITLES.get((slug, language), ()):
        if _key(name) in seen:
            continue
        seen.add(_key(name))
        out.append(name)
    return out
