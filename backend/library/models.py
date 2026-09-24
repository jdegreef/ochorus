"""Content model for Ochorus.

A canonical work is identified by ``Book.slug``; each *language* of that work is
a separate ``Book`` row sharing the slug, keyed unique by ``(slug, language)``.
This mirrors Take Root's per-language ``Translation``/``Verse`` pattern: there is
no separate "Work" row — the shared slug is what ties translations together, and
it's what the AI-translation pipeline keys on (same slug, new language).
"""

from __future__ import annotations

from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.db.models import Subquery
from django.db.models.functions import Coalesce

from . import fts


class AuthorQuerySet(models.QuerySet):
    def with_work_counts(self, language: str):
        """Annotate ``num_books`` / ``num_sermons``: published works in ``language``.

        The library's one definition of how much an author carries — used by the
        public author list (which shows the counts) and by the admin's biography
        queue (which ranks by them).

        Correlated SUBQUERIES rather than joined aggregates. Two reverse joins
        fan each other out multiplicatively — Spurgeon's 5 books × 13 sermons is
        65 intermediate rows for one author — and surviving that needed
        ``Count(distinct=True)`` plus a trailing ``.distinct()``, which forced
        Postgres to GROUP BY and de-duplicate over every selected column. That
        includes ``bio`` and ``bio_html``: the full biography HTML of every
        author, hashed and sorted, on a page the prerender crawl requests once
        per locale. A subquery counts without fanning out, so the text columns
        leave the GROUP BY entirely — there is no GROUP BY left.
        """
        from django.apps import apps

        def published_count(model_name: str, related_field: str):
            model = apps.get_model("library", model_name)
            return Coalesce(
                Subquery(
                    model.objects.filter(
                        **{related_field: models.OuterRef("pk")},
                        is_published=True,
                        language=language,
                    )
                    # order_by() clears the model's default ordering, which
                    # would otherwise be added to the subquery's GROUP BY and
                    # break the aggregate.
                    .order_by()
                    .values(related_field)
                    .annotate(n=models.Count("pk"))
                    .values("n")[:1]
                ),
                models.Value(0),
                output_field=models.IntegerField(),
            )

        return self.annotate(
            num_books=published_count("Book", "author"),
            num_sermons=published_count("Sermon", "author"),
        )


class AuthorManager(models.Manager.from_queryset(AuthorQuerySet)):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class Author(models.Model):
    slug = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=200)
    # Short summary (a few sentences) — used on cards, lists and SEO meta.
    bio = models.TextField(blank=True)
    # Long-form biography as cleaned HTML (paragraphs, <h2> sections, pull-quote
    # <blockquote>s, and <aside class="prayer"> callouts). Rendered on the author
    # page above their books. Written via the `write-biography` skill.
    bio_html = models.TextField(blank=True)
    # Self-hosted portrait (under /portraits/, B&W-processed). Every one is
    # verified free-to-use before it ships: a public-domain artwork/photo, or a
    # Creative Commons image whose credit is carried in `photo_attribution`.
    # Blank for authors with no genuinely free image (most contemporary ones) —
    # the UI falls back to an initials avatar rather than host a copyrighted
    # photo. See `library/migrations/0127_*` for the sourcing receipts.
    photo_url = models.URLField(blank=True)
    # Visible credit for the portrait, shown on the author page. Required by the
    # licence for a CC image ("<creator>, <licence>, via Wikimedia Commons");
    # left blank for a public-domain portrait, where no attribution is due.
    photo_attribution = models.TextField(blank=True)
    # The portrait's source page (the Wikimedia Commons File: page), used as the
    # href for the credit line so a reader can check the provenance and licence.
    photo_source_url = models.URLField(blank=True)
    birth_year = models.IntegerField(null=True, blank=True)
    death_year = models.IntegerField(null=True, blank=True)
    original_language = models.CharField(max_length=10, default="en")
    # A house byline rather than a human (e.g. "Ochorus Originals", which
    # authors the compiled anthologies). Kept off the Biographies shelf, whose
    # cards and schema.org ItemList both speak of Person — their works are still
    # reachable from /books and the byline's own author page.
    is_imprint = models.BooleanField(default=False)
    # A real PERSON who is part of the library through their work but is kept off
    # the Biographies shelf (e.g. a living contributor who does not want a
    # biographical presence). Unlike `is_imprint`, this makes no claim that the
    # byline isn't human — their Person markup and `same_as` stand — it only
    # withholds the card. Their books/sermons stay on /books and their own author
    # page stays reachable. Default True: everyone is listed unless withheld.
    list_in_biographies = models.BooleanField(default=True)
    # Authoritative identifiers for this PERSON — Wikipedia, Wikidata, VIAF —
    # emitted as schema.org `sameAs` in the author page's Person markup.
    #
    # This is the strongest entity signal available to the site, and the reason
    # it matters is that search and answer engines resolve ENTITIES before they
    # rank documents. On "andrew murray books" Ochorus competes with Wikipedia
    # and CCEL for the right to be recognised as a page ABOUT that man; without
    # this, the connection has to be inferred from the prose, and with it the
    # page asserts which person it is about.
    #
    # A WRONG identifier is worse than none — it tells search engines the page
    # is about somebody else — so entries are verified against the person's
    # dates before they are written, and an author nobody could confirm keeps
    # an empty list rather than a plausible guess. `tests_author_entity.py` is
    # the standing guard on shape; identity is a human check, by design.
    #
    # Never populated for an imprint (`is_imprint`): "Ochorus Originals" is a
    # house byline, not a person, and pointing it at a real one would be a
    # false claim about authorship.
    same_as = models.JSONField(default=list, blank=True)
    # Life-and-ministry milestones plotted on the author page's timeline: an
    # ordered list of {"year": int, "label": str, "key": bool} dicts (key marks
    # a turning point the timeline emphasises). Optional and progressive — an
    # author with none keeps the plain lifespan bar, so this backfills a few
    # marquee lives without a migration touching all ~90. Hand-authored (a data
    # migration / seed), NOT derived from the bio, so dates are trustworthy on a
    # page whose whole promise is trustworthy public-domain scholarship.
    milestones = models.JSONField(default=list, blank=True)
    # A short question-and-answer set shown at the FOOT of the author page, below
    # their works, and emitted as schema.org `FAQPage` markup. Each entry is a
    # ``{"q": ..., "a": ...}`` pair of PLAIN TEXT — the question a reader (or an
    # answer engine) actually asks about this person, and a grounded answer drawn
    # from the verified biography and their works. Plain text, not HTML: it is
    # rendered as escaped text and carried in JSON-LD, so it needs no sanitize
    # profile and cannot inject markup. Six-to-ten entries where present; an
    # author with none simply shows no Q&A band. Translatable via
    # ``AuthorTranslation.faq`` — an untranslated set is absent, never English,
    # exactly like the bio.
    faq = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AuthorManager()

    class Meta:
        ordering = ["name"]

    def natural_key(self):
        return (self.slug,)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        # The author name is baked into their chapters' and sermons' search
        # vectors (library/fts.py) — a rename must ripple into them. The
        # rebuild re-tokenises the author's whole corpus, so compare against
        # the stored name first: a bio edit costs one SELECT, not a cascade.
        update_fields = kwargs.get("update_fields")
        ripple = update_fields is None or "name" in update_fields
        if ripple and self.pk:
            old_name = (
                Author.objects.filter(pk=self.pk)
                .values_list("name", flat=True)
                .first()
            )
            ripple = old_name != self.name
        super().save(*args, **kwargs)
        if ripple:
            fts.refresh_author_works(self)

    def _localized(self, field: str, language: str, *, fallback: bool = False) -> str:
        """A translated prose field in ``language``.

        Returns ``""`` when the language has no translation, because a reader who
        asked for Swahili must never be handed English prose — an untranslated
        bio is absent, not English. Pass ``fallback=True`` only for surfaces that
        exist to show what *is* there to translate (admin, coverage, tooling).

        Reads ``self.translations.all()`` (not ``.filter()``) so a caller that
        prefetched translations pays no extra query.
        """
        if language and language != self.original_language:
            tr = next((t for t in self.translations.all() if t.language == language), None)
            if tr and getattr(tr, field):
                return getattr(tr, field)
            return getattr(self, field) if fallback else ""
        return getattr(self, field)

    def bio_for(self, language: str, *, fallback: bool = False) -> str:
        """Short bio in ``language``; ``""`` when untranslated.

        An imprint (``is_imprint``) is a house byline, not a person, so it never
        presents a biography. Withheld at this shared chokepoint rather than at
        each caller so every surface (author page, book-card mini-bio, tooling)
        agrees — the same reason ``same_as`` is "never populated for an imprint".
        """
        if self.is_imprint:
            return ""
        return self._localized("bio", language, fallback=fallback)

    def bio_html_for(self, language: str, *, fallback: bool = False) -> str:
        """Long-form bio HTML in ``language``; ``""`` when untranslated.

        Withheld for an imprint, like ``bio_for`` — a byline has no biography.
        """
        if self.is_imprint:
            return ""
        return self._localized("bio_html", language, fallback=fallback)

    def faq_for(self, language: str, *, fallback: bool = False) -> list:
        """The Q&A list in ``language``; ``[]`` when untranslated.

        Rides on the same per-field localization as the bios. Two empties meet
        here: a translation whose ``faq`` is ``[]`` is falsy, so ``_localized``
        treats it as "not translated here" and skips it (the no-fallback rule);
        and in that absent, non-fallback case ``_localized`` returns its string
        sentinel ``""``, which the trailing ``or []`` normalizes back to the
        empty list this list-typed field should yield.

        Withheld for an imprint, like the bios — the editorial Q&A is part of the
        biographical surface a byline does not have.
        """
        if self.is_imprint:
            return []
        return self._localized("faq", language, fallback=fallback) or []

    def has_bio_in(self, language: str) -> bool:
        """Whether a bio exists in ``language`` — the honest test for "does this
        author have something to read here", used by the biographies page."""
        return bool(self.bio_for(language).strip() or self.bio_html_for(language).strip())


