"""Repo-owned seed data for the curated reading plans.

The plans ``manage.py seed_plans`` creates, in a module of its own for the same
reason ``topic_seed.py`` and ``language_seed.py`` are: the seed command pulls in
``django.core.management`` and ``library.models``, and this data has readers
that cannot afford that — chiefly the content digest, which must be able to see
that a plan changed.

That is not hypothetical. A plan's title and description are prerendered onto
``/plans/<slug>/``, and while this list lived inside the seed command nothing
rebuilt the reader when it changed: the pages kept the previous prose until some
unrelated commit happened to trigger a build. Exactly what
``content_sources.json``'s own note describes happening to plan and topic prose
once before.

Per-language prose lives in ``plan_translations`` (already a declared root);
this is the English definition and the structure.
"""

from __future__ import annotations

# (plan slug, source book slug, title, description[, (first, last) chapter order])
#
# A plan reads every chapter of its book unless the optional span narrows it —
# for a devotional whose Introduction and Conclusion bracket numbered days, so
# that plan day N is the chapter titled "Day N" rather than one off from it.
LAUNCH_PLANS = [
    (
        "humility-12-days",
        "humility-2",
        "Humility in 12 Days",
        "Andrew Murray's classic on the root of every virtue — one short chapter "
        "a day for twelve days.",
    ),
    (
        "the-inner-chamber-month",
        "the-inner-chamber",
        "A Month in the Inner Chamber",
        "Build a daily habit of prayer and the Word: thirty-six mornings with "
        "Andrew Murray, one chapter each day.",
    ),
    (
        "growing-in-wisdom-18-days",
        "growing-in-wisdom",
        "Growing in Wisdom in 18 Days",
        "James DeGreef's guide for students — one short reading a day for "
        "eighteen days. From discovering your purpose to building a vision for "
        "the future, each day pairs practical counsel with a Scripture, a "
        "reflection, and a prayer.",
    ),
    (
        "school-of-prayer-31-days",
        "school-of-prayer",
        "31 Days in the School of Prayer",
        "A month with Andrew Murray at the feet of the only Teacher. Each day "
        "opens one of Jesus' own words on prayer, from \u201cLord, teach us to "
        "pray\u201d to the promises of the last night, and ends in a prayer of "
        "its own. One lesson a day, about ten minutes, building toward "
        "intercession and a life of prayer.",
        (2, 32),  # Lesson 1 … Lesson 31, between the Preface and the Müller note
    ),
]


def article(slug: str) -> tuple:
    """A curated-plan item: one day reading this article."""
    return ("article", slug)


def chapters(book_slug: str, first: int, last: int) -> tuple:
    """A curated-plan item: this book's chapters ``first``..``last``, a day each."""
    return ("book", book_slug, first, last)


def plan_items(items) -> list[tuple]:
    """A curated plan's items in one shape: ``("article", slug)`` or
    ``("book", slug, first, last)``, where a bare book slug (the whole book)
    has ``first``/``last`` of None. The one place that reads the item forms."""
    return [("book", i, None, None) if isinstance(i, str) else i for i in items]


def plan_sources(items) -> tuple[list[str], list[str]]:
    """The (book slugs, article slugs) a curated plan's items need, in order.

    A plan exists in a language only where every one of them is published —
    the seed and the prose-coverage test both ask this, so it is said once.
    """
    sources: dict[str, list[str]] = {"book": [], "article": []}
    for kind, slug, *_ in plan_items(items):
        if slug not in sources[kind]:
            sources[kind].append(slug)
    return sources["book"], sources["article"]


