"""The AI translation pipeline and its commands: translating a sermon or a topic,
the contemporize passes, the preflight that runs before any of it, the review
approval that has to survive a rebuild, and the job queue that files the work.

The Anthropic client is stubbed here (the `_Fake*` classes) rather than reached
over the network, and the Bible API with it. That is not only about speed: the
preflight treats an unresolvable Bible code as fatal, so a test that let it
reach a real API would fail for the wrong reason the day the API moved."""

import json
import shutil
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock
from unittest.mock import patch  # noqa: E402

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .languages import config as language_config
from .models import (
    Article,
    Author,
    Book,
    Chapter,
    Language,
    Plan,
    Sermon,
    Topic,
    TopicTranslation,
)
from .translation import (
    missing_glossary_terms,
    verify_bible_code,
    verify_glossary,
)


class _FakeUsage:
    input_tokens = 120
    output_tokens = 240


class _FakeBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _FakeMessage:
    def __init__(self, text):
        self.content = [_FakeBlock(text)]
        self.usage = _FakeUsage()


class _FakeStream:
    def __init__(self, message):
        self._message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._message


class _FakeMessages:
    """Stands in for anthropic client.messages — stream() for the body,
    create() for the structured scripture-ref call."""

    def stream(self, **kwargs):
        return _FakeStream(
            _FakeMessage(
                "<chapter_title>El Nuevo Nacimiento</chapter_title>"
                "<chapter_body><p>Debéis nacer de nuevo.</p></chapter_body>"
            )
        )

    def create(self, **kwargs):
        return _FakeMessage('{"reference": "Juan 3:3"}')


class _FakeClient:
    def __init__(self, *a, **k):
        self.messages = _FakeMessages()


class _FakeModernMessages:
    """Stands in for the client used by the contemporize careful pass: returns a
    modernized chapter in the same <chapter_title>/<chapter_body> wrapper."""

    def stream(self, **kwargs):
        return _FakeStream(
            _FakeMessage(
                "<chapter_title>Of Humility</chapter_title>"
                "<chapter_body><p>You must be born again.</p></chapter_body>"
            )
        )


class _FakeModernClient:
    def __init__(self, *a, **k):
        self.messages = _FakeModernMessages()


# No Bible API network. Returns a minimal valid chapter rather than None: the
# translate_* preflight (verify_bible_code) treats an unresolvable code as fatal,
# and these tests exercise the translation flow, not a broken configuration.
@patch(
    "library.translation.fetch_chapter",
    return_value={"reference": "John 3", "verses": [{"number": 3, "text": "…"}]},
)
@patch(
    "library.management.commands._translate_base.anthropic.Anthropic",
    new=_FakeClient,
)
class SermonTranslationTests(TestCase):
    def setUp(self):
        from django.core.management import call_command  # noqa: F401

        self.author = Author.objects.create(slug="cs", name="Charles Spurgeon")
        self.source = Sermon.objects.create(
            author=self.author,
            slug="the-new-birth",
            language="en",
            title="The New Birth",
            scripture_ref="John 3:3",
            body_html="<p>You must be born again.</p>",
            sort_order=4,
        )

    def _translate(self, language="es"):
        from django.core.management import call_command

        call_command("translate_sermon", "the-new-birth", language=language)

    def test_creates_ai_unreviewed_translation(self, _fetch):
        self._translate("es")
        s = Sermon.objects.get(slug="the-new-birth", language="es")
        self.assertEqual(s.source_type, "ai_unreviewed")
        self.assertEqual(s.title, "El Nuevo Nacimiento")
        self.assertIn("Debéis nacer de nuevo", s.body_html)
        self.assertEqual(s.scripture_ref, "Juan 3:3")
        self.assertEqual(s.author, self.author)
        self.assertEqual(s.sort_order, 4)
        self.assertTrue(s.is_published)

    def test_derives_body_text_and_word_count(self, _fetch):
        self._translate("es")
        s = Sermon.objects.get(slug="the-new-birth", language="es")
        self.assertEqual(s.body_text, "Debéis nacer de nuevo.")
        self.assertGreater(s.word_count, 0)

    def test_idempotent_without_force(self, _fetch):
        self._translate("es")
        self._translate("es")  # second run should skip, not duplicate
        self.assertEqual(
            Sermon.objects.filter(slug="the-new-birth", language="es").count(), 1
        )

    def test_unknown_slug_errors(self, _fetch):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("translate_sermon", "nope", language="es")

    def test_approve_flips_to_reviewed(self, _fetch):
        from django.core.management import call_command

        self._translate("es")
        call_command("approve_sermon_translation", "the-new-birth", language="es", no_fixture=True)
        s = Sermon.objects.get(slug="the-new-birth", language="es")
        self.assertEqual(s.source_type, "ai_reviewed")

    def test_approve_rejects_public_domain_original(self, _fetch):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("approve_sermon_translation", "the-new-birth", language="en", no_fixture=True)


