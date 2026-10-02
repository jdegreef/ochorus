"""The content audit: one full scan of the library, and its recorded history.

The scan lives here, once, so the admin audit page
(``admin_views.quality.AdminAuditView``) and the nightly ``manage.py audit_scan``
run the SAME heuristics — the page reads it through its per-revision cache, the
command records it. Chapter-quality thresholds stay in ``library.qa``.

Around the scan sit three small jobs:

* **record** — an :class:`~library.models.AuditScan` row per scan worth keeping
  (the nightly one, and an admin's Re-run): its scope and per-check totals.
* **schedule** — the nightly scan rides the existing 15-minute email cron
  (``send_email_cron`` calls ``audit_scan --if-due``), so "due" is a pure
  function of the clock and the table: once per UTC day, at or after
  ``AUDIT_SCAN_HOUR_UTC``. No new service, and a missed tick just runs later.
* **alert** — when a scheduled scan finds an INTEGRITY check higher than the
  previous scheduled scan did, the super admins get one email naming what rose.
  Quality checks are advisory heuristics and never alert.
"""

from __future__ import annotations

import logging
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from html import escape

from django.conf import settings
from django.db.models import Count, Max
from django.utils import timezone

from .languages import entry as language_entry
from .models import (
    Article,
    AuditDismissal,
    AuditScan,
    Book,
    Chapter,
    ContentRevision,
    PlanDay,
)
from .qa import (
    FRAG_MAX_AVG,
    FRAG_MIN_PARAS,
    FRAG_MIN_WORDS,
    GENERIC_TITLE,
    GIANT_MIN,
    LENGTH_EDGES,
    TERMINAL_PUNCT,
    TINY_MAX,
    length_bucket,
    loose_snippet,
    loose_text,
)

logger = logging.getLogger(__name__)

# --- Presentation helpers -------------------------------------------------------

# Per-list cap so the payload stays bounded on a large library; totals are still
# reported.
AUDIT_LIMIT = 100


def _capped(items: list) -> dict:
    return {"total": len(items), "items": items[:AUDIT_LIMIT]}


# The advisory quality checks, and the tail of each finding's identity (its
# `ref`). Chapter-shaped checks are keyed by chapter order; duplicate_titles by
# the offending title. This is the single source of truth for "what is
# dismissible" — the audit view filters by it and the dismiss endpoint validates
# against it, so the two cannot disagree about which findings can be accepted.
QUALITY_CHAPTER_CHECKS = (
    "generic_titles",
    "tiny_chapters",
    "giant_chapters",
    "fragmented",
    "missing_dropcap",
    "mid_sentence_splits",
    "loose_text",
)
DISMISSIBLE_CHECKS = frozenset(QUALITY_CHAPTER_CHECKS + ("duplicate_titles",))


def _ref_of(check: str, finding: dict) -> str:
    """The dismissal `ref` for one finding — its identity within (check, book,
    language). A stringified chapter order for chapter checks; the title for
    duplicate_titles."""
    return finding["title"] if check == "duplicate_titles" else str(finding["order"])


def _only(items: list, language: str) -> list:
    """The findings for one edition. Every finding carries its ``language``."""
    return [f for f in items if f["language"] == language]


def _open(check: str, items: list, dismissed: set) -> list:
    """``items`` without the findings a reviewer has accepted."""
    return [
        f for f in items
        if (check, f["book"], f["language"], _ref_of(check, f)) not in dismissed
    ]


def _present(check: str, items: list, dismissed: set) -> dict:
    """Cap a quality check's findings after removing accepted ones, and report
    how many were hidden so the check still reads as examined, not empty."""
    kept = _open(check, items, dismissed)
    return {
        "total": len(kept),
        "items": kept[:AUDIT_LIMIT],
        "dismissed": len(items) - len(kept),
    }


#: Structural defects — fixed, never dismissed, and the only checks that alert.
INTEGRITY_CHECKS = ("empty_books", "empty_chapters", "order_gaps", "broken_plan_days")


# --- The scan ------------------------------------------------------------------


