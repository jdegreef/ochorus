"""Tests for the campaigns the system builds itself (emails/auto_emails.py): the
monthly digest and "new in your language" — when they are built, what goes in
them, per-language strictness, stream consent, the continue-reading block, and
the admin API."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from library import languages
from library.models import (
    AdminAction,
    Author,
    Book,
    Chapter,
    Language,
    Plan,
    Quote,
    Sermon,
)
from reading.models import ReadingProgress, WorkKind

from . import auto_emails
from .audience import resolve
from .broadcasts import send_broadcast
from .models import (
    AutoEmail,
    AutoEmailConfig,
    Broadcast,
    BroadcastStatus,
    EmailSubscription,
)
from .rendering import render_broadcast
from .tests import SENDING, _make_profile

# The first Monday of November 2026 is the 2nd.
NOV_ISSUE = datetime(2026, 11, 2, 9, tzinfo=UTC)


def _live(*codes):
    """Make exactly ``codes`` the live languages."""
    Language.objects.exclude(code__in=codes).update(status=Language.Status.DRAFT)
    names = {"en": ("English", "English"), "fr": ("French", "Français"), "es": ("Spanish", "Español")}
    for code in codes:
        name, native = names.get(code, (code, code))
        Language.objects.update_or_create(
            code=code, defaults={"name": name, "native_name": native, "status": Language.Status.LIVE}
        )
    languages.invalidate()


def tearDownModule():
    languages.invalidate()  # the registry cache outlives each test's rows


def _book(slug, lang, *, author, created=None, title=None):
    book = Book.objects.create(author=author, slug=slug, language=lang, title=title or slug.title())
    if created is not None:
        Book.objects.filter(pk=book.pk).update(created_at=created)
    return book


def _enable(key, *, approval=True, at=None):
    config = AutoEmailConfig.get(key)
    config.enabled = True
    config.enabled_at = at or timezone.now()
    config.require_approval = approval
    config.save()
    return config


class IssueDateTests(TestCase):
    def test_first_monday_of_the_month(self):
        self.assertEqual(auto_emails.issue_date(2026, 11), NOV_ISSUE)
        self.assertEqual(auto_emails.issue_date(2026, 6), datetime(2026, 6, 1, 9, tzinfo=UTC))

    def test_next_issue_rolls_over_after_the_send(self):
        self.assertEqual(auto_emails.next_issue(NOV_ISSUE - timedelta(days=1)), NOV_ISSUE)
        self.assertEqual(
            auto_emails.next_issue(NOV_ISSUE + timedelta(hours=1)),
            datetime(2026, 12, 7, 9, tzinfo=UTC),
        )
        self.assertEqual(
            auto_emails.next_issue(datetime(2026, 12, 20, tzinfo=UTC)),
            datetime(2027, 1, 4, 9, tzinfo=UTC),
        )


class DigestBuildTests(TestCase):
    def setUp(self):
        _live("en", "fr")
        self.murray = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        self.build_time = NOV_ISSUE - timedelta(days=2)
        _book("humility", "en", author=self.murray, created=NOV_ISSUE - timedelta(days=10))
        _book("old-book", "en", author=self.murray, created=NOV_ISSUE - timedelta(days=90))
        Plan.objects.create(slug="prayer-30", language="en", title="Thirty days of prayer")

    def test_off_until_switched_on(self):
        self.assertIsNone(auto_emails.build_digest(self.build_time))
        self.assertFalse(Broadcast.objects.exists())

    def test_not_built_before_the_lead_time(self):
        _enable(AutoEmail.DIGEST)
        self.assertIsNone(auto_emails.build_digest(NOV_ISSUE - timedelta(days=5)))

    def test_builds_a_draft_for_approval_once(self):
        _enable(AutoEmail.DIGEST)
        b = auto_emails.build_digest(self.build_time)
        self.assertIsNotNone(b)
        self.assertEqual(b.status, BroadcastStatus.DRAFT)
        self.assertEqual(b.scheduled_at, NOV_ISSUE)
        self.assertEqual(b.auto_key, "digest:2026-11")
        self.assertEqual(b.stream, "digest")
        self.assertTrue(b.strict_locale)
        # Again: nothing new.
        self.assertIsNone(auto_emails.build_digest(self.build_time + timedelta(hours=1)))
        self.assertEqual(Broadcast.objects.count(), 1)

    def test_without_approval_it_is_scheduled(self):
        _enable(AutoEmail.DIGEST, approval=False)
        b = auto_emails.build_digest(self.build_time)
        self.assertEqual(b.status, BroadcastStatus.SCHEDULED)

    def test_content_is_this_months_work_and_skips_a_language_with_nothing(self):
        _enable(AutoEmail.DIGEST)
        b = auto_emails.build_digest(self.build_time)
        # French has no work, quote or plan: no French email at all.
        self.assertEqual(sorted(b.content), ["en"])
        blocks = b.content["en"]["blocks"]
        slugs = [x.get("slug") for x in blocks if x["type"] == "book"]
        self.assertEqual(slugs, ["humility"])  # not the 90-day-old one
        self.assertIn("prayer-30", [x.get("slug") for x in blocks if x["type"] == "plan"])
        types = [x["type"] for x in blocks]
        self.assertIn("continue_reading", types)
        self.assertEqual(types[-2:], ["button", "text"])

    def test_sections_can_be_switched_off(self):
        config = _enable(AutoEmail.DIGEST)
        config.sections = {"plan": False, "continue": False, "letter": False}
        config.save()
        b = auto_emails.build_digest(self.build_time)
        types = [x["type"] for x in b.content["en"]["blocks"]]
        self.assertNotIn("plan", types)
        self.assertNotIn("continue_reading", types)

    def test_a_quote_from_the_languages_own_work(self):
        _enable(AutoEmail.DIGEST)
        book = _book("absolute-surrender", "fr", author=self.murray, created=NOV_ISSUE - timedelta(days=400))
        chapter = Chapter.objects.create(book=book, order=1, title="Un", body_html="<p>x</p>")
        Quote.objects.create(
            slug="murray-1", author=self.murray, text="Dieu attend.", chapter=chapter, paragraph=0, reviewed=True
        )
        Quote.objects.create(
            slug="murray-2", author=self.murray, text="Unreviewed.", chapter=chapter, paragraph=1
        )
        b = auto_emails.build_digest(self.build_time)
        quotes = [x for x in b.content["fr"]["blocks"] if x["type"] == "quote"]
        self.assertEqual(quotes, [{"type": "quote", "text": "Dieu attend.", "attribution": "Andrew Murray, Absolute-Surrender"}])
        self.assertEqual(b.subject["fr"], "Votre mois sur Ochorus")

    def test_force_builds_a_draft_now_even_when_off(self):
        b = auto_emails.build_digest(datetime(2026, 10, 17, tzinfo=UTC), force=True)
        self.assertEqual(b.status, BroadcastStatus.DRAFT)
        self.assertEqual(b.auto_key, "digest:2026-11")


class NewInLanguageTests(TestCase):
    def setUp(self):
        _live("en", "fr")
        self.author = Author.objects.create(slug="spurgeon", name="C. H. Spurgeon")
        self.now = datetime(2026, 10, 17, 12, tzinfo=UTC)

    def test_waits_for_the_batch_then_builds_once_per_gap(self):
        _enable(AutoEmail.NEW_IN_LANGUAGE, approval=False, at=self.now - timedelta(days=30))
        _book("all-of-grace", "fr", author=self.author, created=self.now - timedelta(days=1))
        self.assertEqual(auto_emails.build_new_in_language(self.now), [])  # still gathering
        later = self.now + timedelta(days=3)
        _book("morning-and-evening", "fr", author=self.author, created=self.now)
        built = auto_emails.build_new_in_language(later)
        self.assertEqual(len(built), 1)
        b = built[0]
        self.assertEqual(b.audience, {"email_language": "fr"})
        self.assertEqual(b.stream, "new_in_language")
        self.assertEqual(b.status, BroadcastStatus.SCHEDULED)
        self.assertEqual(b.subject, {"fr": "Nouveau en français sur Ochorus"})
        slugs = {x.get("slug") for x in b.content["fr"]["blocks"]}
        self.assertTrue({"all-of-grace", "morning-and-evening"} <= slugs)

        # A new book two days later waits out the weekly gap...
        _book("the-soul-winner", "fr", author=self.author, created=later + timedelta(days=1))
        Broadcast.objects.filter(pk=b.pk).update(created_at=later)
        self.assertEqual(auto_emails.build_new_in_language(later + timedelta(days=5)), [])
        # ...then goes out alone, without repeating the first batch.
        nxt = auto_emails.build_new_in_language(later + timedelta(days=8))
        self.assertEqual(len(nxt), 1)
        slugs = [x.get("slug") for x in nxt[0].content["fr"]["blocks"] if x.get("slug")]
        self.assertEqual(slugs, ["the-soul-winner"])

    def test_never_announces_the_back_catalogue(self):
        _book("all-of-grace", "fr", author=self.author, created=self.now - timedelta(days=20))
        _enable(AutoEmail.NEW_IN_LANGUAGE, at=self.now - timedelta(days=10))
        self.assertEqual(auto_emails.build_new_in_language(self.now), [])

    def test_off_builds_nothing(self):
        _book("all-of-grace", "fr", author=self.author, created=self.now - timedelta(days=5))
        self.assertEqual(auto_emails.build_new_in_language(self.now), [])

    def test_email_language_audience(self):
        fr = _make_profile(email="fr@example.com", locale="fr")
        frca = _make_profile(email="frca@example.com", locale="fr-CA")
        en_reads_fr_mail = _make_profile(email="x@example.com", locale="en")
        EmailSubscription.objects.create(profile=en_reads_fr_mail, email_locale="fr")
        fr_reads_en_mail = _make_profile(email="y@example.com", locale="fr")
        EmailSubscription.objects.create(profile=fr_reads_en_mail, email_locale="en")
        _make_profile(email="en@example.com", locale="en")
        got = set(resolve({"email_language": "fr"}))
        self.assertEqual(got, {fr, frca, en_reads_fr_mail})


@SENDING
class SendingTests(TestCase):
    def setUp(self):
        _live("en", "fr")
        self.author = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        _book("humility", "en", author=self.author)

    def _digest(self, **kw):
        fields = {
            "name": "Digest",
            "subject": {"en": "Your month"},
            "content": {
                "en": {
                    "blocks": [
                        {"type": "text", "text": "Hello {name}"},
                        {"type": "continue_reading", "heading": "Continue reading", "label": "Chapter {chapter}"},
                    ]
                }
            },
            "audience": {},
            "stream": "digest",
            "strict_locale": True,
            "status": BroadcastStatus.DRAFT,
        }
        fields.update(kw)
        return Broadcast.objects.create(**fields)

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_consent_is_the_campaigns_stream(self, send):
        wants_digest = _make_profile(email="a@example.com")
        EmailSubscription.objects.create(profile=wants_digest, stream_prefs={"announcements": False})
        no_digest = _make_profile(email="b@example.com")
        EmailSubscription.objects.create(profile=no_digest, stream_prefs={"digest": False})
        send_broadcast(self._digest())
        self.assertEqual([c.kwargs["to"] for c in send.call_args_list], ["a@example.com"])

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_strict_locale_skips_other_languages(self, send):
        _make_profile(email="en@example.com", locale="en")
        _make_profile(email="fr@example.com", locale="fr")
        b = self._digest()
        send_broadcast(b)
        self.assertEqual([c.kwargs["to"] for c in send.call_args_list], ["en@example.com"])
        b.refresh_from_db()
        self.assertEqual(b.progress["skipped"], 1)

    def test_continue_reading_is_the_readers_own_book(self):
        reader = _make_profile(email="r@example.com")
        sub = EmailSubscription.objects.create(profile=reader)
        idle = _make_profile(email="idle@example.com")
        idle_sub = EmailSubscription.objects.create(profile=idle)
        ReadingProgress.objects.create(
            profile=reader, kind=WorkKind.BOOK, book_slug="humility", language="en", chapter_order=7
        )
        b = self._digest()
        html = render_broadcast(b, reader, sub).html
        self.assertIn("Chapter 7", html)
        self.assertIn("https://ochorus.test/books/humility/7/", html)
        self.assertIn("Continue reading", html)
        idle_html = render_broadcast(b, idle, idle_sub).html
        self.assertNotIn("Continue reading", idle_html)  # the heading goes with the card

    def test_a_finished_book_is_not_in_progress(self):
        reader = _make_profile(email="r@example.com")
        sub = EmailSubscription.objects.create(profile=reader)
        ReadingProgress.objects.create(
            profile=reader,
            kind=WorkKind.BOOK,
            book_slug="humility",
            language="en",
            chapter_order=9,
            finished_at=timezone.now(),
        )
        self.assertNotIn("Chapter 9", render_broadcast(self._digest(), reader, sub).html)


@override_settings(DEBUG=True)  # loopback test client → admin gate bypassed
class AdminApiTests(TestCase):
    def setUp(self):
        _live("en")
        author = Author.objects.create(slug="andrew-murray", name="Andrew Murray")
        _book("humility", "en", author=author)

    def _call(self, method, url, payload):
        return getattr(self.client, method)(url, data=json.dumps(payload), content_type="application/json")

    def test_get_and_switch_on(self):
        data = self.client.get("/api/admin/emails/auto/").json()
        self.assertEqual([c["key"] for c in data["configs"]], ["digest", "new_in_language"])
        self.assertFalse(data["configs"][0]["enabled"])
        self.assertEqual(set(data["configs"][0]["sections"]), set(auto_emails.SECTIONS))
        res = self._call(
            "patch",
            "/api/admin/emails/auto/",
            {"key": "new_in_language", "enabled": True, "require_approval": False},
        )
        self.assertEqual(res.status_code, 200)
        config = AutoEmailConfig.get("new_in_language")
        self.assertTrue(config.enabled)
        self.assertIsNotNone(config.enabled_at)
        self.assertFalse(config.require_approval)
        self.assertEqual(self._call("patch", "/api/admin/emails/auto/", {"key": "x"}).status_code, 400)
        res = self._call("patch", "/api/admin/emails/auto/", {"key": "digest", "sections": {"plan": False, "bogus": True}})
        self.assertEqual(AutoEmailConfig.get("digest").sections, {"plan": False})
        self.assertTrue(
            AdminAction.objects.filter(action=AdminAction.Action.EMAIL_AUTO_SETTINGS).exists()
        )

    def test_build_now(self):
        res = self._call("post", "/api/admin/emails/auto/build/", {"key": "digest"})
        self.assertEqual(res.status_code, 201)
        built = Broadcast.objects.get(pk=res.json()["built"])
        self.assertEqual(built.status, BroadcastStatus.DRAFT)
        self.assertEqual(res.json()["recent"][0]["auto_key"], built.auto_key)
        again = self._call("post", "/api/admin/emails/auto/build/", {"key": "digest"})
        self.assertEqual(again.status_code, 409)
        self.assertEqual(self._call("post", "/api/admin/emails/auto/build/", {"key": "new_in_language"}).status_code, 400)


class SermonWorksTests(TestCase):
    def test_new_works_lists_books_then_sermons(self):
        author = Author.objects.create(slug="spurgeon", name="C. H. Spurgeon")
        now = timezone.now()
        _book("all-of-grace", "en", author=author, created=now)
        Sermon.objects.create(author=author, slug="a-sermon", language="en", title="A sermon")
        works = auto_emails._new_works("en", now - timedelta(days=1), now + timedelta(days=1), 6)
        self.assertEqual([w["type"] for w in works], ["book", "sermon"])


class ReviewFixTests(TestCase):
    """The edges a review found: windows that must not leave gaps, a skipped
    campaign that must stay skipped, and test sends of single-language mail."""

    def setUp(self):
        _live("en", "fr")
        self.author = Author.objects.create(slug="spurgeon", name="C. H. Spurgeon")
        self.now = datetime(2026, 10, 17, 12, tzinfo=UTC)

    def test_a_long_batch_carries_over_instead_of_being_dropped(self):
        _enable(AutoEmail.NEW_IN_LANGUAGE, approval=False, at=self.now - timedelta(days=30))
        for i in range(auto_emails.NEW_IN_LANGUAGE_LIMIT + 2):
            _book(f"book-{i:02d}", "fr", author=self.author, created=self.now - timedelta(days=10, minutes=-i))
        first = auto_emails.build_new_in_language(self.now)[0]
        listed = [x["slug"] for x in first.content["fr"]["blocks"] if x.get("slug")]
        self.assertEqual(listed, [f"book-{i:02d}" for i in range(auto_emails.NEW_IN_LANGUAGE_LIMIT)])
        Broadcast.objects.filter(pk=first.pk).update(created_at=self.now)
        second = auto_emails.build_new_in_language(self.now + timedelta(days=8))[0]
        listed = [x["slug"] for x in second.content["fr"]["blocks"] if x.get("slug")]
        self.assertEqual(listed, ["book-08", "book-09"])

    def test_the_digest_window_starts_where_the_last_one_was_built(self):
        _enable(AutoEmail.DIGEST)
        Plan.objects.create(slug="p", language="en", title="P")
        oct_build = datetime(2026, 10, 2, 9, tzinfo=UTC)
        Broadcast.objects.create(name="Oct", auto_key="digest:2026-10", status=BroadcastStatus.SENT)
        Broadcast.objects.filter(auto_key="digest:2026-10").update(created_at=oct_build)
        # Published after October's build but before October's send.
        _book("in-the-gap", "en", author=self.author, created=oct_build + timedelta(days=1))
        b = auto_emails.build_digest(NOV_ISSUE - timedelta(days=2))
        self.assertIn("in-the-gap", [x.get("slug") for x in b.content["en"]["blocks"]])

    @override_settings(DEBUG=True)
    def test_deleting_a_built_campaign_cancels_it_so_it_is_not_rebuilt(self):
        _enable(AutoEmail.DIGEST)
        Plan.objects.create(slug="p", language="en", title="P")
        b = auto_emails.build_digest(NOV_ISSUE - timedelta(days=2))
        res = self.client.delete(f"/api/admin/broadcasts/{b.pk}/")
        self.assertEqual(res.status_code, 200)
        b.refresh_from_db()
        self.assertEqual(b.status, BroadcastStatus.CANCELED)
        self.assertIsNone(auto_emails.build_digest(NOV_ISSUE - timedelta(days=1)))

    @override_settings(DEBUG=True)
    def test_flags_must_be_booleans(self):
        res = self.client.patch(
            "/api/admin/emails/auto/",
            data=json.dumps({"key": "digest", "enabled": "false"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertFalse(AutoEmailConfig.get("digest").enabled)

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_an_admin_can_test_a_campaign_in_another_language(self, send):
        from .broadcasts import send_test

        admin = _make_profile(email="admin@example.com", locale="en")
        b = Broadcast.objects.create(
            name="Nouveau",
            subject={"fr": "Nouveau"},
            content={"fr": {"blocks": [{"type": "text", "text": "Bonjour"}]}},
            strict_locale=True,
            stream="new_in_language",
        )
        self.assertTrue(send_test(b, admin))
        self.assertIn("Bonjour", send.call_args.kwargs["html"])

    @SENDING
    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_a_batch_send_fills_each_readers_own_book(self, send):
        _book("all-of-grace", "en", author=self.author)
        _book("morning", "en", author=self.author)
        a = _make_profile(email="a@example.com")
        b = _make_profile(email="b@example.com")
        ReadingProgress.objects.create(profile=a, kind=WorkKind.BOOK, book_slug="all-of-grace", language="en", chapter_order=2)
        ReadingProgress.objects.create(profile=b, kind=WorkKind.BOOK, book_slug="morning", language="en", chapter_order=5)
        campaign = Broadcast.objects.create(
            name="D",
            subject={"en": "D"},
            content={"en": {"blocks": [{"type": "text", "text": "Hi"}, {"type": "continue_reading", "heading": "", "label": "ch {chapter}"}]}},
            stream="digest",
        )
        send_broadcast(campaign)
        html = {c.kwargs["to"]: c.kwargs["html"] for c in send.call_args_list}
        self.assertIn("books/all-of-grace/2/", html["a@example.com"])
        self.assertIn("books/morning/5/", html["b@example.com"])
