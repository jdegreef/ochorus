"""Rejoin the migration graph after two 0092s landed within four minutes.

#1189 (``0092_strip_restated_chapter_headings``) and #1190
(``0092_drop_index_chapters``) were both cut from ``0091`` and both merged, so
``main`` came out of it with two leaves. Every branch since fails CI on
``makemigrations --check`` with "multiple leaf nodes", and — the part that is
not just an inconvenience — a production ``migrate`` refuses to run at all, so
the deploy chain's ``preDeployCommand`` dies and no deploy can go live.

This is the standard cure (``makemigrations --merge``, as after PR #12): it
carries no operations of its own and only declares that both 0092s come before
whatever follows. It is here rather than in its own PR because ``main`` was red
for every open branch while it sat unfixed, and this branch had to sit on top of
both leaves anyway.

Neither 0092 touches what the other reads — one deletes four back-matter
chapters, the other rewrites 281 chapter bodies — so their order between
themselves does not matter. What DOES matter is that both precede
``0094_rederive_word_count``: it re-derives ``word_count`` from ``body_html``,
and #1189 moved 281 of those bodies.
"""

from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0092_drop_index_chapters"),
        ("library", "0092_strip_restated_chapter_headings"),
    ]
    operations = []
