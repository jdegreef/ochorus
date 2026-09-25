"""Repo-owned seed data for the curated topical shelves.

The shelves themselves (``TOPICS``), which sermons each holds
(``TOPIC_SERMONS``) and the Scripture epigraph on each topic page
(``TOPIC_SCRIPTURE``) — every part of a topic that reaches a reader, in one
file, so one declared content root covers all of it.

The literal that ``manage.py seed_topics`` plants in the ``Topic`` /
``TopicBook`` tables, kept in a module of its own for the same reason
``language_seed.py`` and ``topic_translations.py`` are: the seed command pulls
in ``django.core.management`` and ``library.models``, and not every reader of
this data can afford that.

``library/covers.py`` is the reader that forced the split. It is deliberately
Django-free — ``scripts/localize_covers.py`` and
``scripts/build_cover_assets.py`` import it as a plain module with no
``django.setup()`` — and it needs to know which topic a book belongs to, so it
can draw that topic's emblem on the book's generated cover.

This stays the single source of truth for topic membership. It is deliberately
NOT exported to a data file the way the emblem drawings are: those have to
cross into the API image, this does not, and a copy is a thing that drifts.
"""

from __future__ import annotations

# (slug, title, description, [ordered member book slugs]). A book may appear in
# several topics — topics are overlapping shelves, not exclusive categories.
TOPICS = [
    (
        "prayer",
        "On Prayer",
        "Learning to pray — and to keep praying. The classics on the inner life "
        "of prayer, from the secret place to prevailing intercession.",
        [
            "the-inner-chamber",
            "spurgeon-on-prayer",
            "a-short-and-easy-method-of-prayer",
            "lord-teach-us-to-pray-2",
            "prevailing-prayer",
            "answers-to-prayer",
            "men-of-prayer-2",
            "possibilities-of-prayer",
            "prayer-the-pulse-of-life",
            "cheque-book",
        ],
    ),
    (
        "holy-spirit",
        "The Holy Spirit",
        "The Spirit's baptism, indwelling and work — the promised power for the "
        "Christian life.",
        [
            "baptism-with-the-holy-spirit",
            "the-person-and-work-of-the-holy-spirit",
            "the-masters-indwelling",
            "jesus-himself-2",
        ],
    ),
    (
        "deeper-life",
        "The Deeper Life",
        "Holiness, surrender and the abundant life hidden with Christ — books for "
        "going further in.",
        [
            "humility-2",
            "on-loving-god",
            "the-christians-secret-of-a-happy-life-4",
            "purity-of-heart",
            "way-into-holiest",
            "watchman-nee-a-life",
            "key-teachings-of-watchman-nee",
            "key-teachings-of-a-b-simpson",
        ],
    ),
    (
        "grace-and-comfort",
        "Grace & Comfort",
        "The unfailing grace of God and his comfort in every trial — good news "
        "for the weary.",
        [
            "all-of-grace",
            "the-god-of-all-comfort",
            "the-unselfishness-of-god",
            "he-holds-my-tomorrows",
            "the-way-to-god",
            "all-things-for-good",
        ],
    ),
    (
        "revival-and-missions",
        "Revival & Missions",
        "Lives poured out for the gospel, and seasons of awakening — fuel for a "
        "burning heart.",
        [
            "revival-lectures",
            "life-and-diary-of-david-brainerd",
            "things-as-they-are",
            "journal-of-an-expedition-up-the-niger",
            "religious-experience-and-journal",
            "a-brand-plucked-from-the-fire",
            "men-and-women-who-gave-everything-2",
            "women-who-moved-heaven-2",
            "union-and-communion",
            "men-who-moved-heaven",
            "evangelization-of-the-world",
        ],
    ),
    (
        "faith-and-guidance",
        "Faith & Guidance",
        "Trusting God for daily bread, direction and every promise — walking by "
        "faith, not sight.",
        [
            "the-secret-of-guidance",
            "the-life-of-trust",
            "days-of-heaven-upon-earth",
            "morning-by-morning",
            "evening-by-evening",
            "thoughts-for-the-quiet-hour",
            "our-daily-walk",
            "the-fourfold-gospel",
            "soar-like-the-eagle-3",
            "waiting-on-god",
        ],
    ),
    (
        "the-gospel-call",
        "The Gospel Call",
        "The oldest invitation there is \u2014 come, repent, believe. Preachers "
        "pleading with the unconverted, and the testimony of grace found by the "
        "chief of sinners.",
        [
            "a-call-to-the-unconverted",
            "around-the-wicket-gate",
            "grace-abounding",
            "how-to-bring-men-to-christ",
        ],
    ),
    (
        "enduring-classics",
        "The Enduring Classics",
        "The books that have walked with pilgrims for centuries \u2014 "
        "Augustine's confession, Bunyan's dream, the counsel of \u00e0 Kempis "
        "\u2014 the old paths, still good.",
        [
            "confessions",
            "treatises-of-cyprian",
            "first-epistle-of-clement",
            "epistles-of-ignatius",
            "pilgrims-progress",
            "the-imitation-of-christ",
            "freedom-of-the-will",
            "a-serious-call",
        ],
    ),
    (
        "the-way-of-holiness",
        "The Way of Holiness",
        "Set apart for God \u2014 the commandments searched, perfection "
        "honestly pursued, and the affections of the heart tried and found "
        "true.",
        [
            "plain-account-christian-perfection",
            "godliness",
            "religious-affections",
            "key-teachings-of-jonathan-edwards",
            "ten-commandments",
        ],
    ),
    (
        "the-preached-word",
        "The Preached Word",
        "Great preaching on the page \u2014 Whitefield and Wesley in full "
        "voice, Spurgeon among his farmers \u2014 and Baxter's charge to every "
        "shepherd of souls.",
        [
            "selected-sermons-whitefield",
            "sermons-on-several-occasions",
            "talks-to-the-farmer",
            "till-he-come",
            "the-reformed-pastor",
            "key-teachings-of-richard-baxter",
            "men-who-tended-the-flock-2",
            "the-fundamental-doctrines-of-the-christian-faith",
        ],
    ),
    (
        "christ-and-the-cross",
        "Christ & the Cross",
        "The person and work of the Saviour \u2014 the Lamb slain, the shame and "
        "triumph of the cross, the excellency of Christ, and the empty tomb.",
        [],
    ),
    (
        "the-puritans",
        "The Puritans",
        "The plain, searching divinity of the Puritans \u2014 Bunyan's pilgrim, "
        "Owen on the sin within, Watson's warmth and Edwards' fire \u2014 doctrine "
        "pressed home upon the heart.",
        [
            "pilgrims-progress",
            "grace-abounding",
            "the-bruised-reed",
            "mortification-of-sin",
            "all-things-for-good",
            "ten-commandments",
            "a-call-to-the-unconverted",
            "the-reformed-pastor",
            "religious-affections",
            "freedom-of-the-will",
            "selected-sermons-edwards",
        ],
    ),
    (
        "abiding-in-christ",
        "Abiding in Christ",
        "The branch in the Vine \u2014 union and communion with the Lord Jesus, and "
        "the life that flows from no other source than staying near him.",
        [
            "true-vine",
            "holy-in-christ",
            "absolute-surrender",
            "the-masters-indwelling",
            "jesus-himself-2",
            "on-loving-god",
            "union-and-communion",
            "the-bruised-reed",
        ],
    ),
    (
        "women-of-faith",
        "Women of Faith",
        "Mothers, missionaries and mystics \u2014 the faith of women who prayed, "
        "suffered and dared, from Guyon's cell to the freed slave's pulpit.",
        [
            "a-brand-plucked-from-the-fire",
            "amanda-smith-autobiography",
            "religious-experience-and-journal",
            "susanna-wesley-clarke",
            "godliness",
            "things-as-they-are",
            "the-christians-secret-of-a-happy-life-4",
            "the-god-of-all-comfort",
            "the-unselfishness-of-god",
            "a-short-and-easy-method-of-prayer",
            "prayer-the-pulse-of-life",
            "clothed-with-strength-and-dignity",
            "women-who-moved-heaven-2",
        ],
    ),
    (
        "voices-of-the-early-church",
        "Voices of the Early Church",
        "The faith of the first centuries in its own words \u2014 Augustine's heart "
        "laid bare, Athanasius on the Word made flesh, and the letters of martyrs "
        "and shepherds.",
        [
            "confessions",
            "enchiridion",
            "on-the-incarnation",
            "life-of-antony",
            "on-the-priesthood",
            "treatises-of-cyprian",
            "first-epistle-of-clement",
            "epistles-of-ignatius",
        ],
    ),
    (
        "day-by-day",
        "Day by Day",
        "A reading for the morning and the evening \u2014 daily bread to keep the "
        "soul fed, from Spurgeon's beloved classics to the books of the quiet hour.",
        [
            "morning-by-morning",
            "evening-by-evening",
            "gleanings-among-the-sheaves",
            "thoughts-for-the-quiet-hour",
            "our-daily-walk",
            "days-of-heaven-upon-earth",
            "cheque-book",
        ],
    ),
    (
        "the-east-african-revival",
        "The East African Revival",
        "Tukutendereza Yesu \u2014 the awakening that ran from a Kampala hillside "
        "through six countries and most of a century, and the walk in the light "
        "it taught.",
        [
            "a-hidden-fire",
            "tukutendereza",
            "clothed-with-strength-and-dignity",
            "rise-up-men-of-god-2",
            "prayer-the-pulse-of-life",
        ],
    ),
    (
        "contemporary-voices",
        "Contemporary Voices",
        "The old road has living guides \u2014 present-day teachers writing for East "
        "Africa and beyond, meeting the disciple where the questions are now.",
        [
            "feasting-at-the-table",
            "stepping-stones-2",
            "the-key-in-my-hand",
            "soar-like-the-eagle-3",
            "he-holds-my-tomorrows",
            "prayer-the-pulse-of-life",
        ],
    ),
    (
        "the-inner-life",
        "The Inner Life",
        "The path that turns inward \u2014 \u00e0 Kempis, Law and Guyon, the love of "
        "God and the shut door of the secret place, the soul alone with him.",
        [
            "the-imitation-of-christ",
            "a-serious-call",
            "a-short-and-easy-method-of-prayer",
            "on-loving-god",
            "confessions",
            "the-inner-chamber",
        ],
    ),
    (
        "the-great-awakening",
        "The Great Awakening",
        "The preaching that shook two continents \u2014 Whitefield and Wesley in the "
        "open air, Edwards among his people, Finney on revival \u2014 and the "
        "doctrine beneath the flame.",
        [
            "revival-lectures",
            "sermons-on-several-occasions",
            "selected-sermons-whitefield",
            "selected-sermons-edwards",
            "plain-account-christian-perfection",
            "freedom-of-the-will",
            "religious-affections",
        ],
    ),
    (
        "the-body-of-christ",
        "The Body of Christ",
        "The church as a living whole \u2014 members of one another, joined to the "
        "Head, and the service and shepherding that flow from it.",
        [
            "on-the-priesthood",
            "the-reformed-pastor",
            "first-epistle-of-clement",
            "separation-and-service",
        ],
    ),
    (
        "for-those-who-lead",
        "For Those Who Lead",
        "A charge to shepherds and soul-winners \u2014 the pastor's care, the "
        "preacher's power in prayer, and how to bring men to Christ.",
        [
            "the-reformed-pastor",
            "on-the-priesthood",
            "power-through-prayer",
            "how-to-bring-men-to-christ",
            "men-who-tended-the-flock-2",
            "the-fundamental-doctrines-of-the-christian-faith",
        ],
    ),
    (
        "the-wesleys-and-early-methodism",
        "The Wesleys & Early Methodism",
        "The awakening that became a movement \u2014 John Wesley's sermons and plain "
        "account, the mother who shaped him, and the fervour that followed.",
        [
            "sermons-on-several-occasions",
            "plain-account-christian-perfection",
            "susanna-wesley-clarke",
            "selected-sermons-whitefield",
            "godliness",
            "purity-of-heart",
        ],
    ),
    (
        "foundations-of-the-faith",
        "Foundations of the Faith",
        "The old doctrines, plainly held \u2014 the incarnation, the grace and will "
        "of God, the commandments and the fundamentals once for all delivered.",
        [
            "the-fundamental-doctrines-of-the-christian-faith",
            "enchiridion",
            "on-the-incarnation",
            "freedom-of-the-will",
            "ten-commandments",
        ],
    ),
    (
        "saints-of-the-african-diaspora",
        "Saints of the African Diaspora",
        "The gospel carried in Black voices \u2014 Richard Allen and the freeborn "
        "preachers, the holiness women who would not be silenced, and Crowther on "
        "the Niger.",
        [
            "life-experience-gospel-labours",
            "religious-experience-and-journal",
            "a-brand-plucked-from-the-fire",
            "amanda-smith-autobiography",
            "journal-of-an-expedition-up-the-niger",
        ],
    ),
    (
        "the-grace-of-god",
        "The Grace of God",
        "Grace from first to last \u2014 free, sovereign and sufficient, abounding "
        "to the chief of sinners and holding the weakest saint.",
        [
            "all-of-grace",
            "grace-abounding",
            "the-way-to-god",
            "all-things-for-good",
        ],
    ),
    (
        "victory-over-sin",
        "Victory Over Sin",
        "The inward fight for holiness \u2014 mortifying sin, purity of heart, the "
        "affections set in order, and the way into the holiest.",
        [
            "mortification-of-sin",
            "religious-affections",
            "purity-of-heart",
            "plain-account-christian-perfection",
            "holy-in-christ",
            "way-into-holiest",
        ],
    ),
    (
        "to-the-ends-of-the-earth",
        "To the Ends of the Earth",
        "The missionary journals \u2014 Brainerd in the forests, Taylor in China, "
        "Carmichael in India, Crowther on the Niger \u2014 the gospel carried at "
        "any cost.",
        [
            "life-and-diary-of-david-brainerd",
            "a-retrospect",
            "separation-and-service",
            "things-as-they-are",
            "journal-of-an-expedition-up-the-niger",
            "amanda-smith-autobiography",
            "men-and-women-who-gave-everything-2",
        ],
    ),
    (
        "faith-for-the-impossible",
        "Faith for the Impossible",
        "Taking God at his word \u2014 M\u00fcller's orphans fed by prayer alone, the "
        "grace of waiting on him, and the bank of faith that never breaks.",
        [
            "answers-to-prayer",
            "the-life-of-trust",
            "waiting-on-god",
            "cheque-book",
            "days-of-heaven-upon-earth",
        ],
    ),
    (
        "men-of-valour",
        "Men of Valour",
        "A call to the men \u2014 to pray, to lead, to give everything and to tend "
        "the flock \u2014 lives of courage for the sons of God.",
        [
            "men-of-prayer-2",
            "men-who-moved-heaven",
            "men-who-tended-the-flock-2",
            "rise-up-men-of-god-2",
            "men-and-women-who-gave-everything-2",
        ],
    ),
    (
        "for-teens",
        "For Teens",
        "Faith for the teenage years — coming to Christ, belonging to his "
        "people, and the courage to follow. Short, plain, honest books, and "
        "true stories of lives that were spent for him, written for or well "
        "within reach of younger readers.",
        [
            "growing-in-wisdom",
            "around-the-wicket-gate",
            "all-of-grace",
            "the-way-to-god",
            "prayer-the-pulse-of-life",
            "he-holds-my-tomorrows",
            "soar-like-the-eagle-3",
            "stepping-stones-2",
            "clothed-with-strength-and-dignity",
            "rise-up-men-of-god-2",
            "a-retrospect",
            "things-as-they-are",
            "the-life-of-trust",
            "life-and-diary-of-david-brainerd",
            "men-and-women-who-gave-everything-2",
            "men-who-moved-heaven",
            "women-who-moved-heaven-2",
        ],
    ),
    (
        "soar-like-the-eagle",
        "Soar Like the Eagle",
        "They that wait upon the Lord renew their strength — the classics on "
        "drawing power from God when your own is spent. Books for the weary: to "
        "wait, to rest, and to mount up again on eagles' wings.",
        [
            "waiting-on-god",
            "soar-like-the-eagle-3",
            "the-christians-secret-of-a-happy-life-4",
            "the-god-of-all-comfort",
            "the-life-of-trust",
            "the-secret-of-guidance",
            "thoughts-for-the-quiet-hour",
            "clothed-with-strength-and-dignity",
        ],
    ),
    (
        "for-young-readers",
        "For Young Readers",
        "The faith, told simply, for children and those who read with them — "
        "the great story of the journey home, in language a child can follow. "
        "A shelf that grows as more is retold and written for the young.",
        [
            "pilgrims-progress-words-of-one-syllable",
            "divine-songs-for-children",
            "brave-for-god",
            "brave-for-god-2",
            "brave-for-god-3",
            "brave-for-god-4",
            "hurlbuts-life-of-christ",
            "rooted-1",
            "rooted-2",
            "rooted-3",
            "rooted-4",
            "rooted-5",
            "rooted-6",
            "daughters-of-the-king-1",
            "daughters-of-the-king-2",
            "sons-of-the-king-1",
            "sons-of-the-king-2",
            "daughters-of-the-king-3",
            "sons-of-the-king-3",
        ],
    ),
]

