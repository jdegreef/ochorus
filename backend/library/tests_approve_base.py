"""The contract the two approval commands now share.

``approve_translation`` and ``approve_sermon_translation`` were the same file
twice. Collapsing them onto one base means the rules below exist once — so they
are worth asserting once, rather than relying on each command's own tests to
notice a change in shared code.

The rule that matters most is the failure handling: by the time the fixture is
written the DB flip has ALREADY committed, so a fixture problem must warn, not
raise. A traceback there reads to an automated caller as "the approval failed"
and invites a retry of something that already happened.
"""

from __future__ import annotations

from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .models import Author, Book, Sermon


class ApproveCommandBaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(slug="am", name="Andrew Murray")
        cls.book = Book.objects.create(
            author=cls.author,
            slug="humility",
            language="sw",
            title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        cls.sermon = Sermon.objects.create(
            author=cls.author,
            slug="humility",
            language="sw",
            title="Sermon",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )

    # -- both subclasses act on their OWN model -------------------------------

    def test_approving_the_book_leaves_the_sermon_alone(self):
        """They share a slug and a language; only the named kind may flip."""
        call_command("approve_translation", "humility", language="sw", no_fixture=True)
        self.book.refresh_from_db()
        self.sermon.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.AI_REVIEWED)
        self.assertEqual(self.sermon.source_type, Book.SourceType.AI_UNREVIEWED)

    def test_approving_the_sermon_leaves_the_book_alone(self):
        call_command(
            "approve_sermon_translation", "humility", language="sw", no_fixture=True
        )
        self.book.refresh_from_db()
        self.sermon.refresh_from_db()
        self.assertEqual(self.sermon.source_type, Book.SourceType.AI_REVIEWED)
        self.assertEqual(self.book.source_type, Book.SourceType.AI_UNREVIEWED)

    # -- refusals name the right thing ----------------------------------------

    def test_a_missing_work_is_named_by_its_own_noun(self):
        for command, noun in (
            ("approve_translation", "book"),
            ("approve_sermon_translation", "sermon"),
        ):
            with self.subTest(command=command):
                with self.assertRaises(CommandError) as caught:
                    call_command(command, "nope", language="sw", no_fixture=True)
                self.assertIn(noun, str(caught.exception))

    def test_a_public_domain_original_is_refused(self):
        Book.objects.filter(pk=self.book.pk).update(
            source_type=Book.SourceType.PUBLIC_DOMAIN
        )
        with self.assertRaises(CommandError) as caught:
            call_command("approve_translation", "humility", language="sw", no_fixture=True)
        self.assertIn("public-domain", str(caught.exception))
        self.book.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.PUBLIC_DOMAIN)

    # -- the fixture round-trip, and its failure mode -------------------------

    def test_a_fixture_write_failure_warns_and_keeps_the_approval(self):
        """The DB flip has already committed; a fixture problem must not raise."""
        out = StringIO()
        with mock.patch(
            "library.content_fixtures.persist_source_type",
            side_effect=OSError("read-only filesystem"),
        ), mock.patch(
            "library.content_fixtures.book_fixture_path"
        ) as path:
            path.return_value.exists.return_value = True
            path.return_value.name = "humility.sw.json"
            call_command("approve_translation", "humility", language="sw", stdout=out)

        self.book.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.AI_REVIEWED)
        self.assertIn("couldn't update fixture", out.getvalue())

    def test_a_missing_fixture_warns_that_the_approval_will_not_survive(self):
        """source_type is create-only in the seed, so a DB-only flip is lost."""
        out = StringIO()
        with mock.patch("library.content_fixtures.book_fixture_path") as path:
            path.return_value.exists.return_value = False
            path.return_value.name = "humility.sw.json"
            call_command("approve_translation", "humility", language="sw", stdout=out)

        self.book.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.AI_REVIEWED)
        self.assertIn("lost on a rebuild", out.getvalue())

    def test_the_fixture_is_updated_on_a_normal_approval(self):
        out = StringIO()
        with mock.patch(
            "library.content_fixtures.persist_source_type", return_value=True
        ) as persist, mock.patch(
            "library.content_fixtures.sermon_fixture_path"
        ) as path:
            path.return_value.exists.return_value = True
            path.return_value.name = "humility.sw.json"
            call_command(
                "approve_sermon_translation", "humility", language="sw", stdout=out
            )
        persist.assert_called_once()
        self.assertIn("updated fixture", out.getvalue())
