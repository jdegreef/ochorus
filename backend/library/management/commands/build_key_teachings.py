"""Build the *Key Teachings of …* series — Ochorus's own study companions.

These are NOT the authors' own texts. Each is an independent, house-written
work of exposition and appreciation that distills a classic teacher's message
into eighteen short chapters (each ending in questions and a prayer), quoting
only the Authorised (King James) Version and naming the author's own works for
further reading. That design is what lets the series cover writers whose actual
books are still in copyright (Watchman Nee) as safely as it covers the
public-domain ones (Simpson, Edwards, Baxter): nothing of the author's own prose
is reproduced — only Ochorus's summaries and KJV Scripture.

A companion is filed **under the author it is about** (author FK = that person,
e.g. ``a-b-simpson``), with the Ochorus attribution carried in the ``subtitle``
and the rights note in ``attribution`` — the same pattern as a biography ABOUT a
person (``susanna-wesley-clarke``, ``watchman-nee-a-life``), never crediting the
subject as if they wrote it. It is not filed under ``ochorus-originals`` (that is
for multi-subject collections).

Why a bespoke command rather than ``import_pdf``: these are typographically rich
digital PDFs (one shared template) that the generic PDF importer mishandles in
three ways — the small-caps running header ("N THE KEY TEACHINGS OF …") leaks
into every chapter body, the bold in-chapter subheadings fuse into the following
paragraph, and the biographical narrative + "A Reader's Guide" fold into the
Introduction/Conclusion instead of standing as their own chapters. This command
reads the font/weight structure directly:

    >= body*1.11   section / chapter title      -> chapter boundary
    ~  body        prose (regular)  -> <p> ;  bold, short, unpunctuated -> <h2>
    ~  body*0.80   set-apart Scripture quotation -> <blockquote>
    <  body*0.72   small: an epigraph citation (chapter:verse) is kept with its
                   quote; a running header / "CHAPTER N" marker / page number is
                   dropped.

The source PDFs are committed under ``data/key-teachings/`` (they are Ochorus's
own prose, not fetchable from any public-domain source, so the build must not
depend on a scratch copy). Fixture-driven: ``seed_books`` creates each book (and
resolves the author from ``authors.json``) on the next deploy. Idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_key_teachings                # all
    DJANGO_DEBUG=true uv run python manage.py build_key_teachings key-teachings-of-a-b-simpson
"""

from __future__ import annotations

import html
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import fitz
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from library import english_audit
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, is_front_matter, word_count
from library.management.commands.import_ochorus import _ends_sentence
from library.models import Author, Book, Chapter, Series
from library.titlecase import recase_title

DATA_DIR = Path(__file__).resolve().parent / "data" / "key-teachings"

# De-hyphenation has to tell a syllable break ("rev-elation" → revelation) from a
# real hyphenated compound that broke at its hyphen ("self-righteousness") — which
# a dictionary alone can't do (web2 lacks inflections/proper nouns, so it would
# wrongly keep "Simp-son's" etc.). For this closed 4-book corpus the answer is:
# DROP by default, and enumerate the few real compounds that occur — the `self-*`
# forms (all genuine here, so keep the hyphen unless the joined word is a known
# CLOSED self-word), number-word compounds ("twenty-five"), and one stray pair.
_NUM_WORDS = {
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety", "hundred", "eighteenth", "nineteenth", "twentieth",
}
# self-words that are written CLOSED — a "self-" line break here is a syllable
# break, so drop the hyphen ("self-ish" → "selfish"). Every other "self-" split
# in this corpus is a real compound and keeps it.
_SELF_CLOSED = {"selfish", "selfless", "selfsame", "selfhood"}
_KEEP_PAIRS = {("feeble", "minded")}


def _dehyphenate(left: str, right: str) -> str:
    """Join a line-break-hyphenated split (``left`` ends "word-", ``right`` opens
    with the rest). Drop the hyphen — except for a real ``self-*`` or numeric
    compound, where it is kept."""
    m1 = re.search(r"([A-Za-z]+)-$", left)
    m2 = re.match(r"([A-Za-z]+)", right)
    if m1 and m2:
        f1, f2 = m1.group(1), m2.group(1)
        keep = (
            (f1.lower() == "self" and (f1 + f2).lower() not in _SELF_CLOSED)
            or f1.lower() in _NUM_WORDS
            or (f1.lower(), f2.lower()) in _KEEP_PAIRS
        )
        if keep:
            return left + right  # the hyphen is already at the end of `left`
    return left[:-1] + right

