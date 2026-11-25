"""Reviewers' chapter notes on a translation (``/api/admin/review-queue/notes/``)."""

import uuid

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import AdminCapability, AdminGrant, AdminVerb

from .models import AdminAction, Author, Book, ReviewNote

URL = "/api/admin/review-queue/notes/"
VERIFIED = {"email_verified": True}


@override_settings(ADMIN_EMAILS={"super@ochorus.com"})
class ReviewNotesTests(TestCase):
    def setUp(self):
        author = Author.objects.create(slug="am", name="Andrew Murray")
        for lang in ("sw", "es"):
            Book.objects.create(
                author=author,
                slug="humility",
                language=lang,
                title=f"Humility {lang}",
                source_type=Book.SourceType.AI_UNREVIEWED,
            )
        self.superu = self._user("super@ochorus.com")
        self.sw = self._user("sw@ochorus.com")
        AdminGrant.objects.create(
            email="sw@ochorus.com",
            capability=AdminCapability.REVIEW,
            verb=AdminVerb.ACT,
            languages="sw",
        )

    @staticmethod
    def _user(email):
        return User.objects.create(username=str(uuid.uuid4()), email=email)

    def client_for(self, user):
        c = APIClient()
        c.force_authenticate(user=user, token=VERIFIED)
        return c

    def add(self, user, language="sw", chapter=3, note="Paragraph 2 is missing."):
        return self.client_for(user).post(
            URL,
            {
                "kind": "book",
                "slug": "humility",
                "language": language,
                "chapter": chapter,
                "note": note,
            },
            format="json",
        )

    def test_add_list_and_audit(self):
        res = self.add(self.sw)
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(
            (res.data["chapter"], res.data["author"]), (3, "sw@ochorus.com")
        )
        listed = self.client_for(self.sw).get(
            URL, {"kind": "book", "slug": "humility", "language": "sw"}
        )
        self.assertEqual(
            [n["note"] for n in listed.data["notes"]], ["Paragraph 2 is missing."]
        )
        self.assertTrue(listed.data["notes"][0]["mine"])
        self.assertTrue(
            AdminAction.objects.filter(
                action=AdminAction.Action.REVIEW_NOTE, target="book:humility:sw"
            ).exists()
        )

    def test_scope_validation_and_missing_translation(self):
        self.assertEqual(self.add(self.sw, language="es").status_code, 403)
        self.assertEqual(self.add(self.sw, note="  ").status_code, 400)
        self.assertEqual(self.add(self.sw, note="x" * 2001).status_code, 400)
        self.assertEqual(self.add(self.superu, language="fr").status_code, 404)

    def test_only_the_author_or_a_super_admin_removes_a_note(self):
        note_id = self.add(self.superu).data["id"]
        res = self.client_for(self.sw).delete(f"{URL}?id={note_id}&language=sw")
        self.assertEqual(res.status_code, 403)
        mine = self.add(self.sw).data["id"]
        self.assertEqual(
            self.client_for(self.sw).delete(f"{URL}?id={mine}&language=sw").status_code,
            200,
        )
        self.assertEqual(
            self.client_for(self.superu)
            .delete(f"{URL}?id={note_id}&language=sw")
            .status_code,
            200,
        )
        self.assertFalse(ReviewNote.objects.exists())
        self.assertEqual(
            AdminAction.objects.filter(
                action=AdminAction.Action.REVIEW_NOTE_DELETE
            ).count(),
            2,
        )

    def test_a_note_is_held_to_the_language_its_delete_names(self):
        note_id = self.add(self.superu).data["id"]
        # A Spanish-scoped request can't reach a Swahili note by naming its id.
        res = self.client_for(self.superu).delete(f"{URL}?id={note_id}&language=es")
        self.assertEqual(res.status_code, 404)
