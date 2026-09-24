"""Create the curated topical shelves from books already in the library.

Idempotent: a topic is created only if its slug doesn't exist yet. After that
``topic_seed`` is the truth for everything it owns: the English title,
description and sort order are re-asserted, and membership is SYNCED each run —
new members added, removed members deleted. Until 2026-09-24 membership was
add-only, so a book taken off a shelf in ``topic_seed`` stayed on it live (the
copyright-blocked *Grace for Grace* sat on two shelves in es/fr/pt that way).
Nothing else writes these rows, so there is no live edit to protect. Members are soft slug-references — a slug that isn't present in
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

from library.models import (
    Topic,
    TopicArticle,
    TopicBook,
    TopicSermon,
    TopicTranslation,
)
from library.topic_seed import (
    TOPIC_ARTICLES,
    TOPIC_QA,
    TOPIC_SCRIPTURE,
    TOPIC_SEO,
    TOPIC_SERMONS,
    TOPICS,
)
from library.topic_translations import topic_scripture, topic_seo, topic_translations


class Command(BaseCommand):
    help = "Seed the curated topical shelves and their membership (idempotent)."

    def handle(self, *args, **opts):
        created = 0
        prose, scripture, seo = (
            topic_translations(),
            topic_scripture(),
            topic_seo(),
        )
        for order, (slug, title, description, book_slugs) in enumerate(TOPICS):
            ref, verse = TOPIC_SCRIPTURE.get(slug, ("", ""))
            qa = TOPIC_QA.get(slug, [])
            seo_title, meta_description = TOPIC_SEO.get(slug, ("", ""))
            topic, was_created = Topic.objects.get_or_create(
                slug=slug,
                defaults={
                    "title": title,
                    "description": description,
                    "seo_title": seo_title,
                    "meta_description": meta_description,
                    "scripture_ref": ref,
                    "scripture_text": verse,
                    "qa": qa,
                    "sort_order": order,
                },
            )
            if was_created:
                created += 1
            else:
                # Refresh the fixture-owned English fields on an already-seeded
                # topic: nothing else writes them, so a corrected title, blurb,
                # order, scripture, Q&A or SEO override must reach production on
                # the next deploy. (is_published stays create-only.)
                changed = []
                if (topic.title, topic.description, topic.sort_order) != (
                    title,
                    description,
                    order,
                ):
                    topic.title, topic.description, topic.sort_order = (
                        title,
                        description,
                        order,
                    )
                    changed += ["title", "description", "sort_order"]
                if (topic.scripture_ref, topic.scripture_text) != (ref, verse):
                    topic.scripture_ref, topic.scripture_text = ref, verse
                    changed += ["scripture_ref", "scripture_text"]
                if topic.qa != qa:
                    topic.qa = qa
                    changed.append("qa")
                if (topic.seo_title, topic.meta_description) != (
                    seo_title,
                    meta_description,
                ):
                    topic.seo_title, topic.meta_description = (
                        seo_title,
                        meta_description,
                    )
                    changed += ["seo_title", "meta_description"]
                if changed:
                    topic.save(update_fields=changed)
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
            # Upsert article membership the same way (the bidirectional funnel).
            for i, article_slug in enumerate(TOPIC_ARTICLES.get(slug, [])):
                _, entry_created = TopicArticle.objects.update_or_create(
                    topic=topic,
                    article_slug=article_slug,
                    defaults={"sort_order": i},
                )
                if entry_created:
                    added += 1
            # ...and delete whatever topic_seed no longer lists, so a removal
            # reaches production too.
            removed = 0
            for model, field, wanted in (
                (TopicBook, "book_slug", book_slugs),
                (TopicSermon, "sermon_slug", TOPIC_SERMONS.get(slug, [])),
                (TopicArticle, "article_slug", TOPIC_ARTICLES.get(slug, [])),
            ):
                removed += (
                    model.objects.filter(topic=topic)
                    .exclude(**{f"{field}__in": wanted})
                    .delete()[0]
                )
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
                seo_title_tr, meta_tr = seo.get(lang, {}).get(slug, ("", ""))
                TopicTranslation.objects.update_or_create(
                    topic=topic,
                    language=lang,
                    defaults={
                        "title": tr[0],
                        "description": tr[1],
                        "seo_title": seo_title_tr,
                        "meta_description": meta_tr,
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
            elif added or removed:
                self.stdout.write(
                    f"Topic {slug}: added {added}, removed {removed} member(s)."
                )

        if not created:
            self.stdout.write("Topics already seeded.")
