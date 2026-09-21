"""Admin dashboard API — serve the operator manuals as inline PDFs.

Two handbooks, two audiences:

* :class:`AdminManualView` — the whole-console operators' manual, gated by
  ``IsAdminEmail`` (the ``ADMIN_EMAILS`` super-admin allowlist) — deliberately NOT
  ``RequireCapability``, which would let a scoped grantee read it.
* :class:`AdminLanguageManualView` — the handbook written *for* language admins
  (any non-super admin), so it is gated on the ``REPORTING/view`` capability every
  admin role preset holds (a super admin passes ``RequireCapability`` outright).

Both are static assets shipped in the API image, streamed inline so the browser
opens them in its PDF viewer; a plain ``<a href>`` on the SPA can't carry the
Supabase bearer token, so the frontend fetches the blob (see ``library-admin.ts``).
"""

from __future__ import annotations

from pathlib import Path

from django.http import FileResponse, Http404
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import IsAdminEmail, requires

# backend/library/assets/*.pdf (this module is backend/library/admin_views/).
_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_MANUAL = _ASSETS / "admin-manual.pdf"
_LANGUAGE_MANUAL = _ASSETS / "language-admin-manual.pdf"


def _serve_pdf(path: Path, *, filename: str, what: str) -> FileResponse:
    """Stream a manual PDF inline (as_attachment=False) so the browser opens it in
    its PDF viewer; ``filename`` still names the download if the reader saves it."""
    if not path.is_file():
        raise Http404(f"{what} not found")
    return FileResponse(
        path.open("rb"),
        content_type="application/pdf",
        as_attachment=False,
        filename=filename,
    )


class AdminManualView(APIView):
    """GET the Admin Manual PDF. Super admins only."""

    permission_classes = [IsAdminEmail]

    def get(self, request):
        return _serve_pdf(_MANUAL, filename="Ochorus-Admin-Manual.pdf", what="admin manual")


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminLanguageManualView(APIView):
    """GET the Language Admin Manual PDF — for any admin (super or scoped grant)."""

    def get(self, request):
        return _serve_pdf(
            _LANGUAGE_MANUAL,
            filename="Ochorus-Language-Admin-Manual.pdf",
            what="language admin manual",
        )
