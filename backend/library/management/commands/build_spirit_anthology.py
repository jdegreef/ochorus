"""Build *Spurgeon on the Holy Spirit* — a curated book of twelve Spurgeon sermons.

The second CCEL sermon anthology after *Mighty Power in Prayer*
(``build_prayer_anthology``), built the same way: each chapter is one sermon
pulled clean through the CCEL sermon extractor (``import_sermons.extract``),
behind an editorial Introduction, written as one ``Book`` row.

SOURCE CHOICE — only the GENUINE printed text. CCEL's Spurgeon volumes are not
one transcription. The early New Park Street volumes and a scattering of later
sermons carry the Pulpit as printed; most sermons from about 1862 on carry a
later digital text that silently modernised the Authorised Version Spurgeon
quoted ("whereby you are sealed" for "whereby ye are sealed", "He that believes
on Me, as the Scripture has said" for "believeth … hath said"). That is the
modernised-scripture trap the book-import skill warns about, so every candidate
was screened by KJV-archaism density (thee/thou/ye/hath/unto/… per 10k words,
and -eth verbs): the twelve below run 30–171 archaisms per 10k, and every one
but No. 251 (62 archaisms, few -eth verbs) runs 14–50 -eth verbs; the modernised
texts run under ~20 and ~0, and their epigraphs read "you"/"has" where the AV
reads "ye"/"hath". Each epigraph was then checked word for word against the
KJV. That screen is why the famous later sermons ("The Pentecostal Wind and
Fire", No. 1619; "The Covenant Promise of the Spirit", No. 2200; "Grieve Not the
Holy Spirit", No. 738) are not here: CCEL holds them only in the modernised
text. Ezekiel 36:27 still opens the second movement — No. 251, "The Necessity
of the Spirit's Work", is on the same text — and No. 278 stands for No. 738.

    DJANGO_DEBUG=true uv run python manage.py build_spirit_anthology

Sermon numbers and dates (Metropolitan Tabernacle / New Park Street Pulpit):
  No. 4     1855-01-21  The Personality of the Holy Ghost      John 14:16-17
  No. 5     1855-01-21  The Comforter                          John 14:26
  No. 50    1855-11-18  The Holy Ghost—The Great Teacher       John 16:13
  No. 251   1859-05-08  The Necessity of the Spirit's Work     Ezekiel 36:27
  No. 999   1871-07-09  The Withering Work of the Spirit       1 Peter 1:23-25
  No. 1435  1878-04-14  Adoption—The Spirit and the Cry        Galatians 4:6
  No. 178   1858        The Work of the Holy Spirit            Galatians 3:3
  No. 1532  1880-04-11  The Holy Spirit's Intercession         Romans 8:26-27
  No. 278   1859-10-09  Grieving the Holy Spirit               Ephesians 4:30
  No. 30    1855-06-17  The Power of the Holy Ghost            Romans 15:13
  No. 201   1858-06-20  The Outpouring of the Holy Spirit      Acts 10:44
  No. 1918  1886-09-05  The Abiding of the Spirit the Glory of the Church
                                                               Haggai 2:4-5
"""

from __future__ import annotations

import re
import time

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.management.commands.import_sermons import extract, fetch
from library.models import Author, Book, Chapter
from library.quote_marks import convert_work

SLUG = "spurgeon-on-the-holy-spirit"
TITLE = "Spurgeon on the Holy Spirit"
SUBTITLE = "Twelve Sermons on the Holy Spirit"
AUTHOR_SLUG = "charles-h-spurgeon"
COVER_COLOR = "#7c2d12"  # ember — the fire of Pentecost

DESCRIPTION = (
    "Charles Spurgeon believed a church without the Holy Spirit was a body "
    "without breath. Here are twelve of his sermons on the Spirit, gathered "
    "into one volume — from “The Personality of the Holy Ghost,” "
    "preached in the first month of his printed Pulpit, through “The Withering Work of "
    "the Spirit” and “The Holy Spirit's Intercession” to "
    "“The Abiding of the Spirit the Glory of the Church.” Who the "
    "Spirit is, and what he does, from the Prince of Preachers."
)

