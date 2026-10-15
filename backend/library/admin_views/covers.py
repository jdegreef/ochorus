"""The cover wall: every published edition's cover, with what it is made of.

A cover is judged on the shelf, beside its neighbours, at the size a reader
meets it — and that is the one view nothing in the library gave. The gates hold
each cover up on its own (contrast, digests, provenance); none of them can see
that seven books in a row are brown landscapes, or that one painter has been
given five covers. This endpoint feeds ``/admin/covers``, which lays the whole
library out at thumbnail size and flags exactly that kind of sameness.

It is read-only and derived. The page draws each edition from its composed
share twin (``coverArt.shareImage``), so all this has to say is what the
picture IS — its tier, and for a museum painting the object and painter, which
only the backend's catalogue tables know.
"""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from ..curated_art import CURATED, CURATED_GROUND, ORIGINAL_GROUND, SOURCES
from ..designed_covers import DERIVED_GROUND, is_designed
from ..models import Book


def cover_tier(slug: str, cover_url: str) -> str:
    """Which kind of picture an edition wears, read from the URL it carries.

    Keyed on the edition's own ``cover_url`` rather than on the catalogue
    tables alone, because the tables describe a WORK and the URL says what this
    edition actually shows: the English edition of a ``DERIVED_GROUND`` work
    wears its designed cover while every translation wears the crop.
    """
    if not cover_url:
        return "none"
    if cover_url.endswith(".svg"):
        return "plate"
    if is_designed(cover_url):
        return "designed"
    if cover_url.startswith("/covers/art/"):
        if slug in ORIGINAL_GROUND:
            return "original"
        if slug in CURATED or slug in CURATED_GROUND:
            return "painting"
        if slug in DERIVED_GROUND:
            return "derived"
    return "other"


def artwork(slug: str) -> dict | None:
    """The museum object behind a painted ground, or None for any other tier."""
    a = CURATED.get(slug) or CURATED_GROUND.get(slug)
    if a is None:
        return None
    source = SOURCES.get(a.source)
    return {
        "artist": a.artist,
        "title": a.title,
        "year": a.year,
        "source": a.source,
        "institution": source.institution if source else a.source,
        "object_id": a.object_id,
    }


@requires(AdminCapability.AUDIT, verb=AdminVerb.VIEW)
class AdminCoversView(APIView):
    """Every published edition's cover and its provenance, for the cover wall."""

    def get(self, request):
        books = (
            Book.objects.filter(is_published=True)
            .select_related("author")
            .only(
                "slug",
                "language",
                "title",
                "cover_title",
                "cover_url",
                "author__slug",
                "author__name",
            )
            .order_by("author__name", "slug", "language")
        )
        return Response(
            [
                {
                    "slug": b.slug,
                    "language": b.language,
                    "title": b.cover_title or b.title,
                    "author": {"slug": b.author.slug, "name": b.author.name},
                    "cover_url": b.cover_url,
                    "tier": (tier := cover_tier(b.slug, b.cover_url)),
                    "artwork": artwork(b.slug) if tier == "painting" else None,
                }
                for b in books
            ]
        )
