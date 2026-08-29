"""Put every stored ``word_count`` back in step with its own ``body_html``.

``word_count`` is DERIVED — every importer sets it with
``ingest.word_count(body_html)``, the tokens left once tags become spaces — and
the reader spends it: the per-chapter reading-time estimate in the TOC drawer,
the length sort on the shelf, the word totals under a book and under a reading
plan. It is the same defect class as 0085_rederive_body_text, one step worse.

``body_text`` at least has a keeper: ``Chapter.save()`` and ``Sermon.save()``
recompute it on every write, so only the paths that bypass ``save()`` can drift.
NOTHING recomputes ``word_count`` after creation — ``backfill_word_count`` says
so in its own docstring, and deliberately fills only rows sitting at zero,
mirroring ``backfill_body_text``'s "fill what is empty" contract. So a count
that is present but WRONG is invisible to every step of the release chain, on
every deploy, forever: ``loaddata`` writes it verbatim, the backfill skips it,
and an edit to the body it describes does not disturb it.

381 rows across 83 files were in that state in the committed fixture, in two
classes:

  * STALE (237 rows, all English) — the count describes the ``body_html`` as it
    stood before a later prose repair. Each fits exactly one earlier revision of
    its own file: the 20 drifted chapters of `the-inner-chamber.en` and the 29
    of `the-unselfishness-of-god.en` were both last right before #854 closed
    their line-break hyphens, which fuses two half-words into one and drops the
    count by one — and nothing re-derived it.
  * MIS-DERIVED AT BIRTH (144 rows — every non-English row that drifted, across
    ar/es/hi/lg/pt/sw/uk) — the count equals ``len(html_to_text(body_html)
    .split())``, the OTHER text derivation here, the one ``body_text`` uses. It
    joins across inline tags where ``ingest.word_count`` spaces them, so
    `لأجلك<em>.</em>` is one token to the first rule and two to the second.
    These matched no revision: they were wrong in the commit that introduced
    them.

The fixture is repaired in the same commit and gated from here on by
``tests_fixture.WordCountDerivationTests`` — but a fresh build loads the
fixture and a deployed database does not, and those rows were dumped FROM a
database, so the same wrong counts are sitting in production. Hence this.

Every row and every language, like 0085. This applies no rule of its own and
makes no judgement about prose: it counts the words in a body, which is as true
of Arabic or Luganda as of English. A row already in step is not written, so on
a database that is already correct this does nothing at all.

``search_vector``, ``body_text`` and ``citations_indexed_at`` are deliberately
left alone — the one place this departs from 0085, and for 0085's own stated
reason read the other way. 0085 NULLed the vector because it rewrote
``body_text``, which IS the indexed text, so a repaired row would otherwise
keep matching searches for text it no longer held. Here ``body_html`` does not
move, so ``body_text`` does not move, so the vector and the citation stamp
still describe exactly the text they were built from. NULLing them would blank
a correct index and make 381 rows unsearchable until the next
``backfill_search_vectors`` — a regression bought for nothing. ``Chapter.save()``
agrees: it skips the vector rebuild when a scoped save touches no indexed
field, and ``word_count`` is not one.
"""

from __future__ import annotations

from django.db import migrations

from library.ingest import word_count


def rederive(apps, schema_editor):
    for model_name in ("Chapter", "Sermon"):
        model = apps.get_model("library", model_name)
        # `.only(...)`: `search_vector` is the largest column on the row and
        # nothing here reads or writes it — same reason 0085 deferred it.
        rows = model.objects.only("pk", "body_html", "word_count")
        for row in rows.iterator(chunk_size=200):
            # Same rule as the fixture command and its gate: a row with no
            # `body_html` has nothing to derive FROM, and deriving 0 would blank
            # a count rather than repair it.
            if not row.body_html:
                continue
            words = word_count(row.body_html)
            if words == row.word_count:
                continue
            # `update()` rather than `save(update_fields=...)`: it writes the one
            # column without re-sending the body, and it cannot be mistaken for
            # a save that was expected to ripple. Nothing here should ripple.
            model.objects.filter(pk=row.pk).update(word_count=words)


def noop(apps, schema_editor):
    """Deliberately irreversible.

    Reversing would put back reading times and plan lengths that describe text
    the reader is not being shown. There is nothing to go back to worth having.
    """


class Migration(migrations.Migration):
    dependencies = [("library", "0093_merge_index_chapters_and_restated_headings")]
    operations = [migrations.RunPython(rederive, noop)]
