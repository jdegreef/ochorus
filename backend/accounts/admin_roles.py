"""Named admin roles — bundles of :class:`~accounts.models.AdminGrant` rows.

A role is a *label over a set of grants*, not a table: applying a preset (via the
``admin_grants`` command) creates one grant per (capability, verb) below, stamped
with the role's name so the team console and ``/api/auth/me`` can say "Reviewer"
rather than list nine rows. The
grants are the truth; splitting a preset later is a data change, not a migration.

The super admin is deliberately NOT a preset here — it stays the ``ADMIN_EMAILS``
allowlist bootstrap, outside the grant table (see ``accounts.permissions``).
"""

from __future__ import annotations

from django.db import transaction

from .models import ALL_LANGUAGES, AdminGrant
from .models import AdminCapability as C
from .models import AdminVerb as V

#: role name → the (capability, verb) grants it bundles. Language scope is chosen
#: per assignment (``grant_admin --languages es,pt``), not baked into the preset.
PRESETS: dict[str, list[tuple[str, str]]] = {
    # View the library and its queues; propose work (files jobs — applies nothing
    # live). No PII, no publishing, no review decisions.
    "contributor": [
        (C.REPORTING, V.VIEW),
        (C.AUDIT, V.VIEW),
        (C.REVIEW, V.VIEW),
        (C.TRANSLATE, V.SUGGEST),
        (C.CONTENT_EDIT, V.SUGGEST),
    ],
    # A contributor who also records review decisions on their language(s). Those
    # decisions are provisional — a super admin confirms the reader-visible flip
    # (the PR2 mechanic); the grant here is what lets them do the review work.
    "reviewer": [
        (C.REPORTING, V.VIEW),
        (C.AUDIT, V.VIEW),
        (C.REVIEW, V.ACT),
        (C.TRANSLATE, V.SUGGEST),
        (C.CONTENT_EDIT, V.SUGGEST),
    ],
    # Runs their language end to end — publish, confirm reviews, act on the
    # queues and authors, triage the reader feedback for their languages, and
    # VIEW their language's readiness cockpit (/admin/languages/<code>).
    # Deliberately WITHOUT user/PII analytics, and the language-admin grant is
    # VIEW only: create/settings/thresholds (:act) and go-live (:approve) stay
    # super admin — the destructive, global levers a read grant can't reach on
    # the verb ladder. The feedback queue is language-scoped per row, so this
    # grant shows a language admin only their languages' suggestions.
    "language_admin": [
        (C.REPORTING, V.VIEW),
        (C.AUDIT, V.ACT),
        (C.REVIEW, V.APPROVE),
        (C.PUBLISH, V.ACT),
        (C.TRANSLATE, V.ACT),
        (C.CONTENT_EDIT, V.ACT),
        (C.AUTHORS, V.ACT),
        (C.FEEDBACK, V.ACT),
        (C.LANGUAGE_ADMIN, V.VIEW),
    ],
}

ROLE_NAMES = tuple(PRESETS)


def apply_grant(email, *, role=None, capability=None, verb=None, languages=ALL_LANGUAGES, granted_by=""):
    """Create/replace the grant rows for ``email`` — from a preset ``role`` OR a
    single ``(capability, verb)``. The single home for "assign access", shared by
    the ``admin_grants`` command and the ``/admin/team`` endpoint. Returns the
    role label ('' for a raw capability grant). Raises ``ValueError`` on bad
    input; the caller is responsible for the super-admin guard.
    """
    email = (email or "").strip().lower()
    if not email:
        raise ValueError("email is required")
    if role:
        if role not in PRESETS:
            raise ValueError(f"unknown role {role!r}")
        pairs, label = PRESETS[role], role
    elif capability and verb:
        # Validate against the enums (the CLI does this via argparse choices; an
        # unvalidated capability/verb would persist a dead grant that matches
        # nothing — an integrity gap, so reject it here for both callers).
        if capability not in C.values:
            raise ValueError(f"unknown capability {capability!r}")
        if verb not in V.values:
            raise ValueError(f"unknown verb {verb!r}")
        pairs, label = [(capability, verb)], ""
    else:
        raise ValueError("a role, or both capability and verb, is required")
    granted_by = (granted_by or "").strip().lower()
    with transaction.atomic():
        if role:
            # A role REPLACES the person's previous role: drop the rows another
            # preset left behind (language_admin → reviewer must lose publish).
            # Single-capability grants (no role label) survive — unless the new
            # role covers the same capability, which it then overwrites.
            AdminGrant.objects.filter(email=email).exclude(role_label="").exclude(
                capability__in=[cap for cap, _ in pairs]
            ).delete()
        for cap, vb in pairs:
            AdminGrant.objects.update_or_create(
                email=email,
                capability=cap,
                defaults={"verb": vb, "languages": languages, "role_label": label, "granted_by": granted_by},
            )
    return label


