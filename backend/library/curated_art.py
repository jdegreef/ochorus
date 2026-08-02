"""Curated public-domain artwork for the flagship covers.

Tier 3 of the cover rule: a handful of titles get real artwork instead of a
plain typographic plate. The art layer is language-neutral and the type is
drawn over it, so the same painting serves every locale with its own title —
the reason the art is composited rather than baked in.

SOURCE AND LICENCE
Every image is from the Metropolitan Museum of Art's Open Access collection,
chosen because the API exposes an explicit ``isPublicDomain`` flag: licence
status is verifiable per object rather than assumed. The object id below is the
receipt — https://www.metmuseum.org/art/collection/search/<id>. The Met
releases these under CC0; attribution isn't required, but the artist and title
are recorded here because crediting the work is right, and because a future
reader of this file should be able to check the provenance without re-deriving
it.

ART DIRECTION — landscape, architecture, sky, water, path.
Deliberately no figurative devotional painting. The Met's religious holdings
are overwhelmingly Catholic and medieval, and a saint or a Madonna sits wrong
on a Protestant evangelical classic — the first pass surfaced Barocci's
*Saint Francis* for a Moody revival book, which is the mismatch in miniature.
Landscape and architecture carry the subject without claiming a tradition.

NOT EVERY BOOK SHOULD GET ART. Susanna Wesley is deliberately absent: every
candidate was a period portrait of a different real woman, and a portrait on a
cover reads as a portrait OF that person. Shipping one would imply an image is
Susanna Wesley when it isn't. She keeps a generated cover.
"""

from __future__ import annotations

from typing import NamedTuple


class Artwork(NamedTuple):
    met_id: int
    artist: str
    title: str
    year: str
    why: str


# slug -> artwork. Slugs match Book.slug (shared across languages).
CURATED: dict[str, Artwork] = {
    "waiting-on-god": Artwork(
        437914, "Simon de Vlieger", "Calm Sea", "ca. 1640s",
        "Still water under a wide sky — waiting, held rather than idle.",
    ),
    "all-of-grace": Artwork(
        438642, "Simon Denis", "Cloud Study (Early Evening)", "ca. 1786–1806",
        "Light breaking through cloud; grace as something given, not achieved.",
    ),
    "prevailing-prayer": Artwork(
        437526, "Peter Paul Rubens", "A Forest at Dawn with a Deer Hunt", "ca. 1635",
        "Dark wood at first light — prayer that persists until morning.",
    ),
    "the-fourfold-gospel": Artwork(
        283081, "Roger Fenton", "Salisbury Cathedral — The Nave", "1858",
        "A nave receding into light: the one gospel seen down its full length.",
    ),
    "life-and-diary-of-david-brainerd": Artwork(
        16875, "Worthington Whittredge", "The Brook in the Woods", "ca. 1885–90",
        "American forest — the wilderness Brainerd actually walked into.",
    ),
    "pilgrims-progress": Artwork(
        459103, "Henri-Joseph Harpignies", "The Rocky Path in the Morvan", "1878",
        "A path climbing out of frame. The book in one image.",
    ),
    "the-reformed-pastor": Artwork(
        928532, "Pieter Jansz. Saenredam", "Interior of the Sint-Pieterskerk", "1632",
        "A whitewashed reformed church — Baxter's own subject, drawn from life.",
    ),
    "ten-commandments": Artwork(
        359021, "John Ruskin", "The Valley of Lauterbrunnen, Switzerland", "1866",
        "The mountain, where the Law was given.",
    ),
    "confessions": Artwork(
        436455, "Théodore Géricault", "Evening: Landscape with an Aqueduct", "1818",
        "Late-Roman architecture at dusk — Augustine's own world and hour.",
    ),
    "freedom-of-the-will": Artwork(
        11319, "John Frederick Kensett", "Passing off of the Storm", "1872",
        "Weather clearing over water: will and providence, without an argument.",
    ),
}

MET_OBJECT_URL = "https://www.metmuseum.org/art/collection/search/{}"


def credit(slug: str) -> str | None:
    """One-line attribution for a curated cover, or None if it has no art."""
    a = CURATED.get(slug)
    if not a:
        return None
    return f"{a.artist}, “{a.title}” ({a.year}). The Metropolitan Museum of Art, Open Access."
