"""Original-language editions: non-English rows that are NOT translations.

Every non-English book, sermon and article in the library is an AI translation
of an English edition (``ai_unreviewed``, then ``ai_reviewed``) — except these,
which are the author's own text: Pascal wrote in French, so his French is the
original and the English is the translation. They carry ``public_domain``,
the source type the model defines as "Public domain (original language)".

``public_domain`` is also the model's DEFAULT, so on its own it cannot tell an
original from a translation that was created without a source type. That is
why the originals are listed here as well: ``tests_fixture`` fails on any
non-English ``public_domain`` row that is not in ``ORIGINAL_EDITIONS``, so a
mislabelled translation cannot slip past the translation gates as an original.
"""

from __future__ import annotations

ORIGINAL_SOURCE_TYPE = "public_domain"

#: (slug, language) of every original-language edition that is not English.
ORIGINAL_EDITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("pensees", "fr"),
        ("provincial-letters", "fr"),
        ("life-of-pascal", "fr"),
    }
)


def is_original(language: str, source_type: str) -> bool:
    """A non-English edition in its original language, not a translation.

    Such a row has no English source to match: the translation gates (markup
    parity, staleness) leave it alone.
    """
    return language != "en" and source_type == ORIGINAL_SOURCE_TYPE