# Curated plans that walk through SEVERAL works in order. An item is a book
# slug (the whole book, chapter by chapter), ``chapters(slug, first, last)``
# (a span of one book) or ``article(slug)`` (one day reading that article).
# Days are numbered sequentially across the items. A plan is created only in a
# language where EVERY source book and article is present and published (so a
# partially-translated set is skipped, not shipped half-empty).
#   (plan slug, title, description, [ordered items])
CURATED_PLANS = [
    (
        "school-of-prayer",
        "Foundations in Prayer",
        "Four weeks laying the foundations of prayer with three guides: Andrew "
        "Murray on how the Lord himself teaches us to pray, D. L. Moody on "
        "prevailing prayer, and Hannah Buyinza on prayer as the daily pulse of "
        "the Christian life.",
        [
            "lord-teach-us-to-pray-2",
            "prevailing-prayer",
            "prayer-the-pulse-of-life",
        ],
    ),
    (
        "deeper-life-in-christ",
        "The Deeper Life: Christ in You",
        "Not more effort, but a Person: the secret of the deeper life is Christ "
        "himself living within. Andrew Murray opens with the wonder of Jesus "
        "himself, then unfolds the indwelling life, and Hudson Taylor closes in "
        "the rest of union and communion with the Beloved.",
        [
            "jesus-himself-2",
            "the-masters-indwelling",
            "union-and-communion",
        ],
    ),
    (
        "grace-for-every-sinner",
        "The Way to God: Grace for Every Sinner",
        "A month on the oldest good news there is. Richard Baxter's tender call "
        "to the unconverted, D. L. Moody on the way to God, and Charles "
        "Spurgeon's All of Grace — the plainest of guides to how a sinner is "
        "saved, and how to know it.",
        [
            "a-call-to-the-unconverted",
            "the-way-to-god",
            "all-of-grace",
        ],
    ),
    (
        "faith-in-the-fire",
        "The God of All Comfort: Faith in the Fire",
        "For the days that are hard to pray through. Hannah Whitall Smith on the "
        "God of all comfort, and Gareth Evans on trusting the One who holds our "
        "tomorrows — a five-week walk into settled peace when life is uncertain.",
        [
            "the-god-of-all-comfort",
            "he-holds-my-tomorrows",
        ],
    ),
    (
        "power-from-on-high",
        "Power from on High: The Holy Spirit",
        "Four weeks with R. A. Torrey on the Spirit-filled life: first the "
        "baptism with the Holy Spirit and the power it brings for service, then "
        "the fuller study of the Person and work of the Spirit who indwells "
        "every believer.",
        [
            "baptism-with-the-holy-spirit",
            "the-person-and-work-of-the-holy-spirit",
        ],
    ),
    (
        "everything-for-christ",
        "Everything for Christ: A Life Poured Out",
        "What does whole-hearted surrender cost, and what does it yield? David "
        "Brainerd's searching missionary diary, followed by the stories of men "
        "and women who gave everything for the sake of the gospel — a call to "
        "consecration told through lives that answered it.",
        [
            "life-and-diary-of-david-brainerd",
            "men-and-women-who-gave-everything-2",
        ],
    ),
    (
        "praying-men",
        "Praying Men: A School of Prayer with E. M. Bounds",
        "Seven weeks in the furnace of intercession with the great apostle of "
        "prayer. E. M. Bounds begins with the preacher's own need of power, then "
        "unfolds the purpose that makes prayer prevail, and the necessity that "
        "makes it the whole business of the Christian life.",
        [
            "power-through-prayer",
            "purpose-in-prayer",
            "necessity-of-prayer",
        ],
    ),
    (
        "the-puritan-heart",
        "The Puritan Heart",
        "Eight weeks with three masters of the inner life. Richard Sibbes binds "
        "up the bruised reed, John Owen wages war on the sin that still dwells "
        "within, and Thomas Watson rests the whole struggle on the promise that "
        "all things work together for good.",
        [
            "the-bruised-reed",
            "mortification-of-sin",
            "all-things-for-good",
        ],
    ),
    (
        "christ-our-healer",
        "Christ Our Healer",
        "Six weeks on Christ as Saviour, Sanctifier, Healer, and Coming King. "
        "A. B. Simpson lays out the fourfold gospel and its ministry of healing, "
        "and Andrew Murray closes with a month of meditations on the Lord who "
        "still heals the body as a pledge of the life to come.",
        [
            "the-fourfold-gospel",
            "the-gospel-of-healing",
            "divine-healing",
        ],
    ),
    (
        "pursuit-of-holiness",
        "The Pursuit of Holiness",
        "Nine weeks on being wholly the Lord's. Andrew Murray traces our "
        "holiness to our union with the Holy One, William Law calls us to a life "
        "devout in every ordinary hour, and John Wesley sets out plainly what "
        "Christian perfection is — and is not.",
        [
            "holy-in-christ",
            "a-serious-call",
            "plain-account-christian-perfection",
        ],
    ),
    (
        "send-the-fire",
        "Send the Fire: Praying for Revival",
        "How revival comes, and how to pray it down. Charles Finney's lectures "
        "on the conditions of revival, R. A. Torrey on the baptism with the Holy "
        "Spirit that empowers it, and the sermons through which God shook New "
        "England under Jonathan Edwards.",
        [
            "revival-lectures",
            "baptism-with-the-holy-spirit",
            "selected-sermons-edwards",
        ],
    ),
    (
        "the-pilgrims-way",
        "The Pilgrim's Way",
        "The road home, in three classics. Charles Spurgeon meets the seeker at "
        "the wicket gate, John Bunyan's immortal allegory follows the pilgrim "
        "the whole way to the Celestial City, and Bunyan's own testimony shows "
        "the grace that abounded to the chief of sinners.",
        [
            "around-the-wicket-gate",
            "pilgrims-progress",
            "grace-abounding",
        ],
    ),
    (
        "waiting-on-god-trust",
        "Waiting on God: A Life of Trust",
        "Ten weeks in the school of trust. Andrew Murray teaches the daily "
        "discipline of waiting on God, F. B. Meyer opens the secret of being "
        "guided by him, and George Müller's astonishing life of faith shows what "
        "such trust receives.",
        [
            "waiting-on-god",
            "the-secret-of-guidance",
            "the-life-of-trust",
        ],
    ),
    (
        "women-of-faith",
        "Women of Faith",
        "A longer journey with three remarkable women. Hannah Whitall Smith "
        "opens the secret of a happy life, and the autobiographies of Amanda "
        "Berry Smith and Julia A. J. Foote — two Black women who preached the "
        "gospel across the nineteenth-century world — show that secret lived out "
        "at great cost.",
        [
            "the-christians-secret-of-a-happy-life-4",
            "amanda-smith-autobiography",
            "a-brand-plucked-from-the-fire",
        ],
    ),
    (
        "voices-of-the-early-church",
        "Voices of the Early Church",
        "The first Christian centuries in their own words. Clement of Rome "
        "writes from the church at Rome while the apostles' own generation "
        "still lived, Ignatius of Antioch sends his letters on the road to "
        "martyrdom, and Athanasius of Alexandria sets out the heart of the "
        "faith — why God himself became man — in On the Incarnation. Short "
        "daily readings over about four months.",
        [
            "first-epistle-of-clement",
            "epistles-of-ignatius",
            "on-the-incarnation",
        ],
    ),
    (
        "new-to-the-faith",
        "New to the Faith",
        "Five and a half weeks for anyone just beginning with Christ. Charles "
        "Spurgeon meets you at the wicket gate with the plainest help there is "
        "for trusting Jesus; then R. A. Torrey, writing for new believers, shows "
        "how to begin right — assurance, the Holy Spirit, the church, the Bible, "
        "prayer and witness. Short articles along the way answer the questions "
        "every new Christian asks: what the gospel is, why Jesus died, what "
        "baptism and the Lord\u2019s Supper mean, and how to keep growing.",
        [
            article("what-is-the-gospel"),
            chapters("around-the-wicket-gate", 1, 2),  # Awakening; Jesus only
            article("why-did-jesus-die"),
            chapters("around-the-wicket-gate", 3, 4),  # faith in Him; faith very simple
            article("what-is-grace"),
            chapters("around-the-wicket-gate", 5, 8),  # fears, difficulties, hindrances
            article("what-is-repentance"),
            chapters("around-the-wicket-gate", 9, 11),  # … to those who have believed
            chapters("how-to-succeed-in-the-christian-life", 1, 2),  # confessing Christ
            article("what-is-baptism"),
            chapters("how-to-succeed-in-the-christian-life", 3, 4),  # assurance; the Spirit
            article("who-is-the-holy-spirit"),
            chapters("how-to-succeed-in-the-christian-life", 5, 6),  # church membership
            article("what-is-the-church"),
            article("what-is-the-lords-supper"),
            article("how-to-read-the-bible-for-beginners"),
            chapters("how-to-succeed-in-the-christian-life", 7, 9),  # Bible study; prayer
            article("the-morning-watch"),
            chapters("how-to-succeed-in-the-christian-life", 10, 10),  # working for Christ
            article("how-to-share-your-faith"),
            chapters("how-to-succeed-in-the-christian-life", 11, 13),  # missions … amusements
            article("how-to-overcome-sin-and-temptation"),
            chapters("how-to-succeed-in-the-christian-life", 14, 15),  # persecution; guidance
            article("how-to-grow-in-your-faith"),
        ],
    ),
    (
        "first-steps-for-teens",
        "Starting Out: Faith for Teens",
        "A first walk with Jesus, for teenage readers. Charles Spurgeon meets "
        "you at the gate with the plainest of help for anyone finding their way "
        "to Christ; then the true stories of men and women who gave him "
        "everything show what that life becomes — two short books over about "
        "three weeks.",
        [
            "around-the-wicket-gate",
            "men-and-women-who-gave-everything-2",
        ],
    ),
    # Whole-series plans: a series read end to end, one chapter a day, its
    # volumes in their order (a collection in the order its writers lived).
    (
        "brave-for-god-24-true-stories",
        "Brave for God: 24 True Stories",
        "Three and a half weeks of true stories for young readers, one each day: "
        "all four books of Brave for God, twenty-four ordinary people from every "
        "part of the world who trusted God and were made brave.",
        [
            "brave-for-god",
            "brave-for-god-2",
            "brave-for-god-3",
            "brave-for-god-4",
        ],
    ),
    (
        # Was "the-key-teachings-four-teachers" until migration 0172 reshaped its books
        # and moved the plan (a new slug fences stale devices' old day numbers).
        "key-teachings-four-teachers",
        "The Key Teachings: Four Teachers",
        "Twelve weeks with four teachers, one short chapter a day, each ending in "
        "questions and a prayer: Richard Baxter on the saints' everlasting rest, "
        "Jonathan Edwards on the beauty of God and true religion, A. B. Simpson "
        "on Christ our Saviour, Sanctifier, Healer and Coming King, and Watchman "
        "Nee on the normal Christian life.",
        [
            "key-teachings-of-richard-baxter",
            "key-teachings-of-jonathan-edwards",
            "key-teachings-of-a-b-simpson",
            "key-teachings-of-watchman-nee",
        ],
    ),
    (
        "rooted-three-months-books-1-3",
        "Rooted: Three Months with God — Books 1–3",
        "Three months with God for readers aged 9 to 12: the first three books "
        "of Rooted — Planted, Following Jesus and Growing Fruit — one short "
        "devotion a day on who God is and the good news of Jesus, walking with "
        "Him from the manger to the empty tomb, and growing the fruit of the "
        "Spirit.",
        [
            "rooted-1",
            "rooted-2",
            "rooted-3",
        ],
    ),
    (
        "rooted-three-months-books-4-6",
        "Rooted: Three Months with God — Books 4–6",
        "Three more months with God for readers aged 9 to 12: the last three "
        "books of Rooted — Strong in the Storm, Branching Out and Bearing Fruit "
        "— one short devotion a day on standing firm when life is hard, loving "
        "the people around you, and God's purpose for your life.",
        [
            "rooted-4",
            "rooted-5",
            "rooted-6",
        ],
    ),
    (
        "daughters-of-the-king-three-months",
        "Daughters of the King: Three Months with God",
        "Three months with God for girls aged 9 to 12: all three books of "
        "Daughters of the King — Beloved, Brave and Growing Up — one short "
        "devotion a day on who you are in Christ, courage to speak and serve, "
        "and growing up with wisdom.",
        [
            "daughters-of-the-king-1",
            "daughters-of-the-king-2",
            "daughters-of-the-king-3",
        ],
    ),
    (
        "sons-of-the-king-three-months",
        "Sons of the King: Three Months with God",
        "Three months with God for boys aged 9 to 12: all three books of Sons "
        "of the King — Strong, Faithful and Growing Up — one short devotion a "
        "day on who you are in Christ, being someone who can be trusted, and "
        "growing up with wisdom.",
        [
            "sons-of-the-king-1",
            "sons-of-the-king-2",
            "sons-of-the-king-3",
        ],
    ),
    # Family devotions: the young-reader editions read aloud, one short chapter
    # a night — each carries its own verse and prayer, and ends with three
    # questions to talk about (`Chapter.study_questions`), so a night's reading
    # is a whole five-minute devotion.
    (
        "family-devotions-pilgrims-journey",
        "Family Devotions: The Pilgrim’s Journey",
        "Five-minute family devotions for children and the grown-ups who read "
        "with them, about three and a half weeks of nights. Read one short "
        "chapter aloud: first Bunyan’s pilgrim on the road to the Celestial "
        "City, then Spurgeon’s pictures from the farm. Each ends with a prayer "
        "and three questions to talk about together.",
        [
            "pilgrims-progress-children",
            "talks-to-the-farmer-children",
        ],
    ),
    (
        "family-devotions-heroes-who-trusted-god",
        "Family Devotions: Heroes Who Trusted God",
        "Five weeks of five-minute family devotions: true stories of three "
        "people who trusted God for everything, read aloud one short chapter a "
        "night — George Müller and his orphans, Hudson Taylor on his way to "
        "China, and Amanda Smith, born into slavery, who prayed for a pair of "
        "shoes. Each ends with a prayer and three questions to talk about "
        "together.",
        [
            "the-life-of-trust-children",
            "a-retrospect-children",
            "amanda-smith-autobiography-children",
        ],
    ),
    (
        "family-devotions-talking-with-god",
        "Family Devotions: Talking with God All Day",
        "Twelve nights of five-minute family devotions with Brother Lawrence, "
        "the clumsy kitchen helper who learned to talk with God among the pots "
        "and pans. Read one short chapter aloud: how a bare winter tree turned "
        "him to God, how he did every job for God’s love, and what he did when "
        "he got things wrong. Each ends with a prayer and three questions to "
        "talk about together.",
        [
            "the-practice-of-the-presence-of-god-children",
        ],
    ),
]

