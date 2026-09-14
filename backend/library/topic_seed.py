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
    ]
}
