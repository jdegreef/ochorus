"""Index the Bible references cited in chapter bodies.

Scans each chapter's plain text for valid references (pythonbible-validated)
and stores them as ChapterCitation verse-id spans, which is what lets search
answer "John 3:16" with every passage that cites it.

Idempotent and incremental: only chapters whose `citations_indexed_at` is
unset are scanned (Chapter.save() clears the stamp when the body changes, and
fixture loads bypass save(), so fresh seeds arrive unstamped). Run on every
deploy via `manage.py release` — a full pass over ~1,500 chapters takes a few
seconds. `--all` forces a rescan of everything.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from library.models import Chapter, ChapterCitation
from library.scripture import extract_citations


class Command(BaseCommand):
    help = "Index Bible citations in chapter bodies (incremental; --all rescans)."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Rescan every chapter.")

    def handle(self, *args, **opts):
        qs = Chapter.objects.all()
        if not opts["all"]:
            qs = qs.filter(citations_indexed_at__isnull=True)
        now = timezone.now()
        scanned = rows = 0
        for chapter in qs.iterator(chunk_size=200):
            cites = extract_citations(chapter.body_text)
            with transaction.atomic():
                chapter.citations.all().delete()
                if cites:
                    ChapterCitation.objects.bulk_create(
                        ChapterCitation(
                            chapter=chapter,
                            ref_text=c["ref"],
                            start_verse_id=c["start"],
                            end_verse_id=c["end"],
                            count=c["count"],
                        )
                        for c in cites
                    )
                # .update() skips save() so the stamp isn't immediately
                # re-cleared. Known, accepted race: a concurrent body save
                # between our read and this stamp loses its invalidation until
                # the next body save or --all; the window is sub-second and
                # deploy-time only.
                Chapter.objects.filter(pk=chapter.pk).update(
                    citations_indexed_at=now
                )
            scanned += 1
            rows += len(cites)
        if scanned:
            self.stdout.write(
                self.style.SUCCESS(f"Indexed {rows} citations across {scanned} chapters.")
            )
        else:
            self.stdout.write("Citation index already current.")
