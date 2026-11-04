"""Where a translation job is now — for the admin Activity log.

A ``translation.job`` row records the press of a Translate button and nothing
after it, so the log said "filed" forever. The rest of a job's life is already
recorded in two places, and this module reads both:

* **GitHub** (the queue — see ``admin_views/jobs.py``): an open issue is
  *queued*; the ``in-progress`` label is a worker's claim; a claim untouched for
  ``STALE_AFTER`` is *stalled* (the translation-worker playbook's crashed-run
  rule). A worker closes the issue when its PR is OPEN and hands the merge off,
  so a closed issue whose job has an open PR is *pr_open* — waiting on CI or a
  merge, with the PR's link. The PR is found by the job's title line in its
  body (the translation-worker playbook writes it), or — for PRs opened before
  that rule — by the worker's branch suffix ``-<type>-<slug>`` plus ``(<lang>)``
  in the PR title.
* **This database**: the translated edition existing is the only proof the job
  shipped — a closed issue is not, since the merge (and the deploy) come after
  it. ``source_type`` / ``reviewed`` then say whether the founder approved it.

So the database wins: an edition that exists is *review* or *done* whatever
GitHub says (a worker has left an issue open after shipping). "Exists" means
shipped — merged and deployed — not necessarily visible: a language that isn't
live yet still hides it from readers. An issue that is closed with no edition is
*closed* (with no open PR) — merged and awaiting a deploy, or closed as not
planned. A PR read that fails only loses the *pr_open* split: those jobs read
*closed*, as before. When GitHub can't be read, a job without an edition is
*unknown* rather than a guess.
"""

from __future__ import annotations

import contextlib
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
PR_OPEN = "pr_open"  # issue closed, its PR open: waiting on CI or a merge
CLOSED = "closed"  # issue closed, no open PR, edition not live: a deploy pending, or not planned
REVIEW = "review"  # live as an AI translation, awaiting approval
DONE = "done"  # approved — or live, for a type with no approval step
UNKNOWN = "unknown"  # no edition, and GitHub couldn't be read
STATUSES = (QUEUED, IN_PROGRESS, STALLED, PR_OPEN, CLOSED, REVIEW, DONE, UNKNOWN)
#: What waits on a person: a merge, a job that closed without shipping, an approval.
NEEDS_ME = (PR_OPEN, CLOSED, REVIEW)

#: How long one read of the open queue is reused. The page is reloaded on every
#: filter change; the queue moves on the scale of minutes. A failed read is
#: remembered as long, so an outage doesn't stall every page load on a timeout.
CACHE_SECONDS = 60
_CACHE_KEY = "activity:open-translation-jobs"
_DOWN = "down"

Key = tuple[str, str, str]  # (type, slug, language) — a job's identity


def parse_key(target: str) -> Key | None:
    """A ``translation.job`` target (``book:humility:es``) as a key."""
    parts = target.split(":")
    if len(parts) != 3 or not all(parts):
        return None
    return parts[0], parts[1], parts[2]


def target_of(key: Key) -> str:
    return ":".join(key)


class Queue:
    """One read of the open queue: ``jobs`` by key, when it was read, and the
    open PRs (empty when they couldn't be read)."""

    def __init__(self, jobs: list[dict], read_at, prs: list[dict] | None = None):
        self.read_at = read_at
        self.prs = prs or []
        self.jobs: dict[Key, dict] = {}
        for job in jobs:
            key = (job["type"], job["slug"], job["language"])
            # One job can have duplicate open issues (a double press before the
            # guard saw the first). Keep the most advanced: a claim beats a
            # queued duplicate, and the freshest claim says whether it's stalled.
            if (held := self.jobs.get(key)) is None or _rank(job) > _rank(held):
                self.jobs[key] = job

    def pr_for(self, key: Key) -> str | None:
        """The open PR shipping ``key``, as its URL; None when there is none."""
        from .admin_views.jobs import job_title

        type_, slug, lang = key
        line = job_title(type_, slug, lang)
        for pr in self.prs:
            if line in pr["body"].splitlines():
                return pr["url"]
        # Before the body line was a rule: the worker's branch and title habit.
        for pr in self.prs:
            if pr["branch"].endswith(f"-{type_}-{slug}") and f"({lang})" in pr["title"]:
                return pr["url"]
        return None


def _rank(job: dict) -> tuple:
    return (job["state"] == "in_progress", job.get("updated_at") or "")


def open_jobs() -> Queue | str | None:
    """The open queue; ``"down"`` when GitHub didn't answer; None when no token
    is configured (the queue isn't set up here, which isn't an outage)."""
    if not settings.GITHUB_TRANSLATION_TOKEN:
        return None
    read = cache.get(_CACHE_KEY)
    if read is None:
        from .admin_views.jobs import (  # the view module imports models
            _list_open_jobs,
            list_open_prs,
        )

        try:
            read = (_list_open_jobs(), timezone.now())
        except requests.RequestException:
            read = _DOWN
        else:
            # Its own try: a token without pull-request read access, or a PR
            # listing that fails, costs the pr_open split — never the queue.
            with contextlib.suppress(requests.RequestException):
                read = (*read, list_open_prs())
        cache.set(_CACHE_KEY, read, CACHE_SECONDS)
    return _DOWN if read == _DOWN else Queue(*read)


def forget_queue() -> None:
    """Drop the cached read — after filing a job, so it shows up as queued."""
    cache.delete(_CACHE_KEY)


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
            unreviewed = Book.SourceType.AI_UNREVIEWED
            mark(type_, ((s, lang, st != unreviewed) for s, lang, st in rows))
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


def statuses(keys: dict[Key, object], read_queue, now=None) -> dict[Key, str]:
    """Each key's status. ``keys`` maps a job to when it was last filed;
    ``read_queue`` is called (once, and only if some job hasn't shipped) for
    :func:`open_jobs`' answer."""
    now = now or timezone.now()
    out = _editions(set(keys))
    pending = [k for k in keys if k not in out]
    queue = read_queue() if pending else None
    for key in pending:
        if not isinstance(queue, Queue):
            out[key] = UNKNOWN
        elif (job := queue.jobs.get(key)) is None:
            # Filed after the cached read: not closed — the read predates it.
            filed = keys[key]
            if filed and filed >= queue.read_at:
                out[key] = QUEUED
            else:
                out[key] = PR_OPEN if queue.pr_for(key) else CLOSED
        elif job["state"] != "in_progress":
            out[key] = QUEUED
        else:
            touched = parse_datetime(job.get("updated_at") or "")
            out[key] = STALLED if touched and now - touched >= STALE_AFTER else IN_PROGRESS
    return out
