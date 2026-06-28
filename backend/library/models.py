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
    bio = models.TextField(blank=True)
    birth_year = models.IntegerField(null=True, blank=True)
    death_year = models.IntegerField(null=True, blank=True)
    original_language = models.CharField(max_length=10, default="en")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


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

    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.PUBLIC_DOMAIN,
    )
    source_url = models.URLField(blank=True)
    # Optional hex accent (e.g. "#3b5bdb") used to tint the generated cover.
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
