"""Admin API for editing the automated emails (emails/lifecycle_copy.py): the
onboarding drip, the series nudge, milestones and plan reminders.

Super-admin-only like the rest of the Emails section. Saving changes only the
working copy; Publish is what readers see; Reset goes back to the code's words.
AI drafts of a language go through the same translation queue as broadcasts.
"""

from __future__ import annotations

import requests
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail
from library.audit import AdminAudited, AdminNotAudited, actor_email
from library.languages import entry as language_entry
from library.models import AdminAction

from . import blocks as blocks_mod
from . import lifecycle_copy as lc
from . import translation_jobs


def _step(step: lc.Step) -> dict:
    return {
        "key": step.key,
        "label": step.label,
        "when": step.when,
        "stream": lc.stream_of(step.key),
        "placeholders": step.placeholders,
        "link": step.link,
    }


def _detail(copy) -> dict:
    statuses = lc.statuses(copy)
    return {
        **_step(lc.STEP_BY_KEY[copy.step]),
        "subject": copy.subject,
        "content": blocks_mod.as_blocks(copy.content),
        "statuses": statuses,
        "names": {code: language_entry(code).get("native_name") or code for code in statuses},
        "translations": translation_jobs.states(copy),
        "updated_by": copy.updated_by,
        "versions": [
            {"id": v.id, "published_at": v.published_at.isoformat(), "published_by": v.published_by, "languages": v.languages}
            for v in copy.versions.all()[:20]
        ]
        if not copy._state.adding
        else [],
    }


def _get_step(key: str):
    if key not in lc.STEP_BY_KEY:
        return None
    return lc.row(key)


class AdminLifecycleListView(AdminNotAudited, APIView):
    """Every editable automated email, with where its languages stand."""

    permission_classes = [IsAdminEmail]
    audit_exempt = "Read-only list."

    def get(self, request):
        rows = []
        for step in lc.STEPS:
            statuses = lc.statuses(lc.row(step.key))
            counts: dict[str, int] = {}
            for s in statuses.values():
                counts[s["status"]] = counts.get(s["status"], 0) + 1
            rows.append(
                {
                    **_step(step),
                    "subject": lc.working(lc.row(step.key), "en")["subject"] if "en" in statuses else "",
                    "languages": len(statuses),
                    "counts": counts,
                    "stale": sum(1 for s in statuses.values() if s["stale"]),
                }
            )
        return Response({"steps": rows})


class AdminLifecycleDetailView(AdminAudited, APIView):
    """``GET`` one email's working copy, statuses and history; ``PATCH
    {"subject", "content"}`` saves the working copy (readers see nothing yet)."""

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.EMAIL_LIFECYCLE_EDIT

    def audit_entry(self, request, response):
        return (f"lifecycle:{self.kwargs.get('step')}", {"languages": sorted((request.data.get("content") or {}).keys())})

    def get(self, request, step):
        copy = _get_step(step)
        if copy is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        return Response(_detail(copy))

    def patch(self, request, step):
        if step not in lc.STEP_BY_KEY:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        subject = request.data.get("subject") if isinstance(request.data.get("subject"), dict) else {}
        content = request.data.get("content") if isinstance(request.data.get("content"), dict) else {}
        copy = lc.save_working(step, subject, content, actor=actor_email(request))
        return Response(_detail(copy))


class AdminLifecycleActionView(AdminAudited, APIView):
    """Act on one automated email: ``publish`` (``languages``: the ones to
    publish, or every edited one), ``reset`` (``language``, or all), ``restore``
    (``version``), or an AI draft — ``request`` / ``fetch`` / ``approve``
    (``language``) and ``request_stale`` (every language left behind by an
    English change)."""

    permission_classes = [IsAdminEmail]

    _AUDIT = {
        "publish": AdminAction.Action.EMAIL_LIFECYCLE_PUBLISH,
        "reset": AdminAction.Action.EMAIL_LIFECYCLE_RESET,
        "restore": AdminAction.Action.EMAIL_LIFECYCLE_EDIT,
        "request": AdminAction.Action.EMAIL_TRANSLATION_REQUEST,
        "request_stale": AdminAction.Action.EMAIL_TRANSLATION_REQUEST,
        "fetch": AdminAction.Action.EMAIL_TRANSLATION_DRAFT,
        "approve": AdminAction.Action.EMAIL_TRANSLATION_APPROVE,
    }

    def audit_action_for(self, request):
        return self._AUDIT.get(str(request.data.get("action", "")), AdminAction.Action.EMAIL_LIFECYCLE_EDIT)

    def audit_entry(self, request, response):
        detail = {k: request.data.get(k) for k in ("action", "language", "languages", "version") if k in request.data}
        return (f"lifecycle:{self.kwargs.get('step')}", detail)

    def post(self, request, step):
        if step not in lc.STEP_BY_KEY:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        action = str(request.data.get("action", ""))
        language = str(request.data.get("language") or "").strip().lower()
        actor = actor_email(request)
        outcome = None
        try:
            if action == "publish":
                langs = request.data.get("languages")
                copy = lc.publish(step, [str(x) for x in langs] if isinstance(langs, list) else None, actor=actor)
            elif action == "reset":
                copy = lc.reset(step, language or None, actor=actor)
            elif action == "restore":
                copy = lc.restore(step, int(request.data.get("version") or 0), actor=actor)
            elif action in ("request", "fetch", "approve", "request_stale"):
                copy = lc.row(step)
                if copy._state.adding:
                    copy.save()  # a job needs the row it reports back to
                if action == "request":
                    translation_jobs.request(copy, "en", language)
                elif action == "fetch":
                    translation_jobs.fetch(copy, language)
                elif action == "approve":
                    translation_jobs.approve(copy, language, actor=actor)
                else:
                    outcome = {}
                    for code, s in lc.statuses(copy).items():
                        if not s["stale"] or s["status"] in ("requested", "draft"):
                            continue
                        try:
                            translation_jobs.request(copy, "en", code)
                            outcome[code] = "requested"
                        except translation_jobs.TranslationJobError as exc:
                            outcome[code] = str(exc)
                lc._forget(step)
            else:
                return Response({"detail": f"unknown action {action!r}"}, status=http_status.HTTP_400_BAD_REQUEST)
        except (lc.CopyError, translation_jobs.TranslationJobError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=http_status.HTTP_409_CONFLICT)
        except requests.RequestException:
            return Response(
                {"detail": "GitHub is unreachable — try again shortly."}, status=http_status.HTTP_502_BAD_GATEWAY
            )
        data = _detail(copy)
        if outcome is not None:
            data["outcome"] = outcome
        return Response(data)