def scan_library() -> dict:
    """One full pass over the library — the expensive part the page caches.

    Language names come from the registry (the runtime source), like the review
    queue, so an edition added without a frontend deploy still reads as itself
    rather than a bare code. ``scope`` is what the pass covered and how long it
    took, which the page shows beside the result and :func:`record_scan` keeps.
    """
    started = timezone.now()
    t0 = time.monotonic()
    revision = ContentRevision.current()
    raw, per_book = _scan_chapters()
    dup_raw = _duplicate_titles(per_book["titles"])
    # empty_chapters is a structural defect (integrity), not an advisory
    # heuristic — capped like the rest of integrity, never dismissible.
    integrity_raw = {
        "empty_books": _empty_books(),
        "empty_chapters": raw.pop("empty_chapters"),
        "order_gaps": _order_gaps(per_book["orders"]),
        "broken_plan_days": _broken_plan_days(),
    }
    editions = Book.objects.count()
    # Computed on the FULL result so the picker is stable under a filter.
    # A clean edition still has a length chart, so it must stay pickable.
    languages = sorted(set(_languages(raw, dup_raw, integrity_raw)) | set(per_book["lengths"]))
    return {
        "started_at": started.isoformat(),
        "scanned_at": timezone.now().isoformat(),
        "content_revision": revision,
        "scope": {
            "editions": editions,
            "chapters": per_book["chapters"],
            "duration_ms": round((time.monotonic() - t0) * 1000),
        },
        "raw": raw,
        "dup_raw": dup_raw,
        "integrity_raw": integrity_raw,
        "languages": languages,
        "language_names": {code: language_entry(code)["name"] for code in languages},
        "lengths": per_book["lengths"],
    }


def chapter_lengths(by_language: dict[str, list[int]], language: str) -> dict:
    """The chapter-length histogram for one edition ('' = all), with the edges
    and thresholds it is drawn against — all from qa.py, so the chart cannot
    draw a threshold the checks don't use. Accepted findings still count: this
    is the shape of the library, not a list of open flags."""
    zeros = [0] * (len(LENGTH_EDGES) + 1)
    rows = [by_language.get(language, zeros)] if language else list(by_language.values())
    return {
        "edges": list(LENGTH_EDGES),
        "counts": [sum(col) for col in zip(zeros, *rows, strict=True)],
        "tiny_max": TINY_MAX,
        "giant_min": GIANT_MIN,
    }


def dismissed_fingerprints() -> set:
    """Every accepted finding, as (check, book, language, ref) fingerprints."""
    return set(AuditDismissal.objects.values_list("check_key", "book", "language", "ref"))


def present(scan: dict, dismissed: set, language: str = "") -> tuple[dict, dict]:
    """The page's ``(quality, integrity)`` sections for one scan: filtered to
    ``language`` (if any) BEFORE capping, so a capped check (e.g. 344
    mid-sentence splits across editions) reports its true per-language count,
    not whatever survived the first 100 rows; accepted quality findings removed.
    Builds new lists — the cached scan is never mutated."""
    raw, dup_raw, integrity_raw = scan["raw"], scan["dup_raw"], scan["integrity_raw"]
    if language:
        raw = {k: _only(v, language) for k, v in raw.items()}
        dup_raw = _only(dup_raw, language)
        integrity_raw = {k: _only(v, language) for k, v in integrity_raw.items()}
    quality = {check: _present(check, raw[check], dismissed) for check in QUALITY_CHAPTER_CHECKS}
    quality["duplicate_titles"] = _present("duplicate_titles", dup_raw, dismissed)
    integrity = {k: _capped(v) for k, v in integrity_raw.items()}
    return quality, integrity


#: How many editions the "worst books first" ranking lists.
WORST_BOOKS_LIMIT = 25


