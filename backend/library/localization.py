"""How the API decides which language a reader asked for.

One rule, one home: both the views (`_language`) and the serializers
(`LocalizedMixin`) resolve the request language through here, so the two
layers can't drift apart — they did once, which is how a localized book page
ended up serving an English author bio.
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"


def language_from_request(request) -> str:
    """The requested content language, from ``?language=``.

    Falls back to English for a missing request or a blank value.
    """
    if request is None:
        return DEFAULT_LANGUAGE
    return request.query_params.get("language") or DEFAULT_LANGUAGE


def is_english_edition(language: str) -> bool:
    """English, or an English variant of it — the Modern English edition
    (``en-modern``, library.contemporize.MODERN_LANGUAGE).

    One rule for every place that has to decide "is this English?": an English
    variant shares English prose (plan titles), English covers (the words on
    them are English) and is never a translation. Spelled once because it was
    spelled two ways — ``in ("en", MODERN_LANGUAGE)`` and ``startswith("en-")``
    — and the cover script used neither, so it would have redrawn the modern
    edition's cover as if it were a foreign one.
    """
    return language == "en" or language.startswith("en-")
