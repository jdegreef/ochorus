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
