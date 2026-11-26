"""A Bible book's overview card: who wrote it, when, its key verse and its theme.

The card at the top of each of the 66 Bible book pages (``/books/<slug>/``):
"Paul · c. AD 57 · Key verse Romans 1:16 · The gospel of God's righteousness,
received by faith." The words are ``OVERVIEWS`` below, keyed by the book's
slug:

* ``author`` and ``date`` say what the church has long held, in its own words
  ("Traditionally Moses", "Isaiah son of Amoz"), and say so plainly where
  nobody knows ("Author unknown", "Date unknown") — never a scholarly debate;
* ``key_verse`` is a REFERENCE only. Its text is quoted live from the bundled
  Open Word Bible through ``scripture.lookup``, the verse popover's own source,
  and set the way the book's reader sets it (curled quotes, as
  ``build_owb_book`` curls them), so the card cannot drift from the
  translation the book prints;
* ``theme`` is one plain sentence.

Read at serialize time, so this module is a content root
(``content_sources.json``): editing a theme rebuilds the prerendered page. The
words live here, not in the books' editorial folder, so an edit to an
introduction (which reaches readers only through ``build_owb_book``'s fixture)
does not count as a release of its own.

OTHER LANGUAGES. A Bible edition in another language gets the same card in its
own words: ``author``, ``date`` and ``theme`` from
``data/bible/overview-<lang>.json`` (translated from ``OVERVIEWS``, same
slugs), the key verse quoted from that language's bundled OWB text
(``owb-<lang>``) and its reference in the edition's own book name ("Romanos
1:16"), from its chapter titles. A language with no file has no card — never
the English one.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .quote_marks import convert, curl_singles
from .scripture import lookup, owb_verse, reference_verse_ids

#: The fields every overview carries.
FIELDS = ("author", "date", "key_verse", "theme")

OPEN, CLOSE = "“", "”"

#: The languages whose OWB sets « » outside (as ``build_owb_book`` does).
GUILLEMETS = frozenset({"es", "fr", "ru"})

WORDS = Path(__file__).resolve().parent / "data" / "bible"


@lru_cache(maxsize=16)
def words(language: str) -> dict[str, dict[str, str]]:
    """``{slug: {author, date, theme}}`` in ``language`` ({} where there is none)."""
    if language == "en":
        return OVERVIEWS
    path = WORDS / f"overview-{language}.json"
    return json.loads(path.read_text("utf-8")) if path.is_file() else {}


def table() -> dict[str, dict[str, str]]:
    """``{book slug: overview}``, in canonical order."""
    return OVERVIEWS


def set_quotes(text: str, language: str = "en") -> str:
    """Straight quotes curled as the book's reader curls them (``build_owb_book``
    curls singles, then doubles, the same two steps)."""
    return convert(curl_singles(text), outer_guillemets=language in GUILLEMETS)[0]


def trim_borrowed_quotes(text: str, open_: str = OPEN, close: str = CLOSE) -> str:
    """Drop the quotation marks a verse borrows from its neighbours.

    Read by direction, on curled text: a closing mark with no opening mark
    before it closes a speech that began in an earlier verse ("…as a ransom
    for many.”"), and an opening mark as the very last character opens one
    that runs into the next. Out of context both read as typos, so both go.
    Every paired mark stays, and so does a speech that opens inside the verse
    and runs on past its end (Ruth 1:16), as Bibles print it.
    """
    out: list[str] = []
    depth = 0
    for ch in text:
        if ch == open_:
            depth += 1
        elif ch == close:
            if depth == 0:
                continue  # closes a speech from an earlier verse
            depth -= 1
        out.append(ch)
    result = "".join(out).strip()
    if result.endswith(open_):
        result = result[:-1].rstrip()
    return result


def _chapter_title(slug: str, order: int, language: str) -> str:
    from .models import Chapter

    return (
        Chapter.objects.filter(book__slug=slug, book__language=language, order=order)
        .values_list("title", flat=True)
        .first()
        or ""
    )


_REFERENCE = re.compile(r"^(?P<name>.+?) (?P<ref>\d.*)$")
_TRAILING_NUMBER = re.compile(r"\s\d+$")


def local_reference(reference: str, slug: str, chapter: int, language: str) -> str | None:
    """``reference`` ("Romans 1:16") with the book named as ``language``'s
    edition titles its chapter ("Romanos 1" -> "Romanos 1:16"); None when that
    edition has no such chapter."""
    m = _REFERENCE.match(reference)
    title = _chapter_title(slug, chapter + 1, language)
    name = _TRAILING_NUMBER.sub("", title)
    if not m or not title or name == title:
        return None
    return f"{name} {m['ref']}"


def _anchor_exists(slug: str, order: int, verse: int, language: str = "en") -> bool:
    """Whether reader chapter ``order`` of ``slug`` carries ``id="v<verse>"``:
    a verse OWB prints inside another chapter (Isaiah 64:1, at the end of 63)
    or inside a range ("33–34", whose number is only v33) has none."""
    from .models import Chapter

    body = (
        Chapter.objects.filter(book__slug=slug, book__language=language, order=order)
        .values_list("body_html", flat=True)
        .first()
    )
    return bool(body) and f'id="v{verse}"' in body


@lru_cache(maxsize=512)
def key_verse(slug: str, reference: str, language: str = "en") -> dict | None:
    """``{reference, text, chapter, verse}`` for a key verse, or None when the
    Bible lookup cannot resolve it. ``chapter`` is its ENGLISH chapter (the
    reader prints English chapter ``n`` as reader chapter ``n + 1``); ``verse``
    is the reader's ``#v<n>`` anchor there, or None where the reader prints no
    such anchor in that chapter — the card then links the chapter's top."""
    ref = reference.replace("–", "-")
    ids = sorted(reference_verse_ids(ref))
    if not ids:
        return None
    chapter, verse = ids[0] // 1000 % 1000, ids[0] % 1000
    if language == "en":
        found = lookup(ref)
        if not found or not found.get("verses"):
            return None
        text = " ".join(v["text"] for v in found["verses"])
        label = reference
    else:
        # That language's OWB text, each printed verse once (Psalm 13:5-6).
        printed: dict[int, str] = {}
        for vid in ids:
            if hit := owb_verse(vid, language):
                printed.setdefault(hit[0], hit[1])
        label = local_reference(reference, slug, chapter, language)
        if not printed or not label:
            return None
        text = " ".join(printed.values())
    marks = ("«", "»") if language in GUILLEMETS else (OPEN, CLOSE)
    return {
        "reference": label,
        "text": trim_borrowed_quotes(set_quotes(text, language), *marks),
        "chapter": chapter,
        "verse": verse if _anchor_exists(slug, chapter + 1, verse, language) else None,
    }


def overview(slug: str, language: str = "en") -> dict | None:
    """The overview card for the Bible book ``slug`` in ``language``, or None
    when it has none there."""
    meta = table().get(slug)
    local = words(language).get(slug)
    if not meta or not local:
        return None
    return {
        "author": local["author"],
        "date": local["date"],
        "theme": local["theme"],
        "key_verse": key_verse(slug, meta["key_verse"], language),
    }


#: ``{book slug: overview}``, in canonical order: ``author`` and ``date`` as the
#: church has long held them (said plainly where unknown), ``key_verse`` a
#: reference only, ``theme`` one sentence. See the module doc.
OVERVIEWS: dict[str, dict[str, str]] = {
    "genesis": {
        "author": "Traditionally Moses",
        "date": "Date uncertain",
        "key_verse": "Genesis 1:1",
        "theme": "God creates the world, and begins its rescue through the family of Abraham.",
    },
    "exodus": {
        "author": "Traditionally Moses",
        "date": "Date uncertain",
        "key_verse": "Exodus 3:14",
        "theme": "God frees Israel from slavery, gives his law, and comes to live among them.",
    },
    "leviticus": {
        "author": "Traditionally Moses",
        "date": "Date uncertain",
        "key_verse": "Leviticus 11:45",
        "theme": "How a holy God can live among his people: sacrifice, cleansing and holy living.",
    },
    "numbers": {
        "author": "Traditionally Moses",
        "date": "Date uncertain",
        "key_verse": "Numbers 23:19",
        "theme": "Israel’s forty years in the wilderness, between Sinai and the promised land.",
    },
    "deuteronomy": {
        "author": "Traditionally Moses",
        "date": "Date uncertain",
        "key_verse": "Deuteronomy 6:4–5",
        "theme": "Moses’ last words to Israel: love the LORD your God and keep his covenant.",
    },
    "joshua": {
        "author": "Traditionally Joshua",
        "date": "Date uncertain",
        "key_verse": "Joshua 1:9",
        "theme": "Israel crosses the Jordan and receives the land God promised.",
    },
    "judges": {
        "author": "Author unknown",
        "date": "Date uncertain",
        "key_verse": "Judges 21:25",
        "theme": "Israel’s cycle of turning away and rescue, in the days before a king.",
    },
    "ruth": {
        "author": "Author unknown",
        "date": "Set in the time of the judges",
        "key_verse": "Ruth 1:16",
        "theme": "A Moabite widow’s loyalty, and the kinsman who redeems her into David’s line.",
    },
    "1-samuel": {
        "author": "Author unknown",
        "date": "11th century BC setting",
        "key_verse": "1 Samuel 16:7",
        "theme": "Israel asks for a king: Samuel, Saul, and David chosen by God.",
    },
    "2-samuel": {
        "author": "Author unknown",
        "date": "10th century BC setting",
        "key_verse": "2 Samuel 7:22",
        "theme": "David’s reign: God’s promise to his house, his sin, and its cost.",
    },
    "1-kings": {
        "author": "Author unknown",
        "date": "Completed in the exile, 6th century BC",
        "key_verse": "1 Kings 18:21",
        "theme": "Solomon’s glory, the kingdom divided, and Elijah’s stand against Baal.",
    },
    "2-kings": {
        "author": "Author unknown",
        "date": "Completed in the exile, 6th century BC",
        "key_verse": "2 Kings 17:13",
        "theme": "The kings of Israel and Judah, down to the fall of both kingdoms.",
    },
    "1-chronicles": {
        "author": "Traditionally Ezra",
        "date": "After the exile",
        "key_verse": "1 Chronicles 16:34",
        "theme": "Israel’s story retold around David, the temple and true worship.",
    },
    "2-chronicles": {
        "author": "Traditionally Ezra",
        "date": "After the exile",
        "key_verse": "2 Chronicles 7:14",
        "theme": "From Solomon’s temple to the exile, and the decree to rebuild.",
    },
    "ezra": {
        "author": "Traditionally Ezra",
        "date": "5th century BC",
        "key_verse": "Ezra 7:10",
        "theme": "The exiles return to rebuild the temple and to live by God’s law.",
    },
    "nehemiah": {
        "author": "Nehemiah",
        "date": "5th century BC",
        "key_verse": "Nehemiah 8:10",
        "theme": "Jerusalem’s walls rebuilt, and a people renewed in God’s covenant.",
    },
    "esther": {
        "author": "Author unknown",
        "date": "5th century BC setting",
        "key_verse": "Esther 4:14",
        "theme": "God’s unseen hand saves his people in Persia through a Jewish queen.",
    },
    "job": {
        "author": "Author unknown",
        "date": "Date unknown",
        "key_verse": "Job 19:25",
        "theme": "A righteous man’s suffering, and God’s answer out of the whirlwind.",
    },
    "psalms": {
        "author": "David and others",
        "date": "Written over many centuries",
        "key_verse": "Psalm 46:1",
        "theme": "Israel’s songs and prayers: praise, lament, trust and thanksgiving.",
    },
    "proverbs": {
        "author": "Mainly Solomon",
        "date": "10th century BC onward",
        "key_verse": "Proverbs 1:7",
        "theme": "Wisdom for everyday life, beginning with the fear of the LORD.",
    },
    "ecclesiastes": {
        "author": "The Teacher, traditionally Solomon",
        "date": "Date uncertain",
        "key_verse": "Ecclesiastes 12:13",
        "theme": "Life under the sun is fleeting; fear God and keep his commandments.",
    },
    "song-of-songs": {
        "author": "Traditionally Solomon",
        "date": "Date uncertain",
        "key_verse": "Song of Songs 8:6",
        "theme": "A song of love between a bride and her beloved.",
    },
    "isaiah": {
        "author": "Isaiah son of Amoz",
        "date": "8th century BC",
        "key_verse": "Isaiah 53:5",
        "theme": "The Holy One of Israel judges and redeems, through his suffering servant.",
    },
    "jeremiah": {
        "author": "Jeremiah",
        "date": "Late 7th to 6th century BC",
        "key_verse": "Jeremiah 31:33",
        "theme": "Warnings before Jerusalem’s fall, and the promise of a new covenant.",
    },
    "lamentations": {
        "author": "Traditionally Jeremiah",
        "date": "Soon after 586 BC",
        "key_verse": "Lamentations 3:22–23",
        "theme": "Grief over Jerusalem’s ruin, and hope in the LORD’s steadfast love.",
    },
    "ezekiel": {
        "author": "Ezekiel",
        "date": "6th century BC",
        "key_verse": "Ezekiel 36:26",
        "theme": "A priest in exile sees God’s glory, and the promise of a new heart.",
    },
    "daniel": {
        "author": "Traditionally Daniel",
        "date": "6th century BC setting",
        "key_verse": "Daniel 2:44",
        "theme": "Faithfulness in exile, and the kingdom of God that outlasts empires.",
    },
    "hosea": {
        "author": "Hosea",
        "date": "8th century BC",
        "key_verse": "Hosea 6:6",
        "theme": "God’s unfailing love for unfaithful Israel, pictured in Hosea’s marriage.",
    },
    "joel": {
        "author": "Joel son of Pethuel",
        "date": "Date uncertain",
        "key_verse": "Joel 2:28",
        "theme": "A plague of locusts, a call to return, and the promise of the Spirit.",
    },
    "amos": {
        "author": "Amos, a shepherd of Tekoa",
        "date": "8th century BC",
        "key_verse": "Amos 5:24",
        "theme": "Let justice roll down: judgment on a people who oppress the poor.",
    },
    "obadiah": {
        "author": "Obadiah",
        "date": "Date uncertain",
        "key_verse": "Obadiah 15",
        "theme": "Judgment on Edom for its betrayal of Judah; the kingdom will be the LORD’s.",
    },
    "jonah": {
        "author": "Traditionally Jonah",
        "date": "8th century BC setting",
        "key_verse": "Jonah 2:9",
        "theme": "A reluctant prophet learns how far God’s mercy reaches.",
    },
    "micah": {
        "author": "Micah of Moresheth",
        "date": "8th century BC",
        "key_verse": "Micah 6:8",
        "theme": "Judgment and hope for Judah, and a ruler to come from Bethlehem.",
    },
    "nahum": {
        "author": "Nahum of Elkosh",
        "date": "7th century BC",
        "key_verse": "Nahum 1:7",
        "theme": "The fall of Nineveh, and the LORD a refuge for those who trust him.",
    },
    "habakkuk": {
        "author": "Habakkuk",
        "date": "Late 7th century BC",
        "key_verse": "Habakkuk 2:4",
        "theme": "A prophet questions God, and learns that the righteous live by faith.",
    },
    "zephaniah": {
        "author": "Zephaniah",
        "date": "7th century BC",
        "key_verse": "Zephaniah 3:17",
        "theme": "The day of the LORD is near, yet he will rejoice over his people.",
    },
    "haggai": {
        "author": "Haggai",
        "date": "520 BC",
        "key_verse": "Haggai 1:8",
        "theme": "A call to the returned exiles to rebuild the LORD’s house.",
    },
    "zechariah": {
        "author": "Zechariah",
        "date": "From 520 BC",
        "key_verse": "Zechariah 9:9",
        "theme": "Visions for the rebuilding, and a king who comes humble, on a donkey.",
    },
    "malachi": {
        "author": "Malachi",
        "date": "5th century BC",
        "key_verse": "Malachi 3:1",
        "theme": "God’s love for a weary people, and the messenger who will prepare his way.",
    },
    "gospel-of-matthew": {
        "author": "Traditionally Matthew",
        "date": "1st century AD",
        "key_verse": "Matthew 5:17",
        "theme": "Jesus the Messiah fulfils the Scriptures and brings the kingdom of heaven.",
    },
    "gospel-of-mark": {
        "author": "Traditionally Mark",
        "date": "c. AD 60s",
        "key_verse": "Mark 10:45",
        "theme": "Jesus, the Son of God, came to serve and to give his life as a ransom.",
    },
    "gospel-of-luke": {
        "author": "Traditionally Luke",
        "date": "1st century AD",
        "key_verse": "Luke 19:10",
        "theme": "An orderly account of Jesus, the Saviour who seeks and saves the lost.",
    },
    "gospel-of-john": {
        "author": "Traditionally John the apostle",
        "date": "Late 1st century AD",
        "key_verse": "John 3:16",
        "theme": "Jesus, the Word made flesh, so that believing you may have life in his name.",
    },
    "acts-of-the-apostles": {
        "author": "Traditionally Luke",
        "date": "1st century AD",
        "key_verse": "Acts 1:8",
        "theme": "The Spirit carries the good news of Jesus from Jerusalem to Rome.",
    },
    "romans": {
        "author": "Paul",
        "date": "c. AD 57",
        "key_verse": "Romans 1:16",
        "theme": "The gospel of God’s righteousness, received by faith.",
    },
    "1-corinthians": {
        "author": "Paul",
        "date": "c. AD 54",
        "key_verse": "1 Corinthians 13:13",
        "theme": "Paul answers a divided church: the cross, love, and the resurrection.",
    },
    "2-corinthians": {
        "author": "Paul",
        "date": "c. AD 56",
        "key_verse": "2 Corinthians 12:9",
        "theme": "God’s power made perfect in weakness, in Paul’s defence of his ministry.",
    },
    "galatians": {
        "author": "Paul",
        "date": "c. AD 48 to 55",
        "key_verse": "Galatians 2:20",
        "theme": "Freedom in Christ: made right with God by faith, not by works of the law.",
    },
    "ephesians": {
        "author": "Paul",
        "date": "c. AD 60",
        "key_verse": "Ephesians 2:8–9",
        "theme": "One new people in Christ, saved by grace and called to walk in love.",
    },
    "philippians": {
        "author": "Paul",
        "date": "c. AD 61",
        "key_verse": "Philippians 1:21",
        "theme": "Joy in Christ, written from prison, and the mind of Christ who humbled himself.",
    },
    "colossians": {
        "author": "Paul",
        "date": "c. AD 60",
        "key_verse": "Colossians 1:15",
        "theme": "Christ, the image of the invisible God, is supreme over all and is enough.",
    },
    "1-thessalonians": {
        "author": "Paul",
        "date": "c. AD 51",
        "key_verse": "1 Thessalonians 4:16",
        "theme": "Encouragement for a young church: holy living and the Lord’s coming.",
    },
    "2-thessalonians": {
        "author": "Paul",
        "date": "c. AD 51",
        "key_verse": "2 Thessalonians 3:3",
        "theme": "Stand firm, keep working, and do not be shaken about the day of the Lord.",
    },
    "1-timothy": {
        "author": "Paul",
        "date": "c. AD 63",
        "key_verse": "1 Timothy 1:15",
        "theme": "Guidance for Timothy on sound teaching, worship and leading a church.",
    },
    "2-timothy": {
        "author": "Paul",
        "date": "c. AD 66",
        "key_verse": "2 Timothy 3:16–17",
        "theme": "Paul’s last letter: guard the gospel, endure, and preach the word.",
    },
    "titus": {
        "author": "Paul",
        "date": "c. AD 63",
        "key_verse": "Titus 2:11",
        "theme": "Sound teaching and good works for the churches of Crete.",
    },
    "philemon": {
        "author": "Paul",
        "date": "c. AD 60",
        "key_verse": "Philemon 15–16",
        "theme": "Paul asks Philemon to welcome Onesimus back, no longer a slave but a brother.",
    },
    "hebrews": {
        "author": "Author unknown",
        "date": "Probably before AD 70",
        "key_verse": "Hebrews 4:14",
        "theme": "Jesus the Son is greater: the high priest of a better covenant.",
    },
    "james": {
        "author": "Traditionally James, the Lord’s brother",
        "date": "Mid-1st century AD",
        "key_verse": "James 1:22",
        "theme": "Faith that works: wisdom, patience, and doing the word, not only hearing it.",
    },
    "1-peter": {
        "author": "Peter",
        "date": "c. AD 63",
        "key_verse": "1 Peter 2:9",
        "theme": "A living hope for Christians suffering as exiles in the world.",
    },
    "2-peter": {
        "author": "Traditionally Peter",
        "date": "c. AD 65",
        "key_verse": "2 Peter 3:9",
        "theme": "Grow in grace, beware false teachers, and wait for the day of the Lord.",
    },
    "1-john": {
        "author": "Traditionally John the apostle",
        "date": "Late 1st century AD",
        "key_verse": "1 John 4:8",
        "theme": "God is light and love: assurance for those who walk in his truth.",
    },
    "2-john": {
        "author": "The elder, traditionally John",
        "date": "Late 1st century AD",
        "key_verse": "2 John 6",
        "theme": "Walk in truth and love, and do not welcome false teachers.",
    },
    "3-john": {
        "author": "The elder, traditionally John",
        "date": "Late 1st century AD",
        "key_verse": "3 John 4",
        "theme": "Praise for Gaius’s welcome to the travelling teachers of the truth.",
    },
    "jude": {
        "author": "Jude, brother of James",
        "date": "1st century AD",
        "key_verse": "Jude 3",
        "theme": "Contend for the faith against those who turn grace into licence.",
    },
    "revelation": {
        "author": "John, traditionally the apostle",
        "date": "c. AD 95",
        "key_verse": "Revelation 21:5",
        "theme": "Christ reigns, and will return to make all things new.",
    },
}
