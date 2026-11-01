"""The curated sermon shelf: individual sermons, one per entry.

Most are public domain (CCEL, Gutenberg); the SermonIndex block carries
still-in-copyright authors (Tozer, Lloyd-Jones) imported with permission — so
"public domain" is not a safe assumption for every entry here.

Like ``catalog.py`` for books, each sermon declares where its clean source
lives. ``source`` is "ccel", "gutenberg", "web", or "sermonindex";
``source_ref`` is the full URL of the per-sermon page (an ebook id for
gutenberg). CCEL parses the scripture reference and preached-on date from the
page itself; the other sources don't, so set the optional ``scripture_ref`` /
``preached_on`` fields where they are known (they also override CCEL when its
parse gets it wrong).

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
    source: str  # "ccel" | "gutenberg" | "web" | "sermonindex" | "archive"
    # ccel/web/sermonindex: full URL of the page; gutenberg: ebook id;
    # archive: the archive.org identifier of the primary scan
    source_ref: str
    section: str = ""  # gutenberg: the heading text of the sermon, at any level
    # gutenberg: the heading tag ("h1".."h4") to match, when `section` names
    # more than one heading (a volume titled after one of its studies).
    section_level: str = ""
    scripture_ref: str = ""  # override; parsed from the page when empty
    preached_on: str = ""  # ISO date override; parsed from the page when empty
    body_starts: str = ""  # web/archive: literal text the sermon's first paragraph starts with
    # archive (see library.archive_ocr): the words its Bible text begins with,
    # the heading that follows the sermon, and other scans of the same edition
    # to cross-check the OCR against.
    text_starts: str = ""
    ends_before: str = ""
    alt_scans: tuple[str, ...] = ()


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
_EDWARDS = "https://ccel.org/ccel/edwards/sermons/"
_NEWTON = "https://ccel.org/ccel/newton/"
_MACLAREN = "https://ccel.org/ccel/maclaren/"
_NPNF106 = "https://ccel.org/ccel/schaff/npnf106/"
# SermonIndex speaker pages — one transcript per page. Full URL is
# _SI + "<speaker-slug>/<sermon-slug>/".
_SI = "https://sermonindex.net/speakers/"

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
        section_level="h1",  # not the <h2> repeat: the epigraph sits between
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
    SermonEntry(
        "a-ribband-of-blue",
        "A Ribband of Blue",
        "hudson-taylor",
        "gutenberg",
        "23438",
        section="A Ribband of Blue",
        section_level="h3",  # the <h1> of that name is the whole volume
        scripture_ref="Numbers 15:38-39",
    ),
    SermonEntry(
        "blessed-prosperity",
        "Blessed Prosperity",
        "hudson-taylor",
        "gutenberg",
        "23438",
        section="Blessed Prosperity",
        scripture_ref="Psalm 1",
    ),
    SermonEntry(
        "a-full-reward",
        "A Full Reward",
        "hudson-taylor",
        "gutenberg",
        "23438",
        section="A Full Reward",
        scripture_ref="Ruth 2:12",
    ),
    SermonEntry(
        "self-denial-versus-self-assertion",
        "Self-Denial versus Self-Assertion",
        "hudson-taylor",
        "gutenberg",
        "23438",
        section="Self-Denial versus Self-Assertion",
        scripture_ref="Luke 9:23",
    ),
    SermonEntry(
        "all-sufficiency",
        "All Sufficiency",
        "hudson-taylor",
        "gutenberg",
        "23438",
        section="All Sufficiency",
        scripture_ref="Psalm 84:11",
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
    # --- Jonathan Edwards: five from CCEL's collection --------------------------
    # Edwards had three books and a bio but no sermon. CCEL's Edwards pages were
    # transcribed piecemeal and every masthead differs (title as <h1> or <h2>,
    # "A Sermon / by / Jonathan Edwards" rows, a bracketed <h5> preaching note, and
    # the scripture in a <blockquote>, a <p>, an <h3> or an <h4>, verse before OR
    # after the reference) — so scripture_ref and preached_on are pinned here
    # rather than trusted to the masthead parser. All five are wholly
    # straight-quoted (a consistent style; QuoteStyleTests only rejects a mix).
    SermonEntry(
        "sinners-in-the-hands-of-an-angry-god",
        "Sinners in the Hands of an Angry God",
        "jonathan-edwards",
        "ccel",
        _EDWARDS + "sermons.sinners.html",
        scripture_ref="Deuteronomy 32:35",
        preached_on="1741-07-08",
    ),
    SermonEntry(
        "a-divine-and-supernatural-light",
        "A Divine and Supernatural Light",
        "jonathan-edwards",
        "ccel",
        _EDWARDS + "sermons.supernatural_light.html",
        scripture_ref="Matthew 16:17",
    ),
    SermonEntry(
        "god-glorified-in-mans-dependence",
        "God Glorified in Man's Dependence",
        "jonathan-edwards",
        "ccel",
        # sermons.dependence.html is a wrapper; .1 is an advertisement, .2 the sermon.
        _EDWARDS + "sermons.dependence.2.html",
        scripture_ref="1 Corinthians 1:29-31",
        preached_on="1731-07-08",
    ),
    SermonEntry(
        "the-excellency-of-christ",
        "The Excellency of Christ",
        "jonathan-edwards",
        "ccel",
        _EDWARDS + "sermons.excellency.html",
        scripture_ref="Revelation 5:5-6",
    ),
    SermonEntry(
        "safety-fulness-and-sweet-refreshment-in-christ",
        "Safety, Fulness, and Sweet Refreshment in Christ",
        "jonathan-edwards",
        "ccel",
        _EDWARDS + "sermons.safety.html",
        scripture_ref="Isaiah 32:2",
    ),
    # --- Tier 2: topping up the authors stuck at one or two sermons -----------
    # Finney: two from CCEL's "Lectures on Revivals of Religion" (a <p class="text">
    # "Text.—verse—ref." masthead, footnotes) and the 1836 sermon that made him
    # famous, from gospeltruth (the Booth-shaped page). Refs pinned throughout.
    SermonEntry(
        "prevailing-prayer",
        "Prevailing Prayer",
        "charles-finney",
        "ccel",
        "https://ccel.org/ccel/finney/revivals/revivals.iii.iv.html",
        scripture_ref="James 5:16",
    ),
    SermonEntry(
        "the-spirit-of-prayer",
        "The Spirit of Prayer",
        "charles-finney",
        "ccel",
        "https://ccel.org/ccel/finney/revivals/revivals.iii.vi.html",
        scripture_ref="Romans 8:26-27",
    ),
    SermonEntry(
        "sinners-bound-to-change-their-own-hearts",
        "Sinners Bound to Change Their Own Hearts",
        "charles-finney",
        "web",
        "https://www.gospeltruth.net/1836SOIS/01sois_sinners_bound.htm",
        scripture_ref="Ezekiel 18:31",
        body_starts="These words were addressed to the house of Israel",
    ),
    # Luther: two more from the Lenker Postil site (see pauls-praise-of-christian-love).
    # The Good Friday sermon meditates on the Passion narrative and carries no text.
    SermonEntry(
        "the-appearing-of-the-grace-of-god",
        "The Appearing of the Grace of God",
        "martin-luther",
        "web",
        "https://sermons.martinluther.us/sermons14.html",
        scripture_ref="Titus 2:11-15",
        body_starts="1. It is written in the book of Nehemiah",
    ),
    SermonEntry(
        "how-to-contemplate-christs-holy-sufferings",
        "How to Contemplate Christ's Holy Sufferings",
        "martin-luther",
        "web",
        "https://sermons.martinluther.us/sermons45.html",
        body_starts="1. In the first place, some reflect",
    ),
    # Chrysostom: NPNF vol. 9 on CCEL, like against-eutropius. A treatise-sermon
    # written from exile; it has no scripture text.
    SermonEntry(
        "no-one-can-harm-the-man-who-does-not-injure-himself",
        "No One Can Harm the Man Who Does Not Injure Himself",
        "john-chrysostom",
        "ccel",
        "https://ccel.org/ccel/schaff/npnf109.xvi.iii.html",
    ),
    # Hudson Taylor: two more studies from "A Ribband of Blue" (PG 23438), the
    # volume blessed-adversity came from; <h3>-delimited, so the section importer
    # bounds them. The epigraph sits in a <div class="c1"> before the prose.
    SermonEntry(
        "under-the-shepherds-care",
        "Under the Shepherd's Care",
        "hudson-taylor",
        "gutenberg",
        "23438",
        section="Under the Shepherd's Care.",
        scripture_ref="1 Peter 2:25",
    ),
    SermonEntry(
        "coming-to-the-king",
        "Coming to the King",
        "hudson-taylor",
        "gutenberg",
        "23438",
        section="Coming to the King.",
        scripture_ref="1 Kings 10:13",
    ),
    # --- Tier 3: backbone additions for thin-but-famous preachers ------------
    # Spurgeon — five more from the New Park Street / Metropolitan Tabernacle
    # Pulpit on CCEL (assurance, grace, comfort, warm gospel appeal).
    SermonEntry(
        "faith",
        "Faith",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons03/sermons03.i.html",
    ),
    SermonEntry(
        "justification-by-grace",
        "Justification by Grace",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons03/sermons03.xx.html",
        # CCEL's scripRef abbreviates the book ("Rom. 3:24"); pin the full
        # form the rest of the shelf uses so a re-import can't drift it.
        scripture_ref="Romans 3:24",
    ),
    SermonEntry(
        "the-shameful-sufferer",
        "The Shameful Sufferer",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons05/sermons05.xiii.html",
    ),
    SermonEntry(
        "the-sinners-friend",
        "The Sinner's Friend",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons10/sermons10.viii.html",
    ),
    SermonEntry(
        "songs-in-the-night",
        "Songs in the Night",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons44/sermons44.ix.html",
    ),
    # D. L. Moody — three more warm gospel addresses from "Wondrous Love"
    # (PG 33520), the volume his earlier addresses came from.
    SermonEntry(
        "naaman-the-syrian",
        "Naaman the Syrian",
        "dwight-l-moody",
        "gutenberg",
        "33520",
        section="NAAMAN THE SYRIAN",
        scripture_ref="2 Kings 5",
    ),
    SermonEntry(
        "the-right-kind-of-faith",
        "The Right Kind of Faith",
        "dwight-l-moody",
        "gutenberg",
        "33520",
        section="THE RIGHT KIND OF FAITH",
        scripture_ref="Acts 16:30",
    ),
    SermonEntry(
        "one-word-gospel",
        'One Word—"Gospel"',
        "dwight-l-moody",
        "gutenberg",
        "33520",
        section='ONE WORD—"GOSPEL"',
        scripture_ref="1 Corinthians 15:1",
    ),
    # A. B. Simpson — two more deeper-life addresses from "The Larger Life",
    # the Alliance-studies source his other addresses came from.
    SermonEntry(
        "filled-with-the-spirit",
        "Filled with the Spirit",
        "a-b-simpson",
        "web",
        "https://online.ambrose.edu/alliancestudies/simpson/larglif5.htm",
        scripture_ref="Ephesians 5:18",
        body_starts="The emphatic word in both these verses",
    ),
    SermonEntry(
        "the-death-of-self",
        "The Death of Self",
        "a-b-simpson",
        "web",
        "https://online.ambrose.edu/alliancestudies/simpson/larglif9.htm",
        scripture_ref="Galatians 2:20",
        body_starts="The story of Abraham, Ishmael and Isaac",
    ),
    # R. A. Torrey — the first sermons on his shelf, from "Revival Addresses"
    # on CCEL. Both are single-leaf addresses: several of the collection's
    # addresses (Refuges of Lies, The Way of Salvation Made as Plain as Day)
    # split their argument across two or three sub-pages, so a single import
    # would catch only the intro — these two carry their whole text on one leaf.
    SermonEntry(
        "the-greatest-sentence-ever-written",
        "The Greatest Sentence That Was Ever Written",
        "r-a-torrey",
        "ccel",
        "https://ccel.org/ccel/torrey/revival.v.ii.html",
        scripture_ref="1 John 4:8",
    ),
    SermonEntry(
        "every-mans-need-of-a-refuge",
        "Every Man's Need of a Refuge",
        "r-a-torrey",
        "ccel",
        "https://ccel.org/ccel/torrey/revival.v.v.html",
        scripture_ref="Isaiah 32:2",
    ),
    # John Newton — his first sermons on the shelf (he was a bio-only author):
    # five of the fifty "Messiah" discourses (1786, CCEL newton/messiah1-2),
    # preached on the scripture passages of Handel's oratorio. Chosen to trace
    # its arc — Advent comfort, gospel invitation, the Lamb, assurance, the
    # closing doxology. Each is a self-contained discourse on its own text.
    SermonEntry(
        "comfort-ye-my-people",
        "Comfort Ye My People",
        "john-newton",
        "ccel",
        _NEWTON + "messiah1/messiah1.iii.html",
    ),
    SermonEntry(
        "come-unto-him",
        "Come Unto Him",
        "john-newton",
        "ccel",
        _NEWTON + "messiah1/messiah1.xvi.html",
    ),
    SermonEntry(
        "behold-the-lamb-of-god",
        "Behold the Lamb of God",
        "john-newton",
        "ccel",
        _NEWTON + "messiah1/messiah1.xviii.html",
    ),
    SermonEntry(
        "if-god-be-for-us",
        "If God Be for Us",
        "john-newton",
        "ccel",
        _NEWTON + "messiah2/messiah2.xxi.html",
    ),
    SermonEntry(
        "worthy-is-the-lamb",
        "Worthy Is the Lamb",
        "john-newton",
        "ccel",
        _NEWTON + "messiah2/messiah2.xxv.html",
    ),
    # J. C. Ryle — the first sermons on his shelf (new author with bio+portrait).
    # Three of his plain-spoken evangelical tracts (prayer, the new birth,
    # assurance) — his best-known voice, from gracegems' clean transcriptions.
    SermonEntry(
        "do-you-pray",
        "Do You Pray?",
        "j-c-ryle",
        "web",
        "https://gracegems.org/Ryle/a_call_to_prayer.htm",
        scripture_ref="Luke 18:1",
        body_starts="I have a question to offer you",
    ),
    SermonEntry(
        "are-you-born-again",
        "Are You Born Again?",
        "j-c-ryle",
        "web",
        "https://gracegems.org/SERMONS/born_again.htm",
        scripture_ref="John 3:3",
        body_starts="This is one of the most important questions in religion",
    ),
    SermonEntry(
        "faith-and-assurance",
        "Faith and Assurance",
        "j-c-ryle",
        "web",
        "https://gracegems.org/Ryle/faith_and_assurance.htm",
        body_starts="Reader, If you are a thoughtless, careless man",
    ),
    # Alexander Maclaren — the first sermons on his shelf (new author with
    # bio+portrait). Single-leaf expositions from his "Expositions of Holy
    # Scripture" on CCEL, each a full expository sermon on its text (grace,
    # faith, and quiet trust). CCEL's scripRef is abbreviated/ALL-CAPS, so pin
    # the full form the shelf uses.
    SermonEntry(
        "grace-and-truth",
        "Grace and Truth",
        "alexander-maclaren",
        "ccel",
        _MACLAREN + "john1/john1.ii.vi.html",
        scripture_ref="John 1:17",
    ),
    SermonEntry(
        "the-power-of-feeble-faith",
        "The Power of Feeble Faith",
        "alexander-maclaren",
        "ccel",
        _MACLAREN + "mark/mark.ii.xxv.html",
        scripture_ref="Mark 5:25-28",
    ),
    SermonEntry(
        "the-secret-of-tranquillity",
        "The Secret of Tranquillity",
        "alexander-maclaren",
        "ccel",
        _MACLAREN + "psalms/psalms.ii.xxix.html",
        scripture_ref="Psalm 37:4-7",
    ),
    # A.W. Tozer — the first sermons on his shelf (bio-only author, no books).
    # Transcribed messages from SermonIndex; curated for full-length, standalone
    # sermons on worship, the cross, backsliding, and the greatness of God — the
    # short devotional excerpts SermonIndex also carries are left off (they fall
    # under the importer's word floor anyway). The three dated pulpit sermons
    # keep the date the transcript records.
    SermonEntry(
        "the-infinite-god", "The Infinite God", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/the-infinite-god/", scripture_ref="Psalm 147:5",
    ),
    SermonEntry(
        "god-is-our-refuge-and-strength", "God Is Our Refuge and Strength",
        "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/god-is-our-refuge-strength/", scripture_ref="Psalm 46:1",
    ),
    SermonEntry(
        "god-made-man-to-worship", "God Made Man to Worship", "a-w-tozer",
        "sermonindex", _SI + "aw-tozer/god-made-man-to-worship/",
    ),
    SermonEntry(
        "all-with-one-accord", "All with One Accord", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/all-with-one-accord/", scripture_ref="Acts 2:1",
    ),
    SermonEntry(
        "the-cross-is-a-radical-thing", "The Cross Is a Radical Thing",
        "a-w-tozer", "sermonindex", _SI + "aw-tozer/the-cross-is-a-radical-thing/",
    ),
    SermonEntry(
        "causes-of-backsliding", "Causes of Backsliding", "a-w-tozer",
        "sermonindex", _SI + "aw-tozer/causes-of-backsliding/",
        scripture_ref="Proverbs 14:14",
    ),
    SermonEntry(
        "a-call-to-return-to-god", "A Call to Return to God", "a-w-tozer",
        "sermonindex", _SI + "aw-tozer/a-call-to-return-to-god/",
    ),
    SermonEntry(
        "the-bridge-that-was-too-short", "The Bridge That Was Too Short",
        "a-w-tozer", "sermonindex", _SI + "aw-tozer/the-bridge-that-was-too-short/",
        scripture_ref="Acts 26",
    ),
    SermonEntry(
        "three-great-days", "Three Great Days: An Easter Message", "a-w-tozer",
        "sermonindex", _SI + "aw-tozer/three-great-days-an-easter-message/",
        preached_on="1958-04-06",
    ),
    SermonEntry(
        "prepare-by-prayer", "Prepare by Prayer", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/prepare-by-prayer/", scripture_ref="Matthew 26:31-46",
        preached_on="1957-06-09",
    ),
    SermonEntry(
        "faith-as-confidence-in-god", "Faith, as Confidence in God", "a-w-tozer",
        "sermonindex", _SI + "aw-tozer/faith-as-confidence-in-god/",
        scripture_ref="John 14:13-14; 1 John 5:14", preached_on="1955-08-21",
    ),
    # Martyn Lloyd-Jones — the first sermons on his shelf (bio-only author, no
    # books). Transcribed from SermonIndex: the Sermon-on-the-Mount trio, the
    # great salvation sermons, and single expository messages on grace, prayer,
    # and revival.
    SermonEntry(
        "the-salt-of-the-earth", "The Salt of the Earth", "martyn-lloyd-jones",
        "sermonindex", _SI + "martyn-lloyd-jones/the-salt-of-the-earth/",
        scripture_ref="Matthew 5:13",
    ),
    SermonEntry(
        "the-light-of-the-world", "The Light of the World", "martyn-lloyd-jones",
        "sermonindex", _SI + "martyn-lloyd-jones/the-light-of-the-world/",
        scripture_ref="Matthew 5:14-16",
    ),
    SermonEntry(
        "god-or-mammon", "God or Mammon", "martyn-lloyd-jones", "sermonindex",
        _SI + "martyn-lloyd-jones/god-or-mammon/", scripture_ref="Matthew 6:19-24",
    ),
    SermonEntry(
        "jesus-on-prayer", "Jesus on Prayer", "martyn-lloyd-jones", "sermonindex",
        _SI + "martyn-lloyd-jones/jesus-on-prayer/", scripture_ref="Matthew 6:5-8",
    ),
    SermonEntry(
        "the-parable-of-the-prodigal-son", "The Parable of the Prodigal Son",
        "martyn-lloyd-jones", "sermonindex",
        _SI + "martyn-lloyd-jones/the-parable-of-the-prodigal-son/",
        scripture_ref="Luke 15:11-32",
    ),
    SermonEntry(
        "working-out-our-own-salvation", "Working Out Our Own Salvation",
        "martyn-lloyd-jones", "sermonindex",
        _SI + "martyn-lloyd-jones/working-out-our-own-salvation/",
        scripture_ref="Philippians 2:12-13",
    ),
    SermonEntry(
        "so-great-salvation", "So Great Salvation", "martyn-lloyd-jones",
        "sermonindex", _SI + "martyn-lloyd-jones/so-great-salvation/",
        scripture_ref="Hebrews 2:1-4",
    ),
    SermonEntry(
        "full-salvation", "Full Salvation", "martyn-lloyd-jones", "sermonindex",
        _SI + "martyn-lloyd-jones/full-salvation/",
    ),
    SermonEntry(
        "the-wrath-of-god", "The Wrath of God", "martyn-lloyd-jones",
        "sermonindex", _SI + "martyn-lloyd-jones/the-wrath-of-god/",
        scripture_ref="Romans 1:18",
    ),
    SermonEntry(
        "a-living-hope-of-the-hereafter", "A Living Hope of the Hereafter",
        "martyn-lloyd-jones", "sermonindex",
        _SI + "martyn-lloyd-jones/a-living-hope-of-the-hereafter/",
        scripture_ref="1 Peter 1:3-4",
    ),
    SermonEntry(
        "what-is-revival", "What Is Revival?", "martyn-lloyd-jones",
        "sermonindex", _SI + "martyn-lloyd-jones/what-is-revival/",
    ),
    # R. A. Torrey — genuine standalone evangelistic and revival addresses
    # (each a single sermon on one text), from SermonIndex. Deliberately NOT his
    # systematic teaching books, which SermonIndex also serves chapter-by-chapter
    # and which belong on the book shelf (several already are) — these are the
    # preached sermons, joining his two existing ones.
    SermonEntry(
        "where-will-you-spend-eternity", "Where Will You Spend Eternity?",
        "r-a-torrey", "sermonindex",
        _SI + "ra-torrey/where-will-you-spend-eternity/", scripture_ref="John 16:5",
    ),
    SermonEntry(
        "refuges-of-lies", "Refuges of Lies", "r-a-torrey", "sermonindex",
        _SI + "ra-torrey/refuges-of-lies/", scripture_ref="Isaiah 28:17",
    ),
    SermonEntry(
        "found-wanting", "Found Wanting", "r-a-torrey", "sermonindex",
        _SI + "ra-torrey/found-wanting/", scripture_ref="Daniel 5:25-27",
    ),
    SermonEntry(
        "excuses", "Excuses", "r-a-torrey", "sermonindex",
        _SI + "ra-torrey/excuses/", scripture_ref="Luke 14:18",
    ),
    SermonEntry(
        "the-most-important-question", "The Most Important Question",
        "r-a-torrey", "sermonindex",
        _SI + "ra-torrey/the-most-important-question-that-any-man-ever-asked-or-answered/",
        scripture_ref="Matthew 27:22",
    ),
    SermonEntry(
        "the-uplifted-christ", "The Great Attraction: The Uplifted Christ",
        "r-a-torrey", "sermonindex",
        _SI + "ra-torrey/the-great-attraction-the-uplifted-christ/",
        scripture_ref="John 12:32",
    ),
    SermonEntry(
        "the-way-of-salvation-made-plain", "The Way of Salvation Made as Plain as Day",
        "r-a-torrey", "sermonindex",
        _SI + "ra-torrey/the-way-of-salvation-made-as-plain-as-day/",
        scripture_ref="Acts 16:30-31",
    ),
    SermonEntry(
        "what-it-costs-not-to-be-a-christian", "What It Costs Not to Be a Christian",
        "r-a-torrey", "sermonindex",
        _SI + "ra-torrey/what-it-costs-not-to-be-a-christian/",
        scripture_ref="Psalm 119:59",
    ),
    SermonEntry(
        "three-fires", "Three Fires", "r-a-torrey", "sermonindex",
        _SI + "ra-torrey/three-fires/", scripture_ref="Matthew 3:11",
    ),
    SermonEntry(
        "the-day-of-golden-opportunity", "The Day of Golden Opportunity",
        "r-a-torrey", "sermonindex",
        _SI + "ra-torrey/the-day-of-golden-opportunity/", scripture_ref="Hebrews 3:7",
    ),
    SermonEntry(
        "heroes-and-cowards", "Heroes and Cowards", "r-a-torrey", "sermonindex",
        _SI + "ra-torrey/heroes-and-cowards/", scripture_ref="Proverbs 29:25",
    ),
    SermonEntry(
        "the-drama-of-life-in-three-acts", "The Drama of Life in Three Acts",
        "r-a-torrey", "sermonindex",
        _SI + "ra-torrey/the-drama-of-life-in-three-acts/", scripture_ref="Luke 15:11",
    ),
    # Corrie ten Boom — transcribed talks from SermonIndex (in copyright; the
    # fixtures carry an `attribution` line so the reader never labels them public
    # domain). Her enduring themes: surrender, forgiveness, the love of Christ,
    # prayer, and steadfastness in tribulation.
    SermonEntry(
        "total-surrender", "Total Surrender", "corrie-ten-boom", "sermonindex",
        _SI + "corrie-ten-boom/total-surrender/",
    ),
    SermonEntry(
        "the-love-of-christ", "The Love of Christ", "corrie-ten-boom", "sermonindex",
        _SI + "corrie-ten-boom/the-love-of-christ/",
    ),
    SermonEntry(
        "power-in-prayer", "Power in Prayer", "corrie-ten-boom", "sermonindex",
        _SI + "corrie-ten-boom/power-in-prayer/",
    ),
    SermonEntry(
        "how-to-forgive", "How to Forgive", "corrie-ten-boom", "sermonindex",
        _SI + "corrie-ten-boom/how-to-forgive/",
    ),
    SermonEntry(
        "tribulation", "Tribulation", "corrie-ten-boom", "sermonindex",
        _SI + "corrie-ten-boom/tribulation/",
    ),
    SermonEntry(
        "the-greatest-of-these-is-love", "The Greatest of These Is Love",
        "corrie-ten-boom", "sermonindex",
        _SI + "corrie-ten-boom/the-greatest-of-these-is-love/",
        scripture_ref="1 Corinthians 13:13",
    ),
    # Elisabeth Elliot — transcribed conference talks from SermonIndex (in
    # copyright; attribution as above). Her short "Gateway to Joy" devotionals
    # are left off (they fall under the importer's word floor). Themes: a quiet
    # heart, the cross, holiness, and the pilgrim life.
    SermonEntry(
        "i-keep-a-quiet-heart", "I Keep a Quiet Heart", "elisabeth-elliot",
        "sermonindex", _SI + "elisabeth-elliot/i-keep-a-quiet-heart/",
        scripture_ref="Psalm 131:2",
    ),
    SermonEntry(
        "how-to-find-rest", "How to Find Rest", "elisabeth-elliot", "sermonindex",
        _SI + "elisabeth-elliot/how-to-find-rest/",
    ),
    SermonEntry(
        "the-meaning-of-the-cross", "The Meaning of the Cross", "elisabeth-elliot",
        "sermonindex", _SI + "elisabeth-elliot/meaning-of-the-cross/",
    ),
    SermonEntry(
        "hearts-set-on-pilgrimage", "Hearts Set on Pilgrimage", "elisabeth-elliot",
        "sermonindex", _SI + "elisabeth-elliot/hearts-set-on-pilgrimage/",
        scripture_ref="Psalm 84:5",
    ),
    SermonEntry(
        "christ-lives-in-me", "Christ Lives in Me", "elisabeth-elliot",
        "sermonindex", _SI + "elisabeth-elliot/christ-lives-in-me/",
        scripture_ref="Galatians 2:20",
    ),
    SermonEntry(
        "women-that-make-a-difference", "Women That Make a Difference",
        "elisabeth-elliot", "sermonindex",
        _SI + "elisabeth-elliot/women-that-make-a-difference/",
    ),
    # William Booth — the Salvation Army's founder (d. 1912, public domain). He
    # left few long text sermons; these are his central atonement message, his
    # defense of the Army's urgency, and two of his famous short evangelistic
    # parables.
    SermonEntry(
        "the-atonement-of-jesus-christ", "The Atonement of Jesus Christ",
        "william-booth", "sermonindex",
        _SI + "william-booth/the-atonement-of-jesus-christ/",
    ),
    SermonEntry(
        "youre-going-too-fast", "You're Going Too Fast", "william-booth",
        "sermonindex", _SI + "william-booth/youre-going-too-fast/",
    ),
    SermonEntry(
        "rope-wanted", "Rope Wanted", "william-booth", "sermonindex",
        _SI + "william-booth/rope-wanted/",
    ),
    SermonEntry(
        "please-sir-save-me", "Please, Sir, Save Me", "william-booth",
        "sermonindex", _SI + "william-booth/please-sir-save-me/",
    ),
    # Catherine Booth — the Army's co-founder and "Mother" (d. 1890, public
    # domain). Full addresses joining her four already on the shelf: on faith,
    # method, child-rearing, soul-work, assurance, and effective service.
    SermonEntry(
        "a-true-and-a-false-faith", "A True and a False Faith", "catherine-booth",
        "sermonindex", _SI + "catherine-booth/a-true-and-a-false-faith/",
        scripture_ref="Galatians 5:6",
    ),
    SermonEntry(
        "adaptation-of-measures", "Adaptation of Measures", "catherine-booth",
        "sermonindex", _SI + "catherine-booth/adaptation-of-measures/",
    ),
    SermonEntry(
        "the-training-of-children", "The Training of Children", "catherine-booth",
        "sermonindex",
        _SI + "catherine-booth/the-training-of-children-an-address-to-parents/",
    ),
    SermonEntry(
        "dealing-with-anxious-souls", "Dealing with Anxious Souls",
        "catherine-booth", "sermonindex",
        _SI + "catherine-booth/dealing-with-anxious-souls-an-address-to-christian-workers/",
    ),
    SermonEntry(
        "assurance-of-salvation", "Assurance of Salvation", "catherine-booth",
        "sermonindex", _SI + "catherine-booth/assurance-of-salvation/",
        scripture_ref="Romans 7:4",
    ),
    SermonEntry(
        "how-to-work-for-god-with-success", "How to Work for God with Success",
        "catherine-booth", "sermonindex",
        _SI + "catherine-booth/how-to-work-for-god-with-success/",
        scripture_ref="Matthew 21:28",
    ),
    # --- 2026-09-29 batch: thin authors topped up ------------------------------
    # Finney — three more of the Lectures on Revivals (1835), joining Prevailing
    # Prayer and The Spirit of Prayer from the same book (which is also on the
    # book shelf; these three are his most-preached lectures).
    SermonEntry(
        "what-a-revival-of-religion-is", "What a Revival of Religion Is",
        "charles-finney", "ccel",
        "https://ccel.org/ccel/finney/revivals/revivals.iii.i.html",
        scripture_ref="Habakkuk 3:2",
    ),
    SermonEntry(
        "breaking-up-the-fallow-ground", "Breaking Up the Fallow Ground",
        "charles-finney", "ccel",
        "https://ccel.org/ccel/finney/revivals/revivals.iii.iii.html",
        scripture_ref="Hosea 10:12",
    ),
    SermonEntry(
        "be-filled-with-the-spirit", "Be Filled with the Spirit",
        "charles-finney", "ccel",
        "https://ccel.org/ccel/finney/revivals/revivals.iii.vii.html",
        scripture_ref="Ephesians 5:18",
    ),
    # Luther — the three great feasts from the Lenker Church Postil. Christmas
    # and Easter are on sermons.martinluther.us like his other Postil sermons;
    # the site stops after Easter, so Pentecost (John 14:23-31) ships as a
    # hand-extracted fixture from the Lenker project's PDF, with no entry here.
    SermonEntry(
        "the-story-of-the-birth-of-jesus", "The Story of the Birth of Jesus",
        "martin-luther", "web", "https://sermons.martinluther.us/sermon13.html",
        scripture_ref="Luke 2:1-14",
        body_starts="1. It is written in Haggai",
    ),
    SermonEntry(
        "of-christs-resurrection", "Of Christ's Resurrection",
        "martin-luther", "web", "https://sermons.martinluther.us/sermons46.html",
        scripture_ref="Mark 16:1-8",
        body_starts="1. In the first place we shall briefly examine",
    ),
    # Wesley — three of the Standard Sermons: the doctrine of salvation, money,
    # and assurance (Discourse I of his two on Romans 8:16).
    SermonEntry(
        "the-scripture-way-of-salvation", "The Scripture Way of Salvation",
        "john-wesley", "ccel", _WESLEY + "sermons.v.xliii.html",
        scripture_ref="Ephesians 2:8",
    ),
    SermonEntry(
        "the-use-of-money", "The Use of Money", "john-wesley", "ccel",
        _WESLEY + "sermons.v.l.html", scripture_ref="Luke 16:9",
    ),
    SermonEntry(
        "the-witness-of-the-spirit", "The Witness of the Spirit", "john-wesley",
        "ccel", _WESLEY + "sermons.v.x.html", scripture_ref="Romans 8:16",
    ),
    # Edwards — Pressing into the Kingdom of God (CCEL sets its text inside an
    # <h4> with the reference, which the parser drops, so the verse is restored
    # by hand), The Christian Pilgrim and Christian Charity (split across several
    # CCEL leaves in Works vol. 2) all ship as hand-built fixtures, no entries.
    # Newton — three more Messiah discourses, on the oratorio's Christmas,
    # Passion and Easter texts.
    SermonEntry(
        "unto-us-a-child-is-born", "Unto Us a Child Is Born", "john-newton",
        "ccel", _NEWTON + "messiah1.xi.html", scripture_ref="Isaiah 9:6",
    ),
    SermonEntry(
        "he-was-despised", "He Was Despised", "john-newton", "ccel",
        _NEWTON + "messiah1.xix.html", scripture_ref="Isaiah 53:3",
    ),
    SermonEntry(
        "i-know-that-my-redeemer-liveth", "I Know That My Redeemer Liveth",
        "john-newton", "ccel", _NEWTON + "messiah2.xv.html",
        scripture_ref="Job 19:25-26",
    ),
    # Chrysostom — three of the NPNF vol. 9 homilies preached at Antioch. Only
    # Homily II on the Statues opens with a masthead the CCEL parser reads; the
    # Paralytic and Lowliness of Mind leaves have no epigraph, so the parser
    # takes their first paragraph for one and drops it — those two ship as
    # hand-extracted fixtures (footnotes stripped) with no entry here.
    SermonEntry(
        "homily-ii-on-the-statues", "Homily II on the Statues",
        "john-chrysostom", "ccel",
        "https://ccel.org/ccel/schaff/npnf109.xix.iv.html",
        scripture_ref="1 Timothy 6:17",
    ),
    # M'Cheyne — mcheyne.info's two remaining printed sermons (A Castaway, Our
    # Duty to Israel) ship as hand-extracted fixtures like his first four; the
    # third comes from SermonIndex's transcription of the Additional Remains.
    SermonEntry(
        "electing-love", "Electing Love", "robert-murray-mcheyne", "sermonindex",
        _SI + "robert-murray-mcheyne/electing-love/",
        scripture_ref="John 15:16",
    ),
    # A.W. Tozer, batch 2 — nine more full-length transcribed sermons from
    # SermonIndex, picked for the clearest transcripts (several others read as
    # raw speech-to-text and were left off). Scripture refs are pinned from each
    # sermon's own opening text, not SermonIndex's generated tags.
    SermonEntry(
        "gods-best-is-himself", "God's Best Is Himself", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/gods-best-is-himself/", scripture_ref="Numbers 18:20",
    ),
    SermonEntry(
        "he-must-increase", "He Must Increase", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/he-must-increase/", scripture_ref="John 3:30",
    ),
    SermonEntry(
        "seraphims-worship", "The Seraphim's Worship", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/seraphims-worship/", scripture_ref="Isaiah 6:1-4",
    ),
    SermonEntry(
        "in-everything-by-prayer", "In Everything by Prayer", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/in-everything-by-prayer/", scripture_ref="Philippians 4:6",
    ),
    SermonEntry(
        "how-to-cultivate-the-holy-spirits-companionship", "How to Cultivate the Holy Spirit's Companionship", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/how-to-cultivate-the-holy-spirits-companionship/", scripture_ref="John 14:16-17",
    ),
    SermonEntry(
        "i-am-crucified-with-christ", "I Am Crucified with Christ", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/i-am-crucified-with-christ/", scripture_ref="Galatians 2:20",
    ),
    SermonEntry(
        "how-to-grow-in-grace", "How to Grow in Grace", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/how-to-grow-in-grace/", scripture_ref="2 Peter 3:18",
    ),
    SermonEntry(
        "how-to-have-a-personal-revival", "How to Have a Personal Revival", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/how-to-have-a-personal-revival/",
    ),
    SermonEntry(
        "praying-church", "The Praying Church", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/praying-church/", scripture_ref="James 5:16",
    ),
    # A. B. Simpson, batch 2 — nine standalone printed sermons from SermonIndex,
    # each opening on its own text. Public domain (Simpson d. 1919). Several of
    # his SermonIndex texts come from a modernized edition ("my eye sees You" for
    # the KJV "mine eye seeth thee") — those are left off; only texts that keep
    # his own King James quotations are taken. His one-page devotionals there
    # fall under the importer's word floor.
    SermonEntry(
        "the-spirit-of-prayer-simpson", "The Spirit of Prayer", "a-b-simpson",
        "sermonindex", _SI + "ab-simpson/the-spirit-of-prayer/",
        scripture_ref="Romans 8:26",
    ),
    SermonEntry(
        "the-school-of-faith", "The School of Faith", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/the-school-of-faith/", scripture_ref="Hebrews 12:11",
    ),
    SermonEntry(
        "practical-prayer", "Practical Prayer", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/practical-prayer/", scripture_ref="James 5:16",
    ),
    SermonEntry(
        "the-great-secret", "The Great Secret", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/the-great-secret/", scripture_ref="Philippians 4:11-12",
    ),
    SermonEntry(
        "the-boundless-sufficiency", "The Boundless Sufficiency", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/the-boundless-sufficiency/", scripture_ref="Philippians 4:19",
    ),
    SermonEntry(
        "the-cloud-of-witnesses", "The Cloud of Witnesses", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/the-cloud-of-witnesses/", scripture_ref="Hebrews 12:1",
    ),
    SermonEntry(
        "the-logic-of-missions", "The Logic of Missions", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/the-logic-of-missions/", scripture_ref="Romans 10:14-15",
    ),
    SermonEntry(
        "wholly-sanctified", "Wholly Sanctified", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/wholly-sanctified/", scripture_ref="1 Thessalonians 5:23",
    ),
    SermonEntry(
        "the-practical-hope-of-the-lords-coming", "The Practical Hope of the Lord's Coming", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/the-practical-hope-of-the-lords-coming/", scripture_ref="James 5:7-8",
    ),
    # A.W. Tozer, batch 3 — more full-length transcribed sermons from SermonIndex,
    # each read in full before shipping (wrong-title pages, splices and garbled
    # transcripts are left off). Refs pinned from each sermon's own opening.
    SermonEntry(
        "the-hidden-life-of-faith", "The Hidden Life of Faith", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/the-hidden-life-of-faith/", scripture_ref="Exodus 33:22",
    ),
    SermonEntry(
        "what-difference-does-the-holy-spirit-make", "What Difference Does the Holy Spirit Make?", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/what-difference-does-the-holy-spirit-make/",
    ),
    SermonEntry(
        "the-sin-of-murmuring", "The Sin of Murmuring", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/the-sin-of-murmuring/", scripture_ref="1 Corinthians 10:1-13",
    ),
    SermonEntry(
        "the-triumph-of-the-resurrection", "The Triumph of the Resurrection", "a-w-tozer", "sermonindex",
        _SI + "aw-tozer/the-triumph-of-the-resurrection/", scripture_ref="Acts 2:22-39",
    ),
    # A. B. Simpson, batch 3 — printed sermons that keep his King James
    # quotations (the modernized-edition texts on SermonIndex are left off).
    SermonEntry(
        "partnership-with-god", "Partnership with God", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/partnership-with-god/",
    ),
    SermonEntry(
        "gideon-or-the-strength-of-weakness", "Gideon, or the Strength of Weakness", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/gideon-or-the-strength-of-weakness/", scripture_ref="1 Corinthians 1:27-29",
    ),
    SermonEntry(
        "jephthah-or-the-faith-that-leads-to-faithfulness", "Jephthah, or the Faith That Leads to Faithfulness", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/jephthah-or-the-faith-that-leads-to-faithfulness/", scripture_ref="Judges 11:30-36",
    ),
    SermonEntry(
        "bochim-or-the-cause-of-spiritual-failure", "Bochim, or the Cause of Spiritual Failure", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/bochim-or-the-cause-of-spiritual-failure/", scripture_ref="Judges 2:5",
    ),
    SermonEntry(
        "the-practical-discipline-of-life", "The Practical Discipline of Life", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/the-practical-discipline-of-life/", scripture_ref="James 1:2",
    ),
    SermonEntry(
        "the-christian-temper-supernatural-and-divine", "The Christian Temper, Supernatural and Divine", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/the-christian-temper-supernatural-and-divine/", scripture_ref="Philippians 3:10-11",
    ),
    SermonEntry(
        "the-goal-of-faith", "The Goal of Faith", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/the-goal-of-faith/", scripture_ref="Hebrews 12:18-24",
    ),
    # A. B. Simpson, batch 4 — standalone printed sermons that keep his King James
    # quotations. Chapters of his serial books on SermonIndex (Power from on
    # High, the Emblems series, the Christ in the Bible studies) are left for a
    # future book import rather than split onto the sermon shelf.
    SermonEntry(
        "personal-responsibility", "Personal Responsibility", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/personal-responsibility/",
    ),
    SermonEntry(
        "more-than-conquerors", "More Than Conquerors", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/more-than-conquerors/", scripture_ref="Romans 8:37",
    ),
    SermonEntry(
        "grace-abounding", "Grace Abounding", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/grace-abounding/", scripture_ref="Romans 5:20",
    ),
    SermonEntry(
        "from-strength-to-strength", "From Strength to Strength", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/from-strength-to-strength/", scripture_ref="Psalm 84:7",
    ),
    SermonEntry(
        "hindering-the-holy-spirit", "Hindering the Holy Spirit", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/hindering-the-holy-spirit/",
    ),
    SermonEntry(
        "spiritual-growth", "Spiritual Growth", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/spiritual-growth/", scripture_ref="2 Peter 3:18",
    ),
    SermonEntry(
        "words-for-discouraged-workers", "Words for Discouraged Workers", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/words-for-discouraged-workers/",
    ),
    SermonEntry(
        "the-weapons-of-our-warfare", "The Weapons of Our Warfare", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/the-weapons-of-our-warfare/", scripture_ref="2 Corinthians 10:4",
    ),
    SermonEntry(
        "our-kinsman-redeemer", "Our Kinsman Redeemer", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/our-kinsman-redeemer-lessons-from-the-book-of-ruth/", scripture_ref="Isaiah 54:5",
    ),
    SermonEntry(
        "how-to-abide", "How to Abide", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/how-to-abide/", scripture_ref="1 John 2:28",
    ),
    SermonEntry(
        "sinning-and-repenting", "Sinning and Repenting", "a-b-simpson", "sermonindex",
        _SI + "ab-simpson/sinning-and-repenting/", scripture_ref="Judges 2:14-19",
    ),
    # Spurgeon, batch 2 — the Pulpit as printed, with the Authorised Version he
    # quoted. Most CCEL sermons from about 1862 on are a later digital text that
    # modernised his Scripture ("all you that labor") and splits paragraphs at
    # page breaks, so every pick was screened by KJV-archaism density first (see
    # build_spirit_anthology). Sermons already gathered in Spurgeon on Prayer or
    # Spurgeon on the Holy Spirit (The Throne of Grace, The Comforter, …) are
    # left to those books. The Sin of Unbelief (No. 3) was read and dropped: it
    # bids the hearer tell every Jew he meets that unbelief made him "murder
    # Christ" and a homeless wanderer.
    SermonEntry(
        "a-faithful-friend",
        "A Faithful Friend",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons03/sermons03.xiv.html",
    ),
    SermonEntry(
        "prayer-the-forerunner-of-mercy",
        "Prayer—the Forerunner of Mercy",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons03/sermons03.xxxii.html",
    ),
    SermonEntry(
        "looking-unto-jesus",
        "Looking Unto Jesus",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons04/sermons04.xxxi.html",
    ),
    SermonEntry(
        "come-and-welcome",
        "Come and Welcome",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons05/sermons05.liv.html",
    ),
    SermonEntry(
        "the-blood-of-the-everlasting-covenant",
        "The Blood of the Everlasting Covenant",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons05/sermons05.lii.html",
    ),
    SermonEntry(
        "loves-logic",
        "Love's Logic",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons17/sermons17.xli.html",
    ),
    # Its closing appeal quotes an enslaved man in minstrel dialect ("Massa, I
    # fall flat on de promise"). Unpublished 2026-10, then republished
    # unedited on the founder's decision (2026-11).
    SermonEntry(
        "healing-for-the-wounded",
        "Healing for the Wounded",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons01/sermons01.l.html",
    ),
    SermonEntry(
        "a-simple-sermon-for-seeking-souls",
        "A Simple Sermon for Seeking Souls",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons03/sermons03.xxxiv.html",
    ),
    SermonEntry(
        "waiting-only-upon-god",
        "Waiting Only Upon God",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons03/sermons03.xxxvii.html",
    ),
    SermonEntry(
        "a-lecture-for-little-faith",
        "A Lecture for Little-Faith",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons04/sermons04.xli.html",
    ),
    SermonEntry(
        "prayer-answered-love-nourished",
        "Prayer Answered, Love Nourished",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons05/sermons05.xvii.html",
    ),
    SermonEntry(
        "mr-fearing-comforted",
        "Mr. Fearing Comforted",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons05/sermons05.xxiii.html",
    ),
    SermonEntry(
        "consolation-in-christ",
        "Consolation in Christ",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons07/sermons07.i.html",
    ),
    # Middle tier, batch 1 — three each for M'Cheyne, Ryle, Maclaren and Moody,
    # checked against their books for overlap (Maclaren has a fourth). Moody's two
    # are from The Overcoming Life (PG 33015); two more were read and dropped —
    # Wondrous Love's "The Blood" for the Jews' "honour of killing the Christian's
    # God", and "Results of True Repentance" for a quoted illustration that makes
    # Black skin the picture of sin; Ryle's are
    # sermons he revised for The Upper Room (1888) — not "Let Any Man Come", which
    # is Holiness ch. 18 again, nor "The Good Way" (a quarter is Old Paths ch. 15);
    # M'Cheyne's are SermonIndex transcriptions of the 1840s printed text
    # (KJV-dense, unlike its modernised Davies and Winslow pages).
    SermonEntry(
        "true-wisdom", "True Wisdom", "dwight-l-moody", "gutenberg", "33015",
        section="TRUE WISDOM.",
        scripture_ref="Daniel 12:3",
    ),
    SermonEntry(
        "humility", "Humility", "dwight-l-moody", "gutenberg", "33015",
        section="HUMILITY.",
        scripture_ref="Matthew 11:29",
    ),
    SermonEntry(
        "victory", "Victory", "j-c-ryle", "ccel",
        "https://ccel.org/ccel/ryle/upper_room/upper_room.x.html",
    ),
    SermonEntry(
        "to-whom", "To Whom?", "j-c-ryle", "ccel",
        "https://ccel.org/ccel/ryle/upper_room/upper_room.xiii.html",
    ),
    SermonEntry(
        "without-clouds", "Without Clouds", "j-c-ryle", "ccel",
        "https://ccel.org/ccel/ryle/upper_room/upper_room.xvi.html",
        scripture_ref="2 Samuel 23:4-5",
    ),
    SermonEntry(
        "the-burden-bearing-god", "The Burden-Bearing God", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.iii.xi.html", scripture_ref="Psalm 68:19",
    ),
    SermonEntry(
        "thirsting-for-god", "Thirsting for God", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.ii.xxxii.html",
        scripture_ref="Psalm 42:2",
    ),
    SermonEntry(
        "let-us-have-peace", "Let Us Have Peace", "alexander-maclaren", "ccel",
        _MACLAREN + "rom_cor/rom_cor.ii.ix.html",
        scripture_ref="Romans 5:1",
    ),
    SermonEntry(
        "christs-peace", "Christ's Peace", "alexander-maclaren", "ccel",
        _MACLAREN + "john1/john1.ii.lxxvi.html", scripture_ref="John 14:27",
    ),
    SermonEntry(
        "believers-not-ashamed", "Believers Not Ashamed", "robert-murray-mcheyne", "sermonindex",
        _SI + "robert-murray-mcheyne/believers-not-ashamed/",
        scripture_ref="Romans 1:15-17",
    ),
    SermonEntry(
        "the-saviours-tears-over-the-lost", "The Saviour's Tears over the Lost",
        "robert-murray-mcheyne", "sermonindex",
        _SI + "robert-murray-mcheyne/the-saviours-tears-over-the-lost/",
        scripture_ref="Luke 19:41-42",
    ),
    SermonEntry(
        "the-cry-for-revival", "The Cry for Revival", "robert-murray-mcheyne", "sermonindex",
        _SI + "robert-murray-mcheyne/the-cry-for-revival/",
        scripture_ref="Psalm 85:6",
    ),
    # New preachers, batch 1. F. W. Robertson from Gutenberg; Samuel Davies,
    # Thomas Chalmers and Horatius Bonar from archive.org scans of the printed
    # editions, since the only clean-looking copies online are modernised
    # rewrites (SermonIndex's Davies quotes the NIV). The OCR is cleaned and
    # cross-checked against other scans of the same edition (see
    # library.archive_ocr): Davies, Sermons, vol. 1 (New York, 1864); Chalmers,
    # Sermons and Discourses, vol. 2 (New York, 1844) — the St John's Church
    # sermons; Bonar, Family Sermons (New York, 1863), one scan only.
    SermonEntry(
        "the-prodigal-and-his-brother", "The Prodigal and His Brother",
        "frederick-w-robertson", "gutenberg", "16645",
        section="XX. Preached February 21, 1853. THE PRODIGAL AND HIS BROTHER.",
        scripture_ref="Luke 15:11-32", preached_on="1853-02-21",
    ),
    SermonEntry(
        "victory-over-death", "Victory over Death", "frederick-w-robertson", "gutenberg", "16645",
        section="XVII. Preached May 16, 1852. VICTORY OVER DEATH.",
        scripture_ref="1 Corinthians 15:56-57", preached_on="1852-05-16",
    ),
    SermonEntry(
        "the-power-of-sorrow", "The Power of Sorrow", "frederick-w-robertson", "gutenberg", "16645",
        section="VIII. Preached June 30, 1850. THE POWER OF SORROW.",
        scripture_ref="2 Corinthians 7:10", preached_on="1850-06-30",
    ),
    SermonEntry(
        "sinners-entreated-to-be-reconciled-to-god", "Sinners Entreated to Be Reconciled to God",
        "samuel-davies", "archive", "sermonsdavies01daviiala", alt_scans=("sermons_01daviuoft",),
        text_starts="Now then we are ambassadors", body_starts="To preside in the solemnities",
        ends_before="SERMON IV.", scripture_ref="2 Corinthians 5:20",
    ),
    SermonEntry(
        "making-light-of-christ", "The Nature and Danger of Making Light of Christ",
        "samuel-davies", "archive", "sermonsdavies01daviiala", alt_scans=("sermons_01daviuoft",),
        text_starts="But they made light of it", body_starts="There is not one of us in this assembly",
        ends_before="SERMON VIII.", scripture_ref="Matthew 22:5",
    ),
    SermonEntry(
        "the-compassion-of-christ-to-weak-believers", "The Compassion of Christ to Weak Believers",
        "samuel-davies", "archive", "sermonsdavies01daviiala", alt_scans=("sermons_01daviuoft",),
        text_starts="A bruised reed shall he not break", body_starts="The Lord Jesus possesses all those virtues",
        ends_before="SERMON IX.", scripture_ref="Matthew 12:20",
    ),
    SermonEntry(
        "the-expulsive-power-of-a-new-affection", "The Expulsive Power of a New Affection",
        "thomas-chalmers", "archive", "sermonsdiscourse02chal", alt_scans=("sermonsdiscoursesd02chal", "sermonsanddisco03chalgoog"),
        text_starts="neither the things that are in the world", body_starts="There are two ways",
        ends_before="SERMON III.", scripture_ref="1 John 2:15",
    ),
    SermonEntry(
        "the-sure-warrant-of-a-believers-hope", "The Sure Warrant of a Believer's Hope",
        "thomas-chalmers", "archive", "sermonsdiscourse02chal", alt_scans=("sermonsdiscoursesd02chal", "sermonsanddisco03chalgoog"),
        text_starts="we were reconciled to God by the death", body_starts="St. Paul, who, by the way",
        ends_before="SERMON IV.", scripture_ref="Romans 5:10",
    ),
    SermonEntry(
        "the-transitory-nature-of-visible-things", "The Transitory Nature of Visible Things",
        "thomas-chalmers", "archive", "sermonsdiscourse02chal", alt_scans=("sermonsdiscoursesd02chal", "sermonsanddisco03chalgoog"),
        text_starts="are temporal", body_starts="The assertion that the things which are seen",
        ends_before="SERMON VI.", scripture_ref="2 Corinthians 4:18",
    ),
    SermonEntry(
        "faith-in-an-unseen-christ", "Faith in an Unseen Christ", "horatius-bonar", "archive",
        "familysermons00bona", text_starts="Blessed are they that have not seen",
        body_starts="Here is another", ends_before="CONSECRATION BY BLOOD", scripture_ref="John 20:29",
    ),
    SermonEntry(
        "a-present-saviour", "A Present Saviour", "horatius-bonar", "archive",
        "familysermons00bona", text_starts="And knew not that it was Jesus",
        body_starts="When Jesus comes the second time", ends_before="SERMON XXIX.",
        scripture_ref="John 20:14",
    ),
    SermonEntry(
        "the-vain-wish", "The Vain Wish", "horatius-bonar", "archive",
        "familysermons00bona", text_starts="die the death of the righteous, and let my last end",
        body_starts="We must not lose sight of the place", ends_before="SERMON XLVIII.",
        scripture_ref="Numbers 23:10",
    ),
    # Spurgeon, batch 3 — the Pulpit as printed (1855–1860), screened as batch 2
    # was: KJV-archaism density, no page-split damage, and text overlap with the
    # library (Comfort Proclaimed and The Christian's Heaviness are 10–13%
    # Gleanings among the Sheaves). Pages that end in a publisher's notice (The
    # God of the Aged, Light at Evening Time) were passed over. Read and dropped:
    # The God of Peace, which closes on the Tabernacle building fund, and The
    # Meek and Lowly One, whose opening illustration caricatures Islam as spread
    # by "decapitation or impalement"; A Mighty Saviour, whose main proof paints a
    # "South Sea Islander" as a cannibal "very little removed from the brute";
    # and Love's Commendation, for an anecdote told in caricatured Black dialect.
    SermonEntry(
        "consolation-proportionate-to-spiritual-sufferings",
        "Consolation Proportionate to Spiritual Sufferings",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons01/sermons01.xii.html",
    ),
    SermonEntry(
        "the-desire-of-the-soul-in-spiritual-darkness",
        "The Desire of the Soul in Spiritual Darkness",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons01/sermons01.xxx.html",
    ),
    SermonEntry(
        "salvation-to-the-uttermost",
        "Salvation to the Uttermost",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons02/sermons02.xxx.html",
    ),
    SermonEntry(
        "lovest-thou-me",
        "Lovest Thou Me?",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons03/sermons03.xi.html",
    ),
    SermonEntry(
        "heavenly-rest",
        "Heavenly Rest",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons03/sermons03.xxvii.html",
    ),
    SermonEntry(
        "christ-lifted-up",
        "Christ Lifted Up",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons03/sermons03.xxxiii.html",
    ),
    SermonEntry(
        "fear-not",
        "Fear Not",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons03/sermons03.xlviii.html",
    ),
    SermonEntry(
        "as-thy-days-so-shall-thy-strength-be",
        "As Thy Days, So Shall Thy Strength Be",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons04/sermons04.xlvi.html",
    ),
    SermonEntry(
        "the-new-heart",
        "The New Heart",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons04/sermons04.xlviii.html",
    ),
    SermonEntry(
        "spiritual-peace",
        "Spiritual Peace",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons06/sermons06.xiv.html",
    ),
    SermonEntry(
        "one-antidote-for-many-ills",
        "One Antidote for Many Ills",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons05/sermons05.lix.html",
        # The Pulpit prints "Psalm 80:10"; the words are verse 19.
        scripture_ref="Psalm 80:19",
    ),
    SermonEntry(
        "the-treasure-of-grace",
        "The Treasure of Grace",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons06/sermons06.x.html",
    ),
    SermonEntry(
        "thy-redeemer",
        "Thy Redeemer",
        "charles-h-spurgeon",
        "ccel",
        _CCEL + "sermons03/sermons03.xlix.html",
    ),
    # Alexander Maclaren, third batch: warm expositions from *Expositions of
    # Holy Scripture* — comfort, prayer, the Christian life — screened with
    # `screen_sermons`; judgment-centred titles left on the shelf. *The Fruit of
    # the Spirit* (iicor_tim.ii.ii.viii) was dropped: its epigraph carries no
    # scripRef link, so `extract` took an in-body reference as the masthead end
    # and lost the first eight paragraphs.
    SermonEntry(
        "the-secret-of-immortal-youth", "The Secret of Immortal Youth", "alexander-maclaren", "ccel",
        _MACLAREN + "isa_jer/isa_jer.ii.i.xlix.html", scripture_ref="Isaiah 40:30-31",
    ),
    SermonEntry(
        "the-writing-on-gods-hands", "The Writing on God's Hands", "alexander-maclaren", "ccel",
        _MACLAREN + "isa_jer/isa_jer.ii.ii.iv.html", scripture_ref="Isaiah 49:16",
    ),
    SermonEntry(
        "the-hiding-place", "The Hiding-Place", "alexander-maclaren", "ccel",
        _MACLAREN + "isa_jer/isa_jer.ii.i.xxxiv.html", scripture_ref="Isaiah 32:2",
    ),
    SermonEntry(
        "the-call-to-the-thirsty", "The Call to the Thirsty", "alexander-maclaren", "ccel",
        _MACLAREN + "isa_jer/isa_jer.ii.ii.xxiv.html", scripture_ref="Isaiah 55:1-13",
    ),
    SermonEntry(
        "the-shepherd-king-of-israel", "The Shepherd King of Israel", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.ii.xi.html", scripture_ref="Psalm 23:1-6",
    ),
    SermonEntry(
        "into-thy-hands", "Into Thy Hands", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.ii.xx.html", scripture_ref="Psalm 31:5",
    ),
    SermonEntry(
        "the-encamping-angel", "The Encamping Angel", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.ii.xxiv.html", scripture_ref="Psalm 34:7",
    ),
    SermonEntry(
        "the-fixed-heart", "The Fixed Heart", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.iii.vi.html", scripture_ref="Psalm 57:7",
    ),
    SermonEntry(
        "looking-to-the-hills", "Looking to the Hills", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.iii.xxxviii.html", scripture_ref="Psalm 121:1-2",
    ),
    SermonEntry(
        "the-true-vine", "The True Vine", "alexander-maclaren", "ccel",
        _MACLAREN + "john2/john2.ii.ii.html", scripture_ref="John 15:1-4",
    ),
    SermonEntry(
        "christs-friends", "Christ's Friends", "alexander-maclaren", "ccel",
        _MACLAREN + "john2/john2.ii.vi.html", scripture_ref="John 15:14-17",
    ),
    SermonEntry(
        "sorrow-turned-into-joy", "Sorrow Turned into Joy", "alexander-maclaren", "ccel",
        _MACLAREN + "john2/john2.ii.xv.html", scripture_ref="John 16:20-22",
    ),
    SermonEntry(
        "the-praying-christ", "The Praying Christ", "alexander-maclaren", "ccel",
        _MACLAREN + "luke/luke.ii.xliv.html", scripture_ref="Luke 11:1",
    ),
    SermonEntry(
        "the-prodigal-and-his-father", "The Prodigal and His Father", "alexander-maclaren", "ccel",
        _MACLAREN + "luke/luke.iii.ix.html", scripture_ref="Luke 15:11-24",
    ),
    SermonEntry(
        "rejoice-evermore", "Rejoice Evermore", "alexander-maclaren", "ccel",
        _MACLAREN + "iicor_tim/iicor_tim.iii.i.iii.html", scripture_ref="Philippians 4:4",
    ),
    # John Henry Newman — his first sermons on the shelf, from *Parochial and
    # Plain Sermons* VII–VIII (Gutenberg; newmanreader.org's text is under
    # copyright). Practical holiness only: the volumes' sermons on baptism,
    # church order and "the old paths" are left out. Each volume heads its
    # sermons "SERMON VIII." at h2 (the contents repeat it at h4) and prints the
    # title as the first paragraph, which the importer drops. Read in full and
    # dropped for tone: *The Lapse of Time* (judgment its thrust), *Mental
    # Prayer* (closes on hell for careless youth), *The Season of Epiphany* and
    # *The Crucifixion* (bound to their day; the latter chides those who keep
    # no Good Friday), *The Yoke of Christ*, *The Duty of Self-Denial*, *Doing
    # Glory to God in Pursuits of the World* and *Love of Religion, a New
    # Nature* (asides against "enthusiasts", "faith alone" and Dissenters).
    SermonEntry(
        "temporal-advantages", "Temporal Advantages", "john-henry-newman", "gutenberg", "24256",
        section="SERMON V.", section_level="h2", scripture_ref="1 Timothy 6:7-8",
    ),
    SermonEntry(
        "religion-pleasant-to-the-religious", "Religion Pleasant to the Religious", "john-henry-newman", "gutenberg", "24256",
        section="SERMON XIV.", section_level="h2", scripture_ref="Psalm 34:8",
    ),
    SermonEntry(
        "divine-calls", "Divine Calls", "john-henry-newman", "gutenberg", "24284",
        section="SERMON II.", section_level="h2", scripture_ref="1 Samuel 3:10",
    ),
    SermonEntry(
        "jeremiah-a-lesson-for-the-disappointed", "Jeremiah, a Lesson for the Disappointed", "john-henry-newman", "gutenberg", "24284",
        section="SERMON IX.", section_level="h2", scripture_ref="Jeremiah 1:8",
    ),
    SermonEntry(
        "the-shepherd-of-our-souls", "The Shepherd of Our Souls", "john-henry-newman", "gutenberg", "24284",
        section="SERMON XVI.", section_level="h2", scripture_ref="John 10:11",
    ),
    SermonEntry(
        "religious-joy", "Religious Joy", "john-henry-newman", "gutenberg", "24284",
        section="SERMON XVII.", section_level="h2", scripture_ref="Luke 2:10-11",
    ),
    # Batch 4 toward 400 (2026-11): warm sermons from authors already on the
    # shelf, screened with `screen_sermons` and read in full against the tone
    # rubric (sermon-import skill). John Newton, more of *Messiah* (the
    # "Opposition to Messiah" sermons left out). Read and dropped: *The Great
    # Shepherd* (ends denouncing idle clergy, with Leo X's "lucrative fable"),
    # *The Intercession of Christ* and *Death Swallowed Up in Victory* (close on
    # damnation; the latter also attacks universalism).
    SermonEntry(
        "messiahs-easy-yoke", "Messiah's Easy Yoke", "john-newton", "ccel",
        _NEWTON + "messiah1/messiah1.xvii.html", scripture_ref="Matthew 11:29-30",
    ),
    SermonEntry(
        "the-angels-message-and-song", "The Angel's Message and Song", "john-newton", "ccel",
        _NEWTON + "messiah1/messiah1.xii.html", scripture_ref="Luke 2:8-14",
    ),
    SermonEntry(
        "messiah-suffering-and-wounded-for-us", "Messiah Suffering and Wounded for Us", "john-newton", "ccel",
        _NEWTON + "messiah1/messiah1.xxi.html", scripture_ref="Isaiah 53:4-5",
    ),
    SermonEntry(
        "the-lord-is-risen-indeed", "The Lord Is Risen Indeed", "john-newton", "ccel",
        _NEWTON + "messiah2/messiah2.xvi.html", scripture_ref="1 Corinthians 15:20",
    ),
    # Robert Murray M"Cheyne, from SermonIndex"s printed text (no Bible
    # reference there, so each is set here). *Children Called to Christ* is a
    # 152-word poem there, not a sermon. Read and dropped for tone: *Melting the
    # Betrayer* (a warning to unworthy communicants throughout) and *Faith's
    # View of Christ* ("many of you are going to hell").
    SermonEntry(
        "adoption", "Adoption", "robert-murray-mcheyne", "sermonindex",
        _SI + "robert-murray-mcheyne/adoption/", scripture_ref="1 John 3:1",
    ),
    SermonEntry(
        "grieve-not-the-holy-spirit", "Grieve Not the Holy Spirit", "robert-murray-mcheyne", "sermonindex",
        _SI + "robert-murray-mcheyne/grieve-not-the-holy-spirit/", scripture_ref="Ephesians 4:30",
    ),
    SermonEntry(
        "the-spirit-committed-to-god", "The Spirit Committed to God", "robert-murray-mcheyne", "sermonindex",
        _SI + "robert-murray-mcheyne/the-spirit-commited-to-god/", scripture_ref="Psalm 31:5",
    ),
    SermonEntry(
        "the-lords-dealings-with-his-people", "The Lord's Dealings with His People", "robert-murray-mcheyne", "sermonindex",
        _SI + "robert-murray-mcheyne/the-lords-dealings-with-his-people/", scripture_ref="Isaiah 46:3-4",
    ),
    SermonEntry(
        "thanksgiving-obtains-the-spirit", "Thanksgiving Obtains the Spirit", "robert-murray-mcheyne", "sermonindex",
        _SI + "robert-murray-mcheyne/thanksgiving-obtains-the-spirit/", scripture_ref="2 Chronicles 5:13-14",
    ),
    # Horatius Bonar, more of *Family Sermons* (single scan; see archive_ocr).
    # Only sermons complete in one part: the volume prints several as pairs.
    # *Christ the Healer* is suffixed: A. B. Simpson's book holds the slug.
    # *Nazareth and Its Good News* was dropped (grace "transformed into
    # vengeance"; "the worst specimens of Israel").
    SermonEntry(
        "bethlehem-and-its-good-news", "Bethlehem and Its Good News", "horatius-bonar", "archive",
        "familysermons00bona", text_starts="The Word was made flesh", body_starts="There was nothing great about Bethlehem", ends_before="SERMON II.", scripture_ref="John 1:14",
    ),
    SermonEntry(
        "christ-the-healer-bonar", "Christ the Healer", "horatius-bonar", "archive",
        "familysermons00bona", text_starts="If I may but touch his garment", body_starts="Here, we may say", ends_before="CHRIST THE CLEANSER", scripture_ref="Matthew 9:21",
    ),
    SermonEntry(
        "christ-the-cleanser", "Christ the Cleanser", "horatius-bonar", "archive",
        "familysermons00bona", text_starts="He that is washed needeth not", body_starts="This washing of the disciples", ends_before="SERMON XIII.", scripture_ref="John 13:10",
    ),
    SermonEntry(
        "bethany-and-its-feast", "Bethany and Its Feast", "horatius-bonar", "archive",
        "familysermons00bona", text_starts="Then Jesus, six days before the passover", body_starts="We find ourselves here at Bethany", ends_before="SERMON XLIV.", scripture_ref="John 12:1-3",
    ),
    SermonEntry(
        "the-mortal-and-the-immortal", "The Mortal and the Immortal", "horatius-bonar", "archive",
        "familysermons00bona", text_starts="Neither can they die any more", body_starts="Ours is a dying world", ends_before="LONGINGS FOR THE LAND", scripture_ref="Luke 20:36",
    ),
    SermonEntry(
        "the-divine-banquet", "The Divine Banquet", "horatius-bonar", "archive",
        "familysermons00bona", text_starts="He shall eat the bread of his God", body_starts="It is not easy to say whether", ends_before="SERMON XLIII.", scripture_ref="Leviticus 21:22",
    ),
    # Augustine, his first sermons on the shelf: *Sermons on Selected Lessons of
    # the New Testament* (NPNF 1st series vol. 6, R. G. MacMullen's 1888
    # translation, CCEL). Pastoral Gospel sermons only — those headed against
    # the Donatists, Arians or Pelagians are left out, and four more were read
    # and dropped: *The Boat in the Storm* (a section against docetic
    # heretics), *Men Ought Always to Pray* and *Ask, and It Shall Be Given*
    # (against the Pelagians; the latter closes on an alms appeal), and *The
    # Friend at Midnight* (its last third answers pagan critics of the sack of
    # Rome).
    SermonEntry(
        "peter-on-the-waves", "Peter on the Waves", "augustine-of-hippo", "ccel",
        _NPNF106 + "npnf106.vii.xxviii.html", scripture_ref="Matthew 14:25-31",
    ),
    SermonEntry(
        "martha-and-mary", "Martha and Mary", "augustine-of-hippo", "ccel",
        _NPNF106 + "npnf106.vii.lv.html", scripture_ref="Luke 10:38-42",
    ),
    SermonEntry(
        "asking-in-christs-name", "Asking in Christ's Name", "augustine-of-hippo", "ccel",
        _NPNF106 + "npnf106.vii.xcvii.html", scripture_ref="John 16:24",
    ),
    # Batch 5 toward 400 (2026-11): more of Maclaren's *Expositions* (John,
    # Romans–Corinthians, Mark, Matthew, Genesis–Numbers, Acts), warm titles only,
    # and Bonar's remaining single-part *Family Sermons* (*Christ and the World*
    # and *The Three Witnesses* passed over as set against "the world").
    # Two Maclaren titles are suffixed: Lloyd-Jones and Wesley hold the plain
    # slugs, and an import would have written over their sermons. Dropped:
    # Bonar's *Self or Christ* (ends on "the undying worm") and *The Church's
    # Amen* (the last sermon in the book; the archive slice ran into another).
    # Read in full and dropped for tone: Maclaren's *Guidance in the Way* (an
    # anti-Catholic aside), *The Lost Sheep and the Seeking Shepherd* ("people
    # with narrow foreheads"), *Tempest and Trust* (a "Jewish characteristic"),
    # *Access into Grace* (Calvinism and "the liberties of Europe"); Bonar's
    # *Christ and the New Creation* (a paragraph of hell) and *Longings for the
    # Land* (closes "shall be damned").
    SermonEntry(
        "the-wearied-christ", "The Wearied Christ", "alexander-maclaren", "ccel",
        _MACLAREN + "john1/john1.ii.xxii.html", scripture_ref="John 4:6",
    ),
    SermonEntry(
        "the-springing-fountain", "The Springing Fountain", "alexander-maclaren", "ccel",
        _MACLAREN + "john1/john1.ii.xxv.html", scripture_ref="John 4:14",
    ),
    SermonEntry(
        "the-light-of-the-world-maclaren", "The Light of the World", "alexander-maclaren", "ccel",
        _MACLAREN + "john1/john1.ii.xxxvi.html", scripture_ref="John 8:12",
    ),
    SermonEntry(
        "the-delays-of-love", "The Delays of Love", "alexander-maclaren", "ccel",
        _MACLAREN + "john1/john1.ii.xliv.html", scripture_ref="John 11:5-6",
    ),
    SermonEntry(
        "the-love-of-the-departing-christ", "The Love of the Departing Christ", "alexander-maclaren", "ccel",
        _MACLAREN + "john1/john1.ii.lv.html", scripture_ref="John 13:1",
    ),
    SermonEntry(
        "many-mansions", "Many Mansions", "alexander-maclaren", "ccel",
        _MACLAREN + "john1/john1.ii.lxv.html", scripture_ref="John 14:2",
    ),
    SermonEntry(
        "the-absent-present-christ", "The Absent Present Christ", "alexander-maclaren", "ccel",
        _MACLAREN + "john1/john1.ii.lxxii.html", scripture_ref="John 14:18-19",
    ),
    SermonEntry(
        "the-sources-of-hope", "The Sources of Hope", "alexander-maclaren", "ccel",
        _MACLAREN + "rom_cor/rom_cor.ii.xi.html", scripture_ref="Romans 5:2-4",
    ),
    SermonEntry(
        "what-proves-gods-love", "What Proves God's Love", "alexander-maclaren", "ccel",
        _MACLAREN + "rom_cor/rom_cor.ii.xiii.html", scripture_ref="Romans 5:8",
    ),
    SermonEntry(
        "the-witness-of-the-spirit-maclaren", "The Witness of the Spirit", "alexander-maclaren", "ccel",
        _MACLAREN + "rom_cor/rom_cor.ii.xviii.html", scripture_ref="Romans 8:16",
    ),
    SermonEntry(
        "joy-and-peace-in-believing", "Joy and Peace in Believing", "alexander-maclaren", "ccel",
        _MACLAREN + "rom_cor/rom_cor.ii.xlii.html", scripture_ref="Romans 15:13",
    ),
    SermonEntry(
        "looking-at-the-unseen", "Looking at the Unseen", "alexander-maclaren", "ccel",
        _MACLAREN + "rom_cor/rom_cor.iv.vi.html", scripture_ref="2 Corinthians 4:18",
    ),
    SermonEntry(
        "the-love-that-constrains", "The Love that Constrains", "alexander-maclaren", "ccel",
        _MACLAREN + "rom_cor/rom_cor.iv.xi.html", scripture_ref="2 Corinthians 5:14",
    ),
    SermonEntry(
        "christs-touch", "Christ's Touch", "alexander-maclaren", "ccel",
        _MACLAREN + "mark/mark.ii.vii.html", scripture_ref="Mark 1:41",
    ),
    SermonEntry(
        "the-secret-of-gladness", "The Secret of Gladness", "alexander-maclaren", "ccel",
        _MACLAREN + "mark/mark.ii.x.html", scripture_ref="Mark 2:19",
    ),
    SermonEntry(
        "the-looks-of-jesus", "The Looks of Jesus", "alexander-maclaren", "ccel",
        _MACLAREN + "mark/mark.ii.xxvii.html", scripture_ref="Mark 5:32",
    ),
    SermonEntry(
        "the-rest-giver", "The Rest Giver", "alexander-maclaren", "ccel",
        _MACLAREN + "matt2/matt2.ii.xviii.html", scripture_ref="Matthew 11:28-29",
    ),
    SermonEntry(
        "jehovah-jireh", "Jehovah-Jireh", "alexander-maclaren", "ccel",
        _MACLAREN + "gen_num/gen_num.ii.i.xxix.html", scripture_ref="Genesis 22:14",
    ),
    SermonEntry(
        "the-guiding-pillar", "The Guiding Pillar", "alexander-maclaren", "ccel",
        _MACLAREN + "gen_num/gen_num.iii.iv.ii.html", scripture_ref="Numbers 9:16",
    ),
    # Batch 6 toward 400 (2026-11): more of Maclaren's *Expositions* — Psalms,
    # Isaiah, John, Romans–Corinthians, the later Epistles, Mark — warm titles
    # only, screened and read in full against the tone rubric. Read and dropped:
    # nine, each for one aside or its close — on Jews (*Give Me to Drink*, *As I
    # Have Loved*, *The Well-Spring of Salvation*), Roman Catholics (*Continual
    # Prayer and Its Effects*), Islam (*The Warrior Peace*), other religions
    # (*God's Yea; Man's Amen*), "the gipsy strain" (*Happy Pilgrims*), the
    # Turkish government (*A Soul Gazing on God*), and a close on "outer
    # darkness" (*What Men Find Beneath the Wings of God*).
    SermonEntry(
        "waiting-and-singing", "Waiting and Singing", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.iii.vii.html", scripture_ref="Psalm 59:9",
    ),
    SermonEntry(
        "blessed-trust", "Blessed Trust", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.iii.xvii.html", scripture_ref="Psalm 84:12",
    ),
    SermonEntry(
        "continual-sunshine", "Continual Sunshine", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.iii.xx.html", scripture_ref="Psalm 89:15",
    ),
    SermonEntry(
        "the-sheltering-wing", "The Sheltering Wing", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.iii.xxii.html", scripture_ref="Psalm 91:4",
    ),
    SermonEntry(
        "the-habitation-of-the-soul", "The Habitation of the Soul", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.iii.xxiii.html", scripture_ref="Psalm 91:9-10",
    ),
    SermonEntry(
        "the-satisfier-of-all-desires", "The Satisfier of All Desires", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.iii.xliv.html", scripture_ref="Psalm 145:16",
    ),
    SermonEntry(
        "hid-in-light", "Hid in Light", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.ii.xxii.html", scripture_ref="Psalm 31:20",
    ),
    SermonEntry(
        "the-city-and-river-of-god", "The City and River of God", "alexander-maclaren", "ccel",
        _MACLAREN + "psalms/psalms.ii.xxxvi.html", scripture_ref="Psalm 46:4-7",
    ),
    SermonEntry(
        "the-rivers-of-god", "The Rivers of God", "alexander-maclaren", "ccel",
        _MACLAREN + "isa_jer/isa_jer.ii.i.xxxvii.html", scripture_ref="Isaiah 33:21",
    ),
    SermonEntry(
        "the-joy-bringer", "The Joy-Bringer", "alexander-maclaren", "ccel",
        _MACLAREN + "isa_jer/isa_jer.ii.ii.xxxi.html", scripture_ref="Isaiah 61:3",
    ),
    SermonEntry(
        "our-strong-city", "Our Strong City", "alexander-maclaren", "ccel",
        _MACLAREN + "isa_jer/isa_jer.ii.i.xxi.html", scripture_ref="Isaiah 26:1-2",
    ),
    SermonEntry(
        "the-way", "The Way", "alexander-maclaren", "ccel",
        _MACLAREN + "john1/john1.ii.lxvii.html", scripture_ref="John 14:4-7",
    ),
    SermonEntry(
        "abiding-in-love", "Abiding in Love", "alexander-maclaren", "ccel",
        _MACLAREN + "john2/john2.ii.iv.html", scripture_ref="John 15:9-11",
    ),
    SermonEntry(
        "our-ally", "Our Ally", "alexander-maclaren", "ccel",
        _MACLAREN + "john2/john2.ii.ix.html", scripture_ref="John 15:26-27",
    ),
    SermonEntry(
        "the-intercessor", "The Intercessor", "alexander-maclaren", "ccel",
        _MACLAREN + "john2/john2.ii.xxi.html", scripture_ref="John 17:1-19",
    ),
    SermonEntry(
        "it-is-the-lord", "It Is the Lord!", "alexander-maclaren", "ccel",
        _MACLAREN + "john2/john2.ii.xliii.html", scripture_ref="John 21:7",
    ),
    SermonEntry(
        "the-gift-that-brings-all-gifts", "The Gift That Brings All Gifts", "alexander-maclaren", "ccel",
        _MACLAREN + "rom_cor/rom_cor.ii.xxiv.html", scripture_ref="Romans 8:32",
    ),
    SermonEntry(
        "strength-in-weakness", "Strength in Weakness", "alexander-maclaren", "ccel",
        _MACLAREN + "iicor_tim/iicor_tim.ii.i.x.html", scripture_ref="2 Corinthians 12:8-9",
    ),
    SermonEntry(
        "how-to-say-thank-you", "How to Say 'Thank You'", "alexander-maclaren", "ccel",
        _MACLAREN + "iicor_tim/iicor_tim.iii.i.vii.html", scripture_ref="Philippians 4:10-14",
    ),
    SermonEntry(
        "the-toiling-christ", "The Toiling Christ", "alexander-maclaren", "ccel",
        _MACLAREN + "mark/mark.ii.xxi.html", scripture_ref="Mark 4:36-38",
    ),
    SermonEntry(
        "the-heavenly-workers-and-the-earthly-watchers", "The Heavenly Workers and the Earthly Watchers", "alexander-maclaren", "ccel",
        _MACLAREN + "isa_jer/isa_jer.ii.ii.xxxii.html", scripture_ref="Isaiah 62:1",
    ),
    # Batch 7 toward 400 (2026-11): Spurgeon's printed *New Park Street Pulpit*
    # (1856–61) comfort and faith sermons, and Maclaren's Ezekiel–Matthew,
    # 2 Kings–Ecclesiastes and Deuteronomy–Kings volumes; warm titles only.
    # The 1860–61 Spurgeon picks (*Love to Jesus*, *Trust in God*, *The Shield of
    # Faith*, *Bread for the Hungry*, *The Fullness of Christ Received*) were
    # CCEL's modernised transcription (archaisms 3–15 per 10k, no -eth) and left.
    # Read in full and dropped for tone, 17 of 30, each for an aside or its
    # close: polemic against Arminians, Wesleyans, free-will preaching, heretics
    # or denominations (*The Beatific Vision*, *The Plea of Faith*, *The Fainting
    # Warrior*, *God in the Covenant*, *Weak Hands and Feeble Knees*, *Plenteous
    # Redemption*); against Rome (*Our Father*, *God and His Saints*); on Jews or
    # "heathen" (*The Third Beatitude*, *God the Joy-Bringer*, *The Fatherhood of
    # God*, *Anxious Care*, *The River of Life*); "Red Indians" (*Shod for the
    # Road*); closes on judgment or hell (*All Things Are Yours*, *The Afterwards
    # and Our Hope*, *A Sense of Pardoned Sin*). The Spurgeon of 1856–59 fails
    # the rubric far more often than Maclaren; a top-up of Maclaren follows.
    SermonEntry(
        "the-dew-and-the-plants", "The Dew and the Plants", "alexander-maclaren", "ccel",
        _MACLAREN + "ezek_matt1/ezek_matt1.ii.iv.vii.html", scripture_ref="Hosea 14:5-6",
    ),
    SermonEntry(
        "the-second-beatitude", "The Second Beatitude", "alexander-maclaren", "ccel",
        _MACLAREN + "ezek_matt1/ezek_matt1.iii.xvi.html", scripture_ref="Matthew 5:4",
    ),
    SermonEntry(
        "our-knocking", "Our Knocking", "alexander-maclaren", "ccel",
        _MACLAREN + "ezek_matt1/ezek_matt1.iii.xlvi.html", scripture_ref="Matthew 7:7",
    ),
    SermonEntry(
        "the-peace-bringer-in-the-spiritual-world", "The Peace-Bringer in the Spiritual World", "alexander-maclaren", "ccel",
        _MACLAREN + "ezek_matt1/ezek_matt1.iii.lvii.html", scripture_ref="Matthew 8:28-34",
    ),
    SermonEntry(
        "the-search-that-always-finds", "The Search that Always Finds", "alexander-maclaren", "ccel",
        _MACLAREN + "2kings_eccl/2kings_eccl.ii.iv.vi.html", scripture_ref="2 Chronicles 15:15",
    ),
    SermonEntry(
        "holding-fast-and-held-fast", "Holding Fast and Held Fast", "alexander-maclaren", "ccel",
        _MACLAREN + "2kings_eccl/2kings_eccl.ii.iv.xi.html", scripture_ref="2 Chronicles 20:20",
    ),
    SermonEntry(
        "keeping-and-kept", "Keeping and Kept", "alexander-maclaren", "ccel",
        _MACLAREN + "2kings_eccl/2kings_eccl.ii.ix.viii.html", scripture_ref="Proverbs 4:23",
    ),
    SermonEntry(
        "the-peaceable-fruits-of-sorrows-rightly-borne", "The Peaceable Fruits of Sorrows Rightly Borne", "alexander-maclaren", "ccel",
        _MACLAREN + "2kings_eccl/2kings_eccl.ii.viii.ii.html", scripture_ref="Job 5:17-27",
    ),
    SermonEntry(
        "the-eagle-and-its-brood", "The Eagle and Its Brood", "alexander-maclaren", "ccel",
        _MACLAREN + "deut/deut.ii.ii.viii.html", scripture_ref="Deuteronomy 32:11",
    ),
    SermonEntry(
        "caleb-a-green-old-age", "Caleb—A Green Old Age", "alexander-maclaren", "ccel",
        _MACLAREN + "deut/deut.ii.iii.xii.html", scripture_ref="Joshua 14:6-14",
    ),
    SermonEntry(
        "elijahs-weakness-and-its-cure", "Elijah's Weakness, and Its Cure", "alexander-maclaren", "ccel",
        _MACLAREN + "deut/deut.iii.iii.xix.html", scripture_ref="1 Kings 19:1-18",
    ),
    SermonEntry(
        "christ-in-the-covenant", "Christ in the Covenant", "charles-h-spurgeon", "ccel",
        _CCEL + "sermons02/sermons02.xlix.html",
    ),
    SermonEntry(
        "the-first-beatitude", "The First Beatitude", "alexander-maclaren", "ccel",
        _MACLAREN + "ezek_matt1/ezek_matt1.iii.xv.html", scripture_ref="Matthew 5:3",
    ),
    SermonEntry(
        "a-dew-from-the-lord", "A Dew from the Lord", "alexander-maclaren", "ccel",
        _MACLAREN + "ezek_matt1/ezek_matt1.ii.vii.iv.html", scripture_ref="Micah 5:7",
    ),
    SermonEntry(
        "the-cry-for-bread", "The Cry for Bread", "alexander-maclaren", "ccel",
        _MACLAREN + "ezek_matt1/ezek_matt1.iii.xxxvi.html", scripture_ref="Matthew 6:11",
    ),
    SermonEntry(
        "the-healing-christ", "The Healing Christ", "alexander-maclaren", "ccel",
        _MACLAREN + "ezek_matt1/ezek_matt1.iii.liii.html", scripture_ref="Matthew 8:17",
    ),
    SermonEntry(
        "the-faith-which-christ-praises", "The Faith Which Christ Praises", "alexander-maclaren", "ccel",
        _MACLAREN + "ezek_matt1/ezek_matt1.iii.li.html", scripture_ref="Matthew 8:8-9",
    ),
    SermonEntry(
        "brave-encouragements", "Brave Encouragements", "alexander-maclaren", "ccel",
        _MACLAREN + "ezek_matt1/ezek_matt1.ii.x.ii.html", scripture_ref="Haggai 2:1-9",
    ),
    SermonEntry(
        "the-secret-of-victory", "The Secret of Victory", "alexander-maclaren", "ccel",
        _MACLAREN + "2kings_eccl/2kings_eccl.ii.iv.iii.html", scripture_ref="2 Chronicles 13:18",
    ),
    SermonEntry(
        "what-life-may-be-made", "What Life May Be Made", "alexander-maclaren", "ccel",
        _MACLAREN + "2kings_eccl/2kings_eccl.ii.viii.vi.html", scripture_ref="Job 22:26-29",
    ),
    SermonEntry(
        "heroic-faith", "Heroic Faith", "alexander-maclaren", "ccel",
        _MACLAREN + "2kings_eccl/2kings_eccl.ii.v.vi.html", scripture_ref="Ezra 8:22-23",
    ),
    SermonEntry(
        "at-the-bush", "At the Bush", "alexander-maclaren", "ccel",
        _MACLAREN + "deut/deut.ii.ii.xii.html", scripture_ref="Deuteronomy 33:16",
    ),
    SermonEntry(
        "when-the-oil-flows", "When the Oil Flows", "alexander-maclaren", "ccel",
        _MACLAREN + "deut/deut.iii.iv.v.html", scripture_ref="2 Kings 4:6",
    ),
    SermonEntry(
        "the-child-prophet", "The Child Prophet", "alexander-maclaren", "ccel",
        _MACLAREN + "deut/deut.ii.vi.i.html", scripture_ref="1 Samuel 3:1-14",
    ),
    SermonEntry(
        "jonathan-the-pattern-of-friendship", "Jonathan, the Pattern of Friendship", "alexander-maclaren", "ccel",
        _MACLAREN + "deut/deut.ii.vi.xiii.html", scripture_ref="1 Samuel 20:1-13",
    ),
]
