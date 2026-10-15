"""Build a volume of *The Lamplighters of Gloamhaven* — a fantasy series for young readers — from its manuscript.

A house-written adventure series for readers aged 9–12, in six books, set in a
land under a cursed sun. Book 1 is *Fire Against the Dark*: a chimney-sweep
orphan finds a brass lamp that cannot be bought, stolen or earned, only given,
and a city falling to the Hollows learns what that means. The series carries
the shape of the Bible's story — grace, faith, temptation, the cross, mission,
new creation — as story, never as sermon: nothing in it names God or quotes
Scripture, in the manner of the classic Christian fantasies.

The prose is committed as Markdown under
``data/the-lamplighters-of-gloamhaven/<slug>.md`` (Ochorus's own writing,
nothing fetched; ``OUTLINE.md`` beside it is the series bible — world rules,
the lamp's law, the fixed cast, the seeds for later books — which every volume
is written against) in the closed Markdown subset of ``build_rooted.parse``:
one ``## Title`` per chapter, one paragraph per line. A novel has no study
questions, so ``study_questions`` stays empty on every chapter.

Fixture-driven: ``seed_books`` creates the book on the next deploy from
``fixtures/content/books/<slug>.en.json``. Idempotent. The series row lives in
``fixtures/content/series.json``.

    DJANGO_DEBUG=true uv run python manage.py build_lamplighters 1
"""

from __future__ import annotations

import re
from html import escape, unescape

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.build_rooted import DATA_DIR, parse
from library.models import Author, Book, Chapter, Series
from library.quote_marks import convert

SERIES = "the-lamplighters-of-gloamhaven"

#: The founder's own series, written with Ochorus: credited jointly, as a byline
#: (``is_imprint``), not as a person with a biography.
AUTHOR_SLUG = "james-degreef-and-ochorus"

ATTRIBUTION = (
    "© James DeGreef and Ochorus. An Ochorus Original, written for young "
    "readers, free to read and share. Book 1 of The Lamplighters of Gloamhaven."
)

