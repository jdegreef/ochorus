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
    # ── Batch 3 ────────────────────────────────────────────────────────────
    # Where a book is ABOUT a place and a moment, the art comes from that place
    # and near that moment: Finney gets the American landscape of his own
    # burned-over district, painted three years after his lectures. That is two
    # of the six, and the rule is not general — four of these are Dutch Golden
    # Age landscapes on books that are neither Dutch nor of that century,
    # chosen for what they show rather than when they were painted. Whitefield's
    # enormous sky is a van Goyen because the sky is the subject, not because
    # 1646 has anything to do with him.
    #
    # ONE PAIRING IS DELIBERATE, and only one: the two Hobbema roads. Everything
    # else here should be able to stand on its own book.
    "all-things-for-good": Artwork(
        "cma", 148363, "Simon de Vlieger",
        "Sleeping Peasants near Fields (Parable of the Weeds)", "1650–53",
        "Watson is expounding Romans 8:28, and this is the parable next door: "
        "wheat and tares left to grow together while men sleep. Painted in his "
        "own decade, and it trusts providence rather than explaining it.",
    ),
    "till-he-come": Artwork(
        "met", 437975, "Andreas Achenbach",
        "Sunset after a Storm on the Coast of Sicily", "1853",
        "Communion meditations, and the title is 1 Corinthians 11:26 — the "
        "church between the cross and the return. Light coming from behind the "
        "headland, not yet arrived.",
    ),
    "the-way-to-god": Artwork(
        "met", 436652, "Meyndert Hobbema", "Entrance to a Village", "ca. 1665",
        "A road ARRIVING somewhere, deliberately paired with the Hobbema on "
        "`a-call-to-the-unconverted`, which is a road leaving. Baxter summons a "
        "reader to set out; Moody tells him where the road goes.",
    ),
    "revival-lectures": Artwork(
        "cma", 93014, "Thomas Cole",
        "View of Schroon Mountain, Essex County, New York, After a Storm", "1838",
        "Finney's own decade, his own country, and very nearly his own county — "
        "the burned-over district. A landscape after a storm, which is what he "
        "spent the book arguing a revival leaves behind.",
    ),
    "selected-sermons-whitefield": Artwork(
        "met", 436558, "Jan van Goyen", "View of Haarlem and the Haarlemmer Meer", "1646",
        "Nine tenths sky over a low horizon. Whitefield preached in fields to "
        "crowds no building could hold, and this is what they were standing "
        "under.",
    ),
    "the-normal-christian-life": Artwork(
        "met", 437191, "Aert van der Neer", "Landscape at Sunset", "1650s",
        "Ordinary evening, ordinary people going home, nothing singled out. "
        "Nee's whole argument is that what the New Testament describes is not "
        "the exceptional Christian life but the normal one.",
    ),
    # ── Batch 4 ────────────────────────────────────────────────────────────
    # The last fifteen, which is every remaining generated plate in the English
    # library. Chosen against each other as much as individually: they land on
    # one shelf, so two books on one subject do not get one picture (Murray's
    # moving stream against Simpson's still pond), and the four Watchman Nee
    # editions are deliberately four different weathers.
    "around-the-wicket-gate": Artwork(
        "cma", 97189, "Herman van Swanevelt", "Landscape with Travelers", "1630s",
        "Travellers at a bridge, not yet across. Spurgeon is writing to the "
        "people standing AROUND the gate rather than through it, and the whole "
        "book is a friendly hand on the elbow.",
    ),
    "cheque-book": Artwork(
        "met", 438380, "Salomon van Ruysdael", "Fishing Boats on a River", "early 1660s",
        "Daily readings on God's promises. This is daily provision being drawn "
        "out of the water — the same errand every morning, the sail already up "
        "before anyone has decided whether to trust it.",
    ),
    "days-of-heaven-upon-earth": Artwork(
        "cma", 134072, "George Inness", "Sunny Autumn Day", "1892",
        "A year of daily devotions. Inness spent his life painting the ordinary "
        "American afternoon as though the light in it came from somewhere else, "
        "which is this book's title and not a word more.",
    ),
    "divine-healing": Artwork(
        "met", 436090, "Charles-François Daubigny",
        "Landscape with a Sunlit Stream", "ca. 1877",
        "Moving water with light let into it. Murray's case is that healing is "
        "God's ordinary provision rather than a spectacle, so the picture is a "
        "stream and not a miracle.",
    ),
    "grace-for-grace-2": Artwork(
        "cma", 140338, "Charles-François Daubigny", "Sunset on the River Oise", "1866",
        "John 1:16 — grace UPON grace, one measure laid over the last until "
        "there is nothing left to add. Light on water is the only thing that "
        "does that in front of you.",
    ),
    "if": Artwork(
        "cma", 133298, "George Inness", "Montclair, New Jersey", "c. 1878",
        "A hundred one-line self-examinations, not one of which raises its "
        "voice. Neither does this: a hazy valley, olive trees, nothing "
        "insisting on itself. The quietest painting in the library, for the "
        "quietest book in it.",
    ),
    "let-us-pray-2": Artwork(
        "cma", 128371, "Camille Corot", "The Pond at the Entrance of the Woods", "c. 1860–75",
        "The edge of a wood, where you go to be out of sight. Nee is writing "
        "about the closet rather than the platform.",
    ),
    "plain-account-christian-perfection": Artwork(
        "cma", 154962, "Richard Wilson", "Cader Idris, with the Mawddach River", "c. 1774",
        "Wesley's own century and his own roads — he rode something like a "
        "quarter of a million miles over country of exactly this kind. "
        "Perfection as a long way up, which is how the book argues it.",
    ),
    "sermons-on-several-occasions": Artwork(
        "cma", 128363, "Charles-François Daubigny",
        "Villerville Seen from Le Ratier", "1855",
        "The same enormous sky over a low horizon that `selected-sermons-"
        "whitefield` wears, and the echo is the point: the two men preached the "
        "same way, in the open, to whoever came.",
    ),
    # Susanna Wesley HAS artwork now, and the reason she had none still stands.
    # Every candidate was a period PORTRAIT of a different real woman, and a
    # portrait on a cover reads as a portrait OF the subject — so shipping one
    # would have claimed an image is Susanna Wesley when it is not. That
    # objection is about portraits, not about her, and it does not reach a
    # house. Her life's work was a household: ten surviving children taught at
    # a kitchen table, in this century. So the cover is the house, and nobody
    # in it is being passed off as her.
    "susanna-wesley-clarke": Artwork(
        "met", 438116, "Francesco Guardi", "The Villa Loredan, Paese", "early 1780s",
        "A house of her century, for a woman whose work was a household — and "
        "not a face, which is the one thing this book must not be given.",
    ),
    "the-body-of-christ-a-reality": Artwork(
        "met", 436556, "Jan van Goyen", "Country House near the Water", "1646",
        "The title is arguing that the body is a fact and not a figure of "
        "speech, so it gets a building: something actually standing there, "
        "weathered, lived in, with boats tied up against it.",
    ),
    "the-body-of-christ-teens": Artwork(
        "cma", 110952, "George Inness", "Landscape", "1888",
        "The same subject as `the-body-of-christ-a-reality` in a younger "
        "register — one small figure under trees that read as a wood rather "
        "than as a crowd of separate trees.",
    ),
    "the-gospel-of-healing": Artwork(
        "cma", 124078, "Camille Corot", "Pond at Ville-d'Avray", "late 1860s",
        "Still water, where Murray's `divine-healing` gets a moving stream. Two "
        "books on one subject sitting on one shelf should not wear one picture.",
    ),
    "things-as-they-are": Artwork(
        "cma", 148365, "Georges Michel", "Landscape Near Paris", "c. 1840",
        "Carmichael wrote this to correct the romance in mission reports and "
        "was told it was too discouraging to print. Hard country under a heavy "
        "sky, the people in it very small. Deliberately NOT a picture of India: "
        "the European painting of Indian subjects available here is precisely "
        "the exoticism the book exists to refuse.",
    ),
    "way-into-holiest": Artwork(
        "cma", 109239, "George Inness", "A Winter Sky", "1866",
        "Hebrews, and the veil. A burning horizon at the far end of a cold "
        "marsh: the light is real, and it is not where you are standing.",
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

