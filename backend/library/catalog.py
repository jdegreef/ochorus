"""The Ochorus launch shelf: 10 public-domain Christian classics.

Each book declares its `source` ("ccel", "gutenberg" or "archive") and a `source_ref`:
  - ccel:      the work path under ccel.org/ccel/<ref>  (e.g. "spurgeon/grace")
  - gutenberg: the Project Gutenberg ebook id as a string (e.g. "57121")
  - archive:   the archive.org item identifier (e.g. "bruisedreedands00sibbgoog").
               A work has many scans there and the PRINTING decides whether the
               OCR is usable — run `import_archive --inspect <id>` and read the
               sample before adding an entry.

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
    # A one-line stub, NOT the author's real biography — that lives in
    # `fixtures/content/authors.json`. Both readers (`upsert_book`,
    # `import_sermons`) apply it only when the author row is first created; see
    # the rationale on `upsert_book`. It is what the site shows until that
    # author reaches `authors.json`, at which point the next deploy replaces it
    # (`library/author_sync`) — so write a real sentence, and keep the wording
    # here in step with any live row still carrying it. Required, not defaulted,
    # so a new entry can't silently ship with no bio at all.
    bio: str


@dataclass(frozen=True)
class BookEntry:
    slug: str
    title: str
    author_slug: str
    source: str  # "ccel" | "gutenberg" | "archive" | "pdf" | "web" | "docsouth"
    source_ref: str
    subtitle: str = ""
    cover_color: str = ""
    # CCEL only: import one chapter per PART rather than per leaf section, with
    # the leaves joined under subheadings. For works whose leaves are short
    # numbered divisions ("Chapter I" … repeated in every Book) the part is the
    # real reading unit — see `import_ccel.toc_parts`.
    group_parts: bool = False
    # CCEL only: import ONE WORK out of a multi-work volume. The Schaff sets
    # (ANF/NPNF) publish a whole volume under a single work path — there is no
    # per-work URL, verified by probing: `chrysostom/priesthood`,
    # `cyprian/treatises` and `athanasius/life_antony` all 404, and the one
    # per-work path that does resolve, `athanasius/incarnation`, is the 1944
    # C.S.M.V. translation and still in copyright. So a volume's works are
    # addressed by their section-stem prefix in its TOC: "iv" is On the
    # Priesthood inside npnf109, "xvi.ii" is the Life of Antony inside npnf204.
    # Empty imports the whole volume, as before.
    part: str = ""
    #: archive only: the heading of the NEXT work, ending this one. Without it a
    #: part runs until the chapter numbering restarts, which fails when the scan
    #: loses a marker — Grosart's Sibbes drops XXVI and XXVII, so the Bruised
    #: Reed ran on into The Soul's Conflict and produced a 93,000-word chapter.
    #: The person adding a part has to read the scan anyway (`--inspect`), so
    #: naming both ends is a check, not a burden.
    part_end: str = ""
    # CCEL only: NPNF/ANF section "titles" are often not titles at all but a
    # paragraph-long summary of the argument ("Introductory.--The subject of
    # this treatise: the humiliation and incarnation of the Word. Presupposes
    # …", 443 characters). Keep the lead clause — see
    # `import_ccel.summary_title`. Opt-in, because a work whose titles are real
    # titles must not have them cut at their first full stop.
    summary_titles: bool = False


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
    "charles-h-spurgeon": AuthorEntry(
        slug="charles-h-spurgeon",
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
        name="F. B. Meyer",
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
    "arthur-t-pierson": AuthorEntry(
        slug="arthur-t-pierson",
        name="Arthur T. Pierson",
        birth_year=1837,
        death_year=1911,
        bio=(
            "American Presbyterian pastor, missions advocate and Bible teacher "
            "who wrote more than fifty books, including the authorized life of "
            "his friend George Müller."
        ),
    ),
    "bernard-of-clairvaux": AuthorEntry(
        slug="bernard-of-clairvaux",
        name="Bernard of Clairvaux",
        birth_year=1090,
        death_year=1153,
        bio=(
            "Cistercian abbot, reformer, and preacher of the twelfth century "
            "whose writings on the love of God shaped medieval devotion and were "
            "prized by the Reformers after him."
        ),
    ),
    "clement-of-rome": AuthorEntry(
        slug="clement-of-rome",
        name="Clement of Rome",
        birth_year=35,
        death_year=99,
        bio=(
            "First-century leader of the church at Rome and one of the "
            "Apostolic Fathers, whose letter to the Corinthians is the earliest "
            "surviving Christian writing outside the New Testament."
        ),
    ),
    "jeanne-guyon": AuthorEntry(
        slug="jeanne-guyon",
        name="Jeanne Guyon",
        birth_year=1648,
        death_year=1717,
        bio=(
            "French mystic whose 'A Short and Easy Method of Prayer' (1685) "
            "taught that the humblest soul may seek and find God in the heart. "
            "Condemned in Catholic France, she was embraced by Protestants."
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
    # Augustine is NOT a new author — authors.json already carries his full
    # biography and portrait, and he had simply never had a book. The entry is
    # required (upsert_book looks the slug up); the stub below is dead text that
    # only an empty database would ever show. See AuthorEntry.bio.
    "augustine-of-hippo": AuthorEntry(
        slug="augustine-of-hippo",
        name="Augustine of Hippo",
        birth_year=354,
        death_year=430,
        bio=(
            "Bishop of Hippo in Roman North Africa and the most influential "
            "theologian of the Western church, whose Confessions invented the "
            "spiritual autobiography and has never been out of readers' hands "
            "since."
        ),
    ),
    "athanasius-of-alexandria": AuthorEntry(
        slug="athanasius-of-alexandria",
        name="Athanasius of Alexandria",
        birth_year=296,
        death_year=373,
        bio=(
            "Bishop of Alexandria for forty-five years, seventeen of them in "
            "exile, who refused to concede that the Son of God was a creature "
            "and very largely settled how the church confesses Christ."
        ),
    ),
    "john-chrysostom": AuthorEntry(
        slug="john-chrysostom",
        name="John Chrysostom",
        birth_year=347,
        death_year=407,
        bio=(
            "Archbishop of Constantinople and the greatest preacher of the "
            "ancient church, named golden-mouthed by later generations, who "
            "died on a forced march into exile."
        ),
    ),
    "richard-sibbes": AuthorEntry(
        slug="richard-sibbes",
        name="Richard Sibbes",
        birth_year=1577,
        death_year=1635,
        bio=(
            "English Puritan preacher known as \u201cthe heavenly Doctor\u201d, whose "
            "gentleness toward struggling believers set him apart from his "
            "sterner contemporaries."
        ),
    ),
    "john-owen": AuthorEntry(
        slug="john-owen",
        name="John Owen",
        birth_year=1616,
        death_year=1683,
        bio=(
            "The foremost theologian of English Puritanism, Vice-Chancellor of "
            "Oxford under Cromwell and ejected from public ministry in 1662, "
            "who wrote with unusual precision about how sin is actually fought."
        ),
    ),
    "thomas-a-kempis": AuthorEntry(
        slug="thomas-a-kempis",
        name="Thomas à Kempis",
        birth_year=1380,
        death_year=1471,
        bio=(
            "German-born Dutch monk who spent some seventy years in one "
            "monastery outside Zwolle, copying manuscripts and teaching "
            "novices. For those young men he wrote The Imitation of Christ, "
            "after the Bible the most widely read Christian book ever written."
        ),
    ),
    "e-m-bounds": AuthorEntry(
        slug="e-m-bounds",
        name="E. M. Bounds",
        birth_year=1835,
        death_year=1913,
        bio=(
            "American Methodist pastor and Civil War chaplain who left the "
            "practice of law for the ministry and gave his last years to rising "
            "at four in the morning to pray. Seven of his eight books on prayer "
            "were published only after his death."
        ),
    ),
    "richard-allen": AuthorEntry(
        slug="richard-allen",
        name="Richard Allen",
        birth_year=1760,
        death_year=1831,
        bio=(
            "Born into slavery in Philadelphia, Richard Allen was converted "
            "under Methodist preaching, bought his freedom, and in 1816 was "
            "consecrated the first bishop of the African Methodist Episcopal "
            "Church, the independent Black denomination he founded."
        ),
    ),
    "amanda-berry-smith": AuthorEntry(
        slug="amanda-berry-smith",
        name="Amanda Berry Smith",
        birth_year=1837,
        death_year=1915,
        bio=(
            "Born into slavery in Maryland, Amanda Berry Smith became a "
            "washerwoman and then one of the most widely travelled evangelists "
            "of the Wesleyan-Holiness movement, preaching across the United "
            "States, Britain, India, and West Africa as an independent "
            "missionary."
        ),
    ),
    "r-a-torrey": AuthorEntry(
        slug="r-a-torrey",
        name="R. A. Torrey",
        birth_year=1856,
        death_year=1928,
        bio=(
            "American evangelist, pastor and teacher, the first superintendent "
            "of the Moody Bible Institute and first dean of the Bible Institute "
            "of Los Angeles, who wrote more than forty books chiefly on prayer "
            "and the Holy Spirit."
        ),
    ),
    "jesse-lyman-hurlbut": AuthorEntry(
        slug="jesse-lyman-hurlbut",
        name="Jesse Lyman Hurlbut",
        birth_year=1843,
        death_year=1930,
        bio=(
            "American Methodist minister and Sunday-school leader, a central "
            "figure in the Chautauqua movement, best known for retelling the "
            "Bible for the young in plain, vivid language."
        ),
    ),
    # Arrives with Fox's Book of Martyrs, which is built by
    # `build_foxes_book_of_martyrs` (no BookEntry — see that command).
    "john-foxe": AuthorEntry(
        slug="john-foxe",
        name="John Foxe",
        birth_year=1516,
        death_year=1587,
        bio=(
            "English Protestant historian and preacher whose Actes and Monuments "
            "(1563), known as Foxe's Book of Martyrs, told the sufferings of the "
            "martyrs from the early church to the burnings under Queen Mary."
        ),
    ),
}

# Shelf order. Small, clean books first.
BOOKS: list[BookEntry] = [
    BookEntry("humility", "Humility", "andrew-murray", "gutenberg", "57121",
              subtitle="The Beauty of Holiness", cover_color="#3b5bdb"),
    BookEntry("all-of-grace", "All of Grace", "charles-h-spurgeon", "ccel", "spurgeon/grace",
              subtitle="An Earnest Word to Those Seeking Salvation", cover_color="#8c6c00"),
    BookEntry("absolute-surrender", "Absolute Surrender", "andrew-murray",
              "ccel", "murray/surrender", cover_color="#c92a2a"),
    BookEntry("school-of-prayer", "With Christ in the School of Prayer",
              "andrew-murray", "ccel", "murray/prayer", cover_color="#5f3dc4"),
    BookEntry("true-vine", "The True Vine", "andrew-murray", "ccel", "murray/true_vine",
              subtitle="Meditations for a Month on John 15", cover_color="#28813a"),
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
    # Holy in Christ (1887, Gutenberg #26990) — a thirty-one-day devotional on
    # holiness, same daily-reading shape as Waiting on God.
    BookEntry("holy-in-christ", "Holy in Christ", "andrew-murray",
              "gutenberg", "26990",
              subtitle="Thoughts on the Calling of God's Children to Be Holy as He Is Holy",
              cover_color="#1864ab"),
    BookEntry("around-the-wicket-gate", "Around the Wicket Gate", "charles-h-spurgeon",
              "gutenberg", "60669",
              subtitle="A Friendly Talk with Seekers", cover_color="#a61e4d"),
    BookEntry("talks-to-farmers", "Talks to Farmers", "charles-h-spurgeon",
              "gutenberg", "42518",
              subtitle="Plain Advice in Parables", cover_color="#846358"),
    BookEntry("cheque-book", "The Cheque Book of the Bank of Faith",
              "charles-h-spurgeon", "ccel", "spurgeon/checkbook",
              subtitle="Daily Readings on God's Promises", cover_color="#258037"),
    BookEntry("till-he-come", "Till He Come",
              "charles-h-spurgeon", "ccel", "spurgeon/till_he_come",
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
    # Re-imported from Meyer's genuine PD text after shipping as a damaged AI
    # paraphrase (see migration 0121 for the why). Keeps its designed cover.
    BookEntry("the-secret-of-guidance", "The Secret of Guidance", "frederick-brotherton-meyer",
              "ccel", "meyer/guidance"),
    BookEntry("susanna-wesley-clarke", "Susanna Wesley", "susanna-wesley",
              "archive", "susannawesley00clariala",
              subtitle="A Biography by Eliza Clarke", cover_color="#6d4482"),
    BookEntry("answers-to-prayer", "Answers to Prayer", "george-muller",
              "gutenberg", "25891",
              subtitle="From George Müller's Narratives", cover_color="#0b7285"),
    BookEntry("the-life-of-trust", "The Life of Trust", "george-muller",
              "gutenberg", "27288",
              subtitle="The Lord's Dealings with George Müller", cover_color="#1e3a5f"),
    # Pierson's authorised life of Müller (1899, Gutenberg #26522), written from
    # Müller's journals with the help of his son-in-law James Wright — a
    # biography ABOUT Müller, so it is shelved under Pierson and links Müller
    # as its subject (book_people_seed).
    BookEntry("george-muller-of-bristol", "George Müller of Bristol",
              "arthur-t-pierson", "gutenberg", "26522",
              subtitle="And His Witness to a Prayer-Hearing God",
              cover_color="#5b3a29"),
    BookEntry("on-loving-god", "On Loving God", "bernard-of-clairvaux",
              "archive", "saintbernardlove00bernuoft",
              part="A LITTLE WORK BY ST. BERNARD",
              part_end="FRAGMENT BY ST. BERNARD",
              subtitle="De Diligendo Deo", cover_color="#7a1f2b"),
    # One work (1 Clement) out of the multi-work ANF01 volume: chapters live at
    # anf01.ii.ii.<roman> (I-LIX), the editors' Introductory Notice at .ii.i is
    # gated out as front matter. 59 chapters — the ANF/Roberts-Donaldson text is
    # Codex Alexandrinus (pre-Bryennios), the honest public-domain edition.
    BookEntry("first-epistle-of-clement",
              "The First Epistle of Clement to the Corinthians",
              "clement-of-rome", "ccel", "schaff/anf01", part="ii.ii",
              subtitle="The Church of Rome to the Church of Corinth",
              cover_color="#734b2e", summary_titles=True),
    BookEntry("a-short-and-easy-method-of-prayer", "A Short and Easy Method of Prayer",
              "jeanne-guyon", "gutenberg", "24989",
              subtitle="Translated by A. W. Marston", cover_color="#4c1d6b"),
    BookEntry("union-and-communion", "Union and Communion", "hudson-taylor",
              "ccel", "taylor_jh/union",
              subtitle="Thoughts on the Song of Solomon", cover_color="#862e9c"),
    # A Retrospect (Gutenberg #26744) — Taylor's own autobiographical account of
    # the founding of the China Inland Mission. Imported here from the GITenberg
    # mirror because this environment's egress blocks gutenberg.org; the
    # ebook-id source_ref is unchanged, so `import_gutenberg a-retrospect` picks
    # it up unmodified wherever the web is reachable.
    BookEntry("a-retrospect", "A Retrospect", "hudson-taylor",
              "gutenberg", "26744", cover_color="#862e9c"),
    # Separation and Service (1898, Gutenberg #26384) — one continuous
    # exposition of Numbers 6–7 across ~30 short sections. Described as
    # "addresses" but a single book-length argument by structure and size, so it
    # imports as a book, not sermons (see the book-import skill's Book-vs-Sermon
    # note).
    BookEntry("separation-and-service", "Separation and Service", "hudson-taylor",
              "gutenberg", "26384",
              subtitle="Thoughts on Numbers VI and VII", cover_color="#862e9c"),
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
    # Selected Sermons of Jonathan Edwards (1904, Gutenberg #34632), ed. H.
    # Norman Gardiner — a handful of the major sermons ("Sinners in the Hands of
    # an Angry God" among them) with the editor's introduction. A book, like the
    # Whitefield / Wesley sermon collections.
    BookEntry("selected-sermons-edwards", "Selected Sermons of Jonathan Edwards",
              "jonathan-edwards", "gutenberg", "34632",
              subtitle="Edited by H. Norman Gardiner", cover_color="#3b5b6b"),
    BookEntry("selected-sermons-whitefield", "Selected Sermons of George Whitefield",
              "george-whitefield", "ccel", "whitefield/sermons",
              subtitle="Fifty-Nine Sermons", cover_color="#6b4e3d"),
    BookEntry("plain-account-christian-perfection", "A Plain Account of Christian Perfection",
              "john-wesley", "ccel", "wesley/perfection",
              subtitle="As Believed and Taught by John Wesley", cover_color="#58786a"),
    BookEntry("sermons-on-several-occasions", "Sermons on Several Occasions", "john-wesley",
              "ccel", "wesley/sermons",
              subtitle="Selected Standard Sermons", cover_color="#7a5c48"),
    BookEntry("the-imitation-of-christ", "The Imitation of Christ", "thomas-a-kempis",
              "ccel", "kempis/imitation",
              subtitle="Four Books of Counsel for the Inner Life",
              cover_color="#3d3a6e"),
    # CCEL's `augustine/confessions` is Outler's 1955 translation — still in
    # copyright, hosted there by permission. `augustine/confess` is Pusey's
    # 1838 translation, public domain. group_parts: the 278 leaf sections are
    # 150–900-word "Chapter I…XXXVIII" divisions repeated in all thirteen
    # Books; the Book is the reading (and citation) unit.
    BookEntry("confessions", "Confessions", "augustine-of-hippo",
              "ccel", "augustine/confess",
              subtitle="Translated by Edward B. Pusey",
              cover_color="#5c4033", group_parts=True),
    # The Enchiridion (Handbook on Faith, Hope, and Love) — the NPNF public-
    # domain translation (J. F. Shaw), extracted from Schaff's npnf103 volume by
    # its section stem (part="iv.ii"); CCEL's standalone augustine/enchiridion is
    # the copyrighted Outler translation.
    BookEntry("enchiridion", "The Enchiridion", "augustine-of-hippo",
              "ccel", "schaff/npnf103", part="iv.ii",
              subtitle="On Faith, Hope, and Love", cover_color="#4a5d4a"),
    # The Schaff sets publish a whole volume under one work path, so these three
    # are addressed by `part` — the work's section-stem prefix inside the
    # volume's TOC. See BookEntry.part for why there is no per-work URL to use
    # instead, and note the trap it names: `athanasius/incarnation` resolves,
    # but it is the 1944 C.S.M.V. translation and still in copyright. npnf204 is
    # Robertson's, public domain.
    BookEntry("on-the-priesthood", "On the Priesthood", "john-chrysostom",
              "ccel", "schaff/npnf109", part="iv",
              subtitle="Six Books on the Pastoral Office",
              cover_color="#6b4a2f"),
    # summary_titles: Schaff heads each section with a precis of its argument
    # rather than a title — 57 of them here, averaging 232 characters.
    BookEntry("on-the-incarnation", "On the Incarnation", "athanasius-of-alexandria",
              "ccel", "schaff/npnf204", part="vii.ii",
              subtitle="Translated by Archibald Robertson",
              cover_color="#2f5d62", summary_titles=True),
    BookEntry("life-of-antony", "The Life of Antony", "athanasius-of-alexandria",
              "ccel", "schaff/npnf204", part="xvi.ii",
              subtitle="The Life That Began Christian Monasticism",
              cover_color="#8a6a3d"),
    # Published in 1907 as "Preacher and Prayer" — the one prayer book Bounds
    # saw in print; the other seven were issued posthumously, 1920–1931.
    BookEntry("power-through-prayer", "Power Through Prayer", "e-m-bounds",
              "ccel", "bounds/power",
              subtitle="Men Are God's Method",
              cover_color="#1d3557"),
    # The companion volume Bounds wrote to Power Through Prayer; posthumous,
    # 1920, the first of the seven his friends placed after his death.
    BookEntry("purpose-in-prayer", "Purpose in Prayer", "e-m-bounds",
              "ccel", "bounds/purpose",
              subtitle="On Importunity and the Prayer That Persists",
              cover_color="#3d2b56"),
    # Posthumous, 1929. Chapters pair prayer with faith, trust, desire,
    # fervency, importunity, character, obedience and the Word.
    BookEntry("necessity-of-prayer", "The Necessity of Prayer", "e-m-bounds",
              "ccel", "bounds/necessity",
              subtitle="Prayer and Faith, Desire, and Obedience",
              cover_color="#1f4d3f"),
    # Posthumous, 1921. Nine praying men of Scripture — Abraham, Moses,
    # Elijah, Hezekiah, Ezra, Nehemiah, Samuel, Daniel and Paul.
    BookEntry("prayer-and-praying-men", "Prayer and Praying Men", "e-m-bounds",
              "ccel", "bounds/prayingmen",
              subtitle="Nine Men of the Bible and How They Prayed",
              cover_color="#5c2a3e"),
    # The Reality of Prayer (1924, Gutenberg #73032) — one of the posthumous
    # prayer volumes; clean chapterised Gutenberg source.
    BookEntry("reality-of-prayer", "The Reality of Prayer", "e-m-bounds",
              "gutenberg", "73032",
              subtitle="The Life That Prays", cover_color="#5c2a3e"),
    # Essentials of Prayer (1925, Gutenberg #73271) — companion posthumous
    # prayer volume; clean chapterised Gutenberg source.
    BookEntry("essentials-of-prayer", "The Essentials of Prayer", "e-m-bounds",
              "gutenberg", "73271",
              subtitle="What Prayer Requires of the One Who Prays", cover_color="#5c2a3e"),
    # Sibbes is on neither CCEL (`ccel/sibbes` 404s) nor Gutenberg — the gap the
    # archive source exists to close (the 1878 standalone scan is too damaged:
    # it opens "B L For his cattingz God stykdi liMn"). Pickering's 1838
    # standalone printing, NOT Grosart's 1862 collected works, which the book
    # first shipped from. Grosart is a CRITICAL edition: its variant-reading
    # sigla ("'…,' in A and B") and editor's glosses ("— G.") are OCR-fused
    # mid-sentence through ten chapters, the next chapter's heading leaks into
    # the last one's tail, and the scan lost the "XXVIII." marker, merging the
    # last two chapters — ~200 defects that no corrections list should be asked
    # to carry, and which made the book untranslatable (a faithful translation
    # reproduces the apparatus). Pickering is a reader edition with no apparatus
    # and 28 chapters; its OCR damage is repaired in `corrections.py`, settled
    # word by word against Grosart as a second witness. The volume binds three
    # works, so `part` / `part_end` slice this one out; the index that follows
    # the last chapter is the boundary.
    BookEntry("the-bruised-reed", "The Bruised Reed", "richard-sibbes",
              "archive", "bwb_C0-AVW-616",
              # The text-start title is split over two lines ("THE BRUISED REED
              # AND" / "SMOKING FLAX."), so name the line the chapters actually
              # start under — the half-title 400 lines earlier is one line, and
              # would scope the part to the front matter.
              part="SMOKING FLAX.",
              part_end="INDEX.",
              subtitle="And Smoking Flax",
              cover_color="#4a6741"),
    # Owen's most-read book, and the one that needs no volume slicing: CCEL
    # carries it as its own work path rather than inside the collected works.
    BookEntry("mortification-of-sin", "The Mortification of Sin in Believers",
              "john-owen", "ccel", "owen/mort",
              subtitle="On Killing Sin by the Spirit",
              cover_color="#5b2333"),
    # Two early African-American spiritual autobiographies, keyed (not OCR'd) by
    # UNC's Documenting the American South. Both first published pre-1929, US
    # public domain. See `import_docsouth`. Amanda Smith's per-chapter titles are
    # bare "CHAPTER I." in the body; her real titles live in the CONTENTS and are
    # supplied via `corrections.chapter_titles`.
    BookEntry("life-experience-gospel-labours",
              "The Life, Experience, and Gospel Labours", "richard-allen",
              "docsouth", "https://docsouth.unc.edu/neh/allen/allen.html",
              subtitle="Written by Himself",
              cover_color="#7a1f2b"),
    BookEntry("amanda-smith-autobiography", "An Autobiography",
              "amanda-berry-smith", "docsouth",
              "https://docsouth.unc.edu/neh/smitham/smith.html",
              subtitle="The Story of the Lord's Dealings with Mrs. Amanda Smith",
              cover_color="#1d6f6f"),
    # Three more R. A. Torrey titles alongside his two Holy-Spirit books, from
    # Project Gutenberg (all first published pre-1929, US public domain).
    BookEntry("how-to-bring-men-to-christ", "How to Bring Men to Christ",
              "r-a-torrey", "gutenberg", "51931",
              subtitle="A Handbook of Personal Work",
              cover_color="#1b4965"),
    BookEntry("how-to-succeed-in-the-christian-life",
              "How to Succeed in the Christian Life", "r-a-torrey", "gutenberg",
              "55743", cover_color="#2f6b4f"),
    BookEntry("the-fundamental-doctrines-of-the-christian-faith",
              "The Fundamental Doctrines of the Christian Faith", "r-a-torrey",
              "gutenberg", "52648", cover_color="#6a4c93"),
    # Hurlbut's Life of Christ for Young and Old (1915, Gutenberg #40460) — the
    # life of Jesus told as ~104 short story-chapters from the four Gospels, for
    # the young-readers shelf. (His whole-Bible Story of the Bible is OCR-only.)
    BookEntry("hurlbuts-life-of-christ",
              "Hurlbut's Life of Christ for Young and Old", "jesse-lyman-hurlbut",
              "gutenberg", "40460",
              subtitle="The life of Jesus told simply, for young and old",
              cover_color="#7a4a2a"),
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