#: Book 1's plates — shadow-play silhouettes in the style the founder approved
#: (2026-10-14). The anchor is the opening of the manuscript paragraph the plate
#: follows; the build fails if it matches no paragraph, or more than one.
PLATES_1: tuple[tuple[int, str, str, str, str], ...] = (
    (
        1,
        "Only it was not quite dark.",
        "plate-01-the-lamp-in-the-flue.jpg",
        "Wren, a small black silhouette, braced across a narrow brick chimney "
        "with her back to one wall and her feet to the other, reaches up toward "
        "a brass lamp glowing gold in a niche, a red ribbon at her wrist; below "
        "her in the dark, a Gutterling climbs and white eyes watch.",
        "Halfway up, in a little niche cut into the brick, something was shining.",
    ),
    (
        2,
        "It went in with a dull",
        "plate-02-the-lamp-in-the-canal.jpg",
        "A small girl with spiky hair stands silhouetted at the edge of a black "
        "canal, looking down at a brass lamp still shining on the muddy bottom "
        "among old bottles; its light spreads in gold rings across the water, "
        "with black tannery buildings opposite under a hazy grey sky.",
        "…like a star that had fallen out of the sky and gone to sleep.",
    ),
    (
        3,
        "As he watched, the point of light moved.",
        "plate-03-the-orrery.jpg",
        "A tall, gangly boy in spectacles bends over a round table holding a brass "
        "ring of tiny dim beads, staring at one brilliant point of light inside "
        "it; behind him a round window looks onto the night city, with clocks, "
        "jars, maps and a telescope in the shadows and a small glass lamp at the "
        "table’s edge.",
        "…brighter than any bead on the whole Orrery, brighter than the whole Ring put together.",
    ),
    (
        4,
        "She leapt the gap to the cooper's roof,",
        "plate-04-the-rooftop-chase.jpg",
        "A small spiky-haired girl leaps across a gap between two slate roofs, a "
        "stolen compass in her fist and a warm glow leaking from inside her coat, "
        "while behind her a tall, gangly boy in spectacles wobbles on the ridge "
        "with his arms flung out among chimney-pots and sagging washing lines.",
        "No nob alive could follow her across the roofs of Soot Lane.",
    ),
    (
        5,
        "It was not the small warm glow she knew.",
        "plate-05-over-the-wall.jpg",
        "In a dark street of crooked black houses, a small girl holds up a blazing "
        "white-gold lamp. Near a bakery door, a tall grey faceless smoke-figure "
        "shrinks back from the light, away from a tiny child patting a grey baker "
        "on her doorstep, while more grey shapes pour over the city wall behind.",
        "It was white-gold, blazing, as if somebody had opened the door of a great furnace.",
    ),
    (
        6,
        "Then the younger guardsman stopped in front of the",
        "plate-06-the-mechanical-footman.jpg",
        "In a dim attic workshop, a guard with a halberd recoils from a tall tin "
        "automaton whose two round eyes and chest-door seams glow gold, while a "
        "boy in spectacles stands rigid at a cluttered bench and a stout sergeant "
        "watches from the doorway beside a thin steward.",
        "“Sarge, its eyes are lit.”",
    ),
    (
        7,
        "He reached up with his long pole, the brass",
        "plate-07-the-leaning-tower.jpg",
        "At night on a city wall, a tall, stooped, bearded old man in a long coat "
        "uses a long hooked pole to relight a tall street-lamp. High in a crooked "
        "leaning tower, a girl and a small fox watch from a little gold-lit window "
        "under the roof, and faint grey figures drift on the plain beyond the wall.",
        "The Ring-lamp coughed and caught and burned up again, brighter than its neighbours.",
    ),
    (
        8,
        "Cinder strolled out from behind the stool, and her shadow",
        "plate-08-the-shadow-play.jpg",
        "Two children sit in silhouette before a hanging sheet lit gold from "
        "behind. On it a giant fox shadow walks beside a paper mountain, where a "
        "tiny figure carries a glowing lamp, while a bearded old man kneels at the "
        "sheet’s edge.",
        "A fox the size of a carthorse, with a brush like a bonfire.",
    ),
    (
        9,
        "And as he said it, Tobin saw him",
        "plate-09-the-ceiling-beam.jpg",
        "A boy lies along a beam in the dark space above a ceiling, his eye to a "
        "crack beside a plaster rose; below, a tall man in a grey cloak sits by a "
        "desk rubbing his palm while a lord stands beneath a portrait of a "
        "fair-haired woman.",
        "From up in the ceiling Tobin could see the palm quite clearly.",
    ),
    (
        10,
        "He looked at her. He put his foot where",
        "plate-10-across-the-glass-dome.jpg",
        "On a vast glass dome high above a dark city, a fox, a terrified gangly boy "
        "and a small girl inch along a narrow iron rib. The girl reaches back to "
        "the boy, a faint gold glow shines from inside her coat, and a white-eyed "
        "imp waits ahead at the dome’s edge.",
        "“Look at me. Not down. Me.”",
    ),
    (
        11,
        "And in that light, Nettle's freckles came back.",
        "plate-11-given-to-nettle.jpg",
        "At night, a kneeling girl holds out a glowing lamp in both hands to a tiny "
        "girl sitting on a bakery step, whose blue eye and pink cheek show in the "
        "gold light; a boy shields his eyes, a grey fox with a glowing tail "
        "watches, and grey ghostly shapes flee.",
        "“Here, Nettle. It’s for you. You don’t have to do anything.”",
    ),
    (
        12,
        "He took the stairs two at a time.",
        "plate-12-the-strongroom-stair.jpg",
        "A tall, thin boy in a long coat, in black silhouette, climbs a dark stone "
        "stair two steps at a time, holding up a small brass lamp. Its gold glow "
        "lights the damp stone wall and catches his spectacles, and an unlit "
        "lantern dangles from his other hand.",
        "…every one of its sixty-one steps lit and golden and perfectly plain.",
    ),
    (
        13,
        "At last Snib stopped at the edge of a high roof and pointed with one long finger.",
        "plate-13-snibs-rooftop-road.jpg",
        "Above a blacked-out city, a small white-eyed Gutterling at the end of a "
        "roof ridge points at a tall black tower with an empty bowl on top; behind "
        "him come a grey fox with a glowing tail, a hunched girl with gold light "
        "leaking from her coat and a boy crawling on hands and knees, while grey "
        "shapes fill the streets and a grey rider waits at the tower’s foot.",
        "“Beacon Square,” he whispered. “Big tower. Big trouble.”",
    ),
    (
        14,
        "She heard the fire go down into the pipes",
        "plate-14-given-away.jpg",
        "On top of the Great Beacon, Wren tips the lamp over the rim of the vast "
        "iron bowl and gold fire roars up, while Captain Varrick throws an arm "
        "across his eyes; far below, the Ring of lamps blazes around the city.",
        "And she tipped the lamp, and gave the Flame away.",
    ),
    (
        15,
        "They walked out together: a tall old man with",
        "plate-15-into-the-greywaste.jpg",
        "From the top of a city wall lined with glowing gold lamps, a tall old man "
        "with a hooked pole, a lanky boy, a small girl carrying a glowing lamp and "
        "a grey fox walk away down a road across a pale grey plain of dead trees, "
        "toward a faint mountain with a gold point under a pale sun; a tiny grey "
        "horseman is far off on the plain.",
        "Behind them the Ring burned gold along the wall.",
    ),
)

