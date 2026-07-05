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
        if not created:
            self.stdout.write("Plans already seeded (or source books missing).")
