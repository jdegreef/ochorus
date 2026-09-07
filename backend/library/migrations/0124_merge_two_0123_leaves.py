"""Rejoin the migration graph after two 0123 leaves landed in parallel.

Both PRs were healing the SAME earlier 0121/0122 split, and the asymmetry in
how is why neither noticed the other. #1633 added a dedicated empty merge node,
the by-the-book move. #1632 healed it implicitly instead, by widening its data
migration to depend on both leaves. So they merged cleanly and left main with
two leaves — `makemigrations --check` then failed on main and on every branch
cut from it.

Had both taken the by-the-book route they could not have collided silently:
`makemigrations --merge` names its output deterministically, so both would have
written `0123_merge_0121_..._0122_...py` and git would have raised an add/add
conflict at merge time. A merge node wants to be its own migration for exactly
that reason — the filename is what makes the fork visible.

Empty by construction: a merge migration only rejoins the graph.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0123_merge_0121_recase_chapter_titles_0122_quotetopic_rls"),
        ("library", "0123_reimport_secret_of_guidance"),
    ]

    operations = []
