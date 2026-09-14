"""Grant, revoke, and list scoped admin access — the CLI for admin roles until
the ``/admin/team`` console (Phase 2) exists.

    manage.py admin_grants grant  --email a@b.com --role reviewer --languages es,pt
    manage.py admin_grants grant  --email a@b.com --capability review --verb act --languages es
    manage.py admin_grants revoke --email a@b.com [--capability review]
    manage.py admin_grants list   [--email a@b.com]

The super admin is NOT managed here — it stays the ``ADMIN_EMAILS`` allowlist
(env), on purpose, so this command can never revoke the last way in.
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts.admin_roles import PRESETS, ROLE_NAMES
from accounts.models import (
    ALL_LANGUAGES,
    AdminCapability,
    AdminGrant,
    AdminVerb,
    split_providers,
)


class Command(BaseCommand):
    help = "Grant, revoke, or list scoped admin access (AdminGrant rows)."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=("grant", "revoke", "list"))
        parser.add_argument("--email")
        parser.add_argument("--role", choices=ROLE_NAMES, help="A preset bundle of grants.")
        parser.add_argument("--capability", choices=AdminCapability.values)
        parser.add_argument("--verb", choices=AdminVerb.values)
        parser.add_argument(
            "--languages",
            default=ALL_LANGUAGES,
            help='Comma-separated codes, or "*" for all (default).',
        )
        parser.add_argument("--by", default="", help="Super admin issuing the grant (for the audit trail).")

    def handle(self, *args, **opts):
        getattr(self, f"_{opts['action']}")(opts)

    # -- actions ---------------------------------------------------------------

    def _grant(self, opts):
        email = self._require_email(opts)
        if email in settings.ADMIN_EMAILS:
            raise CommandError(
                f"{email} is already a super admin via ADMIN_EMAILS — grants add nothing."
            )
        languages = self._clean_languages(opts["languages"])

        if opts["role"]:
            pairs = PRESETS[opts["role"]]
            label = opts["role"]
            granted = f"role '{opts['role']}'"
        elif opts["capability"] and opts["verb"]:
            pairs = [(opts["capability"], opts["verb"])]
            label = ""
            granted = f"{opts['capability']}:{opts['verb']}"
        else:
            raise CommandError("grant needs either --role, or both --capability and --verb.")

        granted_by = (opts.get("by") or "").strip().lower()
        for capability, verb in pairs:
            AdminGrant.objects.update_or_create(
                email=email,
                capability=capability,
                defaults={
                    "verb": verb,
                    "languages": languages,
                    "role_label": label,
                    "granted_by": granted_by,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Granted {granted} to {email} ({languages})."))
        self._show(email)

    def _revoke(self, opts):
        email = self._require_email(opts)
        qs = AdminGrant.objects.filter(email=email)
        if opts["capability"]:
            qs = qs.filter(capability=opts["capability"])
        n, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Revoked {n} grant row(s) from {email}."))

    def _list(self, opts):
        email = (opts.get("email") or "").strip().lower()
        if email:
            self._show(email)
            return
        emails = (
            AdminGrant.objects.order_by("email").values_list("email", flat=True).distinct()
        )
        if not emails:
            self.stdout.write("No admin grants. (Super admins: " + ", ".join(sorted(settings.ADMIN_EMAILS)) + ")")
            return
        for e in emails:
            self._show(e)

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _require_email(opts) -> str:
        email = (opts.get("email") or "").strip().lower()
        if not email:
            raise CommandError("--email is required.")
        return email

    @staticmethod
    def _clean_languages(raw: str) -> str:
        raw = (raw or "").strip()
        if raw == ALL_LANGUAGES or not raw:
            return ALL_LANGUAGES
        # split_providers: the shared comma-split "blanks mean nothing" helper.
        codes = sorted({c.strip().lower() for c in split_providers(raw)})
        return ",".join(codes) or ALL_LANGUAGES

    def _show(self, email: str):
        grants = AdminGrant.objects.filter(email=email).order_by("capability")
        if not grants:
            self.stdout.write(f"  {email}: (no grants)")
            return
        self.stdout.write(self.style.HTTP_INFO(email))
        for g in grants:
            role = f" [{g.role_label}]" if g.role_label else ""
            self.stdout.write(f"  · {g.capability}:{g.verb} — {g.languages}{role}")
