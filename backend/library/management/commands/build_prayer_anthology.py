"""Build *Mighty Power in Prayer* — a curated book of twelve Spurgeon sermons.

This is not an ochorus.com scrape and it does not fit a single-work importer:
the book gathers twelve sermons that Spurgeon preached on prayer, drawn from
across the Metropolitan Tabernacle Pulpit and each transcribed cleanly on CCEL.
So it reuses the proven CCEL sermon extractor (``import_sermons.extract``) to
pull each chapter, prepends an editorial Introduction, and writes one ``Book``
row with thirteen chapters.

The book is fixture-driven like every other: ``seed_books`` creates it (with its
chapters and author) on the next deploy straight from
``fixtures/content/books/spurgeon-on-prayer.en.json``. This command exists to
GENERATE that fixture reproducibly — run it, then serialize the row (see the
book-import skill's "write its fixture file yourself" step). It is idempotent:
re-running replaces the book's chapters in the dev DB.

    DJANGO_DEBUG=true uv run python manage.py build_prayer_anthology

The twelve sermons, their sermon numbers and texts were verified against
spurgeongems.org's prayer index and The Spurgeon Library before selection.
"""

from __future__ import annotations

import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_sermons import extract, fetch
from library.models import Author, Book, Chapter

SLUG = "spurgeon-on-prayer"
TITLE = "Mighty Power in Prayer"
SUBTITLE = "Twelve Sermons on Prayer"
AUTHOR_SLUG = "charles-h-spurgeon"
COVER_COLOR = "#312e81"  # deep indigo — house-style cover ground
SORT_ORDER = 46  # appends to the current shelf (max was 45)

DESCRIPTION = (
    "No subject drew more of Charles Spurgeon's fire than prayer. Here are "
    "twelve of his greatest sermons on it, gathered into one volume — from the "
    "boldness of “The Throne of Grace” and the holy argument of "
    "“Order and Argument in Prayer” to the tender comfort of "
    "“Prayer, the Cure for Care.” A school of prayer from the Prince "
    "of Preachers."
)

ATTRIBUTION = (
    "Sermons from the New Park Street Pulpit and the Metropolitan Tabernacle "
    "Pulpit (1860–1888), transcribed by the Christian Classics Ethereal "
    "Library. Introduction © the Ochorus Library."
)

# (chapter title, CCEL leaf URL, expected scripture reference for verification).
# Order IS the reading order and a public contract (PlanDay, saved positions,
# prerendered URLs), arranged in four movements:
#   I.  The ground and boldness of prayer
#   II. How to pray
#   III. Prayer that prevails
#   IV. Prayer for the weary
# (title, CCEL leaf URL, expected scripture prefix). The third field is a
# build-time sanity check only — `extract()` parses the reference from the page,
# and this asserts the RIGHT page loaded (a prefix, since CCEL's scripRef anchor
# is sometimes terser than the verse: "1 John 3" for 3:22–24, "Jude" for 20).
# If a SECOND CCEL anthology is ever added, lift this list into a catalog sidecar
# (cf. `catalog.WEB_CHAPTERS` / `sermon_catalog.SERMONS`) consumed by a shared
# importer, rather than copying this one-off command.
_CCEL = "https://ccel.org/ccel/spurgeon/"
SERMONS: list[tuple[str, str, str]] = [
    # I. The ground and boldness of prayer
    ("The Throne of Grace", _CCEL + "sermons17/sermons17.lvii.html", "Hebrews 4:16"),
    ("The Golden Key of Prayer", _CCEL + "sermons11/sermons11.xiii.html", "Jeremiah 33:3"),
    # II. How to pray
    ("Order and Argument in Prayer", _CCEL + "sermons12/sermons12.iv_1.html", "Job 23:3"),
    ("Ask and Have", _CCEL + "sermons28/sermons28.xlvi.html", "James 4:2"),
    ("The Conditions of Power in Prayer", _CCEL + "sermons19/sermons19.xv.html", "1 John 3"),
    ("Praying in the Holy Spirit", _CCEL + "sermons12/sermons12.lii.html", "Jude"),
    ("Pray Without Ceasing", _CCEL + "sermons18/sermons18.xii.html", "1 Thessalonians 5:17"),
    # III. Prayer that prevails
    ("True Prayer—True Power!", _CCEL + "sermons06/sermons06.xxix_1.html", "Mark 11:24"),
    ("Intercessory Prayer", _CCEL + "sermons18/sermons18.xxii.html", "Psalm 141:5"),
    (
        "The Power of Prayer and the Pleasure of Praise",
        _CCEL + "sermons09/sermons09.xxi.html",
        "2 Corinthians 1:11",
    ),
    # IV. Prayer for the weary
    ("Prayer, the Cure for Care", _CCEL + "sermons40/sermons40.x.html", "Philippians 4:6"),
    ("The Ravens' Cry", _CCEL + "sermons12/sermons12.v.html", "Psalm 147:9"),
]

