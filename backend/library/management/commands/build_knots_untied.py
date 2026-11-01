"""Build J. C. Ryle's *Knots Untied* from an Internet Archive scan.

Nineteen papers on the points disputed among Churchmen in Ryle's day — the
Church, the ministry, baptism, regeneration, the Lord's Supper, confession,
worship, the Sabbath — "plain statements on disputed points in religion, from
the standpoint of an Evangelical Churchman". First published 1874.

Neither Gutenberg nor CCEL carries the book, so the source is the OCR of
William Hunt's London printing of 1885 (the tenth edition), the University
of Toronto's copy (`knotsuntied00ryleuoft`) — the one pre-1929 scan on
archive.org — read from ABBYY's XML for its italics, type sizes, small
capitals and indents (see `library.abbyy_book`).

OCR REPAIRS in `data/knots-untied/ocr_fixes.json` were settled by aligning
ABBYY's reading with an independent Tesseract OCR of the same page images
(where the two disagree, the reading that is an English word in its context
wins), and then by checking every doubtful word against the page image.

Fixture-driven (`seed_books` creates it on deploy), idempotent, and no
`catalog.py` entry.

    DJANGO_DEBUG=true uv run python manage.py build_knots_untied
    DJANGO_DEBUG=true uv run python manage.py build_knots_untied --abbyy <saved _abbyy.gz>
"""

from __future__ import annotations

from library.abbyy_book import AbbyyBookCommand


class Command(AbbyyBookCommand):
    help = "Build J. C. Ryle's Knots Untied from its Internet Archive scan (dev DB)."

    SLUG = "knots-untied"
    TITLE = "Knots Untied"
    #: The title page's "Being Plain Statements on Disputed Points in Religion,
    #: from the Standpoint of an Evangelical Churchman", without the participle.
    SUBTITLE = "Plain Statements on Disputed Points in Religion"
    AUTHOR_SLUG = "j-c-ryle"
    COVER_COLOR = "#3f4f63"
    ARCHIVE_ID = "knotsuntied00ryleuoft"
    PUBLICATION_YEAR = 1874
    RUNNING_HEAD = "knots untied"
    #: Scanned larger than Old Paths: a body x-height of 30 px, not 23.
    SCALE = 30 / 23

    DESCRIPTION = (
        "Nineteen plain papers on the questions that divided Churchmen in Ryle’s "
        "day: private judgment, the Articles, baptism and regeneration, the "
        "Lord’s Supper and the Real Presence, the Church, the priest, confession, "
        "worship and the Sabbath. The companion to Old Paths and Practical "
        "Religion, written from the standpoint of an Evangelical Churchman."
    )
    ATTRIBUTION = (
        "Public domain — J. C. Ryle, Knots Untied (London: William Hunt and "
        "Company, 1874). Text from the tenth edition (1885), University of "
        "Toronto copy, digitized by the Internet Archive."
    )

    TITLES = [
        "Preface to the Tenth Edition",
        "Preface",
        "Evangelical Religion",
        "Only One Way of Salvation",
        "Private Judgment",
        "The Thirty-nine Articles",
        "Baptism",
        "Regeneration",
        "Prayer-book Statements about Regeneration",
        "The Lord’s Supper",
        "The Real Presence",
        "The Church",
        "The Priest",
        "Confession",
        "Worship",
        "The Sabbath",
        "Pharisees and Sadducees",
        "Divers and Strange Doctrines",
        "The Fallibility of Ministers",
        "Apostolic Fears",
        "Idolatry",
    ]
    #: The leaf each opens on: the two prefaces, then pages 1, 26, 44 …
    STARTS = [6, 7, 12, 37, 55, 73, 98, 121, 141, 174, 201, 223, 253, 271, 288, 309, 336, 358, 374, 396, 411]
    #: The prefaces (iii–vi) and the papers (1–422); the Contents falls outside.
    LEAVES = [*range(6, 10), *range(12, 434)]
    #: The tenth edition's one-page preface.
    SHORT_CHAPTERS = frozenset({1})
    #: The quotations closing "Prayer-book Statements", in small type under a
    #: rule where footnotes would be.
    EXTRACT_LEAVES = frozenset({170})
    EXTRA_CLEANUP = (
        # The OCR reads this printing's query as "1": "the fact 1 What …"
        (
            r"(?<=[a-z]) 1(?=\s*(?:[\"'”’)—*;]|<i>|[A-Za-z]|$))"
            r"(?! (?:Cor|John|Pet|Peter|Tim|Thess|Kings|Sam|Chron|Ki|Macc)\b)",
            "?",
        ),
        (r"(?<=[a-z])1\?", "?"),  # "time1?"
        (r" ¶ [ft] (?=[\"“A-Z])", "\n\n[note 0] † "),  # a second note run into the first
        (r"(?<=[.,;:!?\"”])[tf](?=\s|$)", ""),  # a dagger read as t or f after a stop
        (r"(?<=\s)(?:[»«™]|•(?! [a-z]))(?=\s)", ""),  # specks
        (r"[!\]]N\"o\b", "No"),
        (r"(?<=[IV]\. )/ <i>", "<i>I "),  # "II. / <i>will show" is "I will show"
        (r"\bX(?=(?:o|ow|ew|ever|ot|or|one|othing|ay)\b)", "N"),  # "Xo", "Xow"
        # a closing quote set off from its stop: '. "(John', '. "—Hooker'
        (r'(?<=[.,;:!?]) "(?=\()', '" '),
        (r'(?<=[.,;:!?]) "(?=—)', '"'),
    )
