"""The curated sermon shelf: individual public-domain sermons.

Like ``catalog.py`` for books, each sermon declares where its clean source
lives. ``source`` is "ccel" (the only importer so far); ``source_ref`` is the
full URL of the per-sermon page. The importer parses the scripture reference
and preached-on date from the page itself; the optional ``scripture_ref`` /
``preached_on`` fields override when parsing gets it wrong.

The order of SERMONS is the shelf order (sort_order).

Curation rule: themed to the library's readers — prayer, comfort in trial,
assurance and grace, and warm evangelistic appeal. Curate a readable dozen or
two per author; never bulk-import a 63-volume set.
"""

from __future__ import annotations

from dataclasses import dataclass

from library.catalog import AUTHORS, AuthorEntry


@dataclass(frozen=True)
class SermonEntry:
    slug: str
    title: str
    author_slug: str  # canonical DB author slug (see AuthorListView / fixture)
    source: str  # "ccel" (one page per sermon) | "gutenberg" (heading section of an ebook)
    source_ref: str  # ccel: full URL of the sermon page; gutenberg: ebook id
    section: str = ""  # gutenberg: the heading text of the sermon, at any level
    scripture_ref: str = ""  # override; parsed from the page when empty
    preached_on: str = ""  # ISO date override; parsed from the page when empty
    body_starts: str = ""  # web: literal text the sermon's first paragraph starts with


# Authors that sermons may introduce before any of their books exist in the
# catalog. Keyed by the canonical DB slug.
#
# All three now also carry books, so they reuse the book catalog's entry rather
# than restating it — three near-identical copies of the same author is how the
# Spurgeon slug drifted (the sermon side said `charles-h-spurgeon`, matching the
# fixture; the book side said `charles-spurgeon`, and re-importing a Spurgeon
# book forked him into a second, bio-less author row). Add a literal
# `AuthorEntry` here only for an author with no books at all — and give it the
# slug `authors.json` uses.
SERMON_AUTHORS: dict[str, AuthorEntry] = {
    slug: AUTHORS[slug]
    for slug in ("charles-h-spurgeon", "a-b-simpson", "dwight-l-moody")
}

_CCEL = "https://ccel.org/ccel/spurgeon/"

