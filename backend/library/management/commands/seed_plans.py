"""Create the launch reading plans from books already in the library.

Idempotent: a plan is only created if its slug doesn't exist yet for the
language, and only if the source book is present with enough chapters. Run on
deploy (release command) after the library is seeded.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from library.models import Book, Plan, PlanDay
from library.plan_translations import plan_translations

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
]


def _prose(slug, lang, en_title, en_description):
    """Localized (title, description) for a plan, or None if there is none.

    English is its own prose; every other language must have an explicit
    entry in ``data/plan_translations/<lang>.json``. This used to fall back to
    the English tuple,
    which is how shipping a BOOK silently published an English-titled plan:
    a plan row is created per language in which the source books exist, so
    PR #819 (Arabic *Humility*) put "Humility in 12 Days" on the Arabic plans
    page without anyone touching a plan. The row was valid, the page rendered,
    and nothing failed.

    ``PlanTranslationCoverageTests`` catches that case in CI, but a CI test
    guards the fixture, not the command: a language whose books reach the DB by
    any other route (a hand-run import, a locale added from the admin) would
    still get the English fallback. Returning None makes the command itself
    refuse, so "no prose" produces no plan rather than a wrong one — the same
    stance ``_seed_curated`` already takes when a source book is missing, where
    a partial set is skipped rather than shipped half-empty.
    """
    # "en" and any English variant ("en-modern", the contemporize pipeline's
    # edition language) own the English tuple: it is their prose, not a
    # fallback. Without this an en-modern book would publish no plan at all,
    # and every plan would need a duplicated en-modern.json.
    if lang == "en" or lang.startswith("en-"):
        return (en_title, en_description)
    return plan_translations().get(lang, {}).get(slug)


class Command(BaseCommand):
    help = "Seed launch reading plans from existing books (idempotent)."

    def _report_untranslated(self, slug, lang) -> None:
        """Say loudly that a plan row was NOT created for want of prose.

        Two different situations, and the deploy log should distinguish them:
        the plan is simply not translated yet (expected, and the queue job for
        it says so), or a row already exists — meaning it predates this guard
        and is on a live page under whatever prose it was created with. The
        second is not repaired here: deleting a published plan is a bigger
        decision than a seed step should make on its own.
        """
        exists = Plan.objects.filter(slug=slug, language=lang).exists()
        note = (
            "a row already EXISTS from before this guard and keeps its current "
            "prose — check the page and add the entry"
            if exists
            else "no plan row created"
        )
        self.stdout.write(
            self.style.WARNING(
                f"Plan {slug} ({lang}): no {lang}.json entry for {slug!r}; {note}."
            )
        )

    def _reconcile_existing(self, slug, lang, title, description) -> bool:
        """If a plan already exists for (slug, lang), keep its prose in sync with
        the defs/translations and return True (caller skips creation). An edited
        or newly-added translation thus reaches prod on the next redeploy."""
        plan = Plan.objects.filter(slug=slug, language=lang).first()
        if not plan:
            return False
        # A plan with no days is broken: a previous run created the Plan row but
        # died (or was interrupted) before its PlanDays landed. Treat it as absent
        # — delete it and let the caller rebuild it with days — because this method
        # otherwise reports every existing (slug, lang) row as "done", so a
        # day-less plan would stay permanently empty across all future deploys.
        if not plan.days.exists():
            plan.delete()
            self.stdout.write(f"Rebuilding day-less plan {slug} ({lang}).")
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
                prose = _prose(slug, book.language, title, description)
                if prose is None:
                    self._report_untranslated(slug, book.language)
                    continue
                t, d = prose
                if self._reconcile_existing(slug, book.language, t, d):
                    continue
                orders = list(
                    book.chapters.order_by("order").values_list("order", flat=True)
                )
                if not orders:
                    continue
                # Create the plan and its days as one unit: a crash between the
                # two would otherwise leave a permanently-empty plan (see
                # _reconcile_existing).
                with transaction.atomic():
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
                by_slug = {
                    b.slug: b
                    for b in Book.objects.filter(
                        slug__in=book_slugs, language=lang, is_published=True
                    )
                }
                # Whether this language could have this plan at all. A curated
                # plan needs EVERY source book, so most languages here can never
                # get most plans — and telling someone to write prose for a plan
                # that cannot exist is noise that trains them to skim the log.
                complete = set(by_slug) == wanted
                prose = _prose(slug, lang, title, description)
                if prose is None:
                    if complete:
                        self._report_untranslated(slug, lang)
                    continue
                t, d = prose
                if self._reconcile_existing(slug, lang, t, d):
                    continue
                if not complete:
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
                with transaction.atomic():
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
