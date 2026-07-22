"""Per-user reading state: where you are in a book, and what you've marked.

All rows hang off :class:`accounts.UserProfile` (the app-side identity for a
Supabase-authenticated user). Content is referenced by ``book_slug`` +
``language`` rather than a FK to :class:`library.Book`, mirroring how the rest of
the app addresses books: the slug is the canonical, language-agnostic handle, so
a reader's progress in "humility" survives a book row being re-imported and works
uniformly across translations. The frontend keeps the same data in localStorage
as an offline cache; these rows are the synced source of truth when signed in.
"""

from __future__ import annotations

from django.db import models


class WorkKind(models.TextChoices):
    """What a row's ``book_slug`` names.

    Sermons joined the reading layer in 2026-07 (roadmap #10): a sermon is a
    single document, so its rows pin ``chapter_order`` to 1. Author biographies
    followed (roadmap #12) with the same single-document shape — the slug names
    the author. The slug column keeps its historical ``book_slug`` name to
    spare a rename across the API, merge payloads, and every reader's
    localStorage cache.
    """

    BOOK = "book", "Book"
    SERMON = "sermon", "Sermon"
    BIO = "bio", "Biography"


class ReadingProgress(models.Model):
    """The last place a reader was in a given work (book or sermon).

    One row per (user, kind, work). ``paragraph_index`` is the top-level block index
    within the chapter's rendered ``.reading`` container — the same paragraph
    anchor the frontend uses, chosen so a saved position survives font-size and
    column-width changes (unlike a pixel offset).
    """

    profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="progress",
    )
    kind = models.CharField(
        max_length=10, choices=WorkKind.choices, default=WorkKind.BOOK
    )
    book_slug = models.SlugField(max_length=160)
    language = models.CharField(max_length=10, default="en")
    chapter_order = models.PositiveIntegerField(default=1)
    paragraph_index = models.PositiveIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "kind", "book_slug"],
                name="uniq_progress_profile_work",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.profile_id}:{self.kind}:{self.book_slug} → ch{self.chapter_order}"


class FavoriteKind(models.TextChoices):
    """What a favorite's ``slug`` names.

    Broader than :class:`WorkKind`: a reader follows *authors* and saves
    *plans* as well as works. Kept as its own enum so the reading kinds and
    the favoritable kinds can evolve independently.
    """

    AUTHOR = "author", "Author"
    BOOK = "book", "Book"
    PLAN = "plan", "Plan"
    SERMON = "sermon", "Sermon"


class Favorite(models.Model):
    """A reader's saved author / book / plan / sermon (roadmap #18).

    Slug-referenced like everything else in this app, so a favorite survives
    content re-imports and is language-agnostic (a favorite author is the
    same author in every language).
    """

    profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    kind = models.CharField(max_length=10, choices=FavoriteKind.choices)
    slug = models.SlugField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "kind", "slug"], name="uniq_favorite_profile_item"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.profile_id} ♥ {self.kind}:{self.slug}"


class ChapterMarks(models.Model):
    """A reader's highlights and notes within one chapter.

    Marks are anchored at *paragraph* granularity: ``highlights`` is a JSON array
    of block indices, ``notes`` a JSON object of ``{index: text}``. Paragraph-
    level anchoring is deliberately coarse — it survives re-rendering without the
    fragile character-offset bookkeeping that text-range anchoring needs, and it
    matches the shape the frontend already stores locally.
    """

    profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="marks",
    )
    kind = models.CharField(
        max_length=10, choices=WorkKind.choices, default=WorkKind.BOOK
    )
    book_slug = models.SlugField(max_length=160)
    language = models.CharField(max_length=10, default="en")
    chapter_order = models.PositiveIntegerField()

    # Text-range marks: [{"id", "p", "s", "e", "note"?}, ...] — see reading/marks.py.
    marks = models.JSONField(default=list)
    # Legacy paragraph-level fields, converted to `marks` by data migration
    # 0002 and no longer written; kept only so old rows remain inspectable.
    highlights = models.JSONField(default=list)
    notes = models.JSONField(default=dict)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["book_slug", "chapter_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "kind", "book_slug", "chapter_order"],
                name="uniq_marks_profile_work_chapter",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.profile_id}:{self.book_slug}/{self.chapter_order}"

    @property
    def is_empty(self) -> bool:
        return not self.marks

