"""What the team did to readers, for drawing against reader activity: emails
sent to readers, languages taken live, and works added.

Read from the source tables, not the admin activity log: works arrive through
fixture imports, which never log an action. Only things that reached readers
count. Lifecycle emails go out every day (background, not an event), and
drafts, tests and canceled broadcasts never reached anyone. Works are one event
per week, however many were added, so a big import doesn't bury the row.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

from .weeks import day_of, week_start


def team_events(since: datetime) -> list[dict]:
    """Everything since ``since``, oldest first, as ``{at, kind, title,
    detail}`` (``kind`` is email, language or works)."""
    from emails.models import Broadcast

    from .languages import entry as language_entry
    from .models import Book, Language, Sermon

    events = []
    for name, at, tally in Broadcast.objects.filter(
        send_started_at__gte=since, status__in=Broadcast.MAILED
    ).values_list("name", "send_started_at", "send_tally"):
        sent = (tally or {}).get("sent", 0)
        events.append(
            _event(
                at, "email", name, f"sent to {sent} reader{'' if sent == 1 else 's'}"
            )
        )
    for name, at in Language.objects.filter(went_live_at__gte=since).values_list(
        "name", "went_live_at"
    ):
        events.append(
            _event(at, "language", f"{name} went live", "now in the language switcher")
        )

    added: dict = defaultdict(Counter)  # week -> language -> works
    first: dict = {}  # week -> its earliest addition
    for model in (Book, Sermon):
        for code, at in model.objects.filter(created_at__gte=since).values_list(
            "language", "created_at"
        ):
            week = week_start(day_of(at))
            added[week][code] += 1
            first[week] = min(first.get(week, at), at)
    for week, counts in added.items():
        total = sum(counts.values())
        detail = ", ".join(
            f"{n} in {language_entry(code)['name']}" for code, n in counts.most_common()
        )
        events.append(
            _event(
                first[week],
                "works",
                f"{total} work{'' if total == 1 else 's'} added",
                detail,
            )
        )

    return sorted(events, key=lambda e: e["at"])


def _event(at: datetime, kind: str, title: str, detail: str) -> dict:
    return {"at": at, "kind": kind, "title": title, "detail": detail}
