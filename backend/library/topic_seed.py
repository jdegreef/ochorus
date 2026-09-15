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
            "let-us-pray-2",
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
            "if",
            "the-normal-christian-life",
            "watchman-nee-a-life",
        ],
    ),
    (
        "grace-and-comfort",
        "Grace & Comfort",
        "The unfailing grace of God and his comfort in every trial — good news "
        "for the weary.",
        [
            "all-of-grace",
            "grace-for-grace-2",
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
            "the-body-of-christ-a-reality",
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
            "if",
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
            "the-body-of-christ-a-reality",
            "the-body-of-christ-teens",
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
            "grace-for-grace-2",
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
            "the-body-of-christ-teens",
            "if",
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
    ],
    "holy-spirit": [
        "what-is-the-baptism-of-the-holy-spirit",
        "who-is-the-holy-spirit",
        "what-are-the-spiritual-gifts",
        "what-is-the-fruit-of-the-spirit",
        "soar-like-the-eagle-guide",
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
    ],
    "the-preached-word": [
        "how-to-know-if-god-is-calling-you-to-ministry",
        "what-makes-a-godly-leader",
        "sinners-in-the-hands-of-an-angry-god-explained",
        "what-is-the-church",
        "religious-affections-guide",
    ],
    "soar-like-the-eagle": [
        "how-to-wait-on-god",
        "how-to-find-rest-for-your-soul",
        "how-to-be-content",
        "how-to-trust-god-in-suffering",
        "soar-like-the-eagle-guide",
    ],
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
            "answer": "Among them are Andrew Murray's \"The Inner Chamber\" and \"Lord, Teach Us to Pray,\" Spurgeon's teaching on prayer and his \"Cheque Book of the Bank of Faith,\" Jeanne Guyon's \"A Short and Easy Method of Prayer,\" E. M. Bounds on prevailing and persistent prayer, George Müller's \"Answers to Prayer,\" and Watchman Nee's \"Let Us Pray\" — a spread across centuries and traditions united by a single subject."
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
            "answer": "They include Jeanne Guyon's \"A Short and Easy Method of Prayer,\" Amanda Berry Smith's \"Autobiography,\" Hannah Whitall Smith's \"The Christian's Secret of a Happy Life,\" \"The God of All Comfort\" and \"The Unselfishness of God,\" and Amy Carmichael's \"Things as They Are\" and \"If\" — works of prayer, testimony and missionary witness that have shaped readers far beyond their own day."
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
            "answer": "Hannah Whitall Smith's \"The Christian's Secret of a Happy Life\" is a warm and accessible starting point on the life of trust; Amanda Berry Smith's \"Autobiography\" offers gripping testimony; and Amy Carmichael's \"If\" is a short, piercing meditation for those ready to be searched. Together they open the shelf's range from settled peace to costly devotion."
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
            "answer": "Among them are Andrew Murray's \"Humility\" and \"The Way into the Holiest,\" Bernard of Clairvaux's \"On Loving God,\" Hannah Whitall Smith's \"The Christian's Secret of a Happy Life,\" Amy Carmichael's \"If,\" and Watchman Nee's \"The Normal Christian Life\" — a spread across centuries and traditions united by a single concern: the life of God lived out from within the believer."
        },
        {
            "question": "What does the shelf mean by surrender?",
            "answer": "The yielding of the whole self to God as the doorway to the deeper life — not striving to become holy by effort but abandoning oneself to Christ so that He may live His life through the believer. It is the note struck across the collection, from Murray's insistence on humility as the root to Nee's account of the Christian life as Christ's own life reproduced in us."
        },
        {
            "question": "What is the \"abundant life\" these writers describe?",
            "answer": "Not an intenser version of religious effort but Christ living His own life through the believer, so that holiness becomes a gift received rather than a height climbed. Watchman Nee's \"The Normal Christian Life\" is the shelf's fullest treatment — its argument that the ordinary birthright of every Christian is not endless struggle but Christ Himself lived out from within."
        },
        {
            "question": "Why is humility so central here?",
            "answer": "Because these writers agree that pride is the great obstacle to the deeper life and humility its root. Andrew Murray's little book on the subject argues that humility is not one virtue among many but the ground in which all the others grow — the emptying of self that alone makes room for the fullness of God. Without it, the deeper life is sought in vain."
        },
        {
            "question": "Where should a reader begin?",
            "answer": "Hannah Whitall Smith's \"The Christian's Secret of a Happy Life\" is a warm and accessible entry into the life of trust; Andrew Murray's \"Humility\" goes to the root; and Watchman Nee's \"The Normal Christian Life\" sets out the whole mechanism — how the cross, the blood, and the indwelling Spirit make the abundant life a reality rather than a hope."
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
            "answer": "Among them are Spurgeon's \"All of Grace\" and \"Grace for Grace,\" Hannah Whitall Smith's \"The God of All Comfort\" and \"The Unselfishness of God,\" Andrew Murray's \"The Way to God,\" and Thomas Watson's \"All Things for Good\" — works written to steady the anxious and lift the discouraged with the plain assurance of grace."
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
    ]
}
