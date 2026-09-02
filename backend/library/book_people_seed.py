"""Repo-owned seed data for the people FOUND IN a book (not its author).

This is the single source of truth for ``BookPerson`` membership — which bios a
book points at, and in what capacity — kept in a module of its own for the same
reason ``topic_seed.py`` is: the seed command pulls in
``django.core.management`` and ``library.models``, and this data is plain enough
that a reader of it should not have to. It is deliberately Django-free (plain
literals, string role values), so a non-Django tool could read it too.

Shape — an ordered list of works, each with an ordered list of the people in it::

    BOOK_PEOPLE = [
        ("men-who-moved-heaven", [
            ("george-whitefield", "subject"),
            ("john-wesley", "mentioned"),
        ]),
    ]

``book_slug`` is the canonical, language-agnostic work slug (the one a book file
is named for, e.g. ``men-who-moved-heaven.en.json`` → ``men-who-moved-heaven``);
ONE entry covers every language edition of that work. Each member is
``(author_slug, role)`` where ``author_slug`` is the slug of an existing
``Author`` (their bio) and ``role`` is one of ``PersonRole``'s values —
``"featured"``, ``"subject"`` or ``"mentioned"``. List position sets the display
order (``sort_order``).

``manage.py seed_book_people`` upserts these into ``BookPerson`` on every deploy
(idempotent), tolerating a member whose author bio hasn't landed yet — it skips
the row rather than failing, so membership can be seeded slightly ahead of a
bio, the same way a topic can be seeded ahead of a book.

Populated by hand (or via the Django admin locally); the repo wins on deploy, so
keep the curation here rather than only in the database.
"""

from __future__ import annotations

# (book_slug, [(author_slug, role), ...]). Empty for now — add works as their
# featured bios are curated. See the module docstring for the shape and roles.
BOOK_PEOPLE: list[tuple[str, list[tuple[str, str]]]] = []
