# ADR 0001 — Graduated, scoped admin access

**Status:** Accepted (Phase 1 implemented) · **Date:** 2026-09-13 · **Supersedes:** the flat `IsAdminEmail` allowlist as the only admin gate.

## Context

Admin was one all-or-nothing boolean: an email in `ADMIN_EMAILS` (env), checked
by `accounts.permissions.IsAdminEmail` (+ a verified-email requirement, and a
DEBUG-loopback bypass for local dev). No roles, scopes, or groups. We want to let
other people help — some to view and *suggest* only, some to *review* content and
submit work a super admin confirms — across specific languages, growing from a
handful of helpers to many contributors over time.

Two facts about Ochorus shape the design:

- **The content pipeline is already proposal-based.** Nothing reaches readers
  except through a committed fixture + a deploy; translations and content edits
  are already "file a job → a worker executes it → a reviewer approves it." Git +
  PR review is our maker-checker.
- **Identity already has a local home** (`accounts.UserProfile`, mirrored from the
  Supabase JWT), but no place for authority.

## Decision

Model access as **roles with a language attribute**, stored in the DB, enforced in
Django from declarations co-located on each view, and lean on Git/PR review for
maker-checker. Launch with a few presets; keep the flexible primitive underneath.

The unit of authority is a grant: **`(email · capability · language-scope · verb)`**.

- **Capabilities** (9): `reporting`, `users` (PII — split out on purpose), `audit`,
  `review`, `publish`, `translate`, `content_edit`, `authors`, `language_admin`.
- **Verbs** (ladder): `view` < `suggest` < `act` < `approve`. A grant at a higher
  rank satisfies any lower requirement for the same capability + language.
- **Language scope**: a set of codes, or `*` for all. Non-language-scoped endpoints
  ignore it.

A **role** (Contributor, Reviewer, Language Admin) is a labelled bundle of grants,
not a table — the rows are the truth.

### Decisions and rejected alternatives

1. **RBAC + a language attribute**, not pure RBAC (role explosion: `es-reviewer`,
   `pt-reviewer`…) and not full ABAC/ReBAC (hard to audit, overkill at this scale).
   Language is inherently an attribute.
2. **DB-stored grants** (`accounts.AdminGrant`), not Supabase JWT custom claims
   (revocation lags a token refresh — unacceptable for admin power) and not
   Supabase RLS (the Django API connects as table owner and bypasses RLS; RLS
   guards the anon key, not the admin surface). `ADMIN_EMAILS` remains the
   **super-admin bootstrap only**, outside the grant table, so a bad grant edit
   can't lock everyone out.
3. **Enforce in Django from co-located declarations** (`@requires(...)` sets
   `admin_capability`/`admin_verb(s)`/`admin_language_arg` and wires
   `RequireCapability`), not a policy engine (premature at ~10 rules). A coverage
   test (`library.tests_admin_access`) walks the URL conf and fails the build if
   any admin route ships without a valid declaration.
4. **Lean on Git/PR review for maker-checker**, not a bespoke in-app approval
   queue. Content prose already ships as fixture PRs; limited admins route into
   that pipeline (the job queues are the "propose without applying" channel). The
   only changes without a PR are live-DB levers (publish, review-flip, go-live);
   for those, limited admins *propose* and a super admin *acts*. A small
   provisional-review extension (Phase 2) covers "they review, I approve".
5. **Four verbs, only where each is real** — `suggest` exists on the queues (where
   filing a job changes nothing live); not forced onto every capability.
6. **Three presets now** (Contributor, Reviewer, + Language Admin for later),
   matrix editor deferred — start coarse, refine on evidence.

### Roles (presets)

| Role | Can | Cannot | Scope |
|---|---|---|---|
| **Contributor** | view reports/queues; suggest (file jobs) | apply anything live; approve; PII | granted language(s) |
| **Reviewer** | + record *provisional* review decisions | confirm the reader-visible flip; publish; go-live | granted language(s) |
| **Language Admin** *(later)* | act + approve within language | global destructive levers | granted language(s) |
| **Super Admin** | everything, incl. granting roles | — | `all` (env bootstrap) |

### Non-negotiables

1. **Close the side doors** — the API must be the only content-mutation path
   (direct DB / DEBUG Django-admin bypass the model and the audit log).
2. **Separation of duties** on destructive levers (go-live, unpublish,
   bulk-approve): proposer ≠ approver.
3. **Least privilege, default-deny** — no grant, no access.
4. **Audit the actor and the authority** — the append-only `AdminAction` log
   records who; grant/revoke are themselves audited.
5. **One source of truth for policy**, backend + frontend, coverage-tested.
6. **PII is its own scope** — `users`/`export` are not implied by content reporting.

## Language scoping — resolution rules

- A view declaring a language dimension (`admin_language_arg`) **fails closed**:
  if the target language can't be resolved from the request, access is denied
  (an unresolved language must never read as "global — allow").
- A **batch / multi-language** endpoint (the review-queue POST) carries language
  *per item*, so the view-level gate can't scope it — it declares no
  `admin_language_arg` and enforces scope per row against `allowed_languages`,
  and its list GET is filtered to the caller's languages. Same for the job-queue
  list reads.
- `authors` and `language_admin` are **global-by-design** (an author is
  language-independent; creating a language is not scoped to an existing one), so
  a grant's language set doesn't narrow them — deliberate, not an oversight.

## Frontend navigation (Phase 1, PR2)

The admin rail (`routes/admin/+layout.svelte`) shows only the sections a user's
grants open, via `auth.can(capability)` (the pure mirror in `$lib/adminAccess.ts`;
UX only — the API still authorises every request). The "Admin" entry link is
gated on `auth.hasAdminAccess` (super **or** any grant), not `is_admin` (which is
super-only), so scoped grantees can reach the area.

The rail has sections for `reporting`, `publish`, `review`, `audit`, `users`.
`translate` / `content_edit` / `authors` are reached as **drill-downs** (book and
author detail pages), and `language_admin`'s landing is the dashboard's language
list — none has a dedicated top-level section. So every preset includes
`reporting:view` (the Dashboard) to guarantee a navigable entry; a hand-issued
single-capability grant for a drill-down capability is the one case that lands
with an empty rail (reachable by URL, still API-authorised). Per-control gating
inside a page (hiding an action above a user's verb) is a later refinement — the
API is the enforcement in the meantime.

## Consequences

- With no grants issued, behaviour is identical to today: super admins in, all
  others out — `RequireCapability` short-circuits on the allowlist. Grants then
  light up scoped access without touching endpoint code.
- Roles are assigned via `manage.py admin_grants` until the Phase-2 `/admin/team`
  console exists.

## Status by phase

- **Phase 1 (this ADR):** `AdminGrant` model, `RequireCapability` + `@requires`
  across the admin surface, `/api/auth/me` roles/scopes, the `admin_grants`
  command, coverage + enforcement tests. Frontend nav/guard and the
  provisional-review mechanic follow in the next PR.
- **Phase 2:** the `/admin/team` console; fine-grained grants; the provisional
  review extension to `ReviewOutcome`.
- **Phase 3:** two-person enforcement, time-boxed grants, notifications, more
  presets.

The styled, shareable version of this record lives as a Claude artifact for
onboarding; this file is the canonical text.
