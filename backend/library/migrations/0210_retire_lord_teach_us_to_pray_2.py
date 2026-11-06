"""Retire *Lord, Teach Us to Pray* (``lord-teach-us-to-pray-2``) as a duplicate.

Its four chapters are Lessons 1-4 of *With Christ in the School of Prayer*
(``school-of-prayer``, chapters 2-5 — chapter 1 is the Preface), stored as a
modernized paraphrase with ESV-swapped Scripture, while the library carries the
whole school in Murray's own words. The founder chose to retire it rather than
rebuild it (2026-11).

* **Unpublish every edition.** ``seed_books`` treats ``is_published`` as
  create-only, so the fixture's ``false`` would never reach the live rows; this
  does (the 0164 shape). The rows stay: readers' progress, bookmarks and
  highlights are keyed by slug, and the book's row is what they resolve to.
* **Move the plan days.** ``seed_plans`` creates a curated plan's days once and
  never re-syncs them, so the live *Foundations in Prayer* days still name the
  retired book. Each moves to the same lesson in ``school-of-prayer`` (order + 1)
  — same day numbers, so readers' plan progress needs no renumbering. A plan in
  a language whose ``school-of-prayer`` lacks the target chapter is left alone.

The topic shelf needs nothing here: ``seed_topics`` deletes members topic_seed no
longer lists. Quotes re-point on the next ``seed_quotes``. The successor map is
frozen here on purpose (``corrections.RETIRED_BOOKS`` is the living copy).
Irreversible by design.
"""

from __future__ import annotations

from django.db import migrations

RETIRED = {"lord-teach-us-to-pray-2": ("school-of-prayer", 1)}


def retire(apps, schema_editor):
    Book = apps.get_model("library", "Book")
    Chapter = apps.get_model("library", "Chapter")
    PlanDay = apps.get_model("library", "PlanDay")
    Book.objects.filter(slug__in=RETIRED, is_published=True).update(is_published=False)
    for old, (new, offset) in RETIRED.items():
        for day in PlanDay.objects.filter(book_slug=old).select_related("plan"):
            target = day.chapter_order + offset
            if not Chapter.objects.filter(
                book__slug=new, book__language=day.plan.language, order=target
            ).exists():
                continue
            day.book_slug = new
            day.chapter_order = target
            day.save(update_fields=["book_slug", "chapter_order"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("library", "0209_qa_stepping_stones_2_titles")]
    operations = [migrations.RunPython(retire, noop)]
