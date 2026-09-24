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

The Ochorus Originals are biographical anthologies — one chapter per figure — so
the people in them are the figures each gives a chapter to (``role="subject"``),
listed in the book's own chapter order. Only figures who already have a bio in
the library are listed; a chapter subject with no bio yet is left out until one
is written (linking a bio-less name would be a dead end). ``A Hidden Fire`` is
the exception to the one-chapter-per-figure shape: it is a single biography of
Simeon Nsibambi, so he is its lone subject.
"""

from __future__ import annotations

# (book_slug, [(author_slug, role), ...]). See the module docstring for the
# shape and roles.
BOOK_PEOPLE: list[tuple[str, list[tuple[str, str]]]] = [
    ("a-hidden-fire", [("simeon-nsibambi", "subject")]),
    # Pierson's authorised memoir of Müller — like A Hidden Fire, a single
    # biography, so its subject is its lone member.
    ("george-muller-of-bristol", [("george-muller", "subject")]),
    (
        "men-and-women-who-gave-everything-2",
        [
            ("william-carey", "subject"),
            ("david-livingstone", "subject"),
            ("catherine-booth", "subject"),
            ("dwight-l-moody", "subject"),
            ("pandita-ramabai", "subject"),
            ("c-t-studd", "subject"),
            ("john-stott", "subject"),
            ("helen-roseveare", "subject"),
            ("jim-elliot", "subject"),
            ("elisabeth-elliot", "subject"),
        ],
    ),
    (
        "men-of-prayer-2",
        [
            ("andrew-murray", "subject"),
            ("charles-h-spurgeon", "subject"),
            ("watchman-nee", "subject"),
            ("dwight-l-moody", "subject"),
            ("r-a-torrey", "subject"),
            ("e-m-bounds", "subject"),
            ("jonathan-edwards", "subject"),
            ("charles-finney", "subject"),
            ("rees-howells", "subject"),
            ("billy-graham", "subject"),
            ("henry-blackaby", "subject"),
            ("bill-bright", "subject"),
            ("loren-cunningham", "subject"),
            ("derek-prince", "subject"),
            ("timothy-keller", "subject"),
        ],
    ),
    (
        "men-who-moved-heaven",
        [
            ("charles-h-spurgeon", "subject"),
            ("andrew-murray", "subject"),
            ("rees-howells", "subject"),
            ("hudson-taylor", "subject"),
            ("e-m-bounds", "subject"),
            ("george-muller", "subject"),
            ("john-hyde", "subject"),
            ("david-brainerd", "subject"),
            ("martin-luther", "subject"),
            ("john-wesley", "subject"),
        ],
    ),
    (
        "men-who-tended-the-flock-2",
        [
            ("john-chrysostom", "subject"),
            ("gregory-the-great", "subject"),
            ("george-herbert", "subject"),
            ("richard-baxter", "subject"),
            ("jonathan-edwards", "subject"),
            ("john-newton", "subject"),
            ("robert-murray-mcheyne", "subject"),
            ("a-w-tozer", "subject"),
            ("dietrich-bonhoeffer", "subject"),
            ("martyn-lloyd-jones", "subject"),
        ],
    ),
    (
        "tukutendereza",
        [
            ("simeon-nsibambi", "subject"),
            ("joe-church", "subject"),
            ("yosiya-kinuka", "subject"),
            ("blasio-kigozi", "subject"),
            ("william-nagenda", "subject"),
            ("erica-sabiti", "subject"),
            ("yona-kanamuzeyi", "subject"),
            ("festo-kivengere", "subject"),
            ("janani-luwum", "subject"),
            ("lawrence-barham", "subject"),
        ],
    ),
    (
        "women-who-moved-heaven-2",
        [
            ("monica-of-hippo", "subject"),
            ("teresa-of-avila", "subject"),
            ("susanna-wesley", "subject"),
            ("jeanne-guyon", "subject"),
            ("amy-carmichael", "subject"),
            ("corrie-ten-boom", "subject"),
            ("lottie-moon", "subject"),
            ("mary-slessor", "subject"),
            ("gladys-aylward", "subject"),
            ("evelyn-christenson", "subject"),
        ],
    ),
]
