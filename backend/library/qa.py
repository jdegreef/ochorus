"""Content-quality checks run on an import preview before publishing.

Ports the book-qa audit heuristics into code so the admin sees warnings inline
(generic titles, front matter as a chapter, mid-sentence chapter splits,
tiny/fragmented chapters, missing drop-caps, duplicate titles) rather than
discovering them after the book is live. Pure analysis — never mutates.

Input is a list of preview chapters ``[{title, html, words}]`` in reading order,
the same shape ``parse_upload`` produces.
"""

from __future__ import annotations

import re

from .ingest import is_front_matter, text_of

TINY_WORDS = 150
GIANT_WORDS = 8000
MIN_WORDS_PER_PARA = 25
# A bare "Chapter 3" / "Chapter IV." with no real heading — the chapterizer
# fell back to a number instead of capturing the actual title.
GENERIC_TITLE_RE = re.compile(r"^chapter\s+[\divxlcdm]+\.?$", re.I)
# Sentence-ending punctuation, incl. closing quotes / ellipsis / bracket.
TERMINAL_PUNCT_RE = re.compile(r"[.!?\"'”’…\)]$")

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _para_count(html: str) -> int:
    return len(re.findall(r"<p[ >]", html))


def qa_report(chapters: list[dict]) -> list[dict]:
    """Return preview warnings, most reader-impacting first.

    Each warning is ``{check, severity, chapter_index, title, message}`` where
    ``chapter_index`` is 0-based (``None`` for a book-level warning).
    """
    warnings: list[dict] = []

    def add(check: str, severity: str, message: str, i: int | None = None, title: str = "") -> None:
        warnings.append(
            {
                "check": check,
                "severity": severity,
                "chapter_index": i,
                "title": title,
                "message": message,
            }
        )

    if not chapters:
        add("no_chapters", "high", "No chapters were detected in this document.")
        return warnings

    n = len(chapters)
    titles_seen: dict[str, list[int]] = {}

    for i, ch in enumerate(chapters):
        title = (ch.get("title") or "").strip()
        html = ch.get("html") or ""
        words = ch.get("words") or 0
        text = text_of(html)
        label = title or f"Chapter {i + 1}"

        if not text:
            add("empty_body", "high", "This chapter has no readable text.", i, label)
            continue  # body-based checks below are meaningless without text

        if not title or GENERIC_TITLE_RE.match(title):
            add(
                "generic_title",
                "high",
                "No real chapter title was captured — give it one so the contents and search read well.",
                i,
                label,
            )
        elif is_front_matter(title):
            add(
                "front_matter_as_chapter",
                "high",
                "This looks like front matter (contents / index / title page), not a chapter.",
                i,
                label,
            )

        if title:
            titles_seen.setdefault(title.lower(), []).append(i)

        # A chapter that doesn't end on a sentence probably runs into the next
        # one — only meaningful when a following chapter exists.
        if i < n - 1 and not TERMINAL_PUNCT_RE.search(text):
            add(
                "mid_sentence_split",
                "high",
                "Chapter doesn't end on a sentence — it may run into the next one.",
                i,
                label,
            )

        first_alpha = next((c for c in text if c.isalpha()), "")
        if first_alpha and first_alpha.islower():
            add(
                "missing_drop_cap",
                "medium",
                "Opens with a lowercase letter — a drop-cap capital may have been lost.",
                i,
                label,
            )

        paras = _para_count(html)
        if paras and words / paras < MIN_WORDS_PER_PARA:
            add(
                "fragmented_paragraphs",
                "medium",
                f"Short average paragraph (~{words // paras} words) — line breaks may not have merged.",
                i,
                label,
            )

        if words < TINY_WORDS:
            add(
                "tiny_chapter",
                "medium",
                f"Only {words} words — may be a split heading or a stray fragment.",
                i,
                label,
            )
        elif words > GIANT_WORDS:
            add(
                "giant_chapter",
                "low",
                f"{words:,} words — unusually long; a chapter break may have been missed.",
                i,
                label,
            )

    for idxs in titles_seen.values():
        if len(idxs) > 1:
            first = idxs[0]
            add(
                "duplicate_title",
                "medium",
                f"{len(idxs)} chapters share this title — sub-headings may be mistaken for chapters.",
                first,
                chapters[first].get("title") or "",
            )

    warnings.sort(
        key=lambda w: (
            SEVERITY_ORDER[w["severity"]],
            w["chapter_index"] if w["chapter_index"] is not None else -1,
        )
    )
    return warnings
