"""Shared scaffolding for the AI-translation commands.

``translate_book``, ``translate_sermon``, ``translate_author`` and
``translate_topic`` each open the same way: the same four flags, the same
language-registry lookup, the same two preflight checks, the same client. Four
copies of a preamble, and the middle of each command — what it actually
translates — is genuinely its own.

The scaffolding is worth sharing for one reason above the others. The preflight
runs BEFORE any paid model work, because a bad Bible code does not fail: it
omits scripture silently, and you discover it after paying to translate a book.
A new command written by copying an existing one inherits that ordering by luck;
a new command written on this base inherits it by construction.

``contemporize_book`` is deliberately not here. It produces the ``en-modern``
edition, so it has no target language to look up, no Bible and no glossary to
verify, and a ``--mode`` of its own. It shares the shape but not the rules.
"""

from __future__ import annotations

import anthropic
from django.core.management.base import BaseCommand, CommandError

from library.languages import config as language_config
from library.translation import verify_bible_code, verify_glossary

#: The reasoning-effort ladder every translate command offers.
EFFORT_CHOICES = ["low", "medium", "high", "xhigh"]


class TranslateCommand(BaseCommand):
    """Base for the commands that translate content into a target language."""

    #: What ``--force`` means here — the one flag whose help genuinely differs.
    force_help = "Re-translate content that already exists"

    def add_arguments(self, parser):
        # The subclass's own arguments come first so ``--help`` reads the way
        # the command is typed: the thing being translated, then how.
        self.add_target_arguments(parser)
        parser.add_argument(
            "--language", required=True, help="Target language code (see the admin)"
        )
        parser.add_argument("--force", action="store_true", help=self.force_help)
        parser.add_argument("--effort", default="high", choices=EFFORT_CHOICES)
        parser.add_argument(
            "--dry-run", action="store_true", help="Show the plan, translate nothing"
        )

    def add_target_arguments(self, parser):
        """Hook: the positional target and any command-specific flags."""

    # -- the shared preamble ---------------------------------------------------

    def language_config(self, language: str) -> dict:
        """The target's registry entry, or a clear error.

        The Bible code and glossary come from the Language registry, so an
        unknown code should be a legible failure here rather than a KeyError
        somewhere further in.
        """
        try:
            return language_config(language)
        except ValueError as exc:
            raise CommandError(str(exc)) from None

    def preflight(self, language: str) -> None:
        """Check the target's Bible and glossary BEFORE any paid model work.

        A bad Bible code omits scripture silently rather than failing, so this
        has to run before the first request, not after the first failure.
        """
        try:
            verify_bible_code(language)
            verify_glossary(language)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

    def client(self) -> anthropic.Anthropic:
        """The Anthropic client (ANTHROPIC_API_KEY / ant auth profile)."""
        return anthropic.Anthropic()
