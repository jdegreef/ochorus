"""Give in-prose author cross-links their trailing slash.

Biography prose can contain hand-written links to other library pages. The
no-slash form of a detail URL is not the page — it falls through to the SPA
catch-all and serves an empty shell (no title, no content), so a link written
that way sends readers and crawlers to nothing. One such link exists today:
John Wesley's biography links to Susanna Wesley.

The fixture is corrected too, but that only helps a fresh database:
``seed_books`` sets ``bio_html`` in ``get_or_create`` defaults, i.e. on CREATE
only, so an author already in production keeps the old prose. Hence this.

Deliberately a targeted string replace rather than a blanket regex over all
``bio_html``: it is reversible, cannot touch asset URLs or external links, and
leaves prose whose wording has since been edited untouched.
"""

from __future__ import annotations

from django.db import migrations

# (slug, old fragment, new fragment)
LINK_FIXES = [
    (
        "john-wesley",
        'href="/authors/susanna-wesley"',
        'href="/authors/susanna-wesley/"',
    ),
]


def add_slashes(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    for slug, old, new in LINK_FIXES:
        for author in Author.objects.filter(slug=slug, bio_html__contains=old):
            author.bio_html = author.bio_html.replace(old, new)
            author.save(update_fields=["bio_html"])


def remove_slashes(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    for slug, old, new in LINK_FIXES:
        for author in Author.objects.filter(slug=slug, bio_html__contains=new):
            author.bio_html = author.bio_html.replace(new, old)
            author.save(update_fields=["bio_html"])


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0053_three_new_biography_authors"),
    ]

    operations = [
        migrations.RunPython(add_slashes, remove_slashes),
    ]
