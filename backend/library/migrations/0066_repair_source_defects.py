"""Repair two source defects in The Person and Work of the Holy Spirit.

The fixture is fixed in the same commit, which covers a database built from
scratch. This covers the rows already in production, because `seed_books`
creates chapters only for a book it has never seen — for a book that already
exists it reports body drift and changes nothing. Without this migration the
fixture and production would simply disagree.

Chapter rows in EVERY language are repaired: the translations reproduced both
defects faithfully (correctly — a translator dropping them silently would have
hidden the problem), so the same repair applies to each, and
`library/source_fixes` no-ops on any text it does not match.

`search_vector` is NULLed on every row touched rather than left alone: these
are historical model instances, so no `save()` hook runs and the stored vector
would otherwise stay valid-looking but STALE, and search would keep matching
the deleted duplicate text. The release chain's `backfill_search_vectors`
repairs NULLs, so nulling is what puts them back in step.
"""

from __future__ import annotations

from django.db import migrations

from library.source_fixes import SOURCE_FIXES, apply_source_fixes

SLUG = "the-person-and-work-of-the-holy-spirit"
ORDERS = sorted(order for slug, order in SOURCE_FIXES if slug == SLUG)


def repair(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    rows = Chapter.objects.filter(book__slug=SLUG, order__in=ORDERS)
    for chapter in rows.select_related("book"):
        fixed = apply_source_fixes(SLUG, chapter.order, chapter.body_html)
        if fixed == chapter.body_html:
            continue
        chapter.body_html = fixed
        # Chapter.save()'s hooks don't exist on the historical model, so
        # derive what they would have derived.
        import re

        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fixed)).strip()
        chapter.body_text = text
        chapter.word_count = len(text.split())
        chapter.search_vector = None
        chapter.save(
            update_fields=["body_html", "body_text", "word_count", "search_vector"]
        )


def noop(apps, schema_editor):
    """Deliberately irreversible.

    Reversing would mean restoring a fabricated quotation of John 7:17 and a
    verse printed under the wrong reference. There is nothing to go back to
    that is worth having.
    """


class Migration(migrations.Migration):
    dependencies = [("library", "0065_search_click_log_rls")]
    operations = [migrations.RunPython(repair, noop)]