SERMONS: list[SermonEntry] = [
    # --- Assurance & the character of God -----------------------------------
    SermonEntry(
        "the-immutability-of-god",
        "The Immutability of God",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons01/sermons01.i.html",
    ),
    SermonEntry(
        "free-grace",
        "Free Grace",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons05/sermons05.x.html",
    ),
    SermonEntry(
        "christ-precious-to-believers",
        "Christ Precious to Believers",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons05/sermons05.xix.html",
    ),
    # --- Prayer --------------------------------------------------------------
    SermonEntry(
        "the-golden-key-of-prayer",
        "The Golden Key of Prayer",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons11/sermons11.xiii.html",
    ),
    SermonEntry(
        "order-and-argument-in-prayer",
        "Order and Argument in Prayer",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons12/sermons12.iv_1.html",
    ),
    SermonEntry(
        "the-ravens-cry",
        "The Ravens' Cry",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons12/sermons12.v.html",
    ),
    SermonEntry(
        "pauls-first-prayer",
        "Paul's First Prayer",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons01/sermons01.xv.html",
    ),
    # --- Comfort in trial -----------------------------------------------------
    SermonEntry(
        "sweet-comfort-for-feeble-saints",
        "Sweet Comfort for Feeble Saints",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons01/sermons01.vi.html",
    ),
    SermonEntry(
        "comfort-for-the-desponding",
        "Comfort for the Desponding",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons01/sermons01.xlviii.html",
    ),
    SermonEntry(
        "the-sweet-uses-of-adversity",
        "The Sweet Uses of Adversity",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons05/sermons05.lviii.html",
    ),
    SermonEntry(
        "consolation-in-the-furnace",
        "Consolation in the Furnace",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons11/sermons11.lv.html",
    ),
    # --- Evangelistic ---------------------------------------------------------
    SermonEntry(
        "compel-them-to-come-in",
        "Compel Them to Come In",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons05/sermons05.iv.html",
    ),
    SermonEntry(
        "christ-crucified",
        "Christ Crucified",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons01/sermons01.vii.html",
    ),
    # --- D. L. Moody — warm gospel addresses (undated) ------------------------
    SermonEntry(
        "christs-boundless-compassion",
        "Christ's Boundless Compassion",
        "dwight-l-moody",
        "gutenberg",
        "33520",
        section="CHRIST'S BOUNDLESS COMPASSION",
        scripture_ref="Matthew 14:14",
    ),
    SermonEntry(
        "christ-all-in-all",
        "Christ All in All",
        "dwight-l-moody",
        "gutenberg",
        "33520",
        section="CHRIST ALL IN ALL",
        scripture_ref="Colossians 3:11",
    ),
    SermonEntry(
        "eight-i-wills-of-christ",
        "Eight \"I Wills\" of Christ",
        "dwight-l-moody",
        "gutenberg",
        "33520",
        section="EIGHT \"I WILLS\" OF CHRIST",
        scripture_ref="Matthew 11:28",
    ),
    SermonEntry(
        "the-dying-thief",
        "The Dying Thief",
        "dwight-l-moody",
        "gutenberg",
        "33520",
        section="THE DYING THIEF",
        scripture_ref="Luke 23:39-43",
    ),
    SermonEntry(
        "rest",
        "Rest",
        "dwight-l-moody",
        "gutenberg",
        "33015",
        section="REST",
        scripture_ref="Matthew 11:28",
    ),
    SermonEntry(
        "the-new-birth",
        "The New Birth",
        "dwight-l-moody",
        "gutenberg",
        "33520",
        section="THE NEW BIRTH",
        scripture_ref="John 3:3",
    ),
    SermonEntry(
        "the-way-of-salvation",
        "The Way of Salvation",
        "dwight-l-moody",
        "gutenberg",
        "33520",
        section="THE WAY OF SALVATION",
        scripture_ref="Acts 16:23-40",
    ),
    SermonEntry(
        "come-thou-into-the-ark",
        "Come Thou and All Thy House into the Ark",
        "dwight-l-moody",
        "gutenberg",
        "33015",
        section="\"COME THOU AND ALL THY HOUSE INTO THE ARK.\"",
        scripture_ref="Genesis 7:1",
    ),
    # --- A. B. Simpson — the deeper life (undated addresses) -----------------
    SermonEntry(
        "himself",
        "Himself",
        "a-b-simpson",
        "web",
        "https://www.biblebelievers.com/simpson-ab_himself.html",
        scripture_ref="Colossians 1:27",
        body_starts="I wish to speak to you about Jesus",
    ),
    SermonEntry(
        "the-power-of-stillness",
        "The Power of Stillness",
        "a-b-simpson",
        "web",
        "http://hanswaldvogel.com/lib/Simpson%20-%20Power%20of%20Stillness.html",
        scripture_ref="1 Kings 19:12",
    ),
    SermonEntry(
        "the-possibilities-of-faith",
        "The Possibilities of Faith",
        "a-b-simpson",
        "web",
        "https://online.ambrose.edu/alliancestudies/simpson/larglif1.htm",
        scripture_ref="Mark 9:23",
    ),
    SermonEntry(
        "the-joy-of-the-lord",
        "The Joy of the Lord",
        "a-b-simpson",
        "web",
        "https://online.ambrose.edu/alliancestudies/simpson/larglif3.htm",
        scripture_ref="Nehemiah 8:10",
    ),
    SermonEntry(
        "unfailing-springs",
        "Unfailing Springs",
        "hudson-taylor",
        "gutenberg",
        "57109",
        section="Unfailing Springs",
        scripture_ref="John 4:14",
    ),
    # From "A Ribband of Blue" (1899), a collection of eight self-contained
    # studies — each its own text and argument, which is what makes them
    # sermons rather than chapters. (Taylor's "Separation and Service" is the
    # opposite case: one continuous 57k-word exposition, so it belongs in the
    # book catalog.)
    SermonEntry(
        "blessed-adversity",
        "Blessed Adversity",
        "hudson-taylor",
        "gutenberg",
        "23438",
        section="Blessed Adversity",
        scripture_ref="Psalm 23:6",
    ),
]
