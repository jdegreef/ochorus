"""Finding a person by the way readers actually type their name.

Full-text search tokenises a name the way it tokenises prose, which is wrong
for people:

* initials don't meet the name they stand for — "d l moody" asks for the
  lexeme ``d``, which "Dwight L. Moody" doesn't hold, so Moody's own author row
  never matched while R. A. Torrey's bio (which mentions "D. L. Moody") did;
* run-together initials are one opaque token — "D.L. Moody" parses as ``d.l``
  and ``moodi``, so it matched nothing of Moody's at all;
* a missing middle initial or a misspelt surname ("Charles Spurgen") is a miss.

So people are matched here, in Python, against the few hundred author names:
each query word is paired with a word of the name — exactly, as a prefix, as
an initial, or (five letters and up) as a near-spelling. What comes back says
how strongly the query names each person, so search can rank the person first,
mark an unmistakable naming as the top result, and rewrite the query for the
other types ("d l moody prayer" also searches "Dwight L Moody prayer") so a
person's books and sermons are found by the same spelling that found them.

Pure functions over ``(pk, name)`` pairs: nothing here touches the database.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field

#: Words a reader may put around a name that no name in the library spells out
#: ("St. Augustine", "Rev. Spurgeon", "Pastor Hsi"). Skipped when unmatched,
#: used when the name does carry them ("Brother Lawrence").
OPTIONAL = frozenset(
    {
        "st", "saint", "rev", "revd", "reverend", "dr", "mr", "mrs", "pastor",
        "father", "fr", "brother", "sister", "mother", "bishop", "the", "of",
        "by", "author", "and",
    }
)

#: Joining words inside names ("Basil of Caesarea", "Julian of Norwich"): never
#: a surname, and never enough on their own to say a query names someone.
PARTICLES = frozenset({"of", "the", "de", "von", "van", "der", "da", "la", "le", "old"})

#: Per-word match strengths. An exact word beats a prefix beats a typo beats an
#: initial — "c s lewis" is named by its surname, carried by its initials.
EXACT, PREFIX, FUZZY, INITIAL = 3.0, 2.0, 1.5, 1.0

_FUZZY_MIN_LEN = 5
_FUZZY_RATIO = 0.84
_WORD = re.compile(r"[^\W_]+", re.UNICODE)


def fold(text: str) -> str:
    """Lowercase with Latin accents removed ("Frères" → "freres")."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


_POSSESSIVE = re.compile(r"['’]s\b", re.IGNORECASE)


def words(text: str) -> list[str]:
    """``text`` as folded words; punctuation splits, so "D.L." is ``d``, ``l``,
    and a possessive goes ("Moody's" is ``moody``, not ``moody`` + ``s``)."""
    return _WORD.findall(fold(_POSSESSIVE.sub("", text or "")))


def asked_for(q: str) -> list[str]:
    """The words of ``q`` a person could be named by: no ``-excluded`` word
    (``moody -torrey`` asks for Moody, never Torrey) and no ``OR``."""
    kept = [c for c in (q or "").split() if not c.startswith("-") and c != "OR"]
    return words(" ".join(kept))


@dataclass(frozen=True)
class _Name:
    pk: object
    name: str
    tokens: tuple[str, ...]
    surname: str


def _surname(name: str, tokens: list[str]) -> str:
    """The last real word outside any parenthesis: "Mary Stone (Shi Meiyu)" →
    "stone"; "Basil of Caesarea" → "caesarea"; "Boethius" → "boethius"."""
    outer = words(re.sub(r"\(.*?\)", " ", name)) or tokens
    real = [t for t in outer if len(t) > 1 and t not in PARTICLES]
    return real[-1] if real else (outer[-1] if outer else "")


def _strength(typed: str, word: str) -> float:
    if typed == word:
        return EXACT
    if len(typed) == 1:
        return INITIAL if word.startswith(typed) else 0.0
    # A prefix long enough to be meant ("spurg"), not a word that happens to
    # open a name ("christ" of Christenson, "ruth" of Rutherford).
    if len(typed) >= 4 and word.startswith(typed) and len(typed) >= 0.6 * len(word):
        return PREFIX
    if (
        len(typed) >= _FUZZY_MIN_LEN
        and len(word) >= _FUZZY_MIN_LEN
        and difflib.SequenceMatcher(None, typed, word).ratio() >= _FUZZY_RATIO
    ):
        return FUZZY
    return 0.0


def _initials(typed: str, tokens: tuple[str, ...], free: list[int]) -> list[int]:
    """Name words a run of initials stands for, in order — "dl" over "Dwight
    L. Moody" is [0, 1] — or [] when ``typed`` isn't this person's initials (and
    so is an ordinary word: "on" in "moody on prayer")."""
    if not (2 <= len(typed) <= 3 and typed.isalpha()) or typed in OPTIONAL:
        return []
    run: list[int] = []
    for letter in typed:
        nxt = next(
            (j for j in free if j not in run and (not run or j > run[-1])
             and tokens[j].startswith(letter)),
            None,
        )
        if nxt is None:
            return []
        run.append(nxt)
    return run


