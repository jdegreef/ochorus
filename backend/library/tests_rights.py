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

    def test_public_domain_about_something_else_is_no_claim(self):
        # The Key Teachings companions are the house's writing, filed under the
        # author they are about — whose OWN works are public domain.
        for note in (
            "An independent work of exposition by Ochorus. Andrew Murray's own "
            "writings are in the public domain and freely available.",
            "Scripture quotations are from the Berean Standard Bible (BSB), which is "
            "in the public domain.",
        ):
            with self.subTest(note=note):
                self.assertFalse(is_public_domain(self.book(self.recent, slug=note[:8], attribution=note)))

    def test_the_declaration_forms_the_library_uses(self):
        for note in ("Public domain — first published 1879.",
                     "Translated by W. (London, 1884). Public domain.",
                     "The epistles are public domain, in the translation of J. B. Lightfoot."):
            with self.subTest(note=note):
                self.assertTrue(is_public_domain(self.book(self.recent, slug=note[:8], attribution=note)))

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
