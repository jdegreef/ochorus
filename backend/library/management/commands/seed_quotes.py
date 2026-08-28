"""Upsert the curated quotations from `library/quote_seed.py`.

Runs on every deploy, like the other seeds, and is idempotent: a quote is keyed
by its slug (author + hash of the normalised text), so re-running updates the
row rather than duplicating it, and a reworded quotation becomes a NEW row
instead of silently editing one somebody already approved.

`reviewed` is CREATE-ONLY, and set from `quote_seed.APPROVED` — the record, in
version control, of which authors a person has signed off. Recording it here
rather than only in production is deliberate: a prod-only approval is invisible
to a database rebuild, which is the failure author_sync.py exists to fix.

Create-only cuts BOTH ways and that is the point. The seed publishes what the
repo has approved when it first creates a row, and never touches `reviewed`
again — so a takedown in the live database (a misattribution found, a
complaint) survives every later deploy. That is the same rule `is_published`
and `source_type` follow in seed_books, for the same reason.

A row created before its author was approved therefore stays unreviewed; that
is what `approve_quotes` is for.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from library.models import Author, Chapter, Quote, Sermon
from library.quote_seed import APPROVED, QUOTES


class Command(BaseCommand):
    help = "Upsert curated quotations (idempotent; `reviewed` is create-only)."

    @transaction.atomic
    def handle(self, *args, **opts):
        created = updated = skipped = 0
        for author_slug, quotes in QUOTES.items():
            author = Author.objects.filter(slug=author_slug).first()
            if author is None:
                # Not an error: a fresh database seeds authors first, but an
                # install without this author simply has no quotes to place.
                self.stdout.write(f"  no author {author_slug!r} — skipping its quotes")
                continue
            for q in quotes:
                source = self._source(author, q)
                if source is None:
                    # The work is not in this install (or not in English). A
                    # quotation with no source must never be published, so it is
                    # skipped rather than stored unsourced.
                    skipped += 1
                    continue
                field, obj = source
                row = Quote.objects.filter(slug=q["slug"]).first()
                if row is None:
                    Quote.objects.create(
                        slug=q["slug"], author=author, text=q["text"],
                        paragraph=q["paragraph"],
                        reviewed=author_slug in APPROVED,
                        **{field: obj},
                    )
                    created += 1
                    continue
                changed = []
                for name, value in (("text", q["text"]), ("paragraph", q["paragraph"]),
                                    (field, obj), ("author", author)):
                    if getattr(row, name) != value:
                        setattr(row, name, value)
                        changed.append(name)
                if changed:
                    row.save(update_fields=changed)
                    updated += 1
        msg = f"Quotes: {created} created, {updated} updated"
        if skipped:
            msg += f", {skipped} skipped (source not installed)"
        self.stdout.write(self.style.SUCCESS(msg + "."))

    def _source(self, author, q):
        if "sermon" in q:
            s = Sermon.objects.filter(
                slug=q["sermon"], language="en", author=author
            ).first()
            return ("sermon", s) if s else None
        slug, order = q["chapter"]
        c = Chapter.objects.filter(
            book__slug=slug, book__language="en", book__author=author, order=order
        ).first()
        return ("chapter", c) if c else None
