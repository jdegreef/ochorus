"""Rejoin the migration graph after two 0123 leaves landed in parallel.

#1632 healed the earlier 0121/0122 split by giving its data migration both as
dependencies; #1633 healed the same split with an explicit merge. Each was
correct alone, both merged, and main had two leaves again — so
`makemigrations --check` failed on main and on every branch cut from it.

Empty by construction: a merge migration only rejoins the graph.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0123_merge_0121_recase_chapter_titles_0122_quotetopic_rls"),
        ("library", "0123_reimport_secret_of_guidance"),
    ]

    operations = []
