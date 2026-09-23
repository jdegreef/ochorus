"""Custom shelves sync (reading.models.CustomShelf).

The shelf's name and deleted state are last-write-wins on the client clock;
its book list merges per book, so adds and removals from two devices both
survive and a stale copy can't undo either.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile

from .models import CustomShelf
from .views import MAX_SHELF_BOOKS, MAX_SHELVES

User = get_user_model()

T0 = 1_790_000_000_000
MIN = 60_000


def body(name="Lent", *, updated=T0, created=T0, books=(), deleted=False):
    return {
        "name": name,
        "created_at": created,
        "updated_at": updated,
        "deleted": deleted,
        "books": [{"slug": s, "at": at, "removed": removed} for s, at, removed in books],
    }


class ShelfTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000c1")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="sh@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def put(self, shelf_id="s1", **kw):
        return self.client.put(f"/api/reading/shelves/{shelf_id}/", body(**kw), format="json")

    def live_books(self, data):
        return sorted(b["slug"] for b in data["books"] if not b["removed"])

    def test_create_and_state(self):
        res = self.put(books=[("humility", T0, False)])
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["name"], "Lent")
        state = self.client.get("/api/reading/state/").data
        self.assertEqual([s["shelf_id"] for s in state["shelves"]], ["s1"])

    def test_books_from_two_devices_both_survive(self):
        self.put(books=[("humility", T0 + MIN, False)], updated=T0 + MIN)
        # The other device never saw humility; its later write adds a different book.
        res = self.put(books=[("true-vine", T0 + 2 * MIN, False)], updated=T0 + 2 * MIN)
        self.assertEqual(self.live_books(res.data), ["humility", "true-vine"])

    def test_a_removal_beats_a_stale_add(self):
        self.put(books=[("humility", T0, False)])
        self.put(books=[("humility", T0 + MIN, True)], updated=T0 + MIN)
        # A device still holding the older add merges it back in.
        res = self.client.post(
            "/api/reading/merge/",
            {"shelves": [{"shelf_id": "s1", **body(books=[("humility", T0, False)])}]},
            format="json",
        )
        shelf = res.data["shelves"][0]
        self.assertEqual(self.live_books(shelf), [])
        # …but re-adding it later lands.
        res = self.put(books=[("humility", T0 + 2 * MIN, False)], updated=T0 + 2 * MIN)
        self.assertEqual(self.live_books(res.data), ["humility"])

    def test_name_and_delete_are_last_write_wins(self):
        self.put(name="Lent", updated=T0 + 2 * MIN)
        res = self.put(name="Old name", updated=T0 + MIN)  # stale rename
        self.assertEqual(res.data["name"], "Lent")
        res = self.put(name="Lent", deleted=True, updated=T0 + 3 * MIN)
        self.assertTrue(res.data["deleted"])
        # A stale copy can't revive it; a newer write can.
        res = self.put(name="Lent", updated=T0 + 2 * MIN, books=[("humility", T0 + 2 * MIN, False)])
        self.assertTrue(res.data["deleted"])
        self.assertEqual(self.live_books(res.data), ["humility"])  # books still merge
        res = self.put(name="Lent again", updated=T0 + 4 * MIN)
        self.assertFalse(res.data["deleted"])
        self.assertEqual(res.data["name"], "Lent again")

    def test_tombstones_ride_the_state(self):
        self.put(deleted=True)
        state = self.client.get("/api/reading/state/").data
        self.assertTrue(state["shelves"][0]["deleted"])

    def test_merge_creates_and_merges_shelves(self):
        self.put("s1", books=[("humility", T0, False)])
        res = self.client.post(
            "/api/reading/merge/",
            {
                "shelves": [
                    {"shelf_id": "s1", **body(books=[("true-vine", T0 + MIN, False)])},
                    {"shelf_id": "s2", **body(name="Small group")},
                    {"shelf_id": "bad id!", **body()},
                    "junk",
                ]
            },
            format="json",
        )
        shelves = {s["shelf_id"]: s for s in res.data["shelves"]}
        self.assertEqual(set(shelves), {"s1", "s2"})
        self.assertEqual(self.live_books(shelves["s1"]), ["humility", "true-vine"])

    def test_invalid_bodies_are_rejected(self):
        self.assertEqual(self.client.put("/api/reading/shelves/bad id/", body(), format="json").status_code, 400)
        bad = body()
        del bad["updated_at"]
        self.assertEqual(self.client.put("/api/reading/shelves/s1/", bad, format="json").status_code, 400)
        bad = {**body(), "books": "nope"}
        self.assertEqual(self.client.put("/api/reading/shelves/s1/", bad, format="json").status_code, 400)
        # Malformed book entries are dropped, not fatal.
        res = self.client.put(
            "/api/reading/shelves/s1/",
            {**body(), "books": [{"slug": "ok", "at": T0}, {"slug": "bad slug!", "at": T0}, {"slug": "x", "at": "soon"}]},
            format="json",
        )
        self.assertEqual([b["slug"] for b in res.data["books"]], ["ok"])

    def test_caps(self):
        for i in range(MAX_SHELVES):
            CustomShelf.objects.create(
                profile=self.profile, shelf_id=f"x{i}", client_created_at="2026-01-01T00:00:00Z", client_updated_at="2026-01-01T00:00:00Z"
            )
        self.assertEqual(self.put("one-too-many").status_code, 400)
        CustomShelf.objects.all().delete()
        many = [(f"b{i}", T0 + i, False) for i in range(MAX_SHELF_BOOKS + 5)]
        res = self.put(books=many)
        self.assertEqual(len(res.data["books"]), MAX_SHELF_BOOKS)
        self.assertNotIn("b0", [b["slug"] for b in res.data["books"]])  # oldest dropped

    def test_long_names_are_trimmed(self):
        res = self.put(name="  " + "x" * 200 + "  ")
        self.assertEqual(len(res.data["name"]), 80)

    def test_requires_auth(self):
        self.assertEqual(APIClient().put("/api/reading/shelves/s1/", body(), format="json").status_code, 401)
