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

The shelf definitions themselves live in ``library/topic_seed.py`` — a
Django-free module, because the cover generator reads them too.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.models import Topic, TopicBook, TopicSermon, TopicTranslation
from library.topic_seed import TOPICS
from library.topic_translations import topic_scripture, topic_translations

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
                if not tr:
                    continue
                # The file is authoritative in BOTH directions: a scripture
                # object deleted from the entry (a reviewer rejecting a verse)
                # must blank the stored one on the next deploy, not leave it
                # rendering forever. So absent scripture writes "", never skips.
                ref, verse_tr = scripture.get(lang, {}).get(slug, ("", ""))
                TopicTranslation.objects.update_or_create(
                    topic=topic,
                    language=lang,
                    defaults={
                        "title": tr[0],
                        "description": tr[1],
                        "scripture_ref": ref,
                        "scripture_text": verse_tr,
                    },
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
