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
    #: WHERE in the painting the 3:4 plate is taken from, along whichever axis
    #: overflows: 0 is the left (or top) edge, 1 the right (or bottom), 0.5 the
    #: centre. Default 0.5, which is what every entry above was cropped at.
    #:
    #: A cover is 3:4 and most of these paintings are wide landscapes, so
    #: cropping to fill throws away a third to a half of the picture — and a
    #: centre crop assumes the subject is in the middle, which is exactly what a
    #: landscape composition tends not to do. Hobbema's road leaves the frame at
    #: one side; Saenredam's nave recedes from a corner. `DERIVED_GROUND` has
    #: carried per-work crop numbers from the start, for the same reason and with
    #: the same lesson behind it: framing is most of whether a ground reads as a
    #: picture or as a texture.
    #:
    #: Nothing detects a crop left stale by a changed `focus` — unlike a derived
    #: ground, which digests the cover it was cut from, a museum's image has no
    #: digest recorded here. Change this and re-run `build_curated_covers`.
    focus: float = 0.5


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
    # ── Batch 3 · Andrew Murray's plate books ──────────────────────────────
    # Murray held a devotional style and a handful of hand-made covers, but five
    # of his works wore a flat coloured plate — the shelf's one place a reader
    # looks first said they were the lesser editions. These give them the same
    # painted ground his designed covers carry. Two of his own century's Dutch
    # painters — van Gogh (a Reformed pastor's son) — because Murray was a Dutch
    # Reformed minister of the Cape, and the shelf should sound like his world.
    "divine-healing": Artwork(
        "met", 437518, "Théodore Rousseau", "A River in a Meadow", "ca. 1840",
        "Still, restorative water under an open sky — healing as something the "
        "body is returned to rather than seized. Barbizon, Murray's own century.",
    ),
    "ministry-of-intercession": Artwork(
        "met", 438490, "Emanuel de Witte", "Interior of the Oude Kerk, Delft", "probably 1650",
        "A Dutch Reformed church interior, columns receding into light and a few "
        "figures at prayer below — Murray's own tradition, and the book is a plea "
        "for more of exactly what is happening in it.",
        focus=0.4,
    ),
    "holy-in-christ": Artwork(
        "met", 436535, "Vincent van Gogh", "Wheat Field with Cypresses", "1889",
        "Field and trees straining up toward a radiant sky — holiness as a life "
        "drawn into the light rather than scrubbed of fault. Van Gogh, a Reformed "
        "pastor's son, and Murray's exact decade.",
        focus=0.6,
    ),
    "true-vine": Artwork(
        "met", 435809, "Pieter Bruegel the Elder", "The Harvesters", "1565",
        "The harvest laid in under a great tree — \"that ye bear much fruit\" "
        "(John 15), which the book meditates on for a month. The definitive "
        "painting of a harvest brought in.",
        focus=0.45,
    ),
    "absolute-surrender": Artwork(
        "met", 437980, "Vincent van Gogh", "Cypresses", "1889",
        "A single cypress rising like green flame into a churning sky — the self "
        "wholly given up, taken up. Van Gogh again, one year on, for the book of "
        "Murray's that asks for everything.",
    ),
    # ── Batch 4 · E. M. Bounds's prayer books ──────────────────────────────
    # Bounds wrote nothing but prayer — six plate-covered works, one subject. Six
    # DIFFERENT Western landscape painters, one facet of prayer each, so the shelf
    # reads as one author without six interchangeable "praying interior" scenes.
    "power-through-prayer": Artwork(
        "met", 437683, "Alfred Sisley", "Sahurs Meadows in Morning Sun", "1894",
        "Morning light flooding a meadow — Bounds' thesis is that a man's power "
        "is not worked up but received at first light, in the closet before dawn.",
    ),
    "purpose-in-prayer": Artwork(
        "met", 437586, "Salomon van Ruysdael", "A Country Road", "1648",
        "A road set toward somewhere out of frame — prayer with an aim, the book's "
        "argument that asking is meant to arrive.",
    ),
    "necessity-of-prayer": Artwork(
        "met", 439344, "Johan Christian Dahl", "Two Men before a Waterfall at Sunset", "1823",
        "Water that must fall — a source that does not choose whether to give. "
        "Prayer as the thing without which nothing else runs.",
        focus=0.32,
    ),
    "essentials-of-prayer": Artwork(
        "met", 435979, "Camille Corot", "A Pond in Picardy", "ca. 1867",
        "Corot pared a landscape to a still pond and a few trees — the essential "
        "and nothing spare, which is the book on the one thing prayer cannot omit.",
    ),
    "reality-of-prayer": Artwork(
        "met", 438624, "Joseph Bidauld", "Lake Fucino and the Abruzzi Mountains", "ca. 1789",
        "Solid mountains held in still water — prayer as substance and not "
        "sentiment, as real as the rock it is reflected in.",
    ),
    "prayer-and-praying-men": Artwork(
        "met", 436831, "Philips Koninck", "An Extensive Wooded Landscape", "1670s",
        "A vast country under an enormous sky — the wide world the praying men of "
        "the book carried, seen at the scale their intercession reached for.",
    ),
    # ── Batch 5 · Watchman Nee (biography) ─────────────────────────────────
    # The one place the shelf leaves Europe, and on purpose: the book is the life
    # of a CHINESE servant of Christ who spent twenty years in prison, so it wears
    # a Chinese landscape the way Murray's intercession book wears a Dutch Reformed
    # church — the subject's own world. Kuncan was a monk who painted through the
    # Ming collapse; his dusk mountains carry endurance and vision at once.
    "watchman-nee-a-life": Artwork(
        "met", 39557, "Kuncan", "Wooded Mountains at Dusk", "1666",
        "Towering peaks going into the dark — a life of suffering and spiritual "
        "vision, in the idiom of the country Nee never left.",
        focus=0.3,
    ),
    # ── Batch 6 · C. H. Spurgeon's plate books ─────────────────────────────
    # Spurgeon's covers are set in the `revival` display face his century printed
    # in; the grounds are that century's landscape painting, one to each book's
    # own subject.
    "around-the-wicket-gate": Artwork(
        "met", 436557, "Jan van Goyen", "The Pelkus Gate near Utrecht", "1646",
        "A low gate on the water, the way through standing open — the book is a "
        "friendly talk with seekers at exactly this threshold.",
    ),
    "cheque-book": Artwork(
        "met", 439844, "Joseph Anton Koch", "Heroic Landscape with Rainbow", "1824",
        "The bow set in the cloud — the promise a reader draws on daily. Spurgeon's "
        "title makes God's word a cheque book of the bank of faith; here is the bond.",
    ),
    "gleanings-among-the-sheaves": Artwork(
        "met", 437097, "Jean-François Millet", "Haystacks: Autumn", "ca. 1874",
        "The field after the reaping, gathered into stacks — short readings gleaned "
        "from the harvest, by the painter of the gleaners.",
    ),
    "spurgeon-on-prayer": Artwork(
        "met", 437975, "Andreas Achenbach", "Sunset after a Storm on the Coast of Sicily", "1853",
        "A sea still heaving as the storm clears — mighty power spent and answered, "
        "which is what the twelve sermons are about.",
    ),
    # ── Batch 7 · R. A. Torrey's plate books ───────────────────────────────
    # Moody's man, three books on three works of the faith — winning others,
    # walking oneself, and the ground both stand on — each to its own subject in
    # the `revival` display face of his century.
    "how-to-bring-men-to-christ": Artwork(
        "met", 436012, "Gustave Courbet", "The Fishing Boat", "1865",
        "A boat drawn up on the shore — fishers of men, which is the trade the "
        "handbook of personal work is teaching.",
    ),
    "how-to-succeed-in-the-christian-life": Artwork(
        "met", 437436, "Auguste Renoir", "A Road in Louveciennes", "ca. 1870",
        "A road going on ahead in ordinary light — the Christian life is walked, "
        "not seized, and the book is about keeping to the way.",
    ),
    "the-fundamental-doctrines-of-the-christian-faith": Artwork(
        "met", 438106, "Canaletto", "Warwick Castle", "1748",
        "A stronghold on its rock, drawn stone by stone — the fundamentals are "
        "the fortress a faith is kept in, and this is one built to last.",
    ),
}


