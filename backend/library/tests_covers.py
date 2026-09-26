"""Cover art: the ink-safe plate, the emblem, generated covers, curated art.

Moved out of the 6,500-line library/tests.py so a domain can be run — and
edited — on its own. Pure move: no test changed.
"""

import re
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from .models import (
    Author,
    Book,
)


class PlateMaterialTests(SimpleTestCase):
    """The ribbing that gives a generated plate a surface, and its one rule.

    `ink_safe` promises white type at the byline clears AA against this ground,
    and it computes that from the FLAT colour — the only thing it can see. So a
    material that lightens any pixel breaks the promise exactly where there is
    no headroom: on a plate already floored to 4.5:1. Measured on the library's
    floored colours, a symmetric `mix-blend-mode: overlay` grain took the worst
    pixel from 4.58 to 4.12 — below AA — at the faintest strength tried.

    Black at a low alpha cannot do that: white ink on a darker ground is higher
    contrast, never lower. These hold the drawing to that, because the failure
    is invisible — a lightening material looks like a nicer texture and quietly
    costs a book its contrast floor.
    """

    def _pattern(self, svg):
        """The one grain pattern, or a failure naming what it found instead."""
        found = re.findall(r"<pattern\b.*?</pattern>", svg, re.S)
        self.assertEqual(len(found), 1, f"expected one pattern, found {len(found)}")
        return found[0]

    def test_the_material_is_black_and_nothing_but_black(self):
        from library.covers import build_ground

        tile = self._pattern(build_ground("#7a2740"))
        fills = re.findall(r'fill="([^"]+)"', tile)
        self.assertEqual(
            fills,
            ["black"],
            "the tile paints something other than black, so it can lighten a pixel "
            "and break the contrast floor ink_safe computed from the flat plate",
        )
        # A tile that painted its whole area would be a flat wash, not a rib —
        # and the transparent remainder is half of why this can only subtract.
        rib = re.search(r'<rect[^>]*width="([\d.]+)"[^>]*height="([\d.]+)"', tile)
        period = re.search(r'<pattern[^>]*width="([\d.]+)"', tile)
        self.assertLess(
            float(rib.group(1)),
            float(period.group(1)),
            "the rib fills the tile, so the material is a flat darkening",
        )
        opacity = float(re.search(r'opacity="([\d.]+)"', tile).group(1))
        self.assertTrue(0 < opacity < 1, f"opacity {opacity} is not a partial ink")

    def test_the_material_holds_no_lightening_primitive(self):
        from library.covers import build_ground

        svg = build_ground("#7a2740")
        # A blend mode is exactly the mechanism by which a black layer ends up
        # lightening a pixel — `overlay` is what made the first attempt look
        # right and measure wrong. A filter could do it too (an `feComposite`
        # in arithmetic, an `feBlend` in screen), and a ground has no other use
        # for one, so neither may appear at all.
        self.assertNotIn("mix-blend-mode", svg)
        self.assertNotIn("<filter", svg)
        self.assertNotIn("feBlend", svg)
        self.assertNotIn("feComposite", svg)

    def test_the_material_rect_paints_nothing_of_its_own(self):
        from library.covers import build_ground

        # A paint reference that does not resolve is an error, and a dropped
        # reference falls to SVG's initial fill, which is BLACK across the whole
        # plate. Either way every generated cover breaks at once — and breaks
        # green, because no other gate looks at this element. The `none`
        # fallback degrades it to the flat plate instead.
        rect = re.search(r"<rect[^>]*url\(#grain\)[^>]*>", build_ground("#7a2740"))
        self.assertIsNotNone(rect, "the ground no longer references the material")
        self.assertIn(
            'fill="url(#grain) none"',
            rect.group(0),
            "no paint fallback, so a broken reference paints the plate black",
        )

    def test_a_plate_is_byte_identical_when_rebuilt(self):
        from library.covers import build_ground

        # The plates are committed files. Anything per-run in the material would
        # rewrite all eighteen on every regeneration and bury a real change.
        for color in ("#7a2740", "#4a7ac8", "#8ab04a"):
            with self.subTest(color=color):
                self.assertEqual(build_ground(color), build_ground(color))