def worst_books(scan: dict, dismissed: set, language: str = "", limit: int = WORST_BOOKS_LIMIT) -> dict:
    """Editions ranked by open quality flags, most first, with each one's count
    per check — the page's "worst books first" table.

    Fixes happen per edition (a re-import repairs a whole book), so this is the
    list of re-imports that clear the most flags. Counted here from the UNCAPPED
    raw lists: the per-check item lists the page receives stop at AUDIT_LIMIT, so
    grouping them in the browser would undercount exactly the editions that
    matter. Accepted findings are excluded, like everywhere else; the language
    filter applies first. Integrity defects are not counted — they are listed
    (and fixed) on their own. ``total`` is how many editions have any open flag.
    """
    checks = [(c, scan["raw"][c]) for c in QUALITY_CHAPTER_CHECKS]
    checks.append(("duplicate_titles", scan["dup_raw"]))
    by_edition: defaultdict[tuple[str, str], Counter] = defaultdict(Counter)
    for check, items in checks:
        if language:
            items = _only(items, language)
        for f in _open(check, items, dismissed):
            by_edition[(f["book"], f["language"])][check] += 1
    ranked = sorted(by_edition.items(), key=lambda kv: (-kv[1].total(), kv[0]))[:limit]
    keys = {key for key, _ in ranked}
    # Titles are looked up per request, not cached with the scan: 25 rows, one query.
    titles = {
        (slug, lang): title
        for slug, lang, title in Book.objects.filter(
            slug__in={slug for slug, _ in keys}
        ).values_list("slug", "language", "title")
        if (slug, lang) in keys
    }
    items = [
        {
            "book": slug,
            "language": lang,
            "title": titles.get((slug, lang), ""),
            "total": counts.total(),
            "by_check": dict(counts.most_common()),
        }
        for (slug, lang), counts in ranked
    ]
    return {"total": len(by_edition), "items": items}


# --- Recording ------------------------------------------------------------------

#: How long scan rows are kept. A row a night is ~180 rows: enough for a
#: half-year trend per check, small enough never to matter.
RETENTION_DAYS = 180


def record_scan(scan: dict, trigger: str) -> AuditScan:
    """Store ``scan``'s scope and per-check totals (every check, so a trend can
    be drawn for any of them). Quality totals are net of accepted findings —
    what the page shows — with the accepted counts kept beside them."""
    quality, integrity = present(scan, dismissed_fingerprints())
    return AuditScan.objects.create(
        started_at=datetime.fromisoformat(scan["started_at"]),
        duration_ms=scan["scope"]["duration_ms"],
        trigger=trigger,
        editions_scanned=scan["scope"]["editions"],
        chapters_scanned=scan["scope"]["chapters"],
        content_revision=scan["content_revision"],
        integrity={k: v["total"] for k, v in integrity.items()},
        quality={k: v["total"] for k, v in quality.items()},
        quality_accepted={k: v["dismissed"] for k, v in quality.items()},
    )


def prune(now: datetime | None = None) -> int:
    """Delete scan rows older than :data:`RETENTION_DAYS`; return how many."""
    cutoff = (now or timezone.now()) - timedelta(days=RETENTION_DAYS)
    deleted, _ = AuditScan.objects.filter(started_at__lt=cutoff).delete()
    return deleted


# --- Schedule -------------------------------------------------------------------


def next_scheduled_at(now: datetime | None = None) -> datetime:
    """When the next scheduled scan is expected: today's (UTC) mark if no
    scheduled scan has run since it — possibly already past, i.e. due now —
    else tomorrow's."""
    now = now or timezone.now()
    mark = now.astimezone(UTC).replace(
        hour=settings.AUDIT_SCAN_HOUR_UTC, minute=0, second=0, microsecond=0
    )
    if now < mark:
        return mark
    ran = AuditScan.objects.filter(
        trigger=AuditScan.Trigger.SCHEDULE, started_at__gte=mark
    ).exists()
    return mark + timedelta(days=1) if ran else mark


def scheduled_scan_due(now: datetime | None = None) -> bool:
    """Whether the nightly scan should run now. The cron ticks every 15 minutes,
    so this is asked ~96 times a day and true for (at most) one of them."""
    now = now or timezone.now()
    return next_scheduled_at(now) <= now


#: Past its mark by more than this, the nightly scan reads as overdue — a few
#: missed 15-minute ticks, which in practice means the cron isn't running.
OVERDUE_AFTER = timedelta(minutes=45)


def schedule_status(now: datetime | None = None) -> dict:
    """The page's view of the nightly scan: when it last ran, what its alert
    did, when the next is expected, and whether it is overdue."""
    now = now or timezone.now()
    last = AuditScan.objects.filter(trigger=AuditScan.Trigger.SCHEDULE).first()
    nxt = next_scheduled_at(now)
    return {
        "hour_utc": settings.AUDIT_SCAN_HOUR_UTC,
        "last_at": last.started_at.isoformat() if last else None,
        "last_alert": last.alert if last else None,
        "next_at": nxt.isoformat(),
        "overdue": now - nxt > OVERDUE_AFTER,
    }


