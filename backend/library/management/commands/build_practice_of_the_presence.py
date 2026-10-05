"""Build Brother Lawrence's *The Practice of the Presence of God*.

The source is Project Gutenberg #13871, the Fleming H. Revell edition ("The
Practice of the Presence of God the Best Rule of a Holy Life … Translated from
the French"), the anonymous English version that circulated through the
nineteenth century. www.gutenberg.org refuses this environment's egress, so the
plain-text file is read from the GITenberg mirror of the same ebook on GitHub —
the route ``build_unspoken_sermons`` takes.

NOT Project Gutenberg #5657, the obvious search hit: that ebook is a
copyrighted 2002 modernised edition ("Copyright (C) 2002 by Lightheart"), and
the Gutenberg header says so.

One book, nineteen chapters — the four Conversations and the fifteen Letters,
each a chapter under its own title, in the edition's order. The publisher's
preface is left out (its facts are in the description). The edition has no
Spiritual Maxims.

How the plain text is read:

* ``_underscores_`` are the edition's italics, ``--`` its dashes, and the
  ``----`` standing for a withheld name ("Mr. ----") becomes a two-em dash;
* the edition sets the divine names in small capitals (GOD, LORD, FATHER,
  JESUS CHRIST, HOLY SPIRIT); the plain text can only spell that as capitals,
  which on a screen read as shouting two hundred times, so they are set in
  ordinary title case;
* the four ``[n]`` notes — three the translator's, one a pointer to the Bible —
  are marked * † at the end of their chapter, the way ``build_unspoken_sermons``
  does it.

Fixture-driven like every other book: ``seed_books`` creates it (and the author,
from ``authors.json``) on the next deploy from
``fixtures/content/books/the-practice-of-the-presence-of-god.en.json``. This
command GENERATES that fixture reproducibly; it is idempotent.

    DJANGO_DEBUG=true uv run python manage.py build_practice_of_the_presence
"""

from __future__ import annotations

import html
import re

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from library import covers, english_audit
from library.content_fixtures import book_sort_order
from library.corrections import settled_chapter_body
from library.ingest import clean_fragment, word_count
from library.models import Author, Book, Chapter
from library.quote_marks import assert_punctuation_only, convert

SLUG = "the-practice-of-the-presence-of-god"
TITLE = "The Practice of the Presence of God"
SUBTITLE = "The Best Rule of a Holy Life"
AUTHOR_SLUG = "brother-lawrence"
GUTENBERG_ID = "13871"
SOURCE_TXT = (
    "https://raw.githubusercontent.com/GITenberg/"
    "The-Practice-of-the-Presence-of-God-the-Best-Rule-of-a-Holy-Life_13871/master/13871.txt"
)
# The year of the first French edition of the Conversations (Mœurs et
# entretiens, 1694), which gave the book its shape: conversations, then letters.
PUBLICATION_YEAR = 1694
COVER_COLOR = covers.ink_safe("#5b4a3a")

AUTHOR_STUB = {"name": "Brother Lawrence", "birth_year": 1614, "death_year": 1691}

DESCRIPTION = (
    "Brother Lawrence was a lay brother of the Discalced Carmelites in Paris, a "
    "former soldier and footman who spent fifteen years as the monastery's cook, "
    "in a kitchen for which he had, he said, a great natural aversion. What he "
    "learned there was to live every hour in the company of God — “in the noise "
    "and clatter of my kitchen,” as he put it, as quietly as on his knees before "
    "the sacrament. Here are the four conversations that Joseph de Beaufort "
    "recorded with him in 1666 and 1667, and fifteen of his letters, many of them "
    "written in his old age to friends who were ill or troubled: a small book, unlearned and "
    "plain, that Catholics and Protestants have loved alike for three centuries."
)

ATTRIBUTION = (
    "Public domain — the Conversations (recorded by Joseph de Beaufort) and "
    "Letters of Brother Lawrence (Nicolas Herman, c. 1614–1691), in the "
    "anonymous English translation published by the Fleming H. Revell Company, "
    "“Translated from the French”; text from Project Gutenberg (ebook 13871). "
    "The publisher's preface is not included; the divine names the edition sets "
    "in small capitals are set here in ordinary type, and its four notes follow "
    "the chapters they belong to."
)