ATTRIBUTION = (
    "Sermons from the New Park Street Pulpit and the Metropolitan Tabernacle "
    "Pulpit (1855–1886), transcribed by the Christian Classics Ethereal "
    "Library. Introduction © the Ochorus Library."
)

# The book page's grounded Q&A (FAQPage JSON-LD) — every answer rests on the
# sermons in this volume, never on outside claims about them.
QA: list[dict[str, str]] = [
    {
        "question": "What is Spurgeon on the Holy Spirit about?",
        "answer": (
            "It is a collection of twelve of Charles Spurgeon's sermons on the Holy Spirit, "
            "gathered into one volume. Arranged in four movements — who the Spirit is, his work "
            "in salvation, his work in the believer, and his power in the church — they teach "
            "that the Spirit is a divine Person, and that every true conversion, every true "
            "prayer and every true revival is his work."
        ),
    },
    {
        "question": "Who was Charles Spurgeon?",
        "answer": (
            "Charles Haddon Spurgeon (1834–1892) was the most famous English preacher of the "
            "nineteenth century, the 'Prince of Preachers,' pastor of New Park Street Chapel and "
            "then the Metropolitan Tabernacle in London. His sermons were printed weekly from "
            "1855, and the Holy Spirit was a theme he returned to from the first weeks of that "
            "printed ministry to the end of his life."
        ),
    },
    {
        "question": "Does Spurgeon teach that the Holy Spirit is a person?",
        "answer": (
            "Yes, emphatically. 'The Personality of the Holy Ghost,' preached in January 1855 "
            "on John 14:16–17, opens the book by insisting that the Spirit is not a mere "
            "influence or power but a Person, truly God, who is to be loved, trusted and "
            "worshipped — and who can be grieved, as the sermon 'Grieving the Holy Spirit' "
            "warns from Ephesians 4:30."
        ),
    },
    {
        "question": "What is 'The Withering Work of the Spirit' about?",
        "answer": (
            "It is one of Spurgeon's most searching sermons. From the picture of grass that "
            "withers when the breath of the Lord blows upon it, he shows that the Spirit first "
            "humbles a person — withering their confidence in their own goodness — before the "
            "incorruptible seed of the Word takes root and makes them new."
        ),
    },
    {
        "question": "What does Spurgeon say about the Spirit and prayer?",
        "answer": (
            "In 'The Holy Spirit's Intercession,' on Romans 8:26–27, he comforts believers who "
            "do not know how to pray: the Spirit helps their infirmities and intercedes for them "
            "with groanings that cannot be uttered. 'The Outpouring of the Holy Spirit' urges "
            "the church to pray for the Spirit to fall upon its preaching as he fell while Peter "
            "was still speaking."
        ),
    },
    {
        "question": "Is the text modernised or abridged?",
        "answer": (
            "No. The sermons are given as they were printed in the New Park Street and "
            "Metropolitan Tabernacle Pulpit, with the Authorised Version that Spurgeon quoted. "
            "They were chosen from transcriptions of the original printed text, not from later "
            "editions that updated his Scripture quotations into modern English."
        ),
    },
    {
        "question": "Where should a reader begin?",
        "answer": (
            "Each sermon stands complete on its own, so any of them is a fair start. 'The "
            "Personality of the Holy Ghost' lays the foundation for the rest, while 'The Holy "
            "Spirit's Intercession' and 'The Comforter' are the gentlest places to begin for "
            "a reader who comes looking for comfort."
        ),
    },
]

