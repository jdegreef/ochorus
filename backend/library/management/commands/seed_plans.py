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


# Per-language plan prose. A plan is a per-language row (like Book), so the
# translation replaces the English title/description on the row for that
# language; missing languages/plans fall back to the English tuple in the defs.
# AI-drafted, pending native review.
#   {language: {slug: (title, description)}}
PLAN_TRANSLATIONS = {
    "lg": {
        "humility-12-days": (
            "Obwetoowaze mu Nnaku 12",
            "Ekitabo kya Andrew Murray eky'edda ku musingi gwa buli mpisa "
            "ennungi — essuula emu ennyimpi buli lunaku okumala ennaku kkumi na "
            "bbiri.",
        ),
        "the-inner-chamber-month": (
            "Omwezi mu Kisenge eky'omunda",
            "Zimba empisa eya buli lunaku ey'okusaba n'Ekigambo: enkya amakumi "
            "asatu mu mukaaga ne Andrew Murray, essuula emu buli lunaku.",
        ),
        "school-of-prayer": (
            "Essomero ery'Okusaba",
            "Wiiki nnya mu ssomero ery'okusaba n'abakulembeze basatu: Andrew "
            "Murray ku ngeri Mukama gy'atuyigiriza yekka okusaba, D. L. Moody ku "
            "kusaba okuwangula, ne Hannah Buyinza ku kusaba ng'okukuba kw'omutima "
            "okwa buli lunaku mu bulamu obw'Ekikristaayo.",
        ),
    },
    "sw": {
        "school-of-prayer": (
            "Shule ya Maombi",
            "Wiki nne katika shule ya maombi pamoja na waelekezi watatu: Andrew "
            "Murray kuhusu jinsi Bwana mwenyewe anavyotufundisha kuomba, D. L. "
            "Moody kuhusu maombi yenye kushinda, na Hannah Buyinza kuhusu maombi "
            "kama mapigo ya kila siku ya maisha ya Mkristo.",
        ),
    },
}


def _prose(slug, lang, en_title, en_description):
    """Localized (title, description) for a plan, else the English original."""
    return PLAN_TRANSLATIONS.get(lang, {}).get(slug) or (en_title, en_description)


class Command(BaseCommand):
    help = "Seed launch reading plans from existing books (idempotent)."

    def _reconcile_existing(self, slug, lang, title, description) -> bool:
        """If a plan already exists for (slug, lang), keep its prose in sync with
        the defs/translations and return True (caller skips creation). An edited
        or newly-added translation thus reaches prod on the next redeploy."""
        plan = Plan.objects.filter(slug=slug, language=lang).first()
        if not plan:
            return False
        if (plan.title, plan.description) != (title, description):
            plan.title = title
            plan.description = description
            plan.save(update_fields=["title", "description"])
            self.stdout.write(f"Updated plan {slug} ({lang}) prose.")
        return True

    def handle(self, *args, **opts):
        created = 0
        for slug, book_slug, title, description in LAUNCH_PLANS:
            for book in Book.objects.filter(slug=book_slug, is_published=True):
                t, d = _prose(slug, book.language, title, description)
                if self._reconcile_existing(slug, book.language, t, d):
                    continue
                orders = list(
                    book.chapters.order_by("order").values_list("order", flat=True)
                )
                if not orders:
                    continue
                plan = Plan.objects.create(
                    slug=slug,
                    language=book.language,
                    title=t,
                    description=d,
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
                t, d = _prose(slug, lang, title, description)
                if self._reconcile_existing(slug, lang, t, d):
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
                    title=t,
                    description=d,
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