#: The size every plate is shipped at (portrait, the house plate frame).
#: Book 2's plates, in the same hand as Book 1's (2026-10-15).
PLATES_2: tuple[tuple[int, str, str, str, str], ...] = (
    (
        1,
        "All round the foot of the waystone, in a circle",
        "b2-plate-01-the-pale-road.jpg",
        "On a pale grey plain, a small girl with a lamp holds it to a "
        "glowing stone post, and a circle of green grass spreads round "
        "its base. A tall stooped old man with a hooked pole, a gangly "
        "boy holding a compass and a grey fox with a glowing tail-tip "
        "watch; far off on a rise sits a tiny grey rider.",
        "“Green,” said Old Ash softly. “That’s green, that is.”",
    ),
    (
        2,
        "She did not think about it. There was no time",
        "b2-plate-02-the-hollow-hunt.jpg",
        "In a dark gully at dusk, a girl lunges forward holding out a "
        "blazing lamp while grey smoky figures flee up the banks. A boy "
        "with fogged spectacles stands frozen, a tall old man lies "
        "propped on one elbow with one leg turned ash-grey, and a grey "
        "fox with a white-hot tail-tip bristles.",
        "…it flared — white-gold, all at once, like a door flung open.",
    ),
    (
        3,
        "“Hide it,” said Old Ash. His voice cracked like",
        "b2-plate-03-mothwing-weather.jpg",
        "At dusk, a kneeling girl reaches for a lamp on a stone, beside a"
        " huge moth whose wings glow like faint stained glass. A boy "
        "holding sticks stares at it, an old man sitting under dead trees"
        " thrusts out his arm in warning, and a grey fox on the ridge "
        "faces an enormous cloud of moths rising from the plain.",
        "“Hide it, child. Every scrap of light. Now.”",
    ),
    (
        4,
        "But the girl beside Wren had not flinched. She",
        "b2-plate-04-down-among-the-delvers.jpg",
        "In a cavern, a girl sitting on rubble holds a glowing lamp in "
        "her tied hands. A ring of tall, braided cave-folk raise their "
        "palms against its warmth, while a girl with long beaded braids "
        "kneels close and holds her hands out to it.",
        "“It’s like standing next to someone who’s laughing.”",
    ),
    (
        5,
        "Every surface. The ledge they stood on was cut",
        "b2-plate-05-the-city-of-echoes.jpg",
        "A girl in a cliff doorway holds a lamp high. Its small circle of"
        " light shows carved spiral walls threaded with faint colours, a "
        "ridged ledge, a tall fluted column across a gap, a seated girl "
        "with beaded braids, and a woman carrying a basket on her head. "
        "Everything beyond the circle is black.",
        "Above that ring there was no roof that she could see.",
    ),
    (
        6,
        "It went up gold and white, so bright that",
        "b2-plate-06-the-elders-judgment.jpg",
        "In a round hall of tiered stone benches packed with hundreds of "
        "braided figures, many shielding their faces, a girl on a round "
        "stone holds out a blazing lamp. Seven elders sit on a carved "
        "ledge, the huge bearded Speaker in the middle facing her "
        "unflinching. An old man on a stretcher with a fox, and a boy in "
        "spectacles, are beside her.",
        "“Here. Feel it. It’s for you. You don’t have to do anything.”",
    ),
    (
        7,
        "It was only a shape in the stone.",
        "b2-plate-07-the-story-wall.jpg",
        "Two girls kneel in silhouette before a wall of pale carved "
        "stone: a robed man kneeling with his hand over a child’s eyes, "
        "holding a small lamp-shaped carving whose bead glows gold. Wren "
        "holds up a brass lamp, and Mira, with long beaded braids, rests "
        "her fingertips on rows of raised marks.",
        "…the little bead in the Warm Man’s hand shone gold.",
    ),
    (
        8,
        "Mira could not see any of that. So",
        "b2-plate-08-the-whispering-galleries.jpg",
        "Inside a round, ribbed tunnel with three dark archways, Wren "
        "holds the lamp high, while tall Tobin holds a thread that drifts"
        " into the right-hand arch and Mira touches its end. In front, "
        "Old Ash lies propped on a stone-sledge with his hooked pole, and"
        " Cinder the fox sits beside him with her tail glowing.",
        "…the thread stirred, and lifted, and leaned…",
    ),
    (
        9,
        "Captain Varrick stepped out of the mouth of",
        "b2-plate-09-varrick-in-the-deeps.jpg",
        "A tall man in a grey cloak stands at a ribbed tunnel mouth, with"
        " armoured knights behind him and grey, smoky, faceless shapes "
        "drifting in the dark. Facing him, a girl holds up a glowing lamp"
        " while a fox bristles, a braided girl grips her sleeve, an old "
        "man lies on a sledge, and blind Delvers cross a rope bridge "
        "toward a doorway.",
        "“Give me the lamp, child, and I leave them their songs.”",
    ),
    (
        10,
        "The lamp stood up straight in the draught.",
        "b2-plate-10-the-black-stair.jpg",
        "A boy in spectacles climbs a dark spiral stair, holding a "
        "glowing lamp above his head. A big bearded man carrying a child "
        "follows him on a rope, and a line of shadowy figures holding the"
        " rope winds down into blackness.",
        "“Though I walk through the gloaming,” said Tobin Harrowgate, “I "
        "will fear no dark—”",
    ),
    (
        11,
        "He gathered his son up off the grass, blanket",
        "b2-plate-11-light-in-the-low-places.jpg",
        "On a grassy hilltop under a pale moon, a kneeling boy holds out "
        "a glowing lamp to a small child cradled by a big kneeling man, "
        "who bows his head over him and weeps. Other figures sit among "
        "the rocks behind, faces lifted to the sky.",
        "“Why is it warm? Where is the roof?”",
    ),
    (
        12,
        "The ferryman did not answer. He dipped his",
        "b2-plate-12-the-ferryman.jpg",
        "In a misty grey river, a hooded ferryman leans from the stern of a "
        "long boat and lays his thumbs on the closed eyes of Mira, a girl with "
        "beaded braids. Wren watches beside her, holding a glowing lamp, while "
        "Tobin and Old Ash look on.",
        "“It is a gift. That is all.”",
    ),
    (
        13,
        "And Wren laughed.",
        "b2-plate-13-colours.jpg",
        "A grey morning beside a misty river, under a dull sun. Mira, "
        "with long beaded braids, kneels and tilts a tin cup towards a "
        "small glowing lamp. Wren sits on the shingle with her head "
        "thrown back laughing and one arm flung up; a fox has its paws on"
        " her knee. Tobin is bent double laughing behind them, and Old "
        "Ash sits on a stone by a small fire with one leg stretched out. "
        "Faint colours show in the pebbles only near the lamp.",
        "“It is the colour of what it tastes like.”",
    ),
    (
        14,
        "So Wren went, and stood beside the waystone",
        "b2-plate-14-a-letter-sealed-in-grey.jpg",
        "At dusk on grey hills, Tobin sits hunched on the base of a tall "
        "waystone whose niche glows gold behind him. He holds a folded "
        "letter with a grey seal showing a tower and a flame. Wren sits a"
        " little way off at the edge of the stone, hands in her pockets, "
        "looking at him. Far up the slope the others wait by an open "
        "satchel and a grazing horse, and a line of small lit waystones "
        "runs back across the hills.",
        "For a long time neither of them said anything.",
    ),
    (
        15,
        "Old Ash had not said a word. He stood",
        "b2-plate-15-the-lights-of-vaelport.jpg",
        "Five small black silhouettes stand on a dark clifftop at dusk: a"
        " tall stooped old man leaning on two poles, a fox sitting with "
        "its back to the sea, a girl with long braids holding her hands "
        "up before her face, a small girl holding a glowing gold lamp, "
        "and a tall boy at the cliff edge. Across a wide bay, a tiered "
        "city on the hills shines brilliant white, sending long beams "
        "over the water.",
        "“That isn’t Flame,” he said.",
    ),
)

