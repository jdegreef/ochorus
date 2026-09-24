"""Admin dashboard API — the translation job queue (buttons → GitHub issues).

The per-language "Next to work on" lists get a Translate button; pressing it
files a GitHub issue (label ``translation-job``) that a Claude Code worker
session processes one at a time (see ``.claude/skills/translation-worker``).

GitHub is the queue deliberately: prod holds no Anthropic credentials
(translations are produced off-server and ship as data, per the pipeline's
founding rule), and the worker sessions can reach GitHub but not this API —
issues are the one surface both sides share. State is derived, not stored:
queued = open issue, in progress = ``in-progress`` label, done = the worker
closed the issue (and the item leaves the todo list once its translation
deploys via the seed_* release steps).

Requires ``GITHUB_TRANSLATION_TOKEN`` (a repo-scoped token) in the environment;
without it GET reports ``configured: false`` and POST explains what's missing.
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
from accounts.permissions import allowed_languages, is_admin_user, requires

from ..audit import AdminAudited
from ..corrections import COPYRIGHT_BLOCKED_SLUGS
from ..languages import entry as language_entry
from ..languages import known_codes
from ..models import (
    AdminAction,
    Article,
    Author,
    AuthorTranslation,
    Book,
    Plan,
    Sermon,
    Topic,
    TopicTranslation,
)

# Env-overridable so local dev / tests can point at a mock GitHub.
GITHUB_API = os.getenv("GITHUB_API_BASE", "https://api.github.com")
LABEL = "translation-job"
IN_PROGRESS_LABEL = "in-progress"
# Every content type the queue can enqueue. Each ships through its own delivery
# vehicle once translated (see ``_JOB_GUIDANCE``); the worker skill picks the
# right one from the job type.
JOB_TYPES = ("book", "sermon", "plan", "bio", "topic", "article")

# Deterministic issue title — it is the job's identity (duplicate-press guard)
# and what the worker parses, so both ends share this exact shape.
_TITLE_RE = re.compile(
    r"^\[translation\] (book|sermon|plan|bio|topic|article):([a-z0-9-]+) -> ([a-z-]{2,10})$"
)

# How each translated type is delivered — appended to the issue body so the
# worker session knows which pipeline ships it.
_JOB_GUIDANCE = {
    "book": "Produces an `ai_unreviewed` book translation shipped via the normal PR flow.",
    "sermon": "Produces an `ai_unreviewed` sermon translation shipped via the normal PR flow.",
    "plan": (
        "Ships as a localized `Plan` + `PlanDay` rows for this language "
        "(the `seed_plans` release step upserts them from the plan definition)."
    ),
    "bio": (
        "Ships as an `ai_unreviewed` long-form biography under "
        "`library/migrations/data/author_bios_<language>/` (`<slug>.short.txt` + "
        "`<slug>.html`); the `seed_author_translations` release step upserts it."
    ),
    "topic": (
        "Ships as an entry in `library/data/topic_translations/<language>.json` (run "
        "`manage.py translate_topic --language <language>`, which writes the file "
        "directly); the `seed_topics` release step upserts it. Topic prose "
        "has NO English fallback — an untranslated shelf is hidden in that "
        "language rather than shown in English — so every topic must be covered."
    ),
    "article": (
        "Produces an `ai_unreviewed` article translation shipped as one new file "
        "`library/fixtures/content/articles/<slug>.<language>.json` (a single "
        "`library.article` row, natural-key format); the `seed_articles` release "
        "step upserts it. No author byline, no chapters."
    ),
}


def _job_title(type_: str, slug: str, language: str) -> str:
    return f"[translation] {type_}:{slug} -> {language}"


def _resolve_source(type_: str, slug: str, language: str):
    """Look up the English source for a job and whether it's already translated.

    Returns ``(title, byline, exists_in_language)`` where ``byline`` is the
    author's name (or None for authorless plans), or ``None`` when there is no
    English source to translate. Each type has its own home: books/sermons are
    per-language rows; a plan is a per-language row too; a long-form bio lives
    on ``Author.bio_html`` with translations in ``AuthorTranslation``.
    """
    if type_ in ("book", "sermon"):
        model = Book if type_ == "book" else Sermon
        src = model.objects.filter(slug=slug, language="en").select_related("author").first()
        if src is None:
            return None
        exists = model.objects.filter(slug=slug, language=language).exists()
        return src.title, src.author.name, exists
    if type_ == "plan":
        src = Plan.objects.filter(slug=slug, language="en").first()
        if src is None:
            return None
        exists = Plan.objects.filter(slug=slug, language=language).exists()
        return src.title, None, exists
    if type_ == "bio":
        author = Author.objects.filter(slug=slug).exclude(bio_html="").first()
        if author is None:
            return None
        exists = (
            AuthorTranslation.objects.filter(author__slug=slug, language=language)
            .exclude(bio_html="")
            .exists()
        )
        return f"the biography of {author.name}", author.name, exists
    if type_ == "topic":
        topic = Topic.objects.filter(slug=slug, is_published=True).first()
        if topic is None:
            return None
        # A shelf counts as translated once it has a TITLE: that is what makes it
        # visible in the language at all (Topic.is_translated_into), and the
        # description is translated in the same call.
        exists = (
            TopicTranslation.objects.filter(topic__slug=slug, language=language)
            .exclude(title="")
            .exists()
        )
        return f"the {topic.title} shelf", None, exists
    if type_ == "article":
        # Like a plan: a per-language row on one slug, and authorless — so the
        # byline is None. The headline lives on ``h1`` (an article has no title).
        src = Article.objects.filter(slug=slug, language="en").first()
        if src is None:
            return None
        exists = Article.objects.filter(slug=slug, language=language).exists()
        return src.h1, None, exists
    return None


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.GITHUB_TRANSLATION_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def _issue_to_job(issue: dict) -> dict | None:
    """Parse a GitHub issue into a job dict; None if it isn't a job issue."""
    m = _TITLE_RE.match(issue.get("title", ""))
    if not m:
        return None
    labels = {lbl.get("name", "") for lbl in issue.get("labels", [])}
    return {
        "type": m.group(1),
        "slug": m.group(2),
        "language": m.group(3),
        "url": issue.get("html_url", ""),
        "number": issue.get("number"),
        "state": "in_progress" if IN_PROGRESS_LABEL in labels else "queued",
        "created_at": issue.get("created_at", ""),
    }


