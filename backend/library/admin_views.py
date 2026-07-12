"""Admin dashboard API: aggregate content stats for the ``/admin`` page.

A single read-only endpoint that rolls up how much content the library holds and
how it breaks down by language and source type. Gated to allowlisted admins (see
``accounts.permissions``). Everything is computed with a handful of grouped
aggregate queries — no per-row Python loops over the whole library.
"""

from __future__ import annotations

import re

from django.db.models import Count, Max, Q, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from .models import Author, AuthorTranslation, Book, Chapter, Plan, PlanDay, Sermon
from .views import _language_entry


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
        """Per-language content breakdown, one row per language code that has
        any book, sermon or plan. Merged from four grouped queries."""
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
        )
        total = agg["total"] or 0
        reviewed = agg["reviewed"] or 0
        return {"total": total, "reviewed": reviewed, "unreviewed": total - reviewed}

    def _attention(self) -> dict:
        """Content-health signals worth surfacing at a glance."""
        return {
            "unpublished_books": Book.objects.filter(is_published=False).count(),
            "unpublished_sermons": Sermon.objects.filter(is_published=False).count(),
            "unreviewed_translations": Book.objects.filter(
                source_type=Book.SourceType.AI_UNREVIEWED
            ).count(),
            "authors_without_bio": Author.objects.filter(bio="").count(),
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


# How many "next to work on" items to surface per content type.
TODO_LIMIT = 4


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
                "todo": {
                    "books": self._books_todo(code),
                    "sermons": self._sermons_todo(code),
                    "plans": self._plans_todo(code),
                    "bios": self._bios_todo(code),
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
        qs = (
            Sermon.objects.filter(language="en", is_published=True)
            .exclude(slug__in=have)
            .select_related("author")
            .order_by("sort_order", "title")[:TODO_LIMIT]
        )
        return [
            {"slug": s.slug, "title": s.title, "author": s.author.name} for s in qs
        ]

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
        if code == "en":
            return []
        translated = set(
            AuthorTranslation.objects.filter(language=code)
            .exclude(bio_html="")
            .values_list("author__slug", flat=True)
        )
        qs = (
            Author.objects.exclude(bio_html="")
            .exclude(slug__in=translated)
            .order_by("name")[:TODO_LIMIT]
        )
        return [{"slug": a.slug, "name": a.name} for a in qs]

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


class AdminReviewQueueView(APIView):
    """The AI-translation review queue, with one-click approve.

    GET lists unreviewed AI translations — books (``source_type`` ai_unreviewed)
    and author bios (``AuthorTranslation.reviewed`` False). POST approves one,
    mirroring the approve_translation / approve_author_translation commands:
    a book flips ai_unreviewed → ai_reviewed (removing the "awaiting review"
    badge in the reader); a bio flips reviewed → True. The change is written to
    the live database immediately.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        return Response({"books": self._books(), "bios": self._bios()})

    def _books(self) -> list[dict]:
        qs = (
            Book.objects.filter(source_type=Book.SourceType.AI_UNREVIEWED)
            .select_related("author")
            .annotate(num_chapters=Count("chapters"))
            .order_by("language", "sort_order", "title")
        )
        return [
            {
                "slug": b.slug,
                "language": b.language,
                "title": b.title,
                "author": b.author.name,
                "chapters": b.num_chapters,
            }
            for b in qs
        ]

    def _bios(self) -> list[dict]:
        qs = (
            AuthorTranslation.objects.filter(reviewed=False)
            .exclude(bio="", bio_html="")
            .select_related("author")
            .order_by("language", "author__name")
        )
        return [
            {
                "slug": t.author.slug,
                "language": t.language,
                "name": t.author.name,
                "has_short": bool(t.bio),
                "has_long": bool(t.bio_html),
            }
            for t in qs
        ]

    def post(self, request):
        kind = request.data.get("kind")
        slug = request.data.get("slug")
        language = request.data.get("language")
        if kind not in ("book", "bio") or not slug or not language:
            return Response(
                {"detail": "kind ('book'|'bio'), slug and language are required."},
                status=400,
            )
        if kind == "book":
            return self._approve_book(slug, language)
        return self._approve_bio(slug, language)

    def _approve_book(self, slug, language):
        try:
            book = Book.objects.get(slug=slug, language=language)
        except Book.DoesNotExist:
            return Response({"detail": "No such book translation."}, status=404)
        if book.source_type == Book.SourceType.PUBLIC_DOMAIN:
            return Response(
                {"detail": "That book is a public-domain original, not a translation."},
                status=400,
            )
        book.source_type = Book.SourceType.AI_REVIEWED
        book.save(update_fields=["source_type"])
        return Response({"ok": True, "kind": "book", "slug": slug, "language": language})

    def _approve_bio(self, slug, language):
        try:
            tr = AuthorTranslation.objects.get(author__slug=slug, language=language)
        except AuthorTranslation.DoesNotExist:
            return Response({"detail": "No such author-bio translation."}, status=404)
        tr.reviewed = True
        tr.save(update_fields=["reviewed"])
        return Response({"ok": True, "kind": "bio", "slug": slug, "language": language})


# --- Content audit (quality + integrity) -------------------------------------

# A chapter title the chapterizer failed to capture: empty, or a bare
# "Chapter <n>" with no real heading.
GENERIC_TITLE = re.compile(r"^chapter\s+[\divxlc]+\.?$", re.IGNORECASE)
# Sentence-final punctuation; a body not ending in one of these before the next
# chapter suggests a mid-sentence split.
TERMINAL_PUNCT = tuple('.!?"\'”’»)')
# Per-list cap so the payload stays bounded on a large library; totals are still
# reported.
AUDIT_LIMIT = 100


def _capped(items: list) -> dict:
    return {"total": len(items), "items": items[:AUDIT_LIMIT]}


class AdminAuditView(APIView):
    """Content-quality and data-integrity audit for the admin dashboard.

    Quality checks port the ``book-qa`` skill's heuristics (generic titles,
    tiny/giant/fragmented chapters, missing drop caps, mid-sentence splits,
    duplicate titles). Integrity checks cover structural problems (empty books,
    empty chapters, chapter-order gaps, broken reading-plan day references).

    Read-only, admin-gated. One streamed pass over chapters plus a few small
    aggregate/lookup queries; heuristics are advisory — read the body before
    acting (see the skill's known-accepted list).
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        quality, per_book = self._scan_chapters()
        quality["duplicate_titles"] = self._duplicate_titles(per_book["titles"])
        integrity = {
            "empty_books": _capped(self._empty_books()),
            "empty_chapters": quality.pop("_empty_chapters"),
            "order_gaps": _capped(self._order_gaps(per_book["orders"])),
            "broken_plan_days": _capped(self._broken_plan_days()),
        }
        return Response({"quality": quality, "integrity": integrity})

    def _scan_chapters(self):
        maxima = {
            r["book_id"]: r["mx"]
            for r in Chapter.objects.values("book_id").annotate(mx=Max("order"))
        }
        generic, tiny, giant, fragmented, dropcap, mid_split, empty = (
            [], [], [], [], [], [], []
        )
        titles: dict[str, list[str]] = {}
        orders: dict[str, list[int]] = {}

        rows = Chapter.objects.select_related("book").values(
            "book_id", "book__slug", "book__language", "order", "title",
            "word_count", "body_html", "body_text",
        )
        for c in rows.iterator(chunk_size=50):
            slug = c["book__slug"]
            lang = c["book__language"]
            order = c["order"]
            title = (c["title"] or "").strip()
            wc = c["word_count"] or 0
            body = (c["body_text"] or "").strip()

            titles.setdefault(slug, []).append(title)
            orders.setdefault(slug, []).append(order)

            def finding(**extra):
                return {"book": slug, "language": lang, "order": order, "title": title, **extra}

            if not title or GENERIC_TITLE.match(title):
                generic.append(finding())
            if not body or wc == 0:
                empty.append(finding())
                continue  # remaining checks need body text
            if 0 < wc < 150:
                tiny.append(finding(word_count=wc))
            if wc > 8000:
                giant.append(finding(word_count=wc))

            paras = c["body_html"].count("<p")
            if paras >= 10 and wc >= 100 and wc / paras < 20:
                fragmented.append(finding(avg_words=round(wc / paras, 1), paragraphs=paras))

            first_alpha = next((ch for ch in body if ch.isalpha()), "")
            if first_alpha and first_alpha.islower():
                dropcap.append(finding(starts=body[:40]))

            if order < maxima.get(c["book_id"], order) and not body.endswith(TERMINAL_PUNCT):
                mid_split.append(finding(ends=body[-40:]))

        quality = {
            "generic_titles": _capped(generic),
            "tiny_chapters": _capped(tiny),
            "giant_chapters": _capped(giant),
            "fragmented": _capped(fragmented),
            "missing_dropcap": _capped(dropcap),
            "mid_sentence_splits": _capped(mid_split),
            "_empty_chapters": _capped(empty),
        }
        return quality, {"titles": titles, "orders": orders}

    def _duplicate_titles(self, titles_by_book: dict) -> dict:
        out = []
        for slug, titles in titles_by_book.items():
            seen: dict[str, int] = {}
            for t in titles:
                if t:
                    seen[t] = seen.get(t, 0) + 1
            for title, n in seen.items():
                if n > 1:
                    out.append({"book": slug, "title": title, "count": n})
        out.sort(key=lambda r: (-r["count"], r["book"]))
        return _capped(out)

    def _empty_books(self) -> list[dict]:
        books = (
            Book.objects.annotate(n=Count("chapters"))
            .filter(n=0)
            .select_related("author")
            .order_by("language", "slug")
        )
        return [
            {"book": b.slug, "language": b.language, "title": b.title, "author": b.author.name}
            for b in books
        ]

    def _order_gaps(self, orders_by_book: dict) -> list[dict]:
        out = []
        for slug, orders in orders_by_book.items():
            present = set(orders)
            expected = set(range(1, max(orders) + 1))
            missing = sorted(expected - present)
            if missing:
                out.append({"book": slug, "missing": missing, "count": len(orders)})
        out.sort(key=lambda r: r["book"])
        return out

    def _broken_plan_days(self) -> list[dict]:
        valid = set(
            Chapter.objects.values_list("book__slug", "book__language", "order")
        )
        out = []
        days = PlanDay.objects.select_related("plan").values(
            "plan__slug", "plan__language", "day", "book_slug", "chapter_order"
        )
        for d in days:
            key = (d["book_slug"], d["plan__language"], d["chapter_order"])
            if key not in valid:
                out.append(
                    {
                        "plan": d["plan__slug"],
                        "language": d["plan__language"],
                        "day": d["day"],
                        "book": d["book_slug"],
                        "order": d["chapter_order"],
                    }
                )
        out.sort(key=lambda r: (r["plan"], r["day"]))
        return out


class AdminEngagementView(APIView):
    """Reading-engagement analytics from ReadingProgress / ChapterMarks.

    Aggregate-only — counts and per-book/-language rollups, never individual
    readers' identities. "Active" is distinct profiles whose progress was
    touched within the window; "finishers" reached (or passed) the book's last
    English chapter.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        from datetime import timedelta

        from django.utils import timezone

        from reading.models import ChapterMarks, ReadingProgress

        now = timezone.now()

        def active(days):
            return (
                ReadingProgress.objects.filter(updated_at__gte=now - timedelta(days=days))
                .values("profile")
                .distinct()
                .count()
            )

        overview = {
            "readers": ReadingProgress.objects.values("profile").distinct().count(),
            "progress_rows": ReadingProgress.objects.count(),
            "active_1d": active(1),
            "active_7d": active(7),
            "active_30d": active(30),
            "readers_with_marks": ChapterMarks.objects.exclude(marks=[])
            .values("profile")
            .distinct()
            .count(),
            "marked_chapters": ChapterMarks.objects.exclude(marks=[]).count(),
            "total_users": self._total_users(),
        }
        return Response(
            {
                "overview": overview,
                "most_read": self._most_read(),
                "most_marked": self._most_marked(),
                "by_language": self._by_language(),
                "weekly_active": self._weekly_active(now),
            }
        )

    def _total_users(self) -> int:
        from accounts.models import UserProfile

        return UserProfile.objects.count()

    def _book_meta(self) -> dict:
        meta: dict[str, tuple[str, str]] = {}
        for b in Book.objects.values("slug", "language", "title", "author__name"):
            if b["language"] == "en" or b["slug"] not in meta:
                meta[b["slug"]] = (b["title"], b["author__name"])
        return meta

    def _chapter_counts(self) -> dict:
        return {
            r["book__slug"]: r["n"]
            for r in Chapter.objects.filter(book__language="en")
            .values("book__slug")
            .annotate(n=Count("id"))
        }

    def _most_read(self, limit: int = 10) -> list[dict]:
        from reading.models import ReadingProgress

        meta = self._book_meta()
        counts = self._chapter_counts()
        top = (
            ReadingProgress.objects.values("book_slug")
            .annotate(readers=Count("profile", distinct=True))
            .order_by("-readers")[:limit]
        )
        out = []
        for r in top:
            slug = r["book_slug"]
            title, author = meta.get(slug, (slug, ""))
            length = counts.get(slug)
            finishers = (
                ReadingProgress.objects.filter(
                    book_slug=slug, chapter_order__gte=length
                )
                .values("profile")
                .distinct()
                .count()
                if length
                else 0
            )
            out.append(
                {
                    "slug": slug,
                    "title": title,
                    "author": author,
                    "readers": r["readers"],
                    "finishers": finishers,
                }
            )
        return out

    def _most_marked(self, limit: int = 10) -> list[dict]:
        from reading.models import ChapterMarks

        meta = self._book_meta()
        top = (
            ChapterMarks.objects.exclude(marks=[])
            .values("book_slug")
            .annotate(readers=Count("profile", distinct=True), chapters=Count("id"))
            .order_by("-readers", "-chapters")[:limit]
        )
        out = []
        for r in top:
            title, author = meta.get(r["book_slug"], (r["book_slug"], ""))
            out.append(
                {
                    "slug": r["book_slug"],
                    "title": title,
                    "author": author,
                    "readers": r["readers"],
                    "chapters": r["chapters"],
                }
            )
        return out

    def _by_language(self) -> list[dict]:
        from reading.models import ReadingProgress

        rows = (
            ReadingProgress.objects.values("language")
            .annotate(readers=Count("profile", distinct=True))
            .order_by("-readers")
        )
        out = []
        for r in rows:
            entry = _language_entry(r["language"])
            entry["readers"] = r["readers"]
            out.append(entry)
        return out

    def _weekly_active(self, now, weeks: int = 8) -> list[dict]:
        from datetime import timedelta

        from reading.models import ReadingProgress

        today = now.date()
        this_week = today - timedelta(days=today.weekday())  # Monday
        out = []
        for i in range(weeks - 1, -1, -1):
            start = this_week - timedelta(weeks=i)
            end = start + timedelta(weeks=1)
            readers = (
                ReadingProgress.objects.filter(
                    updated_at__date__gte=start, updated_at__date__lt=end
                )
                .values("profile")
                .distinct()
                .count()
            )
            out.append({"week": start.isoformat(), "readers": readers})
        return out
