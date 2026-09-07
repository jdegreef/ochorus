"""Trim the publisher's book catalogue that leaked into `around-the-wicket-gate`
ch11 ("To those who have Believed").

The importer appended an American Tract Society catalogue — 94 paragraphs of
priced book advertisements ("Any book in this Catalogue sent postage prepaid…",
"PUBLISHED BY THE American Tract Society…") — to Spurgeon's ten-paragraph closing
exhortation, separated from it by an `<hr/>`. It is back-matter, not the author's
text; the reader currently ends the book on a Victorian bookseller's price list.

Surfaced while translating the book into Spanish: an es edition would have carried
the catalogue too, and `tests_translation_markup` pins the es tag sequence to its
English source, so the English had to be trimmed to keep the two coherent. The
fixture is trimmed in the same commit (a fresh DB loads it AFTER migrate runs, so
this migration no-ops there — guarded on the catalogue marker being present).

Same shape as 0120/0069: `seed_books` never rewrites an existing book's chapter
bodies, so without this the deployed row keeps the catalogue. A historical model
runs no `save()` hook, so `body_text` and `word_count` are re-derived here with
the canonical helpers (`library.text`), and `search_vector` is nulled — the body
shrank by ~90%, and the release chain's `backfill_search_vectors` repairs NULLs.
"""

from __future__ import annotations

from django.db import migrations

from library.text import html_to_text, word_count

SLUG, ORDER = "around-the-wicket-gate", 11
# The catalogue opens with this line, one `<hr/>` after Spurgeon's last paragraph.
MARKER = "Any book in this Catalogue"


def trim(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    for chapter in Chapter.objects.filter(book__slug=SLUG, order=ORDER):
        html = chapter.body_html or ""
        if MARKER not in html or "<hr/>" not in html:
            continue  # already trimmed (fresh DB from fixture), or not this body
        kept = html[: html.index("<hr/>")].rstrip()
        if not kept.endswith("</p>"):
            continue  # boundary not where expected — leave it for a human
        chapter.body_html = kept
        chapter.body_text = html_to_text(kept)
        chapter.word_count = word_count(kept)
        chapter.search_vector = None
        chapter.save(
            update_fields=["body_html", "body_text", "word_count", "search_vector"]
        )


def noop(apps, schema_editor):
    """Deliberately irreversible — the removed rows are a bookseller's price list,
    not the author's text; there is nothing worth restoring."""


class Migration(migrations.Migration):
    dependencies = [("library", "0125_merge_two_0124_leaves")]
    operations = [migrations.RunPython(trim, noop)]