class AdminTranslationJobsTests(TestCase):
    """The admin translation queue: buttons → GitHub issues (mocked GitHub)."""

    @classmethod
    def setUpTestData(cls):
        author = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        Book.objects.create(
            author=author, slug="humility", language="en", title="Humility"
        )
        Book.objects.create(
            author=author,
            slug="the-inner-chamber",
            language="en",
            title="The Inner Chamber",
        )
        Book.objects.create(
            author=author,
            slug="the-inner-chamber",
            language="lg",
            title="Ekisenge Eky'omunda",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Sermon.objects.create(
            author=author, slug="himself", language="en", title="Himself",
            body_html="<p>x</p>",
        )
        # An English plan and an author with a long-form bio, so plan/bio jobs
        # have real English sources to resolve against.
        Plan.objects.create(slug="humility-12-days", language="en", title="Humility in 12 Days")
        author.bio_html = "<p>A long-form biography.</p>"
        author.save(update_fields=["bio_html"])

    def setUp(self):
        self.client = APIClient()

    @staticmethod
    def _issue(title, labels=("translation-job",), number=7):
        return {
            "title": title,
            "labels": [{"name": name} for name in labels],
            "html_url": f"https://github.com/o/r/issues/{number}",
            "number": number,
            "created_at": "2026-07-16T00:00:00Z",
        }

    @override_settings(DEBUG=True)
    def test_get_unconfigured(self):
        res = self.client.get("/api/admin/translation-jobs/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, {"configured": False, "jobs": []})

    @override_settings(DEBUG=True)
    def test_post_unconfigured_is_503(self):
        res = self.client.post(
            "/api/admin/translation-jobs/",
            {"type": "book", "slug": "humility", "language": "lg"},
            format="json",
        )
        self.assertEqual(res.status_code, 503)

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_validation(self):
        from unittest.mock import patch

        cases = [
            ({"type": "essay", "slug": "humility", "language": "lg"}, 400),  # unknown type
            ({"type": "book", "slug": "humility", "language": "en"}, 400),  # source language
            ({"type": "book", "slug": "humility", "language": "xx"}, 400),  # unknown code
            ({"type": "book", "slug": "nope", "language": "lg"}, 404),  # no English source
            ({"type": "book", "slug": "the-inner-chamber", "language": "lg"}, 409),  # exists
            ({"type": "plan", "slug": "nope", "language": "lg"}, 404),  # no English plan
            ({"type": "bio", "slug": "nope", "language": "lg"}, 404),  # no author with a bio
            ({"type": "topic", "slug": "nope", "language": "lg"}, 404),  # no such shelf
        ]
        with patch("library.admin_views.jobs.requests"):
            for body, expected in cases:
                res = self.client.post("/api/admin/translation-jobs/", body, format="json")
                self.assertEqual(res.status_code, expected, body)

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_refuses_a_copyright_blocked_book(self):
        # grace-for-grace-2 was queued in eight languages on 2026-09-24 and three
        # translations of the protected English shipped live. No issue is filed.
        from unittest.mock import patch

        with patch("library.admin_views.jobs.requests") as gh:
            res = self.client.post(
                "/api/admin/translation-jobs/",
                {"type": "book", "slug": "grace-for-grace-2", "language": "es"},
                format="json",
            )
        self.assertEqual(res.status_code, 451)
        gh.post.assert_not_called()

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_creates_issue(self):
        from unittest.mock import MagicMock, patch

        with patch("library.admin_views.jobs.requests") as gh:
            gh.get.return_value = MagicMock(json=lambda: [], raise_for_status=lambda: None)
            created = self._issue("[translation] book:humility -> lg")
            gh.post.return_value = MagicMock(
                json=lambda: created, raise_for_status=lambda: None
            )
            res = self.client.post(
                "/api/admin/translation-jobs/",
                {"type": "book", "slug": "humility", "language": "lg"},
                format="json",
            )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["created"])
        self.assertEqual(res.data["job"]["slug"], "humility")
        self.assertEqual(res.data["job"]["state"], "queued")
        # The issue was filed with the deterministic title + queue label.
        payload = gh.post.call_args.kwargs["json"]
        self.assertEqual(payload["title"], "[translation] book:humility -> lg")
        self.assertEqual(payload["labels"], ["translation-job"])
        self.assertIn("Humility", payload["body"])

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_creates_plan_and_bio_issues(self):
        from unittest.mock import MagicMock, patch

        for type_, slug, marker in (
            ("plan", "humility-12-days", "Humility in 12 Days"),
            ("bio", "andrew-murray", "Andrew Murray"),
        ):
            title = f"[translation] {type_}:{slug} -> lg"
            with patch("library.admin_views.jobs.requests") as gh:
                gh.get.return_value = MagicMock(json=lambda: [], raise_for_status=lambda: None)
                gh.post.return_value = MagicMock(
                    json=lambda t=title: self._issue(t), raise_for_status=lambda: None
                )
                res = self.client.post(
                    "/api/admin/translation-jobs/",
                    {"type": type_, "slug": slug, "language": "lg"},
                    format="json",
                )
            self.assertEqual(res.status_code, 201, type_)
            self.assertEqual(res.data["job"]["type"], type_)
            payload = gh.post.call_args.kwargs["json"]
            self.assertEqual(payload["title"], title)
            self.assertIn(marker, payload["body"])

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_duplicate_returns_existing(self):
        from unittest.mock import MagicMock, patch

        existing = self._issue("[translation] book:humility -> lg")
        with patch("library.admin_views.jobs.requests") as gh:
            gh.get.return_value = MagicMock(
                json=lambda: [existing], raise_for_status=lambda: None
            )
            res = self.client.post(
                "/api/admin/translation-jobs/",
                {"type": "book", "slug": "humility", "language": "lg"},
                format="json",
            )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["created"])
        gh.post.assert_not_called()

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_duplicate_is_caught_past_the_first_page(self):
        """The guard has to read the whole queue, not the first hundred of it.

        `direction: asc` makes page one the OLDEST hundred open jobs, so once
        the queue passed 100 the newest job — the one a second press is about
        to re-file — was the one the guard could not see. On 2026-09-06 that
        put 31 issues on the board for 17 distinct jobs.
        """
        from unittest.mock import MagicMock, patch

        full_page = [
            self._issue(f"[translation] book:filler-{i} -> lg", number=1000 + i)
            for i in range(100)
        ]
        existing = self._issue("[translation] book:humility -> lg", number=2000)
        pages = [full_page, [existing]]
        with patch("library.admin_views.jobs.requests") as gh:
            gh.get.side_effect = [
                MagicMock(json=lambda page=page: page, raise_for_status=lambda: None)
                for page in pages
            ]
            res = self.client.post(
                "/api/admin/translation-jobs/",
                {"type": "book", "slug": "humility", "language": "lg"},
                format="json",
            )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["created"])
        self.assertEqual(res.data["job"]["number"], 2000)
        # Both pages read, and nothing filed.
        self.assertEqual(gh.get.call_count, 2)
        gh.post.assert_not_called()

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_get_lists_jobs_with_state(self):
        from unittest.mock import MagicMock, patch

        issues = [
            self._issue("[translation] book:humility -> lg"),
            self._issue(
                "[translation] sermon:himself -> sw",
                labels=("translation-job", "in-progress"),
                number=8,
            ),
            self._issue("unrelated issue", number=9),  # ignored: not a job title
        ]
        with patch("library.admin_views.jobs.requests") as gh:
            gh.get.return_value = MagicMock(
                json=lambda: issues, raise_for_status=lambda: None
            )
            res = self.client.get("/api/admin/translation-jobs/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["configured"])
        self.assertEqual(len(res.data["jobs"]), 2)
        self.assertEqual(res.data["jobs"][0]["state"], "queued")
        self.assertEqual(res.data["jobs"][1]["state"], "in_progress")

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/translation-jobs/")
        self.assertIn(res.status_code, (401, 403))


class ContemporizeLightTests(TestCase):
    """The deterministic light modernization pass (no model, no key)."""

    def test_pronoun_and_verb_phrases(self):
        from library.contemporize import modernize_light

        self.assertEqual(modernize_light("Thou art mine."), "You are mine.")
        self.assertEqual(modernize_light("What hast thou done?"), "What have you done?")
        self.assertEqual(
            modernize_light("He hath spoken; he cometh."), "He has spoken; he comes."
        )
        self.assertEqual(modernize_light("shew me thy ways"), "show me your ways")

    def test_case_is_preserved(self):
        from library.contemporize import modernize_light

        self.assertEqual(modernize_light("Thou knowest"), "You know")
        self.assertEqual(modernize_light("thou knowest"), "you know")

    def test_unlisted_words_and_html_untouched(self):
        from library.contemporize import modernize_light

        # A modern homograph ("art" the noun) and the HTML tags must survive.
        self.assertEqual(
            modernize_light("<p>the fine art of prayer</p>"),
            "<p>the fine art of prayer</p>",
        )
        self.assertEqual(modernize_light("<em>God is love</em>"), "<em>God is love</em>")


class ContemporizeCommandTests(TestCase):
    """The light-mode command end to end: creates an en-modern edition."""

    def setUp(self):
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=self.author,
            slug="humility",
            language="en",
            title="Humility",
            source_type=Book.SourceType.PUBLIC_DOMAIN,
            sort_order=3,
        )
        Chapter.objects.create(
            book=self.book,
            order=1,
            title="Thou Art Called",
            body_html="<p>Thou hast been called; walk thou humbly.</p>",
        )

    def _run(self, **kw):
        from django.core.management import call_command

        call_command("contemporize_book", "humility", **kw)

    def test_light_creates_modern_edition(self):
        self._run()  # default mode is light
        mb = Book.objects.get(slug="humility", language="en-modern")
        self.assertEqual(mb.source_type, "ai_unreviewed")
        self.assertEqual(mb.author, self.author)
        ch = mb.chapters.get(order=1)
        self.assertIn("You have been called", ch.body_html)
        self.assertNotIn("Thou", ch.body_html)
        self.assertNotIn("Thou", ch.title)
        self.assertIn("You are", ch.title)
        self.assertGreater(ch.word_count, 0)
        self.assertTrue(ch.body_text)  # derived on save

    def test_original_english_is_untouched(self):
        self._run()
        en = Chapter.objects.get(
            book__slug="humility", book__language="en", order=1
        )
        self.assertIn("Thou hast", en.body_html)

    def test_idempotent_without_force(self):
        self._run()
        self._run()
        self.assertEqual(
            Book.objects.filter(slug="humility", language="en-modern").count(), 1
        )
        self.assertEqual(
            Chapter.objects.filter(
                book__slug="humility", book__language="en-modern"
            ).count(),
            1,
        )

    def test_rejects_non_public_domain_source(self):
        from django.core.management.base import CommandError

        self.book.source_type = Book.SourceType.AI_UNREVIEWED
        self.book.save(update_fields=["source_type"])
        with self.assertRaises(CommandError):
            self._run()

    def test_approve_flips_modern_edition_to_reviewed(self):
        from django.core.management import call_command

        self._run()
        call_command("approve_translation", "humility", language="en-modern", no_fixture=True)
        mb = Book.objects.get(slug="humility", language="en-modern")
        self.assertEqual(mb.source_type, "ai_reviewed")

    def test_new_chapters_regate_an_approved_edition(self):
        # Approve the modern edition, then add a chapter to the English source
        # and re-run: the new chapter is unreviewed AI text, so the edition must
        # drop back to ai_unreviewed rather than silently staying "approved".
        from django.core.management import call_command

        self._run()
        call_command("approve_translation", "humility", language="en-modern", no_fixture=True)
        Chapter.objects.create(
            book=self.book,
            order=2,
            title="A Second Call",
            body_html="<p>Thou shalt walk humbly still.</p>",
        )

        self._run()  # no --force; only the new chapter 2 is contemporized

        mb = Book.objects.get(slug="humility", language="en-modern")
        self.assertEqual(mb.source_type, "ai_unreviewed")
        self.assertEqual(mb.chapters.count(), 2)

    def test_no_regate_when_nothing_new_is_translated(self):
        # Re-running with no new chapters must NOT walk back an approval.
        from django.core.management import call_command

        self._run()
        call_command("approve_translation", "humility", language="en-modern", no_fixture=True)
        self._run()  # nothing to do — chapter 1 already exists
        mb = Book.objects.get(slug="humility", language="en-modern")
        self.assertEqual(mb.source_type, "ai_reviewed")

    def test_api_exposes_modern_edition_flags(self):
        # Before an edition exists, the English book advertises none.
        res = self.client.get("/api/library/books/humility/?language=en")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["has_modern_edition"])
        self.assertFalse(res.data["is_modern_edition"])

        # After contemporizing, the English book advertises it and the modern
        # row identifies itself.
        self._run()
        res = self.client.get("/api/library/books/humility/?language=en")
        self.assertTrue(res.data["has_modern_edition"])
        self.assertFalse(res.data["is_modern_edition"])

        res = self.client.get("/api/library/books/humility/?language=en-modern")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["is_modern_edition"])
        self.assertTrue(res.data["has_modern_edition"])
        # The chapter endpoint carries the same flags for the reader toggle.
        ch = self.client.get(
            "/api/library/books/humility/chapters/1/?language=en-modern"
        )
        self.assertTrue(ch.data["is_modern_edition"])


