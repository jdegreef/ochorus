"""Build Zilpha Elaw's *Memoirs* (London, 1846) from a committed page-by-page proof.

The only scan of the 1846 printing on the Internet Archive
(`MinisterialTravelsAndLaboursOfMrs.ZilphaElaw`) is set in a bold, blotchy face
that archive.org's own OCR reads badly, and it stops at page 168 mid-sentence.
So the text was proofed line by line against the page images (two OCR passes,
every page read against its scan) and the four missing pages (169–172) were
proofed from the Google Books copy of the same edition (id `yQyKdhcxtHsC`).
The proof is committed as `data/memoirs-of-mrs-zilpha-elaw/pages.txt` — one
line per PRINTED line, in print order, with a two-character prefix:

    "¶ "  the line opens an indented paragraph
    "  "  an ordinary continuation line
    "V "  a line of verse (her hymns are set apart and kept as verse)
    "## " a page marker (printed page number; the dedication's pages unnumbered)

It is a faithful transcription: 1846 spellings, punctuation and line-end
hyphens as printed. `{word?}` marks a reading the proofer could not see whole
(an ink blot, a letter that failed to ink); `READINGS` settles each one.

The 1846 book has NO chapter divisions — a dedication, then one continuous
narrative. A 50,000-word single chapter reads badly on a phone, so the memoir is
split at paragraph boundaries where her story turns (a new period or a new
field of travel), under plain editorial titles; `CHAPTERS` names each break by
the opening words of its first paragraph. The wording is untouched apart from
`CORRECTIONS`: obvious printer's errors (broken or dropped type, a wrong digit
the context proves), each one listed there.

    DJANGO_DEBUG=true uv run python manage.py build_zilpha_elaw
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert

SLUG = "memoirs-of-mrs-zilpha-elaw"
TITLE = "Memoirs of Mrs. Zilpha Elaw"
# The 1846 title page in full: "Memoirs of the Life, Religious Experience,
# Ministerial Travels and Labours of Mrs. Zilpha Elaw, an American Female of
# Colour". Split so the cover can carry it.
SUBTITLE = "Life, Religious Experience, Ministerial Travels and Labours"
AUTHOR_SLUG = "zilpha-elaw"
ARCHIVE_ID = "MinisterialTravelsAndLaboursOfMrs.ZilphaElaw"
COVER_COLOR = "#2f4a5c"  # deep slate blue — house-style cover ground

AUTHOR_STUB = {"name": "Zilpha Elaw", "birth_year": 1790, "death_year": 1873}

DESCRIPTION = (
    "A free Black woman from Pennsylvania tells how God found her: a girl in "
    "service with a Quaker family, converted by a vision of Christ, sanctified "
    "at a camp meeting, and called to preach against the protests of her "
    "husband, her church and her own fears. Widowed, she travelled the slave "
    "states, New England and then England itself, preaching more than a "
    "thousand sermons there. Written in London in 1846 and dedicated to the "
    "English friends who heard her, it is a fervent record of holiness, "
    "hardship and a call she would not deny."
)

ATTRIBUTION = (
    "Public domain — first published London, 1846. Proofed line by line from "
    "the Internet Archive scan of the first edition, with its four missing "
    "final pages from the Google Books copy. The original has no chapters: the "
    "chapter divisions and titles are editorial; the wording is unchanged "
    "apart from a few obvious printer's errors."
)

DATA = Path(__file__).resolve().parent / "data" / SLUG / "pages.txt"

# (title, opening words of the chapter's first paragraph). The first chapter
# starts at the top of the proof; every later anchor must open exactly one
# paragraph.
CHAPTERS: list[tuple[str, str | None]] = [
    ("Dedication", None),
    ("Childhood, Conversion and Marriage", "I WAS born in the United States"),
    ("Sanctification and a Sister's Death", "In the year 1817, I attended"),
    ("The Call to Preach", "But still I could not believe"),
    ("Widowhood and the First Journeys", "The fatal hour came at last"),
    ("Baltimore, Washington and the Slave States", "I returned home in April, 1828"),
    ("New York, New Haven and Hartford", "My mind was at this time directed"),
    ("Boston, Cape Cod and Salem", "I left Hartford for Boston"),
    ("Maine and Nantucket", "From Salem I again returned to Boston"),
    ("Last Years in America", "While I was in this district"),
    ("England: London, Yorkshire and Lancashire", "On the 23rd day of July, we"),
    ("Newcastle, Shields and a Farewell", "On the 2nd of August, I embarked"),
]

# Each `{…?}` in the proof → the reading adopted. Context makes every one
# near-certain except the preacher's name, kept as the scan reads it.
READINGS: dict[str, str] = {
    "{prophets?}": "prophets",
    "{to?}": "to",
    "{book?}": "book",
    "{by all?} means.": "by all means",  # and the stray stop after "means"
    "{demon:?}": "demon:",
    "{,?}": ",",
    "{seminaries;?}": "seminaries;",
    "{described?}": "described",
    "{Gess?}": "Gess",
    "{mpt I?}": "mpt I",
    "{the?}": "the",
    "{desire?}": "desire",
    "{years, with?}": "years, with",
    "{in?}": "in",
}

# Printer's errors, fixed in the reflowed text: (as printed, corrected,
# expected count). Broken or dropped type, transposed letters, a dropped
# function word, a stray stop, a scripture reference whose quoted words are
# unambiguously another verse, and a year the narrative's own dates prove.
# Period spellings (shew, intreat, connexion, ancle, exhilirating, assidious,
# befal, unparalled, Weslayan, Stanningly) are hers and stay.
CORRECTIONS: list[tuple[str, str, int]] = [
    ("bnt here", "but here", 1),
    ("morning aud evening", "morning and evening", 1),
    ("whieh is the scavenger", "which is the scavenger", 1),
    ("attacked wirh", "attacked with", 1),
    ("became ustified", "became justified", 1),
    ("heavenly Jesusalem", "heavenly Jerusalem", 1),
    ("a few mo ths", "a few months", 1),
    ("me the re son,", "me the reason,", 1),
    ("Robinson c me", "Robinson came", 1),
    ("M ss Sarah", "Miss Sarah", 1),
    ("no you g man", "no young man", 1),
    ("discernment o the", "discernment of the", 1),
    ("comsists", "consists", 1),
    ("north-eastern par of", "north-eastern part of", 1),
    ("soul an to their", "soul and to their", 1),
    ("as well a His servants", "as well as His servants", 1),
    ("witnessed uch ministers", "witnessed such ministers", 1),
    ("with grea weight", "with great weight", 1),
    ("occurrrd", "occurred", 1),
    ("offendind", "offending", 1),
    ("opportunites", "opportunities", 1),
    ("opportuuity", "opportunity", 1),
    ("conntry", "country", 1),
    ("thoughout", "throughout", 2),
    ("throught that", "thought that", 1),
    ("truimph", "triumph", 1),
    ("propensites", "propensities", 1),
    ("respectabilty", "respectability", 1),
    ("wish to addres the", "wish to address the", 1),
    ("way was en larged", "way was enlarged", 1),
    ("preachin in", "preaching in", 1),
    ("Wesleyau", "Wesleyan", 1),
    ("Newhottle", "Newbottle", 1),  # the Durham pit village beside Rainton/Lumley
    ("Bishop Heading", "Bishop Hedding", 1),  # Elijah Hedding, M.E. bishop in New England
    ("as we not seen", "as we had not seen", 1),
    ("enabled pay it", "enabled to pay it", 1),
    ("unable for speak", "unable to speak", 1),
    ("Philadelphia; and. on entering", "Philadelphia; and on entering", 1),
    ("Heb. ii. 14", "Heb. i. 14", 1),  # ministering spirits: Heb. 1:14
    ("Acts v. 31", "Acts iv. 31", 1),  # the place shaken where they prayed: Acts 4:31
    ("January, 1343", "January, 1844", 1),  # between Dec. 1843 and July 1844
    # A quotation the printer opened with a single mark and closed with a double.
    ("xlviii. 18, 'Oh, that", 'xlviii. 18, "Oh, that', 1),
    # Four quotations the printer never closed; the closing mark goes where
    # the quoted speech plainly ends.
    ("the reason thereof. I further", 'the reason thereof." I further', 1),
    ("your passage money; upon", 'your passage money"; upon', 1),
    ("allow of it at all? Addressing", 'allow of it at all?" Addressing', 1),
    ("very much burdened; her tears", 'very much burdened"; her tears', 1),
]

# Words broken at a line end whose hyphen is part of the word. Every other
# line-end hyphen is a printer's break and is closed up, unless the hyphenated
# form occurs elsewhere in the book mid-line ("Lord's-day", "camp-meeting").
_KEEP_HYPHEN = {"self", "class", "target", "angel"}

_PREFIX = re.compile(r"^(¶ |  |V )(.*)$")


def _proof_lines() -> list[tuple[str, str]]:
    out = []
    for n, line in enumerate(DATA.read_text(encoding="utf-8").splitlines(), start=1):
        if line.startswith("## "):
            continue
        m = _PREFIX.match(line)
        if not m:
            raise CommandError(f"pages.txt line {n}: no ¶/V/continuation prefix")
        out.append((m.group(1), m.group(2).strip()))
    return out


def _resolve_readings(text: str) -> str:
    for marked, reading in READINGS.items():
        if marked not in text:
            raise CommandError(f"reading {marked!r} not found in the proof")
        text = text.replace(marked, reading)
    left = re.findall(r"\{[^}]*\}", text)
    if left:
        raise CommandError(f"unsettled proof readings: {left}")
    return text


def _blocks(lines: list[tuple[str, str]]) -> list[tuple[str, object]]:
    """Reflow printed lines into ("p", text) paragraphs and ("v", [lines]) verse."""
    flat = " ".join(t for _, t in lines)
    mid_line_hyphened = {w.lower() for w in re.findall(r"[A-Za-z']+-[A-Za-z']+", flat)}

    def join(prev: str, nxt: str) -> str:
        if prev.endswith("—"):
            return prev + nxt
        m = re.search(r"([A-Za-z']+)-$", prev)
        if not m:
            return prev + " " + nxt
        head = m.group(1)
        tail = re.match(r"[A-Za-z']*", nxt).group(0)
        if (
            head.lower() in _KEEP_HYPHEN
            or f"{head}-{tail}".lower() in mid_line_hyphened
            or tail[:1].isupper()
        ):
            return prev + nxt
        return prev[:-1] + nxt

    blocks: list[list] = []
    for prefix, text in lines:
        cur = blocks[-1] if blocks else None
        if prefix == "V ":
            if cur is None or cur[0] != "v":
                blocks.append(["v", []])
            blocks[-1][1].append(text)
        elif prefix == "¶ " or cur is None or cur[0] == "v":
            blocks.append(["p", text])
        else:
            cur[1] = join(cur[1], text)
    return blocks


_PARA_SEP, _VERSE_SEP = "\u0000", "\u0001"


def _correct(blocks: list[tuple[str, object]]) -> list[tuple[str, object]]:
    flat = _PARA_SEP.join(v if k == "p" else _VERSE_SEP.join(v) for k, v in blocks)
    flat = _resolve_readings(flat)
    for wrong, right, n in CORRECTIONS:
        found = flat.count(wrong)
        if found != n:
            raise CommandError(f"correction {wrong!r}: expected {n}, found {found}")
        flat = flat.replace(wrong, right)
    parts = flat.split(_PARA_SEP)
    return [
        (k, p if k == "p" else p.split(_VERSE_SEP))
        for (k, _), p in zip(blocks, parts, strict=True)
    ]


# A single mark opens a quotation only at the start of a line or after a space
# or a bracket; everywhere else it is an apostrophe or a closing mark —
# including after a blanked name's dash ("Mr. W——'s").
_OPEN_SINGLE = re.compile(r"(^|[\s(])'")


def _text(value: str) -> str:
    curled = _OPEN_SINGLE.sub("\\1\u2018", value).replace("'", "\u2019")
    return html.escape(curled, quote=False)


def _html(kind: str, value) -> str:
    if kind == "p":
        return f"<p>{_text(value)}</p>"
    return "<blockquote>" + "<br/>".join(_text(x) for x in value) + "</blockquote>"


def _chapters() -> list[tuple[str, str]]:
    blocks = _correct(_blocks(_proof_lines()))
    starts = [0]
    for title, anchor in CHAPTERS[1:]:
        hits = [i for i, (k, v) in enumerate(blocks) if k == "p" and v.startswith(anchor)]
        if len(hits) != 1:
            raise CommandError(f"chapter {title!r}: anchor matched {len(hits)} paragraphs")
        starts.append(hits[0])
    if starts != sorted(starts):
        raise CommandError("chapter anchors are out of document order")
    out = []
    for (title, _), a, b in zip(CHAPTERS, starts, [*starts[1:], len(blocks)], strict=True):
        out.append((title, "".join(_html(k, v) for k, v in blocks[a:b])))
    return out


class Command(BaseCommand):
    help = "Build Zilpha Elaw's Memoirs (1846) from the committed proof (dev DB); then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created_author = Author.objects.get_or_create(
            slug=AUTHOR_SLUG, defaults=AUTHOR_STUB
        )
        if created_author:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": f"https://archive.org/details/{ARCHIVE_ID}",
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": next_order,
            },
        )
        book.chapters.all().delete()

        # The proof is straight-quoted throughout; curl the double marks (`_text`
        # already curled the singles) to the
        # corpus's typographic style, guarded so only quote glyphs move.
        for order, (title, body) in enumerate(chapters, start=1):
            settled = settled_chapter_body(SLUG, order, clean_fragment(body))
            curled, changed = convert(settled, outer_guillemets=False)
            if changed:
                assert_punctuation_only(settled, curled, f"{SLUG}.en[{order}]")
            wc = word_count(curled)
            if wc < 500:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=curled)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
