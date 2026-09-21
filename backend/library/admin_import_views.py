"""Admin "upload a document" import — a parse/publish endpoint pair.

`parse` accepts a Word/PDF upload and returns a *preview* (detected chapters or a
sermon body) without saving; the admin reviews/edits it in the browser; `publish`
takes the reviewed content back and creates the Book+Chapters or Sermon. Both are
admin-gated (see ``accounts.permissions``). Parsing lives in ``upload_import``.
"""

from __future__ import annotations

from django.utils.text import slugify
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import IsAdminEmail, requires

from . import invalidation, upload_import
from .audit import AdminAudited, AdminNotAudited
from .languages import known_codes, language_map
from .models import AdminAction, Author
from .serializers import AuthorSerializer
from .views import _language_entry


def _unique_author_slug(name: str) -> str:
    """A globally-unique Author slug derived from the name.

    The root is capped short of ``SlugField(max_length=120)`` so an appended
    ``-N`` collision suffix can never overflow the column.
    """
    root = slugify(name)[:110] or "author"
    slug = root
    n = 2
    while Author.objects.filter(slug=slug).exists():
        slug = f"{root}-{n}"
        n += 1
    return slug


@requires(AdminCapability.AUTHORS, verb=AdminVerb.ACT)
class AdminAuthorCreateView(AdminAudited, APIView):
    """POST {name} → create a name-only stub Author.

    Lets the import flow add an author who isn't in the system yet without
    leaving the page; the bio and portrait are filled in later. Returns the
    ``AuthorBio``-shaped row so the picker can select it immediately.
    """

    audit_action = AdminAction.Action.AUTHOR_CREATE

    def audit_entry(self, request, response):
        return f"author:{response.data['slug']}", {"name": response.data.get("name", "")}

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"detail": "An author name is required."}, status=400)
        author = Author.objects.create(slug=_unique_author_slug(name), name=name[:200])
        # AuthorSerializer covers the prose/date fields; book_count is trivially
        # 0 for a just-created author (avoids re-querying for the annotation).
        return Response({**AuthorSerializer(author).data, "book_count": 0}, status=201)


class AdminImportLanguagesView(APIView):
    """GET → every language we support publishing in (not just ones with content).

    The public ``LanguageListView`` only lists languages that already have a
    published book, which would make it impossible to import the *first* book in
    a new language. The import picker uses this fuller list instead.

    Super-admin-only: document import is reserved to the ``ADMIN_EMAILS``
    allowlist (a founder product decision, 2026-09-21). Language admins run
    review/QA on their languages, not raw content ingestion — so the whole import
    surface, picker included, is gated on :class:`IsAdminEmail` rather than the
    ``PUBLISH`` capability a grantee could hold.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        # Every language the registry knows — the import form's target list.
        # Includes drafts on purpose: you import content INTO a language in
        # order to get it ready, so the picker can't be limited to live ones.
        return Response([_language_entry(code) for code in language_map()])


class AdminImportParseView(AdminNotAudited, APIView):
    """POST a file (+ ``kind`` = book|sermon) → detected-chapters preview, no save.

    Super-admin-only (see :class:`AdminImportLanguagesView`)."""

    permission_classes = [IsAdminEmail]
    audit_exempt = (
        "Parses an upload into a preview and returns it. Nothing is written — "
        "publishing is a separate request, and that one is audited."
    )
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        kind = (request.data.get("kind") or "book").strip()
        if not upload:
            return Response({"detail": "No file uploaded."}, status=400)
        # Reject by declared size before read() pulls the whole file into memory.
        if upload.size and upload.size > upload_import.MAX_UPLOAD_BYTES:
            return Response({"detail": "File is too large (max 25 MB)."}, status=400)
        try:
            result = upload_import.parse_upload(upload.read(), upload.name, kind)
        except upload_import.ParseError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(result)


class AdminImportPublishView(AdminAudited, APIView):
    """POST reviewed content → create the Book+Chapters or Sermon; return its link.

    Super-admin-only (see :class:`AdminImportLanguagesView`)."""

    permission_classes = [IsAdminEmail]
    audit_action = AdminAction.Action.CONTENT_PUBLISH

    def audit_entry(self, request, response):
        # This is the endpoint that puts prose in front of readers, and
        # `create_book` stamps every upload PUBLIC_DOMAIN — so it never passes
        # through the review queue. The record of who published it is the only
        # one there will be.
        data = response.data
        target = f"{data['kind']}:{data['slug']}:{request.data.get('language') or 'en'}"
        return target, {
            "title": data.get("title", ""),
            "chapters": data.get("chapters"),
            "source_url": (request.data.get("source_url") or "").strip(),
        }

    def post(self, request):
        d = request.data
        kind = (d.get("kind") or "").strip()
        title = (d.get("title") or "").strip()
        language = (d.get("language") or "en").strip() or "en"
        source_url = (d.get("source_url") or "").strip()

        if kind not in ("book", "sermon"):
            return Response({"detail": "kind must be 'book' or 'sermon'."}, status=400)
        if not title:
            return Response({"detail": "A title is required."}, status=400)
        # Free text before this: a typo published content into a locale that
        # does not exist, where nothing lists it and no reader can reach it —
        # and create_book stamps every upload PUBLIC_DOMAIN, so it would be
        # presented as an original rather than surfacing in the review queue.
        # The same check the translation-job endpoint already makes.
        if language not in known_codes():
            return Response(
                {"detail": f"Unknown language {language!r} — pick one from the list."},
                status=400,
            )
        author = Author.objects.filter(slug=(d.get("author_slug") or "").strip()).first()
        if not author:
            return Response({"detail": "Unknown author — pick one from the list."}, status=400)

        if kind == "book":
            chapters = d.get("chapters") or []
            if not isinstance(chapters, list) or not chapters:
                return Response({"detail": "No chapters to publish."}, status=400)
            try:
                book = upload_import.create_book(
                    author,
                    title,
                    chapters,
                    language,
                    source_url,
                    subtitle=d.get("subtitle"),
                    cover_color=d.get("cover_color"),
                    publication_year=d.get("publication_year"),
                    attribution=d.get("attribution"),
                )
            except upload_import.ParseError as exc:
                return Response({"detail": str(exc)}, status=400)
            # A new published book is reader-visible now but on prerendered pages
            # only after a rebuild — trigger it (and bump the content revision).
            invalidation.mark_content_changed()
            return Response(
                {
                    "kind": "book",
                    "slug": book.slug,
                    "title": book.title,
                    "chapters": book.chapters.count(),
                    "path": f"/books/{book.slug}",
                },
                status=201,
            )

        # `or ""` guards absence, not TYPE: a client sending a number reached
        # .strip() on an int and raised AttributeError — a 500 out of the branch
        # whose whole job is to reject bad input.
        raw_body = d.get("body_html")
        body = raw_body if isinstance(raw_body, str) else ""
        if not body.strip():
            return Response({"detail": "The sermon body is empty."}, status=400)
        try:
            sermon = upload_import.create_sermon(
                author,
                title,
                body,
                language,
                scripture_ref=(d.get("scripture_ref") or ""),
                source_url=source_url,
            )
        except upload_import.ParseError as exc:
            return Response({"detail": str(exc)}, status=400)
        invalidation.mark_content_changed()
        return Response(
            {"kind": "sermon", "slug": sermon.slug, "title": sermon.title, "path": f"/sermons/{sermon.slug}"},
            status=201,
        )
