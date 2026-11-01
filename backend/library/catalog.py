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
    # CCEL only: TOC titles (as CCEL lists them) to leave out — sections that
    # are someone else's text in the transcription, not the author's: How to
    # Pray's "Preface" is a paperback's back-cover copy and its "Postscript" a
    # 1990s keyer's note. Named one by one, because "Preface" and "Postscript"
    # are the author's own in other works.
    skip: tuple[str, ...] = ()
    # CCEL only: section stems (as in "<work>.i.vii.iii.html" → "i.vii.iii")
    # of PARENT pages that carry prose of their own. A page with children is
    # otherwise taken for a part divider and dropped — see import_ccel.toc_parts.
    keep: tuple[str, ...] = ()


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
    "a-w-tozer": AuthorEntry(
        slug="a-w-tozer",
        name="A. W. Tozer",
        birth_year=1897,
        death_year=1963,
        bio=(
            "Self-taught American pastor of the Christian and Missionary "
            "Alliance who called the church back to the pursuit of God Himself."
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
    "horatius-bonar": AuthorEntry(
        slug="horatius-bonar",
        name="Horatius Bonar",
        birth_year=1808,
        death_year=1889,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Horatius Bonar (1808–1889) was a Scottish minister and hymn writer of the Free Church, at Kelso and then in Edinburgh."
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
    "anselm-of-canterbury": AuthorEntry(
        slug="anselm-of-canterbury",
        name="Anselm of Canterbury",
        birth_year=1033,
        death_year=1109,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Anselm of Canterbury (1033–1109) was a monk of Bec who became an unwilling archbishop and was exiled twice for refusing to treat the church's offices as the king's property."
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
    "gregory-the-great": AuthorEntry(
        slug="gregory-the-great",
        name="Gregory the Great",
        birth_year=540,
        death_year=604,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Gregory the Great (c.540–604) was Prefect of Rome who renounced the city’s highest civil office to become a monk, and the reluctant pope who wrote the West’s most influential manual of pastoral ministry, the Pastoral Rule."
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
    "francis-de-sales": AuthorEntry(
        slug="francis-de-sales",
        name="Francis de Sales",
        birth_year=1567,
        death_year=1622,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Francis de Sales (1567–1622) was a Savoyard priest and Bishop of Geneva, a see whose city he could never enter, remembered for his patience and gentleness."
        ),
    ),
    "catherine-of-siena": AuthorEntry(
        slug="catherine-of-siena",
        name="Catherine of Siena",
        birth_year=1347,
        death_year=1380,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Catherine of Siena (1347–1380) was an Italian mystic and Dominican laywoman who nursed the sick, counselled popes, and urged Gregory XI to return from Avignon to Rome."
        ),
    ),
    "jeremy-taylor": AuthorEntry(
        slug="jeremy-taylor",
        name="Jeremy Taylor",
        birth_year=1613,
        death_year=1667,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Jeremy Taylor (1613–1667) was an English Anglican priest, Royalist chaplain and bishop, called the “Shakespeare of Divines” for his prose."
        ),
    ),
    "henry-scougal": AuthorEntry(
        slug="henry-scougal",
        name="Henry Scougal",
        birth_year=1650,
        death_year=1678,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Henry Scougal (1650–1678) was a Scottish minister and Professor of Divinity at King’s College, Aberdeen, who died of consumption at about twenty-eight."
        ),
    ),
    "philip-doddridge": AuthorEntry(
        slug="philip-doddridge",
        name="Philip Doddridge",
        birth_year=1702,
        death_year=1751,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Philip Doddridge (1702–1751) was an English Congregationalist minister, tutor and hymn-writer who led a Dissenting academy at Northampton."
        ),
    ),
    "cyril-of-jerusalem": AuthorEntry(
        slug="cyril-of-jerusalem",
        name="Cyril of Jerusalem",
        birth_year=313,
        death_year=386,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Cyril of Jerusalem (313–386) was bishop of Jerusalem and the teacher behind the Catechetical Lectures, the only complete course of instruction for new Christians to survive from the early church."
        ),
    ),
    "ignatius-of-loyola": AuthorEntry(
        slug="ignatius-of-loyola",
        name="Ignatius of Loyola",
        birth_year=1491,
        death_year=1556,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Ignatius of Loyola (1491–1556) was a Basque soldier who, after a cannonball shattered his leg at Pamplona, turned to God and founded the Society of Jesus."
        ),
    ),
    "boethius": AuthorEntry(
        slug="boethius",
        name="Boethius",
        birth_year=480,
        death_year=524,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Boethius (c."
        ),
    ),
    "basil-of-caesarea": AuthorEntry(
        slug="basil-of-caesarea",
        name="Basil of Caesarea",
        birth_year=330,
        death_year=379,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Basil of Caesarea (330–379) was the archbishop of Caesarea in Cappadocia remembered as Basil the Great, a founder of Eastern monastic life and one of the Cappadocian Fathers."
        ),
    ),
    "gregory-of-nazianzus": AuthorEntry(
        slug="gregory-of-nazianzus",
        name="Gregory of Nazianzus",
        birth_year=329,
        death_year=390,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Gregory of Nazianzus (c."
        ),
    ),
    "cyprian-of-carthage": AuthorEntry(
        slug="cyprian-of-carthage",
        name="Cyprian of Carthage",
        birth_year=200,
        death_year=258,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Cyprian of Carthage (c. 200–258) was a celebrated North African rhetorician who was converted in middle age, gave away his fortune, and was made bishop within two years."
        ),
    ),
    "justin-martyr": AuthorEntry(
        slug="justin-martyr",
        name="Justin Martyr",
        birth_year=100,
        death_year=165,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Justin Martyr (c. 100–165) was a Greek-speaking philosopher from Samaria who found in Christ the “true philosophy” after years in the schools."
        ),
    ),
    "clement-of-alexandria": AuthorEntry(
        slug="clement-of-alexandria",
        name="Clement of Alexandria",
        birth_year=150,
        death_year=215,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Clement of Alexandria (c. 150–c. 215) was a convert from paganism who studied under Pantaenus and taught the faith in Alexandria until the persecution of 202 drove him away."
        ),
    ),
    "gregory-of-nyssa": AuthorEntry(
        slug="gregory-of-nyssa",
        name="Gregory of Nyssa",
        birth_year=335,
        death_year=394,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Gregory of Nyssa (c. 335–c. 394) was bishop of Nyssa in Cappadocia and one of the three Cappadocian Fathers, with his brother Basil and Gregory of Nazianzus."
        ),
    ),
    "tertullian": AuthorEntry(
        slug="tertullian",
        name="Tertullian",
        birth_year=155,
        death_year=220,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Tertullian (c. 155–c. 220) was a Christian writer of Carthage, the first to produce a large body of Christian work in Latin."
        ),
    ),
    "john-henry-newman": AuthorEntry(
        slug="john-henry-newman",
        name="John Henry Newman",
        birth_year=1801,
        death_year=1890,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "John Henry Newman (1801–1890) was an English priest, theologian and writer who led the Oxford Movement in the Church of England and in 1845 was received into the Catholic Church."
        ),
    ),
    "irenaeus-of-lyons": AuthorEntry(
        slug="irenaeus-of-lyons",
        name="Irenaeus of Lyons",
        birth_year=130,
        death_year=202,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Irenaeus of Lyons (c. 130–c. 202) was a Greek bishop of Lyons in Roman Gaul who as a boy had heard Polycarp of Smyrna."
        ),
    ),
    "origen-of-alexandria": AuthorEntry(
        slug="origen-of-alexandria",
        name="Origen of Alexandria",
        birth_year=185,
        death_year=253,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Origen of Alexandria (c. 185–c. 253) was an Alexandrian teacher, preacher and biblical scholar, one of the most influential and most debated theologians of the early Church."
        ),
    ),
    "eusebius-of-caesarea": AuthorEntry(
        slug="eusebius-of-caesarea",
        name="Eusebius of Caesarea",
        birth_year=260,
        death_year=339,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Eusebius of Caesarea (c. 260–339) was a bishop and scholar of Palestine, the pupil of the martyr Pamphilus and the father of church history."
        ),
    ),
    "lactantius": AuthorEntry(
        slug="lactantius",
        name="Lactantius",
        birth_year=250,
        death_year=325,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Lactantius (c. 250–c. 325) was a North African teacher of rhetoric, called by Diocletian to Nicomedia, who lost his career in the Great Persecution and turned his eloquence to defending the faith."
        ),
    ),
    "minucius-felix": AuthorEntry(
        slug="minucius-felix",
        name="Minucius Felix",
        birth_year=None,
        death_year=None,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Minucius Felix (fl. c. 200) was a Roman advocate and convert who wrote the Octavius, one of the first Christian books in Latin."
        ),
    ),
    "william-booth": AuthorEntry(
        slug="william-booth",
        name="William Booth",
        birth_year=1829,
        death_year=1912,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "William Booth, born in 1829 in Nottingham, England, was the founder of The Salvation Army."
        ),
    ),
    "polycarp": AuthorEntry(
        slug="polycarp",
        name="Polycarp of Smyrna",
        birth_year=69,
        death_year=155,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Polycarp of Smyrna (c. 69–c. 155) was bishop of Smyrna, remembered by tradition as a hearer of the apostle John."
        ),
    ),
    "hermas": AuthorEntry(
        slug="hermas",
        name="Hermas",
        birth_year=None,
        death_year=None,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Hermas (fl. c. 140) was a Christian of Rome and a former slave who wrote The Shepherd, a book of visions, commandments and parables calling believers to repentance and an undivided heart."
        ),
    ),
    "theophilus-of-antioch": AuthorEntry(
        slug="theophilus-of-antioch",
        name="Theophilus of Antioch",
        birth_year=None,
        death_year=183,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Theophilus of Antioch (died c. 183) was a second-century bishop of Antioch in Syria, a pagan who came to faith by reading the Hebrew prophets."
        ),
    ),
    "hippolytus-of-rome": AuthorEntry(
        slug="hippolytus-of-rome",
        name="Hippolytus of Rome",
        birth_year=170,
        death_year=235,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Hippolytus of Rome (c. 170–c. 235) was a Greek-speaking presbyter and theologian of the Roman church whose clash with Bishops Zephyrinus and Callistus led later historians to call him the first antipope."
        ),
    ),
    "jerome": AuthorEntry(
        slug="jerome",
        name="Jerome",
        birth_year=342,
        death_year=420,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Jerome (c. 342–420) was a Latin scholar, ascetic and Church Father who translated the Old Testament from the Hebrew and gave the West its Vulgate Bible."
        ),
    ),
    "william-wilberforce": AuthorEntry(
        slug="william-wilberforce",
        name="William Wilberforce",
        birth_year=1759,
        death_year=1833,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "William Wilberforce (1759–1833) was an English evangelical politician who led the parliamentary campaign that abolished the British slave trade in 1807."
        ),
    ),
    "samuel-rutherford": AuthorEntry(
        slug="samuel-rutherford",
        name="Samuel Rutherford",
        birth_year=1600,
        death_year=1661,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Samuel Rutherford (c. 1600–1661) was a Scottish Presbyterian minister of Anwoth, a professor at St Andrews and a commissioner to the Westminster Assembly."
        ),
    ),
    "teresa-of-avila": AuthorEntry(
        slug="teresa-of-avila",
        name="Teresa of Ávila",
        birth_year=1515,
        death_year=1582,
        # The author page carries the full bio (authors.json); this stub is
        # create-only and never overwrites it.
        bio=(
            "Teresa of Ávila (1515–1582) was a Spanish Carmelite nun, mystic and reformer who taught that prayer is “an intimate sharing between friends.” She founded the reformed Discalced Carmelites, wrote The Interior Castle, and in 1970 became the first woman named a Doctor of the Church."
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
    # `build_stewart_meditations` (no BookEntry — see that command).
    "maria-w-stewart": AuthorEntry(
        slug="maria-w-stewart",
        name="Maria W. Stewart",
        birth_year=1803,
        death_year=1879,
        bio=(
            "Boston writer and lecturer, among the first American women to speak "
            "in public, whose meditations, prayers and addresses called her people "
            "to faith, learning and freedom."
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
    # Arrives with How I Became a Christian (Tokyo, 1895), whose fixture was
    # hand-built from an Internet Archive OCR of the Keiseisha printing,
    # checked against the scans (no BookEntry: `import_archive` cannot chapter
    # it, and a re-import would undo the proofreading).
    "kanzo-uchimura": AuthorEntry(
        slug="kanzo-uchimura",
        name="Kanzo Uchimura",
        birth_year=1861,
        death_year=1930,
        bio=(
            "Japanese Christian writer and Bible teacher, a samurai's son "
            "converted at Sapporo and brought to assurance at Amherst, who "
            "founded the Non-Church movement and wrote in English the story "
            "of his own conversion."
        ),
    ),
    "sadhu-sundar-singh": AuthorEntry(
        slug="sadhu-sundar-singh",
        name="Sadhu Sundar Singh",
        birth_year=1889,
        death_year=1929,
        bio=(
            "Sikh-born Indian evangelist who met Christ in a vision in 1904 and "
            "became a barefoot Christian sadhu, preaching across India, into "
            "Tibet, and around the world."
        ),
    ),
    "j-c-ryle": AuthorEntry(
        slug="j-c-ryle",
        name="J. C. Ryle",
        birth_year=1816,
        death_year=1900,
        bio=(
            "First Bishop of Liverpool and a plain-spoken leader of Victorian "
            "evangelicals."
        ),
    ),    "john-calvin": AuthorEntry(
        slug="john-calvin",
        name="John Calvin",
        birth_year=1509,
        death_year=1564,
        bio=(
            "French reformer and pastor of Geneva, whose Institutes shaped "
            "Reformed theology."
        ),
    ),
    "martin-luther": AuthorEntry(
        slug="martin-luther",
        name="Martin Luther",
        birth_year=1483,
        death_year=1546,
        bio=(
            "German monk and professor whose Ninety-Five Theses began the "
            "Protestant Reformation."
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
    # Secret Power (1881, Gutenberg #33341): Moody's five addresses on the
    # Holy Spirit's power for service, with his preface.
    BookEntry("secret-power", "Secret Power", "dwight-l-moody",
              "gutenberg", "33341",
              subtitle="The Secret of Success in Christian Life and Work",
              cover_color="#7c2d12"),
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
    # The ORIGINAL 1876 Barnes/Oberlin edition only — the 1989 "complete restored
    # text" (Rosell & Dupuis) is in copyright. Of the four 1876 scans this one
    # keeps its end-of-line hyphens, so every wrapped word rejoins exactly;
    # `memoirsofrevchar00finnuoft` drops them (~600 "meas ures" splits, plus the
    # invisible both-halves-are-words kind), and the two Google scans are worse.
    # Its own OCR slip — v read as y ("haye", "conyerted") — is repaired in
    # `corrections.py`. 36 chapters, per the book's Contents.
    BookEntry("finney-memoirs", "Memoirs of Rev. Charles G. Finney", "charles-finney",
              "archive", "memoirsofrevchar1876finn",
              subtitle="Written by Himself", cover_color="#364fc7"),
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
    # The Holy War (1682), CCEL bunyan/holy_war: Bunyan's allegory of the
    # siege of the town of Mansoul, with his verse address to the reader.
    BookEntry("the-holy-war", "The Holy War", "john-bunyan", "ccel",
              "bunyan/holy_war",
              subtitle="The Losing and Taking Again of the Town of Mansoul",
              cover_color="#7a2e1f"),
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
    # Wesley's Journal in Percy Livingstone Parker's abridgment (New York:
    # Revell, 1903), from CCEL (part="vi": Parker's note, the introduction,
    # appreciation and sketch are left out). group_parts: one chapter per
    # Parker chapter, his headings as subheads.
    BookEntry("the-journal-of-john-wesley", "The Journal of John Wesley", "john-wesley",
              "ccel", "wesley/journal", part="vi", group_parts=True,
              subtitle="Abridged by Percy Livingstone Parker", cover_color="#3b4a3a"),
    BookEntry("sermons-on-several-occasions", "Sermons on Several Occasions", "john-wesley",
              "ccel", "wesley/sermons",
              subtitle="Selected Standard Sermons", cover_color="#7a5c48"),
    # The Stanbrook Benedictines' translation (1921, revised edition), public
    # domain. group_parts: each Mansion's short chapters read as one chapter; the
    # editor's introduction and his note before VI.iii are left out.
    # Francis de Sales' Introduction to the Devout Life (1609) — the public-
    # domain English translation on CCEL.
    # Francis de Sales' Treatise on the Love of God (1616) — Henry Benedict
    # Mackey's translation (1884), public domain, from CCEL, one chapter per
    # Book. Mackey's introduction is the translator's, so it is left out.
    BookEntry("treatise-on-the-love-of-god", "Treatise on the Love of God", "francis-de-sales",
              "ccel", "desales/love", subtitle="Translated by Henry Benedict Mackey",
              cover_color="#6b3a4a", group_parts=True,
              skip=("Cover Page", "Frontispiece", "Translator's Introduction",
                    "Table of Contents")),
    BookEntry("introduction-to-the-devout-life", "Introduction to the Devout Life",
              "francis-de-sales", "ccel", "desales/devout_life",
              cover_color="#4a5d3a"),
    # Catherine of Siena's Dialogue (1378) — Algar Thorold's translation, in
    # its abridged edition of 1907, public domain. Thorold's introduction on
    # her life and times is his essay, not her book, so it is left out.
    BookEntry("the-dialogue-of-catherine-of-siena", "The Dialogue", "catherine-of-siena",
              "ccel", "catherine/dialog", subtitle="Translated by Algar Thorold",
              cover_color="#6b2d2d", skip=("INTRODUCTION",)),
    # Jeremy Taylor's Holy Living (1650), public domain, from CCEL. The
    # edition's nineteenth-century "Sketch of the Life and Times" is the
    # editor's, not Taylor's, so it is left out.
    # Jeremy Taylor's Holy Dying (1651), the companion to Holy Living, public
    # domain, from CCEL: the dedication and one chapter per Section.
    BookEntry("holy-dying", "The Rule and Exercises of Holy Dying", "jeremy-taylor",
              "ccel", "taylor/holy_dying", cover_color="#2f3a4a"),
    BookEntry("holy-living", "The Rule and Exercises of Holy Living", "jeremy-taylor",
              "ccel", "taylor/holy_living", cover_color="#3d4a5c",
              skip=("A Sketch of the Life and Times of Bishop Taylor.",),
              # Divider pages that carry prose: the dedication and Chapter I's
              # introduction, Section III's opening, the introductions to
              # Chapters III and IV, and Chapter IV's Section I on faith.
              keep=("iii", "iii.iii", "v", "vi", "vi.vi")),
    # Henry Scougal's Life of God in the Soul of Man (1677), public domain,
    # from CCEL.
    BookEntry("the-life-of-god-in-the-soul-of-man", "The Life of God in the Soul of Man",
              "henry-scougal", "ccel", "scougal/life", cover_color="#5a4a2f"),
    # Philip Doddridge's Rise and Progress of Religion in the Soul (1745),
    # public domain, from CCEL.
    BookEntry("the-rise-and-progress-of-religion-in-the-soul",
              "The Rise and Progress of Religion in the Soul", "philip-doddridge",
              "ccel", "doddridge/rise", cover_color="#2f4f4f"),
    # Cyril of Jerusalem's Catechetical Lectures (c. 350) — E. H. Gifford's
    # NPNF translation (1894), public domain, extracted from npnf207 by its
    # stem. Gifford's introduction is his own essay, so it is left out.
    BookEntry("catechetical-lectures", "The Catechetical Lectures", "cyril-of-jerusalem",
              "ccel", "schaff/npnf207", part="ii",
              subtitle="Translated by Edwin Hamilton Gifford", cover_color="#4a3b2a",
              skip=("Preface.", "Life of S. Cyril.", "Catechetical Instruction.",
                    "Special Preparation for Baptism.", "Ceremonies of Baptism and Chrism.",
                    "Eucharistic Rites.\xa0 Liturgy.", "Effects of Baptism and of Chrism.",
                    "Eucharistic Doctrine.", "Place of S. Cyril's Lectures.",
                    "The Time and Arrangement of S. Cyril's Lectures.",
                    "The Creed of Jerusalem:\xa0 Doctrine of the Holy Trinity.",
                    "S. Cyril's Writings.")),
    # Ignatius of Loyola's Spiritual Exercises (1548) — Elder Mullan's
    # translation from the Spanish Autograph (1914), public domain, from
    # CCEL, one chapter per part (the Weeks, the Methods of Prayer, the
    # Rules). Mullan's preface and notes, the Latin approbations and Paul
    # III's bull are the edition's apparatus, so they are left out.
    BookEntry("the-spiritual-exercises", "The Spiritual Exercises", "ignatius-of-loyola",
              "ccel", "ignatius/exercises", subtitle="Translated by Elder Mullan",
              cover_color="#5c3a2e", group_parts=True,
              skip=("APPROBATION OF THE LATIN TEXTS", "VULGATE VERSION", "LITERAL VERSION",
                    "PAUL III, POPE FOR A PERPETUAL REMEMBRANCE", "PREFACE", "CONTENTS",
                    "GENERAL NOTE", "PRAYER")),
    # Boethius' Consolation of Philosophy (524) — W. V. Cooper's translation
    # (Dent, 1902), public domain, from CCEL. The editor's notes, appendix
    # and chronology are left out.
    BookEntry("the-consolation-of-philosophy", "The Consolation of Philosophy", "boethius",
              "ccel", "boethius/consolation", subtitle="Translated by W. V. Cooper",
              cover_color="#3b3b52",
              skip=("A Note on the Translation", "Appendix", "Editorial Note",
                    "Chronological Table")),
    # Basil the Great's On the Holy Spirit (375) — Blomfield Jackson's NPNF
    # translation (1895), public domain, extracted from npnf208 by its stem.
    # Jackson's preface is his own, so it is left out.
    # Basil the Great's Hexaemeron (c. 370), nine homilies on the six days of
    # creation — Blomfield Jackson's NPNF translation (1895), public domain,
    # extracted from npnf208 by its stem. Jackson's introduction is his own.
    BookEntry("the-hexaemeron", "The Hexaemeron", "basil-of-caesarea",
              "ccel", "schaff/npnf208", part="viii",
              subtitle="Translated by Blomfield Jackson", cover_color="#3a5a3a",
              skip=("Introduction.",)),
    BookEntry("on-the-holy-spirit", "On the Holy Spirit", "basil-of-caesarea",
              "ccel", "schaff/npnf208", part="vii",
              subtitle="Translated by Blomfield Jackson", cover_color="#2e4a5a",
              summary_titles=True, skip=("Preface.",)),
    # Gregory of Nazianzus' five Theological Orations (380) — Browne and
    # Swallow's NPNF translation (1894), public domain, extracted from
    # npnf207's Select Orations. The volume's other orations, the editors'
    # prolegomena and their introduction to these five are left out.
    BookEntry("the-theological-orations", "The Theological Orations", "gregory-of-nazianzus",
              "ccel", "schaff/npnf207", part="iii",
              subtitle="Translated by Charles Gordon Browne and James Edward Swallow",
              cover_color="#4b3a5c",
              skip=("The Life.", "The Writings.", "Literature.",
                    "On Easter and His Reluctance.",
                    "In Defence of His Flight to Pontus, and His Return, After His Ordination "
                    "to the Priesthood, with an Exposition of the Character of the Priestly Office.",
                    "To Those Who Had Invited Him, and Not Come to Receive Him.",
                    "Panegyric on His Brother S. Cæsarius.", "On his Sister Gorgonia.",
                    "To His Father, When He Had Entrusted to Him the Care of the Church of Nazianzus.",
                    "On His Father's Silence, Because of the Plague of Hail.",
                    "On the Death of His Father.", "On the Great Athanasius, Bishop of Alexandria.",
                    "Introduction to the 'Theological' Orations.",
                    "Against The Arians, and Concerning Himself.", "On the Arrival of the Egyptians.",
                    "On the Words of the Gospel, 'When Jesus Had Finished These Sayings,' "
                    "Etc.--S. Matt. xix. 1.",
                    "On the Theophany, or Birthday of Christ.", "Oration on the Holy Lights.",
                    "The Oration on Holy Baptism.", "On Pentecost.",
                    "The Last Farewell in the Presence of the One Hundred and Fifty Bishops.",
                    "Funeral Oration on the Great S. Basil, Bishop of Cæsarea in Cappadocia.",
                    "The Second Oration on Easter.")),
    # The Epistles of Cyprian (c. 248–258) — Robert Ernest Wallis's ANF
    # translation (1886), public domain, extracted from anf05 by its stem:
    # Cyprian's letters, with those written to him, in the ANF numbering.
    BookEntry("the-epistles-of-cyprian", "The Epistles of Cyprian", "cyprian-of-carthage",
              "ccel", "schaff/anf05", part="iv.iv",
              subtitle="Translated by Robert Ernest Wallis", cover_color="#4a2e2e"),
    # Justin Martyr's First Apology (c. 155) — Marcus Dods and George Reith's
    # ANF translation (1885), public domain, extracted from anf01 by its stem.
    BookEntry("the-first-apology", "The First Apology", "justin-martyr",
              "ccel", "schaff/anf01", part="viii.ii",
              subtitle="Translated by Marcus Dods and George Reith", cover_color="#5a3e2b"),
    # Clement of Alexandria's Exhortation to the Heathen (c. 195) — William
    # Wilson's ANF translation (1885), public domain, extracted from anf02 by
    # its stem.
    BookEntry("exhortation-to-the-heathen", "Exhortation to the Heathen", "clement-of-alexandria",
              "ccel", "schaff/anf02", part="vi.ii",
              subtitle="Translated by William Wilson", cover_color="#5c4a2a"),
    # Gregory of Nyssa's Great Catechism (c. 385) — William Moore and Henry
    # Austin Wilson's NPNF translation (1893), public domain, extracted from
    # npnf205 by its stem.
    BookEntry("the-great-catechism", "The Great Catechism", "gregory-of-nyssa",
              "ccel", "schaff/npnf205", part="xi.ii",
              subtitle="Translated by William Moore and Henry Austin Wilson",
              cover_color="#3e3a5c", summary_titles=True),
    # Tertullian's Apology (197) — S. Thelwall's ANF translation (1885),
    # public domain, extracted from anf03 by its stem.
    BookEntry("the-apology-of-tertullian", "The Apology", "tertullian",
              "ccel", "schaff/anf03", part="iv.iii",
              subtitle="Translated by S. Thelwall", cover_color="#5a2e2e"),
    # Justin's Dialogue with Trypho (c. 160) — the same ANF translation,
    # extracted from anf01 by its stem.
    BookEntry("dialogue-with-trypho", "Dialogue with Trypho", "justin-martyr",
              "ccel", "schaff/anf01", part="viii.iv",
              subtitle="Translated by Marcus Dods and George Reith", cover_color="#3d4a5c"),
    # Apologia Pro Vita Sua (1864, Gutenberg #19690): Newman's answer to Charles
    # Kingsley, the history of his religious opinions up to his reception into
    # the Catholic Church in 1845, with the 1864 Appendix answering each charge.
    # Built from a reshaped copy of the PG HTML (one <h2> per Part and
    # Appendix item; the editor's Introduction and the seven footnotes left out).
    BookEntry("apologia-pro-vita-sua", "Apologia Pro Vita Sua", "john-henry-newman",
              "gutenberg", "19690",
              subtitle="Being a History of His Religious Opinions", cover_color="#5c3d2e"),
    # Irenaeus's Against Heresies (c. 180) — Alexander Roberts and W. H.
    # Rambaut's ANF translation (1885), public domain, extracted from anf01 by
    # its stem. group_parts: each of the five Books is a chapter, its short
    # chapters subheads; the editor's note, Elucidation and fragments are left out.
    BookEntry("against-heresies", "Against Heresies", "irenaeus-of-lyons",
              "ccel", "schaff/anf01", part="ix", group_parts=True,
              subtitle="Translated by Alexander Roberts and W. H. Rambaut", cover_color="#4a3b5c"),
    # Origen's On First Principles (De Principiis, c. 220–230) — Frederick
    # Crombie's ANF translation (1885), public domain, extracted from anf04 by
    # its stem. group_parts: Origen's Preface and each of the four Books is a
    # chapter. Where ANF prints a passage twice, from Rufinus's Latin and from
    # the surviving Greek, the Greek is kept.
    BookEntry("on-first-principles", "On First Principles", "origen-of-alexandria",
              "ccel", "schaff/anf04", part="vi.v", group_parts=True,
              subtitle="Translated by Frederick Crombie", cover_color="#3e5a4a"),
    # Eusebius's Church History (c. 325) — Arthur Cushman McGiffert's NPNF
    # translation (1890), public domain, extracted from npnf201 by its stem.
    # group_parts: each of the ten Books is a chapter, its short chapters
    # subheads. McGiffert's prolegomena, the testimonies and his supplementary
    # tables are left out; the Martyrs of Palestine, which ANF prints between
    # Books VIII and IX, is kept as Eusebius's own appendix to Book VIII.
    BookEntry("church-history", "The Church History", "eusebius-of-caesarea",
              "ccel", "schaff/npnf201", part="iii", group_parts=True,
              subtitle="Translated by Arthur Cushman McGiffert", cover_color="#5c4a2e"),
    # Lactantius's Divine Institutes (c. 303–311) — William Fletcher's ANF
    # translation (1886), public domain, extracted from anf07 by its stem.
    # group_parts: each of the seven Books is a chapter, its short chapters
    # subheads. The Epitome that follows it in the volume is left out.
    BookEntry("the-divine-institutes", "The Divine Institutes", "lactantius",
              "ccel", "schaff/anf07", part="iii.ii", group_parts=True,
              subtitle="Translated by William Fletcher", cover_color="#2e4a5c"),
    # The Octavius of Minucius Felix (c. 200–235) — Robert Ernest Wallis's ANF
    # translation (1885), public domain, extracted from anf04 by its stem: a
    # dialogue at Ostia between the pagan Caecilius and the Christian Octavius,
    # in forty-one short chapters. Each is titled from the translator's
    # "Argument" (summary_titles keeps its lead clause).
    BookEntry("the-octavius", "The Octavius", "minucius-felix",
              "ccel", "schaff/anf04", part="iv.iii", summary_titles=True,
              subtitle="Translated by Robert Ernest Wallis", cover_color="#5c2e3e"),
    # Clement of Alexandria's Who Is the Rich Man That Shall Be Saved? (c. 200)
    # — William Wilson's ANF translation (1885), public domain, extracted from
    # anf02 by its stem: a homily on Mark 10:17–31, ending with the story of
    # St John and the young robber.
    BookEntry("who-is-the-rich-man-that-shall-be-saved", "Who Is the Rich Man That Shall Be Saved?",
              "clement-of-alexandria", "ccel", "schaff/anf02", part="vi.v", keep=("vi.v",),
              subtitle="Translated by William Wilson", cover_color="#6b5a2e"),
    # Tertullian's On Prayer (c. 198–203) — S. Thelwall's ANF translation
    # (1885), public domain, extracted from anf03 by its stem: the oldest
    # surviving exposition of the Lord's Prayer, then counsel on the manner of
    # praying, in twenty-nine short chapters.
    BookEntry("tertullian-on-prayer", "On Prayer", "tertullian",
              "ccel", "schaff/anf03", part="vi.iv",
              subtitle="Translated by S. Thelwall", cover_color="#2e5c4a"),
    # Gregory of Nyssa's On the Making of Man (379) — H. A. Wilson's NPNF
    # translation (1893), public domain, extracted from npnf205 by its stem:
    # the dedication to his brother Peter and thirty chapters completing
    # Basil's Hexaemeron with the creation of man, under the translator's
    # headings (summary_titles keeps each one's lead clause).
    BookEntry("on-the-making-of-man", "On the Making of Man", "gregory-of-nyssa",
              "ccel", "schaff/npnf205", part="x.ii.ii", summary_titles=True,
              subtitle="Translated by H. A. Wilson", cover_color="#4a5c2e"),
    # The Idea of a University (1852–1858, Gutenberg #24526) — Newman's
    # nine Discourses on University Teaching and ten Lectures on University
    # Subjects, with his Preface. Built from a reshaped copy of the PG HTML
    # (one <h2> per Discourse or Lecture, his numbered sections kept as § marks;
    # the contents, index and the two short notes to Part II left out).
    BookEntry("the-idea-of-a-university", "The Idea of a University", "john-henry-newman",
              "gutenberg", "24526",
              subtitle="Defined and Illustrated", cover_color="#2e3e5c"),
    # In Darkest England and the Way Out (1890, Gutenberg #475) — Booth's survey
    # of London's "submerged tenth" and the Salvation Army's scheme to raise
    # them: City, Farm and Over-Sea Colonies. Built from a reshaped copy of the
    # PG HTML (one <h2> per chapter, titled from its Contents; the transcription's
    # "#" restored to "£"; the Appendix of documents left out).
    BookEntry("in-darkest-england-and-the-way-out", "In Darkest England and the Way Out",
              "william-booth", "gutenberg", "475", cover_color="#5c3e2e"),
    # Horatius Bonar's God's Way of Peace (1862) — CCEL's bonar/peace: a book
    # for the anxious, in twelve short chapters.
    BookEntry("gods-way-of-peace", "God's Way of Peace", "horatius-bonar",
              "ccel", "bonar/peace", skip=("Title Page",), cover_color="#2e4a4a"),
    # Polycarp's Epistle to the Philippians (c. 110–140) and the Martyrdom of
    # Polycarp (c. 155–160), the church of Smyrna's letter telling of his
    # death — Roberts and Donaldson's ANF translation (1885), public domain,
    # extracted from anf01 by its stem. group_parts: each work is a chapter,
    # its short chapters subheads; the editors' introductory notes are left out.
    BookEntry("epistle-and-martyrdom-of-polycarp", "The Epistle and Martyrdom of Polycarp",
              "polycarp", "ccel", "schaff/anf01", part="iv", group_parts=True, keep=("iv.ii", "iv.iv"),
              subtitle="Translated by Alexander Roberts and James Donaldson", cover_color="#5c4a3e"),
    # The Shepherd of Hermas (c. 100–150) — F. Crombie's ANF translation (1885),
    # public domain, extracted from anf02 by its stem: the five Visions, twelve
    # Commandments and ten Similitudes, one chapter each. The editors'
    # introductory note and Elucidations are left out.
    BookEntry("the-shepherd-of-hermas", "The Shepherd of Hermas", "hermas",
              "ccel", "schaff/anf02", part="ii",
              subtitle="Translated by F. Crombie", cover_color="#3e5c3e"),
    # Theophilus of Antioch's To Autolycus (c. 180) — Marcus Dods's ANF
    # translation (1885), public domain, extracted from anf02 by its stem.
    # group_parts: each of the three Books is a chapter, its short chapters
    # subheads; the editors' introductory note is left out.
    BookEntry("to-autolycus", "To Autolycus", "theophilus-of-antioch",
              "ccel", "schaff/anf02", part="iv.ii", group_parts=True,
              subtitle="Translated by Marcus Dods", cover_color="#5c3e4a"),
    # Hippolytus's Refutation of All Heresies (c. 222–235) — J. H. MacMahon's
    # ANF translation (1886), public domain, extracted from anf05 by its stem.
    # group_parts: each surviving Book is a chapter (Books II and III are
    # lost), its short chapters subheads.
    BookEntry("refutation-of-all-heresies", "The Refutation of All Heresies", "hippolytus-of-rome",
              "ccel", "schaff/anf05", part="iii.iii", group_parts=True,
              subtitle="Translated by J. H. MacMahon", cover_color="#4a4a5c"),
    # The Letters of St. Jerome (370–419) — W. H. Fremantle, G. Lewis and
    # W. G. Martley's NPNF translation (1893), public domain, extracted from
    # npnf206 by its stem: the letters in Vallarsi's numbering, including some
    # written to Jerome, each with the translators' summary as its first lines.
    BookEntry("letters-of-jerome", "The Letters of St. Jerome", "jerome",
              "ccel", "schaff/npnf206", part="v",
              subtitle="Translated by W. H. Fremantle", cover_color="#5c3e2e"),
    # Clement of Alexandria's The Instructor (Paedagogus, c. 198) — William
    # Wilson's ANF translation (1885), public domain, extracted from anf02 by
    # its stem. group_parts: each of the three Books is a chapter, its short
    # chapters subheads.
    BookEntry("the-instructor", "The Instructor", "clement-of-alexandria",
              "ccel", "schaff/anf02", part="vi.iii", group_parts=True,
              subtitle="Translated by William Wilson", cover_color="#4a5c5c"),
    # Tertullian's Against Marcion (c. 207–208) — Peter Holmes's ANF translation
    # (1885), public domain, extracted from anf03 by its stem. group_parts: each
    # of the five Books is a chapter, its short chapters subheads.
    BookEntry("against-marcion", "Against Marcion", "tertullian",
              "ccel", "schaff/anf03", part="v.iv", group_parts=True,
              subtitle="Translated by Peter Holmes", cover_color="#5c2e2e"),
    # Augustine's Ten Homilies on the First Epistle of John (c. 407) — H. Browne's
    # translation as revised by Joseph H. Myers in NPNF (1888), public domain,
    # extracted from npnf107 by its stem: his prologue and the ten homilies.
    # The editor's introduction and the passages from other works that the
    # volume appends on single verses are left out.
    BookEntry("homilies-on-the-first-epistle-of-john", "Homilies on the First Epistle of John",
              "augustine-of-hippo", "ccel", "schaff/npnf107", part="iv",
              subtitle="Translated by H. Browne", cover_color="#2e4a5c"),
    # Luther's Table Talk (Gutenberg #9841) — selections from Captain Henry
    # Bell's English translation (1652) of Aurifaber's Tischreden, public
    # domain. Built from a reshaped copy of the PG HTML: one <h2> per topic,
    # each saying a subhead; the editor's introduction and Bell's
    # narrative and parliamentary order are left out.
    BookEntry("table-talk", "Table Talk", "martin-luther",
              "gutenberg", "9841",
              subtitle="Translated by Henry Bell", cover_color="#5c4a2e"),
    # Parochial and Plain Sermons, Volume VII (Gutenberg #24256) — eighteen of
    # the sermons Newman preached as vicar of St Mary's, Oxford (1834–1843),
    # in the Rivingtons edition. Built from a reshaped copy of the PG HTML
    # (one <h2> per sermon, titled from its own title line).
    BookEntry("parochial-and-plain-sermons-vii", "Parochial and Plain Sermons, Volume VII",
              "john-henry-newman", "gutenberg", "24256", cover_color="#3e3e5c"),
    # A Practical View of Christianity (1797, Gutenberg #25709, from the Dublin
    # printing of the same year) — Wilberforce's appeal to the nominal Christians
    # of his class. Built from a reshaped copy of the PG HTML: the Introduction
    # and seven chapters, titled from his Contents; the index and footnotes are
    # left out.
    BookEntry("a-practical-view-of-christianity", "A Practical View of Christianity",
              "william-wilberforce", "gutenberg", "25709",
              subtitle="Of the Prevailing Religious System of Professed Christians Contrasted with Real Christianity",
              cover_color="#2e3e5c"),
    # Letters of Samuel Rutherford (Gutenberg #42557) — Andrew A. Bonar's
    # edition (third edition, Religious Tract Society): all 365 letters in his
    # chronological order. Built from a reshaped copy of the PG HTML: one <h2>
    # per letter titled "Letter N: To …", Bonar's topical heading kept as the
    # first line; his preface, sketch, indexes, glossary, notices of each
    # correspondent and the footnote marks are left out.
    BookEntry("letters-of-samuel-rutherford", "Letters of Samuel Rutherford",
              "samuel-rutherford", "gutenberg", "42557",
              subtitle="Edited by Andrew A. Bonar", cover_color="#3e2e5c"),
    BookEntry("interior-castle", "Interior Castle", "teresa-of-avila",
              "ccel", "teresa/castle2",
              subtitle="Or the Mansions",
              cover_color="#5e3d52", group_parts=True,
              skip=("Title Page", "Note", "Introduction",
                    "Introductory Note to Chapter III by the Editor")),
    # Anselm's three great works and the Gaunilo exchange in Sidney Norton
    # Deane's translation (Open Court, 1903), from CCEL (anselm/basic_works).
    # Deane's introduction (after Weber), criticisms and bibliography are left
    # out. The fixture regroups CCEL's one-page chapters into readable ones.
    BookEntry("proslogium-monologium-cur-deus-homo",
              "Proslogium, Monologium and Cur Deus Homo", "anselm-of-canterbury",
              "ccel", "anselm/basic_works",
              subtitle="Translated by Sidney Norton Deane", cover_color="#3d4f5e",
              skip=("Title Page", "Anselm's Philosophy (After Weber.)",
                    "Criticisms of Anselm's Ontological Argument for the Being of God",
                    "Bibliography")),
    BookEntry("the-imitation-of-christ", "The Imitation of Christ", "thomas-a-kempis",
              "ccel", "kempis/imitation",
              subtitle="Four Books of Counsel for the Inner Life",
              cover_color="#3d3a6e"),
    # The Grace and Duty of Being Spiritually Minded (1681), Goold's Works
    # vol. 7, from CCEL. Goold's prefatory note and analysis are left out; the
    # fixture gives each chapter a short title and sets Owen's full heading in
    # italics as its argument.
    BookEntry("the-grace-and-duty-of-being-spiritually-minded",
              "The Grace and Duty of Being Spiritually Minded", "john-owen",
              "ccel", "owen/spirituallyminded",
              subtitle="Declared and Practically Improved",
              cover_color="#2f4a4a",
              skip=("Title page.", "Prefatory note.", "Analysis.", "Title.")),
    # The City of God — Marcus Dods's translation (NPNF first series, vol. 2,
    # 1887), public domain, extracted from npnf102 by its stem. group_parts:
    # each of the twenty-two Books is a chapter, its short chapters subheads.
    BookEntry("the-city-of-god", "The City of God", "augustine-of-hippo",
              "ccel", "schaff/npnf102", part="iv", group_parts=True,
              subtitle="Translated by Marcus Dods", cover_color="#5a3e2b",
              skip=("Translator’s Preface",)),
    # CCEL's `augustine/confessions` is Outler's 1955 translation — still in
    # copyright, hosted there by permission. `augustine/confess` is Pusey's
    # 1838 translation, public domain. group_parts: the 278 leaf sections are
    # 150–900-word "Chapter I…XXXVIII" divisions repeated in all thirteen
    # Books; the Book is the reading (and citation) unit.
    BookEntry("confessions", "Confessions", "augustine-of-hippo",
              "ccel", "augustine/confess",
              subtitle="Translated by Edward B. Pusey",
              cover_color="#5c4033", group_parts=True),
    # Gregory the Great's Book of Pastoral Rule — James Barmby's NPNF
    # translation (1895), public domain, extracted from npnf212 by its stem.
    BookEntry("the-book-of-pastoral-rule", "The Book of Pastoral Rule", "gregory-the-great",
              "ccel", "schaff/npnf212", part="iii.iv",
              subtitle="Translated by James Barmby", cover_color="#4f4a2e"),
    # The Enchiridion (Handbook on Faith, Hope, and Love) — the NPNF public-
    # domain translation (J. F. Shaw), extracted from Schaff's npnf103 volume by
    # its section stem (part="iv.ii"); CCEL's standalone augustine/enchiridion is
    # the copyrighted Outler translation.
    BookEntry("enchiridion", "The Enchiridion", "augustine-of-hippo",
              "ccel", "schaff/npnf103", part="iv.ii",
              subtitle="On Faith, Hope, and Love", cover_color="#4a5d4a"),
    # Chrysostom's ninety Homilies on Matthew, in the Oxford Library of the
    # Fathers translation revised by M. B. Riddle (NPNF first series, vol. 10,
    # 1888), from npnf110 by its stem. The editors' preface and introductory
    # essay are left out; the fixture titles each homily by its text.
    BookEntry("homilies-on-matthew", "Homilies on Matthew", "john-chrysostom",
              "ccel", "schaff/npnf110", part="iii",
              subtitle="Homilies on the Gospel of St. Matthew", cover_color="#4e3d2c",
              skip=("Title Page.", "Preface to the Oxford Edition.", "Introductory Essay.",
                    "Introduction.", "The Place of Chrysostom in the History of Exegesis.",
                    "Extent and Character of Chrysostom's Exegetical Labors.")),
    # On the Trinity, in Arthur West Haddan's translation (1873, NPNF), from
    # Schaff's npnf103 volume (part="iv.i"). One chapter per book; Shedd's
    # introductory essay and Haddan's preface are the editors', not Augustine's.
    # The fixture titles each book "Book I: …" from Schaff's summary of it.
    BookEntry("on-the-trinity", "On the Trinity", "augustine-of-hippo",
              "ccel", "schaff/npnf103", part="iv.i",
              subtitle="Translated by Arthur West Haddan", cover_color="#4b4a6b",
              group_parts=True, skip=("Introductory Essay.", "Translator’s Preface.")),
    # On Christian Doctrine in J. F. Shaw's translation, from Schaff's npnf102
    # volume (part="v"), one chapter per book. CCEL's standalone
    # augustine/doctrine has the same text but a broken TOC that scrambles the
    # chapters. Schaff's introductory note and the contents are left out. Each
    # book's "Argument" sits on its part page, which group_parts skips, so the
    # fixture sets it in italics at the head of the book.
    BookEntry("on-christian-doctrine", "On Christian Doctrine", "augustine-of-hippo",
              "ccel", "schaff/npnf102", part="v",
              subtitle="Translated by J. F. Shaw", cover_color="#5d4a2f", group_parts=True,
              skip=("Introductory Note by the Editor", "Contents of Christian Doctrine")),
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
    # Chrysostom's Homilies on Romans, in the Oxford Library of the Fathers
    # translation revised by George B. Stevens (NPNF first series, vol. 11,
    # 1889), extracted from npnf111 by its stem. The editor's preface is left
    # out; the fixture writes each homily's text reference out in full.
    BookEntry("homilies-on-romans", "Homilies on Romans", "john-chrysostom",
              "ccel", "schaff/npnf111", part="vii",
              subtitle="Homilies on the Epistle of St. Paul to the Romans",
              cover_color="#5a4a2e",
              skip=("Preface to Homilies on Romans.",)),
    # summary_titles: Schaff heads each section with a precis of its argument
    # rather than a title — 57 of them here, averaging 232 characters.
    BookEntry("on-the-incarnation", "On the Incarnation", "athanasius-of-alexandria",
              "ccel", "schaff/npnf204", part="vii.ii",
              subtitle="Translated by Archibald Robertson",
              cover_color="#2f5d62", summary_titles=True),
    # Athanasius's four Discourses Against the Arians in Newman's translation,
    # revised by Archibald Robertson (NPNF second series, vol. 4, 1892), from
    # npnf204 by its stem. The editor's introduction and excursuses are left
    # out; the fixture titles each chapter by its Discourse and its argument.
    BookEntry("against-the-arians", "Against the Arians", "athanasius-of-alexandria",
              "ccel", "schaff/npnf204", part="xxi.ii",
              subtitle="Four Discourses", cover_color="#3e4a5e",
              skip=("Excursus B. On §22 (Note 3).",
                    "Excursus C. Introductory to the Fourth Discourse against the Arians.")),
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
    # Of Temptation (1658), Goold's Works vol. 6, from CCEL. Goold's prefatory
    # note is left out; CCEL titles the chapters "Chapter I." only, so the
    # fixture gives each a title from its own argument.
    BookEntry("of-temptation", "Of Temptation", "john-owen",
              "ccel", "owen/temptation",
              subtitle="The Nature and Power of It; the Danger of Entering into It; and the Means of Preventing That Danger",
              cover_color="#4a2f3a",
              skip=("Title page.", "Prefatory note.")),
    # Of Communion with God the Father, Son, and Holy Ghost (1657), in Goold's
    # edition of the Works (CCEL owen/communion). part="i" leaves out the
    # separate Vindication that follows it; Goold's prefatory note and analysis
    # are the editor's, not Owen's.
    BookEntry("communion-with-god", "Communion with God", "john-owen",
              "ccel", "owen/communion", part="i",
              subtitle="With the Father, Son, and Holy Ghost",
              cover_color="#2f4f6f",
              skip=("Title Page.", "Prefatory note.", "Analysis.", "Title."),
              keep=("i.vii.iii",)),
    # Indwelling Sin (1667), Goold's Works vol. 6, from CCEL. Goold's prefatory
    # note is left out; the fixture gives each chapter a short title and sets
    # Owen's full heading in italics as its argument.
    BookEntry("indwelling-sin-in-believers", "Indwelling Sin in Believers", "john-owen",
              "ccel", "owen/indwellingsin",
              subtitle="The Nature, Power, Deceit, and Prevalency of the Remainders of Indwelling Sin",
              cover_color="#3e3a2a",
              skip=("Title page.", "Prefatory note.", "Title.")),
    # Meditations and Discourses on the Glory of Christ (1684) and the second
    # part published after Owen's death (1691), in Goold's edition of the Works
    # (CCEL owen/glory). Goold's prefatory note and the 1691 publisher's
    # preface to the second part are not Owen's.
    BookEntry("the-glory-of-christ", "The Glory of Christ", "john-owen",
              "ccel", "owen/glory",
              subtitle="Meditations and Discourses on the Glory of Christ",
              cover_color="#6b4e1f",
              skip=("Title page.", "Prefatory note.", "Original preface.")),
    # Goold's edition (Works, vol. 10, 1852). His prefatory note and analysis
    # are left out; the fixture groups the chapters by Owen's four books.
    BookEntry("the-death-of-death-in-the-death-of-christ",
              "The Death of Death in the Death of Christ", "john-owen",
              "ccel", "owen/deathofdeath",
              subtitle="A Treatise of the Redemption and Reconciliation That Is in the Blood of Christ",
              cover_color="#5b2a2a",
              skip=("Title page.", "Prefatory note.", "Analysis.", "Title.")),
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
    BookEntry("amanda-smith-autobiography", "Amanda Smith: An Autobiography",
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
    # How to Pray (1900), CCEL torrey/pray: twelve chapters and a postscript.
    BookEntry("how-to-pray", "How to Pray", "r-a-torrey", "ccel", "torrey/pray",
              cover_color="#4a3f8f", skip=("Preface", "Postscript")),
    # Hurlbut's Life of Christ for Young and Old (1915, Gutenberg #40460) — the
    # life of Jesus told as ~104 short story-chapters from the four Gospels, for
    # the young-readers shelf. (His whole-Bible Story of the Bible is OCR-only.)
    BookEntry("hurlbuts-life-of-christ",
              "Hurlbut's Life of Christ for Young and Old", "jesse-lyman-hurlbut",
              "gutenberg", "40460",
              subtitle="The life of Jesus told simply, for young and old",
              cover_color="#7a4a2a"),
    # A. W. Tozer's The Pursuit of God (1948, Gutenberg #25141): its copyright
    # was never renewed (no entry in the 1950–92 renewal records, which list
    # only his later books), so it is US public domain.
    BookEntry("the-pursuit-of-god", "The Pursuit of God", "a-w-tozer",
              "gutenberg", "25141", cover_color="#5b3a29"),
    # Sadhu Sundar Singh's dialogue between the Disciple and the Master, in
    # the Parkers' translation from the Urdu (Revell, London, 1922; CCEL).
    # group_parts: each of the six topics is split into short "Section I/II"
    # leaves; the topic is the reading unit.
    BookEntry("at-the-masters-feet", "At the Master's Feet",
              "sadhu-sundar-singh", "ccel", "singh/feet",
              subtitle="Translated from the Urdu by Rev. Arthur and Mrs. Parker",
              cover_color="#8a4b1f", group_parts=True),
    # J. C. Ryle's Holiness in the enlarged 1879 edition (Introduction + 21
    # papers; CCEL). Its last paper, "Christ Is All", is also on the sermon
    # shelf as christ-is-all — kept in both places on purpose.
    BookEntry("holiness", "Holiness", "j-c-ryle", "ccel", "ryle/holiness",
              subtitle="Its Nature, Hindrances, Difficulties, and Roots",
              cover_color="#6b2d3a"),
    # The first volume of Ryle's Expository Thoughts on the Gospels (1856),
    # from CCEL. group_parts: one chapter per chapter of Matthew, its passages
    # as subheads.
    BookEntry("expository-thoughts-on-matthew", "Expository Thoughts on Matthew", "j-c-ryle",
              "ccel", "ryle/matthew", group_parts=True,
              subtitle="For Family and Private Use", cover_color="#4b3a2b",
              skip=("Title Page",)),
    # Thomas Watson's A Body of Divinity (1692), sermons on the Westminster
    # Shorter Catechism, with the memoir C. H. Spurgeon compiled for his
    # edition (CCEL). Its companions, The Ten Commandments and The Lord's
    # Prayer, are separate books. The CCEL text is OCR with damaged Scripture
    # references; corrections.py re-points them. CCEL also closes Watson's
    # quotations with a straight ': the committed fixture sets them as ’, so
    # after a re-import convert the book's single quotes again before writing
    # the fixture (QuoteStyleTests.test_no_quotation_closes_with_the_wrong_mark).
    BookEntry("a-body-of-divinity", "A Body of Divinity", "thomas-watson",
              "ccel", "watson/divinity",
              subtitle="Contained in Sermons upon the Westminster Assembly’s Catechism",
              cover_color="#3f4a2b"),
    # Luther's reply to Erasmus (1525) in Henry Cole's translation of 1823, as CCEL
    # carries it from the 1931 Atherton reprint. Atherton's own preface is 1931
    # and left out; the rest is Cole's 1823 text (with Atherton's "slight
    # alterations from Vaughan", whose translation is also 1823). Cole numbers
    # the treatise in Sections, which CCEL sets as leaves under its parts.
    BookEntry("bondage-of-the-will", "The Bondage of the Will", "martin-luther",
              "ccel", "luther/bondage",
              subtitle="Translated by Henry Cole",
              cover_color="#4a3328", group_parts=True,
              skip=("Preface by Henry Atherton",)),
    # The Ninety-five Theses and the three treatises of 1520 (To the Christian
    # Nobility, Christian Liberty, the Babylonish Captivity) in Wace and
    # Buchheim's translation (1883), from CCEL. The editors' two introductory
    # essays and their advertisement are theirs, not Luther's. The fixture
    # regroups CCEL's leaves by treatise ("To the Christian Nobility: The Three
    # Walls …"), so a re-import must be regrouped the same way.
    BookEntry("first-principles-of-the-reformation", "First Principles of the Reformation",
              "martin-luther", "ccel", "luther/first_prin",
              subtitle="The Ninety-five Theses and the Three Primary Works",
              cover_color="#5a2e2e",
              skip=("Title Page", "Advertisement", "Contents",
                    "I. On the Primary Principles of Luther’ Life and Teaching.",
                    "II. The Political Course of the Reformation in Germany (1517-1546.)")),
    # Calvin's Institutes (1559) in Henry Beveridge's translation (1845), from
    # CCEL. Each leaf is one of Calvin's chapters, so the import is flat.
    # corrections.py restores the Greek CCEL carries in a legacy font encoding.
    BookEntry("institutes-of-the-christian-religion", "Institutes of the Christian Religion",
              "john-calvin", "ccel", "calvin/institutes",
              subtitle="Translated by Henry Beveridge",
              cover_color="#2f3e57",
              # John Murray's Introduction is from the 1949 Eerdmans reprint and
              # still in copyright; the Printers' note (1599) and Thomas
              # Norton's preface (1581) introduce Norton's translation, not this
              # one; the tables are empty and the index of chapters repeats the
              # contents.
              skip=("Introduction", "The Printers to the Readers.",
                    "The Original Translator’s Preface.",
                    "Table I. Of Passages from the Holy Scriptures",
                    "Table II. Of Hebrew Words Explained.",
                    "Table III. Of Greek Words Explained.",
                    "General Index of Chapters.")),
    # Calvin's Commentary on Romans in John Owen's translation (Calvin
    # Translation Society, 1849), from CCEL. group_parts: one chapter per
    # chapter of Romans, its passages as subheads. Owen's preface and his new
    # translation of the epistle are the translator's, not Calvin's.
    BookEntry("commentary-on-romans", "Commentary on Romans", "john-calvin",
              "ccel", "calvin/calcom38", group_parts=True,
              subtitle="Translated by John Owen", cover_color="#4a3b2a",
              skip=("Translator's Preface", "Translation of Romans")),
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
