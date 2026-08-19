"""Create the curated topical shelves from books already in the library.

Idempotent: a topic is created only if its slug doesn't exist yet, and its
membership is upserted each run (new books added to existing topics as the
library grows). Members are soft slug-references — a slug that isn't present in
a given language simply doesn't appear on that language's shelf, so a topic can
be seeded ahead of a book landing. Run on deploy (see release.py).

Topic titles/descriptions are seeded in English; per-language translations live
in ``TopicTranslation``. There is NO English fallback: a topic with no title in
a language is omitted from that language's shelf list and its page 404s there
(``Topic.is_translated_into``), so a shelf only exists where it has been
translated. This mirrors ``seed_plans``, whose curated prose is English too.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.models import Topic, TopicBook, TopicSermon, TopicTranslation
from library.topic_translations import topic_scripture, topic_translations

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
            "the-christians-secret-of-a-happy-life-4",
            "purity-of-heart",
            "way-into-holiest",
            "if",
            "the-normal-christian-life",
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


class Command(BaseCommand):
    help = "Seed the curated topical shelves and their membership (idempotent)."

    def handle(self, *args, **opts):
        created = 0
        prose, scripture = topic_translations(), topic_scripture()
        for order, (slug, title, description, book_slugs) in enumerate(TOPICS):
            ref, verse = TOPIC_SCRIPTURE.get(slug, ("", ""))
            topic, was_created = Topic.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "description": description,
                    "scripture_ref": ref,
                    "scripture_text": verse,
                    "sort_order": order,
                },
            )
            if was_created:
                created += 1
            elif (topic.scripture_ref, topic.scripture_text) != (ref, verse):
                # Backfill/refresh the epigraph on an already-seeded topic.
                topic.scripture_ref = ref
                topic.scripture_text = verse
                topic.save(update_fields=["scripture_ref", "scripture_text"])
            # Upsert membership each run so new books join existing shelves.
            added = 0
            for i, book_slug in enumerate(book_slugs):
                _, entry_created = TopicBook.objects.update_or_create(
                    topic=topic,
                    book_slug=book_slug,
                    defaults={"sort_order": i},
                )
                if entry_created:
                    added += 1
            # Upsert sermon membership the same way.
            for i, sermon_slug in enumerate(TOPIC_SERMONS.get(slug, [])):
                _, entry_created = TopicSermon.objects.update_or_create(
                    topic=topic,
                    sermon_slug=sermon_slug,
                    defaults={"sort_order": i},
                )
                if entry_created:
                    added += 1
            # Upsert per-language prose each run so an edited/added translation
            # reaches an already-seeded topic on the next deploy.
            for lang in set(prose) | set(scripture):
                tr = prose.get(lang, {}).get(slug)
                sc = scripture.get(lang, {}).get(slug)
                if not tr and not sc:
                    continue
                defaults = {}
                if tr:
                    defaults["title"], defaults["description"] = tr
                if sc:
                    defaults["scripture_ref"], defaults["scripture_text"] = sc
                TopicTranslation.objects.update_or_create(
                    topic=topic, language=lang, defaults=defaults
                )
            if was_created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created topic {slug} with {len(book_slugs)} members."
                    )
                )
            elif added:
                self.stdout.write(f"Topic {slug}: added {added} new member(s).")

        if not created:
            self.stdout.write("Topics already seeded.")