# (chapter title, CCEL leaf URL, expected scripture prefix). Order IS the
# reading order and a public contract (saved positions, prerendered URLs),
# arranged in four movements:
#   I.   Who the Spirit is
#   II.  The Spirit's work in salvation
#   III. The Spirit in the believer
#   IV.  The Spirit's power in the church
# The prefix is a build-time check that the RIGHT page loaded; "" where the
# page's epigraph carries no scripRef anchor (No. 251 — fixed up below).
_CCEL = "https://ccel.org/ccel/spurgeon/"
SERMONS: list[tuple[str, str, str]] = [
    # I. Who the Spirit is
    ("The Personality of the Holy Ghost", _CCEL + "sermons01/sermons01.iv.html", "John 14:16"),
    ("The Comforter", _CCEL + "sermons01/sermons01.v.html", "John 14:26"),
    ("The Holy Ghost—The Great Teacher", _CCEL + "sermons01/sermons01.xlvii.html", "John 16:13"),
    # II. The Spirit's work in salvation
    ("The Necessity of the Spirit's Work", _CCEL + "sermons05/sermons05.xxviii.html", ""),
    ("The Withering Work of the Spirit", _CCEL + "sermons17/sermons17.xxxii.html", "1 Peter 1:23"),
    ("Adoption—The Spirit and the Cry", _CCEL + "sermons24/sermons24.ii_1.html", "Galatians 4:6"),
    # III. The Spirit in the believer
    ("The Work of the Holy Spirit", _CCEL + "sermons04/sermons04.xiv.html", "Galatians 3:3"),
    ("The Holy Spirit's Intercession", _CCEL + "sermons26/sermons26.viii.html", "Romans 8:26"),
    ("Grieving the Holy Spirit", _CCEL + "sermons05/sermons05.liii.html", "Ephesians 4:30"),
    # IV. The Spirit's power in the church
    ("The Power of the Holy Ghost", _CCEL + "sermons01/sermons01.xxix.html", "Romans 15:13"),
    ("The Outpouring of the Holy Spirit", _CCEL + "sermons04/sermons04.xxxvii.html", "Acts 10:44"),
    (
        "The Abiding of the Spirit the Glory of the Church",
        _CCEL + "sermons32/sermons32.xi_1.html",
        "Haggai 2:4",
    ),
]

