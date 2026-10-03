"""The engagement page's chart markers: what the team did, by week.

They sit under the weekly readers chart so a jump has its likely cause beside
it, so the edges matter: only things that reached readers count (not a draft or
a test send), works are one marker per week however many were added, and
anything older than the chart's window stays off it.
"""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from emails.models import Broadcast, BroadcastStatus

from .models import Author, Book, Language, Sermon
from .weeks import day_of, week_start


@override_settings(DEBUG=True)
class EngagementEventsTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.author = Author.objects.create(slug="am", name="Andrew Murray")

    def _events(self):
        res = APIClient().get("/api/admin/engagement/")
        self.assertEqual(res.status_code, 200)
        return res.data["events"]

    def _week(self, dt):
        return week_start(day_of(dt)).isoformat()

    def test_a_sent_email_is_an_event_and_a_draft_is_not(self):
        Broadcast.objects.create(
            name="September letter",
            status=BroadcastStatus.SENT,
            send_started_at=self.now,
            send_tally={"sent": 28, "skipped": 2},
        )
        Broadcast.objects.create(name="Unsent draft", status=BroadcastStatus.DRAFT)
        Broadcast.objects.create(
            name="Canceled", status=BroadcastStatus.CANCELED, send_started_at=self.now
        )
        events = [e for e in self._events() if e["kind"] == "email"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["title"], "September letter")
        self.assertEqual(events[0]["detail"], "sent to 28 readers")
        self.assertEqual(events[0]["week"], self._week(self.now))

    def test_a_language_going_live_is_an_event(self):
        Language.objects.update_or_create(
            code="xh",
            defaults={"name": "Xhosa", "native_name": "isiXhosa", "went_live_at": self.now},
        )
        titles = [e["title"] for e in self._events() if e["kind"] == "language"]
        self.assertEqual(titles, ["Xhosa went live"])

    def test_works_added_in_a_week_are_one_event(self):
        for i in range(3):
            Book.objects.create(author=self.author, slug=f"b{i}", language="en", title=f"B{i}")
        Sermon.objects.create(author=self.author, slug="s", language="sw", title="S")
        works = [e for e in self._events() if e["kind"] == "works"]
        self.assertEqual(len(works), 1)
        self.assertEqual(works[0]["title"], "4 works added")
        self.assertTrue(works[0]["detail"].startswith("3 in English, 1 in "))

    def test_events_before_the_chart_are_left_out(self):
        long_ago = self.now - timedelta(weeks=12)
        Broadcast.objects.create(
            name="Spring letter", status=BroadcastStatus.SENT, send_started_at=long_ago
        )
        old = Book.objects.create(author=self.author, slug="old", language="en", title="Old")
        Book.objects.filter(pk=old.pk).update(created_at=long_ago)
        self.assertEqual(self._events(), [])

    def test_recent_means_the_same_last_7_days_as_the_active_tile(self):
        Broadcast.objects.create(
            name="This week", status=BroadcastStatus.SENT, send_started_at=self.now - timedelta(days=2)
        )
        Broadcast.objects.create(
            name="Last week", status=BroadcastStatus.SENT, send_started_at=self.now - timedelta(days=8)
        )
        recent = {e["title"]: e["recent"] for e in self._events()}
        self.assertEqual(recent, {"This week": True, "Last week": False})

    def test_every_event_falls_in_a_charted_week(self):
        Broadcast.objects.create(
            name="Letter", status=BroadcastStatus.SENT, send_started_at=self.now - timedelta(weeks=3)
        )
        Book.objects.create(author=self.author, slug="b", language="en", title="B")
        res = APIClient().get("/api/admin/engagement/").data
        weeks = {w["week"] for w in res["weekly_active"]}
        self.assertTrue(res["events"])
        self.assertTrue(all(e["week"] in weeks for e in res["events"]))