def revoke_grant(email, *, capability=None) -> int:
    """Remove grant rows for ``email`` (all, or just one ``capability``). Returns
    the number removed."""
    qs = AdminGrant.objects.filter(email=(email or "").strip().lower())
    if capability:
        qs = qs.filter(capability=capability)
    return qs.delete()[0]


def restore_grants(email, scopes, *, granted_by="") -> None:
    """Put back exactly the rows ``scopes`` describes (``scopes_for`` dicts) —
    the team console's Undo after a revoke. Re-applying the roles instead would
    re-scope mixed-language rows, add whatever a preset gained since, and let a
    second role's grant delete the first's rows: an "undo" must not change
    access. Replaces whatever ``email`` holds now, all or nothing."""
    email = (email or "").strip().lower()
    if not email:
        raise ValueError("email is required")
    if not isinstance(scopes, list) or not scopes:
        raise ValueError("restore needs the list of scopes to put back")
    rows = []
    for s in scopes:
        cap, verb, role = s.get("capability"), s.get("verb"), s.get("role") or ""
        if cap not in C.values or verb not in V.values:
            raise ValueError(f"unknown capability/verb {cap!r}:{verb!r}")
        if role and role not in PRESETS:
            raise ValueError(f"unknown role {role!r}")
        codes = sorted({str(c).strip().lower() for c in s.get("languages") or [] if str(c).strip()})
        if not codes:
            raise ValueError(f"{cap} has no languages")
        langs = ALL_LANGUAGES if ALL_LANGUAGES in codes else ",".join(codes)
        rows.append(
            AdminGrant(
                email=email, capability=cap, verb=verb, languages=langs, role_label=role,
                granted_by=(granted_by or "").strip().lower(),
            )
        )
    if len({r.capability for r in rows}) != len(rows):
        raise ValueError("a capability appears twice")
    with transaction.atomic():
        AdminGrant.objects.filter(email=email).delete()
        AdminGrant.objects.bulk_create(rows)


def role_drift(scopes) -> list[dict]:
    """Where a member's role rows have fallen behind the role's CURRENT preset.

    A role is a label over rows written when it was granted, so widening a
    preset later (language_admin gained ``feedback`` and ``language_admin``)
    leaves earlier grantees without the new rows while the console still calls
    them by the role's name. ``scopes`` is ``AdminGrant.scopes_for(email)``.
    Returns one entry per out-of-date role: the capabilities it lacks or holds
    at the wrong verb, and the languages to re-apply it with — ``None`` when
    the role's rows disagree on languages, so no single re-grant is the
    faithful fix.
    """
    by_cap = {s["capability"]: s for s in scopes}  # one row per capability
    drift = []
    for role in sorted({s["role"] for s in scopes if s["role"] in PRESETS}):
        # A capability is behind only if nobody holds it, or this role's own
        # row sits at another verb. A row a single grant (or another role)
        # wrote is a deliberate choice, and "Update" must not overwrite it.
        missing = sorted(
            cap
            for cap, verb in PRESETS[role]
            if cap not in by_cap or (by_cap[cap]["role"] == role and by_cap[cap]["verb"] != verb)
        )
        held = {c: s for c, s in by_cap.items() if s["role"] == role}
        if not missing:
            continue
        langs = {tuple(s["languages"]) for s in held.values()}
        drift.append(
            {"role": role, "missing": missing, "languages": list(langs.pop()) if len(langs) == 1 else None}
        )
    return drift
