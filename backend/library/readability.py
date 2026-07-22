"""A reading-difficulty estimate for works — the badge, not a science.

A Flesch-Reading-Ease-style score with a cheap vowel-group syllable estimate,
bucketed into three honest labels. Nineteenth-century devotional prose skews
long-sentenced, so the brackets are calibrated to spread the library rather
than to grade modern web copy: the point is relative guidance ("this one is
heavier going than that one"), which is exactly what a reader choosing between
two classics needs.
"""

from __future__ import annotations

import re
from functools import lru_cache

ACCESSIBLE = "accessible"
MODERATE = "moderate"
ADVANCED = "advanced"

_WORD = re.compile(r"[A-Za-z’']+")
_SENTENCE_END = re.compile(r"[.!?]+")
_VOWEL_GROUP = re.compile(r"[aeiouy]+", re.IGNORECASE)

# How much text is enough: difficulty stabilises quickly, so cap the sample
# and spare the CPU on a 100k-word book.
_SAMPLE_CHARS = 20_000


def _syllables(word: str) -> int:
    """Vowel-group count with a silent-e discount — crude but consistent."""
    count = len(_VOWEL_GROUP.findall(word))
    if word.lower().endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def flesch_reading_ease(text: str) -> float | None:
    """The classic score (higher = easier), or None for too-little text."""
    sample = text[:_SAMPLE_CHARS]
    words = _WORD.findall(sample)
    if len(words) < 100:
        return None
    sentences = max(1, len(_SENTENCE_END.findall(sample)))
    syllables = sum(_syllables(w) for w in words)
    return 206.835 - 1.015 * (len(words) / sentences) - 84.6 * (syllables / len(words))


@lru_cache(maxsize=1024)
def difficulty(text: str) -> str | None:
    """'accessible' | 'moderate' | 'advanced', or None when there's too little
    text to judge. Cached — the same body is scored on every detail request."""
    score = flesch_reading_ease(text)
    if score is None:
        return None
    if score >= 70:
        return ACCESSIBLE
    if score >= 50:
        return MODERATE
    return ADVANCED
