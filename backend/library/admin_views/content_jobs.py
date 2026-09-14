"""Admin dashboard API — the content-edit job queue (fix buttons → GitHub issues).

Content-quality flags get a "fix" control in the admin: a chapter's wrong title
or garbled text on the book page, an author's missing/thin bio on the worklist.
Submitting one files a GitHub issue (label ``content-edit``) that a Claude Code
worker session turns into a fixture PR. Three job **kinds** share this one queue:

- ``title`` — retitle a chapter (a concrete proposed title).
- ``body`` — revise a chapter's text (a note describing what's wrong).
- ``bio`` — write/expand an author biography (an optional emphasis note).

Same queue-over-GitHub design as the translation queue (see ``jobs.py``), and for
the same reason: a chapter title/body and an author bio are **fixture-owned prose**
(see ``backend/CLAUDE.md``), so an in-admin edit cannot be a live DB write. A live
edit would move no content digest — the prerendered reader page would never
rebuild — and ``seed_books`` deliberately never syncs an existing book's chapters,
so it would also drift from the fixture and be walked back on a fresh install. The
correct shape is a PR that edits the fixture *and* migrates the live rows; prod
holds no credentials to author that, so the admin files a job and a worker ships
it. State is derived, not stored: queued = open issue, done = the worker closed
it. The per-kind worker instructions live in the ``content-edit-worker`` skill.

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

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import allowed_languages, requires

from ..audit import AdminAudited
from ..languages import entry as language_entry
from ..languages import known_codes
from ..models import AdminAction, Author, Chapter

GITHUB_API = os.getenv("GITHUB_API_BASE", "https://api.github.com")
LABEL = "content-edit"
IN_PROGRESS_LABEL = "in-progress"

# The job's identity (duplicate-press guard) and what the worker parses — both
# ends share these exact shapes. One open job per (kind, target). The wire verb
# encodes the kind and the entity it targets; a chapter carries an order, an
# author bio does not.
#   [edit] retitle     book:<slug>/<lang>#<order>   → title
#   [edit] revise      book:<slug>/<lang>#<order>   → body
#   [edit] rewrite-bio author:<slug>/<lang>         → bio
_TITLE_RE = re.compile(
    r"^\[edit\] (?P<verb>retitle|revise|rewrite-bio) "
    r"(?P<entity>book|author):(?P<slug>[a-z0-9-]+)/(?P<lang>[a-z-]{2,10})"
    r"(?:#(?P<order>\d+))?$"
)

# kind ↔ (verb, entity). A chapter job needs an order; a bio job must not have one.
_VERB_FOR = {"title": "retitle", "body": "revise", "bio": "rewrite-bio"}
_KIND_FOR = {v: k for k, v in _VERB_FOR.items()}
_CHAPTER_KINDS = ("title", "body")

_PAGE_SIZE = 100
_MAX_PAGES = 20


def _job_title(kind: str, slug: str, language: str, order: int | None) -> str:
    if kind == "bio":
        return f"[edit] {_VERB_FOR[kind]} author:{slug}/{language}"
    return f"[edit] {_VERB_FOR[kind]} book:{slug}/{language}#{order}"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.GITHUB_TRANSLATION_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def _issue_to_job(issue: dict) -> dict | None:
    m = _TITLE_RE.match(issue.get("title", ""))
    if not m:
        return None
    kind = _KIND_FOR[m.group("verb")]
    entity, order = m.group("entity"), m.group("order")
    # Reject a title that pairs a verb with the wrong entity or order-ness — a
    # chapter kind must be a `book:…#order`, a bio must be an author with none.
    if kind in _CHAPTER_KINDS and (entity != "book" or order is None):
        return None
    if kind == "bio" and (entity != "author" or order is not None):
        return None
    labels = {lbl.get("name", "") for lbl in issue.get("labels", [])}
    return {
        "kind": kind,
        "entity": entity,
        "slug": m.group("slug"),
        "language": m.group("lang"),
        "order": int(order) if order is not None else None,
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


@requires(
    AdminCapability.CONTENT_EDIT,
    verbs={"GET": AdminVerb.VIEW, "POST": AdminVerb.SUGGEST},
    language_arg="language",
)
class AdminContentEditJobsView(AdminAudited, APIView):
    """GET the open content-edit queue; POST to file a fix (title / body / bio)."""

    audit_action = AdminAction.Action.CONTENT_EDIT_JOB

    def audit_entry(self, request, response):
        # A book kind links the row to the book's admin page (`book:<slug>:<lang>`);
        # a bio links to the author page (`author:<slug>`). parseTarget handles both.
        data = request.data
        kind = str(data.get("kind", "title")).strip().lower()
        slug = str(data.get("slug", "")).strip().lower()
        language = str(data.get("language", "")).strip().lower()
        target = f"author:{slug}" if kind == "bio" else f"book:{slug}:{language}"
        return target, {
            "kind": kind,
            "chapter": data.get("order", "") if kind in _CHAPTER_KINDS else "",
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
        # Least privilege: a language-scoped user sees only their languages' jobs.
        allowed = allowed_languages(request, AdminCapability.CONTENT_EDIT, AdminVerb.VIEW)
        if allowed is not None:
            jobs = [j for j in jobs if j["language"] in allowed]
        return Response({"configured": True, "jobs": jobs})

    def post(self, request):
        kind = str(request.data.get("kind", "title")).strip().lower()
        if kind in _CHAPTER_KINDS:
            return self._file_chapter_job(request, kind)
        if kind == "bio":
            return self._file_bio_job(request)
        return Response({"detail": "unknown edit kind."}, status=400)

    # --- chapter jobs (title / body) -------------------------------------------

    def _file_chapter_job(self, request, kind: str):
        slug = str(request.data.get("slug", "")).strip().lower()
        language = str(request.data.get("language", "")).strip().lower()
        try:
            order = int(request.data.get("order"))
        except (TypeError, ValueError):
            return Response({"detail": "order must be an integer."}, status=400)

        if not re.fullmatch(r"[a-z0-9-]+", slug or ""):
            return Response({"detail": "invalid slug."}, status=400)
        # A content fix can target any known language, English included — unlike a
        # translation, which must be into a non-English one.
        if language not in known_codes():
            return Response({"detail": "language must be a known code."}, status=400)

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

        if kind == "title":
            proposed = str(request.data.get("title", "")).strip()
            if not proposed:
                return Response({"detail": "a new title is required."}, status=400)
            if len(proposed) > 300:
                return Response({"detail": "that title is too long."}, status=400)
            if (current_title or "").strip() == proposed:
                return Response(
                    {"detail": "that is already the chapter's title."}, status=400
                )
            note = proposed
        else:  # body
            note = str(request.data.get("note", "")).strip()
            if not note:
                return Response(
                    {"detail": "describe what's wrong with the text."}, status=400
                )
            if len(note) > 2000:
                return Response({"detail": "that note is too long."}, status=400)

        if not settings.GITHUB_TRANSLATION_TOKEN:
            return self._unconfigured()

        lang_name = language_entry(language)["name"]
        body = (
            self._title_body(slug, language, lang_name, order, book_title, current_title, note)
            if kind == "title"
            else self._body_body(slug, language, lang_name, order, book_title, note)
        )
        return self._file(kind, slug, language, order, body)

    # --- bio jobs --------------------------------------------------------------

    def _file_bio_job(self, request):
        slug = str(request.data.get("slug", "")).strip().lower()
        # The bio worklist is the English `Author.bio`; a translated bio job names
        # its language explicitly. Default to English, the source bio.
        language = str(request.data.get("language", "en")).strip().lower()

        if not re.fullmatch(r"[a-z0-9-]+", slug or ""):
            return Response({"detail": "invalid slug."}, status=400)
        if language not in known_codes():
            return Response({"detail": "language must be a known code."}, status=400)

        author = Author.objects.filter(slug=slug).values_list("name", "is_imprint").first()
        if author is None:
            return Response(
                {"detail": f"no author {slug!r}."}, status=status.HTTP_404_NOT_FOUND
            )
        name, is_imprint = author
        # An imprint (e.g. "Ochorus Originals") is a byline, not a person — it never
        # gets a bio, so a bio job for one would be permanently unfinishable.
        if is_imprint:
            return Response({"detail": "an imprint has no biography."}, status=400)

        note = str(request.data.get("note", "")).strip()
        if len(note) > 2000:
            return Response({"detail": "that note is too long."}, status=400)

        if not settings.GITHUB_TRANSLATION_TOKEN:
            return self._unconfigured()

        lang_name = language_entry(language)["name"]
        body = self._bio_body(slug, language, lang_name, name, note)
        return self._file("bio", slug, language, None, body)

    # --- shared GitHub plumbing ------------------------------------------------

    def _file(self, kind: str, slug: str, language: str, order: int | None, body: str):
        """Duplicate-guard on (kind, slug, language, order), then open the issue."""
        title = _job_title(kind, slug, language, order)
        identity = (kind, slug, language, order)
        try:
            for job in _list_open_jobs():
                if (job["kind"], job["slug"], job["language"], job["order"]) == identity:
                    return Response({"job": job, "created": False})
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
    def _unconfigured():
        return Response(
            {
                "detail": "Content-edit queue isn't configured — set "
                "GITHUB_TRANSLATION_TOKEN in the API environment."
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    # --- issue bodies (the worker's instructions) ------------------------------

    @staticmethod
    def _title_body(slug, language, lang_name, order, book_title, current, proposed) -> str:
        """A chapter title lives in the fixture AND in the live DB row, and
        ``seed_books`` syncs neither — so the fix is two edits, and the title feeds
        the search index, so the row must go through ``save()``."""
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

    @staticmethod
    def _body_body(slug, language, lang_name, order, book_title, note) -> str:
        """A chapter body is sanitised prose with three derived columns; the worker
        must respect the settled form and refresh the search vector through
        ``save()``. See the ``content-edit-worker`` skill for the full contract."""
        return (
            f"Revise the **text** of chapter **{order}** of **{book_title}** "
            f"({lang_name}, `{language}`).\n\n"
            "Reported problem:\n"
            f"> {note}\n\n"
            "```json\n"
            f'{{"job": "revise", "type": "book", "slug": "{slug}", '
            f'"language": "{language}", "order": {order}}}\n'
            "```\n\n"
            "**Two edits, because `seed_books` syncs neither a fixture chapter nor a "
            "live row:**\n"
            f"1. Fixture — edit `body_html` of the `library.chapter` row with "
            f"`\"order\": {order}` in `library/fixtures/content/books/{slug}.{language}.json`. "
            "Sanitise to the **chapter** profile (`clean_fragment`, narrow, no "
            "attributes — NOT the bio profile), and write the **settled form** "
            "(`corrections.settled_chapter_body`) so `apply_body_corrections` doesn't "
            "revert it on the next deploy.\n"
            "2. Data migration — update the live row **through `save()`** so all three "
            "derived columns refresh (`body_text`, `word_count`, `search_vector`); a "
            "bare `queryset.update()` leaves search matching the old prose.\n\n"
            "Confirm the change with `manage.py content_diff`. Filed from the Ochorus "
            "admin dashboard; ship via the normal PR flow."
        )

    @staticmethod
    def _bio_body(slug, language, lang_name, name, note) -> str:
        """An author biography: English lives on the ``Author`` row, a translation
        is an ``AuthorTranslation`` shipped as migration data files. Written with the
        ``write-biography`` skill and the bio sanitiser profile."""
        is_english = language == "en"
        reported = f"> {note}\n\n" if note else ""
        return (
            f"Write / expand the biography of **{name}** (`{slug}`)"
            + ("" if is_english else f", in **{lang_name}** (`{language}`)")
            + ".\n\n"
            + ("Note:\n" + reported if note else "")
            + "```json\n"
            f'{{"job": "rewrite-bio", "type": "author", "slug": "{slug}", '
            f'"language": "{language}"}}\n'
            "```\n\n"
            "Use the **write-biography** skill. Bios use the `clean_bio_html` sanitiser "
            "profile (they legitimately carry `<aside class=\"prayer\">`, `<cite>` and "
            "internal links) — never the chapter profile, which would strip them.\n"
            + (
                "- English — set the `Author` row's `bio` (short plain-text) and "
                "`bio_html` (long-form HTML). The bio ships in `authors.json`; add a "
                "data migration to reach the existing prod row.\n"
                if is_english
                else "- Translated — an `AuthorTranslation` ships as files under "
                f"`library/migrations/data/author_bios_{language}/` "
                "(`<slug>.short.txt` + `<slug>.html`); `seed_author_translations` "
                "upserts unreviewed rows from them on deploy. No new migration per "
                "batch — the files win.\n"
            )
            + "Filed from the Ochorus admin dashboard; ship via the normal PR flow."
        )
