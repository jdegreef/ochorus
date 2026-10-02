"""The email streams a reader can opt in and out of, per the preference center.

A "stream" is a kind of email, finer-grained than the two legacy booleans
(``lifecycle_opt_in`` / ``newsletter_opt_in``). The preference center shows one
toggle per stream; ``EmailSubscription.wants_stream`` reads a reader's choice,
defaulting ON (opt-out posture). New streams are added here as the emails that
use them are built — a stream with no sender yet is still a valid choice a
reader can pre-set.

``legacy`` names the old boolean a stream inherits its default from, so an
existing opt-out (there was only ever the master switch, but be safe) is honored
until the reader sets the stream explicitly.
"""

from __future__ import annotations

STREAMS: list[dict] = [
    {
        "key": "onboarding",
        "label": "Onboarding & tips",
        "description": "Getting started, reading plans, finding your way in.",
        "legacy": "lifecycle_opt_in",
    },
    {
        "key": "digest",
        "label": "Monthly digest",
        "description": "A short “for you” each month — picks from what you’ve read and loved.",
        "legacy": None,
    },
    {
        "key": "plan_reminders",
        "label": "Reading-plan reminders",
        "description": "Today’s reading from a plan you’ve started.",
        "legacy": None,
    },
    {
        "key": "series",
        "label": "Continue the series",
        "description": "When you finish a book in a series, a nudge toward the next one.",
        "legacy": None,
    },
    {
        "key": "new_in_language",
        "label": "New in your language",
        "description": "When a book you’d want is newly translated.",
        "legacy": None,
    },
    {
        "key": "announcements",
        "label": "Announcements",
        "description": "New sections and the occasional note from Ochorus.",
        "legacy": "newsletter_opt_in",
    },
]

STREAM_KEYS = frozenset(s["key"] for s in STREAMS)
LEGACY_FIELD: dict[str, str | None] = {s["key"]: s["legacy"] for s in STREAMS}

#: A lifecycle step whose own stream differs from the default "onboarding" one.
#: Most lifecycle steps are onboarding; a behavioural nudge like finish-the-series
#: belongs to its own stream so a reader can keep onboarding tips but silence the
#: series pokes (or the reverse). ``stream_for`` reads this; see emails/models.py.
STEP_STREAM: dict[str, str] = {
    "finish_series": "series",
}

def require_stream(stream: str) -> str:
    """Return ``stream`` if it names a real stream, else raise ``ValueError``.

    A typo'd key would otherwise resolve to its default (ON for a stream with no
    legacy boolean), so an unknown stream silently reads as *wanted* — a
    miscounted metric or a mis-sent email rather than a loud failure. Call this
    at the stream-consent entry points to turn that into an error."""
    if stream not in STREAM_KEYS:
        raise ValueError(f"unknown email stream: {stream!r}")
    return stream
