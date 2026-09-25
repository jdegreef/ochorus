"""Admin dashboard API — what content exists: library totals, one language's
drill-down, and the work x language coverage matrix.

Read-only. Administering a language as a thing — its Bible code, glossary,
readiness thresholds and the live switch — is ``languages.py``; this module only
borrows that module's ``language_settings`` so the drill-down can show a
language's configuration beside its content.
"""

from __future__ import annotations

from django.db.models import Count, F, Q, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from ..languages import known_codes
from ..models import (
    Article,
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    Language,
    Plan,
    Series,
    Sermon,
    Topic,
    TopicTranslation,
)
from ..views import _language_entry
from .languages import language_settings


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminStatsView(APIView):
    """Library-wide content statistics for the admin dashboard."""


    def get(self, request):
        return Response(
            {
                "totals": self._totals(),
                "languages": self._languages(),
                "source_types": self._source_types(),
                "author_translations": self._author_translations(),
                "attention": self._attention(),
                "recent_books": self._recent_books(),
            }
        )

    # -- sections --------------------------------------------------------------

    def _totals(self) -> dict:
        book_agg = Book.objects.aggregate(
            total=Count("id"),
            published=Count("id", filter=Q(is_published=True)),
        )
        sermon_agg = Sermon.objects.aggregate(
            total=Count("id"),
            published=Count("id", filter=Q(is_published=True)),
            words=Sum("word_count"),
        )
        plan_agg = Plan.objects.aggregate(
            total=Count("id"),
            published=Count("id", filter=Q(is_published=True)),
        )
        chapter_agg = Chapter.objects.aggregate(
            total=Count("id"), words=Sum("word_count")
        )
        # Distinct canonical works: one per slug regardless of how many languages
        # it's published in.
        works = Book.objects.values("slug").distinct().count()

        chapter_words = chapter_agg["words"] or 0
        sermon_words = sermon_agg["words"] or 0
        return {
            "works": works,
            "books": book_agg["total"],
            "published_books": book_agg["published"],
            "unpublished_books": book_agg["total"] - book_agg["published"],
            "chapters": chapter_agg["total"],
            "sermons": sermon_agg["total"],
            "published_sermons": sermon_agg["published"],
            "plans": plan_agg["total"],
            "published_plans": plan_agg["published"],
            "authors": Author.objects.count(),
            "authors_with_bio": Author.objects.exclude(bio="").count(),
            "languages": Book.objects.values("language").distinct().count(),
            "words": chapter_words + sermon_words,
            "chapter_words": chapter_words,
            "sermon_words": sermon_words,
        }

    def _languages(self) -> list[dict]:
        """Per-language content breakdown — every language in the REGISTRY, plus
        any code that has content but no row.

        This used to list only languages that already had a book, sermon or plan,
        which made starting a language impossible: the Translate buttons live on
        the per-language page, and a language with nothing in it never appeared
        here, so there was no way to reach the page that would give it content.
        Arabic sat fully wired — Bible, glossary, interface, RTL — and invisible.

        So the registry seeds the rows and content fills them in. A language with
        no content shows honest zeros, which is exactly the state you act on.
        """
        rows: dict[str, dict] = {}

        def row(code: str) -> dict:
            if code not in rows:
                entry = _language_entry(code)
                entry.update(
                    {
                        "books": 0,
                        "published_books": 0,
                        "chapters": 0,
                        "sermons": 0,
                        "plans": 0,
                        "bios": 0,
                        "articles": 0,
                        "words": 0,
                        "source_types": {
                            "public_domain": 0,
                            "ai_reviewed": 0,
                            "ai_unreviewed": 0,
                        },
                    }
                )
                rows[code] = entry
            return rows[code]

        # Seed from the registry first, so a language you haven't started yet is
        # still reachable — that page is where you queue the work that fills it.
        for lang in Language.objects.all():
            row(lang.code)

        for r in (
            Book.objects.values("language", "source_type").annotate(n=Count("id"))
        ):
            entry = row(r["language"])
            entry["books"] += r["n"]
            st = entry["source_types"]
            st[r["source_type"]] = st.get(r["source_type"], 0) + r["n"]

        for r in (
            Book.objects.filter(is_published=True)
            .values("language")
            .annotate(n=Count("id"))
        ):
            row(r["language"])["published_books"] = r["n"]

        for r in (
            Chapter.objects.values("book__language").annotate(
                n=Count("id"), words=Sum("word_count")
            )
        ):
            entry = row(r["book__language"])
            entry["chapters"] = r["n"]
            entry["words"] += r["words"] or 0

        for r in Sermon.objects.values("language").annotate(
            n=Count("id"), words=Sum("word_count")
        ):
            entry = row(r["language"])
            entry["sermons"] = r["n"]
            entry["words"] += r["words"] or 0

        for r in Plan.objects.values("language").annotate(n=Count("id")):
            row(r["language"])["plans"] = r["n"]

        # Translated long-form (bio_html) author biographies, per language. The
        # English row counts the canonical authors that have one.
        for r in (
            AuthorTranslation.objects.exclude(bio_html="")
            .values("language")
            .annotate(n=Count("id"))
        ):
            row(r["language"])["bios"] = r["n"]
        en_bios = Author.objects.exclude(bio_html="").count()
        if en_bios:
            row("en")["bios"] = en_bios

        # Articles are authorless per-language rows on a shared slug (like plans),
        # so a plain per-language count is the whole story — no source split.
        for r in Article.objects.values("language").annotate(n=Count("id")):
            row(r["language"])["articles"] = r["n"]

        return sorted(
            rows.values(),
            key=lambda e: (e["code"] != "en", -e["books"], e["code"]),
        )

    def _source_types(self) -> dict:
        counts = {
            r["source_type"]: r["n"]
            for r in Book.objects.values("source_type").annotate(n=Count("id"))
        }
        return {
            "public_domain": counts.get("public_domain", 0),
            "ai_reviewed": counts.get("ai_reviewed", 0),
            "ai_unreviewed": counts.get("ai_unreviewed", 0),
        }

    def _author_translations(self) -> dict:
        agg = AuthorTranslation.objects.aggregate(
            total=Count("id"),
            reviewed=Count("id", filter=Q(reviewed=True)),
            # Translated from English that has since been replaced. Independent
            # of `reviewed` — an approved translation can still go stale.
            stale=Count("id", filter=Q(source_stale=True)),
        )
        total = agg["total"] or 0
        reviewed = agg["reviewed"] or 0
        return {
            "total": total,
            "reviewed": reviewed,
            "unreviewed": total - reviewed,
            "stale": agg["stale"] or 0,
        }

    def _attention(self) -> dict:
        """Content-health signals worth surfacing at a glance."""
        return {
            "unpublished_books": Book.objects.filter(is_published=False).count(),
            "unpublished_sermons": Sermon.objects.filter(is_published=False).count(),
            "unreviewed_translations": Book.objects.filter(
                source_type=Book.SourceType.AI_UNREVIEWED
            ).count(),
            # Imprints are bylines, not people — they never get a bio, so
            # counting them would leave this to-do permanently unfinishable.
            "authors_without_bio": Author.objects.filter(bio="", is_imprint=False).count(),
            "empty_chapters": Chapter.objects.filter(word_count=0).count(),
        }

    def _recent_books(self, limit: int = 8) -> list[dict]:
        books = (
            Book.objects.select_related("author")
            .order_by("-created_at")[:limit]
        )
        return [
            {
                "slug": b.slug,
                "title": b.title,
                "language": b.language,
                "author": b.author.name,
                "source_type": b.source_type,
                "is_published": b.is_published,
                "created_at": b.created_at.isoformat(),
            }
            for b in books
        ]