# --- Alert ----------------------------------------------------------------------

#: How many example findings the alert email lists, across all checks.
ALERT_EXAMPLES = 10

CHECK_LABELS = {
    "empty_books": "Books with no chapters",
    "empty_chapters": "Empty chapters",
    "order_gaps": "Chapter-order gaps",
    "broken_plan_days": "Broken reading-plan days",
}


def alert_baseline(row: AuditScan) -> AuditScan | None:
    """The scan ``row`` is compared with: the latest EARLIER scheduled scan whose
    alert didn't fail.

    Scheduled only — a manual Re-run never alerts, so if it could be a baseline,
    an admin who happened to re-run after a defect landed would silently absorb
    the nightly alert. And a scan whose alert FAILED is passed over, so a Resend
    outage delays the email by a night instead of losing it.
    """
    return (
        AuditScan.objects.filter(trigger=AuditScan.Trigger.SCHEDULE, started_at__lt=row.started_at)
        .exclude(alert=AuditScan.Alert.FAILED)
        .order_by("-started_at")
        .first()
    )


def worsened(current: dict, baseline: dict) -> dict[str, tuple[int, int]]:
    """``{check: (before, after)}`` for each integrity check that rose."""
    out = {}
    for check in INTEGRITY_CHECKS:
        before, after = int(baseline.get(check, 0)), int(current.get(check, 0))
        if after > before:
            out[check] = (before, after)
    return out


def _describe(check: str, item: dict) -> str:
    lang = item.get("language", "")
    if check == "broken_plan_days":
        target = item.get("article") or f"{item.get('book')} ch. {item.get('order')}"
        return f"{item['plan']} [{lang}] day {item['day']} → {target}"
    if check == "order_gaps":
        missing = ", ".join(str(n) for n in item["missing"][:8])
        return f"{item['book']} [{lang}] missing ch. {missing}"
    if check == "empty_chapters":
        return f"{item['book']} [{lang}] ch. {item['order']} {item.get('title') or ''}".rstrip()
    return f"{item['book']} [{lang}] {item.get('title') or ''}".rstrip()


def render_alert(scan: dict, rises: dict[str, tuple[int, int]]) -> tuple[str, str]:
    """``(subject, html)`` for the alert email. Admin mail is English-only."""
    n = len(rises)
    subject = f"Ochorus content audit: {n} integrity check{'s' if n != 1 else ''} worsened"
    rows = "".join(
        f"<li><strong>{escape(CHECK_LABELS.get(c, c))}</strong>: {before} → {after}</li>"
        for c, (before, after) in rises.items()
    )
    examples = [
        _describe(check, item) for check in rises for item in scan["integrity_raw"][check]
    ][:ALERT_EXAMPLES]
    example_html = "".join(f"<li>{escape(e)}</li>" for e in examples)
    url = f"{settings.PUBLIC_SITE_URL}/admin/audit"
    scope = scan["scope"]
    html = (
        "<p>The scheduled content audit found data-integrity problems that the "
        "previous scheduled scan did not.</p>"
        f"<ul>{rows}</ul>"
        + (f"<p>Examples:</p><ul>{example_html}</ul>" if example_html else "")
        + f'<p><a href="{escape(url)}">Open the content audit</a></p>'
        f'<p style="color:#666;font-size:12px">Scanned {scope["editions"]:,} editions and '
        f"{scope['chapters']:,} chapters in {scope['duration_ms'] / 1000:.1f} s. "
        "You get this because you are an Ochorus super admin (ADMIN_EMAILS).</p>"
    )
    return subject, html


