"""Move saved highlights and bookmarks to where their words are after a text repair.

A deploy can change a chapter's text under readers' saved places: a body
correction, a re-import, a split or merged paragraph. A highlight is stored as
offsets into that text plus ``q``, the words it covered, and a bookmark as a
paragraph index plus the paragraph's opening words; this step re-finds each by
its words and rewrites the stored position where they moved (see
``reading.anchor``). The reader finds a moved highlight at render time anyway —
this makes the stored copy agree, so the notebook, every device and the
bookmark list do too.

Runs in ``release`` after every content step. Idempotent: a place whose words
are still where it says is left untouched, so a deploy that repaired nothing
writes nothing. A failure on one row is logged and skipped — a reader's saved
place must never fail a deploy.
"""

from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from itertools import batched, groupby

from django.core.management.base import BaseCommand
from django.db import transaction

from library.models import Article, Author, Chapter, Sermon
from reading.anchor import block_texts, refind_bookmark, remap_mark_list
from reading.marks import merge_mark_lists
from reading.models import Bookmark, ChapterMarks, Removal, WorkKind
from reading.views import _record_removal


def _bodies(kind: str, slug: str, order: int) -> dict[str, str]:
    """Every edition's stored body for one chapter / document, by language."""
    if kind == WorkKind.BOOK:
        rows = Chapter.objects.filter(book__slug=slug, order=order)
        return dict(rows.values_list("book__language", "body_html"))
    if kind == WorkKind.SERMON:
        return dict(Sermon.objects.filter(slug=slug).values_list("language", "body_html"))
    if kind == WorkKind.ARTICLE:
        return dict(Article.objects.filter(slug=slug).values_list("language", "body_html"))
    if kind == WorkKind.BIO:
        author = Author.objects.filter(slug=slug).prefetch_related("translations").first()
        if author is None:
            return {}
        langs = {author.original_language, *(t.language for t in author.translations.all())}
        return {lang: author.bio_html_for(lang) for lang in langs}
    return {}


# Rows are walked ordered by work, so holding only the latest one is enough —
# a library's worth of parsed chapters never sits in memory at once.
@lru_cache(maxsize=1)
def _editions(kind: str, slug: str, order: int) -> dict[str, list[str]]:
    """Block texts of every edition of one chapter / document, by language."""
    return {lang: block_texts(body) for lang, body in _bodies(kind, slug, order).items()}


def _anchored(marks) -> bool:
    # The cheap pre-check that spares a row with nothing to re-find its text load.
    return isinstance(marks, list) and any(
        isinstance(m, dict) and m.get("q") and m.get("lang") for m in marks
    )


