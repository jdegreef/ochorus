"""The design blocks (image, hero, book row, spacer, Scripture) and the library
blocks for articles, authors and topics: cleaning, per-language resolution,
rendering, their pre-send checks, the picker, and the image upload."""

from __future__ import annotations

import io
import json
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image

from library.models import (
    AdminAction,
    Article,
    Author,
    AuthorTranslation,
    Book,
    Topic,
    TopicTranslation,
)

from . import blocks as blocks_mod
from . import images
from .models import EmailSubscription
from .preflight import run as run_checks
from .rendering import render_broadcast
from .tests import SENDING, _broadcast, _make_profile


def _library():
    murray = Author.objects.create(
        slug="andrew-murray",
        name="Andrew Murray",
        bio="South African pastor and writer on prayer.",
        photo_url="/authors/andrew-murray.jpg",
        birth_year=1828,
        death_year=1917,
    )
    AuthorTranslation.objects.create(author=murray, language="es", bio="Pastor sudafricano.")
    for slug, langs in (("humility-2", ("en", "es")), ("absolute-surrender", ("en",))):
        for lang in langs:
            Book.objects.create(author=murray, slug=slug, language=lang, title=f"{slug} {lang}")
    topic = Topic.objects.create(slug="prayer", title="Prayer", description="Talking with God.")
    TopicTranslation.objects.create(topic=topic, language="es", title="Oración", description="Hablar con Dios.")
    Topic.objects.create(slug="humility", title="Humility")
    Article.objects.create(slug="how-to-pray", language="en", h1="How to pray", description="A short guide.", body_html="<p>x</p>")


def _render(locale, *blocks):
    profile = _make_profile(locale=locale, email=f"{locale}@example.com")
    sub = EmailSubscription.objects.create(profile=profile)
    b = _broadcast(subject={locale: "Hi"}, content={locale: {"blocks": list(blocks)}})
    return render_broadcast(b, profile, sub).html


class CleanTests(SimpleTestCase):
    def test_new_types_keep_their_fields(self):
        cleaned = blocks_mod.clean(
            [
                {"type": "image", "url": "https://x/y.png", "alt": "A", "path": "books", "caption": "C", "onload": "x"},
                {"type": "hero", "title": "T", "color": "plum", "style": "x"},
                {"type": "book_row", "slugs": "a,b"},
                {"type": "spacer", "size": "large"},
            ]
        )
        self.assertEqual(cleaned[0], {"type": "image", "url": "https://x/y.png", "alt": "A", "path": "books", "caption": "C"})
        self.assertNotIn("style", cleaned[1])
        self.assertEqual(cleaned[2]["slugs"], "a,b")

    def test_row_slugs(self):
        self.assertEqual(blocks_mod.row_slugs({"slugs": " a, b ,a,,c,d"}), ["a", "b", "c"])

    @override_settings(PUBLIC_SITE_URL="https://ochorus.test")
    def test_image_url(self):
        self.assertEqual(blocks_mod.image_url("/covers/a.png"), "https://ochorus.test/covers/a.png")
        self.assertEqual(blocks_mod.image_url("https://cdn/a.png"), "https://cdn/a.png")
        for bad in ("http://x/a.png", "javascript:alert(1)", "//evil/a.png", "data:image/png;base64,x", ""):
            self.assertEqual(blocks_mod.image_url(bad), "", bad)