# A chapter:verse reference — marks a small block as a kept epigraph citation
# ("COLOSSIANS 2:9–10") rather than a running header ("2 THE KEY TEACHINGS OF …").
_VERSE = re.compile(r"\d+\s*[:.]\s*\d+")
_MASTHEAD = re.compile(r"key teachings of", re.I)
_PROSE_END = re.compile(r"[.!?;:,]$")
# A block that is nothing but a page number — arabic or roman, optionally with
# stray punctuation. On a chapter's opening page this is set in the same size
# band as the set-apart Scripture, so it must be recognised by content, not
# size, and dropped as furniture without breaking the prose it sits inside.
_BARE_NUM = re.compile(r"^[ivxlcdm\d]+[.)]?$", re.I)


@dataclass(frozen=True)
class Work:
    slug: str
    title: str
    subtitle: str
    author_slug: str
    pdf: str
    description: str
    attribution: str
    cover_color: str
    about_html: str  # reader-visible "About this work" — carries the rights note


WORKS: dict[str, Work] = {
    "key-teachings-of-a-b-simpson": Work(
        slug="key-teachings-of-a-b-simpson",
        title="The Key Teachings of A. B. Simpson",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="a-b-simpson",
        pdf="a-b-simpson.pdf",
        description=(
            "A concise, faithful guide to the heart of A. B. Simpson's message — "
            "the Fourfold Gospel of Christ our Saviour, Sanctifier, Healer, and "
            "Coming King, and the single theme beneath it all: not the blessing "
            "but the Blesser, Christ Himself. Eighteen short chapters, each ending "
            "in questions and a prayer, written by Ochorus as a companion to "
            "Simpson's own public-domain works — which readers are warmly "
            "encouraged to go to directly."
        ),
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus — not published by, affiliated with, or endorsed by The "
            "Christian and Missionary Alliance or any body descended from "
            "Simpson's ministry. A. B. Simpson's own writings are in the public "
            "domain and freely available; readers are encouraged to go to them "
            "directly. Scripture quotations are from the Authorised (King James) "
            "Version."
        ),
        cover_color="#1f5468",
        about_html=(
            "<p>This is not a book by A. B. Simpson. It is a companion to him — an "
            "independent work of exposition and appreciation, written by Ochorus, "
            "that gathers the heart of his teaching into eighteen short chapters "
            "for the ordinary reader.</p>"
            "<p>Simpson's one theme was Christ Himself. Behind the Fourfold Gospel "
            "— Christ our Saviour, Sanctifier, Healer and Coming King — lay a "
            "single discovery he never tired of pressing: that the Christian life "
            "is not the pursuit of a blessing, an experience or a gift, but the "
            "possession of a Person. Once it was the blessing, he sang, now it is "
            "the Lord. This volume follows that thread through his life, his "
            "deeper-life teaching, and his understanding of faith, prayer and "
            "mission, and it ends each chapter where he would have wanted it to "
            "end: in a few questions and a prayer.</p>"
            "<p>Simpson's own writings are in the public domain and freely "
            "available, and every chapter here names them so the reader can go to "
            "the source. This companion is offered only to open the door. It "
            "quotes Scripture from the Authorised (King James) Version, the Bible "
            "Simpson preached from, and makes no claim to stand in for the man's "
            "own unhurried, Christ-filled pages.</p>"
        ),
    ),
    "key-teachings-of-jonathan-edwards": Work(
        slug="key-teachings-of-jonathan-edwards",
        title="The Key Teachings of Jonathan Edwards",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="jonathan-edwards",
        pdf="jonathan-edwards.pdf",
        description=(
            "A concise, faithful guide to the mind and heart of Jonathan Edwards "
            "— the sovereignty and the beauty of God, true religion as holy "
            "affections, and the end for which God created the world: His own "
            "glory, delighted in by His creatures. Eighteen short chapters, each "
            "ending in questions and a prayer, written by Ochorus as a companion "
            "to Edwards's own public-domain works, which readers are warmly "
            "encouraged to go to directly."
        ),
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Jonathan Edwards's own writings are in the public domain "
            "and freely available; readers are encouraged to go to them directly. "
            "Scripture quotations are from the Authorised (King James) Version, "
            "the version Edwards preached from."
        ),
        cover_color="#2f4a34",
        about_html=(
            "<p>This is a companion to Jonathan Edwards, not a book by him. "
            "Written by Ochorus, it distils the thought of America's greatest "
            "theologian into eighteen short chapters an ordinary reader can "
            "carry.</p>"
            "<p>Edwards saw further into the greatness and beauty of God than "
            "almost anyone who has written in English, and he bent the whole "
            "force of a formidable mind to a single end: that God might be seen as "
            "supremely glorious and enjoyed as supremely good. This volume traces "
            "that vision through his most important works — the sovereignty of "
            "God, the beauty of holiness, true religion as holy affections, the "
            "end for which God created the world — and through the sterner texts, "
            "like the sermon on sinners in the hands of an angry God, that people "
            "remember and misremember. Each chapter closes in questions and a "
            "prayer, because Edwards held that truth unfelt and unobeyed has not "
            "yet been truly known.</p>"
            "<p>Edwards's own writings are in the public domain and freely "
            "available, and this companion names them throughout so the reader may "
            "go to the source. It quotes Scripture from the Authorised (King "
            "James) Version, the Bible Edwards preached from, and is offered only "
            "to open the door to the man's own pages.</p>"
        ),
    ),
    "key-teachings-of-richard-baxter": Work(
        slug="key-teachings-of-richard-baxter",
        title="The Key Teachings of Richard Baxter",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="richard-baxter",
        pdf="richard-baxter.pdf",
        description=(
            "A concise, faithful guide to the pastoral heart of Richard Baxter — "
            "the saints' everlasting rest, the call to the unconverted, and the "
            "minister's charge to take heed to himself and to all the flock. "
            "Eighteen short chapters, each ending in questions and a prayer, "
            "written by Ochorus as a companion to Baxter's own public-domain "
            "works, which readers are warmly encouraged to go to directly."
        ),
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. Richard Baxter's own writings are in the public domain; his "
            "seventeenth-century English has been rendered into modern prose "
            "rather than quoted, and readers are encouraged to go to the originals "
            "directly. Scripture quotations are from the Authorised (King James) "
            "Version."
        ),
        cover_color="#5b2f2a",
        about_html=(
            "<p>This is a companion to Richard Baxter, not a book by him. Written "
            "by Ochorus, it renders the pastoral wisdom of the great Puritan of "
            "Kidderminster into eighteen short chapters in plain modern "
            "English.</p>"
            "<p>Baxter wrote, by his own account, as a dying man to dying men, and "
            "the urgency never left him. Out of a lifetime of sickness and labour "
            "came books the church has never let go of: The Saints' Everlasting "
            "Rest, on the heaven the weary are travelling toward; A Call to the "
            "Unconverted, pressed on the careless with tears; and The Reformed "
            "Pastor, still the most searching book a minister can read about his "
            "own soul. This volume follows those themes and more — conversion, "
            "family religion, the crucifying of the world, counsel for the "
            "melancholy, peace among Christians — and ends each chapter, as Baxter "
            "would, in self-examination and prayer.</p>"
            "<p>Baxter's own writings are in the public domain and freely "
            "available. Because his seventeenth-century English can be heavy "
            "going, this companion renders his thought into modern prose rather "
            "than quoting it, and names his works throughout so the reader may go "
            "to the source. Scripture is quoted from the Authorised (King James) "
            "Version.</p>"
        ),
    ),
    "key-teachings-of-watchman-nee": Work(
        slug="key-teachings-of-watchman-nee",
        title="The Key Teachings of Watchman Nee",
        subtitle="An Ochorus companion to his life and teaching",
        author_slug="watchman-nee",
        pdf="watchman-nee.pdf",
        description=(
            "A concise, faithful guide to the heart of Watchman Nee's ministry — "
            "the normal Christian life as Christ living in the believer, the "
            "finished work of the cross, and the way of the overcomers. Eighteen "
            "short chapters, each ending in questions and a prayer, written by "
            "Ochorus as an independent companion to Nee's ministry, naming his "
            "books for the reader's own further study."
        ),
        # Nee's own works are NOT public domain — this companion quotes only the
        # KJV and paraphrases; the disavowal below is essential and must ship.
        attribution=(
            "An independent work of exposition, summary and appreciation by "
            "Ochorus. It is not published by, affiliated with, or endorsed by any "
            "organisation holding rights in the writings of Watchman Nee. All "
            "descriptions of his teaching are the present author's own summaries; "
            "his books and spoken ministry are named for further study, and "
            "readers are warmly encouraged to obtain those works from their "
            "rightful publishers. Scripture quotations are from the Authorised "
            "(King James) Version."
        ),
        cover_color="#2a3a5e",
        about_html=(
            "<p>This is a companion to Watchman Nee, not a book by him. Written by "
            "Ochorus, it sets out in eighteen short chapters the teaching for "
            "which Nee is chiefly remembered — the normal Christian life as Christ "
            "living in the believer, the finished work of the cross, the release "
            "of the spirit through the breaking of the outer man, and the way of "
            "the overcomers.</p>"
            "<p>It is important to be clear about what this book is and is not. It "
            "is an independent work of exposition, summary and appreciation. It is "
            "not published by, affiliated with, or endorsed by any organisation "
            "that holds rights in the writings of Watchman Nee. All descriptions "
            "of his teaching are the present author's own summaries; his books and "
            "spoken ministry are named only for the reader's further study, and "
            "readers are warmly encouraged to obtain those works from their "
            "rightful publishers. Nothing of Nee's own text is reproduced here — "
            "only Scripture, quoted from the Authorised (King James) Version, and "
            "Ochorus's account of what he taught.</p>"
            "<p>Nee taught, more insistently than almost anyone, that no servant "
            "of God is to be looked at. The right response to his ministry is not "
            "admiration but obedience — not to him, but to the Lord he spent his "
            "life trying to describe.</p>"
        ),
    ),
}


