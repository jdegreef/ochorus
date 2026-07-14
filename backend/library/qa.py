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


# One table maps each chapter_flags flag → (preview check id, severity, message
# builder). Keeping the id/severity/message together means adding a flag is a
# single edit, and an unmapped flag is skipped (below) rather than crashing.
_FLAG_INFO = {
    "generic-title": (
        "generic_title",
        "high",
        lambda w, p: "No real chapter title was captured — give it one so the contents and search read well.",
    ),
    "empty": (
        "empty_body",
        "high",
        lambda w, p: "This chapter has no readable text.",
    ),
    "mid-split": (
        "mid_sentence_split",
        "high",
        lambda w, p: "Chapter doesn't end on a sentence — it may run into the next one.",
    ),
    "tiny": (
        "tiny_chapter",
        "medium",
        lambda w, p: f"Only {w} words — may be a split heading or a stray fragment.",
    ),
    "fragmented": (
        "fragmented_paragraphs",
        "medium",
        lambda w, p: f"Short average paragraph (~{w // max(p, 1)} words) — line breaks may not have merged.",
    ),
    "no-dropcap": (
        "missing_drop_cap",
        "medium",
        lambda w, p: "Opens with a lowercase letter — a drop-cap capital may have been lost.",
    ),
    "giant": (
        "giant_chapter",
        "low",
        lambda w, p: f"{w:,} words — unusually long; a chapter break may have been missed.",
    ),
}
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


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
            info = _FLAG_INFO.get(flag)
            if info is None:  # a flag with no preview mapping — skip, never crash
                continue
            check, severity, message = info
            warnings.append(
                {
                    "check": check,
                    "severity": severity,
                    "chapter_index": i,
                    "title": label,
                    "message": message(words, paras),
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
                    "title": (chapters[first].get("title") or "").strip(),
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
