"""The admin dashboard's read endpoints: stats, coverage, audit, engagement, export.

Moved out of the 6,500-line library/tests.py so a domain can be run — and
edited — on its own. Pure move: no test changed.
"""


from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from common.testing import body_of

from .models import (
    AdminAction,
    AuditDismissal,
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    Plan,
    PlanDay,
    Sermon,
)


class AdminStatsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray", bio="Preacher.")
        Author.objects.create(slug="cs", name="Charles Spurgeon")  # no bio

        en = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        Chapter.objects.create(book=en, order=1, title="One", body_html="<p>one two three</p>")
        Chapter.objects.create(book=en, order=2, title="Two", body_html="<p>four five</p>")
        # A published Swahili AI translation and an unpublished English draft.
        Book.objects.create(
            author=author,
            slug="humility",
            language="sw",
            title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Book.objects.create(
            author=author, slug="secret", language="en", title="Draft", is_published=False
        )
        Sermon.objects.create(
            author=author, slug="all-of-grace", language="en", title="All of Grace",
            body_html="<p>grace</p>",
        )
        Plan.objects.create(slug="p1", language="en", title="Plan One")

    @override_settings(DEBUG=True)
    def test_totals_and_language_breakdown(self):
        res = self.client.get("/api/admin/stats/")
        self.assertEqual(res.status_code, 200)
        totals = res.data["totals"]
        self.assertEqual(totals["works"], 2)  # humility, secret
        self.assertEqual(totals["books"], 3)
        self.assertEqual(totals["published_books"], 2)
        self.assertEqual(totals["unpublished_books"], 1)
        self.assertEqual(totals["chapters"], 2)
        self.assertEqual(totals["authors"], 2)
        self.assertEqual(totals["authors_with_bio"], 1)
        self.assertEqual(totals["languages"], 2)

        langs = {row["code"]: row for row in res.data["languages"]}
        self.assertEqual(langs["en"]["books"], 2)
        self.assertEqual(langs["en"]["chapters"], 2)
        self.assertEqual(langs["sw"]["source_types"]["ai_unreviewed"], 1)
        # English comes first (owner language), then by book count.
        self.assertEqual(res.data["languages"][0]["code"], "en")

    @override_settings(DEBUG=True)
    def test_attention_flags(self):
        res = self.client.get("/api/admin/stats/")
        attn = res.data["attention"]
        self.assertEqual(attn["unpublished_books"], 1)
        self.assertEqual(attn["unreviewed_translations"], 1)
        self.assertEqual(attn["authors_without_bio"], 1)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_forbidden_without_admin_email(self):
        # Anonymous → 401 (authenticate), a signed-in non-admin would get 403.
        res = self.client.get("/api/admin/stats/")
        self.assertIn(res.status_code, (401, 403))

    @override_settings(DEBUG=True)
    def test_language_bios_count(self):
        # A translated long-form bio counts toward the language's bios tally.
        from .models import Author

        murray = Author.objects.get(slug="am")
        murray.bio_html = "<p>Long English bio.</p>"
        murray.save(update_fields=["bio_html"])
        AuthorTranslation.objects.create(
            author=murray, language="sw", bio_html="<p>Wasifu.</p>", reviewed=True
        )
        langs = {row["code"]: row for row in self.client.get("/api/admin/stats/").data["languages"]}
        self.assertEqual(langs["en"]["bios"], 1)
        self.assertEqual(langs["sw"]["bios"], 1)


class AdminLanguageDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.murray = Author.objects.create(
            slug="am", name="Andrew Murray", bio="Preacher.", bio_html="<p>Bio.</p>"
        )
        # Two published English books; one translated to Swahili.
        for i, slug in enumerate(("humility", "abide", "with-christ")):
            b = Book.objects.create(
                author=self.murray, slug=slug, language="en", title=slug.title(),
                sort_order=i,
            )
            Chapter.objects.create(book=b, order=1, title="One", body_html="<p>x</p>")
        Book.objects.create(
            author=self.murray, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        Sermon.objects.create(
            author=self.murray, slug="grace", language="en", title="Grace",
            body_html="<p>g</p>",
        )
        Plan.objects.create(slug="p1", language="en", title="Plan One")

    @override_settings(DEBUG=True)
    def test_present_and_todo_for_translation_language(self):
        res = self.client.get("/api/admin/languages/sw/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["is_source"])
        self.assertEqual(res.data["language"]["name"], "Swahili")

        # Present: the one translated book, nothing else yet.
        self.assertEqual([b["slug"] for b in res.data["books"]], ["humility"])
        self.assertEqual(res.data["sermons"], [])

        # Todo: highest-priority English books not yet in Swahili, by sort_order,
        # excluding the already-translated "humility".
        todo_slugs = [b["slug"] for b in res.data["todo"]["books"]]
        self.assertEqual(todo_slugs, ["abide", "with-christ"])
        self.assertEqual([s["slug"] for s in res.data["todo"]["sermons"]], ["grace"])
        self.assertEqual([p["slug"] for p in res.data["todo"]["plans"]], ["p1"])
        # Murray's bio isn't translated to Swahili yet → he's a bio todo.
        self.assertEqual([a["slug"] for a in res.data["todo"]["bios"]], ["am"])

        self.assertEqual(res.data["english_counts"]["books"], 3)

    @override_settings(DEBUG=True)
    def test_sermon_todo_round_robins_across_authors(self):
        # Five more Murray sermons would fill the todo list by sort_order alone;
        # the list should instead lead with one sermon per preacher and only
        # repeat an author once every preacher is represented.
        moody = Author.objects.create(slug="dm", name="Dwight Moody", bio="P.")
        for i, slug in enumerate(("m1", "m2", "m3", "m4", "m5"), start=1):
            Sermon.objects.create(
                author=self.murray, slug=slug, language="en", title=slug.upper(),
                body_html="<p>x</p>", sort_order=i,
            )
        Sermon.objects.create(
            author=moody, slug="fire", language="en", title="Fire",
            body_html="<p>f</p>", sort_order=99,
        )
        todo = self.client.get("/api/admin/languages/sw/").data["todo"]["sermons"]
        # Murray's best ("grace", sort_order 0), then Moody's only sermon despite
        # its low priority, then back to Murray's queue in order once Moody's is
        # exhausted. (Six candidates here, under TODO_LIMIT, so none are cut.)
        self.assertEqual(
            [s["slug"] for s in todo], ["grace", "fire", "m1", "m2", "m3", "m4", "m5"]
        )

    @override_settings(DEBUG=True)
    def test_bio_todo_ranks_by_how_much_the_author_carries(self):
        """The bio queue leads with the authors most of the library hangs off.

        A translated bio is what a reader reaches from any of that author's
        works, so it pays back in proportion to how many they have. Murray
        (3 books + 1 sermon here) must outrank an author with a single sermon,
        whatever the alphabet says.
        """
        prolific = Author.objects.create(
            slug="zz-many", name="Zebedee Many", bio="P.", bio_html="<p>b</p>"
        )
        for i, slug in enumerate(("z1", "z2", "z3", "z4"), start=1):
            Sermon.objects.create(
                author=prolific, slug=slug, language="en", title=slug.upper(),
                body_html="<p>x</p>", sort_order=i,
            )
        Author.objects.create(
            slug="aa-one", name="Aaron One", bio="P.", bio_html="<p>b</p>"
        )
        todo = self.client.get("/api/admin/languages/sw/").data["todo"]["bios"]
        # Zebedee (4 works) first, Murray (3 books + 1 sermon) — tied on total,
        # but books break the tie — then Aaron, who carries nothing, last
        # despite sorting first alphabetically.
        self.assertEqual([a["slug"] for a in todo], ["am", "zz-many", "aa-one"])
        self.assertEqual(todo[0]["book_count"], 3)
        self.assertEqual(todo[0]["sermon_count"], 1)
        self.assertEqual(todo[2]["book_count"], 0)

    @override_settings(DEBUG=True)
    def test_source_language_has_no_todo(self):
        res = self.client.get("/api/admin/languages/en/")
        self.assertTrue(res.data["is_source"])
        self.assertEqual(len(res.data["books"]), 3)
        self.assertEqual(res.data["todo"]["books"], [])
        self.assertEqual([a["slug"] for a in res.data["bios"]], ["am"])

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/languages/sw/")
        self.assertIn(res.status_code, (401, 403))


class AdminCoverageTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        Book.objects.create(author=author, slug="humility", language="en", title="Humility", sort_order=0)
        Book.objects.create(
            author=author, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED, sort_order=0,
        )
        Book.objects.create(author=author, slug="abide", language="en", title="Abide", sort_order=1)
        Sermon.objects.create(author=author, slug="grace", language="en", title="Grace", body_html="<p>g</p>")
        Plan.objects.create(slug="p1", language="es", title="Plan Uno")

    @override_settings(DEBUG=True)
    def test_matrix_shape_and_cells(self):
        res = self.client.get("/api/admin/coverage/")
        self.assertEqual(res.status_code, 200)

        # Columns are the union of all content languages, English first.
        codes = [lang["code"] for lang in res.data["languages"]]
        self.assertEqual(codes[0], "en")
        self.assertEqual(set(codes), {"en", "sw", "es"})

        books = {b["slug"]: b for b in res.data["books"]}
        # Canonical title comes from the English row; cells carry source_type.
        self.assertEqual(books["humility"]["title"], "Humility")
        self.assertEqual(books["humility"]["cells"]["en"], "public_domain")
        self.assertEqual(books["humility"]["cells"]["sw"], "ai_unreviewed")
        self.assertNotIn("es", books["humility"]["cells"])  # missing → absent
        # Rows ordered by sort_order.
        self.assertEqual([b["slug"] for b in res.data["books"]], ["humility", "abide"])

        self.assertEqual(res.data["sermons"][0]["cells"], {"en": "present"})
        self.assertEqual(res.data["plans"][0]["cells"], {"es": "present"})

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/coverage/")
        self.assertIn(res.status_code, (401, 403))


class AdminReviewQueueTests(TestCase):
    def setUp(self):

        self.client = APIClient()
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=self.author, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        # A reviewed book and a public-domain original should NOT appear.
        Book.objects.create(
            author=self.author, slug="abide", language="es", title="Permaneced",
            source_type=Book.SourceType.AI_REVIEWED,
        )
        Book.objects.create(author=self.author, slug="humility", language="en", title="Humility")
        self.tr = AuthorTranslation.objects.create(
            author=self.author, language="sw", bio_html="<p>Wasifu.</p>", reviewed=False
        )
        AuthorTranslation.objects.create(
            author=self.author, language="es", bio="Bio.", reviewed=True
        )  # reviewed → excluded

    @override_settings(DEBUG=True)
    def test_lists_only_unreviewed(self):
        # The payload is a single filtered/paged `results` list across all three
        # content types, not per-type arrays — sermons were invisible while the
        # shape was {books, bios}. See tests_review_queue for the full contract.
        res = self.client.get("/api/admin/review-queue/")
        self.assertEqual(res.status_code, 200)
        rows = res.data["results"]
        books = [r for r in rows if r["kind"] == "book"]
        bios = [r for r in rows if r["kind"] == "bio"]
        self.assertEqual([b["slug"] for b in books], ["humility"])
        self.assertEqual(books[0]["language"], "sw")
        self.assertEqual([b["language"] for b in bios], ["sw"])
        self.assertTrue(bios[0]["has_long"])

    @override_settings(DEBUG=True)
    def test_approve_book_flips_source_type(self):
        res = self.client.post(
            "/api/admin/review-queue/",
            {"kind": "book", "slug": "humility", "language": "sw"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.book.refresh_from_db()
        self.assertEqual(self.book.source_type, Book.SourceType.AI_REVIEWED)
        # It drops out of the queue afterwards.
        follow = self.client.get("/api/admin/review-queue/")
        self.assertEqual([r for r in follow.data["results"] if r["kind"] == "book"], [])

    @override_settings(DEBUG=True)
    def test_approve_bio_marks_reviewed(self):
        res = self.client.post(
            "/api/admin/review-queue/",
            {"kind": "bio", "slug": "am", "language": "sw"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.tr.refresh_from_db()
        self.assertTrue(self.tr.reviewed)

    @override_settings(DEBUG=True)
    def test_approve_public_domain_book_rejected(self):
        res = self.client.post(
            "/api/admin/review-queue/",
            {"kind": "book", "slug": "humility", "language": "en"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    @override_settings(DEBUG=True)
    def test_bad_payload_rejected(self):
        res = self.client.post(
            "/api/admin/review-queue/", {"kind": "book"}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/review-queue/")
        self.assertIn(res.status_code, (401, 403))


class AdminAuditTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(author=self.author, slug="humility", language="en", title="Humility")
        # ch1: generic title + doesn't end in terminal punctuation (mid-split, has next).
        Chapter.objects.create(book=self.book, order=1, title="Chapter I", body_html="<p>text runs on</p>")
        # ch2: empty chapter (also an order gap will exist since order 3 skipped).
        Chapter.objects.create(book=self.book, order=2, title="Real Title", body_html="")
        # ch4: starts lowercase (missing drop cap); order 3 is missing → gap.
        Chapter.objects.create(book=self.book, order=4, title="Good", body_html="<p>and so it began.</p>")
        # A book with no chapters at all.
        Book.objects.create(author=self.author, slug="empty", language="en", title="Empty Book")
        # A plan whose day points at a non-existent chapter.
        plan = Plan.objects.create(slug="p1", language="en", title="Plan One")
        PlanDay.objects.create(plan=plan, day=1, book_slug="humility", chapter_order=1)  # valid
        PlanDay.objects.create(plan=plan, day=2, book_slug="humility", chapter_order=99)  # broken

    @override_settings(DEBUG=True)
    def test_quality_checks(self):
        res = self.client.get("/api/admin/audit/")
        self.assertEqual(res.status_code, 200)
        q = res.data["quality"]
        gen = [(f["book"], f["order"]) for f in q["generic_titles"]["items"]]
        self.assertIn(("humility", 1), gen)
        mids = [(f["book"], f["order"]) for f in q["mid_sentence_splits"]["items"]]
        self.assertIn(("humility", 1), mids)  # order 1, has a later chapter, no terminal punct
        drops = [(f["book"], f["order"]) for f in q["missing_dropcap"]["items"]]
        self.assertIn(("humility", 4), drops)

    @override_settings(DEBUG=True)
    def test_integrity_checks(self):
        res = self.client.get("/api/admin/audit/")
        integ = res.data["integrity"]
        self.assertIn("empty", [b["book"] for b in integ["empty_books"]["items"]])
        self.assertIn(("humility", 2), [(c["book"], c["order"]) for c in integ["empty_chapters"]["items"]])
        gaps = {g["book"]: g["missing"] for g in integ["order_gaps"]["items"]}
        self.assertEqual(gaps.get("humility"), [3])
        broken = [(d["plan"], d["day"]) for d in integ["broken_plan_days"]["items"]]
        self.assertEqual(broken, [("p1", 2)])

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/audit/")
        self.assertIn(res.status_code, (401, 403))


class AdminAuditMultiLanguageTests(TestCase):
    """The audit against the content model it actually runs on.

    Books are per-language ROWS sharing a slug, and every check above was
    written against a one-language fixture — which is how the audit came to
    group chapters by slug alone. That pooled unrelated editions: it reported
    17 cross-language title collisions as duplicates "in a book", and it left
    the API emitting findings that no longer had a unique identity, which
    crashed the admin page outright.
    """

    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        # One work, three editions — the shape the whole content model is built
        # around, and the shape the single-language fixture above never had.
        for lang in ("en", "es", "pt"):
            book = Book.objects.create(
                author=author, slug="humility", language=lang, title="Humility"
            )
            # Same defect in every edition: a body with no terminal punctuation,
            # in a chapter that has a later one. One finding per edition.
            Chapter.objects.create(
                book=book, order=1, title="One", body_html="<p>runs on</p>"
            )
            Chapter.objects.create(
                book=book, order=2, title="Two", body_html="<p>Ends well.</p>"
            )

    @override_settings(DEBUG=True)
    def test_a_finding_in_three_editions_keeps_three_identities(self):
        """The crash: a page cannot key rows that aren't distinguishable."""
        res = self.client.get("/api/admin/audit/")
        splits = res.data["quality"]["mid_sentence_splits"]["items"]
        mine = [f for f in splits if f["book"] == "humility"]
        self.assertEqual(len(mine), 3, "one finding per edition")
        keys = {(f["book"], f["language"], f["order"]) for f in mine}
        self.assertEqual(len(keys), 3, "book+language+order must be unique")

    @override_settings(DEBUG=True)
    def test_every_chapter_finding_is_uniquely_identified(self):
        """Asserted over every list, so a new check inherits the guarantee."""
        res = self.client.get("/api/admin/audit/")
        lists = {**res.data["quality"], **res.data["integrity"]}
        checked = 0
        for name, capped in lists.items():
            items = capped["items"]
            if not items or "order" not in items[0]:
                continue
            checked += 1
            keys = [(f["book"], f["language"], f["order"]) for f in items]
            self.assertEqual(
                len(keys), len(set(keys)), f"{name} has two findings with one identity"
            )
        self.assertTrue(checked, "no chapter-finding list was examined")

    @override_settings(DEBUG=True)
    def test_the_same_title_in_two_editions_is_not_a_duplicate(self):
        """A proper noun that survives translation is not a defect.

        "Hazelglen Fellowship" as chapter 19 of en, lg, pt and sw is one
        untranslated name, and the audit reported it as four duplicates.
        """
        res = self.client.get("/api/admin/audit/")
        dupes = res.data["quality"]["duplicate_titles"]["items"]
        self.assertEqual([d for d in dupes if d["book"] == "humility"], [])

    @override_settings(DEBUG=True)
    def test_a_real_duplicate_within_one_edition_still_reports(self):
        """The check must still do its job — and say which edition."""
        es = Book.objects.get(slug="humility", language="es")
        Chapter.objects.create(
            book=es, order=3, title="One", body_html="<p>Again.</p>"
        )
        res = self.client.get("/api/admin/audit/")
        dupes = res.data["quality"]["duplicate_titles"]["items"]
        mine = [d for d in dupes if d["book"] == "humility"]
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0]["language"], "es")
        self.assertEqual(mine[0]["title"], "One")

    @override_settings(DEBUG=True)
    def test_a_gap_in_one_edition_is_not_masked_by_another(self):
        """Spanish is missing chapter 2; English has it. That is still a gap.

        Pooled by slug, English's chapter 2 filled the hole in Spanish and the
        gap went unreported — a false negative in the check whose entire job is
        noticing a missing chapter.
        """
        Chapter.objects.filter(book__slug="humility", book__language="es", order=2).delete()
        es = Book.objects.get(slug="humility", language="es")
        Chapter.objects.create(
            book=es, order=3, title="Three", body_html="<p>Third.</p>"
        )
        res = self.client.get("/api/admin/audit/")
        gaps = res.data["integrity"]["order_gaps"]["items"]
        mine = [g for g in gaps if g["book"] == "humility"]
        self.assertEqual(len(mine), 1, "the Spanish gap must be reported")
        self.assertEqual(mine[0]["language"], "es")
        self.assertEqual(mine[0]["missing"], [2])


@override_settings(DEBUG=True)
class AdminAuditDismissTests(TestCase):
    """Accepting an advisory quality finding removes it and stays undoable."""

    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        book = Book.objects.create(
            author=author, slug="humility", language="en", title="Humility"
        )
        # Two giant chapters (> GIANT_MIN words) — an advisory quality finding.
        big = "<p>" + ("word " * 9000) + "</p>"
        Chapter.objects.create(book=book, order=1, title="One", body_html=big)
        Chapter.objects.create(book=book, order=2, title="Two", body_html=big)

    def _giants(self):
        res = self.client.get("/api/admin/audit/")
        return res.data["quality"]["giant_chapters"]

    def test_dismiss_removes_finding_and_counts_it(self):
        self.assertEqual(self._giants()["total"], 2)
        res = self.client.post(
            "/api/admin/audit/dismiss/",
            {"check": "giant_chapters", "book": "humility", "language": "en",
             "ref": "1", "note": "a legitimately long chapter"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["created"])
        giants = self._giants()
        self.assertEqual(giants["total"], 1, "the accepted finding is gone")
        self.assertEqual(giants["dismissed"], 1, "and counted")
        self.assertEqual([f["order"] for f in giants["items"]], [2])

    def test_dismiss_is_idempotent(self):
        body = {"check": "giant_chapters", "book": "humility", "language": "en", "ref": "1"}
        first = self.client.post("/api/admin/audit/dismiss/", body, format="json")
        second = self.client.post("/api/admin/audit/dismiss/", body, format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.data["created"])
        self.assertEqual(AuditDismissal.objects.count(), 1)

    def test_undo_restores_the_finding(self):
        body = {"check": "giant_chapters", "book": "humility", "language": "en", "ref": "1"}
        self.client.post("/api/admin/audit/dismiss/", body, format="json")
        self.assertEqual(self._giants()["total"], 1)
        # Undo carries its target in the query string (like undoReview).
        res = self.client.delete(
            "/api/admin/audit/dismiss/?check=giant_chapters&book=humility&language=en&ref=1"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(self._giants()["total"], 2, "the finding is back")
        self.assertEqual(self._giants()["dismissed"], 0)

    def test_undo_of_nothing_is_404(self):
        res = self.client.delete(
            "/api/admin/audit/dismiss/?check=giant_chapters&book=humility&language=en&ref=9"
        )
        self.assertEqual(res.status_code, 404)

    def test_integrity_checks_are_not_dismissible(self):
        for check in ("empty_chapters", "empty_books", "order_gaps", "broken_plan_days"):
            res = self.client.post(
                "/api/admin/audit/dismiss/",
                {"check": check, "book": "humility", "language": "en", "ref": "1"},
                format="json",
            )
            self.assertEqual(res.status_code, 400, f"{check} must be refused")
        self.assertEqual(AuditDismissal.objects.count(), 0)

    def test_duplicate_titles_dismissed_by_title(self):
        book = Book.objects.get(slug="humility", language="en")
        Chapter.objects.create(book=book, order=3, title="One", body_html="<p>Short.</p>")
        res = self.client.get("/api/admin/audit/")
        self.assertEqual(res.data["quality"]["duplicate_titles"]["total"], 1)
        self.client.post(
            "/api/admin/audit/dismiss/",
            {"check": "duplicate_titles", "book": "humility", "language": "en", "ref": "One"},
            format="json",
        )
        res = self.client.get("/api/admin/audit/")
        self.assertEqual(res.data["quality"]["duplicate_titles"]["total"], 0)
        self.assertEqual(res.data["quality"]["duplicate_titles"]["dismissed"], 1)

    def test_dismiss_is_recorded_as_an_admin_action(self):
        self.client.post(
            "/api/admin/audit/dismiss/",
            {"check": "giant_chapters", "book": "humility", "language": "en", "ref": "1"},
            format="json",
        )
        action = AdminAction.objects.latest("at")
        self.assertEqual(action.action, AdminAction.Action.AUDIT_DISMISS)
        self.assertEqual(action.target, "giant_chapters:humility:en")

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.post(
            "/api/admin/audit/dismiss/",
            {"check": "giant_chapters", "book": "humility", "language": "en", "ref": "1"},
            format="json",
        )
        self.assertIn(res.status_code, (401, 403))


class AdminEngagementTests(TestCase):
    def setUp(self):
        import uuid

        from django.contrib.auth import get_user_model

        from accounts.models import UserProfile
        from reading.models import ChapterMarks, ReadingProgress

        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        book = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        for i in (1, 2, 3):
            Chapter.objects.create(book=book, order=i, title=f"C{i}", body_html="<p>x</p>")
        Book.objects.create(author=author, slug="abide", language="en", title="Abide")

        User = get_user_model()
        self.p1 = UserProfile.objects.create(user=User.objects.create(username=str(uuid.uuid4())), supabase_uid=uuid.uuid4())
        self.p2 = UserProfile.objects.create(user=User.objects.create(username=str(uuid.uuid4())), supabase_uid=uuid.uuid4())

        # p1 finished humility (ch3 of 3) + started abide; p2 at humility ch1.
        ReadingProgress.objects.create(profile=self.p1, book_slug="humility", language="en", chapter_order=3)
        ReadingProgress.objects.create(profile=self.p2, book_slug="humility", language="en", chapter_order=1)
        ReadingProgress.objects.create(profile=self.p1, book_slug="abide", language="en", chapter_order=1)
        ChapterMarks.objects.create(
            profile=self.p1, book_slug="humility", language="en", chapter_order=1,
            marks=[{"id": "a", "p": 0, "s": 0, "e": 5}],
        )

    @override_settings(DEBUG=True)
    def test_overview_and_rollups(self):
        res = self.client.get("/api/admin/engagement/")
        self.assertEqual(res.status_code, 200)
        ov = res.data["overview"]
        self.assertEqual(ov["readers"], 2)
        self.assertEqual(ov["total_users"], 2)
        self.assertEqual(ov["active_7d"], 2)
        self.assertEqual(ov["readers_with_marks"], 1)
        self.assertEqual(ov["marked_chapters"], 1)

        most = {b["slug"]: b for b in res.data["most_read"]}
        self.assertEqual(most["humility"]["readers"], 2)
        self.assertEqual(most["humility"]["finishers"], 1)  # only p1 reached ch3
        self.assertEqual(most["abide"]["readers"], 1)

        self.assertEqual(res.data["most_marked"][0]["slug"], "humility")
        by_lang = {r["code"]: r["readers"] for r in res.data["by_language"]}
        self.assertEqual(by_lang["en"], 2)
        # 8 weekly buckets; this week has activity.
        self.assertEqual(len(res.data["weekly_active"]), 8)
        self.assertEqual(res.data["weekly_active"][-1]["readers"], 2)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/engagement/")
        self.assertIn(res.status_code, (401, 403))


class AdminUsersTests(TestCase):
    def setUp(self):
        import uuid

        from django.contrib.auth import get_user_model

        from accounts.models import UserProfile
        from reading.models import ReadingProgress

        self.client = APIClient()
        User = get_user_model()

        def mk(locale="en", theme="paper", providers="", display_name="", email=""):
            u = User.objects.create(username=str(uuid.uuid4()))
            return UserProfile.objects.create(
                user=u,
                supabase_uid=uuid.uuid4(),
                locale=locale,
                theme=theme,
                providers=providers,
                display_name=display_name,
                email=email,
            )

        self.p1 = mk("en", "dark", providers="google", email="a@example.com")
        self.p2 = mk("sw", "paper", providers="email,google", display_name="Bea", email="b@example.com")
        self.p3 = mk("en", "paper")  # dormant (no progress), no provider recorded
        ReadingProgress.objects.create(profile=self.p1, book_slug="humility", language="en")
        ReadingProgress.objects.create(profile=self.p2, book_slug="humility", language="sw")

    @override_settings(DEBUG=True)
    def test_users_analytics(self):
        res = self.client.get("/api/admin/users/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["total"], 3)
        self.assertEqual(res.data["with_activity"], 2)
        self.assertEqual(res.data["dormant"], 1)
        self.assertEqual(res.data["signups_7d"], 3)

        by_locale = {r["code"]: r["count"] for r in res.data["by_locale"]}
        self.assertEqual(by_locale["en"], 2)
        self.assertEqual(by_locale["sw"], 1)
        by_theme = {r["theme"]: r["count"] for r in res.data["by_theme"]}
        self.assertEqual(by_theme["paper"], 2)
        self.assertEqual(by_theme["dark"], 1)

        self.assertEqual(len(res.data["weekly_signups"]), 12)
        self.assertEqual(res.data["weekly_signups"][-1]["count"], 3)  # all signed up this week

    @override_settings(DEBUG=True)
    def test_by_method_counts_overlap_and_unknown(self):
        res = self.client.get("/api/admin/users/")
        by_method = {r["method"]: r["count"] for r in res.data["by_method"]}
        # google: p1 + p2; email: p2 only; unknown: p3 (nothing recorded).
        self.assertEqual(by_method["google"], 2)
        self.assertEqual(by_method["email"], 1)
        self.assertEqual(by_method["unknown"], 1)
        labels = {r["method"]: r["label"] for r in res.data["by_method"]}
        self.assertEqual(labels["google"], "Google")
        self.assertEqual(labels["email"], "Email")

    @override_settings(DEBUG=True)
    def test_recent_lists_individuals_newest_first(self):
        res = self.client.get("/api/admin/users/")
        recent = res.data["recent"]
        self.assertEqual(len(recent), 3)
        # Newest first: p3 was created last.
        self.assertEqual(recent[0]["email"], self.p3.email)
        bea = next(r for r in recent if r["email"] == "b@example.com")
        self.assertEqual(bea["display_name"], "Bea")
        # Providers carry their server label so the frontend needs no map.
        self.assertEqual(
            bea["providers"],
            [{"code": "email", "label": "Email"}, {"code": "google", "label": "Google"}],
        )
        self.assertIn("joined_at", bea)
        self.assertIn("last_seen_at", bea)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/users/")
        self.assertIn(res.status_code, (401, 403))


class AdminBookDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        en = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        # ch1 has a next and doesn't end in punctuation → mid-split (+ no drop cap);
        # ch2 has a generic title and ends fine.
        Chapter.objects.create(book=en, order=1, title="Real", body_html=body_of(300))
        Chapter.objects.create(book=en, order=2, title="Chapter II", body_html=body_of(200, end="."))
        Book.objects.create(
            author=author, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )

    @override_settings(DEBUG=True)
    def test_book_detail_across_languages(self):
        res = self.client.get("/api/admin/books/humility/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["title"], "Humility")
        self.assertEqual(res.data["author"]["slug"], "am")

        langs = {lang["code"]: lang for lang in res.data["languages"]}
        self.assertEqual(res.data["languages"][0]["code"], "en")  # English first
        self.assertEqual(langs["en"]["word_count"], 500)
        chapters = {c["order"]: c for c in langs["en"]["chapters"]}
        self.assertIn("mid-split", chapters[1]["flags"])
        self.assertIn("generic-title", chapters[2]["flags"])
        self.assertNotIn("mid-split", chapters[2]["flags"])  # last chapter, no next
        self.assertEqual(langs["sw"]["source_type"], "ai_unreviewed")

    @override_settings(DEBUG=True)
    def test_unknown_slug_404(self):
        res = self.client.get("/api/admin/books/nope/")
        self.assertEqual(res.status_code, 404)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/books/humility/")
        self.assertIn(res.status_code, (401, 403))


class AdminExportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray", bio="x")
        b = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        Chapter.objects.create(book=b, order=1, title="One", body_html=body_of(100))
        Sermon.objects.create(author=author, slug="grace", language="en", title="Grace", body_html=body_of(50))
        Plan.objects.create(slug="p1", language="en", title="Plan One")

    @override_settings(DEBUG=True)
    def test_json_inventory(self):
        res = self.client.get("/api/admin/export/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["books"][0]["chapters"], 1)
        self.assertEqual(res.data["books"][0]["words"], 100)
        self.assertEqual(res.data["sermons"][0]["slug"], "grace")
        self.assertEqual(res.data["plans"][0]["slug"], "p1")
        self.assertEqual(res.data["authors"][0]["has_bio"], True)

    @override_settings(DEBUG=True)
    def test_csv_inventory(self):
        res = self.client.get("/api/admin/export/?fmt=csv")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=", res["Content-Disposition"])
        body = res.content.decode()
        self.assertIn("type,slug,language,title", body)
        self.assertIn("book,humility,en,Humility", body)
        self.assertIn("sermon,grace,en,Grace", body)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/export/")
        self.assertIn(res.status_code, (401, 403))