@SENDING
class RenderTests(TestCase):
    def setUp(self):
        _library()

    def test_image_and_hero(self):
        html = _render(
            "en",
            {"type": "image", "url": "/img/a.png", "alt": "A lamp", "path": "books", "caption": "Light"},
            {"type": "image", "url": "http://insecure/a.png", "alt": "", "path": "", "caption": ""},
            {"type": "hero", "eyebrow": "November", "title": "Giving thanks", "text": "Hi {name}", "image": "", "color": "plum", "label": "Read", "path": "plans"},
        )
        self.assertIn('src="https://ochorus.test/img/a.png"', html)
        self.assertIn('alt="A lamp"', html)
        self.assertNotIn("insecure", html)
        self.assertIn("#613f64", html)
        self.assertIn("Hi James", html)
        self.assertIn('href="https://ochorus.test/plans"', html)

    def test_book_row_keeps_only_this_languages_editions(self):
        block = {"type": "book_row", "slugs": "humility-2,absolute-surrender", "label": ""}
        self.assertIn("absolute-surrender en", _render("en", block))
        es = _render("es", block)
        self.assertIn("humility-2 es", es)
        self.assertNotIn("absolute-surrender", es)

    def test_spacer_and_scripture(self):
        html = _render(
            "en",
            {"type": "spacer", "size": "large"},
            {"type": "scripture", "text": "In every thing give thanks", "reference": "1 Thess 5:18"},
        )
        self.assertIn("height:48px", html)
        self.assertIn("In every thing give thanks", html)
        self.assertIn("1 Thess 5:18", html)

    def test_author_bio_only_in_its_language(self):
        block = {"type": "author", "slug": "andrew-murray", "label": ""}
        en = _render("en", block)
        self.assertIn("South African pastor", en)
        self.assertIn("1828–1917", en)
        self.assertIn("https://ochorus.test/authors/andrew-murray.jpg", en)
        es = _render("es", block)
        self.assertIn("Pastor sudafricano", es)
        self.assertIn("https://ochorus.test/es/authors/andrew-murray/", es)

    def test_topic_needs_a_translated_title(self):
        prayer = {"type": "topic", "slug": "prayer", "label": ""}
        humility = {"type": "topic", "slug": "humility", "label": ""}
        self.assertIn("Oración", _render("es", prayer))
        self.assertNotIn("Humility", _render("es", humility))
        self.assertIn("Humility", _render("en", humility))

    def test_article_card(self):
        html = _render("en", {"type": "article", "slug": "how-to-pray", "label": "Read it"})
        self.assertIn("How to pray", html)
        self.assertIn("https://ochorus.test/articles/how-to-pray/", html)


class CheckTests(TestCase):
    def setUp(self):
        _library()

    def _levels(self, *blocks, locale="en"):
        b = _broadcast(subject={locale: "Hi"}, content={locale: {"blocks": [{"type": "text", "text": "Body"}, *blocks]}})
        return {c["code"]: c["level"] for c in run_checks(b)}

    def test_image_checks(self):
        levels = self._levels(
            {"type": "image", "url": "", "alt": "", "path": "", "caption": ""},
            {"type": "image", "url": "http://x/a.png", "alt": "", "path": "", "caption": ""},
            {"type": "image", "url": "/a.png", "alt": "", "path": "", "caption": ""},
        )
        self.assertEqual(levels["image:en:1"], "error")
        self.assertEqual(levels["image:en:2"], "error")
        self.assertEqual(levels["image-alt:en:3"], "warning")

    def test_book_row_checks(self):
        levels = self._levels(
            {"type": "book_row", "slugs": "", "label": ""},
            {"type": "book_row", "slugs": "humility-2,nope,absolute-surrender", "label": ""},
            locale="es",
        )
        self.assertEqual(levels["library:es:1"], "error")
        self.assertEqual(levels["library:es:2:1"], "error")
        self.assertEqual(levels["library:es:2:2"], "warning")
        self.assertNotIn("library:es:2:0", levels)

    def test_topic_and_author_checks(self):
        levels = self._levels(
            {"type": "topic", "slug": "humility", "label": ""},
            {"type": "author", "slug": "andrew-murray", "label": ""},
            {"type": "author", "slug": "nobody", "label": ""},
            locale="es",
        )
        self.assertEqual(levels["library:es:1"], "warning")  # no Spanish title
        self.assertNotIn("library:es:2", levels)
        self.assertEqual(levels["library:es:3"], "error")

    def test_hero_checks(self):
        levels = self._levels(
            {"type": "hero", "title": "", "text": "", "image": "", "color": "", "label": "", "path": ""},
            {"type": "hero", "title": "T", "text": "", "image": "ftp://x", "color": "", "label": "Go", "path": "https://evil"},
        )
        self.assertEqual(levels["hero:en:1"], "warning")
        self.assertEqual(levels["hero:en:2"], "error")
        self.assertEqual(levels["hero-cta:en:2"], "error")


