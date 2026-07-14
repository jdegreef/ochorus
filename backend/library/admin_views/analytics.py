"""Admin dashboard API — reading & account analytics (engagement, users)."""

from __future__ import annotations

from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from ..models import Book, Chapter
from ..views import _language_entry


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


# Human labels for the reader themes stored on UserProfile.
THEME_LABELS = {"paper": "Paper (light)", "light": "Light", "dark": "Lamplight (dark)"}


class AdminUsersView(APIView):
    """Account analytics: sign-up growth, locale/theme split, activation.

    Aggregate-only over ``accounts.UserProfile`` (+ a distinct-reader count from
    ReadingProgress for activation). No emails or identifiers are returned.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        from datetime import timedelta

        from django.db.models import Count
        from django.utils import timezone

        from accounts.models import UserProfile
        from reading.models import ReadingProgress

        now = timezone.now()
        total = UserProfile.objects.count()
        with_activity = ReadingProgress.objects.values("profile").distinct().count()

        return Response(
            {
                "total": total,
                "with_activity": with_activity,
                "dormant": max(0, total - with_activity),
                "signups_7d": UserProfile.objects.filter(
                    created_at__gte=now - timedelta(days=7)
                ).count(),
                "signups_30d": UserProfile.objects.filter(
                    created_at__gte=now - timedelta(days=30)
                ).count(),
                "weekly_signups": self._weekly_signups(now),
                "by_locale": self._by_locale(),
                "by_theme": [
                    {
                        "theme": r["theme"],
                        "label": THEME_LABELS.get(r["theme"], r["theme"]),
                        "count": r["n"],
                    }
                    for r in UserProfile.objects.values("theme")
                    .annotate(n=Count("id"))
                    .order_by("-n")
                ],
            }
        )

    def _by_locale(self):
        from django.db.models import Count

        from accounts.models import UserProfile

        out = []
        for r in (
            UserProfile.objects.values("locale")
            .annotate(n=Count("id"))
            .order_by("-n")
        ):
            entry = _language_entry(r["locale"])
            entry["count"] = r["n"]
            out.append(entry)
        return out

    def _weekly_signups(self, now, weeks: int = 12):
        from datetime import timedelta

        from accounts.models import UserProfile

        today = now.date()
        this_week = today - timedelta(days=today.weekday())  # Monday
        buckets = {}
        # One pass over sign-up dates, counted into their Monday-anchored week.
        for (created,) in UserProfile.objects.values_list("created_at"):
            wk = created.date() - timedelta(days=created.date().weekday())
            buckets[wk] = buckets.get(wk, 0) + 1
        out = []
        for i in range(weeks - 1, -1, -1):
            wk = this_week - timedelta(weeks=i)
            out.append({"week": wk.isoformat(), "count": buckets.get(wk, 0)})
        return out


