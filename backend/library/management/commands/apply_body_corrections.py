"""Apply body-text corrections + trailing-number cleanup to stored works.

The same fixes run automatically on every import; this command backfills rows
that were imported before the corrections existed. Idempotent — safe to re-run.
`save()` re-derives body_text and word_count, so search and the reading-time
estimates stay in step with the body this rewrites.

Covers chapters AND sermons. Sermons joined BODY_CORRECTIONS when the sermon
importer started using it; until this ran over them too, a sermon entry in the
table was inert in production — the corrected text only ever reached prod if
someone happened to regenerate the fixture in the same session.

Every changed work is visited, not only those with a declared entry, because
`apply_body_corrections` now also carries the line-break hyphen rejoin — a rule
rather than a list. That is what lets 429 stored defects across 39 works repair
themselves on the next deploy instead of needing a migration.

"Changed" is per body and per version of the rules: a body whose stored
``corrections_key`` matches the one computed now was settled by this exact
code and is skipped unread (library/deploy_fingerprints). ``--all`` ignores the
keys and checks everything.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import F

from library import corrections, dashes, text
from library.corrections import settled_chapter_body, settled_sermon_body
from library.deploy_fingerprints import keyed_md5, keyed_md5_hex, source_version
from library.models import Chapter, Sermon

#: The code that decides what a settled body is. Editing any of it changes the
#: version, which re-checks every body on the next deploy.
CORRECTIONS_MODULES = (corrections, dashes, text)


def _store_keys(model, rows: list) -> None:
    """Record the keys of bodies that were already settled, and empty ``rows``.

    bulk_update, not save(): the body didn't change, so nothing derived from it
    needs refreshing, and save() would clear the citation stamp."""
    model.objects.bulk_update(rows, ["corrections_key"])
    rows.clear()


class Command(BaseCommand):
    help = "Backfill body corrections + trailing-number strip over chapters and sermons."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Check every body, not only those changed since the last run.",
        )

    def handle(self, *args, **opts):
        version = source_version(*CORRECTIONS_MODULES)
        fixed = checked = 0
        # Only bodies this version of the rules has not already settled: the
        # key is compared IN SQL, so an unchanged body is never fetched. In the
        # steady state that is the bodies the seeds just wrote, not the corpus.
        # Defer the two heaviest columns as well. This command reads only
        # body_html and writes it back; body_text is re-derived by
        # Chapter.save() (which assigns it, un-deferring it so it IS written),
        # and the tsvector is refreshed by fts.refresh_chapter's own UPDATE.
        # (word_count is derived by the same save() but stays loaded: it is a
        # 4-byte int, so deferring it would buy nothing.)
        chapters = Chapter.objects.select_related("book").defer("body_text", "search_vector")
        if not opts["all"]:
            chapters = chapters.alias(key_now=keyed_md5(version, "body_html")).exclude(
                corrections_key=F("key_now")
            )
        settled = []
        for chapter in chapters.iterator(chunk_size=100):
            checked += 1
            slug = chapter.book.slug
            # Unconditional: `apply_body_corrections` now carries the line-break
            # hyphen rejoin, which is a RULE and applies to every work, not only
            # the 22 with a hand-written entry. For a slug with no entry the rest
            # of the call is a no-op.
            new = settled_chapter_body(slug, chapter.order, chapter.body_html)
            chapter.corrections_key = keyed_md5_hex(version, new)
            if new != chapter.body_html:
                chapter.body_html = new
                chapter.save()
                fixed += 1
                self.stdout.write(f"  fixed {slug}/{chapter.order}")
            else:
                # A bare (pk, key) stand-in, not the loaded row: on a first run
                # every body lands here, and holding them all is the 2026-08-14
                # OOM again.
                settled.append(Chapter(pk=chapter.pk, corrections_key=chapter.corrections_key))
                if len(settled) >= 500:
                    _store_keys(Chapter, settled)
        _store_keys(Chapter, settled)

        sermons_fixed = 0
        # Every changed sermon, not just those with an entry — same reason as above.
        sermons = Sermon.objects.defer("body_text", "search_vector")
        if not opts["all"]:
            sermons = sermons.alias(key_now=keyed_md5(version, "body_html")).exclude(
                corrections_key=F("key_now")
            )
        settled = []
        for sermon in sermons.iterator(chunk_size=100):
            checked += 1
            new_html = settled_sermon_body(sermon.slug, sermon.body_html)
            sermon.corrections_key = keyed_md5_hex(version, new_html)
            if new_html != sermon.body_html:
                sermon.body_html = new_html
                sermon.save()
                sermons_fixed += 1
                self.stdout.write(f"  fixed sermon {sermon.slug}/{sermon.language}")
            else:
                settled.append(Sermon(pk=sermon.pk, corrections_key=sermon.corrections_key))
                if len(settled) >= 500:
                    _store_keys(Sermon, settled)
        _store_keys(Sermon, settled)

        parts = []
        if fixed:
            parts.append(f"{fixed} chapters")
        if sermons_fixed:
            parts.append(f"{sermons_fixed} sermons")
        msg = f"Corrected {', '.join(parts)}." if parts else "Nothing to correct."
        self.stdout.write(self.style.SUCCESS(f"{msg} ({checked} bodies checked)"))
