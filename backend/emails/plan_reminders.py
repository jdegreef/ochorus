"""Reading-plan reminders — "today's reading" from a plan the reader started.

A reader who asked for email reminders on a plan (``PlanSchedule.email_reminder``,
chosen when they start it) gets that day's chapter by email at about their
reminder time (``remind_at``, "HH:MM" in their own wall-clock time). A time set
only for the calendar file's alerts never starts emails.
The ``send_email_cron`` pass runs every 15 minutes, so "about" means within one
pass; a send more than ``SEND_WINDOW`` late is dropped rather than arriving at
an odd hour.

Rules, in the order they're checked:

* only on the plan's reading days (daily / weekdays / Monday–Saturday — the
  same rule the calendar view lays the plan out with, ``lib/planSchedule.ts``);
* not on a day the reader has already read (a ``ReadingDay`` for their local
  date) — the reminder is for the day they'd otherwise miss;
* not once the plan is finished;
* after ``IDLE_DAYS`` days with no reading, one gentle "your place is saved"
  email instead, then nothing until they read again — a reminder nobody acts on
  turns into noise, and noise is how a reader unsubscribes from everything.

At most one plan email a day per reader (the idempotency key is the local
date), for the plan started most recently. It is the reader's own request, so
it does NOT take the shared 20h lifecycle slot (``lifecycle.UNGATED_STEPS``),
and it has its own preference-centre stream, ``plan_reminders``.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from library.models import Article, Chapter, Plan, PlanDay
from reading.models import PlanProgress, PlanSchedule, ReadingDay

from . import links
from .models import (
    EmailKind,
    EmailMessage,
    EmailSubscription,
    SendStatus,
    idempotency_key,
)
from .recipient import verified_email
from .rendering import email_language, render_plan_reminder
from .sending import deliver

PLAN_REMINDER_STEP = "plan_reminder"
PLAN_PAUSED_STEP = "plan_paused"

#: A reminder later than this after its time is dropped, not sent late.
SEND_WINDOW = timedelta(hours=3)
#: Days without reading after which reminders pause (one "paused" email).
IDLE_DAYS = 3


def reads_on(day: date, rule: str) -> bool:
    """Whether ``rule`` has a reading on ``day`` — the Python twin of the
    frontend's ``readsOn`` (lib/planSchedule.ts)."""
    weekday = day.weekday()  # Monday = 0 … Sunday = 6
    if rule == PlanSchedule.ReadingDays.WEEKDAYS:
        return weekday < 5
    if rule == PlanSchedule.ReadingDays.MONSAT:
        return weekday != 6
    return True


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name) if name else ZoneInfo("UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _remind_time(value: str) -> time | None:
    try:
        hours, minutes = (int(p) for p in value.split(":"))
        return time(hours, minutes)
    except (ValueError, TypeError):
        return None


class Due(NamedTuple):
    """The plan email due for a reader now: which step, plan, day, and date."""

    step: str
    plan: Plan
    day: PlanDay
    local_date: date
    #: The paused email's once-only anchor: the last day they read (or started).
    anchor: date | None = None


def due_plan_email(profile, subscription, now: datetime) -> Due | None:
    """The plan email ``profile`` is due right now, or ``None``."""
    zone = _zone(profile.timezone)
    local_now = now.astimezone(zone)
    local_date = local_now.date()
    # The plan edition is the one they READ (their reading locale), which an
    # email-language override doesn't change.
    lang = (profile.locale or "en").split("-")[0]

    schedules = {
        s.plan_slug: s
        for s in PlanSchedule.objects.filter(profile=profile, email_reminder=True).exclude(remind_at="")
    }
    if not schedules:
        return None
    progress = PlanProgress.objects.filter(
        profile=profile, plan_slug__in=schedules
    ).order_by("-started_at")

    last_read = (
        ReadingDay.objects.filter(profile=profile).order_by("-day").values_list("day", flat=True).first()
    )
    read_today = last_read == local_date

    for p in progress:
        schedule = schedules[p.plan_slug]
        if not in_window(schedule.remind_at, local_now):
            continue
        if not reads_on(local_date, schedule.reading_days):
            continue
        # The plan in the reader's language. No English fallback: content in
        # another language isn't what they started (CLAUDE.md, content model).
        plan = Plan.objects.filter(slug=p.plan_slug, language=lang, is_published=True).first()
        if plan is None:
            continue
        done = set(p.done or [])
        day = plan.days.exclude(day__in=done).order_by("day").first()
        if day is None:
            continue  # finished
        if read_today:
            return None
        started = timezone.localtime(p.started_at, zone).date()
        anchor = max(d for d in (last_read, started) if d is not None)
        if (local_date - anchor).days >= IDLE_DAYS:
            return Due(PLAN_PAUSED_STEP, plan, day, local_date, anchor)
        return Due(PLAN_REMINDER_STEP, plan, day, local_date)
    return None


def in_window(remind_at: str, local_now: datetime) -> bool:
    """Whether ``local_now`` is within ``SEND_WINDOW`` after ``remind_at``."""
    at = _remind_time(remind_at)
    if at is None:
        return False
    due_at = datetime.combine(local_now.date(), at, tzinfo=local_now.tzinfo)
    return due_at <= local_now < due_at + SEND_WINDOW


def _reading_title(day: PlanDay, language: str) -> str:
    if day.article_slug:
        article = Article.objects.filter(slug=day.article_slug, language=language).only("h1").first()
        return article.h1 if article else ""
    chapter = (
        Chapter.objects.filter(
            book__slug=day.book_slug, book__language=language, order=day.chapter_order or 1
        )
        .only("title")
        .first()
    )
    return chapter.title if chapter else ""


def day_path(plan: Plan, day: PlanDay) -> str:
    """The reader-site path for a plan day — the email twin of the frontend's
    ``planDayPath``: the chapter (or article) with ``?plan=&day=`` so the page
    shows the plan's day bar and "mark day done"."""
    query = f"?plan={plan.slug}&day={day.day}"
    if day.article_slug:
        return links.localized(f"articles/{day.article_slug}/{query}", plan.language)
    return links.localized(f"books/{day.book_slug}/{day.chapter_order or 1}/{query}", plan.language)


def _send(profile, subscription, due: Due) -> EmailMessage | None:
    discriminator = (
        # Once per idle stretch per reader, whichever plan noticed it.
        f"{PLAN_PAUSED_STEP}:{due.anchor.isoformat()}"
        if due.step == PLAN_PAUSED_STEP
        else f"{PLAN_REMINDER_STEP}:{due.local_date.isoformat()}"
    )
    key = idempotency_key(EmailKind.LIFECYCLE, discriminator, profile)
    # Already sent this one: skip before rendering, so the passes in the rest
    # of the window cost nothing and aren't counted as sends.
    if EmailMessage.objects.filter(idempotency_key=key, status=SendStatus.SENT).exists():
        return None
    to_email = verified_email(profile)
    if not to_email:
        return None
    total = due.plan.days.count()
    rendered = render_plan_reminder(
        profile,
        subscription,
        step=due.step,
        plan_title=due.plan.title,
        day=due.day.day,
        total=total,
        reading_title=_reading_title(due.day, due.plan.language),
        cta_path=day_path(due.plan, due.day),
    )
    return deliver(
        profile=profile,
        subscription=subscription,
        kind=EmailKind.LIFECYCLE,
        rendered=rendered,
        idempotency_key=key,
        to_email=to_email,
        locale=email_language(profile, subscription),
        lifecycle_step=due.step,
    )


def send_due(profile, now: datetime | None = None) -> EmailMessage | None:
    """Send the plan email this reader is due now, if any."""
    subscription, _ = EmailSubscription.objects.get_or_create(profile=profile)
    if not subscription.wants(EmailKind.LIFECYCLE, PLAN_REMINDER_STEP):
        return None
    due = due_plan_email(profile, subscription, now or timezone.now())
    if due is None:
        return None
    return _send(profile, subscription, due)


def candidates(now: datetime | None = None):
    """Profiles with an email-reminder plan whose time falls in the send window
    now, in their own time zone. The window test is cheap and done here, so a
    pass only does the real work for the few readers actually due — and never
    stops at an arbitrary cap with later readers starved."""
    now = now or timezone.now()
    seen: set[int] = set()
    out = []
    schedules = (
        PlanSchedule.objects.filter(email_reminder=True)
        .exclude(remind_at="")
        .select_related("profile")
        .order_by("profile_id")
    )
    for s in schedules.iterator():
        if s.profile_id in seen:
            continue
        if in_window(s.remind_at, now.astimezone(_zone(s.profile.timezone))):
            seen.add(s.profile_id)
            out.append(s.profile)
    return out