@patch(
    "library.management.commands.contemporize_book.anthropic.Anthropic",
    new=_FakeModernClient,
)
class ContemporizeCarefulTests(TestCase):
    """The model-backed careful mode, with a stubbed Anthropic client."""

    def setUp(self):
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=self.author,
            slug="humility",
            language="en",
            title="Humility",
            source_type=Book.SourceType.PUBLIC_DOMAIN,
        )
        Chapter.objects.create(
            book=self.book,
            order=1,
            title="Of Humility",
            body_html="<p>Thou must be born again.</p>",
        )

    def test_careful_uses_model_output(self):
        from django.core.management import call_command

        call_command("contemporize_book", "humility", mode="careful")
        ch = Book.objects.get(slug="humility", language="en-modern").chapters.get(order=1)
        self.assertIn("You must be born again", ch.body_html)
        self.assertEqual(ch.book.source_type, "ai_unreviewed")


class TranslationPreflightTests(TestCase):
    """The checks every translate_* command runs before spending money.

    They read the REGISTRY now, not a dict in the tree — which is what lets a
    language added from the admin be translated at all, and also means these
    tests need a database.
    """

    def test_verify_bible_code_raises_when_the_code_does_not_resolve(self):
        # Mocked so it stays hermetic — what matters is that a non-resolving
        # code RAISES rather than letting the job proceed and quietly drop all
        # scripture.
        with mock.patch("library.translation.fetch_chapter", return_value=None):
            with self.assertRaises(ValueError) as ctx:
                verify_bible_code("pt")
        self.assertIn("scripture would be silently omitted", str(ctx.exception))

    def test_verify_bible_code_passes_when_verses_come_back(self):
        with mock.patch(
            "library.translation.fetch_chapter", return_value={"verses": [{"number": 1}]}
        ):
            verify_bible_code("pt")  # must not raise

    def test_verify_glossary_raises_on_a_half_filled_glossary(self):
        lang = Language.objects.get(code="pt")
        lang.glossary = {"grace": "graça"}
        lang.save(update_fields=["glossary"])
        with self.assertRaises(ValueError) as ctx:
            verify_glossary("pt")
        self.assertIn("justification", str(ctx.exception))

    def test_verify_glossary_passes_for_a_seeded_language(self):
        verify_glossary("pt")  # must not raise

    def test_an_unknown_language_is_a_clear_error_not_a_key_error(self):
        with self.assertRaises(ValueError) as ctx:
            language_config("xx")
        self.assertIn("Unknown language", str(ctx.exception))

    def test_the_source_language_is_not_a_translation_target(self):
        with self.assertRaises(ValueError):
            language_config("en")

    def test_missing_glossary_terms_ignores_blank_values(self):
        # A term present but empty is not a term — it would render as nothing in
        # the prompt, which is the same failure as leaving it out.
        self.assertIn("grace", missing_glossary_terms({"grace": "   "}))


