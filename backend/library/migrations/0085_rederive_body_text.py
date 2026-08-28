"""Put every stored ``body_text`` back in step with its own ``body_html``.

``body_text`` is DERIVED — ``Chapter.save()`` and ``Sermon.save()`` both set it
to ``html_to_text(body_html)`` — and it is what full-text search indexes and
what snippets are rendered from. Nothing repairs a wrong one. ``loaddata``
writes it verbatim (it never calls ``save()``), and ``backfill_body_text``
filters on ``body_text=""``, so a value that is present but wrong is invisible
to every step of the release chain, on every deploy, forever.

490 rows across 58 files were in that state in the committed fixture, in four
ways: quote marks left behind by a sweep that converted `body_html` only;
`man&#x27;s` where the rule gives `man's`; `الخيرات. »` for `الخيرات.»`, from an
older derivation that spaced every tag rather than the block-level ones; and 36
chapters carrying no `body_text` at all. The fixture is repaired in the same
commit and gated by `tests_fixture.BodyTextDerivationTests` — but a fresh build
loads the fixture and a deployed database does not, and those rows were dumped
FROM a database, so the same values are sitting in production.

Every row and every language, unlike 0084. This applies no rule of its own and
makes no judgement about prose: it recomputes a derived column from its source
column, which is as true of Arabic or Luganda as of English. A row already in
step is not written, so on a database that is already correct this does nothing
at all.

`search_vector` is NULLed on every row it touches, and here that is the whole
point rather than a precaution: `body_text` IS the indexed text, so a repaired
row whose vector was left alone would keep matching searches for the text it no
longer holds. The release chain's `backfill_search_vectors` repairs NULLs.

`word_count` is deliberately untouched: it derives from `body_html`, which this
does not change.
"""

from __future__ import annotations

from django.db import migrations

from library.text import html_to_text


def rederive(apps, schema_editor):
    for model_name in ("Chapter", "Sermon"):
        model = apps.get_model("library", model_name)
        # `search_vector` is written but never read, and it is the largest
        # column on the row — the same reason `apply_body_corrections` defers
        # it. `body_text` cannot be deferred: it is what we compare against.
        stamped = model_name == "Chapter"
        for row in model.objects.defer("search_vector").iterator(chunk_size=100):
            # Same rule as the fixture command and its gate: a row with no
            # `body_html` has nothing to derive FROM, and deriving "" would
            # blank a `body_text` rather than repair it.
            if not row.body_html:
                continue
            derived = html_to_text(row.body_html)
            if derived == row.body_text:
                continue
            row.body_text = derived
            row.search_vector = None
            fields = ["body_text", "search_vector"]
            if stamped:
                # `index_citations` scans `body_text` and is INCREMENTAL on this
                # stamp, so a repaired row keeps the citations extracted from
                # the text it no longer holds — `jesus-himself-2.en` ch2 would
                # keep five where its new text yields four, and a fresh build
                # and the deployed database would disagree permanently.
                # `Chapter.save()` clears it whenever `body_html` moves; here
                # `body_html` does not move and `body_text` does, which is the
                # one case that rule does not cover.
                row.citations_indexed_at = None
                fields.append("citations_indexed_at")
            row.save(update_fields=fields)


def noop(apps, schema_editor):
    """Deliberately irreversible.

    Reversing would put back a search index that matches text the page does not
    show. There is nothing to go back to that is worth having.
    """


class Migration(migrations.Migration):
    dependencies = [("library", "0084_repair_mixed_quotes")]
    operations = [migrations.RunPython(rederive, noop)]
