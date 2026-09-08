"""Shared base for the book and sermon translation-approval commands.

``approve_translation`` and ``approve_sermon_translation`` were the same 66-line
command twice, differing in about twenty substituted identifiers — the model,
the noun, and which fixture path to write. The sermon one even imported ``Book``
solely to read ``Book.SourceType``, which is the tell: it was a copy, not a
sibling.

Two copies of a rule mean two places to fix it, and the rule here is not
obvious. Approval must reach the committed FIXTURE as well as the row, because
``source_type`` is create-only in the seed — flip only the DB and the next
fresh-DB rebuild silently re-gates the work back to unreviewed. And the fixture
write must WARN rather than raise, because the DB flip has already committed by
then: a traceback would read to an automated caller as "the approval failed" and
invite a retry of something that already happened. Both subtleties now live in
one place.

``approve_author_translation`` is deliberately NOT built on this. It takes a
list of slugs rather than one, flips two booleans rather than ``source_type``,
has no fixture to persist to (translated bios ship as files under
``migrations/data/``), and reports a batch. Folding it in would mean a command
whose arguments are mutually exclusive depending on ``--kind`` — worse than the
duplication it removed.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from library import content_fixtures as cf
from library.models import Book


class ApproveSourceTypeCommand(BaseCommand):
    """Flip one work's ``source_type`` to ai_reviewed, and persist it.

    Subclasses set ``model``, ``noun`` and ``fixture_path``; everything else —
    arguments, refusals, the fixture round-trip and its failure handling — is
    shared.
    """

    #: The model to look up by (slug, language).
    model = None
    #: What to call it in messages: "book", "sermon".
    noun = ""
    #: The attribute holding the work's display title. Book/Sermon use "title";
    #: an Article has no author and names its headline "h1".
    title_field = "title"

    @staticmethod
    def fixture_path(slug: str, language: str):
        """Where this work's committed fixture lives."""
        raise NotImplementedError

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--language", required=True)
        parser.add_argument(
            "--no-fixture",
            action="store_true",
            help="Flip only the DB row; don't update the committed fixture file.",
        )

    def handle(self, slug, language, no_fixture=False, **opts):
        try:
            obj = self.model.objects.get(slug=slug, language=language)
        except self.model.DoesNotExist:
            raise CommandError(
                f"no {self.noun} {slug!r} in language {language!r}"
            ) from None
        # Sermon shares Book's SourceType vocabulary rather than declaring its
        # own, so the enum is read off Book for both.
        if obj.source_type == Book.SourceType.PUBLIC_DOMAIN:
            raise CommandError(
                f"that {self.noun} is a public-domain original, not a translation"
            )
        obj.source_type = Book.SourceType.AI_REVIEWED
        obj.save(update_fields=["source_type"])
        title = getattr(obj, self.title_field)
        self.stdout.write(
            self.style.SUCCESS(f"✓ {title} ({language}) marked reviewed")
        )

        if no_fixture:
            return
        # Persist the approval into the committed fixture too, or a fresh-DB
        # rebuild would silently re-gate it to unreviewed (source_type is
        # create-only in the seed, so the live flip alone never round-trips).
        path = self.fixture_path(slug, language)
        if not path.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ no fixture {path.name}: approval is DB-only and would be "
                    f"lost on a rebuild. Serialize this {self.noun} to a fixture "
                    "and commit it."
                )
            )
            return
        # The DB flip is the primary action and has already succeeded; a fixture
        # write failure (unexpected match count, read-only filesystem) must warn,
        # not raise — a traceback here would read to an automated caller as "the
        # approval failed" and trigger a retry.
        try:
            if cf.persist_source_type(path, Book.SourceType.AI_REVIEWED):
                self.stdout.write(f"  ↳ updated fixture {path.name} — commit it")
        except (ValueError, OSError) as exc:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ DB approved, but couldn't update fixture {path.name}: {exc}. "
                    "Set source_type to ai_reviewed there by hand and commit it."
                )
            )