class AuthorTranslation(models.Model):
    """A translated copy of an Author's prose (short ``bio`` and/or long-form
    ``bio_html``) in one language. Kept in a side-table rather than per-language
    Author rows so the Author FK graph (books, sermons) stays intact — the
    English Author is canonical and every language points at the same row.

    Populated by the AI-translate pipeline (``manage.py translate_author``).
    ``reviewed`` tracks whether a native speaker has approved the wording
    (flipped by ``approve_author_translation``); it records review state but is
    not yet surfaced in the UI, so a bio is served whether or not it's reviewed.
    """

    author = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name="translations"
    )
    language = models.CharField(max_length=10)
    # Either field may be blank: the short bio and the long bio_html are
    # translated in separate passes, and the serializer falls back per-field.
    bio = models.TextField(blank=True)
    bio_html = models.TextField(blank=True)
    # The translated Q&A set (the twin of ``Author.faq``): a list of
    # ``{"q": ..., "a": ...}`` plain-text pairs in this language. Blank until the
    # set is translated, and — like every prose field here — served only in its
    # own language, never falling back to the English original.
    faq = models.JSONField(default=list, blank=True)
    reviewed = models.BooleanField(default=False)
    # The English this was translated from has since been replaced, so the
    # wording may describe text that no longer exists. Deliberately NOT modelled
    # by clearing `reviewed`: that field also tells `seed_author_translations`
    # "an approver owns this wording, don't overwrite it", so flipping it to
    # signal staleness drops that protection and the next deploy replaces the
    # approved translation with the repo's AI text. The two facts are
    # independent — a translation can be both approved and stale.
    source_stale = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["author", "language"]
        constraints = [
            models.UniqueConstraint(
                fields=["author", "language"], name="uniq_author_translation"
            ),
        ]
        indexes = [
            # The admin language pages filter by language across all authors;
            # the unique constraint leads with author_id and cannot serve that.
            models.Index(fields=["language"], name="idx_authortr_language"),
        ]

    def __str__(self) -> str:
        return f"{self.author.slug} [{self.language}]"


#: Columns a sermon CARD never renders. SermonListSerializer emits title,
#: scripture_ref, summary, word_count and author — no body — yet every list path
#: was hauling body_html, body_text AND the tsvector, roughly 100 KB a row, to
#: draw a line of text. The chapter equivalent was found and fixed for
#: BookDetailView (see its Prefetch note, and the 2026-08-14 OOM); the same
#: lesson never reached sermons.
#:
#: One constant, not four literals: this list drifted apart once already by
#: existing in one place and not the others.
SERMON_CARD_DEFER = ("body_html", "body_text", "search_vector")


class SeriesManager(models.Manager):
    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class Series(models.Model):
    """A named run of separate works that belong together — *Brave for God*,
    *Rooted*, *The Key Teachings of …*.

    One row per series, language-agnostic like Author: the identity is shared,
    and each language's Book rows join it through ``Book.series``, so a language
    holding two of four volumes has a two-volume series — there is no English
    fallback here either.

    Not an edition family. The full / teens / children / Modern English forms of
    ONE work are tied by the slug convention (``serializers.sibling_editions``)
    and never join a series; a series is DIFFERENT works. Nor an author's shelf:
    *Key Teachings* spans authors, so a series belongs to no one.

    Whether it is ORDERED is its members' fact, not a flag: a series whose books
    carry ``series_position`` has a reading order (and a numeral on each cover);
    one whose books leave it null is a collection. ``tests_fixture`` holds a
    series to one or the other.
    """

    slug = models.SlugField(max_length=160, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SeriesManager()

    class Meta:
        ordering = ["sort_order", "title"]
        verbose_name_plural = "series"

    def natural_key(self):
        return (self.slug,)

    def __str__(self) -> str:
        return self.title

    def _localized(self, field: str, language: str) -> str:
        """A translated field in ``language``; ``""`` when it has none there.

        No English fallback — the rule every translated field here follows (see
        ``Topic._localized``). A reader on a Swahili edition who meets an
        English series name has been told the series is not in their language,
        so an untranslated series shows no series line and has no page there.

        Reads ``self.translations.all()`` so a caller that prefetched pays no
        query.
        """
        if not language or language == "en":
            return getattr(self, field)
        tr = next((t for t in self.translations.all() if t.language == language), None)
        return getattr(tr, field) if tr else ""

    def title_for(self, language: str) -> str:
        return self._localized("title", language)

    def description_for(self, language: str) -> str:
        return self._localized("description", language)


class SeriesTranslationManager(models.Manager):
    def get_by_natural_key(self, series_slug, language):
        return self.get(series__slug=series_slug, language=language)


class SeriesTranslation(models.Model):
    """A series' name (and description) in one language.

    A side-table, like ``TopicTranslation``, because a series is one identity
    across languages. Its rows ship in ``content/series.json`` after the series
    they name, and seed_books upserts them with the rest of that file.
    """

    series = models.ForeignKey(
        Series, on_delete=models.CASCADE, related_name="translations"
    )
    language = models.CharField(max_length=10)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SeriesTranslationManager()

    class Meta:
        ordering = ["series", "language"]
        constraints = [
            models.UniqueConstraint(
                fields=["series", "language"], name="uniq_series_translation"
            ),
        ]

    def natural_key(self):
        return (*self.series.natural_key(), self.language)

    natural_key.dependencies = ["library.series"]

    def __str__(self) -> str:
        return f"{self.series.slug} [{self.language}]"


class BookManager(models.Manager):
    def get_by_natural_key(self, slug, language):
        return self.get(slug=slug, language=language)


class Book(models.Model):
    class SourceType(models.TextChoices):
        PUBLIC_DOMAIN = "public_domain", "Public domain (original language)"
        AI_REVIEWED = "ai_reviewed", "AI translation — reviewed"
        AI_UNREVIEWED = "ai_unreviewed", "AI translation — unreviewed"

    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="books")
    # Canonical, language-agnostic identifier shared across all languages of the
    # same work (e.g. "humility"). Unique per language, not globally.
    slug = models.SlugField(max_length=160)
    language = models.CharField(max_length=10, default="en")

    title = models.CharField(max_length=300)
    subtitle = models.CharField(max_length=300, blank=True)
    # The title the COVER sets, when the full one is too long to leave the
    # cover room for anything else ("Rooted" for "Rooted – 30 Days with God for
    # Youth – Book 1": the series numeral and the subtitle already say the
    # rest). Blank = the cover sets `title`. Cover-only: the book page, search,
    # the shelf's text and the cover's accessible name all keep `title`.
    # Per-language like every other row field; `translate_book` leaves it blank,
    # so a translation sets its own full title until someone gives it a short one.
    cover_title = models.CharField(max_length=120, blank=True)
    # Short summary (a few sentences) — used on cards, lists and SEO meta.
    description = models.TextField(blank=True)
    # Long-form "About this work" as cleaned HTML, the twin of Author.bio_html
    # and cleaned by the same sanitizer: what the work is, the situation it was
    # written into, and who it still repays. Rendered on the book page.
    #
    # It exists because the chapters do not distinguish this page from anyone
    # else's copy of the same public-domain text — CCEL, Gutenberg and a dozen
    # reprints carry them verbatim. This is the part that is Ochorus's own, so
    # it is the part worth writing, and it is per-language for the same reason
    # every other row is: there is no English fallback.
    about_html = models.TextField(blank=True)
    # Answered Questions & Answers: a list of {"question", "answer"} objects, both
    # PLAIN TEXT (no HTML — rendered as escaped text, so no sanitize path). Like
    # `about_html`, this is Ochorus's own writing about the work, grounded strictly
    # in it: AI-drafted off-server, shipped in the fixture, per-language for the
    # same reason every other row is. The reader shows a "Questions and Answers"
    # section and the page emits FAQPage JSON-LD. Empty list = nothing shown. See
    # the `content-questions` skill for the generation pipeline.
    qa = models.JSONField(default=list, blank=True)
    # Year the work was first published (e.g. 1885). Optional — many classics
    # are known only by era.
    publication_year = models.PositiveIntegerField(null=True, blank=True)

    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.PUBLIC_DOMAIN,
    )
    source_url = models.URLField(blank=True)
    # Free-text licence / attribution / rights note (e.g. "Public domain —
    # scanned by CCEL" or an edition/translation credit). Shown on the book page.
    attribution = models.TextField(blank=True)
    # Optional cover image and original PDF (used by the ochorus.com importer).
    cover_url = models.URLField(blank=True)
    pdf_url = models.URLField(blank=True)
    # Optional hex accent (e.g. "#3b5bdb") used to tint a generated cover when
    # there's no cover image.
    cover_color = models.CharField(max_length=9, blank=True)

    # The series this edition belongs to, and its volume in it — the numeral a
    # cover sets above its title. Per ROW, like cover_url: each language's
    # edition joins on its own, so a translation that has not shipped yet is
    # simply not in the series in that language. A null position inside a
    # series means the series is an unordered collection (see `Series`).
    # PROTECT: removing a series must be a decision about its books first.
    series = models.ForeignKey(
        Series,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="books",
    )
    series_position = models.PositiveSmallIntegerField(null=True, blank=True)

    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BookManager()

    class Meta:
        ordering = ["sort_order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "language"], name="uniq_book_slug_language"
            ),
            # Two editions of one language cannot both be volume 2. Rows with
            # no position (a collection, or no series) are exempt: NULLs are
            # distinct in a unique index. DEFERRED because seed_books saves a
            # book at a time: renumbering a series (a new volume 1, a swap)
            # passes through a moment where two rows share a number, and an
            # immediate check would abort the deploy on it.
            models.UniqueConstraint(
                fields=["series", "language", "series_position"],
                name="uniq_book_series_volume",
                deferrable=models.Deferrable.DEFERRED,
            ),
            # A volume number means nothing outside a series, and counts from 1
            # (the cover draws no ring for a missing one).
            models.CheckConstraint(
                condition=models.Q(series_position__isnull=True)
                | models.Q(series__isnull=False, series_position__gte=1),
                name="book_series_position_needs_series",
            ),
        ]
        indexes = [
            # BookListView: filter(is_published, language) then
            # order_by(sort_order, title). The unique constraint above leads
            # with `slug`, which this query does not mention, so it was a
            # sequential scan of every book in every language on the busiest
            # read in the app. Column order matches the query: equality first,
            # then the sort, so Postgres can satisfy both from the index.
            models.Index(
                fields=["language", "is_published", "sort_order", "title"],
                name="idx_book_shelf",
            ),
        ]

    def natural_key(self):
        return (self.slug, self.language)

    natural_key.dependencies = ["library.author", "library.series"]

    def __str__(self) -> str:
        return f"{self.title} ({self.language})"

    def save(self, *args, **kwargs):
        # The book title (and language, which picks the FTS config) is baked
        # into its chapters' search vectors (library/fts.py) — a retitle must
        # ripple. Compare against the stored row first so unrelated edits
        # (covers, sort order) don't re-tokenise the whole book; on create the
        # refresh matches zero chapter rows, so it's free either way.
        update_fields = kwargs.get("update_fields")
        ripple = update_fields is None or not {
            "title", "language", "author", "author_id"
        }.isdisjoint(update_fields)
        if ripple and self.pk:
            old = (
                Book.objects.filter(pk=self.pk)
                .values_list("title", "language", "author_id")
                .first()
            )
            ripple = old != (self.title, self.language, self.author_id)
        super().save(*args, **kwargs)
        if ripple:
            fts.refresh_book_chapters(self)

    @property
    def chapter_count(self) -> int:
        return self.chapters.count()


