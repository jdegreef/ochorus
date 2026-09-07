"""Drop the restated <h2> that opens `absolute-surrender` chapter 3.

ch03's body opened with an `<h2>` repeating the chapter title ("SEPARATED UNTO
THE HOLY GHOST" against the title "Separated unto the Holy Spirit"), so the
reader printed the title twice. `strip_restated_headings` (migration 0092) missed
it because its title rule sees "Ghost" != "Spirit"; but it is the same
restatement, and every translated edition collapses the two into one word
(es/pt "Espíritu/Espírito Santo", ar "الروح القدس"), so the heading exactly
restates the translated title and the fixture gate rejects it.

The fixtures are settled in the same commit (fresh installs load them, so this
no-ops there). This delivers the same drop to the en/pt/ar rows already on prod —
`seed_books` never rewrites an existing chapter body. es is a new edition and
needs no migration. A historical model runs no `save()` hook, so body_text and
word_count are re-derived here and search_vector nulled (the release chain's
backfill repairs the NULL).
"""

from __future__ import annotations

import re

from django.db import migrations

from library.text import html_to_text, word_count

SLUG, ORDER = "absolute-surrender", 3
LEADING_H2 = re.compile(r"^<h2>.*?</h2>\s*", re.S)


def drop_heading(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    for chapter in Chapter.objects.filter(book__slug=SLUG, order=ORDER):
        html = chapter.body_html or ""
        kept = LEADING_H2.sub("", html, count=1)
        if kept == html:
            continue  # already dropped (es / fresh DB) or shape unexpected
        chapter.body_html = kept
        chapter.body_text = html_to_text(kept)
        chapter.word_count = word_count(kept)
        chapter.search_vector = None
        chapter.save(
            update_fields=["body_html", "body_text", "word_count", "search_vector"]
        )


def noop(apps, schema_editor):
    """Irreversible — the removed heading merely restated the title."""


class Migration(migrations.Migration):
    dependencies = [("library", "0126_trim_wicket_gate_catalogue")]
    operations = [migrations.RunPython(drop_heading, noop)]
