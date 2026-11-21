"""Other names readers search by — the cases spelling rules can't catch.

``library/people.py`` already finds "d l moody", "C.H. Spurgeon" and
"St. Augustine" from the names themselves. What it can't know is a full name
the library abbreviates ("Charles Haddon Spurgeon"), a by-name ("Prince of
Preachers"), a birth or religious name ("Nicholas Herman" for Brother
Lawrence), or a work's Latin or traditional title ("De Civitate Dei",
"Foxe's Book of Martyrs"). Those live here, keyed by slug.

Search-only: nothing here is shown to a reader, so a wrong entry costs a stray
result, never a wrong page. Keep each entry a name the person or work is
genuinely known by, and spell it the way it is usually written — matching
folds case, accents and punctuation (see ``people.words``).

A per-query fix ("this exact search should go there") belongs in the admin's
search triage (synonym / pin), not here: this list is for names that hold
whatever else is typed around them.
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

#: author slug -> other names for that person.
AUTHOR_ALIASES: dict[str, tuple[str, ...]] = {
    "a-b-simpson": ("Albert Benjamin Simpson",),
    "a-w-tozer": ("Aiden Wilson Tozer",),
    "augustine-of-hippo": ("Aurelius Augustinus",),
    "billy-graham": ("William Franklin Graham",),
    "billy-sunday": ("William Ashley Sunday",),
    "brother-lawrence": ("Nicholas Herman", "Lawrence of the Resurrection"),
    "c-s-lewis": ("Clive Staples Lewis", "Jack Lewis"),
    "c-t-studd": ("Charles Thomas Studd",),
    "charles-h-spurgeon": ("Charles Haddon Spurgeon", "Prince of Preachers"),
    "corrie-ten-boom": ("Cornelia ten Boom",),
    "dwight-l-moody": ("Dwight Lyman Moody",),
    "e-m-bounds": ("Edward McKendree Bounds",),
    "frederick-brotherton-meyer": ("Frederick Brotherton Meyer",),
    "g-k-chesterton": ("Gilbert Keith Chesterton",),
    "george-muller": ("George Mueller", "Georg Müller"),
    "gregory-the-great": ("Pope Gregory I", "Gregory I"),
    "harriet-tubman": ("Araminta Ross",),
    "hudson-taylor": ("James Hudson Taylor", "J. Hudson Taylor"),
    "j-c-ryle": ("John Charles Ryle", "Bishop Ryle"),
    "jeanne-guyon": ("Madame Guyon",),
    "jerome": ("Eusebius Hieronymus",),
    "julian-of-norwich": ("Mother Julian", "Dame Julian"),
    "kateri-tekakwitha": ("Lily of the Mohawks",),
    "lottie-moon": ("Charlotte Digges Moon",),
    "pastor-hsi": ("Hsi Sheng-mo",),
    "phillis-wheatley": ("Phillis Wheatley Peters",),
    "r-a-torrey": ("Reuben Archer Torrey",),
    "robert-murray-mcheyne": ("Robert Murray McCheyne", "McCheyne"),
    "sadhu-sundar-singh": ("Sundar Singh",),
    "teresa-of-avila": ("Teresa of Jesus",),
    "thomas-a-kempis": ("Thomas Kempis", "Thomas Hemerken"),
    "thomas-aquinas": ("Angelic Doctor",),
    "timothy-keller": ("Tim Keller",),
    "watchman-nee": ("Ni Tuosheng", "Nee To-sheng"),
}

#: book slug -> other titles it is known by (in any language: a Latin title
#: finds the work in whatever language the reader is reading).
BOOK_ALIASES: dict[str, tuple[str, ...]] = {
    "confessions": ("Confessions of Saint Augustine", "Confessiones"),
    "foxes-book-of-martyrs": ("Foxe's Book of Martyrs", "Acts and Monuments", "Actes and Monuments"),
    "institutes-of-the-christian-religion": ("Calvin's Institutes", "Institutio Christianae Religionis"),
    "interior-castle": ("Las Moradas", "The Interior Castle or the Mansions"),
    "introduction-to-the-devout-life": ("Philothea",),
    "revelations-of-divine-love": ("Showings",),
    "the-city-of-god": ("De Civitate Dei",),
    "the-consolation-of-philosophy": ("De Consolatione Philosophiae",),
    "the-imitation-of-christ": ("De Imitatione Christi", "Imitatio Christi"),
}


def books_named(words: list[str]) -> list[str]:
    """Slugs of the books one of whose other titles the query contains, as
    consecutive words: "de civitate dei" and "augustine de civitate dei" both
    name The City of God. ``words`` is the query as ``people.words`` folds it."""
    from .people import words as fold_words

    found = []
    for slug, titles in BOOK_ALIASES.items():
        for title in titles:
            want = fold_words(title)
            n = len(want)
            if n and any(words[i : i + n] == want for i in range(len(words) - n + 1)):
                found.append(slug)
                break
    return found


#: How each author's name is written in each language (data/author_names.json).
AUTHOR_NAMES_FILE = Path(__file__).parent / "data" / "author_names.json"


@cache
def author_names_by_language() -> dict[str, dict[str, list[str]]]:
    """slug -> language -> the forms that language writes the name in."""
    data = json.loads(AUTHOR_NAMES_FILE.read_text(encoding="utf-8"))
    return {slug: names for slug, names in data.items() if not slug.startswith("_")}


def other_names(slug: str) -> list[str]:
    """Every other name ``slug`` is searched by: its aliases, and its name as
    written in every language. Every language, not only the reader's: a
    Ukrainian reading the English site still types Муді."""
    names = list(AUTHOR_ALIASES.get(slug, ()))
    for forms in author_names_by_language().get(slug, {}).values():
        names.extend(forms)
    return names