class InkSafePlateTests(SimpleTestCase):
    """The legibility floor under every generated plate.

    White type on a coloured plate is the house style across both cover tiers,
    so when a plate colour is too pale the colour has to yield, not the ink. The
    numbers below are the library's real ones: 8 of 45 plate colours failed AA
    on the 23px author line, worst at 2.81:1.
    """

    PALE = ["#ca8d21", "#4996a2", "#2f9e44", "#987952", "#987652", "#ffffff"]
    ALREADY_LEGIBLE = ["#3b5bdb", "#1864ab", "#7a5c48", "#14532d", "#000000"]

    def test_pale_plates_are_darkened_until_the_byline_passes(self):
        from library.covers import AUTHOR_MIN_CONTRAST, author_ink_contrast, ink_safe

        for color in self.PALE:
            with self.subTest(color=color):
                self.assertLess(author_ink_contrast(color), AUTHOR_MIN_CONTRAST)
                self.assertGreaterEqual(
                    author_ink_contrast(ink_safe(color)), AUTHOR_MIN_CONTRAST
                )

    def test_legible_plates_are_returned_untouched(self):
        from library.covers import ink_safe

        # The floor must be a no-op on 37 of the library's 45 plate colours, or
        # it would rewrite artwork it has no business rewriting.
        for color in self.ALREADY_LEGIBLE:
            with self.subTest(color=color):
                self.assertEqual(ink_safe(color), color)

    def test_hue_survives_the_floor(self):
        from library.covers import ink_safe

        # Scaling channels, not moving through HLS: a green plate comes back a
        # deeper green. Ratios between channels are what carry the hue.
        darkened = ink_safe("#2f9e44")
        original = (0x2F, 0x9E, 0x44)
        got = tuple(int(darkened[i : i + 2], 16) for i in (1, 3, 5))
        self.assertLess(got[0], original[0])
        self.assertAlmostEqual(got[1] / got[0], original[1] / original[0], delta=0.08)
        self.assertAlmostEqual(got[2] / got[0], original[2] / original[0], delta=0.08)

    def test_blank_and_malformed_colours_fall_back_to_the_house_blue(self):
        from library.covers import ink_safe

        for value in ["", None, "#zzz", "not-a-colour"]:
            with self.subTest(value=value):
                self.assertEqual(ink_safe(value), "#3b5bdb")

    def test_the_drawn_plate_uses_the_floored_colour(self):
        from library.covers import build_ground

        # The floor is only worth anything if build_ground actually applies it.
        svg = build_ground("#ca8d21")
        self.assertIn('stop-color="#956818"', svg)
        self.assertNotIn('stop-color="#ca8d21"', svg)


class CoverEmblemTests(SimpleTestCase):
    """The device that stops a shelf of generated plates reading as wallpaper.

    105 of the library's 153 editions wear a generated plate. The colour varies
    per book but the COMPOSITION doesn't, so a grid of them is twelve coloured
    slabs with nothing to tell one from another at a glance. The emblem is a
    second variable, and it is the book's own — the drawing its topic already
    wears on the topics shelf.
    """

    def test_a_book_wears_its_topics_emblem(self):
        from library.covers import emblem_for_book

        self.assertEqual(emblem_for_book("prevailing-prayer"), "praying-hands")
        self.assertEqual(emblem_for_book("confessions"), "laurel-tome")
        self.assertIsNone(emblem_for_book("a-book-in-no-topic"))

    def test_the_topic_seed_stays_the_source_of_which_books_a_topic_holds(self):
        """One list of shelf members, read by the seed AND by the generator.

        `covers.py` is deliberately Django-free — the curation scripts import it
        as a plain module — so it cannot import `seed_topics`, which pulls in
        `django.core.management`. The membership therefore lives in
        `library/topic_seed.py`, which both import. This fails if a copy is
        introduced: an emblem drawn from a second list would be right until the
        day someone edits only one of them.
        """
        from library.management.commands import seed_topics
        from library.topic_seed import TOPICS

        self.assertIs(seed_topics.TOPICS, TOPICS)

    def test_the_emblem_lands_in_the_band_the_type_reserves(self):
        """The emblem lands in the band, centred, at the size the band allows.

        It used to be fitted instead: the band between the last line of type and
        the lockup was measured and the drawing sized to what was left, because
        a four-line title pushed the type 52 units further down than a one-line
        one. Nothing in this module knows where the type ends any more — the
        browser wraps it — so the band is reserved on both sides instead.

        That the CSS reserves the SAME band is checked by `coverBand.test.ts`,
        which reads the constants below and converts them; asserting it here
        would only restate the arithmetic that defines them.
        """
        import re

        from library.covers import _EMBLEM_BOTTOM, _EMBLEM_TOP, build_ground

        found = re.search(
            r'<g transform="translate\((\d+) (\d+)\) scale\(([\d.]+)\)"',
            build_ground("#0b7285", "praying-hands"),
        )
        left, top, scale = int(found.group(1)), int(found.group(2)), float(found.group(3))
        size = scale * 48  # every emblem is drawn on a 48x48 canvas

        self.assertEqual(top, _EMBLEM_TOP)
        self.assertEqual(top + size, _EMBLEM_BOTTOM)
        self.assertEqual(left, (600 - size) / 2, "emblem is not centred on the plate")

    def test_a_plate_without_an_emblem_is_unchanged(self):
        """A book in no topic, or one whose emblem the API image is missing,
        gets the plate it had — not a broken one, and not a shifted one."""
        from library.covers import build_ground

        self.assertEqual(
            build_ground("#0b7285"),
            build_ground("#0b7285", emblem="not-an-emblem"),
        )