# Editorial introduction (~1,000 words). Written for Ochorus; sanitized into the
# chapter allowlist on the way in, like every other stored body.
INTRO_HTML = """
<p>Charles Haddon Spurgeon (1834–1892) is remembered as the “Prince of
Preachers,” yet those who knew the Metropolitan Tabernacle best would have
told you that the secret of the pulpit lay somewhere beneath it. When admirers
pressed him for the reason behind his extraordinary influence, Spurgeon is said
to have led them downstairs to a room where hundreds of members were kneeling in
prayer while he preached, and answered simply, “There is my boiler
room.” The heat that warmed thousands in the auditorium above was generated,
he insisted, on the knees of praying people below. The sermons gathered in this
volume come from a man who believed that to the marrow — that prayer is the
true engine of the Christian life — and who preached on it more searchingly,
and far more often, than on almost any other theme.</p>

<p>Out of the hundreds of times Spurgeon opened the Scriptures on prayer, twelve
are gathered here. They were not chosen at random. Each is among his most loved
and most reprinted, and together they form something like a school of prayer:
they teach the trembling beginner how to draw near, they press the seasoned saint
to plead with holy boldness, and they carry the weary sufferer to the only place
where care is truly cured. Spurgeon never treated prayer as a technique to be
mastered. “True prayer,” he says in one of these sermons, “is an
approach of the soul by the Spirit of God to the throne of God.” It is not
the utterance of words, nor the beauty of the phrases, but the movement of a
living heart toward a living God — and that is a thing the plainest Christian
can do as well as the most eloquent.</p>

<p>The book is arranged in four movements, and it may help the reader to see the
shape of the whole before beginning.</p>

<p><strong>First, the ground and boldness of prayer.</strong> The opening two
sermons lay the foundation. “The Throne of Grace” dwells on the
astonishing invitation to “come boldly” to a King whose very throne is
made of grace; “The Golden Key of Prayer” unlocks the great promise,
“Call unto me, and I will answer thee.” Here Spurgeon settles the
question that silences most prayer before it begins: whether God will hear us at
all. He answers with both hands full.</p>

<p><strong>Second, how to pray.</strong> The heart of the book is intensely
practical. “Order and Argument in Prayer” shows the saint filling his
mouth with arguments and reasoning his case before God, as Job longed to do.
“Ask and Have” confronts the reason so many of us live spiritually
empty — “ye have not, because ye ask not.” “The Conditions of
Power in Prayer” and “Praying in the Holy Spirit” turn to the
abiding life and the Spirit’s help without which no prayer rises higher than
the ceiling. “Pray Without Ceasing” gathers it all into a life of
unbroken communion, prayer becoming as natural and constant as breath.</p>

<p><strong>Third, prayer that prevails.</strong> Spurgeon believed, without
embarrassment, that prayer moves the arm that moves the world. “True
Prayer—True Power!” links believing prayer to real spiritual might;
“Intercessory Prayer” turns the praying heart outward to plead for
others, as our great High Priest ever lives to do; and “The Power of Prayer
and the Pleasure of Praise” binds asking and thanksgiving together, so that
the church which begs on its knees also sings on its feet.</p>

<p><strong>Fourth, prayer for the weary.</strong> The book closes tenderly.
“Prayer, the Cure for Care” takes Paul’s remedy for anxiety —
“be careful for nothing; but in everything by prayer” — and presses
it into the reader’s trembling hands. And “The Ravens’ Cry”
ends where prayer so often begins: not with polished words at all, but with the
instinctive cry of a needy creature, which the God who feeds the young ravens
never fails to hear. It is a fitting last word, for it puts prayer within reach
of the most stammering soul in the room.</p>

<p>It is worth remembering that Spurgeon preached none of this from a distance.
The man who urged his people to pray without ceasing rose early to pray over his
sermons, bathed every service in the intercession of the church, and traced the
great Tabernacle awakening not to his own gifts but to praying knees. He knew,
too, the harder side of the praying life — long seasons of depression,
petitions that seemed to go unanswered, and the private struggle to keep praying
when all feeling had drained away. That is why these sermons never scold. They
come from a fellow pilgrim who had found the throne of grace to be exactly what
its name promises, and who could not rest until he had led others to kneel
there beside him.</p>

<p>A word about the sermons themselves. They were preached to Victorian
congregations, most of them between 1860 and 1888, and they carry the cadence of
that pulpit — the long sentences, the vivid illustrations, the sudden
turns to direct appeal. Nothing has been modernized or abridged; the text is
Spurgeon’s own, transcribed from the printed Pulpit volumes. Readers new to
him will find that a little patience is richly repaid, for beneath the older
style beats a pastor’s heart that is startlingly close to our own
struggles. He knew dry seasons, unanswered petitions, and the temptation to give
up praying, and he speaks to all of them.</p>

<p>Spurgeon would not have wanted this book to be merely read. “Let us
pray” were words he came back to again and again, not as a formula but as a
summons. The best way to honor these sermons is to close the book at intervals
and do the very thing they commend. Read one sermon; then pray. Read another;
then pray again. If, by the time the last page is turned, prayer has become less
of a duty and more of a delight, the volume will have served its purpose —
and its author, now these many years “with Christ, which is far better,”
would count it joy.</p>

<p><em>— The Ochorus Library</em></p>
"""


