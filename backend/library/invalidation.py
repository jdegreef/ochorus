"""One channel for "reader-visible content changed through the API".

The reader is a prerendered static site, so a DB change an admin makes without a
deploy — an import publish, a review approval, a go-live — is invisible to
readers until a build runs. Before this, only go-live fired the rebuild; import
publish and review approval mutated the DB and rebuilt nothing, so the
prerendered pages (and every crawler and social-preview) stayed stale until an
unrelated commit happened to move the content digest. (The digest can't help: it
hashes repo files, not the DB — see ``library/http_cache`` and ``content_sources``.)

``mark_content_changed`` is that one channel. It bumps a DB-side content revision
(``ContentRevision``) — the primitive the public ETag will key on — and fires the
Render web deploy hook so the static site rebuilds. The fire is *leading-edge
throttled*: a burst of approvals coalesces into few rebuilds, and that is safe
because a rebuild reads the live API minutes later, so one fire picks up every
change made before its build reaches the data. ``force`` bypasses the throttle
for a deliberate single action (go-live) that must always rebuild and report its
result. ``manage.py flush_content_deploy`` fires once if any change is still
un-deployed — the trailing-edge safety net for the last change in a throttled
burst.

Never raises: a content mutation must not fail because a rebuild couldn't be
triggered, exactly as ``golive.trigger_web_deploy`` never raises.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from . import golive
from .models import ContentRevision

#: Leading-edge throttle window. A rebuild takes many minutes and reads live data
#: when it runs, so one fire covers everything changed in this window; firing per
#: mutation would queue a rebuild per approval. Long enough to coalesce a
#: dashboard session, short enough that a lone action rebuilds promptly.
DEPLOY_COOLDOWN = timedelta(minutes=5)


_FAILED = "Rebuild could not be triggered."


def mark_content_changed(*, force: bool = False) -> golive.DeployResult | None:
    """Record a reader-visible content change and (throttled) trigger a rebuild.

    Returns the ``DeployResult`` when the hook was fired (always, for ``force``
    callers like go-live, which report it), or ``None`` when the throttle
    suppressed the fire because a rebuild is already imminent. Never raises.
    """
    try:
        revision = ContentRevision.bump()
    except Exception:  # noqa: BLE001 — a failed bump must not fail the mutation
        return golive.DeployResult("failed", _FAILED) if force else None
    return _fire_deploy(revision, force=force)


def _fire_deploy(revision: int, *, force: bool) -> golive.DeployResult | None:
    try:
        row = ContentRevision.load()
        now = timezone.now()
        if not force and not _cooldown_elapsed(row, now):
            return None  # a recent fire will rebuild this change when it reads data
        result = golive.trigger_web_deploy()
        if result.status == "triggered":
            ContentRevision.objects.filter(pk=row.pk).update(
                deploy_fired_at=now, deploy_fired_revision=revision
            )
        return result
    except Exception:  # noqa: BLE001 — force callers rely on a result; see docstring
        return golive.DeployResult("failed", _FAILED) if force else None


def _cooldown_elapsed(row: ContentRevision, now) -> bool:
    return row.deploy_fired_at is None or (now - row.deploy_fired_at) >= DEPLOY_COOLDOWN


def has_undeployed_changes() -> bool:
    """True when content changed since the last hook fire (the throttle's tail)."""
    row = ContentRevision.load()
    return row.revision > row.deploy_fired_revision


def flush_deploy() -> golive.DeployResult | None:
    """Fire the hook if any change is still un-deployed. Used by the command."""
    if not has_undeployed_changes():
        return None
    return _fire_deploy(ContentRevision.load().revision, force=True)
