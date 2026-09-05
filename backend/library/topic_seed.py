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
            "pilgrims-progress",
            "the-imitation-of-christ",
            "freedom-of-the-will",
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
]

# Sermon members per topic, by canonical sermon slug (language-agnostic, like
# the book members). A sermon shows on a topic's shelf in each language it
# exists in. {topic slug: [ordered sermon slugs]}
TOPIC_SERMONS = {
    "prayer": [
        "the-golden-key-of-prayer",
        "order-and-argument-in-prayer",
        "pauls-first-prayer",
    ],
    "deeper-life": ["himself", "christ-all-in-all"],
    "grace-and-comfort": [
        "free-grace",
        "the-immutability-of-god",
        "sweet-comfort-for-feeble-saints",
        "comfort-for-the-desponding",
        "consolation-in-the-furnace",
    ],
    "revival-and-missions": [
        "compel-them-to-come-in",
        "the-way-of-salvation",
        "christs-boundless-compassion",
    ],
    "faith-and-guidance": ["the-possibilities-of-faith", "unfailing-springs"],
    "the-gospel-call": [
        "christ-crucified",
        "the-new-birth",
        "salvation-by-faith",
        "come-thou-into-the-ark",
        "the-dying-thief",
        "the-ravens-cry",
    ],
    "the-way-of-holiness": ["aggressive-christianity"],
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
    ],
    "grace-and-comfort": [
        "how-to-trust-god-in-suffering",
        "how-to-overcome-fear-and-anxiety-with-faith",
    ],
    "revival-and-missions": [
        "what-is-revival-and-how-does-it-begin",
        "what-is-the-great-commission",
        "hudson-taylor-trusting-god-for-the-impossible",
        "amy-carmichael-and-the-cost-of-love",
        "samuel-crowther-from-captive-to-bishop",
        "how-to-pray-for-revival",
        "the-marks-of-a-true-revival",
        "what-was-the-great-awakening",
        "personal-revival-reviving-a-cold-heart",
        "revival-and-repentance-breaking-up-the-fallow-ground",
    ],
    "faith-and-guidance": [
        "how-to-find-gods-will-for-your-life",
        "how-to-hear-gods-voice",
        "how-to-trust-god-in-suffering",
    ],
    "the-gospel-call": [
        "how-to-be-born-again",
        "how-to-have-assurance-of-salvation",
        "what-is-the-gospel",
        "what-is-justification-by-faith",
        "pilgrims-progress-guide",
        "augustines-confessions-guide",
        "sinners-in-the-hands-of-an-angry-god-explained",
    ],
    "the-way-of-holiness": [
        "what-is-sanctification",
        "how-to-forgive-someone-who-hurt-you",
        "how-to-overcome-sin-and-temptation",
        "the-priesthood-of-all-believers",
        "why-humility-matters",
        "the-imitation-of-christ-guide",
        "revival-and-repentance-breaking-up-the-fallow-ground",
    ],
    "enduring-classics": [
        "pilgrims-progress-guide",
        "the-imitation-of-christ-guide",
        "augustines-confessions-guide",
        "sinners-in-the-hands-of-an-angry-god-explained",
    ],
    "the-preached-word": [
        "how-to-know-if-god-is-calling-you-to-ministry",
        "what-makes-a-godly-leader",
        "sinners-in-the-hands-of-an-angry-god-explained",
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
}