class TopicTranslationJobTests(TestCase):
    """The `topic` job type: queueing a shelf for translation.

    Topics were the one content type the queue couldn't express, which is why
    the es/sw/pt shelves had to be written by hand. This covers the plumbing
    that makes them queueable like everything else.
    """

    def setUp(self):
        self.client = APIClient()
        self.topic = Topic.objects.create(
            slug="prayer",
            title="On Prayer",
            description="Learning to pray.",
            scripture_ref="Jeremiah 33:3",
            scripture_text="Call unto me, and I will answer thee.",
            is_published=True,
        )

    def test_topic_is_an_accepted_job_type(self):
        from library.admin_views.jobs import _TITLE_RE, JOB_TYPES

        self.assertIn("topic", JOB_TYPES)
        # The title is the job's identity and what the worker parses, so the
        # regex has to accept the new type too — a JOB_TYPES-only change would
        # file issues the queue then couldn't read back.
        m = _TITLE_RE.match("[translation] topic:prayer -> sw")
        self.assertIsNotNone(m)
        self.assertEqual(m.groups(), ("topic", "prayer", "sw"))

    def test_resolve_source_reports_untranslated_then_translated(self):
        from library.admin_views.jobs import _resolve_source

        title, byline, exists = _resolve_source("topic", "prayer", "sw")
        self.assertIn("On Prayer", title)
        self.assertIsNone(byline)
        self.assertFalse(exists)

        # A row with a blank title does NOT count: a shelf is visible in a
        # language only once it has a title, so a titleless row is still a job.
        tr = TopicTranslation.objects.create(topic=self.topic, language="sw", title="")
        _, _, exists = _resolve_source("topic", "prayer", "sw")
        self.assertFalse(exists)

        tr.title = "Kuhusu Maombi"
        tr.save()
        _, _, exists = _resolve_source("topic", "prayer", "sw")
        self.assertTrue(exists)

    def test_resolve_source_ignores_unpublished_shelves(self):
        from library.admin_views.jobs import _resolve_source

        self.topic.is_published = False
        self.topic.save()
        self.assertIsNone(_resolve_source("topic", "prayer", "sw"))