# The edition's headings, in order, and the chapter title each becomes.
CHAPTERS = [
    "First Conversation",
    "Second Conversation",
    "Third Conversation",
    "Fourth Conversation",
    "First Letter",
    "Second Letter",
    "Third Letter",
    "Fourth Letter",
    "Fifth Letter",
    "Sixth Letter",
    "Seventh Letter",
    "Eighth Letter",
    "Ninth Letter",
    "Tenth Letter",
    "Eleventh Letter",
    "Twelfth Letter",
    "Thirteenth Letter",
    "Fourteenth Letter",
    "Fifteenth Letter",
]

# Transcription slips, each unambiguous and each checked to occur exactly the
# given number of times, so a changed edition fails loudly instead of quietly.
SOURCE_FIXES = [
    # "all would be equal to a soul truly resigned" — b read as li. E. M.
    # Bounds quotes this sentence with "be" (Purpose in Prayer, ch. 1).
    ("for all would lie equal", "for all would be equal", 1),
    # The full stop before a new sentence, lost before "Give".
    ("_natural to_ us Give Him thanks", "_natural to_ us. Give Him thanks", 1),
    # A comma for the full stop before a new sentence ("Thus continued").
    ("and my sins, Thus continued", "and my sins. Thus continued", 1),
    # A word broken across the printed line, its hyphen kept; "vouchsafed"
    # is whole in the Fifteenth Letter.
    ("vouch-safe to me", "vouchsafe to me", 1),
    # "conformable to His holy will" — a stray hyphen.
    ("His holy-will", "His holy will", 1),
]

# The edition's small-capital divine names, longest first.
DIVINE_NAMES = [
    ("JESUS CHRIST", "Jesus Christ"),
    ("HOLY SPIRIT", "Holy Spirit"),
    ("GOD'S", "God's"),
    ("GOD", "God"),
    ("LORD", "Lord"),
    ("FATHER", "Father"),
]

_START = "CONVERSATIONS."
_END = "NOTES:"
_HEADING = re.compile(r"^([A-Z]+) (CONVERSATION|LETTER)\.$")
_NOTE_MARK = re.compile(r"\[(\d)\]")
_NOTE = re.compile(r"^\[(\d): (.*)\]$", re.S)
# Footnote signs, the printer's order. Not numerals: the deploy's correction
# step strips every lone numbered ``<sup>`` as extraction residue
# (`corrections.strip_footnote_markers`). No chapter has more than two notes.
_SIGNS = ("*", "†")
_LEFTOVER_CAPS = re.compile(r"\b[A-Z]{3,}\b")


def _source_text() -> str:
    resp = requests.get(SOURCE_TXT, timeout=60)
    resp.raise_for_status()
    text = resp.text.replace("\r\n", "\n")
    for old, new, count in SOURCE_FIXES:
        if text.count(old) != count:
            raise CommandError(f"source fix {old!r}: expected {count}, found {text.count(old)}.")
        text = text.replace(old, new)
    return text


def _blocks(lines: list[str]) -> list[str]:
    """Paragraphs: blank-line separated, hard-wrapped lines rejoined."""
    blocks: list[str] = []
    current: list[str] = []
    for ln in [*lines, ""]:
        if ln.strip():
            current.append(ln.strip())
        elif current:
            out = ""
            for part in current:
                # A dash (--) at a line end runs on; a withheld name (----)
                # is a word, and keeps its space.
                runs_on = re.search(r"(?<!-)--$", out) or re.match(r"--(?!-)", part)
                if out and not runs_on:
                    out += " "
                out += part
            blocks.append(re.sub(r" {2,}", " ", out))
            current = []
    return blocks


def _recase(text: str) -> str:
    for caps, title in DIVINE_NAMES:
        text = re.sub(rf"\b{re.escape(caps)}\b", title, text)
    return text


def _inline(text: str, where: str) -> str:
    text = _recase(text)
    leftover = _LEFTOVER_CAPS.findall(text)
    if leftover:
        raise CommandError(f"{where}: capitals left after recasing: {leftover}")
    text = html.escape(text, quote=False)
    text = text.replace("----", "——").replace("--", "—")
    if text.count("_") % 2:
        raise CommandError(f"{where}: an italic span never closes: {text[:80]!r}")
    return re.sub(r"_([^_]+)_", r"<em>\1</em>", text)


