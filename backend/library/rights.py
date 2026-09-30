"""Whether an edition may be declared public domain in structured data.

The book page and every chapter page tell search engines, in JSON-LD, what they
are allowed to say about a work's rights: a public-domain edition carries
schema.org ``license`` pointing at the Public Domain Mark. That is a legal
CLAIM made on the work's behalf, so it is made only where the library's own
records support it, and a silence costs nothing where they don't.

The library is not uniformly public domain. The Ochorus Originals are the
house's own writing; a handful of works are shared by their living author's
permission ("© Gareth Evans. Shared free on Ochorus with the author's
permission."); an introduction may be the house's; the Modern English edition
is the house's modernization. So the rule reads the records, most specific
first:

1. The imprint's own books and the Modern English editions: never.
2. A rights note (``Book.attribution``) that reserves anything — ©, copyright,
   permission — or names the work as the house's ("by Ochorus": the Key
   Teachings companions, filed under the author they are ABOUT): never,
   whatever else it says.
3. A note that DECLARES the work public domain — "Public domain — …",
   "… (1876). Public domain.", "The epistles are public domain …": yes. Only as
   the opening of the note or of a sentence, because the phrase also turns up
   about something else ("Andrew Murray's own writings are in the public
   domain", "the Berean Standard Bible, which is in the public domain"), and
   a bare substring match read those as a claim about the book.
4. No note at all, and an author who died more than 70 years ago (the life+70
   term most of the world has converged on): yes.
5. Anything else — a note that is only a credit, an author with no death year,
   or one who died too recently: no claim.

A translation is judged by its English edition's note (translated editions
carry a translator's note, not a rights note); the translation itself is
machine-made and adds no rights of its own.
"""

from __future__ import annotations

import re
from datetime import date

from .contemporize import MODERN_LANGUAGE

#: The Public Domain Mark — what `license` points at for a public-domain work.
PUBLIC_DOMAIN_MARK = "https://creativecommons.org/publicdomain/mark/1.0/"

#: The house imprint's author row (see the reader's $lib/originals).
ORIGINALS_SLUG = "ochorus-originals"

#: Words in a rights note that reserve something, or name the house as author.
_RESERVED = re.compile(r"©|\bcopyright\b|\bpermission\b|\bby ochorus\b", re.IGNORECASE)

#: "public domain" as the note's own declaration about the work: at the start of
#: the note or of a sentence, optionally after "The <noun> is/are".
_DECLARES = re.compile(
    r"(?:^|[.;!?]\s+)(?:the \w+(?: \w+)? (?:is|are) )?public domain\b", re.IGNORECASE
)

#: Years after the author's death before the work is treated as free.
TERM_YEARS = 70


def is_public_domain(book) -> bool:
    """Whether ``book`` (a Book row) may be marked public domain."""
    if book.author.slug == ORIGINALS_SLUG or book.language == MODERN_LANGUAGE:
        return False
    note = book.attribution or ""
    if book.language != "en" and book.source_type != "public_domain":
        from .models import Book

        english = Book.objects.filter(slug=book.slug, language="en").only("attribution").first()
        note = english.attribution if english else note
    if _RESERVED.search(note):
        return False
    if _DECLARES.search(note.strip()):
        return True
    death = book.author.death_year
    return not note.strip() and death is not None and death < date.today().year - TERM_YEARS
