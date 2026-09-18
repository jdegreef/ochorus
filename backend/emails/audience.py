"""Resolve a broadcast's audience filter to the readers it targets.

The filter is a small JSON object on ``Broadcast.audience``; an empty object
means everyone. Consent (newsletter opt-in) and suppression are NOT applied here
— they're enforced per recipient at send time (``emails.broadcasts``), so the
audience count reflects "who this targets" and the send reflects "who agreed".

Supported keys:

* ``locale``          — a code or list of codes (reader's reading language)
* ``signup_variant``  — the home sign-up prompt they arrived through
* ``activity``        — ``active_7d`` / ``active_30d`` / ``lapsed_30d`` / ``never_seen``
* ``has_plan``        — bool: has (or hasn't) started a reading plan
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from accounts.models import UserProfile
from reading.models import PlanProgress

_ACTIVITY_WINDOWS = {"active_7d": 7, "active_30d": 30}


def resolve(audience: dict):
    """The ``UserProfile`` queryset a broadcast targets."""
    qs = UserProfile.objects.all()

    locale = audience.get("locale")
    if locale:
        locales = [locale] if isinstance(locale, str) else list(locale)
        qs = qs.filter(locale__in=locales)

    variant = audience.get("signup_variant")
    if variant:
        qs = qs.filter(signup_variant=variant)

    qs = _apply_activity(qs, audience.get("activity"))

    has_plan = audience.get("has_plan")
    if has_plan is not None:
        planned = PlanProgress.objects.values_list("profile_id", flat=True)
        qs = qs.filter(pk__in=planned) if has_plan else qs.exclude(pk__in=planned)

    return qs.order_by("created_at")


def _apply_activity(qs, activity):
    if not activity:
        return qs
    now = timezone.now()
    if activity in _ACTIVITY_WINDOWS:
        return qs.filter(last_seen_at__gte=now - timedelta(days=_ACTIVITY_WINDOWS[activity]))
    if activity == "lapsed_30d":
        return qs.filter(last_seen_at__lt=now - timedelta(days=30))
    if activity == "never_seen":
        return qs.filter(last_seen_at__isnull=True)
    return qs


def count(audience: dict) -> int:
    return resolve(audience).count()
