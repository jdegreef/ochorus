"""Localized topic-shelf prose and scripture — one file per language.

Topics are the highest-stakes translated prose in the library: shelf text has
**no English fallback**, so an untranslated topic is *hidden* from that
language rather than shown in English, and a language wants all of them (a
test pins full per-language coverage). This was two dicts in ``seed_topics``
— ``TOPIC_TRANSLATIONS`` and ``TOPIC_SCRIPTURE_TR`` — which made every topic
job in every language a writer of one shared file. Splitting by language
deletes the cross-language conflict, exactly as ``data/plan_translations/``
did for plans; what remains (two jobs writing one language) is genuine.

**Scripture is not the translator's to write.** A shelf's verse must come
verbatim from that language's trusted Bible via the Take Root API
(``fetch_verse_text``), with only the reference's book name localized — never
from a model's memory. The topic page renders no verse block when
``scripture`` is absent, so a shelf is complete without one; ship without a
verse rather than paraphrase.

File format, ``data/topic_translations/<language>.json``::

    {
      "_note": ["language-level guidance"],          // optional
      "<topic slug>": {
        "title": "...",
        "description": "...",
        "scripture": {"reference": "...", "text": "..."},   // optional; Take Root verbatim
        "note": ["why this wording"]                        // optional
      }
    }
"""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data" / "topic_translations"


def raw_topic_translations() -> dict[str, dict[str, dict]]:
    """``{language: {slug: entry}}`` as written, ``_note`` keys included.

    A new language is picked up by dropping in its file; the CI gate over
    these files reads them through this rather than globbing a second time.
    Deliberately UNCACHED, unlike the plan loader: ``translate_topic`` WRITES
    these files in the same process that may later seed them, and a cache
    would serve the pre-write snapshot — five small files cost microseconds,
    a stale seed costs a hidden shelf.
    """
    return {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(DATA_DIR.glob("*.json"))
    }


def _entries(payload: dict) -> dict[str, dict]:
    return {slug: e for slug, e in payload.items() if not slug.startswith("_")}


def topic_translations() -> dict[str, dict[str, tuple[str, str]]]:
    """``{language: {slug: (title, description)}}`` — what ``seed_topics`` upserts."""
    return {
        lang: {
            # Both fields unconditionally: the CI gate requires both, and a
            # file that reaches a deploy without one should fail the release
            # LOUDLY here rather than seed a half-translated shelf silently.
            slug: (e["title"], e["description"])
            for slug, e in _entries(payload).items()
        }
        for lang, payload in raw_topic_translations().items()
    }


def topic_scripture() -> dict[str, dict[str, tuple[str, str]]]:
    """``{language: {slug: (reference, text)}}`` for entries carrying a verse."""
    return {
        lang: {
            slug: (e["scripture"]["reference"], e["scripture"]["text"])
            for slug, e in _entries(payload).items()
            if "scripture" in e
        }
        for lang, payload in raw_topic_translations().items()
    }


def topic_seo() -> dict[str, dict[str, tuple[str, str]]]:
    """``{language: {slug: (seo_title, meta_description)}}`` for entries that
    carry a localized SEO override.

    Optional per entry, like ``scripture``: a shelf without one keeps the
    localized-title default in that locale (the reader falls back). Both keys
    are required together when either is present, so a half-written override
    fails the release here rather than seeding a stray title with no blurb.
    """
    return {
        lang: {
            slug: (e["seo_title"], e["meta_description"])
            for slug, e in _entries(payload).items()
            if "seo_title" in e or "meta_description" in e
        }
        for lang, payload in raw_topic_translations().items()
    }
