"""Curated public-domain artwork for the flagship covers.

Tier 3 of the cover rule: a handful of titles get real artwork instead of a
plain typographic plate. The art layer is language-neutral and the type is
drawn over it, so the same painting serves every locale with its own title —
the reason the art is composited rather than baked in.

SOURCE AND LICENCE
Every image comes from a collection whose API states its licence PER OBJECT, so
status is verifiable rather than assumed — the Met's ``isPublicDomain`` flag,
the Cleveland Museum's ``share_license_status``. ``build_curated_covers``
re-checks that flag on every fetch and refuses anything that fails it, because
the manifest records what we believed and the API is what is true.

Both release under CC0, so attribution isn't required; the artist, title and
year are recorded anyway because crediting the work is right, and because a
reader of this file should be able to check the provenance without re-deriving
it. ``SOURCES`` below turns each entry into that receipt.

WHY NOT THE ART INSTITUTE OF CHICAGO, the obvious third: its catalogue API is
excellent, but its IIIF image server refuses programmatic clients — 403 to
every User-Agent tried, a browser's included. Metadata reachable, pixels not,
so it cannot be a source here.

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


class Source(NamedTuple):
    """A collection we take artwork from, and how to cite and check it."""

    #: How the credit line names the institution, after the artist and title.
    institution: str
    #: The public page for one object, as a `{}` template for its id. Data for
    #: a human checking provenance — format it and open it — not a code path;
    #: nothing renders a link to the source, and a reader gets the artist,
    #: title and year through `credit()` instead.
    object_url: str


SOURCES: dict[str, Source] = {
    "met": Source(
        "The Metropolitan Museum of Art, Open Access",
        "https://www.metmuseum.org/art/collection/search/{}",
    ),
    "cma": Source(
        "The Cleveland Museum of Art, CC0",
        "https://www.clevelandart.org/art/{}",
    ),
}


class Artwork(NamedTuple):
    #: Which collection — a key of ``SOURCES``.
    source: str
    #: That collection's own object id. Not globally unique; it means nothing
    #: without ``source``, which is why the two always travel together.
    object_id: int
    artist: str
    title: str
    year: str
    why: str


# slug -> artwork. Slugs match Book.slug (shared across languages).
CURATED: dict[str, Artwork] = {
    "waiting-on-god": Artwork(
        "met", 437914, "Simon de Vlieger", "Calm Sea", "ca. 1640s",
        "Still water under a wide sky — waiting, held rather than idle.",
    ),
    "all-of-grace": Artwork(
        "met", 438642, "Simon Denis", "Cloud Study (Early Evening)", "ca. 1786–1806",
        "Light breaking through cloud; grace as something given, not achieved.",
    ),
    "prevailing-prayer": Artwork(
        "met", 437526, "Peter Paul Rubens", "A Forest at Dawn with a Deer Hunt", "ca. 1635",
        "Dark wood at first light — prayer that persists until morning.",
    ),
    "the-fourfold-gospel": Artwork(
        "met", 283081, "Roger Fenton", "Salisbury Cathedral — The Nave", "1858",
        "A nave receding into light: the one gospel seen down its full length.",
    ),
    "life-and-diary-of-david-brainerd": Artwork(
        "met", 16875, "Worthington Whittredge", "The Brook in the Woods", "ca. 1885–90",
        "American forest — the wilderness Brainerd actually walked into.",
    ),
    "pilgrims-progress": Artwork(
        "met", 459103, "Henri-Joseph Harpignies", "The Rocky Path in the Morvan", "1878",
        "A path climbing out of frame. The book in one image.",
    ),
    "the-reformed-pastor": Artwork(
        "met", 928532, "Pieter Jansz. Saenredam", "Interior of the Sint-Pieterskerk", "1632",
        "A whitewashed reformed church — Baxter's own subject, drawn from life.",
    ),
    "ten-commandments": Artwork(
        "met", 359021, "John Ruskin", "The Valley of Lauterbrunnen, Switzerland", "1866",
        "The mountain, where the Law was given.",
    ),
    "confessions": Artwork(
        "met", 436455, "Théodore Géricault", "Evening: Landscape with an Aqueduct", "1818",
        "Late-Roman architecture at dusk — Augustine's own world and hour.",
    ),
    "freedom-of-the-will": Artwork(
        "met", 11319, "John Frederick Kensett", "Passing off of the Storm", "1872",
        "Weather clearing over water: will and providence, without an argument.",
    ),
    # ── Batch 2 ────────────────────────────────────────────────────────────
    # Same art direction as above: landscape, architecture, sky, path. For the
    # Puritans that means their century's own painters, since the Dutch
    # landscape school and the English divines are contemporaries — where a
    # book's subject is a road, it gets the road a reader of 1670 would have
    # walked. Where the subject is an interior life, the art is an interior.
    "a-call-to-the-unconverted": Artwork(
        "met", 436653, "Meyndert Hobbema", "Woodland Road", "ca. 1670",
        "A road leaving the frame, painted in Baxter's own decade — the book is "
        "a summons to set out, and this is what setting out looked like to him.",
    ),
    "grace-abounding": Artwork(
        "met", 437549, "Jacob van Ruisdael", "Wheat Fields", "ca. 1670",
        "Two figures on a track under an enormous half-cleared sky. Bunyan's "
        "century, and his subject: weather that is neither storm nor fair.",
    ),
    "religious-affections": Artwork(
        "met", 435907, "Claude Lorrain (Claude Gellée)", "Sunrise", "possibly 1646–47",
        "Edwards' whole argument is that true religion is a LIGHT rather than a "
        "feeling worked up. Claude painted first light better than anyone.",
    ),
    "the-imitation-of-christ": Artwork(
        "cma", 150354, "Jakob Alt",
        "View of the Cloister of San Giovanni in Laterano, Rome", "1836",
        "A monk alone in a cloister, reading. Thomas à Kempis spent seventy "
        "years in one monastery and wrote this for the novices there; the "
        "picture is very nearly the book's own setting.",
    ),
    "answers-to-prayer": Artwork(
        "met", 436305, "Georg Flegel", "Still Life", "probably ca. 1625–30",
        "A laid table with bread on it and nobody in the room. Müller prayed "
        "for the orphans' next meal and it came; this is the answer rather "
        "than the asking.",
    ),
    "union-and-communion": Artwork(
        "met", 436085, "Charles-François Daubigny", "Apple Blossoms", "1873",
        "Taylor is reading the Song of Songs, which is set in an orchard — a "
        "garden enclosed, the vines in flower. Painted in his own decade.",
    ),
}


def credit(slug: str) -> str | None:
    """One-line attribution for a curated cover, or None if it has no art.

    Lenient about an unknown ``source`` rather than raising, because this runs
    on the REQUEST path — the book detail serializer is its only caller — and a
    manifest typo should cost a credit line, not turn a public book page into a
    500. `test_every_entry_records_its_provenance_and_reason` is what actually
    stops such an entry, before it is ever deployed; this is the floor under it.
    """
    a = CURATED.get(slug)
    source = SOURCES.get(a.source) if a else None
    if not a or source is None:
        return None
    return f"{a.artist}, “{a.title}” ({a.year}). {source.institution}."

