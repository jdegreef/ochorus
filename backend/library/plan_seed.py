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
        "rooted-book-1-30-days",
        "rooted-1",
        "Rooted: 30 Days with God — Book 1",
        "Thirty days to plant deep roots, for readers aged 9 to 12: who God is, "
        "the good news of Jesus, who you are in Christ, how to pray, and how to "
        "grow. Each day is one short reading with a Bible verse, a question to "
        "think about, something to try, and a prayer.",
        (2, 31),  # Day 1 … Day 30, between the Introduction and Conclusion
    ),
    (
        "rooted-book-2-30-days",
        "rooted-2",
        "Rooted: 30 Days with God — Book 2",
        "Thirty days walking with Jesus, for readers aged 9 to 12: from the "
        "manger in Bethlehem through His miracles and stories to the cross and "
        "the empty tomb. Each day is one short reading with a Gospel passage, a "
        "question to think about, something to try, and a prayer.",
        (2, 31),  # Day 1 … Day 30, between the Introduction and Conclusion
    ),
    (
        "rooted-book-3-30-days",
        "rooted-3",
        "Rooted: 30 Days with God — Book 3",
        "Thirty days of growing fruit, for readers aged 9 to 12: love, joy, "
        "peace, patience, kindness and the rest of the fruit of the Spirit, the "
        "words we say, and the habits of the heart. Each day is one short "
        "reading with a Bible verse, a question to think about, something to "
        "try, and a prayer.",
        (2, 31),  # Day 1 … Day 30, between the Introduction and Conclusion
    ),
    (
        "rooted-book-4-30-days",
        "rooted-4",
        "Rooted: 30 Days with God — Book 4",
        "Thirty days of standing strong in the storms of life, for readers aged "
        "9 to 12: when you're afraid, worried or sad, when you're tempted, and "
        "when life isn't fair. Each day is one short reading with a Bible verse, "
        "a question to think about, something to try, and a prayer.",
        (2, 31),  # Day 1 … Day 30, between the Introduction and Conclusion
    ),
    (
        "rooted-book-5-30-days",
        "rooted-5",
        "Rooted: 30 Days with God — Book 5",
        "Thirty days of branching out in love, for readers aged 9 to 12: family, "
        "friends, forgiveness, God's family at church, and the whole world. Each "
        "day is one short reading with a Bible verse, a question to think about, "
        "something to try, and a prayer.",
        (2, 31),  # Day 1 … Day 30, between the Introduction and Conclusion
    ),
    (
        "rooted-book-6-30-days",
        "rooted-6",
        "Rooted: 30 Days with God — Book 6",
        "Thirty days on God's purpose for your life, for readers aged 9 to 12: "
        "chosen and created for good works, using your gifts and time for God, "
        "serving and speaking up, and looking ahead to Jesus' return. Each day is "
        "one short reading with a Bible verse, a question to think about, "
        "something to try, and a prayer.",
        (2, 31),  # Day 1 … Day 30, between the Introduction and Conclusion
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
    (
        "daughters-of-the-king-book-1-30-days",
        "daughters-of-the-king-1",
        "Daughters of the King: 30 Days with God — Book 1",
        "Thirty days for girls aged 9 to 12 on who you are as a daughter of the "
        "King: worth that comes from God, escaping the comparison trap, "
        "friendship without drama, and the brave girls of the Bible. Each day is "
        "one short reading with a Bible verse, a question to think about, "
        "something to try, and a prayer.",
        (2, 31),  # Day 1 … Day 30, between the Introduction and Conclusion
    ),
    (
        "daughters-of-the-king-book-2-30-days",
        "daughters-of-the-king-2",
        "Daughters of the King: 30 Days with God — Book 2",
        "Thirty days of courage for girls aged 9 to 12: facing worry with God, "
        "using your voice, serving and leading, and following Jesus like the "
        "brave women of the Gospels. Each day is one short reading with a Bible "
        "verse, a question to think about, something to try, and a prayer.",
        (2, 31),  # Day 1 … Day 30, between the Introduction and Conclusion
    ),
    (
        "daughters-of-the-king-book-3-30-days",
        "daughters-of-the-king-3",
        "Daughters of the King: 30 Days with God — Book 3",
        "Thirty days on growing up for girls aged 9 to 12: big feelings, the "
        "changes of puberty as God's good design, wise choices, discovering "
        "your calling, and learning from older women who love God. Each day is "
        "one short reading with a Bible verse, a question to think about, "
        "something to try, and a prayer.",
        (2, 31),  # Day 1 … Day 30, between the Introduction and Conclusion
    ),
    (
        "sons-of-the-king-book-1-30-days",
        "sons-of-the-king-1",
        "Sons of the King: 30 Days with God — Book 1",
        "Thirty days for boys aged 9 to 12 on who you are as a son of the King: "
        "worth that comes from God, strength under control, friends who make you "
        "better, and courage from the men of the Bible. Each day is one short "
        "reading with a Bible verse, a question to think about, something to "
        "try, and a prayer.",
        (2, 31),  # Day 1 … Day 30, between the Introduction and Conclusion
    ),
    (
        "sons-of-the-king-book-2-30-days",
        "sons-of-the-king-2",
        "Sons of the King: 30 Days with God — Book 2",
        "Thirty days of faithfulness for boys aged 9 to 12: integrity, screens "
        "and gaming, temptation, winning and losing well, and following Jesus "
        "like His first disciples. Each day is one short reading with a Bible "
        "verse, a question to think about, something to try, and a prayer.",
        (2, 31),  # Day 1 … Day 30, between the Introduction and Conclusion
    ),
    (
        "sons-of-the-king-book-3-30-days",
        "sons-of-the-king-3",
        "Sons of the King: 30 Days with God — Book 3",
        "Thirty days on growing up for boys aged 9 to 12: handling feelings, "
        "the changes of puberty as God's good design, wise choices, discovering "
        "your calling, and learning from older men who walk with God. Each day "
        "is one short reading with a Bible verse, a question to think about, "
        "something to try, and a prayer.",
        (2, 31),  # Day 1 … Day 30, between the Introduction and Conclusion
    ),
]

# Curated plans that walk through SEVERAL books in order (each book read in
# full, chapter by chapter). Days are numbered sequentially across the books.
# A plan is created only in a language where EVERY source book is present and
# published (so a partially-translated set is skipped, not shipped half-empty).
#   (plan slug, title, description, [ordered source book slugs])
CURATED_PLANS = [
    (
        "school-of-prayer",
        "A School of Prayer",
        "Four weeks in the school of prayer with three guides: Andrew Murray on "
        "how the Lord himself teaches us to pray, D. L. Moody on prevailing "
        "prayer, and Hannah Buyinza on prayer as the daily pulse of the "
        "Christian life.",
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
        "the-key-teachings-four-teachers",
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
        "rooted-six-months-with-god",
        "Rooted: Six Months with God",
        "Half a year with God for readers aged 9 to 12: all six books of Rooted, "
        "from Planted to Bearing Fruit, one short devotion a day — a verse, what "
        "it means, something to think about and something to try, and a prayer.",
        [
            "rooted-1",
            "rooted-2",
            "rooted-3",
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
]