@override_settings(DEBUG=True)  # loopback test client → admin gate bypassed
class PickerTests(TestCase):
    def setUp(self):
        _library()

    def test_author_topic_and_article_search(self):
        authors = self.client.get("/api/admin/emails/library/?type=author&q=murray").json()["results"]
        self.assertEqual(authors[0]["title"], "Andrew Murray")
        topics = self.client.get("/api/admin/emails/library/?type=topic&q=pray").json()["results"]
        self.assertEqual(topics[0]["languages"], ["en", "es"])
        articles = self.client.get("/api/admin/emails/library/?type=article&slugs=how-to-pray").json()["results"]
        self.assertEqual(articles[0]["title"], "How to pray")
        self.assertEqual(self.client.get("/api/admin/emails/library/?type=image").status_code, 400)


def _png(width=40, height=20, fmt="PNG"):
    out = io.BytesIO()
    Image.new("RGB", (width, height), "navy").save(out, fmt)
    return out.getvalue()


class _Resp:
    def __init__(self, status=200, text="{}"):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise images.requests.HTTPError(self.text)


@override_settings(DEBUG=True, SUPABASE_URL="https://sb.test", SUPABASE_SERVICE_ROLE_KEY="key")
class ImageUploadTests(TestCase):
    def _upload(self, data, name="a.png"):
        return self.client.post("/api/admin/emails/images/", {"file": SimpleUploadedFile(name, data)})

    @mock.patch("emails.images.requests.post", return_value=_Resp())
    def test_upload_returns_a_public_url(self, post):
        res = self._upload(_png())
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json()["url"].startswith("https://sb.test/storage/v1/object/public/email-images/"))
        self.assertTrue(res.json()["url"].endswith(".png"))
        self.assertEqual(post.call_args.kwargs["headers"]["Content-Type"], "image/png")
        self.assertTrue(AdminAction.objects.filter(action=AdminAction.Action.EMAIL_IMAGE_UPLOAD).exists())

    @mock.patch("emails.images.requests.post", return_value=_Resp())
    def test_a_wide_picture_is_scaled_down(self, post):
        self._upload(_png(3000, 1000, "JPEG"), "big.jpg")
        stored = Image.open(io.BytesIO(post.call_args.kwargs["data"]))
        self.assertEqual(stored.size, (1200, 400))

    def test_not_a_picture(self):
        res = self._upload(b"%PDF-1.4 not an image", "a.png")
        self.assertEqual(res.status_code, 400)

    @mock.patch(
        "emails.images.requests.post",
        side_effect=[_Resp(404, '{"error":"Bucket not found"}'), _Resp(200), _Resp(200)],
    )
    def test_the_first_upload_makes_the_bucket(self, post):
        self.assertEqual(self._upload(_png()).status_code, 201)
        self.assertTrue(post.call_args_list[1].args[0].endswith("/storage/v1/bucket"))
        self.assertEqual(post.call_args_list[1].kwargs["json"]["public"], True)

    @override_settings(SUPABASE_URL="")
    def test_needs_storage_configured(self):
        res = self._upload(_png())
        self.assertEqual(res.status_code, 400)
        self.assertIn("isn't configured", res.json()["detail"])


class TranslationSlotTests(SimpleTestCase):
    def test_new_words_are_translated_and_addresses_are_not(self):
        from .translation_jobs import _slots

        blocks = blocks_mod.clean(
            [
                {"type": "hero", "eyebrow": "E", "title": "T", "text": "X", "image": "/a.png", "color": "plum", "label": "Go", "path": "books"},
                {"type": "image", "url": "/a.png", "alt": "Alt", "path": "", "caption": "Cap"},
                {"type": "scripture", "text": "Verse", "reference": "John 1:1"},
            ]
        )
        fields = {(i, f) for i, f in _slots(blocks)}
        self.assertIn((0, "title"), fields)
        self.assertIn((0, "eyebrow"), fields)
        self.assertNotIn((0, "image"), fields)
        self.assertNotIn((0, "color"), fields)
        self.assertIn((1, "alt"), fields)
        self.assertIn((2, "reference"), fields)


