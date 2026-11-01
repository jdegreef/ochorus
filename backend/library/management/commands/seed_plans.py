"""Create the launch reading plans from books already in the library.

Idempotent: a plan is only created if its slug doesn't exist yet for the
language, and only if the source book is present with enough chapters. Run on
deploy (release command) after the library is seeded.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max

from library import daily_readings
from library.localization import is_english_edition
from library.models import Article, Book, Plan, PlanDay
from library.plan_seed import (
    CURATED_PLANS,
    DAILY_PLANS,
    LAUNCH_PLANS,
    RETIRED_PLANS,
    plan_items,
    plan_sources,
)
from library.plan_translations import plan_translations

#: Where the year-long devotional plans sort: below every journey (see
#: _seed_daily). Far above any journey's number, which counts up from 0.
DAILY_SORT_BASE = 100_000


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
    if is_english_edition(lang):
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

    def _retire(self) -> None:
        """Delete every row of a plan in ``RETIRED_PLANS``, in every language.

        The rest of this command only creates and reconciles, so a plan dropped
        from the lists would otherwise stay live forever. Deleting rather than
        unpublishing because a Plan row is wholly derived from the seed data:
        nothing points at it by FK but its own days, which go with it, and
        readers' progress is slug-keyed and carried to the successor elsewhere
        (see ``RETIRED_PLANS``). An unpublished row would still count as a
        "present" plan in the admin coverage grid and per-language totals.
        """
        rows = Plan.objects.filter(slug__in=RETIRED_PLANS)
        found = sorted(rows.values_list("slug", "language"))
        if not found:
            return  # the steady state: one query per deploy
        rows.delete()
        for slug, lang in found:
            self.stdout.write(self.style.WARNING(f"Retired plan {slug} ({lang})."))

    def handle(self, *args, **opts):
        self._retire()
        # Every journey this run creates sorts after every journey already on
        # the shelf, in seed order. The seed used to number from the plans
        # created in this run alone — 0 on a live database, where every older
        # plan is already there — which put each new plan at the head of it.
        top = (
            Plan.objects.filter(sort_order__lt=DAILY_SORT_BASE)
            .aggregate(top=Max("sort_order"))["top"]
        )
        self._next_sort = 0 if top is None else top + 1
        created = self._seed_launch() + self._seed_curated() + self._seed_daily()
        if not created:
            self.stdout.write("Plans already seeded (or source books missing).")

    def _create_plan(
        self, slug, lang, title, description, days: list[dict], sort_order=None
    ) -> None:
        """One plan row and its days (``PlanDay`` field dicts, day 1 first), as
        one unit: a crash between the two would otherwise leave a
        permanently-empty plan (see _reconcile_existing)."""
        with transaction.atomic():
            plan = Plan.objects.create(
                slug=slug,
                language=lang,
                title=title,
                description=description,
                sort_order=self._next_sort if sort_order is None else sort_order,
            )
            PlanDay.objects.bulk_create(
                [PlanDay(plan=plan, day=i + 1, **day) for i, day in enumerate(days)]
            )
        if sort_order is None:
            self._next_sort += 1

    def _editions_needing(self, slug, book_slug, title, description):
        """Each published edition of ``book_slug`` that still needs plan
        ``slug``, with its (title, description) — an existing plan is
        reconciled instead, and a language with no prose is reported."""
        for book in Book.objects.filter(slug=book_slug, is_published=True):
            prose = _prose(slug, book.language, title, description)
            if prose is None:
                self._report_untranslated(slug, book.language)
                continue
            if self._reconcile_existing(slug, book.language, *prose):
                continue
            yield book, *prose

    def _seed_launch(self):
        """One book's chapters, a day each (or the optional span of them)."""
        created = 0
        for slug, book_slug, title, description, *rest in LAUNCH_PLANS:
            span = rest[0] if rest else None  # (first, last) chapter order
            for book, t, d in self._editions_needing(slug, book_slug, title, description):
                chapters = book.chapters.order_by("order")
                if span:
                    chapters = chapters.filter(order__range=span)
                orders = list(chapters.values_list("order", flat=True))
                if not orders:
                    continue
                self._create_plan(
                    slug,
                    book.language,
                    t,
                    d,
                    [{"book_slug": book_slug, "chapter_order": o} for o in orders],
                )
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created plan {slug} ({book.language}) with {len(orders)} days."
                    )
                )
        return created

    def _seed_daily(self):
        """The year-long devotional plans: one per published edition, a day per
        dated entry (``daily_readings.year_entries``), January first.

        Their own band at the foot of the shelf (``DAILY_SORT_BASE`` + their
        place in DAILY_PLANS, the same in every language): a different shape
        of plan, which seven of would otherwise head the journeys — and a
        journey added later still sorts above them."""
        created = 0
        version = daily_readings.content_version()
        for position, (slug, book_slug, title, description) in enumerate(DAILY_PLANS):
            for book, t, d in self._editions_needing(slug, book_slug, title, description):
                entries = daily_readings.year_entries(book, version)
                if not entries:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Plan {slug} ({book.language}): the edition has no dated "
                            "entries; no plan row created."
                        )
                    )
                    continue
                self._create_plan(
                    slug,
                    book.language,
                    t,
                    d,
                    [
                        {
                            "book_slug": book_slug,
                            "chapter_order": daily_readings.chapter_order(book_slug, month),
                            "entry_date": daily_readings.format_date(month, entry.day),
                        }
                        for month, entry in entries
                    ],
                    sort_order=DAILY_SORT_BASE + position,
                )
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created devotional plan {slug} ({book.language}) with "
                        f"{len(entries)} days."
                    )
                )
        return created

    def _seed_curated(self):
        """Create curated plans — several books, and articles — once per
        language that has every one of their sources published."""
        created = 0
        for slug, title, description, items in CURATED_PLANS:
            book_slugs, article_slugs = plan_sources(items)
            books = Book.objects.filter(slug__in=book_slugs, is_published=True)
            articles = Article.objects.filter(slug__in=article_slugs, is_published=True)
            langs = set(books.values_list("language", flat=True)) | set(
                articles.values_list("language", flat=True)
            )
            for lang in sorted(langs):
                by_slug = {b.slug: b for b in books.filter(language=lang)}
                have_articles = set(
                    articles.filter(language=lang).values_list("slug", flat=True)
                )
                # Whether this language could have this plan at all. A curated
                # plan needs EVERY source, so most languages here can never get
                # most plans — and telling someone to write prose for a plan
                # that cannot exist is noise that trains them to skim the log.
                complete = set(by_slug) == set(book_slugs) and have_articles == set(
                    article_slugs
                )
                prose = _prose(slug, lang, title, description)
                if prose is None:
                    if complete:
                        self._report_untranslated(slug, lang)
                    continue
                t, d = prose
                if self._reconcile_existing(slug, lang, t, d):
                    continue
                if not complete:
                    continue  # a source isn't published in this language
                days = self._curated_days(items, by_slug)
                if not days:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Plan {slug} ({lang}): a chapter span does not resolve "
                            "in this edition; no plan row created."
                        )
                    )
                    continue
                self._create_plan(slug, lang, t, d, days)
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created curated plan {slug} ({lang}) with {len(days)} days "
                        f"across {len(book_slugs)} books and {len(article_slugs)} articles."
                    )
                )
        return created

    @staticmethod
    def _curated_days(items, by_slug) -> list[dict]:
        """Every item's days in order, as PlanDay field dicts: a whole book or a
        span of one is a day per chapter, an article is one day.

        Empty when a ``chapters(slug, first, last)`` span is not all there — an
        edition numbered differently would otherwise yield a plan with holes
        whose day count no longer matches its prose."""
        days: list[dict] = []
        for item in plan_items(items):
            if item[0] == "article":
                days.append({"article_slug": item[1]})
                continue
            _, bslug, first, last = item
            chapters = by_slug[bslug].chapters.order_by("order")
            if first is not None:
                chapters = chapters.filter(order__range=(first, last))
            orders = list(chapters.values_list("order", flat=True))
            if first is not None and orders != list(range(first, last + 1)):
                return []
            days += [{"book_slug": bslug, "chapter_order": o} for o in orders]
        return days
