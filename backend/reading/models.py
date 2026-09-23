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
    # The CLIENT's as-of time for this position (its Date.now() when the read
    # happened), distinct from `updated_at` (server clock, auto_now, which the
    # analytics window on). Recency is judged on THIS so a device is compared to
    # its own clock, not the server's — comparing a client timestamp to the
    # server's save time would freeze any device whose clock lags the server.
    # Null on rows written before this field existed / by pre-timestamp clients.
    client_updated_at = models.DateTimeField(null=True, blank=True)

    # When the reader FINISHED this work: reaching the end of the last chapter
    # (books) or of the single document (sermons, bios), or an explicit "mark as
    # finished". Null while it is still in progress. This is what splits the
    # reader's "Continue reading" list (finished_at IS NULL) from the finished /
    # history shelf (finished_at IS NOT NULL), and it counts for every readable
    # kind — unlike the old client-side guess (chapter_order >= chapter_count),
    # which only worked for books and re-broke if a book was re-imported at a
    # different length.
    #
    # Finishing UNIONS across devices: the earliest non-null wins and a routine
    # position write never clears it (see `_upsert_progress`), so a completion
    # earned on any device is never lost — the same lossless rule as plan days
    # and favorites. Reopening a finished work does not un-finish it. The one
    # thing that clears it is an explicit un-finish, which — like un-favoriting —
    # is a live-only signal the sign-in merge deliberately does not carry.
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "kind", "book_slug"],
                name="uniq_progress_profile_work",
            ),
        ]
        indexes = [
            # The engagement dashboard groups by (kind, book_slug) and counts
            # finishers per work. The unique constraint leads with `profile`, so
            # none of that could use it — every panel scanned the whole table.
            models.Index(fields=["kind", "book_slug"], name="idx_progress_work"),
            # ...and the weekly-active panel windows on updated_at. `ordering`
            # is not an index.
            models.Index(fields=["updated_at"], name="idx_progress_updated"),
        ]

    def __str__(self) -> str:
        return f"{self.profile_id}:{self.kind}:{self.book_slug} → ch{self.chapter_order}"


class FavoriteKind(models.TextChoices):
    """What a favorite's ``slug`` names.

    Broader than :class:`WorkKind`: a reader follows *authors* and saves
    *plans*, *topics*, *articles* and individual *quotes* as well as works.
    Kept as its own enum so the reading kinds and the favoritable kinds can
    evolve independently. A quote's slug is the quote's own permanent address
    (author slug + text hash); a topic/article/plan/author slug names that row.
    """

    AUTHOR = "author", "Author"
    BOOK = "book", "Book"
    PLAN = "plan", "Plan"
    SERMON = "sermon", "Sermon"
    TOPIC = "topic", "Topic"
    ARTICLE = "article", "Article"
    QUOTE = "quote", "Quote"


