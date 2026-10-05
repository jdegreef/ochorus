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
    # A painting none of the three museums hold, catalogued on Wikidata (the id
    # is the number after the Q) and photographed on Wikimedia Commons.
    "wikidata": Source(
        "Wikimedia Commons, public domain",
        "https://www.wikidata.org/wiki/Q{}",
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
        "aic", 39554, "Gustave Courbet", "An Alpine Scene", "1874",
        "Snow peaks set apart above the tree line, over a plain working chalet — "
        "the calling to be holy lived out from an ordinary house. It replaced a "
        "second 1889 Van Gogh cypress, which read as `absolute-surrender`'s twin "
        "on the shelf.",
        focus=0.55,
    ),
    "school-of-prayer": Artwork(
        "met", 436329, "François-Louis Français", "Gathering Olives at Tivoli", "1868",
        "An olive grove at first light: the garden the disciples learned to pray "
        "in, without a figure of Christ to claim a likeness. Upright on the "
        "canvas, so the tree and the pickers both survive the 3:4 crop.",
        focus=0.55,
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
        "aic", 109938, "Joseph Mallord William Turner",
        "Valley of Aosta: Snowstorm, Avalanche, and Thunderstorm", "1836–37",
        "Power on the scale the title claims, by an English painter of Spurgeon's "
        "own century. It replaced the Achenbach, which `till-he-come` had worn "
        "first — the one painting the library ever gave two books.",
        focus=0.45,
    ),
    # Spurgeon's paired devotionals, one painter's morning and evening, so the
    # two read as a pair on the shelf. Both late Inness, both whole in the band.
    "morning-by-morning": Artwork(
        "aic", 110561, "George Inness", "A Silver Morning", "1886",
        "Sun coming through mist over a stream: the first light a morning reading "
        "is taken in.",
    ),
    "evening-by-evening": Artwork(
        "aic", 64740, "George Inness", "Landscape, Sunset", "1887–89",
        "The last red of the day held in water under dark trees — the companion "
        "to `morning-by-morning`'s silver morning, by the same hand.",
        focus=0.45,
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
    # ── Batch 17 · the new-shelf classics ──────────────────────────────────
    # Three famous works that joined the library on plates and sat on "New to
    # the Library" looking unfinished. All single-plate authors, English-only
    # when levelled (so no per-language plates to repoint). Art Institute CC0,
    # three painters, each a place rather than a face — two are biographies.
    "foxes-book-of-martyrs": Artwork(
        "aic", 60755, "Jacob van Ruisdael",
        "Landscape with the Ruins of the Castle of Egmond", "1650–55",
        "A record of the church burned and scattered and never put out. "
        "Ruisdael's shattered tower still stands under a storm sky — what "
        "persecution breaks and cannot bring down.",
    ),
    "finney-memoirs": Artwork(
        "aic", 71971, "Sanford Robinson Gifford",
        "Mist Rising at Sunset in the Catskills", "c. 1861",
        "Finney's revivals swept upstate New York in his own decades. Gifford "
        "paints that country with the sky set alight over a darkened lake — "
        "fire falling on a sleeping land.",
    ),
    "george-muller-of-bristol": Artwork(
        "aic", 152437, "Harald Oscar Sohlberg", "Fisherman's Cottage", "1906",
        "Müller kept thousands of orphans without once asking anyone but God. "
        "Sohlberg sets one lit house among dark pines at nightfall — a home "
        "kept, by no visible means, with its light on.",
    ),
    # ── Batch 18 · the healing evangelists ─────────────────────────────────
    # Bosworth and Wigglesworth, one plate book each, both English-only when
    # levelled. Two new painters, one source each: water out of the rock for
    # the book on healing, and a mountain for the faith that moves one.
    "christ-the-healer": Artwork(
        "aic", 146701, "Albert Bierstadt", "Mountain Brook", "1863",
        "Bosworth preached that healing is in the atonement, as sure as the "
        "water from the struck rock. Bierstadt's spring breaks out of stone "
        "into a dark wood — living water, flowing where no one dug for it.",
    ),
    "ever-increasing-faith": Artwork(
        "cma", 154962, "Richard Wilson", "Cader Idris, with the Mawddach River",
        "c. 1774",
        "Wigglesworth's whole message was Mark 11:23 — faith that says to the "
        "mountain, be removed. Wilson sets one great British mountain over a "
        "wide valley, the thing faith is told to speak to.",
    ),
    "evangelization-of-the-world": Artwork(
        "cma", 153388, "Eugène Boudin", "View of Bordeaux, from the Quai des Chartrons",
        "1874",
        "Mott's watchword sent a generation of student volunteers to sea for "
        "every nation. Boudin paints a harbour of tall ships rigged and ready "
        "at the quay — the moment before sailing.",
        focus=0.72,  # the fully rigged ship at right, not the empty quay
    ),
    # ── Batch 19 · the last painted plates ─────────────────────────────────
    # Every remaining classic and children's book that wore a plate. Two are
    # already in lg and sw, so their per-language plates are retired here too.
    # Six painters, four collections' worth of landscape — places, not faces.
    "hurlbuts-life-of-christ": Artwork(
        "aic", 16439, "Claude Joseph Vernet", "Morning", "1760",
        "A life of Christ for young and old. Vernet's fishermen haul their nets "
        "at first light on a still shore — where the story began with nets left "
        "behind, and where the risen Christ met them again at dawn.",
    ),
    "treatises-of-cyprian": Artwork(
        "cma", 95268, "William Linton", "Carthage", "c. 1830",
        "Cyprian was bishop of Carthage and died for it in 258. Linton paints "
        "the city itself, its harbour lit gold at the day's end.",
    ),
    "journal-of-an-expedition-up-the-niger": Artwork(
        "aic", 57191, "Eugène Fromentin", "On the Nile", "1871",
        "Crowther's journal of a missionary voyage up a great African river. "
        "Fromentin's moored boats and wide water give that voyage its river — "
        "the continent's own, not a Dutch one standing in for it.",
    ),
    "divine-songs-for-children": Artwork(
        "aic", 181702, "Aelbert Cuyp",
        "A View of Vianen with a Herdsman and Cattle by a River", "c. 1643–c. 1645",
        "Watts wrote the first hymnbook for children. Cuyp's river pasture in "
        "warm evening light is the gentle, ordered world those songs sing of.",
    ),
    "pilgrims-progress-words-of-one-syllable": Artwork(
        "aic", 16340, "Joos de Momper, II", "Mountain Road with Travelers", "c. 1615",
        "Bunyan's journey retold for children. Momper's travellers climb a road "
        "under great trees toward the far hills — the way, and the long view "
        "of where it goes.",
    ),
    "our-daily-walk": Artwork(
        "aic", 890, "Jules Dupré", "On the Road", "1856",
        "Meyer's readings are for walking with God one ordinary day at a time. "
        "Dupré's cart keeps to a country road under a great sheltering tree — "
        "an everyday journey, made in company.",
    ),
    # ── Batch 20 · Pascal ──────────────────────────────────────────────────
    "pensees": Artwork(
        "aic", 56905, "James McNeill Whistler",
        "Nocturne: Blue and Gold—Southampton Water", "1872",
        "'The eternal silence of these infinite spaces frightens me.' Whistler's "
        "night water fades into a night sky with no line between them, one low "
        "light hung in it — the vastness Pascal set his thinking reed against.",
        focus=0.2,  # bring the low moon in from the left edge
    ),
    "provincial-letters": Artwork(
        "aic", 81568, "Jean-François Rafaëlli", "Notre Dame de Paris", "c. 1890",
        "The letters were printed in secret and passed from hand to hand through "
        "Paris. Rafaëlli's autumn quai under Notre-Dame, with two nuns walking "
        "by the Seine, recalls the nuns of Port-Royal whom Pascal defended.",
        focus=0.7,
    ),
    "letters-and-minor-works": Artwork(
        "met", 437311, "Camille Pissarro", "Rue de l'Epicerie, Rouen (Effect of Sunlight)", "1898",
        "Rouen, where the Pascal family was converted in 1646 and where the "
        "earliest of these letters was written. Pissarro's old street climbs to "
        "the cathedral towers above a crowded market.",
    ),
    "life-of-pascal": Artwork(
        "aic", 81516, "Jean François Millet", "In the Auvergne", "c. 1866–69",
        "Pascal was born at Clermont in Auvergne, and it was on the Puy de Dôme "
        "above the town that his brother-in-law carried out his experiment on "
        "the weight of the air. Millet's bare volcanic hillside is that country.",
        focus=0.6,
    ),
    # ── Batch 21 · Portraits of Courage, volume 2 ──────────────────────────
    # Volume 1 wears the country Nee never left. No painting of the Punjab
    # plains in the three collections is a landscape rather than a court or
    # devotional scene, so Hyde's life wears its own image instead: the
    # people called him "the man who never sleeps".
    "john-hyde-a-life": Artwork(
        "aic", 64754, "George Inness", "Moonrise", "1891",
        "A lone man crossing a dark field as the moon comes up: the night "
        "watches of the missionary the Punjab called \"the man who never "
        "sleeps\", painted the year before he sailed.",
    ),
    # ── Batch 22 · Portraits of Courage, volume 3 ──────────────────────────
    # The founder's pick of five mockups (2026-09-29). Haarlem from the dunes,
    # the Grote Kerk on the skyline: Corrie's city, whole. The Mauritshuis
    # painting, through Wikidata — none of the three museums above hold a view
    # of Haarlem that isn't already another book's.
    "corrie-ten-boom-a-life": Artwork(
        "wikidata", 17275831, "Jacob van Ruisdael", "View of bleaching fields and Haarlem", "1670",
        "Haarlem seen from the dunes, the Grote Kerk rising over the town: the "
        "city where the ten Booms kept their watch shop for a century and hid "
        "Jews from the Nazis in the Beje, a few streets from that church.",
        focus=0.3,
    ),
    # ── Batch 23 · Portraits of Courage, volume 4 ──────────────────────────
    # The founder's pick of five mockups (2026-09-29). A tropical river at
    # sunset for the woman who travelled the Cross River and the Enyong Creek
    # by canoe for forty years. It is Colombia's Magdalena, not the Cross —
    # the rationale says "evokes", never "depicts".
    "mary-slessor-a-life": Artwork(
        "wikidata", 20201742, "Frederic Edwin Church", "La Magdalena", "1854",
        "A tropical river at sunset, palms and forest down to the water: it "
        "evokes the Cross River country she travelled by canoe for forty years. "
        "Church painted the Magdalena in Colombia, but the river, the heat and "
        "the light are hers.",
        focus=0.62,
    ),
    # ── Batch 24 · Portraits of Courage, volume 5 ──────────────────────────
    # The founder's pick of five mockups (2026-09-29). The West Africa Squadron
    # running down a slaver — the rescue that set the boy Ajayi free in 1822.
    # A like capture two decades later, not his own: the rationale says so.
    "samuel-ajayi-crowther-a-life": Artwork(
        "wikidata", 50868900, "Nicholas Matthews Condy",
        "The Capture of the slaver Gabriel by HMS Acorn, 6 July 1841", "1841",
        "A Royal Navy brig running down a slave ship off West Africa, as HMS "
        "Myrmidon ran down the ship that carried the boy Ajayi in 1822: not "
        "his ship, but his deliverance.",
        focus=0.45,
    ),
    # ── Batch 25 · Portraits of Courage, volume 6 ──────────────────────────
    # The founder's pick of five mockups (2026-09-30). Ravi Varma's girl at a
    # doorway giving to a starving beggar: the Mukti of "I am a sweeper".
    "pandita-ramabai-a-life": Artwork(
        "wikidata", 112062313, "Raja Ravi Varma", "Charity", "",
        "A girl in a white sari at her doorway, putting food into a starving "
        "old man's bowl: Ravi Varma, the great Indian painter of her day, "
        "painted the plain mercy Ramabai made a life's work at Mukti.",
        focus=0.5,
    ),
    # ── A. W. Tozer ─────────────────────────────────────────────────────────
    # His first book on the shelf. The Pursuit of God is about the Presence
    # that is already here and the soul that turns to see it, so the ground is
    # light breaking into an ordinary valley, not a distant summit.
    "the-pursuit-of-god": Artwork(
        "aic", 68388, "George Inness", "Catskill Mountains", "1870",
        "Tozer's book is a call to the God who is already present and waiting "
        "to be seen. Inness lets the light break through the cloud onto a "
        "plain farm valley — glory falling on the ordinary ground of life.",
        focus=0.38,
    ),
    # ── A. B. Simpson, The Holy Spirit; or, Power from on High ──────────────
    # The two volumes share one register: weather over land and sea. Part II
    # follows the Spirit from the Gospels to Pentecost and the epistles, so its
    # ground is the wind.
    "power-from-on-high-new-testament": Artwork(
        "aic", 57215, "Elihu Vedder", "Storm in Umbria", "1875",
        "Pentecost came \"as of a rushing mighty wind.\" Vedder's storm sweeps "
        "down over the Umbrian hills, and one small figure walks on into it — "
        "the believer moved and carried by a power not his own.",
        focus=0.68,
    ),
    # Part I follows the Spirit through the Old Testament, whose first picture
    # is the Spirit moving on the face of the waters — so its ground is the sea.
    "power-from-on-high-old-testament": Artwork(
        "aic", 68792, "George Inness", "A Marine", "c. 1874–75",
        "\"The Spirit of God moved upon the face of the waters.\" Inness's dark "
        "sea breaks in light along the rocks under a heavy sky — the deep the "
        "Spirit brooded over before the first day.",
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
    # Brave for God 1–4 (young readers). A mid-century travel poster, one per
    # volume: flat sun-ray skies, a big pale sun, and a young traveller with a
    # scarf facing a new part of the wide world. Chosen 2026-09-29 from ten
    # lighter concepts, replacing the first set (a child on a lit trail at night).
    "brave-for-god": Original(
        "699635594792348fe4eb6f3aa0f3dd13c8cbf018768d2c71154e11847f5482e9",
        "A sea voyage: a traveller on a red headland by a lighthouse, a steamer "
        "on the turquoise sea under a sun-ray sky. Every bright element sits below "
        "y602, under the lowest subtitle any edition sets (lg/sw wrap to y595).",
    ),
    "brave-for-god-2": Original(
        "507568a8f1e09fbd2e023a2737ee3a3cb67f5bfd2d937f6404120749f0d3ff43",
        "A jungle river under an orange sky: palms, a winding river and a canoe.",
    ),
    "brave-for-god-3": Original(
        "1b0e419349813afa1a8a05cdc3258d850516bf6df8c786478a86f2647619955d",
        "A desert under a magenta sky: terracotta dunes, a camel caravan, an oasis.",
    ),
    "brave-for-god-4": Original(
        "a5c690a89c4784a4e108cf74d6cc6d857a2fffe7a855582d746777728d92c343",
        "Snowy mountains under cobalt: pines, a snowfield and a small red cabin.",
    ),
    "growing-in-wisdom": Original(
        "fe3a7ee388b67085b7aaceab5be296a9a50e20502cb234e5c8f6fc590f34c3b6",
        "The Teens 'Editorial' system: a lone figure crests a dark ridge toward "
        "a single dawn breaking over distant mountains, under a starfield — the "
        "pursuit of wisdom. Deep night-blue with one warm light; the drama is in "
        "the sky so the figure stays clear of the title.",
    ),
    # Rooted 1–6 (ages 9–12). Loose watercolour on textured paper with a deckled
    # edge: one tree that visibly grows book by book, each volume in its own
    # landscape and palette under a shared painted frame. The founder chose this
    # over nine other concepts (2026-09-28), replacing the first set, a cutaway of
    # tree, soil and underground stream (#4295).
    "rooted-1": Original(
        "0437dcb2576dddecfaedb8aeee1b063675a3e2e25a202065d526f50a3f18fa22",
        "Planted: a two-leaf seedling breaking from its seed in a dawn meadow.",
    ),
    "rooted-2": Original(
        "b198da8e4cc6023ec769ae2cb391594423e0eba3128124e1b70c94dac331e1a1",
        "Following Jesus: a young tree beside a path winding into the hills.",
    ),
    "rooted-3": Original(
        "89d001022985690f7ff356ace361c28edb7f950dda84ffde5679eb64381ea442",
        "Growing Fruit: the tree's first fruit at an orchard's edge.",
    ),
    "rooted-4": Original(
        "6c8c74a011051ddc5ee068ef629266b8728e68868fcdf6106845331ba8555fd3",
        "Strong in the Storm: the tree holding in wind and rain, the grass bent.",
    ),
    "rooted-5": Original(
        "17dd6c9e11b7cf291eb09ed8a559c8c16fe3b4c10cc8076ac964807eeb12b94d",
        "Branching Out: a wide crown over a river valley, birds in the air.",
    ),
    "rooted-6": Original(
        "0571cd2ba638736649c0165c308d3a13a6b80523aeb8a5110d762222df6599a2",
        "Bearing Fruit: a laden tree over a harvest field, windfalls at its foot.",
    ),
    # The two East African Revival Originals share one frame: the hills of
    # Buganda at night under a faint Milky Way, lit by fire. One fire becomes
    # many — the revival spreading hill to hill, and the fellowship meetings
    # gathered around the fire.
    "a-hidden-fire": Original(
        "2da88d638edf683963f7b67daa79e986094164d379ab1476f8ee2cdea8bcbdc8",
        "A single fire on a dark hillside, one figure seated beside it, sparks "
        "rising: the hidden fire before it spread.",
    ),
    "tukutendereza": Original(
        "7adbe65452786313e86f48c6fd676d8b3ef232882d9ffa9c56070bd97671f6f1",
        "Fires on hill after hill into the distance, a circle gathered at the "
        "nearest, the first dawn on the rim — the revival's fellowship spreading.",
    ),
    # Sons of the King 1–3 and Daughters of the King 1–3: sibling series in
    # dark ink (`covers.INK_DARK`). Loose watercolour plants frame a pale cream
    # page, kept to the side margins so the words sit on paper (the founder chose
    # this from ten concepts, 2026-09-30, replacing night-sky silhouettes that
    # read too dark). Daughters take warm plants, Sons cool ones, one per volume.
    "sons-of-the-king-1": Original(
        "41cd07c644ab65d224aca74f36037718e60909e05ddcc83d3a82ddddfcd6e64d",
        "Strong: slate-blue pine with cones framing a cream page.",
    ),
    "sons-of-the-king-2": Original(
        "b6839633ad5576b225264c00bb04fcc208c9328511a0e0577a1675b47611890c",
        "Faithful: deep-teal cedar sprays (Psalm 92:12) framing a cream page.",
    ),
    "sons-of-the-king-3": Original(
        "b5cb90e5b414d3460604e7c9396b94931726c8fedba0c8be9a2b7fb16b8c5ff3",
        "Growing Up: sage ferns with unfurling fiddleheads.",
    ),
    "daughters-of-the-king-1": Original(
        "dfbc04c44e0ee7fe3c1997f37735ad0ffb0303b40ca2c24146a415ae93f3dd80",
        "Beloved: pink watercolour lilies framing a cream page.",
    ),
    "daughters-of-the-king-2": Original(
        "70338ad2830db824e6b62e59176ce4ce99599945689c9b8ab521ed756bc3316b",
        "Brave: oak with acorns and fruiting olive sprigs framing a cream page.",
    ),
    "daughters-of-the-king-3": Original(
        "6d744ac8bc5a63b942d6f03bc1dcafa37a64c0dd146d3046631dad2cf8cc1592",
        "Growing Up: a morning-glory vine climbing the page, buds at its tip.",
    ),
    # The Key Teachings companions (Simpson, Edwards, Baxter, Nee, …). One frame for
    # the series: each man's desk, painted close and warm by the light of his own
    # era, on one shared table against a wall in the book's colour. Chosen
    # 2026-09-29 from sixteen mockups ("the study", warm and close), replacing
    # the gilt-tree SVGs that were the series' first covers.
    "key-teachings-of-a-b-simpson": Original(
        "de5850753d4104a5274562c9978df590299ef3d8f701ccdfe8713be632233638",
        "A brass oil lamp, an open hymnal on a book-rest, steel spectacles: the "
        "hymn-writer of the Christian and Missionary Alliance.",
    ),
    "key-teachings-of-jonathan-edwards": Original(
        "94c5325bac2b02e8b8f9ff6c4880f9c8db96d8d3caf4633dceddf687fd99187e",
        "A candle in a brass chamberstick, a quill and inkwell, sewn sermon "
        "booklets on a calf volume: the Northampton preacher's desk.",
    ),
    "key-teachings-of-richard-baxter": Original(
        "15a71d6d8cd90dcf95de4c1b641a614319c0694ced8816977bc29fc971e45d11",
        "A tallow candle, an hourglass, a heavy calf book and a goose quill: "
        "the Kidderminster pastor's seventeenth century.",
    ),
    "key-teachings-of-watchman-nee": Original(
        "c172ac7988c4ab041ea0008a6edc8669f37d3976f8df7bd27d9a73affd954ea9",
        "A green-shaded desk lamp, a blue-and-white teacup, a black Bible and a "
        "fountain pen on a notebook: a twentieth-century Chinese study.",
    ),
    # Five more (2026-09-29), painted by the same renderer and light.
    "key-teachings-of-charles-h-spurgeon": Original(
        "ca1653b4fcedca27f0695e5bab27f3a3654cd8a83216d532303dfe8ecff4e2a0",
        "A brass parlour lamp under an opal globe, a thick black Bible, folded "
        "sermon notes and pince-nez: the Victorian preacher's desk.",
    ),
    "key-teachings-of-andrew-murray": Original(
        "ec2cd771a3430ce5f6453a52b0a832c9bf0970d2f0be2222350bb3207414a7ef",
        "A tin hurricane lantern, a worn brown Bible and a chipped enamel "
        "coffee mug: the South African pastor on the road.",
    ),
    "key-teachings-of-hannah-whitall-smith": Original(
        "0a299d3bcebd317610ad3d7de26fa5bb829879978d24cfb0b8caa9898415c54f",
        "A milk-glass oil lamp, an embroidery hoop, a grey cloth book with a "
        "thimble, a plain white cup and saucer: a Quaker woman's table.",
    ),
    "key-teachings-of-catherine-booth": Original(
        "99d4c0dcab78da89ffbdddf65e38bdbbff00490afe570278f76610e84555f0b2",
        "A brass lamp with a glass font, a Bible under a crimson hymn book, "
        "handwritten pages and a dip pen: the Army mother's desk.",
    ),
    "key-teachings-of-augustine-of-hippo": Original(
        "c55f903d40fec3a8d27bec4ae7086201bf84c73ddc88a862dd7b3f08c169505d",
        "A terracotta lamp on a bronze stand, papyrus scrolls, a wax tablet "
        "and stylus, a clay cup: a bishop's table in Roman Africa.",
    ),
    "key-teachings-of-amanda-berry-smith": Original(
        "79598d3106675be9f655e1282909d8c7ef6432952eb1521d6ac1809ab5610fd2",
        "A plain tin oil lamp, a worn Bible on a japanned travel trunk and a "
        "cast-iron sad iron: the washerwoman evangelist who crossed three "
        "continents.",
    ),
    "key-teachings-of-hudson-taylor": Original(
        "c86a2f01873b90093fbaae9571a7ca7e3ae34545293f14b25c8637844618da23",
        "A red paper lantern, blue thread-bound volumes, a celadon rice bowl "
        "with chopsticks, an inkstone and brush: the China Inland Mission.",
    ),
    "key-teachings-of-athanasius-of-alexandria": Original(
        "6cf846ed7d86770123daf3fe16b5e190a093c44e1eb611ecc60088a9bfa568ac",
        "A bronze lamp on a low stand, a codex in boards with brass clasps, a "
        "reed pen in a black inkpot: the bishop of Alexandria.",
    ),
    "key-teachings-of-julia-foote": Original(
        "f662f89b034b48595a2d7854e650d1d8f64b187fc34f41f3518c1f65fa3d91d6",
        "A glass finger lamp, a small black Bible on a green hymnbook, a "
        "folded letter with a bonnet ribbon: the AME Zion evangelist.",
    ),
    "key-teachings-of-jeanne-guyon": Original(
        "99b75afc5624a0c487ec8709ae46678c663bdebdd56a5c872282ec8ecc99a746",
        "A silver candlestick, a red morocco prayer book, a folded letter "
        "under a red wax seal with a quill: seventeenth-century France.",
    ),
    "key-teachings-of-r-a-torrey": Original(
        "2142aec4cbdeb1d54341210e9bbcf98cd023e300f0444fc2857d26260198c03c",
        "A brass student lamp, a black Bible with ribbon markers and a "
        "fountain pen, a stack of ruled index cards: the Bible teacher's "
        "desk.",
    ),
    "key-teachings-of-dwight-l-moody": Original(
        "dcc2eb60a31c9b28b403c4af281ecfc9bfcc5143fd0c449737b1bb60f07faf91",
        "A pewter lamp with a glass font, a worn brown Bible and a small "
        "cloth Sankey hymnbook: the Northfield evangelist.",
    ),
    "key-teachings-of-john-bunyan": Original(
        "d913c4dc76a110d91100919982167f73d85154ad1f272f406196de7aa7df392e",
        "A candle in an iron socket, a leather Bible and a copper tinker's "
        "kettle: the tinker of Elstow.",
    ),
    "key-teachings-of-john-wesley": Original(
        "72b01daad903cfab069efc084e8372473e95d63e44796f7040ef35572e2ca274",
        "A brass candlestick, a pocket Bible on a leather saddlebag, a "
        "journal and quill: the itinerant's desk.",
    ),
    "key-teachings-of-charles-finney": Original(
        "858b22fc6ab5c9f3cde1a7f5dfcff4b2a65fc883554289d9d83f783f51c3b3cd",
        "A brass oil lamp, calf law books with a Bible on top, an inkpot and "
        "quill: the lawyer turned revivalist.",
    ),
    "key-teachings-of-john-owen": Original(
        "1b0c0ee5cf2123906b8176bbe53c013787f9ae934ba6827bc46bc37fcc6c0b4e",
        "A pewter candlestick, a great calf folio with clasps, sealing wax "
        "and a quill: the Puritan divine.",
    ),
    "key-teachings-of-e-m-bounds": Original(
        "65918f89135761820286e6387bae8585acdacca016c9fa6a945d7bb1d958533f",
        "A tin oil lamp in the cool before dawn, an open Bible and a gold "
        "pocket watch: the early hour of prayer.",
    ),
    "key-teachings-of-frederick-brotherton-meyer": Original(
        "c6ebc5669a4560afa3c3641e9643773d4ade7be07ff1d072708e6df36d51a6a6",
        "A brass lamp with a cranberry-glass font, a small devotional book "
        "with a letter, a gilt-rimmed cup: the Victorian pastor.",
    ),
    "key-teachings-of-george-whitefield": Original(
        "249909ebaea3a7c91a234acea5a33fca6739ae81a44cc178ea93cebbed350f87",
        "A brass candlestick, a leather travelling valise, a tied sermon "
        "manuscript and a quill: the field preacher.",
    ),
    "key-teachings-of-ignatius-of-antioch": Original(
        "508f76f1d92a0a2d2814b5d42e1a1604ae922800c6eb1d0540e2ebfdbe5bec18",
        "A bronze lamp hanging from a stand, papyrus letters under a seal, "
        "three iron chain links: the bishop on the road to Rome.",
    ),
    "key-teachings-of-john-calvin": Original(
        "b995d3b471c403ecce9c3f262bbafd6dee2f5f39f61e4786afd05a9ca950be8d",
        "A plain iron candlestick, a clasped Geneva book, a pewter inkstand "
        "and quill: the Reformer of Geneva.",
    ),
    "key-teachings-of-martin-luther": Original(
        "509efdc45554398a9fe30b50c69985aa40e2d9a4c5ac558d9d8f743885cc4529",
        "A tin chamberstick, a great Bible with brass bosses and a lute "
        "leaning on it: the Wittenberg Reformer.",
    ),
    "key-teachings-of-a-w-tozer": Original(
        "5ac9dffd163d449a07ddb4f80905649fac7a4adfd4392e05f475353e44213ed7",
        "A 1940s gooseneck lamp, an open old book of the mystics, a black "
        "Bible and a notebook: the Chicago pastor's study.",
    ),
    "key-teachings-of-martyn-lloyd-jones": Original(
        "2a1025900a2ddac96dec2c3281df0de2191edb09010ea78c65849e3e633cd325",
        "A cream anglepoise lamp, a black Bible, a coiled stethoscope and "
        "sermon notes: the doctor turned preacher.",
    ),
    "key-teachings-of-corrie-ten-boom": Original(
        "596ba9b9691089f22e56e04b56a9c9efe646405a1936da4fe0d03e8663bb0b18",
        "A watchmaker's lamp, a small Bible with a loupe, an open watch and "
        "an embroidered cloth: the Haarlem watch shop.",
    ),
    "key-teachings-of-derek-prince": Original(
        "c8cbfb5bab7b1588992525ee25a22bd4e2ceba6d23ebdaac66c7ba2b112515d6",
        "A drum-shade lamp, a Bible with a Greek New Testament, an olive-wood "
        "bowl of olives: the teacher in Jerusalem.",
    ),
    "key-teachings-of-dietrich-bonhoeffer": Original(
        "11423ee7f679323acf2d7c673e1ff5f9413e0df885834b6cf0774a22b1e34ecb",
        "A candle stub on an enamel dish, a thin grey book, handwritten "
        "letters and a pencil: letters from a cell.",
    ),
    "key-teachings-of-gareth-evans": Original(
        "bb28022b3975fb39a0704adce0b101a04bf596ee3d71266f5ea90eea578da47f",
        "A slim desk lamp, an open Bible, a blue ceramic mug and a notebook "
        "with a pen: a present-day study.",
    ),
    # Drawn 2026-10-04 by a stand-in SDF ray-marcher in the same frame (wall in
    # the book's colour, desk in lamplight), since the series' own renderer is
    # not in the repo. Nothing Narnian and no likeness: the don's desk only.
    "key-teachings-of-c-s-lewis": Original(
        "aa4d46315b0c6a682340cb7582980c59e02fc2c996cac38ce3b8849dff22017e",
        "A parchment-shaded brass lamp, three old calf and cloth volumes, an "
        "ink bottle with a dip pen and a cup of tea: the Oxford don who wrote "
        "everything by hand.",
    ),
    # Drawn 2026-10-05 by the same stand-in SDF ray-marcher as the Lewis volume
    # (the series' own renderer is not in the repo): the wall in the book's
    # Highland green, the desk in lamplight. No likeness, nothing of Lewis's.
    "key-teachings-of-george-macdonald": Original(
        "5703af8c08002646d680b6f07d0c6edb4da988d66f920fcb7b259238573bc20b",
        "A brass paraffin lamp with a glass chimney, three old volumes with a "
        "stoneware jug of heather, and sermon pages with a dip pen: the "
        "Aberdeenshire minister who preached his sermons on paper.",
    ),
    # Portraits of Courage, volume 7. The series wears museum paintings through
    # CURATED, but the session that wrote this life could reach no collection
    # host (Commons, Wikidata and the museum APIs were all blocked), so the
    # ground is our own: an inline SVG (gradients, fractal-noise cloud and
    # foliage, a mirrored sky for the river) rendered in headless Chromium at
    # 2x and downscaled. A placeholder in the series' register, not a likeness
    # and nothing Narnian; a public-domain Oxford view (Turner's or a Victorian
    # watercolour of Magdalen from the meadows) would be the natural level-up,
    # which is a two-line diff here plus a CURATED entry.
    "c-s-lewis-a-life": Original(
        "4d80afaaceebb5ae4bab8867a17a5ce700f592b3b430d527ce13ffc7716e1ae9",
        "Dusk over the Magdalen water meadow: a storm-dark sky, the college "
        "tower on the skyline and the Cherwell winding toward it, the walk "
        "where Lewis talked through the night of 19 September 1931.",
    ),
}


# slug -> a ground we drew as SVG. The same promise as ORIGINAL_GROUND — an
# illustration made for the work, with no museum to re-fetch and no designed
# cover to re-crop — for the files that are vector rather than raster. Kept
# apart because every raster path (`art_url`, the webp variants, the scrim
# measure) assumes `covers/art/<slug>.jpg`; an SVG ground is served as it is.
#
# Empty since 2026-09-29: the Key Teachings trees, its only members, were
# replaced by raster grounds in ORIGINAL_GROUND. The tier and its gates stay for
# the next vector Original.
ORIGINAL_SVG_GROUND: dict[str, Original] = {}


# slug -> the scrim each SVG Original needs, MEASURED — carried into
# `art_scrim.ART_SCRIM` by `scripts/tune_art_scrim.py` on every run, because
# that script reads rasters and cannot open these. Measured the tuner's way
# (its compositing model, its AA bars plus MARGIN, its 0.30 floor) but at the
# words' real positions: such covers set their type from the top
# (`coverLayouts.TYPE_TOP`). The tuner reads those rows for a raster itself
# (`covers.ink_boxes`); it is only an SVG it cannot open. Each ground was rasterised in Chromium at 600x800, the
# text bands found on its og twin, and the strength walked up from 0.30. The
# digest in ORIGINAL_SVG_GROUND pins the input: a
# replaced tree fails that gate first, which is the cue to re-measure this.
ORIGINAL_SVG_SCRIM: dict[str, float] = {}

