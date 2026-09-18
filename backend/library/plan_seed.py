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

# (plan slug, source book slug, title, description)
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
]
