"""Produce a "Modern English" edition of an English book.

Creates a separate Book row sharing the work's slug, in content language
``en-modern`` (see library/contemporize.py), with source_type="ai_unreviewed".
The original English row is never modified. Ship the result to prod as data
like any content change (see the ship-content-fix skill), then, after review,
run ``manage.py approve_translation <slug> --language en-modern``.

Two modes:
  --mode light    Deterministic; no model, no key. Ships today.
  --mode careful  Model-backed (needs ANTHROPIC_API_KEY); run locally.

Idempotent/resumable: already-done chapters are skipped unless --force.

Usage:
    manage.py contemporize_book <slug>                     # light (default)
    manage.py contemporize_book <slug> --mode careful
    manage.py contemporize_book <slug> --chapters 1,2 --force
"""

from __future__ import annotations

import anthropic
from django.core.management.base import BaseCommand, CommandError

from library.contemporize import MODERN_LANGUAGE, modernize_chapter, modernize_light
from library.models import Book, Chapter
from library.sanitize import clean_fragment


class Command(BaseCommand):
    help = "Create a Modern English edition of a book (en-modern, ai_unreviewed)."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument(
            "--mode",
            default="light",
            choices=["light", "careful"],
            help="light = deterministic (no key); careful = model-backed",
        )
        parser.add_argument("--chapters", help="Comma-separated chapter orders (default: all)")
        parser.add_argument("--force", action="store_true", help="Redo existing chapters")
        parser.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh"])
        parser.add_argument("--dry-run", action="store_true", help="Show the plan, change nothing")

    def handle(self, slug, mode, chapters, force, effort, dry_run, **opts):
        try:
            source = Book.objects.get(slug=slug, language="en")
        except Book.DoesNotExist:
            raise CommandError(f"no English book with slug {slug!r}") from None
        if source.source_type != Book.SourceType.PUBLIC_DOMAIN:
            raise CommandError(
                f"{slug!r} (en) is {source.source_type}, not a public-domain original; "
                "only contemporize the authentic English edition"
            )

        wanted = {int(c) for c in chapters.split(",")} if chapters else None
        todo = [c for c in source.chapters.all() if wanted is None or c.order in wanted]

        target = Book.objects.filter(slug=slug, language=MODERN_LANGUAGE).first()
        existing = set(target.chapters.values_list("order", flat=True)) if target else set()
        plan = [c for c in todo if force or c.order not in existing]

        self.stdout.write(
            f"{source.title} → Modern English ({mode}): {len(plan)} chapter(s) "
            f"({len(todo) - len(plan)} already done)"
        )
        if dry_run:
            for c in plan:
                self.stdout.write(f"  would contemporize ch{c.order}: {c.title[:60]}")
            return

        client = None
        if mode == "careful":
            client = anthropic.Anthropic()  # ANTHROPIC_API_KEY / auth profile

        if target is None or force:
            # Metadata is left as the original English (titles/blurbs rarely need
            # modernizing); only the body prose is contemporized.
            target, _ = Book.objects.update_or_create(
                slug=slug,
                language=MODERN_LANGUAGE,
                defaults={
                    "author": source.author,
                    "title": source.title,
                    "subtitle": source.subtitle,
                    "cover_title": source.cover_title,
                    "description": source.description,
                    "source_type": Book.SourceType.AI_UNREVIEWED,
                    "source_url": source.source_url,
                    "attribution": source.attribution,
                    "cover_url": source.cover_url,
                    "cover_color": source.cover_color,
                    "publication_year": source.publication_year,
                    "sort_order": source.sort_order,
                    "is_published": True,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"  ✓ {target.title} [en-modern]"))

        total_in = total_out = 0
        for chapter in plan:
            self.stdout.write(f"→ ch{chapter.order}: {chapter.title[:60]}")
            if mode == "light":
                title = modernize_light(chapter.title)
                body_html = modernize_light(chapter.body_html)
            else:
                title, body_html, usage = modernize_chapter(
                    client, chapter.title, chapter.body_html, effort=effort
                )
                total_in += usage.input_tokens
                total_out += usage.output_tokens
            # Untrusted in both modes: the model path returns generated text, and
            # the light path rewrites source prose scraped off the public web.
            # This column is rendered with {@html}.
            body_html = clean_fragment(body_html)
            Chapter.objects.update_or_create(
                book=target,
                order=chapter.order,
                defaults={
                    "title": title[:300],
                    "body_html": body_html,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"  ✓ {title[:60]}"))

        # New/updated chapters in an already-approved edition mean it again holds
        # unreviewed AI text — re-gate it so the "awaiting native review" badge
        # returns. (The metadata branch only sets source_type on create/--force.)
        if plan and target.source_type == Book.SourceType.AI_REVIEWED:
            target.source_type = Book.SourceType.AI_UNREVIEWED
            target.save(update_fields=["source_type"])
            self.stdout.write(
                self.style.WARNING(
                    "  ⚠ chapters changed in an approved edition — reset to "
                    "ai_unreviewed; re-review required"
                )
            )

        tail = (
            f" ({total_in} input / {total_out} output tokens)" if mode == "careful" else ""
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {len(plan)} chapters{tail}. Marked ai_unreviewed — run "
                f"`manage.py approve_translation {slug} --language {MODERN_LANGUAGE}` "
                "after review."
            )
        )
