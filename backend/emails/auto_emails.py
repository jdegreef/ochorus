"""Campaigns the system builds on its own: the monthly digest and "new in your
language".

Both are ordinary :class:`Broadcast` rows once built, so they go out through the
same batched sender, pre-send checks, preview and guardrail as anything an admin
writes — and an admin can open one, edit it and send it like any other. What is
automatic is only the *building*: the email cron calls :func:`build_due` each
run, and each builder makes at most one campaign per period (``auto_key`` is
unique, so a build that runs twice makes one).

* **Monthly digest** (stream ``digest``) — for the first Monday of each month,
  built :data:`DRAFT_LEAD` ahead: per language, the works published there since
  the last issue, a sourced quote, a reading plan, and each reader's own book in
  progress (the ``continue_reading`` block, filled per recipient). A language
  with nothing to say that month is left out.
* **New in your language** (stream ``new_in_language``) — per language, once a
  work has been published there for :data:`NEW_BATCH_WAIT` (so a run of uploads
  goes out as one email), at most one every :data:`NEW_MIN_GAP`, oldest work
  first; a batch longer than one email carries over to the next. Only works
  published after it was switched on are announced, so turning it on doesn't
  mail the back catalogue.

Each is off until an admin switches it on (:class:`AutoEmailConfig`). With
``require_approval`` (the default) a build is a DRAFT carrying the time it is
meant for, and goes out only when an admin schedules it; without, it is
SCHEDULED at once. The words around the library picks are app copy, one block
per language in ``emails/copy.py``; a language with no copy gets no email —
never an English one (there is no English fallback).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from library.languages import entry as language_entry
from library.languages import live_codes

from . import copy as copy_mod
from .blocks import BlockType
from .models import AutoEmail, AutoEmailConfig, Broadcast, BroadcastStatus

#: The digest's sections, in the order they appear. Each can be switched off.
SECTIONS = ("letter", "continue", "new", "quote", "plan")

#: The digest goes out on the first Monday of the month at this hour (UTC).
DIGEST_WEEKDAY = 0
DIGEST_HOUR = 9
#: How long before the send the digest is built (and, by default, waits for an
#: admin to approve it).
DRAFT_LEAD = timedelta(days=3)
#: Most works one email lists; the rest are a click away in the library.
NEW_LIMIT = 6

#: "New in your language" waits this long after the first new work, gathering.
NEW_BATCH_WAIT = timedelta(days=3)
#: ...and goes out at most this often per language.
NEW_MIN_GAP = timedelta(days=7)
NEW_IN_LANGUAGE_LIMIT = 8

#: Languages that write a language's name in lower case mid-sentence
#: ("nouveau en français"), where the registry's native name is capitalised.
_LOWERCASE_LANGUAGE_NAMES = frozenset({"es", "fr", "pt"})


# --- When ------------------------------------------------------------------------


def issue_date(year: int, month: int) -> datetime:
    """The digest's send time for a month: its first Monday, at DIGEST_HOUR UTC."""
    first = datetime(year, month, 1, DIGEST_HOUR, tzinfo=UTC)
    return first + timedelta(days=(DIGEST_WEEKDAY - first.weekday()) % 7)