# Shelves that ship LIVE IN ENGLISH while their translations are still being
# produced. Topic prose has no English fallback, so a shelf missing from a
# language is simply absent there (``Topic.is_translated_into``) — these appear
# on the English ``/topics`` and are hidden in the other languages until the
# translation queue fills each one (``manage.py translate_topic --language
# <lang>``, which writes ``data/topic_translations/<lang>.json``).
#
# This is the ONE deliberate exception to the full per-language coverage guard:
# ``TopicTests.test_every_translated_language_covers_every_topic`` and
# ``tests_fixture.TopicTranslationFileTests`` still demand that every OTHER
# shelf is covered in every language, and still reject prose for a slug that
# names no topic — they only stop treating a *pending* shelf's absence as a
# failure. A pending shelf may also be partially covered (some languages done,
# others not) as the queue works through it.
#
# Remove a slug from this set once its seven languages (ar/es/hi/lg/pt/sw/uk)
# are all present; when the set is empty the guard is back to full strength.
# A slug here MUST name a real topic in ``TOPICS`` above — a stale entry would
# quietly exempt nothing and mask a genuinely uncovered shelf (a test pins this).
TRANSLATION_PENDING: frozenset[str] = frozenset(
    {
        "the-puritans",
        "abiding-in-christ",
        "women-of-faith",
        "voices-of-the-early-church",
        "day-by-day",
        "the-east-african-revival",
        "contemporary-voices",
        "the-inner-life",
        "the-great-awakening",
        "the-body-of-christ",
        "for-those-who-lead",
        "the-wesleys-and-early-methodism",
        "foundations-of-the-faith",
        "saints-of-the-african-diaspora",
        "the-grace-of-god",
        "victory-over-sin",
        "to-the-ends-of-the-earth",
        "faith-for-the-impossible",
        "men-of-valour",
        "for-teens",
        "soar-like-the-eagle",
        "for-young-readers",
    }
)

# Sermon members per topic, by canonical sermon slug (language-agnostic, like
# the book members). A sermon shows on a topic's shelf in each language it
# exists in. {topic slug: [ordered sermon slugs]}
TOPIC_SERMONS = {
    "prayer": [
        "the-golden-key-of-prayer",
        "order-and-argument-in-prayer",
        "pauls-first-prayer",
        "do-you-pray",
        "intercession-every-christians-duty",
        "prevailing-prayer",
        "the-spirit-of-prayer",
    ],
    "holy-spirit": [
        "filled-with-the-spirit",
        "the-holy-ghost",
    ],
    "deeper-life": [
        "himself",
        "christ-all-in-all",
        "the-death-of-self",
        "self-denial-versus-self-assertion",
        "pauls-praise-of-christian-love",
        "the-joy-of-the-lord",
        "the-power-of-stillness",
        "walking-with-god",
        "catholic-spirit",
    ],
    "grace-and-comfort": [
        "free-grace",
        "the-immutability-of-god",
        "sweet-comfort-for-feeble-saints",
        "comfort-for-the-desponding",
        "consolation-in-the-furnace",
        "comfort-ye-my-people",
        "blessed-adversity",
        "if-god-be-for-us",
        "no-one-can-harm-the-man-who-does-not-injure-himself",
        "every-mans-need-of-a-refuge",
        "rest",
        "songs-in-the-night",
        "the-sweet-uses-of-adversity",
        "under-the-shepherds-care",
        "safety-fulness-and-sweet-refreshment-in-christ",
        "the-appearing-of-the-grace-of-god",
        "grace-and-truth",
        "eight-i-wills-of-christ",
        "against-eutropius",
        "enduring-persecution-for-christ",
        "god-glorified-in-mans-dependence",
        "the-greatest-sentence-ever-written",
    ],
    "revival-and-missions": [
        "compel-them-to-come-in",
        "the-way-of-salvation",
        "christs-boundless-compassion",
        "the-worlds-need",
        "witnessing-for-christ",
        "why-is-god-a-stranger-in-the-land",
    ],
    "faith-and-guidance": [
        "the-possibilities-of-faith",
        "unfailing-springs",
        "a-full-reward",
        "all-sufficiency",
        "blessed-prosperity",
        "faith-and-assurance",
        "faith",
        "the-power-of-feeble-faith",
        "the-secret-of-tranquillity",
    ],
    "the-gospel-call": [
        "christ-crucified",
        "the-new-birth",
        "salvation-by-faith",
        "come-thou-into-the-ark",
        "the-dying-thief",
        "the-ravens-cry",
        "a-divine-and-supernatural-light",
        "are-you-born-again",
        "come-unto-him",
        "coming-to-the-king",
        "fall-and-recovery-of-man",
        "gods-love-for-a-sinning-world",
        "justification-by-grace",
        "marks-of-a-true-conversion",
        "naaman-the-syrian",
        "one-word-gospel",
        "sinners-bound-to-change-their-own-hearts",
        "sinners-in-the-hands-of-an-angry-god",
        "the-almost-christian",
        "the-good-way-of-coming-before-the-lord",
        "the-impressions-of-natural-men",
        "the-lord-our-righteousness",
        "the-method-of-grace",
        "the-right-kind-of-faith",
        "the-sinners-friend",
    ],
    "the-way-of-holiness": [
        "aggressive-christianity",
        "a-ribband-of-blue",
        "the-circumcision-of-the-heart",
        "what-have-i-to-do-any-more-with-idols",
    ],
    "christ-and-the-cross": [
        "behold-the-lamb-of-god",
        "christ-precious-to-believers",
        "christ-the-believers-wisdom",
        "how-to-contemplate-christs-holy-sufferings",
        "the-excellency-of-christ",
        "the-resurrection-of-jesus",
        "the-shameful-sufferer",
        "the-triumph-of-calvary",
        "worthy-is-the-lamb",
    ],
    "soar-like-the-eagle": [
        "rest",
        "the-power-of-stillness",
        "the-power-of-feeble-faith",
        "under-the-shepherds-care",
    ],
}


# Article members per topic, by canonical article slug (language-agnostic, like
# the book and sermon members). This is the bidirectional funnel: an article
# shows on a topic's shelf, and the topics it lists appear as chips on the
# article. {topic slug: [ordered article slugs]}
TOPIC_ARTICLES = {
    "prayer": [
        "how-to-pray-so-god-answers",
        "what-is-intercessory-prayer",
        "the-power-of-persistent-prayer",
        "how-to-pray-the-psalms",
        "the-morning-watch",
        "augustines-confessions-guide",
        "how-to-pray-for-revival",
        "the-life-of-trust-guide",
        "power-through-prayer-guide",
        "the-inner-chamber-guide",
        "prayer-and-praying-men-guide",
        "ministry-of-intercession-guide",
        "necessity-of-prayer-guide",
        "purpose-in-prayer-guide",
        "prevailing-prayer-guide",
        "essentials-of-prayer-guide",
        "a-short-and-easy-method-of-prayer-guide",
    ],
    "holy-spirit": [
        "what-is-the-baptism-of-the-holy-spirit",
        "who-is-the-holy-spirit",
        "what-are-the-spiritual-gifts",
        "what-is-the-fruit-of-the-spirit",
        "soar-like-the-eagle-guide",
        "the-person-and-work-of-the-holy-spirit-guide",
    ],
    "deeper-life": [
        "what-does-it-mean-to-abide-in-christ",
        "the-cost-of-following-jesus",
        "what-is-surrender-to-god",
        "what-is-biblical-fasting",
        "the-morning-watch",
        "pilgrims-progress-guide",
        "the-imitation-of-christ-guide",
        "what-is-the-lords-supper",
        "what-is-the-church",
        "what-is-the-kingdom-of-god",
        "how-to-read-the-bible-for-beginners",
        "how-to-wait-on-god",
        "how-to-grow-in-your-faith",
        "how-to-be-content",
        "how-to-walk-in-humility",
        "how-to-memorize-scripture",
        "absolute-surrender-guide",
        "the-christians-secret-of-a-happy-life-guide",
        "what-is-worship",
        "how-to-find-rest-for-your-soul",
        "what-is-spiritual-warfare",
        "soar-like-the-eagle-guide",
        "waiting-on-god-guide",
        "life-of-antony-guide",
        "till-he-come-guide",
        "true-vine-guide",
        "way-into-holiest-guide",
        "days-of-heaven-upon-earth-guide",
        "the-fourfold-gospel-guide",
        "jesus-himself-2-guide",
        "the-masters-indwelling-guide",
    ],
    "grace-and-comfort": [
        "how-to-trust-god-in-suffering",
        "how-to-overcome-fear-and-anxiety-with-faith",
        "what-is-grace",
        "what-is-faith",
        "what-does-the-bible-say-about-heaven",
        "what-is-the-love-of-god",
        "how-to-overcome-doubt",
        "how-to-find-comfort-in-grief-and-loss",
        "how-to-be-content",
        "how-to-deal-with-guilt-and-shame",
        "how-to-find-rest-for-your-soul",
        "what-does-the-bible-say-about-the-end-times",
        "the-bruised-reed-guide",
        "why-would-a-good-god-allow-suffering",
        "the-unselfishness-of-god-guide",
        "the-god-of-all-comfort-guide",
        "gleanings-among-the-sheaves-guide",
    ],
    "revival-and-missions": [
        "what-is-revival-and-how-does-it-begin",
        "what-is-the-great-commission",
        "how-to-pray-for-revival",
        "the-marks-of-a-true-revival",
        "what-was-the-great-awakening",
        "personal-revival-reviving-a-cold-heart",
        "revival-and-repentance-breaking-up-the-fallow-ground",
        "how-to-share-your-faith",
        "the-life-and-diary-of-david-brainerd-guide",
        "revival-lectures-guide",
        "things-as-they-are-guide",
        "amanda-smith-autobiography-guide",
        "a-retrospect-guide",
        "religious-experience-and-journal-guide",
        "life-experience-gospel-labours-guide",
    ],
    "faith-and-guidance": [
        "how-to-find-gods-will-for-your-life",
        "how-to-hear-gods-voice",
        "how-to-trust-god-in-suffering",
        "what-is-faith",
        "how-to-read-the-bible-for-beginners",
        "how-to-overcome-doubt",
        "how-to-wait-on-god",
        "how-to-grow-in-your-faith",
        "can-i-be-a-christian-and-have-doubts",
        "is-the-bible-reliable",
        "do-science-and-faith-contradict",
        "divine-healing-guide",
        "the-secret-of-guidance-guide",
        "the-fundamental-doctrines-of-the-christian-faith-guide",
    ],
    "the-gospel-call": [
        "how-to-be-born-again",
        "how-to-have-assurance-of-salvation",
        "what-is-the-gospel",
        "what-is-justification-by-faith",
        "pilgrims-progress-guide",
        "augustines-confessions-guide",
        "sinners-in-the-hands-of-an-angry-god-explained",
        "what-is-grace",
        "what-is-repentance",
        "why-did-jesus-die",
        "what-is-the-trinity",
        "what-is-the-kingdom-of-god",
        "how-to-share-your-faith",
        "how-to-deal-with-guilt-and-shame",
        "grace-abounding-guide",
        "on-the-incarnation-guide",
        "what-does-the-bible-say-about-the-end-times",
        "what-is-baptism",
        "how-do-we-know-jesus-rose",
        "is-jesus-the-only-way",
        "freedom-of-the-will-guide",
        "selected-sermons-whitefield-guide",
        "the-way-to-god-guide",
        "talks-to-the-farmer-guide",
        "a-call-to-the-unconverted-guide",
        "all-of-grace-guide",
    ],
    "the-way-of-holiness": [
        "what-is-sanctification",
        "how-to-forgive-someone-who-hurt-you",
        "how-to-overcome-sin-and-temptation",
        "the-priesthood-of-all-believers",
        "why-humility-matters",
        "the-imitation-of-christ-guide",
        "revival-and-repentance-breaking-up-the-fallow-ground",
        "what-is-repentance",
        "how-to-walk-in-humility",
        "how-to-memorize-scripture",
        "what-is-worship",
        "how-to-overcome-anger",
        "how-to-honor-god-with-your-money",
        "what-is-spiritual-warfare",
        "how-to-love-your-enemies",
        "mortification-of-sin-guide",
        "a-serious-call-guide",
        "ten-commandments-guide",
        "sermons-on-several-occasions-guide",
        "holy-in-christ-guide",
        "a-brand-plucked-from-the-fire-guide",
        "first-epistle-of-clement-guide",
        "godliness-guide",
        "purity-of-heart-guide",
    ],
    "enduring-classics": [
        "pilgrims-progress-guide",
        "the-imitation-of-christ-guide",
        "augustines-confessions-guide",
        "sinners-in-the-hands-of-an-angry-god-explained",
        "what-is-the-trinity",
        "absolute-surrender-guide",
        "the-christians-secret-of-a-happy-life-guide",
        "the-life-and-diary-of-david-brainerd-guide",
        "grace-abounding-guide",
        "on-the-incarnation-guide",
        "religious-affections-guide",
        "mortification-of-sin-guide",
        "the-bruised-reed-guide",
        "a-serious-call-guide",
        "the-life-of-trust-guide",
        "ten-commandments-guide",
        "revival-lectures-guide",
        "waiting-on-god-guide",
        "the-person-and-work-of-the-holy-spirit-guide",
        "things-as-they-are-guide",
        "freedom-of-the-will-guide",
        "sermons-on-several-occasions-guide",
        "the-reformed-pastor-guide",
        "life-of-antony-guide",
        "till-he-come-guide",
        "selected-sermons-whitefield-guide",
        "the-unselfishness-of-god-guide",
        "holy-in-christ-guide",
        "a-brand-plucked-from-the-fire-guide",
        "true-vine-guide",
        "divine-healing-guide",
        "first-epistle-of-clement-guide",
        "amanda-smith-autobiography-guide",
        "the-god-of-all-comfort-guide",
        "epistles-of-ignatius-guide",
        "a-retrospect-guide",
        "power-through-prayer-guide",
        "the-way-to-god-guide",
        "the-secret-of-guidance-guide",
        "the-inner-chamber-guide",
        "prayer-and-praying-men-guide",
        "way-into-holiest-guide",
        "ministry-of-intercession-guide",
        "godliness-guide",
        "necessity-of-prayer-guide",
        "days-of-heaven-upon-earth-guide",
        "purity-of-heart-guide",
        "talks-to-the-farmer-guide",
        "purpose-in-prayer-guide",
        "a-call-to-the-unconverted-guide",
        "the-fourfold-gospel-guide",
        "gleanings-among-the-sheaves-guide",
        "the-fundamental-doctrines-of-the-christian-faith-guide",
        "prevailing-prayer-guide",
        "religious-experience-and-journal-guide",
        "jesus-himself-2-guide",
        "essentials-of-prayer-guide",
        "all-of-grace-guide",
        "a-short-and-easy-method-of-prayer-guide",
        "the-masters-indwelling-guide",
        "life-experience-gospel-labours-guide",
    ],
    "the-preached-word": [
        "how-to-know-if-god-is-calling-you-to-ministry",
        "what-makes-a-godly-leader",
        "sinners-in-the-hands-of-an-angry-god-explained",
        "what-is-the-church",
        "religious-affections-guide",
        "the-reformed-pastor-guide",
        "epistles-of-ignatius-guide",
    ],
    "soar-like-the-eagle": [
        "how-to-wait-on-god",
        "how-to-find-rest-for-your-soul",
        "how-to-be-content",
        "how-to-trust-god-in-suffering",
        "soar-like-the-eagle-guide",
    ],
    "for-teens": [
        "can-i-be-a-christian-and-have-doubts",
        "is-the-bible-reliable",
        "why-would-a-good-god-allow-suffering",
        "do-science-and-faith-contradict",
        "how-do-we-know-jesus-rose",
        "is-jesus-the-only-way",
    ],
}


