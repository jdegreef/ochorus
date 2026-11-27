"""Recording who changed what from the admin dashboard.

Every admin endpoint that mutates something mixes in :class:`AdminAudited`, and
the recording happens in ``finalize_response`` rather than inside each handler.
That placement is the point: a handler has several exits — a validation 400, an
early return, an exception — and a ``record(...)`` call written at the bottom of
the happy path is one refactor away from being skipped. Wrapping the response
means the log describes what the API actually did, not what the handler meant to
do, and a request that failed leaves no row claiming otherwise.

Forgetting the mixin on a NEW endpoint is the failure this cannot catch by
itself, so ``tests_audit.py`` walks the URL conf, finds every admin view with a
write method, and fails on any that is not audited — naming it. That test is the
rule; this module is only the mechanism.
"""

from __future__ import annotations

from .models import AdminAction

#: The methods that can change something. GET and HEAD are not recorded: an
#: audit log that grows a row per dashboard refresh buries the eight events a
#: month anyone actually needs to find.
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class AdminNotAudited:
    """Mixin: this admin endpoint takes a write method but changes nothing.

    Exemption by declaration rather than by a list kept somewhere else, so the
    reason sits next to the code it excuses and the coverage test can report it.
    A subclass must say why in ``audit_exempt``.
    """

    #: Why this endpoint records nothing. Required — an unexplained exemption is
    #: indistinguishable from a forgotten one.
    audit_exempt: str = ""


def actor_email(request) -> str:
    """The identity ``IsAdminEmail`` gated on, lower-cased as it compares it.

    Empty for a DEBUG loopback request with no token — the one case that
    permission lets through unauthenticated. Blank is honest there; inventing
    "localhost" would put a name in the log that no account answers to.
    """
    return (getattr(getattr(request, "user", None), "email", "") or "").strip().lower()


class AdminAudited:
    """Mixin: append an :class:`AdminAction` for each successful admin write.

    Subclasses set ``audit_action`` and implement ``audit_entry`` to say what
    was touched. ``audit_entry`` runs with the response in hand, so it can
    report what happened rather than what was asked for — whether a go-live
    actually launched, how many items a batch decision settled.
    """

    #: An ``AdminAction.Action`` value. Views whose methods record different
    #: actions override :meth:`audit_action_for` instead.
    audit_action: str = ""

    def audit_action_for(self, request) -> str:
        """Which action this request is. Overridden where one view has two —
        the review queue decides on POST and undoes on DELETE."""
        return self.audit_action

    def audit_entry(self, request, response) -> tuple[str, dict]:
        """Return ``(target, detail)`` for this request.

        The default records nothing beyond the action and the actor, which is
        already more than these endpoints had.
        """
        return "", {}

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if request.method in WRITE_METHODS and 200 <= response.status_code < 300:
            target, detail = self.audit_entry(request, response)
            AdminAction.objects.create(
                action=self.audit_action_for(request),
                actor=actor_email(request),
                target=target[:200],
                detail=detail or {},
            )
        return response


#: How long a repeat of the same privacy-sensitive read by the same person is
#: folded into the row already written. Opening a reader's page, going back and
#: opening it again is one look, not two; a refresh loop shouldn't bury the log.
READ_DEDUPE_MINUTES = 30


def record_read(
    request,
    action: str,
    target: str = "",
    detail: dict | None = None,
    *,
    dedupe: bool = True,
) -> None:
    """Append an :class:`AdminAction` for a privacy-sensitive READ.

    The log deliberately skips GETs (``WRITE_METHODS``), but two reads deserve a
    trace because they hand someone readers' personal data: a reader's page
    with their email in the clear (``user.view``) and a reader-list export
    (``user.export``). Nothing else should call this — a row per ordinary page
    view is the noise ``WRITE_METHODS`` exists to keep out.

    A repeat of the same ``(action, actor, target)`` inside
    :data:`READ_DEDUPE_MINUTES` writes nothing, unless ``dedupe=False`` (an
    export: each download is another copy of the data). Never raises: a logging hiccup
    must not cost an admin the page they asked for.
    """
    from datetime import timedelta

    from django.utils import timezone

    actor = actor_email(request)
    target = (target or "")[:200]
    try:
        since = timezone.now() - timedelta(minutes=READ_DEDUPE_MINUTES)
        if (
            dedupe
            and AdminAction.objects.filter(
                action=action, actor=actor, target=target, at__gte=since
            ).exists()
        ):
            return
        AdminAction.objects.create(
            action=action, actor=actor, target=target, detail=detail or {}
        )
    except Exception:  # noqa: BLE001 — see docstring: the read must still succeed
        import logging

        logging.getLogger(__name__).exception("could not record %s", action)
