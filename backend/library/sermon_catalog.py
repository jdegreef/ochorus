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
    source: str  # "ccel" | "gutenberg" | "web" | "sermonindex"
    source_ref: str  # ccel/web/sermonindex: full URL of the page; gutenberg: ebook id
    section: str = ""  # gutenberg: the heading text of the sermon, at any level
    # gutenberg: the heading tag ("h1".."h4") to match, when `section` names
    # more than one heading (a volume titled after one of its studies).
    section_level: str = ""
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
_EDWARDS = "https://ccel.org/ccel/edwards/sermons/"
_NEWTON = "https://ccel.org/ccel/newton/"
_MACLAREN = "https://ccel.org/ccel/maclaren/"
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
]
