"""Clear any biography prose stored on an imprint byline (e.g. "Ochorus Originals").

An imprint is a house byline, not a person: it authors the compiled biography
anthologies but is deliberately kept off the Biographies shelf, excluded from the
admin "authors without a bio" report and from bio-readiness counts, and its
``same_as`` is never populated (see the ``Author`` model notes). A bio makes it
read like a person, which it is not — so a byline carries none.

The fixture already ships imprints with empty ``bio``/``bio_html``/``faq``, and
``author_sync`` only ever *fills* an empty bio (never overwrites), so a bio typed
into an imprint row through the Django admin on a live database is never reverted
by a deploy. ``faq`` is fixture-wins but the imprint row OMITS the key, so sync
leaves a live value untouched there too. This one-time data migration clears the
biographical surface on existing installs; on a fresh database the fields are
already empty (the fixture loads right after migrate), so it is a no-op.
Idempotent — it re-runs harmlessly on every future deploy.

Covers the Author row and any AuthorTranslation rows (an imprint carries no
translated bio either). Clearing a bio touches no derived column — only the
author *name* ripples into search vectors — so a ``.update()`` that bypasses
``save()`` is safe here.
"""

from __future__ import annotations

from django.db import migrations


def clear_imprint_bios(apps, schema_editor):
    Author = apps.get_model("library", "Author")
    AuthorTranslation = apps.get_model("library", "AuthorTranslation")

    imprints = Author.objects.filter(is_imprint=True)
    imprints.exclude(bio="", bio_html="", faq=[]).update(bio="", bio_html="", faq=[])
    AuthorTranslation.objects.filter(author__in=imprints).exclude(
        bio="", bio_html="", faq=[]
    ).update(bio="", bio_html="", faq=[])


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0136_merge_author_faq_milestones"),
    ]

    operations = [
        migrations.RunPython(clear_imprint_bios, migrations.RunPython.noop),
    ]
