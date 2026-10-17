"""Admin API for designing campaigns: live preview, the library picker, and
saved templates.

Kept apart from ``admin_views`` (sending, metrics, readers) so neither grows into
a god-module. Super-admin-only like the rest of the Emails section.
"""

from __future__ import annotations

import requests
from django.db.models import Q
from rest_framework import status as http_status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile
from accounts.permissions import IsAdminEmail
from library.audit import AdminAudited, AdminNotAudited, actor_email
from library.models import AdminAction

from . import blocks as blocks_mod
from . import copy as copy_mod
from . import images, library_search, merge_tags, starter_templates, translation_jobs
from .admin_views import _serialize_broadcast
from .models import Broadcast, EmailSubscription, EmailTemplate, TemplateCategory
from .rendering import render_blocks

#: How many works the library picker returns per search.
LIBRARY_LIMIT = 20


class AdminEmailPreviewView(AdminNotAudited, APIView):
    """Render one language of a design exactly as a reader would receive it —
    the unsaved editor state, so the preview follows every keystroke.

    Body: ``{"locale": "es", "subject": "...", "content": {...one language...},
    "as": "me" | "sample" | "new"}``. ``me`` (the default) renders for the
    admin's own account when it has one — their own merge-tag values; ``sample``
    for a made-up reader with every tag filled; ``new`` for a reader with no
    name and no reading yet, to see the fallbacks and the sentences that drop
    out. Never touches the database: the subscription is a stand-in, so the
    footer links in a preview go nowhere.
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
        reader = str(request.data.get("as") or "me")
        uid = getattr(request.user, "username", "")
        profile = UserProfile()
        if reader == "me" and uid:
            profile = UserProfile.objects.filter(supabase_uid=uid).first() or profile
        rendered = render_blocks(
            subject=str(request.data.get("subject") or "")[:300],
            content=content,
            profile=profile,
            subscription=EmailSubscription(unsubscribe_token="preview"),
            lang=locale,
            values=merge_tags.sample_values(locale) if reader == "sample" else None,
        )
        return Response({"subject": rendered.subject, "html": rendered.html})


class AdminEmailLibraryView(AdminNotAudited, APIView):
    """Search the library for the picker: ``?type=<block type>&q=…`` (book,
    sermon, plan, article, author or topic), or look up exact items with
    ``&slugs=a,b`` (what a saved design already names).

    One row per item (slug), with every language it reaches, so the designer
    can show at a glance which emails a block will appear in."""

    permission_classes = [IsAdminEmail]
    audit_exempt = "Read-only search."

    def get(self, request):
        kind = request.query_params.get("type", blocks_mod.BlockType.BOOK)
        if kind not in blocks_mod.SLUG_TYPES:
            return Response(
                {"detail": f"type must be one of {', '.join(blocks_mod.SLUG_TYPES)}"},
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        _, _, _, title_field = blocks_mod.LIBRARY[kind]
        model = blocks_mod.library_model(kind)
        if kind == blocks_mod.BlockType.AUTHOR:
            rows = model.objects.filter(is_imprint=False, list_in_biographies=True)
        else:
            rows = model.objects.filter(is_published=True)
        exact = [s for s in request.query_params.get("slugs", "").split(",") if s]
        if exact:
            slugs = exact[:LIBRARY_LIMIT]
        else:
            q = request.query_params.get("q", "").strip()
            matches = rows.filter(Q(**{f"{title_field}__icontains": q}) | Q(slug__icontains=q)) if q else rows
            slugs = list(matches.order_by("slug").values_list("slug", flat=True).distinct()[:LIBRARY_LIMIT])
        reach = blocks_mod.editions(kind, slugs)
        if kind in blocks_mod.LIBRARY_TYPES:
            works = blocks_mod.works_by_slug(kind, rows, slugs)
        else:
            works = {
                row["slug"]: {"slug": row["slug"], "title": row[title_field], "author": ""}
                for row in rows.filter(slug__in=slugs).order_by("slug").values("slug", title_field)
            }
        for work in works.values():
            work.pop("cover", None)
            work["languages"] = sorted(reach.get(work["slug"], set()))
        return Response({"results": list(works.values())})


class AdminEmailMergeTagsView(AdminNotAudited, APIView):
    """The merge tags the designer offers, with a sample value and what each
    means (emails/merge_tags.py)."""

    permission_classes = [IsAdminEmail]
    audit_exempt = "Read-only list."

    def get(self, request):
        return Response(
            {
                "tags": [
                    {"key": t.key, "label": t.label, "sample": t.sample, "description": t.description}
                    for t in merge_tags.TAGS.values()
                ],
                "friend": copy_mod.FRIEND,
            }
        )


class AdminEmailLibrarySearchView(AdminNotAudited, APIView):
    """The "Insert from the library" panel: ``?q=…`` across books, sermons,
    plans, articles, authors, topics and quotes, each result with the block
    that inserts it (emails/library_search.py)."""

    permission_classes = [IsAdminEmail]
    audit_exempt = "Read-only search."

    def get(self, request):
        return Response(library_search.search(request.query_params.get("q", "")[:100]))


def _serialize_template(t: EmailTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "category": t.category,
        "description": t.description,
        "created_by": t.created_by,
        "subject": t.subject,
        "content": blocks_mod.as_blocks(t.content),
        "locales": sorted(t.content),
    }


class AdminEmailTemplatesView(AdminAudited, APIView):
    """List the starter templates and the team's saved ones, or save a broadcast
    as one (``{"name", "from_broadcast": id, "category"?, "description"?}``)."""

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.EMAIL_TEMPLATE_SAVE

    def audit_entry(self, request, response):
        return (f"email-template:{response.data.get('id')}", {"name": response.data.get("name", "")})

    def get(self, request):
        return Response(
            {
                "templates": [_serialize_template(t) for t in EmailTemplate.objects.all()],
                "starters": [starter_templates.serialize(t) for t in starter_templates.STARTERS],
                "categories": [{"key": k, "label": label} for k, label in TemplateCategory.choices],
            }
        )

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
            **_described(request.data),
        )
        return Response(_serialize_template(template), status=http_status.HTTP_201_CREATED)


def _described(data) -> dict:
    """The category and description fields from request data, cleaned."""
    out = {}
    if data.get("category") in TemplateCategory.values:
        out["category"] = data["category"]
    if "description" in data:
        out["description"] = str(data.get("description") or "").strip()[:300]
    return out


class AdminEmailTemplateDetailView(AdminAudited, APIView):
    """Rename or re-describe a saved template (``PATCH {"name"?, "category"?,
    "description"?}``), or delete it — broadcasts made from it are copies,
    unaffected either way."""

    permission_classes = [IsAdminEmail]

    def audit_action_for(self, request):
        if request.method == "DELETE":
            return AdminAction.Action.EMAIL_TEMPLATE_DELETE
        return AdminAction.Action.EMAIL_TEMPLATE_SAVE

    def audit_entry(self, request, response):
        detail = {}
        if request.method == "PATCH" and isinstance(response.data, dict):
            detail = {"edited": True, "name": response.data.get("name", "")}
        return (f"email-template:{self.kwargs.get('pk')}", detail)

    def patch(self, request, pk):
        template = EmailTemplate.objects.filter(pk=pk).first()
        if template is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        if "name" in request.data:
            name = str(request.data.get("name") or "").strip()[:200]
            if not name:
                return Response({"detail": "name can't be empty"}, status=http_status.HTTP_400_BAD_REQUEST)
            template.name = name
        for field, value in _described(request.data).items():
            setattr(template, field, value)
        template.save()
        return Response(_serialize_template(template))

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
        language = str(request.data.get("language", "")).strip().lower()
        entry = (response.data.get("translations") or {}).get(language) or {}
        return (
            f"broadcast:{self.kwargs.get('pk')}:{language}",
            {"state": entry.get("state", ""), "issue": entry.get("url", "")},
        )

    def post(self, request, pk):
        broadcast = Broadcast.objects.filter(pk=pk).first()
        if broadcast is None:
            return Response(status=http_status.HTTP_404_NOT_FOUND)
        action = str(request.data.get("action", ""))
        language = str(request.data.get("language", "")).strip().lower()
        try:
            if action == "request":
                source = str(request.data.get("source") or "en").strip().lower()
                translation_jobs.request(broadcast, source, language)
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
        return Response(_serialize_broadcast(broadcast, detail=True))


class AdminEmailImageView(AdminAudited, APIView):
    """Upload a picture for an email (multipart ``file``); returns its public
    ``url`` for an image or hero block (emails/images.py)."""

    permission_classes = [IsAdminEmail]
    parser_classes = [MultiPartParser]
    audit_action = AdminAction.Action.EMAIL_IMAGE_UPLOAD

    def audit_entry(self, request, response):
        return ("email-image", {"url": response.data.get("url", "")})

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "choose a picture to upload"}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            url = images.upload(upload.read())
        except images.ImageError as exc:
            return Response({"detail": str(exc)}, status=http_status.HTTP_400_BAD_REQUEST)
        except requests.RequestException:
            return Response(
                {"detail": "The image store didn't answer — try again shortly."},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"url": url}, status=http_status.HTTP_201_CREATED)