class ChapterManager(models.Manager):
    def get_by_natural_key(self, slug, language, order):
        return self.get(book__slug=slug, book__language=language, order=order)


class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chapters")
    # 1-based position within the book.
    order = models.PositiveIntegerField()
    title = models.CharField(max_length=300, blank=True)
    # Cleaned, structured HTML (paragraphs, headings, blockquotes).
    body_html = models.TextField()
    # Plain text derived from body_html — what full-text search matches and
    # snippets. Kept by save(); fixture loads bypass save(), so the
    # backfill_body_text command (run on every deploy) fills any gaps.
    body_text = models.TextField(blank=True, default="")
    # Words in body_html — derived and kept by the same save() as body_text.
    # Spent on the per-chapter reading time in the TOC, the length sort on the
    # shelf, and the totals under a book and under a reading plan.
    word_count = models.PositiveIntegerField(default=0)
    # Stored tsvector (Postgres only; NULL on SQLite). Kept by save() +
    # backfill_search_vectors; GIN-indexed in migration 0041. See library/fts.py.
    search_vector = SearchVectorField(null=True, editable=False, serialize=False)
    # When this chapter's Bible citations were last indexed (see
    # ChapterCitation + the index_citations release step). Cleared by save()
    # so a body edit triggers reindexing on the next deploy.
    citations_indexed_at = models.DateTimeField(
        null=True, editable=False, serialize=False
    )

    objects = ChapterManager()

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["book", "order"], name="uniq_chapter_book_order"
            ),
        ]
        indexes = [
            # index_citations runs on EVERY deploy and asks for the chapters it
            # has not stamped yet — `filter(citations_indexed_at__isnull=True)`.
            # In the steady state that is zero rows, but finding them was a scan
            # of the whole corpus. A PARTIAL index holds only the unstamped
            # rows, so the usual answer ("none") is an empty index lookup, and
            # the index itself stays tiny.
            models.Index(
                fields=["citations_indexed_at"],
                condition=models.Q(citations_indexed_at__isnull=True),
                name="idx_chapter_uncited",
            ),
        ]

    def natural_key(self):
        return self.book.natural_key() + (self.order,)

    natural_key.dependencies = ["library.book"]

    def __str__(self) -> str:
        return f"{self.book.slug}/{self.order} — {self.title}"

    def save(self, *args, **kwargs):
        from .text import html_to_text, word_count

        self.body_text = html_to_text(self.body_html)
        self.word_count = word_count(self.body_html)
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "body_html" in update_fields:
            # A body change invalidates the citation index; the index_citations
            # release step re-scans stamp-cleared chapters on the next deploy.
            self.citations_indexed_at = None
            if update_fields is not None:
                kwargs["update_fields"] = list(update_fields) + [
                    "body_text",
                    "word_count",
                    "citations_indexed_at",
                ]
        super().save(*args, **kwargs)
        # Skip the vector rebuild when a scoped save touches no indexed field
        # (it re-tokenises the whole body — pure waste for a flag flip).
        # Both the FK name and its attname: update_fields accepts either.
        if update_fields is None or not {
            "title", "body_html", "body_text", "book", "book_id"
        }.isdisjoint(update_fields):
            fts.refresh_chapter(self)


