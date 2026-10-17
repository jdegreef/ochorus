"""Automations: flows an admin builds — "when a reader does X, wait, check Y,
send this email" — run by the email cron.

An :class:`Automation` has a **trigger** (:data:`TRIGGERS`), an ordered list of
**steps** — ``wait`` (days/hours), ``condition`` (one of :data:`CHECKS`, or its
opposite; a reader who fails it leaves), ``email`` (an :class:`AutomationEmail`)
— and **exit** conditions that take a reader out before any step.

Each cron pass (:func:`run_due`):

1. **Enrols** readers whose trigger happened since the last scan — never
   before the automation was switched on, so turning one on doesn't mail
   everyone who ever finished a book. Each reader enters an automation at most
   once (a unique row).
2. **Advances** every run that is due, step by step, until it reaches a wait,
   the end, or an email it must hold back.

Emails obey the automation's preference-center stream, suppression and the
20-hour gap shared by every automated email (a held email waits for the gap,
it isn't dropped). A reader whose language the email isn't written in — or only
as an unapproved AI draft — skips that email and carries on (there is no English
fallback). Sends are keyed per (automation, email, reader), so a step can never
send twice.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from django.utils import timezone

from accounts.models import UserProfile
from reading.models import PlanProgress, ReadingProgress, WorkKind

from . import translation_jobs
from .lifecycle import MIN_GAP, last_lifecycle_sent_at
from .models import (
    Automation,
    AutomationEmail,
    AutomationRun,
    EmailEvent,
    EmailKind,
    EmailMessage,
    EmailSubscription,
    EventType,
    RunStatus,
    SendStatus,
    idempotency_key,
)
from .recipient import verified_email
from .rendering import email_language, render_blocks, sendable_locales
from .sending import deliver
from .streams import STREAM_KEYS

logger = logging.getLogger(__name__)

#: Runs advanced per cron pass at most; the rest are picked up next pass.
BATCH = 500
#: How long before the switch-on a synced event may have happened (a book
#: finished offline the evening before still counts).
SYNC_GRACE = timedelta(days=1)


@dataclass(frozen=True)
class Param:
    key: str
    label: str
    #: "book" / "author" / "plan" (a library slug), or "number".
    kind: str
    required: bool = False
    default: int | None = None


@dataclass(frozen=True)
class Kind:
    key: str
    label: str
    params: tuple[Param, ...] = field(default_factory=tuple)


TRIGGERS: dict[str, Kind] = {
    k.key: k
    for k in (
        Kind("signed_up", "Reader signs up"),
        Kind(
            "finished_book",
            "Reader finishes a book",
            (Param("author", "By this author (optional)", "author"), Param("book", "This book (optional)", "book")),
        ),
        Kind("started_plan", "Reader starts a reading plan", (Param("plan", "This plan (optional)", "plan"),)),
        Kind("went_quiet", "Reader goes quiet", (Param("days", "For this many days", "number", True, 14),)),
    )
}

CHECKS: dict[str, Kind] = {
    k.key: k
    for k in (
        Kind("has_plan", "has started a reading plan"),
        Kind("started_book", "has started the book", (Param("book", "Book", "book", True),)),
        Kind("finished_book", "has finished the book", (Param("book", "Book", "book", True),)),
        Kind("finished_books", "has finished at least this many books", (Param("count", "Books", "number", True, 1),)),
        Kind("active_within", "has read on Ochorus in the last days", (Param("days", "Days", "number", True, 7),)),
        Kind("opened_last", "opened this automation’s last email"),
        Kind("clicked_last", "clicked this automation’s last email"),
    )
}

STEP_TYPES = ("wait", "condition", "email")


def vocabulary() -> dict:
    """What the builder offers, for the admin UI."""

    def kinds(table: dict[str, Kind]) -> list[dict]:
        return [
            {
                "key": k.key,
                "label": k.label,
                "params": [
                    {"key": p.key, "label": p.label, "kind": p.kind, "required": p.required, "default": p.default}
                    for p in k.params
                ],
            }
            for k in table.values()
        ]

    from .streams import STREAMS

    return {
        "triggers": kinds(TRIGGERS),
        "checks": kinds(CHECKS),
        "streams": [{"key": s["key"], "label": s["label"]} for s in STREAMS],
    }


# --- Checking a flow -----------------------------------------------------------------


def _int(value, default: int = 0) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _param_problems(kind: Kind, given: dict, where: str) -> list[str]:
    out = []
    for p in kind.params:
        value = given.get(p.key)
        if p.required and value in (None, ""):
            out.append(f"{where}: choose {p.label.lower()}")
        elif p.kind == "number" and value not in (None, "") and _int(value, -1) < 1:
            out.append(f"{where}: {p.label.lower()} must be a whole number above 0")
    return out


def problems(automation: Automation) -> list[str]:
    """What stops ``automation`` being switched on, in words."""
    out = []
    trigger = TRIGGERS.get((automation.trigger or {}).get("type", ""))
    if trigger is None:
        out.append("Choose what starts it.")
    else:
        out += _param_problems(trigger, automation.trigger, "Starts when")
    emails = {e.pk: e for e in automation.emails.all()}
    sends = 0
    for i, step in enumerate(automation.steps or []):
        where = f"Step {i + 1}"
        kind = step.get("type")
        if kind == "wait":
            if _int(step.get("days")) == 0 and _int(step.get("hours")) == 0:
                out.append(f"{where}: a wait needs a number of days or hours")
        elif kind == "condition":
            check = CHECKS.get(step.get("check", ""))
            if check is None:
                out.append(f"{where}: choose a condition")
            else:
                out += _param_problems(check, step, where)
        elif kind == "email":
            email = emails.get(step.get("email"))
            if email is None:
                out.append(f"{where}: the email is missing")
            elif not ready_locales(email):
                why = "; ".join(f"{code}: {p}" for code in sendable_locales(email) for p in language_problems(email, code))
                out.append(f"{where}: the email isn't ready in any language yet{f' ({why})' if why else ''}")
            else:
                sends += 1
        else:
            out.append(f"{where}: unknown step")
    for i, cond in enumerate(automation.exit or []):
        check = CHECKS.get(cond.get("check", ""))
        if check is None:
            out.append(f"Leaves early {i + 1}: choose a condition")
        else:
            out += _param_problems(check, cond, f"Leaves early {i + 1}")
    if not sends:
        out.append("Add at least one email.")
    if automation.stream not in STREAM_KEYS:
        out.append("Choose which email preference it obeys.")
    return out


def clean_steps(steps) -> list[dict]:
    """Keep known step types and their own fields (ids kept for the UI)."""
    out = []
    for raw in steps if isinstance(steps, list) else []:
        if not isinstance(raw, dict) or raw.get("type") not in STEP_TYPES:
            continue
        step = {"id": str(raw.get("id") or "")[:40], "type": raw["type"]}
        if raw["type"] == "wait":
            step |= {"days": _int(raw.get("days")), "hours": _int(raw.get("hours"))}
        elif raw["type"] == "condition":
            step |= _clean_condition(raw)
        else:
            step["email"] = _int(raw.get("email")) or None
        out.append(step)
    return out[:50]


def _clean_condition(raw: dict) -> dict:
    out = {"check": str(raw.get("check") or ""), "negate": bool(raw.get("negate"))}
    check = CHECKS.get(out["check"])
    for p in check.params if check else ():
        value = raw.get(p.key)
        out[p.key] = _int(value, p.default or 0) if p.kind == "number" else str(value or "")[:160]
    return out


def clean_exit(exit_) -> list[dict]:
    return [_clean_condition(c) for c in (exit_ if isinstance(exit_, list) else []) if isinstance(c, dict)][:10]


def clean_trigger(trigger) -> dict:
    trigger = trigger if isinstance(trigger, dict) else {}
    kind = TRIGGERS.get(str(trigger.get("type") or ""))
    if kind is None:
        return {}
    out = {"type": kind.key}
    for p in kind.params:
        value = trigger.get(p.key)
        out[p.key] = _int(value, p.default or 0) if p.kind == "number" else str(value or "")[:160]
    return out


# --- Who it is ready for -----------------------------------------------------------------


def language_problems(email: AutomationEmail, code: str) -> list[str]:
    """What stops ``email`` going out in ``code``: an empty subject, no content,
    or a template hint still in it (``[Like this]`` — preflight's rule)."""
    from . import blocks as blocks_mod
    from .preflight import STARTER_HINTS, _placeholder

    subject = str(email.subject.get(code) or "")
    content = email.content.get(code) or {}
    blocks = blocks_mod.blocks_for(content)
    library = blocks_mod.library_editions({code: blocks})
    out = []
    if not subject.strip():
        out.append("the subject is empty")
    if not blocks_mod.has_body(blocks, lambda b: code in library.get(b["type"], {}).get(b["slug"], set())):
        out.append("it has no content in this language")
    texts = [subject, str(content.get("preheader", "")), *(b.get(f, "") for b in blocks for f in blocks_mod.WORD_FIELDS)]
    hint = _placeholder(texts)
    if hint in STARTER_HINTS:
        out.append(f"“{hint}” is a template hint — replace it")
    return out


def ready_locales(email: AutomationEmail) -> list[str]:
    """Languages the email can go out in: complete, nothing left from a
    template, and not an AI draft still waiting for review."""
    states = email.translations or {}
    return [
        code
        for code in sendable_locales(email)
        if states.get(code, {}).get("state") not in (translation_jobs.State.DRAFT, translation_jobs.State.REQUESTED)
        and not language_problems(email, code)
    ]


# --- Enrolling ------------------------------------------------------------------------


def _candidates(automation: Automation, start: datetime, end: datetime) -> list[tuple[int, dict]]:
    """``(profile_id, context)`` for readers whose trigger happened in (start, end]."""
    from library.models import Book

    trigger = automation.trigger or {}
    kind = trigger.get("type")
    if kind == "signed_up":
        ids = UserProfile.objects.filter(created_at__gt=start, created_at__lte=end).values_list("id", flat=True)
        return [(pk, {}) for pk in ids]
    # Reading rows carry the reader's own clock (an offline finish syncs later
    # with its earlier time), so a scan windows on the server's updated_at and
    # then asks only that the event itself came after the switch-on.
    baseline = automation.enabled_at - SYNC_GRACE
    if kind == "finished_book":
        rows = ReadingProgress.objects.filter(
            kind=WorkKind.BOOK, updated_at__gt=start, updated_at__lte=end, finished_at__gte=baseline
        )
        if trigger.get("book"):
            rows = rows.filter(book_slug=trigger["book"])
        if trigger.get("author"):
            slugs = Book.objects.filter(author__slug=trigger["author"]).values_list("slug", flat=True).distinct()
            rows = rows.filter(book_slug__in=list(slugs))
        found: dict[int, dict] = {}
        for row in rows.order_by("finished_at").values("profile_id", "book_slug", "language"):
            found.setdefault(row["profile_id"], {"book": row["book_slug"], "language": row["language"]})
        return list(found.items())
    if kind == "started_plan":
        rows = PlanProgress.objects.filter(updated_at__gt=start, updated_at__lte=end, started_at__gte=baseline)
        if trigger.get("plan"):
            rows = rows.filter(plan_slug=trigger["plan"])
        found = {}
        for row in rows.order_by("started_at").values("profile_id", "plan_slug"):
            found.setdefault(row["profile_id"], {"plan": row["plan_slug"]})
        return list(found.items())
    if kind == "went_quiet":
        days = timedelta(days=_int(trigger.get("days"), 14) or 14)
        ids = UserProfile.objects.filter(last_seen_at__gt=start - days, last_seen_at__lte=end - days).values_list(
            "id", flat=True
        )
        return [(pk, {}) for pk in ids]
    return []


def enroll(automation: Automation, now: datetime) -> int:
    """Start a run for each reader the trigger caught since the last scan."""
    if not automation.enabled or automation.enabled_at is None:
        return 0
    start = max(automation.scanned_to or automation.enabled_at, automation.enabled_at)
    if start >= now:
        return 0
    found = _candidates(automation, start, now)
    if found:
        AutomationRun.objects.bulk_create(
            [AutomationRun(automation=automation, profile_id=pk, next_at=now, context=ctx) for pk, ctx in found],
            ignore_conflicts=True,  # at most once per reader
        )
    Automation.objects.filter(pk=automation.pk).update(scanned_to=now)
    automation.scanned_to = now
    return len(found)


# --- Checks -------------------------------------------------------------------------------


def _last_message(run: AutomationRun):
    pk = (run.context or {}).get("last_message")
    return EmailMessage.objects.filter(pk=pk).first() if pk else None


def holds(cond: dict, run: AutomationRun, now: datetime) -> bool:
    """Whether condition ``cond`` is true for the run's reader (``negate`` flips it)."""
    profile = run.profile
    check = cond.get("check")
    if check == "has_plan":
        result = PlanProgress.objects.filter(profile=profile).exists()
    elif check == "started_book":
        result = ReadingProgress.objects.filter(profile=profile, kind=WorkKind.BOOK, book_slug=cond.get("book", "")).exists()
    elif check == "finished_book":
        result = ReadingProgress.objects.filter(
            profile=profile, kind=WorkKind.BOOK, book_slug=cond.get("book", ""), finished_at__isnull=False
        ).exists()
    elif check == "finished_books":
        count = ReadingProgress.objects.filter(profile=profile, kind=WorkKind.BOOK, finished_at__isnull=False).count()
        result = count >= (_int(cond.get("count"), 1) or 1)
    elif check == "active_within":
        days = _int(cond.get("days"), 7) or 7
        result = bool(profile.last_seen_at and profile.last_seen_at >= now - timedelta(days=days))
    elif check in ("opened_last", "clicked_last"):
        message = _last_message(run)
        wanted = EventType.OPENED if check == "opened_last" else EventType.CLICKED
        result = bool(message and EmailEvent.objects.filter(message=message, type=wanted).exists())
    else:
        result = False
    return not result if cond.get("negate") else result


# --- Advancing -----------------------------------------------------------------------------


def _finish(run: AutomationRun, status: str, reason: str = "") -> None:
    run.status = status
    run.reason = reason[:200]
    run.finished_at = timezone.now()


def _send(run: AutomationRun, email: AutomationEmail, now: datetime, cache: dict) -> str:
    """Send one email step. Returns "sent", "skipped" or "held" (the 20-hour
    gap: try again at ``run.next_at``)."""
    profile = run.profile
    subscription, _ = EmailSubscription.objects.get_or_create(profile=profile)
    if not subscription.wants_stream(run.automation.stream):
        return "skipped"
    last = last_lifecycle_sent_at(profile)
    if last is not None and now - last < MIN_GAP:
        run.next_at = last + MIN_GAP
        return "held"
    lang = email_language(profile, subscription)
    ready = cache.get(("ready", email.pk))
    if ready is None:
        ready = cache[("ready", email.pk)] = ready_locales(email)
    if lang not in ready:
        return "skipped"  # not written (or not approved) in their language
    to_email = verified_email(profile)
    if not to_email:
        return "skipped"
    rendered = render_blocks(
        subject=str(email.subject.get(lang, "")),
        content=email.content.get(lang) or {},
        profile=profile,
        subscription=subscription,
        lang=lang,
        cards=cache,
    )
    message = deliver(
        profile=profile,
        subscription=subscription,
        kind=EmailKind.LIFECYCLE,
        rendered=rendered,
        idempotency_key=idempotency_key(EmailKind.LIFECYCLE, f"automation:{run.automation_id}:{email.pk}", profile),
        to_email=to_email,
        locale=lang,
        lifecycle_step=step_label(run.automation_id),
    )
    run.context = {**(run.context or {}), "last_message": message.pk}
    return "sent" if message.status == SendStatus.SENT else "skipped"


def step_label(automation_id: int) -> str:
    """What an automation's emails are filed under (``EmailMessage.lifecycle_step``)."""
    return f"automation:{automation_id}"


def advance(run: AutomationRun, now: datetime, *, emails: dict | None = None, cache: dict | None = None) -> str:
    """Take ``run`` as far as it can go now. Returns what stopped it: "wait",
    "held", "done" or "exited"."""
    automation = run.automation
    steps = automation.steps or []
    emails = {e.pk: e for e in automation.emails.all()} if emails is None else emails
    cache = {} if cache is None else cache
    outcome = "done"
    for _ in range(len(steps) + 1):
        exit_cond = next((c for c in automation.exit or [] if holds(c, run, now)), None)
        if exit_cond is not None:
            _finish(run, RunStatus.EXITED, f"left early: {exit_cond.get('check')}")
            outcome = "exited"
            break
        if run.step_index >= len(steps):
            _finish(run, RunStatus.DONE)
            outcome = "done"
            break
        step = steps[run.step_index]
        if step["type"] == "wait":
            run.step_index += 1
            run.next_at = now + timedelta(days=_int(step.get("days")), hours=_int(step.get("hours")))
            outcome = "wait"
            break
        if step["type"] == "condition":
            if not holds(step, run, now):
                _finish(run, RunStatus.EXITED, f"condition not met: {step.get('check')}")
                outcome = "exited"
                break
            run.step_index += 1
            continue
        email = emails.get(step.get("email"))
        if email is not None and _send(run, email, now, cache) == "held":
            outcome = "held"
            break
        run.step_index += 1
    run.save(update_fields=["step_index", "next_at", "status", "context", "reason", "finished_at"])
    return outcome


def run_due(now: datetime | None = None) -> dict[str, int]:
    """One cron pass: enrol, then advance what is due. Returns a tally."""
    now = now or timezone.now()
    tally = {"enrolled": 0, "advanced": 0}
    automations = list(Automation.objects.filter(enabled=True))
    for automation in automations:
        tally["enrolled"] += enroll(automation, now)
    emails: dict[int, dict] = {}
    cache: dict = {}
    due = (
        AutomationRun.objects.filter(status=RunStatus.ACTIVE, next_at__lte=now, automation__enabled=True)
        .select_related("automation", "profile")
        .order_by("next_at")[:BATCH]
    )
    for run in due:
        if run.automation_id not in emails:
            emails[run.automation_id] = {e.pk: e for e in run.automation.emails.all()}
        # No transaction around it: a send that went out stays recorded (its
        # key makes a retry a no-op) even if a later step of this run fails.
        try:
            advance(run, now, emails=emails[run.automation_id], cache=cache)
        except Exception:
            logger.exception("automation %s: run %s failed", run.automation_id, run.pk)
            tally["failed"] = tally.get("failed", 0) + 1
            continue
        tally["advanced"] += 1
    return tally


def set_enabled(automation: Automation, enabled: bool) -> None:
    """Switch on (re)starting the baseline — readers who triggered it while it
    was off aren't enrolled after the fact — or off (runs pause where they are)."""
    if enabled and not automation.enabled:
        automation.enabled_at = timezone.now()
        automation.scanned_to = automation.enabled_at
    automation.enabled = enabled


def end_active_runs(automation: Automation, reason: str) -> int:
    """End every reader's run part-way through (the steps changed under them)."""
    return AutomationRun.objects.filter(automation=automation, status=RunStatus.ACTIVE).update(
        status=RunStatus.EXITED, reason=reason[:200], finished_at=timezone.now()
    )
