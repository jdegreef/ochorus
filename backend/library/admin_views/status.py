"""Admin dashboard API — System status: is everything that runs on its own running?

The email cron, the nightly content audit and the deploy's release chain run
outside any request, so a stopped cron or a step failing every tick was
invisible until a reader noticed. This view reads their heartbeats
(:class:`~library.models.JobHeartbeat`) and the few settings that decide
whether email goes out at all, and says, per job, whether it is ok, late,
failing, paused or has never reported.

Read-only and secret-free: it reports whether a key is SET, never its value.
"""

from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import AdminCapability, AdminVerb
from accounts.permissions import requires

from ..models import AuditScan, ContentRevision, JobHeartbeat, LanguageHealthSnapshot

CRON = "email_cron"
DEPLOY = "deploy"

#: (heartbeat name, label, group, late after). Order is the page's order. The
#: email steps run every 15 minutes, so an hour without a good run is late.
JOBS: list[tuple[str, str, str, timedelta | None]] = [
    (
        "send_lifecycle_emails",
        "Welcome and onboarding emails",
        CRON,
        timedelta(hours=1),
    ),
    ("send_plan_reminders", "Reading-plan reminders", CRON, timedelta(hours=1)),
    ("send_series_nudges", "Keep-reading nudges", CRON, timedelta(hours=1)),
    ("send_milestone_cards", "Milestone cards", CRON, timedelta(hours=1)),
    ("run_automations", "Automations", CRON, timedelta(hours=1)),
    (
        "build_auto_emails",
        "Digest and new-in-your-language builds",
        CRON,
        timedelta(hours=1),
    ),
    ("send_due_broadcasts", "Scheduled broadcasts", CRON, timedelta(hours=1)),
    ("audit_scan", "Nightly content audit check", CRON, timedelta(hours=1)),
    # A deploy runs when the train does, so it is never "late" — just shown.
    ("release", "Deploy release chain", DEPLOY, None),
]


def sending_state() -> dict:
    """The switches that decide whether email leaves the building."""
    from emails.sending import emails_enabled

    return {
        "enabled": emails_enabled(),
        "switch_on": bool(settings.EMAIL_ENABLED),
        "provider_key_set": bool(settings.RESEND_API_KEY),
        "base_urls_set": bool(settings.API_PUBLIC_URL and settings.PUBLIC_SITE_URL),
        # Review mode: only these addresses get mail. The count, not the list.
        "allowlist_size": len(settings.EMAIL_ALLOWLIST or []),
    }


def job_state(beat: JobHeartbeat | None, late_after, now, *, paused: bool) -> str:
    """``ok``, ``late``, ``failing``, ``paused`` or ``never``."""
    if beat is None or beat.last_started_at is None:
        return "paused" if paused else "never"
    if beat.last_error:
        return "failing"
    if late_after is not None and (
        beat.last_ok_at is None or now - beat.last_ok_at > late_after
    ):
        return "paused" if paused else "late"
    return "ok"


@requires(AdminCapability.REPORTING, verb=AdminVerb.VIEW)
class AdminStatusView(APIView):
    def get(self, request):
        now = timezone.now()
        sending = sending_state()
        beats = {b.name: b for b in JobHeartbeat.objects.all()}
        jobs = []
        for name, label, group, late_after in JOBS:
            beat = beats.get(name)
            # With sending off the email cron is suspended on Render on purpose
            # (render.yaml), so a silent cron then is expected, not an alarm.
            paused = group == CRON and not sending["enabled"]
            jobs.append(
                {
                    "name": name,
                    "label": label,
                    "group": group,
                    "state": job_state(beat, late_after, now, paused=paused),
                    "late_after_minutes": int(late_after.total_seconds() // 60)
                    if late_after
                    else None,
                    "last_started_at": beat.last_started_at if beat else None,
                    "last_ok_at": beat.last_ok_at if beat else None,
                    "last_error": beat.last_error if beat else "",
                    "runs": beat.runs if beat else 0,
                }
            )
        revision = ContentRevision.objects.filter(pk=1).first()
        scan = (
            AuditScan.objects.order_by("-started_at")
            .values_list("started_at", flat=True)
            .first()
        )
        snapshot = (
            LanguageHealthSnapshot.objects.order_by("-date")
            .values_list("date", flat=True)
            .first()
        )
        return Response(
            {
                "now": now,
                "sending": sending,
                "jobs": jobs,
                "content": {
                    # Changes made through the admin since the last rebuild
                    # hook fired — what the reader is still waiting to see.
                    "unbuilt_changes": max(
                        0,
                        (revision.revision - revision.deploy_fired_revision)
                        if revision
                        else 0,
                    ),
                    "deploy_fired_at": revision.deploy_fired_at if revision else None,
                    "last_audit_scan_at": scan,
                    "last_health_snapshot": snapshot,
                },
                "worst": _worst(jobs),
            }
        )


def _worst(jobs: list[dict]) -> str:
    """The one word for the dashboard: the worst state any job is in."""
    for state in ("failing", "late", "never"):
        if any(j["state"] == state for j in jobs):
            return state
    return "ok"
