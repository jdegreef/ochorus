"""Reshape the first four Key Teachings volumes, and move their reading plan.

0170 reshaped nine volumes and left Simpson, Edwards, Baxter and Nee at 22
chapters because "The Key Teachings: Four Teachers" is built from their
chapters. Their manuscripts are now reshaped too (Simpson 20, Edwards 24,
Baxter 19, Nee 23), so this migration does 0170's work for them — rebuild
the chapters from the fixture while the live book still has its old shape,
and move every reader row to where its paragraph now lives — and then moves
the plan:

* **Plan days.** `seed_plans` creates a curated plan's days once and never
  re-syncs them, so every plan that reads one of these books gets its days
  rebuilt: the same books in the same order, each now read through its new
  chapters. A plan that does not read ALL of a reshaped book's old chapters is
  a hand-made span this migration cannot map, and is left alone.
* **Plan progress.** A reader's ``done`` days are renumbered through the
  chapter map. A new day made of several old ones is done only if all of them
  were; a brand-new chapter's day is done when the reader has already done the
  days either side of it in that book (they read past it).
* **A new slug.** Completed days UNION across devices (`_upsert_plan_progress`)
  and each device re-sends its whole cached list, so a device still holding
  the old numbering would tick the wrong days the moment it synced. The plan
  therefore moves to a new slug (`RENAMES`), carrying the renumbered progress;
  a stale device's old numbers land on the retired slug, which no plan reads.
  The reader's own cache is moved the same way on the device
  (`frontend/src/lib/planMoves.ts`), and render.yaml redirects the old URL.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from django.db import migrations

DATA = Path(__file__).resolve().parent / "data" / "key_teachings_reshape_first_four.json"
RENAMES = {"the-key-teachings-four-teachers": "key-teachings-four-teachers"}

# The chapter rebuild and the reader move are 0170's, unchanged.
_0170 = importlib.import_module("library.migrations.0170_reshape_key_teachings")


def reshape(apps, schema_editor):
    specs = json.loads(DATA.read_text(encoding="utf-8"))
    Book = apps.get_model("library", "Book")
    # Which books this run actually reshapes: 0170's guard (still the old
    # 22-chapter shape) is re-checked here so the plan moves with them only.
    live = {
        slug for slug in specs
        if Book.objects.filter(slug=slug, language="en").exists()
        and Book.objects.get(slug=slug, language="en").chapters.count() == _0170.OLD_COUNT
    }
    with _patched_data():
        _0170.reshape(apps, schema_editor)
    reshaped = {
        slug: {int(k): v for k, v in spec["old_to_new"].items()}
        for slug, spec in specs.items()
        if slug in live
        and Book.objects.get(slug=slug, language="en").chapters.count() == spec["new_count"]
    }
    if reshaped:
        move_plans(apps, reshaped)


class _patched_data:
    """Point 0170 at this migration's map (same schema) for one call."""

    def __enter__(self):
        self.saved, _0170.DATA = _0170.DATA, DATA

    def __exit__(self, *exc):
        _0170.DATA = self.saved


def move_plans(apps, reshaped: dict[str, dict[int, int]]):
    Plan = apps.get_model("library", "Plan")
    PlanDay = apps.get_model("library", "PlanDay")
    PlanProgress = apps.get_model("reading", "PlanProgress")
    Chapter = apps.get_model("library", "Chapter")

    new_orders = {
        slug: list(
            Chapter.objects.filter(book__slug=slug, book__language="en")
            .order_by("order").values_list("order", flat=True)
        )
        for slug in reshaped
    }
    # English plans only: the chapters rebuilt are the English edition's, and a
    # plan in another language reads that language's own books.
    touched = set(
        PlanDay.objects.filter(book_slug__in=reshaped, plan__language="en")
        .values_list("plan__slug", flat=True)
    )
    for plan_slug in sorted(touched):
        rows = list(Plan.objects.filter(slug=plan_slug, language="en"))
        old_days = [
            (d.day, d.book_slug, d.chapter_order)
            for d in PlanDay.objects.filter(plan=rows[0]).order_by("day")
        ]
        # Only a plan that reads every old chapter of each reshaped book it
        # touches can be mapped; a hand-picked span is left as it is.
        if any(
            sorted(o for _, b, o in old_days if b == slug) != sorted(reshaped[slug])
            for slug in {b for _, b, _ in old_days if b in reshaped}
        ):
            continue

        new_days: list[tuple[str, int]] = []
        seen_books: set[str] = set()
        for _, book, order in old_days:
            if book in reshaped:
                if book not in seen_books:
                    new_days += [(book, o) for o in new_orders[book]]
                    seen_books.add(book)
            else:
                new_days.append((book, order))
        index = {spot: i + 1 for i, spot in enumerate(new_days)}

        # old day -> new day, and each new day's old days
        to_new: dict[int, int] = {}
        sources: dict[int, list[int]] = {}
        for day, book, order in old_days:
            spot = (book, reshaped[book][order]) if book in reshaped else (book, order)
            to_new[day] = index[spot]
            sources.setdefault(index[spot], []).append(day)

        new_slug = RENAMES.get(plan_slug, plan_slug)
        for plan in rows:
            if new_slug != plan_slug:
                plan.slug = new_slug
                plan.save(update_fields=["slug", "updated_at"])
            plan.days.all().delete()
            PlanDay.objects.bulk_create([
                PlanDay(plan=plan, day=i + 1, book_slug=b, chapter_order=o)
                for i, (b, o) in enumerate(new_days)
            ])

        for progress in PlanProgress.objects.filter(plan_slug=plan_slug):
            done = set(progress.done or [])
            new_done = {n for n, olds in sources.items() if all(d in done for d in olds)}
            for n in range(1, len(new_days) + 1):
                if n in sources:
                    continue  # a brand-new chapter: done if read past on both sides
                book = new_days[n - 1][0]
                before = n - 1 >= 1 and new_days[n - 2][0] == book and (n - 1) in new_done
                after = n + 1 <= len(new_days) and new_days[n][0] == book and (n + 1) in new_done
                if before and after:
                    new_done.add(n)
            progress.done = sorted(new_done)
            progress.plan_slug = new_slug
            progress.save(update_fields=["plan_slug", "done", "updated_at"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("library", "0171_book_cover_byline"),
        ("reading", "0031_progress_furthest_and_pct"),
    ]

    operations = [
        migrations.RunPython(reshape, noop),
    ]
