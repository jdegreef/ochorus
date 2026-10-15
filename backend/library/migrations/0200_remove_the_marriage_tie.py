"""Remove William J. Seymour's "The Marriage Tie" sermon.

Withdrawn at the founder's decision after it shipped in #5999: of Seymour's
signed pieces it is the least representative and the most pastorally risky
(it treats remarriage after divorce as adultery), and his other eleven sermons
carry his message.

A migration AND a fixture removal, as with every content withdrawal here (see
0073): the seeds only create-or-update, so deleting the fixture alone would
leave the live row in place. The author keeps his other sermons, so only the
sermon row goes.
"""

from __future__ import annotations

from django.db import migrations

SERMON_SLUG = "the-marriage-tie"
AUTHOR_SLUG = "william-j-seymour"


def remove(apps, schema_editor):
    Sermon = apps.get_model("library", "Sermon")
    Sermon.objects.filter(slug=SERMON_SLUG, author__slug=AUTHOR_SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [("library", "0199_scene_portraits")]

    # Reverse is a no-op: the fixture is gone in the same commit, so there is
    # nothing to restore, and an unrelated rollback shouldn't be blocked.
    operations = [migrations.RunPython(remove, migrations.RunPython.noop)]
