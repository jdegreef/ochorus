"""Seed the people found in a book (``BookPerson``) from ``book_people_seed``.

Idempotent: membership is upserted each run (new people added, roles and order
refreshed) so an edited seed reaches an already-seeded row on the next deploy.
Members are keyed by ``(book_slug, author_slug)``; the ``book_slug`` is a soft
reference, so a work that isn't present in a given language simply doesn't show
the person on that language's page. A member whose author bio hasn't been
created yet is skipped with a notice rather than failing the deploy — the same
tolerance ``seed_topics`` gives a book slug that isn't in the library yet.

The membership definitions live in ``library/book_people_seed.py`` — a
Django-free module, kept separate for the same reason ``topic_seed.py`` is.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from library.book_people_seed import BOOK_PEOPLE
from library.models import Author, BookPerson


class Command(BaseCommand):
    help = "Seed the people found in each book (BookPerson membership), idempotent."

    def handle(self, *args, **opts):
        # One query for every author a seed member names, so a large seed is a
        # handful of round-trips, not one per person.
        wanted = {slug for _, members in BOOK_PEOPLE for slug, _ in members}
        authors = {a.slug: a for a in Author.objects.filter(slug__in=wanted)}

        added = updated = missing = 0
        for book_slug, members in BOOK_PEOPLE:
            for i, (author_slug, role) in enumerate(members):
                person = authors.get(author_slug)
                if person is None:
                    # A bio that hasn't landed yet — seed can run ahead of it.
                    missing += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  skip {book_slug} → {author_slug}: no such author yet"
                        )
                    )
                    continue
                _, created = BookPerson.objects.update_or_create(
                    book_slug=book_slug,
                    person=person,
                    defaults={"role": role, "sort_order": i},
                )
                added += created
                updated += not created

        if added or updated:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Book people seeded: {added} added, {updated} refreshed"
                    + (f", {missing} awaiting a bio." if missing else ".")
                )
            )
        else:
            self.stdout.write("No book-people membership to seed.")