class ChapterCitation(models.Model):
    """One Bible reference cited in a chapter's text, as a verse-id span.

    Spans use pythonbible's numeric verse ids (BBBCCCVVV), so range overlap
    against a query's verse ids finds a chapter that cites "John 3:14-21" when
    the reader searches "John 3:16". Populated by the index_citations release
    step from body_text; `count` records how often the same span recurs in the chapter.
    """

    chapter = models.ForeignKey(
        Chapter, on_delete=models.CASCADE, related_name="citations"
    )
    ref_text = models.CharField(max_length=80)
    start_verse_id = models.IntegerField()
    end_verse_id = models.IntegerField()
    count = models.PositiveSmallIntegerField(default=1)

    class Meta:
        indexes = [
            models.Index(
                fields=["start_verse_id", "end_verse_id"],
                name="idx_citation_span",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["chapter", "start_verse_id", "end_verse_id"],
                name="uniq_citation_chapter_span",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.chapter_id} cites {self.ref_text}"


class SermonManager(models.Manager):
    def get_by_natural_key(self, slug, language):
        return self.get(slug=slug, language=language)


class Sermon(models.Model):
    """A single sermon by an author — like a Book, but a standalone piece with no
    chapters. Grouped under the author and listed on the /sermons shelf.
    """

    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="sermons")
    # Canonical identifier shared across languages, unique per language.
    slug = models.SlugField(max_length=180)
    language = models.CharField(max_length=10, default="en")

    title = models.CharField(max_length=300)
    # The sermon's text — e.g. "John 3:16" or "Isaiah 45:22".
    scripture_ref = models.CharField(max_length=160, blank=True)
    # Provenance / translation status — shares Book's vocabulary so a machine
    # translation carries the same "awaiting native review" trust badge.
    source_type = models.CharField(
        max_length=20,
        choices=Book.SourceType.choices,
        default=Book.SourceType.PUBLIC_DOMAIN,
    )
    # When it was preached, if known (day precision optional — see year note).
    preached_on = models.DateField(null=True, blank=True)
    # An "In brief" TL;DR (2–4 sentences, plain text). AI-drafted off-server
    # and shipped in the sermon's fixture file, per the pipeline's founding
    # rule (prod holds no model credentials); blank = the reader shows none.
    summary = models.TextField(blank=True, default="")
    # Answered study questions: a list of {"question", "answer"} objects, both
    # PLAIN TEXT (no HTML — rendered as escaped text, so no sanitize path). Like
    # `summary`: AI-drafted off-server, grounded strictly in this sermon, shipped
    # in the fixture; the reader shows a "Questions for reflection" section and
    # the page emits FAQPage JSON-LD. Empty list = nothing shown. See the
    # `sermon-questions` skill for the generation + review pipeline.
    study_questions = models.JSONField(default=list, blank=True)
    # Cleaned, structured HTML body (paragraphs, headings, blockquotes).
    body_html = models.TextField()
    # Plain text derived from body_html; what full-text search indexes.
    body_text = models.TextField(blank=True, default="")
    # Words in body_html — derived and kept by save(), as on Chapter.
    word_count = models.PositiveIntegerField(default=0)
    # Stored tsvector (Postgres only; NULL on SQLite). Kept by save() +
    # backfill_search_vectors; GIN-indexed in migration 0041. See library/fts.py.
    search_vector = SearchVectorField(null=True, editable=False, serialize=False)
    source_url = models.URLField(blank=True)
    # Free-text rights / permission / credit note, the twin of Book.attribution.
    # Blank for a public-domain sermon (the reader then shows its generic
    # "public domain" line); set for a work used by permission, where it both
    # RECORDS the grant and REPLACES that line on the page — so a copyrighted
    # sermon is never mislabelled public domain. Fixture-owned prose, updated on
    # every deploy (in SERMON_FIELDS, not create-only).
    attribution = models.TextField(blank=True, default="")

    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SermonManager()

    class Meta:
        ordering = ["sort_order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "language"], name="uniq_sermon_slug_language"
            ),
        ]
        indexes = [
            # SermonListView, and the topic/author attach paths — same shape and
            # same reason as idx_book_shelf.
            models.Index(
                fields=["language", "is_published", "sort_order", "title"],
                name="idx_sermon_shelf",
            ),
        ]

    def natural_key(self):
        return (self.slug, self.language)

    natural_key.dependencies = ["library.author"]

    def __str__(self) -> str:
        return f"{self.title} — {self.author.name} ({self.language})"

    def save(self, *args, **kwargs):
        from .text import html_to_text, word_count

        self.body_text = html_to_text(self.body_html)
        self.word_count = word_count(self.body_html)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "body_html" in update_fields:
            kwargs["update_fields"] = list(update_fields) + [
                "body_text",
                "word_count",
            ]
        super().save(*args, **kwargs)
        # Skip the vector rebuild when a scoped save touches no indexed field
        # (e.g. approve_sermon_translation flips only source_type).
        # Both the FK name and its attname: update_fields accepts either.
        if update_fields is None or not {
            "title", "body_html", "body_text", "scripture_ref",
            "author", "author_id", "language",
        }.isdisjoint(update_fields):
            fts.refresh_sermon(self)


class ArticleManager(models.Manager):
    def get_by_natural_key(self, slug, language):
        return self.get(slug=slug, language=language)


class Article(models.Model):
    """A devotional / theological article — original site writing, NOT a
    public-domain work and NOT attributed to anyone.

    Articles are the SEO layer: they answer the questions people search
    ("how to trust God", "what does it mean to abide in Christ") and funnel the
    reader into the library via the ``related`` links at the end. Unlike a Book
    or Sermon there is **no author FK** — an article is simply a page on the
    site, so nothing on it claims a byline.

    Everything else follows the per-language row convention: ``slug`` is the
    canonical identifier shared across translations, unique per language, with no
    English fallback. English is where they start, but translations exist (fr,
    lg, es, pt, sw) and a translated article is simply another row on the same
    slug — so code reading articles must filter by language rather than assume
    English. This docstring said "English is the only language today" long after
    that stopped being true, and two separate callers were written to gate on
    English because of it.
    """

    # Canonical, language-agnostic identifier shared across translations.
    slug = models.SlugField(max_length=180)
    language = models.CharField(max_length=10, default="en")

    # The on-page headline — the warm, human H1, and the display title
    # everywhere the article is listed.
    h1 = models.CharField(max_length=300)
    # The SEO <title> tag, which leads with the keyword. Blank falls back to h1,
    # so a title only differs from the headline when it needs to.
    meta_title = models.CharField(max_length=300, blank=True)
    # The standfirst: a short summary shown under the H1 and reused as the meta
    # description. Like Book.description, one field serves the page and the crawl.
    description = models.TextField(blank=True)
    # The article body as cleaned, structured HTML. Carries pull-quotes and
    # internal links, so it is sanitized with the RICH (bio) profile, not the
    # narrow chapter one — see backend/CLAUDE.md on the two sanitize profiles.
    body_html = models.TextField()

    # The funnel. A list of soft references to the works this article sends the
    # reader to, rendered as the "Read next" block:
    #   [{"type": "book"|"sermon"|"author", "slug": "..."}, ...]
    # Soft references (not FKs) so they are language-agnostic and survive a
    # re-import, exactly like TopicBook.book_slug.
    related = models.JSONField(default=list, blank=True)

    # Provenance / translation status — shares Book's vocabulary (as Sermon does)
    # so a machine translation carries the same "awaiting native review" trust
    # badge and the approve command can flip it. English originals stay
    # public_domain by default; a translated row ships ai_unreviewed until a
    # native speaker signs it off. See backend/CLAUDE.md on never presenting an
    # unreviewed translation as an original.
    source_type = models.CharField(
        max_length=20,
        choices=Book.SourceType.choices,
        default=Book.SourceType.PUBLIC_DOMAIN,
    )
    source_url = models.URLField(blank=True)

    # Reading-time source: the article's word count, derived from body_html on
    # save() (the same as Chapter/Sermon). Drives the "N min read" estimate on
    # the index cards and the article-page eyebrow. A save()-bypassing write
    # (loaddata on a fresh DB) leaves it zero until backfill_word_count fills it.
    word_count = models.PositiveIntegerField(default=0)

    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ArticleManager()

    class Meta:
        ordering = ["sort_order", "h1"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "language"], name="uniq_article_slug_language"
            ),
        ]
        indexes = [
            # ArticleListView: filter(language, is_published) then
            # order_by(sort_order, h1) — same shape and reason as idx_book_shelf.
            models.Index(
                fields=["language", "is_published", "sort_order", "h1"],
                name="idx_article_shelf",
            ),
        ]

    def natural_key(self):
        return (self.slug, self.language)

    # No `dependencies`: unlike Book/Sermon, an article has no author FK to load
    # first, so it can seed in any order.

    def __str__(self) -> str:
        return f"{self.h1} ({self.language})"

    def save(self, *args, **kwargs):
        # word_count is the only derived column (no body_text / FTS on an
        # article), so a scoped save() that touches body_html carries it too.
        from .text import word_count

        self.word_count = word_count(self.body_html)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "body_html" in update_fields:
            kwargs["update_fields"] = list(update_fields) + ["word_count"]
        super().save(*args, **kwargs)


class PlanManager(models.Manager):
    def get_by_natural_key(self, slug, language):
        return self.get(slug=slug, language=language)


class Plan(models.Model):
    """A curated, daily-cadence reading plan: one chapter per day, in order.

    Like books, plans are addressed by ``slug`` + ``language`` so the same plan
    can exist per translation. Days reference chapters by (book_slug,
    chapter_order) rather than FK — the same soft-reference convention the
    reading app uses, so plans survive book re-imports.
    """

    slug = models.SlugField(max_length=160)
    language = models.CharField(max_length=10, default="en")
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PlanManager()

    class Meta:
        ordering = ["sort_order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "language"], name="uniq_plan_slug_language"
            ),
        ]

    def natural_key(self):
        return (self.slug, self.language)

    def __str__(self) -> str:
        return f"{self.title} ({self.language})"


class PlanDayManager(models.Manager):
    def get_by_natural_key(self, slug, language, day):
        return self.get(plan__slug=slug, plan__language=language, day=day)


class PlanDay(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="days")
    # 1-based day within the plan.
    day = models.PositiveIntegerField()
    book_slug = models.SlugField(max_length=160)
    chapter_order = models.PositiveIntegerField()

    objects = PlanDayManager()

    class Meta:
        ordering = ["day"]
        constraints = [
            models.UniqueConstraint(fields=["plan", "day"], name="uniq_plan_day"),
        ]

    def natural_key(self):
        return self.plan.natural_key() + (self.day,)

    natural_key.dependencies = ["library.plan"]

    def __str__(self) -> str:
        return f"{self.plan_id} day {self.day} → {self.book_slug}/{self.chapter_order}"


