"""Build A. B. Simpson's *The Holy Spirit; or, Power from on High* — Part II,
The New Testament (1896).

The second of the work's two volumes: twenty-eight chapters tracing the Holy
Spirit book by book from Matthew to Revelation, first given as Sunday messages
at the Gospel Tabernacle in New York. Public domain (Simpson d. 1919; the
volume appeared in 1896).

SOURCE. SermonIndex carries the whole volume one chapter to a page, as clean
transcribed text — far cleaner than the only scans, which are the Christian
Publications "new edition from new plates" (Internet Archive
`holyspiritorpowe0002reva`, `cihm_24366`). Checked against that scan: the
SermonIndex text is the printed text word for word apart from the scan's own
page furniture (diff ratio 0.91 on chapter II, every difference a running head,
page number or OCR smear). The chapters come off SermonIndex through the sermon
importer's transcript extractor; the short Preface to Volume II, which
SermonIndex does not carry, is set here from the scan (its "(now the Alliance
Weekly)" is that later edition's own insertion and is kept as printed).

Chapter titles are the volume's Contents, without its parenthetical book names
("(Matthew)", "(Acts)") — the chapter's opening text names its book anyway.
OCR slips in the SermonIndex text are repaired in `corrections.py`.

SermonIndex also lists two empty placeholder pages in the run ("22. GOD",
"27. THE SPIRIT"); the chapters below name the real pages.

Fixture-driven like every other book: `seed_books` creates it on deploy from
`fixtures/content/books/power-from-on-high-new-testament.en.json`, resolving the
existing `a-b-simpson` author. No `catalog.py` entry, so no importer can
re-chapter it. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_power_from_on_high
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_sermons import extract_sermonindex, fetch
from library.models import Author, Book, Chapter

SLUG = "power-from-on-high-new-testament"
AUTHOR_SLUG = "a-b-simpson"
TITLE = "The Holy Spirit, or Power from on High"
SUBTITLE = "Part II: The New Testament"
PUBLICATION_YEAR = 1896
COVER_COLOR = "#7a3b2e"
SOURCE_URL = "https://archive.org/details/holyspiritorpowe0002reva"
ATTRIBUTION = (
    "Public domain — Part II first published 1896 by the Christian Alliance "
    "Publishing Co., New York. Text from SermonIndex, checked against the "
    "Christian Publications \"new edition from new plates\" (Internet Archive)."
)
DESCRIPTION = (
    "The second volume of Simpson's great study of the Holy Spirit, tracing the "
    "Spirit through the New Testament from the Gospels to the last message of "
    "Revelation. Chapter by chapter he shows the Spirit in the life of Jesus, the "
    "promise of the Comforter, the waiting and the outpouring at Pentecost, and "
    "the Spirit's work in every epistle — calling the reader past doctrine to be "
    "filled with the Spirit for holiness and service. First given as Sunday "
    "messages at the Gospel Tabernacle in New York."
)

_SI = "https://sermonindex.net/speakers/ab-simpson/"

#: (title, SermonIndex page slug), in the volume's Contents order.
CHAPTERS = [
    ("The Holy Spirit in the Life of the Lord Jesus Christ",
     "power-from-on-high-1-the-holy-spirit-in-the-life-of-the-lord-jesus-christ"),
    ("The Baptism with the Holy Ghost",
     "power-from-on-high-2-the-baptism-with-the-holy-ghost"),
    ("The Wise and Foolish Virgins",
     "power-from-on-high-3-the-wise-and-foolish-virgins-or-the-holy-spirit-and-the-com"),
    ("The Parable of the Pounds, or Power for Service",
     "power-from-on-high-4-the-parable-of-the-pounds-or-power-for-service"),
    ("The Holy Ghost in the Gospel of John",
     "power-from-on-high-5-the-holy-ghost-in-the-gospel-of-john"),
    ("The Comforter", "power-from-on-high-6-the-comforter"),
    ("Waiting for the Spirit", "power-from-on-high-7-waiting-for-the-spirit"),
    ("Power from on High", "power-from-on-high-8-power-from-on-high"),
    ("Filled with the Spirit", "power-from-on-high-9-filled-with-the-spirit"),
    ("The Holy Spirit in the Epistle to the Romans",
     "power-from-on-high-10-the-holy-spirit-in-the-epistle-to-the-romans"),
    ("The Holy Spirit in the First Epistle to the Corinthians",
     "power-from-on-high-11-the-holy-spirit-in-the-first-epistle-to-the-corinthians"),
    ("The Holy Spirit in the Body of Christ",
     "power-from-on-high-12-the-holy-spirit-in-the-body-of-christ"),
    ("The Holy Spirit in Second Corinthians",
     "power-from-on-high-13-the-holy-spirit-in-second-corinthians"),
    ("The Holy Spirit in Galatians", "power-from-on-high-14-the-holy-spirit-in-galatians"),
    ("All the Blessings of the Spirit",
     "power-from-on-high-15-all-the-blessings-of-the-spirit-or-the-holy-ghost-in-ephes"),
    ("The Holy Spirit in Philippians", "power-from-on-high-16-the-holy-spirit-in-philippians"),
    ("The Spirit of Love", "power-from-on-high-17-the-spirit-of-love"),
    ("The Holy Spirit in Thessalonians",
     "power-from-on-high-18-the-holy-spirit-in-thessalonians"),
    ("The Holy Spirit in the Epistles of Paul to Timothy",
     "power-from-on-high-19-the-holy-spirit-in-the-epistles-of-paul-to-timothy"),
    ("Regeneration and Renewal", "power-from-on-high-20-regeneration-and-renewal"),
    ("The Holy Spirit in the Epistle to the Hebrews",
     "power-from-on-high-21-the-holy-spirit-in-the-epistle-to-the-hebrews"),
    ("God's Jealous Love", "power-from-on-high-22-gods-jealous-love"),
    ("The Holy Spirit in the Epistles of Peter",
     "power-from-on-high-23-the-holy-spirit-in-the-epistles-of-peter"),
    ("The Holy Spirit in the First Epistle of John",
     "power-from-on-high-24-the-holy-spirit-in-the-first-epistle-of-john"),
    ("The Holy Spirit in Jude", "power-from-on-high-25-the-holy-spirit-in-jude"),
    ("The Sevenfold Holy Ghost", "power-from-on-high-26-the-sevenfold-holy-ghost"),
    ("The Spirit's Message to the Churches",
     "power-from-on-high-27-the-spirits-message-to-the-churches"),
    ("The Holy Spirit's Last Message", "power-from-on-high-28-the-holy-spirits-last-message"),
]

#: The Preface to Volume II, set from the scan (SermonIndex does not carry it):
#: line-end hyphens rejoined, one OCR slip ("searcely") read as printed.
PREFACE = """\
<p>In issuing the second volume of the Holy Spirit or Power from on High, after \
an interval of a year since the publication of the first volume, the author is \
deeply conscious of the imperfections of his work. In view of the vastness and \
grandeur of the theme, he asks the kind indulgence of his readers and friends, \
and begs them to remember that these chapters are the substance of his weekly \
pulpit ministrations amid the pressure of a life of almost overwhelming work \
and care.</p>\
<p>He is, however, encouraged by the numerous letters that have come from those \
who have read these messages in the weekly columns of the Christian Alliance \
(now the Alliance Weekly), to believe that they have often been bread for \
God's hungry children. He is reassured by the humble consciousness that he is \
not attempting to minister entertainment or instruction for the wise, the \
scholarly and the critical, but to provide simple and satisfying bread for the \
King's children.</p>\
<p>He need scarcely say that this sublime theme has continually grown upon him \
during the two years that it has been the subject of his regular pulpit \
ministrations, and that, although he has now been able to complete the survey \
of the whole sacred volume in unfolding this theme, he feels, at the close, as \
if he were only standing upon the shore of an infinite ocean of truth and love, \
without a fathoming line or a shore.</p>\
<p>He would humbly commend these pages to the blessing of God and the earnest \
prayers of his friends, that this volume may be used for the honor of the Holy \
Spirit and the deepening of the interest of God's people in this great theme \
which, happily today, is occupying the profoundest attention of the church of \
God, and which, perhaps more than any other, is the "present truth" which God \
is pressing upon the attention of His people in these last days.</p>\
<p>The first edition of Volume I having been quite exhausted, another large \
edition is being rapidly pushed through the press.</p>\
<p>New York, April 1, 1896.</p>"""

#: A chapter shorter than this is a placeholder page, not the chapter.
_MIN_WORDS = 1500


class Command(BaseCommand):
    help = "Build Simpson's Power from on High, Part II (New Testament) from SermonIndex."

    @transaction.atomic
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"author {AUTHOR_SLUG!r} not in the DB — loaddata authors.json first."
            ) from None

        chapters = [("Preface to Volume II", PREFACE)]
        for title, page in CHAPTERS:
            body = extract_sermonindex(fetch(_SI + page + "/"), title)
            if word_count(body) < _MIN_WORDS:
                raise CommandError(f"{page}: only {word_count(body)} words — aborted.")
            chapters.append((title, body))

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": COVER_COLOR,
            "source_url": SOURCE_URL,
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, was_created = Book.objects.update_or_create(
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

        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:58]:58} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"
        ))
