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

from library.catalog import AuthorEntry


@dataclass(frozen=True)
class SermonEntry:
    slug: str
    title: str
    author_slug: str  # canonical DB author slug (see AuthorListView / fixture)
    source: str  # "ccel" (one page per sermon) | "gutenberg" (h1 section of an ebook)
    source_ref: str  # ccel: full URL of the sermon page; gutenberg: ebook id
    section: str = ""  # gutenberg: the h1 heading text of the sermon
    scripture_ref: str = ""  # override; parsed from the page when empty
    preached_on: str = ""  # ISO date override; parsed from the page when empty


# Authors that sermons may introduce before any of their books exist in the
# catalog. Keyed by the canonical DB slug.
SERMON_AUTHORS: dict[str, AuthorEntry] = {
    "charles-h-spurgeon": AuthorEntry(
        slug="charles-h-spurgeon",
        name="Charles H. Spurgeon",
        birth_year=1834,
        death_year=1892,
        bio=(
            "English Baptist preacher, the “Prince of Preachers,” whose sermons "
            "and devotional writings have been read by millions."
        ),
    ),
    "dwight-l-moody": AuthorEntry(
        slug="dwight-l-moody",
        name="Dwight L. Moody",
        birth_year=1837,
        death_year=1899,
        bio=(
            "American evangelist whose plain, warm gospel addresses reached "
            "millions across America and Britain; founder of the Moody Bible "
            "Institute."
        ),
    ),
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
]
