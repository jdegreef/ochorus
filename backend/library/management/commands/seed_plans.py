"""Create the launch reading plans from books already in the library.

Idempotent: a plan is only created if its slug doesn't exist yet for the
language, and only if the source book is present with enough chapters. Run on
deploy (release command) after the library is seeded.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from library.models import Book, Plan, PlanDay
from library.plan_seed import CURATED_PLANS, LAUNCH_PLANS
from library.plan_translations import plan_translations


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
