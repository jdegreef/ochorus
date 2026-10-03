"""``/api/library/authors/eras/`` — birth years on each live language's shelf.

The era pages build their hreflang from it, so it must follow the Biographies
shelf's own rule (``listed_in_biographies``) and only the live languages.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Author, Book, Language


class AuthorEraPresenceTests(TestCase):
    def setUp(self):
        Language.objects.update(status=Language.Status.DRAFT)
        for code in ("en", "sw"):
            Language.objects.update_or_create(
                code=code, defaults={"name": code, "status": Language.Status.LIVE}
            )
        dated = Author.objects.create(slug="d", name="D", bio="A bio.", birth_year=1828)
        Author.objects.create(slug="u", name="U", bio="A bio.")
        # On the Swahili shelf only through a book there.
        Book.objects.create(author=dated, slug="k", language="sw", title="K", is_published=True)
        # Withheld from the shelf: never counts.
        Author.objects.create(
            slug="h", name="H", bio="A bio.", birth_year=1500, list_in_biographies=False
        )

    def test_years_per_live_language_follow_the_shelf(self):
        res = APIClient().get("/api/library/authors/eras/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, {"en": [1828, None], "sw": [1828]})