class Quote(models.Model):
    """One sourced sentence from a work, for the author's quote page.

    THE POINT IS THE SOURCING. Quote queries are large and are served today by
    aggregators that publish unattributed — often misattributed — lines. The one
    thing they cannot fake is the citation, so every row here points at the exact
    work, chapter and PARAGRAPH the sentence came from, and the card shows it.
    A quote whose source cannot be named has no business on the page.

    `paragraph` indexes the body's TOP-LEVEL CHILDREN, which is the unit the
    reader's `?p=` jump counts — not the <p> elements alone. Any chapter with an
    <h2> makes those two disagree, and the reader would land in the wrong place.

    `reviewed` is the publication gate and mirrors the translation pipeline's
    trust model: extraction is mechanical plus judgement, and neither is a human
    saying "yes, print this under his name". Nothing reaches a reader until
    `approve_quotes` runs. The public serializer filters on it.
    """

    #: Stable identity for the seed: author slug + a hash of the normalised text,
    #: so re-running extraction updates a row rather than duplicating it, and a
    #: reworded quote is a new row rather than a silent edit of an approved one.
    #: It is also the quote's PERMANENT public address — the per-quote page will
    #: be served at it — so a text REPAIR must keep this slug (edit the row in
    #: place), and only a genuinely new quotation earns a fresh hash. The
    #: extraction skill states the rule; seed_quotes never rewrites the slug (it
    #: is the match key), and tests_quotes guards the edit-in-place path.
    slug = models.SlugField(max_length=80, unique=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="quotes")
    text = models.TextField()
    # Exactly one of these carries the source; a quote with neither is unsourced
    # and the fixture gate rejects it.
    chapter = models.ForeignKey(
        "Chapter", on_delete=models.CASCADE, null=True, blank=True, related_name="quotes"
    )
    sermon = models.ForeignKey(
        Sermon, on_delete=models.CASCADE, null=True, blank=True, related_name="quotes"
    )
    paragraph = models.PositiveIntegerField()
    reviewed = models.BooleanField(default=False)
    # The devotional themes this sentence is filed under — what powers the
    # "Quotes on Prayer" and "Andrew Murray Quotes on Prayer" pages. A quote may
    # sit under several themes; the tags are curated in `quote_seed.py` where the
    # sentence is visible, and (unlike `reviewed`) re-asserted every deploy, so a
    # re-tag ships. Public pages still filter on `reviewed`, so a tagged-but-
    # unreviewed quote reaches no reader.
    topics = models.ManyToManyField(
        "QuoteTopic", related_name="quotes", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["slug"]

    def natural_key(self):
        return (self.slug,)

    def __str__(self) -> str:
        return f"{self.author.slug}: {self.text[:48]}"


class QuoteTopic(models.Model):
    """A devotional theme a quotation can be filed under — e.g. "Prayer".

    DELIBERATELY A SEPARATE VOCABULARY from ``Topic`` (the shelves of works).
    A quote theme is finer and more numerous than a book shelf, and the two
    audiences differ: ``Topic`` is "which books are about prayer", this is
    "the memorable lines on prayer". Reusing ``Topic`` would either strand
    themes that hold no books as empty rows on the ``/topics`` browse, or force
    every theme to double as a book shelf. Membership is a plain M2M from
    ``Quote`` (``Quote.topics``), tagged in ``quote_seed.py``.

    English-only in practice, exactly as the quotes are: the sentences are lifted
    from English works and every citation names an English chapter. ``title`` is
    the standalone label ("Prayer", "The Holy Spirit"); the page composes
    "Quotes on …" from it, lowercasing a leading article for the running form.
    """

    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=120)
    # A one-line description shown on the topic page and its index card, and used
    # as the page's meta description.
    blurb = models.TextField(blank=True)
    # A themed Scripture epigraph shown on the topic page — the same furniture
    # the work-topic pages carry (public-domain wording).
    scripture_ref = models.CharField(max_length=120, blank=True)
    scripture_text = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "title"]

    def natural_key(self):
        return (self.slug,)

    def __str__(self) -> str:
        return self.title


class Topic(models.Model):
    """A curated topical shelf — a themed grouping of works (e.g. "On Prayer").

    A topic is language-agnostic: unlike Book/Plan there is a *single* Topic row
    per subject, and its members are referenced by canonical ``book_slug`` (a
    soft reference, like PlanDay), so one topic serves every language and each
    reader sees the members that exist in their language. Prose (title,
    description) is translated in a side-table (``TopicTranslation``), the same
    pattern Author uses, and falls back to the English original per field.
    """

    slug = models.SlugField(max_length=160, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # SEO overrides for the topic page's <title> and <meta description>. Both
    # optional: when blank the reader falls back to "<title> — Ochorus" and to
    # `description`. English lives here; per-language values ride
    # `TopicTranslation` like the prose above, so a locale with no override
    # keeps its localized default (the no-fallback rule of `_localized`).
    seo_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    # A themed Scripture epigraph shown on the topic page (public-domain wording).
    scripture_ref = models.CharField(max_length=120, blank=True)
    scripture_text = models.TextField(blank=True)
    # Answered Questions & Answers about the shelf: a list of {"question",
    # "answer"} objects, both PLAIN TEXT (no HTML — rendered as escaped text, so
    # no sanitize path). Ochorus's own writing about the topic, grounded in it;
    # translated in the side-table like the prose above. The reader shows a
    # "Questions and Answers" section and the page emits FAQPage JSON-LD. Empty
    # list = nothing shown. See the `content-questions` skill.
    qa = models.JSONField(default=list, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self) -> str:
        return self.title

    def _localized(self, field: str, language: str, *, fallback: bool = False) -> str:
        """A translated prose field in ``language``.

        Returns ``""`` when untranslated rather than the English original — see
        ``Author._localized``. Pass ``fallback=True`` for admin/coverage surfaces.

        Reads ``self.translations.all()`` (not ``.filter()``) so a caller that
        prefetched translations pays no extra query.
        """
        if language and language != "en":
            tr = next((t for t in self.translations.all() if t.language == language), None)
            if tr and getattr(tr, field):
                return getattr(tr, field)
            return getattr(self, field) if fallback else ""
        return getattr(self, field)

    def title_for(self, language: str, *, fallback: bool = False) -> str:
        return self._localized("title", language, fallback=fallback)

    def description_for(self, language: str, *, fallback: bool = False) -> str:
        return self._localized("description", language, fallback=fallback)

    def seo_title_for(self, language: str, *, fallback: bool = False) -> str:
        return self._localized("seo_title", language, fallback=fallback)

    def meta_description_for(self, language: str, *, fallback: bool = False) -> str:
        return self._localized("meta_description", language, fallback=fallback)

    def scripture_ref_for(self, language: str, *, fallback: bool = False) -> str:
        return self._localized("scripture_ref", language, fallback=fallback)

    def scripture_text_for(self, language: str, *, fallback: bool = False) -> str:
        return self._localized("scripture_text", language, fallback=fallback)

    def qa_for(self, language: str, *, fallback: bool = False) -> list:
        """The editorial Q&A list in ``language``; ``[]`` when untranslated.

        Rides the same per-field localization as the prose accessors above, like
        ``Author.faq_for``: ``_localized`` treats an empty ``qa`` as "not
        translated here" (the no-fallback rule) and, in that absent non-fallback
        case, returns its string sentinel ``""`` — which the trailing ``or []``
        normalizes back to the empty list this list-typed field should yield.
        """
        return self._localized("qa", language, fallback=fallback) or []

    def is_translated_into(self, language: str) -> bool:
        """Whether this shelf has a usable title in ``language``.

        A topic is a curatorial label; without a translated title there is
        nothing honest to render, so untranslated shelves are omitted from a
        locale rather than shown in English. Its books stay reachable through
        the catalogue, search and their author pages.
        """
        return bool(self.title_for(language).strip())


class TopicTranslation(models.Model):
    """A translated copy of a Topic's title/description in one language.

    Kept in a side-table (rather than per-language Topic rows) so a topic stays
    a single subject across languages; the serializers fall back per-field to
    the English original when a translation is missing.
    """

    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name="translations"
    )
    language = models.CharField(max_length=10)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    # Translated SEO overrides — the side-table twins of Topic.seo_title /
    # Topic.meta_description, surfaced by seo_title_for() / meta_description_for().
    # Blank until a locale ships one; readers fall back to the localized default,
    # not the English override (the no-fallback rule).
    seo_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    scripture_ref = models.CharField(max_length=120, blank=True)
    scripture_text = models.TextField(blank=True)
    # Translated Q&A — the side-table twin of Topic.qa, surfaced by qa_for().
    # Empty until a translation ships; readers fall back to nothing, not English.
    qa = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["topic", "language"]
        constraints = [
            models.UniqueConstraint(
                fields=["topic", "language"], name="uniq_topic_translation"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.topic.slug} [{self.language}]"


class TopicBook(models.Model):
    """Membership of a work in a topic, by canonical ``book_slug``.

    A soft reference (like PlanDay) rather than an FK, so it's language-agnostic
    and survives book re-imports. A work may belong to several topics.
    """

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="entries")
    book_slug = models.SlugField(max_length=160)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["topic", "book_slug"], name="uniq_topic_book"
            ),
        ]
        indexes = [
            # BookDetailSerializer asks "which shelves is this book on?" on
            # every book page — a lookup by book_slug alone. The unique
            # constraint leads with topic_id, so it cannot serve it.
            models.Index(fields=["book_slug"], name="idx_topicbook_slug"),
        ]

    def __str__(self) -> str:
        return f"{self.topic.slug} ⊃ {self.book_slug}"