class Command(BaseCommand):
    help = "Re-find saved highlights and bookmarks whose text moved (deploy step)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Report what would move; write nothing."
        )

    def handle(self, *args, dry_run: bool = False, **opts):
        _editions.cache_clear()
        marks_moved, rows_changed = self._marks(dry_run)
        bookmarks_moved = self._bookmarks(dry_run)
        prefix = "[dry run] would move" if dry_run else "moved"
        self.stdout.write(
            f"remap_marks: {prefix} {marks_moved} highlight segment(s) in "
            f"{rows_changed} chapter(s), {bookmarks_moved} bookmark(s)"
        )

    # Neither pass iterates a live cursor: each write commits, and a commit
    # invalidates a Postgres server-side cursor (see emails/broadcasts.py) —
    # which would fail the release. Keys are listed first, rows read in batches.
    _BATCH = 500

    def _marks(self, dry_run: bool) -> tuple[int, int]:
        moved_total = rows_changed = 0
        order = ("kind", "book_slug", "chapter_order")
        pks = list(
            ChapterMarks.objects.exclude(marks=[]).order_by(*order).values_list("pk", flat=True)
        )
        for batch in batched(pks, self._BATCH):
            rows = (
                ChapterMarks.objects.filter(pk__in=batch)
                .order_by(*order)
                .only("pk", "kind", "book_slug", "chapter_order", "marks")
            )
            for row in rows:
                if not _anchored(row.marks):
                    continue
                try:
                    moved = self._remap_row(row, dry_run)
                except Exception as exc:  # noqa: BLE001 — never fail a deploy over one row
                    self.stderr.write(f"remap_marks: skipped marks row {row.pk}: {exc!r}")
                    continue
                if moved:
                    moved_total += moved
                    rows_changed += 1
        return moved_total, rows_changed

    @staticmethod
    def _remap_row(row: ChapterMarks, dry_run: bool) -> int:
        texts_for = _editions(row.kind, row.book_slug, row.chapter_order).get
        _, moved = remap_mark_list(row.marks, texts_for)
        if not moved or dry_run:
            return moved
        # Recompute under the lock on what is stored NOW: a sync may have
        # landed since the scan read the row.
        with transaction.atomic():
            locked = ChapterMarks.objects.select_for_update().get(pk=row.pk)
            remapped, moved = remap_mark_list(locked.marks or [], texts_for)
            if moved:
                # A copy pushed at the old offsets between the repair and this
                # step now coincides with the moved mark: keep one.
                locked.marks = merge_mark_lists(remapped, [])
                locked.save(update_fields=["marks", "updated_at"])
        return moved

    def _bookmarks(self, dry_run: bool) -> int:
        moved = 0
        rows = list(
            Bookmark.objects.exclude(snippet="")
            .order_by("kind", "book_slug", "chapter_order", "profile_id", "paragraph_index")
            .values_list(
                "pk", "kind", "book_slug", "chapter_order", "profile_id",
                "paragraph_index", "snippet",
            )
        )
        # One reader's bookmarks in one chapter move together: planned first,
        # then applied so each spot is vacated before it is filled — a shift
        # down moves the last bookmark first, a shift up the first. One at a
        # time in reading order, a bookmark moving onto its still-unmoved
        # neighbour's spot would be taken for a duplicate and dropped.
        for (kind, slug, order, _), group in groupby(rows, key=lambda r: r[1:5]):
            group = list(group)
            try:
                editions = list(_editions(kind, slug, order).values())
                moves = [
                    (pk, p, new_p)
                    for pk, *_, p, snippet in group
                    if (new_p := refind_bookmark(editions, p, snippet)) is not None
                ]
                moves.sort(key=lambda mv: (mv[2] < mv[1], -mv[1] if mv[2] > mv[1] else mv[1]))
                for pk, p, new_p in moves:
                    if not dry_run:
                        self._move_bookmark(pk, p, new_p)
                    moved += 1
            except Exception as exc:  # noqa: BLE001 — never fail a deploy over one row
                self.stderr.write(f"remap_marks: skipped bookmarks {kind}:{slug}/{order}: {exc!r}")
        return moved

    @staticmethod
    def _move_bookmark(pk: int, old_p: int, new_p: int) -> None:
        """Move a bookmark to block ``new_p``. A bookmark is identified by its
        spot, so the old spot is then removed the way a reader's own tap removes
        it — tombstoned, so a device still holding it there can't merge it back
        — and any tombstone at the new spot is lifted, as a live save lifts it.
        When the reader already has a bookmark at the new spot, this one simply
        goes."""
        with transaction.atomic():
            bm = Bookmark.objects.select_for_update().filter(pk=pk).first()
            if bm is None or bm.paragraph_index != old_p:
                return
            spot = {"profile_id": bm.profile_id, "kind": bm.kind, "chapter_order": bm.chapter_order}
            if not Bookmark.objects.filter(
                **spot, book_slug=bm.book_slug, paragraph_index=new_p
            ).exists():
                bm.paragraph_index = new_p
                bm.save(update_fields=["paragraph_index"])
                Removal.objects.filter(
                    **spot, domain=Removal.Domain.BOOKMARK, slug=bm.book_slug,
                    paragraph_index=new_p,
                ).delete()
            _record_removal(
                bm.profile, Removal.Domain.BOOKMARK, bm.kind, bm.book_slug,
                datetime.now(UTC), live=True, order=bm.chapter_order, p=old_p,
            )
