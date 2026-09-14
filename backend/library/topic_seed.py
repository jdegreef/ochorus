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
