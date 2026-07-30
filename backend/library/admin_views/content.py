"""Admin dashboard API — content inventory (stats, per-language, coverage)."""

from __future__ import annotations

from django.db.models import Count, F, Q, Sum
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from .. import golive, readiness
from ..models import (
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    Language,
    Plan,
    Sermon,
    Topic,
    TopicTranslation,
)
from ..views import _language_entry


class AdminStatsView(APIView):
    """Library-wide content statistics for the admin dashboard."""

    permission_classes = [IsAdminEmail]

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


class AdminLanguageDetailView(APIView):
    """Per-language drill-down: what's translated into a language, and the next
    few items to translate next.

    "Present" lists everything published (or drafted) in the language. The
    "todo" lists are the highest-priority English works (by ``sort_order``) that
    do *not* yet exist in the language — the natural next targets for the
    translate-book / write-biography pipelines. English is the source language,
    so it has no todo lists.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request, code):
        code = code.lower()
        return Response(
            {
                "language": _language_entry(code),
                "is_source": code == "en",
                "english_counts": self._english_counts(),
                "books": self._books(code),
                "sermons": self._sermons(code),
                "plans": self._plans(code),
                "bios": self._bios(code),
                "topics": self._topics(code),
                "todo": {
                    "books": self._books_todo(code),
                    "sermons": self._sermons_todo(code),
                    "plans": self._plans_todo(code),
                    "bios": self._bios_todo(code),
                    "topics": self._topics_todo(code),
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

    def _english_counts(self) -> dict:
        return {
            "books": Book.objects.filter(language="en", is_published=True).count(),
            "sermons": Sermon.objects.filter(language="en", is_published=True).count(),
            "plans": Plan.objects.filter(language="en", is_published=True).count(),
            "bios": Author.objects.exclude(bio_html="").count(),
        }


class AdminCoverageView(APIView):
    """Translation-coverage matrices: every canonical work (row) × language
    (column), so gaps across the whole library are visible at a glance.

    Books, sermons and plans each get their own matrix but share one column set
    (every language present in any of them, English first). A book cell carries
    its ``source_type``; sermon/plan cells are simply "present" (those models
    have no source_type). A missing language is absent from the row's ``cells``.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        codes = self._language_codes()
        return Response(
            {
                "languages": [_language_entry(c) for c in codes],
                "books": self._book_rows(),
                "sermons": self._sermon_rows(),
                "plans": self._plan_rows(),
            }
        )

    def _language_codes(self) -> list[str]:
        codes: set[str] = set()
        for model in (Book, Sermon, Plan):
            codes.update(model.objects.values_list("language", flat=True).distinct())
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
        return self._rows(records, lambda r: r["source_type"], with_author=True)

    def _sermon_rows(self) -> list[dict]:
        records = Sermon.objects.select_related("author").values(
            "slug", "language", "title", "author__name", "sort_order"
        )
        return self._rows(records, lambda r: "present", with_author=True)

    def _plan_rows(self) -> list[dict]:
        records = Plan.objects.values("slug", "language", "title", "sort_order")
        return self._rows(records, lambda r: "present", with_author=False)




class AdminLanguageReadinessView(APIView):
    """Is this language ready to go live, and what is still missing?

    Separate from the language detail view on purpose: the Bible check makes a
    live call to the Take Root API, and the detail page is loaded constantly —
    paying a network round trip on every visit just to show counts would be a
    poor trade. This is fetched when you actually ask the question.

    Read-only. Nothing here launches anything; the go-live action re-runs these
    same checks server-side rather than trusting a report a browser is holding.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request, code):
        lang = Language.objects.filter(code=code.lower()).first()
        if lang is None:
            return Response({"detail": "Unknown language."}, status=status.HTTP_404_NOT_FOUND)
        data = readiness.report(lang).as_dict()
        data["status"] = lang.status
        data["thresholds"] = {
            "min_books": lang.min_books,
            "min_sermons": lang.min_sermons,
            "min_bios": lang.min_bios,
            "min_plans": lang.min_plans,
            "require_all_topics": lang.require_all_topics,
            "require_complete_ui": lang.require_complete_ui,
        }
        return Response(data)


class AdminLanguageThresholdsView(APIView):
    """Edit a language's readiness bar.

    The bar is per-language and yours to set: a language with a big catalogue
    behind it should clear a higher one than a first beachhead language, and 0
    disables a check. Only thresholds are writable here — ``status`` is changed
    by the go-live action (which runs the checks) and identity belongs to the
    repo's seed, which never touches these fields once the row exists.
    """

    permission_classes = [IsAdminEmail]

    INT_FIELDS = ("min_books", "min_sermons", "min_bios", "min_plans")
    BOOL_FIELDS = ("require_all_topics", "require_complete_ui")

    def patch(self, request, code):
        lang = Language.objects.filter(code=code.lower()).first()
        if lang is None:
            return Response({"detail": "Unknown language."}, status=status.HTTP_404_NOT_FOUND)

        changed = []
        for f in self.INT_FIELDS:
            if f not in request.data:
                continue
            try:
                value = int(request.data[f])
            except (TypeError, ValueError):
                return Response(
                    {"detail": f"{f} must be a whole number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if value < 0:
                return Response(
                    {"detail": f"{f} cannot be negative (0 disables the check)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            setattr(lang, f, value)
            changed.append(f)

        for f in self.BOOL_FIELDS:
            if f in request.data:
                setattr(lang, f, bool(request.data[f]))
                changed.append(f)

        if not changed:
            return Response(
                {"detail": "Nothing to update."}, status=status.HTTP_400_BAD_REQUEST
            )
        lang.save(update_fields=changed)
        return Response(
            {
                "code": lang.code,
                "updated": changed,
                "thresholds": {
                    f: getattr(lang, f) for f in self.INT_FIELDS + self.BOOL_FIELDS
                },
            }
        )


class AdminLanguageGoLiveView(APIView):
    """Take a language live: re-check, record, and trigger the rebuild.

    The checks run again HERE rather than trusting what the browser was holding —
    that report could be minutes old and content can change underneath it. The
    button is a request to launch, not permission to.

    Returns 409 with the blockers when a language isn't ready. `force: true`
    launches anyway, for the case where you disagree with the bar rather than as
    a way around it; the response records that it was forced.
    """

    permission_classes = [IsAdminEmail]

    def post(self, request, code):
        lang = Language.objects.filter(code=code.lower()).first()
        if lang is None:
            return Response({"detail": "Unknown language."}, status=status.HTTP_404_NOT_FOUND)
        if lang.is_source:
            return Response(
                {"detail": "English is the source language; it is always live."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = golive.go_live(lang, force=bool(request.data.get("force")))
        if not result["launched"]:
            return Response(result, status=status.HTTP_409_CONFLICT)
        return Response(result)


class AdminLanguageDeployCheckView(APIView):
    """Did the launch actually reach readers?

    `status` says what was decided; this says what shipped. They are different
    facts — a prerendered site only reflects a decision after a build — and
    reporting one as the other is how a dashboard starts lying.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request, code):
        lang = Language.objects.filter(code=code.lower()).first()
        if lang is None:
            return Response({"detail": "Unknown language."}, status=status.HTTP_404_NOT_FOUND)
        return Response(golive.verify_deployed(lang))
