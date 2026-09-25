"""The admin dashboard's read endpoints: stats, coverage, audit, engagement, export.

Moved out of the 6,500-line library/tests.py so a domain can be run — and
edited — on its own. Pure move: no test changed.
"""


from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from common.testing import body_of

from .models import (
    AdminAction,
    Article,
    AuditDismissal,
    Author,
    AuthorTranslation,
    Book,
    Chapter,
    ContentRevision,
    Plan,
    PlanDay,
    SearchQueryLog,
    Series,
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

    @override_settings(DEBUG=True)
    def test_language_articles_count(self):
        # Articles are authorless per-language rows on a shared slug; each row
        # counts toward its own language's articles tally.
        Article.objects.create(slug="what-is-grace", language="en", h1="What is grace?")
        Article.objects.create(slug="what-is-faith", language="en", h1="What is faith?")
        Article.objects.create(
            slug="what-is-grace",
            language="sw",
            h1="Neema ni nini?",
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        langs = {row["code"]: row for row in self.client.get("/api/admin/stats/").data["languages"]}
        self.assertEqual(langs["en"]["articles"], 2)
        self.assertEqual(langs["sw"]["articles"], 1)


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
    def test_articles_present_and_todo(self):
        # Two published English articles; one translated to Swahili (unreviewed).
        for i, slug in enumerate(("what-is-grace", "what-is-faith")):
            Article.objects.create(
                slug=slug, language="en", h1=slug.replace("-", " ").title(),
                body_html="<p>x</p>", sort_order=i, is_published=True,
            )
        Article.objects.create(
            slug="what-is-grace", language="sw", h1="Neema Ni Nini?",
            body_html="<p>x</p>", is_published=True,
            source_type=Book.SourceType.AI_UNREVIEWED,
        )
        res = self.client.get("/api/admin/languages/sw/")
        self.assertEqual(res.status_code, 200)
        # Present: the one translated article, carrying its review state so the
        # admin row can badge it.
        self.assertEqual([a["slug"] for a in res.data["articles"]], ["what-is-grace"])
        self.assertEqual(res.data["articles"][0]["source_type"], "ai_unreviewed")
        # Todo: the still-untranslated English article only.
        self.assertEqual(
            [a["slug"] for a in res.data["todo"]["articles"]], ["what-is-faith"]
        )
        self.assertEqual(res.data["english_counts"]["articles"], 2)

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
        # A content row in a code the translation registry never adopted: it is a
        # matrix column, but the queue can't accept it (see test_marks_queueable).
        Book.objects.create(author=author, slug="humility", language="zz", title="Humility zz", sort_order=0)

    @override_settings(DEBUG=True)
    def test_matrix_shape_and_cells(self):
        res = self.client.get("/api/admin/coverage/")
        self.assertEqual(res.status_code, 200)

        # Columns are the union of all content languages, English first.
        codes = [lang["code"] for lang in res.data["languages"]]
        self.assertEqual(codes[0], "en")
        self.assertEqual(set(codes), {"en", "sw", "es", "zz"})

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

    @override_settings(DEBUG=True)
    def test_marks_queueable(self):
        # queueable == the translation-jobs POST would accept the language:
        # a registered non-English target, never English, never a stray code.
        res = self.client.get("/api/admin/coverage/")
        queueable = {lang["code"]: lang["queueable"] for lang in res.data["languages"]}
        self.assertFalse(queueable["en"])  # the source language
        self.assertTrue(queueable["sw"])  # registered target
        self.assertTrue(queueable["es"])  # registered target
        self.assertFalse(queueable["zz"])  # content exists, but not a known code

    @override_settings(DEBUG=True)
    def test_reports_unmet_search_demand_per_language(self):
        # Zero-result searches in a language are demand its content isn't
        # answering — surfaced on the column so it can steer what to translate.
        SearchQueryLog.objects.create(query="wendy bello", language="es", result_count=0)
        SearchQueryLog.objects.create(query="jose luis navajo", language="es", result_count=0)
        SearchQueryLog.objects.create(query="prayer", language="es", result_count=7)  # answered
        SearchQueryLog.objects.create(query="humility", language="sw", result_count=0)
        res = self.client.get("/api/admin/coverage/")
        unmet = {lang["code"]: lang["unmet_searches"] for lang in res.data["languages"]}
        self.assertEqual(unmet["es"], 2)  # two zero-result; the answered one excluded
        self.assertEqual(unmet["sw"], 1)
        self.assertEqual(unmet["en"], 0)

    @override_settings(DEBUG=True)
    def test_bios_matrix(self):
        # Row = author. English cell is the original Author.bio_html; a translated
        # cell carries the review state; a bio counts only when its LONG-form body
        # is present (a short-bio-only translation is not a bio in the matrix).
        author = Author.objects.get(slug="am")
        author.bio_html = "<p>Life of Andrew Murray.</p>"
        author.save()
        AuthorTranslation.objects.create(author=author, language="sw", bio_html="<p>Maisha.</p>", reviewed=True)
        AuthorTranslation.objects.create(author=author, language="es", bio_html="<p>Vida.</p>", reviewed=False)
        booth = Author.objects.create(slug="cb", name="Catherine Booth", bio_html="<p>Booth.</p>")
        AuthorTranslation.objects.create(author=booth, language="sw", bio="short only", reviewed=True)

        res = self.client.get("/api/admin/coverage/")
        bios = {b["slug"]: b for b in res.data["bios"]}
        self.assertEqual(bios["am"]["title"], "Andrew Murray")
        self.assertEqual(bios["am"]["cells"]["en"], "present")
        self.assertEqual(bios["am"]["cells"]["sw"], "ai_reviewed")
        self.assertEqual(bios["am"]["cells"]["es"], "ai_unreviewed")
        # Booth has only an English bio; the short-only sw translation isn't present.
        self.assertEqual(bios["cb"]["cells"], {"en": "present"})
        # Rows sorted by author name.
        self.assertEqual([b["slug"] for b in res.data["bios"]], ["am", "cb"])

    @override_settings(DEBUG=True)
    def test_book_rows_carry_their_series(self):
        # The Books matrix narrows to one series (the admin's "queue the whole
        # series into Swahili"), so each book row names its series and volume,
        # and the payload lists the series to choose from.
        author = Author.objects.create(slug="oo", name="Ochorus")
        rooted = Series.objects.create(slug="rooted", title="Rooted")
        for n in (1, 2):
            Book.objects.create(
                author=author, slug=f"rooted-{n}", language="en", title=f"Rooted {n}",
                series=rooted, series_position=n,
            )
        Book.objects.create(author=author, slug="solo", language="en", title="Solo")

        res = self.client.get("/api/admin/coverage/")
        by_slug = {b["slug"]: b for b in res.data["books"]}
        self.assertEqual(
            (by_slug["rooted-2"]["series"], by_slug["rooted-2"]["series_position"]), ("rooted", 2)
        )
        self.assertNotIn("series", by_slug["solo"])
        self.assertIn({"slug": "rooted", "title": "Rooted"}, res.data["series"])

    @override_settings(DEBUG=True)
    def test_articles_matrix(self):
        # Row = article slug, titled by the English h1. The English original is
        # site writing, so it reads "present" (not PD); a translated cell carries
        # its review state. An article-only language still becomes a column.
        Article.objects.create(slug="trust", language="en", h1="How to Trust God", body_html="<p>t</p>", sort_order=1)
        Article.objects.create(
            slug="trust", language="fr", h1="Comment faire confiance", body_html="<p>t</p>",
            source_type=Book.SourceType.AI_UNREVIEWED, sort_order=1,
        )
        Article.objects.create(
            slug="abide", language="en", h1="Abiding in Christ", body_html="<p>a</p>", sort_order=0,
        )
        Article.objects.create(
            slug="abide", language="es", h1="Permanecer", body_html="<p>a</p>",
            source_type=Book.SourceType.AI_REVIEWED, sort_order=0,
        )

        res = self.client.get("/api/admin/coverage/")
        self.assertIn("fr", [lang["code"] for lang in res.data["languages"]])
        articles = res.data["articles"]
        self.assertEqual([a["slug"] for a in articles], ["abide", "trust"])  # sort_order
        by_slug = {a["slug"]: a for a in articles}
        self.assertEqual(by_slug["trust"]["title"], "How to Trust God")
        self.assertNotIn("author", by_slug["trust"])
        self.assertEqual(by_slug["trust"]["cells"], {"en": "present", "fr": "ai_unreviewed"})
        self.assertEqual(by_slug["abide"]["cells"], {"en": "present", "es": "ai_reviewed"})

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
    def test_languages_lists_every_edition_with_a_finding(self):
        res = self.client.get("/api/admin/audit/")
        # ch1 of en/es/pt each trips mid_sentence_splits.
        self.assertEqual(res.data["languages"], ["en", "es", "pt"])
        self.assertEqual(res.data["language"], "")
        # Registry-sourced display names ride along for the picker.
        self.assertEqual(res.data["language_names"]["en"], "English")
        self.assertEqual(set(res.data["language_names"]), {"en", "es", "pt"})

    @override_settings(DEBUG=True)
    def test_language_filter_narrows_findings_to_one_edition(self):
        res = self.client.get("/api/admin/audit/?language=es")
        self.assertEqual(res.data["language"], "es")
        splits = res.data["quality"]["mid_sentence_splits"]
        self.assertEqual(splits["total"], 1, "only the Spanish split")
        self.assertEqual({f["language"] for f in splits["items"]}, {"es"})

    @override_settings(DEBUG=True)
    def test_language_menu_is_stable_under_a_filter(self):
        """Filtering to one edition must not empty the picker you switch through."""
        res = self.client.get("/api/admin/audit/?language=es")
        self.assertEqual(res.data["languages"], ["en", "es", "pt"])

    @override_settings(DEBUG=True)
    def test_unknown_language_yields_no_findings(self):
        res = self.client.get("/api/admin/audit/?language=zz")
        self.assertEqual(res.data["quality"]["mid_sentence_splits"]["total"], 0)
        # The menu still offers the real editions.
        self.assertEqual(res.data["languages"], ["en", "es", "pt"])


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

    def test_ref_column_holds_any_title(self):
        """A duplicate_titles ref IS the chapter title, so the column must be at
        least as wide as Chapter.title — else accepting a long duplicate 500s on
        Postgres (SQLite would silently truncate)."""
        title_max = Chapter._meta.get_field("title").max_length
        ref_max = AuditDismissal._meta.get_field("ref").max_length
        self.assertGreaterEqual(ref_max, title_max)

    def test_dismiss_a_long_duplicate_title(self):
        book = Book.objects.get(slug="humility", language="en")
        long_title = "A" * 280  # within Chapter.title (300), over the old ref (255)
        Chapter.objects.create(book=book, order=3, title=long_title, body_html="<p>x.</p>")
        Chapter.objects.create(book=book, order=4, title=long_title, body_html="<p>y.</p>")
        res = self.client.post(
            "/api/admin/audit/dismiss/",
            {"check": "duplicate_titles", "book": "humility", "language": "en", "ref": long_title},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        dupes = self.client.get("/api/admin/audit/").data["quality"]["duplicate_titles"]
        self.assertEqual([d for d in dupes["items"] if d["title"] == long_title], [])

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.post(
            "/api/admin/audit/dismiss/",
            {"check": "giant_chapters", "book": "humility", "language": "en", "ref": "1"},
            format="json",
        )
        self.assertIn(res.status_code, (401, 403))


@override_settings(
    DEBUG=True,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class AdminAuditCacheTests(TestCase):
    """The full scan is memoised on the content revision; dismissals and the
    language filter are applied fresh per request."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        book = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        big = "<p>" + ("word " * 9000) + "</p>"  # two giant chapters
        Chapter.objects.create(book=book, order=1, title="One", body_html=big)
        Chapter.objects.create(book=book, order=2, title="Two", body_html=big)

    def tearDown(self):
        cache.clear()

    def _scanned_at(self, url="/api/admin/audit/"):
        return self.client.get(url).data["scanned_at"]

    def test_response_reports_when_it_scanned(self):
        res = self.client.get("/api/admin/audit/")
        self.assertTrue(res.data["scanned_at"], "a scan timestamp is reported")

    def test_second_request_reuses_the_cached_scan(self):
        self.assertEqual(self._scanned_at(), self._scanned_at(), "not re-scanned")

    def test_a_language_filter_reuses_the_cached_scan(self):
        # The scan is language-independent (filtering is per request), so the
        # cache key carries no language — switching editions must not re-scan.
        first = self._scanned_at()
        self.assertEqual(
            self._scanned_at("/api/admin/audit/?language=en"), first, "filter, don't re-scan"
        )

    def test_refresh_forces_a_new_scan(self):
        first = self._scanned_at()
        self.assertNotEqual(first, self._scanned_at("/api/admin/audit/?refresh=1"))

    def test_a_content_change_invalidates_the_cache(self):
        first = self._scanned_at()
        ContentRevision.bump()
        self.assertNotEqual(first, self._scanned_at(), "a new revision re-scans")

    def test_accepting_a_finding_takes_effect_without_a_rescan(self):
        before = self.client.get("/api/admin/audit/")
        self.assertEqual(before.data["quality"]["giant_chapters"]["total"], 2)
        scanned = before.data["scanned_at"]
        self.client.post(
            "/api/admin/audit/dismiss/",
            {"check": "giant_chapters", "book": "humility", "language": "en", "ref": "1"},
            format="json",
        )
        after = self.client.get("/api/admin/audit/")
        self.assertEqual(after.data["quality"]["giant_chapters"]["total"], 1, "dismissal applied")
        self.assertEqual(after.data["scanned_at"], scanned, "and NOT by re-scanning")


class AdminEngagementTests(TestCase):
    def setUp(self):
        import uuid

        from django.contrib.auth import get_user_model

        from accounts.models import UserProfile
        from reading.models import (
            ChapterMarks,
            Favorite,
            FavoriteKind,
            PlanProgress,
            ReadingProgress,
        )

        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        book = Book.objects.create(author=author, slug="humility", language="en", title="Humility")
        for i in (1, 2, 3):
            Chapter.objects.create(book=book, order=i, title=f"C{i}", body_html="<p>x</p>")
        Book.objects.create(author=author, slug="abide", language="en", title="Abide")

        User = get_user_model()
        self.p1 = UserProfile.objects.create(user=User.objects.create(username=str(uuid.uuid4())), supabase_uid=uuid.uuid4())
        self.p2 = UserProfile.objects.create(user=User.objects.create(username=str(uuid.uuid4())), supabase_uid=uuid.uuid4())

        # p1 finished humility (the stored finished_at stamp) + started abide;
        # p2 is mid-humility (no stamp).
        ReadingProgress.objects.create(
            profile=self.p1, book_slug="humility", language="en", chapter_order=3,
            finished_at=timezone.now(),
        )
        ReadingProgress.objects.create(profile=self.p2, book_slug="humility", language="en", chapter_order=1)
        ReadingProgress.objects.create(profile=self.p1, book_slug="abide", language="en", chapter_order=1)
        ChapterMarks.objects.create(
            profile=self.p1, book_slug="humility", language="en", chapter_order=1,
            marks=[{"id": "a", "p": 0, "s": 0, "e": 5}],
        )
        # Hearts: abide is loved by both readers, humility + the author by p1.
        Favorite.objects.create(profile=self.p1, kind=FavoriteKind.BOOK, slug="abide")
        Favorite.objects.create(profile=self.p2, kind=FavoriteKind.BOOK, slug="abide")
        Favorite.objects.create(profile=self.p1, kind=FavoriteKind.BOOK, slug="humility")
        Favorite.objects.create(profile=self.p1, kind=FavoriteKind.AUTHOR, slug="am")
        # A 7-day plan: p1 finished it, p2 came back (2 days) but didn't finish.
        plan = Plan.objects.create(slug="seven-days", language="en", title="Seven Days")
        for day in range(1, 8):
            PlanDay.objects.create(plan=plan, day=day, book_slug="humility", chapter_order=1)
        PlanProgress.objects.create(
            profile=self.p1, plan_slug="seven-days", started_at=timezone.now(),
            done=[1, 2, 3, 4, 5, 6, 7],
        )
        PlanProgress.objects.create(
            profile=self.p2, plan_slug="seven-days", started_at=timezone.now(), done=[1, 2],
        )

    @override_settings(DEBUG=True)
    def test_overview_and_rollups(self):
        res = self.client.get("/api/admin/engagement/")
        self.assertEqual(res.status_code, 200)
        ov = res.data["overview"]
        self.assertEqual(ov["readers"], 2)
        self.assertEqual(ov["total_users"], 2)
        self.assertEqual(ov["active_7d"], 2)
        self.assertEqual(ov["active_30d"], 2)
        self.assertEqual(ov["readers_with_marks"], 1)
        self.assertEqual(ov["marked_chapters"], 1)
        # Prior-window counts back the week-over-week deltas the page shows. All
        # activity here is "now", so the preceding windows are empty.
        self.assertEqual(ov["active_7d_prev"], 0)
        self.assertEqual(ov["active_30d_prev"], 0)

        books = {b["slug"]: b for b in res.data["top_content"]["book"]}
        self.assertEqual(books["humility"]["readers"], 2)
        self.assertEqual(books["humility"]["finishers"], 1)  # only p1 finished it
        self.assertEqual(books["humility"]["highlighters"], 1)  # p1 marked it
        self.assertEqual(books["humility"]["hearts"], 1)
        self.assertEqual(books["abide"]["readers"], 1)
        self.assertEqual(books["abide"]["hearts"], 2)  # both readers hearted it
        by_lang = {r["code"]: r["readers"] for r in res.data["by_language"]}
        self.assertEqual(by_lang["en"], 2)
        # 8 weekly buckets; this week has activity.
        self.assertEqual(len(res.data["weekly_active"]), 8)
        self.assertEqual(res.data["weekly_active"][-1]["readers"], 2)

    @override_settings(DEBUG=True)
    def test_hearts(self):
        res = self.client.get("/api/admin/engagement/")
        ov = res.data["overview"]
        self.assertEqual(ov["hearts"], 4)
        self.assertEqual(ov["hearts_7d"], 4)
        self.assertEqual(ov["hearts_7d_prev"], 0)  # all created "now"

        by_kind = {r["kind"]: r["count"] for r in res.data["hearts_by_kind"]}
        self.assertEqual(by_kind["book"], 3)
        self.assertEqual(by_kind["author"], 1)

        loved = {(b["kind"], b["slug"]): b for b in res.data["most_loved"]}
        self.assertEqual(loved[("book", "abide")]["hearts"], 2)
        self.assertEqual(loved[("book", "abide")]["title"], "Abide")
        # An author favorite is titled and linked as a bio (the person).
        self.assertEqual(loved[("bio", "am")]["hearts"], 1)
        self.assertEqual(loved[("bio", "am")]["title"], "Andrew Murray")

    @override_settings(DEBUG=True)
    def test_plan_funnel(self):
        res = self.client.get("/api/admin/engagement/")
        f = res.data["plan_funnel"]
        self.assertEqual(f["started"], 2)
        self.assertEqual(f["returned"], 2)  # both ticked >= 2 days
        self.assertEqual(f["completed"], 1)  # only p1 finished all 7
        row = {p["slug"]: p for p in f["by_plan"]}["seven-days"]
        self.assertEqual(row["title"], "Seven Days")
        self.assertEqual(row["length"], 7)
        self.assertEqual(row["started"], 2)
        self.assertEqual(row["completed"], 1)

    @override_settings(DEBUG=True)
    def test_rising_counts_this_week_over_last(self):
        from datetime import timedelta

        from reading.models import ReadingProgress

        # Move abide's reader into last week; humility stays "now". (update()
        # bypasses auto_now, so the backdated updated_at sticks.)
        ReadingProgress.objects.filter(book_slug="abide").update(
            updated_at=timezone.now() - timedelta(days=10)
        )
        res = self.client.get("/api/admin/engagement/")
        rising = {(r["kind"], r["slug"]): r for r in res.data["rising"]}
        # humility: 2 readers this week, none before — a real gain.
        self.assertEqual(rising[("book", "humility")]["this_week"], 2)
        self.assertEqual(rising[("book", "humility")]["prev_week"], 0)
        self.assertEqual(rising[("book", "humility")]["delta"], 2)
        # abide's only activity was last week, so it isn't rising this week.
        self.assertNotIn(("book", "abide"), rising)

    @override_settings(DEBUG=True)
    def test_highlight_heatmap(self):
        res = self.client.get("/api/admin/engagement/")
        hm = res.data["highlight_heatmap"]
        # humility is the only marked book, so it's the most-marked one.
        self.assertEqual(hm["slug"], "humility")
        self.assertEqual(hm["title"], "Humility")
        # 3 chapters exist; only chapter 1 is marked (by p1). Every chapter is
        # present so the strip draws whole.
        self.assertEqual(len(hm["chapters"]), 3)
        by_ch = {c["chapter"]: c["readers"] for c in hm["chapters"]}
        self.assertEqual(by_ch[1], 1)
        self.assertEqual(by_ch[2], 0)
        self.assertEqual(hm["peak_chapter"], 1)
        self.assertEqual(hm["peak_readers"], 1)

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

        def mk(locale="en", theme="paper", providers="", display_name="", email="", timezone=""):
            u = User.objects.create(username=str(uuid.uuid4()))
            return UserProfile.objects.create(
                user=u,
                supabase_uid=uuid.uuid4(),
                locale=locale,
                theme=theme,
                providers=providers,
                display_name=display_name,
                email=email,
                timezone=timezone,
            )

        self.p1 = mk("en", "dark", providers="google", email="a@example.com", timezone="America/New_York")
        self.p2 = mk("sw", "paper", providers="email,google", display_name="Bea", email="b@example.com", timezone="Europe/London")
        self.p3 = mk("en", "paper")  # dormant, no provider, no timezone reported
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

        # Prior-window counts exist so the UI can show a trend (no prior sign-ups
        # here, so they're zero).
        self.assertEqual(res.data["signups_prev_7d"], 0)
        self.assertEqual(res.data["signups_prev_30d"], 0)

    @override_settings(DEBUG=True)
    def test_by_country_derived_from_timezone(self):
        res = self.client.get("/api/admin/users/")
        by_country = {r["code"]: r for r in res.data["by_country"]}
        # p1 → US, p2 → GB, each derived from its browser timezone.
        self.assertEqual(by_country["US"]["count"], 1)
        self.assertEqual(by_country["US"]["name"], "United States")
        self.assertEqual(by_country["GB"]["count"], 1)
        # p3 reported no timezone → the single "unknown" bucket (string sentinel,
        # matching by_method).
        self.assertEqual(by_country["unknown"]["count"], 1)
        self.assertEqual(by_country["unknown"]["name"], "Unknown")
        # Unknown is ordered last regardless of size.
        self.assertEqual(res.data["by_country"][-1]["code"], "unknown")

    @override_settings(DEBUG=True)
    def test_by_timezone_lists_raw_zones_skipping_blanks(self):
        res = self.client.get("/api/admin/users/")
        zones = {r["timezone"]: r["count"] for r in res.data["by_timezone"]}
        self.assertEqual(zones["America/New_York"], 1)
        self.assertEqual(zones["Europe/London"], 1)
        # p3's blank timezone is not a row here (the country "Unknown" bucket
        # already accounts for it).
        self.assertNotIn("", zones)

    @override_settings(DEBUG=True)
    def test_by_timezone_caps_and_folds_the_tail_into_other(self):
        import uuid

        from django.contrib.auth import get_user_model

        from accounts.models import UserProfile

        User = get_user_model()
        # 14 distinct mapped zones on top of setUp's 2 → 16 distinct; the raw
        # list caps at 12 and folds the remaining 4 into one "Other" row.
        zones = [
            "America/Chicago", "America/Denver", "America/Los_Angeles",
            "Europe/Paris", "Europe/Berlin", "Europe/Madrid", "Europe/Rome",
            "Africa/Lagos", "Africa/Nairobi", "Asia/Tokyo", "Asia/Manila",
            "Asia/Kolkata", "America/Sao_Paulo", "Australia/Sydney",
        ]
        for tz in zones:
            u = User.objects.create(username=str(uuid.uuid4()))
            UserProfile.objects.create(user=u, supabase_uid=uuid.uuid4(), timezone=tz)

        res = self.client.get("/api/admin/users/")
        by_tz = res.data["by_timezone"]
        # 12 real zones + exactly one "Other" row.
        self.assertEqual(len(by_tz), 13)
        self.assertEqual(by_tz[-1]["timezone"], "Other")
        # Every timezoned account is still accounted for: setUp's New_York + London
        # (1 each) plus the 14 added here = 16, with the 4 beyond the cap folded
        # into "Other".
        self.assertEqual(sum(r["count"] for r in by_tz), 16)
        self.assertEqual(by_tz[-1]["count"], 4)

    @override_settings(DEBUG=True)
    def test_by_country_orders_by_count_descending(self):
        import uuid

        from django.contrib.auth import get_user_model

        from accounts.models import UserProfile

        User = get_user_model()
        # Give Great Britain a clear lead so the ranking is unambiguous
        # (setUp seeds US=1, GB=1). After this GB=4, US=1.
        for _ in range(3):
            u = User.objects.create(username=str(uuid.uuid4()))
            UserProfile.objects.create(
                user=u, supabase_uid=uuid.uuid4(), timezone="Europe/London"
            )

        res = self.client.get("/api/admin/users/")
        real = [r for r in res.data["by_country"] if r["code"] != "unknown"]
        counts = [r["count"] for r in real]
        # Highest first, and GB (now the largest) leads.
        self.assertEqual(counts, sorted(counts, reverse=True))
        self.assertEqual(real[0]["code"], "GB")
        # The "unknown" bucket stays last regardless of these counts.
        self.assertEqual(res.data["by_country"][-1]["code"], "unknown")

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
    def test_by_signup_variant_counts_labels_and_targeted_flag(self):
        import uuid

        from django.contrib.auth import get_user_model

        from accounts.models import UserProfile

        User = get_user_model()

        def mk_variant(variant):
            u = User.objects.create(username=str(uuid.uuid4()))
            UserProfile.objects.create(user=u, supabase_uid=uuid.uuid4(), signup_variant=variant)

        for v in ("keep", "keep", "habit", "progress"):
            mk_variant(v)
        # setUp's three profiles have no variant → they land in "unknown".

        res = self.client.get("/api/admin/users/")
        rows = {r["variant"]: r for r in res.data["by_signup_variant"]}
        self.assertEqual(rows["keep"]["count"], 2)
        self.assertEqual(rows["habit"]["count"], 1)
        self.assertEqual(rows["progress"]["count"], 1)
        self.assertEqual(rows["unknown"]["count"], 3)
        # The progress arm is flagged as targeted; the random arms are not.
        self.assertTrue(rows["progress"]["targeted"])
        self.assertFalse(rows["keep"]["targeted"])
        self.assertEqual(rows["keep"]["label"], "Keep what you find")
        # "unknown" stays last regardless of its size.
        self.assertEqual(res.data["by_signup_variant"][-1]["variant"], "unknown")

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
        self.assertEqual(res["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=", res["Content-Disposition"])
        # A UTF-8 BOM leads the file so Excel reads non-ASCII titles correctly.
        self.assertTrue(res.content.startswith(b"\xef\xbb\xbf"))
        body = res.content.decode("utf-8-sig")
        self.assertIn("type,slug,language,title", body)
        self.assertIn("book,humility,en,Humility", body)
        self.assertIn("sermon,grace,en,Grace", body)

    @override_settings(DEBUG=True)
    def test_csv_guards_formula_injection(self):
        # A title beginning with a formula leader must be apostrophe-prefixed so a
        # spreadsheet won't execute it when the admin opens the export.
        author = Author.objects.create(slug="ev", name="=cmd|evil")
        Book.objects.create(
            author=author, slug="danger", language="en", title="=1+2"
        )
        res = self.client.get("/api/admin/export/?fmt=csv")
        body = res.content.decode("utf-8-sig")
        # The guarded cells carry the apostrophe; the raw formula never appears.
        self.assertIn("'=1+2", body)
        self.assertIn("'=cmd|evil", body)
        self.assertNotIn(",=1+2", body)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/export/")
        self.assertIn(res.status_code, (401, 403))


class AdminBookPublishTests(TestCase):
    """The publish/unpublish toggle on the admin book page.

    ``is_published`` is the reader-visibility switch, so this asserts the toggle
    actually moves the public API (not just the flag), records the right paired
    audit action, and is admin-gated like every other write.
    """

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="am", name="Andrew Murray")
        self.en = Book.objects.create(
            author=self.author, slug="humility", language="en", title="Humility"
        )
        Chapter.objects.create(book=self.en, order=1, title="One", body_html="<p>one</p>")
        # An unpublished AI edition, ready to be made live.
        self.sw = Book.objects.create(
            author=self.author, slug="humility", language="sw", title="Unyenyekevu",
            source_type=Book.SourceType.AI_UNREVIEWED, is_published=False,
        )

    @override_settings(DEBUG=True)
    def test_unpublish_removes_edition_from_the_reader_and_is_audited(self):
        before = self.client.get("/api/library/books/?language=en")
        self.assertIn("humility", [b["slug"] for b in before.data])

        res = self.client.post(
            "/api/admin/books/humility/publish/",
            {"language": "en", "published": False},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["is_published"])
        self.en.refresh_from_db()
        self.assertFalse(self.en.is_published)

        after = self.client.get("/api/library/books/?language=en")
        self.assertNotIn("humility", [b["slug"] for b in after.data])

        act = AdminAction.objects.latest("id")
        self.assertEqual(act.action, AdminAction.Action.CONTENT_UNPUBLISH)
        self.assertEqual(act.target, "book:humility:en")
        self.assertEqual(act.detail, {"is_published": False})

    @override_settings(DEBUG=True)
    def test_publish_makes_edition_live_and_is_audited(self):
        res = self.client.post(
            "/api/admin/books/humility/publish/",
            {"language": "sw", "published": True},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["is_published"])
        self.sw.refresh_from_db()
        self.assertTrue(self.sw.is_published)

        live = self.client.get("/api/library/books/?language=sw")
        self.assertIn("humility", [b["slug"] for b in live.data])

        act = AdminAction.objects.latest("id")
        self.assertEqual(act.action, AdminAction.Action.CONTENT_PUBLISH)

    @override_settings(DEBUG=True)
    def test_a_bare_press_defaults_to_publishing(self):
        res = self.client.post(
            "/api/admin/books/humility/publish/", {"language": "sw"}, format="json"
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["is_published"])

    @override_settings(DEBUG=True)
    def test_unknown_edition_is_404(self):
        res = self.client.post(
            "/api/admin/books/humility/publish/",
            {"language": "fr", "published": False},
            format="json",
        )
        self.assertEqual(res.status_code, 404)

    @override_settings(DEBUG=True)
    def test_language_is_required(self):
        res = self.client.post(
            "/api/admin/books/humility/publish/", {"published": False}, format="json"
        )
        self.assertEqual(res.status_code, 400)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.post(
            "/api/admin/books/humility/publish/",
            {"language": "en", "published": False},
            format="json",
        )
        self.assertIn(res.status_code, (401, 403))


class AdminSermonDetailTests(TestCase):
    """The admin sermon detail endpoint — one sermon across its languages."""

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="cs", name="Charles Spurgeon")
        Sermon.objects.create(
            author=self.author, slug="grace", language="en", title="All of Grace",
            body_html="<p>one two three</p>", scripture_ref="Eph 2:8", source_url="http://x",
        )
        Sermon.objects.create(
            author=self.author, slug="grace", language="es", title="Toda la gracia",
            body_html="<p>uno dos</p>", source_type=Book.SourceType.AI_UNREVIEWED,
            is_published=False,
        )

    @override_settings(DEBUG=True)
    def test_lists_editions_english_first(self):
        res = self.client.get("/api/admin/sermons/grace/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["title"], "All of Grace")
        self.assertEqual(res.data["author"]["slug"], "cs")
        langs = res.data["languages"]
        self.assertEqual(langs[0]["code"], "en")
        self.assertEqual(langs[0]["scripture_ref"], "Eph 2:8")
        es = next(row for row in langs if row["code"] == "es")
        self.assertEqual(es["source_type"], "ai_unreviewed")
        self.assertFalse(es["is_published"])

    @override_settings(DEBUG=True)
    def test_unknown_slug_404(self):
        res = self.client.get("/api/admin/sermons/nope/")
        self.assertEqual(res.status_code, 404)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/sermons/grace/")
        self.assertIn(res.status_code, (401, 403))


class AdminSermonPublishTests(TestCase):
    """The publish/unpublish toggle for a sermon edition (shared base with books)."""

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="cs", name="Charles Spurgeon")
        self.en = Sermon.objects.create(
            author=self.author, slug="grace", language="en", title="All of Grace",
            body_html="<p>x</p>",
        )
        self.es = Sermon.objects.create(
            author=self.author, slug="grace", language="es", title="Toda la gracia",
            body_html="<p>y</p>", is_published=False,
        )

    @override_settings(DEBUG=True)
    def test_unpublish_removes_edition_and_is_audited(self):
        before = self.client.get("/api/library/sermons/?language=en")
        self.assertIn("grace", [s["slug"] for s in before.data])

        res = self.client.post(
            "/api/admin/sermons/grace/publish/",
            {"language": "en", "published": False}, format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["is_published"])
        self.en.refresh_from_db()
        self.assertFalse(self.en.is_published)

        after = self.client.get("/api/library/sermons/?language=en")
        self.assertNotIn("grace", [s["slug"] for s in after.data])

        act = AdminAction.objects.latest("id")
        self.assertEqual(act.action, AdminAction.Action.CONTENT_UNPUBLISH)
        self.assertEqual(act.target, "sermon:grace:en")

    @override_settings(DEBUG=True)
    def test_publish_makes_edition_live(self):
        res = self.client.post(
            "/api/admin/sermons/grace/publish/",
            {"language": "es", "published": True}, format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.es.refresh_from_db()
        self.assertTrue(self.es.is_published)
        act = AdminAction.objects.latest("id")
        self.assertEqual(act.action, AdminAction.Action.CONTENT_PUBLISH)
        self.assertEqual(act.target, "sermon:grace:es")

    @override_settings(DEBUG=True)
    def test_unknown_edition_is_404(self):
        res = self.client.post(
            "/api/admin/sermons/grace/publish/",
            {"language": "fr", "published": False}, format="json",
        )
        self.assertEqual(res.status_code, 404)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.post(
            "/api/admin/sermons/grace/publish/",
            {"language": "en", "published": False}, format="json",
        )
        self.assertIn(res.status_code, (401, 403))


class AdminContentEditJobsTests(TestCase):
    """The content-edit queue: a chapter-title fix → a GitHub issue (mocked)."""

    def setUp(self):
        self.client = APIClient()
        author = Author.objects.create(slug="am", name="Andrew Murray")
        self.book = Book.objects.create(
            author=author, slug="humility", language="en", title="Humility"
        )
        # Two chapters, so a query that joins the whole chapter set (rather than
        # the one at `order`) would read the wrong title — the bug a single
        # chapter would hide.
        Chapter.objects.create(
            book=self.book, order=1, title="Lowliness", body_html="<p>a</p>"
        )
        Chapter.objects.create(
            book=self.book, order=2, title="Chapter 2", body_html="<p>one two</p>"
        )

    @staticmethod
    def _issue(title, number=7):
        return {
            "title": title,
            "labels": [{"name": "content-edit"}],
            "html_url": f"https://github.com/o/r/issues/{number}",
            "number": number,
            "created_at": "2026-09-13T00:00:00Z",
        }

    @override_settings(DEBUG=True)
    def test_get_reports_unconfigured_without_a_token(self):
        res = self.client.get("/api/admin/content-edit-jobs/")
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["configured"])

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_get_lists_open_edit_jobs(self):
        from unittest.mock import MagicMock, patch

        issue = self._issue("[edit] retitle book:humility/en#2")
        with patch("library.admin_views.content_jobs.requests") as gh:
            gh.get.return_value = MagicMock(json=lambda: [issue], raise_for_status=lambda: None)
            res = self.client.get("/api/admin/content-edit-jobs/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data["configured"])
        job = res.data["jobs"][0]
        self.assertEqual((job["slug"], job["language"], job["order"]), ("humility", "en", 2))

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_files_issue_and_is_audited(self):
        from unittest.mock import MagicMock, patch

        created = self._issue("[edit] retitle book:humility/en#2")
        with patch("library.admin_views.content_jobs.requests") as gh:
            gh.get.return_value = MagicMock(json=lambda: [], raise_for_status=lambda: None)
            gh.post.return_value = MagicMock(json=lambda: created, raise_for_status=lambda: None)
            res = self.client.post(
                "/api/admin/content-edit-jobs/",
                {"slug": "humility", "language": "en", "order": 2, "title": "True Humility"},
                format="json",
            )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["created"])
        self.assertEqual(res.data["job"]["order"], 2)
        payload = gh.post.call_args.kwargs["json"]
        self.assertEqual(payload["title"], "[edit] retitle book:humility/en#2")
        self.assertEqual(payload["labels"], ["content-edit"])
        self.assertIn("True Humility", payload["body"])
        # Both edits are spelled out for the worker.
        self.assertIn("Fixture", payload["body"])
        self.assertIn("migration", payload["body"])

        act = AdminAction.objects.latest("id")
        self.assertEqual(act.action, AdminAction.Action.CONTENT_EDIT_JOB)
        self.assertEqual(act.target, "book:humility:en")
        self.assertEqual(act.detail["chapter"], 2)

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_duplicate_returns_existing(self):
        from unittest.mock import MagicMock, patch

        existing = self._issue("[edit] retitle book:humility/en#2")
        with patch("library.admin_views.content_jobs.requests") as gh:
            gh.get.return_value = MagicMock(json=lambda: [existing], raise_for_status=lambda: None)
            res = self.client.post(
                "/api/admin/content-edit-jobs/",
                {"slug": "humility", "language": "en", "order": 2, "title": "True Humility"},
                format="json",
            )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.data["created"])
        gh.post.assert_not_called()

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_no_change_rejected(self):
        res = self.client.post(
            "/api/admin/content-edit-jobs/",
            {"slug": "humility", "language": "en", "order": 2, "title": "Chapter 2"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_reads_the_targeted_chapters_own_title(self):
        # Proposing chapter 1's title *for chapter 2* must be accepted: the no-op
        # guard has to compare against chapter 2's title, not another chapter's.
        from unittest.mock import MagicMock, patch

        created = self._issue("[edit] retitle book:humility/en#2")
        with patch("library.admin_views.content_jobs.requests") as gh:
            gh.get.return_value = MagicMock(json=lambda: [], raise_for_status=lambda: None)
            gh.post.return_value = MagicMock(json=lambda: created, raise_for_status=lambda: None)
            res = self.client.post(
                "/api/admin/content-edit-jobs/",
                {"slug": "humility", "language": "en", "order": 2, "title": "Lowliness"},
                format="json",
            )
        self.assertEqual(res.status_code, 201)
        # And the issue body quotes chapter 2's real current title.
        self.assertIn("Chapter 2", gh.post.call_args.kwargs["json"]["body"])

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_unknown_chapter_404(self):
        res = self.client.post(
            "/api/admin/content-edit-jobs/",
            {"slug": "humility", "language": "en", "order": 99, "title": "X"},
            format="json",
        )
        self.assertEqual(res.status_code, 404)

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_blank_title_rejected(self):
        res = self.client.post(
            "/api/admin/content-edit-jobs/",
            {"slug": "humility", "language": "en", "order": 2, "title": "  "},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/content-edit-jobs/")
        self.assertIn(res.status_code, (401, 403))

    # --- body-fix jobs ---------------------------------------------------------

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_body_fix_files_revise_issue(self):
        from unittest.mock import MagicMock, patch

        created = self._issue("[edit] revise book:humility/en#2")
        with patch("library.admin_views.content_jobs.requests") as gh:
            gh.get.return_value = MagicMock(json=lambda: [], raise_for_status=lambda: None)
            gh.post.return_value = MagicMock(json=lambda: created, raise_for_status=lambda: None)
            res = self.client.post(
                "/api/admin/content-edit-jobs/",
                {
                    "kind": "body",
                    "slug": "humility",
                    "language": "en",
                    "order": 2,
                    "note": "The second paragraph is duplicated.",
                },
                format="json",
            )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["job"]["kind"], "body")
        payload = gh.post.call_args.kwargs["json"]
        self.assertEqual(payload["title"], "[edit] revise book:humility/en#2")
        self.assertIn("duplicated", payload["body"])
        # The body worker instruction names the settled-form + search-vector traps.
        self.assertIn("settled", payload["body"])
        self.assertIn("search_vector", payload["body"])

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_body_fix_requires_a_note(self):
        res = self.client.post(
            "/api/admin/content-edit-jobs/",
            {"kind": "body", "slug": "humility", "language": "en", "order": 2, "note": "  "},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_body_and_title_jobs_for_one_chapter_coexist(self):
        # The duplicate guard is per-kind: an open title job must not block a body
        # job for the same chapter (they're different fixes).
        from unittest.mock import MagicMock, patch

        title_job = self._issue("[edit] retitle book:humility/en#2")
        body_created = self._issue("[edit] revise book:humility/en#2", number=8)
        with patch("library.admin_views.content_jobs.requests") as gh:
            gh.get.return_value = MagicMock(
                json=lambda: [title_job], raise_for_status=lambda: None
            )
            gh.post.return_value = MagicMock(
                json=lambda: body_created, raise_for_status=lambda: None
            )
            res = self.client.post(
                "/api/admin/content-edit-jobs/",
                {"kind": "body", "slug": "humility", "language": "en", "order": 2, "note": "typo"},
                format="json",
            )
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.data["created"])
        gh.post.assert_called_once()

    # --- bio jobs --------------------------------------------------------------

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_bio_files_author_job(self):
        from unittest.mock import MagicMock, patch

        created = self._issue("[edit] rewrite-bio author:am/en")
        with patch("library.admin_views.content_jobs.requests") as gh:
            gh.get.return_value = MagicMock(json=lambda: [], raise_for_status=lambda: None)
            gh.post.return_value = MagicMock(json=lambda: created, raise_for_status=lambda: None)
            res = self.client.post(
                "/api/admin/content-edit-jobs/",
                {"kind": "bio", "slug": "am", "language": "en", "note": "Emphasise his missionary years."},
                format="json",
            )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["job"]["kind"], "bio")
        self.assertIsNone(res.data["job"]["order"])
        payload = gh.post.call_args.kwargs["json"]
        self.assertEqual(payload["title"], "[edit] rewrite-bio author:am/en")
        self.assertIn("write-biography", payload["body"])
        self.assertIn("missionary", payload["body"])
        # A bio job links the activity row to the author, not a book.
        act = AdminAction.objects.latest("id")
        self.assertEqual(act.target, "author:am")
        self.assertEqual(act.detail["kind"], "bio")

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_bio_note_is_optional(self):
        from unittest.mock import MagicMock, patch

        created = self._issue("[edit] rewrite-bio author:am/en")
        with patch("library.admin_views.content_jobs.requests") as gh:
            gh.get.return_value = MagicMock(json=lambda: [], raise_for_status=lambda: None)
            gh.post.return_value = MagicMock(json=lambda: created, raise_for_status=lambda: None)
            res = self.client.post(
                "/api/admin/content-edit-jobs/",
                {"kind": "bio", "slug": "am"},
                format="json",
            )
        self.assertEqual(res.status_code, 201)

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_bio_rejects_an_imprint(self):
        Author.objects.create(slug="ochorus-originals", name="Ochorus Originals", is_imprint=True)
        res = self.client.post(
            "/api/admin/content-edit-jobs/",
            {"kind": "bio", "slug": "ochorus-originals"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_bio_unknown_author_404(self):
        res = self.client.post(
            "/api/admin/content-edit-jobs/",
            {"kind": "bio", "slug": "nobody"},
            format="json",
        )
        self.assertEqual(res.status_code, 404)

    @override_settings(DEBUG=True, GITHUB_TRANSLATION_TOKEN="t")
    def test_post_unknown_kind_rejected(self):
        res = self.client.post(
            "/api/admin/content-edit-jobs/",
            {"kind": "sideways", "slug": "humility", "language": "en"},
            format="json",
        )
        self.assertEqual(res.status_code, 400)

class AdminLanguageHealthTests(TestCase):
    """The per-language health score — a composite of readiness, coverage,
    review and engagement, ranked healthiest-first."""

    def setUp(self):
        self.client = APIClient()
        self.author = Author.objects.create(slug="am", name="Andrew Murray", bio="x")

        # A small, deterministic library: English is the source shelf (the
        # coverage ceiling); Spanish has half of it, one edition still unreviewed.
        for i in range(4):
            Book.objects.create(
                author=self.author, slug=f"b{i}", language="en", title=f"B{i}",
                is_published=True, source_type=Book.SourceType.PUBLIC_DOMAIN,
            )
        Book.objects.create(
            author=self.author, slug="b0", language="es", title="B0",
            is_published=True, source_type=Book.SourceType.AI_REVIEWED,
        )
        Book.objects.create(
            author=self.author, slug="b1", language="es", title="B1",
            is_published=True, source_type=Book.SourceType.AI_UNREVIEWED,
        )
        # No Bible mock is needed: the scoreboard scores with verify_bible=False,
        # so it never makes the live Take Root call (see test_makes_no_bible_call).

    @override_settings(DEBUG=True)
    def _get(self):
        res = self.client.get("/api/admin/language-health/")
        self.assertEqual(res.status_code, 200)
        return res.data

    def test_source_language_scores_full_on_coverage_and_review(self):
        data = self._get()
        by_code = {r["code"]: r for r in data["languages"]}
        self.assertEqual(data["source_published_books"], 4)
        en = by_code["en"]
        self.assertEqual(en["scores"]["coverage"], 1.0)
        self.assertEqual(en["scores"]["review"], 1.0)
        self.assertTrue(en["is_source"])

    def test_coverage_is_measured_against_the_source_shelf(self):
        by_code = {r["code"]: r for r in self._get()["languages"]}
        # Spanish has 2 of English's 4 published books.
        self.assertEqual(by_code["es"]["content"]["published_books"], 2)
        self.assertAlmostEqual(by_code["es"]["scores"]["coverage"], 0.5, places=3)

    def test_review_score_reflects_the_unreviewed_share(self):
        by_code = {r["code"]: r for r in self._get()["languages"]}
        es = by_code["es"]
        # 1 of 2 published Spanish books is unreviewed → review score 0.5.
        self.assertEqual(es["content"]["unreviewed_books"], 1)
        self.assertAlmostEqual(es["scores"]["review"], 0.5, places=3)

    def test_ranked_healthiest_first(self):
        codes = [r["health"] for r in self._get()["languages"]]
        self.assertEqual(codes, sorted(codes, reverse=True))

    def test_engagement_normalises_to_the_busiest_language(self):
        # No reading data → engagement is zero for everyone (not a crash).
        for r in self._get()["languages"]:
            self.assertEqual(r["scores"]["engagement"], 0.0)

    def test_makes_no_bible_call(self):
        # The scoreboard must never fan out a live Bible-API call per language —
        # that is why the single-language readiness route exists. If it did, this
        # patched _bible_check would be hit.
        from unittest import mock

        from . import readiness

        with mock.patch.object(readiness, "_bible_check") as bible:
            self._get()
        bible.assert_not_called()

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_admin(self):
        res = self.client.get("/api/admin/language-health/")
        self.assertIn(res.status_code, (401, 403))


class AdminManualTests(TestCase):
    """The Admin Manual PDF endpoint — super admins only, served inline."""

    def setUp(self):
        self.client = APIClient()

    @override_settings(DEBUG=True)
    def test_super_admin_gets_the_pdf_inline(self):
        res = self.client.get("/api/admin/manual/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertIn("inline", res["Content-Disposition"])
        if hasattr(res, "streaming_content"):
            res.close()  # release the file handle opened by FileResponse

    @override_settings(DEBUG=False, ADMIN_EMAILS={"admin@example.com"})
    def test_requires_super_admin(self):
        # A signed-out / non-allowlisted caller cannot reach it.
        res = self.client.get("/api/admin/manual/")
        self.assertIn(res.status_code, (401, 403))
