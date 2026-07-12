"""Admin dashboard API: aggregate content stats for the ``/admin`` page.

A single read-only endpoint that rolls up how much content the library holds and
how it breaks down by language and source type. Gated to allowlisted admins (see
``accounts.permissions``). Everything is computed with a handful of grouped
aggregate queries — no per-row Python loops over the whole library.
"""

from __future__ import annotations

from django.db.models import Count, Q, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from .models import Author, AuthorTranslation, Book, Chapter, Plan, Sermon
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
