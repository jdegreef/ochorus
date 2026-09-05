"""Fix a miscount in George Whitefield's biography on already-seeded databases.

The bio said Whitefield's answer "was three words: 'He is the man.'" — which is
four words. The fixture (authors.json) now carries the corrected text, so fresh
installs are right via ``seed_if_empty``; but ``bio_html`` is a fill-only field
(``author_sync.FILL_ONLY_FIELDS``), so a re-deploy never rewrites an existing
row. This applies the one-word fix to the live row. Idempotent and narrow: it
touches only the exact phrase, only if present.
"""

from __future__ import annotations

from django.db import migrations

_OLD = "given again and again, was three words: “He is the man.”"
_NEW = "given again and again, was four words: “He is the man.”"


def fix(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    a = Author.objects.filter(slug="george-whitefield").first()
    if a and a.bio_html and _OLD in a.bio_html:
        a.bio_html = a.bio_html.replace(_OLD, _NEW)
        a.save(update_fields=["bio_html"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0116_article_word_count"),
    ]

    operations = [
        migrations.RunPython(fix, noop),
    ]
