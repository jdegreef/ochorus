"""The Ochorus launch shelf: 10 public-domain Christian classics.

Each book declares its `source` ("ccel" or "gutenberg") and a `source_ref`:
  - ccel:      the work path under ccel.org/ccel/<ref>  (e.g. "spurgeon/grace")
  - gutenberg: the Project Gutenberg ebook id as a string (e.g. "57121")

The order of BOOKS is the shelf order.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorEntry:
    slug: str
    name: str
    birth_year: int
    death_year: int
    # A one-line placeholder, NOT the author's real biography. Both readers
    # (`upsert_book`, `import_sermons`) apply it only when the author row is
    # first created, so it exists purely so a brand-new author isn't born with
    # an empty bio. `fixtures/content/authors.json` is the source of truth, and
    # `content_sync` re-asserts it over whatever is in the database — so the
    # moment an author has a fixture row, the text here stops being read.
    # Keep it short: a full bio copied down here only rots out of sync.
    bio: str = ""


@dataclass(frozen=True)
class BookEntry:
    slug: str
    title: str
    author_slug: str
    source: str  # "ccel" | "gutenberg"
    source_ref: str
    subtitle: str = ""
    cover_color: str = ""


AUTHORS: dict[str, AuthorEntry] = {
    "andrew-murray": AuthorEntry(
        slug="andrew-murray",
        name="Andrew Murray",
        birth_year=1828,
        death_year=1917,
        bio=(
            "South African pastor and writer of the Dutch Reformed Church, known "
            "for devotional classics on prayer, humility, and abiding in Christ."
        ),
    ),
    "charles-spurgeon": AuthorEntry(
        slug="charles-spurgeon",
        name="Charles H. Spurgeon",
        birth_year=1834,
        death_year=1892,
        bio=(
            "English Baptist preacher, the “Prince of Preachers,” whose sermons and "
            "devotional writings have been read by millions."
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
    "a-b-simpson": AuthorEntry(
        slug="a-b-simpson",
        name="A. B. Simpson",
        birth_year=1843,
        death_year=1919,
        bio=(
            "Canadian-born preacher and founder of the Christian and Missionary "
            "Alliance, whose \"Fourfold Gospel\" — Christ as Saviour, Sanctifier, "
            "Healer, and Coming King — called readers past every blessing to "
            "Christ Himself."
        ),
    ),
    "amy-carmichael": AuthorEntry(
        slug="amy-carmichael",
        name="Amy Carmichael",
        birth_year=1867,
        death_year=1951,
        bio=(
            "Irish-born missionary to India who served fifty-five years without "
            "furlough, founding the Dohnavur Fellowship to rescue children from "
            "temple prostitution."
        ),
    ),
    "frederick-brotherton-meyer": AuthorEntry(
        slug="frederick-brotherton-meyer",
        name="Frederick Brotherton Meyer",
        birth_year=1847,
        death_year=1929,
        bio=(
            "English Baptist pastor, teacher, and evangelist in London, known "
            "for expository preaching and a long shelf of devotional writing."
        ),
    ),
    "susanna-wesley": AuthorEntry(
        slug="susanna-wesley",
        name="Susanna Wesley",
        birth_year=1669,
        death_year=1742,
        bio=(
            "Mother of John and Charles Wesley, whose rigorous household of "
            "prayer and Scripture study shaped the sons who founded Methodism."
        ),
    ),
    # Added with their first book (2026-07-10).
    "george-muller": AuthorEntry(
        slug="george-muller",
        name="George Müller",
        birth_year=1805,
        death_year=1898,
        bio=(
            "Prussian-born evangelist who founded the Ashley Down orphanages in "
            "Bristol, feeding more than ten thousand orphans over his lifetime "
            "without ever asking anyone but God for money."
        ),
    ),
    "hudson-taylor": AuthorEntry(
        slug="hudson-taylor",
        name="Hudson Taylor",
        birth_year=1832,
        death_year=1905,
        bio=(
            "English missionary to China and founder of the China Inland "
            "Mission, who pioneered a faith mission that took no debt and "
            "solicited no funds but told every need to God in prayer."
        ),
    ),
    "charles-finney": AuthorEntry(
        slug="charles-finney",
        name="Charles G. Finney",
        birth_year=1792,
        death_year=1875,
        bio=(
            "American lawyer turned evangelist whose preaching helped drive the "
            "Second Great Awakening across upstate New York and beyond; later "
            "president of Oberlin College."
        ),
    ),
    "david-brainerd": AuthorEntry(
        slug="david-brainerd",
        name="David Brainerd",
        birth_year=1718,
        death_year=1747,
        bio=(
            "Missionary to the Native American peoples of colonial New Jersey "
            "and Pennsylvania, whose diary, published after his death at "
            "twenty-nine, stirred generations of missionaries."
        ),
    ),
    # Puritans & Reformers (17th century).
    "john-bunyan": AuthorEntry(
        slug="john-bunyan",
        name="John Bunyan",
        birth_year=1628,
        death_year=1688,
        bio=(
            "English writer and Puritan preacher, a Bedford tinker by trade who "
            "was imprisoned for more than a decade for preaching without a "
            "licence. During that confinement he wrote The Pilgrim's Progress, "
            "one of the most published allegories in the English language."
        ),
    ),
    "thomas-watson": AuthorEntry(
        slug="thomas-watson",
        name="Thomas Watson",
        birth_year=1620,
        death_year=1686,
        bio=(
            "English Nonconformist Puritan preacher and rector of St Stephen "
            "Walbrook in London, ejected from his living in 1662. He is "
            "remembered for warm, vivid, and remarkably accessible devotional "
            "writing."
        ),
    ),
    "richard-baxter": AuthorEntry(
        slug="richard-baxter",
        name="Richard Baxter",
        birth_year=1615,
        death_year=1691,
        bio=(
            "English Puritan church leader and pastor at Kidderminster, ejected "
            "from the Church of England in 1662. A prolific author of practical "
            "divinity whose pastoral and devotional works became enduring "
            "Christian classics."
        ),
    ),
    # The Great Awakenings (18th century).
    "jonathan-edwards": AuthorEntry(
        slug="jonathan-edwards",
        name="Jonathan Edwards",
        birth_year=1703,
        death_year=1758,
        bio=(
            "American Congregationalist preacher and theologian, a central "
            "figure of the First Great Awakening. He pastored in Northampton, "
            "Massachusetts, and briefly served as president of the College of "
            "New Jersey (later Princeton)."
        ),
    ),
    "george-whitefield": AuthorEntry(
        slug="george-whitefield",
        name="George Whitefield",
        birth_year=1714,
        death_year=1770,
        bio=(
            "English Anglican cleric and one of the founders of Methodism and "
            "the evangelical revival. A famed open-air preacher, he toured "
            "Britain and colonial America and became a leading figure of the "
            "Great Awakening."
        ),
    ),
    "john-wesley": AuthorEntry(
        slug="john-wesley",
        name="John Wesley",
        birth_year=1703,
        death_year=1791,
        bio=(
            "English Anglican cleric and evangelist who founded Methodism. A "
            "tireless itinerant preacher and organiser, he was a central figure "
            "of the 18th-century evangelical revival."
        ),
    ),
}

# Shelf order. Small, clean books first.
BOOKS: list[BookEntry] = [
    BookEntry("humility", "Humility", "andrew-murray", "gutenberg", "57121",
              subtitle="The Beauty of Holiness", cover_color="#3b5bdb"),
    BookEntry("all-of-grace", "All of Grace", "charles-spurgeon", "ccel", "spurgeon/grace",
              subtitle="An Earnest Word to Those Seeking Salvation", cover_color="#b08900"),
    BookEntry("absolute-surrender", "Absolute Surrender", "andrew-murray",
              "ccel", "murray/surrender", cover_color="#c92a2a"),
    BookEntry("school-of-prayer", "With Christ in the School of Prayer",
              "andrew-murray", "ccel", "murray/prayer", cover_color="#5f3dc4"),
    BookEntry("true-vine", "The True Vine", "andrew-murray", "ccel", "murray/true_vine",
              subtitle="Meditations for a Month on John 15", cover_color="#2b8a3e"),
    BookEntry("waiting-on-god", "Waiting on God", "andrew-murray", "ccel", "murray/waiting",
              cover_color="#1864ab"),
    # Divine Healing (1900) — US public domain by publication year. CCEL has no
    # clean edition of this title, so source it from a public-domain PDF (same
    # `source="pdf"` path as A. B. Simpson's The Gospel of Healing above). If a
    # CCEL edition surfaces, prefer it (cleaner transcription than PDF OCR).
    BookEntry("divine-healing", "Divine Healing", "andrew-murray",
              "pdf", "https://www.hopefaithprayer.com/books/Divine%20Healing%20-%20Andrew%20Murray.pdf",
              cover_color="#0b7285"),
    BookEntry("ministry-of-intercession", "The Ministry of Intercession",
              "andrew-murray", "gutenberg", "29296",
              subtitle="A Plea for More Prayer", cover_color="#0b7285"),
    BookEntry("around-the-wicket-gate", "Around the Wicket Gate", "charles-spurgeon",
              "gutenberg", "60669",
              subtitle="A Friendly Talk with Seekers", cover_color="#a61e4d"),
    BookEntry("talks-to-farmers", "Talks to Farmers", "charles-spurgeon",
              "gutenberg", "42518",
              subtitle="Plain Advice in Parables", cover_color="#846358"),
    BookEntry("cheque-book", "The Cheque Book of the Bank of Faith",
              "charles-spurgeon", "ccel", "spurgeon/checkbook",
              subtitle="Daily Readings on God's Promises", cover_color="#2f9e44"),
    BookEntry("till-he-come", "Till He Come",
              "charles-spurgeon", "ccel", "spurgeon/till_he_come",
              subtitle="Communion Meditations and Addresses", cover_color="#704881"),
    BookEntry("the-way-to-god", "The Way to God", "dwight-l-moody",
              "gutenberg", "30449",
              subtitle="And How to Find It", cover_color="#9a3412"),
    BookEntry("prevailing-prayer", "Prevailing Prayer", "dwight-l-moody",
              "gutenberg", "61883",
              subtitle="What Hinders It?", cover_color="#365314"),
    BookEntry("the-fourfold-gospel", "The Fourfold Gospel", "a-b-simpson",
              "web", "https://online.ambrose.edu/alliancestudies/simpson/4fold.html",
              subtitle="Christ Our Saviour, Sanctifier, Healer, and Coming King",
              cover_color="#7c2d12"),
    BookEntry("the-gospel-of-healing", "The Gospel of Healing", "a-b-simpson",
              "pdf", "https://cdn.cmalliance.org/wordpress/cmalliance/the-gospel-of-healing.pdf",
              cover_color="#14532d"),
    BookEntry("days-of-heaven-upon-earth", "Days of Heaven Upon Earth", "a-b-simpson",
              "gutenberg", "28416",
              subtitle="A Year of Daily Devotions", cover_color="#1e3a8a"),
    BookEntry("things-as-they-are", "Things as They Are", "amy-carmichael",
              "gutenberg", "29426",
              subtitle="Mission Work in Southern India", cover_color="#a4133c"),
    BookEntry("way-into-holiest", "The Way Into the Holiest", "frederick-brotherton-meyer",
              "ccel", "meyer/into_holiest",
              subtitle="Expositions of the Epistle to the Hebrews", cover_color="#1971c2"),
    BookEntry("susanna-wesley-clarke", "Susanna Wesley", "susanna-wesley",
              "archive", "susannawesley00clariala",
              subtitle="A Biography by Eliza Clarke", cover_color="#6d4482"),
    BookEntry("answers-to-prayer", "Answers to Prayer", "george-muller",
              "gutenberg", "25891",
              subtitle="From George Müller's Narratives", cover_color="#0b7285"),
    BookEntry("union-and-communion", "Union and Communion", "hudson-taylor",
              "ccel", "taylor_jh/union",
              subtitle="Thoughts on the Song of Solomon", cover_color="#862e9c"),
    # Revival & Awakening — clean CCEL/Gutenberg sources.
    BookEntry("revival-lectures", "Lectures on Revivals of Religion", "charles-finney",
              "ccel", "finney/revivals",
              subtitle="How Revival Comes", cover_color="#a61e4d"),
    BookEntry("life-and-diary-of-david-brainerd", "The Life and Diary of David Brainerd",
              "david-brainerd", "gutenberg", "65066",
              subtitle="Edited by Jonathan Edwards", cover_color="#5f3dc4"),

    # Puritans & Reformers (17th century) — CCEL sources.
    BookEntry("pilgrims-progress", "The Pilgrim's Progress", "john-bunyan",
              "ccel", "bunyan/pilgrim",
              subtitle="From This World to That Which Is to Come", cover_color="#2e2a5a"),
    BookEntry("grace-abounding", "Grace Abounding to the Chief of Sinners", "john-bunyan",
              "ccel", "bunyan/grace",
              subtitle="The Mercy of God in Christ to His Servant", cover_color="#4a2c1a"),
    BookEntry("all-things-for-good", "All Things for Good", "thomas-watson",
              "ccel", "watson/cordial",
              subtitle="A Divine Cordial", cover_color="#2b6b4f"),
    BookEntry("ten-commandments", "The Ten Commandments", "thomas-watson",
              "ccel", "watson/commandments",
              subtitle="A Body of Practical Divinity", cover_color="#5a4a6b"),
    BookEntry("the-reformed-pastor", "The Reformed Pastor", "richard-baxter",
              "ccel", "baxter/pastor",
              subtitle="On the Duties of the Christian Ministry", cover_color="#3f4c6b"),
    BookEntry("a-call-to-the-unconverted", "A Call to the Unconverted", "richard-baxter",
              "ccel", "baxter/unconverted",
              subtitle="To Turn and Live", cover_color="#7a5a3a"),

    # The Great Awakenings (18th century) — CCEL sources.
    BookEntry("religious-affections", "A Treatise Concerning Religious Affections",
              "jonathan-edwards", "ccel", "edwards/affections",
              subtitle="The Nature of True Religion", cover_color="#3b5b6b"),
    BookEntry("freedom-of-the-will", "Freedom of the Will", "jonathan-edwards",
              "ccel", "edwards/will",
              subtitle="A Careful and Strict Inquiry", cover_color="#6b4a3b"),
    BookEntry("selected-sermons-whitefield", "Selected Sermons of George Whitefield",
              "george-whitefield", "ccel", "whitefield/sermons",
              subtitle="Fifty-Nine Sermons", cover_color="#6b4e3d"),
    BookEntry("plain-account-christian-perfection", "A Plain Account of Christian Perfection",
              "john-wesley", "ccel", "wesley/perfection",
              subtitle="As Believed and Taught by John Wesley", cover_color="#5b7c6e"),
    BookEntry("sermons-on-several-occasions", "Sermons on Several Occasions", "john-wesley",
              "ccel", "wesley/sermons",
              subtitle="Selected Standard Sermons", cover_color="#7a5c48"),
]

# Chapters of source="web" books: (title, page URL, optional anchor). When an
# anchor is given, only content AFTER <a name="anchor"> is the chapter (the
# Ambrose edition of The Fourfold Gospel merges the publisher's introduction
# and chapter I on one page; the intro is not Simpson's text and is dropped).
WEB_CHAPTERS: dict[str, list[tuple[str, str, str]]] = {
    "the-fourfold-gospel": [
        ("Christ Our Saviour",
         "https://online.ambrose.edu/alliancestudies/simpson/4fold1.htm", "saviour"),
        ("Christ Our Sanctifier",
         "https://online.ambrose.edu/alliancestudies/simpson/4fold2.htm", ""),
        ("Christ Our Healer",
         "https://online.ambrose.edu/alliancestudies/simpson/4fold4.htm", ""),
        ("Christ Our Coming Lord",
         "https://online.ambrose.edu/alliancestudies/simpson/4fold5.htm", ""),
        ("The Walk With God",
         "https://online.ambrose.edu/alliancestudies/simpson/4fold7.htm", ""),
        ("Kept",
         "https://online.ambrose.edu/alliancestudies/simpson/4fold8.htm", ""),
    ],
}
