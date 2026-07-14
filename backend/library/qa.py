"""Shared content-quality heuristics (the book-qa checks) + the import-preview
audit built on top of them.

``chapter_flags`` and the thresholds are the single source of truth for "what
counts as a problem chapter" — used by both the admin content audit
(``admin_views``, over already-published books) and the import preview
(``qa_report``, over freshly-parsed chapters). Keeping them here means the two
surfaces can never drift. Pure analysis — never mutates.
"""

from __future__ import annotations

import re

from .ingest import text_of

# A chapter title the chapterizer failed to capture: empty, or a bare
# "Chapter <n>" with no real heading.
GENERIC_TITLE = re.compile(r"^chapter\s+[\divxlc]+\.?$", re.IGNORECASE)
# Sentence-final punctuation; a body not ending in one of these before the next
# chapter suggests a mid-sentence split.
TERMINAL_PUNCT = tuple('.!?"\'”’»)')

# Shared chapter-quality thresholds (see the book-qa skill).
TINY_MAX = 150
GIANT_MIN = 8000
FRAG_MIN_PARAS = 10
FRAG_MIN_WORDS = 100
FRAG_MAX_AVG = 20


def chapter_flags(title, wc, body_text, body_html, has_next) -> list[str]:
    """Quality flags for one chapter (a subset of the audit heuristics).

    ``empty`` short-circuits the body checks. Returns short flag strings such as
    ``generic-title`` / ``tiny`` / ``mid-split``.
    """
    flags = []
    t = (title or "").strip()
    body = (body_text or "").strip()
    if not t or GENERIC_TITLE.match(t):
        flags.append("generic-title")
    if not body or wc == 0:
        flags.append("empty")
        return flags
    if 0 < wc < TINY_MAX:
        flags.append("tiny")
    if wc > GIANT_MIN:
        flags.append("giant")
    paras = (body_html or "").count("<p")
    if paras >= FRAG_MIN_PARAS and wc >= FRAG_MIN_WORDS and wc / paras < FRAG_MAX_AVG:
        flags.append("fragmented")
    first_alpha = next((c for c in body if c.isalpha()), "")
    if first_alpha and first_alpha.islower():
        flags.append("no-dropcap")
    if has_next and not body.endswith(TERMINAL_PUNCT):
        flags.append("mid-split")
    return flags


# flag → (stable check id for the preview, severity)
_FLAG_MAP = {
    "generic-title": ("generic_title", "high"),
    "empty": ("empty_body", "high"),
    "mid-split": ("mid_sentence_split", "high"),
    "tiny": ("tiny_chapter", "medium"),
    "fragmented": ("fragmented_paragraphs", "medium"),
    "no-dropcap": ("missing_drop_cap", "medium"),
    "giant": ("giant_chapter", "low"),
}
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _flag_message(flag: str, words: int, paras: int) -> str:
    if flag == "generic-title":
        return "No real chapter title was captured — give it one so the contents and search read well."
    if flag == "empty":
        return "This chapter has no readable text."
    if flag == "mid-split":
        return "Chapter doesn't end on a sentence — it may run into the next one."
    if flag == "tiny":
        return f"Only {words} words — may be a split heading or a stray fragment."
    if flag == "giant":
        return f"{words:,} words — unusually long; a chapter break may have been missed."
    if flag == "fragmented":
        return f"Short average paragraph (~{words // max(paras, 1)} words) — line breaks may not have merged."
    if flag == "no-dropcap":
        return "Opens with a lowercase letter — a drop-cap capital may have been lost."
    return flag


def qa_report(chapters: list[dict]) -> list[dict]:
    """Preview warnings for parsed chapters, most reader-impacting first.

    ``chapters`` is ``[{title, html, words}]`` in reading order. Each warning is
    ``{check, severity, chapter_index, title, message}`` (``chapter_index`` is
    ``None`` for a book-level warning). Built on the shared ``chapter_flags`` so
    the preview and the admin audit agree, plus the cross-chapter duplicate-title
    check.
    """
    if not chapters:
        return [
            {
                "check": "no_chapters",
                "severity": "high",
                "chapter_index": None,
                "title": "",
                "message": "No chapters were detected in this document.",
            }
        ]

    warnings: list[dict] = []
    n = len(chapters)
    titles_seen: dict[str, list[int]] = {}

    for i, ch in enumerate(chapters):
        title = (ch.get("title") or "").strip()
        html = ch.get("html") or ""
        words = ch.get("words") or 0
        label = title or f"Chapter {i + 1}"
        paras = html.count("<p")
        flags = chapter_flags(title, words, text_of(html), html, has_next=(i < n - 1))
        for flag in flags:
            check, severity = _FLAG_MAP[flag]
            warnings.append(
                {
                    "check": check,
                    "severity": severity,
                    "chapter_index": i,
                    "title": label,
                    "message": _flag_message(flag, words, paras),
                }
            )
        if title:
            titles_seen.setdefault(title.lower(), []).append(i)

    for idxs in titles_seen.values():
        if len(idxs) > 1:
            first = idxs[0]
            warnings.append(
                {
                    "check": "duplicate_title",
                    "severity": "medium",
                    "chapter_index": first,
                    "title": chapters[first].get("title") or "",
                    "message": f"{len(idxs)} chapters share this title — sub-headings may be mistaken for chapters.",
                }
            )

    warnings.sort(
        key=lambda w: (
            _SEVERITY_ORDER[w["severity"]],
            w["chapter_index"] if w["chapter_index"] is not None else -1,
        )
    )
    return warnings
