"""Removing from the shelf sticks across devices (reading.models.Removal).

Every signed-in device runs the sign-in merge on each app load and uploads what
it still holds locally, so before tombstones a removal on one device was undone
by the next load of any other. These pin the rule: a write NOT newer than the
removal is dropped; a newer one (read it again, re-hearted it) lands and lifts
the tombstone.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile

from .models import Favorite, ReadingProgress, Removal

User = get_user_model()

T0 = 1_790_000_000_000  # epoch ms
HOUR = 3_600_000


class RemovalTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000a1")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="rm@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def put_progress(self, slug, at, order=3, **extra):
        return self.client.put(
            f"/api/reading/progress/{slug}/",
            {"language": "en", "chapter_order": order, "paragraph_index": 0, "updated_at": at, **extra},
            format="json",
        )

    def merge(self, **payload):
        res = self.client.post("/api/reading/merge/", payload, format="json")
        self.assertEqual(res.status_code, 200)
        return res.data

    def progress_slugs(self, state):
        return {p["book_slug"] for p in state["progress"]}

    def fav_keys(self, state):
        return {(f["kind"], f["slug"]) for f in state["favorites"]}


class ProgressRemovalTests(RemovalTestBase):
    def test_delete_removes_the_position_and_leaves_a_tombstone(self):
        self.put_progress("humility", T0)
        res = self.client.delete(f"/api/reading/progress/humility/?kind=book&at={T0 + HOUR}")
        self.assertEqual(res.status_code, 204)
        self.assertFalse(ReadingProgress.objects.filter(profile=self.profile).exists())
        self.assertTrue(Removal.objects.filter(profile=self.profile, domain="progress", slug="humility").exists())
        self.assertEqual(self.client.get("/api/reading/progress/humility/?kind=book").status_code, 404)

    def test_a_stale_device_merging_its_copy_does_not_bring_it_back(self):
        self.put_progress("humility", T0)
        self.client.delete(f"/api/reading/progress/humility/?kind=book&at={T0 + HOUR}")
        # The phone still holds the old position (and an untimestamped legacy row).
        state = self.merge(
            progress=[
                {"kind": "book", "book_slug": "humility", "language": "en", "chapter_order": 3, "updated_at": T0},
                {"kind": "book", "book_slug": "humility", "language": "en", "chapter_order": 5},
            ]
        )
        self.assertNotIn("humility", self.progress_slugs(state))

    def test_a_stale_live_push_is_dropped_not_an_error(self):
        self.put_progress("humility", T0)
        self.client.delete(f"/api/reading/progress/humility/?kind=book&at={T0 + HOUR}")
        res = self.put_progress("humility", T0 + 1)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, {"removed": True})
        self.assertFalse(ReadingProgress.objects.filter(profile=self.profile).exists())

    def test_reading_it_again_after_removal_revives_it(self):
        self.put_progress("humility", T0)
        self.client.delete(f"/api/reading/progress/humility/?kind=book&at={T0 + HOUR}")
        res = self.put_progress("humility", T0 + 2 * HOUR, order=1)
        self.assertEqual(res.data["chapter_order"], 1)
        self.assertFalse(Removal.objects.filter(profile=self.profile).exists())
        # …and it stays revived through a stale merge afterwards.
        state = self.merge(
            progress=[{"kind": "book", "book_slug": "humility", "language": "en", "chapter_order": 3, "updated_at": T0}]
        )
        self.assertIn("humility", self.progress_slugs(state))

    def test_a_removal_older_than_newer_reading_is_not_applied(self):
        # An offline device carries up a removal made BEFORE reading elsewhere.
        self.put_progress("humility", T0 + 2 * HOUR)
        state = self.merge(removed=[{"domain": "progress", "kind": "book", "slug": "humility", "at": T0}])
        self.assertIn("humility", self.progress_slugs(state))
        self.assertFalse(Removal.objects.filter(profile=self.profile).exists())

    def test_merge_carries_an_offline_removal(self):
        self.put_progress("humility", T0)
        state = self.merge(
            removed=[{"domain": "progress", "kind": "book", "slug": "humility", "at": T0 + HOUR}],
            # The same bundle can't also resurrect it.
            progress=[{"kind": "book", "book_slug": "humility", "language": "en", "chapter_order": 3, "updated_at": T0}],
        )
        self.assertNotIn("humility", self.progress_slugs(state))

    def test_removal_is_per_kind(self):
        self.put_progress("humility", T0)
        self.put_progress("humility", T0, kind="sermon")
        self.client.delete(f"/api/reading/progress/humility/?kind=sermon&at={T0 + HOUR}")
        kinds = set(ReadingProgress.objects.filter(profile=self.profile).values_list("kind", flat=True))
        self.assertEqual(kinds, {"book"})

    def test_bad_removals_are_rejected_or_skipped(self):
        self.assertEqual(self.client.delete("/api/reading/progress/humility/?kind=galaxy").status_code, 400)
        state = self.merge(
            removed=[
                {"domain": "progress", "kind": "book", "slug": "humility"},  # no `at`
                {"domain": "galaxy", "kind": "book", "slug": "humility", "at": T0},
                {"domain": "favorite", "kind": "galaxy", "slug": "x", "at": T0},
                "not-a-dict",
            ]
        )
        self.assertEqual(state["progress"], [])
        self.assertFalse(Removal.objects.exists())

    def test_requires_auth(self):
        self.assertEqual(APIClient().delete("/api/reading/progress/humility/").status_code, 401)


class FavoriteRemovalTests(RemovalTestBase):
    def test_unhearting_survives_another_devices_merge(self):
        self.client.put("/api/reading/favorites/book/humility/")
        self.client.delete(f"/api/reading/favorites/book/humility/?at={T0}")
        # A device still holding the heart: old client (no saved_at), and a new
        # client whose heart predates the removal.
        state = self.merge(
            favorites=[
                {"kind": "book", "slug": "humility"},
                {"kind": "book", "slug": "humility", "saved_at": T0},
            ]
        )
        self.assertNotIn(("book", "humility"), self.fav_keys(state))

    def test_a_heart_saved_after_the_removal_lands(self):
        self.client.put("/api/reading/favorites/book/humility/")
        removed = int(Favorite.objects.get().created_at.timestamp() * 1000) + HOUR
        self.client.delete(f"/api/reading/favorites/book/humility/?at={removed}")
        state = self.merge(favorites=[{"kind": "book", "slug": "humility", "saved_at": removed + HOUR}])
        self.assertIn(("book", "humility"), self.fav_keys(state))
        self.assertFalse(Removal.objects.filter(profile=self.profile).exists())

    def test_a_live_reheart_lifts_the_tombstone(self):
        self.client.delete(f"/api/reading/favorites/book/humility/?at={T0}")
        self.client.put("/api/reading/favorites/book/humility/")
        self.assertFalse(Removal.objects.filter(profile=self.profile).exists())
        state = self.merge(favorites=[{"kind": "book", "slug": "humility"}])
        self.assertIn(("book", "humility"), self.fav_keys(state))

    def test_merge_carries_an_offline_unheart(self):
        Favorite.objects.create(profile=self.profile, kind="author", slug="andrew-murray")
        # created_at is now; an offline removal from "the future" relative to it.
        future = int(Favorite.objects.get().created_at.timestamp() * 1000) + HOUR
        state = self.merge(removed=[{"domain": "favorite", "kind": "author", "slug": "andrew-murray", "at": future}])
        self.assertEqual(state["favorites"], [])

    def test_an_offline_unheart_older_than_the_heart_is_not_applied(self):
        Favorite.objects.create(profile=self.profile, kind="author", slug="andrew-murray")
        state = self.merge(removed=[{"domain": "favorite", "kind": "author", "slug": "andrew-murray", "at": T0 - 10 * HOUR * 24 * 365}])
        self.assertIn(("author", "andrew-murray"), self.fav_keys(state))

    def test_tombstone_keeps_the_latest_removal(self):
        self.client.delete(f"/api/reading/favorites/book/humility/?at={T0 + HOUR}")
        self.merge(removed=[{"domain": "favorite", "kind": "book", "slug": "humility", "at": T0}])
        tomb = Removal.objects.get(profile=self.profile)
        self.assertEqual(int(tomb.removed_at.timestamp() * 1000), T0 + HOUR)

    def test_a_live_unheart_from_a_slow_clock_still_applies(self):
        # The heart was saved "now" on the server; the removing device's clock
        # is a day behind. A tap is a tap — it must still remove, and the
        # tombstone must still cover the heart it removed.
        self.client.put("/api/reading/favorites/book/humility/")
        created = Favorite.objects.get().created_at
        slow = int(created.timestamp() * 1000) - 24 * HOUR
        self.client.delete(f"/api/reading/favorites/book/humility/?at={slow}")
        self.assertFalse(Favorite.objects.exists())
        self.assertGreaterEqual(Removal.objects.get().removed_at, created)


class LiveRemovalClockTests(RemovalTestBase):
    def test_a_live_removal_covers_a_position_written_by_a_faster_clock(self):
        self.put_progress("humility", T0 + 5 * HOUR)  # another device, clock ahead
        self.client.delete(f"/api/reading/progress/humility/?kind=book&at={T0}")
        self.assertFalse(ReadingProgress.objects.exists())
        # That device's own copy, merged later, stays removed.
        state = self.merge(
            progress=[{"kind": "book", "book_slug": "humility", "language": "en", "chapter_order": 3, "updated_at": T0 + 5 * HOUR}]
        )
        self.assertEqual(state["progress"], [])


class MergeAcknowledgementTests(RemovalTestBase):
    def test_merge_says_it_applied_removals(self):
        self.assertIs(self.merge()["removed_applied"], True)