class JsonShapeTests(SimpleTestCase):
    def test_every_block_type_has_fields(self):
        self.assertEqual(set(blocks_mod.FIELDS), set(blocks_mod.BlockType.values))
        json.dumps(blocks_mod.FIELDS)


class ReviewFixTests(TestCase):
    def test_hero_colours_match_the_designer(self):
        import re
        from pathlib import Path

        ts = (Path(__file__).resolve().parents[2] / "frontend/src/lib/library-admin.ts").read_text()
        block = ts[ts.index("export const HERO_COLORS") :]
        block = block[: block.index("};")]
        self.assertEqual(dict(re.findall(r"(\w+): '(#[0-9a-f]{6})'", block)), blocks_mod.HERO_COLORS)

    @override_settings(PUBLIC_SITE_URL="https://ochorus.test")
    def test_hero_title_takes_the_name(self):
        out = blocks_mod.resolve(
            [{"type": "hero", "eyebrow": "For {name}", "title": "Welcome, {name}", "text": "", "image": "", "color": "", "label": "", "path": ""}],
            "en",
            name="Ana",
        )
        self.assertEqual((out[0]["title"], out[0]["eyebrow"]), ("Welcome, Ana", "For Ana"))

    def test_an_email_of_only_an_insecure_image_or_a_bare_hero_button_is_empty(self):
        b = _broadcast(
            subject={"en": "Hi"},
            content={
                "en": {
                    "blocks": [
                        {"type": "image", "url": "http://x/a.png", "alt": "", "path": "", "caption": ""},
                        {"type": "hero", "eyebrow": "", "title": "", "text": "", "image": "", "color": "", "label": "Go", "path": ""},
                    ]
                }
            },
        )
        levels = {c["code"]: c["level"] for c in run_checks(b)}
        self.assertEqual(levels["body:en"], "error")
        self.assertEqual(levels["hero-cta:en:1"], "warning")

    def test_an_author_reaches_only_the_languages_their_page_is_built_for(self):
        from library.models import Language

        Language.objects.get_or_create(code="fr", defaults={"name": "French", "native_name": "Français"})
        Author.objects.create(slug="ochorus-originals", name="Ochorus", is_imprint=True)
        quiet = Author.objects.create(slug="quiet", name="Quiet Person")
        murray = Author.objects.create(slug="murray", name="Andrew Murray", bio="Pastor.")
        Book.objects.create(author=quiet, slug="q", language="fr", title="Q")
        reach = blocks_mod.editions("author", ["ochorus-originals", "quiet", "murray"])
        self.assertNotIn("ochorus-originals", reach)
        self.assertEqual(reach["quiet"], {"fr"})
        self.assertIn("en", reach["murray"])
        self.assertTrue(murray)


class ImagePrepTests(SimpleTestCase):
    def test_a_rotated_phone_photo_is_turned_upright_and_stripped(self):
        img = Image.new("RGB", (40, 20), "navy")
        exif = img.getexif()
        exif[0x0112] = 6  # Orientation: rotate 90° CW to view
        exif[0x010F] = "PhoneMaker"
        out = io.BytesIO()
        img.save(out, "JPEG", exif=exif)
        data, ext, _ = images._prepare(out.getvalue())
        stored = Image.open(io.BytesIO(data))
        self.assertEqual(stored.size, (20, 40))
        self.assertEqual(dict(stored.getexif()), {})
        self.assertEqual(ext, "jpg")

    def test_too_many_pixels(self):
        with mock.patch.object(images, "MAX_PIXELS", 100):
            with self.assertRaises(images.ImageError):
                images._prepare(_png(20, 20))