class Favorite(models.Model):
    """A reader's saved author / book / plan / sermon / topic / article / quote.

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


class Removal(models.Model):
    """A reader deliberately took something off their shelf: a reading position
    (the Bookshelf's "Remove from shelf"), a heart, or a bookmark.

    The live DELETE removes the row itself, so everything else that reads
    ``ReadingProgress`` / ``Favorite`` — state, analytics, admin — is unchanged.
    This row is the TOMBSTONE that keeps it removed. Without it the removal
    doesn't survive the next sign-in merge: every signed-in device runs that
    merge on each app load, uploads what it still holds locally, and the union
    quietly re-creates the row on the account (and so on every device).

    With it, an incoming position or heart that is NOT newer than ``removed_at``
    is dropped as stale; one that is newer — the reader opened the book again,
    or re-hearted it — is a genuine new act, which clears the tombstone and
    lands. ``removed_at`` is the removing device's clock, compared with the
    incoming write's client clock (``client_updated_at`` / the heart's saved-at),
    the same client-to-client rule ``_upsert_progress`` uses for recency.

    ``kind`` is the WorkKind for a position or a bookmark and the FavoriteKind
    for a heart; ``domain`` says which. A bookmark is identified by its spot, so
    its tombstone also carries ``chapter_order`` / ``paragraph_index``; the other
    domains leave them 0. Kept forever — one small row per removal — because a
    device can be offline for any length of time.
    """

    class Domain(models.TextChoices):
        PROGRESS = "progress", "Reading position"
        FAVORITE = "favorite", "Favorite"
        BOOKMARK = "bookmark", "Bookmark"

    profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="removals",
    )
    domain = models.CharField(max_length=10, choices=Domain.choices)
    kind = models.CharField(max_length=10)
    slug = models.SlugField(max_length=160)
    # Bookmarks only (0 otherwise). Not nullable: NULLs never collide in a
    # unique constraint, so two tombstones for one position or heart could
    # otherwise coexist.
    chapter_order = models.PositiveIntegerField(default=0)
    paragraph_index = models.PositiveIntegerField(default=0)
    removed_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "domain", "kind", "slug", "chapter_order", "paragraph_index"],
                name="uniq_removal_profile_spot",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.profile_id} ✕ {self.domain}:{self.kind}:{self.slug}"


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
    # Deletion tombstones: {group_id: deleted_at_ms}. A mark removed on one device
    # is recorded here so a stale device re-pushing the full list can't resurrect
    # it (the live PUT unions marks now, so absence no longer means "deleted").
    # See reading/marks.py (reconcile_marks) and backend/CLAUDE.md.
    deleted = models.JSONField(default=dict)
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



class Bookmark(models.Model):
    """A reader's explicit bookmark — a paragraph they saved on purpose.

    Modelled like :class:`Favorite`: one row per saved spot, created by a live
    PUT and removed by a DELETE, and merges union by position — so a bookmark
    made on any device shows on all of them. Un-bookmarking is a real server
    DELETE (it propagates), and the DELETE leaves a ``Removal`` tombstone for
    the spot, so a device still holding the bookmark can't merge it back — the
    same rule as favorites and reading positions. That is the accepted tradeoff for a
    curated set that unions, and it keeps this a plain add/remove model rather
    than the tombstoned reconcile ChapterMarks needs.

    Identity is the position — (profile, kind, book_slug, chapter_order,
    paragraph_index) — because the reader keeps at most one bookmark per
    paragraph. ``snippet``/``title`` are cached display text so a bookmark shows
    without refetching the chapter; ``bm_id``/``at`` carry the client's own id
    and save-time so the localStorage cache round-trips through the server
    unchanged. A sermon or biography is a single document, so its
    ``chapter_order`` is always 1 and ``paragraph_index`` alone locates the spot.
    """

    profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    kind = models.CharField(
        max_length=10, choices=WorkKind.choices, default=WorkKind.BOOK
    )
    book_slug = models.SlugField(max_length=160)
    chapter_order = models.PositiveIntegerField(default=1)
    paragraph_index = models.PositiveIntegerField(default=0)

    # Cached display text + the client's own id, so the reader shows a bookmark
    # without refetching the chapter and its list key stays stable across a sync.
    # (The client also keeps a local save-time, but nothing reads it — the list
    # sorts by position — so it isn't stored here.)
    bm_id = models.CharField(max_length=80, blank=True)
    snippet = models.CharField(max_length=300, blank=True)
    title = models.CharField(max_length=300, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["book_slug", "chapter_order", "paragraph_index"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "profile",
                    "kind",
                    "book_slug",
                    "chapter_order",
                    "paragraph_index",
                ],
                name="uniq_bookmark_profile_spot",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.profile_id} ▸ {self.kind}:{self.book_slug}"
            f"/{self.chapter_order}#{self.paragraph_index}"
        )


class ReadingDay(models.Model):
    """One calendar day on which the reader read something — the activity log
    behind the reading streak.

    Deliberately coarse: a single row per (profile, day), not per session, so
    it's cheap and union-merges perfectly across devices (a day read on *any*
    device counts toward the streak). The day is stored as the reader's local
    date (the client sends 'YYYY-MM-DD'); a streak is a human, wall-clock notion,
    so we don't normalise to UTC.
    """

    profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="reading_days",
    )
    day = models.DateField()

    class Meta:
        ordering = ["-day"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "day"], name="uniq_readingday_profile_day"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.profile_id} read {self.day}"


class PlanProgress(models.Model):
    """A reader's progress through one reading plan — synced across devices.

    A plan is a fixed sequence of daily readings; progress is which day-numbers
    the reader has completed plus when they started. Both union-merge cleanly:
    a day marked done on any device stays done (like Favorites / ReadingDay),
    and the earliest start wins. Slug-referenced like everything in this app, so
    progress survives a plan re-import and is language-agnostic (a plan is the
    same plan in every language it's published in).

    ``done`` is a JSON list of 1-based day numbers, kept sorted and unique.
    """

    profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="plan_progress",
    )
    plan_slug = models.SlugField(max_length=160)
    started_at = models.DateTimeField()
    done = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "plan_slug"], name="uniq_planprogress_profile_plan"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.profile_id} plan:{self.plan_slug} ({len(self.done)} done)"


class ReadingSession(models.Model):
    """One sitting of reading — the signal behind "time on site".

    A session is a contiguous stretch of reading. The client accumulates the
    *active* reading time into the current session and syncs it, rolling to a
    new session after a long gap of no reading. Active time is the same
    plausible words-over-milliseconds the pace estimator already measures
    (foreground, non-idle, real forward reading — see the frontend `pace.ts`),
    so ``seconds`` is time actually spent reading, not the wall-clock span
    (which would fold in idle and paused time). ``started_at`` / ``last_seen_at``
    bound the sitting, for time-of-day and recency.

    Identity is (profile, ``client_id``): the client owns the session id, so a
    sync is an idempotent upsert and a session survives a reload mid-sitting.
    Union-merge like the rest of the reading layer — ``seconds`` only grows (the
    larger wins), the earliest start and latest last-seen win — so a retry or a
    second device never double-counts or drops time.

    Per-profile and coarse by design: no per-paragraph log, no clickstream, just
    how long each sitting lasted and roughly when. Ochorus stays privacy-light
    (no IP; see accounts/geo.py). ``kind``/``book_slug``/``language`` record what
    the reader opened the sitting on — context only; a sitting may span works.
    """

    profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    # The client's own id for this sitting — the upsert key, so a sync is
    # idempotent and a reload mid-sitting keeps writing the same row.
    client_id = models.CharField(max_length=80)
    started_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    # Active reading seconds in the sitting (monotonic — see class docstring).
    seconds = models.PositiveIntegerField(default=0)
    # What the reader opened the sitting on (context; blank on an older client).
    kind = models.CharField(
        max_length=10, choices=WorkKind.choices, blank=True, default=""
    )
    book_slug = models.SlugField(max_length=160, blank=True)
    language = models.CharField(max_length=10, blank=True, default="")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "client_id"], name="uniq_session_profile_client"
            ),
        ]
        indexes = [
            # The engagement rollups window on started_at / last_seen_at; the
            # per-user page reads a profile's sessions newest-first.
            models.Index(
                fields=["profile", "-last_seen_at"], name="idx_session_profile_seen"
            ),
            models.Index(fields=["started_at"], name="idx_session_started"),
        ]

    def __str__(self) -> str:
        return f"{self.profile_id} read {self.seconds}s @ {self.started_at:%Y-%m-%d %H:%M}"
