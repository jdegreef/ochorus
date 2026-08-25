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

from django.core.management.base import CommandError

from library.management.commands._translate_base import TranslateCommand
from library.models import Book, Sermon
from library.sanitize import clean_fragment
from library.translation import (
    translate_scripture_ref,
    translate_sermon,
    translate_summary,
)


class Command(TranslateCommand):
    help = "AI-translate a sermon into a target language (ai_unreviewed)."

    force_help = "Re-translate if it exists"

    def add_target_arguments(self, parser):
        parser.add_argument("slug")

    def handle(self, slug, language, force, effort, dry_run, **opts):
        cfg = self.language_config(language)

        try:
            source = Sermon.objects.select_related("author").get(slug=slug, language="en")
        except Sermon.DoesNotExist:
            raise CommandError(f"no English sermon with slug {slug!r}") from None

        existing = Sermon.objects.filter(slug=slug, language=language).first()
        if existing and not force:
            self.stdout.write(f"{source.title} → {cfg['name']}: already done (use --force)")
            return

        self.stdout.write(
            f"{source.title} → {cfg['name']} "
            f"({source.word_count} words), effort={effort}"
        )
        if dry_run:
            self.stdout.write(f"  would translate sermon: {source.title[:60]} [{source.scripture_ref}]")
            return

        self.preflight(language)

        client = self.client()

        self.stdout.write("→ translating body…")
        title, body_html, usage = translate_sermon(
            client, language, source.title, source.body_html, source.scripture_ref, effort=effort
        )
        ref = translate_scripture_ref(client, language, source.scripture_ref)
        # The shelf prints the "In brief" under every sermon. Leaving it behind
        # gave the translated shelves bare titles while the English one read
        # properly — 38 rows across es/lg/sw/pt/ar/uk before this was fixed.
        summary = translate_summary(client, language, source.summary)

        # The model's output is untrusted: it is a regex capture of generated
        # text, produced from source prose scraped off the public web, and it
        # lands in a column the reader renders with {@html}. Sanitize before it
        # is stored — and before word_count is taken from it, so the count
        # describes the text that was actually kept.
        body_html = clean_fragment(body_html)

        Sermon.objects.update_or_create(
            slug=slug,
            language=language,
            defaults={
                "author": source.author,
                "title": title[:300] or source.title,
                "scripture_ref": ref[:160],
                "summary": summary,
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
