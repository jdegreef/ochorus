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

import re

import anthropic
from django.core.management.base import BaseCommand, CommandError

from library.models import Book, Chapter
from library.translation import LANGUAGES, translate_book_meta, translate_chapter, verify_bible_code


class Command(BaseCommand):
    help = "AI-translate a book's chapters into a target language (ai_unreviewed)."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--language", required=True, choices=sorted(LANGUAGES))
        parser.add_argument("--chapters", help="Comma-separated chapter orders (default: all)")
        parser.add_argument("--force", action="store_true", help="Re-translate existing chapters")
        parser.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh"])
        parser.add_argument("--dry-run", action="store_true", help="Show the plan, translate nothing")

    def handle(self, slug, language, chapters, force, effort, dry_run, **opts):
        try:
            source = Book.objects.get(slug=slug, language="en")
        except Book.DoesNotExist:
            raise CommandError(f"no English book with slug {slug!r}")

        wanted = {int(c) for c in chapters.split(",")} if chapters else None
        todo = [
            c for c in source.chapters.all()
            if wanted is None or c.order in wanted
        ]

        target = Book.objects.filter(slug=slug, language=language).first()
        existing = set(target.chapters.values_list("order", flat=True)) if target else set()
        plan = [c for c in todo if force or c.order not in existing]

        self.stdout.write(
            f"{source.title} → {LANGUAGES[language]['name']}: "
            f"{len(plan)} chapter(s) to translate "
            f"({len(todo) - len(plan)} already done), effort={effort}"
        )
        if dry_run:
            for c in plan:
                self.stdout.write(f"  would translate ch{c.order}: {c.title[:60]}")
            return

        # Preflight: a bad Bible code omits scripture silently, so check
        # BEFORE any paid model work (see verify_bible_code).
        try:
            verify_bible_code(language)
        except ValueError as e:
            raise CommandError(str(e)) from e

        client = anthropic.Anthropic()  # ANTHROPIC_API_KEY / ant auth profile

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
                    "cover_url": source.cover_url,
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
            Chapter.objects.update_or_create(
                book=target,
                order=chapter.order,
                defaults={
                    "title": title[:300],
                    "body_html": body_html,
                    "word_count": len(re.sub(r"<[^>]+>", " ", body_html).split()),
                },
            )
            total_in += usage.input_tokens
            total_out += usage.output_tokens
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ {title[:60]} ({usage.input_tokens}in/{usage.output_tokens}out)"
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
