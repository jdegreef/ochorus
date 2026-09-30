"""`library.rights.is_public_domain` — when JSON-LD may claim the Public Domain Mark."""

from __future__ import annotations

from django.test import TestCase

from library.models import Author, Book
from library.rights import ORIGINALS_SLUG, is_public_domain


class PublicDomainRuleTests(TestCase):
    def setUp(self):
        self.old = Author.objects.create(slug="old", name="Old Writer", death_year=1890)
        self.recent = Author.objects.create(slug="recent", name="Recent Writer", death_year=1990)
        self.house = Author.objects.create(slug=ORIGINALS_SLUG, name="Ochorus Originals")

    def book(self, author, slug="w", language="en", attribution="", source_type="public_domain"):
        return Book.objects.create(
            author=author, slug=slug, language=language, title="T",
            attribution=attribution, source_type=source_type,
        )

    def test_a_long_dead_author_with_no_note_is_public_domain(self):
        self.assertTrue(is_public_domain(self.book(self.old)))

    def test_a_recent_author_is_not(self):
        self.assertFalse(is_public_domain(self.book(self.recent)))

    def test_a_note_saying_public_domain_is_enough(self):
        self.assertTrue(is_public_domain(self.book(self.recent, attribution="Public domain.")))

    def test_any_reservation_wins(self):
        for note in ("© A. Writer. Shared with permission.", "Introduction © the Ochorus Library.",
                     "Public domain text; copyright in the notes reserved."):
            with self.subTest(note=note):
                self.assertFalse(is_public_domain(self.book(self.old, slug=note[:8], attribution=note)))

    def test_a_credit_alone_makes_no_claim(self):
        self.assertFalse(is_public_domain(self.book(self.old, attribution="Transcribed by CCEL.")))

    def test_the_house_and_the_modern_edition_never_are(self):
        self.assertFalse(is_public_domain(self.book(self.house)))
        self.assertFalse(is_public_domain(self.book(self.old, language="en-modern")))

    def test_a_translation_follows_its_english_edition(self):
        self.book(self.old, attribution="© Someone.")
        es = self.book(self.old, language="es", attribution="Traducción.", source_type="ai_unreviewed")
        self.assertFalse(is_public_domain(es))
        Book.objects.filter(language="en").update(attribution="Public domain.")
        self.assertTrue(is_public_domain(es))
