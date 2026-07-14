"""Admin dashboard API — per-work detail and library export."""

from __future__ import annotations

from django.db.models import Count, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from ..models import Author, Book, Plan, Sermon
from ..views import _language_entry
from .quality import chapter_flags


class AdminBookDetailView(APIView):
    """A single canonical work across all its languages, for the admin.

    Each language row carries its metadata (source, cover, links) and its
    chapter list with word counts and quality flags (see ``chapter_flags``),
    plus ids for deep-linking into the Django admin. English is listed first.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request, slug):
        books = list(Book.objects.filter(slug=slug).select_related("author"))
        if not books:
            return Response({"detail": "No such work."}, status=404)
        canonical = next((b for b in books if b.language == "en"), books[0])

        languages = []
        for b in sorted(books, key=lambda x: (x.language != "en", x.language)):
            rows = list(
                b.chapters.order_by("order").values(
                    "order", "title", "word_count", "body_text", "body_html"
                )
            )
            max_order = max((r["order"] for r in rows), default=0)
            chapters = []
            for r in rows:
                chapters.append(
                    {
                        "order": r["order"],
                        "title": r["title"],
                        "word_count": r["word_count"] or 0,
                        "flags": chapter_flags(
                            r["title"], r["word_count"] or 0,
                            r["body_text"], r["body_html"],
                            r["order"] < max_order,
                        ),
                    }
                )
            languages.append(
                {
                    **_language_entry(b.language),
                    "id": b.id,
                    "title": b.title,
                    "subtitle": b.subtitle,
                    "description": b.description,
                    "source_type": b.source_type,
                    "is_published": b.is_published,
                    "sort_order": b.sort_order,
                    "cover_url": b.cover_url,
                    "cover_color": b.cover_color,
                    "source_url": b.source_url,
                    "pdf_url": b.pdf_url,
                    "word_count": sum(ch["word_count"] for ch in chapters),
                    "chapters": chapters,
                }
            )

        return Response(
            {
                "slug": slug,
                "title": canonical.title,
                "author": {
                    "name": canonical.author.name,
                    "slug": canonical.author.slug,
                    "id": canonical.author_id,
                },
                "languages": languages,
            }
        )


class AdminExportView(APIView):
    """Download the full content inventory as JSON (default) or CSV.

    ``?format=csv`` streams a flat one-row-per-item table (books, sermons,
    plans); otherwise a structured JSON object (books, sermons, plans, authors)
    for offline analysis or reporting. Admin-gated.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        data = self._inventory()
        # Note: not "format" — DRF reserves that query param for renderer
        # negotiation, so ?format=csv would 404 before reaching here.
        if request.query_params.get("fmt", "").lower() == "csv":
            return self._csv(data)
        return Response(data)

    def _inventory(self) -> dict:
        books = [
            {
                "type": "book",
                "slug": b.slug,
                "language": b.language,
                "title": b.title,
                "subtitle": b.subtitle,
                "author": b.author.name,
                "source_type": b.source_type,
                "is_published": b.is_published,
                "chapters": b.num_chapters,
                "words": b.words or 0,
                "source_url": b.source_url,
            }
            for b in Book.objects.select_related("author")
            .annotate(num_chapters=Count("chapters"), words=Sum("chapters__word_count"))
            .order_by("slug", "language")
        ]
        sermons = [
            {
                "type": "sermon",
                "slug": s.slug,
                "language": s.language,
                "title": s.title,
                "author": s.author.name,
                "is_published": s.is_published,
                "words": s.word_count,
                "source_url": s.source_url,
            }
            for s in Sermon.objects.select_related("author").order_by("slug", "language")
        ]
        plans = [
            {
                "type": "plan",
                "slug": p.slug,
                "language": p.language,
                "title": p.title,
                "is_published": p.is_published,
                "days": p.num_days,
            }
            for p in Plan.objects.annotate(num_days=Count("days")).order_by(
                "slug", "language"
            )
        ]
        authors = [
            {
                "slug": a.slug,
                "name": a.name,
                "birth_year": a.birth_year,
                "death_year": a.death_year,
                "has_bio": bool(a.bio),
                "has_bio_html": bool(a.bio_html),
            }
            for a in Author.objects.order_by("name")
        ]
        return {"books": books, "sermons": sermons, "plans": plans, "authors": authors}

    def _csv(self, data: dict):
        import csv
        import io

        from django.http import HttpResponse
        from django.utils import timezone

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["type", "slug", "language", "title", "author", "source_type",
             "published", "chapters_or_days", "words", "source_url"]
        )
        for b in data["books"]:
            writer.writerow(
                ["book", b["slug"], b["language"], b["title"], b["author"],
                 b["source_type"], b["is_published"], b["chapters"], b["words"],
                 b["source_url"]]
            )
        for s in data["sermons"]:
            writer.writerow(
                ["sermon", s["slug"], s["language"], s["title"], s["author"], "",
                 s["is_published"], "", s["words"], s["source_url"]]
            )
        for p in data["plans"]:
            writer.writerow(
                ["plan", p["slug"], p["language"], p["title"], "", "",
                 p["is_published"], p["days"], "", ""]
            )
        stamp = timezone.now().date().isoformat()
        resp = HttpResponse(buf.getvalue(), content_type="text/csv")
        resp["Content-Disposition"] = f'attachment; filename="ochorus-inventory-{stamp}.csv"'
        return resp
