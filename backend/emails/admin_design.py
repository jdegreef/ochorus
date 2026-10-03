"""Admin API for designing campaigns: live preview, the library picker, and
saved templates.

Kept apart from ``admin_views`` (sending, metrics, readers) so neither grows into
a god-module. Super-admin-only like the rest of the Emails section.
"""

from __future__ import annotations

import requests
from django.db.models import Q
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile
from accounts.permissions import IsAdminEmail
from library.audit import AdminAudited, AdminNotAudited, actor_email
from library.models import AdminAction

from . import blocks as blocks_mod
from . import translation_jobs
from .models import Broadcast, EmailSubscription, EmailTemplate
from .rendering import render_blocks

#: How many works the library picker returns per search.
LIBRARY_LIMIT = 20


class AdminEmailPreviewView(AdminNotAudited, APIView):
    """Render one language of a design exactly as a reader would receive it —
    the unsaved editor state, so the preview follows every keystroke.

    Body: ``{"locale": "es", "subject": "...", "content": {...one language...}}``.
    Rendered for the admin's own account when it has one (their first name fills
    ``{name}``), never touching the database: the subscription is a stand-in, so
    the footer links in a preview go nowhere.
    """

    permission_classes = [IsAdminEmail]
    audit_exempt = "Read-only: renders a preview and writes nothing (POST because the design is a JSON body)."

    def post(self, request):
        locale = str(request.data.get("locale") or "en")[:10]
        content = request.data.get("content")
        if not isinstance(content, dict):
            return Response(
                {"detail": "content must be an object"}, status=http_status.HTTP_400_BAD_REQUEST
            )
        content = blocks_mod.clean_content({locale: content})[locale]
        uid = getattr(request.user, "username", "")
        profile = (uid and UserProfile.objects.filter(supabase_uid=uid).first()) or UserProfile()
        rendered = render_blocks(
            subject=str(request.data.get("subject") or "")[:300],
            content=content,
            profile=profile,
            subscription=EmailSubscription(unsubscribe_token="preview"),
            lang=locale,
        )
        return Response({"subject": rendered.subject, "html": rendered.html})


