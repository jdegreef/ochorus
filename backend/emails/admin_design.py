"""Admin API for designing campaigns: live preview, the library picker, and
saved templates.

Kept apart from ``admin_views`` (sending, metrics, readers) so neither grows into
a god-module. Super-admin-only like the rest of the Emails section.
"""

from __future__ import annotations

from django.db.models import Q
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile
from accounts.permissions import IsAdminEmail
from library.audit import AdminAudited, AdminNotAudited, actor_email
from library.models import AdminAction

from . import blocks as blocks_mod
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
    """Search the library for the picker: ``?type=book|sermon|plan&q=…``.

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
        q = request.query_params.get("q", "").strip()
        model = blocks_mod.library_model(kind)
        qs = model.objects.filter(is_published=True)
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(slug__icontains=q))
        if kind != blocks_mod.BlockType.PLAN:
            qs = qs.select_related("author")
        works: dict[str, dict] = {}
        for work in qs.order_by("slug", "language")[:500]:
            row = works.get(work.slug)
            if row is None:
                if len(works) >= LIBRARY_LIMIT:
                    continue
                row = works[work.slug] = {
                    "slug": work.slug,
                    "title": work.title,
                    "author": work.author.name if kind != blocks_mod.BlockType.PLAN else "",
                    "languages": [],
                }
            row["languages"].append(work.language)
            if work.language == "en":  # name a work by its English title when it has one
                row["title"] = work.title
        return Response({"results": list(works.values())})


def _serialize_template(t: EmailTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "subject": t.subject,
        "content": t.content,
        "locales": sorted(t.content),
        "created_by": t.created_by,
        "updated_at": t.updated_at.isoformat(),
    }


class AdminEmailTemplatesView(AdminAudited, APIView):
    """List saved templates, or save one — from a design in the body, or from an
    existing broadcast (``{"name": ..., "from_broadcast": id}``)."""

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
        template = EmailTemplate(
            name=name,
            description=str(request.data.get("description") or "").strip()[:300],
            created_by=actor_email(request),
        )
        source = request.data.get("from_broadcast")
        if source is not None:
            broadcast = Broadcast.objects.filter(pk=source).first()
            if broadcast is None:
                return Response(status=http_status.HTTP_404_NOT_FOUND)
            template.subject, template.content = broadcast.subject, broadcast.content
        else:
            subject = request.data.get("subject") or {}
            template.subject = subject if isinstance(subject, dict) else {}
            template.content = blocks_mod.clean_content(request.data.get("content") or {})
        template.save()
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
