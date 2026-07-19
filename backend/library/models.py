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

from . import fts


class AuthorManager(models.Manager):
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
    # Public-domain portrait (self-hosted under /portraits/, B&W-processed).
    # Blank for contemporary authors — the UI falls back to an initials avatar.
    photo_url = models.URLField(blank=True)
    birth_year = models.IntegerField(null=True, blank=True)
    death_year = models.IntegerField(null=True, blank=True)
    original_language = models.CharField(max_length=10, default="en")
    # A house byline rather than a human (e.g. "Ochorus Originals", which
    # authors the compiled anthologies). Kept off the Biographies shelf, whose
    # cards and schema.org ItemList both speak of Person — their works are still
    # reachable from /books and the byline's own author page.
    is_imprint = models.BooleanField(default=False)
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

    def _localized(self, field: str, language: str) -> str:
        """A translated prose field in ``language``, else the English original.

        Reads ``self.translations.all()`` (not ``.filter()``) so a caller that
        prefetched translations pays no extra query.
        """
        if language and language != self.original_language:
            tr = next((t for t in self.translations.all() if t.language == language), None)
            if tr and getattr(tr, field):
                return getattr(tr, field)
        return getattr(self, field)

    def bio_for(self, language: str) -> str:
        """Short bio in ``language``, falling back to the English original."""
        return self._localized("bio", language)

    def bio_html_for(self, language: str) -> str:
        """Long-form bio HTML in ``language``, falling back to the English original."""
        return self._localized("bio_html", language)


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
    reviewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["author", "language"]
        constraints = [
            models.UniqueConstraint(
                fields=["author", "language"], name="uniq_author_translation"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.author.slug} [{self.language}]"


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
    description = models.TextField(blank=True)
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
        ]

    def natural_key(self):
        return (self.slug, self.language)

    natural_key.dependencies = ["library.author"]

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
    word_count = models.PositiveIntegerField(default=0)
    # Stored tsvector (Postgres only; NULL on SQLite). Kept by save() +
    # backfill_search_vectors; GIN-indexed in migration 0041. See library/fts.py.
    search_vector = SearchVectorField(null=True, editable=False, serialize=False)

    objects = ChapterManager()

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["book", "order"], name="uniq_chapter_book_order"
            ),
        ]

    def natural_key(self):
        return self.book.natural_key() + (self.order,)

    natural_key.dependencies = ["library.book"]

    def __str__(self) -> str:
        return f"{self.book.slug}/{self.order} — {self.title}"

    def save(self, *args, **kwargs):
        from .text import html_to_text

        self.body_text = html_to_text(self.body_html)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "body_html" in update_fields:
            kwargs["update_fields"] = list(update_fields) + ["body_text"]
        super().save(*args, **kwargs)
        # Skip the vector rebuild when a scoped save touches no indexed field
        # (it re-tokenises the whole body — pure waste for a flag flip).
        # Both the FK name and its attname: update_fields accepts either.
        if update_fields is None or not {
            "title", "body_html", "body_text", "book", "book_id"
        }.isdisjoint(update_fields):
            fts.refresh_chapter(self)


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
    # Cleaned, structured HTML body (paragraphs, headings, blockquotes).
    body_html = models.TextField()
    # Plain text derived from body_html; what full-text search indexes.
    body_text = models.TextField(blank=True, default="")
    word_count = models.PositiveIntegerField(default=0)
    # Stored tsvector (Postgres only; NULL on SQLite). Kept by save() +
    # backfill_search_vectors; GIN-indexed in migration 0041. See library/fts.py.
    search_vector = SearchVectorField(null=True, editable=False, serialize=False)
    source_url = models.URLField(blank=True)

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

    def natural_key(self):
        return (self.slug, self.language)

    natural_key.dependencies = ["library.author"]

    def __str__(self) -> str:
        return f"{self.title} — {self.author.name} ({self.language})"

    def save(self, *args, **kwargs):
        from .text import html_to_text

        self.body_text = html_to_text(self.body_html)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "body_html" in update_fields:
            kwargs["update_fields"] = list(update_fields) + ["body_text"]
        super().save(*args, **kwargs)
        # Skip the vector rebuild when a scoped save touches no indexed field
        # (e.g. approve_sermon_translation flips only source_type).
        # Both the FK name and its attname: update_fields accepts either.
        if update_fields is None or not {
            "title", "body_html", "body_text", "scripture_ref",
            "author", "author_id", "language",
        }.isdisjoint(update_fields):
            fts.refresh_sermon(self)


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
    # A themed Scripture epigraph shown on the topic page (public-domain wording).
    scripture_ref = models.CharField(max_length=120, blank=True)
    scripture_text = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "title"]

    def __str__(self) -> str:
        return self.title

    def _localized(self, field: str, language: str) -> str:
        """A translated prose field in ``language``, else the English original.

        Reads ``self.translations.all()`` (not ``.filter()``) so a caller that
        prefetched translations pays no extra query.
        """
        if language and language != "en":
            tr = next((t for t in self.translations.all() if t.language == language), None)
            if tr and getattr(tr, field):
                return getattr(tr, field)
        return getattr(self, field)

    def title_for(self, language: str) -> str:
        return self._localized("title", language)

    def description_for(self, language: str) -> str:
        return self._localized("description", language)

    def scripture_ref_for(self, language: str) -> str:
        return self._localized("scripture_ref", language)

    def scripture_text_for(self, language: str) -> str:
        return self._localized("scripture_text", language)


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
    scripture_ref = models.CharField(max_length=120, blank=True)
    scripture_text = models.TextField(blank=True)
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

    def __str__(self) -> str:
        return f"{self.topic.slug} ⊃ {self.sermon_slug}"


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
    result_count = models.PositiveIntegerField()
    # A "did you mean" hint was offered (only computed for zero-result queries).
    suggested = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.query!r} [{self.language}] → {self.result_count}"