#: The whole land, shared by every volume's endpapers (the map is the series').
LAND_MAP = (
    "land-of-gloamhaven.jpg",
    "A parchment map of Gloamhaven: the Bright Mountain in the north "
    "above the Greywaste and the Delver Deeps; walled Emberwick ringed "
    "with lamps at the centre; Thornmere’s marshes and the Gloam River "
    "running to Vaelport on the south-west coast; the Harrowgate "
    "Highlands in the east; the Burned Country and Cinder Hill to the "
    "south; and Nightfall Spire on the Sunless Sea. A dotted red road, "
    "numbered one to six, links them.",
    "The Land of Gloamhaven",
)

PLATE_SIZE = (900, 1200)

VOLUMES: dict[int, dict[str, object]] = {
    1: {
        "slug": "fire-against-the-dark",
        "publication_year": 2026,
        "title": "Fire Against the Dark",
        "subtitle": "The Lamplighters of Gloamhaven, Book One",
        # The cover's byline row is one short line; the Ochorus mark at its foot
        # completes "James DeGreef and Ochorus", the byline everywhere else.
        "cover_byline": "James DeGreef",
        # Downloadable (export_policy): book-pdfs.yml builds and uploads the PDF on merge.
        "pdf_url": (
            "https://eywunobxqijvwymdzlwy.supabase.co/storage/v1/object/public/"
            "book-pdfs/fire-against-the-dark.pdf?download=fire-against-the-dark.pdf"
        ),
        # The book's endpapers: the whole land first, then the city — set at the
        # head of Chapter 1, as a printed book sets its maps before the story.
        # Wordless they are not (a map is lettered), so each language edition
        # will want its own lettering when the book is translated.
        "maps": (
            LAND_MAP,
            (
                "map-of-emberwick.jpg",
                "A pen-and-ink map of the walled city of Emberwick: the Ring of "
                "lamps along the wall, most of them dark; the Great Beacon in "
                "Beacon Square at the centre; the Hill with the Warden’s Hall, the "
                "Guild Hall and Thornbury House; the crowded Low Quarter and Soot "
                "Lane; the Soot Canal with Tallow Bridge and Crookback Market; Old "
                "Ash’s Leaning Tower on the north wall; and the Grey Gate, where the "
                "road leaves for the Bright Mountain.",
                "Emberwick, City of the Ring",
            ),
        ),
        # The full-page plates, each set straight after the paragraph it
        # pictures: (chapter, the paragraph's opening words, file, alt, caption).
        "plates": PLATES_1,
        "cover_url": "/covers/art/fire-against-the-dark.jpg",  # ORIGINAL_GROUND, #6060
        "cover_color": covers.ink_safe("#b5651d"),  # an ember in the grey
        "description": (
            "In the smoky city of Emberwick the sun has been pale for three "
            "hundred years, and the lamps on the city wall are failing. Wren "
            "Ashby, a chimney-sweep and a thief who believes nothing in life is "
            "free, finds a battered brass lamp hidden in a sealed chimney. It "
            "burns without oil, it relights itself when she blows it out, and "
            "it keeps coming back however hard she tries to sell it. Soon the "
            "Lamp Guild calls it witch-light, the Warden wants it, a captain in "
            "grey has come to bargain for it, and the Hollows are coming over "
            "the wall. With Tobin, the Warden's son who is secretly afraid of "
            "the dark, and Old Ash, the last true Lamplighter, Wren must learn "
            "the lamp's one law before the last light in Emberwick goes out."
        ),
        "about_html": (
            "<p>Fire Against the Dark is the first book of The Lamplighters of "
            "Gloamhaven, an adventure series by James DeGreef and Ochorus for readers aged "
            "nine to twelve, and a good book to read aloud to younger children "
            "too. It is a story of chimneys and rooftops, a city wall lit by "
            "failing lamps, shadow-creatures that drain the colour out of "
            "everything they touch, a clever ember-fox, a gang of thieving "
            "soot-imps, and two children who have to be braver than they "
            "think they are.</p>"
            "<p>Underneath the adventure it is a story about grace. The lamp at "
            "its heart cannot be bought, stolen or earned, only given, and what "
            "is given grows. Wren has spent her whole life believing that "
            "everything costs, and the book follows her slowly learning to "
            "receive a gift, and then to give one away when giving seems to "
            "cost her everything. Like the classic Christian fantasies it "
            "follows, it never preaches and never names the One it points to; "
            "it lets the story carry the meaning, for children to discover and "
            "for parents to talk about.</p>"
            "<p>The book has fifteen chapters, about the length of a classic "
            "children's fantasy, each one a good evening's reading. Five more "
            "books will follow Wren, Tobin and Old Ash on the long road to the "
            "Bright Mountain, where the Flame began.</p>"
            "<p>© James DeGreef and Ochorus. An Ochorus Original, free to read and share.</p>"
        ),
        "qa": [
            {
                "question": "What age is Fire Against the Dark written for?",
                "answer": (
                    "It is written for readers aged nine to twelve, and it reads "
                    "aloud well to younger children from about seven. The peril "
                    "is real but never gory, and there is plenty of humour."
                ),
            },
            {
                "question": "What is the story about?",
                "answer": (
                    "A chimney-sweep orphan called Wren finds a brass lamp that "
                    "burns without oil and cannot be sold. When the city's wall of "
                    "lamps fails and shadow-creatures called Hollows pour in, she "
                    "and her friends must decide what the lamp is for."
                ),
            },
            {
                "question": "What is the lamp's law?",
                "answer": (
                    "Old Ash teaches it in Chapter 8: it cannot be bought, stolen "
                    "or earned, only given. And its second half: what is given, "
                    "grows."
                ),
            },
            {
                "question": "Is it a Christian book?",
                "answer": (
                    "Yes. Like the classic Christian fantasies, it tells the gospel's "
                    "shape as a story rather than a sermon: grace that cannot be "
                    "earned, a light the darkness cannot put out, and a Lampwright "
                    "whose story readers will recognise. It never names God or "
                    "quotes Scripture directly."
                ),
            },
            {
                "question": "Who are the main characters?",
                "answer": (
                    "Wren Ashby, a quick-tongued sweep and thief; Tobin Harrowgate, "
                    "the Warden's clever son, who is secretly afraid of the dark; "
                    "Old Ash, the last true Lamplighter; and Cinder, his ember-fox, "
                    "who sneezes sparks."
                ),
            },
            {
                "question": "Who is the Lampwright?",
                "answer": (
                    "In the old stories he came down from the Bright Mountain with "
                    "true fire, lit lamps for anyone who asked and never charged, "
                    "and was snuffed out on Cinder Hill, until on the third morning "
                    "the Flame burned again on the mountain. Readers may notice that "
                    "he is closer to the story than anyone thinks."
                ),
            },
            {
                "question": "How long is the book?",
                "answer": (
                    "Fifteen chapters and about forty-eight thousand words, much the "
                    "length of a classic children's fantasy. Each chapter is a good "
                    "evening's reading."
                ),
            },
            {
                "question": "Is it part of a series?",
                "answer": (
                    "Yes. It is the first of six books in The Lamplighters of "
                    "Gloamhaven. Each can be read on its own, and together they "
                    "follow the long road to the Bright Mountain."
                ),
            },
        ],
    },
    2: {
        "slug": "the-black-stair",
        "publication_year": 2026,
        "title": "The Black Stair",
        "subtitle": "The Lamplighters of Gloamhaven, Book Two",
        "cover_byline": "James DeGreef",
        "attribution": (
            "© James DeGreef and Ochorus. An Ochorus Original, written for young "
            "readers, free to read and share. Book 2 of The Lamplighters of Gloamhaven."
        ),
        # Downloadable (export_policy): book-pdfs.yml builds and uploads the PDF on merge.
        "pdf_url": (
            "https://eywunobxqijvwymdzlwy.supabase.co/storage/v1/object/public/"
            "book-pdfs/the-black-stair.pdf?download=the-black-stair.pdf"
        ),
        # The road has left Emberwick, so the endpaper is the whole land only.
        "maps": (LAND_MAP,),
        "plates": PLATES_2,
        "cover_url": "/covers/art/the-black-stair.jpg",  # ORIGINAL_GROUND
        "cover_color": covers.ink_safe("#3d5a6b"),  # deep cave-water slate
        "description": (
            "Wren, Tobin, Old Ash and Cinder have relit Emberwick's Ring and set out "
            "across the Greywaste for the Bright Mountain, with a grey rider on the "
            "road behind them. Then a swarm of mothwings drives them underground, "
            "into the Delver Deeps: a city built for sound, whose people have never "
            "seen light and think it a fairy tale. There they meet Mira, a blind "
            "girl who reads the world by echo and believes an old story carved on a "
            "hidden wall. When Captain Varrick comes down into the dark for the "
            "lamp, the only way out is the Black Stair, a thousand steps of total "
            "darkness, and Wren must do the hardest thing she has ever done: give "
            "the lamp away to someone else and trust him to carry it."
        ),
        "about_html": (
            "<p>The Black Stair is the second book of The Lamplighters of "
            "Gloamhaven, an adventure series by James DeGreef and Ochorus for readers "
            "aged nine to twelve. It follows straight on from Fire Against the Dark, "
            "but a new reader can begin here: the travellers are introduced again, "
            "and the story stands on its own.</p>"
            "<p>This is a book about courage in the dark. Tobin, who has always been "
            "afraid of it, has to climb a thousand steps of it with hundreds of "
            "people trusting him. Wren, who has never trusted anyone, has to hand "
            "over the one thing she owns. And Mira, a girl who has never seen, "
            "believes in a light she cannot see because an old story told her it was "
            "coming. Like the book before it, it never preaches; it lets a story of "
            "faith, trust and a gift freely given speak for itself, for children to "
            "discover and for parents to talk about.</p>"
            "<p>The book has fifteen chapters, about the length of a classic "
            "children's fantasy, each one a good evening's reading.</p>"
            "<p>© James DeGreef and Ochorus. An Ochorus Original, free to read and share.</p>"
        ),
        "qa": [
            {
                "question": "Do I need to read Fire Against the Dark first?",
                "answer": (
                    "It helps, because The Black Stair carries straight on from it, "
                    "but the opening chapters introduce Wren, Tobin, Old Ash and "
                    "Cinder again, so a new reader can begin here."
                ),
            },
            {
                "question": "What age is The Black Stair for?",
                "answer": (
                    "Readers aged nine to twelve, and it reads aloud well to younger "
                    "children from about seven. There is real danger in the dark, "
                    "but nothing gory, and plenty of humour."
                ),
            },
            {
                "question": "Who is Mira?",
                "answer": (
                    "A Delver girl who has been blind from birth and reads the world "
                    "by the echo of clicks. She is quick, funny and brave, and she "
                    "believes an old story about a Warm Man who promised that one day "
                    "her people would see."
                ),
            },
            {
                "question": "What is the Black Stair?",
                "answer": (
                    "A thousand steps of total darkness that climb from the Delver city "
                    "of Deepholm to the surface. When Captain Varrick comes for the "
                    "lamp, it is the only way out."
                ),
            },
            {
                "question": "What happens to the lamp in this book?",
                "answer": (
                    "It still cannot be bought, stolen or earned, only given. On the "
                    "Black Stair Wren has to truly give it to Tobin so that he can lead "
                    "the Delvers up, the hardest act of trust she has ever made."
                ),
            },
            {
                "question": "Is it a Christian book?",
                "answer": (
                    "Yes. Like the classic Christian fantasies, it tells its truths as "
                    "story rather than sermon: faith in what cannot yet be seen, courage "
                    "that trusts while it is afraid, and sight given as a gift. It never "
                    "names God or quotes Scripture directly."
                ),
            },
            {
                "question": "How long is the book?",
                "answer": (
                    "Fifteen chapters and about forty-eight thousand words, much the "
                    "length of a classic children's fantasy."
                ),
            },
        ],
    },
}