# Transcription slips and page furniture in the CCEL text, keyed by chapter
# order (the Introduction is 1). Each is unambiguous against the printed Pulpit:
FIXUPS: dict[int, list[tuple[str, str]]] = {
    # The closing hymn verse arrives one <p> per line; set it as one stanza.
    3: [
        ("You feel like Hurcules,", "You feel like Hercules,"),
        # A quotation closed with an opener (QuoteStyleTests' mispaired gate).
        ("another <i>Comforter.</i>“ However", "another <i>Comforter.</i>” However"),
        ("exemption here. ”<i>Whosoever</i>", "exemption here. “<i>Whosoever</i>"),
        ("Let you soul answer.", "Let your soul answer."),
        ("shall have ever iniquity blotted out", "shall have every iniquity blotted out"),
        (
            "<p>“We have listened to the preacher—</p><p>Truth by him has now been "
            "shown;</p><p>But we want a GREATER TEACHER,</p><p>From the everlasting "
            "throne;</p><p>APPLICATION</p><p>Is the work of God alone.”</p>",
            "<p>“We have listened to the preacher—<br/>Truth by him has now been "
            "shown;<br/>But we want a GREATER TEACHER,<br/>From the everlasting "
            "throne;<br/>APPLICATION<br/>Is the work of God alone.”</p>",
        ),
    ],
    4: [("guide you <i>into</i>“—mark that word", "guide you <i>into</i>”—mark that word")],
    # No. 251's epigraph has no scripRef anchor, so the extractor kept it as a
    # plain paragraph (and the comma in "Ezekiel, 36:27" is a typesetting slip).
    5: [
        (
            "<p>“And I will put my Spirit within you.”—Ezekiel, 36:27.</p>",
            "<blockquote>“And I will put my Spirit within you.”—Ezekiel 36:27.</blockquote>",
        ),
    ],
    # Letter slips: a doubled opener ("written: ”‘Whosoever"), dropped or
    # misread letters, and "facings" for the "fadings" of Isaiah 40's flower.
    6: [
        ("it is written: ”‘Whosoever", "it is written: “Whosoever"),
        ("must be fufilled", "must be fulfilled"),
        ("the righteousuess which", "the righteousness which"),
        ("shall not be atonished", "shall not be astonished"),
        ("witherings and facings occur", "witherings and fadings occur"),
    ],
    8: [("the most punctillious of", "the most punctilious of")],
    # No. 1532 is a different typist's text: single quotes throughout (kept —
    # consistent within the sermon), and every em dash keyed as ’ (repaired by
    # _DASH_AS_APOSTROPHE below). The epigraph transposes two pairs of words
    # (Romans 8:26-27 AV: "what we should pray for", "according to the will"),
    # and Watts's couplet reads "the break" for "they break".
    9: [
        ("for we know not what we should what pray for", "for we know not what we should pray for"),
        ("according the to will of God.’Romans", "according to the will of God.’—Romans"),
        ("READ BEFORE SERMON’Romans", "READ BEFORE SERMON—Romans"),
        ("concerning our great Father:’ </p>", "concerning our great Father:— </p>"),
        (
            "<p>‘He knows the thoughts we mean to speak,</p><p>Ere from our opening lips the break.’</p>",
            "<p>‘He knows the thoughts we mean to speak,<br/>Ere from our opening lips they break.’</p>",
        ),
        ("he feels greenings which", "he feels groanings which"),
    ],
    10: [
        ("my brethen, at", "my brethren, at"),
        ("from all these cervices.", "from all these services."),
    ],
    12: [
        ("beyond all moralsuasion.", "beyond all moral suasion."),
        ("for an inaminate corpse", "for an inanimate corpse"),
    ],
    13: [
        ("to bestir themelves to", "to bestir themselves to"),
        ("the final perserverance of", "the final perseverance of"),
    ],
}

# No. 1532 only: ’ standing between a word and the next with no space, where
# the next is not a contraction tail ("Spirit’s", "don’t") — "sonship,’for
# saith he", "comfort’namely", "omniscience’what". All fourteen are em dashes.
_DASH_AS_APOSTROPHE = (9, re.compile(r"(?<=[A-Za-z,!:.;?])’(?=(?!(?:s|t|d|ll|re|ve|m)\b)[a-z])"))

# The service's hymn numbers ("HYMNS FROM 'OUR OWN HYMN BOOK'—728, 468, 221")
# are order-of-service furniture, not sermon; the scripture-reading line before
# them is kept, as in Mighty Power in Prayer.
_HYMNS = re.compile(r"<p>\s*HYMNS FROM [^<]*</p>\s*$")