def send_alert(row: AuditScan, scan: dict, rises: dict) -> tuple[str, str]:
    """Mail the super admins through the email programme's Resend layer, under
    its master switch and review-mode allowlist. Returns ``(alert, note)``.

    Not ``emails.sending.deliver``: that is the READER choke point — it needs a
    profile and a subscription, and adds unsubscribe headers — and an admin's
    operational alert has neither. The Resend idempotency key is per (scan,
    address), so a retried HTTP call can't double a send.
    """
    # Lazy: the emails app imports library at module level.
    from emails.resend_client import ResendError, send_email
    from emails.sending import address_allowed, emails_enabled

    if not emails_enabled():
        return AuditScan.Alert.SKIPPED, "email sending disabled"
    recipients = [a for a in sorted(settings.ADMIN_EMAILS) if address_allowed(a)]
    if not recipients:
        return AuditScan.Alert.SKIPPED, "no ADMIN_EMAILS address passes EMAIL_ALLOWLIST"
    subject, html = render_alert(scan, rises)
    sent, errors = 0, []
    for to in recipients:
        try:
            send_email(
                to=to, subject=subject, html=html, idempotency_key=f"audit-alert:{row.pk}:{to}"
            )
            sent += 1
        except ResendError as exc:
            logger.warning("audit alert to %s failed: %s", to, exc)
            errors.append(str(exc))
    if not sent:
        return AuditScan.Alert.FAILED, "; ".join(errors)
    return AuditScan.Alert.SENT, f"sent to {sent} of {len(recipients)}"


def evaluate_alert(row: AuditScan, scan: dict) -> AuditScan:
    """Compare ``row`` with its baseline and alert if an integrity check rose;
    the outcome is written onto ``row``. The first scheduled scan has nothing to
    compare with, so it only becomes the baseline."""
    baseline = alert_baseline(row)
    rises = worsened(row.integrity, baseline.integrity) if baseline else {}
    if rises:
        named = ", ".join(f"{c} {b}→{a}" for c, (b, a) in rises.items())
        row.alert, note = send_alert(row, scan, rises)
        row.alert_note = f"{named} — {note}"[:300]
    else:
        row.alert = AuditScan.Alert.NONE
        row.alert_note = "" if baseline else "first scheduled scan (baseline)"
    row.save(update_fields=["alert", "alert_note"])
    return row


def run_scheduled_scan(*, if_due: bool = False, now: datetime | None = None) -> AuditScan | None:
    """The nightly job: scan, record, alert, prune. With ``if_due`` it does
    nothing unless :func:`scheduled_scan_due` — the form the cron calls every
    15 minutes, which makes repeated runs harmless."""
    if if_due and not scheduled_scan_due(now):
        return None
    scan = scan_library()
    row = record_scan(scan, AuditScan.Trigger.SCHEDULE)
    evaluate_alert(row, scan)
    prune(now)
    return row


# --- Scan internals --------------------------------------------------------------


def _languages(raw: dict, dup_raw: list, integrity_raw: dict) -> list[str]:
    lists = (*raw.values(), *integrity_raw.values(), dup_raw)
    return sorted({f["language"] for lst in lists for f in lst})


