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
