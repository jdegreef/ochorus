"""Rejoin the two 0092 leaves that landed from parallel branches.

#1189 (`0092_strip_restated_chapter_headings`) and #1190
(`0092_drop_index_chapters`) were each written against `0091` and merged within
six minutes of each other, so `main` carried two leaf nodes and
`manage.py release` refused to migrate anything at all:

    CommandError: Conflicting migrations detected; multiple leaf nodes in the
    migration graph: (0092_drop_index_chapters,
    0092_strip_restated_chapter_headings in library).

Empty on purpose — this only rejoins the graph. The two data migrations are
independent and commute: one deletes four back-matter chapters, the other
rewrites `body_html` on chapters that restate their own title. Their only
possible overlap is a row the first deletes and the second would have skipped,
so neither order changes the result.
"""

from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0092_drop_index_chapters"),
        ("library", "0092_strip_restated_chapter_headings"),
    ]

    operations = []
