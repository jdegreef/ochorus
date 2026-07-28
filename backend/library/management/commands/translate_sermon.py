"""Translate a sermon into a target language via the AI-translate pipeline.

The sermon counterpart of ``translate_book``. Runs locally (needs
ANTHROPIC_API_KEY); the result is an ordinary Sermon row with
source_type="ai_unreviewed", shipped to prod as data like any other content
change (see the ship-content-fix skill). Scripture is fetched authoritatively
in the target language (Take Root Bible API) — see library.translation.

Idempotent: an already-translated sermon is skipped unless --force.

Usage:
    manage.py translate_sermon <slug> --language es
    manage.py translate_sermon <slug> --language sw --force
"""

from __future__ import annotations

import re

import anthropic
from django.core.management.base import BaseCommand, CommandError

from library.models import Book, Sermon
from library.translation import (
    LANGUAGES,
    translate_scripture_ref,
    translate_sermon,
    verify_bible_code,
)


class Command(BaseCommand):
    help = "AI-translate a sermon into a target language (ai_unreviewed)."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--language", required=True, choices=sorted(LANGUAGES))
        parser.add_argument("--force", action="store_true", help="Re-translate if it exists")
        parser.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh"])
        parser.add_argument("--dry-run", action="store_true", help="Show the plan, translate nothing")

    def handle(self, slug, language, force, effort, dry_run, **opts):
        try:
            source = Sermon.objects.select_related("author").get(slug=slug, language="en")
        except Sermon.DoesNotExist:
            raise CommandError(f"no English sermon with slug {slug!r}")

        existing = Sermon.objects.filter(slug=slug, language=language).first()
        if existing and not force:
            self.stdout.write(f"{source.title} → {LANGUAGES[language]['name']}: already done (use --force)")
            return

        self.stdout.write(
            f"{source.title} → {LANGUAGES[language]['name']} "
            f"({source.word_count} words), effort={effort}"
        )
        if dry_run:
            self.stdout.write(f"  would translate sermon: {source.title[:60]} [{source.scripture_ref}]")
            return

        # Preflight: a bad Bible code omits scripture silently, so check
        # BEFORE any paid model work (see verify_bible_code).
        try:
            verify_bible_code(language)
        except ValueError as e:
            raise CommandError(str(e)) from e

        client = anthropic.Anthropic()  # ANTHROPIC_API_KEY / ant auth profile

        self.stdout.write("→ translating body…")
        title, body_html, usage = translate_sermon(
            client, language, source.title, source.body_html, source.scripture_ref, effort=effort
        )
        ref = translate_scripture_ref(client, language, source.scripture_ref)

        Sermon.objects.update_or_create(
            slug=slug,
            language=language,
            defaults={
                "author": source.author,
                "title": title[:300] or source.title,
                "scripture_ref": ref[:160],
                "preached_on": source.preached_on,
                "body_html": body_html,
                "word_count": len(re.sub(r"<[^>]+>", " ", body_html).split()),
                "source_type": Book.SourceType.AI_UNREVIEWED,
                # source_url deliberately not copied: it points at the English edition.
                "sort_order": source.sort_order,
                "is_published": True,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {title[:60]} [{ref}] "
                f"({usage.input_tokens}in/{usage.output_tokens}out). "
                f"Marked ai_unreviewed — run `manage.py approve_sermon_translation {slug} "
                f"--language {language}` after native review."
            )
        )
