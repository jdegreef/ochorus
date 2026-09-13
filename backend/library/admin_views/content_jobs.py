"""Admin dashboard API — the content-edit job queue (fix buttons → GitHub issues).

A chapter's QA flags (a generic or wrong title, say) get a "Fix title" control on
the admin book page; submitting a correction files a GitHub issue (label
``content-edit``) that a Claude Code worker session turns into a fixture PR.

Same queue-over-GitHub design as the translation queue (see ``jobs.py``), and for
the same reason: a chapter title is **fixture-owned prose** (see
``backend/CLAUDE.md``), so an in-admin edit cannot be a live DB write. A live edit
would move no content digest — the prerendered reader page would never rebuild —
and ``seed_books`` deliberately never syncs an existing book's chapters, so it
would also drift from the fixture and be walked back on a fresh install. The
correct shape is a PR that edits the fixture *and* migrates the live rows; prod
holds no credentials to author that, so the admin files a job and a worker ships
it. State is derived, not stored: queued = open issue, done = the worker closed
it (and the corrected title deploys via the fixture + migration).

The GitHub plumbing is intentionally a small local copy of ``jobs.py``'s rather
than shared: that module's tests patch ``library.admin_views.jobs.requests`` by
name, so extracting the calls would be a refactor of a hot, heavily-tested file.
The paginated list below mirrors its hard-won correctness (fetch every page —
a single page silently blinded the duplicate-guard once the queue passed 100).

Requires ``GITHUB_TRANSLATION_TOKEN`` (a repo-scoped token); without it GET
reports ``configured: false`` and POST explains what's missing.
"""

from __future__ import annotations

import os
import re

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from ..audit import AdminAudited
from ..languages import entry as language_entry
from ..languages import known_codes
from ..models import AdminAction, Chapter

GITHUB_API = os.getenv("GITHUB_API_BASE", "https://api.github.com")
LABEL = "content-edit"
IN_PROGRESS_LABEL = "in-progress"

# The job's identity (duplicate-press guard) and what the worker parses — both
# ends share this exact shape. One open job per (book slug, language, chapter).
_TITLE_RE = re.compile(r"^\[edit\] retitle book:([a-z0-9-]+)/([a-z-]{2,10})#(\d+)$")

_PAGE_SIZE = 100
_MAX_PAGES = 20


def _job_title(slug: str, language: str, order: int) -> str:
    return f"[edit] retitle book:{slug}/{language}#{order}"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.GITHUB_TRANSLATION_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def _issue_to_job(issue: dict) -> dict | None:
    m = _TITLE_RE.match(issue.get("title", ""))
    if not m:
        return None
    labels = {lbl.get("name", "") for lbl in issue.get("labels", [])}
    return {
        "slug": m.group(1),
        "language": m.group(2),
        "order": int(m.group(3)),
        "url": issue.get("html_url", ""),
        "number": issue.get("number"),
        "state": "in_progress" if IN_PROGRESS_LABEL in labels else "queued",
        "created_at": issue.get("created_at", ""),
    }


def _list_open_jobs() -> list[dict]:
    """EVERY open content-edit job, oldest first. Raises requests.RequestException.

    Every page, not the first: the duplicate-press guard reads this, and a single
    page goes blind to the newest job once the queue passes 100 (the bug jobs.py
    documents). ``direction: asc`` keeps page one the oldest.
    """
    jobs: list[dict] = []
    for page in range(1, _MAX_PAGES + 1):
        r = requests.get(
            f"{GITHUB_API}/repos/{settings.GITHUB_TRANSLATION_REPO}/issues",
            headers=_headers(),
            params={
                "state": "open",
                "labels": LABEL,
                "per_page": _PAGE_SIZE,
                "direction": "asc",
                "page": page,
            },
            timeout=15,
        )
        r.raise_for_status()
        batch = r.json()
        jobs.extend(job for issue in batch if (job := _issue_to_job(issue)))
        if len(batch) < _PAGE_SIZE:
            break
    return jobs


