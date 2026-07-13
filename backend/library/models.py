"""Content model for Ochorus.

A canonical work is identified by ``Book.slug``; each *language* of that work is
a separate ``Book`` row sharing the slug, keyed unique by ``(slug, language)``.
This mirrors Take Root's per-language ``Translation``/``Verse`` pattern: there is
no separate "Work" row — the shared slug is what ties translations together, and
it's what the AI-translation pipeline keys on (same slug, new language).
"""

from __future__ import annotations

from django.db import models


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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

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

    class Meta:
        ordering = ["sort_order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "language"], name="uniq_book_slug_language"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.language})"

    @property
    def chapter_count(self) -> int:
        return self.chapters.count()


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

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["book", "order"], name="uniq_chapter_book_order"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.book.slug}/{self.order} — {self.title}"

    def save(self, *args, **kwargs):
        from .text import html_to_text

        self.body_text = html_to_text(self.body_html)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "body_html" in update_fields:
            kwargs["update_fields"] = list(update_fields) + ["body_text"]
        super().save(*args, **kwargs)


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
    # When it was preached, if known (day precision optional — see year note).
    preached_on = models.DateField(null=True, blank=True)
    # Cleaned, structured HTML body (paragraphs, headings, blockquotes).
    body_html = models.TextField()
    # Plain text derived from body_html; what full-text search indexes.
    body_text = models.TextField(blank=True, default="")
    word_count = models.PositiveIntegerField(default=0)
    source_url = models.URLField(blank=True)

    sort_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "language"], name="uniq_sermon_slug_language"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.author.name} ({self.language})"

    def save(self, *args, **kwargs):
        from .text import html_to_text

        self.body_text = html_to_text(self.body_html)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "body_html" in update_fields:
            kwargs["update_fields"] = list(update_fields) + ["body_text"]
        super().save(*args, **kwargs)


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

    class Meta:
        ordering = ["sort_order", "title"]
        constraints = [
            models.UniqueConstraint(
                fields=["slug", "language"], name="uniq_plan_slug_language"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.language})"


class PlanDay(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="days")
    # 1-based day within the plan.
    day = models.PositiveIntegerField()
    book_slug = models.SlugField(max_length=160)
    chapter_order = models.PositiveIntegerField()

    class Meta:
        ordering = ["day"]
        constraints = [
            models.UniqueConstraint(fields=["plan", "day"], name="uniq_plan_day"),
        ]

    def __str__(self) -> str:
        return f"{self.plan_id} day {self.day} → {self.book_slug}/{self.chapter_order}"