class GeneratedCoverTests(TestCase):
    """The two invariants of the cover generator.

    Both of these were real defects, not hypotheticals: covers were written to
    one path per SLUG while the loop ran over every language row, so the last
    language processed overwrote the rest and every locale served the same
    (English) cover under a translated title.
    """

    def setUp(self):
        self.author = Author.objects.create(slug="am", name="Andrew Murray")

    def _book(self, language, title, cover_url=""):
        return Book.objects.create(
            slug="waiting-on-god",
            language=language,
            title=title,
            author=self.author,
            cover_url=cover_url,
            cover_color="#2f6f6b",
        )

    def test_each_language_gets_its_own_cover_path(self):
        from library.management.commands.generate_covers import cover_path

        # English keeps the historic path so the covers already live don't 404.
        self.assertEqual(cover_path("waiting-on-god", "en")[0], "/covers/waiting-on-god.svg")
        self.assertEqual(cover_path("waiting-on-god", "es")[0], "/covers/es/waiting-on-god.svg")
        self.assertEqual(cover_path("waiting-on-god", "ar")[0], "/covers/ar/waiting-on-god.svg")

    def test_artwork_is_never_overwritten_even_with_force(self):
        """--force means "redraw the generated ones", never "replace the art"."""
        from library.management.commands.generate_covers import is_generated

        self.assertFalse(is_generated("/covers/godliness.jpg"))
        self.assertFalse(is_generated("/covers/baptism.png"))
        self.assertTrue(is_generated("/covers/all-of-grace.svg"))
        self.assertTrue(is_generated(""))

    def test_a_ground_carries_no_words(self):
        """The whole point of the tier, and the thing that can regress quietly.

        The generator used to composite the byline, the title, the rule and the
        subtitle into the file, which is why it could only ever set them in a
        font the device already had — an `<img>`-rendered SVG cannot reach the
        page's webfonts, so every cover in the library came out in Georgia. A
        stray `<text>` node here would put a second, worse-set title under the
        one `BookCover` draws, in the wrong language on seven locales out of
        eight.
        """
        from library.covers import build_ground

        svg = build_ground("#8a4b1f", "praying-hands")
        self.assertNotIn("<text", svg)
        self.assertNotIn("font-family", svg)


class CuratedArtFetchTests(SimpleTestCase):
    """A half-downloaded painting must not be mistaken for a whole one.

    `build_curated_covers` caches museum originals under `.cache/` and decides
    it already has one with `raw.exists()` — nothing downstream re-reads the
    bytes. So a transfer that dies mid-stream used to leave a truncated JPEG
    that every later run accepted as the painting, cropped, and committed.

    Not hypothetical: it happened while curating this batch. The Met connection
    dropped and left a 163 KB `met-437975.orig.jpg` with no end-of-image marker,
    which the next run would have shipped as Spurgeon's cover.
    """

    def test_an_interrupted_download_leaves_no_file_behind(self):
        from library.management.commands import build_curated_covers as cmd

        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "painting.orig.jpg"

            # A response that yields some bytes and then dies, which is what a
            # dropped connection looks like from up here.
            def die_partway(src, dst, *a, **kw):
                dst.write(b"\xff\xd8" + b"x" * 4096)
                raise BrokenPipeError(32, "Broken pipe")

            with (
                mock.patch.object(cmd.urllib.request, "urlopen", mock.MagicMock()),
                mock.patch.object(cmd.shutil, "copyfileobj", die_partway),
            ):
                with self.assertRaises(BrokenPipeError):
                    cmd._fetch("https://example.invalid/x.jpg", dest)

            # Nothing at all: not the truncated download the cache would trust
            # as the finished painting, and not the `.part` scratch either.
            self.assertEqual(
                [q.name for q in Path(td).iterdir()],
                [],
                "an interrupted download left a file behind",
            )


