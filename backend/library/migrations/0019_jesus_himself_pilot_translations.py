"""Pilot translations: Jesus Himself in Spanish, Swahili and Luganda.

Prod is never re-seeded, so the translated Book+Chapter rows (and the cleaned
English description — the source page's nav text had been scraped into it)
ship as a data migration. Row content comes from the launch fixture, matched
by slug+language so this stays independent of prod pks. Fixture rows already
carry body_text/word_count derived with the real helpers.
"""

import json
from pathlib import Path

from django.db import migrations

SLUG = "jesus-himself-2"
LANGUAGES = ("es", "sw", "lg")

FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "launch.json"


def _fixture_rows():
    data = json.loads(FIXTURE.read_text())
    authors = {r["pk"]: r["fields"]["slug"] for r in data if r["model"] == "library.author"}
    books = [
        r for r in data
        if r["model"] == "library.book"
        and r["fields"]["slug"] == SLUG
        and r["fields"]["language"] in ("en",) + LANGUAGES
    ]
    chapters_by_book_pk = {}
    for r in data:
        if r["model"] == "library.chapter":
            chapters_by_book_pk.setdefault(r["fields"]["book"], []).append(r["fields"])
    return authors, books, chapters_by_book_pk


def apply(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    Book = apps.get_model("library", "Book")
    Chapter = apps.get_model("library", "Chapter")

    # Fresh installs migrate before seed_if_empty: no library rows yet, and
    # the fixture already contains the translations — nothing to do here.
    if not Book.objects.filter(slug=SLUG, language="en").exists():
        return

    authors, books, chapters_by_book_pk = _fixture_rows()

    for row in books:
        f = row["fields"]
        if f["language"] == "en":
            # Clean the scraped-junk description on the existing English book.
            Book.objects.filter(slug=SLUG, language="en").update(
                description=f["description"]
            )
            continue
        author = Author.objects.get(slug=authors[f["author"]])
        book, _ = Book.objects.update_or_create(
            slug=SLUG,
            language=f["language"],
            defaults={
                "author": author,
                "title": f["title"],
                "subtitle": f["subtitle"],
                "description": f["description"],
                "source_type": f["source_type"],
                "source_url": f["source_url"],
                "cover_url": f["cover_url"],
                "pdf_url": f["pdf_url"],
                "cover_color": f["cover_color"],
                "sort_order": f["sort_order"],
                "is_published": f["is_published"],
            },
        )
        for ch in chapters_by_book_pk.get(row["pk"], []):
            Chapter.objects.update_or_create(
                book=book,
                order=ch["order"],
                defaults={
                    "title": ch["title"],
                    "body_html": ch["body_html"],
                    "body_text": ch["body_text"],
                    "word_count": ch["word_count"],
                },
            )


def revert(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Book.objects.filter(slug=SLUG, language__in=LANGUAGES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("library", "0018_moody_snippet_simpson"),
    ]

    operations = [
        migrations.RunPython(apply, revert),
    ]
