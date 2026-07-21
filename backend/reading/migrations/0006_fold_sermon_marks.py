"""Fold SermonMarks (PR #293's parallel store) into ChapterMarks(kind=sermon).

PR #293 shipped sermon-mark sync as its own model; the reading-layer
unification (roadmap #10) makes sermons a kind of ChapterMarks instead, so
one machine covers books and sermons. This migration rescues every row the
parallel store accumulated on prod — union-merged with any unified row that
already exists (mark lists are unioned; nothing is dropped) — then removes
the model. The old API endpoint lives on as a compat shim writing to the
unified table (views.SermonMarksView), so stale PWA bundles keep syncing.

Uses merge_mark_lists imported live: the union rule must match what the
running MergeView applies, and this runs exactly once per database.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    from reading.marks import merge_mark_lists

    SermonMarks = apps.get_model("reading", "SermonMarks")
    ChapterMarks = apps.get_model("reading", "ChapterMarks")

    for sm in SermonMarks.objects.all().iterator():
        existing = ChapterMarks.objects.filter(
            profile_id=sm.profile_id,
            kind="sermon",
            book_slug=sm.sermon_slug,
            chapter_order=1,
        ).first()
        marks = sm.marks or []
        if existing:
            existing.marks = merge_mark_lists(existing.marks or [], marks)
            existing.language = existing.language or sm.language
            existing.save(update_fields=["marks", "language", "updated_at"])
        elif marks:
            ChapterMarks.objects.create(
                profile_id=sm.profile_id,
                kind="sermon",
                book_slug=sm.sermon_slug,
                chapter_order=1,
                language=sm.language,
                marks=marks,
                highlights=[],
                notes={},
            )


class Migration(migrations.Migration):
    dependencies = [
        ("reading", "0005_work_kind"),
    ]

    operations = [
        # Fold first (reverse is a no-op: the folded rows simply remain).
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.DeleteModel(name="SermonMarks"),
    ]
