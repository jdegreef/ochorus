"""The first taste of a book's prose, for its own page.

A reader deciding whether to start a fourth-century treatise wants to know how
it reads, and nothing on the book page told them: the cover, the chapter list
and a description are all *about* the book. One paragraph of the thing itself
answers the question better than any of them.

WHY THIS IS NOT "THE FIRST PARAGRAPH OF CHAPTER 1". Because that is wrong on
more than a third of the shelf. Measured over the 68 published English books:

  * 25 of them open with front matter — a preface, a foreword, a publisher's
    note, an editor's account of the author, a personal profile.
  * Several open with an editorial SYNOPSIS inside the body rather than as a
    separate chapter. `On the Incarnation` begins "§1. Introductory.—The
    subject of this treatise: the humiliation and incarnation of the Word."
    and Owen's `Mortification` with a chapter argument strung on em-dashes.
    Neither is the author's voice.
  * Some carry an absorbed running head: `Religious Affections` starts
    "RELIGIOUS AFFECTIONS. PART 1. CONCERNING THE NATURE OF THE AFFECTIONS".

So there are two filters, and then a gate. Skip chapters whose TITLE marks them
as apparatus; skip leading paragraphs that are pure epigraph; and then require
what is left to look like prose. A book that passes none of it simply gets no
excerpt — silence is the honest answer, and the page reads fine without one.
"""

from __future__ import annotations

import html as _html
import re

#: Titles that mark a section as being ABOUT the book rather than being it.
#: Matched anywhere in the title, not just at the start: the corpus has
#: "Extract from the Preface", "A Short Account of the Author and the Great
#: Success Which Attended the Call", and "Personal Profile", none of which a
#: start-anchored pattern catches. A real chapter caught by mistake costs
#: nothing — the search simply moves to the next one, which is still the book.
APPARATUS = re.compile(
    r"\b(preface|foreword|forward|prologue|prefatory|dedication|apolog\w*"
    r"|introduction|introductory|synopsis|argument|contents|errata|prefactory"
    r"|publisher|translator|transcriber|editor|imprint|advertisement"
    r"|personal profile|about the author|account of the author|the author.s life"
    r"|to the reader|note to the reader)\b",
    re.I,
)

#: A paragraph that is only a quoted text and its reference — the epigraph many
#: chapters open under. Skipped as a LEADING paragraph so the excerpt reaches
#: the author's own sentences; kept if prose has already started, because then
#: it is the author quoting rather than the chapter's headpiece.
EPIGRAPH = re.compile(
    r"^[\"“'‘(]?.{0,400}?[\"”'’)]?\s*[-–—]?\s*"
    # "John 3:16", "Ps. 62: 1", and the older "1 Peter, i. 7" with a roman chapter
    r"\(?\b[1-3]?\s?[A-Z][a-z]+\.?,?\s+(?:\d{1,3}[:.]\s?\d{1,3}|[ivxl]{1,5}\.\s?\d{1,3})"
    r"(\s*[-–—]\s*\d{1,3})?\.?\)?\s*(\([\w.]+\))?\.?$"
)

MIN_WORDS = 40
MAX_WORDS = 65

#: How far in to look for an opening. An "excerpt" taken from chapter six is
#: not an opening — before this limit, Grace Abounding fell through five
#: front-matter sections and offered its CONCLUSION as a first taste. If the
#: front of the book yields nothing clean, nothing is the right answer.
MAX_DEPTH = 3

#: How much of the excerpt may sit inside quotation marks. An opening that is
#: mostly quoted scripture tastes of the Bible, not of the book — Catherine
#: Booth's "Repentance" opens with two verses and nothing else.
MAX_QUOTED = 0.6


def _paragraphs(body_html: str):
    for raw in re.findall(r"<p[^>]*>(.*?)</p>", body_html or "", re.S):
        # Drop footnote markers CONTENT AND ALL. Stripping tags alone leaves the
        # digits welded to the prose: Pilgrim's Progress opens "where was a
        # den,<sup>3</sup><sup>3</sup>Bedford jail…", which flattens to
        # "a den,33Bedford jail" — a number in the middle of the most famous
        # sentence on the shelf.
        raw = re.sub(r"<sup[^>]*>.*?</sup>", "", raw, flags=re.S)
        text = _html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", raw)))
        text = text.strip()
        if text:
            yield text


def _quoted_fraction(text: str) -> float:
    inside = sum(len(m) for m in re.findall(r"[“\"]([^”\"]*)[”\"]", text))
    return inside / len(text) if text else 0.0


def _reads_as_prose(text: str) -> bool:
    words = text.split()
    if len(words) < MIN_WORDS:
        return False
    if text.lstrip().startswith(("§", "*")):
        return False
    # A chapter ARGUMENT: topic phrases strung on em-dashes, never sentences.
    if text.count(" — ") >= 3 or text.count("—") >= 4:
        return False
    # A running head or part title absorbed into the body.
    if sum(1 for w in words[:12] if len(w) > 2 and w.isupper()) >= 6:
        return False
    if _quoted_fraction(text) > MAX_QUOTED:
        return False
    # Prose ends sentences — ONE is the bar, not two.
    #
    # Two rejected Bunyan and Edwards, whose openings run to ninety words
    # before the first full stop ("IT may possibly be thought, that there is
    # no great need of going about to define or describe the Will; this word
    # being generally as well understood as any other words we can use…").
    # A long period is a feature of the prose this shelf is made of, and the
    # absorbed headings the rule was aimed at are caught by the caps and
    # em-dash tests above.
    return bool(re.search(r"[.!?](?:[\s\"'”]|$)", text))


def _clip(text: str) -> str:
    words = text.split()
    if len(words) <= MAX_WORDS:
        return text
    clipped = " ".join(words[:MAX_WORDS])
    cut = max(clipped.rfind(". "), clipped.rfind("! "), clipped.rfind("? "))
    if cut > len(clipped) * 0.5:
        clipped = clipped[: cut + 1]
        # "…1 Peter, i. 7. Mr." — the sentence search stopped at an
        # ABBREVIATION's full stop and left its next word hanging.
        while re.search(r"\s\w{1,3}\.$", clipped):
            clipped = clipped[: clipped.rstrip().rfind(" ")].rstrip()
        return clipped
    return clipped.rstrip(",;:— ") + "…"


def opening_excerpt(chapters) -> tuple[str, str]:
    """``(excerpt, chapter_title)`` — "" when the book has no clean opening.

    ``chapters`` is ``[(order, title, body_html)]`` in reading order.

    The chapter is returned with the text because the page names it. A reader
    shown an unattributed paragraph cannot tell whether it is the beginning of
    the book or something plucked from the middle, and saying which chapter it
    came from costs a line and removes the doubt.
    """
    tried = 0
    for _order, title, body_html in chapters:
        if APPARATUS.search((title or "").strip()):
            continue
        tried += 1
        if tried > MAX_DEPTH:
            return "", ""
        collected: list[str] = []
        words = 0
        for para in _paragraphs(body_html):
            if not collected and EPIGRAPH.match(para):
                continue
            collected.append(para)
            words += len(para.split())
            if words >= MIN_WORDS:
                break
        text = " ".join(collected)
        if _reads_as_prose(text):
            return _clip(text), (title or "").strip()
    return "", ""
