"""Finish repairing the-bruised-reed's English rows: stray openers, ch28 title.

Pickering's 1838 printing (re-imported in 0134) sets NO quotation marks, and its
OCR read the margin rules as opening marks — 163 `‘` and 15 `“`, against no
`”`. ``corrections.py`` repairs the ones standing where a letter was lost; the
rest are bare strays, stripped here. Not as a ``BODY_CORRECTIONS`` transform: an
entry reaches every language edition of its slug on every deploy, and a
translation of this book may quote (`‘…’` in sw/hi, `„…“` in uk), so a
content-blind strip would eat it. The English rows need it exactly once, so it
is done once, on them, AFTER the settled form — so the letter-restoring pairs
see their marks first, and the result is the committed fixture's text, which
the deploy's ``apply_body_corrections`` then leaves alone.

The title: ``corrections.chapter_titles`` stopped at 27 (see its comment), so
ch28 kept the importer's first heading line, cut off mid-phrase, and
``seed_books`` never rewrites a chapter. 0134's docstring, which can't be
edited once deployed, also says the old edition had chapters 17-27 under the
wrong titles — it did not; it was one chapter SHORT.

A no-op on a fresh install (the fixture loads after migrate, already repaired).
Derived columns are set by hand as in 0134, and ``search_vector`` NULLed for
``backfill_search_vectors`` to refill on deploy. Not reversible: the stripped
marks are scan damage, not text worth restoring.
"""

from __future__ import annotations

import re

from django.db import migrations

SLUG = "the-bruised-reed"
ORDER = 28
TRUNCATED = "Be encouraged to go on cheerfully, with confidence"
WHOLE = "Be encouraged to go on cheerfully, with confidence of prevailing"

#: An opening mark not preceded by a letter — so not the soft hyphen the scan
#: also read as `‘` INSIDE a word (`con‘ceits`), which the pairs rejoin.
STRAY_OPENER = re.compile(r"(?<![^\W\d_])[‘“]")


def repair(apps, schema_editor):
    from library.corrections import settled_chapter_body
    from library.ingest import word_count
    from library.text import html_to_text

    Chapter = apps.get_model("library", "Chapter")
    for ch in Chapter.objects.filter(book__slug=SLUG, book__language="en"):
        body = STRAY_OPENER.sub("", settled_chapter_body(SLUG, ch.order, ch.body_html))
        title = WHOLE if ch.order == ORDER and ch.title == TRUNCATED else ch.title
        if body == ch.body_html and title == ch.title:
            continue
        ch.body_html = body
        ch.body_text = html_to_text(body)
        ch.word_count = word_count(body)
        ch.title = title
        ch.search_vector = None
        ch.save(update_fields=["body_html", "body_text", "word_count", "title", "search_vector"])


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0137_clear_imprint_bios"),
    ]

    operations = [
        migrations.RunPython(repair, migrations.RunPython.noop),
    ]
