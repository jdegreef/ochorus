"""Translate author biographies into a target language via the AI pipeline.

Runs locally (needs ANTHROPIC_API_KEY); the result is AuthorTranslation rows
(reviewed=False). To SHIP them, export the text to
``migrations/data/author_bios_<lang>/`` (``<slug>.short.txt`` + ``<slug>.html``) —
the ``seed_author_translations`` deploy step is the delivery path, survives a
fresh-DB rebuild, and re-asserts those files over unreviewed DB rows on every
deploy, so rows shipped any other way don't stick. The short ``bio`` is
translated by default; pass --long to also translate the long-form
``bio_html``.

Reuses translate_chapter (a titled HTML blob with Scripture substitution) with
an empty title — a bio is just a prose body.

Idempotent/resumable: an already-translated field is skipped unless --force.

Usage:
    manage.py translate_author --language es                 # all authors, short bio
    manage.py translate_author andrew-murray --language sw --long
"""

from __future__ import annotations

from django.core.management.base import CommandError

from library.management.commands._translate_base import TranslateCommand
from library.models import Author, AuthorTranslation
from library.sanitize import clean_bio_html
from library.translation import translate_chapter


class Command(TranslateCommand):
    help = "AI-translate author bios into a target language (unreviewed)."

    force_help = "Re-translate existing fields"

    def add_target_arguments(self, parser):
        parser.add_argument("slugs", nargs="*", help="Author slugs (default: all with a bio)")
        parser.add_argument("--long", action="store_true", help="Also translate the long bio_html")

    def handle(self, slugs, language, long, force, effort, dry_run, **opts):
        cfg = self.language_config(language)

        authors = Author.objects.exclude(bio="")
        if slugs:
            authors = authors.filter(slug__in=slugs)
        authors = list(authors.order_by("name"))
        if not authors:
            raise CommandError("no matching authors with a bio")

        existing = {
            t.author_id: t
            for t in AuthorTranslation.objects.filter(
                author__in=authors, language=language
            )
        }

        def needs(author, field):
            tr = existing.get(author.id)
            done = bool(tr and getattr(tr, field))
            return force or not done

        plan = [
            a for a in authors
            if needs(a, "bio") or (long and a.bio_html and needs(a, "bio_html"))
        ]
        self.stdout.write(
            f"{len(plan)}/{len(authors)} author(s) to translate → "
            f"{cfg['name']} (bio{' + bio_html' if long else ''}), effort={effort}"
        )
        if dry_run:
            for a in plan:
                fields = ["bio"] + (["bio_html"] if long and a.bio_html else [])
                todo = [f for f in fields if needs(a, f)]
                self.stdout.write(f"  {a.slug}: {', '.join(todo)}")
            return

        self.preflight(language)

        client = self.client()
        total_in = total_out = 0

        for a in plan:
            tr = existing.get(a.id)
            bio_out = tr.bio if tr else ""
            html_out = tr.bio_html if tr else ""

            if needs(a, "bio"):
                self.stdout.write(f"→ {a.slug}: bio")
                _, bio_out, usage = translate_chapter(client, language, "", a.bio, effort=effort)
                total_in += usage.input_tokens
                total_out += usage.output_tokens

            if long and a.bio_html and needs(a, "bio_html"):
                self.stdout.write(f"→ {a.slug}: bio_html")
                _, html_out, usage = translate_chapter(
                    client, language, "", a.bio_html, effort=effort
                )
                total_in += usage.input_tokens
                total_out += usage.output_tokens

            AuthorTranslation.objects.update_or_create(
                author=a,
                language=language,
                # source_stale clears: this wording was just made from the
                # CURRENT English, whatever the old row was translated from.
                defaults={
                    # bio is plain text (escaped at render); bio_html is rendered
                    # with {@html}, so the model's output is sanitized first. The
                    # BIO profile, not the chapter one — a biography's <aside
                    # class="prayer"> callouts and <cite> attributions are
                    # legitimate markup the chapter allowlist would strip.
                    "bio": bio_out, "bio_html": clean_bio_html(html_out),
                    "reviewed": False, "source_stale": False,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"  ✓ {a.name}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {len(plan)} author(s), {total_in} input / {total_out} output tokens. "
                f"Bios are unreviewed — run `manage.py approve_author_translation "
                f"--language {language}` after native review."
            )
        )
