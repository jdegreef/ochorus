"""Saved places re-found by their words after a text repair (reading.anchor +
the remap_marks release step)."""

import io

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile
from library.models import Author, Book, Chapter, Sermon

from .anchor import (
    block_texts,
    refind_bookmark,
    remap_mark_list,
    resolve_group,
    resolve_mark,
)
from .marks import merge_mark_lists
from .models import Bookmark, ChapterMarks, Removal

User = get_user_model()

GRACE = "Grace is the free favour of God"  # 31 chars — a full-length anchor


def seg(p, s, e, q, id="g", lang="en"):
    return {"id": id, "p": p, "s": s, "e": e, "q": q, "lang": lang}


class BlockTextsTests(SimpleTestCase):
    def test_top_level_blocks_as_the_dom_reads_them(self):
        html = (
            "<!-- note --><p>One <em>two</em> &amp; three</p>\n"
            "<blockquote><p>Inner</p><p>two</p></blockquote><p>a<br>b</p>"
        )
        self.assertEqual(block_texts(html), ["One two & three", "Innertwo", "ab"])

    def test_empty_body(self):
        self.assertEqual(block_texts(""), [])
        self.assertEqual(block_texts("   "), [])


class ResolveMarkTests(SimpleTestCase):
    def test_in_place_is_returned_untouched(self):
        m = seg(0, 4, 35, GRACE)
        self.assertIs(resolve_mark([f"Lo! {GRACE}."], m), m)

    def test_no_anchor_cannot_be_checked(self):
        m = {"id": "g", "p": 5, "s": 0, "e": 3}
        self.assertIs(resolve_mark([], m), m)

    def test_shift_within_the_block(self):
        got = resolve_mark([f"And lo! {GRACE}."], seg(0, 4, 35, GRACE))
        self.assertEqual((got["p"], got["s"], got["e"]), (0, 8, 39))

    def test_nearest_occurrence_wins(self):
        text = f"{GRACE}. x {GRACE}."
        got = resolve_mark([text], seg(0, 40, 71, GRACE))
        self.assertEqual(got["s"], 35)

    def test_split_paragraph_moves_to_the_neighbour(self):
        got = resolve_mark(["Intro.", GRACE], seg(0, 7, -1, GRACE))
        self.assertEqual((got["p"], got["s"], got["e"]), (1, 0, -1))

    def test_short_anchor_stays_in_its_block(self):
        self.assertIsNone(resolve_mark(["x", "grace"], seg(0, 0, 5, "grace")))

    def test_gone_is_none(self):
        self.assertIsNone(resolve_mark(["Something else entirely."], seg(0, 0, 31, GRACE)))

    def test_offsets_count_utf16_like_the_browser(self):
        # 𝔊 is one code point but two UTF-16 units; the stored offsets are the
        # browser's, so the moved offset must be too.
        got = resolve_mark(["𝔊 " + GRACE], seg(0, 0, 31, GRACE))
        self.assertEqual(got["s"], 3)
        self.assertIs(resolve_mark(["𝔊 " + GRACE], got), got)


class ResolveGroupTests(SimpleTestCase):
    """The same cases as markAnchor.test.ts's resolveGroup — the two must agree."""

    PARAS = [
        "Title.",
        "He spoke of grace that is free to all who ask.",
        "Grace is the free favour of God to the undeserving.",
        "And so we rest.",
    ]
    SEGS = [
        seg(1, 12, 46, "grace that is free to all who ask."),
        seg(2, 0, 51, PARAS[2]),
        seg(3, 0, 6, "And so"),
    ]

    def test_in_place_is_untouched(self):
        self.assertEqual(resolve_group(self.PARAS, self.SEGS), self.SEGS)

    def test_short_tail_moves_with_the_run(self):
        shifted = ["Title.", "A new line.", *self.PARAS[1:]]
        self.assertEqual([m["p"] for m in resolve_group(shifted, self.SEGS)], [2, 3, 4])
        self.assertIsNone(resolve_mark(shifted, self.SEGS[2]))

    def test_short_tail_skips_other_words_in_its_old_block(self):
        shifted = ["Title.", "x", self.PARAS[1], self.PARAS[2] + " And so on.", self.PARAS[3]]
        self.assertEqual(resolve_mark(shifted, self.SEGS[2])["p"], 3)
        tail = resolve_group(shifted, self.SEGS)[2]
        self.assertEqual((tail["p"], tail["s"]), (4, 0))

    def test_lost_middle_guesses_no_further(self):
        split = ["Title.", self.PARAS[1], "Grace is the free favour of God", "to the undeserving.", self.PARAS[3]]
        out = resolve_group(split, self.SEGS)
        self.assertEqual((out[0]["p"], out[0]["s"]), (1, 12))
        self.assertIsNone(out[1])
        self.assertIsNone(out[2])

    def test_follows_a_split_in_the_first_block(self):
        split = ["Title.", "He spoke of", "grace that is free to all who ask.", *self.PARAS[2:]]
        out = resolve_group(split, self.SEGS)
        self.assertEqual([(m["p"], m["s"], m["e"]) for m in out], [(2, 0, 34), (3, 0, 51), (4, 0, 6)])

    def test_never_before_the_segment_ahead(self):
        repeated = ["Title.", "And so. " + self.PARAS[1], self.PARAS[2], "Then. And so we rest."]
        tail = resolve_group(repeated, self.SEGS)[2]
        self.assertEqual((tail["p"], tail["s"]), (3, 6))

    def test_short_first_segment_with_a_block_before_the_lead(self):
        two = [seg(1, 10, 19, "He spoke,", id="h"), seg(2, 0, 51, self.PARAS[2], id="h")]
        inserted = ["Title.", "And then, He spoke,", "A heading.", self.PARAS[2]]
        out = resolve_group(inserted, two)
        self.assertEqual([(m["p"], m["s"]) for m in out], [(1, 10), (3, 0)])

    def test_remap_moves_a_group_together(self):
        shifted = ["Title.", "A new line.", *self.PARAS[1:]]
        out, moved = remap_mark_list(self.SEGS, {"en": shifted}.get)
        self.assertEqual(moved, 3)
        self.assertEqual([m["p"] for m in out], [2, 3, 4])