def _parse() -> tuple[list[tuple[str, list[str]]], dict[str, str]]:
    text = _source_text()
    lines = text.split("\n")
    try:
        start = lines.index(_START)
        end = lines.index(_END, start)
    except ValueError:
        raise CommandError("start/end markers not found — the edition changed.") from None
    body, notes_lines = lines[start + 1 : end], lines[end + 1 :]

    heads = [(i, m) for i, ln in enumerate(body) if (m := _HEADING.match(ln))]
    titles = [f"{m.group(1).title()} {m.group(2).title()}" for _, m in heads]
    if titles != CHAPTERS:
        raise CommandError(f"chapter headings differ from the contents: {titles}")

    sections = []
    for k, (i, _) in enumerate(heads):
        stop = heads[k + 1][0] if k + 1 < len(heads) else len(body)
        chunk = [ln for ln in body[i + 1 : stop] if ln.strip() != "LETTERS."]
        sections.append((CHAPTERS[k], _blocks(chunk)))

    notes: dict[str, str] = {}
    cut = next(n for n, ln in enumerate(notes_lines) if ln.startswith("End of the Project"))
    for block in _blocks(notes_lines[:cut]):
        m = _NOTE.match(block)
        if not m:
            raise CommandError(f"unreadable note {block[:60]!r}")
        notes[m.group(1)] = m.group(2)
    if sorted(notes) != ["1", "2", "3", "4"]:
        raise CommandError(f"expected notes 1–4, found {sorted(notes)}")
    return sections, notes


def _chapter_html(title: str, blocks: list[str], notes: dict[str, str]) -> str:
    used: list[str] = []

    def mark(m: re.Match) -> str:
        used.append(m.group(1))
        return f"\x00{len(used)}\x00"

    parts = []
    for block in blocks:
        body = _inline(_NOTE_MARK.sub(mark, block), title)
        body = re.sub("\x00(\\d)\x00", lambda m: f"<sup>{_SIGNS[int(m.group(1)) - 1]}</sup>", body)
        parts.append(f"<p>{body}</p>")
    if used:
        parts.append("<hr/>")
        for i, n in enumerate(used):
            parts.append(f"<p><sup>{_SIGNS[i]}</sup> {_inline(notes[n], f'{title} note {n}')}</p>")
    return "".join(parts)


def _chapters() -> list[tuple[str, str]]:
    sections, notes = _parse()
    chapters = [(title, _chapter_html(title, blocks, notes)) for title, blocks in sections]
    seen = re.findall(r"<sup>", "".join(b for _, b in chapters))
    if len(seen) != 2 * len(notes):  # each note: its mark and its entry
        raise CommandError(f"expected {2 * len(notes)} note signs, found {len(seen)}")

    # Gutenberg's ASCII double quotes -> the corpus's curly ones (apostrophes
    # stay straight, as across the library). Only the marks may move.
    curled = []
    for n, (title, body) in enumerate(chapters, start=1):
        new, _ = convert(body, outer_guillemets=False)
        assert_punctuation_only(body, new, f"{SLUG}[{n}]")
        curled.append((title, new))
    return curled


class Command(BaseCommand):
    help = "Build Brother Lawrence's Practice of the Presence of God in the dev DB; then serialize the fixture."

    @transaction.atomic
    def handle(self, *args, **opts):
        author, created_author = Author.objects.get_or_create(slug=AUTHOR_SLUG, defaults=AUTHOR_STUB)
        if created_author:
            self.stdout.write(f"  (created author stub {AUTHOR_SLUG!r} — real bio lives in authors.json)")

        chapters = _chapters()

        content = {
            "author": author,
            "title": TITLE,
            "subtitle": SUBTITLE,
            "description": DESCRIPTION,
            "attribution": ATTRIBUTION,
            "publication_year": PUBLICATION_YEAR,
            "cover_color": COVER_COLOR,
            "source_url": f"https://www.gutenberg.org/ebooks/{GUTENBERG_ID}",
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

        total = 0
        for order, (title, body) in enumerate(chapters, start=1):
            body = settled_chapter_body(SLUG, order, clean_fragment(body))
            wc = word_count(body)
            # The shortest letter runs ~270 words; anything far under that is a
            # parse that lost text, not a short letter.
            if wc < 250:
                raise CommandError(f"ch {order} ({title!r}): only {wc} words — aborted.")
            total += wc
            Chapter.objects.create(book=book, order=order, title=title, body_html=body)
            self.stdout.write(f"  ch {order:2}: {title[:44]:44} {wc:>6} words")

        book.refresh_from_db()
        english_audit.report(self, english_audit.audit_book(book), book.slug)
        verb = "Created" if created else "Rebuilt"
        self.stdout.write(self.style.SUCCESS(f"{verb} {TITLE!r} — {book.chapter_count} chapters, {total} words"))
