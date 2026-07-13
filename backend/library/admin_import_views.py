"""Admin "upload a document" import — a parse/publish endpoint pair.

`parse` accepts a Word/PDF upload and returns a *preview* (detected chapters or a
sermon body) without saving; the admin reviews/edits it in the browser; `publish`
takes the reviewed content back and creates the Book+Chapters or Sermon. Both are
admin-gated (see ``accounts.permissions``). Parsing lives in ``upload_import``.
"""

from __future__ import annotations

from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

from . import upload_import
from .models import Author
from .views import LANGUAGE_NAMES, _language_entry


class AdminImportLanguagesView(APIView):
    """GET → every language we support publishing in (not just ones with content).

    The public ``LanguageListView`` only lists languages that already have a
    published book, which would make it impossible to import the *first* book in
    a new language. The import picker uses this fuller list instead.
    """

    permission_classes = [IsAdminEmail]

    def get(self, request):
        return Response([_language_entry(code) for code in LANGUAGE_NAMES])


class AdminImportParseView(APIView):
    """POST a file (+ ``kind`` = book|sermon) → detected-chapters preview, no save."""

    permission_classes = [IsAdminEmail]
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


class AdminImportPublishView(APIView):
    """POST reviewed content → create the Book+Chapters or Sermon; return its link."""

    permission_classes = [IsAdminEmail]

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
        author = Author.objects.filter(slug=(d.get("author_slug") or "").strip()).first()
        if not author:
            return Response({"detail": "Unknown author — pick one from the list."}, status=400)

        if kind == "book":
            chapters = d.get("chapters") or []
            if not isinstance(chapters, list) or not chapters:
                return Response({"detail": "No chapters to publish."}, status=400)
            try:
                book = upload_import.create_book(author, title, chapters, language, source_url)
            except upload_import.ParseError as exc:
                return Response({"detail": str(exc)}, status=400)
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

        body = d.get("body_html") or ""
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
        return Response(
            {"kind": "sermon", "slug": sermon.slug, "title": sermon.title, "path": f"/sermons/{sermon.slug}"},
            status=201,
        )