class ArticleTranslationJobTests(TestCase):
    """The `article` job type: queueing a devotional article for translation.

    Articles are authorless per-language rows (like a plan) with the headline on
    ``h1`` rather than ``title`` — this covers the plumbing that lets the queue
    express them the same way it expresses books and sermons.
    """

    def setUp(self):
        self.client = APIClient()
        self.article = Article.objects.create(
            slug="what-is-grace",
            language="en",
            h1="What Is Grace?",
            body_html="<p>Grace is unmerited favour.</p>",
            is_published=True,
        )

    def test_article_is_an_accepted_job_type(self):
        from library.admin_views.jobs import _TITLE_RE, JOB_TYPES

        self.assertIn("article", JOB_TYPES)
        m = _TITLE_RE.match("[translation] article:what-is-grace -> es")
        self.assertIsNotNone(m)
        self.assertEqual(m.groups(), ("article", "what-is-grace", "es"))

    def test_resolve_source_reports_untranslated_then_translated(self):
        from library.admin_views.jobs import _resolve_source

        title, byline, exists = _resolve_source("article", "what-is-grace", "es")
        self.assertEqual(title, "What Is Grace?")
        # Authorless, like a plan.
        self.assertIsNone(byline)
        self.assertFalse(exists)

        Article.objects.create(
            slug="what-is-grace",
            language="es",
            h1="¿Qué es la gracia?",
            body_html="<p>La gracia es el favor inmerecido.</p>",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        _, _, exists = _resolve_source("article", "what-is-grace", "es")
        self.assertTrue(exists)

    def test_resolve_source_is_none_for_an_unknown_slug(self):
        from library.admin_views.jobs import _resolve_source

        self.assertIsNone(_resolve_source("article", "no-such-article", "es"))


class TranslateTopicCommandTests(TestCase):
    """`translate_topic` — the pipeline behind the queue's `topic` job."""

    def setUp(self):
        self.topic = Topic.objects.create(
            slug="prayer",
            title="On Prayer",
            description="Learning to pray.",
            scripture_ref="Jeremiah 33:3",
            scripture_text="Call unto me, and I will answer thee.",
            is_published=True,
        )

    def _run(self, *args, **kwargs):
        # The command WRITES data/topic_translations/<lang>.json (that file is
        # the delivery path), so every run is pointed at a throwaway dir — a
        # test that touched the real repo data would pollute the working tree.
        out = StringIO()
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        self.written_dir = tmp
        with mock.patch("library.topic_translations.DATA_DIR", tmp):
            call_command("translate_topic", *args, stdout=out, stderr=out, **kwargs)
        return out.getvalue()

    def test_dry_run_touches_nothing(self):
        out = self._run("--language", "sw", "--dry-run")
        self.assertIn("prayer", out)
        self.assertFalse(TopicTranslation.objects.exists())

    def test_translates_title_and_description_and_writes_the_language_file(self):
        meta = {"title": "Kuhusu Maombi", "description": "Kujifunza kuomba."}
        with mock.patch("library.management.commands._translate_base.verify_bible_code"), \
             mock.patch("library.management.commands._translate_base.anthropic"), \
             mock.patch(
                 "library.management.commands.translate_topic.translate_topic_meta",
                 return_value=meta,
             ):
            out = self._run("--language", "sw")

        tr = TopicTranslation.objects.get(topic=self.topic, language="sw")
        self.assertEqual(tr.title, "Kuhusu Maombi")
        self.assertEqual(tr.description, "Kujifunza kuomba.")
        # Scripture is opt-in, so it stays empty on a prose-only run.
        self.assertEqual(tr.scripture_text, "")
        # The shelf is now visible in Swahili — the whole point.
        self.assertTrue(self.topic.is_translated_into("sw"))
        # And the delivery file was written — it, not the DB row, is what
        # survives a deploy — with the translated prose in it.
        written = json.loads((self.written_dir / "sw.json").read_text(encoding="utf-8"))
        self.assertEqual(written["prayer"]["title"], "Kuhusu Maombi")
        self.assertEqual(written["prayer"]["description"], "Kujifunza kuomba.")
        self.assertNotIn("scripture", written["prayer"])  # prose-only run
        self.assertIn("sw.json", out)

    def test_scripture_uses_the_bible_and_never_the_model(self):
        meta = {"title": "Kuhusu Maombi", "description": "d"}
        with mock.patch("library.management.commands._translate_base.verify_bible_code"), \
             mock.patch("library.management.commands._translate_base.anthropic"), \
             mock.patch(
                 "library.management.commands.translate_topic.translate_topic_meta",
                 return_value=meta,
             ), \
             mock.patch(
                 "library.management.commands.translate_topic.fetch_verse_text",
                 return_value="Niite, nami nitakujibu.",
             ), \
             mock.patch(
                 "library.management.commands.translate_topic.translate_scripture_ref",
                 return_value="Yeremia 33:3",
             ):
            self._run("--language", "sw", "--scripture")

        tr = TopicTranslation.objects.get(topic=self.topic, language="sw")
        self.assertEqual(tr.scripture_text, "Niite, nami nitakujibu.")
        self.assertEqual(tr.scripture_ref, "Yeremia 33:3")

    def test_unfetchable_verse_ships_empty_rather_than_paraphrased(self):
        meta = {"title": "Kuhusu Maombi", "description": "d"}
        with mock.patch("library.management.commands._translate_base.verify_bible_code"), \
             mock.patch("library.management.commands._translate_base.anthropic"), \
             mock.patch(
                 "library.management.commands.translate_topic.translate_topic_meta",
                 return_value=meta,
             ), \
             mock.patch(
                 "library.management.commands.translate_topic.fetch_verse_text",
                 return_value="",
             ) , \
             mock.patch(
                 "library.management.commands.translate_topic.translate_scripture_ref"
             ) as ref:
            out = self._run("--language", "sw", "--scripture")

        tr = TopicTranslation.objects.get(topic=self.topic, language="sw")
        self.assertEqual(tr.scripture_text, "")
        # The reference isn't translated either — a citation with no text under
        # it is worse than none, and the model is never asked to supply wording.
        ref.assert_not_called()
        self.assertIn("without a verse", out)

    def test_already_translated_is_skipped_unless_forced(self):
        TopicTranslation.objects.create(
            topic=self.topic, language="sw", title="Kuhusu Maombi", description="d"
        )
        with mock.patch(
            "library.management.commands.translate_topic.translate_topic_meta"
        ) as meta:
            self._run("--language", "sw")
            meta.assert_not_called()

        with mock.patch("library.management.commands._translate_base.verify_bible_code"), \
             mock.patch("library.management.commands._translate_base.anthropic"), \
             mock.patch(
                 "library.management.commands.translate_topic.translate_topic_meta",
                 return_value={"title": "Mpya", "description": "mpya"},
             ) as meta:
            self._run("--language", "sw", "--force")
            meta.assert_called_once()
        self.assertEqual(
            TopicTranslation.objects.get(topic=self.topic, language="sw").title, "Mpya"
        )


class ApprovalDurabilityTests(TestCase):
    """An approval must be written into the committed fixture, or a fresh-DB
    rebuild (seed_if_empty loaddata) re-gates it to unreviewed (review #27)."""

    def _fixture(self, tmp, source_type="ai_unreviewed"):
        rows = [
            {
                "model": "library.book",
                "fields": {
                    "slug": "humility",
                    "language": "sw",
                    "source_type": source_type,
                    "title": "Unyenyekevu",
                },
            }
        ]
        p = Path(tmp) / "humility.sw.json"
        p.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        return p

    def test_persist_source_type_flips_and_is_idempotent(self):
        from library import content_fixtures as cf

        with tempfile.TemporaryDirectory() as tmp:
            p = self._fixture(tmp)
            self.assertTrue(cf.persist_source_type(p, "ai_reviewed"))
            self.assertIn('"source_type": "ai_reviewed"', p.read_text())
            self.assertNotIn("ai_unreviewed", p.read_text())
            self.assertFalse(cf.persist_source_type(p, "ai_reviewed"))  # no-op second time

    def test_persist_source_type_requires_exactly_one_match(self):
        from library import content_fixtures as cf

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.json"
            p.write_text('[{"model": "library.book", "fields": {"slug": "x"}}]', "utf-8")
            with self.assertRaises(ValueError):
                cf.persist_source_type(p, "ai_reviewed")

    def test_approve_translation_updates_db_and_fixture(self):
        from django.core.management import call_command

        author = Author.objects.create(slug="am", name="Andrew Murray")
        Book.objects.create(
            author=author, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = self._fixture(tmp)
            with mock.patch(
                "library.content_fixtures.book_fixture_path", return_value=p
            ):
                call_command("approve_translation", "humility", language="sw")
            self.assertIn('"source_type": "ai_reviewed"', p.read_text())
        self.assertEqual(
            Book.objects.get(slug="humility", language="sw").source_type,
            Book.SourceType.AI_REVIEWED,
        )

    def test_approve_translation_survives_a_fixture_write_failure(self):
        # The DB flip is the primary action; a fixture write error (here a
        # read-only-FS style OSError) must warn, not raise — an automated caller
        # would otherwise read the traceback as "approval failed" and retry.
        from django.core.management import call_command

        author = Author.objects.create(slug="am", name="Andrew Murray")
        Book.objects.create(
            author=author, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = self._fixture(tmp)
            with mock.patch(
                "library.content_fixtures.book_fixture_path", return_value=p
            ), mock.patch(
                "library.content_fixtures.persist_source_type",
                side_effect=OSError("read-only file system"),
            ):
                call_command("approve_translation", "humility", language="sw")  # must not raise
        self.assertEqual(
            Book.objects.get(slug="humility", language="sw").source_type,
            Book.SourceType.AI_REVIEWED,
        )
