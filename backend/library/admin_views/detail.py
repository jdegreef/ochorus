"""Admin dashboard API — per-work detail and library export."""

from __future__ import annotations

from django.db.models import Count, Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from .. import invalidation
from ..audit import AdminAudited
from ..models import AdminAction, Author, Book, Plan, Sermon
from ..qa import chapter_flags
from ..views import _language_entry


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminBookDetailView(APIView):
    """A single canonical work across all its languages, for the admin.

    Each language row carries its metadata (source, cover, links) and its
    chapter list with word counts and quality flags (see ``chapter_flags``).
    English is listed first.
    """


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


@requires(AdminCapability.PUBLISH, verb=AdminVerb.ACT, language_arg="language")
class _EditionPublishView(AdminAudited, APIView):
    """Publish or unpublish one language edition of a per-language work.

    ``is_published`` is the reader-visibility switch — the public API filters on
    it, so unpublishing removes the edition from the site immediately, and it is
    the lever an urgent copyright takedown pulls. It is deliberately
    **create-only** in the seed (``CREATE_ONLY_FIELDS``), so a decision made here
    is never walked back by a deploy re-seeding from the fixture.

    ``POST /api/admin/<works>/<slug>/publish/`` with ``{language, published}``.
    Scoped to a single ``(slug, language)`` row — the admin detail page toggles
    one edition at a time. Prerendered SEO pages catch up on the throttled
    rebuild ``mark_content_changed`` triggers, the same path import-publish uses.

    Subclasses set ``model`` (Book/Sermon) and ``target_kind`` (the audit-target
    prefix); ``save(update_fields=["is_published"])`` is load-bearing on both —
    a bare ``save()`` would re-tokenise every chapter/body for the search index.
    """

    model = None
    target_kind = ""

    def audit_action_for(self, request):
        return (
            AdminAction.Action.CONTENT_PUBLISH
            if self._parse(request.data)[1]
            else AdminAction.Action.CONTENT_UNPUBLISH
        )

    @staticmethod
    def _parse(data) -> tuple[str, bool]:
        """``(language, published)`` from the request body. ``published``
        defaults to True so a bare press publishes rather than silently toggling
        to an unintended state."""
        language = (data.get("language") or "").strip()
        published = data.get("published")
        return language, True if published is None else bool(published)

    def audit_entry(self, request, response):
        # finalize_response only records on a 2xx, and post() always returns
        # these three keys there — so no defensive fallbacks are reachable.
        d = response.data
        return f"{self.target_kind}:{d['slug']}:{d['language']}", {
            "is_published": d["is_published"]
        }

    def post(self, request, slug):
        language, published = self._parse(request.data)
        if not language:
            return Response({"detail": "A language is required."}, status=400)
        obj = self.model.objects.filter(slug=slug, language=language).first()
        if obj is None:
            return Response(
                {"detail": f"No {language} edition of “{slug}”."}, status=404
            )
        if obj.is_published != published:
            obj.is_published = published
            obj.save(update_fields=["is_published"])
            # Reader-visible now on the SPA (the API filters is_published); the
            # prerendered pages follow on the throttled rebuild.
            invalidation.mark_content_changed()
        return Response(
            {"slug": obj.slug, "language": obj.language, "is_published": obj.is_published}
        )


class AdminBookPublishView(_EditionPublishView):
    """Publish/unpublish one book edition (see :class:`_EditionPublishView`)."""

    model = Book
    target_kind = "book"


class AdminSermonPublishView(_EditionPublishView):
    """Publish/unpublish one sermon edition (see :class:`_EditionPublishView`)."""

    model = Sermon
    target_kind = "sermon"


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminSermonDetailView(APIView):
    """A single canonical sermon across all its languages, for the admin.

    The sermon counterpart to :class:`AdminBookDetailView`, minus chapters — a
    sermon is a single body, so each language row carries just its metadata and
    the publish state the toggle acts on. English is listed first.
    """


    def get(self, request, slug):
        sermons = list(Sermon.objects.filter(slug=slug).select_related("author"))
        if not sermons:
            return Response({"detail": "No such sermon."}, status=404)
        canonical = next((s for s in sermons if s.language == "en"), sermons[0])

        languages = [
            {
                **_language_entry(s.language),
                "title": s.title,
                "scripture_ref": s.scripture_ref,
                "source_type": s.source_type,
                "is_published": s.is_published,
                "word_count": s.word_count,
                "source_url": s.source_url,
            }
            for s in sorted(sermons, key=lambda x: (x.language != "en", x.language))
        ]
        return Response(
            {
                "slug": slug,
                "title": canonical.title,
                "author": {"name": canonical.author.name, "slug": canonical.author.slug},
                "languages": languages,
            }
        )


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminExportView(APIView):
    """Download the full content inventory as JSON (default) or CSV.

    ``?format=csv`` streams a flat one-row-per-item table (books, sermons,
    plans); otherwise a structured JSON object (books, sermons, plans, authors)
    for offline analysis or reporting. Admin-gated.
    """


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

        from django.utils import timezone

        from .csv_export import csv_response, csv_safe

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["type", "slug", "language", "title", "author", "source_type",
             "published", "chapters_or_days", "words", "source_url"]
        )
        # csv_safe on the free-text cells (title, author, source_url); the slug,
        # language, numeric and boolean columns are constrained and left as-is.
        for b in data["books"]:
            writer.writerow(
                ["book", b["slug"], b["language"], csv_safe(b["title"]),
                 csv_safe(b["author"]), b["source_type"], b["is_published"],
                 b["chapters"], b["words"], csv_safe(b["source_url"])]
            )
        for s in data["sermons"]:
            writer.writerow(
                ["sermon", s["slug"], s["language"], csv_safe(s["title"]),
                 csv_safe(s["author"]), "", s["is_published"], "", s["words"],
                 csv_safe(s["source_url"])]
            )
        for p in data["plans"]:
            writer.writerow(
                ["plan", p["slug"], p["language"], csv_safe(p["title"]), "", "",
                 p["is_published"], p["days"], "", ""]
            )
        stamp = timezone.now().date().isoformat()
        return csv_response(buf.getvalue(), f"ochorus-inventory-{stamp}.csv")
