"""Answers: a question typed into search, met by a question the library answers.

Readers type questions ("how do I forgive someone who hurt me", "why does God
allow suffering"). Text search finds the passages that use those words, but the
library has already ANSWERED thousands of questions in its own words: every
book, sermon, topic and article page carries a "Questions and Answers" list,
and every bio its Q&A, each grounded in the work. So a question-shaped query is
matched against those questions here, and the best one or two come back as an
answer the reader can read on the spot, linked to the page it answers on.

Matching is by meaning only as far as words carry it, with no model at search
time (the API holds no AI credential, on purpose): the question's content words
must mostly appear in the library's question, each as a word or sharing its
first five letters ("forgive", "forgiving" and "forgiveness" meet). Pure
Python over a memoised per-language list.
"""

from __future__ import annotations

import re

from .people import words

#: How many answers the mixed list carries.
ANSWER_CAP = 2

#: Words that open a question in English. Elsewhere a question mark says it.
_ASKING = frozenset(
    ["how", "why", "what", "who", "whom", "whose", "when", "where", "which", "is", "are", "was", "were", "do", "does", "did", "can", "could", "should", "would", "will", "shall", "may", "might", "must"]
)

#: English words that carry no subject of their own.
_STOP = frozenset(
    ["a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can", "could", "did", "do", "does", "for", "from", "had", "has", "have", "he", "her", "him", "his", "how", "i", "if", "in", "into", "is", "it", "its", "me", "my", "no", "not", "of", "on", "or", "our", "she", "should", "so", "some", "someone", "something", "such", "than", "that", "the", "their", "them", "then", "there", "these", "they", "this", "those", "to", "us", "was", "we", "were", "what", "when", "where", "which", "who", "whom", "why", "will", "with", "would", "you", "your", "about", "am", "any", "get", "let", "make", "much", "many", "one", "other", "really", "very", "way"]
)

#: Share of the query's content words a library question must hold.
MIN_COVER = 0.75
#: Letters two words must share to count as one ("forgiv-").
_STEM = 5

#: Of equally close questions, whose answer comes first: a person's own page
#: answers "who was Hudson Taylor" better than a book of his that also does.
_KIND_ORDER = {"author": 0, "topic": 1, "article": 2, "book": 3, "sermon": 4}


def _stem(word: str) -> str:
    return word[:_STEM]


def is_question(q: str, language: str) -> bool:
    """Whether ``q`` reads as a question: a question mark, or (in English) an
    asking word first and three words at least."""
    if "?" in q or "؟" in q or "？" in q:
        return len(words(q)) >= 2
    typed = words(q)
    return language == "en" and len(typed) >= 3 and typed[0] in _ASKING


def _content(text: str, language: str) -> list[str]:
    # Every language drops one-letter words; English drops its common words
    # too. Elsewhere the coverage rule carries the weight.
    stop = _STOP if language == "en" else frozenset()
    return [w for w in words(text) if len(w) > 1 and w not in stop]


def _rows(language: str) -> list[dict]:
    """Every answered question published in ``language``, with its content
    words' stems, and where it is answered."""
    from .models import Article, Author, Book, Sermon, Topic

    out: list[dict] = []

    def add(pairs, kind, slug, title, qkey, akey):
        for pair in pairs or []:
            question, answer = (pair.get(qkey) or "").strip(), (pair.get(akey) or "").strip()
            if question and answer:
                out.append(
                    {
                        "question": question,
                        "answer": answer,
                        "stems": frozenset(_stem(w) for w in _content(question, language)),
                        "kind": kind,
                        "slug": slug,
                        "title": title,
                    }
                )

    for slug, title, qa in Book.objects.filter(language=language, is_published=True).values_list(
        "slug", "title", "qa"
    ):
        add(qa, "book", slug, title, "question", "answer")
    for slug, title, qa in Sermon.objects.filter(language=language, is_published=True).values_list(
        "slug", "title", "study_questions"
    ):
        add(qa, "sermon", slug, title, "question", "answer")
    for slug, title, qa in Article.objects.filter(language=language, is_published=True).values_list(
        "slug", "h1", "qa"
    ):
        add(qa, "article", slug, title, "question", "answer")
    for topic in Topic.objects.prefetch_related("translations"):
        add(topic.qa_for(language), "topic", topic.slug, topic.title_for(language), "question", "answer")
    for author in Author.objects.filter(is_imprint=False).prefetch_related("translations"):
        add(author.faq_for(language), "author", author.slug, author.name, "q", "a")
    return out


def all_answers(language: str) -> list[dict]:
    from .search import memoized

    return memoized("answers", lambda: _rows(language), language)


def answer_hits(q: str, language: str, scope=None) -> list[dict]:
    """The library's answers to the question ``q`` asks, best first; [] when
    ``q`` isn't a question or nothing answers it closely. Never in a scope:
    an answer is a whole-library reply."""
    if scope or not is_question(q, language):
        return []
    want = list(dict.fromkeys(_stem(w) for w in _content(q, language)))
    if len(want) < 2:
        return []
    found = []
    for row in all_answers(language):
        held = sum(s in row["stems"] for s in want)
        cover = held / len(want)
        if held >= 2 and cover >= MIN_COVER:
            # Fewer words of its own that the reader didn't ask about is the
            # closer question: "why does god allow suffering" over "why does
            # Spurgeon say god allows suffering in the life of Job".
            extra = len(row["stems"]) - held
            found.append(
                (-cover, extra, _KIND_ORDER[row["kind"]], len(row["question"]), row["question"], row)
            )
    found.sort(key=lambda f: f[:5])
    seen: set = set()
    hits = []
    for *_, row in found:
        if (row["kind"], row["slug"]) in seen:
            continue  # one answer per page; its other questions are a tap away
        seen.add((row["kind"], row["slug"]))
        hits.append(_hit(row, want))
    return hits


_WORD = re.compile(r"(\w+)")


def _marked(text: str, want: list[str]) -> str:
    from .people import fold
    from .search import HL_END, HL_START

    stems = set(want)
    return "".join(
        f"{HL_START}{part}{HL_END}" if i % 2 and _stem(fold(part)) in stems and len(part) > 1 else part
        for i, part in enumerate(_WORD.split(text))
    )


def _hit(row: dict, want: list[str]) -> dict:
    return {
        "type": "answer",
        "question": row["question"],
        "answer": row["answer"],
        "work_kind": row["kind"],
        "work_slug": row["slug"],
        "work_title": row["title"],
        "snippet": _marked(row["question"], want),
        "date": "",
    }