# SEO overrides per topic — the <title> and <meta description> the topic
# page uses instead of the bare "<title> — Ochorus" / `description`. English
# only; per-language values ride TopicTranslation. seo_title is the FULL tag
# text (it already ends in "— Ochorus"). {slug: (seo_title, meta_description)}.
TOPIC_SEO = {
    "prayer": (
        "Books on Prayer — Free Christian Classics — Ochorus",
        "How to pray? The enduring Christian classics on prayer — learning to pray and to keep praying, free to read on Ochorus.",
    ),
    "holy-spirit": (
        "Books on the Holy Spirit — Free Classics — Ochorus",
        "Who is the Holy Spirit? Classic books on the Spirit's baptism, indwelling and power — free to read on Ochorus.",
    ),
    "deeper-life": (
        "The Deeper Christian Life — Free Classics — Ochorus",
        "What is the deeper Christian life? Classics on holiness, surrender and the abundant life hidden with Christ — free on Ochorus.",
    ),
    "grace-and-comfort": (
        "Grace & Comfort — Free Christian Classics — Ochorus",
        "Comfort for hard times: the Christian classics on the unfailing grace of God in every trial — free to read on Ochorus.",
    ),
    "revival-and-missions": (
        "Revival & Missions — Free Christian Classics — Ochorus",
        "What is revival? Classic accounts of awakening and lives poured out for the gospel — free to read on Ochorus.",
    ),
    "faith-and-guidance": (
        "Faith & Guidance — Free Christian Classics — Ochorus",
        "How to know God's will: classics on trusting God for daily bread, direction and every promise — free on Ochorus.",
    ),
    "the-gospel-call": (
        "The Gospel Call — Free Christian Classics — Ochorus",
        "How to be saved: the classic gospel invitations to turn, repent and believe — free to read on Ochorus.",
    ),
    "enduring-classics": (
        "The Christian Classics — Free to Read — Ochorus",
        "The best Christian classics to read — the books that have walked with pilgrims for centuries, free on Ochorus.",
    ),
    "the-way-of-holiness": (
        "The Way of Holiness — Free Classics — Ochorus",
        "What is Christian holiness? The classics on being set apart for God, free to read on Ochorus.",
    ),
    "the-preached-word": (
        "Classic Sermons — Free to Read — Ochorus",
        "The greatest sermons ever preached — great preaching on the page, in full, free to read on Ochorus.",
    ),
    "christ-and-the-cross": (
        "Christ & the Cross — Free Christian Classics — Ochorus",
        "What Jesus accomplished on the cross: the classics on the person and work of the Saviour — free on Ochorus.",
    ),
    "the-puritans": (
        "Puritan Books — Free to Read — Ochorus",
        "The best Puritan books to read — the plain, searching divinity of the Puritans, free to read on Ochorus.",
    ),
    "abiding-in-christ": (
        "Abiding in Christ — Free Christian Classics — Ochorus",
        "What does abiding in Christ mean? The classics on union and communion with the Lord Jesus — free on Ochorus.",
    ),
    "women-of-faith": (
        "Women of Faith — Free Christian Classics — Ochorus",
        "The great Christian women of history — mothers, missionaries and mystics whose faith prevailed, free on Ochorus.",
    ),
    "voices-of-the-early-church": (
        "The Early Church Fathers — Free Classics — Ochorus",
        "Who were the church fathers? The faith of the first centuries in its own words, free to read on Ochorus.",
    ),
    "day-by-day": (
        "Daily Devotional Classics — Free to Read — Ochorus",
        "The best daily devotionals — a reading for the morning and the evening, free to read on Ochorus.",
    ),
    "the-east-african-revival": (
        "The East African Revival — Free Classics — Ochorus",
        "What was the East African Revival? Tukutendereza Yesu — the awakening in its own voices, free on Ochorus.",
    ),
    "contemporary-voices": (
        "Modern Christian Classics — Free to Read — Ochorus",
        "The best modern Christian books — living guides writing on the old road, free to read on Ochorus.",
    ),
    "the-inner-life": (
        "The Inner Life — Free Christian Classics — Ochorus",
        "Christian mysticism and the contemplative life — the path that turns inward, free to read on Ochorus.",
    ),
    "the-great-awakening": (
        "The Great Awakening — Free Classics — Ochorus",
        "What was the Great Awakening? The preaching that shook two continents, free to read on Ochorus.",
    ),
    "the-body-of-christ": (
        "Books on the Church — Free Classics — Ochorus",
        "What is the body of Christ? The classics on the church as a living whole, members of one another — free on Ochorus.",
    ),
    "for-those-who-lead": (
        "Christian Leadership — Free Classics — Ochorus",
        "The best books on pastoral ministry — a charge to shepherds and soul-winners, free to read on Ochorus.",
    ),
    "the-wesleys-and-early-methodism": (
        "John Wesley & Early Methodism — Free Classics — Ochorus",
        "What did John Wesley teach? Wesley's sermons and the awakening that became a movement, free on Ochorus.",
    ),
    "foundations-of-the-faith": (
        "Christian Doctrine — Free Classics — Ochorus",
        "The basics of the Christian faith — the old doctrines plainly held, free to read on Ochorus.",
    ),
    "saints-of-the-african-diaspora": (
        "The Black Christian Tradition — Free Classics — Ochorus",
        "The early Black Christian leaders — the gospel carried in Black voices, free to read on Ochorus.",
    ),
    "the-grace-of-god": (
        "The Grace of God — Free Christian Classics — Ochorus",
        "What is the grace of God? Grace from first to last — free, sovereign and sufficient — the classics, free on Ochorus.",
    ),
    "victory-over-sin": (
        "Books on Overcoming Sin — Free Classics — Ochorus",
        "How to overcome sin: the classics on mortifying sin and purity of heart, free to read on Ochorus.",
    ),
    "to-the-ends-of-the-earth": (
        "Missionary Biographies — Free to Read — Ochorus",
        "The great missionary biographies — the missionary journals in full, free to read on Ochorus.",
    ),
    "faith-for-the-impossible": (
        "Faith for the Impossible — Free Classics — Ochorus",
        "How to have more faith: taking God at his word — orphans fed by prayer alone and more, free on Ochorus.",
    ),
    "men-of-valour": (
        "Christian Books for Men — Free to Read — Ochorus",
        "The best Christian books for men — a call to pray, to lead, to give everything, free to read on Ochorus.",
    ),
}

# A themed Scripture epigraph per topic (KJV — public domain), shown on the
# topic page. {slug: (reference, verse text)}
TOPIC_SCRIPTURE = {
    "prayer": (
        "Jeremiah 33:3",
        "Call unto me, and I will answer thee, and shew thee great and mighty "
        "things, which thou knowest not.",
    ),
    "holy-spirit": (
        "Zechariah 4:6",
        "Not by might, nor by power, but by my spirit, saith the Lord of hosts.",
    ),
    "deeper-life": (
        "Colossians 3:3",
        "For ye are dead, and your life is hid with Christ in God.",
    ),
    "grace-and-comfort": (
        "2 Corinthians 12:9",
        "My grace is sufficient for thee: for my strength is made perfect in "
        "weakness.",
    ),
    "revival-and-missions": (
        "Habakkuk 3:2",
        "O Lord, revive thy work in the midst of the years, in the midst of the "
        "years make known.",
    ),
    "faith-and-guidance": (
        "Proverbs 3:6",
        "In all thy ways acknowledge him, and he shall direct thy paths.",
    ),
    "the-gospel-call": (
        "2 Corinthians 5:20",
        "We pray you in Christ\u2019s stead, be ye reconciled to God.",
    ),
    "enduring-classics": (
        "Jeremiah 6:16",
        "Stand ye in the ways, and see, and ask for the old paths, where is "
        "the good way, and walk therein, and ye shall find rest for your "
        "souls.",
    ),
    "the-way-of-holiness": (
        "Hebrews 12:14",
        "Follow peace with all men, and holiness, without which no man shall "
        "see the Lord.",
    ),
    "the-preached-word": (
        "Romans 10:14",
        "How shall they hear without a preacher?",
    ),
    "the-puritans": (
        "Hebrews 4:12",
        "For the word of God is quick, and powerful, and sharper than any "
        "twoedged sword, piercing even to the dividing asunder of soul and spirit.",
    ),
    "abiding-in-christ": (
        "John 15:4",
        "Abide in me, and I in you. As the branch cannot bear fruit of itself, "
        "except it abide in the vine; no more can ye, except ye abide in me.",
    ),
    "women-of-faith": (
        "Proverbs 31:30",
        "Favour is deceitful, and beauty is vain: but a woman that feareth the "
        "Lord, she shall be praised.",
    ),
    "voices-of-the-early-church": (
        "Hebrews 12:1",
        "We also are compassed about with so great a cloud of witnesses.",
    ),
    "day-by-day": (
        "Lamentations 3:22–23",
        "It is of the Lord's mercies that we are not consumed, because his "
        "compassions fail not. They are new every morning: great is thy "
        "faithfulness.",
    ),
    "the-east-african-revival": (
        "1 John 1:7",
        "But if we walk in the light, as he is in the light, we have fellowship "
        "one with another, and the blood of Jesus Christ his Son cleanseth us "
        "from all sin.",
    ),
    "contemporary-voices": (
        "Psalm 145:4",
        "One generation shall praise thy works to another, and shall declare "
        "thy mighty acts.",
    ),
    "the-inner-life": (
        "Matthew 6:6",
        "But thou, when thou prayest, enter into thy closet, and when thou hast "
        "shut thy door, pray to thy Father which is in secret.",
    ),
    "the-great-awakening": (
        "Psalm 85:6",
        "Wilt thou not revive us again: that thy people may rejoice in thee?",
    ),
    "the-body-of-christ": (
        "1 Corinthians 12:27",
        "Now ye are the body of Christ, and members in particular.",
    ),
    "for-those-who-lead": (
        "1 Peter 5:2",
        "Feed the flock of God which is among you, taking the oversight thereof, "
        "not by constraint, but willingly.",
    ),
    "the-wesleys-and-early-methodism": (
        "Luke 24:32",
        "Did not our heart burn within us, while he talked with us by the way, "
        "and while he opened to us the scriptures?",
    ),
    "foundations-of-the-faith": (
        "Jude 3",
        "Ye should earnestly contend for the faith which was once delivered "
        "unto the saints.",
    ),
    "saints-of-the-african-diaspora": (
        "Psalm 68:31",
        "Princes shall come out of Egypt; Ethiopia shall soon stretch out her "
        "hands unto God.",
    ),
    "the-grace-of-god": (
        "Ephesians 2:8",
        "For by grace are ye saved through faith; and that not of yourselves: "
        "it is the gift of God.",
    ),
    "victory-over-sin": (
        "Romans 6:14",
        "For sin shall not have dominion over you: for ye are not under the "
        "law, but under grace.",
    ),
    "to-the-ends-of-the-earth": (
        "Acts 1:8",
        "And ye shall be witnesses unto me both in Jerusalem, and in all "
        "Judaea, and in Samaria, and unto the uttermost part of the earth.",
    ),
    "faith-for-the-impossible": (
        "Mark 9:23",
        "If thou canst believe, all things are possible to him that believeth.",
    ),
    "men-of-valour": (
        "1 Corinthians 16:13",
        "Watch ye, stand fast in the faith, quit you like men, be strong.",
    ),
    "for-teens": (
        "1 Timothy 4:12",
        "Let no man despise thy youth; but be thou an example of the "
        "believers, in word, in conversation, in charity, in spirit, in "
        "faith, in purity.",
    ),
    "soar-like-the-eagle": (
        "Isaiah 40:31",
        "But they that wait upon the Lord shall renew their strength; they "
        "shall mount up with wings as eagles; they shall run, and not be "
        "weary; and they shall walk, and not faint.",
    ),
    "for-young-readers": (
        "Matthew 19:14",
        "Suffer little children, and forbid them not, to come unto me: for of "
        "such is the kingdom of heaven.",
    ),
}


