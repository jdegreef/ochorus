"""The note a person gets when they are granted admin access (Team & access)."""

from __future__ import annotations

from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from emails import admin_invite
from library.models import AdminAction

LIVE = {
    "DEBUG": True,
    "EMAIL_ENABLED": True,
    "RESEND_API_KEY": "re_test",
    "API_PUBLIC_URL": "https://api.example.com",
    "PUBLIC_SITE_URL": "https://ochorus.example",
    "EMAIL_ALLOWLIST": [],
}


@override_settings(**LIVE)
class GrantNoteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        patcher = mock.patch("emails.admin_invite.send_email", return_value="msg_1")
        self.send = patcher.start()
        self.addCleanup(patcher.stop)

    def _grant(self, **extra):
        body = {
            "email": "Maika@Example.com",
            "role": "content_admin",
            "languages": ["*"],
        }
        body.update(extra)
        return self.client.post("/api/admin/team/", body, format="json")

    def test_a_role_grant_with_notify_emails_the_grantee(self):
        res = self._grant(notify=True)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["notified"], "sent")
        kwargs = self.send.call_args.kwargs
        self.assertEqual(kwargs["to"], "maika@example.com")
        self.assertIn("Content admin", kwargs["subject"])
        self.assertIn("every language", kwargs["html"])
        self.assertIn("https://ochorus.example/admin/help", kwargs["html"])
        # The log records that the note went.
        row = AdminAction.objects.get(action=AdminAction.Action.ROLE_GRANT)
        self.assertEqual(row.detail["notified"], "sent")

    def test_no_notify_no_email(self):
        res = self._grant()
        self.assertEqual(res.data["notified"], "")
        self.send.assert_not_called()

    def test_a_change_of_role_says_so(self):
        self._grant(role="reviewer", languages=["es"])
        self._grant(notify=True)
        self.assertIn("now Content admin", self.send.call_args.kwargs["subject"])

    def test_undo_and_single_capability_grants_send_nothing(self):
        self.client.post(
            "/api/admin/team/",
            {
                "email": "x@example.com",
                "capability": "reporting",
                "verb": "view",
                "notify": True,
            },
            format="json",
        )
        self.client.post(
            "/api/admin/team/",
            {
                "email": "y@example.com",
                "restore": [],
                "notify": True,
                "role": "reviewer",
            },
            format="json",
        )
        self.send.assert_not_called()

    @override_settings(EMAIL_ALLOWLIST=["james@example.com"])
    def test_review_mode_skips_an_address_off_the_allowlist(self):
        self.assertEqual(self._grant(notify=True).data["notified"], "skipped")
        self.send.assert_not_called()

    @override_settings(EMAIL_ENABLED=False)
    def test_sending_off_skips(self):
        self.assertEqual(self._grant(notify=True).data["notified"], "skipped")

    def test_a_provider_failure_does_not_fail_the_grant(self):
        self.send.side_effect = admin_invite.ResendError("boom")
        res = self._grant(notify=True)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["notified"], "failed")

    def test_copy_escapes_the_granter(self):
        _, html = admin_invite.render(
            role_label="Reviewer",
            summary="s",
            languages=["Spanish", "Swahili"],
            changed=False,
            granted_by="<b>x</b>",
        )
        self.assertNotIn("<b>x</b>", html)
        self.assertIn("Spanish and Swahili", html)