class RemapListTests(SimpleTestCase):
    def test_only_tagged_anchored_marks_in_a_known_edition_move(self):
        texts = {"en": [f"New. {GRACE}"]}
        marks = [
            seg(0, 0, 31, GRACE, id="a"),
            {**seg(0, 0, 31, GRACE, id="b"), "lang": None},
            seg(0, 0, 31, GRACE, id="c", lang="fr"),
        ]
        out, moved = remap_mark_list(marks, texts.get)
        self.assertEqual(moved, 1)
        self.assertEqual({m["id"]: m["s"] for m in out}, {"a": 5, "b": 0, "c": 0})


class MergeIdentityTests(SimpleTestCase):
    def test_stale_offsets_match_the_remapped_mark(self):
        server = [seg(1, 0, 31, GRACE)]
        stale = [{**seg(0, 7, 38, GRACE), "note": "a longer note"}]
        merged = merge_mark_lists(server, stale)
        self.assertEqual(len(merged), 1)
        self.assertEqual((merged[0]["p"], merged[0]["s"]), (1, 0))
        self.assertEqual(merged[0]["note"], "a longer note")

    def test_anchor_wins_over_another_marks_new_range(self):
        # X and Y are whole-block marks shifted down one block by a repair. A
        # stale Y at its OLD range equals X's NEW range; it is still Y.
        x = {**seg(2, 0, -1, "First paragraph words here", id="x")}
        y = {**seg(3, 0, -1, "Second paragraph words here", id="y")}
        stale_y = {**seg(2, 0, -1, y["q"], id="y"), "note": "a note on Y"}
        merged = merge_mark_lists([x, y], [stale_y])
        self.assertEqual({m["id"]: m.get("note") for m in merged}, {"x": None, "y": "a note on Y"})

    def test_server_duplicates_collapse(self):
        both = [seg(1, 0, 31, GRACE), seg(0, 7, 38, GRACE)]
        self.assertEqual(len(merge_mark_lists(both, [])), 1)

    def test_other_groups_with_the_same_words_stay_apart(self):
        a, b = seg(0, 0, 31, GRACE, id="a"), seg(3, 0, 31, GRACE, id="b")
        self.assertEqual(len(merge_mark_lists([a], [b])), 2)

    def test_unanchored_server_copy_still_matches_by_range(self):
        server = [{"id": "g", "p": 0, "s": 0, "e": 31, "lang": "en"}]
        merged = merge_mark_lists(server, [seg(0, 0, 31, GRACE)])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["q"], GRACE)


class RefindBookmarkTests(SimpleTestCase):
    SNIP = "Grace is the free favour"

    def test_stays_when_the_paragraph_still_opens_with_it(self):
        self.assertIsNone(refind_bookmark([["x", GRACE]], 1, self.SNIP))

    def test_moves_to_the_nearest_match(self):
        self.assertEqual(refind_bookmark([["x", "y", GRACE]], 1, self.SNIP), 2)

    def test_any_edition_keeps_it(self):
        self.assertIsNone(refind_bookmark([["x", "y"], ["x", GRACE]], 1, self.SNIP))

    def test_whitespace_differences_are_ignored(self):
        self.assertIsNone(refind_bookmark([["Grace is\nthe  free favour of God"]], 0, self.SNIP))

    def test_short_or_missing_snippet_never_moves(self):
        self.assertIsNone(refind_bookmark([["x", "Amen"]], 0, "Amen"))
        self.assertIsNone(refind_bookmark([["x", "y"]], 0, self.SNIP))


class RemapCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="00000000-0000-0000-0000-0000000000f1")
        self.profile = UserProfile.objects.create(
            user=self.user, supabase_uid=self.user.username, email="remap@example.com"
        )
        author = Author.objects.create(slug="am", name="Andrew Murray")
        book = Book.objects.create(author=author, slug="grace", language="en", title="Grace")
        self.chapter = Chapter.objects.create(
            book=book, order=1, title="One", body_html=f"<p>Intro.</p><p>{GRACE}.</p>"
        )
        self.sermon = Sermon.objects.create(
            author=author, slug="s", language="en", title="S", body_html=f"<p>{GRACE}.</p>"
        )

    def run_remap(self, *args):
        out = io.StringIO()
        call_command("remap_marks", *args, stdout=out, stderr=io.StringIO())
        return out.getvalue()

    def repair(self, body):
        self.chapter.body_html = body
        self.chapter.save()

    def marks_row(self, p=1, s=0, kind="book", slug="grace"):
        return ChapterMarks.objects.create(
            profile=self.profile, kind=kind, book_slug=slug, chapter_order=1,
            language="en", marks=[seg(p, s, s + 31, GRACE)],
        )

    def test_moves_a_mark_whose_paragraph_split(self):
        row = self.marks_row()
        self.repair(f"<p>Intro.</p><p>Lo!</p><p>{GRACE}.</p>")
        self.assertIn("moved 1 highlight", self.run_remap())
        row.refresh_from_db()
        self.assertEqual((row.marks[0]["p"], row.marks[0]["s"]), (2, 0))

    def test_idempotent_and_writes_nothing_when_nothing_moved(self):
        row = self.marks_row()
        stamp = row.updated_at
        self.assertIn("moved 0 highlight", self.run_remap())
        row.refresh_from_db()
        self.assertEqual(row.updated_at, stamp)

    def test_dry_run_writes_nothing(self):
        row = self.marks_row()
        self.repair(f"<p>Intro.</p><p>Lo! {GRACE}.</p>")
        self.assertIn("would move 1", self.run_remap("--dry-run"))
        row.refresh_from_db()
        self.assertEqual(row.marks[0]["s"], 0)

    def test_sermons_too(self):
        row = self.marks_row(p=0, kind="sermon", slug="s")
        Sermon.objects.filter(pk=self.sermon.pk).update(body_html=f"<p>Hear this. {GRACE}.</p>")
        self.run_remap()
        row.refresh_from_db()
        self.assertEqual(row.marks[0]["s"], 11)

    def test_a_stale_push_after_the_remap_does_not_duplicate(self):
        self.marks_row()
        self.repair(f"<p>Intro.</p><p>Lo!</p><p>{GRACE}.</p>")
        self.run_remap()
        client = APIClient()
        client.force_authenticate(self.user)
        res = client.put(
            "/api/reading/marks/grace/1/",
            {"kind": "book", "language": "en", "marks": [seg(1, 0, 31, GRACE)], "deleted": {}},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        marks = ChapterMarks.objects.get(profile=self.profile).marks
        self.assertEqual([(m["p"], m["s"]) for m in marks], [(2, 0)])

    def bookmark(self, p, snippet=f"{GRACE}."):
        return Bookmark.objects.create(
            profile=self.profile, kind="book", book_slug="grace",
            chapter_order=1, paragraph_index=p, snippet=snippet,
        )

    def test_moves_a_bookmark_and_tombstones_the_old_spot(self):
        bm = self.bookmark(1)
        Removal.objects.create(
            profile=self.profile, domain="bookmark", kind="book", slug="grace",
            chapter_order=1, paragraph_index=2, removed_at="2026-01-01T00:00:00Z",
        )
        self.repair(f"<p>Intro.</p><p>Lo!</p><p>{GRACE}.</p>")
        self.run_remap()
        bm.refresh_from_db()
        self.assertEqual(bm.paragraph_index, 2)
        spots = set(Removal.objects.values_list("paragraph_index", flat=True))
        self.assertEqual(spots, {1})  # old spot tombstoned, new spot's lifted

    def test_a_bookmark_moving_onto_another_is_dropped(self):
        self.bookmark(1)
        self.bookmark(2, snippet="Lo!")
        self.repair(f"<p>Intro.</p><p>Lo!</p><p>{GRACE}.</p>")
        self.run_remap()
        self.assertEqual(list(Bookmark.objects.values_list("paragraph_index", flat=True)), [2])

    def test_a_shifted_run_of_bookmarks_all_survive(self):
        # A paragraph inserted before two adjacent bookmarks: the first must not
        # be dropped as a duplicate of the second before the second has moved.
        self.repair(f"<p>Intro.</p><p>{GRACE}.</p><p>Second paragraph words here.</p>")
        self.bookmark(1)
        self.bookmark(2, snippet="Second paragraph words here.")
        self.repair(f"<p>Intro.</p><p>Lo!</p><p>{GRACE}.</p><p>Second paragraph words here.</p>")
        self.run_remap()
        self.assertEqual(
            sorted(Bookmark.objects.values_list("paragraph_index", flat=True)), [2, 3]
        )
