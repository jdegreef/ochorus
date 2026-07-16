"""Create the curated topical shelves from books already in the library.

Idempotent: a topic is created only if its slug doesn't exist yet, and its
membership is upserted each run (new books added to existing topics as the
library grows). Members are soft slug-references — a slug that isn't present in
a given language simply doesn't appear on that language's shelf, so a topic can
be seeded ahead of a book landing. Run on deploy (see release.py).

Topic titles/descriptions are seeded in English; per-language translations live
in ``TopicTranslation`` and are filled by review later — the shelf falls back to
the English title in the meantime (the same way an untranslated book shows its
English title). This mirrors ``seed_plans``, whose curated prose is English too.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.models import Topic, TopicBook, TopicTranslation

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
        ],
    ),
]


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
}

# Localized epigraphs (reference localized to the target-language Bible book
# name; verse in that language's reverent register). AI-drafted, pending native
# review. {language: {slug: (reference, verse text)}}
TOPIC_SCRIPTURE_TR = {
    "lg": {
        "prayer": (
            "Yeremiya 33:3",
            "Munkoowoole, nange ndikuyitaba, ne nkulaga ebintu ebikulu era "
            "eby'ekitalo, by'otomanyi.",
        ),
        "holy-spirit": (
            "Zekkaliya 4:6",
            "Si na maanyi, so si na buyinza, wabula na Mwoyo gwange, bw'ayogera "
            "Mukama ow'eggye.",
        ),
        "deeper-life": (
            "Abakkolosaayi 3:3",
            "Kubanga mwafa, n'obulamu bwammwe bukwekeddwa mu Kristo mu Katonda.",
        ),
        "grace-and-comfort": (
            "2 Abakkolinso 12:9",
            "Ekisa kyange kikumala: kubanga amaanyi gange gatuukirizibwa mu "
            "bunafu.",
        ),
        "revival-and-missions": (
            "Kaabakuuku 3:2",
            "Ai Mukama, zzaamu obulamu omulimu gwo wakati mu myaka, wakati mu "
            "myaka gumanyise.",
        ),
        "faith-and-guidance": (
            "Engero 3:6",
            "Mu makubo go gonna mumumanye, naye alitereeza amakubo go.",
        ),
    },
}


# Per-language topic prose, upserted into TopicTranslation each run. Missing
# languages / topics fall back per-field to the English original above.
# AI-drafted, pending native review (the same review flow as book translations).
#   {language: {slug: (title, description)}}
TOPIC_TRANSLATIONS = {
    "lg": {
        "prayer": (
            "Ku Kusaba",
            "Okuyiga okusaba — era n'okunyiikira okusaba obutakoowa. Ebitabo "
            "eby'edda ebyogera ku bulamu obw'omunda obw'okusaba, okuva mu kifo "
            "eky'ekyama okutuuka ku kwegayiririra abalala okw'amaanyi.",
        ),
        "holy-spirit": (
            "Omwoyo Omutukuvu",
            "Okubatizibwa kw'Omwoyo, okutuula kwe mu ffe, n'omulimu gwe — amaanyi "
            "agaasuubizibwa ag'obulamu obw'Ekikristaayo.",
        ),
        "deeper-life": (
            "Obulamu Obw'obuziba",
            "Obutukuvu, okwewaayo, n'obulamu obw'ekyengera obukwekeddwa mu Kristo "
            "— ebitabo eby'okugenda mu maaso ennyo mu by'omwoyo.",
        ),
        "grace-and-comfort": (
            "Ekisa n'Okubudaabuda",
            "Ekisa kya Katonda ekitaggwaawo n'okubudaabuda kwe mu kugezesebwa "
            "kwonna — amawulire amalungi eri abakooye.",
        ),
        "revival-and-missions": (
            "Okuzuukusibwa n'Obuweereza bw'Enjiri",
            "Obulamu obwawaayo olw'enjiri, n'ebiseera eby'okuzuukusibwa — "
            "eky'okwongera omuliro mu mutima ogwaka.",
        ),
        "faith-and-guidance": (
            "Okukkiriza n'Obulagirizi",
            "Okwesiga Katonda olw'emmere eya buli lunaku, obulagirizi, na buli "
            "kisuubizo — okutambula mu kukkiriza, so si mu kulaba.",
        ),
    },
}


class Command(BaseCommand):
    help = "Seed the curated topical shelves and their membership (idempotent)."

    def handle(self, *args, **opts):
        created = 0
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
            # Upsert per-language prose each run so an edited/added translation
            # reaches an already-seeded topic on the next deploy.
            langs = set(TOPIC_TRANSLATIONS) | set(TOPIC_SCRIPTURE_TR)
            for lang in langs:
                tr = TOPIC_TRANSLATIONS.get(lang, {}).get(slug)
                sc = TOPIC_SCRIPTURE_TR.get(lang, {}).get(slug)
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
