"""Group totals for "read together" (``ReadingGroup``).

Everything a group shows is a count, and the counting is built so that a
number can't be turned back into what one person did:

- **A floor.** No count is shown for a group with fewer than ``MIN_COUNTED``
  members: with two or three people, "1 of 2 has read" tells each exactly
  what the others did.
- **Today only.** A count is given only for the day the group is on now
  (``current_days``), never for an arbitrary past day — so nobody can read a
  member's whole history off a run of totals taken before and after they
  joined.
- **From joining on.** A member counts for a day only if they finished it
  after joining (``ReadingGroupMember.baseline``), so last year's run through
  the same plan doesn't read as this week's.
- **Opt-in, and bounded in time.** Nobody is counted until they ask to be —
  the leader included — and a group ends ``LIFETIME`` after it starts.

Nothing here returns a name, an email or a list of members — to anyone, the
leader included.
"""

from __future__ import annotations

import secrets
from datetime import date, timedelta

from emails.plan_reminders import reads_on
from library.models import PlanDay

from .models import PlanProgress, ReadingGroup, ReadingGroupMember

#: The fewest members before a group's "have read" count is shown.
MIN_COUNTED = 5

#: How many groups one account may lead, how many it may be counted in, and
#: how many may be counted in one group — bounds against scripted use, far
#: above any real reader's need.
MAX_GROUPS_LED = 50
MAX_GROUPS_JOINED = 100
MAX_MEMBERS = 500

#: A group's totals end this long after it starts (the longest plans run a
#: few months); after that it reads as gone and is cleared away.
LIFETIME = timedelta(days=183)


def new_code() -> str:
    """A random, unguessable code for a group's link (12 URL-safe characters)."""
    while True:
        code = secrets.token_urlsafe(9)
        if not ReadingGroup.objects.filter(code=code).exists():
            return code


def live(today: date):
    """The groups still running on `today`."""
    return ReadingGroup.objects.filter(start_on__gt=today - LIFETIME)


def purge_expired(today: date) -> None:
    """Clear away the groups that have ended, and their members with them."""
    ReadingGroup.objects.filter(start_on__lte=today - LIFETIME).delete()


def day_count(group: ReadingGroup) -> int:
    """How many days the group's plan has (the most any edition of it has)."""
    days = PlanDay.objects.filter(plan__slug=group.plan_slug).values_list("day", flat=True)
    return max(days, default=0)


def reached(group: ReadingGroup, on: date, days: int) -> int:
    """The last day of the plan the group has reached by `on` — the day whose
    count it shows (the frontend's ``countedDay``): today's reading, the last
    one on a rest day, the plan's last once it has finished, 0 before."""
    n, d = 0, group.start_on
    while d <= on and n < days:
        if reads_on(d, group.reading_days):
            n += 1
        d += timedelta(days=1)
    return n


def current_days(group: ReadingGroup, today: date) -> set[int]:
    """The days a reader somewhere in the world may be on now: `today` is the
    server's date, and a reader's own is at most a day either side."""
    days = day_count(group)
    return {reached(group, today + timedelta(days=k), days) for k in (-1, 0, 1)} - {0}


def done_count(group: ReadingGroup, day: int) -> int:
    """How many of the group's members have finished `day` since joining."""
    members = list(ReadingGroupMember.objects.filter(group=group).values_list("profile_id", "baseline"))
    done_by = dict(
        PlanProgress.objects.filter(
            plan_slug=group.plan_slug, profile_id__in=[p for p, _ in members]
        ).values_list("profile_id", "done")
    )
    return sum(
        1
        for profile, baseline in members
        if day in (done_by.get(profile) or []) and day not in (baseline or [])
    )


def baseline(profile, plan_slug: str) -> list[int]:
    """The days `profile` had already finished of a plan — what joining a
    group must not count as read for it."""
    row = PlanProgress.objects.filter(profile=profile, plan_slug=plan_slug).first()
    return list(row.done) if row and isinstance(row.done, list) else []


def totals(group: ReadingGroup, day: int | None, today: date) -> dict:
    """The group's numbers: members, and — once there are enough of them to
    hide in, and only for the day the group is on — how many have read it."""
    members = group.members.count()
    counted = bool(day) and members >= MIN_COUNTED and day in current_days(group, today)
    return {
        "members": members,
        "day": day,
        "done": done_count(group, day) if counted else None,
        "min_counted": MIN_COUNTED,
    }
