"""Admin API for automations (emails/automations.py): build a flow, write its
emails, switch it on, send yourself a test run, and see how it is doing.

Super-admin-only like the rest of the Emails section. A flow's step list is
frozen while it is on (readers mid-way are pinned to a step number); its
emails' words can still be edited.
"""

from __future__ import annotations

import uuid
from collections import Counter

import requests
from django.db.models import Count
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile
from accounts.permissions import IsAdminEmail
from library.audit import AdminAudited, AdminNotAudited, actor_email
from library.models import AdminAction

from . import automations as auto
from . import blocks as blocks_mod
from . import health, starter_templates, translation_jobs
from .models import (
    Automation,
    AutomationEmail,
    EmailKind,
    EmailMessage,
    EmailSubscription,
    EmailTemplate,
    SendStatus,
    idempotency_key,
)
from .recipient import verified_email
from .rendering import email_language, render_blocks
from .sending import deliver
from .streams import STREAM_KEYS


def _email(e: AutomationEmail) -> dict:
    return {
        "id": e.pk,
        "subject": e.subject,
        "content": blocks_mod.as_blocks(e.content),
        "locales": sorted(e.content),
        "ready": auto.ready_locales(e),
        "translations": translation_jobs.states(e),
    }


def _row(a: Automation, runs: dict | None = None) -> dict:
    runs = runs if runs is not None else dict(
        Counter({r["status"]: r["n"] for r in a.runs.values("status").annotate(n=Count("id"))})
    )
    return {
        "id": a.pk,
        "name": a.name,
        "trigger": a.trigger,
        "stream": a.stream,
        "enabled": a.enabled,
        "enabled_at": a.enabled_at.isoformat() if a.enabled_at else None,
        "steps": len(a.steps or []),
        "emails": sum(1 for s in a.steps or [] if s.get("type") == "email"),
        "runs": runs,
        "stats": health.metrics(EmailMessage.objects.filter(lifecycle_step=auto.step_label(a.pk))),
    }


def _detail(a: Automation) -> dict:
    return {
        **_row(a),
        "steps": a.steps,
        "exit": a.exit,
        "email_list": [_email(e) for e in a.emails.all()],
        "problems": auto.problems(a),
        "updated_by": a.updated_by,
    }


def _shape(steps: list[dict]) -> list[tuple]:
    """A flow's structure — what readers mid-way are pinned to."""
    return [(s.get("type"), s.get("id")) for s in steps or []]


class AdminAutomationsView(AdminAudited, APIView):
    """``GET`` every automation plus the builder's vocabulary; ``POST {"name"}``
    makes a new, empty one (off)."""

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.EMAIL_AUTOMATION_SAVE

    def audit_entry(self, request, response):
        return (f"automation:{response.data.get('id')}", {"name": response.data.get("name", "")})

    def get(self, request):
        return Response(
            {"automations": [_row(a) for a in Automation.objects.all()], "vocabulary": auto.vocabulary()}
        )

    def post(self, request):
        name = str(request.data.get("name") or "").strip()[:200] or "Untitled automation"
        automation = Automation.objects.create(
            name=name, trigger={"type": "signed_up"}, updated_by=actor_email(request)
        )
        return Response(_detail(automation), status=http_status.HTTP_201_CREATED)