class AdminEmailLibraryView(AdminNotAudited, APIView):
    """Search the library for the picker: ``?type=book|sermon|plan&q=…``, or look
    up exact works with ``&slugs=a,b`` (what a saved design already names).

    One row per work (slug), with every language it is published in, so the
    designer can show at a glance which editions a block will reach."""

    permission_classes = [IsAdminEmail]
    audit_exempt = "Read-only search."

    def get(self, request):
        kind = request.query_params.get("type", blocks_mod.BlockType.BOOK)
        if kind not in blocks_mod.LIBRARY_TYPES:
            return Response(
                {"detail": "type must be book, sermon or plan"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        published = blocks_mod.library_model(kind).objects.filter(is_published=True)
        exact = [s for s in request.query_params.get("slugs", "").split(",") if s]
        if exact:
            slugs = exact[:LIBRARY_LIMIT]
        else:
            q = request.query_params.get("q", "").strip()
            matches = published.filter(Q(title__icontains=q) | Q(slug__icontains=q)) if q else published
            slugs = list(
                matches.order_by("slug").values_list("slug", flat=True).distinct()[:LIBRARY_LIMIT]
            )
        # Only the picker's columns: a sermon row also carries its whole body.
        fields = ["slug", "language", "title"]
        if blocks_mod.has_author(kind):
            fields.append("author__name")
        works: dict[str, dict] = {}
        for row in published.filter(slug__in=slugs).order_by("slug", "language").values(*fields):
            work = works.setdefault(
                row["slug"],
                {
                    "slug": row["slug"],
                    "title": row["title"],
                    "author": row.get("author__name", ""),
                    "languages": [],
                },
            )
            work["languages"].append(row["language"])
            if row["language"] == "en":  # name a work by its English title when it has one
                work["title"] = row["title"]
        return Response({"results": list(works.values())})


def _serialize_template(t: EmailTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "subject": t.subject,
        "content": blocks_mod.as_blocks(t.content),
        "locales": sorted(t.content),
    }


class AdminEmailTemplatesView(AdminAudited, APIView):
    """List saved templates, or save a broadcast as one
    (``{"name": ..., "from_broadcast": id}``)."""

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.EMAIL_TEMPLATE_SAVE

    def audit_entry(self, request, response):
        return (f"email-template:{response.data.get('id')}", {"name": response.data.get("name", "")})

    def get(self, request):
        return Response({"templates": [_serialize_template(t) for t in EmailTemplate.objects.all()]})

    def post(self, request):
        name = str(request.data.get("name") or "").strip()[:200]
        if not name:
            return Response({"detail": "name is required"}, status=http_status.HTTP_400_BAD_REQUEST)
        source = str(request.data.get("from_broadcast") or "")
        broadcast = Broadcast.objects.filter(pk=source).first() if source.isdigit() else None
        if broadcast is None:
            return Response(
                {"detail": "from_broadcast must name a broadcast"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        template = EmailTemplate.objects.create(
            name=name,
            subject=broadcast.subject,
            content=broadcast.content,
            created_by=actor_email(request),
        )
        return Response(_serialize_template(template), status=http_status.HTTP_201_CREATED)


class AdminEmailTemplateDetailView(AdminAudited, APIView):
    """Delete a saved template (broadcasts made from it are copies, unaffected)."""

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.EMAIL_TEMPLATE_DELETE

    def audit_entry(self, request, response):
        return (f"email-template:{self.kwargs.get('pk')}", {})

    def delete(self, request, pk):
        deleted, _ = EmailTemplate.objects.filter(pk=pk).delete()
        if not deleted:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        return Response(status=http_status.HTTP_204_NO_CONTENT)


class AdminBroadcastTranslationView(AdminAudited, APIView):
    """AI-drafted translations of a broadcast (emails/translation_jobs.py).

    ``POST {"action": "request", "language": "es", "source": "en"}`` files the
    job; ``"fetch"`` pulls the worker's draft in once it's back; ``"approve"``
    marks a draft reviewed. Super-admin-only, like the rest of the Emails
    section — and queueing translation work is a super-admin lever anyway."""

    permission_classes = [IsAdminEmail]

    _AUDIT = {
        "request": AdminAction.Action.EMAIL_TRANSLATION_REQUEST,
        "fetch": AdminAction.Action.EMAIL_TRANSLATION_DRAFT,
        "approve": AdminAction.Action.EMAIL_TRANSLATION_APPROVE,
    }

    def audit_action_for(self, request):
        return self._AUDIT.get(
            str(request.data.get("action", "")), AdminAction.Action.EMAIL_TRANSLATION_REQUEST
        )

    def audit_entry(self, request, response):
        language = str(request.data.get("language", ""))
        entry = (response.data.get("translations") or {}).get(language) or {}
        return (
            f"broadcast:{self.kwargs.get('pk')}:{language}",
            {"state": entry.get("state", ""), "issue": entry.get("url", "")},
        )

    def post(self, request, pk):
        from .admin_views import _serialize_broadcast

        broadcast = Broadcast.objects.filter(pk=pk).first()
        if broadcast is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        action = str(request.data.get("action", ""))
        language = str(request.data.get("language", "")).strip().lower()
        try:
            if action == "request":
                source = str(request.data.get("source") or "en").strip().lower()
                translation_jobs.request(broadcast, source, language, actor=actor_email(request))
            elif action == "fetch":
                translation_jobs.fetch(broadcast, language)
            elif action == "approve":
                translation_jobs.approve(broadcast, language, actor=actor_email(request))
            else:
                return Response(
                    {"detail": "action must be request, fetch or approve"},
                    status=http_status.HTTP_400_BAD_REQUEST,
                )
        except translation_jobs.TranslationJobError as exc:
            return Response({"detail": str(exc)}, status=http_status.HTTP_409_CONFLICT)
        except requests.RequestException:
            return Response(
                {"detail": "GitHub is unreachable — try again shortly."},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )
        broadcast.refresh_from_db()
        return Response(_serialize_broadcast(broadcast, detail=True))
