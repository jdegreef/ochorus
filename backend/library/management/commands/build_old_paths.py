"""Build J. C. Ryle's *Old Paths* (1877) from an Internet Archive scan.

Neither Gutenberg nor CCEL carries the book, so the source is the OCR of
William Hunt's London printing of 1878, Princeton Theological Seminary's copy
(`oldpathsbeingpla00ryle`) — the one pre-1929 scan on archive.org — read from
ABBYY's XML for its italics, type sizes, small capitals and indents (see
`library.abbyy_book`).

OCR REPAIRS in `data/old-paths/ocr_fixes.json` were settled by aligning
ABBYY's reading with an independent Tesseract OCR of the same page images
(where the two disagree, the reading that is an English word in its context
wins), and then by checking every doubtful word against the page image.

Fixture-driven (`seed_books` creates it on deploy), idempotent, and no
`catalog.py` entry.

    DJANGO_DEBUG=true uv run python manage.py build_old_paths
    DJANGO_DEBUG=true uv run python manage.py build_old_paths --abbyy <saved _abbyy.gz>
"""

from __future__ import annotations

from library.abbyy_book import AbbyyBookCommand


class Command(AbbyyBookCommand):
    help = "Build J. C. Ryle's Old Paths from its Internet Archive scan (dev DB)."

    SLUG = "old-paths"
    TITLE = "Old Paths"
    #: The title page's "Being Plain Statements on Some of the Weightier
    #: Matters of Christianity", without the participle.
    SUBTITLE = "Plain Statements on Some of the Weightier Matters of Christianity"
    AUTHOR_SLUG = "j-c-ryle"
    COVER_COLOR = "#5b4a3a"
    ARCHIVE_ID = "oldpathsbeingpla00ryle"
    PUBLICATION_YEAR = 1877
    RUNNING_HEAD = "old paths"

    DESCRIPTION = (
        "Nineteen plain papers on the truths Ryle held “necessary to salvation”: "
        "the inspiration of Scripture, the soul, sin, forgiveness, justification, "
        "the cross, the Holy Ghost, conversion, faith and repentance, Christ’s "
        "invitation and intercession, election and perseverance. The doctrinal "
        "companion to Practical Religion and Knots Untied, it presses each truth "
        "home as a question the reader must answer for himself."
    )
    ATTRIBUTION = (
        "Public domain — J. C. Ryle, Old Paths (London: William Hunt and Company; "
        "preface dated October 1877). Text from the 1878 printing, Princeton "
        "Theological Seminary Library copy, digitized by the Internet Archive."
    )

    #: The papers, as headed in the text (the Contents drops their stops).
    TITLES = [
        "Preface",
        "Inspiration",
        "Our Souls!",
        "Few Saved!",
        "Our Hope!",
        "Alive or Dead?",
        "Our Sins!",
        "Forgiveness",
        "Justification!",
        "The Cross of Christ",
        "The Holy Ghost",
        "Having the Spirit",
        "Conversion",
        "The Heart",
        "Christ’s Invitation",
        "Faith!",
        "Repentance",
        "Christ’s Power to Save",
        "Election",
        "Perseverance",
    ]
    #: The leaf each opens on: the Preface, then pages 1, 40, 64 …
    STARTS = [11, 19, 58, 82, 111, 139, 168, 197, 229, 257, 281, 309, 340, 358, 376, 394, 421, 454, 476, 494]
    #: The Preface (v–x) and the papers (1–521); the Contents and colophon fall outside.
    LEAVES = [*range(11, 17), *range(19, 540)]
    #: Ryle's extracts after "Inspiration" and "Justification", in small type
    #: where footnotes would be.
    EXTRACT_LEAVES = frozenset({53, 256})
    UNMARKED_NOTES = {12: "To this statement", 504: '"As Christ being'}
    NOT_A_NOTE = {477: "He that go"}
    #: "Note referred to at page 487", closing "Perseverance".
    CLOSING_NOTE = (536, "Note")
    MARK_NOISE = (r"(?<=power\.) f(?= \()",)
    EXTRA_CLEANUP = (
        (
            r"Treatise on</i> J\S{5,30}\.—Johnstone.s Edition of Owens Works\.",
            "Treatise on Justification</i>.—Johnstone's Edition of Owen's Works.",
        ),
    )