# GitHub caps an issues page at 100, so one request is one page of the queue.
_PAGE_SIZE = 100
# A stop, not a limit: 2000 open jobs means something upstream is wrong, and a
# loop that keeps asking is worse than a short answer.
_MAX_PAGES = 20


def _list_open_jobs() -> list[dict]:
    """EVERY open job issue, oldest first. Raises requests.RequestException upstream.

    Every page, not the first one. This read backs the duplicate-press guard in
    ``post`` below, and while it fetched a single page that guard silently went
    blind the moment the queue passed a hundred: ``direction: asc`` makes page
    one the hundred OLDEST open jobs, so the newest job — the one a second press
    is actually about to re-file — was precisely the one outside the window.
    On 2026-09-06 the queue stood at 107 before the evening's filing began, and
    31 issues were filed for 17 distinct jobs; ``book:absolute-surrender -> es``
    got three. The guard's logic was right the whole time; it was reading a
    truncated queue.

    The GET path shares this, so the dashboard's own queue was short by the same
    jobs it was hiding from the guard.
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
        # A short page is the last page — no Link-header parsing needed.
        if len(batch) < _PAGE_SIZE:
            break
    return jobs


@requires(AdminCapability.TRANSLATE, verbs={"GET": AdminVerb.VIEW, "POST": AdminVerb.SUGGEST}, language_arg="language")
class AdminTranslationJobsView(AdminAudited, APIView):
    """GET the open translation queue; POST to enqueue one item."""

    audit_action = AdminAction.Action.TRANSLATION_JOB

    def audit_entry(self, request, response):
        # `created` distinguishes filing a job from pressing the button again on
        # one already open — both answer 2xx, and only the first spends anything.
        data = request.data
        target = ":".join(
            str(data.get(k, "")).strip().lower() for k in ("type", "slug", "language")
        )
        return target, {
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
        allowed = allowed_languages(request, AdminCapability.TRANSLATE, AdminVerb.VIEW)
        if allowed is not None:
            jobs = [j for j in jobs if j["language"] in allowed]
        return Response({"configured": True, "jobs": jobs})

    def post(self, request):
        # Filing a translation job is a super-admin-only lever: it spins up a
        # worker session and shapes the pipeline. Language admins (any non-super
        # admin) review and approve translations but do NOT queue them — a founder
        # product decision (2026-09-21). GET stays open to a TRANSLATE/view grant,
        # so language admins still SEE queued state; only the enqueue is reserved.
        if not is_admin_user(request.user, request):
            return Response(
                {"detail": "Only a super admin can queue translation work."},
                status=status.HTTP_403_FORBIDDEN,
            )
        type_ = str(request.data.get("type", "")).strip().lower()
        slug = str(request.data.get("slug", "")).strip().lower()
        language = str(request.data.get("language", "")).strip().lower()

        if type_ not in JOB_TYPES:
            return Response(
                {"detail": f"type must be one of {', '.join(JOB_TYPES)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Validated against the registry, so a language the site doesn't know
        # can't be queued — and adding one is a row, not a code change.
        if language == "en" or language not in known_codes():
            return Response(
                {"detail": "language must be a known non-English code."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.fullmatch(r"[a-z0-9-]+", slug or ""):
            return Response({"detail": "invalid slug."}, status=status.HTTP_400_BAD_REQUEST)

        if type_ == "book" and slug in COPYRIGHT_BLOCKED_SLUGS:
            # A translation of a protected English edition is a derivative of it;
            # three shipped this way before this check existed (2026-09-24).
            return Response(
                {"detail": "this book is under copyright and can't be translated."},
                status=status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS,
            )

        resolved = _resolve_source(type_, slug, language)
        if resolved is None:
            return Response(
                {"detail": f"no English {type_} with slug {slug!r}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        source_title, byline, exists = resolved
        if exists:
            return Response(
                {"detail": f"a {language} version of this {type_} already exists."},
                status=status.HTTP_409_CONFLICT,
            )
        if not settings.GITHUB_TRANSLATION_TOKEN:
            return Response(
                {
                    "detail": "Translation queue isn't configured — set "
                    "GITHUB_TRANSLATION_TOKEN in the API environment."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        title = _job_title(type_, slug, language)
        lang_name = language_entry(language)["name"]
        try:
            # Duplicate-press guard: one open issue per (type, slug, language).
            for job in _list_open_jobs():
                if (job["type"], job["slug"], job["language"]) == (type_, slug, language):
                    return Response({"job": job, "created": False})

            what = f"**{source_title}**" + (f" by {byline}" if byline else "")
            body = (
                f"Translate the {type_} {what} into **{lang_name}** (`{language}`).\n\n"
                "```json\n"
                f'{{"type": "{type_}", "slug": "{slug}", "language": "{language}"}}\n'
                "```\n\n"
                "Filed from the Ochorus admin dashboard. Processed one at a time by a "
                "Claude Code worker session — start one and say “process the translation "
                "queue” (see `.claude/skills/translation-worker`).\n\n"
                f"{_JOB_GUIDANCE[type_]}"
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

        job = _issue_to_job(r.json())
        return Response({"job": job, "created": True}, status=status.HTTP_201_CREATED)
