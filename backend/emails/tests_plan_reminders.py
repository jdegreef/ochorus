"""Reading-plan reminder emails (emails.plan_reminders)."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone

from emails.lifecycle import last_lifecycle_sent_at
from emails.models import EmailKind, EmailMessage, EmailSubscription, SendStatus
from emails.plan_reminders import (
    PLAN_PAUSED_STEP,
    PLAN_REMINDER_STEP,
    candidates,
    day_path,
    due_plan_email,
    reads_on,
    send_due,
)
from emails.tests import SENDING, _make_profile
from library.models import Author, Book, Chapter, Plan, PlanDay
from reading.models import PlanProgress, PlanSchedule, ReadingDay

LONDON = ZoneInfo("Europe/London")
# A Wednesday, 07:10 in London (BST, UTC+1).
NOW = datetime(2026, 10, 7, 7, 10, tzinfo=LONDON)


def _plan(language="en"):
    author = Author.objects.create(slug=f"murray-{language}", name="Andrew Murray")
    book = Book.objects.create(author=author, slug="humility", language=language, title="Humility")
    for order, title in [(1, "The Glory of the Creature"), (2, "The Secret of Redemption")]:
        Chapter.objects.create(book=book, order=order, title=title, body_html="<p>Text.</p>")
    plan = Plan.objects.create(slug="humility-12", language=language, title="Humility in 12 Days")
    for d in (1, 2):
        PlanDay.objects.create(plan=plan, day=d, book_slug="humility", chapter_order=d)
    return plan


@SENDING
class PlanReminderDueTests(TestCase):
    def setUp(self):
        self.profile = _make_profile(name="Grace")
        self.profile.timezone = "Europe/London"
        self.profile.save(update_fields=["timezone"])
        self.sub = EmailSubscription.objects.create(profile=self.profile)
        self.plan = _plan()
        self.progress = PlanProgress.objects.create(
            profile=self.profile,
            plan_slug="humility-12",
            started_at=NOW - timedelta(days=1),
            done=[1],
        )
        self.schedule = PlanSchedule.objects.create(
            profile=self.profile, plan_slug="humility-12", remind_at="07:00", email_reminder=True, client_updated_at=NOW
        )
        ReadingDay.objects.create(profile=self.profile, day=date(2026, 10, 6))

    def due(self, now=NOW):
        return due_plan_email(self.profile, self.sub, now)

    def test_due_at_the_reader_local_time_for_the_next_undone_day(self):
        due = self.due()
        self.assertEqual(due.step, PLAN_REMINDER_STEP)
        self.assertEqual(due.day.day, 2)

    def test_not_before_the_time_nor_long_after_it(self):
        self.assertIsNone(self.due(NOW.replace(hour=6, minute=55)))
        self.assertIsNone(self.due(NOW.replace(hour=11, minute=0)))

    def test_not_on_a_day_already_read(self):
        ReadingDay.objects.create(profile=self.profile, day=date(2026, 10, 7))
        self.assertIsNone(self.due())

    def test_not_on_a_non_reading_day(self):
        self.schedule.reading_days = PlanSchedule.ReadingDays.WEEKDAYS
        self.schedule.save()
        saturday = datetime(2026, 10, 10, 7, 10, tzinfo=LONDON)
        self.assertIsNone(self.due(saturday))

    def test_not_once_the_plan_is_finished(self):
        self.progress.done = [1, 2]
        self.progress.save()
        self.assertIsNone(self.due())

    def test_no_english_fallback_for_another_language_reader(self):
        self.profile.locale = "sw"
        self.profile.save(update_fields=["locale"])
        self.assertIsNone(self.due())

    def test_pauses_after_three_idle_days(self):
        later = NOW + timedelta(days=3)  # last read 6 Oct → 9 Oct is 3 days on
        due = self.due(later)
        self.assertEqual(due.step, PLAN_PAUSED_STEP)
        self.assertEqual(due.anchor, date(2026, 10, 6))

    def test_reads_on_rules(self):
        sunday = date(2026, 10, 11)
        self.assertTrue(reads_on(sunday, PlanSchedule.ReadingDays.DAILY))
        self.assertFalse(reads_on(sunday, PlanSchedule.ReadingDays.MONSAT))
        self.assertFalse(reads_on(date(2026, 10, 10), PlanSchedule.ReadingDays.WEEKDAYS))

    def test_day_path_matches_the_reader_plan_link(self):
        day = PlanDay.objects.get(plan=self.plan, day=2)
        self.assertEqual(day_path(self.plan, day), "books/humility/2/?plan=humility-12&day=2")

    def test_a_calendar_time_alone_sends_no_email(self):
        PlanSchedule.objects.filter(profile=self.profile).update(email_reminder=False)
        self.assertIsNone(self.due())
        self.assertNotIn(self.profile, candidates(NOW))

    def test_candidates_are_readers_inside_their_send_window(self):
        self.assertIn(self.profile, candidates(NOW))
        self.assertNotIn(self.profile, candidates(NOW.replace(hour=12)))
        PlanSchedule.objects.filter(profile=self.profile).update(remind_at="")
        self.assertNotIn(self.profile, candidates(NOW))

    def test_plan_edition_follows_the_reading_locale_not_the_email_language(self):
        self.sub.email_locale = "es"
        self.sub.save()
        self.assertEqual(self.due().plan.language, "en")


@SENDING
class PlanReminderSendTests(TestCase):
    def setUp(self):
        self.profile = _make_profile(name="Grace")
        self.profile.timezone = "Europe/London"
        self.profile.save(update_fields=["timezone"])
        _plan()
        PlanProgress.objects.create(
            profile=self.profile, plan_slug="humility-12", started_at=NOW - timedelta(days=1), done=[1]
        )
        PlanSchedule.objects.create(profile=self.profile, plan_slug="humility-12", remind_at="07:00", email_reminder=True, client_updated_at=NOW)
        ReadingDay.objects.create(profile=self.profile, day=date(2026, 10, 6))

    @mock.patch("emails.sending.send_email", return_value="rid-plan")
    def test_sends_once_a_day_with_the_reading(self, send):
        message = send_due(self.profile, NOW)
        self.assertEqual(message.status, SendStatus.SENT)
        self.assertEqual(message.lifecycle_step, PLAN_REMINDER_STEP)
        self.assertEqual(message.subject, "Day 2 · Humility in 12 Days")
        html = send.call_args.kwargs["html"]
        self.assertIn("The Secret of Redemption", html)
        self.assertIn("books/humility/2/?plan=humility-12&amp;day=2", html)
        # Same day, next cron pass: already sent, so nothing is re-rendered or sent.
        self.assertIsNone(send_due(self.profile, NOW + timedelta(minutes=15)))
        self.assertEqual(send.call_count, 1)

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_does_not_take_or_wait_for_the_shared_slot(self, send):
        EmailMessage.objects.create(
            recipient=self.profile,
            to_email="reader@example.com",
            kind=EmailKind.LIFECYCLE,
            lifecycle_step="welcome",
            idempotency_key="lifecycle:welcome:x",
            status=SendStatus.SENT,
            sent_at=timezone.now(),
        )
        welcome_at = last_lifecycle_sent_at(self.profile)
        self.assertIsNotNone(send_due(self.profile, NOW))
        # The reminder is not what the drip's 20h gap now measures from.
        self.assertEqual(last_lifecycle_sent_at(self.profile), welcome_at)

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_opting_out_of_the_stream_blocks_it(self, send):
        EmailSubscription.objects.create(profile=self.profile, stream_prefs={"plan_reminders": False})
        self.assertIsNone(send_due(self.profile, NOW))
        send.assert_not_called()

    @mock.patch("emails.sending.send_email", return_value="rid")
    def test_paused_email_is_sent_once_per_idle_stretch(self, send):
        later = NOW + timedelta(days=3)
        first = send_due(self.profile, later)
        self.assertEqual(first.lifecycle_step, PLAN_PAUSED_STEP)
        self.assertIsNone(send_due(self.profile, later + timedelta(days=1)))
        self.assertEqual(send.call_count, 1)
