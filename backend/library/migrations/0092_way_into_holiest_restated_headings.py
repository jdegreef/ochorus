"""Drop the heading all 36 chapters of *The Way Into the Holiest* open with,
above prose the reader already sees titled.

CCEL prints each chapter of Meyer's book under its own numbered heading —
``II. THE DIGNITY OF CHRIST`` over the chapter titled "The Dignity of Christ" —
and the reader renders the title itself, so the name lands twice on every page
of the book.

``import_ccel._restates`` already drops that restatement on import, roman
numbering included since #1176. But the rule reaches no existing reader:
``seed_books`` re-upserts the Book row on every deploy and deliberately leaves
an existing book's CHAPTERS alone (its SCOPE note says why — chapter ``order``
is a public contract), so a stored body only moves when a migration moves it.
#1176 shipped the rule without the data, which is what this finishes. The
fixture is re-serialized in the same commit, or the deploy's ``chapter_drift``
warning reports these rows as diverged forever.

TWO SHAPES, one defect. Fourteen chapters carry the restatement as a real
heading element (``<h2>I. THE WORD OF GOD.</h2>``); twenty-two carry it as
loose text before the first tag (``IX. A WARNING AGAINST UNBELIEF <h4>…``),
which lands in ``body_text`` and so in the search index too. Matching only the
tidy shape would have left the book duplicating its title on most of its
chapters. The loose shape is residue from an older import — CCEL prints that
title in a navigation table outside ``#theText``, so a fresh import never sees
it — which is why only the stored rows need repairing and the importer needs no
further change.

The predicate is IMPORTED rather than restated here, so this cannot drift from
the rule it is catching the data up to. It is applied whole: every chapter of
this book restates its own title, the Preface (``<h2>PREFACE.</h2>``) included,
and leaving that one row duplicated to be tidy about which numbering style
caught it would be a worse book for no reason.

``search_vector`` and ``citations_indexed_at`` are cleared on every row this
writes: the historical model runs no ``save()`` hook, so both would survive as
valid-looking indexes over text the chapter no longer holds. The release chain
repairs a NULL vector and re-scans a cleared stamp.

A database built from the corrected fixture never matches the condition, so
this no-ops there — as it does on a second run.
"""

from __future__ import annotations

import re

from django.db import migrations

from library.ingest import text_of, word_count
from library.management.commands.import_ccel import _restates
from library.text import html_to_text

SLUG = "way-into-holiest"
#: The restatement as a heading ELEMENT. Anchored, so this can never reach into
#: a mid-chapter heading of the same wording.
LEADING_HEADING = re.compile(r"\A\s*<(h[1-5])\b[^>]*>(.*?)</\1>\s*", re.S | re.I)
#: The restatement as LOOSE TEXT before the first tag — everything up to it, so
#: a partial match can never leave half a title behind.
LEADING_TEXT = re.compile(r"\A[^<]+")


def _leading_label(body_html: str) -> tuple[str, int] | None:
    """The body's leading label and where it ends, in whichever shape it takes."""
    match = LEADING_HEADING.match(body_html)
    if match:
        return text_of(match.group(2)), match.end()
    match = LEADING_TEXT.match(body_html)
    if match:
        return text_of(match.group()), match.end()
    return None


def rewrite(body_html: str, title: str) -> str | None:
    """`body_html` without its restated heading, or None to leave it alone.

    Kept a pure function of the two stored values so the fixture refresh that
    ships alongside is produced by this exact code rather than a re-reading of
    it — the two must land on the same bodies, byte for byte, or the
    ``chapter_drift`` warning this change exists to clear comes straight back
    on the next deploy.
    """
    found = _leading_label(body_html or "")
    if not found:
        return None
    label, end = found
    if not _restates(label, title):
        return None
    body = body_html[end:]
    if not body.strip():
        return None  # the label was the whole chapter; leave it something
    return body


def strip_restated_headings(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    # `body_text` is deferred alongside the vector: `rewrite` reads only
    # `body_html` and `title`, so the stored text is written or left alone,
    # never compared — unlike 0085, where it IS the comparison and cannot be.
    query = Chapter.objects.filter(book__slug=SLUG).defer("search_vector", "body_text")
    for chapter in query:
        body = rewrite(chapter.body_html, chapter.title)
        if body is None:
            continue
        chapter.body_html = body
        chapter.body_text = html_to_text(body)
        chapter.word_count = word_count(body)
        chapter.search_vector = None
        chapter.citations_indexed_at = None
        chapter.save(
            update_fields=[
                "body_html",
                "body_text",
                "word_count",
                "search_vector",
                "citations_indexed_at",
            ]
        )


def noop(apps, schema_editor):
    """Deliberately irreversible — reversing would print every title twice again."""


class Migration(migrations.Migration):
    dependencies = [("library", "0091_purpose_in_prayer_chapter_titles")]
    operations = [migrations.RunPython(strip_restated_headings, noop)]