# Editorial Questions & Answers per topic, in ENGLISH — the shelf's own
# grounded Q&A. Plain text (no HTML): seed_topics writes it to Topic.qa, the
# reader shows a "Questions and Answers" section and the page emits FAQPage
# JSON-LD. Translations ride TopicTranslation.qa (English first). A slug here
# MUST name a real topic in TOPICS above. {slug: [{question, answer}, ...]}
TOPIC_QA = {
    "prayer": [
        {
            "question": "What is the On Prayer collection?",
            "answer": "It gathers the Christian classics on the inner life of prayer — learning to pray, and learning to keep praying, from the secret place of private devotion to prevailing intercession for others. The shelf ranges from gentle beginners' guides to bracing calls to persevere, and takes as its keynote the promise of Jeremiah 33:3: \"Call unto me, and I will answer thee, and shew thee great and mighty things, which thou knowest not.\""
        },
        {
            "question": "Which classic works on prayer are included?",
            "answer": "Among them are Andrew Murray's \"The Inner Chamber\" and \"Lord, Teach Us to Pray,\" Spurgeon's teaching on prayer and his \"Cheque Book of the Bank of Faith,\" Jeanne Guyon's \"A Short and Easy Method of Prayer,\" E. M. Bounds on prevailing and persistent prayer, George Müller's \"Answers to Prayer,\" and Andrew Murray's \"The Ministry of Intercession\" — a spread across centuries and traditions united by a single subject."
        },
        {
            "question": "Where should a beginner start?",
            "answer": "Andrew Murray's \"Lord, Teach Us to Pray\" and \"The Inner Chamber\" are gentle, practical starting points that assume you are learning. From there, Guyon draws the reader toward contemplative prayer of the heart, E. M. Bounds presses the urgency and cost of intercession, and George Müller's record of answered prayer builds confidence that God hears — so the shelf can be walked from first steps toward a settled life of prayer."
        },
        {
            "question": "What is intercessory or prevailing prayer?",
            "answer": "It is praying through to an answer and standing in the gap for others rather than only for oneself — the persistent, believing prayer the shelf's authors treat as every Christian's calling. E. M. Bounds and Watchman Nee especially press it: that God has chosen to work through the prayers of his people, so that intercession is real labour with real effect, not a formality."
        },
        {
            "question": "What does the shelf teach about unanswered prayer?",
            "answer": "It answers discouragement with both realism and hope. George Müller's \"Answers to Prayer\" records decades of specific requests met by God, while the whole collection urges persistence on the ground of Jeremiah 33:3 — that God invites us to call and promises to answer. The classics distinguish delay from denial and teach the believer to keep asking, aligning the will with God's rather than abandoning the request."
        },
        {
            "question": "What is the \"secret place\" or inner chamber?",
            "answer": "It is the practice of private, hidden prayer — withdrawing from the noise of the day to meet God alone, as Jesus taught his disciples to enter the closet and shut the door. Andrew Murray's \"The Inner Chamber\" is the shelf's fullest treatment of it: that the strength of all public and intercessory prayer is drawn from this unseen, personal communion with God."
        },
        {
            "question": "Which authors are represented in the collection?",
            "answer": "The shelf draws together Andrew Murray, Charles Spurgeon, Jeanne Guyon, E. M. Bounds, George Müller and Watchman Nee, among others — Reformed and Wesleyan, Victorian and modern, Western and Chinese. What unites such different writers is a shared conviction that prayer is the pulse of the Christian life and that it can be learned."
        },
        {
            "question": "Why read old books on prayer today?",
            "answer": "Because the difficulty of prayer has not changed, and these writers faced it honestly — dryness, distraction, delay, and the temptation to give up. Tested across generations, their counsel is practical rather than sentimental, and it consistently points past technique to the God who says, \"Call unto me, and I will answer thee.\" They teach not a method to master but a relationship to keep."
        }
    ],
    "the-puritans": [
        {
            "question": "What is The Puritans collection?",
            "answer": "It gathers the plain, searching divinity of the Puritans — doctrine pressed home upon the heart and conscience rather than left in the abstract. Bunyan's pilgrim, Owen on the sin within, Watson's warmth and Edwards' fire all appear here, held together by the conviction of Hebrews 4:12 that the word of God is living and powerful, \"sharper than any twoedged sword,\" piercing to the dividing of soul and spirit."
        },
        {
            "question": "Which Puritan authors and works are included?",
            "answer": "Among them are John Bunyan's \"The Pilgrim's Progress\" and \"Grace Abounding,\" John Owen's \"The Mortification of Sin,\" Thomas Watson's \"All Things for Good\" and his exposition of the Ten Commandments, Richard Sibbes' \"The Bruised Reed,\" Richard Baxter's \"The Reformed Pastor\" and \"A Call to the Unconverted,\" and Jonathan Edwards' \"Religious Affections,\" \"Freedom of the Will\" and selected sermons."
        },
        {
            "question": "What is Puritan writing like?",
            "answer": "It is plain in style and searching in aim: the Puritans wrote to be understood and to be obeyed, applying doctrine directly to the heart, the conscience and daily life. They combined rigorous theology with warm, experiential religion — as much concerned with how grace is felt and lived as with how it is defined — which is why their books still function as spiritual counsel and not only as historical texts."
        },
        {
            "question": "Where should a newcomer to the Puritans start?",
            "answer": "Bunyan's \"The Pilgrim's Progress\" is the natural entry — an allegory that carries the whole of Puritan spiritual experience in story form — and Richard Sibbes' \"The Bruised Reed\" is a gentle, encouraging introduction to their pastoral heart. Owen's \"The Mortification of Sin\" and Edwards' \"Religious Affections\" are more demanding and best read once the plainer works have set the tone."
        },
        {
            "question": "What does Owen's Mortification of Sin teach?",
            "answer": "Its famous charge is that the believer must \"be killing sin or it will be killing you\" — that indwelling sin is never dormant and must be put to death daily by the power of the Spirit, not merely managed or restrained. Owen is unsparing about self-deception, insisting that true mortification works from a changed heart and reliance on Christ rather than from mere outward discipline."
        },
        {
            "question": "Is Puritan theology harsh or cold?",
            "answer": "It is searching but not cold. The same tradition that examines sin so closely also produced Sibbes' \"The Bruised Reed,\" written to those afraid they are too far gone, and Watson's warm assurance in \"All Things for Good.\" The Puritans took sin seriously precisely because they took grace seriously, and their severity toward self-deception sits alongside deep tenderness toward the genuinely struggling believer."
        },
        {
            "question": "What is Jonathan Edwards known for here?",
            "answer": "Edwards represents the shelf's intellectual and revival fire. \"Religious Affections\" distinguishes true from false religious experience — asking what marks a genuine work of God in the heart — while \"Freedom of the Will\" is his major philosophical defence of God's sovereignty in salvation, and his sermons show the same theology preached for a verdict."
        },
        {
            "question": "Why read the Puritans today?",
            "answer": "Because few writers have mapped the inner Christian life — conversion, indwelling sin, assurance, holiness and joy — with such honesty and care. Their doctrine is pressed home upon the heart, and their books have walked with readers for centuries because they answer questions every serious believer still asks. They reward slow, prayerful reading rather than a hurried skim."
        }
    ],
    "the-east-african-revival": [
        {
            "question": "What was the East African Revival?",
            "answer": "It was a movement of spiritual awakening that ran from a hillside near Kampala through some six countries and across most of the twentieth century. Beginning among Anglican missionaries and African believers in the Rwanda–Uganda region in the 1930s, it spread through East Africa and beyond, marked by open confession of sin, reconciliation, and joyful public praise, and it shaped generations of Christians across the region."
        },
        {
            "question": "What does \"Tukutendereza Yesu\" mean?",
            "answer": "It is the Luganda phrase meaning \"We praise You, Jesus,\" the opening of the hymn that became the anthem of the revival. Sung across languages and borders, it distilled the movement's spirit — grateful, cross-centred praise for cleansing by the blood of Jesus — and it gave the whole awakening its recognisable voice wherever it spread."
        },
        {
            "question": "What is \"walking in the light\"?",
            "answer": "It is the revival's central practice, drawn from 1 John 1:7: \"if we walk in the light, as he is in the light, we have fellowship one with another, and the blood of Jesus Christ his Son cleanseth us from all sin.\" In practice it meant keeping short accounts with God and neighbour through immediate, open confession of sin and quick reconciliation, so that fellowship stayed unbroken and joy remained fresh."
        },
        {
            "question": "Which books cover the revival?",
            "answer": "The shelf includes \"A Hidden Fire\" and \"Tukutendereza,\" along with \"Clothed with Strength and Dignity,\" \"Rise Up, Men of God,\" and \"Prayer, the Pulse of Life\" — works that tell the movement's story and carry forward the teaching on the walk in the light, repentance and reconciliation that were its heart."
        },
        {
            "question": "Who were the Balokole, the \"saved ones\"?",
            "answer": "Balokole is the Luganda word for \"saved ones,\" the name given to those transformed by the revival. They were known for continual repentance, open confession, and irrepressible joy — believers who insisted that a Christian must walk continually in the light of the cross, keeping nothing hidden, and whose changed lives and fellowship carried the awakening from place to place."
        },
        {
            "question": "How is the East African Revival distinctive?",
            "answer": "Unlike a brief campaign, it was a sustained culture of revival that lasted for decades and crossed many nations, and it was largely carried by African believers themselves rather than driven from outside. Its emphasis fell not on dramatic signs but on the ordinary, costly disciplines of confession, reconciliation and daily walking in the light — which is why its influence proved so durable."
        },
        {
            "question": "What can readers learn from it today?",
            "answer": "Its enduring lesson is the practice of walking in the light: bringing sin into the open before God and others quickly, seeking reconciliation without delay, and keeping short accounts so that fellowship and joy are not lost. The revival shows that awakening is sustained less by excitement than by continual repentance and honesty within a community of believers."
        },
        {
            "question": "What role did praise and fellowship play?",
            "answer": "They were central. The revival was audibly joyful — \"Tukutendereza Yesu\" rang through its gatherings — and its life was corporate, lived out in small fellowships where believers confessed to one another and encouraged one another. Praise expressed gratitude for cleansing by the blood, and fellowship was the setting in which walking in the light was actually practised."
        }
    ],
    "holy-spirit": [
        {
            "question": "What is The Holy Spirit collection about?",
            "answer": "It gathers classic teaching on the person and work of the Holy Spirit — his baptism, indwelling and empowering — as the promised power for the Christian life. Its keynote is Zechariah 4:6, \"Not by might, nor by power, but by my spirit, saith the Lord of hosts\": that the Christian life and service are lived out in the Spirit's strength rather than by human effort."
        },
        {
            "question": "Which books are included?",
            "answer": "The shelf holds R. A. Torrey's \"The Baptism with the Holy Spirit\" and \"The Person and Work of the Holy Spirit,\" Andrew Murray's \"The Master's Indwelling,\" and \"Jesus Himself\" — works that together treat who the Spirit is, what he does, and how the believer enters into his fullness for daily life and for service."
        },
        {
            "question": "What is the baptism or filling of the Spirit?",
            "answer": "It is the promised enduing of the believer with power, especially for witness and service, which these authors distinguish from the new birth. R. A. Torrey in particular sets out the Spirit's baptism as a definite experience to be sought and received by faith — power not for display but for effective testimony to Christ, in keeping with Zechariah 4:6."
        },
        {
            "question": "Who is the Holy Spirit?",
            "answer": "He is the third person of the Trinity — not an impersonal force but a person to be known, grieved, obeyed and depended upon. R. A. Torrey's \"The Person and Work of the Holy Spirit\" is the shelf's fullest treatment, insisting that clarity about who the Spirit is must come before any right understanding of what he does in and through the believer."
        },
        {
            "question": "What is the Spirit's \"indwelling\"?",
            "answer": "It is the reality of Christ living in the believer by his Spirit, so that the Christian life is not imitation from without but Christ's own life lived from within. Andrew Murray's \"The Master's Indwelling\" and \"Jesus Himself\" dwell on this — that the secret of holiness and rest is the indwelling presence of the Lord himself, received and yielded to by faith."
        },
        {
            "question": "Where should a reader start?",
            "answer": "R. A. Torrey's \"The Person and Work of the Holy Spirit\" gives the doctrinal foundation — who the Spirit is and what he does — and is a clear place to begin. Andrew Murray's \"The Master's Indwelling\" then turns from doctrine to the experience of the indwelling life, so the two together move the reader from understanding to appropriation."
        },
        {
            "question": "What is the difference between the Spirit in conversion and in empowering?",
            "answer": "These authors distinguish the Spirit's work in the new birth — regenerating and indwelling every believer at conversion — from a subsequent enduing with power for service. The distinction is pastoral, not divisive: they urge Christians who are already born of the Spirit to go on to seek his fullness, so that the promised power for witness is not left unclaimed."
        },
        {
            "question": "Why read older books on the Holy Spirit?",
            "answer": "Because they keep the focus where Scripture puts it — on power for holiness and witness rather than on novelty — and they were written by men whose ministries visibly depended on the Spirit. Torrey and Murray write to lead the reader into an actual experience of the Spirit's fullness, testing every claim against Scripture and against the fruit of a changed life."
        }
    ],
    "women-of-faith": [
        {
            "question": "What is the Women of Faith collection?",
            "answer": "It gathers the writing and life-stories of Christian women who prayed, suffered and dared — mothers, missionaries and mystics, from Guyon's prison cell to a freed slave's pulpit. Its keynote is Proverbs 31:30, \"Favour is deceitful, and beauty is vain: but a woman that feareth the Lord, she shall be praised\" — worth measured by devotion to God rather than by appearance or acclaim."
        },
        {
            "question": "Whose lives and writings does it include?",
            "answer": "Among them are Jeanne Guyon, the French mystic imprisoned for her teaching on prayer; Amanda Berry Smith, born a slave and become an evangelist on four continents; Susanna Wesley, mother of John and Charles; Hannah Whitall Smith, author of \"The Christian's Secret of a Happy Life\"; and Amy Carmichael, missionary to India — a range of centuries, nations and callings."
        },
        {
            "question": "Which classics by women are on the shelf?",
            "answer": "They include Jeanne Guyon's \"A Short and Easy Method of Prayer,\" Amanda Berry Smith's \"Autobiography,\" Hannah Whitall Smith's \"The Christian's Secret of a Happy Life,\" \"The God of All Comfort\" and \"The Unselfishness of God,\" and Amy Carmichael's \"Things as They Are\" — works of prayer, testimony and missionary witness that have shaped readers far beyond their own day."
        },
        {
            "question": "Who was Amanda Berry Smith?",
            "answer": "She was born into slavery in Maryland in 1837 and became one of the most widely travelled evangelists of the holiness movement, preaching across the United States, Britain, India and West Africa. A washerwoman by trade and largely self-taught, she went as an independent missionary trusting God for her needs, and her \"Autobiography\" is a classic record of faith, hardship and joy."
        },
        {
            "question": "Who was Susanna Wesley?",
            "answer": "She was the mother of John and Charles Wesley and, through them, a formative influence on the evangelical revival. Raising a large family in a country parsonage, she gave each child ordered instruction and personal spiritual attention, and her disciplined, praying household is often remembered as a seedbed of the awakening that her sons would carry across two nations."
        },
        {
            "question": "Who was Amy Carmichael?",
            "answer": "She was a missionary to south India who founded the Dohnavur Fellowship and gave her life to rescuing children from temple servitude. Her book \"Things as They Are\" told the hard truth of the mission field when readers preferred romance, and \"If\" distilled her searching vision of Calvary love — the cost of caring for others as Christ cares."
        },
        {
            "question": "Why gather a shelf of women's writing?",
            "answer": "Because the faith of these women — their prayer, endurance and daring — has shaped the church as surely as any preacher's, and their voices are worth hearing together. From the mystic's cell to the mission compound to the family hearth, they show the life of Proverbs 31:30 lived out across centuries and continents: a worth grounded in the fear of the Lord."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Hannah Whitall Smith's \"The Christian's Secret of a Happy Life\" is a warm and accessible starting point on the life of trust; Amanda Berry Smith's \"Autobiography\" offers gripping testimony; and Amy Carmichael's \"Things as They Are\" carries the honest cost of the mission field for those ready to be stirred. Together they open the shelf's range from settled peace to costly devotion."
        }
    ],
    "soar-like-the-eagle": [
        {
            "question": "What is the Soar Like the Eagle collection?",
            "answer": "It gathers the Christian classics on waiting for God and the renewal of strength — books for the weary soul that has run to the end of its own resources. The shelf takes as its keynote the promise of Isaiah 40:31, that they who wait upon the Lord \"shall mount up with wings as eagles,\" and ranges from Andrew Murray's month of readings on waiting to Hannah Whitall Smith on the rest of a life of full trust."
        },
        {
            "question": "Where should a beginner start?",
            "answer": "Andrew Murray's \"Waiting on God\" is the natural first step — thirty-one short readings that teach the habit a day at a time. From there, Hannah Whitall Smith's \"The Christian's Secret of a Happy Life\" and \"The God of All Comfort\" show what a rested, trusting life looks like, and George Müller's \"The Life of Trust\" gives it feet in a record of decades of prayers answered."
        },
        {
            "question": "What does it mean to \"wait on the Lord\"?",
            "answer": "It is not idle passivity but an active, expectant dependence — turning from our own strained effort to draw strength from God himself. The writers here treat waiting as the secret of endurance: the reason some run and grow weary while others mount up as eagles is not greater willpower but a deeper reliance on the One who \"giveth power to the faint.\""
        },
        {
            "question": "Which authors are in this collection?",
            "answer": "The shelf draws together Andrew Murray, Hannah Whitall Smith, George Müller, F. B. Meyer and D. L. Moody, among others — a spread of Reformed and Keswick, Victorian and modern voices. What unites such different writers is a single conviction: that the tired Christian's help is not in trying harder but in waiting on God, who renews the strength of those who hope in him."
        },
        {
            "question": "Is this shelf only for seasons of burnout?",
            "answer": "It speaks first to the weary — but the life of waiting is meant for every day, not only for the moment strength gives out. The daily-reading books here, like D. L. Moody's \"Thoughts for the Quiet Hour,\" build the quiet, God-ward habit in ordinary time, so that strength is already being renewed before the hard day comes."
        },
        {
            "question": "Why read these older books on waiting today?",
            "answer": "Because the soul's weariness has not changed, and these writers faced it honestly — the dryness, the delay, and the temptation to strive in our own power. Tested across generations, their counsel is practical rather than sentimental, and it points past technique to the God who promises that those who wait upon him \"shall run, and not be weary; and they shall walk, and not faint.\""
        }
    ],
    "deeper-life": [
        {
            "question": "What is The Deeper Life collection about?",
            "answer": "It gathers books on holiness, surrender, and the abundant life hidden with Christ — works for the believer who wants to go further in than conversion, past the first steps into the fullness of the Christian life. Its keynote is Colossians 3:3, \"For ye are dead, and your life is hid with Christ in God\": the deeper life is presented not as an achievement to be won but as a hiddenness already secured in Christ, to be entered by faith."
        },
        {
            "question": "Which classic works does it include?",
            "answer": "Among them are Andrew Murray's \"Humility\" and \"The Way into the Holiest,\" Bernard of Clairvaux's \"On Loving God,\" Hannah Whitall Smith's \"The Christian's Secret of a Happy Life,\" and Andrew Murray's \"Holy in Christ\" — a spread across centuries and traditions united by a single concern: the life of God lived out from within the believer."
        },
        {
            "question": "What does the shelf mean by surrender?",
            "answer": "The yielding of the whole self to God as the doorway to the deeper life — not striving to become holy by effort but abandoning oneself to Christ so that He may live His life through the believer. It is the note struck across the collection, from Murray's insistence on humility as the root to Nee's account of the Christian life as Christ's own life reproduced in us."
        },
        {
            "question": "What is the \"abundant life\" these writers describe?",
            "answer": "Not an intenser version of religious effort but Christ living His own life through the believer, so that holiness becomes a gift received rather than a height climbed. Andrew Murray's \"The Master's Indwelling\" and \"Holy in Christ\" are the shelf's fullest treatment — that the ordinary birthright of every Christian is not endless struggle but Christ Himself lived out from within."
        },
        {
            "question": "Why is humility so central here?",
            "answer": "Because these writers agree that pride is the great obstacle to the deeper life and humility its root. Andrew Murray's little book on the subject argues that humility is not one virtue among many but the ground in which all the others grow — the emptying of self that alone makes room for the fullness of God. Without it, the deeper life is sought in vain."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Hannah Whitall Smith's \"The Christian's Secret of a Happy Life\" is a warm and accessible entry into the life of trust; Andrew Murray's \"Humility\" goes to the root; and Andrew Murray's \"The Master's Indwelling\" sets out the whole mechanism — how surrender and the indwelling Spirit make the abundant life a reality rather than a hope."
        },
        {
            "question": "Is this a \"second blessing\" teaching?",
            "answer": "The shelf holds the classic holiness and Keswick stream, but read at its best it points not to a single later crisis that lifts a believer onto a permanently higher plane so much as to a continual return to Christ and daily abiding in Him. The emphasis falls on dependence and surrender kept up over a lifetime rather than on one decisive experience held ever after."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because the gap between knowing about God and actually abiding in Him is perennial, and few writers have mapped the way across it so faithfully. Tested over generations, these works speak to the Christian who has believed the gospel and still longs for more — and they answer that longing not with a technique but with a Person, the Christ in whom the believer's life is already hidden."
        }
    ],
    "grace-and-comfort": [
        {
            "question": "What is the Grace & Comfort collection about?",
            "answer": "It gathers books on the unfailing grace of God and His comfort in every trial — good news for the weary, the failing, and the afflicted. Its keynote is 2 Corinthians 12:9, \"My grace is sufficient for thee: for my strength is made perfect in weakness\": the shelf's whole burden is that grace is not earned by the strong but given to the weak, and that God's comfort meets His people precisely at the point of their need."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are Spurgeon's \"All of Grace,\" Hannah Whitall Smith's \"The God of All Comfort\" and \"The Unselfishness of God,\" Andrew Murray's \"The Way to God,\" and Thomas Watson's \"All Things for Good\" — works written to steady the anxious and lift the discouraged with the plain assurance of grace."
        },
        {
            "question": "What does the shelf teach about grace?",
            "answer": "That it is all of God and none of us — that God justifies the ungodly, and that salvation is a free gift received by faith, not a wage earned by improvement. Spurgeon's \"All of Grace\" is the clearest statement: if any part of salvation depended on the reader's worthiness, the reader would be lost, which is precisely why grace must be free from first to last."
        },
        {
            "question": "What does it offer the suffering and the weary?",
            "answer": "Comfort that is honest rather than sentimental. Thomas Watson's \"All Things for Good\" — written the year after he was ejected from his living — argues from Romans 8:28 that the very providences which seem to wreck a life are, in God's hands, working together for the believer's good, like poisons tempered by an apothecary's skill into a sovereign medicine."
        },
        {
            "question": "What does 2 Corinthians 12:9 mean for these books?",
            "answer": "\"My grace is sufficient for thee: for my strength is made perfect in weakness\" is the shelf's promise that God's grace does not wait for us to be strong but is proved most fully where we are weakest. It reframes affliction and failure not as evidence of God's absence but as the very place His sustaining grace is displayed."
        },
        {
            "question": "Who was Hannah Whitall Smith, and what does she add?",
            "answer": "A nineteenth-century American Quaker writer whose \"The God of All Comfort\" and \"The Unselfishness of God\" turn again and again to the character of God as the ground of a settled peace. Her counsel to the anxious is to look away from their own frames and feelings to the unchanging goodness of the God who loves them — a happiness rooted not in circumstances but in Him."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Spurgeon's \"All of Grace\" is the place to start for the free offer of the gospel; Hannah Whitall Smith's \"The God of All Comfort\" for the weary heart; and Thomas Watson's \"All Things for Good\" for anyone facing a providence they cannot understand. Together they move from the grace that saves to the grace that sustains."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because weakness, weariness, and grief are not solved but only sharpened by a religion of effort, and these writers offer the opposite — a grace that meets the reader exactly where strength runs out. Tested by their own authors' hard losses, they press one message on the discouraged: that God's grace is sufficient, and His comfort real, in every trial."
        }
    ],
    "revival-and-missions": [
        {
            "question": "What is the Revival & Missions collection about?",
            "answer": "It gathers the lives poured out for the gospel and the seasons of awakening God has sent — fuel for a burning heart. Its keynote is Habakkuk 3:2, \"O Lord, revive thy work in the midst of the years\": the shelf holds both the prayer for revival and the record of what it costs and produces, in the diaries of missionaries and the lectures of revivalists."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are Charles Finney's \"Revival Lectures,\" \"The Life and Diary of David Brainerd,\" Amy Carmichael's \"Things as They Are,\" the journal of an expedition up the Niger, Amanda Berry Smith's autobiography (\"A Brand Plucked from the Fire\"), and collections of the lives of men and women who gave everything for the gospel."
        },
        {
            "question": "What does the shelf teach about revival?",
            "answer": "That it is God's work to send — \"revive thy work\" — yet sought through prayer, humbling, and the plain preaching of the gospel. Finney's \"Revival Lectures\" argue that revival follows the right use of God-given means, while Brainerd's diary shows the hidden intercession behind an awakening; together they hold the mystery and the labour side by side."
        },
        {
            "question": "What is David Brainerd's place here?",
            "answer": "\"The Life and Diary of David Brainerd,\" published by Jonathan Edwards, is one of the most influential missionary memoirs ever written — the record of a young man who prayed to exhaustion among the Native peoples of colonial America and saw, shortly before his early death, a remarkable awakening at Crossweeksung. It has sent more people to the mission field than the biographies of a hundred famous preachers."
        },
        {
            "question": "What kind of missionary lives does it hold?",
            "answer": "Costly ones, told plainly. Amy Carmichael's \"Things as They Are\" refused to romanticise the mission field for readers who preferred a prettier picture; Amanda Berry Smith's autobiography records a freed slave's evangelism across four continents; and the collections of those who \"gave everything\" gather many such lives — poured out, often unheralded, for the sake of the gospel among the unreached."
        },
        {
            "question": "What does Habakkuk 3:2 mean for the shelf?",
            "answer": "\"O Lord, revive thy work in the midst of the years, in the midst of the years make known\" is the prayer under the whole collection — a cry that God would do again, in the reader's own dry season, what He has done before. It sets revival not as something the church manufactures but as something it begs for, and it ties the books of awakening to the books of mission as one work."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Brainerd's diary is the classic entry, both moving and searching; Finney's \"Revival Lectures\" set out the case that revival can be prayed and worked toward; and Amy Carmichael's \"Things as They Are\" gives the honest cost of the mission field. Together they stir the heart and count the price at once."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because a burning heart is kindled less by argument than by example, and these are the examples — men and women who staked everything on the gospel, and seasons when God came down in power. They answer the reader's own coldness not with a technique but with a summons: to pray \"revive thy work,\" and to give what cannot be kept for what cannot be lost."
        }
    ],
    "faith-and-guidance": [
        {
            "question": "What is the Faith & Guidance collection about?",
            "answer": "It gathers books on trusting God for daily bread, direction, and every promise — the life of walking by faith and not by sight. Its keynote is Proverbs 3:6, \"In all thy ways acknowledge him, and he shall direct thy paths\": the shelf's burden is that the God who guides is to be trusted for the next step and the daily need alike, and that faith is the settled posture of the whole life, not an occasional act."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are F. B. Meyer's \"The Secret of Guidance,\" George Müller's \"The Life of Trust,\" A. B. Simpson's \"Days of Heaven Upon Earth,\" Spurgeon's \"Morning by Morning\" and \"Evening by Evening,\" F. B. Meyer's \"Our Daily Walk,\" and Andrew Murray's \"Waiting on God\" — daily readings and treatises alike on the trusting, guided life."
        },
        {
            "question": "What does the shelf teach about guidance?",
            "answer": "That God guides those who acknowledge Him in all their ways, and that His leading is found less in signs than in a heart kept near and obedient. F. B. Meyer's \"The Secret of Guidance\" is the shelf's fullest treatment: God's facts laid like a foundation, faith resting on them, and feelings following in God's own time — the temper of trust rather than a technique for extracting instructions."
        },
        {
            "question": "What is George Müller's contribution?",
            "answer": "\"The Life of Trust\" is the record of a man who ran orphanages for thousands of children without ever asking a human being for money — praying in the day's needs and writing down how God met them, again and again, often at the last hour. It is the shelf's great case study in trusting God for daily bread, and it shaped later missionaries who staked their own work on the same God."
        },
        {
            "question": "What are the daily-reading books here?",
            "answer": "Spurgeon's \"Morning by Morning\" and \"Evening by Evening,\" A. B. Simpson's \"Days of Heaven Upon Earth,\" and F. B. Meyer's \"Our Daily Walk\" are devotional companions built for a portion each day — short, Scripture-anchored readings meant to feed the trusting life through the ordinary rhythm of morning and evening rather than in a single sitting."
        },
        {
            "question": "What does Proverbs 3:6 mean for the shelf?",
            "answer": "\"In all thy ways acknowledge him, and he shall direct thy paths\" is the promise under the whole collection — that guidance is bound to trust, and that the believer's part is to acknowledge God in everything, leaving the directing to Him. It ties the books of daily devotion to the books of faith as one life: acknowledging God each day, and being led."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "F. B. Meyer's \"The Secret of Guidance\" is the natural starting point for anyone anxious about God's will; George Müller's \"The Life of Trust\" builds confidence that God provides; and Spurgeon's \"Morning by Morning\" offers a daily companion to keep the heart near. Together they teach both the doctrine and the daily practice of walking by faith."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because anxiety about provision and direction is perennial, and these writers answer it not with a formula but with a God who can be trusted for the next step. Tested in orphanages and mission fields and ordinary parishes, they press one counsel on the worried: acknowledge God in all your ways, rest on His promises, and let Him direct your paths."
        }
    ],
    "the-gospel-call": [
        {
            "question": "What is The Gospel Call collection about?",
            "answer": "It gathers the oldest invitation there is — come, repent, believe — in preachers pleading with the unconverted and in the testimony of grace found by the chief of sinners. Its keynote is 2 Corinthians 5:20, \"We pray you in Christ's stead, be ye reconciled to God\": the shelf is aimed squarely at the reader who is not yet a Christian, or who longs to be and does not know where to begin."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are Richard Baxter's \"A Call to the Unconverted,\" Spurgeon's \"Around the Wicket Gate,\" John Bunyan's \"Grace Abounding to the Chief of Sinners,\" and R. A. Torrey's \"How to Bring Men to Christ\" — books that press the gospel invitation home and show grace laying hold of real, resisting sinners."
        },
        {
            "question": "What does 2 Corinthians 5:20 mean for the shelf?",
            "answer": "\"We pray you in Christ's stead, be ye reconciled to God\" is the note of the whole collection — the gospel not merely explained but pleaded, God Himself entreating sinners through His preachers. It sets the tone: these are not detached treatises but appeals, addressed to the reader as one who still needs to come."
        },
        {
            "question": "What is Bunyan's Grace Abounding?",
            "answer": "John Bunyan's account of his own conversion — the years of terror, doubt, and half-heard verses that ran before \"The Pilgrim's Progress.\" Unsparing about despair, it is one of the first books in English to describe an ordinary man's inner life from the inside, and it stands on the shelf as the testimony of grace found by one who reckoned himself the chief of sinners."
        },
        {
            "question": "What is Baxter's A Call to the Unconverted?",
            "answer": "Richard Baxter's earnest, tender pleading with those who have not yet turned to God — a book written, he said, as a dying man to dying men, urging the unconverted not to put off the one decision that matters. It is among the most direct of the shelf's appeals, and it moved many in its own century and long after to come to Christ."
        },
        {
            "question": "What does the shelf teach about conversion?",
            "answer": "That it is the free gift of God, received by repentance and faith, and that the invitation is genuinely open to all — the vilest sinner not excepted. Bunyan's own story proves it from the inside; Baxter and Spurgeon press it from the pulpit; and Torrey's \"How to Bring Men to Christ\" equips the reader to carry the same invitation to others."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Spurgeon's \"Around the Wicket Gate\" and Baxter's \"A Call to the Unconverted\" are the plainest entries for the seeker; Bunyan's \"Grace Abounding\" is the great testimony of grace laying hold of a despairing man; and Torrey's \"How to Bring Men to Christ\" is for the believer who wants to point others to the same door."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because the oldest invitation is still open, and these writers issue it with a warmth and urgency that later ages rarely match. Whether the reader is seeking, doubting, or wanting to bring someone else, the shelf presses one thing: that God entreats sinners to be reconciled to Him, and that grace has laid hold of worse cases than yours."
        }
    ],
    "enduring-classics": [
        {
            "question": "What is The Enduring Classics collection about?",
            "answer": "It gathers the books that have walked with pilgrims for centuries — Augustine's confession, Bunyan's dream, the counsel of Thomas à Kempis — the old paths that are still good. Its keynote is Jeremiah 6:16, \"ask for the old paths, where is the good way, and walk therein, and ye shall find rest for your souls\": the shelf commends the tested and time-worn over the merely new."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are Augustine's \"Confessions,\" the treatises of Cyprian, the first epistle of Clement, the epistles of Ignatius, Bunyan's \"The Pilgrim's Progress,\" Thomas à Kempis's \"The Imitation of Christ,\" Jonathan Edwards's \"Freedom of the Will,\" and William Law's \"A Serious Call\" — a span from the early church to the eighteenth century."
        },
        {
            "question": "What does Jeremiah 6:16 mean for the shelf?",
            "answer": "\"Stand ye in the ways, and see, and ask for the old paths, where is the good way, and walk therein\" is the collection's whole argument — that wisdom is more often found by returning to the tested roads than by chasing novelty. It sets these classics not as museum pieces but as the good way still worth walking, promising rest to the soul that does."
        },
        {
            "question": "What is Augustine's Confessions?",
            "answer": "Written around 397, it is the first true autobiography in Western literature and still the most searching — Augustine telling his own story back to God as one long prayer, from a boyhood theft to the garden in Milan where his life turned. Its opening line has never been improved upon: that our heart is restless until it rests in God, which is the note the whole shelf sounds."
        },
        {
            "question": "What is The Imitation of Christ?",
            "answer": "Written in the 1420s and, after the Bible, the most widely read Christian book ever, Thomas à Kempis's four short books of counsel call the reader away from the noise of opinion and ambition into the inner life — humility, patience, silence, and a friendship with Christ that outlasts every consolation. It is a classic precisely because its sentences still read as though written this morning."
        },
        {
            "question": "What voices from the early church are here?",
            "answer": "The collection reaches back to the first Christian centuries with Clement of Rome's letter to Corinth (the earliest Christian writing outside the New Testament), the seven urgent letters Ignatius of Antioch wrote on his way to the arena, and the treatises of Cyprian of Carthage — the church, in its earliest generations, learning to live out the gospel and pass it on."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Bunyan's \"The Pilgrim's Progress\" is the most accessible entry, carrying the whole of Christian experience in story form; Augustine's \"Confessions\" rewards the reader who suspects their own motives; and \"The Imitation of Christ\" is best taken slowly, a short chapter at a time, as it was written to be."
        },
        {
            "question": "Why read these old books today?",
            "answer": "Because a book that has fed pilgrims for centuries has been tested in a way no new book can be, and these have not lost their power to search and steady the reader. Jeremiah's counsel holds: the old paths are still the good way, and the soul that walks them finds rest that novelty cannot give."
        }
    ],
    "the-way-of-holiness": [
        {
            "question": "What is The Way of Holiness collection about?",
            "answer": "It gathers books on being set apart for God — the commandments searched, Christian perfection honestly pursued, and the affections of the heart tried and found true. Its keynote is Hebrews 12:14, \"Follow peace with all men, and holiness, without which no man shall see the Lord\": the shelf treats holiness not as an optional extra but as the very thing the Christian life is for."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are John Wesley's \"A Plain Account of Christian Perfection,\" the book \"Godliness,\" Jonathan Edwards's \"Religious Affections,\" and an exposition of the Ten Commandments — works that pursue holiness from several angles: the goal of perfect love, the test of true religious experience, and the searching of God's law."
        },
        {
            "question": "What does Hebrews 12:14 mean for the shelf?",
            "answer": "\"Follow peace with all men, and holiness, without which no man shall see the Lord\" is the collection's sober premise — that holiness is not negotiable, but the necessary mark of those who will see God. It sets the pursuit of holiness as the serious business of every Christian, not the special calling of a few."
        },
        {
            "question": "What is Wesley's Plain Account of Christian Perfection?",
            "answer": "John Wesley's careful statement of what he did and did not mean by Christian perfection — not sinless flawlessness or freedom from mistake, but a heart so filled with the love of God and neighbour that love reigns in it. It is the shelf's fullest treatment of holiness as the goal of the Christian life, honestly guarded against the extremes on either side."
        },
        {
            "question": "What does Edwards's Religious Affections contribute?",
            "answer": "Jonathan Edwards's great work distinguishing true religious experience from false — asking what actually marks a genuine work of God in the heart, as against mere emotion or self-deception. It brings to the shelf a searching test: that holiness shows itself not in fervour alone but in a settled bent of the affections toward God and His holiness itself."
        },
        {
            "question": "Is holiness here presented as effort or gift?",
            "answer": "The shelf holds both emphases in tension — the diligent searching of the commandments and the mortifying of sin on one side, and on the other the conviction that holiness is the fruit of God's grace working in the heart. What unites the works is the refusal to treat holiness as optional: it is pursued honestly, neither presumed nor despaired of."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Wesley's \"A Plain Account of Christian Perfection\" is the clearest statement of the goal; Edwards's \"Religious Affections\" is the searching test of whether one's own religion is true; and the exposition of the Ten Commandments grounds the whole pursuit in God's revealed law. Together they map the way of holiness from law to love."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because the call to holiness is easily softened or ignored, and these writers refuse to let it go — pressing the necessity of it, guarding against both legalism and complacency, and pointing to the love of God as its heart. They answer the reader's half-hearted religion with Hebrews' plain word: without holiness no one will see the Lord."
        }
    ],
    "the-preached-word": [
        {
            "question": "What is The Preached Word collection about?",
            "answer": "It gathers great preaching on the page — Whitefield and Wesley in full voice, Spurgeon among his farmers — and Baxter's charge to every shepherd of souls. Its keynote is Romans 10:14, \"How shall they hear without a preacher?\": the shelf honours preaching as the appointed means by which the gospel reaches the world, and it lets the reader sit under the great preachers in print."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are selected sermons of George Whitefield, John Wesley's \"Sermons on Several Occasions,\" Spurgeon's \"Talks to the Farmer\" and \"Till He Come,\" Richard Baxter's \"The Reformed Pastor,\" and expositions of the fundamental doctrines of the faith — the preached word preserved, and the theology of the preacher's own work."
        },
        {
            "question": "What does Romans 10:14 mean for the shelf?",
            "answer": "\"How shall they hear without a preacher?\" is the collection's charter — that faith comes by hearing, and hearing by the preached word, so that preaching is not a relic but God's chosen instrument. It sets these sermons and manuals not as literary specimens but as the living voice of the gospel, carried down to the reader on the page."
        },
        {
            "question": "Whose preaching does the shelf preserve?",
            "answer": "The great voices of the eighteenth-century awakening and the Victorian pulpit — George Whitefield, whose open-air preaching stirred two continents; John Wesley, whose \"Sermons on Several Occasions\" set out the doctrine of the Methodist revival; and Charles Spurgeon, whose \"Talks to the Farmer\" drew the gospel out of homely country pictures for ordinary hearers."
        },
        {
            "question": "What is Baxter's The Reformed Pastor?",
            "answer": "Richard Baxter on the work of a minister, written for a gathering of Worcestershire clergy — not sermon craft but the personal, house-by-house instruction of every family in a parish. It brings to the shelf the theology of the preacher's own calling: that a man who preaches to hundreds on Sunday and knows none of them the rest of the week has not done the job."
        },
        {
            "question": "What can a modern reader gain from old sermons?",
            "answer": "The chance to sit under preachers whose power moved thousands, and to learn from them how the gospel is proclaimed with warmth, clarity, and force. Read devotionally rather than as history, these sermons still do the work they were preached for — pressing Christ on the conscience — and Baxter's manual still searches those who preach."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Spurgeon's \"Talks to the Farmer\" is the most accessible entry, plain and vivid; Wesley's \"Sermons on Several Occasions\" set out the heart of his gospel; and Baxter's \"The Reformed Pastor\" is essential for anyone in ministry or wanting to understand it. Together they offer both the sermon and the theology of the sermon."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because preaching remains God's appointed means, and the greatest preachers repay study — not to imitate their style but to catch their seriousness about the gospel and about souls. The shelf lets the reader hear Whitefield, Wesley, and Spurgeon still, and lets Baxter still charge every shepherd with the care of the flock."
        }
    ],
    "christ-and-the-cross": [
        {
            "question": "What is the Christ & the Cross collection about?",
            "answer": "It gathers preaching on the person and work of the Saviour — the Lamb slain, the shame and triumph of the cross, the excellency of Christ, and the empty tomb. The shelf turns the reader's attention to the centre of the whole faith: who Jesus is, what He did at Calvary, and what His resurrection secured."
        },
        {
            "question": "What sermons does it include?",
            "answer": "Among them are \"Behold the Lamb of God,\" \"Christ Precious to Believers,\" \"The Excellency of Christ,\" \"How to Contemplate Christ's Holy Sufferings,\" \"The Resurrection of Jesus,\" \"The Shameful Sufferer,\" \"The Triumph of Calvary,\" and \"Worthy is the Lamb\" — messages that dwell on the sufferings and glory of the Saviour from many angles."
        },
        {
            "question": "What does it mean that Christ is the \"Lamb slain\"?",
            "answer": "It is the shelf's recurring image — Jesus as the sacrifice offered for sin, the Lamb of God who takes away the sin of the world. Sermons like \"Behold the Lamb of God\" and \"Worthy is the Lamb\" press this: that the cross was not a tragedy that befell Christ but the offering He came to make, and that the slain Lamb is now the worthy one, adored in heaven."
        },
        {
            "question": "How does the shelf hold together shame and triumph?",
            "answer": "By refusing to separate them. Titles like \"The Shameful Sufferer\" and \"The Triumph of Calvary\" set side by side the humiliation of the cross — its scandal, pain, and apparent defeat — and its hidden victory, in which sin was borne away and death undone. The cross is presented as at once the lowest shame and the highest triumph of the Saviour."
        },
        {
            "question": "What is the \"excellency of Christ\"?",
            "answer": "The surpassing worth and beauty of the Saviour Himself — the theme of the sermon \"The Excellency of Christ,\" which dwells on the wonder that in Him seemingly opposite glories meet: majesty and meekness, justice and mercy, the Lion and the Lamb. The shelf's aim is not only to explain what Christ did but to make the reader see how worthy He is."
        },
        {
            "question": "What place does the resurrection have?",
            "answer": "A central one — the empty tomb completes the shelf's account of the Saviour's work. \"The Resurrection of Jesus\" and the triumph sermons proclaim that Calvary's apparent defeat was reversed on the third day, so that the Lamb who was slain now lives, and the believer's hope rests not on a dead teacher but on a risen and reigning Lord."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "\"Behold the Lamb of God\" is a fitting entry into the meaning of the cross; \"The Excellency of Christ\" lifts the eyes to the worth of the Saviour Himself; and \"The Resurrection of Jesus\" and \"The Triumph of Calvary\" carry the reader from Good Friday's shame to Easter's victory. Together they set the whole work of Christ before the reader."
        },
        {
            "question": "Why is this the heart of the collection?",
            "answer": "Because the person and work of Christ are the centre of the whole Christian faith, and every other theme flows from them. The shelf exists to keep the reader's gaze where it belongs — on the Lamb slain and risen, the shame and triumph of the cross, and the excellency of the Saviour who is worthy of all worship."
        }
    ],
    "abiding-in-christ": [
        {
            "question": "What is the Abiding in Christ collection about?",
            "answer": "It gathers books on the branch in the Vine — union and communion with the Lord Jesus, and the life that flows from no other source than staying near Him. Its keynote is John 15:4, \"Abide in me, and I in you. As the branch cannot bear fruit of itself, except it abide in the vine; no more can ye, except ye abide in me\": the shelf's whole burden is that fruitfulness is not produced by effort but received by remaining joined to Christ."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are Andrew Murray's \"The True Vine,\" \"Holy in Christ,\" \"Absolute Surrender,\" and \"The Master's Indwelling,\" A. B. Simpson's \"Jesus Himself,\" Bernard of Clairvaux's \"On Loving God,\" and Spurgeon's \"Union and Communion\" — works that dwell on the believer's living union with Christ and the communion that flows from it."
        },
        {
            "question": "What does John 15:4 mean for the shelf?",
            "answer": "\"Abide in me, and I in you... the branch cannot bear fruit of itself, except it abide in the vine\" is the image under the whole collection — that the Christian is a branch whose only life and fruit come from remaining in the Vine. It sets abiding, not striving, as the secret of the fruitful life, and makes nearness to Christ the one thing needful."
        },
        {
            "question": "What does Andrew Murray teach about the Vine?",
            "answer": "In \"The True Vine\" Murray takes Christ's own image and presses it home day by day: that the branch's whole business is to abide, and the Vine's business is to bear the fruit through it. His counsel to the anxious believer is not to work harder at holiness but to stay in Christ, trusting that the life which flows from Him will produce what no effort can."
        },
        {
            "question": "What is the difference between union and communion here?",
            "answer": "The shelf holds both: union, the settled fact that the believer is joined to Christ once for all, and communion, the daily, felt fellowship that grows or wanes with the believer's abiding. Spurgeon's \"Union and Communion\" distinguishes them — that the union can never be broken, while the communion must be kept fresh by staying near the Lord."
        },
        {
            "question": "What is the \"indwelling\" the shelf speaks of?",
            "answer": "The reality of Christ living in the believer by His Spirit, so that the Christian life is not imitation from without but Christ's own life lived from within. Andrew Murray's \"The Master's Indwelling\" and A. B. Simpson's \"Jesus Himself\" dwell on this — that the secret of holiness and rest is the indwelling presence of the Lord Himself, received and yielded to by faith."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Andrew Murray's \"The True Vine\" is the natural entry, a gentle daily unfolding of John 15; \"Absolute Surrender\" presses the yielding that abiding requires; and Simpson's \"Jesus Himself\" turns the reader from seeking experiences to resting in the Person of Christ. Together they teach both the doctrine and the practice of staying near."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because the temptation to live the Christian life by effort, at a distance from Christ, is perennial, and these writers keep returning the reader to the Vine. They answer weariness and barrenness not with a harder push but with a Person — the Christ in whom the believer must abide if he is to bear any fruit at all."
        }
    ],
    "voices-of-the-early-church": [
        {
            "question": "What is the Voices of the Early Church collection about?",
            "answer": "It gathers the faith of the first centuries in its own words — Augustine's heart laid bare, Athanasius on the Word made flesh, and the letters of martyrs and shepherds. Its keynote is Hebrews 12:1, \"We also are compassed about with so great a cloud of witnesses\": the shelf lets the reader hear the church's earliest generations speak for themselves, as witnesses whose testimony still surrounds and steadies those who come after."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are Augustine's \"Confessions\" and \"Enchiridion,\" Athanasius's \"On the Incarnation,\" Athanasius's \"Life of Antony,\" John Chrysostom's \"On the Priesthood,\" the treatises of Cyprian of Carthage, the first epistle of Clement of Rome, and the epistles of Ignatius of Antioch — a span from the apostolic age to the great fourth-century fathers."
        },
        {
            "question": "What does Athanasius's On the Incarnation teach?",
            "answer": "Written by Athanasius as a young man, it sets out why God became man, in the line the Greek church has never stopped quoting: \"He was made man that we might be made God\" — meaning that God came the whole way down, took a real body, and died a real death so that creatures might share the life of God. It brings to the shelf the church's foundational confession that Jesus Christ is truly God."
        },
        {
            "question": "What early letters are preserved here?",
            "answer": "The earliest voices of all: Clement of Rome's letter to Corinth — the earliest Christian writing outside the New Testament — and the seven urgent letters Ignatius of Antioch wrote on his way to be killed in the arena at Rome. They let the reader hear a pastor in the generation after the apostles, and a bishop weeks from martyrdom, speaking to churches they loved."
        },
        {
            "question": "What does Hebrews 12:1 mean for the shelf?",
            "answer": "\"We also are compassed about with so great a cloud of witnesses\" frames the whole collection — the early Christians not as distant historical figures but as witnesses whose faith surrounds the reader and calls him on. It sets these ancient texts as living testimony, part of the great company whose example encourages those still running the race."
        },
        {
            "question": "What does the shelf preserve of the desert and the pulpit?",
            "answer": "Athanasius's \"Life of Antony\" carries the monastic ideal of the Egyptian desert — the book that reached a garden in Milan and helped turn Augustine; and Chrysostom's \"On the Priesthood\" is the early church's most searching book on pastoral ministry. Together with Cyprian's treatises, they show the early church at prayer, in the desert, and in the care of souls."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Augustine's \"Confessions\" is the most accessible and moving entry, a soul's story told back to God; Athanasius's \"On the Incarnation\" is short and foundational; and Clement's and Ignatius's letters give the plain voice of the very first generations. Together they open the world of the early church from the inside."
        },
        {
            "question": "Why read these ancient voices today?",
            "answer": "Because a faith that has been believed for two thousand years is best understood by hearing its earliest witnesses, and these writers faced the same questions — about Christ, the church, suffering, and prayer — with a directness later ages rarely match. Hebrews' image holds: they are a cloud of witnesses, and their testimony still surrounds and strengthens the reader."
        }
    ],
    "day-by-day": [
        {
            "question": "What is the Day by Day collection about?",
            "answer": "It gathers readings for the morning and the evening — daily bread to keep the soul fed — from Spurgeon's beloved classics to the books of the quiet hour. Its keynote is Lamentations 3:22–23, \"his compassions fail not. They are new every morning\": the shelf is built for the daily rhythm of devotion, a portion each day rather than a book read at a sitting."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are Spurgeon's \"Morning by Morning\" and \"Evening by Evening\" and \"Gleanings among the Sheaves,\" \"Thoughts for the Quiet Hour,\" F. B. Meyer's \"Our Daily Walk,\" A. B. Simpson's \"Days of Heaven Upon Earth,\" and Spurgeon's \"The Cheque Book of the Bank of Faith\" — devotional companions built to be taken a day at a time."
        },
        {
            "question": "What does Lamentations 3:22–23 mean for the shelf?",
            "answer": "\"It is of the Lord's mercies that we are not consumed, because his compassions fail not. They are new every morning: great is thy faithfulness\" is the promise under the whole collection — that God's mercy is renewed daily, and so the soul is fed daily. It sets the pattern of morning-and-evening reading as a way of meeting fresh mercy each day."
        },
        {
            "question": "What are Spurgeon's Morning by Morning and Evening by Evening?",
            "answer": "Two of the most beloved daily devotionals ever written — a short, Scripture-anchored reading for each morning and each evening of the year, drawn from the warm, Christ-centred heart of Spurgeon's preaching. They have kept company with generations of Christians at the beginning and end of the day, feeding the soul in the small, faithful portions the shelf is built around."
        },
        {
            "question": "What is The Cheque Book of the Bank of Faith?",
            "answer": "Spurgeon's daily book of God's promises, treating each one as a cheque to be endorsed by faith and presented at the bank of heaven — a promise for every day, with a few lines pressing the reader to take God at His word. It brings to the shelf the note of confident, promise-claiming prayer, one day at a time."
        },
        {
            "question": "Why read a portion each day rather than all at once?",
            "answer": "Because these books were made for it, and the soul is fed the way the body is — regularly, in daily portions, not in occasional feasts. Lamentations' word shapes the practice: mercy is new every morning, so the reading is renewed every morning too, keeping the heart near God through the ordinary rhythm of the day."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Spurgeon's \"Morning by Morning\" is the classic entry for the start of the day, \"Evening by Evening\" for its close; \"Thoughts for the Quiet Hour\" gathers brief gems for a pause; and \"The Cheque Book of the Bank of Faith\" turns each day toward a promise of God. Any of them can simply be begun on today's date."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because a soul needs feeding daily, and busy readers rarely keep up a long book but can keep a short daily reading. These companions have proved themselves over generations for exactly that — a portion of green pasture each morning and evening, keeping the great faithfulness of God fresh in the reader's memory through every ordinary day."
        }
    ],
    "contemporary-voices": [
        {
            "question": "What is the Contemporary Voices collection about?",
            "answer": "It gathers present-day teachers who write for East Africa and beyond — living guides on the old road, meeting the disciple where the questions are now. Its keynote is Psalm 145:4, \"One generation shall praise thy works to another, and shall declare thy mighty acts\": the shelf carries the same gospel the classics teach, spoken freshly into the present by voices of this generation."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are \"Feasting at the Table,\" \"Stepping Stones,\" \"The Key in My Hand,\" \"Soar Like the Eagle,\" \"He Holds My Tomorrows,\" and \"Prayer, the Pulse of Life\" — contemporary books written to disciple readers in their own moment, especially across East Africa, in continuity with the great classics on the neighbouring shelves."
        },
        {
            "question": "What does Psalm 145:4 mean for the shelf?",
            "answer": "\"One generation shall praise thy works to another, and shall declare thy mighty acts\" is the collection's charter — that the faith is handed on, generation to generation, and that each generation must declare God's works in its own voice. It sets these living writers as the newest link in a long chain, carrying forward what the fathers received."
        },
        {
            "question": "How do these books relate to the classics?",
            "answer": "They walk the same old road with living feet. Where the classics speak in the idiom of their own centuries, these contemporary voices meet today's disciple where the questions are now — the same gospel of grace, prayer, and the deeper life, translated into the concerns and language of the present, especially for readers in East Africa and the wider church."
        },
        {
            "question": "What themes do the contemporary books address?",
            "answer": "The enduring ones, freshly put: prayer as the pulse of the Christian life, trusting God with an unknown future (\"He Holds My Tomorrows\"), growing and rising in faith (\"Soar Like the Eagle\"), and the ordinary steps of discipleship (\"Stepping Stones\"). They meet the reader in present-day life while keeping the shelf continuous with the classics."
        },
        {
            "question": "Who are these books written for?",
            "answer": "Especially for readers in East Africa and the wider church today — disciples who love the old paths but need a guide speaking into their own moment. The shelf exists to show that the road walked by Augustine and Murray and Spurgeon still has living guides, and that the mighty acts of God are still being declared, generation to generation."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "\"Prayer, the Pulse of Life\" is a fitting entry for the heart of the Christian life; \"He Holds My Tomorrows\" for anyone anxious about the future; and \"Stepping Stones\" for the ordinary path of growth. Any of them meets the present-day reader on familiar ground while pointing to the same Christ the classics preach."
        },
        {
            "question": "Why read contemporary voices alongside the classics?",
            "answer": "Because the old truth needs a living voice in every age, and a guide who shares the reader's own moment can carry the classics' wisdom across the distance of centuries. Psalm 145:4 holds: one generation declares God's works to the next — and these writers are doing exactly that, on the road the fathers walked before them."
        }
    ],
    "the-inner-life": [
        {
            "question": "What is The Inner Life collection about?",
            "answer": "It gathers the books that turn the soul inward — à Kempis, Law, and Guyon, the love of God and the shut door of the secret place, the soul alone with Him. Its keynote is Matthew 6:6, \"when thou prayest, enter into thy closet, and when thou hast shut thy door, pray to thy Father which is in secret\": the shelf commends the hidden, interior life of communion over religion lived only in public."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are Thomas à Kempis's \"The Imitation of Christ,\" William Law's \"A Serious Call to a Devout and Holy Life,\" Jeanne Guyon's \"A Short and Easy Method of Prayer,\" Bernard of Clairvaux's \"On Loving God,\" Augustine's \"Confessions,\" and Andrew Murray's \"The Inner Chamber\" — classics of the interior life across many centuries."
        },
        {
            "question": "What does Matthew 6:6 mean for the shelf?",
            "answer": "\"Enter into thy closet, and when thou hast shut thy door, pray to thy Father which is in secret\" is the image under the whole collection — the shut door, the secret place, the soul alone with God. It sets the inner life not as an escape from duty but as its hidden root: the private communion from which all genuine public devotion flows."
        },
        {
            "question": "What is The Imitation of Christ's place here?",
            "answer": "Thomas à Kempis's four short books of counsel are the shelf's classic guide to the interior life — calling the reader away from the noise of opinion and ambition into humility, silence, and a friendship with Christ that outlasts every consolation. Its single theme, the gap between knowing about God and following Him, is the inner life's whole concern."
        },
        {
            "question": "What does Guyon add on prayer of the heart?",
            "answer": "Jeanne Guyon's \"A Short and Easy Method of Prayer\" teaches that prayer is less a labour of the mind than an application of the heart — a simple, continual turning of the soul toward God, open to the poor and unlettered as much as to the scholar. It brings to the shelf the contemplative stream: prayer as being with God rather than performing before Him."
        },
        {
            "question": "What does the shelf mean by the \"secret place\"?",
            "answer": "The hidden life of private communion — the closet with the door shut, where the soul is alone with God unseen by anyone. Andrew Murray's \"The Inner Chamber\" is its fullest treatment: that the strength of all public and outward religion is drawn from this unseen, personal fellowship, and that a Christian is, in secret, what he truly is."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Thomas à Kempis's \"The Imitation of Christ\" is the classic entry, best taken a short chapter at a time; Andrew Murray's \"The Inner Chamber\" draws the reader into the secret place of prayer; and Guyon's \"A Short and Easy Method\" opens the contemplative turning of the heart. Together they lead the soul inward, toward God alone."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because a religion that is all activity and no interior life runs dry, and these writers keep pointing the reader to the shut door and the secret place. They answer the noise and hurry of modern devotion with the oldest counsel there is: enter into your closet, shut the door, and be alone with your Father who is in secret."
        }
    ],
    "the-great-awakening": [
        {
            "question": "What is The Great Awakening collection about?",
            "answer": "It gathers the preaching that shook two continents — Whitefield and Wesley in the open air, Edwards among his people, Finney on revival — and the doctrine beneath the flame. Its keynote is Psalm 85:6, \"Wilt thou not revive us again: that thy people may rejoice in thee?\": the shelf holds both the fire of the eighteenth-century awakenings and the theology that gave them substance."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are Charles Finney's \"Revival Lectures,\" John Wesley's \"Sermons on Several Occasions,\" selected sermons of George Whitefield and Jonathan Edwards, Wesley's \"A Plain Account of Christian Perfection,\" and Edwards's \"Freedom of the Will\" and \"Religious Affections\" — the preaching of the awakening and the doctrine underneath it."
        },
        {
            "question": "What does Psalm 85:6 mean for the shelf?",
            "answer": "\"Wilt thou not revive us again: that thy people may rejoice in thee?\" is the prayer under the whole collection — the cry that lay behind the awakenings and lies behind every longing for revival since. It sets these sermons and treatises not merely as history but as fuel for the same prayer, that God would revive His people again."
        },
        {
            "question": "Who preached these awakenings?",
            "answer": "The great voices of the eighteenth century: George Whitefield, whose open-air preaching drew vast crowds on both sides of the Atlantic; John Wesley, whose sermons set out the doctrine of the Methodist revival; and Jonathan Edwards, whose preaching in New England helped kindle the awakening and whose \"Sinners in the Hands of an Angry God\" remains its most famous sermon."
        },
        {
            "question": "What doctrine lies beneath the flame?",
            "answer": "The shelf pairs the fire with the theology that gave it weight. Edwards's \"Religious Affections\" tests true religious experience against false; his \"Freedom of the Will\" defends God's sovereignty in salvation; and Wesley's \"Plain Account of Christian Perfection\" sets out the goal of holy love. The awakening, these works insist, was no mere excitement but a work of God with real doctrine underneath it."
        },
        {
            "question": "How does this shelf relate to Revival & Missions?",
            "answer": "They are neighbours on the same theme. Where Revival & Missions gathers the diaries and lectures of those poured out for the gospel across many eras, The Great Awakening focuses on the specific eighteenth-century movement that shook Britain and America — its preachers, its sermons, and the Reformed and Wesleyan theology that shaped it."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Whitefield's and Wesley's sermons let the reader hear the awakening's own voice; Finney's \"Revival Lectures\" argue how revival may be sought; and Edwards's \"Religious Affections\" tests whether one's own religion is a true work of God. Together they carry both the flame and the doctrine beneath it."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because the church still prays \"revive us again,\" and the great awakenings show both what God has done and what it costs and produces. These preachers repay study not for their style but for their seriousness about conversion, holiness, and the sovereign work of God — and they stir the reader toward the same prayer."
        }
    ],
    "the-body-of-christ": [
        {
            "question": "What is The Body of Christ collection about?",
            "answer": "It gathers books on the church as a living whole — members of one another, joined to the Head, and the service and shepherding that flow from it. Its keynote is 1 Corinthians 12:27, \"Now ye are the body of Christ, and members in particular\": the shelf treats the church not as an institution to be managed but as a living body, each member joined to Christ and to the others."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are John Chrysostom's \"On the Priesthood,\" Richard Baxter's \"The Reformed Pastor,\" Watchman Nee's \"Separation and Service,\" and the first epistle of Clement of Rome — works on the nature of the church and the ministry that serves it."
        },
        {
            "question": "What does 1 Corinthians 12:27 mean for the shelf?",
            "answer": "\"Now ye are the body of Christ, and members in particular\" is the image under the whole collection — the church as one body with many members, each needing the others and all joined to Christ the Head. It sets the church not as a loose collection of individuals but as an organism, in which every member has a place and a service."
        },
        {
            "question": "What does the shelf teach about the church?",
            "answer": "That it is a living whole, not a human organisation — members of one another, drawing their common life from Christ. \"Separation and Service\" presses the believer's set-apart place within that body, and Clement's ancient letter to Corinth shows the same conviction at work in the earliest generation, calling a divided church back to its unity in Christ."
        },
        {
            "question": "How does the shelf connect the body and its ministry?",
            "answer": "By holding the two together: the church is a body, and its shepherds serve that body. Chrysostom's \"On the Priesthood\" and Baxter's \"The Reformed Pastor\" set out the weight and care of ministry, while \"Separation and Service\" treats the believer's own calling — so that the doctrine of the body flows naturally into the service and shepherding it requires."
        },
        {
            "question": "What does Clement's letter contribute here?",
            "answer": "Clement of Rome's first epistle, written around AD 96 to a Corinthian church that had deposed its elders, is the earliest Christian writing outside the New Testament, and its whole argument is for the unity and order of the body — humility, love, and the refusal of schism. It brings to the shelf the church's earliest voice on what it means to be one body in Christ."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Clement's letter to Corinth is the natural entry — the earliest Christian voice on the body's unity; Baxter's \"The Reformed Pastor\" shows the shepherding that serves it; and Chrysostom's \"On the Priesthood\" weighs the awe of that ministry. Together they move from the nature of the body to the care of it."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because the church is easily reduced to an institution or an individual preference, and these writers recover it as what Scripture calls it — the body of Christ, members of one another, joined to the Head. They answer both isolation and mere institutionalism with the living reality of a body in which every member belongs."
        }
    ],
    "for-those-who-lead": [
        {
            "question": "What is the For Those Who Lead collection about?",
            "answer": "It gathers a charge to shepherds and soul-winners — the pastor's care, the preacher's power in prayer, and how to bring men to Christ. Its keynote is 1 Peter 5:2, \"Feed the flock of God which is among you, taking the oversight thereof, not by constraint, but willingly\": the shelf is aimed at those who lead in the church, pressing on them the weight and the willing spirit of true oversight."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are Richard Baxter's \"The Reformed Pastor,\" John Chrysostom's \"On the Priesthood,\" E. M. Bounds's \"Power Through Prayer,\" R. A. Torrey's \"How to Bring Men to Christ,\" and expositions of the fundamental doctrines of the faith — the classic charges to ministers and soul-winners across the centuries."
        },
        {
            "question": "What does 1 Peter 5:2 mean for the shelf?",
            "answer": "\"Feed the flock of God which is among you, taking the oversight thereof, not by constraint, but willingly\" is the charge under the whole collection — that leading in the church is shepherding, undertaken not for gain or by compulsion but willingly, as under the Chief Shepherd. It sets the tone: oversight as costly care, not office or status."
        },
        {
            "question": "What does Baxter's The Reformed Pastor charge leaders with?",
            "answer": "The personal, house-by-house instruction of every family in a parish — not sermon craft but knowing and caring for each soul. Baxter's searching argument is that a man who preaches to hundreds on Sunday and knows none of them the rest of the week has not done the job, and that the minister must attend to his own soul before he can attend to a flock."
        },
        {
            "question": "What does the shelf say about the preacher and prayer?",
            "answer": "E. M. Bounds's \"Power Through Prayer\" presses the point the collection returns to: that the power of a ministry lies not in machinery or method but in praying men. \"What the Church needs,\" Bounds wrote, \"is not more machinery or better... but men whom the Holy Spirit can use — men of prayer, men mighty in prayer\" — a charge to every leader to be, first, an intercessor."
        },
        {
            "question": "What does On the Priesthood add?",
            "answer": "John Chrysostom's early-church classic is the most searching book on pastoral ministry the ancient church produced — arguing that the work is so weighty, and the soul of the man who does it so exposed, that fleeing from it may be the sanest response. It brings to the shelf a sober reckoning of the danger and dignity of leading souls."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Baxter's \"The Reformed Pastor\" is the essential charge on pastoral care; Bounds's \"Power Through Prayer\" presses the leader toward the closet before the pulpit; and Torrey's \"How to Bring Men to Christ\" equips the soul-winner. Together they set out the care, the prayer, and the aim of those who lead."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because leadership in the church is easily reduced to management or performance, and these writers recover it as shepherding under the Chief Shepherd — costly, prayerful, and personal. They make uncomfortable reading for those who lead, which is exactly what their authors intended, and they steady anyone charged with the care of souls."
        }
    ],
    "the-wesleys-and-early-methodism": [
        {
            "question": "What is The Wesleys & Early Methodism collection about?",
            "answer": "It gathers the awakening that became a movement — John Wesley's sermons and plain account, the mother who shaped him, and the fervour that followed. Its keynote is Luke 24:32, \"Did not our heart burn within us, while he talked with us by the way?\": the shelf holds the warm, heart-kindled religion of the Methodist revival and the teaching that gave it shape."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are John Wesley's \"Sermons on Several Occasions\" and \"A Plain Account of Christian Perfection,\" a life of Susanna Wesley, selected sermons of George Whitefield, and the books \"Godliness\" and \"Purity of Heart\" — the preaching, the doctrine, and the household that shaped early Methodism."
        },
        {
            "question": "What does Luke 24:32 mean for the shelf?",
            "answer": "\"Did not our heart burn within us, while he talked with us by the way, and while he opened to us the scriptures?\" is the note under the whole collection — the warmed heart of the Emmaus road, echoed in Wesley's own famous testimony that his heart was \"strangely warmed.\" It sets early Methodism as a religion of the affections as well as the understanding."
        },
        {
            "question": "What is Wesley's Plain Account of Christian Perfection?",
            "answer": "John Wesley's careful statement of the doctrine most associated with him — not sinless flawlessness but a heart so filled with the love of God and neighbour that love reigns in it. It is the shelf's fullest treatment of the goal Wesley set before the Methodists, honestly guarded against the extremes that both his critics and his followers were tempted toward."
        },
        {
            "question": "Who was Susanna Wesley, and why is she here?",
            "answer": "The mother of John and Charles Wesley, and through them a formative influence on the whole revival. Raising a large family in a country parsonage, she gave each child ordered instruction and personal spiritual attention, and her disciplined, praying household is often remembered as a seedbed of the awakening her sons would carry across two nations."
        },
        {
            "question": "What was the fervour that followed?",
            "answer": "The heart-religion that spread through the Methodist societies — field preaching to thousands, hymns sung with feeling, the pursuit of holiness and the witness of the Spirit. The shelf holds both the fire, in Wesley's and Whitefield's preaching, and the discipline, in the plain account of perfection and the books on godliness and purity of heart that guided the awakened."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "John Wesley's \"Sermons on Several Occasions\" set out the heart of his gospel; \"A Plain Account of Christian Perfection\" gives the doctrine most his own; and the life of Susanna Wesley opens the household that shaped him. Together they carry both the warmth and the substance of early Methodism."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because the Methodist revival married warm affection to serious doctrine, and both are easily lost — fervour without teaching, or teaching without fire. These writers hold them together, pressing on the reader a religion in which the heart burns and the mind is fed, kindled by the same Christ who warmed the hearts of the disciples on the Emmaus road."
        }
    ],
    "foundations-of-the-faith": [
        {
            "question": "What is the Foundations of the Faith collection about?",
            "answer": "It gathers the old doctrines, plainly held — the incarnation, the grace and will of God, the commandments, and the fundamentals once for all delivered. Its keynote is Jude 3, \"Ye should earnestly contend for the faith which was once delivered unto the saints\": the shelf sets out the settled substance of Christian belief, the things worth holding firmly and, when needed, contending for."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are \"The Fundamental Doctrines of the Christian Faith,\" Augustine's \"Enchiridion\" (his handbook of faith, hope, and love), Athanasius's \"On the Incarnation,\" Jonathan Edwards's \"Freedom of the Will,\" and an exposition of the Ten Commandments — works that state and defend the central doctrines of the faith across the centuries."
        },
        {
            "question": "What does Jude 3 mean for the shelf?",
            "answer": "\"Ye should earnestly contend for the faith which was once delivered unto the saints\" is the charge under the whole collection — that the faith is not endlessly reinvented but once for all delivered, to be held and defended. It sets these books as guardians of the settled deposit of Christian truth, not speculations but foundations."
        },
        {
            "question": "What does On the Incarnation teach about the foundations?",
            "answer": "Athanasius's little book states the church's foundational confession — that in Jesus Christ, God Himself came the whole way down, took a real body, and died a real death, \"that we might be made God.\" It grounds the whole faith on the reality of the incarnation: that what came into the world in Christ was not the best of creatures but God, and that everything else stands or falls with it."
        },
        {
            "question": "What is Augustine's Enchiridion?",
            "answer": "A handbook Augustine wrote setting out the essentials of the faith around the three great virtues — faith, hope, and love — a compact statement of Christian belief from the church's greatest Latin teacher. It brings to the shelf a doctrinal summary from one who had thought as deeply as anyone about the whole of the faith."
        },
        {
            "question": "What place do the Ten Commandments have here?",
            "answer": "The exposition of the Ten Commandments grounds the shelf's doctrine in the moral law God revealed — the enduring standard that shows what holiness requires and what sin is. It sits among the foundations because the commandments are part of the settled deposit: not abolished by grace, but fulfilled in it, and always the mirror that drives the sinner to Christ."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Athanasius's \"On the Incarnation\" is short and foundational for the person of Christ; Augustine's \"Enchiridion\" gives a compact summary of the whole faith; and \"The Fundamental Doctrines of the Christian Faith\" sets out the essentials plainly. Together they map the ground every believer stands on."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because in every age the settled faith is questioned, softened, or reinvented, and these writers hold it firmly — stating the old doctrines plainly and defending them clearly. Jude's charge still stands: to contend earnestly for the faith once delivered, and these books equip the reader to know what that faith is and why it is worth holding."
        }
    ],
    "saints-of-the-african-diaspora": [
        {
            "question": "What is the Saints of the African Diaspora collection about?",
            "answer": "It gathers the gospel carried in Black voices — Richard Allen and the freeborn preachers, the holiness women who would not be silenced, and Samuel Crowther on the Niger. Its keynote is Psalm 68:31, \"Ethiopia shall soon stretch out her hands unto God\": the shelf honours a stream of the church often overlooked, in the words of those who preached and suffered and gave themselves within it."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are Richard Allen's \"The Life Experience and Gospel Labours,\" Jarena Lee's \"Religious Experience and Journal,\" Julia Foote's \"A Brand Plucked from the Fire,\" Amanda Berry Smith's autobiography, and the journal of Samuel Crowther's expedition up the Niger — the testimonies of Black preachers, evangelists, and missionaries in their own words."
        },
        {
            "question": "Who was Richard Allen?",
            "answer": "Born a slave in Philadelphia, Richard Allen bought his freedom, became a pioneering preacher, and after the humiliation of segregated seating at St George's founded the independent Bethel church and, in 1816, the African Methodist Episcopal Church — the first fully independent Black denomination in America, of which he became the first bishop. His \"Life Experience and Gospel Labours\" tells his own story."
        },
        {
            "question": "Which women's voices does the shelf carry?",
            "answer": "The holiness women who would not be silenced: Jarena Lee, the first woman authorized to preach in the AME Church, who travelled thousands of miles proclaiming the gospel; Julia Foote, excommunicated for preaching as a woman and later the first woman ordained a deacon in the AME Zion Church; and Amanda Berry Smith, born a slave and become an evangelist across four continents."
        },
        {
            "question": "What does Psalm 68:31 mean for the shelf?",
            "answer": "\"Princes shall come out of Egypt; Ethiopia shall soon stretch out her hands unto God\" is the promise under the whole collection — long read as a pledge that Africa and its peoples would come to God. It sets these lives not as exceptions but as the fulfilment of an ancient word, and it gave hope and dignity to generations who claimed it as their own."
        },
        {
            "question": "Who was Samuel Crowther?",
            "answer": "Samuel Ajayi Crowther was a Yoruba man, enslaved as a boy and freed by a British anti-slavery squadron, who became the first African Anglican bishop and a pioneer missionary and translator on the Niger. His journal of the Niger expedition brings to the shelf the gospel carried back into Africa by an African, and the beginnings of a Christianity rooted in its own soil and languages."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Amanda Berry Smith's autobiography is a gripping testimony of faith and hardship across four continents; Richard Allen's \"Life Experience and Gospel Labours\" tells the founder's own story; and Jarena Lee's and Julia Foote's journals record women who preached against every obstacle. Together they open a stream of the church's life too often left out."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because the gospel has always been carried by more voices than the familiar histories record, and these testimonies — of freed slaves, of women forbidden the pulpit, of the first African bishop — show grace laying hold of the despised and using them mightily. Psalm 68:31 holds: Ethiopia has stretched out her hands to God, and these are the saints who proved it."
        }
    ],
    "the-grace-of-god": [
        {
            "question": "What is The Grace of God collection about?",
            "answer": "It gathers books on grace from first to last — free, sovereign, and sufficient, abounding to the chief of sinners and holding the weakest saint. Its keynote is Ephesians 2:8, \"For by grace are ye saved through faith; and that not of yourselves: it is the gift of God\": the shelf's whole burden is that salvation is God's free gift, owed to no merit of ours."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are Spurgeon's \"All of Grace,\" John Bunyan's \"Grace Abounding to the Chief of Sinners,\" Andrew Murray's \"The Way to God,\" and Thomas Watson's \"All Things for Good\" — works that set out grace as free at the start, sufficient in the trial, and faithful to the end."
        },
        {
            "question": "What does Ephesians 2:8 mean for the shelf?",
            "answer": "\"For by grace are ye saved through faith; and that not of yourselves: it is the gift of God\" is the verse under the whole collection, and the argument of its central book. It sets grace as pure gift — if any part of salvation were owed to the reader's own improvement, the reader would be lost, which is precisely why grace must be free from first to last."
        },
        {
            "question": "What is Bunyan's Grace Abounding?",
            "answer": "John Bunyan's account of his own conversion — the years of terror, doubt, and half-heard verses before \"The Pilgrim's Progress\" — subtitled \"the Chief of Sinners\" because he reckoned himself the worst case grace ever saved. It is the shelf's great inside view of grace laying hold of a despairing man, and proof that no one is beyond its reach."
        },
        {
            "question": "What does All of Grace teach?",
            "answer": "Spurgeon's \"All of Grace\" is the plainest statement on the shelf: that God justifies the ungodly, that salvation is by grace through faith and not by works, and that even repentance and faith are themselves God's gifts. Written for the seeker who fears he is too far gone, it presses one invitation — come to Christ just as you are, for grace is all of God."
        },
        {
            "question": "How does the shelf show grace in trial?",
            "answer": "Thomas Watson's \"All Things for Good\" carries grace past conversion into affliction — arguing from Romans 8:28 that the very providences which seem to wreck a life are, in God's hands, working together for the believer's good. Grace, the shelf insists, not only saves the sinner freely but holds the saint faithfully, sweetening even the bitter with inward peace."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Spurgeon's \"All of Grace\" is the place to start for the free offer of salvation; Bunyan's \"Grace Abounding\" for the testimony of grace found by the chief of sinners; and Watson's \"All Things for Good\" for grace that sustains in suffering. Together they trace grace from first to last."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because the human heart keeps trying to earn what can only be given, and these writers keep returning the reader to grace — free at the start, sufficient in the trial, faithful to the end. They answer both the despair of the sinner and the anxiety of the saint with one word: that salvation is the gift of God, and not of ourselves."
        }
    ],
    "victory-over-sin": [
        {
            "question": "What is the Victory Over Sin collection about?",
            "answer": "It gathers books on the inward fight for holiness — mortifying sin, purity of heart, the affections set in order, and the way into the holiest. Its keynote is Romans 6:14, \"For sin shall not have dominion over you: for ye are not under the law, but under grace\": the shelf holds out real victory over indwelling sin, not by law-keeping but by the grace that reigns in the believer."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are John Owen's \"The Mortification of Sin,\" Jonathan Edwards's \"Religious Affections,\" \"Purity of Heart,\" John Wesley's \"A Plain Account of Christian Perfection,\" Andrew Murray's \"Holy in Christ,\" and \"The Way into the Holiest\" — works on the daily war against sin and the pursuit of a clean heart."
        },
        {
            "question": "What does Romans 6:14 mean for the shelf?",
            "answer": "\"For sin shall not have dominion over you: for ye are not under the law, but under grace\" is the promise under the whole collection — that the Christian is not doomed to be ruled by sin, because grace has broken its dominion. It sets the fight for holiness not as a hopeless struggle under law but as a real victory made possible under grace."
        },
        {
            "question": "What does Owen's Mortification of Sin teach?",
            "answer": "John Owen's classic handbook on the daily, deliberate war against indwelling sin presses one charge in nine words: \"be killing sin, or it will be killing you.\" Sin is never dormant, he warns, and must be put to death daily by the power of the Spirit, not merely managed — and the believer who ceases the work will find the work being done on him instead."
        },
        {
            "question": "What does the shelf mean by purity of heart?",
            "answer": "The setting-right of the inner affections, so that the heart itself is cleansed and not merely the outward life restrained. Edwards's \"Religious Affections\" tests what a truly changed heart looks like, and \"Purity of Heart\" and Wesley's \"Plain Account\" hold out the goal of a heart so filled with the love of God that sin loses its grip from the inside out."
        },
        {
            "question": "Is victory here by effort or by grace?",
            "answer": "Both are held together, but grace is the ground. The shelf calls for real, deliberate effort — mortifying sin, watching the heart, ordering the affections — yet insists that the power for it comes from union with Christ and the reign of grace, not from the believer's own strength. Andrew Murray's \"Holy in Christ\" and \"The Way into the Holiest\" locate the whole fight in Christ Himself."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "John Owen's \"The Mortification of Sin\" is the classic entry, searching and practical; Andrew Murray's \"The Way into the Holiest\" sets the fight within union with Christ; and Edwards's \"Religious Affections\" tests whether the heart is truly changed. Together they map both the war and the ground of victory."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because indwelling sin is the believer's lifelong enemy, and these writers neither despair of it nor excuse it — they hold out real victory, won daily, under grace. They answer both the defeated Christian and the presumptuous one with Romans 6:14: sin shall not have dominion, and the way to prove it is to keep killing it by the Spirit."
        }
    ],
    "to-the-ends-of-the-earth": [
        {
            "question": "What is the To the Ends of the Earth collection about?",
            "answer": "It gathers the missionary journals — Brainerd in the forests, Taylor in China, Carmichael in India, Crowther on the Niger — the gospel carried at any cost. Its keynote is Acts 1:8, \"ye shall be witnesses unto me... unto the uttermost part of the earth\": the shelf follows the great commission into the hard places, in the first-hand records of those who obeyed it."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are \"The Life and Diary of David Brainerd,\" Hudson Taylor's \"A Retrospect,\" \"Separation and Service,\" Amy Carmichael's \"Things as They Are,\" Samuel Crowther's journal of the Niger expedition, Amanda Berry Smith's autobiography, and collections of the lives of those who gave everything for the gospel."
        },
        {
            "question": "What does Acts 1:8 mean for the shelf?",
            "answer": "\"Ye shall be witnesses unto me both in Jerusalem, and in all Judaea, and in Samaria, and unto the uttermost part of the earth\" is the commission under the whole collection — the widening circle that ends only at the ends of the earth. It sets these journals not as travel writing but as obedience to Christ's last command, carried into forests, deserts, and closed lands."
        },
        {
            "question": "What is Hudson Taylor's A Retrospect?",
            "answer": "Hudson Taylor's own account of his early years and the founding of the China Inland Mission — the story of a man who went inland where others would not, adopting Chinese dress and ways to reach the unreached millions, and who trusted God for every need. It brings to the shelf the pattern of a mission staked wholly on prayer and obedience."
        },
        {
            "question": "What kind of missionary lives does it hold?",
            "answer": "Costly ones, told first-hand. David Brainerd's diary records a young man praying to exhaustion among the Native peoples of colonial America; Amy Carmichael's \"Things as They Are\" refuses to romanticise the mission field in India; Amanda Berry Smith's autobiography follows a freed slave's evangelism across four continents; and Crowther's journal carries the gospel back into Africa by an African."
        },
        {
            "question": "How does this shelf differ from Revival & Missions?",
            "answer": "They overlap and reinforce each other. Revival & Missions pairs the missionary lives with the lectures and seasons of awakening; To the Ends of the Earth focuses on the journals themselves — the day-by-day records of the gospel carried into the uttermost parts, at whatever cost to the ones who carried it."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Brainerd's diary is the classic entry, both moving and searching; Hudson Taylor's \"A Retrospect\" shows a mission built on faith; and Amy Carmichael's \"Things as They Are\" gives the honest, unromantic cost of the field. Together they carry the reader to the ends of the earth in the company of those who went first."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because the great commission still stands, and these journals show what it costs and produces — lives poured out among the forgotten, the gospel carried where no one else would go. They stir the reader not with argument but with example, and press Acts 1:8 home: that the witness is not finished until it reaches the uttermost part of the earth."
        }
    ],
    "faith-for-the-impossible": [
        {
            "question": "What is the Faith for the Impossible collection about?",
            "answer": "It gathers books on taking God at His word — Müller's orphans fed by prayer alone, the grace of waiting on Him, and the bank of faith that never breaks. Its keynote is Mark 9:23, \"If thou canst believe, all things are possible to him that believeth\": the shelf holds out a faith that dares to trust God for what cannot be managed or foreseen."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are George Müller's \"Answers to Prayer\" and \"The Life of Trust,\" Andrew Murray's \"Waiting on God,\" Spurgeon's \"The Cheque Book of the Bank of Faith,\" and A. B. Simpson's \"Days of Heaven Upon Earth\" — works that press the reader to believe God's promises and prove them in practice."
        },
        {
            "question": "What does Mark 9:23 mean for the shelf?",
            "answer": "\"If thou canst believe, all things are possible to him that believeth\" is the word under the whole collection — Christ's answer to a desperate father, and the shelf's summons to a faith that reckons with God's power rather than the size of the problem. It sets believing prayer as the doorway through which the impossible becomes possible."
        },
        {
            "question": "What is George Müller's witness here?",
            "answer": "George Müller ran orphanages for thousands of children in Bristol without ever asking a human being for money — praying in the day's needs and recording, in \"Answers to Prayer\" and \"The Life of Trust,\" how God met them again and again, often at the last hour. He is the shelf's great case study in faith for the impossible, and he set out to prove, on purpose, that God still hears prayer."
        },
        {
            "question": "What is The Cheque Book of the Bank of Faith?",
            "answer": "Spurgeon's daily book of God's promises, treating each as a cheque to be endorsed by faith and presented at the bank of heaven — a promise for every day, pressing the reader to take God at His word. It brings to the shelf the note of confident, promise-claiming prayer: the bank of faith, Spurgeon insists, never breaks."
        },
        {
            "question": "What does the shelf teach about waiting on God?",
            "answer": "That faith for the impossible is not impatience but its opposite — a settled waiting on God for His time and His way. Andrew Murray's \"Waiting on God\" turns the reader from anxious striving to quiet dependence, teaching that the God who answers prayer is to be waited on, and that the waiting itself is part of the faith He honours."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "George Müller's \"Answers to Prayer\" is the clearest place to start — a plain record of faith proved in practice; Spurgeon's \"Cheque Book\" turns each day toward a promise to claim; and Andrew Murray's \"Waiting on God\" teaches the patience that faith requires. Together they build a confidence that God can be taken at His word."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because faith easily shrinks to the size of what we can manage, and these writers keep enlarging it to the size of God's promises. Tested in orphanages fed without an appeal and in ordinary believers' daily needs, they press Christ's own word on the reader: if you can believe, all things are possible — and the bank of faith never breaks."
        }
    ],
    "men-of-valour": [
        {
            "question": "What is the Men of Valour collection about?",
            "answer": "It gathers a call to the men — to pray, to lead, to give everything, and to tend the flock — lives of courage for the sons of God. Its keynote is 1 Corinthians 16:13, \"Watch ye, stand fast in the faith, quit you like men, be strong\": the shelf holds up examples of Christian manhood spent for God, and summons the reader to the same courage."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are \"Men of Prayer,\" \"Men Who Moved Heaven,\" \"Men Who Tended the Flock,\" \"Rise Up, Men of God,\" and collections of the lives of those who gave everything for the gospel — biographies and challenges gathered to stir Christian men to prayer, leadership, and sacrifice."
        },
        {
            "question": "What does 1 Corinthians 16:13 mean for the shelf?",
            "answer": "\"Watch ye, stand fast in the faith, quit you like men, be strong\" is the charge under the whole collection — Paul's four short commands to vigilance, steadfastness, courage, and strength. It sets the shelf's whole tone: a call not to a soft or passive religion but to a watchful, standing, manful faith."
        },
        {
            "question": "What kind of men does the shelf hold up?",
            "answer": "Men of prayer, first of all — those whose hidden intercession moved more than any public labour; men who moved heaven by faith; men who tended the flock as faithful shepherds; and men who gave everything, counting no cost too great for Christ. The shelf gathers their lives as examples of courage for the sons of God."
        },
        {
            "question": "Why does the shelf emphasise prayer?",
            "answer": "Because it treats prayer, not activity, as the root of a valiant Christian life. \"Men of Prayer\" gathers the examples of those whose strength lay on their knees, echoing the conviction of writers like E. M. Bounds that what the church most needs is not machinery but men mighty in prayer — so the call to valour begins in the secret place."
        },
        {
            "question": "How does this shelf relate to Women of Faith?",
            "answer": "They are companion shelves, each honouring courage and consecration in the church — Women of Faith gathering the mothers, missionaries, and mystics, and Men of Valour the men who prayed, led, shepherded, and gave everything. Together they show that the call to spend oneself wholly for Christ is laid on every kind of believer."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "\"Men of Prayer\" roots the whole call in the secret place; \"Men Who Moved Heaven\" and the lives of those who gave everything supply the examples of courage; and \"Men Who Tended the Flock\" holds up faithful shepherding. Together they issue Paul's charge in living form: watch, stand fast, be strong."
        },
        {
            "question": "Why read these books today?",
            "answer": "Because Christian manhood is easily softened into passivity or hardened into mere self-assertion, and these lives show the true thing — courage rooted in prayer, strength spent in service, everything given for Christ. They answer the reader's own half-heartedness with Paul's four commands, and with men who actually lived them out."
        }
    ],
    "for-teens": [
        {
            "question": "What is the For Teens collection about?",
            "answer": "It gathers faith for the teenage years — coming to Christ, belonging to His people, and the courage to follow — in short, plain, honest books and true stories of lives that were spent for Him, written for or well within reach of younger readers. Its keynote is 1 Timothy 4:12, \"Let no man despise thy youth; but be thou an example of the believers\": the shelf takes young readers seriously as disciples."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are \"Growing in Wisdom,\" Spurgeon's \"Around the Wicket Gate\" and \"All of Grace,\" Andrew Murray's \"The Way to God,\" \"Prayer, the Pulse of Life,\" and \"He Holds My Tomorrows,\" \"Rise Up, Men of God,\" and true stories such as David Brainerd's diary and the lives of men and women who gave everything for the gospel."
        },
        {
            "question": "What does 1 Timothy 4:12 mean for the shelf?",
            "answer": "\"Let no man despise thy youth; but be thou an example of the believers, in word, in conversation, in charity, in spirit, in faith, in purity\" is the charge under the whole collection — Paul's word to a young minister, and the shelf's message to young readers: that youth is no barrier to real faith, and that a teenager can be an example to older believers."
        },
        {
            "question": "What does the shelf offer a teenager coming to Christ?",
            "answer": "Plain, honest books that explain the gospel simply — Spurgeon's \"Around the Wicket Gate\" and \"All of Grace\" for the one beginning to seek, and Andrew Murray's \"The Way to God\" for the first steps of following. They meet a young reader where the questions actually are, without talking down, and press the same invitation the classics give: come to Christ just as you are."
        },
        {
            "question": "What true stories does it hold?",
            "answer": "Lives that were spent for God, told to stir courage: David Brainerd's diary, Hudson Taylor's early years, and the gathered lives of men and women who gave everything for the gospel. The shelf sets these before young readers not as distant heroes but as examples of what a life wholly given to Christ can be, whatever one's age."
        },
        {
            "question": "Who is this shelf for?",
            "answer": "For teenagers, and for those who read alongside them — books short and plain enough for younger readers, yet honest about the cost and courage of following Christ. It exists so that the great classics and the great stories of the faith reach the young in a form they can actually take up and be shaped by."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Spurgeon's \"Around the Wicket Gate\" is a warm entry for the seeker; \"Prayer, the Pulse of Life\" opens the life of prayer simply; and \"He Holds My Tomorrows\" speaks to a young reader anxious about the future. The true stories — Brainerd, Taylor, and those who gave everything — supply the courage to follow."
        },
        {
            "question": "Why does the church need a shelf for teens?",
            "answer": "Because the teenage years are when faith is often decided, and young readers are too often handed either nothing serious or nothing they can read. This shelf takes them seriously as disciples, offering the real gospel and real examples in reach of their years — that no one may despise their youth, and that they may become examples of the believers."
        }
    ],
    "for-young-readers": [
        {
            "question": "What is the For Young Readers collection about?",
            "answer": "It gathers the faith told simply, for children and those who read with them — the great story of the journey home, in language a child can follow. Its keynote is Matthew 19:14, \"Suffer little children, and forbid them not, to come unto me: for of such is the kingdom of heaven\": the shelf brings the classics and the gospel within reach of the youngest, and grows as more is retold for them."
        },
        {
            "question": "Which works are included?",
            "answer": "Among them are \"The Pilgrim's Progress in Words of One Syllable,\" \"Divine Songs for Children,\" and \"Brave for God\" — retellings and writings that carry the substance of the faith to children in language they can understand, so that even the youngest may come to Christ."
        },
        {
            "question": "What does Matthew 19:14 mean for the shelf?",
            "answer": "\"Suffer little children, and forbid them not, to come unto me: for of such is the kingdom of heaven\" is Christ's own welcome to children, and the charter of the whole collection. It sets the shelf's purpose plainly: not to keep the young waiting at the edge of the faith, but to bring them to the Saviour who called them to Himself."
        },
        {
            "question": "What is Pilgrim's Progress in Words of One Syllable?",
            "answer": "A retelling of John Bunyan's great allegory of the Christian's journey from the City of Destruction to the Celestial City, put into the simplest possible language so that a child can follow the pilgrim's road. It carries the substance of the classic — the burden, the wicket gate, the trials, the triumph — in words the youngest reader can take in."
        },
        {
            "question": "What are Divine Songs for Children?",
            "answer": "Isaac Watts's hymns and verses written especially for children — simple, singable poems teaching the truths of the faith in a form a child can learn by heart. They bring to the shelf the oldest way of planting the gospel in young hearts: through song and rhyme that stay in the memory long after childhood."
        },
        {
            "question": "Who is this shelf for?",
            "answer": "For children, and for the parents, teachers, and older friends who read with them — books simple enough for a child to follow, yet true to the great story of the faith. It exists so that the journey home can be told to the young in their own language, and so that the shelf can grow as more is retold and written for them."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "\"The Pilgrim's Progress in Words of One Syllable\" is the natural entry — the whole Christian journey told simply as a story; \"Divine Songs for Children\" plants the truths of the faith in verse; and \"Brave for God\" holds up courage for the young. Any of them can be read to a child or by one just beginning to read."
        },
        {
            "question": "Why read the faith to the young?",
            "answer": "Because Christ Himself called the children to come, and the truths planted early go deepest. This shelf answers His welcome by putting the great story and the great truths of the faith into words a child can follow — so that the kingdom which belongs to such as these may be opened to them from the very start."
        }
    ]
}
