"""Translate a book into a target language via the AI-translate pipeline.

Runs locally (needs ANTHROPIC_API_KEY); the result is ordinary Book/Chapter
rows with source_type="ai_unreviewed", shipped to prod as data like any other
content change (see the ship-content-fix skill).

Idempotent/resumable: already-translated chapters are skipped unless --force,
so a partial failure just needs a re-run.

Usage:
    manage.py translate_book <slug> --language es
    manage.py translate_book <slug> --language sw --chapters 1,2 --force
"""

from __future__ import annotations

from django.core.management.base import CommandError

from library.covers import cover_path
from library.management.commands._translate_base import TranslateCommand
from library.models import Book, Chapter
from library.sanitize import clean_fragment
from library.translation import (
    translate_book_meta,
    translate_chapter,
)


class Command(TranslateCommand):
    help = "AI-translate a book's chapters into a target language (ai_unreviewed)."

    force_help = "Re-translate existing chapters"

    def add_target_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--chapters", help="Comma-separated chapter orders (default: all)")

    def handle(self, slug, language, chapters, force, effort, dry_run, **opts):
        cfg = self.language_config(language)

        try:
            source = Book.objects.get(slug=slug, language="en")
        except Book.DoesNotExist:
            raise CommandError(f"no English book with slug {slug!r}") from None

        wanted = {int(c) for c in chapters.split(",")} if chapters else None
        todo = [
            c for c in source.chapters.all()
            if wanted is None or c.order in wanted
        ]

        target = Book.objects.filter(slug=slug, language=language).first()
        existing = set(target.chapters.values_list("order", flat=True)) if target else set()
        plan = [c for c in todo if force or c.order not in existing]

        self.stdout.write(
            f"{source.title} → {cfg['name']}: "
            f"{len(plan)} chapter(s) to translate "
            f"({len(todo) - len(plan)} already done), effort={effort}"
        )
        if dry_run:
            for c in plan:
                self.stdout.write(f"  would translate ch{c.order}: {c.title[:60]}")
            return

        self.preflight(language)

        client = self.client()

        if target is None or force:
            self.stdout.write("→ translating book metadata…")
            meta = translate_book_meta(
                client, language, source.title, source.subtitle, source.description
            )
            target, _ = Book.objects.update_or_create(
                slug=slug,
                language=language,
                defaults={
                    "author": source.author,
                    "title": meta["title"][:300] or source.title,
                    "subtitle": meta["subtitle"][:300],
                    "description": meta["description"],
                    "source_type": Book.SourceType.AI_UNREVIEWED,
                    # NOT source.cover_url: that is the English plate, and it
                    # carries the English title over a translated card. Point at
                    # this language's own path — `scripts/localize_covers.py`
                    # (or `generate_covers <slug>`) draws the file there — and
                    # inherit the work's colour so the fallback plate is the
                    # right hue in the meantime.
                    "cover_url": cover_path(slug, language)[0],
                    "cover_color": source.cover_color,
                    # pdf_url deliberately left empty: the PDF is the English
                    # edition and would mislead on a translated book page.
                    "sort_order": source.sort_order,
                    "is_published": True,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"  ✓ {target.title}"))

        total_in = total_out = 0
        for chapter in plan:
            self.stdout.write(f"→ ch{chapter.order}: {chapter.title[:60]}")
            title, body_html, usage = translate_chapter(
                client, language, chapter.title, chapter.body_html, effort=effort
            )
            # The model's output is untrusted: it is a regex capture of generated
            # text, produced from source prose scraped off the public web, and it
            # lands in a column the reader renders with {@html}. Sanitize before
            # it is stored, not hopefully at render.
            body_html = clean_fragment(body_html)
            Chapter.objects.update_or_create(
                book=target,
                order=chapter.order,
                defaults={
                    "title": title[:300],
                    "body_html": body_html,
                },
            )
            total_in += usage.input_tokens
            total_out += usage.output_tokens
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ {title[:60]} ({usage.input_tokens}in/{usage.output_tokens}out)"
                )
            )

        # If new/updated chapters landed in a book a native reviewer had already
        # approved, that book now contains unreviewed AI text — re-gate it so the
        # "awaiting native review" badge returns. (The metadata branch above only
        # sets source_type when the book is first created or --force'd.)
        if plan and target.source_type == Book.SourceType.AI_REVIEWED:
            target.source_type = Book.SourceType.AI_UNREVIEWED
            target.save(update_fields=["source_type"])
            self.stdout.write(
                self.style.WARNING(
                    "  ⚠ chapters changed in an approved book — reset to "
                    "ai_unreviewed; re-review required"
                )
            )

        # update_or_create goes through save(), so body_text derives; but make
        # sure any bulk path stays covered on future edits.
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {len(plan)} chapters, {total_in} input / {total_out} output tokens. "
                f"Book is marked ai_unreviewed — run `manage.py approve_translation {slug} "
                f"--language {language}` after native review."
            )
        )