def _block_text(block: dict) -> str:
    """Assemble a PyMuPDF block's text, de-hyphenating end-of-line splits.

    PyMuPDF emits one entry per line; a justified line often ends on a soft
    hyphen ("Simp-" / "son's"), so a naive join yields "Simp- son's". Join
    line-by-line: a line ending in a letter+hyphen concatenates the next with no
    space and no hyphen ("Simpson's"); otherwise lines join with a space. A
    mid-line hyphen (a real compound, "deeper-life") is untouched.
    """
    parts: list[str] = []
    for line in block.get("lines", []):
        text = "".join(s["text"] for s in line.get("spans", [])).strip()
        if not text:
            continue
        if parts and re.search(r"[A-Za-z]-$", parts[-1]):
            parts[-1] = _dehyphenate(parts[-1], text)  # line-break split
        else:
            parts.append(text)
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def blocks_with_bold(pdf_bytes: bytes) -> tuple[list[tuple[str, float, bool]], float]:
    """Return ([(text, max_font_size, is_bold), …], modal_body_size)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    out: list[tuple[str, float, bool]] = []
    sizes: Counter[int] = Counter()
    for page in doc:
        for b in page.get_text("dict").get("blocks", []):
            if b.get("type") != 0:  # skip images
                continue
            spans = [s for line in b.get("lines", []) for s in line.get("spans", [])]
            if not spans:
                continue
            text = _block_text(b)
            if not text:
                continue
            size = max(s["size"] for s in spans)
            bold = all((s["flags"] & 16) or ("bold" in s["font"].lower()) for s in spans)
            for s in spans:
                sizes[round(s["size"])] += max(1, len(s["text"].strip()))
            out.append((text, size, bold))
    doc.close()
    body = float(sizes.most_common(1)[0][0]) if sizes else 10.0
    return out, body


def _kind(size: float, body: float) -> str:
    if size >= body * 1.11:
        return "head"
    if size >= body * 0.90:
        return "prose"
    if size >= body * 0.72:
        return "quote"
    return "small"


def _merge_prose(paras: list[str]) -> list[str]:
    """Rejoin prose paragraphs the PDF split across a page/column break.

    Like ``import_ochorus._merge_paragraphs`` (a block that doesn't end a
    sentence continues the previous), but a fragment ending on a hyphen is a
    word broken across the break ("Chris-" / "tians") — drop the hyphen and join
    with no space, matching the in-block de-hyphenation in ``_block_text``.
    """
    out: list[str] = []
    for p in paras:
        if out and not _ends_sentence(out[-1]):
            if re.search(r"[A-Za-z]-$", out[-1]):
                out[-1] = _dehyphenate(out[-1], p)
            else:
                out[-1] = f"{out[-1]} {p}".strip()
        else:
            out.append(p)
    return out


def _segment_html(seg: list[tuple[str, float, bool]], body: float) -> str:
    """Render one chapter's blocks into ``<p>/<h2>/<blockquote>`` HTML.

    ``prose`` buffers consecutive prose paragraphs (rejoined across page-break
    furniture); ``quote`` buffers a set-apart Scripture block plus its citation.
    Each is flushed when a boundary of a different kind arrives.
    """
    parts: list[tuple[str, str]] = []
    prose: list[str] = []
    quote: list[str] = []

    def flush_prose() -> None:
        parts.extend(("p", p) for p in _merge_prose(prose))
        prose.clear()

    def flush_quote() -> None:
        if quote:
            parts.append(("blockquote", " ".join(quote)))
            quote.clear()

    for text, size, bold in seg:
        if _BARE_NUM.match(text):
            continue  # a lone page number — drop, and don't break the prose
        kind = _kind(size, body)
        if kind == "small":
            if _VERSE.search(text) and not _MASTHEAD.search(text):
                if quote:
                    quote.append(text)
                else:
                    flush_prose()
                    parts.append(("blockquote", text))
            # else: running header / marker / stray → drop
            continue
        if kind == "quote":
            flush_prose()
            flush_quote()
            quote.append(text)
            continue
        # prose or bold subheading
        flush_quote()
        if bold and 1 <= len(text.split()) <= 10 and not _PROSE_END.search(text):
            flush_prose()
            parts.append(("h2", text))
        else:
            prose.append(text)
    flush_quote()
    flush_prose()
    return "".join(f"<{tag}>{html.escape(t)}</{tag}>" for tag, t in parts)


def chapters_from_pdf(pdf_bytes: bytes) -> list[tuple[str, str]]:
    """Split the PDF into (title, body_html) chapters, front matter dropped."""
    blocks, body = blocks_with_bold(pdf_bytes)
    starts = [i for i, (_t, s, _b) in enumerate(blocks) if _kind(s, body) == "head"]
    chapters: list[tuple[str, str]] = []
    for j, idx in enumerate(starts):
        end = starts[j + 1] if j + 1 < len(starts) else len(blocks)
        title = recase_title(re.sub(r"\s+", " ", blocks[idx][0]).strip(" .:-"))
        body_html = _segment_html(blocks[idx + 1:end], body)
        if is_front_matter(title) or _MASTHEAD.search(title) or word_count(body_html) < 120:
            continue  # title page, disclaimer, contents, or a stub
        chapters.append((title[:300], body_html))
    return chapters


class Command(BaseCommand):
    help = "Build the Key Teachings of … study-companion series."

    def add_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Work slugs (default: all).")

    def handle(self, *args, **opts):
        wanted = set(opts["slugs"])
        unknown = wanted - set(WORKS)
        if unknown:
            raise CommandError(f"Unknown slug(s): {', '.join(sorted(unknown))}")
        for slug, work in WORKS.items():
            if wanted and slug not in wanted:
                continue
            self._build(work)

    @transaction.atomic
    def _build(self, work: Work) -> None:
        self.stdout.write(f"→ {work.title}")
        pdf_path = DATA_DIR / work.pdf
        if not pdf_path.exists():
            raise CommandError(f"missing PDF: {pdf_path}")
        author = Author.objects.get(slug=work.author_slug)  # exists in authors.json
        chapters = chapters_from_pdf(pdf_path.read_bytes())
        if len(chapters) < 3:
            raise CommandError(f"{work.slug}: only {len(chapters)} chapters — aborted.")

        content = {
            "author": author,
            "title": work.title,
            "subtitle": work.subtitle,
            "description": work.description,
            "attribution": work.attribution,
            "about_html": work.about_html,
            "cover_color": work.cover_color,
            # A collection, not a reading order: no volume numeral.
            "series": Series.objects.get(slug="key-teachings"),
            "cover_url": f"/covers/art/{work.slug}.svg",  # wordless tree ground
        }
        next_order = (Book.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
        book, was_created = Book.objects.update_or_create(
            slug=work.slug,
            language="en",
            defaults=content,
            create_defaults={
                **content,
                "source_type": Book.SourceType.PUBLIC_DOMAIN,
                # Published — the founder reviewed the render and cleared the
                # series (migration 0155 flipped the rows already on prod).
                # Create-only, so the admin's later toggle is never walked back.
                "is_published": True,
                "sort_order": next_order,
            },
        )
        book.chapters.all().delete()
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(work.slug, order, clean_fragment(body))
            wc = word_count(body)
            if wc < 120:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:46]:46} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if was_created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {work.title!r} — {book.chapter_count} chapters"))
