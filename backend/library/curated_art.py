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

THE ART INSTITUTE OF CHICAGO is the third, and its catalogue API is the best of
the lot. Its IIIF image server was long thought unreachable — it 403s every
programmatic client, a browser's own User-Agent included — but that was one
missing header, not a policy: send ``Referer: https://www.artic.edu/`` and the
same request returns 200. The two-hop shape is the catch to know — an object's
id and its ``image_id`` are different values, the former on api.artic.edu and
the latter the key to the pixels — and ``build_curated_covers._aic_image_url``
walks it. Opened here for the landscape-heavy backlog the Met's keyword search
would not surface: its relevance ranking answers a landscape query with famous
figure paintings, and the Institute's search actually finds the picture.

ART DIRECTION — landscape, architecture, sky, water, path.
Deliberately no figurative devotional painting. The Met's religious holdings
are overwhelmingly Catholic and medieval, and a saint or a Madonna sits wrong
on a Protestant evangelical classic — the first pass surfaced Barocci's
*Saint Francis* for a Moody revival book, which is the mismatch in miniature.
Landscape and architecture carry the subject without claiming a tradition.

A BIOGRAPHY GETS A LANDSCAPE, NEVER A PORTRAIT. Susanna Wesley was long left on
a generated cover because every *portrait* candidate was a different real woman,
and a portrait on a cover reads as a portrait OF the subject — shipping one would
imply an image is Susanna Wesley when it isn't. The art-direction rule already
solves this: a wordless landscape claims no likeness, so she now wears a quiet
wooded Hobbema rather than a plate. The lesson stands for any biography — the
ground is a place or a mood, never a face.
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
    "aic": Source(
        "The Art Institute of Chicago, CC0",
        "https://www.artic.edu/artworks/{}",
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
    #: A changed `focus` redraws the painting on the next run: each committed
    #: painting's recipe (object and focus, `crop_recipe`) is recorded in
    #: `art_sources.py`, and a gate fails a painting whose recipe has moved.
    focus: float = 0.5


def crop_recipe(art: Artwork) -> str:
    """What a committed painting was cut from: the object and the crop.

    Recorded per work in ``library/art_sources.py`` by ``build_curated_covers``
    when it draws a painting, and compared on every later run. The painting is
    only KEPT if its recorded recipe is still this entry's — so swapping a work
    to a different artwork, or moving its ``focus``, redraws it rather than
    leaving the old picture under the new credit.
    """
    return f"{art.source}-{art.object_id}@{art.focus:.2f}"


# slug -> artwork. Slugs match Book.slug (shared across languages).
# THE CREDIT IS THE COLLECTION'S, VERBATIM. `artist`, `title` and `year` are
# recorded exactly as the museum records them — not tidied, not shortened, not
# re-punctuated — because `credit()` serves them to readers as provenance they
# can go and check. Thirteen of sixty-six entries were wrong before anything
# compared them to the source: a date off by nine years, titles quietly
# shortened, dates that had lost their qualifier, artists' names abridged. `build_curated_covers`
# now refuses an entry that disagrees with the live record, on every run.

CURATED: dict[str, Artwork] = {
    "waiting-on-god": Artwork(
        "met", 437914, "Simon de Vlieger", "Calm Sea", "after 1640",
        "Still water under a wide sky — waiting, held rather than idle.",
    ),
    "all-of-grace": Artwork(
        "met", 438642, "Simon Denis", "Cloud Study (Early Evening)", "ca. 1786–1806",
        "Light breaking through cloud; grace as something given, not achieved.",
    ),
    "prevailing-prayer": Artwork(
        "met", 11328, "John Frederick Kensett",
        "Twilight in the Cedars at Darien, Connecticut", "1872",
        "Light burning low through a dark wood — prayer that holds on through "
        "the night. Moody's own country and decade; it replaced a Rubens deer "
        "hunt that said the same thing darker and with a hound in it.",
    ),
    "the-fourfold-gospel": Artwork(
        "met", 283081, "Roger Fenton", "Salisbury Cathedral - The Nave, from the South Transept", "1858",
        "A nave receding into light: the one gospel seen down its full length.",
    ),
    "life-and-diary-of-david-brainerd": Artwork(
        "met", 16875, "Worthington Whittredge", "The Brook in the Woods", "ca. 1885–86",
        "American forest — the wilderness Brainerd actually walked into.",
    ),
    "pilgrims-progress": Artwork(
        "met", 459103, "Henri-Joseph Harpignies", "The Rocky Path in the Morvan (Chemin des roches dans le Morvan)", "1869",
        "A path climbing out of frame. The book in one image.",
    ),
    "the-reformed-pastor": Artwork(
        "met", 928532, "Pieter Jansz. Saenredam", "Interior of the Sint-Pieterskerk, 's-Hertogenbosch", "1632",
        "A whitewashed reformed church — Baxter's own subject, drawn from life.",
    ),
    "ten-commandments": Artwork(
        "met", 359021, "John Ruskin", "The Valley of Lauterbrunnen, Switzerland", "ca. 1866",
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
    "thoughts-for-the-quiet-hour": Artwork(
        "met", 11329, "John Frederick Kensett",
        "Twilight on the Sound, Darien, Connecticut", "1872",
        "One figure in a boat on still water at dusk: the quiet hour itself. "
        "The same year and shore as the Kensett on `prevailing-prayer`, so "
        "Moody's two devotional books read as a pair.",
        focus=0.47,
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
        "met", 39557, "Kuncan", "Wooded Mountains at Dusk", "dated 1666",
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
        "met", 438106, "Canaletto (Giovanni Antonio Canal)", "Warwick Castle", "1748",
        "A stronghold on its rock, drawn stone by stone — the fundamentals are "
        "the fortress a faith is kept in, and this is one built to last.",
    ),
    # ── Batch 8 · Athanasius, and a third collection ───────────────────────
    # The two 4th-century Alexandrian works wore flat plates, and both wanted a
    # landscape the Met's search could not surface — a desert and a dawn. So this
    # batch opens the Art Institute of Chicago as the third source (see the
    # module docstring: its pixels are reachable after all, given a Referer).
    # Two different painters, as the art direction asks — a wilderness and a
    # first light.
    "life-of-antony": Artwork(
        "aic", 16512, "Victor Pierre Huguet", "Ravine Near Biskra", "c. 1895",
        "Antony went out into the Egyptian desert and, Athanasius says, made the "
        "wilderness a city. Huguet painted North Africa from life — a ravine at "
        "the desert's edge, robed riders small in it: the solitude the hermit "
        "went to find.",
    ),
    "on-the-incarnation": Artwork(
        "aic", 57163, "Thomas Cole", "New England Scenery", "1839",
        "Athanasius' argument is that God took a body so a light could reach a "
        "world sunk in the dark. Cole fills the whole valley with first light "
        "and sets a white spire exactly where it falls.",
    ),
    # ── Batch 9 · John Wesley's plate books ────────────────────────────────
    # Two of Wesley's works wore plates. His own century and country, from the
    # Cleveland CC0 collection: the open English sky he preached under, and a
    # harvest for the book on love brought to its maturity. Two painters.
    "sermons-on-several-occasions": Artwork(
        "cma", 147017, "John Constable", "Branch Hill Pond, Hampstead", "1828",
        "Wesley preached in the open air to crowds no church would hold. "
        "Constable's English heath under a working sky is the weather and the "
        "country those sermons were first shouted into.",
    ),
    "plain-account-christian-perfection": Artwork(
        "cma", 118116, "George Inness", "Harvest Time", "1864",
        "Wesley's perfection is love grown to its full, not sinlessness seized — "
        "the ripe field, not the forced bloom. Inness fills the light with a "
        "harvest brought in and a spire standing in it.",
        focus=0.45,
    ),
    # ── Batch 10 · Hudson Taylor's plate books ─────────────────────────────
    # (Batch 9 is Wesley's, just above.) Taylor gave his life to inland China,
    # so A Retrospect wears Chinese ink, as Nee's cover does — a different
    # register from the oils on purpose, for the one book here whose whole
    # subject is China. Separation and Service is on Numbers 6–7 (the Nazarite
    # set apart, the offerings brought), so it gets a Western path into
    # consecrated light. Cleveland CC0.
    "a-retrospect": Artwork(
        "cma", 149613, "Chen Hongshou",
        "Paintings after Ancient Masters: Daoist and Crane in Autumn Landscape",
        "1598–1652",
        "Taylor looks back over a life spent inland in China. Chen Hongshou sets "
        "a lone figure by the water under autumn trees — the country Taylor gave "
        "himself to, rendered in its own tradition's hand.",
    ),
    "separation-and-service": Artwork(
        "cma", 172806, "Sanford Robinson Gifford", "Autumn, a Wood Path", "1876",
        "Numbers 6 and 7: the Nazarite set apart, then the offerings brought. "
        "Gifford lights a single path through a wood like a nave — a way walked "
        "apart, toward the service at its end.",
    ),
    # ── Batch 11 · A. B. Simpson's plate books ─────────────────────────────
    # (Batch 10 is Hudson Taylor's, just above.) Simpson founded the Christian
    # and Missionary Alliance; two of his works wore plates, both multilingual
    # (lg, sw). Luminous American landscape for the C&MA man — heaven ablaze
    # over the earth, and still water that restores.
    "days-of-heaven-upon-earth": Artwork(
        "cma", 141639, "Frederic Edwin Church", "Twilight in the Wilderness", "1860",
        "A daily devotional named from Deuteronomy 11:21 — 'as the days of "
        "heaven upon the earth.' Church sets the whole sky ablaze over a still "
        "lake: the heavens come down onto the land.",
        focus=0.4,
    ),
    "the-gospel-of-healing": Artwork(
        "cma", 140338, "Charles François Daubigny", "Sunset on the River Oise", "1866",
        "Simpson's book on divine healing. Daubigny lays a river down still and "
        "reflecting at dusk — the restoring water of Psalm 23, quiet enough to "
        "mend by.",
    ),
    # ── Batch 12 · The Church Fathers' plate books ─────────────────────────
    # (Batch 11 is Simpson's, landing in parallel.) Five ancient and medieval
    # writers who wore plates, given the classical and architectural register
    # their world asks for — ruins, a harbor, an archway, a dome — and, for
    # Bernard, a wood to love God in. Cleveland CC0.
    "enchiridion": Artwork(
        "cma", 135483, "Salvator Rosa", "Ruins in a Rocky Landscape", "c. 1640",
        "Augustine's handbook of faith, hope and love, written as Rome was "
        "falling. Rosa sets classical ruins in a wild country — the earthly city "
        "passing, which is half of Augustine's argument.",
    ),
    "on-loving-god": Artwork(
        "cma", 128371, "Jean Baptiste Camille Corot",
        "The Pond at the Entrance of the Woods", "c. 1860–75",
        "Bernard's treatise turns wholly inward — why God is to be loved, and "
        "how without measure. Corot's warm, enclosing wood is that interior: "
        "quiet, gold, a place to love from.",
    ),
    "first-epistle-of-clement": Artwork(
        "cma", 163456, "Fitz Henry Lane",
        "Harbor of Boston, with the City in the Distance", "c. 1846–1847",
        "Clement wrote from Rome to quiet a divided Corinth, a harbor city, back "
        "into peace and order. Lane's harbor lies still at first light — the calm "
        "the letter is asking for.",
    ),
    "epistles-of-ignatius": Artwork(
        "cma", 148862, "Hubert Robert", "The Grotto of Posillipo", "c. 1769",
        "Ignatius wrote these letters under guard on the road to Rome and his "
        "death. Robert lights a long grotto with figures walking toward the "
        "opening — the way out that is also the way through.",
    ),
    "on-the-priesthood": Artwork(
        "cma", 147938, "Giovanni Paolo Panini", "Interior of the Pantheon, Rome", "1747",
        "Chrysostom's defence of the weight and terror of the pastoral office. "
        "Panini stands inside the one great dome left open to the sky — the house "
        "of God with the light coming straight down into it.",
        focus=0.4,
    ),
    # ── Batch 13 · African-American spiritual autobiographies ──────────────
    # (Batch 12 is the Church Fathers', landing in parallel.) Four Black
    # preachers' and missionaries' own life-stories. For Jarena Lee and Richard
    # Allen — both AME pioneers — the ground is by William Merritt Chase and
    # Robert S. Duncanson; Duncanson was the pre-eminent Black American landscape
    # painter of the century, which is the point. Cleveland CC0.
    "amanda-smith-autobiography": Artwork(
        "cma", 144967, "Martin Johnson Heade", "Point Judith, Rhode Island", "1867–68",
        "A washerwoman who became a world evangelist — India, Africa, England. "
        "Heade lays a luminous sea under a wide sky: the horizon her calling kept "
        "crossing.",
    ),
    "religious-experience-and-journal": Artwork(
        "cma", 117715, "William Merritt Chase", "The Old Road to the Sea", "c. 1893",
        "Jarena Lee, the first woman authorised to preach in the AME church, rode "
        "and walked thousands of miles doing it. Chase opens a bright road across "
        "a meadow toward the sea — the itinerant's own view.",
    ),
    "a-brand-plucked-from-the-fire": Artwork(
        "cma", 134072, "George Inness", "Sunny Autumn Day", "1892",
        "Julia Foote took her title from Zechariah 3:2 — a brand snatched out of "
        "the burning. Inness fills the trees with autumn fire, alive and standing: "
        "the rescue rather than the ruin.",
        focus=0.4,
    ),
    "life-experience-gospel-labours": Artwork(
        "cma", 171296, "Robert S. Duncanson", "Vale of Kashmir", "1867",
        "Richard Allen founded the AME church and became its first bishop. His "
        "life-story wears a luminous valley by Duncanson, the foremost Black "
        "American landscape painter of Allen's own century — the honour is the "
        "hand as much as the scene.",
    ),
    # ── Batch 14 · Puritan & English devotional plate books ────────────────
    # The last of the single-plate sweep — English and European divines, each to
    # its own subject. Cleveland CC0. (Sibbes, Carmichael and Crowther are held
    # for a later pass: they want tender / tropical grounds the Met and Cleveland
    # don't carry, and AIC was throttling.)
    "mortification-of-sin": Artwork(
        "cma", 166506, "Jan Griffier", "Winter Landscape", "c. 1680–1718",
        "Owen on killing sin in the believer. Griffier's Dutch winter is the work "
        "in a picture — the year's growth cut back to bare wood and ice, Owen's "
        "own century's weather.",
    ),
    "selected-sermons-edwards": Artwork(
        "cma", 125058, "Jasper F. Cropsey",
        "The Clove - A Storm Scene in the Catskill Mountains", "1851",
        "Edwards preached the terror and the beauty of God in one breath. Cropsey "
        "opens a storm in his own New England hills — the sublime the sermons "
        "reach for, lightning and light together.",
    ),
    "way-into-holiest": Artwork(
        "cma", 108809, "Emil Carlsen", "Wood Interior", "c. 1910",
        "Meyer's book walks Hebrews into the Holy of Holies. Carlsen stands the "
        "trees up like the pillars of a nave and lays a path between them toward "
        "the light — the way in.",
    ),
    "the-life-of-trust": Artwork(
        "cma", 150047, "Camille Flers", "Cottage by the River with Washerwomen", "1835",
        "Müller fed a thousand orphans on prayer and never asked a man for money. "
        "Flers paints a plain riverside house and the day's work going on — daily "
        "bread, quietly provided.",
    ),
    "a-short-and-easy-method-of-prayer": Artwork(
        "cma", 148968, "Célestin François Nanteuil", "In the Forest", "1841",
        "Guyon's method is to sink out of words into the presence of God. "
        "Nanteuil's still forest interior is that inward turn — a quiet place, off "
        "the road, to pray from.",
    ),
    "possibilities-of-prayer": Artwork(
        "cma", 150038, "Antoine-Claude Ponthus-Cinier", "Châteauvieux-sur-Suran", "1848",
        "Bounds' last plate-covered book on prayer. A stronghold on its hill above "
        "a valley the light is crossing — what prayer lays hold of, kept high and "
        "sure.",
    ),
    "a-serious-call": Artwork(
        "cma", 141166, "Jan Wijnants", "Herengracht, Amsterdam", "c. 1661",
        "Law summons the reader to a whole and ordered devotion. Wijnants draws a "
        "quiet town at its most composed — a still canal, a bridge, the ordinary "
        "way walked with care — in Law's own century.",
    ),
    # ── Batch 15 · Richard Sibbes (the last reachable single) ──────────────
    # The Bruised Reed came out of the deferred set once a tender Western marsh
    # surfaced on Cleveland. Its shelf-mates Carmichael and Crowther still wait
    # for AIC (a tropical/Orientalist source the Met and Cleveland can't give),
    # and the two East-African-Revival Originals are held for an art-direction
    # call, not museum art.
    "the-bruised-reed": Artwork(
        "cma", 140341, "Jules Dupré", "Marshland", "1860s-1870s",
        "Isaiah's bruised reed and smoking flax, for people who feel barely "
        "alight. Dupré lays a low marsh under a vast, tender sky — the gentlest "
        "of the Puritans given the gentlest weather.",
    ),
    # ── Batch 16 · two shelf-mates that were waiting for a source ───────────
    # Both were held in the deferred set (see Batch 15's note). Carmichael was
    # waiting for a tropical source the Met and Cleveland couldn't give; the Art
    # Institute has Church's Andean daybreak, palms and all. Susanna Wesley was
    # held because every candidate was a PORTRAIT — a landscape retires that
    # objection (see the module docstring), so her biography gets a wooded home.
    "susanna-wesley-clarke": Artwork(
        "aic", 869, "Meindert Hobbema", "The Watermill with the Great Red Roof", "c. 1665",
        "A working home among dark trees, painted in her own century — the "
        "Epworth household, not a face the cover would pretend was hers.",
    ),
    "things-as-they-are": Artwork(
        "aic", 76571, "Frederic Edwin Church", "View of Cotopaxi", "1857",
        "A vast tropical valley at daybreak, palms against the light — the far, "
        "hot mission field Carmichael gave her life to, seen at first morning.",
        focus=0.6,
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


# ── Original grounds ────────────────────────────────────────────────────────
# The FOURTH shared-ground tier, and the only one whose picture is ours.
#
# The three tables above all resolve to a picture SOMEONE ELSE made and a
# recipe that can draw the file again: `CURATED` and `CURATED_GROUND` re-fetch a
# museum object and re-verify its licence, `DERIVED_GROUND` re-crops a designed
# cover and digests what it cut. An Ochorus Original — the `Brave for God`
# series, and the imprint's own titles after it — has no museum object to fetch
# and no designed cover to crop: its ground is an illustration drawn FOR the
# book (`scripts` render a wordless 600x800 scene). So there is no recipe to
# re-run, and nothing above can redraw the file.
#
# That is exactly the shape of a DESIGNED cover — a hand-made raster no tool may
# rewrite — except wordless, so `BookCover` still sets each language's title
# over it. `designed_covers.DESIGNED` cannot hold it (that registry is scoped to
# WORDED rasters a row wears as its cover, and `covers/art/` is deliberately
# outside it, trusting the other tiers to be re-drawable). So an Original ground
# is frozen HERE instead, by the same means: the committed file's SHA-256, held
# up by a gate that re-reads it. Replacing one on purpose is a two-line diff —
# new file, new digest — as it is for a designed cover.
#
# WHY A TABLE, NOT `CURATED` WITH A "local" SOURCE. `CURATED`'s whole invariant
# is that every row is verifiable museum art under a licence `credit()` can
# quote; a row we drew has no such receipt, and putting it there would make the
# one table whose job is provenance lie about a picture with none. `credit()`
# returns None for these — an Original wears no external attribution — which is
# why it is not consulted above.
#
# LIKE `CURATED` and unlike the two designed-cover tiers, `keeps_english_designed`
# is FALSE here: an Original has no English designed cover to keep, so every
# language — English included — wears the illustration.


class Original(NamedTuple):
    """An illustration drawn for one work, frozen by the bytes we committed."""

    #: SHA-256 of the committed `covers/art/<slug>.jpg`. Nothing may redraw it,
    #: so `test_original_grounds_are_frozen` re-reads the file and compares.
    sha256: str
    #: Why this scene, for the reader of this file — the receipt an Original has
    #: in place of a museum credit.
    why: str


# slug -> the ground we drew. Slugs match Book.slug (shared across languages).
ORIGINAL_GROUND: dict[str, Original] = {
    "brave-for-god": Original(
        "919c1e481e5e5aef9f9d5460bb1cb8491c37443a9a6dc728173b45d76395b713",
        "A child sets out at first light down a trail toward the horizon — the "
        "series' shared frame. Book 1 of the storybook set: deep dawn over "
        "rolling country. Every book holds the frame and changes the sky.",
    ),
    "brave-for-god-2": Original(
        "4e54f05e22beff434205d4c308aa33b75313792a3bd9ea64d22be48ab48ed352",
        "The same child, the same trail — now a moonlit coast, a small boat on "
        "the water beyond. Book 2 carries the voyage into “the wide world”.",
    ),
    "brave-for-god-3": Original(
        "0eb8b877adce7e100667c5279644b2d7f3079b787dddb7b1bade43d24d0c6c54",
        "Dusk over a mountain range, a snow-lit peak at centre. Book 3 — the "
        "journey climbs.",
    ),
    "brave-for-god-4": Original(
        "83d91d80e6349d938d30432ab7f1a5ae2fee7f233736f881d77df1494ea151eb",
        "Forest twilight, a line of firs along the horizon. Book 4 closes the "
        "set where the wide world grows deepest.",
    ),
    "growing-in-wisdom": Original(
        "fe3a7ee388b67085b7aaceab5be296a9a50e20502cb234e5c8f6fc590f34c3b6",
        "The Teens 'Editorial' system: a lone figure crests a dark ridge toward "
        "a single dawn breaking over distant mountains, under a starfield — the "
        "pursuit of wisdom. Deep night-blue with one warm light; the drama is in "
        "the sky so the figure stays clear of the title.",
    ),
}


# slug -> a ground we drew as SVG. The same promise as ORIGINAL_GROUND — an
# illustration made for the work, with no museum to re-fetch and no designed
# cover to re-crop — for the files that are vector rather than raster. Kept
# apart because every raster path (`art_url`, the webp variants, the scrim
# measure) assumes `covers/art/<slug>.jpg`; these four are served as they are.
#
# The Key Teachings share one motif: a single gilt tree on a dark ground in the
# book's own colour, a different tree for each writer. That motif IS the series
# look, which is why their type is also held to one series layout
# (`coverLayouts.BOOK_LAYOUT`) rather than each author's own.
ORIGINAL_SVG_GROUND: dict[str, Original] = {
    "key-teachings-of-a-b-simpson": Original(
        "620bcb654910fd3474e0541459f873737ad331b16f202e1050713a15475589d9",
        "A palm on teal: the missionary reach of the Christian and Missionary "
        "Alliance he founded.",
    ),
    "key-teachings-of-jonathan-edwards": Original(
        "f266baacb08968960586aba2e405ef3bf268c21e26f6c48a56a190a1170c81af",
        "A broad, full-crowned tree on forest green: New England, and the "
        "beauty of holiness he wrote of.",
    ),
    "key-teachings-of-richard-baxter": Original(
        "1a139874ce9b7005424df79a720bea10a4b0f6f9e4c46cb89763689f823c7a7a",
        "A tiered tree on oxblood, rising in layers: the ordered, patient "
        "pastoral life of The Reformed Pastor.",
    ),
    "key-teachings-of-watchman-nee": Original(
        "c95c85ac19f4fe92ba4cc1ca9c7f3f64c34c5bbf22c7c66644283cadfea55cfa",
        "A tree whose roots reach down into water, on night blue: abiding in "
        "Christ as the life of the normal Christian life.",
    ),
}


# slug -> the scrim each SVG Original needs, MEASURED — carried into
# `art_scrim.ART_SCRIM` by `scripts/tune_art_scrim.py` on every run, because
# that script reads rasters and cannot open these. Measured the tuner's way
# (its compositing model, its AA bars plus MARGIN, its 0.30 floor) but at the
# words' real positions: these covers set their type from the top
# (`coverLayouts.TYPE_TOP`), so the tuner's centred INK_REGIONS would measure
# rows no word crosses. Each ground was rasterised in Chromium at 600x800, the
# text bands found on its og twin, and the strength walked up from 0.30. All
# four clear at the floor. The digest in ORIGINAL_SVG_GROUND pins the input: a
# replaced tree fails that gate first, which is the cue to re-measure this.
ORIGINAL_SVG_SCRIM: dict[str, float] = {
    "key-teachings-of-a-b-simpson": 0.30,
    "key-teachings-of-jonathan-edwards": 0.30,
    "key-teachings-of-richard-baxter": 0.30,
    "key-teachings-of-watchman-nee": 0.30,
}

