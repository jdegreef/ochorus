"""Repair the inverted "do drink" in the Luganda "All of Grace" ch01.

Spurgeon's "find fault if you please; but do drink of the water of life" was
translated with the NEGATIVE imperative — "naye tonywako amazzi ag'obulamu",
"but do NOT drink of the water of life" — so the chapter's closing appeal said
the opposite of the book's whole invitation. The affirmative is "naye nywako"
(the same correction the Luganda all-of-grace-guide article already carries).
The seven other editions translate it affirmatively; only Luganda is touched.

The fixture is corrected in the same commit, which covers a database built from
scratch. This covers the row already in production: `seed_books` never
re-syncs an existing book's chapters, so without it prod and the fixture would
simply disagree (and the deploy log would report chapter drift).

Same shape as 0069: `body_text` gets the SAME string replacement rather than a
re-derivation (for this row the two are identical — the stored text equals
`html_to_text(body_html)` before and after — but the replacement cannot drift
from the fixture on entities or whitespace). `word_count` is unaffected: one
word becomes one word. `search_vector` is NULLed so the release chain's
`backfill_search_vectors` rebuilds it; a historical model runs no `save()`
hook, and the stale vector would keep indexing "tonywako".
"""

from __future__ import annotations

from django.db import migrations

SLUG = "all-of-grace"
LANGUAGE = "lg"
ORDER = 1
WRONG = "naye tonywako amazzi ag'obulamu"
RIGHT = "naye nywako amazzi ag'obulamu"


def repair(apps, schema_editor):
    Chapter = apps.get_model("library", "Chapter")
    for chapter in Chapter.objects.filter(
        book__slug=SLUG, book__language=LANGUAGE, order=ORDER
    ):
        if WRONG not in chapter.body_html and WRONG not in chapter.body_text:
            continue
        chapter.body_html = chapter.body_html.replace(WRONG, RIGHT)
        chapter.body_text = chapter.body_text.replace(WRONG, RIGHT)
        chapter.search_vector = None
        chapter.save(update_fields=["body_html", "body_text", "search_vector"])


def noop(apps, schema_editor):
    """Deliberately irreversible: there is no reason to restore "do not drink"."""


class Migration(migrations.Migration):
    dependencies = [("library", "0158_faith_healing_biography_authors")]
    operations = [migrations.RunPython(repair, noop)]
