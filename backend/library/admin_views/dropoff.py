"""The content audit's "Readers stop here" list: across every book in one
language, the chapters that lose the largest share of their readers, with the
chapter's content flags beside them. The curve itself lives in
``library.dropoff``; one book's full curve is on its admin page."""

from __future__ import annotations

from django.db.models import Count, Q
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from .. import dropoff
from ..models import Book, Chapter
from ..qa import chapter_flags


@requires(AdminCapability.AUDIT, verb=AdminVerb.VIEW)
class AdminDropOffView(APIView):
    """``GET /api/admin/drop-off/?language=en``: each book's steepest drop in
    that language, where at least ``dropoff.MIN_READERS`` readers reached the
    chapter. Flagged chapters first (those are the fixable ones), then by the
    share of readers lost.

    The content checks run only on the few chapters that make the list, not
    the whole library: the full scan is the audit's own, and cached there.
    """

    LIMIT = 15

    def get(self, request):
        """``language`` narrows to one edition language; without it, every
        language that has book readers (the audit page's "all languages")."""
        from reading.models import ReadingProgress, WorkKind

        language = (request.query_params.get("language") or "").strip().lower()
        languages = (
            [language]
            if language
            else ReadingProgress.objects.filter(kind=WorkKind.BOOK)
            .values_list("language", flat=True)
            .distinct()
        )
        drops = [d for lang in languages for d in self._drops(lang)]
        drops.sort(key=lambda d: (not d["flags"], -d["rate"], -d["reached"]))
        return Response(
            {"language": language, "min_readers": dropoff.MIN_READERS, "drops": drops[: self.LIMIT]}
        )

    def _drops(self, language: str) -> list[dict]:
        """Each book's steepest qualifying drop in one language, with the
        chapter's title, length and content flags."""
        progress = dropoff.progress_rows(language)
        lengths = {
            r["book__slug"]: r["n"]
            for r in Chapter.objects.filter(book__language=language, book__slug__in=list(progress))
            .values("book__slug")
            .annotate(n=Count("id"))
        }
        drops = []
        for slug, rows in progress.items():
            drop = dropoff.steepest_drop(
                dropoff.reach(rows, lengths.get(slug, 0)), min_readers=dropoff.MIN_READERS
            )
            if drop:
                drops.append({"slug": slug, "language": language, **drop})
        if not drops:
            return []

        # The chapters on the list, with what the content checks say about them.
        chapters = {
            c["book__slug"]: c
            for c in Chapter.objects.filter(
                Q(*[Q(book__slug=d["slug"], order=d["chapter"]) for d in drops], _connector=Q.OR),
                book__language=language,
            ).values("book__slug", "order", "title", "word_count", "body_text", "body_html")
        }
        titles = dict(
            Book.objects.filter(language=language, slug__in=[d["slug"] for d in drops]).values_list(
                "slug", "title"
            )
        )
        for d in drops:
            c = chapters.get(d["slug"])
            d["book_title"] = titles.get(d["slug"], d["slug"])
            d["chapter_title"] = c["title"] if c else ""
            d["word_count"] = (c["word_count"] or 0) if c else 0
            # Never the last chapter (steepest_drop skips it), so it has a next.
            d["flags"] = (
                chapter_flags(c["title"], c["word_count"] or 0, c["body_text"], c["body_html"], True)
                if c
                else []
            )
        return drops
