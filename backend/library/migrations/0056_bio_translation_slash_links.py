"""Apply the trailing-slash link fix to TRANSLATED bios as well.

Migration 0054 fixed the cross-link in ``Author.bio_html`` and stopped there.
Translated prose lives in its own row (``AuthorTranslation.bio_html``, one per
language) and carries its own copy of the same hand-written markup, so the
Swahili and Luganda biographies kept pointing at the no-slash URL — which is
the empty SPA shell, not the page.

Caught by the build-output guard (``src/lib/href.test.ts``) after 0054 had
deployed: English and Spanish were clean while ``/sw/`` and ``/lg/`` still
carried the bare link. Worth remembering when fixing prose: an author's text
exists in as many rows as there are languages, and the English row is only the
first of them.

Idempotent and reversible, and it re-runs 0054's Author fix so a database that
somehow missed it converges either way.
"""

from __future__ import annotations

from django.db import migrations

OLD = 'href="/authors/susanna-wesley"'
NEW = 'href="/authors/susanna-wesley/"'


def _swap(model, field, old, new):
    for row in model.objects.filter(**{f"{field}__contains": old}):
        setattr(row, field, getattr(row, field).replace(old, new))
        row.save(update_fields=[field])


def add_slashes(apps, schema_editor):
    _swap(apps.get_model("library", "Author"), "bio_html", OLD, NEW)
    _swap(apps.get_model("library", "AuthorTranslation"), "bio_html", OLD, NEW)


def remove_slashes(apps, schema_editor):
    _swap(apps.get_model("library", "Author"), "bio_html", NEW, OLD)
    _swap(apps.get_model("library", "AuthorTranslation"), "bio_html", NEW, OLD)


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0055_authortranslation_source_stale"),
    ]

    operations = [
        migrations.RunPython(add_slashes, remove_slashes),
    ]