class AdminContentEditJobsView(AdminAudited, APIView):
    """GET the open content-edit queue; POST to file a chapter-title fix."""

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.CONTENT_EDIT_JOB

    def audit_entry(self, request, response):
        # `book:<slug>:<lang>` so the activity log links the row to the book's
        # admin page (parseTarget already handles that shape); the chapter and
        # the filed/duplicate outcome ride in the detail.
        data = request.data
        slug = str(data.get("slug", "")).strip().lower()
        language = str(data.get("language", "")).strip().lower()
        return f"book:{slug}:{language}", {
            "chapter": data.get("order", ""),
            "created": response.data.get("created", False),
            "issue": (response.data.get("job") or {}).get("url", ""),
        }

    def get(self, request):
        if not settings.GITHUB_TRANSLATION_TOKEN:
            return Response({"configured": False, "jobs": []})
        try:
            jobs = _list_open_jobs()
        except requests.RequestException:
            return Response(
                {"detail": "GitHub is unreachable — try again shortly."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"configured": True, "jobs": jobs})

    def post(self, request):
        slug = str(request.data.get("slug", "")).strip().lower()
        language = str(request.data.get("language", "")).strip().lower()
        proposed = str(request.data.get("title", "")).strip()
        try:
            order = int(request.data.get("order"))
        except (TypeError, ValueError):
            return Response({"detail": "order must be an integer."}, status=400)

        if not re.fullmatch(r"[a-z0-9-]+", slug or ""):
            return Response({"detail": "invalid slug."}, status=400)
        # A title fix can target any known language, English included — unlike a
        # translation, which must be into a non-English one.
        if language not in known_codes():
            return Response({"detail": "language must be a known code."}, status=400)
        if not proposed:
            return Response({"detail": "a new title is required."}, status=400)
        if len(proposed) > 300:
            return Response({"detail": "that title is too long."}, status=400)

        # Query Chapter directly (one join): filtering and selecting across the
        # Book→chapters reverse relation in separate clauses emits TWO joins, so
        # the projected title comes from the unfiltered join — an arbitrary
        # chapter, not `order`.
        chapter = (
            Chapter.objects.filter(book__slug=slug, book__language=language, order=order)
            .values_list("title", "book__title")
            .first()
        )
        if chapter is None:
            return Response(
                {"detail": f"no chapter {order} of {slug!r} in {language!r}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        current_title, book_title = chapter
        if (current_title or "").strip() == proposed:
            return Response(
                {"detail": "that is already the chapter's title."}, status=400
            )
        if not settings.GITHUB_TRANSLATION_TOKEN:
            return Response(
                {
                    "detail": "Content-edit queue isn't configured — set "
                    "GITHUB_TRANSLATION_TOKEN in the API environment."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        lang_name = language_entry(language)["name"]
        title = _job_title(slug, language, order)
        try:
            # Duplicate-press guard: one open job per (slug, language, order).
            for job in _list_open_jobs():
                if (job["slug"], job["language"], job["order"]) == (slug, language, order):
                    return Response({"job": job, "created": False})

            body = self._issue_body(
                slug, language, lang_name, order, book_title, current_title, proposed
            )
            r = requests.post(
                f"{GITHUB_API}/repos/{settings.GITHUB_TRANSLATION_REPO}/issues",
                headers=_headers(),
                json={"title": title, "body": body, "labels": [LABEL]},
                timeout=15,
            )
            r.raise_for_status()
        except requests.RequestException:
            return Response(
                {"detail": "couldn't reach GitHub to file the job — try again shortly."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {"job": _issue_to_job(r.json()), "created": True},
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def _issue_body(slug, language, lang_name, order, book_title, current, proposed) -> str:
        """The worker's instructions. A chapter title lives in the fixture AND in
        the live DB row, and ``seed_books`` syncs neither — so the fix is two
        edits, and the title feeds the search index, so the row must go through
        ``save()``."""
        return (
            f"Retitle chapter **{order}** of **{book_title}** ({lang_name}, `{language}`).\n\n"
            f"- Current: {current or '(untitled)'!r}\n"
            f"- Proposed: {proposed!r}\n\n"
            "```json\n"
            f'{{"job": "retitle", "type": "book", "slug": "{slug}", '
            f'"language": "{language}", "order": {order}}}\n'
            "```\n\n"
            "**Two edits, because `seed_books` syncs neither a fixture chapter nor a "
            "live row:**\n"
            f"1. Fixture — in `library/fixtures/content/books/{slug}.{language}.json`, "
            f"find the `library.chapter` row with `\"order\": {order}` and set its "
            "`\"title\"` (plain text — no body/settled-form concerns). This is the "
            "source of truth and keeps a fresh install correct.\n"
            "2. Data migration — update the existing row so it reaches prod: load the "
            f"chapter, set `.title`, and `save(update_fields=[\"title\"])` (NOT a "
            "`queryset.update()`), so the title's search vector refreshes — a bare "
            "update leaves search matching the old title.\n\n"
            "Filed from the Ochorus admin dashboard. Ship via the normal PR flow."
        )
