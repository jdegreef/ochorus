"""The Notebook journal — the reader's own notes and prayers, synced."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile

from .models import JournalEntry

User = get_user_model()

URL = "/api/reading/journal/{}/"


class JournalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000a1")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="j@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def put(self, entry_id, **body):
        return self.client.put(URL.format(entry_id), body, format="json")

    def test_save_edit_and_state(self):
        res = self.put("a1", kind="prayer", body="For my mother", client_created_at=1000, client_updated_at=1000)
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data["kind"], res.data["body"]), ("prayer", "For my mother"))
        # A newer edit lands and keeps one row, and the prayer is answered.
        self.put("a1", kind="prayer", body="For my mother's healing", answer="She is home",
                 answered_at=5000, client_updated_at=2000)
        obj = JournalEntry.objects.get(profile=self.profile)
        self.assertEqual(obj.body, "For my mother's healing")
        self.assertEqual(obj.answer, "She is home")
        self.assertIsNotNone(obj.answered_at)
        # The create time is the first write's, not the edit's.
        self.assertEqual(obj.client_created_at.timestamp(), 1.0)
        state = self.client.get("/api/reading/state/").data
        self.assertEqual([e["entry_id"] for e in state["journal"]], ["a1"])

    def test_same_clock_is_not_rewritten(self):
        self.put("a1", body="x", client_updated_at=2000)
        before = JournalEntry.objects.get().updated_at
        self.put("a1", body="x", client_updated_at=2000)
        self.assertEqual(JournalEntry.objects.get().updated_at, before)

    def test_merge_applies_edits_and_deletes_in_bulk(self):
        self.put("e1", body="old", client_updated_at=1000)
        self.put("e2", kind="prayer", body="gone soon", client_updated_at=1000)
        res = self.client.post(
            "/api/reading/merge/",
            {"journal": [
                {"entry_id": "e1", "body": "new", "client_updated_at": 2000},
                {"entry_id": "e2", "kind": "prayer", "deleted": True, "client_updated_at": 500},
                {"entry_id": "e3", "body": "fresh", "client_updated_at": 3000},
            ]},
            format="json",
        )
        by_id = {e["entry_id"]: e for e in res.data["journal"]}
        self.assertEqual(by_id["e1"]["body"], "new")
        self.assertTrue(by_id["e2"]["deleted"])
        self.assertEqual(by_id["e2"]["body"], "")
        self.assertEqual(by_id["e3"]["body"], "fresh")

    def test_stale_edit_loses(self):
        self.put("a1", body="newer", client_updated_at=2000)
        self.put("a1", body="older", client_updated_at=1000)
        self.assertEqual(JournalEntry.objects.get(profile=self.profile).body, "newer")

    def test_delete_is_a_sticky_tombstone_without_text(self):
        self.put("a1", kind="prayer", body="secret", client_updated_at=1000)
        self.put("a1", kind="prayer", deleted=True, client_updated_at=2000)
        obj = JournalEntry.objects.get(profile=self.profile)
        self.assertTrue(obj.deleted)
        self.assertEqual(obj.body, "")
        # An offline device's later edit must not bring it back.
        self.put("a1", kind="prayer", body="secret", client_updated_at=10**13)
        obj.refresh_from_db()
        self.assertTrue(obj.deleted)
        self.assertEqual(obj.body, "")

    def test_delete_wins_over_a_fast_clock(self):
        # Written by a device whose clock is years ahead of this one's delete.
        self.put("a1", body="x", client_updated_at=10**13)
        self.put("a1", body="", deleted=True, client_updated_at=1000)
        self.assertTrue(JournalEntry.objects.get(profile=self.profile).deleted)

    def test_tombstones_do_not_spend_the_cap(self):
        from . import views

        old = views.MAX_JOURNAL_ENTRIES
        views.MAX_JOURNAL_ENTRIES = 1
        try:
            self.put("a1", body="x")
            self.put("a1", deleted=True)
            self.assertEqual(self.put("a2", body="y").status_code, 200)
            self.assertEqual(self.put("a3", body="z").status_code, 400)
            self.assertEqual(self.put("a4", deleted=True).status_code, 200)
        finally:
            views.MAX_JOURNAL_ENTRIES = old

    def test_a_future_clock_is_clamped(self):
        # A phone set to 2100 must not make its version unbeatable: its stamp
        # is held to a day past the server's clock, so a correct device's edit
        # a day later wins.
        from datetime import UTC, datetime, timedelta

        self.put("a1", body="from the future", client_updated_at=4_102_444_800_000)
        stored = JournalEntry.objects.get().client_updated_at
        self.assertLessEqual(stored, datetime.now(UTC) + timedelta(days=1, minutes=1))

    def test_a_daily_prayer_is_kept_like_a_note(self):
        res = self.put("d1", kind="daily", title="Today's prayer", body="Adore\nYou are good.",
                       person="Anna", answered_at=5000)
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data["kind"], res.data["person"], res.data["answered_at"]), ("daily", "", None))

    def test_collection_is_kept_trimmed_and_forgotten_on_delete(self):
        res = self.put("c1", kind="note", body="x", collection="  Notes on Humility  ")
        self.assertEqual(res.data["collection"], "Notes on Humility")
        self.put("c1", deleted=True)
        self.assertEqual(JournalEntry.objects.get(entry_id="c1").collection, "")

    def test_pin_round_trips_and_is_dropped_on_delete(self):
        res = self.put("p1", kind="note", body="Psalm 46:10", pinned_at=5000, client_updated_at=1000)
        self.assertIsNotNone(res.data["pinned_at"])
        res = self.put("p1", kind="note", body="Psalm 46:10", pinned_at=None, client_updated_at=2000)
        self.assertIsNone(res.data["pinned_at"])
        self.put("p1", kind="note", pinned_at=6000, client_updated_at=3000)
        self.put("p1", deleted=True)
        self.assertIsNone(JournalEntry.objects.get(entry_id="p1").pinned_at)

    def test_only_a_prayer_is_answered(self):
        self.put("n1", kind="note", body="x", answer="y", answered_at=5000)
        obj = JournalEntry.objects.get(profile=self.profile)
        self.assertIsNone(obj.answered_at)
        self.assertEqual(obj.answer, "")

    def test_rejects_junk(self):
        self.assertEqual(self.put("bad id!", body="x").status_code, 400)
        self.assertEqual(self.put("a1", kind="poem", body="x").status_code, 400)
        self.assertEqual(self.client.put(URL.format("a1"), [1], format="json").status_code, 400)
        self.assertEqual(JournalEntry.objects.count(), 0)

    def test_body_is_bounded(self):
        self.put("a1", body="x" * 50_000)
        self.assertEqual(len(JournalEntry.objects.get().body), 20_000)

    def test_merge_is_last_write_wins_and_skips_malformed(self):
        JournalEntry.objects.create(
            profile=self.profile, entry_id="srv", body="server newer",
            client_created_at="2026-01-01T00:00:00Z", client_updated_at="2026-06-01T00:00:00Z",
        )
        res = self.client.post(
            "/api/reading/merge/",
            {
                "journal": [
                    {"entry_id": "srv", "body": "local older", "client_updated_at": 1000},
                    {"entry_id": "loc", "kind": "prayer", "body": "offline prayer", "client_updated_at": 1000},
                    {"entry_id": "no good", "body": "x"},
                    "junk",
                ]
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        by_id = {e["entry_id"]: e for e in res.data["journal"]}
        self.assertEqual(set(by_id), {"srv", "loc"})
        self.assertEqual(by_id["srv"]["body"], "server newer")
        self.assertEqual(by_id["loc"]["kind"], "prayer")

    def test_private_to_the_owner(self):
        self.put("a1", body="mine")
        other = User.objects.create(username="00000000-0000-0000-0000-0000000000a2")
        UserProfile.objects.create(user=other, supabase_uid=other.username, email="k@example.com")
        c = APIClient()
        c.force_authenticate(other)
        self.assertEqual(c.get("/api/reading/state/").data["journal"], [])
        self.assertEqual(APIClient().put(URL.format("a1"), {}, format="json").status_code, 401)


class PrayerListTests(TestCase):
    """C: who a prayer is for, its group, reminder and updates. E: its source."""

    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000a3")
        UserProfile.objects.create(user=self.user, supabase_uid=self.user.username, email="p@example.com")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def put(self, entry_id, **body):
        return self.client.put(URL.format(entry_id), body, format="json")

    def test_prayer_list_fields_round_trip(self):
        res = self.put(
            "p1",
            kind="prayer",
            body="New job",
            person="Anna",
            group="family",
            remind="weekly-0@07:30",
            updates=[{"at": 2000, "text": "Interview on Friday"}, {"at": 3000, "text": " "}, "junk"],
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data["person"], res.data["group"], res.data["remind"]), ("Anna", "family", "weekly-0@07:30"))
        self.assertEqual(res.data["updates"], [{"at": 2000, "text": "Interview on Friday"}])

    def test_junk_group_and_reminder_are_dropped(self):
        res = self.put("p1", kind="prayer", group="aliens", remind="hourly@99:00")
        self.assertEqual((res.data["group"], res.data["remind"]), ("", ""))

    def test_a_note_carries_no_prayer_fields(self):
        res = self.put("n1", kind="note", person="Anna", group="family", remind="daily@07:00",
                       updates=[{"at": 1, "text": "x"}])
        self.assertEqual((res.data["person"], res.data["group"], res.data["remind"], res.data["updates"]),
                         ("", "", "", []))

    def test_source_is_positions_only(self):
        src = {"kind": "book", "slug": "humility", "order": 2, "p": 5, "edition": "en",
               "title": "Humility · Chapter 2", "quote": "q" * 900, "href": "javascript:alert(1)"}
        res = self.put("n1", kind="note", body="x", source=src)
        self.assertEqual(res.data["source"]["slug"], "humility")
        self.assertEqual(len(res.data["source"]["quote"]), 600)
        self.assertNotIn("href", res.data["source"])
        bad = self.put("n2", kind="note", body="x", source={**src, "order": 0})
        self.assertIsNone(bad.data["source"])
        kindless = {k: v for k, v in src.items() if k != "kind"}
        self.assertIsNone(self.put("n3", kind="note", body="x", source=kindless).data["source"])

    def test_tombstone_forgets_the_prayer_list_fields(self):
        self.put("p1", kind="prayer", person="Anna", updates=[{"at": 2000, "text": "u"}],
                 source={"kind": "book", "slug": "humility", "order": 1, "p": 0, "edition": "en"})
        self.put("p1", kind="prayer", deleted=True)
        e = JournalEntry.objects.get(entry_id="p1")
        self.assertEqual((e.person, e.updates, e.source), ("", [], None))