class Command(BaseCommand):
    help = "Build the curated Spurgeon prayer anthology (dev DB); then serialize the fixture."

    @transaction.atomic  # a mid-run abort rolls back, never a partial book
    def handle(self, *args, **opts):
        try:
            author = Author.objects.get(slug=AUTHOR_SLUG)
        except Author.DoesNotExist:
            raise CommandError(
                f"Author {AUTHOR_SLUG!r} is not in this database — run "
                "`manage.py seed_if_empty` first."
            )
        # Content fields refresh on every rebuild; the workflow-owned fields
        # (source_type, is_published, sort_order) are create-only so a rebuild
        # can't walk back a review/unpublish (backend/CLAUDE.md).
        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "cover_color": COVER_COLOR,
            "source_url": "",
        }
        book, created = Book.objects.update_or_create(
            slug=SLUG,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                "is_published": True,
                "sort_order": SORT_ORDER,
            },
        )
        book.chapters.all().delete()

        # Chapter 1: the editorial Introduction. `settled_chapter_body` is the
        # canonical "chapter body as stored" form (corrections + trailing-page
        # strip) that the deploy re-applies — build the fixture in it so seeds
        # don't churn. `word_count` is derived by Chapter.save(), so it is not
        # passed; the local is only for the log line.
        intro = settled_chapter_body(SLUG, 1, clean_fragment(INTRO_HTML))
        Chapter.objects.create(book=book, order=1, title="Introduction", body_html=intro)
        self.stdout.write(f"  ch 1: Introduction ({word_count(intro)} words)")

        # Chapters 2–13: the twelve sermons, pulled clean from CCEL.
        for i, (title, url, want_ref) in enumerate(SERMONS, start=2):
            time.sleep(0.8)  # be polite to CCEL
            body, ref, _preached = extract(fetch(url))
            body = settled_chapter_body(SLUG, i, body)
            wc = word_count(body)
            if wc < 500:
                raise CommandError(f"{title!r}: only {wc} words — aborted ({url})")
            flag = "" if ref.startswith(want_ref) else f"  ⚠ ref {ref!r} != expected {want_ref!r}"
            Chapter.objects.create(book=book, order=i, title=title, body_html=body)
            self.stdout.write(f"  ch {i:2}: {title[:44]:44} {ref:22} {wc:>6} words{flag}")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