class CuratedArtTests(TestCase):
    """Guards on the curated-artwork manifest (library/curated_art.py)."""

    def test_susanna_wesley_biography_wears_a_landscape_not_a_portrait(self):
        """A biography's cover must never be a portrait: a face reads as a
        likeness OF the subject, and every period candidate was a DIFFERENT
        real woman. Susanna Wesley was long left on a plate for exactly that
        reason; she now wears a wordless landscape (Hobbema), which claims no
        likeness. Guard the KIND of art, not her absence — swap her to a
        portrait and this fails. (The manifest-wide grep in
        test_no_curated_cover_is_a_portrait_of_its_subject backs this up.)"""
        from library.curated_art import CURATED

        art = CURATED.get("susanna-wesley-clarke")
        self.assertIsNotNone(art, "Susanna Wesley's biography should wear curated art")
        self.assertNotIn("portrait", art.title.lower())

    def test_every_entry_records_its_provenance_and_reason(self):
        # BOTH curated tiers. `CURATED_GROUND` carries the same museum object
        # under the same licence and is shown to readers the same way; the only
        # difference is which editions wear it. An entry there with no receipt
        # is the same defect, so it is the same gate.
        from library.curated_art import CURATED, CURATED_GROUND, SOURCES

        for slug, art in {**CURATED, **CURATED_GROUND}.items():
            with self.subTest(slug=slug):
                # The id is only meaningful with the collection it belongs to —
                # two museums number their objects independently.
                self.assertIn(art.source, SOURCES, "unknown collection")
                self.assertGreater(art.object_id, 0, "needs an object id as the licence receipt")
                self.assertTrue(art.artist.strip())
                self.assertTrue(art.title.strip())
                # `why` is not decoration: it's what stops the next person
                # swapping in a prettier painting that means nothing.
                self.assertTrue(art.why.strip())
                # A focus outside 0..1 asks for a window off the edge of the
                # picture. Pillow's `crop` does not raise on that — it pads with
                # black — so the cover would ship with a bar down one side and
                # nothing anywhere would have failed.
                self.assertGreaterEqual(art.focus, 0.0, "focus is a fraction of the overflow")
                self.assertLessEqual(art.focus, 1.0, "focus is a fraction of the overflow")

    def test_focus_moves_the_crop_window_along_the_overflowing_axis(self):
        """`focus` has to change PIXELS, not just be stored.

        The crop is the one place a curated painting is decided, and it reads
        `focus` through two layers — the manifest entry, then the cache key. Get
        either wrong and the value is inert: the entry keeps its number, the
        command reports success, and every cover is still a centre crop. That is
        a defect with no symptom, so this asserts the thing itself by cropping a
        picture whose left and right halves differ and reading the result back.
        """
        from PIL import Image

        from library.management.commands.build_curated_covers import CACHE, _crop_3x4

        CACHE.mkdir(parents=True, exist_ok=True)
        # Twice as wide as 3:4 needs, so a third of the width is thrown away and
        # the two ends are far apart. Left half red, right half blue.
        source = Image.new("RGB", (2400, 800), (200, 40, 40))
        source.paste(Image.new("RGB", (1200, 800), (40, 40, 200)), (1200, 0))
        written = []
        try:
            with tempfile.TemporaryDirectory() as td:
                src = Path(td) / "s.png"
                source.save(src)
                seen = {}
                for focus in (0.0, 0.5, 1.0):
                    out = _crop_3x4(src, "focus-selftest", focus)
                    written.append(out)
                    with Image.open(out) as im:
                        self.assertEqual(im.size, (600, 800))
                        seen[focus] = im.getpixel((300, 400))
            # Left edge is in the red half, right edge in the blue half. The
            # centre sits on the seam, so it is asserted only to differ from the
            # ends rather than to be a particular colour.
            self.assertGreater(seen[0.0][0], seen[0.0][2], "focus=0 should take the LEFT (red) end")
            self.assertGreater(seen[1.0][2], seen[1.0][0], "focus=1 should take the RIGHT (blue) end")
            self.assertNotEqual(seen[0.0], seen[1.0], "focus changed nothing at all")
        finally:
            for path in written:
                path.unlink(missing_ok=True)

    def test_every_source_can_actually_be_fetched(self):
        """A source in the manifest with no fetcher is a build that dies on a
        re-run, months after the entry was added and by someone else."""
        from library.curated_art import CURATED, CURATED_GROUND
        from library.management.commands.build_curated_covers import FETCHERS

        for slug, art in {**CURATED, **CURATED_GROUND}.items():
            with self.subTest(slug=slug):
                self.assertIn(art.source, FETCHERS, f"no fetcher for {art.source!r}")

    def test_no_painting_is_given_to_two_works(self):
        """One museum object, one work. A painting is chosen for what it says
        about ONE book, and two books wearing it read as the same book on a
        shelf. It happened once and stood unnoticed for weeks: #1771 gave
        `spurgeon-on-prayer` the Achenbach `till-he-come` had worn since #1027,
        on the same author's shelf, and every gate stayed green."""
        from library.curated_art import CURATED, CURATED_GROUND

        seen: dict[tuple[str, int], str] = {}
        for slug, art in {**CURATED, **CURATED_GROUND}.items():
            key = (art.source, art.object_id)
            with self.subTest(slug=slug):
                self.assertIsNone(
                    seen.get(key),
                    f"{art.source} {art.object_id} ({art.title}) is already "
                    f"`{seen.get(key)}`'s painting — pick another",
                )
            seen.setdefault(key, slug)


    def test_the_three_cover_tiers_answer_the_two_questions_differently(self):
        """The tier predicates, exercised on a member of each.

        Written when `CURATED_GROUND` was still empty, and it stays patched
        rather than reaching for a real member now that it has two: what is
        being tested is the PREDICATES, and a test that names a live slug goes
        quietly vacuous the day someone moves that work to another tier — which
        is exactly what happened to the `DERIVED_GROUND` row below when
        `the-inner-chamber` left it.

        The answers are the tier, stated as a truth table:

            tier             shares a ground   English keeps its designed cover
            CURATED                yes                      no
            DERIVED_GROUND         yes                      yes
            CURATED_GROUND         yes                      yes
            (none of them)         no                       no

        Row three is the new one, and it is deliberately identical to row two:
        where the ground CAME FROM is the registries' business, not these
        predicates'. If those two rows ever stop matching, one of the five call
        sites is treating a painting differently from a crop for a reason that
        does not exist.
        """
        from unittest.mock import patch

        from library.covers import keeps_english_designed, shares_a_ground
        from library.curated_art import CURATED_GROUND, Artwork

        art = Artwork("met", 1, "A Painter", "A Painting", "1650", "because")
        with patch.dict(CURATED_GROUND, {"a-designed-work": art}, clear=True):
            for slug, shared, keeps in (
                ("waiting-on-god", True, False),        # CURATED
                ("humility-2", True, True),             # DERIVED_GROUND
                ("a-designed-work", True, True),        # CURATED_GROUND
                ("a-work-in-no-tier-at-all", False, False),
            ):
                with self.subTest(slug=slug):
                    self.assertIs(shares_a_ground(slug), shared)
                    self.assertIs(keeps_english_designed(slug), keeps)

    def test_credit_names_the_artist_and_the_source(self):
        from library.curated_art import credit

        c = credit("confessions")
        self.assertIn("Géricault", c)
        self.assertIn("Metropolitan Museum", c)
        self.assertIsNone(credit("a-book-with-no-curated-art"))

        # A painting used as a GROUND is credited too — same museum object,
        # same licence, same reader looking at it. The serializer is what keeps
        # the credit off the English edition, which wears its designed cover:
        # it asks only for editions whose cover_url is under /covers/art/.
        from unittest.mock import patch

        from library.curated_art import CURATED_GROUND, Artwork

        art = Artwork("met", 1, "Jan van Goyen", "A River", "1646", "because")
        with patch.dict(CURATED_GROUND, {"a-designed-work": art}, clear=True):
            g = credit("a-designed-work")
            self.assertIn("van Goyen", g)
            self.assertIn("Metropolitan Museum", g)

    def test_the_credit_reaches_the_reader(self):
        """The book detail API must actually SERVE the credit.

        It used to live in the composited SVG's `<desc>`, where nothing
        surfaced it; the painting is now a plain image with the type drawn over
        it in HTML, so the API is the only route left. A `get_artwork_credit`
        method with no field declared beside it computes a value DRF never
        emits — which is exactly what shipped for a moment here, and no test
        would have noticed.
        """
        from library.serializers import BookDetailSerializer

        self.assertIn("artwork_credit", BookDetailSerializer.Meta.fields)
        author = Author.objects.create(slug="augustine", name="Augustine of Hippo")
        painted = Book.objects.create(
            slug="confessions", language="en", title="Confessions", author=author,
            cover_url="/covers/art/confessions.jpg",
        )
        self.assertIn("Géricault", BookDetailSerializer(painted).data["artwork_credit"])

        plain = Book.objects.create(
            slug="a-book-with-no-curated-art", language="en", title="Plain", author=author,
            cover_url="/covers/plain.jpg",
        )
        self.assertIsNone(BookDetailSerializer(plain).data["artwork_credit"])

        # The manifest lists the WORK, but an edition may carry designed artwork
        # of its own — the per-language gate deliberately allows it. Crediting a
        # painter for a cover this reader isn't looking at is worse than saying
        # nothing.
        own_cover = Book.objects.create(
            slug="confessions", language="es", title="Confesiones", author=author,
            cover_url="/covers/es/confessions.jpg",
        )
        self.assertIsNone(BookDetailSerializer(own_cover).data["artwork_credit"])


