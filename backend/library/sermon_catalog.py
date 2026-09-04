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
_WESLEY = "https://ccel.org/ccel/wesley/sermons/"
_WHITEFIELD = "https://ccel.org/ccel/whitefield/sermons/"

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
    # Catherine Booth — the first woman on the sermon shelf. "Papers on
    # Aggressive Christianity" (1880) is subtitled "practical sermons" and this
    # page is headed "A Sermon of Catherine Booth", so the ten chapters are
    # sermons proper. Her better-known "Female Ministry" is from "Practical
    # Religion", a collection of PAPERS — an essay, and a book-shelf candidate
    # rather than a sermon.
    SermonEntry(
        "aggressive-christianity",
        "Aggressive Christianity",
        "catherine-booth",
        "web",
        "https://www.gospeltruth.net/booth/cath_booth/agressive_christianity/cbooth_1_agressive.htm",
        scripture_ref="Mark 16:15",
        body_starts="I WAS thinking, while I was reading the lesson",
    ),
    # Three more from the same 1880 "Aggressive Christianity" volume, so the
    # first woman on the shelf has more than one address. The verse sits in the
    # source's Geneva-font masthead block (not a <p>), so a web import keeps it
    # in scripture_ref and starts the body at `body_starts` — the fixture is
    # authoritative regardless (see backend/CLAUDE.md; sermon_catalog is
    # import-time config the fixture supersedes).
    SermonEntry(
        "the-worlds-need",
        "The World's Need",
        "catherine-booth",
        "web",
        "https://www.gospeltruth.net/booth/cath_booth/agressive_christianity/cbooth_9_worldsneed.htm",
        # Source masthead prints "Matthew xxi. 23", but the words it quotes
        # ("Son, go work today in my vineyard") are Matthew 21:28.
        scripture_ref="Matthew 21:28; Luke 14:23",
        body_starts="WE might have enumerated other texts",
    ),
    SermonEntry(
        "witnessing-for-christ",
        "Witnessing for Christ",
        "catherine-booth",
        "web",
        "https://www.gospeltruth.net/booth/cath_booth/agressive_christianity/cbooth_7_witnesses.htm",
        scripture_ref="Acts 1:8; Acts 5:32",
        body_starts="AGAIN and again the same vocation and commission",
    ),
    SermonEntry(
        "the-holy-ghost",
        "The Holy Ghost",
        "catherine-booth",
        "web",
        "https://www.gospeltruth.net/booth/cath_booth/agressive_christianity/cbooth_10_holyghost.htm",
        scripture_ref="Luke 24:49; Acts 1:8",
        body_starts="FRIENDS who were present at former services",
    ),
    # John Wesley — the first pre-19th-century sermon in the library, and the
    # opening of the largest untapped seam here: the 44 Standard Sermons are
    # his primary corpus, all public domain on CCEL.
    #
    # NOTE his masthead differs from Spurgeon's: the preaching note lives in a
    # <span class="mnote"> inside an <h2>, and the reference in an <h3> — which
    # is why extract() reads the leading BLOCKS, not just <p>. Scanning <p>
    # only found Luke 4:34 (a reference inside the sermon), took the whole
    # opening section as masthead, and dropped 517 words silently.
    SermonEntry(
        "salvation-by-faith",
        "Salvation by Faith",
        "john-wesley",
        "ccel",
        _WESLEY + "sermons.v.i.html",
        # CCEL renders it "Eph. 2:8"; every other sermon on the shelf stores a
        # full book name, and this string is what the reader displays.
        scripture_ref="Ephesians 2:8",
    ),
    # Three more Standard Sermons, so Wesley has more than one on the shelf.
    SermonEntry(
        "the-almost-christian",
        "The Almost Christian",
        "john-wesley",
        "ccel",
        _WESLEY + "sermons.v.ii.html",
        scripture_ref="Acts 26:28",
        preached_on="1741-07-25",
    ),
    # The shipped fixture repairs one CCEL 1872-text slip by hand — "whether
    # we;' eat" → "whether we eat"; a re-import would reintroduce it, so the
    # fixture is authoritative here.
    SermonEntry(
        "the-circumcision-of-the-heart",
        "The Circumcision of the Heart",
        "john-wesley",
        "ccel",
        _WESLEY + "sermons.v.xvii.html",
        scripture_ref="Romans 2:29",
        preached_on="1733-01-01",
    ),
    # CCEL appends Charles Wesley's hymn "Catholic Love" ("added in some
    # editions") in brackets after the sermon; the shipped fixture drops that
    # editorial appendix, which extract() does not — so the fixture wins.
    SermonEntry(
        "catholic-spirit",
        "Catholic Spirit",
        "john-wesley",
        "ccel",
        _WESLEY + "sermons.v.xxxix.html",
        scripture_ref="2 Kings 10:15",
    ),
    # --- One famous sermon each for four preachers who had none --------------
    # These authors already carry a bio (and some a book that is NOT a sermon
    # collection); a single landmark sermon gives their preaching a home.
    # Finney's CCEL sermons render via a JS reader (a raw fetch gets only
    # "loading…"); the same sermon is served as static HTML on gospeltruth.net
    # (already the source for Catherine Booth's sermon).
    SermonEntry(
        "gods-love-for-a-sinning-world",
        "God's Love for a Sinning World",
        "charles-finney",
        "web",
        "https://www.gospeltruth.net/1853OE/530622_gods_love.htm",
        scripture_ref="John 3:16",
        body_starts="Sin is the most expensive thing in the universe",
    ),
    SermonEntry(
        "against-eutropius",
        "Against Eutropius",
        "john-chrysostom",
        "ccel",
        "https://ccel.org/ccel/schaff/npnf109.xv.iii.html",
        scripture_ref="Ecclesiastes 1:2",
    ),
    # Luther has no standalone-page PD sermon on CCEL, and the Gutenberg Lenker
    # Postil (28464) sets every sermon AND its subsections at the same <h4>, so
    # the section importer can't bound one sermon. The Lenker translation is
    # served one-sermon-per-page (public domain) at sermons.martinluther.us.
    SermonEntry(
        "pauls-praise-of-christian-love",
        "Paul's Praise of Christian Love",
        "martin-luther",
        "web",
        "https://sermons.martinluther.us/sermons33.html",
        scripture_ref="1 Corinthians 13",
        body_starts="1. Paul's purpose in this chapter is to silence",
    ),
    # Calvin's sermons are on neither CCEL (commentaries only) nor Gutenberg as
    # a clean single section (the Kleiser anthology, id 11981, repeats the
    # heading for the biographical note and the sermon). BibleHub carries the
    # same public-domain Kleiser translation as one page.
    SermonEntry(
        "enduring-persecution-for-christ",
        "Enduring Persecution for Christ",
        "john-calvin",
        "web",
        "https://biblehub.com/sermons/auth/various/calvin_--_enduring_persecution_for_christ.htm",
        scripture_ref="Hebrews 13:13",
        body_starts="All the exhortations which can be given us to suffer patiently",
    ),
    # --- George Whitefield: six from CCEL's 59-sermon edition ------------------
    # Whitefield had a bio and a book but no sermon. CCEL's edition differs from
    # Wesley's: an <h1> title, no footnotes, and the scripture INSIDE the first
    # paragraph as `<a class="scripRef">Ref</a> — “verse”` — so scripture_ref is
    # pinned here rather than trusted to the masthead parser. Two sermons (Wisdom,
    # Intercession) open straight into prose with no heading at all; Intercession's
    # text is the verse it calls "the text": “Brethren, pray for us” (1 Thess 5:25).
    SermonEntry(
        "the-method-of-grace",
        "The Method of Grace",
        "george-whitefield",
        "ccel",
        _WHITEFIELD + "sermons.lx.html",
        scripture_ref="Jeremiah 6:14",
    ),
    SermonEntry(
        "marks-of-a-true-conversion",
        "Marks of a True Conversion",
        "george-whitefield",
        "ccel",
        _WHITEFIELD + "sermons.xxv.html",
        scripture_ref="Matthew 18:3",
    ),
    SermonEntry(
        "walking-with-god",
        "Walking with God",
        "george-whitefield",
        "ccel",
        _WHITEFIELD + "sermons.iv.html",
        scripture_ref="Genesis 5:24",
    ),
    SermonEntry(
        "christ-the-believers-wisdom",
        "Christ the Believer's Wisdom, Righteousness, Sanctification and Redemption",
        "george-whitefield",
        "ccel",
        _WHITEFIELD + "sermons.xlvi.html",
        scripture_ref="1 Corinthians 1:30",
    ),
    SermonEntry(
        "the-lord-our-righteousness",
        "The Lord Our Righteousness",
        "george-whitefield",
        "ccel",
        _WHITEFIELD + "sermons.xvi.html",
        scripture_ref="Jeremiah 23:6",
    ),
    SermonEntry(
        "intercession-every-christians-duty",
        "Intercession Every Christian's Duty",
        "george-whitefield",
        "ccel",
        _WHITEFIELD + "sermons.lvi.html",
        scripture_ref="1 Thessalonians 5:25",
    ),
]
