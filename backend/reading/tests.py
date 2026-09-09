
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile

from .marks import (
    MAX_LANG_LEN,
    clean_mark_list,
    clean_tombstones,
    from_legacy,
    merge_mark_lists,
    reconcile_marks,
)
from .models import Bookmark, ChapterMarks, Favorite, ReadingDay, ReadingProgress
from .views import _now_ms

User = get_user_model()


def mark(p, s, e, note=None, id=None):
    m = {"id": id or f"{p}:{s}:{e}", "p": p, "s": s, "e": e}
    if note:
        m["note"] = note
    return m


class ReadingSyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-000000000001")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="r@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_progress_upsert_and_state(self):
        res = self.client.put(
            "/api/reading/progress/humility/",
            {"language": "en", "chapter_order": 3, "paragraph_index": 12},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["chapter_order"], 3)

        self.client.put(
            "/api/reading/progress/humility/",
            {"chapter_order": 5, "paragraph_index": 0},
            format="json",
        )
        self.assertEqual(ReadingProgress.objects.filter(profile=self.profile).count(), 1)

        state = self.client.get("/api/reading/state/").data
        self.assertEqual(len(state["progress"]), 1)
        self.assertEqual(state["progress"][0]["chapter_order"], 5)

    def test_progress_get_returns_the_synced_position_with_the_writers_clock(self):
        # Nothing synced yet: a clean 404, not an empty row.
        self.assertEqual(self.client.get("/api/reading/progress/humility/").status_code, 404)

        self.client.put(
            "/api/reading/progress/humility/",
            {"language": "en", "chapter_order": 7, "paragraph_index": 3, "updated_at": 1_700_000_000_000},
            format="json",
        )
        res = self.client.get("/api/reading/progress/humility/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data["chapter_order"], res.data["paragraph_index"]), (7, 3))
        # The writing device's clock rides along, so a second device can tell
        # "further along elsewhere" from its own older record.
        self.assertTrue(res.data["client_updated_at"].startswith("2023-11-14"))

        # Scoped by kind: a sermon of the same slug is a different row.
        self.assertEqual(self.client.get("/api/reading/progress/humility/?kind=sermon").status_code, 404)
        self.assertEqual(self.client.get("/api/reading/progress/humility/?kind=nope").status_code, 400)

        # Reads are for everyone who is signed in, and only them.
        self.assertEqual(APIClient().get("/api/reading/progress/humility/").status_code, 401)

    def test_range_marks_put_and_delete(self):
        res = self.client.put(
            "/api/reading/marks/humility/2/",
            {"marks": [mark(1, 5, 42, note=" keep "), mark(1, 5, 42), {"p": -1}]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        # deduped by range, malformed dropped, note trimmed
        self.assertEqual(len(res.data["marks"]), 1)
        self.assertEqual(res.data["marks"][0]["note"], "keep")

        self.client.put("/api/reading/marks/humility/2/", {"marks": []}, format="json")
        self.assertEqual(ChapterMarks.objects.count(), 0)

    def test_tombstone_put_preserves_another_devices_highlight(self):
        # The cross-device loss bug: device A saves H1; device B, which never saw
        # H1, saves only H2 with the new protocol (a `deleted` key present). The
        # server unions, so H1 is NOT clobbered.
        self.client.put(
            "/api/reading/marks/humility/3/",
            {"marks": [mark(1, 0, 5, id="A1")], "deleted": []},
            format="json",
        )
        res = self.client.put(
            "/api/reading/marks/humility/3/",
            {"marks": [mark(2, 0, 5, id="B2")], "deleted": []},
            format="json",
        )
        self.assertEqual({m["id"] for m in res.data["marks"]}, {"A1", "B2"})

    def test_tombstone_put_deletes_only_the_marked_id(self):
        # Two marks; deleting one via a tombstone removes just it and never
        # resurrects it on a later stale re-push that still carries it.
        now = _now_ms()
        self.client.put(
            "/api/reading/marks/humility/4/",
            {"marks": [mark(1, 0, 5, id="A1"), mark(2, 0, 5, id="A2")], "deleted": []},
            format="json",
        )
        res = self.client.put(
            "/api/reading/marks/humility/4/",
            {"marks": [mark(2, 0, 5, id="A2")], "deleted": [{"id": "A1", "at": now}]},
            format="json",
        )
        self.assertEqual({m["id"] for m in res.data["marks"]}, {"A2"})
        # A stale device re-pushes the whole old list — A1 must stay gone.
        res = self.client.put(
            "/api/reading/marks/humility/4/",
            {"marks": [mark(1, 0, 5, id="A1"), mark(2, 0, 5, id="A2")], "deleted": []},
            format="json",
        )
        self.assertEqual({m["id"] for m in res.data["marks"]}, {"A2"})

    def test_tombstone_only_row_is_retained_not_deleted(self):
        # Deleting the last mark leaves an empty row that still holds the tombstone
        # (so a stale re-push can't bring the mark back), rather than dropping the
        # row entirely as the legacy path does.
        now = _now_ms()
        self.client.put(
            "/api/reading/marks/humility/5/",
            {"marks": [mark(1, 0, 5, id="A1")], "deleted": []},
            format="json",
        )
        self.client.put(
            "/api/reading/marks/humility/5/",
            {"marks": [], "deleted": [{"id": "A1", "at": now}]},
            format="json",
        )
        row = ChapterMarks.objects.get(book_slug="humility", chapter_order=5)
        self.assertEqual(row.marks, [])
        self.assertEqual(row.deleted, {"A1": now})

    def test_signin_merge_does_not_resurrect_a_deleted_mark(self):
        # A reader deletes a highlight (server keeps the tombstone). Another device
        # signs in still holding it locally and merges — it must stay deleted.
        now = _now_ms()
        self.client.put(
            "/api/reading/marks/humility/6/",
            {"marks": [mark(1, 0, 5, id="A1")], "deleted": []},
            format="json",
        )
        self.client.put(
            "/api/reading/marks/humility/6/",
            {"marks": [], "deleted": [{"id": "A1", "at": now}]},
            format="json",
        )
        state = self.client.post(
            "/api/reading/merge/",
            {
                "marks": [
                    {"book_slug": "humility", "chapter_order": 6, "marks": [mark(1, 0, 5, id="A1")]}
                ]
            },
            format="json",
        ).data
        ch6 = [m for m in state["marks"] if m["chapter_order"] == 6]
        self.assertEqual(ch6[0]["marks"], [])  # not resurrected

    def test_marks_preserve_highlight_colour(self):
        # A valid colour survives; an unknown one is dropped (default = gold).
        cleaned = clean_mark_list(
            [{**mark(0, 0, 5), "color": "blue"}, {**mark(1, 0, 5), "color": "chartreuse"}]
        )
        self.assertEqual(cleaned[0].get("color"), "blue")
        self.assertNotIn("color", cleaned[1])

    def test_sermon_marks_shim_writes_unified_rows(self):
        # The pre-unification endpoint (PR #293 bundles) keeps working, but
        # its writes land in ChapterMarks(kind="sermon") and its response
        # keeps the old shape.
        res = self.client.put(
            "/api/reading/sermon-marks/himself/",
            {"marks": [{**mark(2, 0, 9, note="a"), "color": "green"}], "language": "en"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["sermon_slug"], "himself")
        self.assertEqual(res.data["marks"][0]["color"], "green")
        row = ChapterMarks.objects.get()
        self.assertEqual((row.kind, row.book_slug, row.chapter_order), ("sermon", "himself", 1))
        self.client.put("/api/reading/sermon-marks/himself/", {"marks": []}, format="json")
        self.assertEqual(ChapterMarks.objects.count(), 0)

    def test_sermon_marks_merge_and_state_compat(self):
        # Old-shape merge payloads fold into the unified table and the state
        # echo still carries the legacy field (old bundles rehydrate from it).
        ChapterMarks.objects.create(
            profile=self.profile, kind="sermon", book_slug="himself",
            chapter_order=1, marks=[mark(0, 0, 3)],
        )
        payload = {"sermon_marks": [{"sermon_slug": "himself", "marks": [mark(1, 0, 4)]}]}
        state = self.client.post("/api/reading/merge/", payload, format="json").data
        self.assertIn("sermon_marks", state)
        rows = {m["sermon_slug"]: m for m in state["sermon_marks"]}
        self.assertEqual(len(rows["himself"]["marks"]), 2)  # unioned, none dropped
        self.assertEqual(ChapterMarks.objects.get().kind, "sermon")

    def test_legacy_payload_converts(self):
        # An old client (cached SPA) still sends paragraph-level h/n.
        res = self.client.put(
            "/api/reading/marks/humility/1/",
            {"highlights": [3], "notes": {"5": "old note"}},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        ranges = {(m["p"], m["s"], m["e"]) for m in res.data["marks"]}
        self.assertEqual(ranges, {(3, 0, -1), (5, 0, -1)})
        by_p = {m["p"]: m for m in res.data["marks"]}
        self.assertEqual(by_p[5]["note"], "old note")

    def test_merge_unions_ranges_and_keeps_newer_progress(self):
        ReadingProgress.objects.create(
            profile=self.profile, book_slug="humility", chapter_order=2, paragraph_index=1
        )
        ChapterMarks.objects.create(
            profile=self.profile,
            book_slug="humility",
            chapter_order=1,
            marks=[mark(1, 0, 20, note="short")],
        )

        payload = {
            "progress": [
                {
                    "book_slug": "humility",
                    "chapter_order": 7,
                    "paragraph_index": 3,
                    "updated_at": 10_000_000_000_000,
                },
                {"book_slug": "abide", "chapter_order": 1, "paragraph_index": 0},
            ],
            "marks": [
                {
                    "book_slug": "humility",
                    "chapter_order": 1,
                    "marks": [
                        mark(1, 0, 20, note="a much longer note"),
                        mark(2, 4, 9),
                    ],
                }
            ],
        }
        state = self.client.post("/api/reading/merge/", payload, format="json").data

        prog = {p["book_slug"]: p for p in state["progress"]}
        self.assertEqual(prog["humility"]["chapter_order"], 7)
        self.assertIn("abide", prog)

        ms = state["marks"][0]["marks"]
        self.assertEqual({(m["p"], m["s"], m["e"]) for m in ms}, {(1, 0, 20), (2, 4, 9)})
        self.assertEqual(ms[0]["note"], "a much longer note")  # longer note won

    def test_merge_folds_in_unconverted_server_row(self):
        # Server row predating the range conversion (only legacy fields set).
        ChapterMarks.objects.create(
            profile=self.profile,
            book_slug="humility",
            chapter_order=4,
            marks=[],
            highlights=[2],
            notes={"2": "legacy"},
        )
        payload = {
            "marks": [
                {"book_slug": "humility", "chapter_order": 4, "marks": [mark(0, 1, 9)]}
            ]
        }
        state = self.client.post("/api/reading/merge/", payload, format="json").data
        ms = state["marks"][0]["marks"]
        self.assertEqual(
            {(m["p"], m["s"], m["e"]) for m in ms}, {(0, 1, 9), (2, 0, -1)}
        )

    def test_requires_auth(self):
        anon = APIClient()
        self.assertEqual(anon.get("/api/reading/state/").status_code, 401)


class FavoriteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-000000000002")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="f@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_save_idempotent_unsave_and_state(self):
        res = self.client.put("/api/reading/favorites/author/andrew-murray/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data["kind"], res.data["slug"]), ("author", "andrew-murray"))
        # Saving twice keeps one row.
        self.client.put("/api/reading/favorites/author/andrew-murray/")
        self.client.put("/api/reading/favorites/plan/school-of-prayer/")
        self.assertEqual(Favorite.objects.filter(profile=self.profile).count(), 2)

        state = self.client.get("/api/reading/state/").data
        favs = {(f["kind"], f["slug"]) for f in state["favorites"]}
        self.assertEqual(
            favs, {("author", "andrew-murray"), ("plan", "school-of-prayer")}
        )

        res = self.client.delete("/api/reading/favorites/author/andrew-murray/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(Favorite.objects.filter(profile=self.profile).count(), 1)

    def test_unknown_kind_rejected(self):
        res = self.client.put("/api/reading/favorites/galaxy/andromeda/")
        self.assertEqual(res.status_code, 400)

    def test_topic_article_and_quote_are_favoritable(self):
        # The reader saves topics, articles and individual quotes as well as
        # works — each a valid FavoriteKind, so a heart on those pages syncs
        # rather than 400ing.
        for kind, slug in (
            ("topic", "prayer"),
            ("article", "how-to-pray"),
            ("quote", "andrew-murray-abc123"),
        ):
            res = self.client.put(f"/api/reading/favorites/{kind}/{slug}/")
            self.assertEqual(res.status_code, 200, (kind, slug))
            self.assertEqual((res.data["kind"], res.data["slug"]), (kind, slug))

    def test_merge_unions_favorites_and_skips_unknown(self):
        Favorite.objects.create(profile=self.profile, kind="book", slug="humility")
        res = self.client.post(
            "/api/reading/merge/",
            {
                "favorites": [
                    {"kind": "book", "slug": "humility"},  # already on server
                    {"kind": "author", "slug": "c-h-spurgeon"},  # offline heart
                    {"kind": "galaxy", "slug": "andromeda"},  # unknown kind
                ]
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        favs = {(f["kind"], f["slug"]) for f in res.data["favorites"]}
        self.assertEqual(favs, {("book", "humility"), ("author", "c-h-spurgeon")})

    def test_requires_auth(self):
        anon = APIClient()
        self.assertEqual(anon.put("/api/reading/favorites/book/humility/").status_code, 401)


class BookmarkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-000000000009")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="bm@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_save_idempotent_unsave_and_state(self):
        res = self.client.put(
            "/api/reading/bookmarks/book/humility/2/5/",
            {"bm_id": "x1", "snippet": "Blessed is he", "title": "Chapter 2", "at": 111},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            (res.data["kind"], res.data["book_slug"], res.data["chapter_order"], res.data["paragraph_index"]),
            ("book", "humility", 2, 5),
        )
        self.assertEqual(res.data["snippet"], "Blessed is he")
        # Saving the same spot again keeps one row (display text refreshed).
        self.client.put(
            "/api/reading/bookmarks/book/humility/2/5/",
            {"snippet": "Blessed is he who", "title": "Chapter 2", "at": 222},
            format="json",
        )
        self.assertEqual(Bookmark.objects.filter(profile=self.profile).count(), 1)
        self.assertEqual(Bookmark.objects.get(profile=self.profile).snippet, "Blessed is he who")

        # A second spot, then confirm both surface in /state.
        self.client.put("/api/reading/bookmarks/book/humility/3/0/", {}, format="json")
        state = self.client.get("/api/reading/state/").data
        spots = {(b["chapter_order"], b["paragraph_index"]) for b in state["bookmarks"]}
        self.assertEqual(spots, {(2, 5), (3, 0)})

        res = self.client.delete("/api/reading/bookmarks/book/humility/2/5/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(Bookmark.objects.filter(profile=self.profile).count(), 1)

    def test_unknown_kind_and_bad_position_rejected(self):
        self.assertEqual(
            self.client.put("/api/reading/bookmarks/galaxy/humility/1/0/", {}, format="json").status_code,
            400,
        )
        # order 0 is not a valid 1-based chapter.
        self.assertEqual(
            self.client.put("/api/reading/bookmarks/book/humility/0/0/", {}, format="json").status_code,
            400,
        )
        # An out-of-range paragraph index is rejected before it reaches the DB
        # (an unbounded int would overflow Postgres integer → 500). SQLite would
        # accept it, so this asserts the guard, not the column.
        self.assertEqual(
            self.client.put(
                "/api/reading/bookmarks/book/humility/1/9999999999/", {}, format="json"
            ).status_code,
            400,
        )
        self.assertEqual(Bookmark.objects.filter(profile=self.profile).count(), 0)

    def test_sermon_bookmark_kind(self):
        res = self.client.put(
            "/api/reading/bookmarks/sermon/the-blood/1/4/", {"snippet": "s"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["kind"], "sermon")

    def test_merge_unions_bookmarks_and_skips_malformed(self):
        Bookmark.objects.create(
            profile=self.profile, kind="book", book_slug="humility", chapter_order=1, paragraph_index=2
        )
        res = self.client.post(
            "/api/reading/merge/",
            {
                "bookmarks": [
                    {"kind": "book", "book_slug": "humility", "chapter_order": 1, "paragraph_index": 2},  # on server
                    {"kind": "book", "book_slug": "humility", "chapter_order": 4, "paragraph_index": 0, "snippet": "off"},  # offline
                    {"kind": "book", "book_slug": "humility", "chapter_order": 0, "paragraph_index": 0},  # bad order
                    {"kind": "galaxy", "book_slug": "x", "chapter_order": 1, "paragraph_index": 0},  # bad kind
                    {"kind": "book", "book_slug": "humility", "chapter_order": 1, "paragraph_index": "nope"},  # bad p
                    {"kind": "book", "book_slug": "humility", "chapter_order": 1, "paragraph_index": 9999999999},  # p out of range
                ]
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        spots = {(b["chapter_order"], b["paragraph_index"]) for b in res.data["bookmarks"]}
        self.assertEqual(spots, {(1, 2), (4, 0)})

    def test_requires_auth(self):
        anon = APIClient()
        self.assertEqual(
            anon.put("/api/reading/bookmarks/book/humility/1/0/", {}, format="json").status_code, 401
        )


class MarkHelpersTests(TestCase):
    def test_from_legacy(self):
        ms = from_legacy([1, 3], {"3": "note on 3", "9": "solo note"})
        self.assertEqual(
            {(m["p"], m["s"], m["e"]) for m in ms}, {(1, 0, -1), (3, 0, -1), (9, 0, -1)}
        )
        by_p = {m["p"]: m for m in ms}
        self.assertEqual(by_p[3]["note"], "note on 3")
        self.assertNotIn("note", by_p[1])

    def test_merge_is_a_union(self):
        a = [mark(0, 0, 5), mark(1, 2, 8, note="x")]
        b = [mark(1, 2, 8, note="longer note"), mark(2, 0, -1)]
        merged = merge_mark_lists(a, b)
        self.assertEqual(len(merged), 3)
        self.assertEqual(merged[1]["note"], "longer note")

    def test_clean_caps_count_and_lengths(self):
        from .marks import MAX_ID_LEN, MAX_MARKS_PER_CHAPTER, MAX_NOTE_LEN

        # One chapter can't store an unbounded number of marks…
        raw = [{"id": f"m{i}", "p": i, "s": 0, "e": 1} for i in range(MAX_MARKS_PER_CHAPTER + 50)]
        cleaned = clean_mark_list(raw)
        self.assertEqual(len(cleaned), MAX_MARKS_PER_CHAPTER)
        # …nor a giant note or id.
        big = clean_mark_list([{"id": "x" * 200, "p": 0, "s": 0, "e": 1, "note": "n" * 9000}])
        self.assertEqual(len(big), 1)
        self.assertLessEqual(len(big[0]["id"]), MAX_ID_LEN)
        self.assertEqual(len(big[0]["note"]), MAX_NOTE_LEN)

    def test_clean_keeps_the_edition_tag(self):
        # A mark's `lang` says which edition's characters its offsets index.
        # Dropping it (the field whitelist did) is what let a highlight made on
        # the original text be painted across the modern text's words.
        cleaned = clean_mark_list([{"id": "a", "p": 0, "s": 0, "e": 5, "lang": "en-modern"}])
        self.assertEqual(cleaned[0]["lang"], "en-modern")
        # Absent on an untagged (pre-editions) mark rather than invented.
        self.assertNotIn("lang", clean_mark_list([{"id": "b", "p": 0, "s": 0, "e": 5}])[0])
        # Junk and over-long values don't reach storage.
        self.assertNotIn("lang", clean_mark_list([{"id": "c", "p": 0, "s": 0, "e": 5, "lang": 7}])[0])
        long = clean_mark_list([{"id": "d", "p": 0, "s": 0, "e": 5, "lang": "x" * 40}])
        self.assertEqual(len(long[0]["lang"]), MAX_LANG_LEN)

    def test_clean_keeps_one_range_per_edition(self):
        # Same offsets, different texts: two highlights, not one. The dedupe key
        # used to be the offsets alone, which silently ate the second.
        cleaned = clean_mark_list(
            [
                {"id": "a", "p": 0, "s": 0, "e": 5, "lang": "en"},
                {"id": "b", "p": 0, "s": 0, "e": 5, "lang": "en-modern"},
                {"id": "c", "p": 0, "s": 0, "e": 5, "lang": "en"},  # a real duplicate
            ]
        )
        self.assertEqual([m["lang"] for m in cleaned], ["en", "en-modern"])

    def test_merge_keeps_editions_apart(self):
        a = [dict(mark(0, 0, 5), lang="en")]
        b = [dict(mark(0, 0, 5), lang="en-modern")]
        self.assertEqual(len(merge_mark_lists(a, b)), 2)
        # An untagged mark still merges with an untagged one, so nothing already
        # on the server is duplicated by the tag arriving.
        self.assertEqual(len(merge_mark_lists([mark(0, 0, 5)], [mark(0, 0, 5)])), 1)

    def test_merge_holds_the_per_chapter_cap(self):
        from .marks import MAX_MARKS_PER_CHAPTER

        # Two full lists (disjoint ranges) union to 2× the cap; the result is held
        # at the cap so a merge can't grow past the bound.
        a = clean_mark_list([{"id": f"a{i}", "p": i, "s": 0, "e": 1} for i in range(MAX_MARKS_PER_CHAPTER)])
        b = clean_mark_list(
            [{"id": f"b{i}", "p": i, "s": 0, "e": 1} for i in range(10_000, 10_000 + MAX_MARKS_PER_CHAPTER)]
        )
        self.assertEqual(len(merge_mark_lists(a, b)), MAX_MARKS_PER_CHAPTER)

    def test_reconcile_unions_marks_the_stale_pusher_never_saw(self):
        # The core cross-device fix: device A's H1 is on the server; device B,
        # which never synced it, pushes only its own H2. The union keeps both.
        h1 = mark(1, 0, 5, id="A1")
        h2 = mark(2, 0, 5, id="B2")
        merged, tombs = reconcile_marks([h1], {}, [h2], {}, now_ms=1000)
        self.assertEqual({m["id"] for m in merged}, {"A1", "B2"})
        self.assertEqual(tombs, {})

    def test_reconcile_deletes_by_tombstone(self):
        # A delete rides in as a tombstone; the mark goes and the tombstone stays.
        h1 = mark(1, 0, 5, id="A1")
        merged, tombs = reconcile_marks([h1], {}, [], {"A1": 900}, now_ms=1000)
        self.assertEqual(merged, [])
        self.assertEqual(tombs, {"A1": 900})

    def test_reconcile_suppresses_a_stale_devices_resurrection(self):
        # Server already deleted A1 (tombstone). A stale device that still holds it
        # re-pushes it in its mark list — it must NOT come back.
        h1 = mark(1, 0, 5, id="A1")
        merged, tombs = reconcile_marks([], {"A1": 900}, [h1], {}, now_ms=1000)
        self.assertEqual(merged, [])
        self.assertEqual(tombs, {"A1": 900})

    def test_reconcile_keeps_a_delete_then_readd_of_the_same_range(self):
        # One payload deletes A1 and re-highlights the same range as B1: the fresh
        # mark wins (this push's deletion is applied to the server side first).
        old = mark(1, 0, 5, id="A1")
        new = mark(1, 0, 5, id="B1")
        merged, _ = reconcile_marks([old], {}, [new], {"A1": 1000}, now_ms=1000)
        self.assertEqual([m["id"] for m in merged], ["B1"])

    def test_prune_drops_expired_tombstones(self):
        from .marks import TOMBSTONE_TTL_MS, prune_tombstones

        now = 10 * TOMBSTONE_TTL_MS
        kept = prune_tombstones({"fresh": now - 1, "old": now - TOMBSTONE_TTL_MS - 1}, now)
        self.assertEqual(set(kept), {"fresh"})

    def test_clean_tombstones_accepts_list_or_dict(self):
        self.assertEqual(clean_tombstones({"a": 5}), {"a": 5})
        self.assertEqual(clean_tombstones([{"id": "a", "at": 5}]), {"a": 5})
        self.assertEqual(clean_tombstones(["a"]), {"a": 0})  # bare id => "long ago"
        self.assertEqual(clean_tombstones([{"at": 5}, 7, None]), {})  # malformed dropped


class WorkKindTests(TestCase):
    """Sermons in the reading layer (kind discriminator, roadmap #10)."""

    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-000000000002")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="k@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_sermon_and_book_progress_share_a_slug_without_colliding(self):
        self.client.put(
            "/api/reading/progress/humility/",
            {"chapter_order": 3, "paragraph_index": 5},
            format="json",
        )
        res = self.client.put(
            "/api/reading/progress/humility/?kind=sermon",
            {"paragraph_index": 40},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["kind"], "sermon")
        rows = ReadingProgress.objects.filter(profile=self.profile)
        self.assertEqual(rows.count(), 2)
        self.assertEqual(
            {(r.kind, r.chapter_order, r.paragraph_index) for r in rows},
            {("book", 3, 5), ("sermon", 1, 40)},
        )

    def test_unknown_kind_rejected_not_misfiled(self):
        res = self.client.put(
            "/api/reading/progress/humility/?kind=plan",
            {"paragraph_index": 1},
            format="json",
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(ReadingProgress.objects.count(), 0)

    def test_sermon_marks_are_scoped_by_kind(self):
        self.client.put(
            "/api/reading/marks/free-grace/1/",
            {"marks": [mark(0, 0, 10)]},
            format="json",
        )
        self.client.put(
            "/api/reading/marks/free-grace/1/?kind=sermon",
            {"marks": [mark(2, 5, 20, note="amen")]},
            format="json",
        )
        self.assertEqual(ChapterMarks.objects.count(), 2)
        # Deleting the sermon's marks (empty payload) leaves the book row.
        self.client.put(
            "/api/reading/marks/free-grace/1/?kind=sermon", {"marks": []}, format="json"
        )
        remaining = ChapterMarks.objects.get()
        self.assertEqual(remaining.kind, "book")

    def test_bio_marks_are_a_valid_kind(self):
        # Biography highlights (roadmap #12): kind="bio", single document like
        # sermons (chapter_order pinned to 1), slug names the author.
        res = self.client.put(
            "/api/reading/marks/andrew-murray/1/?kind=bio",
            {"marks": [mark(0, 0, 12, note="what a life")]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        row = ChapterMarks.objects.get()
        self.assertEqual((row.kind, row.book_slug, row.chapter_order), ("bio", "andrew-murray", 1))
        # And the merge path carries it too.
        res = self.client.post(
            "/api/reading/merge/",
            {"marks": [{"book_slug": "c-h-spurgeon", "kind": "bio", "chapter_order": 1,
                        "marks": [mark(3, 2, 9)]}]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        kinds = {(m.kind, m.book_slug) for m in ChapterMarks.objects.all()}
        self.assertEqual(kinds, {("bio", "andrew-murray"), ("bio", "c-h-spurgeon")})

    def test_merge_carries_kind_and_skips_unknown(self):
        res = self.client.post(
            "/api/reading/merge/",
            {
                "progress": [
                    {"book_slug": "humility", "chapter_order": 2},  # legacy: no kind
                    {"book_slug": "free-grace", "kind": "sermon", "paragraph_index": 7},
                    {"book_slug": "future", "kind": "plan", "paragraph_index": 1},
                ],
                "marks": [
                    {"book_slug": "free-grace", "kind": "sermon", "chapter_order": 1,
                     "marks": [mark(1, 0, 5)]},
                ],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        kinds = {(p.kind, p.book_slug) for p in ReadingProgress.objects.all()}
        self.assertEqual(kinds, {("book", "humility"), ("sermon", "free-grace")})
        m = ChapterMarks.objects.get()
        self.assertEqual((m.kind, m.book_slug, m.chapter_order), ("sermon", "free-grace", 1))
        # The state echo includes kind so clients can rehydrate by kind.
        self.assertEqual(
            {r["kind"] for r in res.data["progress"]}, {"book", "sermon"}
        )


class ActivityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-000000000003")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="a@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_record_day_idempotent_and_in_state(self):
        res = self.client.put("/api/reading/activity/2026-07-20/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["day"], "2026-07-20")
        # Recording the same day again keeps one row.
        self.client.put("/api/reading/activity/2026-07-20/")
        self.client.put("/api/reading/activity/2026-07-21/")
        self.assertEqual(ReadingDay.objects.filter(profile=self.profile).count(), 2)
        state = self.client.get("/api/reading/state/").data
        self.assertEqual(set(state["activity"]), {"2026-07-20", "2026-07-21"})

    def test_bad_date_rejected(self):
        res = self.client.put("/api/reading/activity/not-a-date/")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(ReadingDay.objects.count(), 0)

    def test_merge_unions_activity_and_skips_bad(self):
        ReadingDay.objects.create(profile=self.profile, day="2026-07-20")
        res = self.client.post(
            "/api/reading/merge/",
            {"activity": ["2026-07-20", "2026-07-22", "garbage"]},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            {d.day.isoformat() for d in ReadingDay.objects.filter(profile=self.profile)},
            {"2026-07-20", "2026-07-22"},
        )
        self.assertEqual(set(res.data["activity"]), {"2026-07-20", "2026-07-22"})

    def test_requires_auth(self):
        anon = APIClient()
        self.assertEqual(anon.put("/api/reading/activity/2026-07-20/").status_code, 401)

    def test_merge_ignores_a_non_list_activity_payload(self):
        # A dict's keys look like valid dates; without the type guard they'd be
        # iterated and (mis)merged. The guard makes a non-list a no-op.
        res = self.client.post(
            "/api/reading/merge/",
            {"activity": {"2026-07-20": 1}},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ReadingDay.objects.filter(profile=self.profile).count(), 0)


class MalformedPayloadTests(TestCase):
    """A stale or buggy client can send a wrong-shaped body (a JSON array where
    a dict is expected, non-dict rows in a merge list). None of it may 500: the
    endpoints skip the junk and return normally, so a single bad field never
    aborts a reader's sign-in reconciliation."""

    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000ff")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="m@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_merge_ignores_non_list_sections(self):
        res = self.client.post(
            "/api/reading/merge/",
            {
                "progress": "oops",
                "marks": "nope",
                "favorites": {"not": "a list"},
                "sermon_marks": 42,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)

    def test_merge_skips_non_dict_rows(self):
        res = self.client.post(
            "/api/reading/merge/",
            {
                "progress": [42, "x", None],
                "marks": [7],
                "favorites": [1, 2, 3],
                "sermon_marks": ["nope"],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        # Nothing junk was written.
        self.assertEqual(ReadingProgress.objects.filter(profile=self.profile).count(), 0)
        self.assertEqual(ChapterMarks.objects.filter(profile=self.profile).count(), 0)
        self.assertEqual(Favorite.objects.filter(profile=self.profile).count(), 0)

    def test_merge_with_a_json_array_body_does_not_500(self):
        res = self.client.post("/api/reading/merge/", [1, 2, 3], format="json")
        self.assertEqual(res.status_code, 200)

    def test_put_endpoints_reject_a_non_dict_body_without_losing_data(self):
        # A bare array/scalar body must be a clean 400 — NOT a 500, and crucially
        # NOT coerced to {} (which for marks means "delete" and for progress means
        # "reset to chapter 1"). Existing data must survive the malformed request.
        ReadingProgress.objects.create(
            profile=self.profile, kind="book", book_slug="humility",
            language="en", chapter_order=15, paragraph_index=4,
        )
        ChapterMarks.objects.create(
            profile=self.profile, kind="book", book_slug="humility",
            chapter_order=1, marks=[mark(0, 1, 5)],
        )
        ChapterMarks.objects.create(
            profile=self.profile, kind="sermon", book_slug="a-sermon",
            chapter_order=1, marks=[mark(0, 2, 6)],
        )

        for url in (
            "/api/reading/progress/humility/",
            "/api/reading/marks/humility/1/",
            "/api/reading/plan/school-of-prayer/",
            "/api/reading/sermon-marks/a-sermon/",
        ):
            self.assertEqual(
                self.client.put(url, [1, 2, 3], format="json").status_code,
                400,
                msg=url,
            )

        # Nothing was deleted or reset by the malformed requests.
        prog = ReadingProgress.objects.get(profile=self.profile, book_slug="humility")
        self.assertEqual(prog.chapter_order, 15)
        self.assertTrue(
            ChapterMarks.objects.filter(
                profile=self.profile, kind="book", book_slug="humility", chapter_order=1
            ).exists()
        )
        self.assertTrue(
            ChapterMarks.objects.filter(
                profile=self.profile, kind="sermon", book_slug="a-sermon"
            ).exists()
        )


class MergeHardeningTests(TestCase):
    """Wave 2: caps, atomicity, and input validation on the sync endpoints."""

    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000aa")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="h@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_merge_caps_each_section(self):
        from .views import MAX_MERGE_ROWS

        favorites = [
            {"kind": "book", "slug": f"b{i}"} for i in range(MAX_MERGE_ROWS + 25)
        ]
        res = self.client.post(
            "/api/reading/merge/", {"favorites": favorites}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            Favorite.objects.filter(profile=self.profile).count(), MAX_MERGE_ROWS
        )

    def test_merge_is_atomic_on_a_mid_phase_failure(self):
        from unittest.mock import patch

        from .views import MergeView

        # Favorites merge before activity; force activity to blow up and assert the
        # already-written favorites are rolled back (no half-merged account). The
        # client is configured to turn the unhandled error into a 500 response
        # rather than re-raise it into the test.
        client = APIClient(raise_request_exception=False)
        client.force_authenticate(self.user)
        payload = {"favorites": [{"kind": "book", "slug": "humility"}], "activity": []}
        with patch.object(
            MergeView, "_merge_activity", side_effect=RuntimeError("boom")
        ):
            res = client.post("/api/reading/merge/", payload, format="json")
        self.assertEqual(res.status_code, 500)
        self.assertEqual(Favorite.objects.filter(profile=self.profile).count(), 0)

    def test_merge_skips_negative_and_zero_chapter_orders(self):
        payload = {
            "marks": [
                {"book_slug": "humility", "chapter_order": -5, "marks": [{"p": 0, "s": 0, "e": 1}]},
                {"book_slug": "humility", "chapter_order": 0, "marks": [{"p": 0, "s": 0, "e": 1}]},
                {"book_slug": "humility", "chapter_order": 2, "marks": [{"p": 0, "s": 0, "e": 1}]},
            ]
        }
        self.client.post("/api/reading/merge/", payload, format="json")
        orders = list(
            ChapterMarks.objects.filter(profile=self.profile).values_list(
                "chapter_order", flat=True
            )
        )
        self.assertEqual(orders, [2])  # -5 and 0 dropped, no junk chapter-0 row

    def test_merge_skips_over_long_slugs(self):
        payload = {"favorites": [{"kind": "book", "slug": "x" * 300}]}
        res = self.client.post("/api/reading/merge/", payload, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Favorite.objects.filter(profile=self.profile).count(), 0)

    def test_put_rejects_over_long_slug_and_out_of_range_order(self):
        # A 300-char slug is a 400, not a Postgres DataError 500.
        self.assertEqual(
            self.client.put(
                f"/api/reading/progress/{'x' * 300}/",
                {"chapter_order": 1},
                format="json",
            ).status_code,
            400,
        )
        # An order past the ceiling is a 400, not a 500.
        self.assertEqual(
            self.client.put(
                "/api/reading/marks/humility/999999/",
                {"marks": [{"p": 0, "s": 0, "e": 1}]},
                format="json",
            ).status_code,
            400,
        )

    def test_oversized_chapter_order_is_clamped_not_a_500(self):
        # A value past int4 max would DataError-500 on Postgres; it's clamped.
        from .views import MAX_CHAPTER_ORDER

        res = self.client.put(
            "/api/reading/progress/humility/",
            {"chapter_order": 3_000_000_000, "paragraph_index": 9_000_000_000},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertLessEqual(res.data["chapter_order"], MAX_CHAPTER_ORDER)
        # Same value inside a merge row must not 500 the reconciliation either.
        merged = self.client.post(
            "/api/reading/merge/",
            {"progress": [{"book_slug": "abide", "chapter_order": 3_000_000_000}]},
            format="json",
        )
        self.assertEqual(merged.status_code, 200)

    def test_non_string_language_is_not_a_500(self):
        # `(x or "en")[:10]` on a truthy non-string (5, []) would TypeError-500.
        res = self.client.put(
            "/api/reading/progress/humility/",
            {"chapter_order": 1, "language": 5},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["language"], "en")
        merged = self.client.post(
            "/api/reading/merge/",
            {"marks": [{"book_slug": "x", "chapter_order": 1, "language": [1],
                        "marks": [{"p": 0, "s": 0, "e": 1}]}]},
            format="json",
        )
        self.assertEqual(merged.status_code, 200)

    def test_reading_writes_are_throttled_per_account(self):
        from common.testing import enforcing_throttle

        from .views import _ReadingWriteThrottle

        # Squeezed to 2/min for this test; the 3rd write in the window 429s.
        # Throttles are inert under `manage.py test` — see common.throttling —
        # so this hands the class a real, private cache for the duration.
        with enforcing_throttle(_ReadingWriteThrottle, "2/min"):
            codes = [
                self.client.put(
                    "/api/reading/favorites/book/humility/", format="json"
                ).status_code
                for _ in range(3)
            ]
        self.assertEqual(codes[:2], [200, 200])
        self.assertEqual(codes[2], 429)



class ProgressRecencyTests(TestCase):
    """A stale device must not rewind a reading position a newer one recorded.

    Recency is judged on the CLIENT's own clock (`client_updated_at`), not the
    server's `updated_at` — so a device is compared to itself and can always
    advance, even if its clock lags the server (bug #1 sibling)."""

    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000c1")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="rec@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _put(self, order, at=None):
        body = {"chapter_order": order, "paragraph_index": 0}
        if at is not None:
            body["updated_at"] = at
        return self.client.put("/api/reading/progress/humility/", body, format="json")

    def _state_order(self):
        return self.client.get("/api/reading/state/").data["progress"][0]["chapter_order"]

    def test_a_stale_put_does_not_rewind_a_newer_position(self):
        self._put(8, at=2_000)  # a newer device recorded chapter 8
        self._put(5, at=1_000)  # a backgrounded tab flushes an older position
        self.assertEqual(self._state_order(), 8)

    def test_a_device_can_always_advance_its_own_position(self):
        # Monotonic client times always win — the safety property that a clock
        # lagging the server can never freeze a device out of saving.
        for order, at in ((1, 1_000), (2, 2_000), (3, 3_000)):
            self._put(order, at=at)
        self.assertEqual(self._state_order(), 3)

    def test_an_untimestamped_put_still_saves(self):
        # An old client that sends no timestamp is an active write and must land.
        self._put(8, at=5_000)
        self._put(4)
        self.assertEqual(self._state_order(), 4)

    def test_merge_keeps_the_server_when_the_bundle_has_no_timestamp(self):
        # The sign-in half of the fix: an untimestamped (stale/old) bundle must
        # not overwrite a newer server position it can't out-date.
        self._put(8, at=5_000)
        self.client.post(
            "/api/reading/merge/",
            {"progress": [{"book_slug": "humility", "chapter_order": 3}]},
            format="json",
        )
        self.assertEqual(self._state_order(), 8)

    def test_a_live_put_still_advances_a_null_baseline_row(self):
        # A row with no recency baseline (an old client wrote it with no timestamp)
        # must not freeze the live PUT out of saving — an active write always lands.
        ReadingProgress.objects.create(
            profile=self.profile, kind="book", book_slug="humility",
            chapter_order=8, client_updated_at=None,
        )
        self._put(9, at=1_000)
        self.assertEqual(self._state_order(), 9)


@skipUnless(connection.vendor == "postgresql", "row locking is a Postgres behaviour")
class MarksConcurrentMergeTests(TransactionTestCase):
    """Two devices merging marks into the same chapter at once.

    The live PUT was already locked; this proves the SIGN-IN merge path is too —
    without the row lock both readers see the same server marks and the second
    write clobbers the first's union, dropping a highlight (bug #2). Postgres-only
    and a no-op-safe TransactionTestCase, mirroring the plan-progress race test."""

    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000c2")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="cm@example.com"
        )

    def test_neither_device_loses_its_mark(self):
        import threading

        from django.db import connections

        from reading.views import _now_ms, _upsert_marks_locked

        now = _now_ms()
        ready = threading.Barrier(2, timeout=10)
        errors: list[BaseException] = []

        def write(mark_id: str, p: int):
            try:
                ready.wait()  # both threads enter together
                _upsert_marks_locked(
                    self.profile,
                    "book",
                    "humility",
                    1,
                    language="en",
                    marks=[{"id": mark_id, "p": p, "s": 0, "e": 5}],
                    tombs={},
                    now_ms=now,
                )
            except BaseException as exc:  # noqa: BLE001 — re-raised in the assertions
                errors.append(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=write, args=a) for a in (("A", 1), ("B", 2))]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15)

        self.assertEqual(errors, [], f"a writer raised: {errors}")
        self.assertEqual(ChapterMarks.objects.count(), 1)
        ids = {m["id"] for m in ChapterMarks.objects.get().marks}
        self.assertEqual(ids, {"A", "B"}, "a highlight made on one device was lost to the other's merge")