# ── Curated artwork used as a GROUND, not as the cover ────────────────────────
#
# Fetched exactly like ``CURATED`` above, pointed exactly like
# ``designed_covers.DERIVED_GROUND``. That sentence is the whole tier.
#
# WHY IT HAS TO EXIST. A work with a hand-made English cover and translations
# needs a wordless ground for those translations to wear, and ``DERIVED_GROUND``
# makes one by cropping the English cover's own photography. That works when
# there IS photography to cut — fourteen times it did. It cannot work when the
# designed cover has no picture in it that survives losing its words:
#
#   * ``the-inner-chamber`` is a stone doorway around a black void. Every crop
#     is either the void — an empty dark rectangle — or the lintel where the
#     byline sits.
#   * ``prayer-the-pulse-of-life`` is brown bokeh behind an ECG line. The line
#     IS the design and it sits where the title goes; what is left is a blur,
#     and a crop of a blur is a blur.
#
# The three ways out are: crop anyway and ship a wash (which is what those two
# did, out of ``DERIVED_GROUND``, until this table existed); move the work to
# ``CURATED``, which points EVERY edition at the painting and so retires the
# hand-made English cover; or this — give the translations a real painting and
# leave English alone. Only the third keeps both halves, which is why it is
# worth a third table rather than a flag on one of the other two.
#
# WHY NOT A FLAG. ``Ground`` is a crop recipe: four numbers and the digest of
# the cover they were cut from, policed by a gate that re-reads that digest. An
# ``Artwork`` is a museum object id and a licence receipt. Nothing about one is
# a special case of the other, and the registries stay separate for the reason
# the header above gives for ``CURATED`` and ``DERIVED_GROUND`` — one carries a
# collection's licence receipt and the other must never be mistaken for it.
#
# ART DIRECTION is the same as ``CURATED``: landscape, architecture, sky, water,
# path; no figurative devotional painting. A ground has the title drawn over it
# in every language, so it also has to survive being the BACKGROUND of type in
# a script it was not chosen for — which is the one extra thing asked of this
# tier over the other, and the reason `tune_art_scrim.py` measures these files
# alongside the rest.
CURATED_GROUND: dict[str, Artwork] = {
    "the-inner-chamber": Artwork(
        "met", 440726, "Adolph Menzel", "The Artist’s Sitting Room in Ritterstrasse", "1851",
        "Murray’s first two chapters are “The Morning Hour” and “The Door Shut "
        "— Alone With God”, and this is a back room with the door shut, morning "
        "at the window, a table drawn up to it and nobody there. Menzel painted "
        "his own lodgings. The book is about the ordinary private room rather "
        "than a sanctuary, and so is the picture — which is also why it is not "
        "the church interior on `the-reformed-pastor`.",
    ),
    "prayer-the-pulse-of-life": Artwork(
        "met", 11113, "Winslow Homer", "Cannon Rock", "1895",
        "Water that does not stop moving, painted from a stretch of Maine coast "
        "Homer went back to for years. A pulse is a beat that keeps on whether "
        "or not anyone is attending to it, which is this book’s argument about "
        "prayer — day by day, year by year. The opposite number of the still "
        "water on `waiting-on-god`: the same sea, and the whole difference is "
        "whether it is moving.",
    ),
}


def credit(slug: str) -> str | None:
    """One-line attribution for a curated cover, or None if it has no art.

    Lenient about an unknown ``source`` rather than raising, because this runs
    on the REQUEST path — the book detail serializer is its only caller — and a
    manifest typo should cost a credit line, not turn a public book page into a
    500. `test_every_entry_records_its_provenance_and_reason` is what actually
    stops such an entry, before it is ever deployed; this is the floor under it.

    BOTH curated tiers are credited. A painting used as a ground is the same
    museum object under the same licence, shown to the same reader — a credit
    line that skipped it would drop the attribution for exactly the editions
    that are showing the painting.

    That this returns a credit for the ENGLISH edition of a ``CURATED_GROUND``
    work too, which wears its hand-made cover rather than the painting, is
    already handled where it matters: the serializer asks only for editions
    whose ``cover_url`` is under ``/covers/art/``. Keying on the cover an
    edition actually wears rather than on the manifest is its rule, not a
    special case for this tier.
    """
    a = CURATED.get(slug) or CURATED_GROUND.get(slug)
    source = SOURCES.get(a.source) if a else None
    if not a or source is None:
        return None
    return f"{a.artist}, “{a.title}” ({a.year}). {source.institution}."