class CuratedCoversSurviveForceTests(TestCase):
    """`generate_covers --force` must not redraw the curated artwork.

    This is a real regression, observed in production on 2026-08-02: a --force
    run listed pilgrims-progress, the-reformed-pastor, waiting-on-god and the
    rest and rewrote them as plain typographic plates. It did no harm THERE
    (throwaway container, and cover_url was unchanged) — but the same command
    on a developer's machine overwrites the committed artwork, and the loss is
    committable without anyone noticing, because the file still exists and the
    page still renders.

    is_generated() cannot catch this on its own: curated covers are .svg too.
    """

    def setUp(self):
        self.author = Author.objects.create(slug="jb", name="John Bunyan")

    def test_a_curated_slug_is_skipped_even_with_force(self):


        from library.curated_art import CURATED

        slug = "pilgrims-progress"
        self.assertIn(slug, CURATED, "fixture assumes this slug is curated")
        Book.objects.create(
            slug=slug, language="en", title="The Pilgrim's Progress",
            author=self.author, cover_url=f"/covers/{slug}.svg", cover_color="#6b4b2a",
        )
        out = StringIO()
        call_command("generate_covers", "--force", "--dry-run", stdout=out)
        report = out.getvalue()
        self.assertNotIn(f"{slug}.svg", report, "curated cover was redrawn by --force")
        self.assertIn("kept 1 shared-ground", report)

    def test_a_derived_slug_is_skipped_too(self):
        """The same guard, for the other tier that wears a shared ground.

        A freshly translated derived edition is the case this protects. It
        arrives from `translate_book` carrying the dangling
        `/covers/<lang>/<slug>.svg` that command writes — `is_generated` is True
        for it — and `translate_book`'s own comment recommends running
        `generate_covers <slug>` next. Without the guard that draws the flat
        coloured plate the derived tier exists to replace, and commits an SVG
        that then hard-exits `build_cover_assets`.
        """


        from library.designed_covers import DERIVED_GROUND

        slug = "godliness"
        self.assertIn(slug, DERIVED_GROUND, "fixture assumes this slug is derived")
        Book.objects.create(
            slug=slug, language="sw", title="Utauwa",
            author=self.author, cover_url=f"/covers/sw/{slug}.svg", cover_color="#634836",
        )
        out = StringIO()
        call_command("generate_covers", "--force", "--dry-run", stdout=out)
        report = out.getvalue()
        self.assertNotIn(f"{slug}.svg", report, "derived edition was given a plate")
        self.assertIn("kept 1 shared-ground", report)

    def test_an_uncurated_slug_is_still_redrawn(self):
        """The guard must not turn --force into a no-op for everything else."""


        from library.curated_art import CURATED

        # A slug this test INVENTS, rather than a real uncurated book. It used
        # to name `till-he-come`, which was a fine example right up until that
        # book was given a painting — at which point the test was asserting the
        # opposite of what it means, and failed for a reason that had nothing to
        # do with the guard it exists to check. Curating another book must not
        # be able to break this again.
        slug = "a-book-nobody-has-curated"
        self.assertNotIn(slug, CURATED)
        Book.objects.create(
            slug=slug, language="en", title="Uncurated",
            author=self.author, cover_url=f"/covers/{slug}.svg", cover_color="#333",
        )
        out = StringIO()
        call_command("generate_covers", "--force", "--dry-run", stdout=out)
        self.assertIn(f"{slug}.svg", out.getvalue())
