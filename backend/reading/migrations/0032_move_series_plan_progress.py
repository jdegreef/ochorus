"""Carry readers' progress from the retired young-reader series plans.

The Rooted, Daughters of the King and Sons of the King series used to offer one
30-day plan per book (``<series>-book-<n>-30-days``, reading each book's
"Day 1" … "Day 30" chapters and skipping its Introduction and Conclusion), plus
a six-book ``rooted-six-months-with-god``. They are now one plan per series —
Rooted as two halves — that reads every chapter of each book in order
(``library.plan_seed.RETIRED_PLANS`` names each successor; ``seed_plans``
deletes the old Plan rows).

Progress is keyed by plan slug and day NUMBER, so it is moved here, once, onto
the successor's numbering. Every book in these series has 32 chapters
(Introduction, Day 1 … Day 30, Conclusion) in every language it ships in, so a
successor's day for (book i of the plan, chapter order c) is ``i * 32 + c``:

* per-book plan day ``d`` is that book's chapter ``d + 1``;
* ``rooted-six-months-with-god`` day ``D`` is the same chapter in the half it
  falls in (``D`` for Books 1–3, ``D - 96`` for Books 4–6).

The Introduction and Conclusion days had no old day, so they start unread. A
reader who already has the successor plan keeps it: days union, the earliest
start wins (the rule ``_upsert_plan_progress`` applies to every sync). The
device moves its own cache by the same map (``frontend/src/lib/planMoves.ts``);
a stale device that re-sends an old slug lands on a retired one, which no plan
reads.

Saved (hearted) retired plans move to their successors too (``move_favorites``).

The map is frozen here rather than imported, as a migration must be.
"""

from __future__ import annotations

from django.db import migrations

CHAPTERS = 32  # Introduction, Day 1 … Day 30, Conclusion
DAYS = 30


def _per_book(series: str, target: str, first: int) -> dict:
    """``<series>-book-<n>-30-days`` for the three books of ``target``."""
    return {
        f"{series}-book-{first + i}-30-days": [
            (target, lambda d, i=i: i * CHAPTERS + d + 1 if 1 <= d <= DAYS else None)
        ]
        for i in range(3)
    }


HALF = 3 * CHAPTERS
MOVES = {
    **_per_book("rooted", "rooted-three-months-books-1-3", 1),
    **_per_book("rooted", "rooted-three-months-books-4-6", 4),
    **_per_book("daughters-of-the-king", "daughters-of-the-king-three-months", 1),
    **_per_book("sons-of-the-king", "sons-of-the-king-three-months", 1),
    "rooted-six-months-with-god": [
        ("rooted-three-months-books-1-3", lambda d: d if 1 <= d <= HALF else None),
        ("rooted-three-months-books-4-6", lambda d: d - HALF if HALF < d <= 2 * HALF else None),
    ],
}


def move_progress(apps, schema_editor):
    PlanProgress = apps.get_model("reading", "PlanProgress")
    for old_slug, targets in MOVES.items():
        for old in PlanProgress.objects.filter(plan_slug=old_slug):
            moves = [
                (new_slug, {n for d in (old.done or []) if (n := day_map(d)) is not None})
                for new_slug, day_map in targets
            ]
            # A split plan starts only the halves the reader reached; one who
            # had ticked nothing yet starts the first.
            moves = [m for m in moves if m[1]] or moves[:1]
            for new_slug, carried in moves:
                row = PlanProgress.objects.filter(
                    profile_id=old.profile_id, plan_slug=new_slug
                ).first()
                if row is None:
                    PlanProgress.objects.create(
                        profile_id=old.profile_id,
                        plan_slug=new_slug,
                        started_at=old.started_at,
                        done=sorted(carried),
                    )
                else:
                    row.done = sorted(set(row.done or []) | carried)
                    row.started_at = min(row.started_at, old.started_at)
                    row.save(update_fields=["done", "started_at", "updated_at"])
            old.delete()


def move_favorites(apps, schema_editor):
    """A saved (hearted) retired plan becomes its successor(s), saved.

    The old heart gets a tombstone, so a device that still holds it does not
    re-create it on its next sign-in merge (a heart saved before the tombstone
    is dropped as stale — see ``Removal``). A successor the reader had
    deliberately un-hearted stays un-hearted.
    """
    from django.utils import timezone

    Favorite = apps.get_model("reading", "Favorite")
    Removal = apps.get_model("reading", "Removal")
    now = timezone.now()
    for fav in Favorite.objects.filter(kind="plan", slug__in=MOVES):
        for new_slug, _ in MOVES[fav.slug]:
            unhearted = Removal.objects.filter(
                profile_id=fav.profile_id, domain="favorite", kind="plan", slug=new_slug
            ).exists()
            if not unhearted:
                Favorite.objects.get_or_create(
                    profile_id=fav.profile_id, kind="plan", slug=new_slug
                )
        Removal.objects.update_or_create(
            profile_id=fav.profile_id,
            domain="favorite",
            kind="plan",
            slug=fav.slug,
            chapter_order=0,
            paragraph_index=0,
            defaults={"removed_at": now},
        )
        fav.delete()


def move(apps, schema_editor):
    move_progress(apps, schema_editor)
    move_favorites(apps, schema_editor)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("reading", "0031_progress_furthest_and_pct"),
    ]

    operations = [
        migrations.RunPython(move, noop),
    ]
