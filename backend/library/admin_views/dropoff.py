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
from ..models import Chapter
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
        language (the audit page's "all languages")."""
        language = (request.query_params.get("language") or "").strip().lower()
        progress = dropoff.progress_rows(language=language or None)
        lengths = {
            (r["book__slug"], r["book__language"]): r["n"]
            for r in Chapter.objects.filter(book__slug__in={slug for slug, _ in progress})
            .values("book__slug", "book__language")
            .annotate(n=Count("id"))
        }
        drops = []
        for (slug, lang), rows in progress.items():
            curve = dropoff.reach(rows, lengths.get((slug, lang), 0))
            drop = dropoff.steepest_drop(curve, min_readers=dropoff.MIN_READERS)
            if drop:
                drops.append({"slug": slug, "language": lang, **drop})
        self._describe(drops)
        drops.sort(key=lambda d: (not d["flags"], -d["rate"], -d["reached"]))
        return Response(
            {
                "language": language,
                "min_readers": dropoff.MIN_READERS,
                "stall_days": dropoff.STALL_DAYS,
                "drops": drops[: self.LIMIT],
            }
        )

    @staticmethod
    def _describe(drops: list[dict]) -> None:
        """Add each drop's book and chapter titles, length and content flags,
        in one query for all of them."""
        if not drops:
            return
        chapters = {
            (c["book__slug"], c["book__language"]): c
            for c in Chapter.objects.filter(
                Q(
                    *[
                        Q(book__slug=d["slug"], book__language=d["language"], order=d["chapter"])
                        for d in drops
                    ],
                    _connector=Q.OR,
                )
            ).values(
                "book__slug", "book__language", "book__title",
                "title", "word_count", "body_text", "body_html",
            )
        }
        for d in drops:
            c = chapters.get((d["slug"], d["language"]))
            if c is None:  # its chapters changed under the progress rows
                d.update(book_title=d["slug"], chapter_title="", word_count=0, flags=[])
                continue
            wc = c["word_count"] or 0
            d.update(
                book_title=c["book__title"],
                chapter_title=c["title"],
                word_count=wc,
                # Never the last chapter (steepest_drop skips it), so it has a next.
                flags=chapter_flags(c["title"], wc, c["body_text"], c["body_html"], True),
            )