class TopicSermon(models.Model):
    """Membership of a sermon in a topic, by canonical ``sermon_slug``.

    The sermon companion to ``TopicBook`` — same soft-reference, language-
    agnostic pattern, so a topic lists a sermon slug and each language shows it
    if that sermon exists there.
    """

    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name="sermon_entries"
    )
    sermon_slug = models.SlugField(max_length=160)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["topic", "sermon_slug"], name="uniq_topic_sermon"
            ),
        ]
        indexes = [
            # The sermon counterpart of idx_topicbook_slug.
            models.Index(fields=["sermon_slug"], name="idx_topicsermon_slug"),
        ]

    def __str__(self) -> str:
        return f"{self.topic.slug} ⊃ {self.sermon_slug}"


class TopicArticle(models.Model):
    """Membership of an article in a topic, by canonical ``article_slug``.

    The article companion to ``TopicBook``/``TopicSermon`` — same soft-reference,
    language-agnostic pattern. This is what makes the funnel bidirectional: a
    topic page lists the articles about it, and (via ``_topic_chips``) an article
    shows which topics it belongs to.
    """

    topic = models.ForeignKey(
        Topic, on_delete=models.CASCADE, related_name="article_entries"
    )
    article_slug = models.SlugField(max_length=180)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["topic", "article_slug"], name="uniq_topic_article"
            ),
        ]
        indexes = [
            # The article counterpart of idx_topicbook_slug: the article detail
            # serializer asks "which topics is this article on?" by article_slug.
            models.Index(fields=["article_slug"], name="idx_topicarticle_slug"),
        ]

    def __str__(self) -> str:
        return f"{self.topic.slug} ⊃ {self.article_slug}"


class PersonRole(models.TextChoices):
    """How a person relates to a book they are named in but did not write.

    A curated distinction, not a derived one — it says why this bio hangs off
    this work, and lets the page phrase it ("the subject of" vs "mentioned in").
    """

    FEATURED = "featured", "Featured"      # a central figure of the book
    SUBJECT = "subject", "Subject"         # the book is largely about them
    MENTIONED = "mentioned", "Mentioned"   # a notable figure who appears in it


class BookPerson(models.Model):
    """A person FOUND IN a book — a bio the work points at, not its author.

    An anthology or biography names people who have their own author page (a
    bio), and this links the two so the book can offer "people in this book" and
    the bio can offer "appears in". It is deliberately NOT ``Book.author``:
    authorship says who wrote the work, this says who it is about or who walks
    through it, and a work has one of the first and any number of the second.

    Modelled like ``TopicBook``: a soft ``book_slug`` reference rather than an FK
    to a per-language ``Book`` row, so ONE row covers every language edition of
    the work (the person is the same in all of them) and it survives a book
    re-import. The ``person`` end IS an FK, because an ``Author`` is canonical and
    language-agnostic already (its prose lives in ``AuthorTranslation``) — the
    same reason ``Book.author`` is an FK. A person with no bio in the reader's
    language simply isn't shown there, the usual no-English-fallback rule.
    """

    book_slug = models.SlugField(max_length=160)
    person = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name="featured_in_books"
    )
    role = models.CharField(
        max_length=20, choices=PersonRole.choices, default=PersonRole.FEATURED
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            # Leads with book_slug, so it also serves BookDetail's "who is in
            # this book?" lookup (filter by book_slug alone) — no separate
            # single-column index needed, unlike TopicBook whose unique index
            # leads with topic_id. The reverse lookup ("what does this person
            # appear in?") goes through person_id, which the FK indexes for free.
            models.UniqueConstraint(
                fields=["book_slug", "person"], name="uniq_book_person"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.book_slug} ▷ {self.person.slug} ({self.role})"


class SearchQueryLog(models.Model):
    """One executed library search — anonymous by design (no user, ever).

    Written fail-open by SearchView and read only by the admin search
    analytics (top queries, zero-result queries — the data that decides what
    content and features to build next). Search-as-you-type means prefix
    fragments ("pra", "pray") land here too; the analytics aggregate by full
    query string and skip fragments under 3 characters in the top lists, so
    the noise washes out. Rows older than 180 days are pruned by the
    trim_search_log release step.
    """

    query = models.CharField(max_length=200)
    language = models.CharField(max_length=10)
    # Capped at search.MAX_RESULTS (30) — zero vs nonzero is the meaningful
    # signal; don't average this expecting true match counts.
    result_count = models.PositiveIntegerField()
    # A "did you mean" hint was offered (only computed for zero-result queries).
    suggested = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # Both the popular-searches endpoint and the admin search report
            # filter on created_at AND language. `created_at` alone is indexed
            # (db_index on the field), which makes the window cheap but still
            # reads every language's rows inside it.
            models.Index(fields=["language", "created_at"], name="idx_searchlog_lang_at"),
        ]

    def __str__(self) -> str:
        return f"{self.query!r} [{self.language}] → {self.result_count}"


class SearchClickLog(models.Model):
    """A search result a reader actually opened — anonymous, like the query log.

    The question ``SearchQueryLog`` cannot answer. A query that returns forty
    matches and a query that returns the RIGHT match are indistinguishable
    there: both are "found something". The zero-result report therefore sees
    only the loudest failure, while a query answered with forty near-misses
    looks like a success. This is the other half — what got opened, from which
    position, and of which kind.

    Deliberately NOT a foreign key to a ``SearchQueryLog`` row. Handing the
    browser a row id to post back would make an analytics table writable by
    anything that can guess an integer; keying on the query text instead keeps
    both tables independent and anonymous, and they still join in aggregate,
    which is all the report needs.

    Pruned by the same ``trim_search_log`` release step.
    """

    query = models.CharField(max_length=200)
    language = models.CharField(max_length=10)
    #: Which kind of hit was opened — one of library.search's types.
    result_type = models.CharField(max_length=20)
    #: How far down the rendered list the opened result sat, 1-based.
    #:
    #: Read it as "did they have to hunt", not as a relevance rank, and don't
    #: average it across views. The merged list is ordered by TYPE first (books
    #: before passages, see the frontend's GROUP_ORDER), so a sermon can't be
    #: position 1 whenever a book matched; and with a type facet selected the
    #: same column becomes the rank within that one type. The signal this table
    #: exists for is whether a result was opened at all — that part is exact.
    position = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.query!r} [{self.language}] → {self.result_type} #{self.position}"


