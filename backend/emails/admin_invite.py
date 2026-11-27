"""The email a person gets when a super admin grants them admin access.

A grant is keyed by email and can be made before the person has ever signed in
(``accounts.models.AdminGrant``), so without this nothing tells them: the grant
sits there until they happen to sign in with that exact address. This sends
one short staff note — the role, the languages, and where to start.

It is operational mail to a colleague, not reader mail, so it does not go
through ``sending.deliver`` (which needs a reader profile and adds an
unsubscribe footer). It does honour the same two guards every send honours:
the master switch (``emails_enabled``) and the review-mode allowlist
(``address_allowed``). It never raises — a grant must not fail because the
note about it couldn't be sent.
"""

from __future__ import annotations

import logging
from html import escape

from django.conf import settings

from .resend_client import ResendError, send_email
from .sending import address_allowed, emails_enabled

logger = logging.getLogger(__name__)

SENT, SKIPPED, FAILED = "sent", "skipped", "failed"


def _languages_phrase(languages: list[str]) -> str:
    if not languages or "*" in languages:
        return "every language (including any added later)"
    if len(languages) == 1:
        return languages[0]
    return ", ".join(languages[:-1]) + " and " + languages[-1]


def render(
    *,
    role_label: str,
    summary: str,
    languages: list[str],
    changed: bool,
    granted_by: str,
) -> tuple[str, str]:
    """``(subject, html)`` for the note. Pure, so the copy is testable."""
    site = settings.PUBLIC_SITE_URL or "https://ochorus.com"
    start = f"{site}/admin/help"
    langs = _languages_phrase(languages)
    who = escape(granted_by) if granted_by else "A super admin"
    if changed:
        subject = f"Your Ochorus admin access is now {role_label}"
        opener = f"{who} changed your Ochorus admin access. You are now a <b>{escape(role_label)}</b> in {escape(langs)}."
    else:
        subject = f"You've been given {role_label} access to Ochorus"
        opener = f"{who} gave you <b>{escape(role_label)}</b> access to the Ochorus admin, in {escape(langs)}."
    html = f"""<!doctype html><html><body style="font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#1b2130;line-height:1.55;max-width:560px;margin:0 auto;padding:24px">
<p>{opener}</p>
<p style="color:#5d6679">{escape(summary)}</p>
<p>To start, sign in to Ochorus with <b>this email address</b>, then open the admin. The Help &amp; roles page lists exactly what you can do and has the Admin Manual.</p>
<p><a href="{escape(start)}" style="display:inline-block;background:#3b4fb8;color:#fff;text-decoration:none;padding:10px 16px;border-radius:6px;font-weight:600">Open the admin</a></p>
<p style="color:#5d6679;font-size:13px">If you weren't expecting this, you can ignore it — nothing happens until you sign in. If you'd rather not have access, let the person who granted it know.</p>
</body></html>"""
    return subject, html


def send_grant_note(
    email: str,
    *,
    role_label: str,
    summary: str,
    languages: list[str],
    changed: bool,
    granted_by: str,
) -> str:
    """Send the note and return ``"sent"``, ``"skipped"`` (sending off, or the
    address isn't on the review allowlist) or ``"failed"``."""
    if not emails_enabled() or not address_allowed(email):
        return SKIPPED
    subject, html = render(
        role_label=role_label,
        summary=summary,
        languages=languages,
        changed=changed,
        granted_by=granted_by,
    )
    try:
        send_email(to=email, subject=subject, html=html)
    except ResendError:
        logger.exception("admin grant note to %s failed", email)
        return FAILED
    return SENT