INTRO_HTML = """
<p>Charles Haddon Spurgeon (1834–1892) began his printed ministry with the Holy
Spirit. When the weekly publication of his sermons was launched in January 1855,
the young pastor of New Park Street Chapel was twenty years old, and a
fortnight after the first numbered sermon he gave a whole Sunday, morning and
evening, to the third Person of the Trinity. Those two sermons — numbers four and five of
what became the sixty-three volumes of the <em>New Park Street</em> and
<em>Metropolitan Tabernacle Pulpit</em> — stand first in this book. From that
winter Sunday to the end of his life, Spurgeon returned again and again to the
Holy Ghost, convinced that everything he did in the pulpit was either the
Spirit’s work or no work at all.</p>

<p>He said so constantly, and he meant it. A sermon, in his view, was a dead
thing until the Spirit breathed on it; a church, however large and orthodox, was
a valley of dry bones until the wind blew; a sinner could hear the gospel a
thousand times and never stir until the Spirit applied it. Spurgeon did not
think this a reason for idleness — he preached more, wrote more and organised
more than almost any minister of his century — but he thought it the only
reason for hope. “We want a greater Teacher,” runs the hymn he quotes at the
close of one of these sermons, for “application is the work of God
alone.”</p>

<p>Out of the many times Spurgeon took up the subject, twelve sermons are
gathered here. They are not a systematic treatise, and they were not preached as
a series; each stands complete, on its own text, with its own appeal at the end.
But read together they form something close to a full doctrine of the Spirit,
taught not in the language of the lecture-room but in the warm, direct, often
startling idiom of a preacher pleading with real people. The book is arranged in
four movements.</p>

<p><strong>First, who the Spirit is.</strong> The opening three sermons were all
preached in 1855, and they lay the foundation. “The Personality of the Holy
Ghost” insists that the Spirit is not an influence or an emanation but a Person,
truly God, to be loved, trusted and worshipped. “The Comforter” turns that
doctrine into consolation: the same Person is sent to be the believer’s
advocate, teacher and friend. “The Holy Ghost—The Great Teacher” takes up the
promise that he will guide us into all truth, and presses on the reader both the
need of such a guide and the readiness of the Spirit to be one.</p>

<p><strong>Second, the Spirit’s work in salvation.</strong> “The Necessity of
the Spirit’s Work” opens Ezekiel’s great covenant promise, “I will put my
Spirit within you,” and argues that without it no preaching, however gifted,
can make a single Christian. “The Withering Work of the Spirit,” one of
Spurgeon’s most searching sermons, shows the Spirit first blowing upon the
flower of human goodness until it fades, so that the incorruptible seed of the
Word may take root. “Adoption—The Spirit and the Cry” follows the work through
to its sweetest fruit: the Spirit of the Son sent into our hearts, crying,
“Abba, Father.”</p>

<p><strong>Third, the Spirit in the believer.</strong> Here the sermons turn
from the beginning of the Christian life to its long middle. “The Work of the
Holy Spirit” warns the Galatian in all of us against beginning in the Spirit
and trying to finish in the flesh. “The Holy Spirit’s Intercession” is
perhaps the tenderest thing in the book — an exposition of the groanings that
cannot be uttered, for every believer who has not known how to pray.
“Grieving the Holy Spirit” closes the movement with a loving and very
practical warning: the Spirit who seals us can be grieved by us, and the saint
who grieves him soon finds the light of his own soul going out.</p>

<p><strong>Fourth, the Spirit’s power in the church.</strong> The last three
sermons lift the eye from the individual to the people of God. “The Power of
the Holy Ghost” celebrates the might that raised Christ and still raises dead
souls. “The Outpouring of the Holy Spirit,” preached in 1858 while news of
revival in America was reaching London, asks why the Spirit fell while Peter was
still speaking, and urges the church to pray until he falls again. And “The
Abiding of the Spirit the Glory of the Church,” from the mature preacher of
1886, takes Haggai’s word to discouraged builders — “my spirit remaineth among
you: fear ye not” — and turns it into courage for every congregation that has
looked at its own weakness and despaired.</p>

<p>It is worth remembering where these sermons came from. Spurgeon preached them
to crowds that would have flattered any man into thinking the power lay in his
own gifts, and he never let himself believe it. Again and again he traced the
blessing on his ministry to the prayers of his people and to the Spirit whom
they prayed for. He also knew, as few preachers have, the seasons when the
Spirit’s comfort seemed withdrawn — he suffered long bouts of depression and
pain — and that is why these sermons speak so humanly. They come from a man who
had learned to lean on the Comforter because he had so often needed comfort.</p>

<p>A word about the text. The sermons are given as they were printed in the
weekly Pulpit, without modernisation or abridgement, and the Scripture is the
Authorised Version that Spurgeon read and quoted. Most of the twelve date from
the first half of his ministry, and they carry the energy of the young preacher
— the long sentences, the sudden questions, the direct address to the
unconverted hearer at the end. Readers new to Victorian preaching will find that
a little patience is richly repaid.</p>

<p>Spurgeon would not have wanted this book to be read merely as doctrine. He
would have wanted the reader to stop, and ask for the very thing the sermons
describe. Read one sermon; then pray, as he so often urged his hearers, that the
Spirit who inspired the text would now apply it. If, by the last page, the Holy
Spirit has become to any reader less a doctrine to be defended and more a Person
to be known, loved and obeyed, the volume will have done what its author lived
to do.</p>

<p><em>— The Ochorus Library</em></p>
"""


