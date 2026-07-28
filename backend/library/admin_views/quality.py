"""Admin dashboard API — content quality (review queue, audit heuristics)."""

from __future__ import annotations

from django.db.models import Count, Max
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from ..models import AuthorTranslation, Book, Chapter, PlanDay
from ..qa import (
    FRAG_MAX_AVG,
    FRAG_MIN_PARAS,
    FRAG_MIN_WORDS,
    GENERIC_TITLE,
    GIANT_MIN,
    TERMINAL_PUNCT,
    TINY_MAX,
    chapter_flags,
)


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
        # Same as approve_author_translation: approval answers staleness.
        tr.reviewed = True
        tr.source_stale = False
        tr.save(update_fields=["reviewed", "source_stale"])
        return Response({"ok": True, "kind": "bio", "slug": slug, "language": language})


# --- Content audit (quality + integrity) -------------------------------------
# Chapter-quality heuristics (chapter_flags + thresholds) live in library.qa,
# the single source of truth shared with the import preview.

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
            if 0 < wc < TINY_MAX:
                tiny.append(finding(word_count=wc))
            if wc > GIANT_MIN:
                giant.append(finding(word_count=wc))

            paras = c["body_html"].count("<p")
            if paras >= FRAG_MIN_PARAS and wc >= FRAG_MIN_WORDS and wc / paras < FRAG_MAX_AVG:
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


