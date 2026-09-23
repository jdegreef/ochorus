"""Reader feedback — one suggestion, filed from anywhere on the site, into an
admin queue.

A signed-in reader (an ordinary reader or a scoped language admin) clicks the
feedback button on any page and describes a suggestion about the language, the
content, a feature, or a bug. The submit endpoint captures WHERE they were
(page URL + the resolved work, when the page is a book/sermon/etc.) so a
language note carries "which book, which chapter, which language" without the
admin having to ask. From there it is a triage queue the admin works like the
review queue: a status, an optional note, an assignee.

Feedback is not reader-visible content — approving or triaging it changes no
prerendered page — so nothing here touches the content-revision digest.
"""

from __future__ import annotations

from django.db import models


class FeedbackCategory(models.TextChoices):
    LANGUAGE = "language", "Language / translation"
    CONTENT = "content", "Content"
    FEATURE = "feature", "Feature idea"
    BUG = "bug", "Bug"
    OTHER = "other", "Other"


class FeedbackStatus(models.TextChoices):
    NEW = "new", "New"
    TRIAGING = "triaging", "Triaging"
    PLANNED = "planned", "Planned"
    IN_PROGRESS = "in_progress", "In progress"
    DONE = "done", "Done"
    DECLINED = "declined", "Declined"
    DUPLICATE = "duplicate", "Duplicate"


#: Statuses a submission can be moved to, and which the admin queue offers. NEW
#: is the birth state, never a triage target.
TRIAGE_STATUSES = frozenset(FeedbackStatus.values) - {FeedbackStatus.NEW}


class Feedback(models.Model):
    """One piece of reader feedback and its triage state."""

    # --- who ---
    # Signed-in only: the submitter is a UserProfile. CASCADE so deleting an
    # account removes their feedback with the rest of their data (the reading
    # app's deletion contract). ``submitter_email`` is a denormalised snapshot
    # for display in the queue without a join.
    submitter = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    submitter_email = models.EmailField(blank=True)
    #: The submitter's admin role at submit time (e.g. "language_admin",
    #: "super_admin", or "" for an ordinary reader) — a snapshot so the queue can
    #: badge a trusted reviewer even after their grants change. Drives the
    #: trust badge; recorded now, rendered later.
    submitter_role = models.CharField(max_length=40, blank=True)

    # --- what ---
    category = models.CharField(
        max_length=20, choices=FeedbackCategory.choices, default=FeedbackCategory.OTHER
    )
    body = models.TextField()

    # --- where (auto-captured context; all optional) ---
    page_url = models.TextField(blank=True)
    #: The kind of work the page was showing, when it was one — free text rather
    #: than a hard enum so a new content type needs no migration here.
    content_kind = models.CharField(max_length=20, blank=True)
    content_slug = models.CharField(max_length=200, blank=True)
    content_language = models.CharField(max_length=20, blank=True, db_index=True)
    chapter_ref = models.CharField(max_length=100, blank=True)
    #: The UI language the reader was using (may differ from content_language).
    ui_locale = models.CharField(max_length=20, blank=True)

    # --- triage ---
    status = models.CharField(
        max_length=20, choices=FeedbackStatus.choices, default=FeedbackStatus.NEW
    )
    assignee_email = models.EmailField(blank=True)
    admin_note = models.TextField(blank=True)
    duplicate_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicates",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["category", "-created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - repr only
        return f"{self.category} · {self.status} · {self.submitter_email}"