class Language(models.Model):
    """A content language the site knows about, and whether readers can see it.

    Before this table, "what languages exist" was spread across FOUR places that
    had to agree by hand: the translator's ``LANGUAGES`` (Bible + glossary), the
    frontend's UI locale list, its ``ADVERTISED_LOCALES``, and a
    ``LANGUAGE_NAMES`` display map that had drifted far enough to be missing
    Arabic while carrying five languages with no content at all. This row is the
    identity; the seed re-asserts it from ``library/language_seed.py`` each
    deploy. The translator's dict is gone — its Bible and glossary are fields
    below, so the row an admin creates is the row a translation job reads.

    ``status`` is the switch. Only ``LIVE`` languages are advertised to readers
    and to search engines. Because the reader is a *prerendered static site* —
    UI catalogues, pages, ``sitemap.xml`` and hreflang are all produced at build
    time — flipping this field cannot by itself change what a reader sees: a
    build has to run. The go-live action therefore changes status AND triggers a
    deploy; nothing here should imply an instant switch.

    There is deliberately no ``retired`` state and no review gate: taking a
    language back down is a status change to ``DRAFT`` (the next build stops
    advertising it), and translations go live wearing their "awaiting native
    review" badge rather than waiting on an approval step.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"  # known, not offered to readers
        TRANSLATING = "translating", "Translating"  # work in progress
        LIVE = "live", "Live"  # advertised: sitemap, hreflang, switcher

    code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=60, help_text="English name, e.g. Swahili")
    native_name = models.CharField(max_length=60, help_text="e.g. Kiswahili")
    # The Take Root translation code whose wording is authoritative for Scripture
    # in this language. Blank for the source language.
    bible_code = models.CharField(max_length=32, blank=True)
    bible_label = models.CharField(max_length=120, blank=True)
    # What that Bible is published under, and the credit its licence obliges us
    # to show. Blank means public domain — the norm here, and what every Bible in
    # the library was until Hindi. The IRV is CC BY-SA 4.0: Share-Alike binds
    # derivatives of the Bible text, not a library that quotes it, but BY still
    # wants the credit carried wherever the verses appear. Recording it as data
    # rather than a comment is what lets the readiness check refuse to launch a
    # language whose obligation nothing is discharging.
    bible_licence = models.CharField(
        max_length=60, blank=True, help_text="Blank for a public-domain text."
    )
    bible_attribution = models.CharField(
        max_length=300, blank=True, help_text="Credit line shown to readers."
    )
    # English term -> its rendering in this language, covering
    # translation.GLOSSARY_TERMS. It lives on the row rather than in code
    # because it is what makes a language added from the admin *translatable*:
    # the translate_* commands read this, so creating a row is enough to start
    # work. Repo-defined languages have theirs re-asserted from
    # library/language_seed.py each deploy.
    glossary = models.JSONField(default=dict, blank=True)
    # Right-to-left script (Arabic, Hebrew…). The reader's paged mode honours it.
    rtl = models.BooleanField(default=False)
    # The language content is authored in — English. Exempt from every readiness
    # check, and never a translation target.
    is_source = models.BooleanField(default=False)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT
    )
    # --- Readiness thresholds -------------------------------------------------
    # Per-language and admin-editable rather than one global constant: a language
    # with a big catalogue behind it should clear a higher bar than a first
    # beachhead language, and that judgement belongs to whoever is launching it.
    # 0 disables a check.
    min_books = models.PositiveIntegerField(default=5)
    # Stays 0 deliberately. A first launch stands on books and biographies; a
    # language with those and no sermons is still a good place to read, so
    # requiring them would block a launch on a format that isn't load-bearing.
    min_sermons = models.PositiveIntegerField(default=0)
    min_bios = models.PositiveIntegerField(default=3)
    # One translated plan. This defaulted to 0 on the stated grounds that "no
    # non-English language has ever had a published reading plan" — which was
    # simply wrong, read off a database that had not had `seed_plans` run.
    # Every live language has translated plans (lg 5, sw 3, es 2, pt 1), so the
    # premise for exempting them never held.
    min_plans = models.PositiveIntegerField(default=1)
    # Topic prose has no English fallback, so an untranslated shelf is hidden
    # rather than English — requiring all of them keeps the shelf page whole.
    require_all_topics = models.BooleanField(default=True)
    # The UI catalogue must be complete and translated: a missing message key or
    # a declared English placeholder renders in English, which is the least
    # visible way English leaks into a locale.
    require_complete_ui = models.BooleanField(default=True)
    went_live_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code}) — {self.status}"

    @property
    def is_live(self) -> bool:
        return self.status == self.Status.LIVE

    def natural_key(self):
        return (self.code,)


class ReviewOutcome(models.Model):
    """A reviewer's decision about one AI translation, and who made it.

    Deliberately a side-table rather than new values on ``Book.source_type`` /
    ``AuthorTranslation.reviewed``. Those two fields are load-bearing elsewhere:
    ``source_type`` drives the reader's "awaiting native review" badge and is
    create-only in ``seed_books`` / ``seed_sermons`` (so a deploy cannot walk an
    approval backwards), and ``reviewed`` tells ``seed_author_translations`` that
    an approver owns the wording. Neither can express "a human read this and it
    needs work" without breaking what already depends on them.

    So the approve path still flips the original field — nothing downstream
    changes — and this table records the decision *around* it: the outcome, the
    reason, the reviewer, the timestamp. That is what makes an approval
    undoable and auditable, and what gives a rejection somewhere to live
    instead of looking identical to "nobody has opened it yet".
    """

    class Kind(models.TextChoices):
        BOOK = "book", "Book"
        SERMON = "sermon", "Sermon"
        BIO = "bio", "Author bio"

    class Outcome(models.TextChoices):
        APPROVED = "approved", "Approved"
        NEEDS_WORK = "needs_work", "Needs work"

    kind = models.CharField(max_length=10, choices=Kind.choices)
    # Natural key of the reviewed row, matching the fixture convention: a book
    # and a sermon may legitimately share a slug, which is why `kind` is part of
    # the uniqueness constraint rather than the slug alone.
    slug = models.SlugField(max_length=200)
    language = models.CharField(max_length=10)
    outcome = models.CharField(max_length=12, choices=Outcome.choices)
    note = models.TextField(blank=True)
    reviewer = models.EmailField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)
    # Maker-checker: a reviewer who only holds ``review:act`` records a
    # *provisional* decision that does NOT flip ``source_type`` — the item stays
    # in the queue until someone with ``review:approve`` (or a super admin)
    # confirms it, which does the flip. ``confirmed_at`` unset ⇒ provisional;
    # ``reviewer`` stays the original proposer, ``confirmed_by`` is the approver
    # (they may differ — the two-person value of the workflow). A decision made
    # directly by an approver is confirmed on the spot (both set to them).
    confirmed_by = models.EmailField(blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-decided_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "slug", "language"], name="uniq_review_outcome"
            ),
        ]
        indexes = [models.Index(fields=["outcome", "language"])]

    @property
    def is_provisional(self) -> bool:
        """Recorded but not yet confirmed by an approver (so not applied)."""
        return self.confirmed_at is None

    def __str__(self) -> str:
        return f"{self.kind}:{self.slug} [{self.language}] {self.outcome}"


class AuditDismissal(models.Model):
    """An admin's acknowledgement that one advisory quality finding is accepted
    as-is — the content audit's "known-accepted list", made durable and undoable.

    The quality checks are heuristics with false positives: a legitimately short
    foreword trips ``tiny_chapters``, a chapter that ends on a scripture
    reference trips ``mid_sentence_splits``, a deliberate refrain trips
    ``duplicate_titles``. Without somewhere to record "a human looked and this is
    fine", every re-run re-lists the same accepted findings and the page trains
    its reader to ignore it. This table subtracts them and keeps a count so the
    check still shows the acceptance was a decision, not an oversight.

    Integrity findings are real structural defects and are deliberately NOT
    dismissible — they are fixed, not accepted (the dismiss endpoint rejects any
    check that is not a quality key).
    """

    #: The quality check key (e.g. ``giant_chapters``), matching the audit payload.
    #: Named ``check_key`` because ``check`` shadows ``Model.check()`` (E020); the
    #: API exposes it as ``check``. A bare CharField rather than TextChoices on
    #: purpose: the check catalogue is the shape of the audit payload, which lives
    #: in the view (``DISMISSIBLE_CHECKS``), and every write is validated against
    #: it there — so the enum has no second home to keep in sync on the model.
    check_key = models.CharField(max_length=40)
    #: Natural key of the flagged edition — a book is a per-language ROW sharing a
    #: slug, so language is part of the identity, not decoration.
    book = models.SlugField(max_length=200)
    language = models.CharField(max_length=10)
    #: The tail of the finding's identity: the chapter ``order`` for chapter-shaped
    #: checks, or the duplicated title for ``duplicate_titles``. Stringified so one
    #: column serves every check shape without a nullable-int/​nullable-text pair.
    #: Sized to the largest thing it can hold — a title (``Chapter.title`` /
    #: ``Book.title`` are max_length=300) — so accepting a long duplicate title
    #: can't overflow the column.
    ref = models.CharField(max_length=300)
    note = models.TextField(blank=True)
    reviewer = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["check_key", "book", "language", "ref"],
                name="uniq_audit_dismissal",
            ),
        ]
        indexes = [models.Index(fields=["check_key"])]

    def __str__(self) -> str:
        return f"{self.check_key}:{self.book} [{self.language}] {self.ref}"


class TranslationNote(models.Model):
    """One scripture reference in one translation, and where its wording came from.

    The translation pipeline already works this out and writes it into a pull
    request body, where it is invisible to the person who has to act on it. A
    verse recovered verbatim from our own shipped corpus needs no review; a verse
    the translator had to render itself is the actual review task, and there is
    currently no field anywhere that says which is which.

    Not a fixture model, and deliberately not part of the content file: content
    ships as one file per work so parallel translation jobs cannot collide, and
    threading review metadata into those files would reintroduce exactly that
    conflict. Upserted by the pipeline instead, like ``AuthorTranslation``.
    """

    class Status(models.TextChoices):
        MINED = "mined", "Mined verbatim from our corpus"
        SELF_RENDERED = "self_rendered", "Rendered by the translator — unverified"

    kind = models.CharField(max_length=10, choices=ReviewOutcome.Kind.choices)
    slug = models.SlugField(max_length=200)
    language = models.CharField(max_length=10)
    reference = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=Status.choices)
    # Which shipped file the wording was taken from, for a mined verse. Free of
    # a FK on purpose: the source may be a book in another language's fixture,
    # and a dangling reference must never block a translation from shipping.
    source_file = models.CharField(max_length=200, blank=True)
    # Where in the body it appears, so the reviewer can be taken straight there.
    block_index = models.PositiveIntegerField(null=True, blank=True)
    # Provenance for the whole translation, repeated per row so a single query
    # answers "which job produced this, and how".
    job_issue = models.PositiveIntegerField(null=True, blank=True)
    pull_request = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["kind", "slug", "language", "block_index", "reference"]
        indexes = [models.Index(fields=["kind", "slug", "language"])]

    def __str__(self) -> str:
        return f"{self.reference} [{self.language}] {self.status}"


class VerseReview(models.Model):
    """A reviewer's decision about ONE flagged scripture quotation.

    `ReviewOutcome` records the same thing for a whole work, and that is the
    granularity that made the backlog immovable: 187 translations are
    `ai_unreviewed` and none is approved, because approving one means answering
    "is this 35-chapter book right, yes or no" with no way to work the specific
    lines. `TranslationNote` already says WHICH lines — a verse the translator
    rendered itself, rather than recovered verbatim from our corpus, is the
    actual review task — but nothing could record that a reviewer had settled
    one, so the list was read-only advice.

    A SEPARATE TABLE, and not a field on `TranslationNote`, for a reason that is
    not stylistic: `seed_translation_notes` re-seeds by `delete()` then
    `bulk_create()`, so a decision stored there would not merely be walked back
    on the next deploy — it would be destroyed. Keyed by the same natural key so
    the two join at read time, and the notes can be rebuilt from the repo as
    often as the pipeline likes without touching a human judgement.

    Keyed per TRANSLATION — (kind, slug, language, reference) — not per
    (language, reference) across the corpus. #972 proposed the latter, on the
    grounds that one verse is re-flagged in every book so one decision should
    settle them all. The shipped notes do not bear that out: 1,570 flagged
    quotations span 1,517 distinct (language, reference) pairs and only 48 pairs
    recur at all, so grouping would collapse 3% of the work — and a rendering
    right in one book can still be wrong in another.

    Nor is it keyed per SITE, which would be the ideal: 33 rows across three
    files flag the same reference twice in one work at genuinely different
    blocks (`the-way-to-god.pt` quotes Ephesians 3:19b at block 0 and again at
    block 22), and one decision covers both. There is no key that would separate
    them — 984 of the 1,570 flagged notes carry no `block_index` at all, so for
    two thirds of the corpus the site is simply not recorded. The reviewer is
    shown each occurrence and its wording, so nothing is hidden; the judgement
    is one per verse per translation, and the counts are computed over DISTINCT
    references so a work can actually reach "settled".
    """

    class Outcome(models.TextChoices):
        APPROVED = "approved", "Rendering is right"
        NEEDS_WORK = "needs_work", "Needs work"

    kind = models.CharField(max_length=10, choices=ReviewOutcome.Kind.choices)
    slug = models.SlugField(max_length=200)
    language = models.CharField(max_length=10)
    reference = models.CharField(max_length=64)
    outcome = models.CharField(max_length=12, choices=Outcome.choices)
    note = models.TextField(blank=True)
    reviewer = models.EmailField(blank=True)
    decided_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind", "slug", "language", "reference"]
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "slug", "language", "reference"],
                name="uniq_verse_review",
            ),
        ]
        # The review screen asks "which of THIS translation's verses are
        # settled", once per item it lists.
        indexes = [models.Index(fields=["kind", "slug", "language"])]

    def __str__(self) -> str:
        return f"{self.reference} [{self.language}] {self.outcome}"


class AdminAction(models.Model):
    """Who changed what, from the admin dashboard.

    Nothing recorded this. Eight endpoints under ``/api/admin/`` mutate the
    library or its configuration — a language created, its Bible code or
    glossary edited, its readiness bar moved, a language taken live, a
    translation job filed, an author created, a document published or taken
    down — and afterwards the only evidence any of it happened was the changed
    row itself.
    "Who took Hindi live, and when?" had no answer.

    Not a replacement for ``ReviewOutcome``, which already records a review
    decision far better than this could: the outcome, the reason, the reviewer,
    and enough to undo it. That is workflow STATE, and the review screen reads
    it. This is the flat, append-only record of every admin write including
    those, so that one table answers "what has been done here" without a reader
    having to know which workflow owned which decision.

    Append-only by intent — nothing updates or deletes a row — which is what
    makes it worth reading. It is also why it stores the actor's email as text
    rather than a foreign key: the record must survive the account.
    """

    class Action(models.TextChoices):
        LANGUAGE_CREATE = "language.create", "Language created"
        LANGUAGE_SETTINGS = "language.settings", "Language settings changed"
        LANGUAGE_THRESHOLDS = "language.thresholds", "Readiness thresholds changed"
        LANGUAGE_GO_LIVE = "language.go_live", "Language taken live"
        TRANSLATION_JOB = "translation.job", "Translation job filed"
        CONTENT_EDIT_JOB = "content.edit_job", "Content edit job filed"
        AUTHOR_CREATE = "author.create", "Author created"
        CONTENT_PUBLISH = "content.publish", "Document published"
        CONTENT_UNPUBLISH = "content.unpublish", "Document unpublished"
        REVIEW_DECIDE = "review.decide", "Review decision recorded"
        REVIEW_UNDO = "review.undo", "Review decision undone"
        AUDIT_DISMISS = "audit.dismiss", "Audit finding accepted as known"
        AUDIT_RESTORE = "audit.restore", "Audit finding acceptance undone"
        ROLE_GRANT = "role.grant", "Admin access granted"
        ROLE_REVOKE = "role.revoke", "Admin access revoked"
        BROADCAST_CREATE = "broadcast.create", "Broadcast created"
        BROADCAST_EDIT = "broadcast.edit", "Broadcast edited"
        BROADCAST_DELETE = "broadcast.delete", "Broadcast deleted"
        BROADCAST_SEND = "broadcast.send", "Broadcast sent"
        BROADCAST_SCHEDULE = "broadcast.schedule", "Broadcast scheduled"
        BROADCAST_CANCEL = "broadcast.cancel", "Broadcast canceled"
        BROADCAST_TEST = "broadcast.test", "Broadcast test sent"
        FEEDBACK_TRIAGE = "feedback.triage", "Reader feedback triaged"

    action = models.CharField(max_length=32, choices=Action.choices)
    #: Who, by email — the identity `IsAdminEmail` gates on. Blank only when a
    #: DEBUG-mode request carried no token at all.
    actor = models.EmailField(blank=True)
    #: What it acted on, in the shape the rest of the codebase names things:
    #: "language:sw", "book:humility:es", "author:andrew-murray". Free text
    #: because the targets are of different kinds and this table only has to be
    #: readable, never joined.
    target = models.CharField(max_length=200, blank=True)
    #: Whatever the endpoint thought was worth keeping — the fields that
    #: changed, the outcome, the count. Small by construction: a summary, not a
    #: copy of the request.
    detail = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-at"]
        indexes = [
            models.Index(fields=["-at"], name="idx_adminaction_at"),
            models.Index(fields=["action", "-at"], name="idx_adminaction_action"),
            # One object's whole history: the activity screen can filter to a
            # single target, and this keyset-paginates it by descending id.
            models.Index(fields=["target", "-id"], name="idx_adminaction_target"),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.target} by {self.actor or 'unknown'}"


class ContentRevision(models.Model):
    """A monotonic counter of reader-visible content changed THROUGH the API.

    The prerendered reader and the public API's ETags both need to know when
    admin-borne content changed *without a deploy* — an import publish, a review
    approval, a language go-live. The repo content digest can't see those: it
    hashes files on disk, and those actions touch only the DB (library/http_cache
    spells this out). So every such mutation bumps this counter, through the one
    channel in ``library/invalidation.py``; the counter drives the deploy hook (so
    the static site rebuilds) and will key the public ETag (so a conditional
    request stops answering 304 the moment content changes).

    One row (``pk=1``). ``deploy_fired_*`` record the last hook fire so a burst of
    approvals coalesces into few rebuilds without leaving a change un-deployed.
    """

    revision = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    deploy_fired_at = models.DateTimeField(null=True, blank=True)
    deploy_fired_revision = models.BigIntegerField(default=0)

    def __str__(self) -> str:
        return f"content revision {self.revision}"

    @classmethod
    def bump(cls) -> int:
        """Increment the revision atomically and return the new value."""
        cls.objects.get_or_create(pk=1)
        # F() so two concurrent mutations can't both read N and write N+1.
        cls.objects.filter(pk=1).update(revision=models.F("revision") + 1)
        return cls.objects.values_list("revision", flat=True).get(pk=1)

    @classmethod
    def load(cls) -> ContentRevision:
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    def current(cls) -> int:
        """The revision as a single read, without creating the row.

        For the read path (the ETag, on every public request) — one SELECT, and
        no row yet means nothing has changed through the API, i.e. revision 0."""
        return cls.objects.values_list("revision", flat=True).first() or 0
