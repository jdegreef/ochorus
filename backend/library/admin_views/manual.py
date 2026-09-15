"""Admin dashboard API — serve the Admin Manual PDF to super admins only.

The manual is the operators' handbook for the whole console, so it is gated by
``IsAdminEmail`` (the ``ADMIN_EMAILS`` super-admin allowlist) — deliberately NOT
``RequireCapability``, which would let a scoped grantee (a reviewer, a language
admin) read it. It is a static asset shipped in the API image, streamed inline so
the browser opens it in its PDF viewer; a plain ``<a href>`` on the SPA can't carry
the Supabase bearer token, so the frontend fetches it and opens the blob.
"""

from __future__ import annotations

from pathlib import Path

from django.http import FileResponse, Http404
from rest_framework.views import APIView

from accounts.permissions import IsAdminEmail

# backend/library/assets/admin-manual.pdf (this module is backend/library/admin_views/).
_MANUAL = Path(__file__).resolve().parent.parent / "assets" / "admin-manual.pdf"


class AdminManualView(APIView):
    """GET the Admin Manual PDF. Super admins only."""

    permission_classes = [IsAdminEmail]

    def get(self, request):
        if not _MANUAL.is_file():
            raise Http404("admin manual not found")
        # inline (as_attachment=False) so it opens in the browser's PDF viewer;
        # filename still names the download if the reader chooses to save it.
        return FileResponse(
            _MANUAL.open("rb"),
            content_type="application/pdf",
            as_attachment=False,
            filename="Ochorus-Admin-Manual.pdf",
        )