class AdminAutomationDetailView(AdminAudited, APIView):
    """Read, edit (``name``, ``trigger``, ``steps``, ``exit``, ``stream``) or
    delete one automation."""

    permission_classes = [IsAdminEmail]

    def audit_action_for(self, request):
        if request.method == "DELETE":
            return AdminAction.Action.EMAIL_AUTOMATION_DELETE
        return AdminAction.Action.EMAIL_AUTOMATION_SAVE

    def audit_entry(self, request, response):
        return (f"automation:{self.kwargs.get('pk')}", {})

    def get(self, request, pk):
        a = Automation.objects.filter(pk=pk).first()
        if a is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        return Response(_detail(a))

    def patch(self, request, pk):
        a = Automation.objects.filter(pk=pk).first()
        if a is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        data = request.data
        if "steps" in data:
            steps = auto.clean_steps(data["steps"])
            if a.enabled and _shape(steps) != _shape(a.steps):
                return Response(
                    {"detail": "Turn it off to add, remove or reorder steps — readers part-way through are pinned to a step."},
                    status=http_status.HTTP_409_CONFLICT,
                )
            a.steps = steps
        if "name" in data:
            a.name = str(data["name"]).strip()[:200] or a.name
        if "trigger" in data:
            trigger = auto.clean_trigger(data["trigger"])
            if a.enabled and trigger.get("type") != a.trigger.get("type"):
                return Response(
                    {"detail": "Turn it off to change what starts it."}, status=http_status.HTTP_409_CONFLICT
                )
            a.trigger = trigger
        if "exit" in data:
            a.exit = auto.clean_exit(data["exit"])
        if "stream" in data and data["stream"] in STREAM_KEYS:
            a.stream = data["stream"]
        a.updated_by = actor_email(request)[:254]
        a.save()
        return Response(_detail(a))

    def delete(self, request, pk):
        deleted, _ = Automation.objects.filter(pk=pk).delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT if deleted else http_status.HTTP_404_NOT_FOUND)


