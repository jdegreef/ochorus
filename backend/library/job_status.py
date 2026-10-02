"""Where a translation job is now — for the admin Activity log.

A ``translation.job`` row records the press of a Translate button and nothing
after it, so the log said "filed" forever. The rest of a job's life is already
recorded in two places, and this module reads both:

* **GitHub** (the queue — see ``admin_views/jobs.py``): an open issue is
  *queued*; the ``in-progress`` label is a worker's claim; a claim untouched for
  ``STALE_AFTER`` is *stalled* (the translation-worker playbook's crashed-run
  rule). A worker closes the issue when its PR is OPEN and hands the merge off.
* **This database**: the translated edition existing is the only proof the job
  shipped — a closed issue is not, since the merge (and the deploy) come after
  it. ``source_type`` / ``reviewed`` then say whether the founder approved it.

So the database wins: an edition that exists is *review* or *done* whatever
GitHub says (a worker has left an issue open after shipping). An issue that is
closed with no edition is *closed* — awaiting a merge or a deploy, or closed as
not planned; the open-issue list can't tell those apart. When GitHub can't be
read, a job without an edition is *unknown* rather than a guess.
"""

from __future__ import annotations

from datetime import timedelta

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Article, AuthorTranslation, Book, Plan, Sermon, TopicTranslation

#: A claim older than this is a crashed run (translation-worker, conflict gate).
STALE_AFTER = timedelta(hours=6)

QUEUED = "queued"
IN_PROGRESS = "in_progress"
STALLED = "stalled"
CLOSED = "closed"  # issue closed, edition not live: needs a merge/deploy, or not planned
REVIEW = "review"  # live as an AI translation, awaiting approval
DONE = "done"  # approved — or live, for a type with no approval step
UNKNOWN = "unknown"  # no edition, and GitHub couldn't be read
STATUSES = (QUEUED, IN_PROGRESS, STALLED, CLOSED, REVIEW, DONE, UNKNOWN)
#: The two that wait on the founder: a merge, and an approval.
NEEDS_ME = (CLOSED, REVIEW)

#: How long one read of the open queue is reused. The page is reloaded on every
#: filter change; the queue moves on the scale of minutes.
CACHE_SECONDS = 60
_CACHE_KEY = "activity:open-translation-jobs"

Key = tuple[str, str, str]  # (type, slug, language) — a job's identity


def parse_key(target: str) -> Key | None:
    """A ``translation.job`` target (``book:humility:es``) as a key."""
    parts = target.split(":")
    if len(parts) != 3 or not all(parts):
        return None
    return parts[0], parts[1], parts[2]


def target_of(key: Key) -> str:
    return ":".join(key)


def open_jobs() -> dict[Key, dict] | None:
    """The open queue by key, or None when GitHub isn't configured or answering.

    Reuses the queue read behind the coverage page, cached briefly. A failure
    isn't cached: the next load tries again.
    """
    if not settings.GITHUB_TRANSLATION_TOKEN:
        return None
    jobs = cache.get(_CACHE_KEY)
    if jobs is None:
        from .admin_views.jobs import _list_open_jobs  # the view module imports models

        try:
            jobs = _list_open_jobs()
        except requests.RequestException:
            return None
        cache.set(_CACHE_KEY, jobs, CACHE_SECONDS)
    by_key: dict[Key, dict] = {}
    for job in jobs:
        # Oldest first; keep the newest of duplicate issues for one job.
        by_key[(job["type"], job["slug"], job["language"])] = job
    return by_key


def _editions(keys: set[Key]) -> dict[Key, str]:
    """REVIEW or DONE for each key whose translated edition exists."""
    by_type: dict[str, set[str]] = {}
    for type_, slug, _ in keys:
        by_type.setdefault(type_, set()).add(slug)
    found: dict[Key, str] = {}

    def mark(type_, rows):
        for slug, lang, reviewed in rows:
            if (type_, slug, lang) in keys:
                found[(type_, slug, lang)] = DONE if reviewed else REVIEW

    for type_, model in (("book", Book), ("sermon", Sermon), ("article", Article)):
        if slugs := by_type.get(type_):
            rows = model.objects.filter(slug__in=slugs).values_list("slug", "language", "source_type")
            mark(type_, ((s, lang, st != "ai_unreviewed") for s, lang, st in rows))
    if slugs := by_type.get("plan"):
        rows = Plan.objects.filter(slug__in=slugs).values_list("slug", "language")
        mark("plan", ((s, lang, True) for s, lang in rows))
    if slugs := by_type.get("bio"):
        rows = (
            AuthorTranslation.objects.filter(author__slug__in=slugs)
            .exclude(bio_html="")
            .values_list("author__slug", "language", "reviewed")
        )
        mark("bio", rows)
    if slugs := by_type.get("topic"):
        # A shelf is live in a language once it has a title (jobs.py says why).
        rows = (
            TopicTranslation.objects.filter(topic__slug__in=slugs)
            .exclude(title="")
            .values_list("topic__slug", "language")
        )
        mark("topic", ((s, lang, True) for s, lang in rows))
    return found


def statuses(keys: set[Key], queue: dict[Key, dict] | None, now=None) -> dict[Key, str]:
    """Each key's status. ``queue`` is :func:`open_jobs`' answer (None: unknown)."""
    now = now or timezone.now()
    live = _editions(keys)
    out: dict[Key, str] = {}
    for key in keys:
        if key in live:
            out[key] = live[key]
        elif queue is None:
            out[key] = UNKNOWN
        elif (job := queue.get(key)) is None:
            out[key] = CLOSED
        elif job["state"] != "in_progress":
            out[key] = QUEUED
        else:
            touched = parse_datetime(job.get("updated_at") or "")
            out[key] = STALLED if touched and now - touched >= STALE_AFTER else IN_PROGRESS
    return out
