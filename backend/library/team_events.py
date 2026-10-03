"""What the team did to readers, for drawing against reader activity: emails
sent to readers, languages taken live, and works added.

Read from the source tables, not the admin activity log: works arrive through
fixture imports, which never log an action. Only things that reached readers
count: a broadcast that started sending (a canceled one too, if it got that
far), a language that is live now, and published works in a live language.
Lifecycle emails go out every day (background, not an event), and drafts and
tests never reached anyone. Works are one event per week, however many were
added, so a big import doesn't bury the row.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime

from .weeks import day_of, week_start


def team_events(since: date) -> list[dict]:
    """Everything on or after the day ``since``, oldest first, as ``{id, at,
    kind, title, detail}`` (``kind`` is email, language or works; ``id`` is
    unique and stable)."""
    from django.db.models import Q

    from emails.models import Broadcast, BroadcastStatus

    from .languages import entry as language_entry
    from .languages import live_codes
    from .models import Book, Language, Sermon

    live = live_codes()
    events = []
    for pk, name, at, tally in Broadcast.objects.filter(
        Q(status__in=Broadcast.MAILED) | Q(status=BroadcastStatus.CANCELED),
        send_started_at__date__gte=since,
    ).values_list("pk", "name", "send_started_at", "send_tally"):
        sent = (tally or {}).get("sent", 0)
        events.append(
            _event(f"email:{pk}", at, "email", name, f"sent to {sent} reader{'' if sent == 1 else 's'}")
        )
    for code, name, at in Language.objects.filter(
        code__in=live, went_live_at__date__gte=since
    ).values_list("code", "name", "went_live_at"):
        events.append(
            _event(f"language:{code}", at, "language", f"{name} went live", "now in the language switcher")
        )

    added: dict = defaultdict(Counter)  # week -> language -> works
    latest: dict = {}  # week -> its latest addition, so "recent" means any of them
    for model in (Book, Sermon):
        for code, at in model.objects.filter(
            created_at__date__gte=since, is_published=True, language__in=live
        ).values_list("language", "created_at"):
            week = week_start(day_of(at))
            added[week][code] += 1
            latest[week] = max(latest.get(week, at), at)
    for week, counts in added.items():
        total = sum(counts.values())
        detail = ", ".join(
            f"{n} in {language_entry(code)['name']}" for code, n in counts.most_common()
        )
        events.append(
            _event(
                f"works:{week.isoformat()}",
                latest[week],
                "works",
                f"{total} work{'' if total == 1 else 's'} added",
                detail,
            )
        )

    return sorted(events, key=lambda e: e["at"])


def _event(id: str, at: datetime, kind: str, title: str, detail: str) -> dict:
    return {"id": id, "at": at, "kind": kind, "title": title, "detail": detail}