@dataclass
class PersonMatch:
    """How a query names one person."""

    pk: object
    name: str
    #: The name's surname as folded ("moody"), for a snippet to centre on.
    surname: str
    #: Found by the surname, not only by a first name ("john").
    by_surname: bool
    score: float
    #: Every word of the query is part of the name (or a skippable honorific):
    #: the query is this person's name, not a name plus other words.
    whole: bool
    #: The query words the name consumed, and those it left (the rest of the
    #: query: "prayer" in "moody prayer").
    used: list[int] = field(default_factory=list)
    rest: list[str] = field(default_factory=list)

    @property
    def named(self) -> bool:
        """The query unmistakably IS this person's name — the top-result test.

        Two or more name words and nothing else, so "d l moody", "dwight moody"
        and "c. s. lewis" qualify, while a lone surname ("moody", "sunday",
        "law") doesn't: one word may as well be the subject as the person.
        """
        return self.whole and len(self.used) >= 2


class People:
    """The author names one search matches against (built once per request)."""

    def __init__(self, rows):
        self._names = []
        for pk, name in rows:
            tokens = words(name)
            if tokens:
                self._names.append(_Name(pk, name, tuple(tokens), _surname(name, tokens)))

    def match(self, q: str) -> list[PersonMatch]:
        """Everyone the query names, strongest first.

        A person matches when the query holds their surname (exactly, as a
        prefix, or misspelt) — or a first name typed in full ("dwight") — and
        every single-letter word of the query is one of their initials: "d l
        moody" names Dwight L. Moody, not every Moody.
        """
        typed = asked_for(q)
        if not typed:
            return []
        found = [m for n in self._names if (m := self._match_one(typed, n))]
        found.sort(key=lambda m: (-m.whole, -m.score, m.name))
        return found

    def _match_one(self, typed: list[str], person: _Name) -> PersonMatch | None:
        free = list(range(len(person.tokens)))  # name words not yet used
        used: list[int] = []
        rest: list[str] = []
        score = 0.0
        surname_hit = False
        full_word_hit = False
        for i, t in enumerate(typed):
            best, best_j = 0.0, -1
            for j in free:
                s = _strength(t, person.tokens[j])
                # Of equal strengths, the earlier name word: initials read in order.
                if s > best:
                    best, best_j = s, j
            if best == 0.0:
                if len(t) == 1:
                    return None  # an initial this person doesn't have
                run = _initials(t, person.tokens, free)
                if run:  # "dl moody", "CH Spurgeon": initials typed together
                    for j in run:
                        free.remove(j)
                    used.append(i)
                    score += INITIAL * len(run)
                else:
                    rest.append((i, t))
                continue
            if t in PARTICLES:
                # "of" in "catherine of siena" belongs to the name, but never
                # counts as naming anyone: "the great" is not Gregory the Great.
                if best == EXACT:
                    free.remove(best_j)
                else:
                    rest.append((i, t))
                continue
            free.remove(best_j)
            used.append(i)
            score += best
            word = person.tokens[best_j]
            if word == person.surname and best >= FUZZY:
                surname_hit = True
            if best == EXACT and len(t) >= 3 and t not in PARTICLES:
                full_word_hit = True
        if not (surname_hit or full_word_hit):
            return None
        # A first name alone ("john") is a weak naming; a surname, a strong one.
        if surname_hit:
            score += EXACT
        # An honorific is skippable before the name ("st augustine", "rev
        # spurgeon"); after it, it is something else asked for ("moody mother").
        first = min(used)
        rest = [t for i, t in rest if not (t in OPTIONAL and i < first)]
        whole = not rest
        # Covering more of the name is a better match: "dwight l moody" over a
        # "dwight moody" that left the initial unread.
        score += len(used) / len(person.tokens)
        return PersonMatch(
            pk=person.pk,
            name=person.name,
            surname=person.surname,
            by_surname=surname_hit,
            score=score,
            whole=whole,
            used=used,
            rest=rest,
        )

    def rewrite(self, q: str, found: list[PersonMatch] | None = None) -> str | None:
        """``q`` with the person it names spelt as the library spells them.

        For the types that match an author by the name baked into their vector
        (books, chapters, sermons): "d.l. moody prayer" → "dwight l moody
        prayer". None when there is nothing to rewrite — no one is named by two
        or more words, the naming is a tie, the query uses websearch syntax, or
        the typed name already is the library's spelling.
        """
        if re.search(r"(^|\s)-|\bOR\b|\"", q):
            return None  # websearch syntax: rewriting would drop its operators
        top = strongest(self.match(q) if found is None else found)
        if top is None:
            return None
        rewritten = " ".join([*words(top.name), *top.rest])
        return None if rewritten == " ".join(words(q)) else rewritten


def strongest(found: list[PersonMatch]) -> PersonMatch | None:
    """The person a query names by two or more words, when nobody ties —
    "john w…" between two Johns names no one."""
    strong = [m for m in found if len(m.used) >= 2]
    if not strong:
        return None
    top = strong[0]
    if len(strong) > 1 and (strong[1].whole, strong[1].score) == (top.whole, top.score):
        return None
    return top