def _scan_chapters():
    maxima = {
        r["book_id"]: r["mx"]
        for r in Chapter.objects.values("book_id").annotate(mx=Max("order"))
    }
    generic, tiny, giant, fragmented, dropcap, mid_split, loose, empty = (
        [], [], [], [], [], [], [], []
    )
    # Keyed by (slug, language), NOT slug. A work is a per-language ROW —
    # eight editions of the-inner-chamber share one slug — so grouping by
    # slug alone pools chapters that belong to different books. That made
    # `_duplicate_titles` report 17 cross-language collisions as duplicates
    # "in a book" (a chapter 19 titled "Hazelglen Fellowship" in en, lg, pt
    # and sw is one untranslated proper noun, not four duplicates), and it
    # would hide a real gap in one edition behind another edition's chapters
    # in `_order_gaps`.
    titles: dict[tuple[str, str], list[str]] = {}
    orders: dict[tuple[str, str], list[int]] = {}
    chapters = 0
    # Per-language chapter-length histogram (see qa.length_bucket). Empty
    # chapters are left out: they are an integrity defect, not a length.
    lengths: defaultdict[str, list[int]] = defaultdict(lambda: [0] * (len(LENGTH_EDGES) + 1))

    rows = Chapter.objects.select_related("book").values(
        "book_id", "book__slug", "book__language", "order", "title",
        "word_count", "body_html", "body_text",
    )
    for c in rows.iterator(chunk_size=50):
        chapters += 1
        slug = c["book__slug"]
        lang = c["book__language"]
        order = c["order"]
        title = (c["title"] or "").strip()
        wc = c["word_count"] or 0
        body = (c["body_text"] or "").strip()

        titles.setdefault((slug, lang), []).append(title)
        orders.setdefault((slug, lang), []).append(order)

        def finding(slug=slug, lang=lang, order=order, title=title, **extra):
            return {"book": slug, "language": lang, "order": order, "title": title, **extra}

        if not title or GENERIC_TITLE.match(title):
            generic.append(finding())
        if not body or wc == 0:
            empty.append(finding())
            continue  # remaining checks need body text
        lengths[lang][length_bucket(wc)] += 1
        if 0 < wc < TINY_MAX:
            tiny.append(finding(word_count=wc))
        if wc > GIANT_MIN:
            giant.append(finding(word_count=wc))

        paras = c["body_html"].count("<p")
        if paras >= FRAG_MIN_PARAS and wc >= FRAG_MIN_WORDS and wc / paras < FRAG_MAX_AVG:
            fragmented.append(finding(avg_words=round(wc / paras, 1), paragraphs=paras))

        first_alpha = next((ch for ch in body if ch.isalpha()), "")
        if first_alpha and first_alpha.islower():
            dropcap.append(finding(starts=body[:40]))

        if order < maxima.get(c["book_id"], order) and not body.endswith(TERMINAL_PUNCT):
            mid_split.append(finding(ends=body[-40:]))

        runs = loose_text(c["body_html"])
        if runs:
            loose.append(finding(loose_runs=len(runs), loose=loose_snippet(runs)))

    # Raw (uncapped) lists — the caller filters out accepted findings before
    # capping, so capping here would drop rows the reviewer has NOT accepted
    # whenever a check ran past 100.
    raw = {
        "generic_titles": generic,
        "tiny_chapters": tiny,
        "giant_chapters": giant,
        "fragmented": fragmented,
        "missing_dropcap": dropcap,
        "mid_sentence_splits": mid_split,
        "loose_text": loose,
        # Not a quality check — lifted into integrity by scan_library(). Kept here
        # because it falls out of the same single chapter scan.
        "empty_chapters": empty,
    }
    # A plain dict for the cache (a defaultdict's lambda doesn't pickle).
    return raw, {
        "titles": titles, "orders": orders, "chapters": chapters, "lengths": dict(lengths)
    }

def _duplicate_titles(titles_by_book: dict) -> list[dict]:
    out = []
    for (slug, language), titles in titles_by_book.items():
        seen: dict[str, int] = {}
        for t in titles:
            if t:
                seen[t] = seen.get(t, 0) + 1
        for title, n in seen.items():
            if n > 1:
                out.append(
                    {"book": slug, "language": language, "title": title, "count": n}
                )
    out.sort(key=lambda r: (-r["count"], r["book"], r["language"]))
    return out

def _empty_books() -> list[dict]:
    books = (
        Book.objects.annotate(n=Count("chapters"))
        .filter(n=0)
        .select_related("author")
        .order_by("language", "slug")
    )
    return [
        {"book": b.slug, "language": b.language, "title": b.title, "author": b.author.name}
        for b in books
    ]

def _order_gaps(orders_by_book: dict) -> list[dict]:
    out = []
    for (slug, language), orders in orders_by_book.items():
        present = set(orders)
        expected = set(range(1, max(orders) + 1))
        missing = sorted(expected - present)
        if missing:
            out.append(
                {
                    "book": slug,
                    "language": language,
                    "missing": missing,
                    "count": len(orders),
                }
            )
    out.sort(key=lambda r: (r["book"], r["language"]))
    return out

def _broken_plan_days() -> list[dict]:
    valid = set(
        Chapter.objects.values_list("book__slug", "book__language", "order")
    )
    articles = set(
        Article.objects.filter(is_published=True).values_list("slug", "language")
    )
    out = []
    days = PlanDay.objects.select_related("plan").values(
        "plan__slug",
        "plan__language",
        "day",
        "book_slug",
        "chapter_order",
        "article_slug",
    )
    for d in days:
        if d["article_slug"]:
            ok = (d["article_slug"], d["plan__language"]) in articles
        else:
            key = (d["book_slug"], d["plan__language"], d["chapter_order"])
            ok = key in valid
        if not ok:
            out.append(
                {
                    "plan": d["plan__slug"],
                    "language": d["plan__language"],
                    "day": d["day"],
                    "book": d["book_slug"],
                    "order": d["chapter_order"],
                    "article": d["article_slug"],
                }
            )
    out.sort(key=lambda r: (r["plan"], r["day"]))
    return out