def _figure(slug: str, file: str, alt: str, caption: str, size: tuple[int, int]) -> str:
    width, height = size
    return (
        f'<figure><img src="/illustrations/{slug}/{file}" alt="{escape(alt)}" '
        f'width="{width}" height="{height}"><figcaption>{escape(caption)}</figcaption></figure>'
    )


def _plain(html_text: str) -> str:
    """A paragraph's text for matching: tags gone, entities decoded, quotes straight."""
    text = unescape(re.sub(r"<[^>]+>", "", html_text))
    return text.translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'}))


def _place_plates(slug: str, order: int, body: str, plates) -> str:
    """Set each of this chapter's plates after the paragraph its anchor opens.

    Matched on plain text, so an anchor written as the manuscript reads (straight
    quotes, *italics* as plain words) finds the parsed paragraph however the
    parser spelled its apostrophes or emphasis.
    """
    for chapter, anchor, file, alt, caption in plates:
        if chapter != order:
            continue
        paragraphs = list(re.finditer(r"<p>.*?</p>", body, re.S))
        hits = [m for m in paragraphs if _plain(m.group(0)).startswith(_plain(anchor))]
        if len(hits) != 1:
            raise CommandError(
                f"plate {file}: anchor {anchor!r} opens {len(hits)} paragraphs "
                f"in chapter {order}, not exactly one"
            )
        at = hits[0].end()
        body = body[:at] + _figure(slug, file, alt, caption, PLATE_SIZE) + body[at:]
    return body


