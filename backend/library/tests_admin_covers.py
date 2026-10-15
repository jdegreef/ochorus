"""The cover-wall endpoint: every published edition, its tier and provenance."""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .admin_views.covers import cover_tier
from .curated_art import CURATED, ORIGINAL_GROUND
from .designed_covers import DERIVED_GROUND, DESIGNED
from .models import Author, Book

PAINTED = next(iter(CURATED))
ORIGINAL = next(iter(ORIGINAL_GROUND))
DERIVED = next(iter(DERIVED_GROUND))
DESIGNED_URL = next(iter(DESIGNED))


class CoverTierTests(TestCase):
    def test_reads_the_tier_from_the_url_the_edition_wears(self):
        self.assertEqual(cover_tier("x", ""), "none")
        self.assertEqual(cover_tier("x", "/covers/x.svg"), "plate")
        self.assertEqual(cover_tier("x", "/covers/sw/x.svg"), "plate")
        self.assertEqual(cover_tier("x", DESIGNED_URL), "designed")
        self.assertEqual(cover_tier(PAINTED, f"/covers/art/{PAINTED}.jpg"), "painting")
        self.assertEqual(cover_tier(ORIGINAL, f"/covers/art/{ORIGINAL}.jpg"), "original")
        self.assertEqual(cover_tier(DERIVED, f"/covers/art/{DERIVED}.jpg"), "derived")

    def test_an_art_url_outside_every_table_is_other(self):
        self.assertEqual(cover_tier("not-a-work", "/covers/art/not-a-work.jpg"), "other")


class AdminCoversViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        a = Author.objects.create(slug="am", name="Andrew Murray")
        Book.objects.create(
            author=a, slug=PAINTED, language="en", title="Painted",
            cover_url=f"/covers/art/{PAINTED}.jpg",
        )
        Book.objects.create(
            author=a, slug="plated", language="sw", title="Plated",
            cover_title="Short", cover_url="/covers/sw/plated.svg",
        )
        Book.objects.create(
            author=a, slug="draft", language="en", title="Draft",
            cover_url="/covers/draft.svg", is_published=False,
        )

    @override_settings(DEBUG=True)
    def test_lists_published_editions_with_tier_and_painter(self):
        res = self.client.get("/api/admin/covers/")
        self.assertEqual(res.status_code, 200)
        rows = {(r["slug"], r["language"]): r for r in res.data}
        # The unpublished draft is not on the shelf, so not on the wall.
        self.assertEqual(set(rows), {(PAINTED, "en"), ("plated", "sw")})

        painted = rows[(PAINTED, "en")]
        self.assertEqual(painted["tier"], "painting")
        self.assertEqual(painted["artwork"]["artist"], CURATED[PAINTED].artist)
        self.assertEqual(painted["author"], {"slug": "am", "name": "Andrew Murray"})

        plated = rows[("plated", "sw")]
        self.assertEqual(plated["tier"], "plate")
        self.assertIsNone(plated["artwork"])
        # The words the cover sets, as BookCover does.
        self.assertEqual(plated["title"], "Short")

    def test_requires_admin(self):
        res = self.client.get("/api/admin/covers/")
        self.assertIn(res.status_code, (401, 403))
