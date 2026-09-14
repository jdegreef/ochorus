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
    # queues and authors. Deliberately WITHOUT user/PII analytics and WITHOUT
    # language administration (create/settings/thresholds/go-live stay super
    # admin — the destructive, global levers). A later-phase role.
    "language_admin": [
        (C.REPORTING, V.VIEW),
        (C.AUDIT, V.ACT),
        (C.REVIEW, V.APPROVE),
        (C.PUBLISH, V.ACT),
        (C.TRANSLATE, V.ACT),
        (C.CONTENT_EDIT, V.ACT),
        (C.AUTHORS, V.ACT),
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