#: The size every map is shipped at — large enough that its lettering stays
#: sharp when a reader zooms; the reader scales it to the column.
MAP_SIZE = (1800, 1350)


def _maps_html(slug: str, maps) -> str:
    """The volume's maps as `<figure>`s (the sanitizer settles their attributes)."""
    return "".join(_figure(slug, file, alt, caption, MAP_SIZE) for file, alt, caption in maps)


class Command(BaseCommand):
    help = "Build a volume of The Lamplighters of Gloamhaven from its manuscript (dev DB); then serialize the fixture."

    def add_arguments(self, parser):
        parser.add_argument("volume", type=int)

    @transaction.atomic
    def handle(self, *args, **opts):
        volume = opts["volume"]
        if volume not in VOLUMES:
            raise CommandError(f"{SERIES} has no volume {volume}; known: {sorted(VOLUMES)}")
        meta = dict(VOLUMES[volume])
        slug = meta.pop("slug")
        maps = meta.pop("maps", ())
        plates = meta.pop("plates", ())
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist as exc:
            raise CommandError(f"author {AUTHOR_SLUG!r} not found — seed authors.json first.") from exc
        try:
            series_row = Series.objects.get(slug=SERIES)
        except Series.DoesNotExist as exc:
            raise CommandError(f"series {SERIES!r} not found — load series.json first.") from exc

        chapters = parse((DATA_DIR / SERIES / f"{slug}.md").read_text())

        content = {
            "author": author,
            "attribution": ATTRIBUTION,
            "source_url": "",
            "series": series_row,
            "series_position": volume,
            "sort_order": book_sort_order(slug),
            **meta,
        }
        book, created = Book.objects.update_or_create(
            slug=slug,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
            },
        )
        book.chapters.all().delete()

        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = _place_plates(slug, order, body, plates)
            if order == 1:
                body = _maps_html(slug, maps) + body
            body, _ = convert(clean_fragment(body), outer_guillemets=False)
            body = settled_chapter_body(slug, order, body)
            title, _ = convert(title, outer_guillemets=False)
            wc = word_count(body)
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body, study_questions=[])
            self.stdout.write(f"  ch {order}: {title[:48]:48} {wc:>5} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {book.title!r} — {book.chapter_count} chapters, {total} words"))