class Command(BaseCommand):
    help = "Build the curated Spurgeon Holy Spirit anthology (dev DB); then serialize the fixture."

    def handle(self, *args, **opts):
        # Fetch and clean every sermon BEFORE opening the transaction, so the
        # ~15s of polite CCEL requests never hold the dev DB locked.
        chapters = [("Introduction", clean_fragment(INTRO_HTML))]
        for i, (title, url, want_ref) in enumerate(SERMONS, start=2):
            time.sleep(0.8)  # be polite to CCEL
            body, ref, _preached = extract(fetch(url))
            for old, new in FIXUPS.get(i, []):
                if old not in body:
                    raise CommandError(f"ch {i} {title!r}: fixup target not found: {old[:60]!r}")
                body = body.replace(old, new)
            body = _HYMNS.sub("", body)
            if i == _DASH_AS_APOSTROPHE[0]:
                body = _DASH_AS_APOSTROPHE[1].sub("—", body)
            if not ref.startswith(want_ref):
                raise CommandError(f"{title!r}: ref {ref!r} != expected {want_ref!r} ({url})")
            chapters.append((title, body))

        # The early CCEL volumes mix straight and curly quotes (sermons01 is
        # curly, sermons32 straight); convert the WORK as one, in the build, so
        # a rebuild stays idempotent and QuoteStyleTests passes.
        bodies, _ = convert_work([b for _, b in chapters], f"{SLUG}.en.json")
        # convert_work moves double quotes only; No. 1918 also keys its
        # apostrophes straight ("the Lord's house"), and every straight ' in the
        # book follows a letter, so curl them to match the other eleven.
        bodies = [re.sub(r"(?<=[A-Za-z])'", "’", b) for b in bodies]
        with transaction.atomic():  # a mid-run abort rolls back, never a partial book
            try:
                author = Author.objects.get(slug=AUTHOR_SLUG)
            except Author.DoesNotExist:
                raise CommandError(
                    f"Author {AUTHOR_SLUG!r} is not in this database — run "
                    "`manage.py seed_if_empty` first."
                ) from None
            # Workflow-owned fields (source_type, is_published, sort_order) are
            # create-only so a rebuild can't walk back a review/unpublish.
            content = {
                "author": author,
                "title": TITLE,
                "subtitle": SUBTITLE,
                "description": DESCRIPTION,
                "attribution": ATTRIBUTION,
                "cover_color": COVER_COLOR,
                "source_url": "",
                "qa": QA,
            }
            book, created = Book.objects.update_or_create(
                slug=SLUG,
                language="en",
                defaults=content,
                create_defaults={
                    **content,
                    "source_type": Book.SourceType.PUBLIC_DOMAIN,
                    "is_published": True,
                    "sort_order": book_sort_order(SLUG),
                },
            )
            book.chapters.all().delete()

            for i, ((title, _), body) in enumerate(zip(chapters, bodies, strict=True), start=1):
                body = settled_chapter_body(SLUG, i, body)
                wc = word_count(body)
                if wc < 500:
                    raise CommandError(f"{title!r}: only {wc} words — aborted")
                Chapter.objects.create(book=book, order=i, title=title, body_html=body)
                self.stdout.write(f"  ch {i:2}: {title[:50]:50} {wc:>6} words")

            book.refresh_from_db()
            english_audit.report(self, english_audit.audit_book(book), book.slug)
            verb = "Created" if created else "Rebuilt"
            self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters"))
