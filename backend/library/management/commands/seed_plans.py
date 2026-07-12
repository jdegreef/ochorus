"""Create the launch reading plans from books already in the library.

Idempotent: a plan is only created if its slug doesn't exist yet for the
language, and only if the source book is present with enough chapters. Run on
deploy (release command) after the library is seeded.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.models import Book, Plan, PlanDay

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
]


class Command(BaseCommand):
    help = "Seed launch reading plans from existing books (idempotent)."

    def handle(self, *args, **opts):
        created = 0
        for slug, book_slug, title, description in LAUNCH_PLANS:
            for book in Book.objects.filter(slug=book_slug, is_published=True):
                if Plan.objects.filter(slug=slug, language=book.language).exists():
                    continue
                orders = list(
                    book.chapters.order_by("order").values_list("order", flat=True)
                )
                if not orders:
                    continue
                plan = Plan.objects.create(
                    slug=slug,
                    language=book.language,
                    title=title,
                    description=description,
                    sort_order=created,
                )
                PlanDay.objects.bulk_create(
                    [
                        PlanDay(
                            plan=plan,
                            day=i + 1,
                            book_slug=book_slug,
                            chapter_order=order,
                        )
                        for i, order in enumerate(orders)
                    ]
                )
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created plan {slug} ({book.language}) with {len(orders)} days."
                    )
                )

        created += self._seed_curated(created)

        if not created:
            self.stdout.write("Plans already seeded (or source books missing).")

    def _seed_curated(self, sort_base):
        """Create multi-book curated plans, once per language that has them all."""
        created = 0
        for slug, title, description, book_slugs in CURATED_PLANS:
            wanted = set(book_slugs)
            langs = set(
                Book.objects.filter(slug__in=book_slugs, is_published=True)
                .values_list("language", flat=True)
            )
            for lang in sorted(langs):
                if Plan.objects.filter(slug=slug, language=lang).exists():
                    continue
                by_slug = {
                    b.slug: b
                    for b in Book.objects.filter(
                        slug__in=book_slugs, language=lang, is_published=True
                    )
                }
                if set(by_slug) != wanted:
                    continue  # not every source book exists (published) in this language
                days = [
                    (bslug, order)
                    for bslug in book_slugs
                    for order in by_slug[bslug]
                    .chapters.order_by("order")
                    .values_list("order", flat=True)
                ]
                if not days:
                    continue
                plan = Plan.objects.create(
                    slug=slug,
                    language=lang,
                    title=title,
                    description=description,
                    sort_order=sort_base + created,
                )
                PlanDay.objects.bulk_create(
                    [
                        PlanDay(
                            plan=plan,
                            day=i + 1,
                            book_slug=bslug,
                            chapter_order=order,
                        )
                        for i, (bslug, order) in enumerate(days)
                    ]
                )
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created curated plan {slug} ({lang}) with {len(days)} days "
                        f"across {len(book_slugs)} books."
                    )
                )
        return created