# Plans that have been withdrawn from the shelf, each with the plan(s) that
# took its place. ``seed_plans`` DELETES every row of a retired slug, in every
# language, on each deploy — dropping a tuple from the lists above is not
# enough on its own, because the seed only ever creates and reconciles, so the
# old row would stay live in prod forever.
#
# Deleting is safe because a Plan row holds nothing a seed cannot rebuild: its
# prose and days are derived from the lists above, and readers' progress is
# keyed by slug in the reading app, not by FK. That progress (and a saved
# heart) is carried to the successor plan(s) by a migration (reading 0032 for
# the series plans below) and, for progress, on the device by
# ``frontend/src/lib/planMoves.ts``. A retired slug may never
# return to LAUNCH_PLANS / CURATED_PLANS (``tests_topics_plans`` checks), so a
# stale device that syncs its old day numbers onto one ticks nothing.
#   {retired slug: (successor plan slugs)}
RETIRED_PLANS = {
    # 2026-10: the young-reader series read as ONE plan per series (Rooted as two
    # halves), not one plan per book. The combined plans read every chapter,
    # each book's Introduction and Conclusion included.
    **{
        f"rooted-book-{n}-30-days": ("rooted-three-months-books-1-3",)
        for n in (1, 2, 3)
    },
    **{
        f"rooted-book-{n}-30-days": ("rooted-three-months-books-4-6",)
        for n in (4, 5, 6)
    },
    "rooted-six-months-with-god": (
        "rooted-three-months-books-1-3",
        "rooted-three-months-books-4-6",
    ),
    **{
        f"daughters-of-the-king-book-{n}-30-days": ("daughters-of-the-king-three-months",)
        for n in (1, 2, 3)
    },
    **{
        f"sons-of-the-king-book-{n}-30-days": ("sons-of-the-king-three-months",)
        for n in (1, 2, 3)
    },
}