class AdminAutomationActionView(AdminAudited, APIView):
    """``POST {"action": "enable" | "disable" | "test"}``. ``enable`` refuses a
    flow that couldn't run (its problems are returned); ``test`` sends every
    email in the flow to you, now."""

    permission_classes = [IsAdminEmail]

    def audit_action_for(self, request):
        if str(request.data.get("action")) == "test":
            return AdminAction.Action.EMAIL_AUTOMATION_TEST
        return AdminAction.Action.EMAIL_AUTOMATION_SWITCH

    def audit_entry(self, request, response):
        return (f"automation:{self.kwargs.get('pk')}", {"action": str(request.data.get("action", ""))})

    def post(self, request, pk):
        a = Automation.objects.filter(pk=pk).first()
        if a is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        action = str(request.data.get("action", ""))
        if action == "enable":
            issues = auto.problems(a)
            if issues:
                return Response({"detail": issues[0], "problems": issues}, status=http_status.HTTP_409_CONFLICT)
            auto.set_enabled(a, True)
        elif action == "disable":
            auto.set_enabled(a, False)
        elif action == "test":
            return self._test(request, a)
        else:
            return Response({"detail": f"unknown action {action!r}"}, status=http_status.HTTP_400_BAD_REQUEST)
        a.updated_by = actor_email(request)[:254]
        a.save()
        return Response(_detail(a))

    @staticmethod
    def _test(request, a: Automation):
        profile = UserProfile.objects.filter(supabase_uid=getattr(request.user, "username", "")).first()
        if profile is None:
            return Response(
                {"detail": "a test run goes to your own account; none was found"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        to_email = verified_email(profile)
        subscription, _ = EmailSubscription.objects.get_or_create(profile=profile)
        emails = {e.pk: e for e in a.emails.all()}
        sent = 0
        for step in a.steps or []:
            email = emails.get(step.get("email")) if step.get("type") == "email" else None
            ready = auto.ready_locales(email) if email else []
            if not (email and ready and to_email):
                continue
            mine = email_language(profile, subscription)
            lang = mine if mine in ready else ready[0]
            rendered = render_blocks(
                subject=str(email.subject.get(lang, "")),
                content=email.content.get(lang) or {},
                profile=profile,
                subscription=subscription,
                lang=lang,
            )
            message = deliver(
                profile=profile,
                subscription=subscription,
                kind=EmailKind.LIFECYCLE,
                rendered=rendered,
                idempotency_key=idempotency_key(
                    EmailKind.LIFECYCLE, f"automation-test:{a.pk}:{email.pk}:{uuid.uuid4().hex}", profile
                ),
                to_email=to_email,
                locale=lang,
                lifecycle_step=f"automation-test:{a.pk}",
                is_test=True,
            )
            sent += message.status == SendStatus.SENT
        return Response({"sent": sent, "sent_to": profile.email, **_detail(a)})


class AdminAutomationEmailsView(AdminAudited, APIView):
    """``POST {"template"?: "starter-key" | template id}`` adds an email to the
    automation (blank, or copied from a template) and returns it."""

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.EMAIL_AUTOMATION_SAVE

    def audit_entry(self, request, response):
        return (f"automation:{self.kwargs.get('pk')}:email", {"email": response.data.get("id")})

    def post(self, request, pk):
        a = Automation.objects.filter(pk=pk).first()
        if a is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        template = request.data.get("template")
        subject: dict = {"en": ""}
        content: dict = {"en": {"preheader": "", "blocks": []}}
        starter = next((s for s in starter_templates.STARTERS if s["key"] == template), None)
        if starter is not None:
            serialized = starter_templates.serialize(starter)
            subject, content = serialized["subject"], serialized["content"]
        elif str(template or "").isdigit():
            saved = EmailTemplate.objects.filter(pk=int(template)).first()
            if saved is not None:
                subject, content = saved.subject, saved.content
        email = AutomationEmail.objects.create(automation=a, subject=subject, content=blocks_mod.clean_content(content))
        return Response(_email(email), status=http_status.HTTP_201_CREATED)


class AdminAutomationEmailDetailView(AdminAudited, APIView):
    """``PATCH {"subject", "content"}`` edits an automation email's words;
    ``DELETE`` removes it (a step pointing at it then sends nothing)."""

    permission_classes = [IsAdminEmail]

    def audit_action_for(self, request):
        if request.method == "DELETE":
            return AdminAction.Action.EMAIL_AUTOMATION_DELETE
        return AdminAction.Action.EMAIL_AUTOMATION_SAVE

    def audit_entry(self, request, response):
        return (f"automation-email:{self.kwargs.get('pk')}", {})

    def patch(self, request, pk):
        email = AutomationEmail.objects.filter(pk=pk).first()
        if email is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        if isinstance(request.data.get("subject"), dict):
            email.subject = {str(k)[:10]: str(v)[:300] for k, v in request.data["subject"].items()}
        if isinstance(request.data.get("content"), dict):
            email.content = blocks_mod.clean_content(request.data["content"])
        email.save()
        return Response(_email(email))

    def delete(self, request, pk):
        deleted, _ = AutomationEmail.objects.filter(pk=pk).delete()
        return Response(status=http_status.HTTP_204_NO_CONTENT if deleted else http_status.HTTP_404_NOT_FOUND)


class AdminAutomationEmailTranslationView(AdminAudited, APIView):
    """AI drafts of an automation email: ``POST {"action": "request" | "fetch" |
    "approve", "language", "source"?}`` — the same queue and review as a
    broadcast's (emails/translation_jobs.py)."""

    permission_classes = [IsAdminEmail]

    _AUDIT = {
        "request": AdminAction.Action.EMAIL_TRANSLATION_REQUEST,
        "fetch": AdminAction.Action.EMAIL_TRANSLATION_DRAFT,
        "approve": AdminAction.Action.EMAIL_TRANSLATION_APPROVE,
    }

    def audit_action_for(self, request):
        return self._AUDIT.get(str(request.data.get("action", "")), AdminAction.Action.EMAIL_TRANSLATION_REQUEST)

    def audit_entry(self, request, response):
        return (f"automation-email:{self.kwargs.get('pk')}:{request.data.get('language', '')}", {})

    def post(self, request, pk):
        email = AutomationEmail.objects.filter(pk=pk).first()
        if email is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        action = str(request.data.get("action", ""))
        language = str(request.data.get("language", "")).strip().lower()
        try:
            if action == "request":
                translation_jobs.request(email, str(request.data.get("source") or "en"), language)
            elif action == "fetch":
                translation_jobs.fetch(email, language)
            elif action == "approve":
                translation_jobs.approve(email, language, actor=actor_email(request))
            else:
                return Response({"detail": "action must be request, fetch or approve"}, status=http_status.HTTP_400_BAD_REQUEST)
        except translation_jobs.TranslationJobError as exc:
            return Response({"detail": str(exc)}, status=http_status.HTTP_409_CONFLICT)
        except requests.RequestException:
            return Response({"detail": "GitHub is unreachable — try again shortly."}, status=http_status.HTTP_502_BAD_GATEWAY)
        return Response(_email(email))


class AdminAutomationVocabularyView(AdminNotAudited, APIView):
    """The builder's triggers, conditions and streams."""

    permission_classes = [IsAdminEmail]
    audit_exempt = "Read-only list."

    def get(self, request):
        return Response(auto.vocabulary())
