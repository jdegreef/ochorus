"""Test helpers shared across apps."""

from __future__ import annotations

from contextlib import contextmanager
from unittest import mock

from django.core.cache.backends.locmem import LocMemCache


@contextmanager
def enforcing_throttle(throttle_cls, rate: str):
    """Make one throttle actually count, at ``rate``, for the block.

    Throttles are inert under ``manage.py test`` — their cache alias is a dummy,
    so no test can spend another's budget (see ``common.throttling``). A test
    that wants to prove a throttle FIRES therefore has to hand it a real cache,
    and a private one at that: a shared cache would put this test's requests
    back in everyone else's bucket, which is what the dummy exists to prevent.

    The rate is patched at ``get_rate`` rather than through ``override_settings``
    because DRF binds ``THROTTLE_RATES`` to the class at import, so a settings
    override never reaches it.
    """
    private = LocMemCache(f"throttle-test-{throttle_cls.__name__}", {})
    with (
        mock.patch.object(throttle_cls, "cache", private),
        mock.patch.object(throttle_cls, "get_rate", return_value=rate),
    ):
        yield


def body_of(words: int, tag: str = "p", end: str = "") -> str:
    """Chapter/sermon HTML whose stored ``word_count`` will be exactly ``words``.

    ``Chapter.save()``/``Sermon.save()`` derive ``word_count`` from the body, so
    a test that wants a 200-word book has to supply 200 words — passing
    ``word_count=200`` beside ``body_html="<p>x</p>"`` used to stick, and now
    (correctly) does not.

    ``end`` appends to the last word without adding one, for the quality checks
    that read whether a chapter stops on terminal punctuation.
    """
    return f"<{tag}>{' '.join(['word'] * words)}{end}</{tag}>"