# How many "next to work on" items to surface per content type. Ten is a
# working session's worth of choices — enough to pick around a title you don't
# want yet, short enough to stay a shortlist rather than a second inventory.
TODO_LIMIT = 10


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminLanguageDetailView(APIView):
    """Per-language drill-down: what's translated into a language, and the next
    few items to translate next.

    "Present" lists everything published (or drafted) in the language. The
    "todo" lists are the highest-priority English works (by ``sort_order``) that
    do *not* yet exist in the language — the natural next targets for the
    translate-book / write-biography pipelines. English is the source language,
    so it has no todo lists.
    """


    def get(self, request, code):
        code = code.lower()
        lang = Language.objects.filter(code=code).first()
        return Response(
            {
                "language": _language_entry(code),
                # None for a code that has content but no registry row — the page
                # still renders; there is just nothing to configure.
                "settings": language_settings(lang) if lang else None,
                "is_source": code == "en",
                "english_counts": self._english_counts(),
                "books": self._books(code),
                "sermons": self._sermons(code),
                "plans": self._plans(code),
                "bios": self._bios(code),
                "topics": self._topics(code),
                "articles": self._articles(code),
                "todo": {
                    "books": self._books_todo(code),
                    "sermons": self._sermons_todo(code),
                    "plans": self._plans_todo(code),
                    "bios": self._bios_todo(code),
                    "topics": self._topics_todo(code),
                    "articles": self._articles_todo(code),
                },
            }
        )

    # -- present ---------------------------------------------------------------

    def _books(self, code) -> list[dict]:
        books = (
            Book.objects.filter(language=code)
            .select_related("author")
            .annotate(num_chapters=Count("chapters"))
            .order_by("sort_order", "title")
        )
        return [
            {
                "slug": b.slug,
                "title": b.title,
                "author": b.author.name,
                "chapters": b.num_chapters,
                "source_type": b.source_type,
                "is_published": b.is_published,
            }
            for b in books
        ]

    def _sermons(self, code) -> list[dict]:
        sermons = (
            Sermon.objects.filter(language=code)
            .select_related("author")
            .order_by("sort_order", "title")
        )
        return [
            {
                "slug": s.slug,
                "title": s.title,
                "author": s.author.name,
                "word_count": s.word_count,
                "is_published": s.is_published,
            }
            for s in sermons
        ]

    def _plans(self, code) -> list[dict]:
        plans = (
            Plan.objects.filter(language=code)
            .annotate(num_days=Count("days"))
            .order_by("sort_order", "title")
        )
        return [
            {
                "slug": p.slug,
                "title": p.title,
                "days": p.num_days,
                "is_published": p.is_published,
            }
            for p in plans
        ]

    def _bios(self, code) -> list[dict]:
        """Authors whose long-form (bio_html) biography exists in this language."""
        if code == "en":
            authors = Author.objects.exclude(bio_html="").order_by("name")
            return [
                {"slug": a.slug, "name": a.name, "reviewed": True} for a in authors
            ]
        trs = (
            AuthorTranslation.objects.filter(language=code)
            .exclude(bio_html="")
            .select_related("author")
            .order_by("author__name")
        )
        return [
            {"slug": t.author.slug, "name": t.author.name, "reviewed": t.reviewed}
            for t in trs
        ]

    def _articles(self, code) -> list[dict]:
        """Articles that exist in this language. Like a sermon, an article is a
        single body with no author; it carries ``source_type`` so the page can
        badge an unreviewed AI translation."""
        articles = (
            Article.objects.filter(language=code)
            # The list needs none of the heavy text columns — defer them so the
            # admin query stays lean, as ArticleListView does for the shelf.
            .defer("body_html", "description", "related")
            .order_by("sort_order", "h1")
        )
        return [
            {
                "slug": a.slug,
                "title": a.h1,
                "word_count": a.word_count,
                "source_type": a.source_type,
                "is_published": a.is_published,
            }
            for a in articles
        ]

    # -- next to work on -------------------------------------------------------

    def _books_todo(self, code) -> list[dict]:
        if code == "en":
            return []
        have = set(Book.objects.filter(language=code).values_list("slug", flat=True))
        qs = (
            Book.objects.filter(language="en", is_published=True)
            .exclude(slug__in=have)
            .select_related("author")
            .order_by("sort_order", "title")[:TODO_LIMIT]
        )
        return [
            {"slug": b.slug, "title": b.title, "author": b.author.name} for b in qs
        ]

    def _sermons_todo(self, code) -> list[dict]:
        if code == "en":
            return []
        have = set(Sermon.objects.filter(language=code).values_list("slug", flat=True))
        candidates = (
            Sermon.objects.filter(language="en", is_published=True)
            .exclude(slug__in=have)
            .select_related("author")
            .order_by("sort_order", "title")
        )
        # Round-robin across preachers so the suggestions span different voices
        # (one Spurgeon, one Moody, ...) instead of whoever dominates the top of
        # the sort_order — repeats only once every preacher is represented.
        queues: dict[int, list[Sermon]] = {}
        for s in candidates:
            queues.setdefault(s.author_id, []).append(s)
        picked: list[Sermon] = []
        while queues and len(picked) < TODO_LIMIT:
            for author_id in list(queues):
                picked.append(queues[author_id].pop(0))
                if not queues[author_id]:
                    del queues[author_id]
                if len(picked) >= TODO_LIMIT:
                    break
        return [
            {"slug": s.slug, "title": s.title, "author": s.author.name}
            for s in picked
        ]

    def _topics(self, code) -> list[dict]:
        """Shelves that exist in this language — i.e. that have a title here.

        A shelf without a translated title is not "partly there": it is hidden
        from the language entirely (``Topic.is_translated_into``), so presence is
        exactly title-presence.
        """
        topics = Topic.objects.filter(is_published=True).order_by("sort_order", "title")
        if code == "en":
            return [{"slug": t.slug, "title": t.title} for t in topics]
        by_slug = {
            tr.topic_id: tr
            for tr in TopicTranslation.objects.filter(language=code).exclude(title="")
        }
        return [
            {"slug": t.slug, "title": by_slug[t.id].title}
            for t in topics
            if t.id in by_slug
        ]

    def _topics_todo(self, code) -> list[dict]:
        """Shelves with no title in this language — each one an invisible shelf.

        Not truncated to TODO_LIMIT like the others: there are only a handful of
        topics, and the list is a completeness checklist rather than a ranked
        queue — a language needs *all* of them or its shelf page is short.
        """
        if code == "en":
            return []
        have = set(
            TopicTranslation.objects.filter(language=code)
            .exclude(title="")
            .values_list("topic__slug", flat=True)
        )
        qs = (
            Topic.objects.filter(is_published=True)
            .exclude(slug__in=have)
            .order_by("sort_order", "title")
        )
        return [{"slug": t.slug, "title": t.title} for t in qs]

    def _plans_todo(self, code) -> list[dict]:
        if code == "en":
            return []
        have = set(Plan.objects.filter(language=code).values_list("slug", flat=True))
        qs = (
            Plan.objects.filter(language="en", is_published=True)
            .exclude(slug__in=have)
            .order_by("sort_order", "title")[:TODO_LIMIT]
        )
        return [{"slug": p.slug, "title": p.title} for p in qs]

    def _bios_todo(self, code) -> list[dict]:
        """Untranslated biographies, the authors who carry most of the library first.

        Alphabetical order buried the people who matter — the queue opened on
        A. B. Simpson while Spurgeon, with 5 books and 13 sermons, sat below the
        fold.

        The ranking is by **English** works, deliberately, and it is a bet on
        future rather than current reach: an author with eighteen works in the
        library is one whose works you are most likely to translate next, so his
        biography is the one that will end up serving the most pages. Note the
        consequence — for a language with almost nothing translated yet, the top
        of this queue has no works in that language at all, and the bio is
        reachable only from the localized biographies index until they arrive.
        Ranking by works *in the target language* instead would invert that,
        favouring immediate reach; a hybrid (target-language works first,
        English as tie-break) is the option if this ever needs to serve both.

        Books break ties over sermons (a book is the larger investment), name
        last so the order is stable. Imprints are excluded, as they are on the
        public biographies page: a house byline is not a person, and it carries
        enough titles to head this queue on volume alone.

        The counts ride along so the ranking explains itself in the UI rather
        than looking like an arbitrary order.
        """
        if code == "en":
            return []
        translated = set(
            AuthorTranslation.objects.filter(language=code)
            .exclude(bio_html="")
            .values_list("author__slug", flat=True)
        )
        qs = (
            Author.objects.filter(is_imprint=False)
            .exclude(bio_html="")
            .exclude(slug__in=translated)
            .with_work_counts("en")
            .annotate(num_works=F("num_books") + F("num_sermons"))
            .order_by("-num_works", "-num_books", "name")[:TODO_LIMIT]
        )
        return [
            {
                "slug": a.slug,
                "name": a.name,
                "book_count": a.num_books,
                "sermon_count": a.num_sermons,
            }
            for a in qs
        ]

    def _articles_todo(self, code) -> list[dict]:
        """English articles not yet in this language, highest sort_order first —
        the same shape as _books_todo but authorless (an article has no byline)."""
        if code == "en":
            return []
        have = set(Article.objects.filter(language=code).values_list("slug", flat=True))
        qs = (
            Article.objects.filter(language="en", is_published=True)
            .exclude(slug__in=have)
            .order_by("sort_order", "h1")[:TODO_LIMIT]
        )
        return [{"slug": a.slug, "title": a.h1} for a in qs]

    def _english_counts(self) -> dict:
        return {
            "books": Book.objects.filter(language="en", is_published=True).count(),
            "sermons": Sermon.objects.filter(language="en", is_published=True).count(),
            "plans": Plan.objects.filter(language="en", is_published=True).count(),
            "bios": Author.objects.exclude(bio_html="").count(),
            "articles": Article.objects.filter(language="en", is_published=True).count(),
        }


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminCoverageView(APIView):
    """Translation-coverage matrices: every canonical work (row) × language
    (column), so gaps across the whole library are visible at a glance.

    Books, sermons, plans, biographies and articles each get their own matrix but
    share one column set (every language present in any of them, English first). A
    book cell carries its ``source_type``; an article's translated cells do too, its
    English original shown as "present" (see ``_article_rows``); a biography's translated cells carry
    ai_reviewed / ai_unreviewed (from ``AuthorTranslation.reviewed``) with the
    English original shown as "present"; sermon/plan cells are simply "present"
    (those models have no source_type). A missing language is absent from the
    row's ``cells``.
    """


    def get(self, request):
        codes = self._language_codes()
        # A column is only a translation target when it's a registered language
        # (a Book/Sermon can carry a language code the translation registry never
        # adopted — e.g. an early bulk import). `queueable` mirrors exactly what
        # the translation-jobs POST accepts (`language != "en" and in known_codes`),
        # so the admin UI only offers the queue where a job would actually be filed.
        registry = known_codes()
        unmet = self._unmet_by_language()
        return Response(
            {
                "languages": [
                    {
                        **_language_entry(c),
                        "queueable": c != "en" and c in registry,
                        # Reader demand this language isn't answering — a hint for
                        # which column to translate into next.
                        "unmet_searches": unmet.get(c, 0),
                    }
                    for c in codes
                ],
                "books": self._book_rows(),
                "sermons": self._sermon_rows(),
                "plans": self._plan_rows(),
                "bios": self._bio_rows(),
                "articles": self._article_rows(),
                # The series the Books matrix can be narrowed to (each book row
                # carries its `series`), so a whole series' gaps in one language
                # queue as that column's "queue all".
                "series": list(Series.objects.values("slug", "title")),
            }
        )

    def _unmet_by_language(self) -> dict[str, int]:
        """Zero-result searches per language over the last 30 days — the demand a
        language's readers have that its content isn't answering. Cheap: one
        grouped aggregate over the anonymous SearchQueryLog."""
        from datetime import timedelta

        from django.utils import timezone

        from ..models import SearchQueryLog

        since = timezone.now() - timedelta(days=30)
        return {
            r["language"]: r["n"]
            for r in SearchQueryLog.objects.filter(created_at__gte=since, result_count=0)
            .values("language")
            .annotate(n=Count("id"))
        }

    def _language_codes(self) -> list[str]:
        codes: set[str] = {"en"}  # bios' English source is Author.bio_html, not a row
        for model in (Book, Sermon, Plan, Article):
            codes.update(model.objects.values_list("language", flat=True).distinct())
        codes.update(
            AuthorTranslation.objects.exclude(bio_html="")
            .values_list("language", flat=True)
            .distinct()
        )
        return sorted(codes, key=lambda c: (c != "en", c))

    def _rows(self, records, cell_value, *, with_author: bool) -> list[dict]:
        """Collapse per-(slug, language) records into one row per slug.

        ``records`` is an iterable of dicts with slug/language/title/sort_order
        (and author__name when ``with_author``). The canonical title/author is
        taken from the English row when present, else the first seen.
        """
        rows: dict[str, dict] = {}
        for r in records:
            slug = r["slug"]
            row = rows.get(slug)
            is_en = r["language"] == "en"
            if row is None:
                row = rows[slug] = {
                    "slug": slug,
                    "title": r["title"],
                    "sort_order": r["sort_order"],
                    "cells": {},
                    "_have_en": False,
                }
                if with_author:
                    row["author"] = r["author__name"]
            # Prefer the English row's display metadata.
            if is_en and not row["_have_en"]:
                row["title"] = r["title"]
                row["sort_order"] = r["sort_order"]
                if with_author:
                    row["author"] = r["author__name"]
                row["_have_en"] = True
            row["cells"][r["language"]] = cell_value(r)
        ordered = sorted(rows.values(), key=lambda r: (r["sort_order"], r["title"]))
        for r in ordered:
            r.pop("sort_order")
            r.pop("_have_en")
        return ordered

    def _book_rows(self) -> list[dict]:
        records = Book.objects.select_related("author").values(
            "slug", "language", "source_type", "title", "author__name", "sort_order"
        )
        rows = self._rows(records, lambda r: r["source_type"], with_author=True)
        # A row is a work across languages, and series membership is per edition
        # row — so take it from any edition that carries it (they agree; the
        # fixture gates hold a series to its volumes). A book in no series gets
        # neither key.
        membership = {
            slug: (series, position)
            for slug, series, position in Book.objects.filter(series__isnull=False)
            .values_list("slug", "series__slug", "series_position")
        }
        for row in rows:
            if found := membership.get(row["slug"]):
                row["series"], row["series_position"] = found
        return rows

    def _sermon_rows(self) -> list[dict]:
        records = Sermon.objects.select_related("author").values(
            "slug", "language", "title", "author__name", "sort_order"
        )
        return self._rows(records, lambda r: "present", with_author=True)

    def _plan_rows(self) -> list[dict]:
        records = Plan.objects.values("slug", "language", "title", "sort_order")
        return self._rows(records, lambda r: "present", with_author=False)

    def _article_rows(self) -> list[dict]:
        """Articles (row = slug) × language. Authorless, like a plan; the display
        title is the ``h1`` headline (an article has no ``title`` field).

        A translated cell carries its ``source_type`` (ai_reviewed / ai_unreviewed)
        like a book. The English original is site writing, not a public-domain
        work — it only carries ``public_domain`` as the model default — so it
        reads "present" rather than "PD".
        """
        records = Article.objects.annotate(title=F("h1")).values(
            "slug", "language", "source_type", "title", "sort_order"
        )
        return self._rows(
            records,
            lambda r: "present" if r["source_type"] == Book.SourceType.PUBLIC_DOMAIN else r["source_type"],
            with_author=False,
        )

    def _bio_rows(self) -> list[dict]:
        """Author long-form biographies (row = author) × language.

        The English biography lives on ``Author.bio_html``; each translation is
        an ``AuthorTranslation`` with its own ``bio_html`` and a ``reviewed``
        flag, so a translated cell reads ai_reviewed / ai_unreviewed like a book
        does and the English original shows as "present". A bio counts only when
        its long-form body is non-empty — the same test the language pages use.
        Doesn't go through ``_rows``: the English source and the translations
        live in two different models, not one per-(slug, language) table.
        """
        rows: dict[str, dict] = {}
        for a in Author.objects.exclude(bio_html="").values("slug", "name"):
            rows[a["slug"]] = {"slug": a["slug"], "title": a["name"], "cells": {"en": "present"}}
        translations = AuthorTranslation.objects.exclude(bio_html="").values(
            "author__slug", "author__name", "language", "reviewed"
        )
        for t in translations:
            slug = t["author__slug"]
            row = rows.get(slug)
            if row is None:
                # A translated bio whose English original is blank — unusual, but
                # show it rather than silently drop the work.
                row = rows[slug] = {"slug": slug, "title": t["author__name"], "cells": {}}
            row["cells"][t["language"]] = "ai_reviewed" if t["reviewed"] else "ai_unreviewed"
        return sorted(rows.values(), key=lambda r: r["title"].lower())