def _month_after(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _month_before(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def next_issue(now: datetime) -> datetime:
    """The next digest send time at or after ``now``."""
    this_month = issue_date(now.year, now.month)
    if now <= this_month:
        return this_month
    return issue_date(*_month_after(now.year, now.month))


def digest_key(send_at: datetime) -> str:
    return f"{AutoEmail.DIGEST}:{send_at:%Y-%m}"


# --- What --------------------------------------------------------------------


_WORK_MODELS = ((BlockType.BOOK, "Book"), (BlockType.SERMON, "Sermon"))


def _published_after(code: str, since: datetime, until: datetime, limit: int) -> list[tuple]:
    """``(created_at, kind, slug)`` for the books and sermons published in
    ``code`` after ``since`` and up to ``until``, oldest first, at most ``limit``.

    A row's ``created_at`` stands for its publication: the seeds create a work
    when it ships."""
    from django.apps import apps

    rows: list[tuple] = []
    for kind, model_name in _WORK_MODELS:
        model = apps.get_model("library", model_name)
        rows += [
            (created, kind, slug)
            for created, slug in model.objects.filter(
                language=code, is_published=True, created_at__gt=since, created_at__lte=until
            )
            .order_by("created_at", "slug")
            .values_list("created_at", "slug")[:limit]
        ]
    return sorted(rows)[:limit]


def _new_works(code: str, since: datetime, until: datetime, limit: int) -> list[dict]:
    """Library blocks for the works published in ``code`` after ``since``, books
    first, oldest first."""
    rows = _published_after(code, since, until, limit)
    order = {kind: i for i, (kind, _) in enumerate(_WORK_MODELS)}
    rows.sort(key=lambda r: (order[r[1]], r[0], r[2]))
    return [{"type": kind, "slug": slug, "label": ""} for _, kind, slug in rows]


def _quote(code: str, turn: int) -> dict | None:
    """A reviewed quote from a published ``code`` work, as a quote block — a
    different one each month (``turn``), stable within a month."""
    from django.db.models import Q

    from library.models import Quote

    quotes = list(
        Quote.objects.filter(reviewed=True)
        .filter(
            Q(chapter__book__language=code, chapter__book__is_published=True)
            | Q(sermon__language=code, sermon__is_published=True)
        )
        .order_by("slug")
        .values("text", "author__name", "chapter__book__title", "sermon__title")
    )
    if not quotes:
        return None
    q = quotes[turn % len(quotes)]
    source = q["chapter__book__title"] or q["sermon__title"] or ""
    attribution = f"{q['author__name']}, {source}" if source else q["author__name"]
    return {"type": BlockType.QUOTE, "text": q["text"], "attribution": attribution}


def _plan(code: str, turn: int) -> dict | None:
    """A published ``code`` reading plan, rotating month to month."""
    from library.models import Plan

    slugs = list(
        Plan.objects.filter(language=code, is_published=True)
        .order_by("sort_order", "slug")
        .values_list("slug", flat=True)
    )
    if not slugs:
        return None
    return {"type": BlockType.PLAN, "slug": slugs[turn % len(slugs)], "label": ""}


def _copy(step: str, code: str) -> dict | None:
    """``step``'s words in ``code`` — never another language's."""
    return copy_mod.LIFECYCLE[step].get(code)


def _opening(text: dict) -> list[dict]:
    return [
        {"type": BlockType.HEADING, "text": text["heading"]},
        {"type": BlockType.TEXT, "text": "\n\n".join([text["greeting"], *text["paragraphs"]])},
    ]


def _closing(text: dict) -> list[dict]:
    return [
        {"type": BlockType.BUTTON, "label": text["cta_label"], "path": text["cta_path"]},
        {"type": BlockType.TEXT, "text": f"{text['signoff']}\n{text['signature']}"},
    ]


def digest_content(
    code: str, *, since: datetime, until: datetime, sections: dict, turn: int
) -> dict | None:
    """One language's digest — ``{"subject", "content"}`` — or ``None`` when that
    language has no copy or nothing to say this month (no new work, quote or
    plan: a reader's own book in progress alone is not an email)."""
    text = _copy(AutoEmail.DIGEST, code)
    if text is None:
        return None

    def on(section: str) -> bool:
        return bool(sections.get(section, True))

    picks: list[dict] = []
    if on("new"):
        new = _new_works(code, since, until, NEW_LIMIT)
        if new:
            picks += [{"type": BlockType.HEADING, "text": text["new_heading"]}, *new]
    if on("quote") and (quote := _quote(code, turn)):
        picks += [{"type": BlockType.HEADING, "text": text["quote_heading"]}, quote]
    if on("plan") and (plan := _plan(code, turn)):
        picks += [{"type": BlockType.HEADING, "text": text["plan_heading"]}, plan]
    if not picks:
        return None

    blocks = _opening(text)
    if on("letter"):
        # A note an admin may write each month; empty renders nothing.
        blocks.append({"type": BlockType.TEXT, "text": ""})
    if on("continue"):
        # The heading lives in the block: a reader with nothing in progress
        # loses both, not just the card.
        blocks.append(
            {
                "type": BlockType.CONTINUE,
                "heading": text["continue_heading"],
                "label": text["continue_label"],
            }
        )
    blocks += [*picks, *_closing(text)]
    return {
        "subject": text["subject"],
        "content": {"preheader": text["preheader"], "blocks": blocks},
    }


def _language_name(code: str) -> str:
    name = language_entry(code).get("native_name") or code
    return name.lower() if code in _LOWERCASE_LANGUAGE_NAMES else name


def new_in_language_content(code: str, works: list[dict]) -> dict | None:
    """The "new in your language" email for ``code`` listing ``works``."""
    text = _copy(AutoEmail.NEW_IN_LANGUAGE, code)
    if text is None or not works:
        return None
    language = _language_name(code)
    text = {
        k: [p.replace("{language}", language) for p in v]
        if isinstance(v, list)
        else str(v).replace("{language}", language)
        for k, v in text.items()
    }
    return {
        "subject": text["subject"],
        "content": {
            "preheader": text["preheader"],
            "blocks": [*_opening(text), *works, *_closing(text)],
        },
    }


# --- Building ----------------------------------------------------------------


def _create(**fields) -> Broadcast | None:
    """Create a built campaign, or ``None`` if one with its ``auto_key`` exists
    (a concurrent run built it first)."""
    try:
        with transaction.atomic():
            return Broadcast.objects.create(**fields)
    except IntegrityError:
        return None


def _status_fields(config: AutoEmailConfig, send_at: datetime) -> dict:
    status = BroadcastStatus.DRAFT if config.require_approval else BroadcastStatus.SCHEDULED
    reason = "Built automatically — approve it to send." if config.require_approval else ""
    return {"status": status, "scheduled_at": send_at, "status_reason": reason}


def _digest_since(send_at: datetime) -> datetime:
    """Where this issue's "new this month" starts: when the last issue was built
    (its own window ended there), else the previous issue's build time."""
    last = (
        Broadcast.objects.filter(auto_key__startswith=f"{AutoEmail.DIGEST}:")
        .exclude(auto_key=digest_key(send_at))
        .order_by("-created_at")
        .values_list("created_at", flat=True)
        .first()
    )
    return last or issue_date(*_month_before(send_at.year, send_at.month)) - DRAFT_LEAD


def build_digest(now: datetime | None = None, *, force: bool = False) -> Broadcast | None:
    """Build the next digest if it is due and not built yet.

    ``force`` builds it now whatever the date or switch — the admin's "build a
    draft now", which always waits for approval."""
    now = now or timezone.now()
    config = AutoEmailConfig.get(AutoEmail.DIGEST)
    if not (config.enabled or force):
        return None
    send_at = next_issue(now)
    if not force and now < send_at - DRAFT_LEAD:
        return None
    key = digest_key(send_at)
    if Broadcast.objects.filter(auto_key=key).exists():
        return None

    since = _digest_since(send_at)
    turn = send_at.year * 12 + send_at.month
    subject, content = {}, {}
    for code in live_codes():
        built = digest_content(
            code, since=since, until=now, sections=config.sections or {}, turn=turn
        )
        if built:
            subject[code], content[code] = built["subject"], built["content"]
    if not content:
        return None
    status = _status_fields(config, send_at)
    if force:
        status = _status_fields(AutoEmailConfig(require_approval=True), send_at)
    return _create(
        name=f"Monthly digest · {send_at:%B %Y}",
        subject=subject,
        content=content,
        audience={},
        stream=AutoEmail.DIGEST,
        strict_locale=True,
        auto_key=key,
        **status,
    )


def _last_new_in_language(code: str) -> Broadcast | None:
    return (
        Broadcast.objects.filter(auto_key__startswith=f"{AutoEmail.NEW_IN_LANGUAGE}:{code}:")
        .order_by("-created_at")
        .first()
    )


def build_new_in_language(now: datetime | None = None) -> list[Broadcast]:
    """Build each language's "new in your language" email that is due."""
    now = now or timezone.now()
    config = AutoEmailConfig.get(AutoEmail.NEW_IN_LANGUAGE)
    if not config.enabled or config.enabled_at is None:
        return []
    built = []
    cursor = dict(config.cursor or {})
    for code in live_codes():
        if _copy(AutoEmail.NEW_IN_LANGUAGE, code) is None:
            continue
        last = _last_new_in_language(code)
        if last is not None and now - last.created_at < NEW_MIN_GAP:
            continue
        since = config.enabled_at
        if code in cursor:
            since = max(since, datetime.fromisoformat(cursor[code]))
        rows = _published_after(code, since, now, NEW_IN_LANGUAGE_LIMIT)
        if not rows or now - rows[0][0] < NEW_BATCH_WAIT:
            continue
        works = [{"type": kind, "slug": slug, "label": ""} for _, kind, slug in rows]
        email = new_in_language_content(code, works)
        if email is None:
            continue
        # The next email starts after the last work this one lists — a batch
        # too long for one email carries over to the next.
        cursor[code] = rows[-1][0].isoformat()
        broadcast = _create(
            name=f"New in {language_entry(code).get('name') or code} · {now:%d %b %Y}",
            subject={code: email["subject"]},
            content={code: email["content"]},
            audience={"email_language": code},
            stream=AutoEmail.NEW_IN_LANGUAGE,
            strict_locale=True,
            auto_key=f"{AutoEmail.NEW_IN_LANGUAGE}:{code}:{now:%Y-%m-%d}",
            **_status_fields(config, now),
        )
        if broadcast is not None:
            built.append(broadcast)
    if cursor != (config.cursor or {}):
        AutoEmailConfig.objects.filter(pk=config.pk).update(cursor=cursor)
    return built


def build_due(now: datetime | None = None) -> list[Broadcast]:
    """Everything due this cron run."""
    now = now or timezone.now()
    built = build_new_in_language(now)
    digest = build_digest(now)
    if digest is not None:
        built.append(digest)
    return built


def set_enabled(config: AutoEmailConfig, enabled: bool) -> None:
    """Switch a campaign on or off; switching on (re)starts its baseline."""
    if enabled and not config.enabled:
        config.enabled_at = timezone.now()
    config.enabled = enabled
